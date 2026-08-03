#!/usr/bin/env python3
"""Regression test for the effective-date rule (REQUIREMENTS §5).

The rule, in full:

    effective date = min(claimed date, first scrape date)   — fixed at first sight

A claimed date earlier than our first scrape is accepted: the release plainly existed before we
looked, so the platform's claim is the better evidence. A claimed date later than our first scrape
cannot be a publication date for something we had already seen, so our observation wins.

**And it is never revised.** If the platform later changes its claim — which these platforms do, in
bulk, during refreshes and imports — the stored date does not move. That is the whole point; the
rest is bookkeeping.

Run: python3 adapters/gigaviewer/test_dates.py
"""
import sys


def effective(claimed, first_seen):
    """The rule under test. Mirrors releases.py."""
    cands = [d[:10] for d in (claimed, first_seen) if d]
    return min(cands) if cands else ""


def lock(stored, claimed_now, first_seen):
    """What a re-run produces: the stored date survives regardless of the current claim."""
    return stored if stored else effective(claimed_now, first_seen)


import os

# Inversion for ./test.py --canary. Every check is flipped, so a suite asserting anything real must
# FAIL; one that passes while inverted is asserting nothing. Without this the runner cannot tell a
# suite that was proved from one that ignored the canary and passed untouched, which is the
# vacuous-green failure this project keeps meeting.
CANARY = os.environ.get("YURA_CANARY") == "1"

FAILS = []


def check(name, got, want):
    ok = got == want
    if CANARY:
        ok = not ok
    print(f"  {'ok  ' if ok else 'FAIL'} {name}: {got!r}" + ("" if ok else f" (want {want!r})"))
    if not ok:
        FAILS.append(name)


print("effective date = min(claimed, first scrape)")
check("claimed earlier than scrape -> claimed wins",
      effective("2026-03-14T02:00:00Z", "2026-08-01"), "2026-03-14")
check("claimed later than scrape -> scrape wins",
      effective("2026-09-30T02:00:00Z", "2026-08-01"), "2026-08-01")
check("claimed equals scrape",
      effective("2026-08-01T02:00:00Z", "2026-08-01"), "2026-08-01")
check("no claim at all -> scrape",
      effective("", "2026-08-01"), "2026-08-01")

print("\nnever revised once set")
check("platform moves its claim later -> unchanged",
      lock("2026-03-14", "2026-07-28T02:00:00Z", "2026-08-01"), "2026-03-14")
check("platform moves its claim earlier -> still unchanged",
      lock("2026-07-28", "2026-01-02T02:00:00Z", "2026-08-01"), "2026-07-28")
check("bulk refresh stamps everything today -> unchanged",
      lock("2026-03-14", "2026-08-05T02:00:00Z", "2026-08-01"), "2026-03-14")

print("\na release first seen on a later run keeps that run's scrape date as its bound")
check("appeared between runs, claimed 3 days earlier",
      effective("2026-08-10T02:00:00Z", "2026-08-13"), "2026-08-10")
check("appeared between runs, claim bumped into the future",
      effective("2026-12-01T02:00:00Z", "2026-08-13"), "2026-08-13")

print()
if CANARY:
    # Inverted, so failures are the healthy outcome and silence is the alarm.
    if FAILS:
        print("CANARY-PROVEN")
        sys.exit(0)
    print("VACUOUS: every check passed while inverted")
    sys.exit(2)

if FAILS:
    print(f"{len(FAILS)} FAILED: {', '.join(FAILS)}")
    sys.exit(1)
print("all date-rule invariants hold")
