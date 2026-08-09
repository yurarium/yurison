#!/usr/bin/env python3
"""The two name sets this job resolves, pulled out of the build outputs.

NAMES-PLAN §2 counts 965 distinct web authors and 1055 distinct web titles. Those numbers come from
data/build/series.json alone; the feed files add a handful more (works that appeared in a release
window without yet becoming a series row), so the sets here are a superset and the plan's figures
remain the denominator worth reporting against.

The 302 print works in data/build/index.json are deliberately NOT here. §2 is emphatic about why:
MADB and openBD already carry their readings in `title.yomi` and `collationkey`, sitting on disk in
madb-cache/ and openbd-cache/, so they are a re-parse rather than research. Spending a single
network request on them would be spending it twice.

SPLITTING THE AUTHOR STRING is where the care goes, because the string is a credit line, not a
name. `原作／宮澤伊織(早川書房刊)　作画／水野英多　キャラクター原案／shirakaba` is three people, two
role labels, and a publisher's imprint note. Splitting it naively on the separators §2 used
produces `原作`, `宮澤伊織(早川書房刊)` and `SBクリエイティブ刊)` — a role word with no name attached,
a name welded to an imprint, and a fragment of a parenthesis that got cut in half. All three would
then be looked up as though they were people, which wastes requests on the first and third and
guarantees a miss on the second.

So: bracketed spans are masked before splitting (they contain separators of their own), role labels
are stripped from the front of each part, and parts that are nothing but a role word are dropped.

ONE PARENTHETICAL IS NOT NOISE. 博（ひろ） is a kanji name with its own reading printed beside it —
the platform stating the answer we would otherwise pay a search API for. Any parenthetical that is
pure kana following a non-kana head is kept as a `stated` reading rather than discarded, which is
the entire pass-0 furigana yield §4a said did not exist. It found none in ruby markup; it did not
look in brackets.
"""
import json
import pathlib
import re

from . import credits
from . import kana
from . import key
# THE ONE INTERPUNCT CLASS AND THE ONE FOLD, borrowed rather than spelled again. `interpunct.py`
# imports nothing from here, so there is no cycle, and a second copy of either is the shape §3
# counts seven shipped bugs from: this file already carries the interpunct in two regexes and they
# have to keep agreeing with the module that rules on it.
from .interpunct import INTERPUNCT, SEVERAL

# Splitting only ever happens on these. A space is NOT among them: 森島 明子 and 月夜 涙 are single
# people whose family and given names are spaced, and splitting there would double the author count
# with halves of names.
#
# THE AMPERSAND JOINS TWO PEOPLE AND NEVER SITS INSIDE ONE, measured across the whole corpus before
# it was admitted. Four credit fields carry one and every one of them is two people: `iimAn&惟丞`,
# `大島永遠&大島智`, `ひあるろん＆達磨` and `こんぱる＆ふじしまペポ`. That is the counter-case the
# interpunct argument below turns on, and here it does not exist: no pen name in the store, in the
# works list or in any release row spells itself with an &. So it goes in BOTH lists. Two of these
# were one identifier for two people until this line, which is an address holding two artists.
#
# `&nbsp;` IS THE SHAPE TO WATCH AND IT IS ALREADY HANDLED ELSEWHERE. A rendered-page capture
# handed us `&nbsp;フォローする`, a Follow button; `credits.split_credits` unescapes before it calls
# this, so the entity is a space by the time it arrives and there is no & left to split on. A
# caller that passes raw HTML would get a person called `amp;大島智`, which is why the unescaping
# belongs in front of the splitter and not inside it.
SEPARATORS = re.compile(r"[/／、,，・･&＆]")

# THE SAME LIST WITHOUT THE INTERPUNCT, for a caller that is going to PRINT the parts.
#
# ・ separates people in 矢立肇・富野由悠季 and sits inside a name in さりい・Ｂ, and nothing in the
# string tells the two apart. Which way to be wrong depends on what the answer is for: feeding the
# name store, a wrong split costs one entry nobody looks up, so splitting is right; rendering a
# credit line, it prints half of somebody's name, so it is not. One splitter, one role vocabulary,
# and the single place the two callers genuinely disagree stated as an argument.
SEPARATORS_WHOLE_NAMES = re.compile(r"[/／、,，&＆]")

