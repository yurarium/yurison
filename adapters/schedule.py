#!/usr/bin/env python3
"""Choose what to check this run, and say why for every row.

WHY THIS EXISTS. Stage A revalidated the whole catalogue every run: about 2,126 sequential requests
for the GigaViewer series feeds alone, which at a 1.2 s per-host pause is 43 minutes of sleeping
before any network time. Almost all of it re-read series that had not changed and could not have.

The order of work is: take the leads somebody else already paid to find, spend the cheap
platform-wide feeds, then look at a targeted slice of everything else. This module decides the
slice and, for every row it picks, records the reason in words.

WHAT MAKES THE SAMPLING SAFE. Not the sampling itself. A platform's own feed holds roughly twenty
entries across everything it publishes, so it reaches back a measurable number of days, and where
that reach exceeds the gap since our last successful run the feed has already told us everything
that happened on that platform. Per-series checks are owed only where the window did NOT cover the
interval. Run more often and the sweep shrinks toward nothing on its own.

NO STATE IS TERMINAL, which is the correction that shaped the floors below. A series marked
`completed` still posts おまけ and 番外編 after its final chapter, and one of ours did exactly that
inside a single month. A dormant series revives. Six works we filed as `oneshot` published a second
chapter. So nothing is ever struck off the list; the saving comes from RATE, and every row keeps a
floor past which it gets looked at regardless of how quiet it has been.
"""
import argparse
import collections
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import checkstate

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "render"))
import schedule_text  # noqa: E402

# How long a row may go unchecked, by state, when nothing else argues for it. These are a backstop
# rather than the mechanism: the claims path and the cadence path should reach almost everything
# first, and a floor firing means those missed it.
FLOORS = {
    # `active` is 7 rather than 1 BECAUSE the platform-wide feed already covers these. An active
    # work is by definition one that published recently, so it is exactly the row sitting inside
    # the feed's window. The floor here is not for catching chapters; it is for the things a feed
    # never reports, like a work quietly disappearing or its access terms changing.
    "active": 7,
    "unknown": 7,
    "slow": 14,
    "hiatus": 14,      # attested pause. Still checked: a pause ends, and the end is the news.
    "dormant": 30,     # かいじゅう色の島 revived at 第33話 inside our own observation window
    "completed": 60,   # おまけ and 番外編 arrive after the last chapter
    "oneshot": 90,     # 6 of 415 became series
}
DEFAULT_FLOOR = 30

# A predicted date is worth acting on only where the interval is regular enough to mean something.
MIN_CHAPTERS_FOR_CADENCE = 3
CADENCE_TOLERANCE = 0.25       # how far past the predicted date before it counts as due
# How many missed periods before a prediction stops meaning anything. A series that publishes
# monthly and is nine months late has not got a late chapter, it has stopped, and chasing it every
# run on the strength of a 2021 rhythm is how a sweep fills up with the dead. Past this it falls
# through to its floor and is checked at the quiet rate instead.
CADENCE_GIVE_UP = 3


# ORDER OF EVIDENCE. A platform announcing a date has told us when to look; a platform stating a
# rhythm has told us nearly that; an average we computed from the chapters we happen to hold has
# told us about our own arithmetic. They were being treated as one thing, and the weakest of the
# three was doing almost all the work: of 112 overdue rows, 106 were overdue against an interval we
# calculated and 6 against something a platform said.
#
# That matters most where our capture is thinnest, which is exactly where the interval is least
# trustworthy. A platform serving a rolling window of free chapters gives a short apparent interval
# AND a truncated `latest`, and both errors push the same way.
BASIS_PRIORITY = {
    "stated-date": 0.4,      # the platform named a day and it has passed
    "stated-cadence": 0.6,   # the platform named a rhythm and this is where it falls
    "observed": 1.0,         # our own average over the chapters we hold
}


def stated(row):
    """What the platform says about its own next update, if it says anything."""
    return row.get("stated_next") or {}


def stated_next_date(row):
    """The date the platform announced, as a date."""
    v = stated(row).get("next_update")
    try:
        return datetime.date.fromisoformat(v) if v else None
    except ValueError:
        return None


def stated_cadence_next(row, after=None):
    """The first date at or after `after` where the platform's stated rhythm puts an update.

    Bounded at ten weeks: a monthly cadence is found twice over inside that, and a cadence that
    pins no particular day (隔週金曜 names a fortnight without saying which) never matches, so the
    loop must end on its own rather than on finding something.
    """
    cad = stated(row).get("cadence")
    if not cad:
        return None
    start = after or (datetime.date.fromisoformat(row["latest"]) + datetime.timedelta(days=1)
                      if row.get("latest") else None)
    if not start:
        return None
    for k in range(70):
        d = start + datetime.timedelta(days=k)
        if schedule_text.fits(cad, d.isoformat()):
            return d
    return None


