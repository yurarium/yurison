#!/usr/bin/env python3
"""runslot.py: which ticks of the update workflow are the planned run."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import runslot  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/runslot.py"]

t = runslot.parse


def main(s):
    s.eq(runslot.latest_slot(t("2026-11-17T16:00:00Z")), t("2026-11-17T15:37:00Z"),
         "the slot is the most recent planned time")
    s.eq(runslot.latest_slot(t("2026-11-17T02:00:00Z")), t("2026-11-16T15:37:00Z"),
         "and before the first of the day it is yesterday's last")
    s.eq(runslot.latest_slot(t("2026-11-17T03:07:00Z")), t("2026-11-17T03:07:00Z"),
         "a tick on the slot itself is that slot")

    before = [{"at": "2026-11-17T04:10:00+00:00", "started": "2026-11-17T03:20:00+00:00"}]
    s.check(runslot.due(t("2026-11-17T16:40:00Z"), before)[0],
            "a slot with no run since it is due")
    s.check(not runslot.due(t("2026-11-17T09:00:00Z"), before)[0],
            "a slot already run is not, which is every other tick")

    # A run that began before the slot fetched before the cluster, whenever it finished.
    straddles = [{"at": "2026-11-17T16:05:00+00:00", "started": "2026-11-17T15:20:00+00:00"}]
    s.check(runslot.due(t("2026-11-17T17:00:00Z"), straddles)[0],
            "a run started before the slot does not cover it, though its entry is written after")
    old = [{"at": "2026-11-17T16:05:00+00:00"}]
    s.check(not runslot.due(t("2026-11-17T17:00:00Z"), old)[0],
            "an entry from before `started` was recorded is read by when it was written")

    s.check(runslot.due(t("2026-11-17T17:00:00Z"), [])[0], "an empty ledger is due")
    s.check(not runslot.due(t("2026-11-17T17:00:00Z"), before, attempts=2)[0],
            "two failed runs for one slot are enough until the next")
    s.check(runslot.due(t("2026-11-17T17:00:00Z"), before, attempts=1)[0],
            "while one is retried")


if __name__ == "__main__":
    sys.exit(testkit.run(main, pathlib.Path(__file__).name))
