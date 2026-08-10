#!/usr/bin/env python3
"""配信開始日, the day a shop began delivering a file, as a first publication date where nothing else
is reachable.

WHY THIS EXISTS, AND WHAT IT REVERSES. `adapters/cmoa_volumes.py` measured 配信開始日 against a
stated print date across 353 volumes and refused it: 154 volumes were delivered BEFORE the print
date, 51 in the same month, 45 more than three years after, the extreme being 一迅社 title 153015,
printed 2007-11-01 and delivered 2018-07-18, a hundred and twenty-eight months. That measurement
stands and this module does not touch it. Where a print date exists the print date is the answer,
the delivery date is not evidence about it, and `promote` refuses on sight.

The project owner ruled on 2026-08-08 that the DIGITAL-ONLY case is different, and DEFINITIONS §6
and docs/GAPS.md carry the ruling. 1,209 cmoa works and 1,209 BOOK☆WALKER works had a delivery date
on the page and no paper record anywhere, so the field that decides scope was empty on a work whose
selling date was written down. A dated row a reader can act on beats an undated one as long as the
basis says what the date rests on.

WHAT THE DATE IS, SAID PLAINLY. "BOOK☆WALKER began delivering this file on 2018-10-20" has no error
bar. It is not an estimate of an earlier event and the wording here never suggests it is, because
calling it an approximation asserts that a dated earlier publication exists. For a doujinshi that is
usually false: the first offering is a day at an event, sometimes several events, and no register
records it the way a 奥付 records a printing (DEFINITIONS §6). So the basis names the delivery event
and the row is honest whether or not anything happened before it.

THE FOLLOW-UP MEASURE IS NOT A BACKLOG, AND IT CANNOT FULLY BE MADE INTO ONE. `followup` splits the
population where the evidence allows: a page that says the file is somebody's 同人誌 is a row with
nothing to wait for, and a page that says nothing about its edition may be waiting for a
bibliography nobody has consulted. The split is only as good as the shop's own blurb, so most rows
land in `unclassified`, and a number falling there is worth no conclusion in either direction. Read
`no-earlier-record-expected` as finished work and read the rest as unsorted.

WHY THE STATEMENT IS COUNTED AND NOT STORED. `edition_statement` reads the shop's あらすじ, which is
copyrighted (REQUIREMENTS §2), so what comes back is one of this module's own terms and never the
sentence that produced it. The term and the matched keyword are facts about our reading of the page.

THE COUNTER-CASES CAME FIRST, because a keyword sweep for 同人誌 over the cmoa cache hits 321 pages
and is wrong about a good few of them. `同人誌風マンガ` is a commercial book done in the STYLE of
one, `コミティアの人気作家` describes the author and not the edition, and `参加した同人誌即売会で` is a
scene in the story. `adapters/test_delivery.py` pins all three as refusals, since the rule was wrong
in that direction before it was written.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from facts import dating as _dating                                            # noqa: E402

# The basis value a promoted row carries, and the event the date is of. Two names for one decision,
# because `date_basis` says where a value came from everywhere else in the schema and `date_event`
# is what a reader-facing label has to switch on. Anything reading these should compare against
# these constants and not against the strings.
BASIS = "shop-delivery-date"
EVENT = "shop-delivery"

# ONE SENTENCE PER TERM, IN ONE PLACE, following recon/bookwalker_volumes.BASIS_NOTE. A term whose
# meaning is written out wherever it is displayed drifts, and a reader meeting it in `data/queue/`
# and again in `data/build/` is entitled to the same words.
# The sentence lives in `facts/dating` with every other term of this field; this module owns
# which term it emits and nothing else about the vocabulary.
BASIS_NOTE = {BASIS: _dating.note(BASIS)}

# WHY A PRINT DATE ENDS THE QUESTION. Not a preference between two dates: across the 353 volumes
# stating both, the delivery date fell on either side of the printing by up to 128 months, so it is
# not a bound in either direction and averaging the two would invent a third date nobody stated.
REFUSED_PRINT = "print-date-stated"

# The shop states a printing in its own description instead of on a volume row. Same refusal and a
# different place to have found it, so a reader of the row can tell which one happened.
# `adapters/blurbdate.py` reads it and the owner's ruling of 2026-08-08 admits it.
REFUSED_BLURB = "blurb-print-date-stated"

# The shop states this file is the electronic edition of something published before it. The blurb
# predicates the FILE on the earlier edition, which is what makes it a statement about publishing
# instead of a word occurring in a plot summary.
EARLIER_EDITION = "earlier-edition-stated"

# The shop states this file IS a doujinshi or an individually published book, sold here rather than
# reissued from anywhere. DEFINITIONS §6 admits these and says why their delivery date may be the
# only datable event in the work's history.
OWN_DOUJIN = "own-doujin-edition"

# ── Reading the shop's own description ────────────────────────────────────────────────────────

# CHECKED FIRST, AND THE REASON THE ORDER MATTERS. Each of these contains a word the rules below
# match, and in each the word is about something other than this file's edition. Putting them ahead
# of the positive rules is cheaper than writing every positive rule to exclude them.
NOT_THE_EDITION = re.compile(
    r"同人誌風"                                    # 立花館To Lieあんぐる: a commercial book in the style
    r"|(?:コミティア|COMITIA|コミケ)の人気作家"     # about the author, not this book
    r"|(?:参加|向か|出る|出場|出品)[^。]{0,12}(?:同人誌即売会|同人誌イベント)"
    r"|同人誌(?:即売会|イベント)[^。]{0,8}(?:で、|で崇|に出|へ)"
)

# The file is the electronic edition of an earlier one. `※本作は…の個人誌作品の電子書籍版となります`
# is cmoa's own boilerplate and covers most of them; the rest state the relation in their own words.
STATES_EARLIER = re.compile(
    r"(?:個人誌|同人誌|同人版|個人同人誌)(?:作品)?の電子(?:書籍版|版|配信)"
    r"|(?:個人誌|同人誌|同人版)[^。]{0,10}初の電子(?:配信|書籍)"
    r"|(?:個人誌|同人誌|同人版)(?:で|にて|として)(?:発表|発行|頒布|販売|連載|展開)"
    r"|(?:同人誌|個人誌|同人版)[^。]{0,12}(?:再録|総集編|合冊|加筆修正|選りすぐ)"
    r"|(?:以前|過去に|かつて)[^。]{0,16}(?:同人誌|個人誌)"
    r"|(?:同人誌|個人誌|同人版)版から"
    r"|(?:同人誌|個人誌)[^。]{0,12}(?:をまとめ|を1冊|を１冊|収録)"
    r"|自主制作[^。]{0,24}(?:電子書籍版|連載)"
    r"|(?:コミティア|COMITIA|コミケ|コミックマーケット)[^。]{0,20}(?:にて発刊|で出した|に出した|リリース)"
    r"|人気同人誌が"
)

# The file itself is the doujinshi. cmoa marks these several ways and ナンバーナイン puts the page
# count in the same breath: `創作百合同人誌 40P（表紙込）`.
STATES_OWN = re.compile(
    r"(?:当コンテンツ|本作品?|本書|この作品|こちら)は[^。]{0,40}(?:同人誌|個人誌|同人版)"
    r"|【[^】]{0,16}(?:同人誌|個人誌)[^】]{0,12}】"
    r"|創作(?:百合)?(?:個人)?同人誌"
    r"|(?:同人誌|個人誌|同人版)(?:です|作品です|となります|になります|合本版)"
    r"|(?:発行|頒布)[^。]{0,8}(?:創作)?(?:百合)?(?:同人誌|個人誌)"
    r"|(?:コミティア|COMITIA|コミケ|コミックマーケット)[^。]{0,16}(?:発行|頒布|初出|会場限定)"
    r"|初出\s*[:：][^。]{0,24}(?:コミティア|COMITIA|コミケ|コミックマーケット)"
    r"|同人誌につき"
)

# The doujin words this module knows, for the wider count that makes the strict one interpretable.
MENTIONS = re.compile(r"同人誌|個人誌|同人版|コミティア|COMITIA|即売会|自主制作|コミケ|コミックマーケット")


def edition_statement(text):
    """What the shop's own description says about this file's edition, as one of this module's terms.

    `EARLIER_EDITION` where the blurb predicates the file on something published before it,
    `OWN_DOUJIN` where the blurb says the file itself is a doujinshi or an individually published
    book, and None where neither is stated. A page mentioning a doujin word in its plot summary
    answers None, which is the whole point of `NOT_THE_EDITION`.

    THE EARLIER EDITION WINS A TIE, and the tie is common: `創作百合同人誌の電子書籍版` says both
    that the file is a doujinshi and that a doujin edition came before it. The earlier statement is
    the more specific claim and it is the one the refused argument turned on, so it is reported.
    """
    t = str(text or "")
    if not t:
        return None
    if NOT_THE_EDITION.search(t) and not (STATES_EARLIER.search(t) or STATES_OWN.search(t)):
        return None
    if STATES_EARLIER.search(t):
        return EARLIER_EDITION
    if STATES_OWN.search(t):
        return OWN_DOUJIN
    return None


def mentions_doujin(text):
    """Whether any doujin word appears at all, which is the denominator for the strict count.

    Reported beside `edition_statement` so the strict number can be read against the loose one. A
    strict count alone cannot be told from a broken pattern.
    """
    return bool(MENTIONS.search(str(text or "")))


# ── Promoting a delivery date ─────────────────────────────────────────────────────────────────

def print_dates(items):
    """Every print date the shop states across a work's volumes, in the field names both shops use.

    `printed` is `data/queue/*-volumes.yaml`'s name and `published` is the one `bwingest.py` writes
    into a source record. Both are read here because this function is asked about a work at either
    stage, and a version that knew only one name would answer "no print date" for the other and
    promote a delivery date over a printing. That is the failure this whole module is fenced against.
    """
    out = []
    for v in (items or []):
        for k in ("printed", "published"):
            if v.get(k):
                out.append(str(v[k])[:10])
    return out


def delivery_dates(items):
    """Every 配信開始日 the shop states across a work's volumes."""
    return [str(v["delivered"])[:10] for v in (items or []) if v.get("delivered")]


