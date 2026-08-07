#!/usr/bin/env python3
"""Where each web-manga engine writes the links to the shops selling its series' volumes.

WHAT THIS IS FOR. 862 of the works this database holds have a web serialisation and no print
edition attached, and most of them have collected volumes nobody had asked the right source about.
A platform knows: it links from the series to the shops. Those links carry identifiers
(`stores.py`), an identifier reaches the bibliography, and the bibliography supplies the record.

FIVE ENGINES, NOT FORTY-THREE PLATFORMS. The survey on 2026-08-07 found the corpus's platforms
sitting on a handful of engines, so a parser serves many sites at once:

  GigaViewer      Hatena's engine, run by 講談社, 集英社, 小学館, 双葉社, 新潮社, 一迅社 and more.
  Comici          ビッコミ, チャンピオンクロス, 竹コミ, キミコミ, Gコミ, ヤングチャンピオン,
                  花とゆめ+, ライコミ, HERO'S Web, COMICリュエル, アサコミ, マンガクロス.
  カドコミ        KADOKAWA's own Next.js build.
  pixivコミック   its own JSON API.
  comicブースト   its own server-rendered build.

EVERY FUNCTION HERE TAKES TEXT AND RETURNS DATA. Fetching lives in `capture.py`, so each of these
is tested offline against a fixture taken off the real page (STANDING-INSTRUCTIONS §12).

THE JOIN IS AN IDENTIFIER, NEVER A TITLE. A parser returns the platform's own id for the series
alongside the shop link, because that id is what the work is already held under. Matching a volume
title to a series title would be matching on titles, which this project has already been burned by:
`トワ・エ・モア` is a 1996 コンパス anthology and a 2024 講談社 series at once. Where an engine
offers a page of volumes with no link back to the series, that page is reported as unusable rather
than joined on the strength of a string.
"""
import json
import re

# A GigaViewer コミックス page lists a volume, a link to the shop selling it, and, on some of the
# platforms, a link to the series' first episode. That episode URL is the join: it is the same
# address the database already holds for the serialisation.
GIGA_EPISODE = re.compile(r'href="(https?://[a-z0-9.\-]+/episode/\d+)"')
GIGA_ANY_LINK = re.compile(r'href="(https?://[^"]+)"')


def gigaviewer_comics(html, host):
    """[{book_urls, episode_url}] from a GigaViewer /comics page.

    HOW THE GROUPING WORKS, AND WHY IT IS POSITIONAL. The eighteen GigaViewer platforms render this
    page in at least four markup generations: classic `<li class="comics-item">`, the Next.js
    `Comics_comic__…` build, and two more. Keying on a class name would serve one of them. What
    every generation shares is document ORDER: a volume's cover link and its purchase link come
    before the "第一話を読む" link belonging to the same volume. So links are walked in order and
    each episode link closes the group before it.

    THE HAZARD THIS SHAPE CARRIES, and why the caller is handed a list rather than one URL. If one
    item renders no episode link, its book link stays pending and lands in the NEXT item's group,
    which would attach a print run to the wrong serialisation. So a group is offered whole and
    `stores.one_isbn` refuses a group whose links disagree about which book they are.

    On the platforms that render no episode link at all this returns nothing, which is the honest
    answer: the page states volumes and does not say which series they belong to.
    """
    out, pending = [], []
    for m in GIGA_ANY_LINK.finditer(html or ""):
        url = m.group(1)
        if host in url:
            if GIGA_EPISODE.fullmatch(f'href="{url}"'):
                if pending:
                    out.append({"book_urls": pending, "episode_url": url})
                pending = []
            continue
        if url not in pending:
            pending.append(url)
    return out


# The series sidebar. Every GigaViewer page for a series carries `series-book-details`, one
# `series-book-detail` per collected volume, each holding the volume's title and a link to every
# shop the publisher offers for it. This is the route: the block belongs to the series whose page
# it is on, so the volume is joined to the serialisation by the address rather than by a title.
#
# Two headings appear over the same markup. 講談社 and 集英社 write コミックス情報 and 一迅社 writes
# 関連商品, which is worth knowing because "related products" is a weaker claim than "this series'
# volumes" and a novel a manga was adapted from would sit there just as comfortably. The block's
# own stated volume title is captured for that reason and is never used to decide anything.
BOOK_DETAILS = re.compile(r'class="series-book-details[^"]*"')
# Where the block ends. The container is not closed by anything this side of a DOM parser, so the
# boundary is the next sibling the engine renders. Written as alternatives rather than as one
# closing tag because the sidebar's contents differ by platform: 集英社 follows it with the Hatena
# bookmark strip, 講談社 with the author profile, and 双葉社 with neither.
#
# THIS BOUNDARY IS LOAD-BEARING. Without it the block ran to the end of the document on
# 少年ジャンプ+, so every footer link joined the last volume's group and `stores.one_isbn` was
# deciding between a volume's shops and the whole site navigation.
BOOK_DETAILS_END = re.compile(r'<div class="series-(?!book-detail)|</aside>|</section>|<footer')
BOOK_DETAIL = re.compile(r'class="series-book-detail"(.*?)(?=class="series-book-detail"|\Z)', re.S)
BOOK_TITLE = re.compile(r'alt="([^"]*)"')
BOOK_HREF = re.compile(r'href="([^"]+)"')


