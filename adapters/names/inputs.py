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
from facts.credit import INTERPUNCT, SEVERAL                             # noqa: E402

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
# THE SPLITTER MOVED TO `facts/credit`. Turning a credit field into people is that fact, and this
# module also loads the built collections, which is not. These names are re-exported so a caller
# reading the built data still finds what it expects; a caller SPLITTING should ask the fact, which
# applies the interpunct ruling by default.
from facts import credit as _sp                                         # noqa: E402

BRACKETED = _sp.BRACKETED
BRACKETS = _sp.BRACKETS
BRACKET_ROLES = _sp.BRACKET_ROLES
BREAK = _sp.BREAK
IMPRINT = _sp.IMPRINT
MASK = _sp.MASK
NOT_A_NAME = _sp.NOT_A_NAME
OTHERS_TAIL = _sp.OTHERS_TAIL
ROLES = _sp.ROLES
ROLE_BRACKET_BREAK = _sp.ROLE_BRACKET_BREAK
ROLE_BREAK = _sp.ROLE_BREAK
ROLE_EDGE = _sp.ROLE_EDGE
ROLE_HEAD = _sp.ROLE_HEAD
ROLE_ONLY = _sp.ROLE_ONLY
ROLE_PHRASE = _sp.ROLE_PHRASE
ROLE_PHRASE_LONG = _sp.ROLE_PHRASE_LONG
ROLE_TAIL = _sp.ROLE_TAIL
SEPARATORS = _sp.SEPARATORS
SEPARATORS_WHOLE_NAMES = _sp.SEPARATORS_WHOLE_NAMES
split_authors = _sp.split_authors
split_credits_detail = _sp.split_credits_detail

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
