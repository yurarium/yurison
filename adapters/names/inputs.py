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

from . import kana

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
         "ほか著", "他著")

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
ROLE_ONLY = re.compile(r"^\s*(?:%s)\s*[:：]?\s*$" % ROLE_PHRASE)

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


def split_credits_detail(credit, interpunct=True):
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
    """
    if not credit:
        return []
    masked = _break_after_role_brackets(_mask_brackets(str(credit)))
    seps = SEPARATORS if interpunct else SEPARATORS_WHOLE_NAMES
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
        # A part with no Japanese and no Latin left is punctuation, not a person.
        if not (kana.has_kana(name) or kana.has_kanji(name) or kana.has_latin(name)):
            continue
        if name in seen:
            continue
        seen.add(name)
        out.append((name, reading, role))
    return out


def split_authors(credit, interpunct=True):
    """A credit line to a list of (name, stated_reading_or_None).

    The role the splitter took off is available from `split_credits_detail`, which this wraps.
    """
    return [(n, r) for n, r, _role in split_credits_detail(credit, interpunct)]


def _peel_bracket(part, depth=4):
    """Split `博（ひろ）` into a name and a reading; strip `宮澤伊織(早川書房刊)` down to the name.

    A bracket holding pure kana after a head that is not pure kana is a furigana gloss — the
    platform printing the reading. Anything else in a bracket is an imprint, a studio or a note,
    and belongs to neither the name nor the reading.

    A CREDIT CAN CARRY TWO OF THEM. `壇九（TANJIU)(著者)` is a name, the Latin the artist also goes
    by, and a role, and peeling one bracket left `壇九(著者)`, which is nobody. `depth` bounds the
    peeling so a pathological string cannot loop.
    """
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


def load(build_dir, feeds=None):
    """Return (authors, titles, credits, by_title).

    THE MONTHS ARE FOUND, NOT LISTED. This defaulted to `("feed/current.json", "feed/2026-07.json")`,
    naming one month by hand, so every month after July 2026 was invisible to the name passes and
    nothing would have said so: the passes would simply have stopped seeing new works, gradually,
    with the count of names to fix looking healthy the whole way down. A default that goes stale by
    the calendar is the same failure as reading a rolling window and calling it the corpus.

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

    for r in rows:
        work, credit, url = r.get("work"), r.get("author"), r.get("url")
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
