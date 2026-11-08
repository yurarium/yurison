#!/usr/bin/env python3
"""What a shop calls each book it sells, keyed by the ISBN printed on it.

WHY THIS EXISTS. The bibliography catalogues some works as two books with no number and no name:
MADB holds Qualia as M817307 and M817309, one ISBN each, both 2020-03, and nothing else. The
Releases list and the work page drew the work twice, identically. コミックシーモア sells the same
two ISBNs as `Qualia -Envy-` and `Qualia -Jealousy-`, which is the whole of what tells them apart.

WHAT THIS IS. The shop's product title, as the shop wrote it, against the ISBN the shop states.
Nothing is derived here: which part of the title names the book is `facts/volumenumber`'s to read,
in the build, against the title the work is held under. A retailer is Tier C, so this names a book
that the bibliography holds and never adds one.

Usage:  shopnames.py [--capture data/queue/cmoa-volumes.yaml] [--out …/shop-volume-names.yaml]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import isbn as _isbn                                                           # noqa: E402

OUT = "data/source/comparators/shop-volume-names.yaml"


def names(doc):
    """`[{isbn, title, url}]` for every volume in a capture that states both, one per ISBN.

    AN ISBN THE SHOP GIVES TWO TITLES SAYS NOTHING. A listing that files one book under two
    names is a listing we cannot read a name from, so neither is taken.
    """
    seen = {}
    for w in (doc.get("works") or []):
        for v in (w.get("volumes") or []):
            key = _isbn.isbn13(v.get("isbn"))
            title = str(v.get("title") or "").strip()
            if not key or not title:
                continue
            seen.setdefault(key, []).append({"isbn": key, "title": title,
                                             "url": v.get("url") or w.get("url")})
    return [rows[0] for key, rows in sorted(seen.items())
            if len({r["title"] for r in rows}) == 1]


def main(argv=None):
    import argparse
    import json

    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", default="data/queue/cmoa-volumes.yaml")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)

    doc = yaml.safe_load(pathlib.Path(a.capture).read_text()) or {}
    rows = names(doc)
    js = lambda v: json.dumps(v, ensure_ascii=False)                          # noqa: E731
    L = ["# What a shop calls each book it sells, keyed by the ISBN printed on it.",
         "#",
         "# The shop's product title as written, and nothing read out of it. Written by",
         "# adapters/shopnames.py; the build names a volume from it only where the bibliography",
         "# leaves two books of one work with no number and no name.",
         f"source: {js(str(doc.get('source') or ''))}",
         "role: volume-names",
         f"retrieved: {doc.get('retrieved')}",
         f"names: {len(rows)}",
         "volumes:"]
    for r in rows:
        L.append(f"  - isbn: {js(r['isbn'])}")
        L.append(f"    title: {js(r['title'])}")
        if r.get("url"):
            L.append(f"    url: {js(r['url'])}")
    L.append("")
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L))
    print(f"{doc.get('source')}: {len(rows)} book(s) named by ISBN -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
