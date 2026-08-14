#!/usr/bin/env python3
"""BOOK☆WALKER's 百合 shelf, read as a candidate list rather than as a classification.

WHAT THIS IS. Tag 14 is the shop's own 書籍ジャンル for 百合. Restricted to manga it holds about
2,153 rows, server-rendered 60 to a page. A separate タテスク／話・連載 store, reached with `?wa=1`,
holds about 294 more under the same tag and is a different kind of thing: vertical-scroll and
per-chapter items rather than volumes.

WHAT IT IS NOT. A retailer shelving a work under 百合 is a third party filing it, which
DEFINITIONS §4 makes evidence toward `content_tier` and never toward `marketing_label`. Nothing
here classifies anything. The output goes to data/queue/, which the build does not read.

THE IMPRINT AND THE TAG ARE DIFFERENT EVIDENCE. The listing prints the publisher's own label in
`m-book-item__label`, and repeats it in parentheses after the series title. That is publisher-side.
The 百合 tag is the shop's. They are kept in separate fields because collapsing them would launder
one into the other.

WHAT THE LISTING DOES NOT GIVE YOU. Authors, for series rows. A standalone volume carries
`m-book-item__author`; a series tile carries none, and neither does /series/<id>/ nor
/series/<id>/list/. The author lives on a volume detail page, in its <title>, so filling the field
for every row costs one request per row. `author` is therefore None for most rows and
`author_source` says which it is. An empty author here means the listing did not say, never that
the work has no author: absence is a state (STANDING-INSTRUCTIONS §5).

MEMBERSHIP IS READ FROM FACETS, NOT GUESSED. Whether a row is doujin, direct-published, marked
完結 or filed 男性向け is decided by whether the row appears in that facet's own listing, fetched
once each. Reading 同人 off a publisher name would be an inference; reading it off `?qtag=1083` is
the shop stating it.

CENSORED PORNOGRAPHY ANNOUNCES ITSELF IN THE TITLE, SOMETIMES. An adult doujinshi re-edited to
clear an all-ages filter is the same work as the uncensored edition sold elsewhere, and it is
excluded. The markers below catch only the editions that say so, so the count they produce is a
floor rather than a measurement. Their titles are counted and never written down.
"""
import pathlib as _pl
import sys as _sys

_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))

import population  # noqa: E402

import html
import re
import unicodedata

#: BOOK☆WALKER's shelf label, matched in two files.
SHELF_LABEL = re.compile(r'<p class="m-book-item__label">(.*?)</p>')

# Where one listing row in the volume store starts. The trailing space in the class attribute is
# the shop's. Where it ENDS is `item_blocks`, and the two were one regex until 2026-08-06.
ITEM_START = re.compile(r'<div class="m-book-item\s*">')
# The row wrapper. The shop nests a cart <ul><li> inside a row, so the close that ends the row is
# the one at depth zero and not the first one seen.
LI = re.compile(r"<(/?)li[\s>]")
SERIES_HREF = re.compile(r'href="https://bookwalker\.jp/series/(\d+)/')
DETAIL_HREF = re.compile(r'href="https://bookwalker\.jp/de([0-9a-f-]{36})/')
TITLE_A = re.compile(r'<a[^>]*class="m-book-item__title".*?>\s*(.*?)\s*</a>', re.S)
LABEL = SHELF_LABEL
AUTHOR = re.compile(r'<p class="m-book-item__author">(.*?)</p>', re.S)
COMP_TAG = re.compile(r'<span class="a-tag-comp">\s*完結\s*</span>')
KIND_TAG = re.compile(r'<span class="a-tag-(comic|novel|magazine|[a-z]+)">(.*?)</span>')
VOLUMES = re.compile(r'シリーズ(\d+)冊')
TOTAL = re.compile(r"全([0-9,]+)件")

# The タテスク／話・連載 store renders a different template, and this one does carry the author.
WA_ITEM = re.compile(r'<div class="o-tile--series o-warensai-tile">(.*?)(?=<div class="o-tile--series'
                     r' o-warensai-tile">|<div class="o-tile-wrap|\Z)', re.S)
WA_TITLE = re.compile(r'<h2 class="o-tile-ttl">\s*<a href="([^"]+)">(.*?)</a>', re.S)
WA_AUTHOR = re.compile(r'<p class="o-tile-book-author">(.*?)</p>', re.S)
WA_COUNT = re.compile(r'<p class="o-tile-count">(.*?)</p>', re.S)
WA_TTSK = re.compile(r'a-ttsk-label-logo')

# A trailing （レーベル名） on a series title. Full-width brackets only: half-width parentheses
# appear inside real titles (「ヒロイン(仮)」) and stripping those would rename the work.
PAREN_IMPRINT = re.compile(r"（([^（）]+)）\s*$")

