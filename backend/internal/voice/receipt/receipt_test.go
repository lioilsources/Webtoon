package receipt

import (
	"context"
	"crypto"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"errors"
	"io"
	"log/slog"
	"math/big"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

var now = time.Date(2026, 11, 11, 10, 0, 0, 0, time.UTC)

// testChain is a generated stand-in for Apple's StoreKit chain: root → intermediate (Apple
// intermediate marker) → leaf (Apple leaf marker). No real Apple keys are involved.
type testChain struct {
	root              *x509.Certificate
	inter, leaf       *x509.Certificate
	leafKey           *ecdsa.PrivateKey
	rootDER, interDER []byte
	leafDER           []byte
}

func cert(t *testing.T, tmpl, parent *x509.Certificate, pub any, signer any) ([]byte, *x509.Certificate) {
	t.Helper()
	der, err := x509.CreateCertificate(rand.Reader, tmpl, parent, pub, signer)
	if err != nil {
		t.Fatal(err)
	}
	c, err := x509.ParseCertificate(der)
	if err != nil {
		t.Fatal(err)
	}
	return der, c
}

func newChain(t *testing.T, markers bool) *testChain {
	t.Helper()
	key := func() *ecdsa.PrivateKey {
		k, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
		if err != nil {
			t.Fatal(err)
		}
		return k
	}
	rk, ik, lk := key(), key(), key()
	nb, na := now.Add(-24*time.Hour), now.Add(365*24*time.Hour)
	rootT := &x509.Certificate{SerialNumber: big.NewInt(1), Subject: pkix.Name{CommonName: "Test Root"}, NotBefore: nb, NotAfter: na,
		IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign}
	c := &testChain{leafKey: lk}
	c.rootDER, c.root = cert(t, rootT, rootT, &rk.PublicKey, rk)
	interT := &x509.Certificate{SerialNumber: big.NewInt(2), Subject: pkix.Name{CommonName: "Test WWDR"}, NotBefore: nb, NotAfter: na,
		IsCA: true, BasicConstraintsValid: true, KeyUsage: x509.KeyUsageCertSign}
	leafT := &x509.Certificate{SerialNumber: big.NewInt(3), Subject: pkix.Name{CommonName: "Test StoreKit"}, NotBefore: nb, NotAfter: na,
		KeyUsage: x509.KeyUsageDigitalSignature}
	if markers {
		interT.ExtraExtensions = []pkix.Extension{{Id: oidAppleIntermediate, Value: []byte{5, 0}}}
		leafT.ExtraExtensions = []pkix.Extension{{Id: oidAppleLeaf, Value: []byte{5, 0}}}
	}
	c.interDER, c.inter = cert(t, interT, c.root, &ik.PublicKey, rk)
	c.leafDER, c.leaf = cert(t, leafT, c.inter, &lk.PublicKey, ik)
	return c
}

func (c *testChain) pool() *x509.CertPool {
	p := x509.NewCertPool()
	p.AddCert(c.root)
	return p
}

func (c *testChain) sign(t *testing.T, claims map[string]any) string {
	t.Helper()
	enc := base64.RawURLEncoding
	std := base64.StdEncoding
	h, _ := json.Marshal(map[string]any{"alg": "ES256", "x5c": []string{std.EncodeToString(c.leafDER), std.EncodeToString(c.interDER), std.EncodeToString(c.rootDER)}})
	p, _ := json.Marshal(claims)
	unsigned := enc.EncodeToString(h) + "." + enc.EncodeToString(p)
	sum := sha256.Sum256([]byte(unsigned))
	r, s, err := ecdsa.Sign(rand.Reader, c.leafKey, sum[:])
	if err != nil {
		t.Fatal(err)
	}
	sig := make([]byte, 64)
	r.FillBytes(sig[:32])
	s.FillBytes(sig[32:])
	return unsigned + "." + enc.EncodeToString(sig)
}

func tx(over map[string]any) map[string]any {
	m := map[string]any{"bundleId": "com.example.toonfork", "productId": "voice_clone", "transactionId": "2000000123",
		"originalTransactionId": "2000000100", "environment": "Production", "purchaseDate": now.UnixMilli(), "type": "Non-Consumable"}
	for k, v := range over {
		if v == nil {
			delete(m, k)
		} else {
			m[k] = v
		}
	}
	return m
}

func testApple(c *testChain) *Apple {
	return &Apple{BundleID: "com.example.toonfork", ProductID: "voice_clone", Environments: []string{"Production", "Sandbox"},
		Roots: c.pool(), Now: func() time.Time { return now }}
}

func TestAppleVerify(t *testing.T) {
	c := newChain(t, true)
	a := testApple(c)
	p, err := a.Verify(c.sign(t, tx(nil)))
	if err != nil {
		t.Fatal(err)
	}
	if p.Platform != PlatformIOS || p.TransactionID != "2000000123" || p.OriginalID != "2000000100" || p.Environment != "Production" {
		t.Fatalf("%+v", p)
	}
	if _, err := a.Verify(c.sign(t, tx(map[string]any{"environment": "Sandbox"}))); err != nil {
		t.Fatal("sandbox (TestFlight, App Review) is accepted by default:", err)
	}
	for name, claims := range map[string]map[string]any{
		"bundle":      tx(map[string]any{"bundleId": "com.other.app"}),
		"product":     tx(map[string]any{"productId": "pack_kids_1"}),
		"revoked":     tx(map[string]any{"revocationDate": now.UnixMilli(), "revocationReason": 0}),
		"environment": tx(map[string]any{"environment": "Xcode"}),
		"no tx":       tx(map[string]any{"transactionId": nil}),
	} {
		if _, err := a.Verify(c.sign(t, claims)); !errors.Is(err, ErrInvalid) {
			t.Errorf("%s: %v", name, err)
		}
	}
}

func TestAppleRejectsForgeries(t *testing.T) {
	c := newChain(t, true)
	a := testApple(c)
	good := c.sign(t, tx(nil))
	parts := strings.Split(good, ".")

	// payload swapped after signing
	evil, _ := json.Marshal(tx(map[string]any{"productId": "voice_clone", "transactionId": "999"}))
	tampered := parts[0] + "." + base64.RawURLEncoding.EncodeToString(evil) + "." + parts[2]
	// a chain from another root (self-made "Apple" chain)
	other := newChain(t, true)
	foreign := other.sign(t, tx(nil))
	// right root, but the certificates lack Apple's marker extensions
	plain := newChain(t, false)
	ap := testApple(plain)
	// expired leaf
	late := testApple(c)
	late.Now = func() time.Time { return now.Add(2 * 365 * 24 * time.Hour) }

	cases := map[string]func() error{
		"tampered": func() error { _, err := a.Verify(tampered); return err },
		"foreign":  func() error { _, err := a.Verify(foreign); return err },
		"markers":  func() error { _, err := ap.Verify(plain.sign(t, tx(nil))); return err },
		"expired":  func() error { _, err := late.Verify(good); return err },
		"not jws":  func() error { _, err := a.Verify("MIIT8gYJKoZIhvcNAQcCoIIT4zCCE98CAQEx"); return err },
		"bad sig": func() error {
			_, err := a.Verify(parts[0] + "." + parts[1] + "." + base64.RawURLEncoding.EncodeToString(make([]byte, 64)))
			return err
		},
		"alg none": func() error {
			_, err := a.Verify(base64.RawURLEncoding.EncodeToString([]byte(`{"alg":"none","x5c":["a","b"]}`)) + "." + parts[1] + ".")
			return err
		},
		"no chain": func() error {
			_, err := a.Verify(base64.RawURLEncoding.EncodeToString([]byte(`{"alg":"ES256"}`)) + "." + parts[1] + "." + parts[2])
			return err
		},
	}
	for name, f := range cases {
		if err := f(); !errors.Is(err, ErrInvalid) {
			t.Errorf("%s: %v", name, err)
		}
	}
}

func TestPinnedAppleRoot(t *testing.T) {
	a, err := NewApple("b", "voice_clone", nil)
	if err != nil {
		t.Fatal(err)
	}
	blk, _ := pem.Decode([]byte(AppleRootCAG3))
	sum := sha256.Sum256(blk.Bytes)
	if got := strings.ToUpper(hex.EncodeToString(sum[:])); got != "63343ABFB89A6A03EBB57E9B3F5FA7BE7C4F5C756F3017B3A8C488C3653E9179" {
		t.Fatalf("Apple Root CA - G3 fingerprint %s", got)
	}
	// a chain from a generated root does not verify against the real Apple root
	c := newChain(t, true)
	a.Now = func() time.Time { return now }
	if _, err := a.Verify(c.sign(t, tx(map[string]any{"bundleId": "b"}))); !errors.Is(err, ErrInvalid) {
		t.Fatal(err)
	}
}

// --- Google Play -------------------------------------------------------------------------

type fakePlay struct {
	*httptest.Server
	key      *rsa.PrivateKey
	purchase map[string]any
	status   int
	tokens   int
}

func newFakePlay(t *testing.T) (*fakePlay, []byte) {
	t.Helper()
	k, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	f := &fakePlay{key: k, status: 200, purchase: map[string]any{"purchaseState": 0, "orderId": "GPA.1234-5678", "purchaseTimeMillis": "1762855200000", "productId": "voice_clone"}}
	f.Server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.URL.Path == "/token":
			r.ParseForm() //nolint:errcheck
			parts := strings.Split(r.Form.Get("assertion"), ".")
			sig, _ := base64.RawURLEncoding.DecodeString(parts[2])
			sum := sha256.Sum256([]byte(parts[0] + "." + parts[1]))
			if r.Form.Get("grant_type") != "urn:ietf:params:oauth:grant-type:jwt-bearer" ||
				rsa.VerifyPKCS1v15(&f.key.PublicKey, crypto.SHA256, sum[:], sig) != nil {
				http.Error(w, "bad assertion", 400)
				return
			}
			cb, _ := base64.RawURLEncoding.DecodeString(parts[1])
			var cl map[string]any
			json.Unmarshal(cb, &cl) //nolint:errcheck
			if cl["scope"] != playScope || cl["iss"] != "test-service-account" {
				http.Error(w, "bad claims", 400)
				return
			}
			f.tokens++
			json.NewEncoder(w).Encode(map[string]any{"access_token": "at-1", "expires_in": 3600}) //nolint:errcheck
		case strings.HasPrefix(r.URL.Path, "/androidpublisher/v3/applications/com.example.toonfork/purchases/products/voice_clone/tokens/"):
			if r.Header.Get("Authorization") != "Bearer at-1" {
				http.Error(w, "unauthorized", 401)
				return
			}
			if f.status != 200 {
				http.Error(w, "x", f.status)
				return
			}
			json.NewEncoder(w).Encode(f.purchase) //nolint:errcheck
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(f.Close)
	pk, _ := x509.MarshalPKCS8PrivateKey(k)
	sa, _ := json.Marshal(map[string]string{"type": "service_account", "client_email": "test-service-account",
		"private_key": string(pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: pk})), "token_uri": f.URL + "/token"})
	return f, sa
}

