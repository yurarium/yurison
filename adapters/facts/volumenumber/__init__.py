#!/usr/bin/env python3
"""Which volume a shop's product title says this book is.

WHY THIS EXISTS. `bwingest` numbered a BOOK☆WALKER volume by its POSITION in the shop's listing,
`enumerate`'s index published as the volume number. The listing is neither a volume list nor in
volume order: BOOK☆WALKER sells 32 products under MURCIÉLAGO, three of them free samples of volumes
already in the list, so the corpus said the series had 32 volumes and invented volumes 30, 31 and
32. パロスの剣 lists `【最新刊】…3巻` first, so volume 3 was published as volume 1.

THE SERIES TITLE IS THE EVIDENCE, and this is the whole design. A rule that reads a number off the
end of a title has to guess whether the digits are a number or a name, and `あやめ14`, `魔法少女201`
and `ラブフェロモンNo.5` are names. A PRODUCT title in a series is the series title with something
added, so removing the series title leaves exactly the something: `MURCIELAGO -ムルシエラゴ- 29巻`
minus the series is `29巻`, and there is nothing left to guess about. 94% of the 4,792 volume rows
in multi-volume series have their series title inside their product title, and the 6% that do not
are shop-side umbrellas holding differently named books, `百合シリーズ` and `森永みるく＆袴田めら
百合合同誌`, which state no volume number and should not be given one.

  WHY IT IS NOT `bwingest.NUMBERED_OFF` READ FORWARDS, which is what the plan for this expected.
  That regex answers a different question with different evidence: given ONE title and no series to
  compare it against, does it end in a number that belongs to the volume rather than to the work's
  name. It is what `title_of` needs to name a work the shop holds one volume of, and it stays. This
  is the question you can only ask when the series is known, and knowing it is what makes the
  answer evidence instead of a guess.

  THE COMPARISON IS TOLERANT OF ACCENT, WIDTH, CASE AND PUNCTUATION, because the shop is not.
  BOOK☆WALKER files the series as `MURCIÉLAGO -ムルシエラゴ-` and the volume as `MURCIELAGO
  -ムルシエラゴ- 1巻`, with the accent on one and not the other, and a strict prefix test fails on
  the exact record this module was written for.

WHAT A NUMBER LOOKS LIKE, measured over the tails that survive the strip. `N巻` and a bare `N` are
most of it, `（N）` is a large minority, and `vol.N`, `No.N` and the 上下 of a two volume set are
the rest. 79% of the rows state one of these. The remainder state no number this can read, and
`None` is the honest answer: the interface already draws an unnumbered volume, and VOLUMES-PLAN §3
gives another catalogue the chance to supply what the shop did not.

A MAGAZINE ISSUE IS NOT A VOLUME. `ガレット 2019年5月号` is an issue of a magazine the shop files as
a series, and numbering it would put 12 volumes a year into a work's run. It is declined by name.
"""
import re
import unicodedata

#: A bracketed aside at either end of what is left: `【電子限定特典ペーパー付き】`, `[雑誌]`, and
#: the 〈…〉 a volume's own subtitle is set in. Round brackets are deliberately absent, because
#: `（1）` is one of the ways the number itself is written.
_ASIDE = r"[【\[〈「][^】\]〉」]{0,28}[】\]〉」]"
BRACKET_TAIL = re.compile(rf"\s*{_ASIDE}\s*$")
BRACKET_HEAD = re.compile(rf"^\s*{_ASIDE}\s*")

#: A periodical, which has issues rather than volumes.
ISSUE = re.compile(r"\d+\s*年\s*\d+\s*月号|創刊号|増刊")

#: Punctuation the series title ended in, left stranded at the front of the tail.
LEAD = "】]>〉!！?？。、,.:：-‐―ー–—・~〜 　"

#: How the shop writes the number, once everything else is off. Ordered longest-first in intent:
#: `1巻` before a bare `1`, so the counter is consumed rather than left behind.
FORMS = (
    re.compile(r"^(?:第\s*)?(\d+(?:\.\d+)?)\s*巻$"),
    re.compile(r"^(?:第\s*)?(\d+(?:\.\d+)?)$"),
    re.compile(r"^[(（]\s*(\d+(?:\.\d+)?)\s*[)）]$"),
    re.compile(r"^(?:vol|no)\.?\s*(\d+(?:\.\d+)?)$", re.I),
    # A two volume set numbered by word. `works[].volumes[].number` already carries these.
    re.compile(r"^[(（<〈]?\s*([上中下前後])\s*[)）>〉]?$"),
)

#: A product that is not a volume: the shop's free sample of one. `【期間限定無料】` is deliberately
#: absent, because it marks a real volume the shop is giving away for a while.
SAMPLE = re.compile(r"無料お試し版|お試し版|試し読み")


def _flatten(ch):
    """One character as it compares: accent, width and case removed, punctuation dropped."""
    d = unicodedata.normalize("NFKD", ch)
    d = "".join(c for c in d if not unicodedata.combining(c))
    d = unicodedata.normalize("NFKC", d).casefold()
    if not d or d.isspace() or all(unicodedata.category(c)[0] in "PZC" for c in d):
        return ""
    return d


def _folded(s):
    """`(flattened text, index of the source character each flattened character came from)`."""
    out, where = [], []
    for k, ch in enumerate(s or ""):
        c = _flatten(ch)
        if c:
            out.append(c)
            where += [k] * len(c)
    return "".join(out), where


def is_sample(title):
    """Whether this product is the shop's free sample of a volume rather than a volume."""
    return bool(SAMPLE.search(str(title or "")))


def beyond_series(title, series):
    """What a product title says beyond naming its series, or None where it does not name it.

    THE SERIES TITLE IS SOUGHT ANYWHERE, not stripped from the front, and the shop's badge needs
    no rule of its own as a result. `【最新刊】パロスの剣　3巻` and `【作品名】　１` both work out,
    where a rule that removed a leading `【…】` first ate the whole of the second title. The LAST
    occurrence is taken, so a badge that quotes the series name loses to the real one.
    """
    body = str(title or "")
    seen, where = _folded(body)
    want, _ = _folded(series)
    if not want:
        return None
    at = seen.rfind(want)
    if at < 0:
        return None
    return body[where[at + len(want) - 1] + 1:]


def stated(title, series):
    """The volume number this product title states, as a string, or None.

    None means the shop did not say, which is a fact about the listing and not a gap to fill in. A
    caller must not fall back on the item's position: that is the fault this module exists to end.
    """
    tail = beyond_series(title, series)
    if tail is None:
        return None
    tail = unicodedata.normalize("NFKC", tail).strip()
    if ISSUE.search(tail):
        return None
    for _ in range(4):
        shorter = BRACKET_HEAD.sub("", BRACKET_TAIL.sub("", tail).strip()).strip()
        if shorter == tail:
            break
        tail = shorter
    tail = tail.lstrip(LEAD).strip()
    for form in FORMS:
        m = form.match(tail)
        if m:
            return m.group(1)
    return None
