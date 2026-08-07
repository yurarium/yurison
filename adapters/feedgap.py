#!/usr/bin/env python3
"""Feed rows naming a work this database holds no record of.

WHAT GOES WRONG. The updates feed is keyed by chapter and prints the work's title on every row. A
row whose work has no record cannot offer that work's page, and the work is absent from the list,
from search and from every classification the database makes. On 2026-08-07 five live rows were in
that state, all from ニコニコ漫画, and 24 more sat in the archived month.

WHERE THE CLASS COMES FROM. Each platform pass takes its targets from its own list and nothing
compares the lists. `adapters/nicovideo/releases.py` reads the comparator candidates plus
`data/source/nicovideo/resolved.yaml` and writes `work_update_dates`, which is what the feed shows.
`adapters/nicovideo/works.py` reads `data/queue/serialisation-joins.yaml`, a file of PRINTED works
matched to a serialisation, and writes `web_work_chapters`, which is the only record type build.py
turns into a work row. So a ニコニコ serialisation whose printed book this database does not hold
publishes an update every week and never becomes a work.

WHY THIS DOES NOT READ `wid`. build.py puts the work's identifier on a feed row by matching titles,
so an absent `wid` is that match reporting on itself. It is also a young field: the archived month
predates it and carries no `wid` on any of its 605 rows, so counting absent `wid` gives 610 where
the answer is 29. Reading the two files against each other gives the same answer whenever the
question is asked, which is what a measure has to do.

WHAT IT THEREFORE CANNOT SEE (STANDING-INSTRUCTIONS §14b). Titles are the only join the built feed
offers, so this compares them through `textnorm.norm`, the project's one comparison form. A work
held under a title no fold reconciles with the feed's spelling is invisible here, exactly as it is
invisible to build.py. That is named rather than fixed, because the fold is not what failed: the
five rows of 2026-08-07 are missing under a fold that touches nothing but width and case, and
missing again under one that strips every mark in the string. Both extremes agree, so the finding
does not rest on where the fold draws its line.

WHAT A RULING DOES HERE. `data/queue/unheld-works.yaml` records what was decided about a work and
the evidence behind it. It is joined on for reporting and it leaves the count where it was: a work
admitted and still absent is exactly the state worth counting, and a register that could silence
its own subject is the failure STANDING-INSTRUCTIONS §13 was written about.

Usage:  feedgap.py
        feedgap.py --build data/build --rulings data/queue/unheld-works.yaml
"""
import argparse
import collections
import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import textnorm                                                             # noqa: E402

RULINGS = "data/queue/unheld-works.yaml"


def held(series):
    """`{comparison form: work id}` for every work the database holds a series row for."""
    out = {}
    for row in series or []:
        key = textnorm.norm(row.get("work"))
        if key:
            out.setdefault(key, row.get("id"))
    return out


def unheld(releases, series):
    """The feed rows whose work has no series row, in the order the feed gives them.

    A row with no title at all is not counted. It states no work, so it cannot state a work we
    lack, and counting it would mix a missing record up with a missing field.
    """
    have = held(series)
    out = []
    for r in releases or []:
        key = textnorm.norm(r.get("work"))
        if key and key not in have:
            out.append(r)
    return out


def rulings(path=RULINGS):
    """`{comparison form: ruling}` from the inclusion register, empty where there is no file."""
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    doc = yaml.safe_load(p.read_text()) or {}
    out = {}
    for r in doc.get("rulings") or []:
        key = textnorm.norm(r.get("work"))
        if key:
            out[key] = r
    return out


def works(rows, ruled=None):
    """One entry per distinct work: `[{work, rows, platforms, disposition}]`, commonest first."""
    ruled = ruled or {}
    by_work = collections.OrderedDict()
    for r in rows:
        key = textnorm.norm(r.get("work"))
        e = by_work.setdefault(key, {"work": r.get("work"), "rows": 0, "platforms": set(),
                                     "disposition": (ruled.get(key) or {}).get("disposition")})
        e["rows"] += 1
        e["platforms"].add(r.get("plat") or "")
    for e in by_work.values():
        e["platforms"] = sorted(e["platforms"])
    return sorted(by_work.values(), key=lambda e: (-e["rows"], e["work"] or ""))


def feed_rows(build):
    """Every row a reader can meet: the live feed and each archived month, tagged with its file."""
    b = pathlib.Path(build) / "feed"
    out = []
    for f in [b / "current.json"] + sorted(b.glob("[0-9]*-[0-9]*.json")):
        if not f.exists():
            continue
        for r in (json.loads(f.read_text()) or {}).get("releases") or []:
            out.append(dict(r, feed_file=f.name))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--rulings", default=RULINGS)
    a = ap.parse_args(argv)

    rows = feed_rows(a.build)
    series = (json.loads((pathlib.Path(a.build) / "series.json").read_text())
              or {}).get("series") or []
    bad = unheld(rows, series)
    ruled = rulings(a.rulings)

    by_file = collections.Counter(r.get("feed_file") for r in bad)
    print(f"{len(bad)} of {len(rows)} feed row(s) name a work with no record, "
          f"across {len(works(bad))} work(s)")
    for f, n in sorted(by_file.items()):
        print(f"  {n:4d}  {f}")
    print()
    print(f"  {'rows':>4}  {'ruled':10}  {'platform':14}  work")
    for e in works(bad, ruled):
        print(f"  {e['rows']:>4}  {e['disposition'] or 'unexamined':10}  "
              f"{','.join(e['platforms'])[:14]:14}  {e['work']}")
    unexamined = sum(1 for e in works(bad, ruled) if not e["disposition"])
    if unexamined:
        print(f"\n{unexamined} work(s) with no ruling. Judge them against DEFINITIONS §2 and §7 "
              f"and record the outcome in {a.rulings}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