# Credit roles, stripped from the front of a part. `作画：彩乃浦助` is one person, not a person
# called 作画：彩乃浦助, and `原作` on its own is not a person at all.
#
# WRITTEN OUT RATHER THAN SPELLED FROM CHARACTERS. A class of role kanji reads 協力 and 構成協力
# for free and reads 力 and 成 as roles too, and the credit field is full of pen names built from
# ordinary words. Every entry here was read off a credit this corpus actually carries; the ones
# added late are named in the commit that added them, because a vocabulary that grows by guessing
# is how 石田可奈 came to be filed with キャラクターデザイン as its reading.
ROLES = ("原作", "作画", "漫画", "キャラクター原案", "キャラクターデザイン", "原案", "構成",
         "ストーリー", "シナリオ", "イラスト", "企画", "監修", "脚本", "編集", "著者", "著",
         "作", "画", "story", "art", "Story", "Art",
         # Read off the corpus 2026-08-07, with the count of credits each appears in:
         # 構成協力 1, 協力 1, 原作監修 1, 表紙 1, 校正 2, 編纂 1, 編 1, 絵 5, ネーム 1.
         "構成協力", "原案協力", "作画協力", "協力", "原作監修", "表紙", "ネーム", "校正", "編纂",
         "カバーイラスト", "カバー", "デザイン", "翻訳", "訳", "編", "絵", "文",
         # `ほか著雪子` is an anthology credit: some of the contributors, then the role. The two
         # characters are cataloguing and the name is what follows them.
         "ほか著", "他著",
         # Read off the corpus 2026-08-08: `[話]とい天津`, `[取材協力]御坊`,
         # `[[翻訳協力]][BPS株式会社]` and `[キャラクターデザイン原案]SukeraSparo`. 話 is a single
         # character and so needs a delimiter at the head of a part, which is what stops it taking
         # the first character off a pen name.
         "話", "取材協力", "翻訳協力", "キャラクターデザイン原案")

# ROLES A BRACKET MAY HOLD AND A NAME MAY BEGIN WITH. `[コミック]nishi` states a job and
# `コミックニュータイプ(編)` is a magazine's editorial desk, and a multi-character role needs no
# delimiter at the head of a part, so admitting コミック to `ROLES` turned that magazine into
# `ニュータイプ` credited as art. Inside a bracket the word is the whole content and cannot be the
# start of anything, which is the one context where it is unambiguous. STANDING-INSTRUCTIONS §2:
# the counter-case was in the corpus and the rule was shipped for one round without it.
BRACKET_ROLES = ("コミック",)

# LONGEST FIRST. Python alternation takes the first branch that matches, so `著` ahead of `著者`
# leaves a stray 者 where a name should be, and `編` ahead of `編集` leaves 集.
_ALT = "|".join(re.escape(r) for r in sorted(ROLES, key=len, reverse=True))
_ALT_LONG = "|".join(re.escape(r) for r in sorted(ROLES, key=len, reverse=True) if len(r) > 1)

# ONE ROLE OR SEVERAL, joined the way a credit joins them: `イラスト・漫画`, `表紙 / 漫画`,
# `キャラクター原案・漫画`, `構成協力`. Spelling each compound out as its own entry is what the
# list was doing, and it is why キャラクターデザイン and 構成協力 were missing after a round of
# widening that added four compounds by hand.
ROLE_PHRASE = r"(?:%s)(?:[\s　・･/／]+(?:%s))*" % (_ALT, _ALT)
ROLE_PHRASE_LONG = r"(?:%s)(?:[\s　・･/／]+(?:%s))*" % (_ALT_LONG, _ALT_LONG)

# A SINGLE-CHARACTER ROLE AT THE HEAD NEEDS A DELIMITER, and a longer one does not. `著：山田` and
# `作画／彩乃浦助` are notation; a bare 作 or 画 or 絵 opening a part is far likelier to be the first
# character of a pen name, and stripping it would hand the store 田ハジメ for 作田ハジメ. Nothing in
# the corpus is damaged by the loose rule today, which is exactly the state a vocabulary is in
# before it is widened.
ROLE_HEAD = re.compile(r"^\s*(?:(?:%s)\s*[:：/／]|(?:%s)\s*[:：]?)\s*"
                       % (ROLE_PHRASE, ROLE_PHRASE_LONG))
