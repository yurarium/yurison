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
SEPARATORS = re.compile(r"[/／、,，・･]")

# Credit roles, stripped from the front of a part. `作画：彩乃浦助` is one person, not a person
# called 作画：彩乃浦助, and `原作` on its own is not a person at all.
ROLES = ("原作", "作画", "漫画", "キャラクター原案", "キャラクターデザイン", "原案", "構成",
         "ストーリー", "シナリオ", "イラスト", "企画", "監修", "脚本", "編集", "著者", "著",
         "作", "画", "story", "art", "Story", "Art")
ROLE_HEAD = re.compile(r"^\s*(?:%s)\s*[:：]?\s*" % "|".join(map(re.escape, ROLES)))
ROLE_ONLY = re.compile(r"^\s*(?:%s)\s*[:：]?\s*$" % "|".join(map(re.escape, ROLES)))

# A role label appearing mid-string after whitespace starts a new credit: `原案：士郎正宗　漫画：
# 六道神士`. This is the only case where whitespace splits, and it splits because of the label.
ROLE_BREAK = re.compile(r"[\s　]+(?=(?:%s)\s*[:：])" % "|".join(map(re.escape, ROLES)))

# The label can also end up on the WRONG end of a part, when the credit separated roles with ／
# rather than a colon: `原作／宮澤伊織　作画／水野英多` splits into `宮澤伊織　作画` and `水野英多`.
# Only multi-character roles are stripped here — a lone 作 or 画 after a space is more likely to be
# the tail of somebody's pen name than a credit.
ROLE_TAIL = re.compile(r"[\s　]+(?:%s)\s*$"
                       % "|".join(re.escape(r) for r in ROLES if len(r) > 1))

MASK = "\ue000"  # private-use stand-in for a separator that must survive the split

BRACKETS = [("（", "）"), ("(", ")"), ("〔", "〕"), ("【", "】"), ("[", "]")]
BRACKETED = re.compile(r"[（(〔【\[]([^）)〕】\]]*)[）)〕】\]]")

# Imprint and publisher notes that ride along inside a bracket and are never part of a name.
IMPRINT = re.compile(r"刊$|文庫|新書|書房|書店|出版|社$|MF|GA|富士見|角川|講談|集英|小学館|"
                     r"KADOKAWA|クリエイティブ|編集部|STUDIO|studio|FiFS|Lab")


def _mask_brackets(s):
    """Hide separators inside brackets behind MASK so the split cannot cut a bracketed span in
    half. Restored by split_authors once the splitting is done."""
    out, depth, buf = [], 0, []
    openers = {a for a, _ in BRACKETS}
    closers = {b for _, b in BRACKETS}
    for c in s:
        if c in openers:
            depth += 1
        elif c in closers and depth:
            depth -= 1
        out.append(MASK if (depth and SEPARATORS.match(c)) else c)
    return "".join(out)


def split_authors(credit):
    """A credit line to a list of (name, stated_reading_or_None).

    The reading is only ever non-None for the bracketed-kana case described in the module docstring.
    """
    if not credit:
        return []
    masked = _mask_brackets(str(credit))
    parts = []
    for chunk in SEPARATORS.split(masked):
        parts.extend(ROLE_BREAK.split(chunk))
    out, seen = [], set()
    for raw in parts:
        p = raw.replace(MASK, "・").strip()
        if not p or ROLE_ONLY.match(p):
            continue
        p = ROLE_TAIL.sub("", ROLE_HEAD.sub("", p)).strip()
        name, reading = _peel_bracket(p)
        name = name.strip(" 　:：")
        if not name or ROLE_ONLY.match(name):
            continue
        # A part with no Japanese and no Latin left is punctuation, not a person.
        if not (kana.has_kana(name) or kana.has_kanji(name) or kana.has_latin(name)):
            continue
        if name in seen:
            continue
        seen.add(name)
        out.append((name, reading))
    return out


def _peel_bracket(part):
    """Split `博（ひろ）` into a name and a reading; strip `宮澤伊織(早川書房刊)` down to the name.

    A bracket holding pure kana after a head that is not pure kana is a furigana gloss — the
    platform printing the reading. Anything else in a bracket is an imprint, a studio or a note,
    and belongs to neither the name nor the reading.
    """
    m = BRACKETED.search(part)
    if not m:
        return part, None
    inner = m.group(1).strip()
    head = (part[:m.start()] + part[m.end():]).strip()
    if not head:
        return part, None
    if inner and not IMPRINT.search(inner) and kana.kana_only(inner) and not kana.kana_only(head):
        return head, kana.to_katakana(inner)
    return head, None


def load(build_dir, feeds=("feed/current.json", "feed/2026-07.json")):
    """Return (authors, titles, credits) — sorted name lists plus the raw credit strings.

    `credits` is kept because pass 0 needs to know which page a name was read from, and the credit
    string is the only link back to the work that carried it.
    """
    build = pathlib.Path(build_dir)
    titles, authors, credits = {}, {}, {}
    rows = []

    series = json.loads((build / "series.json").read_text(encoding="utf-8"))
    rows.extend(series.get("series") or [])
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
        for name, reading in split_authors(credit):
            slot = authors.setdefault(name, {"reading": None, "urls": []})
            if reading and not slot["reading"]:
                slot["reading"] = reading
            if url:
                slot["urls"].append(url)
    return authors, titles, credits


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
