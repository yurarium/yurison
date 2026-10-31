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


# ── A DESIGNATION BECOMES AN INTEGER, WHICH IS THE OTHER HALF OF THIS FACT. STORE-PLAN §12 ─────
#
# The rest of this module says which part of a product title is a designation; this says what
# number that designation names, where it names one. The two were a docstring apart and a
# repository apart: the second lived in a 7,400-line compiler, and three adapters imported the
# compiler to reach it.

VOLUME_NO = re.compile(r"^\s*(?:第\s*)?(?:v(?:ol)?(?:ume)?\s*\.?\s*)?(\d+)\s*(?:巻)?\s*$", re.I)


#: HOW A SET NUMBERED BY WORD RUNS, in order. Which position each word takes depends on which of
#: them the work uses, so the number is worked out over a run's own volumes rather than read off
#: this: 上下 is two parts and 上中下 is three, and both spell 下 the same way.
PART_WORDS = ("上", "中", "下")

#: The inaugural issue of a periodical, which is its first. `FIRST_ISSUE` above is the same word as
#: a pattern, for reading a product title; this is the word itself, for reading a designation that
#: is already isolated. Two spellings of one fact in one module was a name collision waiting, and
#: it happened on the first run after these were brought together.
FIRST_ISSUE_WORD = "創刊号"


def volume_number(v):
    """The volume's number as a number, or None where it does not state one.

    MADB writes it a dozen ways: a bare `1`, `vol. 8`, `vol.2`, `volume 1`, `Volume1`, `volume.2`,
    `Vol. 1`, `v.1`, `第1巻`. 上 and 下 are not numbers, they are how a two-volume set is designated,
    and they answer None here.

    `創刊号` IS A NUMBER WRITTEN OUT, which 上 and 下 are not: it names the first issue and nothing
    else, so ガレット's inaugural issue sorts and counts as 1 among its `No.2` to `No.37`. Ruled by
    the project owner 2026-08-12. It is read here rather than at capture, so the record keeps the
    word the shop printed and `a volume number is the shop's own` stays pure arithmetic.
    """
    raw = str(v.get("number") or "").strip()
    if raw == FIRST_ISSUE_WORD:
        return 1
    m = VOLUME_NO.match(raw)
    return int(m.group(1)) if m else None




# ── WHAT A VOLUME IS CALLED IN ITS OWN RIGHT, which is the third part of this fact ─────────────
#
# A designation is what a product is called within its series; part of it can be a position and
# part a name. `鈴木りつ第二短編集　垂直・宇宙・無限` is the second of two collections and every word
# of it is a title, `2巻 ワタシがいなくちゃダメなカノジョのハナシ` is a position and a title, and
# `2巻` is a position and nothing else. The name is what a reader is owed in their own language, and
# the name store answers for it the way it answers for a work's title, keyed by the string; so the
# string has to be the name alone, with the position and the work's own title off.

#: A POSITION WRITTEN BEFORE OR AFTER THE NAME, in the ways the corpus writes one beside a title.
#: `その3`, `ep1`, `Game 3` and `#2` are doujin, anthology and chapter-style numbering; the rest are
#: FORMS above with the anchors taken off, because there the number is the whole tail and here it
#: shares one with a name.
_POSITION = (r"(?:第\s*)?\d+(?:\.\d+)?\s*(?:巻|集|部|号|話)?|[(（]\s*\d+\s*[)）]"
             r"|(?:volume|vol|no|ep|episode|game|act|part|chapter|stage|round|lesson|phase)\.?\s*\d+"
             r"|#\s*\d+|その\s*\d+|[上中下]巻?|[前中後]編")
#: WHAT PARTS A POSITION FROM A NAME. Only separators: a closing bracket or a full stop ending the
#: name belongs to it, and `LEAD`, which is for a tail a series title was cut off, would take it.
_SEPS = " \u3000-‐―–—~〜:：・"
POSITION_HEAD = re.compile(rf"^\s*(?:{_POSITION})(?=[{re.escape(_SEPS)}「『(（]|$)\s*", re.I)
POSITION_TAIL = re.compile(rf"(?:^|(?<=[{re.escape(_SEPS + LEAD)}]))(?:{_POSITION})\s*$", re.I)

#: An imprint the record wrote into the designation, `(ノヴァコミックス)`. The imprint is on the record
#: in its own field and is not what the volume is called.
IMPRINT_ASIDE = re.compile(r"[(（][^)）]*(?:コミックス|COMICS|文庫|ノベルス|ブックス)[^)）]*[)）]", re.I)

#: WHAT MAKES A DESIGNATION A LABEL FOR AN EDITION OR AN EXTRA RATHER THAN A NAME. A word in this set
#: says which printing, which bonus or which language a product is, and none of it is a title.
EDITION_WORD = re.compile(r"特装版|限定版|通常版|新装版|完全版|愛蔵版|合本版|分冊版|単話版|小冊子|特典"
                          r"|翻訳版|語版|おまけ|試し読み|お試し版")


#: A word that says what kind of thing a volume is and nothing about which: `4 volume` is a position
#: and the counter it was written with.
COUNTER_WORD = re.compile(r"^(?:volume|vol|book|part|episode|chapter|巻)\.?$", re.I)

