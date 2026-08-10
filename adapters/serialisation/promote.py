#!/usr/bin/env python3
"""Turn the agreed leads into a joins file and the platform seeds the adapters read.

WHAT A JOIN IS HERE. A work this database holds only as a printed book, and the address its
serialisation was published at, with the field that says they are one work. Nothing is retired and
no identifier is minted: the printed record already has one, and `identity.py --attachments` gives
it the second address. That is the discovery case. The other case, where the serialisation is
already in the corpus under an identifier of its own, is a merge and is done by hand with
`--merge`, because retiring an address that has been published is not something a pass should do
in bulk (RUNBOOK §11).

WHAT ELSE THIS WRITES. Each platform adapter takes its targets from its own seed file, so the
addresses go there too: `data/source/nicovideo/resolved.yaml` and
`data/source/kadokomi/resolved.yaml`. Those files are APPENDED TO, never rewritten from this pass
alone. Both hold rows put there by earlier work, and a pass must not delete what it is not looking
at.

Usage:  promote.py --dry-run
        promote.py
"""
import argparse
import collections
import datetime
import json
import pathlib
import re
import sys
import urllib.parse

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from identity import match_key  # noqa: E402

NICO = re.compile(r"manga\.nicovideo\.jp/comic/(\d+)")
KADOKOMI = re.compile(r"comic-walker\.com/detail/([A-Za-z0-9_]+)")
FUZ = re.compile(r"(comic-fuz\.com/manga/\d+)")


def agreed(doc):
    """`{work id: [row]}` for the leads a platform page agreed with, best-known platform first.

    A work can be serialised in several places and 109 of these are. Every agreeing address is
    kept, because build.py collapses the platforms into one row and picks whichever it likes for
    the row's own URL, so attaching only one of them would leave the join depending on a choice
    made downstream.
    """
    out = collections.defaultdict(list)
    for r in doc.get("confirmed") or []:
        if r.get("verdict") == "agreed":
            out[r["id"]].append(r)
    return dict(out)


def seed_rows(rows, pattern, held):
    """[(code, title, author)] for the addresses a platform adapter has not been told about."""
    out, seen = [], set()
    for r in rows:
        m = pattern.search(r.get("url") or "")
        if not m or m.group(1) in held or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        out.append((m.group(1), r.get("title") or "", r.get("author") or ""))
    return out


def existing_codes(path, key):
    doc = yaml.safe_load(pathlib.Path(path).read_text()) if pathlib.Path(path).exists() else None
    return {str(w.get(key)) for w in ((doc or {}).get("works") or []) if w.get(key)}


def append_seeds(path, new, key, note):
    """Add rows to a platform's seed file, keeping every row already in it.

    Written by hand-shaped lines rather than by dumping the parsed document, because these files
    carry explanatory comments that a round trip through yaml would delete.
    """
    p = pathlib.Path(path)
    text = p.read_text() if p.exists() else ""
    if not text.rstrip().endswith("works:") and "works:" not in text:
        text = text.rstrip() + "\nworks:\n"
    lines = [text.rstrip("\n"), f"  # {note}"]
    for code, title, author in new:
        lines.append(f"  - title: {json.dumps(title, ensure_ascii=False)}")
        lines.append(f"    {key}: {json.dumps(code, ensure_ascii=False)}")
        if author:
            lines.append(f"    author_on_page: {json.dumps(author, ensure_ascii=False)}")
    lines.append("")
    p.write_text("\n".join(lines))


