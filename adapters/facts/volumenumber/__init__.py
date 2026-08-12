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

#: THE SHOP'S OWN BRACKETS, which BOOK☆WALKER sets its own marks in: `【最新刊】`,
#: `【電子限定特典ペーパー付き】`, `[雑誌]`. Nothing in one of these is part of what a book is
#: called.
_SHOP_ASIDE = r"[【\[][^】\]]{0,28}[】\]]"

#: THE BRACKETS A TITLE USES, which are a different set and are content. `〈眼帯の下の紅い目〉` is a
#: volume's subtitle and `「おみくじフォトグラフ」` is the whole of what tells one ゆるゆり booklet
#: from the next: the shop sells 17 of them and every title after the bracket reads
#: `ゆるゆり 特装版小冊子電子版`. Stripped when a NUMBER is being read, because a number is never
#: inside one; kept when the designation is what is wanted.
_TITLE_ASIDE = r"[〈「][^〉」]{0,28}[〉」]"

_ASIDE = f"(?:{_SHOP_ASIDE}|{_TITLE_ASIDE})"
BRACKET_TAIL = re.compile(rf"\s*{_ASIDE}\s*$")
BRACKET_HEAD = re.compile(rf"^\s*{_ASIDE}\s*")
SHOP_TAIL = re.compile(rf"\s*{_SHOP_ASIDE}\s*$")
SHOP_HEAD = re.compile(rf"^\s*{_SHOP_ASIDE}\s*")

#: An instalment designated by when it came out rather than by where it sits in a run. Nothing is
#: read out of one of these: see `stated`.
ISSUE = re.compile(r"\d+\s*年\s*\d+\s*月号|増刊")

#: BOOK☆WALKER's own word for what a product is. The shop states this and we do not infer it.
MAGAZINE = re.compile(r"\[雑誌\]|［雑誌］")

#: Punctuation the series title ended in, left stranded at either end of the tail. The fold that
#: locates the series ignores punctuation, so a title ending in `「you」` leaves its closing bracket
#: behind. Round brackets are absent on purpose: `（1）` is one of the ways a number is written.
LEAD = "】]>〉」』!！?？。、,.:：-‐―ー–—・~〜 　"

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

#: 創刊号 IS A POSITION AND NOT A LABEL, ruled by the project owner 2026-08-12 on ガレット, whose
#: numbering runs `No.2` to `No.37` with its inaugural issue as the only row carrying no number.
#: The word means the first issue, so reading it restores the sequence rather than interpreting it,
#: and it belongs beside 上 and 下 as a designation written out.
FIRST_ISSUE = re.compile(r"^創刊号$")

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


def _strip(tail, head, end):
    """`tail` with every leading and trailing aside off, and the stranded punctuation with it."""
    tail = unicodedata.normalize("NFKC", tail).strip()
    for _ in range(4):
        shorter = head.sub("", end.sub("", tail).strip()).strip()
        if shorter == tail:
            break
        tail = shorter
    return tail.strip(LEAD).strip()


def _clean(tail):
    """A tail with every aside off, for reading a number out of what is left."""
    return _strip(tail, BRACKET_HEAD, BRACKET_TAIL)


def _shown(tail):
    """A tail with the SHOP's marks off and the title's own brackets kept, for showing a reader."""
    return _strip(tail, SHOP_HEAD, SHOP_TAIL)


def is_periodical(title):
    """Whether the shop says this product is a magazine, in its own words.

    STATED, NOT INFERRED. BOOK☆WALKER writes `[雑誌]` after the title of an issue, and that is the
    only thing in reach that says what a product IS rather than what it is called. A rule reading
    the format out of a date-shaped designation would call まんがタイムきららＭＡＸ a magazine and
    still miss ガレット, whose issues are numbered `No.2` to `No.37` and look exactly like a book's.
    An untagged magazine is therefore not marked, which is a limit worth recording rather than
    guessing past.
    """
    return bool(MAGAZINE.search(str(title or "")))


def stated(title, series):
    """The volume number this product title states, as a string, or None.

    None means the shop did not say, which is a fact about the listing and not a gap to fill in. A
    caller must not fall back on the item's position: that is the fault this module exists to end.
    """
    tail = beyond_series(title, series)
    if tail is None:
        return None
    if ISSUE.search(unicodedata.normalize("NFKC", tail)):
        return None
    tail = _clean(tail)
    if FIRST_ISSUE.match(tail):
        # THE SHOP'S OWN WORD, NOT THE NUMBER IT MEANS. `創刊号` is a designation written out, the
        # way `上` and `下` are, and `build.volume_number` is the one place a designation becomes an
        # integer for sorting. Returning `1` here would put a number in the record that the product
        # title does not contain, which is exactly what `a volume number is the shop's own` exists
        # to catch, and it would be right to catch it.
        return tail
    for form in FORMS:
        m = form.match(tail)
        if m:
            return m.group(1)
    return None


def designation(title, series):
    """What this product is called within its series, where that is not a number. None where the
    product's title says nothing the work's own title does not.

    A DESIGNATION THAT IS A LABEL IS CARRIED WHOLE AND NOTHING IS DERIVED FROM IT, which is the
    project owner's ruling of 2026-08-12. `2017年1月号` is what an issue is called. It is not a
    date, and a magazine's naming scheme is not stable across its own life: コミック百合姫 has run
    `Vol. 7 Winter 2007` quarterly, then bimonthly, then with no volume number, and only now
    monthly by cover date. A `Vol. 7` and a `2017年1月号` are not two points on one line, so
    ordering them or looking for a gap between them would be arithmetic on a fiction.

    THE WHOLE TITLE WHERE IT NAMES SOMETHING ELSE. `メガネさんシリーズ` is a shop umbrella over
    `お昼のメガネさん` and others, so the product's own name is the whole of what it says.
    """
    tail = beyond_series(title, series)
    if tail is None:
        return _shown(str(title or "")) or None
    return _shown(tail) or None
