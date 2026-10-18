#!/usr/bin/env python3
"""The single-instalment works whose status nobody has stated, for the job to look up.

WHY THIS EXISTS. A work we hold one instalment of is either a one-shot or the start of something,
and the build can only read shapes: an instalment named after its work, a contest citation, a
第1話. The owner found four in one week labelled inconsistently: マンガワン's 太刀んぼ キルコ and
アマデウス arrived as new series because their only chapter is called 1話, つるこさん was a one-shot
on its page and a chapter in the feed, and Cry for the Moon was a story the platform had moved into
a collection. What settles each is a page: the platform's 読切 badge, the publisher's listing, the
author's own post. The job reads the page and `integrate_status.py` writes what it found into
`data/completion-reviewed.yaml`, the register a person already writes these verdicts in.

WHAT IT ASKS ABOUT. A work holding one instalment that the register has no entry for, or only an
`unsettled` one at least AGAIN days old, whose state is `unknown`, a running state, or a one-shot
resting on our own reading. A one-shot a platform states is not asked about: the page has already
been read.

    status_items.py [--limit 12] [--out data/build/status-items.json]
"""
import argparse
import datetime
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import completion                                                       # noqa: E402
import population                                                       # noqa: E402
import textnorm                                                         # noqa: E402

RUNNING = ("unknown", "active", "slow", "dormant", "hiatus")
#: DAYS BEFORE AN `unsettled` WORK IS ASKED AGAIN. Unsettled says the pages said nothing yet, which
#: changes: nine of the first twelve answers were unsettled, a 第1話 waiting on its second chapter
#: among them, and skipping every reviewed work would have left them unasked for good.
AGAIN = 30


def settled(reviewed, today):
    """The reviewed works to leave alone: every verdict except an `unsettled` one AGAIN days old."""
    out = set()
    for w, e in (reviewed or {}).items():
        if (e or {}).get("verdict") == "unsettled":
            try:
                age = (datetime.date.fromisoformat(today)
                       - datetime.date.fromisoformat(str(e.get("reviewed"))[:10])).days
            except ValueError:
                age = AGAIN
            if age >= AGAIN:
                continue
        out.add(textnorm.norm(w))
    return out


def undecided(series, reviewed, today=None):
    """Single-instalment rows whose status rests on nothing stated, newest first."""
    seen = settled(reviewed, today or datetime.date.today().isoformat())
    out = [r for r in series
           if r.get("chapters") == 1 and not r.get("partial")
           and textnorm.norm(r.get("work") or "") not in seen
           and (r.get("state") in RUNNING or r.get("oneshot_inferred"))]
    return sorted(out, key=lambda r: (str(r.get("latest") or ""), str(r.get("work"))), reverse=True)


def item(row):
    """One work as the job sees it."""
    sources = row.get("sources") or []
    pages = []
    for u in [row.get("series_url"), row.get("url")] + [s.get("url") for s in sources]:
        if u and u not in pages:
            pages.append(str(u))
    return {"key": row.get("work"), "author": row.get("author") or "",
            "platforms": sorted({str(s.get("platform")) for s in sources if s.get("platform")}),
            "instalment": row.get("latest_ep") or "", "dated": row.get("latest") or "",
            "pages": pages[:3]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--out", default="data/build/status-items.json")
    a = ap.parse_args(argv)

    rows = undecided(population.series(None), completion.load().get("works") or {})
    items = [item(r) for r in rows[:a.limit]]
    pathlib.Path(a.out).write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} of {len(rows)} work(s) to look up -> {a.out}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"status={'yes' if items else 'no'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