def write_joins(path, works, retrieved):
    L = ["# A printed work and the address its serialisation was published at.",
         "#",
         "# WHAT MAKES EACH ONE A JOIN. `basis` names the field that agrees, and it is never the",
         "# title: RUNBOOK §11 asks for the creator, the publisher or the imprint, because",
         "# `トワ・エ・モア` is a 1996 コンパス anthology and a 2024 講談社 series at once. The",
         "# creator or the publisher was read off the platform's own page, which is Tier B. Web漫画",
         "# アンテナ found most of these addresses and settled none of them.",
         "#",
         "# READ BY: `identity.py --attachments`, which gives each printed work its second address,",
         "# and by `nicovideo/works.py`, which fetches the ニコニコ pages named here.",
         "source: the platforms named in `platform`",
         "role: join",
         f"retrieved: {retrieved}",
         "record_type: print_web_join",
         f"works: {len(works)}",
         f"joins: {sum(len(v) for v in works.values())}",
         "joins:"]
    for wid in sorted(works):
        for r in works[wid]:
            L.append(f"  - id: {wid}")
            L.append(f"    title: {json.dumps(r['title'], ensure_ascii=False)}")
            L.append(f"    madb: {json.dumps(r.get('madb') or [], ensure_ascii=False)}")
            L.append(f"    platform: {json.dumps(r.get('platform') or '', ensure_ascii=False)}")
            L.append(f"    url: {json.dumps(r['url'], ensure_ascii=False)}")
            L.append(f"    anchor: {json.dumps('web:' + r['url'], ensure_ascii=False)}")
            L.append(f"    basis: {json.dumps(r.get('evidence') or '', ensure_ascii=False)}")
    L.append("")
    pathlib.Path(path).write_text("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--confirmed", default="data/queue/serialisation-confirmed.yaml")
    ap.add_argument("--joins", default="data/queue/serialisation-joins.yaml")
    ap.add_argument("--series", default="data/build/series.json")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    doc = yaml.safe_load(pathlib.Path(a.confirmed).read_text()) or {}
    works = agreed(doc)

    # AN ADDRESS ANOTHER WORK ALREADY ANSWERS TO IS NOT A DISCOVERY. It is the merge case, and a
    # merge is a decision taken by hand. Reported here so it cannot be missed.
    held = {}
    series = json.loads(pathlib.Path(a.series).read_text())["series"]
    for row in series:
        for u in [row.get("url")] + [s.get("url") for s in (row.get("sources") or [])]:
            if u:
                held[u] = row.get("id")
    clash = [(wid, r["url"], held[r["url"]]) for wid, rs in works.items() for r in rs
             if held.get(r["url"]) and held[r["url"]] != wid]

    flat = [r for rs in works.values() for r in rs]
    by_host = collections.Counter(urllib.parse.urlparse(r["url"]).netloc for r in flat)
    print(f"{len(works)} printed work(s) joined to {len(flat)} address(es)")
    for h, n in by_host.most_common():
        print(f"  {n:4d}  {h}")
    for wid, url, other in clash:
        print(f"  ALREADY HELD {url} answers for {other}, wanted by {wid}. That is a merge.")

    nico = seed_rows(flat, NICO, existing_codes("data/source/nicovideo/resolved.yaml", "comic_id"))
    kado = seed_rows(flat, KADOKOMI, existing_codes("data/source/kadokomi/resolved.yaml", "code"))
    # FUZ is keyed on the address rather than on a bare id, which is what its adapter reads. The
    # existing rows hold a full URL, so the comparison is made on the same shape.
    fuz = [(f"https://{c}", t, au) for c, t, au in seed_rows(
        flat, FUZ, {u.replace("https://", "") for u in
                    existing_codes("data/source/comicfuz/resolved.yaml", "url")})]
    print(f"seeds to add: {len(nico)} ニコニコ, {len(kado)} カドコミ, {len(fuz)} COMIC FUZ")

    if a.dry_run:
        return 0

    write_joins(a.joins, works, datetime.date.today().isoformat())
    note = ("Found by adapters/serialisation/: a printed work we hold, whose serialisation was "
            f"here. Added {datetime.date.today().isoformat()}.")
    if nico:
        append_seeds("data/source/nicovideo/resolved.yaml", nico, "comic_id", note)
    if kado:
        append_seeds("data/source/kadokomi/resolved.yaml", kado, "code", note)
    if fuz:
        append_seeds("data/source/comicfuz/resolved.yaml", fuz, "url", note)
    print(f"-> {a.joins}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