_ALT_BRACKET = "|".join(re.escape(r) for r in
                       sorted(ROLES + BRACKET_ROLES, key=len, reverse=True))
_ROLE_PHRASE_BRACKET = r"(?:%s)(?:[\s　・･/／]+(?:%s))*" % (_ALT_BRACKET, _ALT_BRACKET)
ROLE_ONLY = re.compile(r"^\s*(?:%s)\s*[:：]?\s*$" % _ROLE_PHRASE_BRACKET)

# A role label appearing mid-string after whitespace starts a new credit: `原案：士郎正宗　漫画：
# 六道神士`. This is the only case where whitespace splits, and it splits because of the label.
ROLE_BREAK = re.compile(r"[\s　]+(?=(?:%s)\s*[:：])" % ROLE_PHRASE)

# The label can also end up on the WRONG end of a part, when the credit separated roles with ／
# rather than a colon: `原作／宮澤伊織　作画／水野英多` splits into `宮澤伊織　作画` and `水野英多`.
# Only multi-character roles are stripped here — a lone 作 or 画 after a space is more likely to be
# the tail of somebody's pen name than a credit.
ROLE_TAIL = re.compile(r"[\s　]+(?:%s)\s*$" % ROLE_PHRASE_LONG)

# A ROLE IN A BRACKET CLOSES A CREDIT, so the space after it separates two people:
# `冬眠結(漫画) 橙々(原作)` is two, and the splitter had no separator to see. A space is not a
# separator anywhere else here and must not become one: 三松　真由美 and 高坂 はしやん are single
# people with a space inside them, and both appear in fields of exactly this shape. What licenses
# the split is the bracket, and only when what is in it is a role.
ROLE_BRACKET_BREAK = re.compile(r"([（(〔【\[]([^）)〕】\]]*)[）)〕】\]])[\s　]+")

# `ほか` closes a credit line that names some of its contributors and stops. The bibliography
# writes an anthology as `浅見百合子 ほか` and, where it used the slash, as `… / ほか`. A space is
# not a separator here by design, so without this the whole string is one person called
# "浅見百合子 ほか". Nobody is called that, so it matched nobody, and it refused a join to the
# ニコニコ page that names 浅見百合子 first among nine. It fires only after whitespace or on a part
# of its own, so a pen name with those two characters inside it is untouched.
OTHERS_TAIL = re.compile(r"[\s　]+(?:ほか|他)\s*$")

MASK = "\ue000"  # private-use stand-in for a separator that must survive the split
BREAK = "\ue001"  # and one for a boundary the string does not punctuate: see ROLE_BRACKET_BREAK

# Strings that arrive in the author position without being people. `ヨン / 読切` is one author and a
# format tag separated by the same slash the credits use, so the tag becomes an "author" and would
# get a pass 3 search query spent on the word "one-shot". These are dropped at the source rather
# than filtered later, so no pass ever has to know about them.
NOT_A_NAME = {"読切", "読み切り", "連載", "新連載", "完結", "番外編", "特別編", "出張版", "前編",
              "後編", "中編", "無料", "試し読み", "オリジナル", "不明", "作者不明", "その他",
              "ほか", "他"}

BRACKETS = [("（", "）"), ("(", ")"), ("〔", "〕"), ("【", "】"), ("[", "]")]
BRACKETED = re.compile(r"[（(〔【\[]([^）)〕】\]]*)[）)〕】\]]")

# Imprint and publisher notes that ride along inside a bracket and are never part of a name.
IMPRINT = re.compile(r"刊$|文庫|新書|書房|書店|出版|社$|MF|GA|富士見|角川|講談|集英|小学館|"
                     r"KADOKAWA|クリエイティブ|編集部|STUDIO|studio|FiFS|Lab")


