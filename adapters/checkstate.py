#!/usr/bin/env python3
"""When we last looked at each work, and what happened when we did.

WHY THIS EXISTS. Until now the database recorded `latest`, the last release we know about, and
nothing at all about when we last looked. Those are different facts, and conflating them makes two
things impossible.

  SCHEDULING. Checking a sample rather than everything only works if you know which rows are
  overdue for a look. Without a last-checked date there is no queue, only a guess.

  HONESTY. `latest: 2024-07-04` currently means either "we checked yesterday and there is still
  nothing newer" or "we have not looked since 2024". REQUIREMENTS §4 says absence is a state
  rather than a missing value, and this is the case that principle was written for.

WHAT A "RESULT" IS. One observation, not a conclusion. A single 404 during a deploy is not evidence
that a work is gone, so `gone` is never set by one look: `consecutive_failures` counts the run, and
a caller decides what a run means. The same applies to a move. A redirect is recorded when seen,
and what to do about it is a judgement made elsewhere with the comparators in view.

WHY YAML AND WHY COMMITTED. It has to survive between runs, and CI runs on a fresh checkout every
time, so it lives in the repository with the rest of the source data. It is small: one short row
per work and platform.
"""
import argparse
import datetime
import pathlib
import sys

import yaml

STORE = pathlib.Path(__file__).resolve().parents[1] / "data" / "state" / "checks.yaml"

# An outcome a caller may record. Deliberately few: this is what happened, not what it means.
RESULTS = ("ok",         # fetched, parsed, and the work is present
           "empty",      # fetched and parsed, and there is nothing new. A finding, not a failure.
           "missing",    # the source says this work is not there (404 or 410)
           "blocked",    # refused us specifically (401, 403, 429)
           "error",      # transient: 5xx, timeout, connection reset
           "moved")      # redirected somewhere we did not ask for


def _key(platform, work):
    return f"{platform}|{work}"


def load(path=STORE):
    if not pathlib.Path(path).exists():
        return {}
    return (yaml.safe_load(pathlib.Path(path).read_text()) or {}).get("checks") or {}


def save(checks, path=STORE):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(
        {"updated": datetime.date.today().isoformat(), "checks": checks},
        allow_unicode=True, sort_keys=True, width=100))


def record(checks, platform, work, result, when=None, final_url=None, note=None):
    """Note one observation. Returns the row, so a caller can read the failure run straight back."""
    if result not in RESULTS:
        raise ValueError(f"unknown result {result!r}; expected one of {RESULTS}")
    when = when or datetime.date.today().isoformat()
    row = checks.setdefault(_key(platform, work), {})
    row["last_checked"] = when
    row["result"] = result

    if result in ("ok", "empty"):
        row["last_reached"] = when
        row["fails"] = 0
        row.pop("note", None)
    else:
        row["fails"] = int(row.get("fails") or 0) + 1
        if note:
            row["note"] = note

    # A move is kept even after the work is reachable again, because the old URL staying dead is
    # the thing a reader would trip over.
    if result == "moved" and final_url:
        row["moved_to"] = final_url
    return row


def due(checks, platform, work, floor_days, today=None):
    """Whether this row is past its floor. A row never checked is always due."""
    row = checks.get(_key(platform, work))
    if not row or not row.get("last_checked"):
        return True
    today = today or datetime.date.today()
    last = datetime.date.fromisoformat(row["last_checked"])
    return (today - last).days >= floor_days


def overdue_days(checks, platform, work, today=None):
    """How long since we looked. None where we never have, which sorts first as 'most overdue'."""
    row = checks.get(_key(platform, work))
    if not row or not row.get("last_checked"):
        return None
    today = today or datetime.date.today()
    return (today - datetime.date.fromisoformat(row["last_checked"])).days


def summary(checks):
    from collections import Counter
    c = Counter(r.get("result") for r in checks.values())
    runs = [(k, r.get("fails")) for k, r in checks.items() if (r.get("fails") or 0) >= 3]
    return {"rows": len(checks), "by_result": dict(c),
            "failing_3_or_more": sorted(runs, key=lambda x: -x[1])[:20]}


def _self_test():
    """A ledger that cannot demonstrate it counts a run is not worth trusting with the decision."""
    ok = True
    c = {}
    record(c, "p", "w", "ok", when="2026-08-01")
    if not due(c, "p", "w", 1, datetime.date(2026, 8, 3)):
        print("  FAIL: a row 2 days old is not due at a 1-day floor"); ok = False
    if due(c, "p", "w", 30, datetime.date(2026, 8, 3)):
        print("  FAIL: a row 2 days old is due at a 30-day floor"); ok = False
    if not due(c, "p", "never-seen", 30):
        print("  FAIL: a row we have never checked is not due"); ok = False

    for _ in range(3):
        row = record(c, "p", "w", "missing", when="2026-08-03")
    if row["fails"] != 3:
        print(f"  FAIL: three misses counted as {row['fails']}"); ok = False
    if row.get("last_reached") != "2026-08-01":
        print("  FAIL: a failure moved last_reached"); ok = False
    row = record(c, "p", "w", "ok", when="2026-08-04")
    if row["fails"] != 0:
        print("  FAIL: success did not clear the failure run"); ok = False

    r2 = record(c, "p", "moved-one", "moved", final_url="https://new/x")
    record(c, "p", "moved-one", "ok")
    if r2.get("moved_to") != "https://new/x":
        print("  FAIL: recovery erased the move"); ok = False

    try:
        record(c, "p", "w", "nonsense"); print("  FAIL: bad result accepted"); ok = False
    except ValueError:
        pass
    print("  checkstate self-test:", "pass" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if _self_test() else 1)
    if a.summary:
        import json
        print(json.dumps(summary(load()), indent=1, ensure_ascii=False))
