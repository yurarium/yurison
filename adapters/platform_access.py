#!/usr/bin/env python3
"""Whether each platform lets us read it, as a standing condition rather than one bad request.

WHY THIS EXISTS. From 2026-10-22 every comici site answered 403, first with a maintenance notice
and from about 2026-11-02 with a CloudFront page reading 「現在、一部の通信環境からのアクセスを制限して
おります」. The webpages adapter kept what it held and wrote nothing, which is right, and said so only
in its log. Nothing the build reads recorded that the platform had closed to us, so a listing
site's report of a chapter on one of those platforms sat as untraced work that no amount of looking
could finish, and a history frozen on 22 October was still allowed to argue that nothing had
appeared since.

WHAT IT RECORDS. One row per platform, by display name: the day the refusals began, the last day
we were refused, the last day we were let in, and what the refusal said. A platform is CLOSED when
it has refused us for at least CLOSED_AFTER days and has not let us in since. One refused run is a
bad moment and is not enough; three days of every page refused is a decision somebody made.

WHAT IT DOES NOT DO. It never retries, and it never says why a platform closed. It records what
happened to the requests we already make.
"""
import datetime
import pathlib

import yaml

STORE = pathlib.Path(__file__).resolve().parents[1] / "data" / "state" / "platform-access.yaml"

#: Days of unbroken refusal before a platform counts as closed to us.
CLOSED_AFTER = 3

#: The statuses that are a refusal of us, as distinct from a page that is missing or a server fault.
REFUSALS = (401, 403, 429)


def load(path=STORE):
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("platforms") or {}


def save(state, path=STORE, today=None):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# Written by adapters/platform_access.py; see its docstring.\n" + yaml.safe_dump(
        {"updated": str(today or datetime.date.today()), "platforms": state},
        allow_unicode=True, sort_keys=True, width=100), encoding="utf-8")


def record(state, platform, refused, when, note=None):
    """Note one run's outcome for a platform: refused (every page asked was refused) or let in.

    A run that was neither, some pages refused and some read or none asked at all, should not be
    recorded: it says nothing about whether the platform as a whole is open.
    """
    when = str(when)
    row = state.setdefault(platform, {})
    if refused:
        if not row.get("refused_since") or (row.get("last_reached") or "") >= row["refused_since"]:
            row["refused_since"] = when
        row["last_refused"] = when
        if note:
            row["note"] = note
    else:
        row["last_reached"] = when
        row.pop("refused_since", None)
        row.pop("note", None)
    return row


def closed(state, platform, today):
    """The row for a platform closed to us on `today`, or None where it is open or not known."""
    row = (state or {}).get(platform) or {}
    since = row.get("refused_since")
    if not since or (row.get("last_reached") or "") >= since:
        return None
    today = datetime.date.fromisoformat(str(today))
    if (today - datetime.date.fromisoformat(since)).days < CLOSED_AFTER:
        return None
    return row


def run_refused(statuses):
    """Whether one run's statuses for a platform add up to a refusal of the whole platform.

    Every page asked must have been refused. A single page read, or a single 404 or 5xx among the
    refusals, is a different condition, and an empty run asked nothing.
    """
    statuses = list(statuses)
    return bool(statuses) and all(s in REFUSALS for s in statuses)