def _mask_brackets(s):
    """Hide separators inside brackets behind MASK so the split cannot cut a bracketed span in
    half. Restored by split_authors once the splitting is done."""
    out, depth = [], 0
    openers = {a for a, _ in BRACKETS}
    closers = {b for _, b in BRACKETS}
    for c in s:
        if c in openers:
            depth += 1
        elif c in closers and depth:
            depth -= 1
        out.append(MASK if (depth and SEPARATORS.match(c)) else c)
    return "".join(out)


def _break_after_role_brackets(masked):
    """Insert a boundary where a role bracket is followed by a space, and nowhere else."""
    def sub(m):
        inner = m.group(2).replace(MASK, "・").strip()
        return m.group(1) + BREAK if ROLE_ONLY.match(inner) else m.group(0)
    return ROLE_BRACKET_BREAK.sub(sub, masked)


# Whitespace, colons and the separators a role label arrives glued to, cleaned off a captured role
# so that `原作／` and `原作：` and ` 原作` all report the same word.
ROLE_EDGE = re.compile(r"^[\s　:：/／・･]+|[\s　:：/／・･]+$")


def _label(text):
    return ROLE_EDGE.sub("", str(text or "").replace(MASK, "・")) or None


def _roles_on(part):
    """(this part's role, the next part's role) for one split chunk.

    THE SPLITTER ALREADY KNOWS EVERY PLACE A LABEL SITS, so reading one off adds no vocabulary and
    no second traversal. `原作：士郎正宗` puts it at the head and `冬眠結(漫画)` inside a bracket, and
    both belong to the name beside them.

    A TAIL LABEL BELONGS TO THE CREDIT AFTER IT, which is the whole reason `ROLE_TAIL` exists.
    `原作／宮澤伊織　作画／水野英多` splits on the slash into `原作`, `宮澤伊織　作画` and `水野英多`,
    so 作画 arrives glued to the END of 宮澤伊織's chunk while labelling 水野英多. Reading it as
    宮澤伊織's role puts every person in that field under the next person's job: the first version of
    this function credited 宮澤伊織 with 作画 and left shirakaba with nothing.
    """
    m = ROLE_HEAD.match(part)
    if m:
        return _label(m.group(0)), None
    for b in BRACKETED.finditer(part):
        inner = b.group(1).replace(MASK, "・").strip()
        if ROLE_ONLY.match(inner):
            return _label(inner), None
    tail = ROLE_TAIL.search(part)
    return None, (_label(tail.group(0)) if tail else None)