def gigaviewer_books(html):
    """[{title, urls}] from a GigaViewer series sidebar, one entry per collected volume.

    `urls` is every link the block offers, unfiltered, because which of them states a number
    differs by publisher: 集英社 puts the ISBN in the cover link and a short Amazon link beside it,
    一迅社 puts it in the Amazon link and gives 楽天 a title search. Deciding is `stores`' job.
    """
    m = BOOK_DETAILS.search(html or "")
    if not m:
        return []
    rest = html[m.end():]
    end = BOOK_DETAILS_END.search(rest)
    region = rest[:end.start()] if end else rest
    out = []
    for b in BOOK_DETAIL.finditer(region):
        block = b.group(1)
        t = BOOK_TITLE.search(block)
        urls, seen = [], set()
        for h in BOOK_HREF.finditer(block):
            u = h.group(1).replace("&amp;", "&")
            if u not in seen:
                seen.add(u)
                urls.append(u)
        if urls or t:
            out.append({"title": (t.group(1).strip() if t else ""), "urls": urls})
    return out


# ガンガンONLINE is not GigaViewer and renders its 単行本 section as its own Next.js component, one
# `Volume2_volume__` per volume with a shop-banner row. Same shape, different class names.
GANGAN_VOLUME = re.compile(r'class="Volume2_volume__[^"]*"(.*?)(?=class="Volume2_volume__[a-zA-Z0-9_]*"'
                           r'>|</section>|\Z)', re.S)
GANGAN_NAME = re.compile(r'class="Volume2_volume__name__[^"]*">([^<]*)<')


def ganganonline_books(html):
    """[{title, urls}] from a ガンガンONLINE title page's 単行本 section."""
    out = []
    for m in re.finditer(r'class="Volume2_volume__thumbnail(.*?)(?=class="Volume2_volume__thumbnail'
                         r'|</main>|\Z)', html or "", re.S):
        block = m.group(1)
        n = GANGAN_NAME.search(block)
        urls, seen = [], set()
        for h in BOOK_HREF.finditer(block):
            u = h.group(1).replace("&amp;", "&")
            if u.startswith("http") and u not in seen:
                seen.add(u)
                urls.append(u)
        if urls:
            out.append({"title": (n.group(1).strip() if n else ""), "urls": urls})
    return out


# The viewer's back matter. GigaViewer appends "link pages" to a chapter, each an image with an
# optional destination, and the first of them is the series' own コミックス advertisement.
GIGA_LINK_SLOT = re.compile(
    r'class="link-slot">.*?data-src="(?P<img>[^"]*)".*?<a\s[^>]*class="(?P<cls>gtm-[a-z0-9\-]+)"'
    r'\s*href="(?P<href>[^"]+)"', re.S)


def gigaviewer_link_slots(html):
    """[{slot, url}] for the destinations of a GigaViewer viewer page's back-matter link pages.

    `slot` is the platform's own name for the position, `gtm-back-page1-number1` and so on. It
    matters because the slots are NOT equivalent: page 1 carries the series' own volume on every
    page inspected, and later pages carry house advertising, an X account, a questionnaire, or
    another series entirely. A caller that treats them alike will attach a print run to the wrong
    work, so the position is returned and the decision is left where it can be justified.
    """
    out = []
    for m in GIGA_LINK_SLOT.finditer(html or ""):
        out.append({"slot": m.group("cls"), "url": m.group("href")})
    return out


