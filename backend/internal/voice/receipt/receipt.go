// Package receipt verifies the in-app purchase of voice_clone: App Store (StoreKit 2 signed
// transaction, offline against Apple Root CA - G3) and Google Play (Play Developer API with a
// service account). Without credentials it fails closed with ErrUnavailable; there is no bypass
// except the explicit test mode, which refuses to work on a production host.
package receipt

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"os"
	"slices"
	"strings"
	"time"
)

const (
	PlatformIOS     = "ios"
	PlatformAndroid = "android"
	PlatformTest    = "test"

	ModeStore = "store"
	ModeTest  = "test"
)

// Purchase is a verified purchase of the product.
type Purchase struct {
	Platform      string
	ProductID     string
	TransactionID string
	OriginalID    string // stable across restores: originalTransactionId / orderId
	Environment   string
	PurchasedAt   time.Time
}

var (
	// ErrUnavailable: the server cannot verify receipts (no credentials, store down). Never a bypass.
	ErrUnavailable = errors.New("receipt_verification_unavailable")
	// ErrInvalid: the receipt was checked and rejected.
	ErrInvalid = errors.New("receipt_invalid")
)

func invalid(why string) error { return fmt.Errorf("%w: %s", ErrInvalid, why) }

func unavailable(err error) error { return fmt.Errorf("%w: %v", ErrUnavailable, err) }

// Config of the verifier (VOICE_RECEIPT_* and friends, see ConfigFromEnv).
type Config struct {
	Mode            string   // store (default) | test
	ProductID       string   // voice_clone
	AppleBundleID   string   // empty = App Store receipts unavailable
	AppleEnvs       []string // accepted environments, default Production, Sandbox (App Review buys in Sandbox)
	GooglePackage   string   // empty = Play receipts unavailable
	GoogleSAFile    string   // service account JSON; missing file = Play receipts unavailable
	ProductionHosts []string // test mode is refused on these hosts
	PublicURL       string   // VOICE_PUBLIC_URL; its host counts as production when it is in ProductionHosts
}

func ConfigFromEnv() Config {
	return Config{
		Mode:            strings.TrimSpace(os.Getenv("VOICE_RECEIPT_MODE")),
		ProductID:       os.Getenv("VOICE_PRODUCT_ID"),
		AppleBundleID:   os.Getenv("VOICE_APPLE_BUNDLE_ID"),
		AppleEnvs:       split(os.Getenv("VOICE_APPLE_ENVIRONMENTS")),
		GooglePackage:   os.Getenv("VOICE_GOOGLE_PACKAGE"),
		GoogleSAFile:    os.Getenv("VOICE_GOOGLE_SERVICE_ACCOUNT_FILE"),
		ProductionHosts: split(os.Getenv("VOICE_PRODUCTION_HOSTS")),
		PublicURL:       os.Getenv("VOICE_PUBLIC_URL"),
	}
}

func split(s string) []string {
	var out []string
	for _, v := range strings.Split(s, ",") {
		if v = strings.TrimSpace(v); v != "" {
			out = append(out, v)
		}
	}
	return out
}

// DefaultProductionHosts are the public API hosts; test mode never works there.
var DefaultProductionHosts = []string{"webtoon-api.ol1n.com"}

// Verifier dispatches a receipt to the store that issued it.
type Verifier struct {
	mode       string
	product    string
	apple      *Apple
	google     *Google
	prodHosts  []string
	prodConfig bool // VOICE_PUBLIC_URL points at a production host
	log        *slog.Logger
}

// New builds the verifier. A bad service account file is an error (better a failed start than a
// silently disabled store); a missing one only disables Play.
func New(c Config, log *slog.Logger) (*Verifier, error) {
	if log == nil {
		log = slog.Default()
	}
	if c.ProductID == "" {
		c.ProductID = "voice_clone"
	}
	if len(c.AppleEnvs) == 0 {
		c.AppleEnvs = []string{"Production", "Sandbox"}
	}
	if len(c.ProductionHosts) == 0 {
		c.ProductionHosts = DefaultProductionHosts
	}
	if c.Mode == "" {
		c.Mode = ModeStore
	}
	if c.Mode != ModeStore && c.Mode != ModeTest {
		return nil, fmt.Errorf("VOICE_RECEIPT_MODE=%q: must be store or test", c.Mode)
	}
	v := &Verifier{mode: c.Mode, product: c.ProductID, prodHosts: c.ProductionHosts, log: log}
	if h := hostOf(c.PublicURL); h != "" && v.isProdHost(h) {
		v.prodConfig = true
	}
	if c.AppleBundleID != "" {
		a, err := NewApple(c.AppleBundleID, c.ProductID, c.AppleEnvs)
		if err != nil {
			return nil, err
		}
		v.apple = a
	}
	g, err := NewGoogleFromFile(c.GoogleSAFile, c.GooglePackage, c.ProductID)
	if err != nil {
		return nil, err
	}
	v.google = g
	switch {
	case v.mode == ModeTest && v.prodConfig:
		log.Warn("VOICE_RECEIPT_MODE=test on a production host: every voice purchase will be refused (receipt_verification_unavailable)")
	case v.mode == ModeTest:
		log.Warn("VOICE_RECEIPT_MODE=test: receipts \"test:<id>\" are accepted without a store; never use this in production")
	}
	log.Info("voice receipts", "mode", v.mode, "app_store", v.apple != nil, "play", v.google != nil)
	return v, nil
}

func hostOf(u string) string {
	u = strings.TrimSpace(u)
	if i := strings.Index(u, "://"); i >= 0 {
		u = u[i+3:]
	}
	u, _, _ = strings.Cut(u, "/")
	if h, _, err := net.SplitHostPort(u); err == nil {
		u = h
	}
	return strings.ToLower(u)
}

func (v *Verifier) isProdHost(h string) bool { return slices.Contains(v.prodHosts, hostOf(h)) }

// Available reports which stores can be verified (for the health endpoint and logs).
func (v *Verifier) Available() (appStore, play bool) { return v.apple != nil, v.google != nil }

// Verify checks a receipt of the voice_clone product. platform is "ios", "android" or "" (guess:
// a JWS is App Store, anything else a Play token). host is the request's Host header.
func (v *Verifier) Verify(ctx context.Context, platform, receipt, host string) (Purchase, error) {
	receipt = strings.TrimSpace(receipt)
	if receipt == "" {
		return Purchase{}, invalid("receipt missing")
	}
	if v.mode == ModeTest {
		if v.prodConfig || v.isProdHost(host) {
			v.log.Warn("voice receipt refused: test mode on a production host", "host", hostOf(host))
			return Purchase{}, unavailable(errors.New("test receipt mode is not allowed on a production host"))
		}
		id, ok := strings.CutPrefix(receipt, "test:")
		if !ok || id == "" || len(id) > 128 {
			return Purchase{}, invalid(`test mode expects "test:<id>"`)
		}
		return Purchase{Platform: PlatformTest, ProductID: v.product, TransactionID: id, OriginalID: id, Environment: "Test"}, nil
	}
	if platform == "" {
		platform = PlatformAndroid
		if LooksLikeJWS(receipt) {
			platform = PlatformIOS
		}
	}
	switch platform {
	case PlatformIOS:
		if v.apple == nil {
			return Purchase{}, unavailable(errors.New("App Store verification is not configured"))
		}
		return v.apple.Verify(receipt)
	case PlatformAndroid:
		if v.google == nil {
			return Purchase{}, unavailable(errors.New("Play verification is not configured"))
		}
		return v.google.Verify(ctx, receipt)
	}
	return Purchase{}, invalid("platform must be ios or android")
}