def promote(items, stated_print=None):
    """`(date, refusal)`: the delivery date this work may carry, or why it may not carry one.

    THE EARLIEST DELIVERY AND NOT VOLUME ONE'S. The claim being made is that the shop began
    delivering this work on a day, and the earliest date across its volumes is that day. Volume 1's
    own date is the same number on a digitised back catalogue, where every file goes up together,
    and is the wrong number where the shop delivered a later volume first. Taking the minimum also
    means the value cannot land after a date derived from the same volumes, so no ordering invariant
    has to be repaired afterwards.

    A PRINT DATE REFUSES OUTRIGHT. Not the earlier of the two and not an average: the 353-volume
    measurement puts the delivery date on either side of the printing by up to 128 months, so it is
    neither an upper nor a lower bound and combining them would state a date no source holds.

    `stated_print` IS A PRINTING THIS FUNCTION CANNOT SEE. `adapters/blurbdate.py` reads one out of
    the shop's own description, which is on the work page and not on the volume rows here, so the
    caller passes it in. It refuses exactly as a printed volume does, and the refusal reads
    differently so a row says which of the two happened.
    """
    if stated_print:
        return None, REFUSED_BLURB
    if print_dates(items):
        return None, REFUSED_PRINT
    got = delivery_dates(items)
    return (min(got), None) if got else (None, None)


