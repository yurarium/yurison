#!/usr/bin/env python3
"""Ask both searches about every printed work that has no web address, and record every answer.

WHAT IT WRITES, AND WHY IT IS NOT A RECORD. `data/queue/serialisation-search.yaml`, one row per
work asked, holding what was searched for and what each site said. It sits in `data/queue/` for the
same reason `adapters/editions/capture.py` does: Web漫画アンテナ is Tier C and may not supply a
stored field (REQUIREMENTS §1), so nothing in this file can become a record by itself. What
promotes a row is `confirm.py`, which reads the platform's own page and applies the agreement test.

A WORK NOBODY ASKED AND A WORK WITH NO SERIALISATION ARE DIFFERENT STATES, and this file is where
the difference lives. Every row carries `nico` and `antenna` outcomes of `hit`, `none` or
`unanswered`, so the counts at the end separate "asked and found nothing" from "the fetch failed".
An empty result set looks exactly like a broken fetch (STANDING-INSTRUCTIONS §4), so both sites are
required to state their emptiness in words before it is believed.

THE POPULATION. Works in `series.json` with no URL, no chapters, and a first printed volume no
older than `--since`. 2019 is where this pass started, on the argument that the platforms were all
running by then. The argument is only half right, and both halves are worth stating: the platforms
have been running far longer than that (ニコニコ静画 since 2009, カドコミ since 2014), and 1,151
of the 2,068 print-only rows carry no date at all, so a date filter drops more works than it keeps.
`--since 1900 --include-undated` asks about every one of them, which is what closes the difference
between a work with no serialisation and a work nobody asked about.

Usage:  sweep.py --since 2019
        sweep.py --since 1900 --include-undated       every print-only work in the database
        sweep.py --since 2019 --limit 20              a sample, for checking the shape of an answer
"""
import pathlib as _pl0
import sys as _sys0

_sys0.path.insert(0, str(_pl0.Path(__file__).resolve().parents[1]))

# UNDER A NAME THIS FILE DOES NOT ALREADY USE. `population` below is a function here,
# and the bare import bound the module to the same name: whichever came second won and
# nothing said so. `adapters/lint/shadowing.py` counts this shape.
import population as _population  # noqa: E402

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

import find as F                                                               # noqa: E402
import net                                                                     # noqa: E402

NICO = "https://manga.nicovideo.jp/search?q={q}"
ANTENNA = "https://webcomics.jp/search?q={q}"
BRACKET = re.compile(r"^\[[^\]]*\]")


def population(series_path, since, include_undated=False):
    """[{id, title, author, publisher, imprint, madb, first}] for the print-only works to ask about.

    Print-only is no URL and no chapters, which is how `series.json` renders a work the database
    holds only as a book. The date is the row's own `first`, which build.py has already moved back
    to the earliest printed volume.

    AN UNDATED WORK IS NOT AN OLD ONE. 1,151 of the 2,068 print-only rows carry no date at all,
    almost all of them BOOK☆WALKER's digital-first labels, which state no 底本発行日. A date filter
    silently drops every one of them, and "we could not date it" is not "it is too old to have been
    serialised" (STANDING-INSTRUCTIONS §5). So they are asked about deliberately or skipped
    deliberately, and the flag is what says which.
    """
    rows = _population.series(series_path)
    out = []
    for w in rows:
        if w.get("url") or w.get("chapters"):
            continue
        if not w.get("first"):
            if not include_undated:
                continue
        elif w["first"] < since:
            continue
        pr = w.get("print") or []
        out.append({
            "id": w.get("id"), "title": w.get("work"), "author": w.get("author") or "",
            "first": w.get("first"),
            "publisher": sorted({BRACKET.sub("", p.get("publisher") or "") for p in pr if p.get("publisher")}),
            "imprint": sorted({p.get("imprint") for p in pr if p.get("imprint")}),
            "madb": [p.get("work_id") for p in pr if p.get("work_id")],
        })
    return out


def ask(work, cache, age):
    """Both searches for one work, stopping at the first query form that either site answers about.

    Query forms are tried in order and a form is only abandoned when BOTH sites answered and
    neither found anything. Stopping on the first site's silence would drop the works whose
    catalogued title carries apparatus one site strips and the other does not.
    """
    res = {"queries": [], "nico": [], "antenna": [],
           "nico_state": "unanswered", "antenna_state": "unanswered"}
    for q in F.queries(work["title"]):
        res["queries"].append(q)
        enc = urllib.parse.quote(q)
        # Both sites at once. They are different hosts, so neither sees traffic any faster than a
        # serial loop would send it, and the run takes half as long (net.py, per-host pacing).
        got = net.fetch_many([NICO.format(q=enc), ANTENNA.format(q=enc)], cache, age, workers=2)
        rn, ra = got[NICO.format(q=enc)], got[ANTENNA.format(q=enc)]

        if rn.text is not None and F.nico_searched(rn.text):
            hits = [h for h in F.nico_results(rn.text) if F.title_matches(work["title"], h["title"])]
            res["nico_state"] = "hit" if hits else "none"
            res["nico"] = hits or res["nico"]
            res.pop("nico_error", None)
        elif res["nico_state"] == "unanswered":
            res["nico_error"] = rn.error or f"unrecognised page (HTTP {rn.status})"

        pa = F.antenna_results(ra.text)
        if pa["answered"]:
            hits = [h for h in pa["works"] if F.title_matches(work["title"], h["title"])]
            res["antenna_state"] = "hit" if hits else "none"
            res["antenna"] = hits or res["antenna"]
            res.pop("antenna_error", None)
        elif res["antenna_state"] == "unanswered":
            res["antenna_error"] = ra.error or f"unrecognised page (HTTP {ra.status})"

        if res["nico_state"] == "hit" or res["antenna_state"] == "hit":
            break
    return res


