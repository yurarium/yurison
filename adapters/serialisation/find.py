#!/usr/bin/env python3
"""Ask, for a printed book we hold, where it was serialised.

WHAT THIS IS FOR. The previous pass ran platform to shop to ISBN: it read retail links off a
serialisation page and took the numbers to the national bibliography, which brought 862 web works
with no print edition down to 648. This runs the other way. 441 works in the corpus have a printed
volume from 2019 or later and no web address at all, and a book published since the platforms
existed usually ran somewhere first.

THE PUBLISHER SAYS WHO TO ASK, NOT WHERE TO LOOK. The obvious plan is to map each publisher to the
platform it runs and search there. That plan is wrong, and 運命のヤマダダダダダダダダダダ is why:
it is 芳文社's, printed under Manga time KR comics, and 芳文社 runs COMIC FUZ, and the work is on
ニコニコ漫画. ニコニコ漫画 and pixivコミック carry many publishers' serialisations, so a
publisher's own platform is one candidate among several. Both routes below are publisher-blind.

THE TWO ROUTES.

  ニコニコ漫画's own search, `manga.nicovideo.jp/search?q=`, is server-rendered and states the
  title, the author and the work id in the result. It answers about one platform and it answers
  first-hand, so a hit here is the platform speaking (Tier B).

  Web漫画アンテナ's search, `webcomics.jp/search?q=`, covers 96 platforms in one request and is
  the fan-out reducer REQUIREMENTS §5 describes. It is Tier C: it may say a work exists and where,
  and nothing it says becomes a record or settles a join. Its value is that it turns "which of 96
  sites" into "this one address, go and read it".

WHAT SETTLES A JOIN. Not the title. RUNBOOK §11 requires the creator, the publisher or the imprint
to agree, because `トワ・エ・モア` is a 1996 コンパス anthology and a 2024 講談社 series at once.
`agrees` below is that test against a platform page, and it has a second field to work with that
the print-to-print case does not: a ニコニコ work page prints its copyright line, `(C)おにぎり
パクパク/芳文社`, which names the publisher as well as the author. Reading that line belongs to
`nicovideo/releases.py`, which is where this project's one reader of ニコニコ markup lives.

WHAT AN EMPTY ANSWER MEANS. Both sites state "found nothing" in words, so a work that was asked
about and not found is a different state from one nobody asked. `antenna_results` returns that
distinction rather than an empty list, because an empty result set looks exactly like a fetch that
failed (STANDING-INSTRUCTIONS §4).

Every function here takes text and returns data. Fetching is in `sweep.py`.
"""
import html as _html
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from identity import fold, people  # noqa: E402

# ISBD apparatus, as the national bibliography writes a title. `シナモン = Cinnamon : 人外×人間百合
# アンソロジー` is one book; `シナモン` is what a platform calls the work. The parallel title after
# ` = ` and the subtitle after ` : ` are cataloguing, so a search is offered the short form first
# and the full string second.
PARALLEL = re.compile(r"\s+[=:]\s+")
BRACKETED = re.compile(r"[【\[（(][^】\]）)]*[】\]）)]")
VOLUME_TAIL = re.compile(r"\s*(?:第?\s*\d+\s*巻|\d+)\s*$")


def queries(title):
    """The search strings to try for one catalogued title, best first, without repeats.

    Three forms, each earning its place on a measured case:

      the title as catalogued          運命のヤマダダダダダダダダダダ
      without ISBD apparatus           シナモン, from `シナモン = Cinnamon : 人外×人間百合…`
      without a bracketed marker       付き合ってあげてもいいかな, from `…【単話】`

    A search engine matching substrings would need only the shortest, but neither of these does:
    ニコニコ scores whole queries and the antenna wants something close to the work's own title.
    """
    out = []
    for cand in (title or "").strip(), PARALLEL.split(title or "")[0].strip(), \
            BRACKETED.sub("", title or "").strip():
        cand = re.sub(r"\s+", " ", cand)
        if cand and cand not in out:
            out.append(cand)
    return out