# Editions re-cut to clear an all-ages filter. Every one of these is the same work as an
# uncensored edition sold on the adult store, so it is excluded rather than recorded.
CENSORED = {
    "棒消し": re.compile(r"棒消し"),
    "棒修正": re.compile(r"棒修正"),
    "白抜き修正": re.compile(r"白抜き修正"),
    "修正版": re.compile(r"修正版"),
    "R18版": re.compile(r"[Rr]-?\s*18\s*版"),
    # Added after reading the shelf. 全年齢版 and 一般向け(修正)版 are the same edition split from
    # the other side: a work that needs an all-ages edition had an adult one first.
    "全年齢版": re.compile(r"全年齢版"),
    # ぬきどころ / 無修正 name the uncensored edition outright. Neither should reach an all-ages
    # shelf, and if one does it is the thing this rule exists to keep out.
    "無修正": re.compile(r"無修正"),
}


# The shop prints ―― in its label field where a book has no imprint. It is a rendering of absence,
# and storing it as an imprint would give 143 rows a publisher called "――".
NO_LABEL = re.compile(r"^[―ー—–-]+$")

# How the shop prefixes a name with the part its bearer played. Stripped so that 漫画:千種みのり
# and 著:千種みのり are one person rather than two.
ROLE = re.compile(r"(?:漫画|作画|著者|著|原作|原案|イラスト|挿絵|企画|構成|編集部|編集|編著|編|"
                  r"監修|翻訳|キャラクター原案|その他)\s*[:：]")
# 他 closes a truncated list. It is not a person.
ETC = re.compile(r"^\s*(?:他|ほか|他多数)\s*$")


def _text(s):
    """Markup out, entities decoded, runs of space collapsed. Ideographic space is kept."""
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"[ \t\r\n]+", " ", html.unescape(s)).strip()


def _label(s):
    """The imprint, or None where the shop rendered an absent one."""
    s = _text(s)
    return None if not s or NO_LABEL.match(s) else s


def author_names(field):
    """The people named in one `m-book-item__author` string, roles and 他 removed.

    The shop writes `漫画: 千種みのり 他`, and where several people worked on a book it writes each
    role in turn. Splitting on the role prefixes rather than on whitespace is what keeps a name
    that contains a space, which most of the pen names on this shelf do.
    """
    s = _text(field)
    if not s:
        return []
    out, seen = [], set()
    for part in re.split(r"[,、,／/／]|" + ROLE.pattern, ROLE.sub("\n", s)):
        for name in part.split("\n"):
            name = name.strip("　 \t")
            if not name or ETC.match(name):
                continue
            # A trailing 他 rides on the last name rather than standing alone in the markup.
            name = re.sub(r"[　 ]+(?:他|ほか)$", "", name).strip()
            if name and name not in seen:
                seen.add(name)
                out.append(name)
    return out


def match_key(s):
    """The key two shelf listings are compared on, keeping bracketed apparatus that the shop uses
    to distinguish one edition from another.

    ORIGINALLY CALLED `fold`. The key two catalogues can be compared on: width, case and spacing folded away."""
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").replace("　", "").lower()


def total(page):
    """How many rows the shop says the whole listing holds, or None where it does not say."""
    m = TOTAL.search(page or "")
    return int(m.group(1).replace(",", "")) if m else None


def censored_marker(title):
    """The censorship marker this title carries, or None.

    Named rather than boolean, so the exclusion count can be reported per marker and a marker that
    never fires can be seen to have never fired.

    Matched on the NFKC form. The shop writes 【Ｒ－１８版】 in full width on some rows and R-18版 in
    half width on others, and a rule that only knows one of them lets the other through.
    """
    folded = unicodedata.normalize("NFKC", title or "")
    for name, pat in CENSORED.items():
        if pat.search(folded):
            return name
    return None


def split_imprint(title):
    """`(work title, imprint)` where a series title ends in （レーベル）, else `(title, None)`.

    The shop appends its own label field to a series title and prints the same string in
    `m-book-item__label`. Splitting it back off is what lets the two be compared, and where they
    disagree the label field is the one that came from a field rather than from a rendering.
    """
    m = PAREN_IMPRINT.search(title or "")
    if not m:
        return title, None
    return title[:m.start()].strip(), m.group(1).strip()


def item_blocks(page):
    """The markup of each listing row, ending where the row's own `</li>` ends it.

    THE BUG THIS EXISTS TO PREVENT, found on 2026-08-06. This was one regex whose row ran to the
    next row or, for the last row on the page, to the end of the document. So the last row
    swallowed everything printed after the listing, and a `/series/<id>/list/` link down there
    became the row's identity. `bookwalker_volumes.py` keeps only rows identified by a volume
    uuid, so the last row of the listing was dropped.

    What it cost: a listing is sorted 最新刊から, newest first, so the row this dropped is the
    OLDEST volume. `first_publication` is the earliest 底本発行日 across the volumes read, which
    means the work's first volume was the one silently missing from the set the date was chosen
    from. 安達としまむら reads as three volumes starting at volume 2, and it has four starting at
    volume 1. A shorter count is visible; a date belonging to volume 2 is not.

    What made it invisible: the trailing markup only carries a `/series/` link where the shop has
    related series to advertise, so most listings parsed correctly and the ones that did not
    looked like series with one fewer volume. All 16 series that returned nothing at all were
    one-volume series, where the only row was the last row.

    The end is the row's own `</li>` and not the next row's start, because the last row has no
    next row and that is the whole of the fault. A row nests a cart `<ul><li>` of its own, so the
    close that ends the row is the one at depth zero.
    """
    page = page or ""
    starts = [m.end() for m in ITEM_START.finditer(page)]
    for i, start in enumerate(starts):
        limit = starts[i + 1] if i + 1 < len(starts) else len(page)
        end, depth = limit, 0
        for m in LI.finditer(page, start, limit):
            if not m.group(1):
                depth += 1
            elif depth:
                depth -= 1
            else:
                end = m.start()
                break
        yield page[start:end]


