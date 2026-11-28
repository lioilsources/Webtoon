#!/usr/bin/env python3
"""Small App Store Connect API client (JWT ES256), a copy of Store/store-ops/scripts/asc.py. Module or: asc.py versions <bundle>
env: APP_STORE_CONNECT_API_KEY_PATH (fastlane api_key json)"""
import base64, json, os, subprocess, sys, tempfile, time, urllib.request, urllib.error

def _jwt():
    k = json.load(open(os.environ["APP_STORE_CONNECT_API_KEY_PATH"]))
    b = lambda x: base64.urlsafe_b64encode(x).rstrip(b"=")
    h = b(json.dumps({"alg": "ES256", "kid": k["key_id"], "typ": "JWT"}).encode())
    now = int(time.time())
    c = b(json.dumps({"iss": k["issuer_id"], "iat": now, "exp": now + 1100, "aud": "appstoreconnect-v1"}).encode())
    with tempfile.NamedTemporaryFile("w", delete=False) as f: f.write(k["key"])
    der = subprocess.run(["openssl", "dgst", "-sha256", "-sign", f.name], input=h + b"." + c, capture_output=True, check=True).stdout
    os.unlink(f.name)
    # DER -> raw r||s
    i = 4 if der[1] < 0x80 else 5
    rl = der[i - 1]; r = der[i:i + rl]; sl = der[i + rl + 1]; s = der[i + rl + 2:i + rl + 2 + sl]
    raw = r[-32:].rjust(32, b"\0") + s[-32:].rjust(32, b"\0")
    return (h + b"." + c + b"." + b(raw)).decode()

_tok = None
def call(path, method="GET", body=None):
    global _tok
    _tok = _tok or _jwt()
    url = path if path.startswith("http") else "https://api.appstoreconnect.apple.com" + path
    req = urllib.request.Request(url, json.dumps(body).encode() if body else None,
                                 {"Authorization": "Bearer " + _tok, "Content-Type": "application/json"}, method=method)
    try:
        r = urllib.request.urlopen(req).read()
        return json.loads(r) if r else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path}: {e.code} {e.read().decode()[:600]}")

def app_id(bundle):
    return call(f"/v1/apps?filter[bundleId]={bundle}")["data"][0]["id"]

if __name__ == "__main__" and sys.argv[1] == "versions":
    for b in sys.argv[2:]:
        a = app_id(b)
        vs = call(f"/v1/apps/{a}/appStoreVersions?limit=3")["data"]
        print(b, a, [(v["attributes"]["versionString"], v["attributes"]["appStoreState"]) for v in vs])
