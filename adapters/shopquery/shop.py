#!/usr/bin/env python3
"""Ask a shop what it stocks for a work this database already holds, and read the answer.

WHY THIS EXISTS. Every retailer route in this project is shelf-first: `cmoa.py` enumerates
コミックシーモア genre 37 and `bookwalker-yuri.yaml` enumerates BOOK☆WALKER tag 14, and each takes
what it finds there. Neither can ask the question the other way round. That question is "does this
shop stock volumes for a work I already hold", and the BOOK☆WALKER capture's own header records
what the shelf misses without it: コンカフェ嬢は恋を着る is stocked, is marked 完結, is in this
database, and is not on tag 14 at all, because the tag is applied by hand.

WHAT THE SHOP IS BEING ASKED, AND WHAT IT IS NOT. It is asked what it stocks. It is not asked to
classify anything. The works put to it are already admitted on their own evidence, so this route
adds no admission and no `marketing_label`: DEFINITIONS §4 names a shop's shelf as never
publisher-side, and stock is weaker than a shelf. A retailer is Tier C, discovery only
(REQUIREMENTS §1), so what this module produces is a lead and the bibliography produces the record.

WHY BOOK☆WALKER AND NOT コミックシーモア. cmoa states an ISBN and would be the better shop, and its
search is closed to us: https://www.cmoa.jp/robots.txt carries `Disallow: /search/result/` under
`User-agent: *`, which is the endpoint `cmoa.shelf_url` builds. BOOK☆WALKER's robots.txt disallows
/ex/problem/, /entry-list/, /member/, /history/delete/, /history/parts/, /prx/ma/ and sample links,
and none of those is /search/. So the permitted shop is the one that states no number, which is
what `adapters/madb/by_shop_query.py` has to work around and why it joins on a title and a person.

A TITLE IDENTIFIES NOTHING, so `classify` below refuses to call a title match a join. `トワ・エ・モア`
is a 1996 コンパス anthology and a 2024 講談社 series at once, and `citrus+` returned an unrelated
2007 book on a bare title search. A shop hit is a join when the shop's own credit for the volume
agrees with the credit this database holds, and a candidate otherwise. Both are recorded, and the
candidate is not joined to anything.

SEARCHING BY THE AUTHOR IS THE STRONGER QUERY and is tried first, because an author search that
returns an agreeing title has agreed twice. The counter-case is in the same answer: 卯花りりか
returns コンカフェ嬢は恋を着る and also なかよし, the magazine, and only the first has a title this
database recognises. A title search is the fallback for a work whose author the shop spells
differently or does not print.
"""
import pathlib
import re
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import identity                                                                # noqa: E402

BASE = "https://bookwalker.jp"

# The マンガ store. `qcat=2` is the same restriction `bookwalker-yuri.yaml` captured the shelf
# under, so a hit here and a row there are the same kind of object. Without it the answer mixes in
# light novels and magazines, which are not the volumes this route is looking for.
SEARCH = BASE + "/search/?word={word}&qcat=2"

# One result tile. The shop repeats the same block for every hit, so the document is split on the
# opening marker and each piece is read on its own. Reading the whole page with one pattern per
# field pairs the first title with the third label the moment a tile omits one.
TILE = '<li class="m-tile">'

_SERIES = re.compile(r'data-series-id="(\d+)"')
_TITLE = re.compile(r'<p class="m-book-item__title">.*?title="([^"]*)"', re.S)
_LABEL = re.compile(r'<p class="m-book-item__label">(.*?)</p>', re.S)
_TAG = re.compile(r'<span class="a-tag-([a-z]+)">([^<]*)</span>')
_COUNT = re.compile(r'<span class="ico-txt">\s*シリーズ([\d,]+)冊')
_VOLUME = re.compile(r'href="(https://bookwalker\.jp/de[0-9a-f-]+/)"')

# The 作品情報 table on a volume's own page. Each row is a label and a value.
#
# 底本発行日 IS THE FIELD THIS ROUTE CAME FOR, and it is the shop answering the question directly.
# It is the publication date of the PRINT edition the file was made from, so a volume stating one
# is the shop saying a printed book exists, with no bibliography involved. `bookwalker-volumes.yaml`
# measured it on 276 of 870 volumes and this capture finds it on 47 of the first 100, and the
# difference between the two halves is the point: a hit with no 底本発行日 is a digital-only edition
# and there is no print run for MADB to hold.
#
# 配信開始日 is the day the FILE went on sale and is not a publication of the work. The same capture
# measured 115 of 276 volumes delivered before the print edition and 38 after it by up to 4,471
# days, so it bounds nothing in either direction. It is read and named as what it is.
_ROW = re.compile(r'<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>', re.S)

# The shop marks a finished series on the tile. `bookwalker.py` reads the same fact off a series
# page and off a volume list; this is the third place it is printed and the cheapest to read,
# because it arrives with the search answer and costs no request.
FINISHED = "完結"


