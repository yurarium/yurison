#!/usr/bin/env python3
"""A printing the shop states in its own description, which outranks the day it began delivering.

WHY THIS EXISTS. `adapters/delivery.py` dates 1,209 コミックシーモア works from 配信開始日 because
no paper record was reachable for any of them. On 58 of those works the shop's own description
names a date or an event for the doujin edition the file was made from, in its own sentence:
`（２０２２年５月発行の創作百合同人誌です）`, `（初出:2020年2月コミティア）`,
`（コミックマーケット102発行・同人誌）`. The recovery round found them and left them, because
nobody had ruled on whether a shop stating a date in a blurb attests one. The project owner ruled
on 2026-08-08 that it does.

WHAT FOLLOWS FROM THE RULING. A blurb-stated 発行 is the shop stating a PRINTING, and a printing
always beats a delivery date (`delivery.promote`, and the 353-volume measurement behind it). So a
row this module answers stops being dated by the day a shop began selling a file and becomes dated
by the publication of the book. `delivery.promote` still owns the refusal, and it is told about
this date rather than being made to find it, so the rule that a printing wins has one home.

WHAT IS RECORDED, AND WHAT IS NEVER RECORDED. The date, which shop's claim it is, and the sales
event where one is named. Not the sentence. A shop's あらすじ is copyrighted (REQUIREMENTS §2) and
the previous round cut two fixtures out of the cache and deleted them again before committing for
exactly that reason. Every literal in `test_blurbdate.py` is the construction that was matched and
never the story around it.

発行 AND 初出 ARE TWO CLAIMS AND THE ROW SAYS WHICH. 初出 is where the work first appeared; 発行 is
the book being issued. Both precede the delivery and they need not fall on the same day, so the
promoted row carries `first_publication_event` naming the one the shop made. Where a sentence makes
both, as `※初出：COMITIA150（2024年11月発行同人誌）` does, the claim word beside the DATE is the one
reported, since that is the claim the number belongs to.

AN EVENT NUMBER IS RECORDED AND IS NOT TURNED INTO A DATE. This is a choice and here is the
argument for it. コミックマーケット102 was held in August 2023 and COMITIA150 on 2024-11-17, and this
corpus states four such pairings itself, so a table could be assembled. Assembling one is refused.
Comiket 98 was cancelled in 2020 and its number was consumed anyway, so counting two events to the
year across that gap silently returns the wrong year. `関西コミティア68` is a different series from
`COMITIA68` and a table keyed on a number would merge them. A table we maintain is also a second
producer of a fact no source here states, which is the shape STANDING-INSTRUCTIONS §3 attributes
seven shipped bugs to. So `sold_at` reports the series and the
number the shop printed, a reader can look the event up, and the row keeps its delivery date until
somebody dates the event from a source.

THE COUNTER-CASES CAME FIRST, because a year is four digits and a blurb is full of numbers. Each of
these is real and each would be claimed by the obvious rule:

  【165ページ】 and 全42ページ         a page count
  創作百合同人誌15冊発刊記念            a count of books beside a publishing word
  1000年後の地球で目覚めた             a year in the plot
  彩未が結婚でこの地を離れて12年        a duration in the plot
  2025年5月現在は読み切り(完結)の状態    a date the blurb uses to say what is true today
  2011年～2014年にかけて発表した        a range, which dates no single edition
  個人誌『夢落 2021年3月号』            an issue label inside a title
  同人誌風マンガ                       a commercial book in the style of one

The last is `delivery.NOT_THE_EDITION`'s, and this module reaches it by asking
`delivery.edition_statement` first instead of writing its own copy. A blurb that says nothing about
this file's edition can hold whatever dates it likes and none of them is about a printing of it.

WHY 発売 IS NOT A PUBLISHING WORD HERE, recorded so it is not added back. It is the word a shop
uses to announce the release of a DIFFERENT book, usually the next volume, and a date beside it
would be a promotion rather than this file's history. Nothing in the 279 doujin descriptions on
disk needs it: 発売 appears beside a year on none of them.
"""
import datetime
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import delivery                                                                # noqa: E402

# The basis a row promoted here carries. `shop-delivery-date` says the shop stated when it began
# selling a file; this says the shop stated when the book was printed, in the same box, in a
# sentence of its own.
BASIS = "shop-blurb-print-date"

# Which claim the shop made. Written into `first_publication_event`, whose whole job is to stop a
# date being read as an event nobody named.
EV_ISSUE = "issue"
EV_FIRST_APPEARANCE = "first-appearance"

BASIS_NOTE = {
    BASIS:
        "The shop's own description of this work states when the doujin edition it was made from "
        "was published. That is a printing, so it answers the work's first publication and the "
        "day the shop began delivering the file does not. The sentence is not recorded, because a "
        "shop's description is copyrighted; the date, the claim it was made under and the sales "
        "event named beside it are.",
}

EVENT_NOTE = {
    EV_ISSUE:
        "発行. The shop states this is when the book was issued.",
    EV_FIRST_APPEARANCE:
        "初出. The shop states this is where the work first appeared, which can precede the "
        "printing of the book being sold here.",
}

# The sales event series this module can tell apart, as its own terms. 関西コミティア is listed
# first and matched first: it is a separate series with its own numbering, so `関西コミティア68` and
# `COMITIA68` are two different days and a pattern that read the shorter name would merge them.
COMITIA_KANSAI = "comitia-kansai"
COMITIA = "comitia"
COMIKET = "comiket"