# ── The follow-up measure ─────────────────────────────────────────────────────────────────────

# Nothing is waiting on a source. The shop states the file is a doujinshi or an individually
# published book, and DEFINITIONS §6 says the delivery date may be the only datable event it has.
SETTLED = "no-earlier-record-expected"

# A dated earlier edition plausibly exists and nobody has looked for it. The shop states the file is
# the electronic edition of something published before it, so there was a printing, even where the
# printing was a circle's own and left no register.
OPEN = "earlier-edition-unsourced"

# Neither is known. The shop says nothing about the edition, so this row is not evidence that a
# bibliography would answer and not evidence that none would.
UNSORTED = "unclassified"

FOLLOWUP_NOTE = {
    SETTLED:
        "The shop states this file is a doujinshi or an individually published book. Under "
        "DEFINITIONS §6 the delivery date may be the only datable event in its history, so this "
        "row is finished work and not a row awaiting a better source.",
    OPEN:
        "The shop states this file is the electronic edition of an earlier one and does not date "
        "it. A better date may exist, and for a circle's own printing it may never have been "
        "recorded.",
    UNSORTED:
        "The shop says nothing about this file's edition. Whether a better date exists is unknown, "
        "so this row counts toward neither the settled population nor a backlog.",
}


def followup(statement=None, self_published=False):
    """Which of the follow-up states this row is in, from what is known about its edition.

    SELF-PUBLISHING SETTLES IT WITHOUT A BLURB. BOOK☆WALKER states no ISBN anywhere and carries no
    あらすじ this pass can read, so `edition_statement` has nothing to work from on its rows. What it
    does state is the publisher, and 真夜中だけのおともだち records あおい華葉 as author, publisher
    and imprint at once, which is the shop's individual-publishing route describing itself. A book
    published by its own author through a shop has no commercial printing for a bibliography to
    hold.

    THE HONEST ANSWER FOR MOST ROWS IS `unclassified`, and a count of it means only that the shop
    did not say. Anyone reading these numbers as a queue length should read `FOLLOWUP_NOTE` first.
    """
    if statement == EARLIER_EDITION:
        return OPEN
    if statement == OWN_DOUJIN or self_published:
        return SETTLED
    return UNSORTED