def kadokomi_next_data(html):
    """カドコミ's own view of a work: `{code, title, rating, labels, comics: [...]}` or None.

    Read out of `__NEXT_DATA__` on `/detail/<code>`, which robots.txt permits, rather than the
    `/api/` path it disallows. `adapters/kadokomi/catalogue.py` established that route and this
    reads the same document for a different field.

    `comics` is the platform's list of collected volumes, each with the release date KADOKAWA
    states and the shop links it offers. The links are per volume even where several volumes point
    at one shop page, so what is stored is what the platform said.
    """
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html or "",
                  re.S)
    if not m:
        return None
    try:
        doc = json.loads(m.group(1))
    except ValueError:
        return None
    queries = (((doc.get("props") or {}).get("pageProps") or {})
               .get("dehydratedState") or {}).get("queries") or []
    data = None
    for q in queries:
        d = (q.get("state") or {}).get("data")
        if isinstance(d, dict) and "work" in d:
            data = d
            break
    if not data:
        return None
    work = data.get("work") or {}
    comics = (data.get("comics") or {}).get("result")
    if comics is None:
        comics = [c for c in (data.get("firstComic"), data.get("latestComic")) if c]
    out = {
        "code": work.get("code"),
        "title": work.get("title"),
        # KADOKAWA's own rating on its own work. Kept because DEFINITIONS §7 excludes a work
        # marketed as pornography and this is the platform saying so about itself.
        "rating": work.get("ratingLevel"),
        # The publisher's own imprint labels, which ARE publisher-side evidence (§4). Not used
        # here; carried so the capture does not throw away the one field that could bear on it.
        "labels": ((work.get("internal") or {}).get("labelNames")) or [],
        "comics": [],
    }
    seen = set()
    for c in comics or []:
        if c.get("id") in seen:
            continue
        seen.add(c.get("id"))
        out["comics"].append({
            "id": c.get("id"),
            "title": c.get("title"),
            "release": c.get("release"),
            "stores": [{"code": s.get("code"), "url": s.get("url")}
                       for s in (c.get("stores") or [])],
        })
    return out


# Comici renders the 単行本情報 block with a link per volume and a "全N冊" link to the whole list.
COMICI_ITEM = re.compile(r'href="/store_items/(\d+)"')
COMICI_ALL = re.compile(r'href="(/store_items/series/\d+/\d+)"')
COMICI_COUNT = re.compile(r'series-store-more-label">全(\d+)冊')


def comici_store_items(html):
    """`{items: [id], all_url, stated}` from a Comici series, episode or volume-list page.

    The series page shows the newest two volumes and a link to the rest, so `stated` is how many
    the platform says there are and `items` is how many this page happened to render. A caller
    wanting them all follows `all_url`; a caller wanting one identifier for the work does not.
    """
    ids, seen = [], set()
    for m in COMICI_ITEM.finditer(html or ""):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            ids.append(m.group(1))
    allm = COMICI_ALL.search(html or "")
    cnt = COMICI_COUNT.search(html or "")
    return {"items": ids, "all_url": allm.group(1) if allm else None,
            "stated": int(cnt.group(1)) if cnt else None}


COMICI_STORE_LINK = re.compile(r'<a href="(https?://[^"]+)" class="store-detail-buy-btn"')


def comici_store_links(html):
    """The shop URLs a Comici `/store_items/<id>` page offers for one volume.

    Amazon appears twice on these pages, once for the printed book and once for the Kindle file.
    Both are kept: telling them apart is `stores.isbn_of`'s job and it does it by check digit, not
    by which one came first.
    """
    out, seen = [], set()
    for m in COMICI_STORE_LINK.finditer(html or ""):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


def pixiv_ad_books(text):
    """[{title, amazon_url, image_url}] from pixivコミック's `works/<id>/ad_books`.

    pixiv states the printed book as an Amazon product link whose ASIN is the ISBN-10, and states
    it a second time in the cover image path. Both are returned, because one of them survives when
    the other is missing and they are checked against each other by the caller.
    """
    try:
        doc = json.loads(text or "")
    except ValueError:
        return []
    books = ((doc.get("data") or {}).get("ad_books")) or []
    return [{"title": b.get("title"), "amazon_url": b.get("amazon_url"),
             "image_url": b.get("image_url")} for b in books if isinstance(b, dict)]


YANMAGA_BANNER = re.compile(r'class="mod-banner-comics-link[^"]*" href="(https?://[^"]+)"')


def yanmaga_series_url(url):
    """The ヤンマガWeb series page for a viewer URL.

    The address this database holds is `/comics/<title>/<chapter hash>`, which redirects into the
    reader and carries no shop link. Its parent path is the series page, which carries 講談社's own
    product link. Dropping the last segment is the whole of it, and it is written down because the
    difference between the two pages is invisible from the URL.
    """
    u = str(url or "").split("?")[0].rstrip("/")
    parts = u.split("/")
    return "/".join(parts[:-1]) if len(parts) > 5 else u