def query_url(word):
    """The search address for one query term."""
    return SEARCH.format(word=urllib.parse.quote(str(word or "")))


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def tiles(html):
    """Every result the search page printed, in the order it printed them.

    A field the tile does not carry is absent instead of guessed, which is the rule
    `bookwalker-yuri.yaml` states about its own rows: `author: null` there means the listing
    printed none, and the same is meant here.
    """
    out = []
    for part in str(html or "").split(TILE)[1:]:
        title = _TITLE.search(part)
        if not title:
            continue
        series = _SERIES.search(part)
        label = _LABEL.search(part)
        count = _COUNT.search(part)
        tags = {v.strip() for _k, v in _TAG.findall(part)}
        out.append({
            "series_id": series.group(1) if series else None,
            "series_url": f"{BASE}/series/{series.group(1)}/list/" if series else None,
            "title_listed": _text(title.group(1)),
            "imprint": _text(label.group(1)) or None if label else None,
            "volumes_stated": int(count.group(1).replace(",", "")) if count else None,
            "completed_marker": FINISHED in tags,
            "volume_urls": _VOLUME.findall(part),
        })
    return out


def details(html):
    """`{author, imprint, publisher, printed, delivered}` from a volume's own page.

    The credit is the field this route rests on. The tile carries no author at all, which is the
    same absence `bookwalker-yuri.yaml` records about the shelf listing, so confirming who drew a
    book costs one request per hit and there is no cheaper answer. `printed` arrives on the same
    request and answers the question the route was asked.
    """
    got = {"author": None, "imprint": None, "publisher": None, "printed": None, "delivered": None}
    wanted = {"著者": "author", "レーベル": "imprint", "出版社": "publisher",
              "底本発行日": "printed", "配信開始日": "delivered"}
    for label, value in _ROW.findall(str(html or "")):
        key = wanted.get(_text(label))
        if key and got[key] is None:
            got[key] = _text(value) or None
    return got


# THE SHOP'S SEPARATOR BETWEEN TWO PEOPLE IS THE ROLE BRACKET AND NOTHING ELSE. BOOK☆WALKER writes
# a collaboration as `桃田 ロウ(原作) 文尾文(作画) 塩こうじ(キャラクター原案)`, with a space where
# every other source in this project writes a slash. `names.inputs.split_authors` reads the slash,
# the comma and the `作画：` form, and it read that line as ONE person called 桃田ロウ文尾文塩こうじ,
# who agrees with nobody. Three of the first twelve works asked were refused that way, each of them
# a work whose credits plainly agree: 妖怪殲滅のサイコリリー, アイドラトリィ and the line above.
#
# So the bracket is turned into the slash the project already reads. This translates one source's
# spelling into the project's separator; it does not re-read the credit, which stays
# `identity.people`'s job (STANDING-INSTRUCTIONS §3).
_ROLE = re.compile(r"[（(][^）)]{1,24}[）)]")


def names(credit):
    """The comparison keys for a credit line, from `identity.people`.

    ONE PRODUCER OF THIS FACT, and this is a wrapper over it and not a second copy. §3 is the
    reason: `identity.people` is what joins a serialisation to its book run, and a credit line
    parsed twice puts the same person in two forms and the join fails on the works with the most
    evidence.
    """
    return identity.people(_ROLE.sub(" / ", str(credit or "")))


def title_agrees(shop_title, our_title):
    """Whether the shop's series title and ours name the same work.

    `identity.fold` strips bracketed matter, which is what makes コンカフェ嬢は恋を着る（ＦＵＺ
    コミックス） fold onto コンカフェ嬢は恋を着る: the bracket carries the imprint the shop appends
    to a series name, and `bookwalker-yuri.yaml` records that habit as `imprint_in_title`.

    Containment either way, because the shop keeps a marketing subtitle the platform drops and the
    platform sometimes keeps one the shop drops. Equality alone refused ロンリーガールに花束を
    against its shelf form on the first run.
    """
    a, b = identity.match_key(shop_title), identity.match_key(our_title)
    if not a or not b:
        return False
    return a == b or a.startswith(b) or b.startswith(a)


def classify(shop_credit, our_credit):
    """How much of a hit this is, once `pick` has established that the titles agree.

    `creator` means the shop's credit and ours share a person, which is the rule
    `adapters/identity.py` applies to every join between the web and print populations, and it is
    the only value `by_shop_query.py` will act on.

    `title-only` is recorded and joined to nothing. A wrong join attaches one work's volumes to
    another and is hard to see afterwards, so the refusal is stored with its evidence instead of
    being dropped: a shop and a database disagreeing about who drew a book is a lead about one of
    them (STANDING-INSTRUCTIONS §13).

    A shop that printed no credit cannot agree, and neither can a work this database credits to
    nobody. Treating an empty set as agreement turns the rule back into the title match it exists
    to refuse, which is the mistake `by_title.agreeing` records against itself.
    """
    ours, theirs = names(our_credit), names(shop_credit)
    if ours and theirs and (ours & theirs):
        return "creator"
    return "title-only"


def pick(rows, our_title):
    """The results whose title agrees with ours, keyed on the series so a work appears once.

    A search answers with several volumes of one series and with other series entirely. Both are
    real: 卯花りりか returns コンカフェ嬢は恋を着る and なかよし, and only the first is the work
    asked about.
    """
    out, seen = [], set()
    for t in rows:
        if not title_agrees(t["title_listed"], our_title):
            continue
        key = t["series_id"] or t["title_listed"]
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out