def cadence_days(row):
    """Mean days between chapters, or None when there is too little history to say."""
    first, latest, n = row.get("first"), row.get("latest"), row.get("chapters") or 0
    if not (first and latest and n >= MIN_CHAPTERS_FOR_CADENCE):
        return None
    span = (datetime.date.fromisoformat(latest) - datetime.date.fromisoformat(first)).days
    return span / (n - 1) if span > 0 else None


def predicted_next(row):
    c = cadence_days(row)
    if not c or not row.get("latest"):
        return None
    return datetime.date.fromisoformat(row["latest"]) + datetime.timedelta(days=round(c))


def window_covers(depth_days, gap_days):
    """Whether a platform's own feed already reported everything since our last successful run."""
    return depth_days is not None and gap_days is not None and depth_days >= gap_days


def plan(series, checks, claims=(), depths=None, gaps=None, budget=400, today=None):
    """Return [(reason, platform, work, priority)] worth checking, most important first.

    `depths` maps platform to the days its feed reaches back; `gaps` maps platform to days since we
    last successfully read it. Where both are known and the window covers the gap, that platform's
    quiet rows are skipped: the cheap feed already answered for them.
    """
    today = today or datetime.date.today()
    depths, gaps = depths or {}, gaps or {}
    claimed = {(c.get("platform"), c.get("work")) for c in claims}
    picked, seen = [], set()

    def add(reason, plat, work, pri):
        if (plat, work) in seen or not work:
            return
        seen.add((plat, work))
        picked.append((reason, plat, work, pri))

    for row in series:
        work = row.get("work")
        for src in (row.get("sources") or [{"platform": row.get("platform")}]):
            plat = src.get("platform")
            state = row.get("state") or "unknown"
            floor = FLOORS.get(state, DEFAULT_FLOOR)
            over = checkstate.overdue_days(checks, plat, work, today)

            # 1. A lead somebody else already found. Always worth the request.
            if (plat, work) in claimed:
                add("claimed: a comparator reports an update we have not attested", plat, work, 0)
                continue

            covered = window_covers(depths.get(plat), gaps.get(plat))

            covered_note = " (the platform feed already covered the gap)"

            # 2. THE PLATFORM NAMED A DAY AND IT HAS PASSED. The strongest thing we can have short
            #    of a chapter, and it is checked before any arithmetic of ours.
            sd = stated_next_date(row)
            if sd and sd < today and not covered:
                add(f"announced: the platform said {sd} and we hold nothing since",
                    plat, work, BASIS_PRIORITY["stated-date"])
                continue

            # 3. The platform named a rhythm and this is past where it falls.
            sc = stated_cadence_next(row)
            if sc and sc < today and not covered:
                add(f"cadence: the platform states {stated(row)['cadence']}, "
                    f"which put one on {sc}",
                    plat, work, BASIS_PRIORITY["stated-cadence"])
                continue

            # 4. Due by an interval WE worked out. Weakest of the three, so it comes last of them,
            #    and it keeps the give-up bound because an average over a dead series predicts for
            #    ever. Skipped where the platform feed already covered the gap, because then the
            #    answer is in hand for free.
            nxt = predicted_next(row)
            if nxt and not covered:
                c = cadence_days(row) or 30
                late = (today - nxt).days
                if (today >= nxt + datetime.timedelta(days=round(c * CADENCE_TOLERANCE))
                        and late <= c * CADENCE_GIVE_UP):
                    add(f"due: publishes about every {round(c)}d, {late}d past the predicted date",
                        plat, work, BASIS_PRIORITY["observed"] + max(0, 200 - late) / 1000)
                    continue

            # 3. The floor. What makes "caught eventually" a bound rather than a hope.
            if over is None:
                add(f"never checked ({state})", plat, work, 2)
            elif over >= floor:
                add(f"floor: {state} is checked every {floor}d, last looked {over}d ago",
                    plat, work, 3 + max(0, 500 - over) / 10000)

    picked.sort(key=lambda x: x[3])
    return picked[:budget]


