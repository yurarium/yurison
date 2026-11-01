#!/usr/bin/env python3
"""Works whose publisher labels them in its own catalogue text, taken from the national bibliography.

WHY THIS EXISTS. メジロバナの咲く is described by 白泉社 as the author's first full-length
ガールズラブ, which is DEFINITIONS §4's `gl`, and no route reached it: its imprint is 花とゆめ
コミックス, BOOK☆WALKER does not sell it, and the one shop that shelves it as 百合 is down. The label
was found by a person reading the publisher's text, so the label comes from `data/publisher-text.yaml`
and the record comes from MADB by ISBN, as every other record in data/source/madb does.

WHAT IT WRITES. One record per work under `route: isbn-from-publisher-text`, with the publisher's
word as the label's `term` and the page and sentence it was read from as the basis. A work another
route already holds is left to that route and reported, because two records for one work would be
two works.

Usage:  by_publisher_text.py --cache $YURI_CACHE/madb-cache/current
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import by_isbn                                                                 # noqa: E402
import extract                                                                 # noqa: E402

ROUTE = "isbn-from-publisher-text"
SOURCE = "data/publisher-text.yaml"
NOTE = ("The publisher's own catalogue text applies this label to the work (DEFINITIONS §4,\n"
        "    catalogue entry). The term is quoted from it as printed.")


def entries(path):
    """`{isbn13: entry}` out of the hand-kept file."""
    import yaml

    doc = yaml.safe_load(pathlib.Path(path).read_text()) or {}
    return {by_isbn.isbn13(e.get("isbn")): e for e in doc.get("works") or []
            if by_isbn.isbn13(e.get("isbn")) and e.get("label") in ("yuri", "gl")}


def basis(entry):
    """The label's basis: the page the publisher's text was read on, and its own word."""
    return {"source": "publisher", "url": entry["url"], "retrieved": str(entry["retrieved"]),
            "term": entry["term"], "quote": entry["quote"]}


def which(vs, wanted):
    """The entry whose ISBN selected this work's volumes."""
    for r in vs:
        got = wanted.get(by_isbn.isbn13(extract.flat(r.get("schema:isbn", ""))))
        if got:
            return got
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", required=True, help="a MADB release directory")
    ap.add_argument("--tag", help="MADB release tag; read from RELEASE.json by default")
    ap.add_argument("--retrieved", help="ISO date the cache was downloaded; RELEASE.json by default")
    ap.add_argument("--source", default=SOURCE)
    ap.add_argument("--out", default="data/source/madb")
    a = ap.parse_args(argv)
    extract.pinned(a)

    wanted = entries(a.source)
    books = extract.load(a.cache, "metadata101.json")
    series = {r["schema:identifier"]: r for r in extract.load(a.cache, "metadata104.json")}
    vols = by_isbn.select(books, set(wanted))
    by_series, grouping = extract.group(by_isbn.expand(books, vols, series), series)
    by_series = extract.dedupe(by_series)

    out = pathlib.Path(a.out)
    held = by_isbn.owned_elsewhere(out, ROUTE)
    for f in out.glob("*.yaml"):
        if f"route: {ROUTE}" in f.read_text():
            f.unlink()
    written = 0
    for sid, vs in sorted(by_series.items()):
        e = which(vs, wanted)
        if extract.work_id(sid) in held:
            print(f"  held by another route: {extract.work_id(sid)} {e and e.get('title')}")
            continue
        (out / f"{extract.work_id(sid)}.yaml").write_text(
            extract.render(sid, vs, series, grouping[sid], a.tag, a.retrieved, ROUTE,
                           (e["label"], NOTE), basis=basis(e)))
        written += 1
    answered = {by_isbn.isbn13(extract.flat(r.get("schema:isbn", ""))) for r in vols}
    for isbn in sorted(set(wanted) - answered):
        print(f"  not in release {a.tag}: {isbn} {wanted[isbn].get('title')}")
    print(f"{len(wanted)} publisher text(s); {written} work(s) written -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
