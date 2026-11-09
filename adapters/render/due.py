#!/usr/bin/env python3
"""When a rendered page is worth rendering again: on the days its next chapter is due.

WHY THIS EXISTS. Every rendered page was re-rendered on a fixed rotation, each one between four and
seven days after the last, on the reasoning that a chapter a render misses is picked up by the
platform's feed. pixivコミック and マンガワン have no feed we read: the rendered page is the only
route to their chapters, so a chapter there waited up to a week. Between September and November
30 of their chapters reached Updates two days or more after they were published, in a weekly
pattern that was the rotation and not the platforms.

WHAT A PAGE IS DUE ON, strongest evidence first, the order `adapters/schedule.py` sets out for the
feed routes:

  announced   the page states its next update (`次回更新`), and that day has come
  stated      the page states its rhythm (`毎月第3金曜`), and the rhythm puts an update here
  observed    the dates we hold fall on one weekday, or on one day of the month, or at a steady
              interval, and the next one is here

The observed rhythms are the common case and they are regular. Of the 34 pixivコミック and マンガワン
works with three chapters or more since June, 13 published on one weekday and 14 on one day of the
month (pixiv has two clusters, the 8th and the 28th); the other seven are near one of the two.

A DUE PAGE IS LOOKED AT FOR `GRACE_DAYS` MORE DAYS, because a release can land after the run on its
day or slip by one. A rhythm that has missed `GIVE_UP_PERIODS` periods has stopped meaning anything,
and the page falls back to its floor.

THE FLOOR IS WHAT MAKES "CAUGHT EVENTUALLY" A BOUND. A page nothing makes due is still rendered once
its copy is older than `FLOOR_ACTIVE` days, for a recent work whose rhythm we cannot read, or
`FLOOR_QUIET` days for the rest: a rhythm can change and a dormant work can revive.

A PREDICTION DECIDES WHEN WE LOOK AND NOTHING ELSE. It is never shown to a reader, and it is never a
date anything is filed under.
"""
import datetime
import pathlib
import statistics
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import schedule_text  # noqa: E402

#: The due day and this many days after it.
GRACE_DAYS = 2
#: How far back a rhythm is read from. Older chapters describe a schedule the work may have left.
RECENT_DAYS = 183
#: The fewest dates a rhythm is read from. Two dates are one gap, which is not a rhythm.
MIN_DATES = 3
#: How many periods past the latest chapter a rhythm is still believed.
GIVE_UP_PERIODS = 3
#: A work with a chapter this recent is active.
ACTIVE_DAYS = 60
FLOOR_ACTIVE = 7
FLOOR_QUIET = 14
#: The age a due page's copy may have: a copy from today's run stands, yesterday's does not.
DUE_AGE = 0.5
#: Share of recent dates that must fall on one day of the month for that day to be the rhythm.
MONTHDAY_SHARE = 0.75