def parse_listing(page):
    """Every row on one volume-store listing page, in the order the shop lists them.

    Rows carry either a series id or a detail uuid, never both as their identity: a series tile
    links to /series/<id>/list/ and also to the uuid of its first volume, and taking that uuid as
    the row's identity would file a series under one of its volumes.
    """
    rows = []
    for block in item_blocks(page):
        t = TITLE_A.search(block)
        if not t:
            continue
        listed = _text(t.group(1))
        if not listed:
            continue
        sid = SERIES_HREF.search(block)
        did = DETAIL_HREF.search(block)
        work, from_title = split_imprint(listed) if sid else (listed, None)
        label = LABEL.search(block)
        author = AUTHOR.search(block)
        vols = VOLUMES.search(block)
        kind = KIND_TAG.search(block)
        rows.append({
            "id": sid.group(1) if sid else (did.group(1) if did else None),
            "id_kind": "series" if sid else ("detail" if did else None),
            "url": (f"https://bookwalker.jp/series/{sid.group(1)}/" if sid
                    else f"https://bookwalker.jp/de{did.group(1)}/" if did else None),
            "title_listed": listed,
            "title": work,
            "imprint": _label(label.group(1)) if label else from_title,
            "imprint_in_title": from_title,
            "author": _text(author.group(1)) if author else None,
            "kind_tag": _text(kind.group(2)) if kind else None,
            "volumes": int(vols.group(1)) if vols else None,
            "completed_marker": bool(COMP_TAG.search(block)),
        })
    return rows


def parse_warensai(page):
    """Every row on one タテスク／話・連載 listing page. This template does carry the author."""
    rows = []
    for m in WA_ITEM.finditer(page or ""):
        block = m.group(1)
        t = WA_TITLE.search(block)
        if not t:
            continue
        url, listed = t.group(1), _text(t.group(2))
        if not listed:
            continue
        sid = SERIES_HREF.search(f'href="{url}')
        work, from_title = split_imprint(listed)
        author = WA_AUTHOR.search(block)
        count = WA_COUNT.search(block)
        vols = VOLUMES.search(count.group(1)) if count else None
        rows.append({
            "id": sid.group(1) if sid else None,
            "id_kind": "series" if sid else None,
            "url": url,
            "title_listed": listed,
            "title": work,
            "imprint": from_title,
            "imprint_in_title": from_title,
            "author": _text(author.group(1)) if author else None,
            "kind_tag": "タテスク" if WA_TTSK.search(block) else "話・連載",
            "volumes": int(vols.group(1)) if vols else None,
            "completed_marker": False,
        })
    return rows


def facet_counts(page):
    """`{label: (count, url)}` for every facet the shop offers on this listing.

    Reading the facet block rather than hardcoding tag numbers, because the numbers are the shop's
    and a facet that has moved should be visibly absent rather than silently empty.
    """
    out = {}
    pat = re.compile(r'<li><a href="([^"]*)"[^>]*data-action-label="([^"]*)"[^>]*>'
                     r'(.*?)<span class="search-bookNum">\(([0-9,]+)\)</span>', re.S)
    for m in pat.finditer(page or ""):
        out[html.unescape(m.group(2))] = (int(m.group(4).replace(",", "")),
                                          html.unescape(m.group(1)))
    return out


# ---------------------------------------------------------------------------------------------
# The run. Everything above is pure and tested offline; everything below is I/O and checkpointing.

LISTINGS = {
    # order=title, not the shop's default order=rank. Rank is recomputed continuously, so page 12
    # fetched a minute after page 11 can drop a row past the boundary and duplicate another.
    # Alphabetical order is stable for as long as the shelf is, which is what a 36-page walk needs.
    "manga": "https://bookwalker.jp/tag/14/?qcat=2&order=title&page={n}",
    "warensai": "https://bookwalker.jp/tag/14/?wa=1&page={n}",
}

