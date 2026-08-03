#!/usr/bin/env python3
"""The update schedule a platform prints on its own page.

WHY THIS EXISTS. GigaViewer states a work's rhythm and its next update date in words, and we were
inferring both from the gaps between chapters we happened to capture. Inferring what the source
says outright is bad enough on its own; here it was also wrong. マガポケ shows a rolling window of
currently-free chapters, so 平良深姉妹はどっちもヤんでる looked to have stopped in March while the
page said 無料話更新：毎月第3金曜 and 次回無料更新は8/21(金曜)予定です. A live series read as a dead
one, and the claim that it had updated on 2026-07-17 was held as untraceable when 17 July 2026 is
itself a third Friday.

WHAT IT IS AND IS NOT. A stated cadence is an assertion by the platform about its intentions. It
attests no particular chapter, so it can corroborate a report and can never stand in for one: a
work whose page says "next update 21 August" has not published anything on 21 August.

THE YEAR IS INFERRED. 次回無料更新は8/21 carries a month and a day only. The year is resolved against
the day the page was read, choosing the nearest reading that is not in the past, because a "next"
date by definition is not behind us. Where the page was read in December and promises 1/5, that is
January of the following year.
"""
import datetime
import re

# 無料話更新：毎月第3金曜 / 最新話更新：毎週木曜 / 隔週金曜
CADENCE = re.compile(r"(?:無料話更新|最新話更新|更新)[：:]\s*([毎隔][週月][^\s<（(]{0,8})")
# 次回無料更新は8/21(金曜)予定です
NEXT = re.compile(r"次回(?:無料)?更新は\s*(\d{1,2})[／/](\d{1,2})")

DOW = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}
NTH = {"第1": 1, "第２": 2, "第2": 2, "第３": 3, "第3": 3, "第４": 4, "第4": 4, "第１": 1}


def cadence(text):
    """The stated rhythm, verbatim, or None. Kept as the platform's own words."""
    m = CADENCE.search(text or "")
    return m.group(1) if m else None


def next_update(text, read_on):
    """The announced next update as a date, resolved against the day the page was read."""
    m = NEXT.search(text or "")
    if not m:
        return None
    mo, day = int(m.group(1)), int(m.group(2))
    read = datetime.date.fromisoformat(str(read_on)[:10])
    for year in (read.year, read.year + 1):
        try:
            d = datetime.date(year, mo, day)
        except ValueError:
            continue
        if d >= read:
            return d.isoformat()
    return None


def fits(cad, when):
    """Whether a date falls where a stated cadence says updates fall.

    Only the two forms that pin a date are answered: 毎週<day> and 毎月第n<day>. 隔週 names a
    fortnight without saying which, and a bare 毎月 names no day, so both return None rather than
    a guess. None means "the cadence does not decide", which a caller must not read as False.
    """
    if not cad or not when:
        return None
    try:
        d = datetime.date.fromisoformat(str(when)[:10])
    except ValueError:
        return None
    m = re.match(r"毎月(第[0-9０-９])([月火水木金土日])曜?", cad)
    if m and m.group(1) in NTH:
        return d.weekday() == DOW[m.group(2)] and (d.day - 1) // 7 + 1 == NTH[m.group(1)]
    m = re.match(r"毎週([月火水木金土日])曜?", cad)
    if m:
        return d.weekday() == DOW[m.group(1)]
    return None


def read(text, read_on):
    """Everything statable about the schedule on one page."""
    out = {}
    c = cadence(text)
    if c:
        out["cadence"] = c
    n = next_update(text, read_on)
    if n:
        out["next_update"] = n
    return out or None