def _date(v):
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def rhythm(dates, today):
    """The rhythm the dates keep, or None.

    `("weekday", w, step, span)`: every recent date is weekday `w`, the shortest gap is `step`
    days, a whole number of weeks, and the longest is `span`. `("monthday", d, 30, 31)`: at least
    three quarters fall on day `d`. `("interval", m, m, span)`: neither, and the median gap is `m`.
    `span` is the period a rhythm is given up against.
    """
    ds = sorted({d for d in map(_date, dates) if d})
    recent = [d for d in ds if (today - d).days <= RECENT_DAYS]
    if len(recent) < MIN_DATES:
        return _resumed_slot(ds, today)
    gaps = [(b - a).days for a, b in zip(recent, recent[1:])]
    if len({d.weekday() for d in recent}) == 1:
        step = max(7, min(gaps) // 7 * 7)
        return ("weekday", recent[0].weekday(), step, max(gaps))
    day, n = Counter(d.day for d in recent).most_common(1)[0]
    if n / len(recent) >= MONTHDAY_SHARE:
        return ("monthday", day, 30, 31)
    m = statistics.median(gaps)
    return ("interval", int(m), int(m), max(gaps)) if m >= 1 else None


def _resumed_slot(ds, today):
    """A day-of-the-month slot kept across a break, for a work that is active again.

    A DAY OF THE MONTH IS THE PLATFORM'S SLOT, AND IT OUTLASTS A HIATUS. 陰キャギャルでもイキがりたい！
    published on the 8th in November and December 2023, came back on 8 September 2026, and its
    October chapter was on the 8th again; with one recent date there was no rhythm to read and the
    chapter waited six days. A weekday is not read this way, because nothing has shown it survives.
    """
    if len(ds) < MIN_DATES or (today - ds[-1]).days > ACTIVE_DAYS:
        return None
    day, n = Counter(d.day for d in ds).most_common(1)[0]
    return ("monthday", day, 30, 31) if n / len(ds) >= MONTHDAY_SHARE else None


def _month_day(year, month, day):
    """`day` of the month, or its last day where the month is shorter."""
    for d in (day, 30, 29, 28):
        try:
            return datetime.date(year, month, min(day, d))
        except ValueError:
            continue
    return None


def _observed(rh, latest, until):
    """The dates the rhythm puts a chapter on, after `latest` and up to `until`."""
    kind, key, step = rh[:3]
    if kind == "weekday":
        c = latest + datetime.timedelta(days=step)
        while c <= until:
            yield c
            c += datetime.timedelta(days=7)
    elif kind == "monthday":
        y, mth = latest.year, latest.month
        while True:
            mth += 1
            if mth > 12:
                y, mth = y + 1, 1
            c = _month_day(y, mth, key)
            if c is None or c > until:
                return
            yield c
    else:
        c = latest + datetime.timedelta(days=step)
        while c <= until:
            yield c
            c += datetime.timedelta(days=step)


def _stated(cad, latest, until):
    c = schedule_text.next_after(cad, latest.isoformat())
    while c and _date(c) <= until:
        yield _date(c)
        c = schedule_text.next_after(cad, c)


def due(dates, stated, today):
    """Why this page is due today, in words, or None.

    `dates` are the chapter dates we hold for the work on this platform, future ones included where
    a platform dates a chapter by the day it becomes free. `stated` is the page's own
    `stated_schedule`: `next_update` and `cadence`, either or both.
    """
    stated = stated or {}
    held = [d for d in map(_date, dates or []) if d]
    latest = max(held) if held else None
    nu = _date(stated.get("next_update"))
    if nu and (latest is None or nu > latest) and nu <= today <= nu + datetime.timedelta(
            days=GRACE_DAYS):
        return f"announced: the page said {nu}"
    if latest is None:
        return None
    window = datetime.timedelta(days=GRACE_DAYS)
    cad = stated.get("cadence")
    # ONLY A CADENCE THAT PINS A DAY DECIDES. マガポケ states 毎月9日前後 and 隔週火曜, which name a
    # span and no day in it; those fall through to the dates we hold, as a silent page would.
    if cad and schedule_text.next_after(cad, latest.isoformat()):
        period = 31 if schedule_text.period(cad) == "month" else 7
        until = min(today, latest + datetime.timedelta(days=period * GIVE_UP_PERIODS))
        for c in _stated(cad, latest, until):
            if c <= today <= c + window:
                return f"stated: the page states {cad}, which put one on {c}"
        return None
    rh = rhythm(held, today)
    if not rh:
        return None
    # GIVEN UP AGAINST THE LONGEST GAP, not the step. 壊していいよ、すいかちゃん went from weekly to
    # four-weekly, and three weeks from its last chapter the weekly rhythm was abandoned a week
    # before the next one came.
    until = min(today, latest + datetime.timedelta(days=rh[3] * GIVE_UP_PERIODS))
    for c in _observed(rh, latest, until):
        if c <= today <= c + window:
            kind = {"weekday": "the same weekday", "monthday": "the same day of the month",
                    "interval": f"about every {rh[2]} days"}[rh[0]]
            return f"observed: its chapters fall on {kind}, which put one on {c}"
    return None


def age_limit(dates, stated, today):
    """`(days, reason)`: how old a copy of this page may be before it is rendered again.

    A due page may be no older than today's run. Any other takes its floor, which the caller
    staggers so that pages rendered together do not all come due together.
    """
    why = due(dates, stated, today)
    if why:
        return DUE_AGE, why
    held = [d for d in map(_date, dates or []) if d]
    latest = max(held) if held else None
    if latest and (today - latest).days <= ACTIVE_DAYS and not rhythm(held, today):
        return FLOOR_ACTIVE, f"floor: active, no rhythm to read, every {FLOOR_ACTIVE} days"
    return FLOOR_QUIET, f"floor: every {FLOOR_QUIET} days"


# ── THE DATES WE HOLD, KEPT BETWEEN RUNS ─────────────────────────────────────────────────────────
#
# A RENDERED PAGE SHOWS A WINDOW, NOT A HISTORY. pixivコミック draws a work's first chapter and its
# latest free ones, so a capture of 酒と鬼は二合まで holds two dates, three years apart, and no
# rhythm can be read from it. Each run's capture replaces the last, so the dates a rhythm needs
# exist only across runs, and this ledger is where they are kept. It was seeded on 2026-11-09 from
# every committed revision of the rendered captures, 481 of them.
HISTORY = pathlib.Path(__file__).resolve().parents[2] / "data" / "ledger" / "rendered-dates.yaml"


def load_history(path=HISTORY):
    """`{url: set of ISO dates}`, empty where the ledger does not exist yet."""
    import yaml
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    doc = yaml.safe_load(p.read_text()) or {}
    return {u: {str(d)[:10] for d in ds or []} for u, ds in (doc.get("dates") or {}).items()}


def remember(history, url, dates):
    """Add the dates a read of `url` gave. Nothing is ever removed: a date a page has stopped
    showing is still the day a chapter came out."""
    got = {str(d)[:10] for d in dates or [] if _date(d)}
    if url and got:
        history.setdefault(url, set()).update(got)


def save_history(history, path=HISTORY):
    import json
    L = ["# The chapter dates each rendered page has shown, across every run that read it.",
         "#",
         "# Written by adapters/render/releases.py, read by adapters/render/due.py to tell when a",
         "# page's next chapter is due. A rendered page shows a window of its chapters and not its",
         "# history, so the rhythm a work keeps exists only across runs. Seeded on 2026-11-09 from",
         "# every committed revision of data/source/webpages/rendered-*.yaml.",
         "source: derived", "role: rendered-chapter-dates", "dates:"]
    for u in sorted(history):
        L.append(f"  {json.dumps(u)}: [{', '.join(sorted(history[u]))}]")
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text("\n".join(L) + "\n")
