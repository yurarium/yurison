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
# a schedule. The measure that separates them is how many works put MORE THAN ONE instalment on the
# day. On a schedule almost none do; on an import most do, because most works arrive with a back
# catalogue.
#
# Measured: 一迅プラス's 2025-08-08 has 155 works and 58% of them multiple, コミックDAYS's 2021-06-09
# has 8 works and 88%. An ordinary busy day on コミックDAYS, 2026-05-17, has 6 works and 17%, and a
# weekly slot has none at all.
#
# A median was tried and is wrong. Half of 一迅プラス's works contributed a chapter or two to the
# migration, so the median there is 3, and a threshold high enough to exclude an ordinary day also
# excluded the largest migration in the data. The straggler is exactly what the platform-wide rule
# exists to catch: ハロー、メランコリック! ended in 2021 and has one chapter on 2025-08-08, and that
# one chapter was setting the work's latest.
SPREAD = 4
MULTI_SHARE = 0.5


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


#: An instalment's position in its run, where the title states one: 第12話, 【第6話】, track14, #27.
#: Full-width digits are read as digits. A title that states none gives None, and None never counts
#: as continuing anything. 第N巻 is a volume and is not read: カドコミ's コミックス第2巻発売記念イラスト
#: would otherwise have continued a run of one.
NUMBER = re.compile(r"第\s*([0-9０-９]+)\s*話|(?:track|＃|#)\s*([0-9０-９]+)", re.I)

#: The most instalments one day's publishing brings. One is the rule and two is a double update or a
#: launch; ichicomi's 2026-04-09 brought ささやくように恋を唄う 第60話 to 第62話 after nothing since
#: November, which is the platform catching up a run published elsewhere and not a day's publishing.
DAY = 2


def number(title):
    """An instalment's position in its run, where its title states one, else None. See NUMBER."""
    return _number(title)


def _number(title):
    m = NUMBER.search(str(title or ""))
    if not m:
        return None
    return int((m.group(1) or m.group(2)).translate(str.maketrans("０１２３４５６７８９", "0123456789")))


def continues(work, date):
    """Whether everything this work put on `date` carries on from a run the source already held.

    THE EVIDENCE AN IMPORT CANNOT FAKE. A back catalogue arrives from the start of the run: the
    work's early instalments, all on the one day. A publication is the next instalment after the
    ones the source already dated earlier. マガポケ's 2026-10-08 was an ordinary Thursday that
    `platform_wide` read as an import, four works with two of them posting two chapters, and
    アイ・ヘイ・チュー's 【第6話】 on it followed the 第1話 to 第5話 dated June to September. Its newest
    chapter read as September and the work was reported overdue on a schedule it had kept.

    True only where the work has numbered instalments dated before `date` in this source, every
    instalment on `date` is numbered past all of them, and the day brings no more than `DAY` of them.
    A title with no number, a day with nothing before it, or a run of three or more answers False,
    which leaves the work to the tests as they stood.
    """
    before, on = [], []
    for c in (work.get("chapters") or []):
        if not (isinstance(c, dict) and c.get("updated")):
            continue
        d = str(c["updated"])[:10]
        if d < date:
            before.append(_number(c.get("title")))
        elif d == date:
            on.append(_number(c.get("title")))
    earlier = [n for n in before if n is not None]
    return (bool(earlier and on) and None not in on and len(set(on)) <= DAY
            and min(on) > max(earlier))


#: The share of a source's works one day must carry to be the day the source loaded them.
MIGRATION_SHARE = 0.25


def migrations(works):
    """The dates most of a source's works share, which is the day it loaded them.

    A 第1話 ON SUCH A DAY IS PART OF THE LOAD, not a launch: 一迅プラス's 2025-08-08 carries 134 of
    its works, and ハロー、メランコリック！'s lone 第1話 among them was excused as a launch for a
    day. Keyed on scale rather than on whether some work loaded a back catalogue that day, because
    カドコミ puts five to eight chapters of a work up at once in its ordinary course: its
    2026-09-28 holds three such works among nine, and a series launching beside them is a launch.
    """
    ws = [w for w in works or [] if isinstance(w, dict)]
    days = collections.Counter(d for w in ws for d in _chapters_per_date(w))
    floor = max(SPREAD, MIGRATION_SHARE * len(ws))
    return {d for d, n in days.items() if n >= floor}


def launches(work, date):
    """Whether this work's first day in the source is `date`, starting at its first instalment.

    THE OTHER HALF OF `continues`, from the same Thursday. ぎるてぃらいぶらり launched on マガポケ
    on 2026-10-08 with 第1話 and 第2話, the launch 百合ナビ announced, and the platform-wide test read
    that day as an import because three other works posted on it too. A launch is the start of a
    run, numbered from 1, a chapter or two at most: an import brings a back catalogue, which is
    longer, or which starts somewhere other than 1. True only where nothing is dated before
    `date` in this source, every instalment on it is numbered, the lowest is 1, and there are no
    more than `DAY`.
    """
    before, on = False, []
    for c in (work.get("chapters") or []):
        if not (isinstance(c, dict) and c.get("updated")):
            continue
        d = str(c["updated"])[:10]
        if d < date:
            before = True
        elif d == date:
            on.append(_number(c.get("title")))
    return (not before and bool(on) and None not in on and min(on) == 1
            and len(set(on)) <= DAY)


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
        if sum(1 for n in counts if n >= 2) / len(counts) >= MULTI_SHARE:
            out.add(d)
    return out


def stamps(works):
    """{(work_title, date)} for every date in this source that reads as an import.

    Both shapes reach the same answer, so a work caught by either is caught. A platform-wide date
    is a stamp for every work sitting on it, including the work that only has two chapters there:
    the date says when the source imported, and it says that whatever a given work contributed.

    EXCEPT A WORK WHOSE CHAPTERS THAT DAY CONTINUE ITS RUN (`continues`) OR START IT (`launches`). The platform-wide test
    infers an import from the shape of a day, and an ordinary busy day can have that shape; the
    work's own numbering is direct evidence and outranks it. The per-work test is not excused,
    because a late load of a work's remaining chapters continues its numbering too and brings five
    at once.
    """
    wide = platform_wide(works)
    bulk = migrations(works)
    out = set()
    for w in works:
        if not isinstance(w, dict):
            continue
        title = w.get("work_title")
        for d, n in _chapters_per_date(w).items():
            if n >= RUN or (d in wide and not continues(w, d)
                            and not (launches(w, d) and d not in bulk)):
                out.add((title, d))
    return out
