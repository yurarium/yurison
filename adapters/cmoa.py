#!/usr/bin/env python3
"""Reading コミックシーモア's listing pages: what a shop shelves, and under whose name.

WHY THIS EXISTS. cmoa files 百合・GL as genre 37, a shelf of about 1,869 titles reachable only from
a work page (`data/coverage/retailer-recon.md` records how a first pass missed it). That shelf is a
third party's filing, so under DEFINITIONS §4 it is evidence toward `content_tier` and never toward
`marketing_label`. This module reads the pages; it classifies nothing.

WHAT A LISTING ROW CARRIES, AND WHAT IT DOES NOT. A row gives the title id, the title, the 作家
links, the demographic ジャンル and the 雑誌・レーベル links. It does NOT give the publisher, which
lives on the work page. Fetching 1,869 work pages for one field is the obvious move and the wrong
one: the shop's own publisher facet partitions the same shelf 83 ways and those counts sum to
exactly the shelf total, so re-reading the shelf once per publisher fills the field in about 96
requests instead of 1,869. `facet()` and `shelf_url(publisher_id=...)` are what make that available.

TWO KINDS OF CLAIM, TWO FIELDS. 雑誌・レーベル is the publisher's own imprint, so it is
publisher-side evidence about the work. The genre shelf is the shop's opinion about it. They are
kept apart here so the difference survives into whatever reads this.

COMPLETION IS A CSS CLASS. A finished series carries `<span class="end_m">` in the row's title
block, with nothing legible beside it. Believed because the shop's own 完結 facet counts the same
population: 1,050 on the facet against 1,044 marked rows kept plus 6 marked rows excluded, on the
capture of 2026-08-04. `test_cmoa.py` pins a row of each kind.

THE CENSORED-EDITION TRAP, which is why `censored_marker` exists. cmoa's 百合・GL genre excludes its
アダルトマンガ genre, so the shelf looks all-ages by construction. It is not clean. An adult
doujinshi re-edited to erase genitalia clears the all-ages filter and lands here filed 青年マンガ,
announcing itself only in its own title: 【棒消し修正版】 and その類. Such a title is the same WORK
as the uncensored edition sold on the adult shelf, so it is pornography with a different cover on,
and REQUIREMENTS excludes it outright.

  加筆修正版 IS THE COUNTER-CASE AND IT WAS CHECKED FIRST. It means a reissue the author revised and
  added to, an ordinary commercial edition with nothing to do with censoring. A rule reading for
  修正版 alone throws it away, so 加筆 is held out by name. Anything else ending 修正版 that turns up
  later is owed the same care: find out what was corrected before excluding it.
"""
import html as H
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import isbn as _isbn                                                           # noqa: E402

BASE = "https://www.cmoa.jp"
GENRE_YURI = "37"
# The same genre written the way the shop's own links write it. The search accepts a short form and
# normalises it, so genre_id=000037 returns genre 37 and looks correct while being a typo; the
# padded form is used here so nothing rests on that leniency.
GENRE_ID = "0000037"

_BOX = '<li class="search_result_box">'
_TITLE_ID = re.compile(r'id="ti(\d+)"')
_TITLE_LINK = re.compile(r'<a href="/title/\d+/" class="title" >(.*?)</a>', re.S)
_AUTHOR = re.compile(r'<a href="/search/author/(\d+)/">([^<]*)</a>')
_GENRE = re.compile(r'<a href="/search/genre/(\d+)/">([^<]*)</a>')
_MAGAZINE = re.compile(r'<a href="/search/magazine/(\d+)/">([^<]*)</a>')
_TOTAL = re.compile(r"検索結果([\d,]+)件中")

# The shop's query parameter for each facet, so a caller never has to spell one.
FACET_PARAM = {"publisher": "publisher_id", "magazine": "magazine_id", "author": "author_id"}

