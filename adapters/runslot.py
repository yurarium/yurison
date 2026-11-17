#!/usr/bin/env python3
"""Whether this tick of the update workflow is the planned run, or a tick with nothing to do.

WHY THE WORKFLOW TICKS MORE OFTEN THAN IT RUNS. The update is planned twice a day, 30 minutes
behind the release clusters in Japan (see the schedule in .github/workflows/update.yml). GitHub
started each scheduled run 6 to 10 hours late through November 2026, on every workflow in both
repositories: the run planned for 00:37 JST began between 05:30 and 08:50 JST, which is the
latency the times were chosen to remove. Moving a minute does not help a delay of hours. Ticking
about every three hours does, because whatever the delay, some tick lands within three hours of
each slot, and the ticks that find their slot already covered stop here having done nothing.

WHAT COVERS A SLOT. A run that STARTED at or after it. The ledger entry is written near the end of
a run, so a run that began before 15:37 and finished after it fetched before the cluster it was
meant to catch, and counts for the slot before. Entries written before `started` was recorded are
read by `at`, which is the best they say.

A FAILED RUN WRITES NO LEDGER ENTRY, so its slot stays uncovered and the next tick tries again.
At most `ATTEMPTS` times per slot: a run that fails the same way every time would otherwise ask
every source eight times a day.

Usage:  runslot.py slot [--now ISO]      the current slot, ISO UTC, for counting earlier attempts
        runslot.py due [--runs data/ledger/runs.yaml] [--attempts N] [--now ISO]
        prints the decision and writes `due=yes|no` to $GITHUB_OUTPUT when it is set.
"""
import datetime
import os
import pathlib
import sys

#: The planned runs, UTC. 15:37 is 00:37 JST, after the midnight batch; 03:07 is 12:07 JST,
#: after the 11:00 and 12:00 clusters. The workflow's own ticks include these two times.
SLOTS = ((3, 7), (15, 37))

#: Real runs started for one slot before the ticks stop trying until the next.
ATTEMPTS = 2

UTC = datetime.timezone.utc


def parse(s):
    """An ISO time as an aware UTC datetime, or None."""
    if not s:
        return None
    t = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def latest_slot(now):
    """The most recent planned time at or before `now`."""
    for back in (0, 1):
        day = (now - datetime.timedelta(days=back)).date()
        times = [datetime.datetime(day.year, day.month, day.day, h, m, tzinfo=UTC)
                 for h, m in SLOTS]
        past = [t for t in times if t <= now]
        if past:
            return max(past)
    raise AssertionError("a day holds a slot")


def last_started(runs):
    """When the newest real run in the ledger started, or None for an empty ledger."""
    if not runs:
        return None
    r = runs[-1]
    return parse(r.get("started") or r.get("at"))


def due(now, runs, attempts=0):
    """(due, reason) for a tick at `now`, given the ledger's runs and the real runs already started
    for the current slot that wrote no entry."""
    slot = latest_slot(now)
    last = last_started(runs)
    if last is not None and last >= slot:
        return False, f"the {slot:%H:%M} slot is covered by the run started {last:%Y-%m-%d %H:%M}"
    if attempts >= ATTEMPTS:
        return False, (f"the {slot:%H:%M} slot has had {attempts} run(s) that wrote no ledger "
                       f"entry; waiting for the next slot")
    return True, f"the {slot:%Y-%m-%d %H:%M} slot has no run yet"


def main(argv=None):
    import argparse

    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["due", "slot"])
    ap.add_argument("--runs", default="data/ledger/runs.yaml")
    ap.add_argument("--attempts", type=int, default=0)
    ap.add_argument("--now")
    a = ap.parse_args(argv)

    now = parse(a.now) or datetime.datetime.now(UTC)
    if a.command == "slot":
        print(latest_slot(now).strftime("%Y-%m-%dT%H:%M:%SZ"))
        return 0
    p = pathlib.Path(a.runs)
    doc = yaml.safe_load(p.read_text()) if p.exists() else None
    ok, why = due(now, (doc or {}).get("runs") or [], a.attempts)
    print(f"{'due' if ok else 'not due'}: {why}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"due={'yes' if ok else 'no'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
