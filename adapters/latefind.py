#!/usr/bin/env python3
"""Whether a chapter reached us after an update that should already have had it.

THE RULE, decided by the project owner on 2026-11-09. A chapter is a late find when an update ran
on a day after the day it was published and before the day we first saw it. Found on a Monday, a
chapter from Saturday is late, because Sunday's run missed it; one from Sunday is not, because no
run fell between. A late find is listed under the day it was found, so a reader who reads Updates
down to where they stopped last time meets everything that arrived since.

IT REPLACES A MONTH RULE, which surfaced a chapter only when it was found in a later month than it
came out. 燕のあやかし画帳 came out on Friday 6 November, was found on Monday the 9th and was filed
under the Friday, below three days a reader had already read. Between September and November, 76
chapters of works we were already following arrived two days or more late, and the month rule
surfaced 21 rows in all.

MEASURED AGAINST OUR RUNS, NOT THE CALENDAR. A day with no run is a day nothing could have been
found, so a chapter is not late for a run that did not happen. On 11 October no update ran, and a
chapter from the 10th found on the 12th was found by the first run that could find it.

THE DAYS ARE JAPAN'S. Publication dates are the platforms' own, which are Japanese dates, so a run
is placed on the date it was in Japan: a run at 21:58 UTC on 5 November ran on the 6th.
"""
import datetime

JST = datetime.timezone(datetime.timedelta(hours=9))


def run_day(at):
    """The date in Japan of a run that ran at `at`, an ISO timestamp."""
    t = datetime.datetime.fromisoformat(str(at))
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    return t.astimezone(JST).date().isoformat()


def run_days(doc):
    """Every day an update ran, from the runs ledger: its kept `days` and its recent runs."""
    doc = doc or {}
    days = {str(d)[:10] for d in doc.get("days") or []}
    days |= {run_day(r["at"]) for r in doc.get("runs") or [] if r.get("at")}
    return days


def with_day(doc_days, at):
    """The kept days with this run's added, sorted. Never trimmed: a late find is decided from
    them, and a decision must not change as old runs leave the window the ledger keeps."""
    return sorted({str(d)[:10] for d in doc_days or []} | {run_day(at)})


def missed(pub, seen, days):
    """Whether an update ran after the day `pub` and before the day `seen`."""
    pub, seen = str(pub or "")[:10], str(seen or "")[:10]
    if not pub or not seen:
        return False
    return any(pub < d < seen for d in days)