func TestGoogleVerify(t *testing.T) {
	f, sa := newFakePlay(t)
	g, err := NewGoogle(sa, "com.example.toonfork", "voice_clone")
	if err != nil {
		t.Fatal(err)
	}
	g.APIBase, g.Now = f.URL, func() time.Time { return now }
	p, err := g.Verify(context.Background(), "purchase-token-abc")
	if err != nil {
		t.Fatal(err)
	}
	if p.Platform != PlatformAndroid || p.OriginalID != "GPA.1234-5678" || p.Environment != "Production" {
		t.Fatalf("%+v", p)
	}
	if _, err := g.Verify(context.Background(), "purchase-token-abc"); err != nil || f.tokens != 1 {
		t.Fatalf("access token is cached: %v %d", err, f.tokens)
	}
	f.purchase["purchaseState"] = 1
	if _, err := g.Verify(context.Background(), "t"); !errors.Is(err, ErrInvalid) {
		t.Fatal("cancelled purchase:", err)
	}
	f.purchase["purchaseState"] = 2
	if _, err := g.Verify(context.Background(), "t"); !errors.Is(err, ErrInvalid) {
		t.Fatal("pending purchase:", err)
	}
	f.status = 404
	if _, err := g.Verify(context.Background(), "t"); !errors.Is(err, ErrInvalid) {
		t.Fatal("unknown token:", err)
	}
	f.status = 503
	if _, err := g.Verify(context.Background(), "t"); !errors.Is(err, ErrUnavailable) {
		t.Fatal("Play down fails closed:", err)
	}
	f.status = 403
	if _, err := g.Verify(context.Background(), "t"); !errors.Is(err, ErrUnavailable) {
		t.Fatal("no Play Console access fails closed:", err)
	}
}

