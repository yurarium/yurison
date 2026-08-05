#!/usr/bin/env python3
"""ledger.py: a capture that shrank is reported; a host that is down is not."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ledger  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/ledger.py"]

BEFORE = {"magapoke": {"files": 4, "works": 37, "rows": 1952, "retrieved": "2026-08-04"},
          "gigaviewer": {"files": 9, "works": 300, "rows": 7994, "retrieved": "2026-08-04"},
          "tiny": {"files": 1, "works": 1, "rows": 9, "retrieved": "2026-08-04"}}


def main(s):
    # THE CASE THIS EXISTS FOR. マガポケ returned ten well-formed episodes where the platform
    # published 147, for months. Every row was faultless and the file was fresh.
    now = dict(BEFORE, magapoke={"files": 4, "works": 37, "rows": 316, "retrieved": "2026-08-05"})
    d = ledger.compare(now, BEFORE)
    s.eq([x["source"] for x in d], ["magapoke"], "a source re-fetched into far less is reported")
    s.eq(d[0]["lost"], 1636, "with what it lost")
    s.eq(d[0]["was"], 1952, "and what it held before")

    # A HOST THAT IS DOWN IS NOT A DATA PROBLEM. A well-behaved adapter refuses to write a thin
    # result, so the file still holds the last good capture and `retrieved` does not advance.
    # Reporting that would be an alarm about the world, not about us.
    stale = dict(BEFORE, magapoke={"files": 4, "works": 37, "rows": 1952, "retrieved": "2026-08-04"})
    s.eq(ledger.compare(stale, BEFORE), [], "a source that was not re-fetched is not compared")

    # AND THE DANGEROUS SHAPE OF THE SAME FAILURE: an adapter with no floor that wrote what a
    # broken host gave it. The date advanced, so the good data is already gone, and it is reported.
    wiped = dict(BEFORE, magapoke={"files": 4, "works": 2, "rows": 0, "retrieved": "2026-08-05"})
    s.eq([x["now"] for x in ledger.compare(wiped, BEFORE)], [0],
         "a re-fetch that emptied a source is reported")

    grew = dict(BEFORE, magapoke={"files": 4, "works": 40, "rows": 2100, "retrieved": "2026-08-05"})
    s.eq(ledger.compare(grew, BEFORE), [], "a source that grew is not a drop")

    # Proportion, not count: a small source losing two rows has not broken.
    small = dict(BEFORE, tiny={"files": 1, "works": 1, "rows": 7, "retrieved": "2026-08-05"})
    s.eq(ledger.compare(small, BEFORE), [], "a source below the floor is noise, not signal")

    # A chapter withdrawn is normal. 冷たくて柔らか lost a stretch of 64 that way.
    few = dict(BEFORE, gigaviewer={"files": 9, "works": 300, "rows": 7930,
                                   "retrieved": "2026-08-05"})
    s.eq(ledger.compare(few, BEFORE), [], "a handful of withdrawn chapters is not a broken capture")

    s.eq(ledger.compare(BEFORE, None), [], "with no previous run, nothing is claimed")
    s.eq(ledger.compare({"new": {"rows": 5, "retrieved": "2026-08-05"}}, BEFORE), [],
         "and a source seen for the first time is not a drop")

    runs = ledger.append([], BEFORE, at="2026-08-04T00:00:00+00:00")
    s.eq(len(runs), 1, "the first run is recorded")
    runs = ledger.append(runs, BEFORE, at="2026-08-05T00:00:00+00:00")
    s.eq([r["at"][:10] for r in runs], ["2026-08-04", "2026-08-05"], "and the next is appended")
    s.eq(runs[0]["sources"]["magapoke"]["rows"], 1952,
         "a run already written is never rewritten, or the comparison means nothing")
    s.eq(len(ledger.append(runs * 40, BEFORE, keep=3)), 3, "and the window drops the oldest")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
