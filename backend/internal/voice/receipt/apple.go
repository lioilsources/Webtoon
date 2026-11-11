package receipt

import (
	"crypto/ecdsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/asn1"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"math/big"
	"slices"
	"strings"
	"time"
)

// AppleRootCAG3 is Apple Root CA - G3 (https://www.apple.com/certificateauthority/AppleRootCA-G3.cer),
// SHA-256 fingerprint 63:34:3A:BF:B8:9A:6A:03:EB:B5:7E:9B:3F:5F:A7:BE:7C:4F:5C:75:6F:30:17:B3:A8:C4:88:C3:65:3E:91:79.
// StoreKit 2 signs transactions with a chain that ends in it.
const AppleRootCAG3 = `-----BEGIN CERTIFICATE-----
MIICQzCCAcmgAwIBAgIILcX8iNLFS5UwCgYIKoZIzj0EAwMwZzEbMBkGA1UEAwwS
QXBwbGUgUm9vdCBDQSAtIEczMSYwJAYDVQQLDB1BcHBsZSBDZXJ0aWZpY2F0aW9u
IEF1dGhvcml0eTETMBEGA1UECgwKQXBwbGUgSW5jLjELMAkGA1UEBhMCVVMwHhcN
MTQwNDMwMTgxOTA2WhcNMzkwNDMwMTgxOTA2WjBnMRswGQYDVQQDDBJBcHBsZSBS
b290IENBIC0gRzMxJjAkBgNVBAsMHUFwcGxlIENlcnRpZmljYXRpb24gQXV0aG9y
aXR5MRMwEQYDVQQKDApBcHBsZSBJbmMuMQswCQYDVQQGEwJVUzB2MBAGByqGSM49
AgEGBSuBBAAiA2IABJjpLz1AcqTtkyJygRMc3RCV8cWjTnHcFBbZDuWmBSp3ZHtf
TjjTuxxEtX/1H7YyYl3J6YRbTzBPEVoA/VhYDKX1DyxNB0cTddqXl5dvMVztK517
IDvYuVTZXpmkOlEKMaNCMEAwHQYDVR0OBBYEFLuw3qFYM4iapIqZ3r6966/ayySr
MA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgEGMAoGCCqGSM49BAMDA2gA
MGUCMQCD6cHEFl4aXTQY2e3v9GwOAEZLuN+yRhHFD/3meoyhpmvOwgPUnPWTxnS4
at+qIxUCMG1mihDK1A3UT82NQz60imOlM27jbdoXt2QfyFMm+YhidDkLF1vLUagM
6BgD56KyKA==
-----END CERTIFICATE-----
`

// Marker extensions of Apple's StoreKit signing chain (same checks as Apple's App Store Server Library).
var (
	oidAppleLeaf         = asn1.ObjectIdentifier{1, 2, 840, 113635, 100, 6, 11, 1}
	oidAppleIntermediate = asn1.ObjectIdentifier{1, 2, 840, 113635, 100, 6, 2, 1}
)

// Apple verifies StoreKit 2 signed transactions (JWS) offline.
type Apple struct {
	BundleID     string
	ProductID    string
	Environments []string // accepted "environment" values, e.g. Production, Sandbox
	Roots        *x509.CertPool
	Now          func() time.Time
}

// NewApple returns a verifier pinned to Apple Root CA - G3.
func NewApple(bundleID, productID string, envs []string) (*Apple, error) {
	pool := x509.NewCertPool()
	blk, _ := pem.Decode([]byte(AppleRootCAG3))
	if blk == nil {
		return nil, errors.New("apple root: bad PEM")
	}
	root, err := x509.ParseCertificate(blk.Bytes)
	if err != nil {
		return nil, err
	}
	pool.AddCert(root)
	return &Apple{BundleID: bundleID, ProductID: productID, Environments: envs, Roots: pool, Now: time.Now}, nil
}

type jwsHeader struct {
	Alg string   `json:"alg"`
	X5C []string `json:"x5c"`
}

// appleTransaction is the subset of JWSTransactionDecodedPayload the server checks.
type appleTransaction struct {
	BundleID              string `json:"bundleId"`
	ProductID             string `json:"productId"`
	TransactionID         string `json:"transactionId"`
	OriginalTransactionID string `json:"originalTransactionId"`
	Environment           string `json:"environment"`
	PurchaseDate          int64  `json:"purchaseDate"`
	RevocationDate        int64  `json:"revocationDate"`
	RevocationReason      *int   `json:"revocationReason"`
	SignedDate            int64  `json:"signedDate"`
}