def tally(rows):
    """`{"rows": n, "followup": {state: n}}` over works-list rows.

    ONE PRODUCER, AND ONE POPULATION. This number is printed at the end of a build, written into
    `run.json`, and published as a statistic on `status.html`. Counting it three times is the shape
    STANDING-INSTRUCTIONS §3 attributes seven shipped bugs to, and counting it over three different
    populations would be worse: a work record and a works-list row are not the same unit, because
    the build folds several records onto one identity, so the same rule over works.json answers 1,140
    where the rows answer 1,084. Every caller reads the ROWS, which is the population a reader is
    looking at.

    A row in either shape is accepted, because the works list writes `first_event` at the top level
    and a work record writes `date_event` inside `first_publication`. That is one fact under two
    names and joining them here is cheaper than a caller remembering which it holds.
    """
    got = []
    for r in (rows or []):
        fp = r.get("first_publication") or {}
        event = r.get("first_event") or fp.get("date_event")
        if event == EVENT:
            got.append(r.get("first_followup") or fp.get("date_followup") or UNSORTED)
    out = {}
    for k in got:
        out[k] = out.get(k, 0) + 1
    return {"rows": len(got), "followup": out}


def self_published(creator, publisher, imprint=None):
    """Whether the shop records this book's publisher as the person who drew it.

    Read off three fields the shop states separately, so agreement between them is the shop's own
    doing. あおい華葉 fills all three on 真夜中だけのおともだち. A publisher matching one name out of
    a credit line of several is not this: a circle that shares a name with its founder would pass,
    and one name against one name is as far as this can honestly go.
    """
    c, p = (str(creator or "").strip(), str(publisher or "").strip())
    if not c or not p or c != p:
        return False
    i = str(imprint or "").strip()
    return not i or i == p
