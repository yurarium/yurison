#!/usr/bin/env python3
"""latefind.py: a chapter is late when an update ran between its publication and our finding it."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import testkit  # noqa: E402
import latefind as lf  # noqa: E402

COVERS = ["adapters/latefind.py"]


def main(s):
    # ── the owner's example: found Monday 9 November ─────────────────────────────────────────────
    days = {"2026-11-06", "2026-11-07", "2026-11-08", "2026-11-09"}
    s.check(lf.missed("2026-11-07", "2026-11-09", days),
            "a Saturday chapter found on Monday is late: Sunday's run missed it")
    s.check(not lf.missed("2026-11-08", "2026-11-09", days),
            "a Sunday chapter found on Monday is not: no run fell between")
    s.check(not lf.missed("2026-11-09", "2026-11-09", days), "nor is one found the day it came out")
    s.check(lf.missed("2026-11-06", "2026-11-09", days),
            "燕のあやかし画帳, out on Friday and found on Monday, is late")

    # ── a day with no run cannot have missed anything ────────────────────────────────────────────
    october = {"2026-10-09", "2026-10-10", "2026-10-12"}
    s.check(not lf.missed("2026-10-10", "2026-10-12", october),
            "with no run on 11 October, a chapter of the 10th found on the 12th was found in time")

    # ── the days are Japan's ─────────────────────────────────────────────────────────────────────
    s.eq(lf.run_day("2026-11-05T21:58:03+00:00"), "2026-11-06",
         "a run at 21:58 UTC ran on the next day in Japan")
    s.eq(lf.run_day("2026-11-05T13:28:02+00:00"), "2026-11-05", "and one at 13:28 UTC the same day")
    s.eq(lf.run_day("2026-11-05T14:59:59"), "2026-11-05", "a timestamp with no zone is UTC")

    # ── the kept days outlast the window of runs ─────────────────────────────────────────────────
    doc = {"days": ["2026-08-10"], "runs": [{"at": "2026-11-08T11:10:54+00:00"}, {"sources": {}}]}
    s.eq(lf.run_days(doc), {"2026-08-10", "2026-11-08"},
         "the run days are the kept list and the runs still in the window")
    s.eq(lf.with_day(["2026-11-08", "2026-08-10"], "2026-11-09T12:35:14+00:00"),
         ["2026-08-10", "2026-11-08", "2026-11-09"], "a run adds its day and drops none")
    s.eq(lf.with_day(["2026-11-09"], "2026-11-09T01:00:00+00:00"), ["2026-11-09"],
         "and a second run on one day adds nothing")
    s.check(not lf.missed("", "2026-11-09", days), "a row with no publication date is not late")
    s.eq(lf.run_days(None), set(), "an absent ledger has no days")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "latefind"))