def js(v):
    return json.dumps(v, ensure_ascii=False)


def write(path, rows, since, retrieved):
    L = [
        "# Where each printed work with no web address might have been serialised.",
        "#",
        "# NOT A RECORD. Web漫画アンテナ is Tier C and attests nothing (REQUIREMENTS §1); ニコニコ",
        "# 漫画's search is the platform speaking, and even there a search result is a lead until",
        "# the work's own page has been read and the agreement test applied. `confirm.py` does",
        "# that. Nothing here reaches data/source/ on its own.",
        "#",
        "# `nico` and `antenna` each take hit, none or unanswered. `none` means the site said in",
        "# words that it has nothing; `unanswered` means we could not read the page, which is not",
        "# the same claim and must never be counted as an absence.",
        "source: manga.nicovideo.jp, webcomics.jp",
        "role: discovery-only",
        f"first_volume_since: {since}",
        f"retrieved: {retrieved}",
        "record_type: serialisation_search",
        f"works: {len(rows)}",
        "asked:",
    ]
    for r in sorted(rows, key=lambda x: x["id"] or ""):
        L.append(f"  - id: {r['id']}")
        L.append(f"    title: {js(r['title'])}")
        L.append(f"    author: {js(r['author'])}")
        L.append(f"    publisher: {js(r['publisher'])}")
        # The imprint is the third field RUNBOOK §11 accepts, and on one platform it is the only
        # one that speaks: COMIC FUZ tags a series まんがタイムKRコミックス, which is exactly what
        # the bibliography prints on the volume.
        L.append(f"    imprint: {js(r['imprint'])}")
        L.append(f"    first: {js(r['first'])}")
        L.append(f"    madb: {js(r['madb'])}")
        L.append(f"    queries: {js(r['queries'])}")
        L.append(f"    nico: {r['nico_state']}")
        if r.get("nico_error"):
            L.append(f"    nico_error: {js(r['nico_error'])}")
        if r["nico"]:
            L.append("    nico_hits:")
        for h in r["nico"]:
            L.append(f"      - comic_id: {js(h['comic_id'])}")
            L.append(f"        title: {js(h['title'])}")
            L.append(f"        author: {js(h['author'])}")
            L.append(f"        url: {js(h['url'])}")
            L.append(f"        updated: {js(h.get('updated'))}")
        L.append(f"    antenna: {r['antenna_state']}")
        if r.get("antenna_error"):
            L.append(f"    antenna_error: {js(r['antenna_error'])}")
        if r["antenna"]:
            L.append("    antenna_hits:")
        for h in r["antenna"]:
            L.append(f"      - site: {js(h['site'])}")
            L.append(f"        title: {js(h['title'])}")
            L.append(f"        url: {js(h['url'])}")
            L.append(f"        author: {js(h.get('author') or '')}")
    L.append("")
    pathlib.Path(path).write_text("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # THE STORE BY DEFAULT AND A FILE ONLY WHEN ASKED, §13.
    ap.add_argument("--series", default=None,
                    help="read the work rows from this series.json instead of from the store")
    ap.add_argument("--out", default="data/queue/serialisation-search.yaml")
    ap.add_argument("--cache", default="/tmp/yuri-serialisation-cache")
    ap.add_argument("--since", default="2019")
    ap.add_argument("--include-undated", action="store_true",
                    help="ask about the print-only rows that carry no date. They are not the old "
                         "half: almost all of them are digital-first labels that state no "
                         "printing date at all.")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--age", type=int, default=net.AGE_LISTING)
    a = ap.parse_args(argv)

    pop = population(a.series, a.since, a.include_undated)
    if a.limit:
        pop = pop[: a.limit]
    print(f"{len(pop)} print-only work(s): a first volume from {a.since} or later"
          + (", and the undated rows" if a.include_undated else ""))

    rows, done = [], 0
    for w in pop:
        r = dict(w, **ask(w, a.cache, a.age))
        rows.append(r)
        done += 1
        if done % 25 == 0:
            print(f"  {done}/{len(pop)}")

    write(a.out, rows, a.since, datetime.date.today().isoformat())
    c = collections.Counter()
    for r in rows:
        c[("nico", r["nico_state"])] += 1
        c[("antenna", r["antenna_state"])] += 1
        c["either-hit"] += r["nico_state"] == "hit" or r["antenna_state"] == "hit"
    for site in ("nico", "antenna"):
        print(f"{site:8s} hit {c[(site, 'hit')]:4d}   none {c[(site, 'none')]:4d}   "
              f"unanswered {c[(site, 'unanswered')]:4d}")
    print(f"at least one lead: {c['either-hit']} of {len(rows)}")
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
