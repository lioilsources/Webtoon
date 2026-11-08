"""Toonfork on Google Play: upload a build and set up the in-app products (after Kaceny/tool/play_store.py).

    AAB=path/to/app-release.aab python3 tools/play_store.py bundle    # internal testing track, draft release
    python3 tools/play_store.py iap                                   # tools/products.csv → one-time products, active

Uses the google-play-publisher service account from ~/Dev/Distribution/Android/_GoogleConsole/GooglePlay/ (never
printed). The app must exist in Play Console with that account allowed; products need a payments profile and an
uploaded build with the billing permission. Product ids are permanent (docs/store-products.md).
"""

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal
from pathlib import Path

import jwt

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "com.ol1n.webtoon"
SA_DIR = Path.home() / "Dev/Distribution/Android/_GoogleConsole/GooglePlay"
API = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/" + PACKAGE
UPLOAD = "https://androidpublisher.googleapis.com/upload/androidpublisher/v3/applications/" + PACKAGE
_token = None


def token():
    global _token
    if not _token:
        sa = json.loads(next(SA_DIR.glob("*.json")).read_text())
        now = int(time.time())
        assertion = jwt.encode({"iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/androidpublisher",
                                "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600},
                               sa["private_key"], algorithm="RS256")
        body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                       "assertion": assertion}).encode()
        _token = json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", body))["access_token"]
    return _token


def api(method, url, body=None, raw=None, ctype="application/json", ok=()):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": "Bearer " + token(), "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            text = r.read()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        if e.code in ok:
            return None
        raise SystemExit(f"{method} {url} -> {e.code}\n{e.read().decode()[:800]}")


class Edit:
    """A Play edit: everything inside is applied at once on commit."""

    def __enter__(self):
        self.id = api("POST", f"{API}/edits", {})["id"]
        self.base = f"{API}/edits/{self.id}"
        return self

    def __exit__(self, kind, *_):
        if kind is None:
            api("POST", f"{self.base}:commit")
            print("  committed")
        else:
            api("DELETE", self.base, ok=(404,))


def step_bundle():
    path = Path(os.environ["AAB"])
    with Edit() as edit:
        bundle = api("POST", f"{UPLOAD}/edits/{edit.id}/bundles?uploadType=media", raw=path.read_bytes(),
                     ctype="application/octet-stream")
        code = bundle["versionCode"]
        api("PUT", f"{edit.base}/tracks/internal", {"track": "internal", "releases": [
            {"versionCodes": [str(code)], "status": "draft"}]})
        print(f"  bundle versionCode {code} -> internal (draft)")


def step_iap():
    rows = list(csv.DictReader((ROOT / "tools/products.csv").open(encoding="utf-8")))
    for row in rows:
        sku = row["product_id"]
        units, frac = divmod(Decimal(row["price_usd"]), 1)
        usd = {"currencyCode": "USD", "units": str(int(units)), "nanos": int(frac * 1_000_000_000)}
        conv = api("POST", f"{API}/pricing:convertRegionPrices", {"price": usd})
        regions = [{"regionCode": code, "price": p["price"], "availability": "AVAILABLE"}
                   for code, p in sorted(conv["convertedRegionPrices"].items())]
        product = {"packageName": PACKAGE, "productId": sku,
                   "listings": [{"languageCode": "en-US", "title": row["name_en"], "description": row["description_en"]},
                                {"languageCode": "cs-CZ", "title": row["name_cs"], "description": row["description_cs"]}],
                   "purchaseOptions": [{"purchaseOptionId": "buy", "buyOption": {"legacyCompatible": True},
                                        "regionalPricingAndAvailabilityConfigs": regions}]}
        api("PATCH", f"{API}/onetimeproducts/{sku}?allowMissing=true&updateMask=listings,purchaseOptions"
                     f"&regionsVersion.version={conv['regionVersion']['version']}", product)
        api("POST", f"{API}/oneTimeProducts/{sku}/purchaseOptions:batchUpdateStates", {"requests": [
            {"activatePurchaseOptionRequest": {"packageName": PACKAGE, "productId": sku, "purchaseOptionId": "buy"}}]})
        print(f"  {sku} ${row['price_usd']}, {len(regions)} regions, active")


STEPS = {"bundle": step_bundle, "iap": step_iap}

if __name__ == "__main__":
    for name in sys.argv[1:]:
        print(name)
        STEPS[name]()