def split_credits_detail(credit, interpunct=True, ruled=None):
    """A credit line to a list of (name, stated_reading_or_None, role_or_None).

    WHY THE ROLE IS RETURNED AT ALL. A credit becomes a reference when a work links to the person it
    names, and one person is 原作 on one work and 作画 on another. So the role belongs on the EDGE
    between the work and the credit, and it can only get there if the splitter that finds the name
    also says which label it took off. `split_authors` is this function with the role dropped, so
    the identity a page is built on and the name the store is keyed on come out of one traversal.
    Deriving the role in a second pass over the same string is the shape STANDING-INSTRUCTIONS §3
    counts seven shipped bugs from.

    The reading is only ever non-None for the bracketed-kana case described in the module docstring.

    `interpunct=False` keeps ・ inside a name instead of treating it as a separator. See
    SEPARATORS_WHOLE_NAMES for which caller wants which, and why the answer differs.

    `ruled` IS THE THIRD ANSWER AND THE ONLY ONE MADE OF EVIDENCE. It is `interpunct.settled`'s map
    from a folded name to `one` or `several`, and it overrides the flag for the names in it, in both
    directions. The two-answer version cut seven people in half for the store: くろば and Ｕ each
    had a record and a registry identifier, and `Kuro Ba, U` was on the site under that artist's own
    work. See `adapters/names/interpunct.py` for what decides it and, more to the point, for the
    evidence that may not decide it.

    A name the map says nothing about falls back to the flag, so a caller passing no map behaves
    exactly as it did and a string nobody has settled is treated no worse than before.

    THE INTERPUNCT IS TAKEN OUT AFTER THE ROLE COMES OFF, not before. `[作・画]ステファン・セジク`
    holds one ・ inside a role bracket and one inside a name, and a `whole` lookup done on the raw
    part would be looking up a string with `[作・画]` still stuck to the front of it.
    """
    if not credit:
        return []
    # A DOUBLED DELIMITER IS STILL ONE DELIMITER, normalised here so that every reader below
    # sees one. MADB writes `[[著]]椿木とりか` and `[[翻訳協力]][BPS株式会社]`, and against the
    # doubled form `_roles_on` found no role and `_peel_bracket` found no name, so one company
    # credited on two works vanished from the byline in every language. `openbd_reading.credit_parts`
    # had normalised this since it was written and this traversal had not, which is one notation
    # with two readers (STANDING-INSTRUCTIONS §3).
    credit = re.sub(r"\[+", "[", re.sub(r"\]+", "]", str(credit)))
    masked = _break_after_role_brackets(_mask_brackets(credit))
    # ALWAYS THE LIST WITHOUT THE INTERPUNCT. The ・ is dealt with below, on the name and not on the
    # part, so that `whole` can be asked about the string it holds.
    seps = SEPARATORS_WHOLE_NAMES
    parts = []
    for chunk in re.split(r"%s|%s" % (seps.pattern, BREAK), masked):
        parts.extend(ROLE_BREAK.split(chunk))
    out, seen = [], set()
    # A label the previous chunk ended with, or a chunk that was nothing but a label. Either way it
    # names the job of the credit that comes next, and it is spent on that one credit rather than
    # carried down the rest of the field: `原作／A／B` says what A did and says nothing about B.
    carried = None
    for raw in parts:
        p = raw.replace(MASK, "・").strip()
        if not p:
            continue
        if ROLE_ONLY.match(p):
            carried = _label(p)
            continue
        role, ahead = _roles_on(p)
        role, carried = role or carried, ahead
        p = OTHERS_TAIL.sub("", ROLE_TAIL.sub("", ROLE_HEAD.sub("", p))).strip()
        name, reading = _peel_bracket(p)
        name = name.strip(" 　:：")
        if not name or ROLE_ONLY.match(name) or name in NOT_A_NAME:
            continue
        # A part with no LETTERS in it is punctuation, not a person. This asked for kana, kanji or
        # Latin and so dropped four Korean pen names credited on two anthologies, which is a
        # question about the script somebody's name is written in rather than about whether it is a
        # name. `isalpha` answers the question the comment was already asking.
        if not any(ch.isalpha() for ch in name):
            continue
        # A CHAPTER IS NOT A PERSON, AND IT HAS LETTERS IN IT. The clause above catches a bare
        # `#1(1)`; it walks past `１冊目：叔母さんは神絵師`, which is chapter 1 of
        # 新刊100億冊ください and reached us because コミックDAYS prints the newest chapter where a
        # page title puts the author. `credits.is_a_person` states the rule, and it is asked HERE
        # because this is the splitter every consumer goes through: the works list, the naming
        # passes and the credit registry each had their own opinion about it, two of the three
        # never asked, and c00268 was published at credit/c00268/ with a person's page around a
        # chapter title.
        if not credits.is_a_person(name):
            continue
        for one in _interpunct_parts(name, interpunct, ruled):
            if one in seen:
                continue
            seen.add(one)
            out.append((one, reading, role))
    return out


def _interpunct_parts(name, interpunct, ruled):
    """`name` as one name or as the people its ・ separates.

    A NAME THE EVIDENCE SETTLED IS TREATED THE SAME WAY WHOEVER IS ASKING, which is the point of
    `ruled`: it is a finding about that string and not a preference about this call. Where nothing
    settled it the old two-answer behaviour stands, so a caller that prints keeps the ・ and a
    caller feeding the store splits on it, and both are as wrong as they were before and no worse.
    """
    if not INTERPUNCT.search(name):
        return [name]
    said = (ruled or {}).get(key.fold(name))
    apart = interpunct if said is None else (said == SEVERAL)
    if not apart:
        return [name]
    return [p for p in (x.strip() for x in INTERPUNCT.split(name)) if p]


