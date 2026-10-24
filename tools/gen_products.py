#!/usr/bin/env python3
"""Store products from rules/base/pack.yaml → tools/products.csv + the product table of docs/store-products.md.

    python3 tools/gen_products.py                                  # pack 1 of every active type
    python3 tools/gen_products.py --packs kids=2,harlequin=3,superhero=1 --gamebook "drak:Drakova hora:Dragon Mountain"

Names and descriptions fit App Store Connect (display name ≤ 30, description ≤ 45 characters); Play allows more.
Prices are the pack.yaml price_tiers hints (the stores convert them to local prices). Only rows that exist (or are
about to) go into the CSV; gamebooks only with --gamebook (the gamebook reader is a later phase).
"""
import argparse
import csv
import io
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "rules" / "base" / "pack.yaml"
CSV = ROOT / "tools" / "products.csv"
DOC = ROOT / "docs" / "store-products.md"
BEGIN, END = "<!-- products:begin (tools/gen_products.py) -->", "<!-- products:end -->"
COLUMNS = ["product_id", "type", "kind", "price_usd", "tier", "name_cs", "name_en", "description_cs", "description_en"]


def fill(tmpl, **kw):
    return re.sub(r"\{(\w+)\}", lambda m: str(kw[m.group(1)]), tmpl)


def rows(rules, packs, gamebooks):
    types = {t["id"]: t for t in rules["types"]}
    tier = rules["price_tiers"]
    size = rules["pack_size"]
    out = []

    def row(pid, typ, kind, tier_key, name_cs, name_en, desc_cs, desc_en):
        t = tier[tier_key]
        r = dict(product_id=pid, type=typ, kind=kind, price_usd=f"{t['usd']:.2f}", tier=t["tier"],
                 name_cs=name_cs, name_en=name_en, description_cs=desc_cs, description_en=desc_en)
        for k, limit in (("name_cs", 30), ("name_en", 30), ("description_cs", 45), ("description_en", 45)):
            assert len(r[k]) <= limit, f"{pid} {k} over {limit} characters (App Store Connect): {r[k]!r}"
        out.append(r)

    for typ, count in packs.items():
        t = types[typ]
        for n in range(1, count + 1):
            row(fill(rules["naming"]["product_id"], type=typ, n=n), typ, "pack", "pack",
                f"{t['title_i18n']['cs']} {n}", f"{t['title_i18n']['en']} {n}",
                f"{size} komiksových příběhů, 12 jazyků", f"{size} comic stories in 12 languages")
    for b in rules["bundles"]:
        if b["covers"] == "all":
            typ, dcs, den = "all", "Všechny balíčky všech typů, i budoucí", "Every pack of every type, future too"
        else:
            covered = b["covers"]["types"]
            typ = ",".join(covered)
            names_cs = ", ".join(types[c]["title_i18n"]["cs"] for c in covered)
            names_en = ", ".join(types[c]["title_i18n"]["en"] for c in covered)
            dcs, den = f"Všechny balíčky {names_cs}, i budoucí", f"All {names_en} packs, future ones too"
        row(b["product_id"], typ, "bundle", b["price_tier"], b["title_i18n"]["cs"], b["title_i18n"]["en"], dcs, den)
    for gid, cs, en in gamebooks:
        row(fill(rules["naming"]["gamebook_product"], id=gid), "gamebook", "gamebook", "gamebook",
            f"Gamebook: {cs}"[:30], f"Gamebook: {en}"[:30], "Interaktivní příběh s volbami", "Interactive branching story")
        row(fill(rules["naming"]["kit_product"], id=gid), "gamebook", "kit", "kit",
            f"{cs} + editor"[:30], f"{en} + editor kit"[:30], "Gamebook a sada pro vlastní úpravy", "The gamebook plus its editor kit")
    return out


def table(rs):
    lines = ["| product id | kind | type | USD | tier | name cs | name en | description cs | description en |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rs:
        lines.append(f"| `{r['product_id']}` | {r['kind']} | {r['type']} | {r['price_usd']} | Tier {r['tier']} | "
                     f"{r['name_cs']} | {r['name_en']} | {r['description_cs']} | {r['description_en']} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--packs", default="", help="type=count,… (default: 1 per active type)")
    ap.add_argument("--gamebook", action="append", default=[], help="id:czech title:english title")
    ap.add_argument("--check", action="store_true", help="fail when products.csv / the doc table are out of date")
    args = ap.parse_args()
    rules = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    packs = {t["id"]: 1 for t in rules["types"] if t["active"]}
    if args.packs:
        packs = {k: int(v) for k, v in (p.split("=") for p in args.packs.split(","))}
    gamebooks = [tuple(g.split(":", 2)) for g in args.gamebook]
    rs = rows(rules, packs, gamebooks)
    buf = io.StringIO()
    w = csv.DictWriter(buf, COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rs)
    doc = DOC.read_text(encoding="utf-8")
    i, j = doc.index(BEGIN) + len(BEGIN), doc.index(END)
    new_doc = doc[:i] + "\n" + table(rs) + "\n" + doc[j:]
    if args.check:
        ok = CSV.read_text(encoding="utf-8") == buf.getvalue() and new_doc == doc
        raise SystemExit(0 if ok else "products.csv or docs/store-products.md is out of date: run tools/gen_products.py")
    CSV.write_text(buf.getvalue(), encoding="utf-8")
    DOC.write_text(new_doc, encoding="utf-8")
    print(f"{len(rs)} products → {CSV.relative_to(ROOT)}, {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
