#!/usr/bin/env python3
"""The titles the naming job is asked to name, each with only what naming it needs.

WHY THIS EXISTS. The first version of the job handed Claude the repository and a prompt, and it
read CLAUDE.md, the standing instructions and two YAML files of tens of thousands of lines, ran the
build and the gate, and spent 2.5 million input tokens on a dozen names. Naming a title needs the
title, who made it, where to read about it, and what its relatives are already called. This writes
exactly that, and nothing of the project reaches the job but the rules it names by.

WHAT AN ITEM HOLDS. `key`, the title as the store holds it, which is the key the curated file is
written under; `author`; `platforms`; `pages`, the addresses a reader would open; and `related`, up to
three titles already named that share the start of this one or its creator, so a second volume, a
sister series or a companion book is named the way the first was.

    items.py [--limit 12] [--out data/build/naming-items.json]
"""
import argparse
import json
import os
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import population                                                       # noqa: E402

CURATED = pathlib.Path("data/names/curated.yaml")
#: How much of a title two must share before one is offered as the other's relative.
SHARED = 5


def untitled(series, decided):
    """Series rows showing a romanisation that nobody has decided, newest first."""
    out = [r for r in series
           if (r.get("work_en") or {}).get("basis") == "romaji" and r.get("work") not in decided]
    return sorted(out, key=lambda r: (str(r.get("latest") or ""), str(r.get("work"))), reverse=True)


def related(title, named, limit=3, kin=()):
    """`[{ja, en}]` for curated titles that share the first `SHARED` characters with `title`, then
    for named titles by the same creator.

    THE CREATOR'S OTHER TITLES, because a companion book abbreviates its series rather than
    repeating it. 愛カラのゆるい本。 shares nothing at its start with 愛していいのは、カラダだけ, which
    it abbreviates, and the first run of the job, not told the series existed, kept the
    abbreviation as "Ai Kara".
    """
    head = str(title)[:SHARED]
    out = []
    if len(head) >= SHARED:
        out = [k for k in named if k != title and str(k).startswith(head)]
    out += [k for k in kin if k != title and k in named and k not in out]
    return [{"ja": k, "en": named[k].get("en")} for k in out if (named[k] or {}).get("en")][:limit]


def item(row, named, kin=()):
    """One title as the job sees it; `kin` is the other titles by its creator."""
    sources = row.get("sources") or []
    pages = [str(s.get("url")) for s in sources if s.get("url")]
    for u in (row.get("series_url"), row.get("url")):
        if u and u not in pages:
            pages.insert(0, u)
    # A BOOK HAS NO WEB SOURCE, and its shop's page is the one that describes it.
    for p in row.get("print") or []:
        u = p.get("shop_url")
        if u and u not in pages:
            pages.append(u)
    return {"key": row.get("work"), "author": row.get("author") or "",
            "platforms": sorted({str(s.get("platform")) for s in sources if s.get("platform")}),
            "pages": pages[:4], "related": related(row.get("work"), named, kin=kin)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--out", default="data/build/naming-items.json")
    a = ap.parse_args(argv)

    named = (yaml.safe_load(CURATED.read_text(encoding="utf-8")) or {}).get("titles") or {}
    series = population.series(None)
    by = {}
    for r in series:
        if r.get("author"):
            by.setdefault(r["author"], []).append(r.get("work"))
    rows = untitled(series, set(named))[:a.limit]
    items = [item(r, named, by.get(r.get("author")) or ()) for r in rows]
    pathlib.Path(a.out).write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} title(s) to name -> {a.out}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"work={'yes' if items else 'no'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