# WHAT MARKS A CENSORED EDITION OF AN ADULT WORK. Read off the titles on this shelf. Each names a
# way of erasing genitalia (a bar removed, a bar drawn, a white-out), or the adult edition itself,
# or the edition that exists BECAUSE there is an adult one. 修正版 is the loose one, which is what
# EDITION_SAFE is for.
#
# 全年齢版 was added after the capture and is not a guess. 六番目の課長's author page carries six
# titles: 微睡むラブカ and 百合まみれ.zip each appear once filed アダルトマンガ and once as a
# -全年齢版- filed 青年マンガ, which is the twin the recon predicted, stated by the shop's own
# catalogue rather than inferred from a word. The phrase means all-ages EDITION, and an edition is
# only worth naming where another one differs.
CENSORSHIP_MARKERS = ("棒消し", "棒修正", "白抜き修正", "修正版", "R-18版", "R18版", "全年齢版")

# Strings containing a marker that do not mean it. See the docstring: 加筆修正 is authorial revision.
# 完全版 is the other near miss and needs no entry, since it shares no substring with any marker: it
# is a collected reissue and 11 titles on this shelf carry it. Checked before the rule was believed.
EDITION_SAFE = ("加筆修正", "加筆・修正")


# WHO SELLS DOUJINSHI, and why this is a short list rather than a judgement per row. A doujin
# distributor is a property of the SELLER, so it is decided once about a company and not once about
# each of its titles. Every entry here names what it rests on, and the list is deliberately
# evidence-only: `False` means "not on this list", never "checked and found to be a publisher".
#
#   ナンバーナイン is the one that matters, at 595 of the 1,869 titles on the shelf. It is a
#   doujinshi distributor (data/coverage/retailer-recon.md), and its 百合コレ line behaves like one
#   here: 六番目の課長's -全年齢版- titles under that label are the cut editions of works the same
#   shop sells filed アダルトマンガ.
#
# WHAT IS NOT ON IT AND PROBABLY BELONGS. ライトリーズン (90), コンパス (39), DLcomics with its
# DLManiax label (13), ジーオーティー (10), スキマ (9), パルソラ (9) and サークルコネクト (1) all
# read as indie or doujin distribution and none was established. Anyone extending this list should
# establish each one and write down what established it, rather than extending the pattern.
DOUJIN_PUBLISHERS = {"ナンバーナイン"}
DOUJIN_LABELS = {"百合コレ"}


def is_doujin(publisher, labels=()):
    """Whether a doujinshi distributor is selling this, by the evidenced list above."""
    return bool(publisher in DOUJIN_PUBLISHERS or (set(labels or ()) & DOUJIN_LABELS))


def fold(s):
    """NFKC, so a marker matches in whichever width the shop wrote it."""
    return unicodedata.normalize("NFKC", s or "")


def _text(x):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", H.unescape(x or ""))).strip()


def censored_marker(title):
    """Which marker shows this to be a censored edition of an adult work, or None.

    Returns the marker rather than a boolean because the exclusion has to be countable per marker.
    A filter whose effect nobody can see is a filter that stops working silently
    (STANDING-INSTRUCTIONS §13), and the count is the only thing published about these rows.
    """
    t = fold(title)
    if any(fold(s) in t for s in EDITION_SAFE):
        return None
    for m in CENSORSHIP_MARKERS:
        if fold(m) in t:
            return m
    return None


def total(html):
    """How many titles the shop says the result holds, or None where it does not say."""
    m = _TOTAL.search(html or "")
    return int(m.group(1).replace(",", "")) if m else None


def facet(html, kind="publisher"):
    """[(id, name, count)] from a facet sidebar or a /search/other/ page, first occurrence wins.

    The counts matter as much as the names. They are what shows a partition is complete, and a
    partition whose parts do not sum to the whole has dropped a slice without saying so.
    """
    key = FACET_PARAM[kind]
    pat = re.compile(key + r"=(\d+)[^\"]*\"[^>]*>\s*([^<（(]+?)\s*[（(]([\d,]+)[）)]", re.S)
    out, seen = [], set()
    for fid, name, count in pat.findall(html or ""):
        if fid in seen:
            continue
        seen.add(fid)
        out.append((fid, _text(name), int(count.replace(",", ""))))
    return out