# Facets fetched once each and turned into membership sets, so that "is this doujin" is answered
# by the shop rather than inferred from a publisher name.
FACETS = {
    "doujin": ("同人誌・個人出版", "https://bookwalker.jp/tag/14/?qcat=2&order=title&qtag=1083&page={n}"),
    "direct": ("ダイレクト出版", "https://bookwalker.jp/tag/14/?qcat=2&order=title&qtag=1038&page={n}"),
    "completed_facet": ("完結", "https://bookwalker.jp/tag/14/?qcat=2&order=title&qtag=42&page={n}"),
    "male_directed": ("男性向け", "https://bookwalker.jp/tag/14/?qcat=2&order=title&qtag=2&page={n}"),
}

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.6
HEADER = """\
# BOOK☆WALKER's 百合 shelf (tag 14), captured as a CANDIDATE LIST. Not records.
#
# WHERE IT CAME FROM. https://bookwalker.jp/tag/14/ is the shop's own 書籍ジャンル for 百合,
# presented on every work page. Two listings are captured here and kept apart:
#   manga     — the volume store restricted to マンガ (?qcat=2), the main capture
#   warensai  — the タテスク／話・連載 store (?wa=1), vertical-scroll and per-chapter items,
#               which are a different kind of thing from volumes and are flagged as such
# Read with `yurarium/0.1`, at least 1.5 s apart, in title order so that paging is stable.
# robots.txt disallows /ex/problem/, /entry-list/, /member/, /history/, /prx/ma/ and sample
# links; none of those is touched. The 話・連載 link carries rel=nofollow, which is a crawl
# hint rather than access control, and nothing here is gated.
#
# WHAT IT IS NOT EVIDENCE OF. A retailer filing a work under 百合 is a third party filing it.
# DEFINITIONS §4 makes that evidence toward `content_tier` and NEVER toward `marketing_label`,
# so nothing in this file sets `marketing_label` and nothing here classifies anything. The
# file lives in data/queue/, which sits outside the source tree, so no row can become a record.
# build.py globs that directory for one key, `candidates:`, and shows what it finds as a
# discovery queue. This file holds no such key and therefore reaches no surface at all. That is
# a deliberate choice rather than an accident of naming: the rows here have had no inclusion
# decision made about them and are not ready to be shown to anybody as leads.
#
# TWO KINDS OF EVIDENCE, KEPT APART.
#   imprint            the publisher's own label, printed by the shop in its label field
#   imprint_in_title   the same label where the shop also appends it to a series title
#   shop_tag           百合, which is the shop's classification and nobody else's
#   facets             membership read from the shop's own facet listings, not inferred
#
# ABSENCE IS A STATE. `author: null` means the listing did not print one. A series tile carries
# no author at all, and neither does /series/<id>/ nor /series/<id>/list/; the author is on each
# volume's detail page, one request per row. `author_source` says where a name came from.
#
# EXCLUSIONS. Works marketed or intended as pornography are out of this database and are never
# uploaded. The shop keeps R18 stock on a separate adult store, so this shelf is already
# all-ages, which is not sufficient on its own: an adult doujinshi re-cut to erase genitalia
# clears an all-ages filter and is the same work as the uncensored edition. Rows whose titles
# carry such a marker are counted below and their titles are written nowhere.
# 同人誌・個人出版 and ダイレクト出版 are recorded as flags rather than excluded, because the
# decision about them is the owner's and the flag is what makes it possible.
# 男性向け is a marketing direction and is recorded, not excluded.
#
# WHAT THE CAPTURE FOUND ABOUT THE SHOP'S OWN DATA.
#   `completed_facet` is the answer, `completed_marker` is a floor. Every row the listing tags
#   完結 is on the 完結 facet, and 76 rows on the facet carry no tag. Four of those were checked
#   against their series pages with adapters/bookwalker.py and all four read 【完結】, so the
#   facet is right and the row tag under-reports by about a sixth.
#   `doujin` and `direct` are the same 276 rows, exactly. 同人誌・個人出版 and ダイレクト出版 are
#   applied together here, so either one answers the doujin question on its own.
#   THE DOUJIN FACET IS NOT THE DOUJIN FRACTION, and data/coverage/retailer-recon.md expects it
#   to be. 百合コレ is 516 rows here, a fifth of the shelf, published by ナンバーナイン, which is a
#   doujin distributor, and NOT ONE of those rows carries the facet. The 276 rows that do carry
#   it are spread over 86 small imprints. So subtracting the facet leaves the largest
#   doujin-published block on the shelf, and the mechanical exclusion the recon counted on is
#   not available. Whatever rule replaces it has to be decided rather than read off.
#   THE SHELF IS NOT EVERY YURI BOOK THE SHOP SELLS. コンカフェ嬢は恋を着る is stocked, is marked
#   【完結】 and is already in this database, and it is not on tag 14 at all. The tag is applied
#   by hand, so its absence from a work says nothing about the work.
"""


