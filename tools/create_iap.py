#!/usr/bin/env python3
"""Create non-consumable in-app products from tools/products.csv in App Store Connect and Google Play.

    python3 tools/create_iap.py gamebook_archion gamebook_gulasspagety            # dry run: what would be created
    python3 tools/create_iap.py gamebook_archion gamebook_gulasspagety --apply    # create (skips existing ones)
    ... --only asc | --only play

env: APP_STORE_CONNECT_API_KEY_PATH (fastlane api_key json, key with write access),
     SUPPLY_JSON_KEY (Play service account json). The ASC/Play helpers are Store/store-ops/scripts (asc.py, play_pull.py).
ASC: NON_CONSUMABLE, Family Sharing on, cs + en-US localization, every territory, USD base price from the CSV.
The review screenshot (docs/store-products.md step 5) still has to be added by hand before submitting.
Play: managed product, en-US + cs-CZ listing, USD default price, other countries converted, active.
"""

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT.parent / "Store" / "store-ops" / "scripts"
BUNDLE = PACKAGE = "com.ol1n.webtoon"


def products(ids):
    rows = {r["product_id"]: r for r in csv.DictReader((ROOT / "tools/products.csv").open())}
    if missing := [i for i in ids if i not in rows]:
        sys.exit(f"not in tools/products.csv: {missing}")
    return [rows[i] for i in ids]


def asc_create(rows, apply):
    sys.path.insert(0, str(STORE))
    import asc

    app = asc.app_id(BUNDLE)
    existing, url = set(), f"/v1/apps/{app}/inAppPurchasesV2?limit=200"
    while url:
        r = asc.call(url)
        existing |= {x["attributes"]["productId"] for x in r["data"]}
        url = r.get("links", {}).get("next")
    for p in rows:
        pid = p["product_id"]
        if pid in existing:
            print(f"asc {pid}: exists, skipped")
            continue
        print(f"asc {pid}: create NON_CONSUMABLE {p['price_usd']} USD, cs '{p['name_cs']}', en '{p['name_en']}'")
        if not apply:
            continue
        iap = asc.call("/v2/inAppPurchases", "POST", {"data": {
            "type": "inAppPurchases",
            "attributes": {"name": pid, "productId": pid, "inAppPurchaseType": "NON_CONSUMABLE", "familySharable": True},
            "relationships": {"app": {"data": {"type": "apps", "id": app}}}}})["data"]["id"]
        for locale, name, desc in (("cs", p["name_cs"], p["description_cs"]), ("en-US", p["name_en"], p["description_en"])):
            asc.call("/v1/inAppPurchaseLocalizations", "POST", {"data": {
                "type": "inAppPurchaseLocalizations", "attributes": {"locale": locale, "name": name, "description": desc},
                "relationships": {"inAppPurchaseV2": {"data": {"type": "inAppPurchases", "id": iap}}}}})
        terr, url = [], "/v1/territories?limit=200"
        while url:
            r = asc.call(url)
            terr += [{"type": "territories", "id": t["id"]} for t in r["data"]]
            url = r.get("links", {}).get("next")
        asc.call("/v1/inAppPurchaseAvailabilities", "POST", {"data": {
            "type": "inAppPurchaseAvailabilities", "attributes": {"availableInNewTerritories": True},
            "relationships": {"inAppPurchase": {"data": {"type": "inAppPurchases", "id": iap}},
                              "availableTerritories": {"data": terr}}}})
        point, url = None, f"/v2/inAppPurchases/{iap}/pricePoints?filter[territory]=USA&limit=200"
        while url and not point:
            r = asc.call(url)
            point = next((x["id"] for x in r["data"] if x["attributes"]["customerPrice"] == p["price_usd"]), None)
            url = r.get("links", {}).get("next")
        if not point:
            sys.exit(f"asc {pid}: no USA price point {p['price_usd']}")
        asc.call("/v1/inAppPurchasePriceSchedules", "POST", {
            "data": {"type": "inAppPurchasePriceSchedules", "relationships": {
                "inAppPurchase": {"data": {"type": "inAppPurchases", "id": iap}},
                "baseTerritory": {"data": {"type": "territories", "id": "USA"}},
                "manualPrices": {"data": [{"type": "inAppPurchasePrices", "id": "${p0}"}]}}},
            "included": [{"type": "inAppPurchasePrices", "id": "${p0}", "attributes": {"startDate": None},
                          "relationships": {"inAppPurchasePricePoint": {"data": {"type": "inAppPurchasePricePoints", "id": point}}}}]})
        print(f"asc {pid}: created ({iap}); add the review screenshot before submitting")


def play_create(rows, apply):
    sys.path.insert(0, str(STORE))
    from play_pull import token

    tok = token(os.environ["SUPPLY_JSON_KEY"])
    base = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE}/inappproducts"

    def call(url, method="GET", body=None):
        req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None,
                                     {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}, method=method)
        try:
            return json.load(urllib.request.urlopen(req))
        except urllib.error.HTTPError as e:
            if e.code == 404 and method == "GET":
                return None
            raise SystemExit(f"play {method} {url}: {e.code} {e.read().decode()[:600]}")

    for p in rows:
        pid = p["product_id"]
        if call(f"{base}/{pid}"):
            print(f"play {pid}: exists, skipped")
            continue
        print(f"play {pid}: create managed {p['price_usd']} USD, cs '{p['name_cs']}', en '{p['name_en']}'")
        if not apply:
            continue
        call(f"{base}?autoConvertMissingPrices=true", "POST", {
            "packageName": PACKAGE, "sku": pid, "status": "active", "purchaseType": "managedUser",
            "defaultLanguage": "en-US",
            "defaultPrice": {"priceMicros": str(round(float(p["price_usd"]) * 1_000_000)), "currency": "USD"},
            "listings": {"en-US": {"title": p["name_en"], "description": p["description_en"]},
                         "cs-CZ": {"title": p["name_cs"], "description": p["description_cs"]}}})
        print(f"play {pid}: created and active")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", choices=["asc", "play"])
    args = ap.parse_args()
    rows = products(args.ids)
    if args.only != "play":
        asc_create(rows, args.apply)
    if args.only != "asc":
        play_create(rows, args.apply)


if __name__ == "__main__":
    main()