func TestGoogleFromFile(t *testing.T) {
	if g, err := NewGoogleFromFile(filepath.Join(t.TempDir(), "missing.json"), "p", "voice_clone"); g != nil || err != nil {
		t.Fatal("missing file = Play unavailable, not an error")
	}
	bad := filepath.Join(t.TempDir(), "sa.json")
	os.WriteFile(bad, []byte(`{"client_email":"x","private_key":"SECRET-MATERIAL"}`), 0o600) //nolint:errcheck
	if _, err := NewGoogleFromFile(bad, "p", "voice_clone"); err == nil || strings.Contains(err.Error(), "SECRET") {
		t.Fatalf("bad key is an error without key material: %v", err)
	}
}

// --- Verifier ----------------------------------------------------------------------------

func quiet() *slog.Logger { return slog.New(slog.NewTextHandler(io.Discard, nil)) }

func TestVerifierFailsClosedWithoutCredentials(t *testing.T) {
	v, err := New(Config{}, quiet())
	if err != nil {
		t.Fatal(err)
	}
	c := newChain(t, true)
	for _, r := range []struct{ plat, rcpt string }{
		{"", c.sign(t, tx(nil))}, {"ios", "x.y.z"}, {"android", "token"}, {"", "token"}, {"", "test:abc"},
	} {
		if _, err := v.Verify(context.Background(), r.plat, r.rcpt, "api.local"); !errors.Is(err, ErrUnavailable) {
			t.Errorf("%q %.10q: %v", r.plat, r.rcpt, err)
		}
	}
	if _, err := v.Verify(context.Background(), "", "", "api.local"); !errors.Is(err, ErrInvalid) {
		t.Fatal("empty receipt:", err)
	}
	if _, err := New(Config{Mode: "off"}, quiet()); err == nil {
		t.Fatal("unknown mode")
	}
}