def split_authors(credit, interpunct=True, ruled=None):
    """A credit line to a list of (name, stated_reading_or_None).

    The role the splitter took off is available from `split_credits_detail`, which this wraps.
    """
    return [(n, r) for n, r, _role in split_credits_detail(credit, interpunct, ruled)]


def _is_notation(inner):
    """Whether a bracket holds cataloguing rather than a name or a reading.

    A ROLE, OR THE WORD THAT CLOSES A CREDIT. `[著]嵩乃朔 [ほか]` was read as a name with the
    furigana gloss ホカ, because ほか is kana and follows a head that is not, which is the exact
    shape a printed reading has. It is not one: the bibliography writes an anthology this way and
    the bracket says "and others". `NOT_A_NAME` already holds that word for the splitter, so
    asking it here is one vocabulary rather than two.
    """
    inner = str(inner or "").replace(MASK, "・").strip()
    return bool(inner) and (bool(ROLE_ONLY.match(inner)) or inner in NOT_A_NAME)


def _peel_bracket(part, depth=4):
    """Split `博（ひろ）` into a name and a reading; strip `宮澤伊織(早川書房刊)` down to the name.

    A bracket holding pure kana after a head that is not pure kana is a furigana gloss — the
    platform printing the reading. Anything else in a bracket is an imprint, a studio or a note,
    and belongs to neither the name nor the reading.

    A CREDIT CAN CARRY TWO OF THEM. `壇九（TANJIU)(著者)` is a name, the Latin the artist also goes
    by, and a role, and peeling one bracket left `壇九(著者)`, which is nobody. `depth` bounds the
    peeling so a pathological string cannot loop.

    A DOUBLED DELIMITER IS STILL ONE DELIMITER, and until this line it was two. MADB writes
    `[[著]]椿木とりか` and `[[翻訳協力]][BPS株式会社]`, and against the doubled form the search below
    matched `[[翻訳協力]`, left `][BPS株式会社]` as the head, and the part came back as nothing at
    all: a company credited on two works vanished from the byline in every language. The other
    doubled shape, `[上田香子][訳]`, peeled the NAME's bracket first and returned `[訳]` as the
    person, so a reader met a credit called "translation". `openbd_reading.credit_parts` had
    normalised this since it was written and this traversal had not, which is one notation with two
    readers (STANDING-INSTRUCTIONS §3).

    A NAME ALONE IN A BRACKET KEEPS ITS CONTENT. `[BPS株式会社]` is how MADB writes a name it took
    from a Latin catalogue, and returning the brackets with it hands the store a key nothing is
    filed under.
    """
    # Notation brackets first and wherever they sit, because which bracket holds the name is not
    # decided by which comes first: `[上田香子][訳]` puts the person in the leading one.
    stripped = BRACKETED.sub(
        lambda m: "" if _is_notation(m.group(1)) else m.group(0), part).strip()
    if stripped:
        part = stripped
    whole = BRACKETED.fullmatch(part)
    if whole and whole.group(1).strip():
        part = whole.group(1).strip()
    m = BRACKETED.search(part)
    if not m:
        return part, None
    inner = m.group(1).strip()
    head = (part[:m.start()] + part[m.end():]).strip()
    if not head:
        return part, None
    # A ROLE IS NOT A READING, and キャラクターデザイン is kana all the way through. 石田可奈 was
    # filed with キャラクターデザイン as the reading a platform had stated for it, which is a role
    # label printed where a furigana gloss goes. Anything the role vocabulary recognises is
    # notation, whatever script it is in.
    reading = (kana.to_katakana(inner)
               if (inner and not ROLE_ONLY.match(inner) and not IMPRINT.search(inner)
                   and kana.kana_only(inner) and not kana.kana_only(head))
               else None)
    if depth > 1 and BRACKETED.search(head):
        deeper, deeper_reading = _peel_bracket(head, depth - 1)
        return deeper, reading or deeper_reading
    return head, reading


