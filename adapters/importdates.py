#!/usr/bin/env python3
"""Which chapter dates are a platform importing a back catalogue, and not a publication.

WHY THIS EXISTS. 一迅プラス stamped 1972 chapters across 152 series with 2025-08-08. ゆるゆり, which
began in 2008, carries 224 of its 236 chapters on that day. The date is real, and it is the honest
record of what that source says, so REQUIREMENTS §4 keeps it. What it is not is the day those
chapters were published, and 34 works were reading `active` or `slow` on exactly such a date.

WHAT THE SIGNATURE IS. §4 already describes it: a shared timestamp is unremarkable when it is a
scheduled batch, many works with roughly one entry each, and suspect when one work contributes
several entries at an identical instant. That catches a series imported on its own. It misses a
whole platform migrating at once, because there the giveaway is the opposite shape, one date
carrying an implausible share of everything the source holds. Both are looked for here.

WHAT THIS DOES NOT DO. Decide anything. It marks dates as unfit to headline a series, and what to
show instead is build.py's to work out from every source it holds. A stamp on the only date we have
is not a licence to invent a better one.
"""
import collections
import re

# One work contributing this many CHAPTERS at one timestamp. Chapters, not entries: GigaViewer
# splits an instalment into parts published together, so 第23話 わたしのままで(1)(2)(3) is three
# entries and one release. Counting entries made an ordinary monthly update look like an import and
# filed きみが死ぬまで恋をしたい, which updates every month, as dormant.
#
# §4's threshold is 3, measured on a feed whose entries are whole chapters. Five here, because a
# series imported on its own arrives with its back catalogue rather than with three instalments,
# and because the platform-wide rule below catches migrations regardless of what any one work
# contributed.
RUN = 5

# Trailing part markers on an instalment split across entries: (1), （2）, [3].
PART = re.compile(r"[\s　]*[(（\[]\s*\d+\s*[)）\]][\s　]*$")

# A whole source migrating. Share of the catalogue is the obvious measure and it is the wrong one:
# a platform with four weekly slots puts a quarter of everything it holds on each of them, which is
# a schedule. §4 already names the measure that works, so this uses it at the other scale. On a
# schedule each work contributes about one chapter; on an import it contributes its back catalogue.
# 一迅プラス's 2025-08-08 is 13 chapters per series across 152 of them, and コミックDAYS's
# 2021-06-09 is 45 across 8. A weekly slot is 1.
#
# The median, not the mean: one 224-chapter series landing on a day when a hundred others publish
# once would drag a mean over the line and misread an ordinary Friday as a migration.
SPREAD = 4


def _stem(title):
    """An instalment's name with its part marker removed, so its parts count once."""
    return PART.sub("", str(title or "")).strip()


def _dates(work):
    return [str(c["updated"])[:10] for c in (work.get("chapters") or [])
            if isinstance(c, dict) and c.get("updated")]


def _chapters_per_date(work):
    """{date: how many distinct instalments this work put there}."""
    seen = collections.defaultdict(set)
    for c in (work.get("chapters") or []):
        if isinstance(c, dict) and c.get("updated"):
            d = str(c["updated"])[:10]
            seen[d].add(_stem(c.get("title")) or c.get("url") or len(seen[d]))
    return {d: len(v) for d, v in seen.items()}


def platform_wide(works):
    """Dates on which this source appears to have imported much of its catalogue at once."""
    by_date = collections.defaultdict(list)
    for w in works:
        if not isinstance(w, dict):
            continue
        for d, n in _chapters_per_date(w).items():
            by_date[d].append(n)
    out = set()
    for d, counts in by_date.items():
        if len(counts) < SPREAD:
            continue
        counts.sort()
        median = counts[len(counts) // 2]
        if median >= RUN:
            out.add(d)
    return out


def stamps(works):
    """{(work_title, date)} for every date in this source that reads as an import.

    Both shapes reach the same answer, so a work caught by either is caught. A platform-wide date
    is a stamp for every work sitting on it, including the work that only has two chapters there:
    the date says when the source imported, and it says that whatever a given work contributed.
    """
    wide = platform_wide(works)
    out = set()
    for w in works:
        if not isinstance(w, dict):
            continue
        title = w.get("work_title")
        for d, n in _chapters_per_date(w).items():
            if n >= RUN or d in wide:
                out.add((title, d))
    return out