def _write(path, state):
    """Rewrite the whole file from `state`, which must already hold every row ever captured.

    Rebuilding from only the current run's fetches is the failure this is written to avoid; it
    has cost this project earlier pages more than once. Callers mutate `state["items"]` and call
    this after every page, so an interrupted run loses at most one page.
    """
    import json
    import pathlib

    def js(v):
        return json.dumps(v, ensure_ascii=False)

    L = [HEADER.rstrip("\n"), "",
         "source: bookwalker.jp",
         "source_url: https://bookwalker.jp/tag/14/",
         "shop_tag: 百合",
         "shop_tag_id: 14",
         "role: discovery-candidates",
         "record_type: retailer_shelf_capture",
         "evidence_axis: content_tier          # never marketing_label; see DEFINITIONS §4",
         f"retrieved: {state['retrieved']}",
         "listings:"]
    for name, meta in sorted(state["listings"].items()):
        L.append(f"  {name}:")
        for k, v in sorted(meta.items()):
            L.append(f"    {k}: {js(v)}")
    L.append("pages_captured:")
    for name in sorted(state["pages"]):
        L.append(f"  {name}: {js(sorted(state['pages'][name]))}")
    L.append("facets_captured:")
    for name in sorted(state["facets"]):
        f = state["facets"][name]
        L.append(f"  {name}:")
        L.append(f"    label: {js(f['label'])}")
        L.append(f"    url: {js(f['url'])}")
        L.append(f"    stated: {js(f['stated'])}")
        L.append(f"    matched: {len(f['ids'])}")
        # The member ids are written out rather than recovered from the flagged rows, because a
        # facet holds ids for rows this capture excluded and rows it has not reached yet. Rebuilt
        # from the rows, a resumed run would under-flag every page it had not already seen.
        L.append(f"    ids: {js(sorted(f['ids']))}")
    L.append("excluded:")
    for k in sorted(state["excluded"]):
        L.append(f"  {k}: {state['excluded'][k]}")
    L.append(f"item_count: {len(state['items'])}")
    # Counted here rather than left to a reader, because a register nobody totals is a register
    # nobody checks (STANDING-INSTRUCTIONS §13).
    rows = list(state["items"].values())
    L.append("summary:")
    for name, n in [
            ("with_author_in_listing", sum(1 for r in rows if r.get("author"))),
            ("without_author", sum(1 for r in rows if not r.get("author"))),
            ("completed_by_facet", sum(1 for r in rows if r.get("completed_facet"))),
            ("completed_by_row_tag", sum(1 for r in rows if r.get("completed_marker"))),
            ("doujin", sum(1 for r in rows if r.get("doujin"))),
            ("direct", sum(1 for r in rows if r.get("direct"))),
            ("male_directed", sum(1 for r in rows if r.get("male_directed"))),
            ("no_imprint", sum(1 for r in rows if not r.get("imprint")))]:
        L.append(f"  {name}: {n}")
    for listing in sorted({r["listing"] for r in rows}):
        L.append(f"  in_{listing}: {sum(1 for r in rows if r['listing'] == listing)}")
    L.append("items:")
    for key in sorted(state["items"], key=lambda k: (k[0], state["items"][k]["title"] or "")):
        r = state["items"][key]
        L.append(f"  - listing: {js(r['listing'])}")
        for k in ("id", "id_kind", "url", "title", "title_listed", "imprint", "imprint_in_title",
                  "author", "author_source", "kind_tag", "volumes", "completed_marker",
                  "doujin", "direct", "completed_facet", "male_directed", "page"):
            L.append(f"    {k}: {js(r.get(k))}")
    L.append("")
    pathlib.Path(path).write_text("\n".join(L))


def _read(path):
    """Whatever a previous run left, as the state a new run continues from."""
    import datetime
    import pathlib

    import yaml

    blank = {"retrieved": datetime.date.today().isoformat(), "listings": {}, "pages": {},
             "facets": {}, "excluded": {}, "items": {}}
    p = pathlib.Path(path)
    if not p.exists():
        return blank
    doc = yaml.safe_load(p.read_text()) or {}
    if not doc.get("items"):
        return blank
    st = dict(blank)
    st["retrieved"] = doc.get("retrieved", blank["retrieved"])
    st["listings"] = doc.get("listings") or {}
    st["pages"] = {k: set(v) for k, v in (doc.get("pages_captured") or {}).items()}
    st["excluded"] = doc.get("excluded") or {}
    for name, f in (doc.get("facets_captured") or {}).items():
        st["facets"][name] = {"label": f["label"], "url": f["url"], "stated": f["stated"],
                              "ids": set(f.get("ids") or [])}
    st["items"] = {(r["listing"], str(r["id"])): r for r in doc["items"]}
    return st