def rows(html):
    """Every title on one listing page, in the order the shop lists them.

    A row is a dict of title_id, title, authors, author_ids, genre, genre_id, labels, label_ids,
    completed and url. A field the page does not carry is absent rather than guessed: a listing row
    states no publisher, and deriving one from the label would be the same fact produced by two
    paths with nothing forcing agreement (STANDING-INSTRUCTIONS §3).
    """
    out = []
    for box in (html or "").split(_BOX)[1:]:
        m = _TITLE_ID.search(box)
        if not m:
            continue
        # The title appears twice in a row, on the cover link and on the text link. The cover link
        # wraps an <img> and so yields nothing once tags are stripped; the longer text has the words.
        names = [n for n in (_text(t) for t in _TITLE_LINK.findall(box)) if n]
        if not names:
            continue

        head, _, tail = box.partition("search_result_box_right_sec2")
        authors = [(i, _text(n)) for i, n in _AUTHOR.findall(tail)]
        genres = [(i, _text(n)) for i, n in _GENRE.findall(tail)]
        labels = [(i, _text(n)) for i, n in _MAGAZINE.findall(tail)]

        out.append({
            "title_id": m.group(1),
            "title": max(names, key=len),
            "authors": [n for _, n in authors],
            "author_ids": [i for i, _ in authors],
            # One demographic genre to a row. 百合・GL itself is not repeated on the row, so the
            # genre here is 青年マンガ and その類 rather than the shelf the row was found on.
            "genre": genres[0][1] if genres else None,
            "genre_id": genres[0][0] if genres else None,
            "labels": [n for _, n in labels],
            "label_ids": [i for i, _ in labels],
            "completed": "end_m" in head,
            "url": f"{BASE}/title/{m.group(1)}/",
        })
    return out


def shelf_url(page=1, publisher_id=None, complete_only=False):
    """One page of genre 37, optionally narrowed by the shop's own facets."""
    q = [f"genre_id={GENRE_ID}", "sort=14", f"page={page}"]
    if publisher_id:
        q.append(f"publisher_id={publisher_id}")
    if complete_only:
        q.append("complete_flg=1")
    return f"{BASE}/search/result/?" + "&".join(q)


def facet_url(kind="publisher"):
    """The shop's full list for one facet. The sidebar shows five; this shows all of them."""
    return (f"{BASE}/search/other/?type={kind}"
            f"&back_url=genre_id%3D{GENRE_ID}%26page%3D1%26sort%3D14")


# --------------------------------------------------------------------------------------------
# The candidate document, and why merging it is a tested function rather than a loop in a script.
#
# A capture that runs 19 pages and writes at the end loses everything when page 12 times out, and
# one that rewrites the file from only what THIS run fetched loses every page an earlier run got.
# The second has bitten this project more than once and it is silent: the file is well-formed,
# smaller, and says nothing about what went missing. So the fold is here, where a test can run it
# twice with disjoint input and check that both halves survived.

def merge(doc, new_rows, page=None, publisher_id=None):
    """Fold rows into a candidate document, keeping every entry the new rows do not mention.

    Fields already held are not overwritten with nothing: the publisher pass carries no genre and
    the genre pass carries no publisher, so each has to add to what the other found. A field
    arriving with a real value does replace what is there, because the newer read is the better one.
    """
    doc = dict(doc or {})
    titles = list(doc.get("titles") or [])
    by_id = {t["cmoa_title_id"]: t for t in titles}
    added = 0
    for r in new_rows:
        tid = r["cmoa_title_id"]
        cur = by_id.get(tid)
        if cur is None:
            titles.append(r)
            by_id[tid] = r
            added += 1
            continue
        for k, v in r.items():
            if v not in (None, [], ""):
                cur[k] = v
    doc["titles"] = titles
    if page is not None:
        doc["pages_captured"] = sorted(set(doc.get("pages_captured") or []) | {page})
    if publisher_id is not None:
        doc["publishers_captured"] = sorted(set(doc.get("publishers_captured") or [])
                                            | {publisher_id})
    return doc, added