# WHERE A CREDIT FIELD LIVES, as (file, the key the rows hold it under). Four collections, and the
# two at the end were missing for as long as this function existed: `index[].c` is the byline the
# catalogue tab draws and `works[].creator` is the one the 発売 tab draws, so the passes that
# research names were never shown two of the four places a reader meets one. 579 people the
# interface renders had no record in the store on 2026-08-09, and every measure of the naming work
# is taken over the store, so the number that should have said so was blind in the same place.
#
# TITLES ARE STILL SERIES AND THE FEEDS, WHICH IS THE OTHER HALF OF THE DECISION. NAMES-PLAN §2 is
# emphatic that the print half's TITLES are a re-parse of madb-cache and openbd-cache rather than
# research, and no external request may be spent on them. That argument is about a title's `yomi`,
# which those caches hold for every book; it does not reach a person credited on a book whose
# `collationkey` openBD never registered, and the residue of those is exactly what the project
# owner's 2026-08-09 ruling sends to Wikidata.
CREDIT_ROWS = (("index.json", None, "c"), ("works.json", "works", "creator"))


def _rows(build, file, section):
    p = build / file
    if not p.exists():
        return []
    doc = json.loads(p.read_text(encoding="utf-8"))
    got = doc if section is None else doc.get(section)
    return got if isinstance(got, list) else []


def load(build_dir, feeds=None):
    """Return (authors, titles, credits, by_title).

    THE MONTHS ARE FOUND, NOT LISTED. This defaulted to `("feed/current.json", "feed/2026-07.json")`,
    naming one month by hand, so every month after July 2026 was invisible to the name passes and
    nothing would have said so: the passes would simply have stopped seeing new works, gradually,
    with the count of names to fix looking healthy the whole way down. A default that goes stale by
    the calendar is the same failure as reading a rolling window and calling it the corpus.

    AND THE COLLECTIONS ARE FOUND THE SAME WAY, for the same reason one level up. See `CREDIT_ROWS`:
    a credit field the interface draws and this function never reads is a person nothing will ever
    look up, and the shape of that failure is identical to naming one month by hand.

    `credits` is kept because pass 0 needs to know which page a name was read from, and the credit
    string is the only link back to the work that carried it. `by_title` maps a Japanese title to
    the authors credited on it, which is what lets pass 2 join a database's ROMANISED credit to our
    Japanese one — "MIZUNO Eita" cannot be string-matched to 水野英多, so the work is the only join
    available.
    """
    build = pathlib.Path(build_dir)
    titles, authors, credits, by_title = {}, {}, {}, {}
    rows = []

    series = json.loads((build / "series.json").read_text(encoding="utf-8"))
    rows.extend(series.get("series") or [])
    if feeds is None:
        feeds = ["feed/current.json"] + [f"feed/{p.name}" for p in
                                         sorted((build / "feed").glob("[0-9]*.json"))]
    for f in feeds:
        p = build / f
        if p.exists():
            rows.extend(json.loads(p.read_text(encoding="utf-8")).get("releases") or [])

    # PEOPLE ONLY FROM THESE TWO, and the row's title is deliberately not taken. A catalogue row is
    # a print work, and `titles` is what pass 2 spends requests on.
    people_only = [(r, key) for file, section, key in CREDIT_ROWS
                   for r in _rows(build, file, section)]

    for r, credit_key in [(r, "author") for r in rows] + people_only:
        work = r.get("work") if credit_key == "author" else None
        credit, url = r.get(credit_key), r.get("url")
        if work:
            titles.setdefault(work, url)
        if not credit:
            continue
        credits.setdefault(credit, []).append(url)
        names = split_authors(credit)
        if work:
            for name, _ in names:
                if name not in by_title.setdefault(work, []):
                    by_title[work].append(name)
        for name, reading in names:
            slot = authors.setdefault(name, {"reading": None, "urls": []})
            if reading and not slot["reading"]:
                slot["reading"] = reading
            if url:
                slot["urls"].append(url)
    return authors, titles, credits, by_title


def plan_baseline(build_dir):
    """The §2 denominator: authors and titles from series.json only, which is what was measured."""
    build = pathlib.Path(build_dir)
    series = json.loads((build / "series.json").read_text(encoding="utf-8")).get("series") or []
    titles = {r["work"] for r in series if r.get("work")}
    authors = set()
    for r in series:
        for name, _ in split_authors(r.get("author")):
            authors.add(name)
    return authors, titles