def main(argv=None):
    """Walk the shelf, checkpointing after every page, resuming from whatever is already there."""
    import argparse
    import time
    import urllib.request

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="data/queue/bookwalker-yuri.yaml")
    ap.add_argument("--pause", type=float, default=PAUSE)
    ap.add_argument("--max-pages", type=int, default=60)
    a = ap.parse_args(argv)

    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read().decode("utf-8", "replace")

    st = _read(a.out)
    st.setdefault("excluded", {})
    fetched = 0

    def walk(url_tmpl, parse, per_page, note, skip=(), stated=None):
        """Pages of one listing, stopping when the shop's own count says the listing is done.

        `skip` is not fetched. A resumed run that refetched every page to find out where it got
        to would pay the whole cost of the interruption again, which is the reason for the
        checkpoint in the first place. It needs `stated` from the previous run to know where the
        end is; without one it starts from page 1 and finds out.
        """
        nonlocal fetched
        n = 1
        while n <= a.max_pages:
            if n in skip and stated is not None:
                if n * per_page >= stated:
                    break
                n += 1
                continue
            page = get(url_tmpl.format(n=n))
            fetched += 1
            time.sleep(a.pause)
            if stated is None:
                stated = total(page)
            rows = parse(page)
            if not rows:
                break
            print(f"    {note} page {n}: {len(rows)} rows")
            yield n, rows, stated
            if stated is not None and n * per_page >= stated:
                break
            n += 1

    # Facets first: a row cannot be flagged by a facet that has not been read yet.
    for name, (label, tmpl) in FACETS.items():
        if name in st["facets"] and st["facets"][name]["ids"]:
            print(f"  facet {name}: already captured ({len(st['facets'][name]['ids'])})")
            continue
        ids, stated = set(), None
        for n, rows, stated in walk(tmpl, parse_listing, 60, f"facet {name}"):
            ids |= {r["id"] for r in rows if r["id"]}
        st["facets"][name] = {"label": label, "url": tmpl.format(n=1), "stated": stated,
                              "ids": ids}
        print(f"  facet {name}: {len(ids)} ids, shop says {stated}")

    excl = st["excluded"]
    for listing, tmpl in LISTINGS.items():
        parse = parse_warensai if listing == "warensai" else parse_listing
        per_page = 100 if listing == "warensai" else 60
        done = st["pages"].setdefault(listing, set())
        known = (st["listings"].get(listing) or {}).get("stated")
        for n, rows, stated in walk(tmpl, parse, per_page, listing, skip=done, stated=known):
            st["listings"][listing] = {"url": tmpl.format(n=1), "stated": stated,
                                       "per_page": per_page}
            for r in rows:
                if not r["id"]:
                    excl["no_id"] = excl.get("no_id", 0) + 1
                    continue
                marker = censored_marker(r["title_listed"])
                if marker:
                    # Counted, never written. The title is the thing that must not land in the
                    # repository, so it does not go into the register either.
                    excl[f"censored:{marker}"] = excl.get(f"censored:{marker}", 0) + 1
                    continue
                r = dict(r)
                r["listing"] = listing
                r["page"] = n
                r["author_source"] = "listing" if r["author"] else None
                for fname in FACETS:
                    r[fname] = r["id"] in st["facets"].get(fname, {}).get("ids", set())
                st["items"][(listing, r["id"])] = r
            done.add(n)
            _write(a.out, st)

    _write(a.out, st)
    print(f"{len(st['items'])} items, {fetched} pages fetched, "
          f"{sum(excl.values())} excluded -> {a.out}")
    return 0


# ---------------------------------------------------------------------------------------------
# The authors on the shelf, and which of them need somebody to look a reading up.

LATIN = re.compile(r"^[ -~！-～]+$")

AUTHOR_HEADER = """\
# Authors named on BOOK☆WALKER's 百合 shelf who are NEW to this database. CANDIDATES.
#
# WHERE THEY CAME FROM. data/queue/bookwalker-yuri.yaml, the shelf capture beside this file. A
# name is here because the shop printed it and because nothing in data/names/ or in the built
# corpus already holds it, compared on the folded form (width, case and spacing).
#
# WHY THEY ARE NOT IN data/names/. The works they are attached to are candidates, so the people
# are too. Nothing here is applied to anything; adapters/names/curate.py is the route into the
# store and it takes hand-reviewed entries only. The fields below are shaped to that schema so a
# row that survives review can be moved across without being re-derived.
#
# THREE ROUTES TO A READING, AND ONE OF THEM COSTS A REQUEST.
#   surface   the name is already kana, so the kana IS the reading. No source, no doubt.
#   latin     the name is written in Latin script and has no kana reading to state.
#   stated    the National Diet Library records dcndl:creatorTranscription beside dc:creator.
#             `?creator=` on the OpenSearch API. The HTML record pages return 503; the API does
#             not, so anything wanting a second look wants it from the API.
#
# NOTHING HERE IS GUESSED. A name NDL has never catalogued is `unresolved`, which is a finding and
# not a gap: most of these artists publish on the web, their work has no ISBN, and the library
# holds nothing. Deriving a reading from the characters instead is the one thing this must not do.
# Where NDL states a reading that is not compositional it is kept as stated and flagged, because
# pen names frequently are not compositional and the analyser would be wrong rather than the shop.
#
# TWO KINDS OF SILENCE, WHICH MEAN DIFFERENT THINGS TO WHOEVER RESUMES.
#   attempted: true   NDL was asked and stated nothing. Asking again will not help.
#   attempted: false  nobody has asked yet. This is where a later run picks up.
# This pass is capped, so most rows carry the second. The cap and the ordering are recorded below.
#
# THE LOOKUP ROUTE IS CLOSED AS OF 2026-08-05, AND THE 287 UNATTEMPTED ROWS ARE STOPPED RATHER
# THAN OUTSTANDING. https://ndlsearch.ndl.go.jp/robots.txt lists `Disallow: /api` under
# `User-agent: *`, and the OpenSearch endpoint above is under /api. The 60 rows already attempted
# went out before anyone read that file. This project takes the same rule literally elsewhere:
# adapters/kadokomi/ routes around a robots-disallowed /api/ at real cost, so resuming here is a
# decision for the project owner rather than the next run's default. adapters/names/
# openbd_reading.py is the permitted route to the same fact, and it reaches only names attached to
# a book with an ISBN, which is nobody on this shelf.
"""