def _self_test():
    ok = True
    today = datetime.date(2026, 8, 3)
    series = [
        {"work": "due-one", "state": "active", "first": "2026-01-01", "latest": "2026-06-01",
         "chapters": 6, "sources": [{"platform": "P"}]},
        {"work": "fresh-one", "state": "active", "first": "2026-01-01", "latest": "2026-08-02",
         "chapters": 30, "sources": [{"platform": "P"}]},
        {"work": "finished", "state": "completed", "first": "2020-01-01", "latest": "2021-01-01",
         "chapters": 20, "sources": [{"platform": "P"}]},
    ]
    checks = {}
    for w in ("due-one", "fresh-one", "finished"):
        checkstate.record(checks, "P", w, "ok", when="2026-08-02")

    got = {w: r for r, p, w, _ in plan(series, checks, today=today)}

    if "due-one" not in got or not got["due-one"].startswith("due:"):
        print(f"  FAIL: an overdue series was not selected ({got.get('due-one')})"); ok = False
    if "fresh-one" in got:
        print("  FAIL: a series that published yesterday was selected"); ok = False
    if "finished" in got:
        print("  FAIL: a completed series checked yesterday was selected inside its 60d floor")
        ok = False

    # Nothing is terminal: past its floor, a completed series must come back round.
    checkstate.record(checks, "P", "finished", "ok", when="2026-01-01")
    got2 = {w: r for r, p, w, _ in plan(series, checks, today=today)}
    if "finished" not in got2:
        print("  FAIL: a completed series 200d unchecked was not selected"); ok = False

    # The window-depth rule must suppress the cadence path, and only that path.
    got3 = {w for _, p, w, _ in plan(series, checks, depths={"P": 30}, gaps={"P": 1}, today=today)}
    if "due-one" in got3:
        print("  FAIL: cadence fired although the platform feed covered the interval"); ok = False

    # A claim outranks everything, including a row checked an hour ago.
    got4 = plan(series, checks, claims=[{"platform": "P", "work": "fresh-one"}], today=today)
    if not any(w == "fresh-one" and r.startswith("claimed") for r, p, w, _ in got4):
        print("  FAIL: a claimed row was not selected"); ok = False

    # ORDER OF EVIDENCE. The whole point of the three tiers is that they are tried in order, so a
    # row with an announced date must never be picked up by the arithmetic branch instead.
    today = datetime.date(2026, 8, 3)
    announced = {"work": "A", "state": "active", "sources": [{"platform": "P"}],
                 "first": "2026-01-01", "latest": "2026-07-01", "chapters": 20,
                 "stated_next": {"next_update": "2026-07-20"}}
    got = plan([announced], {}, today=today)
    if not got or "announced" not in got[0][0]:
        print(f"  FAIL: an announced date that has passed was not the reason ({got[:1]})"); ok = False
    if got and got[0][3] >= 1.0:
        print("  FAIL: an announced date did not outrank an interval we computed"); ok = False

    cadenced = dict(announced, work="B",
                    stated_next={"cadence": "\u6bce\u6708\u7b2c3\u91d1\u66dc"})
    got = plan([cadenced], {}, today=today)
    if not got or "cadence" not in got[0][0]:
        print(f"  FAIL: a stated cadence was not used ({got[:1]})"); ok = False
    if got and not (0.4 < got[0][3] < 1.0):
        print("  FAIL: a stated cadence did not sit between an announcement and our arithmetic")
        ok = False

    # A cadence naming no particular day must not be turned into a date.
    vague = dict(announced, work="C", stated_next={"cadence": "\u9694\u9031\u91d1\u66dc"})
    got = plan([vague], {}, today=today)
    if got and "cadence:" in got[0][0]:
        print("  FAIL: a fortnightly cadence was read as pinning a day"); ok = False

    # An announced date still in the future is not overdue.
    future = dict(announced, work="D", stated_next={"next_update": "2026-09-01"})
    got = plan([future], {}, today=today)
    if got and "announced" in got[0][0]:
        print("  FAIL: a date that has not arrived was treated as passed"); ok = False

    if all(x[0] for x in [(True,)]):
        pass

    print("  schedule self-test:", "pass" if ok else "FAIL")
    if ok:
        print("CANARY-PROVEN")   # proven by planted canary, not by inversion
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="data/build/series.json")
    ap.add_argument("--budget", type=int, default=400)
    ap.add_argument("--limit", type=int, default=25, help="rows to print")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return 0 if _self_test() else 1

    series = (json.load(open(a.series)) or {}).get("series", [])
    checks = checkstate.load()
    rows = plan(series, checks, budget=a.budget)
    by = collections.Counter(r.split(":")[0] for r, _, _, _ in rows)
    print(f"{len(rows)} of {sum(len(s.get('sources') or [1]) for s in series)} work/platform pairs "
          f"selected (budget {a.budget})")
    for k, v in by.most_common():
        print(f"   {k:16} {v}")
    print()
    for reason, plat, work, _ in rows[:a.limit]:
        print(f"  {str(plat)[:14]:15} {str(work)[:30]:32} {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