def yanmaga_books(html):
    """The 講談社 product pages a ヤンマガWeb series page links, newest volume first."""
    out, seen = [], set()
    for m in YANMAGA_BANNER.finditer(html or ""):
        u = m.group(1).replace("&amp;", "&")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


COMICBOOST_BOOK = re.compile(
    r'class="comic-list-side-by-side-item" href="(https?://www\.gentosha-comics\.net/book/[^"]+)"')


def comicboost_books(html):
    """The 幻冬舎コミックス book pages a comicブースト series page links to, one per volume."""
    out, seen = [], set()
    for m in COMICBOOST_BOOK.finditer(html or ""):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


# A publisher's own page for one book, asked for the number it states. One pattern per publisher
# rather than one that tries to serve them all, because these pages carry other books' ISBNs and a
# pattern loose enough to survive four markups is loose enough to return one of those. Each of
# these was read off the live page on 2026-08-07 and each pins the field the publisher labels.
PUBLISHER_ISBN = [
    # 新潮社 states it in a meta tag of its own naming, which is the cleanest of the four.
    ("shinchosha.co.jp", re.compile(r'<meta name="shc-isbn" content="(\d{13})"')),
    # 幻冬舎コミックス puts it in a definition table. The gap between the label and the value runs
    # to a dozen tabs, so the pattern spans whitespace deliberately.
    ("gentosha-comics.net", re.compile(r"<th>ISBN</th>\s*<td>\s*(\d{13})\s*<")),
    # 少年画報社 likewise, with the hyphenated form.
    ("shonengahosha.co.jp", re.compile(r"ISBN[^0-9]{0,40}?(97[89][0-9\-]{10,15}[0-9])")),
    # 小学館 embeds its catalogue row as escaped JSON. `isbn13_cd` is the book's own field; the
    # page also lists related titles, which is why the field name is required rather than a
    # thirteen-digit run.
    ("shogakukan.co.jp", re.compile(r"isbn13_cd&quot;:&quot;(\d{13})&quot;")),
    # 講談社 uses the standard Open Graph book tag, which is the one publisher here that needs no
    # site-specific reading at all.
    ("kodansha.co.jp", re.compile(r'<meta property="books:isbn" content="(\d{13})"')),
]


# A shop id that identifies a book in a publisher's own catalogue, and the page that catalogue
# serves for it. Following one is a request; completing it into an ISBN by arithmetic is not done
# (see `stores.py` for why).
PUBLISHER_PAGE = {
    "shogakukan_book": "https://www.shogakukan.co.jp/books/{}",
    "shogakukan_jdcn": "https://www.shogakukan.co.jp/books/{}",
    "shinchosha_book": "https://www.shinchosha.co.jp/book/{}/",
    "gentosha_book": "https://www.gentosha-comics.net/book/{}.html",
    "shonengahosha_book": "https://www.shonengahosha.co.jp/book_Info.php?id={}",
}


def publisher_page(shop, shop_id):
    """The publisher's own page for a shop id, or None where the publisher is not one of these."""
    pat = PUBLISHER_PAGE.get(shop or "")
    return pat.format(shop_id) if pat and shop_id else None


# Publishers whose own book code IS the middle of their ISBNs, so that a page reached by the code
# can be checked against the number it states. 幻冬舎コミックス's `b671924` is not one: its code is
# a catalogue serial with no relation to 978-4-344-85698-1, so there is nothing to check and the
# answer is taken as given.
CODE_IN_ISBN = {"shogakukan_book", "shogakukan_jdcn", "shinchosha_book"}


def states_id(isbn, shop, shop_id):
    """Whether an ISBN read off a publisher's page is the book the id asked for.

    A site answering every unknown path with its newest book is the failure this project meets most
    (STANDING-INSTRUCTIONS §4), and `publisher_dates.py` has already been bitten by it. Where the
    code is part of the number, the number is the check: `09863259` has to appear in
    `9784098632596`. Where it is not, there is nothing to check.
    """
    if not isbn:
        return False
    if shop not in CODE_IN_ISBN:
        return True
    sid = re.sub(r"[^0-9]", "", str(shop_id or ""))
    return bool(sid) and sid in isbn


def publisher_isbn(html, host=""):
    """The ISBN a publisher's book page states for its own book, in digits, or None.

    WHY THE HOST IS PASSED IN. The patterns are not interchangeable and trying them all in turn
    would mean the loosest one answering for every publisher. A host with no pattern returns None,
    which says the page was not read rather than that the book has no ISBN.
    """
    for h, pat in PUBLISHER_ISBN:
        if h in (host or ""):
            m = pat.search(html or "")
            return re.sub(r"[^0-9]", "", m.group(1)) if m else None
    return None