def reading_route(name):
    """Which of the three routes settles this name: `surface`, `latin` or `lookup`.

    Deciding this before spending a request is what keeps a capped pass from spending its budget
    on names that never needed one. あとき is kana and answers itself; Rion Nomiya is already
    Latin and has no kana reading to state.
    """
    import pathlib
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from names import kana                                              # noqa: PLC0415

    n = (name or "").strip()
    if not n:
        return None
    if kana.kana_only(n):
        return "surface"
    if LATIN.match(unicodedata.normalize("NFKC", n)):
        return "latin"
    return "lookup"


def shelf_authors(items):
    """`{name: [work titles]}` over every row of a capture that named somebody."""
    out = {}
    for r in items:
        for n in author_names(r.get("author")):
            out.setdefault(n, []).append(r.get("title"))
    return out


def _write_authors(path, doc):
    """Rewrite the author file from `doc`, which must hold every name from every pass."""
    import json
    import pathlib

    def js(v):
        return json.dumps(v, ensure_ascii=False)

    L = [AUTHOR_HEADER.rstrip("\n"), "",
         "source: bookwalker.jp",
         "role: discovery-candidates",
         "record_type: author_reading_candidates",
         f"retrieved: {doc['retrieved']}",
         f"from_capture: {js(doc['from_capture'])}",
         f"reading_lookup: {js(doc['reading_lookup'])}",
         f"ordering: {js(doc['ordering'])}",
         f"attempt_cap: {doc['attempt_cap']}",
         "counts:"]
    rows = list(doc["authors"].values())
    for k, n in [("names", len(rows)),
                 ("resolved", sum(1 for r in rows if r.get("reading"))),
                 ("unresolved_attempted", sum(1 for r in rows
                                              if not r.get("reading") and r.get("attempted"))),
                 ("unresolved_not_attempted", sum(1 for r in rows
                                                  if not r.get("reading")
                                                  and not r.get("attempted")))]:
        L.append(f"  {k}: {n}")
    L.append("authors:")
    for name in sorted(doc["authors"], key=lambda n: (-doc["authors"][n]["works"], n)):
        r = doc["authors"][name]
        L.append(f"  {js(name)}:")
        for k in ("works", "route", "attempted", "status", "reading", "reading_basis",
                  "reading_source_kind", "reading_note", "source", "source_url", "reviewed",
                  "example_work"):
            if k in r:
                L.append(f"    {k}: {js(r[k])}")
    L.append("")
    pathlib.Path(path).write_text("\n".join(L))