# --------------------------------------------------------------------------------------------
# The work page: what a shelf row does not say.
#
# WHY THE WORK PAGE AT ALL. A listing row carries no date, no ISBN and no volume list, and
# DEFINITIONS §6 makes `first_publication` the inclusion test rather than an ornament on it. So a
# shelf row cannot become a work record and the page has to be read.
#
# ONE REQUEST PER WORK, NOT ONE PER VOLUME. `/title/<id>/` lists ten volumes to a page and prints a
# synopsis under each, which is text this project may not store. `?disp_mode=easy` on the same URL
# lists EVERY volume, drops the synopsis entirely, and still carries the 作品情報 block. So the
# cheap page is also the one that keeps us on the right side of REQUIREMENTS §2, and `work_url()`
# asks for it.
#
# WHAT THE 作品情報 BLOCK DESCRIBES, WHICH IS ONE VOLUME AND NOT THE WORK. ISBN, 配信開始日 and
# ファイルサイズ belong to the volume the page is showing. On `/title/<id>/` that is volume 1,
# structurally: volume 1 is the entry whose link is the bare work URL and every later volume links
# to `/vol/N/`. `work()` returns `detail_volume` so a caller can check that rather than assume it,
# because attaching volume 7's ISBN to a work's first publication would be silent and wrong.
#
# 配信開始日 IS NOT A PUBLICATION DATE and must not be recorded as one. It is the day コミックシーモア
# started selling the file. For a simultaneous digital release it lands within days of the print
# on-sale; for a back-catalogue title digitised later it can be years after. 12分のエチュード 1 is
# openBD 201510 against a 配信開始日 of 2015-09-19, and both are about the same book. The field is
# kept under its own name, `distribution_started`, so that nothing downstream can mistake the two.
# The ISBN is what answers publication, through openBD.

_DETAIL = re.compile(r'category_line_f_l_l">\s*([^<]+?)\s*</div>\s*'
                     r'<div class="category_line_f_r_l"[^>]*>(.*?)</div>', re.S)
_LINK = re.compile(r'<a href="([^"]*)"[^>]*>(.*?)</a>', re.S)
# Both list modes. `easy` names each volume in a title_check_box; the detailed mode uses an h3 of
# its own class. A capture asks for easy, and the other is here so a page saved by hand still reads.
_VOL_EASY = re.compile(r'<div class="title_check_box">\s*<h3>\s*<a href="([^"]+)"[^>]*>\s*'
                       r'(.*?)\s*</a>', re.S)
_VOL_FULL = re.compile(r'title_details_title_name_h2">\s*<a href="([^"]+)"[^>]*>\s*(.*?)\s*</a>',
                       re.S)
_VOL_N = re.compile(r"/title/\d+/vol/(\d+)/")
_RELEASE_TEXT = re.compile(r'vol_release_text">\s*(.*?)\s*</span>', re.S)
_JP_DATE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_JP_MONTH = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月")
# The sub-genre row of the 作品情報 block carries no label of its own, which is where 百合・GL is
# written. A parser reading only labelled rows drops the one genre this project came for.
_GENRE_DETAIL = re.compile(r'category_line_f_r_l genre_detail"[^>]*>(.*?)</div>', re.S)


def work_url(title_id):
    """The one page that lists every volume of a work and prints no synopsis under any of them."""
    return f"{BASE}/title/{title_id}/?page=1&order=up&disp_mode=easy"


def volume_url(title_id, n):
    """A single volume's own page, which is the only place its own ISBN is stated."""
    return f"{BASE}/title/{title_id}/" if int(n) == 1 else f"{BASE}/title/{title_id}/vol/{n}/"


def details(html):
    """The 作品情報 block as `{label: inner html}`, first occurrence of each label winning.

    The block is served twice, once for each layout, and the two agree. Taking the first is
    deliberate rather than incidental: a later copy differing would be a page change worth
    noticing, and `work()` has no way to prefer one, so the count of labels is what a test pins.
    """
    out = {}
    for label, value in _DETAIL.findall(html or ""):
        out.setdefault(_text(label), value)
    return out


