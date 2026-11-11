package receipt

import (
	"context"
	"crypto"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Google verifies a Play purchase token of an in-app product through the Play Developer API
// (purchases.products.get) with a service account (OAuth 2.0 JWT bearer flow, no SDK).
type Google struct {
	Package     string
	ProductID   string
	ClientEmail string
	Key         *rsa.PrivateKey
	TokenURL    string // OAuth token endpoint from the service account JSON
	APIBase     string // https://androidpublisher.googleapis.com
	HTTP        *http.Client
	Now         func() time.Time

	mu     sync.Mutex
	token  string
	expiry time.Time
}

type serviceAccount struct {
	Type        string `json:"type"`
	ClientEmail string `json:"client_email"`
	PrivateKey  string `json:"private_key"`
	TokenURI    string `json:"token_uri"`
}

// NewGoogleFromFile loads a service account JSON key. A missing file is not an error: it
// returns nil, so Play receipts fail closed with ErrUnavailable.
func NewGoogleFromFile(path, pkg, productID string) (*Google, error) {
	if path == "" || pkg == "" {
		return nil, nil
	}
	b, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("play service account: %w", err)
	}
	return NewGoogle(b, pkg, productID)
}

// NewGoogle parses a service account JSON key. Errors never include key material.
func NewGoogle(saJSON []byte, pkg, productID string) (*Google, error) {
	var sa serviceAccount
	if err := json.Unmarshal(saJSON, &sa); err != nil {
		return nil, errors.New("play service account: invalid JSON")
	}
	if sa.ClientEmail == "" || sa.PrivateKey == "" {
		return nil, errors.New("play service account: client_email or private_key missing")
	}
	blk, _ := pem.Decode([]byte(sa.PrivateKey))
	if blk == nil {
		return nil, errors.New("play service account: private_key is not PEM")
	}
	k, err := x509.ParsePKCS8PrivateKey(blk.Bytes)
	if err != nil {
		return nil, errors.New("play service account: private_key is not PKCS#8")
	}
	rk, ok := k.(*rsa.PrivateKey)
	if !ok {
		return nil, errors.New("play service account: private_key is not RSA")
	}
	tu := sa.TokenURI
	if tu == "" {
		tu = "https://oauth2.googleapis.com/token"
	}
	return &Google{Package: pkg, ProductID: productID, ClientEmail: sa.ClientEmail, Key: rk, TokenURL: tu,
		APIBase: "https://androidpublisher.googleapis.com", HTTP: &http.Client{Timeout: 15 * time.Second}, Now: time.Now}, nil
}

const playScope = "https://www.googleapis.com/auth/androidpublisher"

func (g *Google) accessToken(ctx context.Context) (string, error) {
	g.mu.Lock()
	defer g.mu.Unlock()
	now := g.Now()
	if g.token != "" && now.Before(g.expiry.Add(-time.Minute)) {
		return g.token, nil
	}
	enc := base64.RawURLEncoding
	hdr := enc.EncodeToString([]byte(`{"alg":"RS256","typ":"JWT"}`))
	claims, _ := json.Marshal(map[string]any{"iss": g.ClientEmail, "scope": playScope, "aud": g.TokenURL,
		"iat": now.Unix(), "exp": now.Add(time.Hour).Unix()})
	unsigned := hdr + "." + enc.EncodeToString(claims)
	sum := sha256.Sum256([]byte(unsigned))
	sig, err := rsa.SignPKCS1v15(nil, g.Key, crypto.SHA256, sum[:])
	if err != nil {
		return "", err
	}
	form := url.Values{"grant_type": {"urn:ietf:params:oauth:grant-type:jwt-bearer"},
		"assertion": {unsigned + "." + enc.EncodeToString(sig)}}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, g.TokenURL, strings.NewReader(form.Encode()))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	resp, err := g.HTTP.Do(req)
	if err != nil {
		return "", fmt.Errorf("play oauth: %w", err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<16))
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("play oauth: HTTP %d", resp.StatusCode)
	}
	var tr struct {
		AccessToken string `json:"access_token"`
		ExpiresIn   int    `json:"expires_in"`
	}
	if err := json.Unmarshal(body, &tr); err != nil || tr.AccessToken == "" {
		return "", errors.New("play oauth: no access token")
	}
	g.token, g.expiry = tr.AccessToken, now.Add(time.Duration(tr.ExpiresIn)*time.Second)
	return g.token, nil
}

// productPurchase is the subset of the ProductPurchase resource the server checks.
type productPurchase struct {
	PurchaseState      *int   `json:"purchaseState"` // 0 purchased, 1 cancelled, 2 pending
	OrderID            string `json:"orderId"`
	PurchaseTimeMillis string `json:"purchaseTimeMillis"`
	PurchaseType       *int   `json:"purchaseType"` // 0 test (license tester), 1 promo, 2 rewarded; absent = real
	ProductID          string `json:"productId"`
}

// Verify asks Play about the purchase token. A token Play does not know (or for another product)
// is ErrInvalid; Play or the network being down is ErrUnavailable.
func (g *Google) Verify(ctx context.Context, token string) (Purchase, error) {
	token = strings.TrimSpace(token)
	if token == "" || len(token) > 4096 {
		return Purchase{}, invalid("purchase token missing")
	}
	at, err := g.accessToken(ctx)
	if err != nil {
		return Purchase{}, unavailable(err)
	}
	u := fmt.Sprintf("%s/androidpublisher/v3/applications/%s/purchases/products/%s/tokens/%s",
		strings.TrimRight(g.APIBase, "/"), url.PathEscape(g.Package), url.PathEscape(g.ProductID), url.PathEscape(token))
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
	if err != nil {
		return Purchase{}, err
	}
	req.Header.Set("Authorization", "Bearer "+at)
	resp, err := g.HTTP.Do(req)
	if err != nil {
		return Purchase{}, unavailable(fmt.Errorf("play api: %w", err))
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<16))
	switch {
	case resp.StatusCode == http.StatusOK:
	case resp.StatusCode == http.StatusBadRequest, resp.StatusCode == http.StatusNotFound, resp.StatusCode == http.StatusGone:
		return Purchase{}, invalid("Play does not know this purchase")
	default:
		// 401/403: the service account lacks access in Play Console; 5xx: Play is down.
		return Purchase{}, unavailable(fmt.Errorf("play api: HTTP %d", resp.StatusCode))
	}
	var p productPurchase
	if err := json.Unmarshal(body, &p); err != nil {
		return Purchase{}, unavailable(errors.New("play api: bad response"))
	}
	if p.PurchaseState == nil || *p.PurchaseState != 0 {
		return Purchase{}, invalid("purchase is not completed (cancelled or pending)")
	}
	if p.ProductID != "" && p.ProductID != g.ProductID {
		return Purchase{}, invalid("product id does not match")
	}
	env := "Production"
	if p.PurchaseType != nil && *p.PurchaseType == 0 {
		env = "Test"
	}
	orig := p.OrderID
	if orig == "" {
		h := sha256.Sum256([]byte(token))
		orig = "token:" + base64.RawURLEncoding.EncodeToString(h[:12])
	}
	ms, _ := strconv.ParseInt(p.PurchaseTimeMillis, 10, 64)
	return Purchase{Platform: PlatformAndroid, ProductID: g.ProductID, TransactionID: orig, OriginalID: orig,
		Environment: env, PurchasedAt: time.UnixMilli(ms).UTC()}, nil
}