def _text(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


# ── ニコニコ漫画 ──────────────────────────────────────────────────────────────────────────────
NICO_ITEM = re.compile(r'<div class="search_result__item">(.*?)(?=<div class="search_result__item">'
                       r'|<div class="footer">)', re.S)
NICO_ID = re.compile(r'href="/comic/(\d+)')
NICO_TITLE = re.compile(r'--title">\s*<a[^>]*>(.*?)</a>', re.S)
NICO_AUTHOR = re.compile(r'--author">(.*?)</div>', re.S)
NICO_UPDATED = re.compile(r'<time datetime="(\d{4}-\d{2}-\d{2})')
NICO_COUNT = re.compile(r"の検索結果：(\d+)")


def nico_results(html):
    """[{comic_id, title, author, updated, url}] from a ニコニコ漫画 search page.

    The zero case is representable: the page says `の検索結果：0` and renders no items, so an empty
    list here means the platform answered and had nothing, which the caller records as such.
    """
    out = []
    for m in NICO_ITEM.finditer(html or ""):
        b = m.group(1)
        cid = NICO_ID.search(b)
        if not cid:
            continue
        t = NICO_TITLE.search(b)
        a = NICO_AUTHOR.search(b)
        u = NICO_UPDATED.search(b)
        out.append({"comic_id": cid.group(1),
                    "title": _text(t.group(1)) if t else "",
                    "author": _text(a.group(1)) if a else "",
                    "updated": u.group(1) if u else None,
                    "url": f"https://manga.nicovideo.jp/comic/{cid.group(1)}"})
    return out


def nico_searched(html):
    """Whether this really is a ニコニコ search page, so an empty result can be believed.

    A 200 carrying an error page, a redirect to the top or a changed template all produce zero
    items and are indistinguishable from an honest nothing. The result summary is the marker that
    the search ran.
    """
    return bool(NICO_COUNT.search(html or ""))


# ── Web漫画アンテナ ───────────────────────────────────────────────────────────────────────────
# Two response shapes, and the second one is easy to miss. A query matching several works renders a
# list of `.entry` blocks; a query matching exactly one renders that work's own page, with an
# author the list form does not carry. Reading only the list shape reports "nothing found" for
# every exact-title hit, which is the whole population this pass is aimed at.
ANT_ENTRY = re.compile(r'<div class="entry" data-comic-no="(\d+)">(.*?)'
                       r'(?=<div class="entry" data-comic-no=|<div class="footer-navi">)', re.S)
ANT_THUMB = re.compile(r'<div class="entry-thumb">\s*<a href="([^"]+)"', re.S)
ANT_ALT = re.compile(r'alt="([^"]*)"')
ANT_SITE = re.compile(r'<div class="entry-site">\s*<a href="[^"]*">\s*(.*?)\s*</a>', re.S)
ANT_NONE = re.compile(r"に関係する漫画が見つかりませんでした")

ANT_ONE_URL = re.compile(r'<div class="comic-title">\s*<h2><a href="([^"]+)"', re.S)
ANT_ONE_TITLE = re.compile(r'<div class="comic-title">\s*<h2><a[^>]*>(.*?)</a>', re.S)
ANT_ONE_SITE = re.compile(r'<div class="comic-site">\s*<a href="[^"]*">\s*(.*?)\s*</a>', re.S)
ANT_ONE_AUTHOR = re.compile(r'<div class="comic-author">\s*作者:\s*(.*?)</div>', re.S)


def antenna_results(html):
    """`{"answered": bool, "works": [...]}` from a Web漫画アンテナ search page.

    `answered` separates "the site ran the search" from "the fetch produced something we cannot
    read". A stated 見つかりませんでした is an answer and is worth recording; a page we failed to
    recognise is not, and must not be filed as an absence.
    """
    if not html:
        return {"answered": False, "works": []}
    if ANT_NONE.search(html):
        return {"answered": True, "works": []}

    one_url = ANT_ONE_URL.search(html)
    if one_url:
        t = ANT_ONE_TITLE.search(html)
        s = ANT_ONE_SITE.search(html)
        a = ANT_ONE_AUTHOR.search(html)
        return {"answered": True, "works": [{
            "url": _html.unescape(one_url.group(1)),
            "title": _text(t.group(1)) if t else "",
            "site": _text(s.group(1)) if s else "",
            "author": _text(a.group(1)) if a else "",
        }]}

    works = []
    for m in ANT_ENTRY.finditer(html):
        b = m.group(2)
        u = ANT_THUMB.search(b)
        # The visible title is truncated with an ellipsis by CSS and by the server both; the
        # thumbnail's alt text carries it whole.
        t = ANT_ALT.search(b)
        s = ANT_SITE.search(b)
        works.append({"url": _html.unescape(u.group(1)) if u else "",
                      "title": _text(t.group(1)) if t else "",
                      "site": _text(s.group(1)) if s else "",
                      "author": ""})
    return {"answered": bool(works), "works": works}


# ── the join test ─────────────────────────────────────────────────────────────────────────────
def agrees(print_creator, print_publisher, platform_author, platform_rights=()):
    """`(verdict, shared)` for one candidate pairing, on a field that is not the title.

    RUNBOOK §11 in the shape this pass needs. `madb/extract.agrees` compares two catalogue records
    and can read a publisher and an imprint off both; here one side is a platform, which states an
    author always and a publisher only where it prints a copyright line. So:

      `agreed`     a person's name is on both sides, or the publisher is.
      `differs`    both sides name people and no name is shared. A platform advertising the
                   author's OTHER series produces exactly this, and the previous pass measured
                   three of them, so it is recorded as a refusal.
      `unknown`    one side names nobody. An anthology credits a table of contents and MADB
                   credits it to nobody at all, so there is nothing to agree about and the pair
                   is left undecided rather than joined on the title.

    The publisher comparison is folded and substring-tolerant in one direction only: a copyright
    line reads `芳文社` where the bibliography reads `芳文社` and, for the volumes a house
    distributes for another, `[発売]講談社`. The bracket is stripped by the caller.
    """
    a, b = people(print_creator), people(platform_author)
    if a & b:
        return "agreed", sorted(a & b)
    rights = {fold(x) for x in platform_rights if x}
    pub = fold(print_publisher)
    if pub and rights and pub in rights:
        return "agreed", [pub]
    # A rights line names the author too, so it can settle a pairing whose author fields are
    # written differently on the two sides only when it names a person we already hold.
    if a & rights:
        return "agreed", sorted(a & rights)
    if a and (b or rights):
        return "differs", []
    return "unknown", []


def title_matches(print_title, platform_title):
    """Whether the two titles are the same string once decoration is removed.

    A lead and never a verdict: `agrees` decides. This exists so that a search result about a
    different work is dropped before anything is fetched for it, which is most of what a keyword
    search returns.
    """
    a, b = fold(print_title), fold(platform_title)
    if not a or not b:
        return False
    if a == b:
        return True
    # The bibliography keeps a volume number in the title of a work published in one volume and the
    # platform does not, and the reverse happens where a platform numbers a re-serialisation.
    return fold(VOLUME_TAIL.sub("", print_title)) == fold(VOLUME_TAIL.sub("", platform_title))