// Verify checks the JWS signature, the certificate chain up to the pinned root, the bundle id,
// the product id, the environment and that the transaction was not revoked (refunded).
func (a *Apple) Verify(jws string) (Purchase, error) {
	parts := strings.Split(strings.TrimSpace(jws), ".")
	if len(parts) != 3 {
		return Purchase{}, invalid("App Store receipt must be a StoreKit 2 signed transaction (JWS)")
	}
	hb, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return Purchase{}, invalid("JWS header encoding")
	}
	var h jwsHeader
	if err := json.Unmarshal(hb, &h); err != nil {
		return Purchase{}, invalid("JWS header")
	}
	if h.Alg != "ES256" {
		return Purchase{}, invalid("JWS alg must be ES256")
	}
	if len(h.X5C) < 2 {
		return Purchase{}, invalid("JWS x5c chain missing")
	}
	certs := make([]*x509.Certificate, len(h.X5C))
	for i, c := range h.X5C {
		der, err := base64.StdEncoding.DecodeString(c)
		if err != nil {
			return Purchase{}, invalid("x5c encoding")
		}
		if certs[i], err = x509.ParseCertificate(der); err != nil {
			return Purchase{}, invalid("x5c certificate")
		}
	}
	inter := x509.NewCertPool()
	for _, c := range certs[1:] {
		inter.AddCert(c)
	}
	chains, err := certs[0].Verify(x509.VerifyOptions{Roots: a.Roots, Intermediates: inter,
		CurrentTime: a.Now(), KeyUsages: []x509.ExtKeyUsage{x509.ExtKeyUsageAny}})
	if err != nil {
		return Purchase{}, invalid("certificate chain: " + err.Error())
	}
	ok := false
	for _, ch := range chains {
		if len(ch) >= 3 && hasExt(ch[0], oidAppleLeaf) && hasExt(ch[1], oidAppleIntermediate) {
			ok = true
			break
		}
	}
	if !ok {
		return Purchase{}, invalid("certificate chain is not Apple's StoreKit signing chain")
	}
	pub, isEC := certs[0].PublicKey.(*ecdsa.PublicKey)
	if !isEC {
		return Purchase{}, invalid("leaf key is not ECDSA")
	}
	sig, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil || len(sig) != 64 {
		return Purchase{}, invalid("JWS signature encoding")
	}
	digest := sha256.Sum256([]byte(parts[0] + "." + parts[1]))
	if !ecdsa.Verify(pub, digest[:], new(big.Int).SetBytes(sig[:32]), new(big.Int).SetBytes(sig[32:])) {
		return Purchase{}, invalid("JWS signature")
	}
	pb, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return Purchase{}, invalid("JWS payload encoding")
	}
	var t appleTransaction
	if err := json.Unmarshal(pb, &t); err != nil {
		return Purchase{}, invalid("JWS payload")
	}
	switch {
	case t.BundleID != a.BundleID:
		return Purchase{}, invalid("bundle id does not match")
	case t.ProductID != a.ProductID:
		return Purchase{}, invalid("product id does not match")
	case t.RevocationDate != 0 || t.RevocationReason != nil:
		return Purchase{}, invalid("transaction was revoked")
	case t.TransactionID == "":
		return Purchase{}, invalid("transaction id missing")
	case len(a.Environments) > 0 && !slices.Contains(a.Environments, t.Environment):
		return Purchase{}, invalid(fmt.Sprintf("environment %q not accepted", t.Environment))
	}
	orig := t.OriginalTransactionID
	if orig == "" {
		orig = t.TransactionID
	}
	return Purchase{Platform: PlatformIOS, ProductID: t.ProductID, TransactionID: t.TransactionID,
		OriginalID: orig, Environment: t.Environment, PurchasedAt: time.UnixMilli(t.PurchaseDate).UTC()}, nil
}

func hasExt(c *x509.Certificate, oid asn1.ObjectIdentifier) bool {
	for _, e := range c.Extensions {
		if e.Id.Equal(oid) {
			return true
		}
	}
	return false
}

// LooksLikeJWS reports whether s has the shape of a compact JWS with an x5c header.
func LooksLikeJWS(s string) bool {
	parts := strings.Split(strings.TrimSpace(s), ".")
	if len(parts) != 3 {
		return false
	}
	hb, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return false
	}
	var h jwsHeader
	return json.Unmarshal(hb, &h) == nil && len(h.X5C) > 0
}