def authors_main(argv=None):
    """Resolve readings for shelf authors new to this database, up to a cap, resumably."""
    import argparse
    import datetime
    import json
    import pathlib
    import sys
    import time
    import urllib.request

    import yaml

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from names import kana, ndl_reading                                 # noqa: PLC0415

    ap = argparse.ArgumentParser(description=authors_main.__doc__.splitlines()[0])
    ap.add_argument("--capture", default="data/queue/bookwalker-yuri.yaml")
    ap.add_argument("--out", default="data/queue/bookwalker-yuri-authors.yaml")
    ap.add_argument("--cap", type=int, default=60)
    ap.add_argument("--pause", type=float, default=PAUSE)
    a = ap.parse_args(argv)

    cap = yaml.safe_load(pathlib.Path(a.capture).read_text())
    by_name = shelf_authors(cap["items"])

    # Everything this database already holds a name for, folded. Read from the built store, the
    # curated file and the corpus rather than from one of them, because a name can be in the
    # corpus without having reached the store yet.
    known = set(yaml.safe_load(pathlib.Path("data/names/authors.yaml").read_text())["names"])
    known |= set(yaml.safe_load(pathlib.Path("data/names/curated.yaml").read_text())
                 .get("authors") or {})
    known |= {w["author"] for w in population.works() if w.get("author")}
    known = {match_key(k) for k in known}

    doc = {"retrieved": datetime.date.today().isoformat(),
           "from_capture": a.capture,
           "reading_lookup": "https://ndlsearch.ndl.go.jp/api/opensearch?creator=",
           "ordering": "kanji-bearing names first, most shelf works first; kana and Latin names "
                       "are settled without a request and do not consume the cap",
           "attempt_cap": a.cap,
           "authors": {}}
    if pathlib.Path(a.out).exists():
        old = yaml.safe_load(pathlib.Path(a.out).read_text()) or {}
        doc["authors"] = old.get("authors") or {}
        doc["retrieved"] = old.get("retrieved", doc["retrieved"])

    for name, works in by_name.items():
        if match_key(name) in known:
            continue
        r = doc["authors"].setdefault(name, {})
        r["works"] = len(works)
        r["example_work"] = works[0]
        r.setdefault("route", reading_route(name))
        r.setdefault("attempted", False)
        if r["route"] == "surface" and not r.get("reading"):
            r.update(reading=kana.to_katakana(name), reading_basis="surface",
                     reading_source_kind="derived", source="surface", attempted=True,
                     status="stated-by-the-name-itself",
                     reading_note="The name is written in kana, so the kana is the reading.")
        elif r["route"] == "latin" and not r.get("reading"):
            r.update(attempted=True, status="latin-script",
                     reading_note="Written in Latin script; there is no kana reading to state.")
    _write_authors(a.out, doc)

    todo = [n for n, r in doc["authors"].items()
            if r["route"] == "lookup" and not r["attempted"]]
    todo.sort(key=lambda n: (-doc["authors"][n]["works"], n))
    todo = todo[:a.cap]
    print(f"{len(doc['authors'])} names new to us; {len(todo)} lookups this pass "
          f"(cap {a.cap}), {sum(1 for r in doc['authors'].values() if not r['attempted'])} "
          f"not yet attempted")

    # ROBOTS IS ASKED BEFORE THE FIRST REQUEST, not remembered. The 60 rows already in this file
    # went out on a path ndlsearch.ndl.go.jp/robots.txt forbids, because nothing here looked and
    # the one thing that could have looked was matching against a truncated copy of the rules
    # (recon/probe.py, fixed 2026-08-05). Refusing here leaves the rest `attempted: false`, which
    # is what they are: nobody asked, and on this route nobody may.
    from recon import probe                                          # noqa: PLC0415
    import urllib.parse                                              # noqa: PLC0415
    if todo:
        path = urllib.parse.urlsplit(ndl_reading.query("x")).path
        rules = probe.robots_rules("ndlsearch.ndl.go.jp")
        if rules["present"] and not probe.allowed(path, rules["disallow"]):
            print(f"Refusing to fetch: robots.txt disallows {path} for User-agent: *. "
                  f"{len(todo)} name(s) stay unattempted. adapters/names/openbd_reading.py is the "
                  f"permitted route, and it reaches only names attached to a book with an ISBN.")
            return 1

    for i, name in enumerate(todo, 1):
        url = ndl_reading.query(name)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as resp:
                xml = resp.read().decode("utf-8", "replace")
        except Exception as e:                                          # noqa: BLE001
            print(f"  {i}/{len(todo)} {name}: {type(e).__name__}")
            continue
        time.sleep(a.pause)
        reading, ev = ndl_reading.resolve(xml, name)
        r = doc["authors"][name]
        r["attempted"] = True
        r["status"] = ev["status"]
        r["source"] = "NDL Search OpenSearch"
        r["source_url"] = url
        r["reviewed"] = doc["retrieved"]
        if reading:
            r.update(reading=reading, reading_basis="stated",
                     reading_source_kind="national-library")
            note = (f"NDL states this transcription beside the name on {ev['records']} record(s), "
                    f"e.g. {ev['examples'][0][0]!r} ({ev['examples'][0][1]}).")
            if not ndl_reading.is_kana(reading):
                note += " Not katakana as stated; recorded as NDL carries it and needs review."
            r["reading_note"] = note
        else:
            r["reading_note"] = {
                "no-record": "NDL holds no record under this name. Most of these artists publish "
                             "on the web and their work has no ISBN, so this is silence rather "
                             "than a negative finding.",
                "conflicting": "NDL carries more than one transcription for this written name, "
                               "which may be two people. Left unresolved on purpose.",
            }.get(ev["status"], f"NDL answered {ev['status']}.")
            if ev["status"] == "conflicting":
                r["reading_note"] += " Readings seen: " + " / ".join(ev.get("readings", []))
        print(f"  {i}/{len(todo)} {name}: {ev['status']} {reading or ''}")
        _write_authors(a.out, doc)

    _write_authors(a.out, doc)
    n = doc["authors"]
    print(f"{len(n)} names -> {a.out}: "
          f"{sum(1 for r in n.values() if r.get('reading'))} resolved, "
          f"{sum(1 for r in n.values() if not r.get('reading') and r['attempted'])} attempted "
          f"and unresolved, "
          f"{sum(1 for r in n.values() if not r['attempted'])} not attempted")
    return 0


if __name__ == "__main__":
    import sys as _sys
    if "--authors" in _sys.argv:
        _sys.argv.remove("--authors")
        raise SystemExit(authors_main())
    raise SystemExit(main())