def iso_date(japanese):
    """`2015年9月19日` as `2015-09-19`, or None. A partial date is not repaired into a whole one."""
    m = _JP_DATE.search(fold(japanese))
    if not m:
        return None
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def iso_month(japanese):
    """`2019年1月` as `2019-01`, the precision the shop states and no more.

    出版年月 is a MONTH and padding it to a day would invent a fact. `first_publication` takes the
    precision it was given; a date this project made up would be indistinguishable from one a
    source stated, which is the failure DEFINITIONS §6 cannot afford in the field that IS the
    inclusion test.
    """
    m = _JP_MONTH.search(fold(japanese))
    return f"{m.group(1)}-{int(m.group(2)):02d}" if m else None


# The converter this module used to carry. It now lives in `adapters/isbn.py`, because four
# modules had a function of this name and two of them only stripped the punctuation, which left
# a third of the national bibliography unreachable. Re-exported so `cmoa.isbn13` keeps resolving.
isbn13 = _isbn.isbn13


def volumes(html, title_id):
    """Every volume the page lists, as `{volume, name, url}`, in the order it lists them.

    The volume number comes off the LINK and not off the name. A name is a title plus whatever the
    publisher put after it, and this shelf holds ぼくらのへんたい 1, 12分のエチュード 1巻 and
    Office Sweet 365(全年齢版) side by side; reading a trailing number out of that would number a
    work by its own title sooner or later. `/vol/N/` says N, and the bare work URL is volume 1.
    """
    found = _VOL_EASY.findall(html or "") or _VOL_FULL.findall(html or "")
    out, seen = [], set()
    for href, name in found:
        m = _VOL_N.search(href)
        n = int(m.group(1)) if m else 1
        if n in seen:
            continue
        seen.add(n)
        out.append({"volume": n, "name": _text(name),
                    "url": f"{BASE}{href.split('?')[0]}" if href.startswith("/") else href})
    return out


def stated_volumes(html):
    """`(count, completed)` from 全14巻完結 or 1巻まで配信中！, or `(None, False)`.

    The shop's own sentence, kept beside the list rather than derived from it. They disagree where
    a volume list is paged and the sentence is not, and a disagreement is the thing worth seeing:
    a capture that only counted `<li>`s would have reported 付き合ってあげてもいいかな as 10 volumes
    from the default page and said nothing.
    """
    t = fold(" ".join(_RELEASE_TEXT.findall(html or "")))
    m = re.search(r"(\d+)\s*巻", t)
    return (int(m.group(1)) if m else None), ("完結" in t)


def work(html, title_id):
    """One work page as a record: its volumes, and what the shop states about volume 1.

    Fields the page does not carry come back None or empty rather than guessed, and nothing here
    classifies: the genre and the imprint are reported as the shop wrote them, for
    `shelfingest.designated()` to test. A designation the shelf row did not show is the reason this
    function returns `genre` and `imprint` at all.
    """
    d = details(html)
    vols = volumes(html, title_id)
    stated, completed = stated_volumes(html)
    labels = [_text(n) for _, n in _LINK.findall(d.get("雑誌・レーベル", ""))]
    genres = [_text(n) for _, n in _LINK.findall(d.get("ジャンル", ""))]
    sub = [_text(n) for row in _GENRE_DETAIL.findall(html or "")
           for _, n in _LINK.findall(row)]
    first = vols[0] if vols else None
    return {
        "cmoa_title_id": str(title_id),
        "publisher": (_text(_LINK.search(d["出版社"]).group(2))
                      if _LINK.search(d.get("出版社", "") or "") else None),
        "imprint": labels[0] if labels else None,
        "labels": labels,
        "genre": genres[0] if genres else None,
        # Deduplicated because the block is served once per layout, so every genre arrives twice.
        "genres": list(dict.fromkeys(genres + sub)),
        "volumes": vols,
        "volumes_stated": stated,
        "completed": completed,
        # Which volume the ISBN and the date below belong to. 1 is the expected answer and the
        # capture counts anything else rather than filing it as volume 1's.
        "detail_volume": first["volume"] if first else None,
        "isbn": isbn13(_text(d.get("ISBN", ""))),
        # 出版年月 is the shop stating the volume's publication month. Where it is present it
        # answers DEFINITIONS §6 outright, with no second source needed and no ISBN required.
        "published": iso_month(_text(d.get("出版年月", ""))),
        "distribution_started": iso_date(_text(d.get("配信開始日", ""))),
    }