#: How much of a work's title a designation must repeat before a partial copy of it counts as the
#: title. Eight characters is longer than any volume name that merely shares a word with its work.
TRUNCATED = 8


def _flat(t):
    """A title as two spellings of it compare: the shop's marks, any position, and every mark,
    space and symbol off."""
    t = _unpositioned(_shown(unicodedata.normalize("NFKC", str(t or "")).strip()))
    return "".join(c for c in _folded(t)[0] if unicodedata.category(c)[0] not in "PSZC")


def _same(a, b):
    """Whether `a` is the title `b`, whole or in part: a record that copies the work's title into
    the volume's designation, cut short or without a word of it, has named the work again and not
    the volume. `魔女と僕についての物語` is filed under `短編オリジナルコミックアンソロジー
    魔女と僕についての物語 ～誰も知らないきみのこと～` with its first two characters dropped."""
    fa, fb = _flat(a), _flat(b)
    return bool(fa) and bool(fb) and (fa == fb or (len(fa) >= TRUNCATED and fa in fb))


def _unpositioned(text):
    """`text` with a position before or after it taken off, where a separator parts the two."""
    for _ in range(3):
        # ー opens nothing in Japanese, so at the front it is a dash the record typed as a vowel mark.
        shorter = POSITION_TAIL.sub("", POSITION_HEAD.sub("", text)).strip().strip(_SEPS).lstrip("ー")
        if shorter == text:
            break
        text = shorter
    return text


def subtitle(designation, titles=()):
    """The name a volume's designation carries in its own right, or None where it carries none.

    `titles` are the work's own titles, as the work and the record that lists the volume write them;
    a designation repeating one of them says nothing a reader does not already see. None for a
    position alone, for an issue of a periodical, and for an edition or extra marked as one: none of
    those is a title, and `volLabel` already says them in a reader's language.

    THE NUMBER STAYS WHERE IT IS GLUED TO THE NAME. `妹とキスとメガネさん2` keeps its 2, because
    `あやめ14` and `魔法少女201` are names and nothing in the string tells the two apart; a position
    comes off only where a space or a mark separates it.
    """
    text = unicodedata.normalize("NFKC", str(designation or "")).strip()
    if not text or ISSUE.search(text) or MAGAZINE.search(text) or EDITION_WORD.search(text):
        return None
    text = IMPRINT_ASIDE.sub(" ", _shown(text)).strip()
    # FROM THE FRONT ONLY, AND ONLY WHERE SOMETHING PARTS IT FROM WHAT FOLLOWS. `beyond_series`
    # finds a series anywhere in a product title, which is right for a shop's badge and wrong here:
    # under the umbrella work メガネさん, `妹とキスとメガネさん2` holds the work's title inside its
    # own, and under 三姉妹, `三姉妹の真ん中` is one name that begins with it.
    seen, where = _folded(text)
    for t in sorted({str(t) for t in titles if t}, key=len, reverse=True):
        want, _ = _folded(t)
        if not want or not seen.startswith(want) or len(seen) <= len(want):
            continue
        rest = text[where[len(want) - 1] + 1:]
        if rest[:1] and (rest[:1] in _SEPS + LEAD + "(（[【" or rest[:1].isdigit()):
            # What the work's title left stranded comes off the front; a closing bracket or full
            # stop at the END belongs to the volume's own name.
            text = rest.lstrip(_SEPS + LEAD)
            break
    text = _unpositioned(text.strip())
    # A TRANSLATED EDITION NAMES ITS VOLUME TWICE, `Friendly Feuding Families - 組長達のなかよし`,
    # the second time in the work's own title, which is already on the page.
    for t in titles:
        head, sep, last = text.rpartition(" - ")
        if sep and head and _same(last, t):
            text = head.strip()
            break
    if not text or not any(ch.isalpha() for ch in text) or COUNTER_WORD.match(text):
        return None
    if any(_same(text, t) for t in titles if t):
        return None
    return text


#: THE ORDER PART WORDS RUN IN, across both ways of writing a set: 上中下 for volumes and 前中後編
#: for parts of a story. Which number each word takes depends on which of them the run uses.
PART_ORDER = ("前", "上", "中", "下", "後")


def position(designation, titles=()):
    """Where the designation places its volume, as the integer it states or the part word it uses,
    or None where it states neither.

    THE SAME POSITION `subtitle` TAKES OFF, read rather than discarded. `(1) -民宿かがや` and
    `(2) -民宿かがや` are two books with one name, and once the name is said apart from the number
    the number is the only thing telling them apart. A part word comes back as itself, one of
    `PART_ORDER`, because 下 is the second of 上下 and the third of 上中下 and only the run can say
    which.
    """
    text = unicodedata.normalize("NFKC", str(designation or "")).strip()
    if not text or ISSUE.search(text) or MAGAZINE.search(text):
        return None
    text = IMPRINT_ASIDE.sub(" ", _shown(text)).strip()
    if any(_same(text, t) for t in titles if t):
        return None
    m = POSITION_HEAD.match(text) or POSITION_TAIL.search(text)
    if not m:
        return None
    said = m.group(0).strip()
    word = re.fullmatch(r"([上中下])巻?|([前中後])編", said)
    if word:
        return word.group(1) or word.group(2)
    digits = re.search(r"\d+(?:\.\d+)?", said)
    if not digits or "." in digits.group(0):
        return None
    return int(digits.group(0))