func TestVerifierDispatch(t *testing.T) {
	f, sa := newFakePlay(t)
	saFile := filepath.Join(t.TempDir(), "sa.json")
	os.WriteFile(saFile, sa, 0o600) //nolint:errcheck
	v, err := New(Config{AppleBundleID: "com.example.toonfork", GooglePackage: "com.example.toonfork", GoogleSAFile: saFile}, quiet())
	if err != nil {
		t.Fatal(err)
	}
	c := newChain(t, true)
	v.apple.Roots, v.apple.Now = c.pool(), func() time.Time { return now }
	v.google.APIBase = f.URL
	if p, err := v.Verify(context.Background(), "", c.sign(t, tx(nil)), "api"); err != nil || p.Platform != PlatformIOS {
		t.Fatal(p, err)
	}
	if p, err := v.Verify(context.Background(), "", "play-token", "api"); err != nil || p.Platform != PlatformAndroid {
		t.Fatal(p, err)
	}
	if _, err := v.Verify(context.Background(), "web", "x", "api"); !errors.Is(err, ErrInvalid) {
		t.Fatal(err)
	}
}

func TestTestMode(t *testing.T) {
	v, err := New(Config{Mode: ModeTest}, quiet())
	if err != nil {
		t.Fatal(err)
	}
	p, err := v.Verify(context.Background(), "", "test:order-1", "localhost:8095")
	if err != nil || p.Platform != PlatformTest || p.OriginalID != "order-1" {
		t.Fatal(p, err)
	}
	if _, err := v.Verify(context.Background(), "", "order-1", "localhost"); !errors.Is(err, ErrInvalid) {
		t.Fatal(err)
	}
	for _, host := range []string{"webtoon-api.ol1n.com", "WEBTOON-API.ol1n.com:443"} {
		if _, err := v.Verify(context.Background(), "", "test:order-1", host); !errors.Is(err, ErrUnavailable) {
			t.Fatalf("%s: test mode must be refused on the production host: %v", host, err)
		}
	}
	vp, _ := New(Config{Mode: ModeTest, PublicURL: "https://webtoon-api.ol1n.com/"}, quiet())
	if _, err := vp.Verify(context.Background(), "", "test:order-1", "localhost"); !errors.Is(err, ErrUnavailable) {
		t.Fatal("production VOICE_PUBLIC_URL refuses test mode for every request:", err)
	}
	vc, _ := New(Config{Mode: ModeTest, ProductionHosts: []string{"api.example.test"}}, quiet())
	if _, err := vc.Verify(context.Background(), "", "test:x", "api.example.test"); !errors.Is(err, ErrUnavailable) {
		t.Fatal(err)
	}
}
