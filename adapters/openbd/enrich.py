#!/usr/bin/env python3
"""Enrich the corpus from openBD, storing only licence-safe derived fields.

openBD's terms permit use for 本の紹介 purposes but forbid transferring use rights to third
parties, and REQUIREMENTS §3 therefore rules out republishing bulk openBD payloads. So this adapter
diverges from the usual source-layer rule: **raw payloads stay in a local cache outside the repo,
and only a derived projection is committed** — existence, confirmed publication date, and a cover
URL where openBD supplies one.

No synopsis (内容紹介) or review text is ever stored; that is copyrightable and forbidden by §2.

Usage:  enrich.py --cache $YURI_CACHE/openbd-cache/yurihime.json \
                  --works data/source/madb --out data/source/openbd --retrieved 2026-08-01
"""
import argparse, glob, json, pathlib, sys

import yaml

# Health assertion: openBD resolved ~77% of this corpus on 2026-08-01. A large drop means the API
# changed or the fetch failed, and the adapter must not write a thinned record set (§6).
MIN_HIT_RATE = 0.50


def yaml_str(t):
    return '"' + str(t).replace("\\", "\\\\").replace('"', '\\"') + '"'


def pubdate(raw):
    """openBD gives YYYYMMDD or YYYYMM. Normalise to ISO; never invent precision we lack."""
    d = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if len(d) >= 8:
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    if len(d) >= 6:
        return f"{d[:4]}-{d[4:6]}"
    return d[:4] if len(d) == 4 else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--works", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    a = ap.parse_args()

    cache = json.loads(pathlib.Path(a.cache).read_text())
    files = sorted(glob.glob(f"{a.works}/*.yaml"))
    if not files:
        sys.exit(f"no source records under {a.works}")

    all_isbns = []
    for f in files:
        all_isbns += [v["isbn"] for v in (yaml.safe_load(open(f)).get("volumes") or []) if v.get("isbn")]
    hit_rate = len(cache) / max(len(set(all_isbns)), 1)
    if hit_rate < MIN_HIT_RATE:
        sys.exit(f"HEALTH: openBD resolved {hit_rate:.1%} of ISBNs (< {MIN_HIT_RATE:.0%}). Refusing to write.")

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.yaml"):
        f.unlink()

    written = covers = confirmed = 0
    for f in files:
        w = yaml.safe_load(open(f))
        rows = []
        for v in w.get("volumes") or []:
            rec = cache.get(v.get("isbn", ""))
            if not rec:
                continue
            s = rec.get("summary", {}) or {}
            rows.append((v["isbn"], pubdate(s.get("pubdate")), (s.get("cover") or "").strip()))
        if not rows:
            continue
        L = [
            "# Derived from openBD. Raw payloads are NOT committed — openBD forbids transferring",
            "# use rights to third parties (REQUIREMENTS §3). No synopsis text is stored (§2).",
            "source: openbd",
            f"retrieved: {a.retrieved}",
            f"work_id: {w['work_id']}",
            "record_type: volume_enrichment",
            "volumes:",
        ]
        for isbn, date, cover in rows:
            L.append(f"  - isbn: {yaml_str(isbn)}")
            L.append("    openbd: present")
            if date:
                L.append(f"    published: {date}")
                confirmed += 1
            if cover:
                # Referenced live from openBD's host, never cached or committed (§2, §4).
                L.append(f"    cover_url: {yaml_str(cover)}")
                covers += 1
        L.append("")
        (out / f"{w['work_id']}.yaml").write_text("\n".join(L))
        written += 1

    print(f"openBD hit rate : {hit_rate:.1%} ({len(cache)}/{len(set(all_isbns))} ISBNs)")
    print(f"works enriched  : {written}/{len(files)}  -> {out}")
    print(f"dates confirmed : {confirmed}")
    print(f"cover URLs      : {covers}")
    if covers < written * 0.05:
        print("NOTE: openBD supplies almost no covers for this publisher. The site is effectively")
        print("      text-only for this corpus — see docs/MADB.md and REQUIREMENTS §2.")


if __name__ == "__main__":
    main()
