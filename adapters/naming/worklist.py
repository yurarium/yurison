#!/usr/bin/env python3
"""What the naming job is asked to do after an update: works to induct, titles to name, rulings owed.

WHY THIS EXISTS. Until 2026-10-15 a person ran the update and then, by hand, minted
an identifier for each work the build could not key, wrote an English name for each title still
showing a romanisation, and ruled on each work the feed named that the database held no record of.
The launch plan moves that to a scheduled Claude Code job (docs/LAUNCH-PLAN.md section 5), and this
is its input. It decides nothing. It lists, from the compiled store and the build's own output, and
the job and the gate do the rest.

THREE LISTS, each from the one place that already answers it:

  awaiting    `data/build/awaiting-identifier.json`, which build.py writes because a row the store
              cannot key never becomes a store row.
  untitled    store series rows whose English falls through to a romanisation and which no curated
              entry has decided, the same test as `titles showing a romanisation nobody has ruled
              on`, newest first.
  unruled     feed rows naming a work with no record and no ruling, through `feedgap`.

NAMED worklist.py, NOT queue.py, because a module called queue shadows the standard library's for
anything that puts this directory on the path, and `concurrent.futures` imports it (net.py records
the same trap for http.py).

A RUN WITH NOTHING TO DO SAYS SO, and the workflow does not start Claude, so a quiet day costs no
usage. Each list is cut to `--limit`, which bounds a run's turns; what is cut waits for the next.

    worklist.py [--limit 12] [--out data/build/naming-queue.md]
"""
import argparse
import json
import os
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import feedgap                                                          # noqa: E402
import population                                                       # noqa: E402

CURATED = pathlib.Path("data/names/curated.yaml")
AWAITING = pathlib.Path("data/build/awaiting-identifier.json")


def untitled(series, decided):
    """Series rows showing a romanisation that nobody has decided, newest first."""
    out = [{"id": r.get("id"), "work": r.get("work"), "author": r.get("author"),
            "url": r.get("series_url") or r.get("url"), "latest": r.get("latest") or ""}
           for r in series
           if (r.get("work_en") or {}).get("basis") == "romaji" and r.get("work") not in decided]
    return sorted(out, key=lambda x: (str(x["latest"]), str(x["work"])), reverse=True)


def unruled(releases, series, ruled):
    """Works the feed names that the database does not hold and nobody has ruled on."""
    rows = feedgap.unheld(releases, series)
    by = {}
    for r in rows:
        if feedgap.textnorm.norm(r.get("work")) in ruled:
            continue
        e = by.setdefault(r.get("work"), {"work": r.get("work"), "platforms": set(), "urls": set()})
        e["platforms"].add(r.get("plat_name") or r.get("plat") or "")
        if r.get("url"):
            e["urls"].add(r["url"])
    return [{"work": e["work"], "platforms": sorted(e["platforms"]), "urls": sorted(e["urls"])[:3]}
            for e in by.values()]


def render(q):
    """The queue as the job reads it: one section per list, each item with what a lookup needs."""
    L = ["# Naming queue", ""]
    if not any(q.values()):
        return "\n".join(L + ["Nothing to do this run.", ""])
    if q["awaiting"]:
        L += ["## Works awaiting an identifier", ""]
        for w in q["awaiting"]:
            L.append(f"- {w['work']} ({', '.join(w.get('platforms') or [])}), by {w.get('author') or '?'}; "
                     f"{w.get('chapters') or 0} chapter(s) {w.get('first') or ''} to {w.get('latest') or ''}; "
                     f"addresses: {', '.join(w.get('addresses') or [])}")
        L.append("")
    if q["untitled"]:
        L += ["## Titles showing a romanisation nobody has decided", ""]
        for w in q["untitled"]:
            L.append(f"- {w['id']} {w['work']}, by {w.get('author') or '?'}; {w.get('url') or ''}")
        L.append("")
    if q["unruled"]:
        L += ["## Works the feed names with no record and no ruling", ""]
        for w in q["unruled"]:
            L.append(f"- {w['work']} ({', '.join(w['platforms'])}): {', '.join(w['urls'])}")
        L.append("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--out", default="data/build/naming-queue.md")
    a = ap.parse_args(argv)

    series = population.series(None)
    decided = set((yaml.safe_load(CURATED.read_text(encoding="utf-8")) or {}).get("titles") or {})
    awaiting = (json.loads(AWAITING.read_text(encoding="utf-8")).get("works") or []
                if AWAITING.exists() else [])
    q = {"awaiting": awaiting[:a.limit],
         "untitled": untitled(series, decided)[:a.limit],
         "unruled": [w for w in unruled(population.releases(None), series, feedgap.rulings())
                     if w["work"] not in {x.get("work") for x in awaiting}][:a.limit]}
    pathlib.Path(a.out).write_text(render(q), encoding="utf-8")
    pathlib.Path(a.out).with_suffix(".json").write_text(
        json.dumps({k: len(v) for k, v in q.items()}), encoding="utf-8")
    work = any(q.values())
    print(f"awaiting {len(q['awaiting'])}, untitled {len(q['untitled'])}, "
          f"unruled {len(q['unruled'])} -> {a.out}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"work={'yes' if work else 'no'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