EVENT_SERIES = (
    (COMITIA_KANSAI, re.compile(r"関西\s*(?:コミティア|COMITIA)\s*([0-9]{1,3})?")),
    (COMITIA, re.compile(r"(?:コミティア|COMITIA)\s*([0-9]{1,3})?")),
    (COMIKET, re.compile(r"(?:コミックマーケット|コミケット|コミケ|C)\s*([0-9]{2,3})")),
)

FULLWIDTH = str.maketrans("０１２３４５６７８９", "0123456789")

# The publishing words a date may lean on. 頒布 and 販売 are here because a doujinshi is issued by
# being sold at an event and this corpus's sellers use all of these for the same act, writing
# `COMITIA154で頒布した同人誌です` and `COMITIA154で発行した同人誌です` on neighbouring rows.
ISSUE_WORDS = r"発行|発刊|発表|頒布|販売|出した|出しました|リリース"
CLAIM = re.compile(rf"(?P<issue>{ISSUE_WORDS})|(?P<first>初出)")

# A year, optionally a month, optionally a day, in the separators this shop's sellers use:
# `2016年`, `2022年5月`, `2026年2月22日`, `2023.12.3`, `2024/5/26`.
DATE = re.compile(r"(?P<y>[0-9]{4})\s*(?:年|[./／])\s*"
                  r"(?:(?P<m>[0-9]{1,2})\s*(?:月|[./／])\s*(?:(?P<d>[0-9]{1,2})\s*日?)?)?")

# A range marker touching the date on either side. `2011年～2014年にかけて個人誌で発表した` names
# the years an author was active and dates no edition, so both ends are refused.
RANGE = re.compile(r"[～~〜─―−\-]")

# How far a publishing word may sit from the date it belongs to. The event name is what gets
# between them, and the longest on disk is `2024年11月開催「COMITIA150」で発行した`, whose 発行 starts
# fifteen characters after the date and ends at seventeen. Sixteen was the first value here and it
# lost that row, so the window is measured on the end of the word and not on its start. Four before
# covers `初出:2020年2月コミティア`, where the claim is a label ahead of the number.
AFTER = 20
BEFORE = 4

# The oldest year a doujin edition sold as a file here could carry. Doujinshi predate this, and the
# bound is not a claim about the medium: it is what separates a printing from `1000年後の地球`, and
# a blurb naming a 1969 printing would be a work this shop does not stock.
EARLIEST = 1970


def sold_at(text):
    """The sales event the shop names, as `(series, number)`, or None where it names none.

    `number` is None where the shop names the event and not which one, which
    `2022年コミティアにて発行しました本` does. That row is dated from its year and the event is
    recorded for what it is.

    NOTHING HERE BECOMES A DATE. The module docstring carries the argument. In short: the numbering
    has a hole in it where Comiket 98 was cancelled, and 関西コミティア numbers its own series.
    """
    t = str(text or "").translate(FULLWIDTH)
    for series, pat in EVENT_SERIES:
        m = pat.search(t)
        if m:
            return series, (int(m.group(1)) if m.group(1) else None)
    return None


def _claim_beside(text, start, end):
    """Which publishing claim, if any, the date spanning `start:end` leans on."""
    m = CLAIM.search(text[end:end + AFTER]) or CLAIM.search(text[max(0, start - BEFORE):start])
    if not m:
        return None
    return EV_FIRST_APPEARANCE if m.group("first") else EV_ISSUE


def dates(text, today=None):
    """Every printing the description states, as `(date, claim)`, earliest first.

    A date is taken only where the blurb leans it on a publishing word, since a blurb states plenty
    of numbers that are not dates and a few dates that are not publications. `2025年5月現在は読み切
    り(完結)の状態` says what is true today and `1000年後の地球` is the setting.

    THE BLURB MUST FIRST HAVE SAID WHAT EDITION THIS FILE IS. `delivery.edition_statement` decides
    that and its three pinned refusals are inherited here rather than copied: 同人誌風マンガ is a
    commercial book in the style of one, コミティアの人気作家 describes the author, and
    参加した同人誌即売会で is a scene. A page that says nothing about its edition can hold a date
    for anything at all.
    """
    t = str(text or "").translate(FULLWIDTH)
    if not delivery.edition_statement(t):
        return []
    latest = (today or datetime.date.today()).year + 1
    out = []
    for m in DATE.finditer(t):
        year = int(m.group("y"))
        if not EARLIEST <= year <= latest:
            continue
        if RANGE.search(t[max(0, m.start() - 2):m.start()]) or RANGE.search(t[m.end():m.end() + 2]):
            continue
        claim = _claim_beside(t, m.start(), m.end())
        if not claim:
            continue
        value = m.group("y")
        if m.group("m"):
            value += "-%02d" % int(m.group("m"))
        if m.group("d"):
            value += "-%02d" % int(m.group("d"))
        out.append((value, claim))
    return sorted(out)


def stated(text, today=None):
    """The printing this description states, as `(date, claim)`, or `(None, None)`.

    THE EARLIEST OF SEVERAL, for the reason `delivery.promote` takes the earliest delivery: the
    claim being made is when this book was published, and a later printing cannot be the first one.
    Several is common and the extras are real editions rather than noise. A 合本版 names both of the
    books bound into it, `（２０２３年９月発行＆１２月発行の創作百合同人誌合本版です）`, and a book
    that reprints a convention paper names the paper's own month beside its own.
    """
    got = dates(text, today=today)
    return got[0] if got else (None, None)


def precision(date):
    """`day`, `month` or `year`, from the value itself so nothing has to store it twice."""
    return {10: "day", 7: "month", 4: "year"}.get(len(str(date or "")))
