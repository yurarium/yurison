#!/usr/bin/env python3
"""What a shop link says about the edition behind it: an ISBN, a shop id, or nothing.

WHY THIS EXISTS. A web-manga platform links from a series to the shops selling that series'
volumes, and those links carry identifiers. A link is Tier C the moment it points at a shop, so
none of this attests anything; it says which edition to go and ask the bibliography about
(REQUIREMENTS §1, and adapters/madb/by_isbn.py for the rule this follows).

TWO KINDS OF LINK, AND ONLY ONE OF THEM IS FREE.

  A link that STATES the number. `s-manga.net/items/contents.html?isbn=978-4-08-894279-7` and
  `futabasha.co.jp/book/97845758625770000000` both carry the ISBN in the path, and an Amazon
  product link for a printed book carries the ISBN-10 as its ASIN. Reading it costs no request.

  A link that carries only the SHOP'S OWN id. `cmoa.jp/title/344812/`,
  `shinchosha.co.jp/book/772966/`, `gentosha-comics.net/book/b671924.html`. The number is on the
  page and nowhere else, so it costs a fetch, which `capture.py` decides about.

WHY A PUBLISHER'S NUMBERING IS NOT DECODED HERE, though it plainly could be. 新潮社 puts the six
ISBN digits straight in its book path and 小学館 puts the publisher prefix and six more in its own,
so `978-4-10-` + `772966` + a check digit is one line of arithmetic. It is not done, because it is
an inference about a numbering scheme rather than a number anybody stated, and the cost of being
wrong is not an empty answer: it is a valid ISBN belonging to a different book, which reaches the
bibliography, comes back with a record, and joins a print run to the wrong serialisation. A wrong
merge is hard to see once made. The page states the ISBN, so the page is asked.

WHY AN ASIN IS CHECKED AND A STATED ISBN IS NOT. `adapters/isbn.py` refuses to validate check
digits, on the ground that a retailer's typo should still get to reach a catalogue and come back
empty. That rule is about a number a source CALLED an ISBN. An ASIN is not called one: Amazon uses
the same ten-character field for `4253013929`, which is a printed book's ISBN-10, and for
`B0CW1FS2V1`, which is a Kindle file with no ISBN at all. The check digit is how the two are told
apart, so it is a recognition test and not a validation of somebody's data entry.
"""
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import isbn as _isbn                                                           # noqa: E402

# Amazon writes a product several ways and the platforms in this corpus use most of them:
# /dp/<asin>, /gp/product/<asin>, /exec/obidos/ASIN/<asin>/<affiliate>, /o/ASIN/<asin>/<affiliate>.
# The image host also names the ASIN, which is how pixivコミック states one without a product link.
ASIN = re.compile(r"amazon(?:\.co\.jp|\.com)?/(?:[a-z]{2}/)?"
                  r"(?:dp|gp/product|exec/obidos/ASIN|o/ASIN|images/P)/([0-9A-Za-z]{10})")

# An ISBN stated in a query string, which is how 集英社's s-manga.net and several publisher search
# pages carry it. Hyphenated or not.
STATED = re.compile(r"[?&](?:isbn|ISBN|isbn13|jan)=([0-9\-]{10,17}[0-9Xx])")

# 双葉社 pads the ISBN to twenty digits with zeros: /book/97845758625770000000.
FUTABASHA = re.compile(r"futabasha\.co\.jp/book/(97[89]\d{10})\d*")

# A bare thirteen-digit ISBN anywhere in the path, which several publisher sites use directly.
BARE13 = re.compile(r"(?<![0-9])(97[89])[-\s]?(\d[-\s]?){9}\d(?![0-9])")

# Shops whose id identifies a title or a volume without stating a number. Each maps to the name the
# capture files it under, so a later pass knows which page to open.
SHOP_ID = [
    ("cmoa_title", re.compile(r"cmoa\.jp/title/(\d+)/(?:vol/(\d+)/)?")),
    ("shinchosha_book", re.compile(r"shinchosha\.co\.jp/book/(\d+)/")),
    # 小学館's own book code, which its catalogue addresses directly and ビッコミ addresses through
    # the JDCN its comic database uses. The first eight digits of the JDCN are the same code:
    # `098632590000d0000000` is `/books/09863259`, which is ベラドンナの恋人 and states
    # 978-4-09-863259-6. The code is followed to that page rather than completed into an ISBN here,
    # and the page has to state a number containing the code before it is believed.
    ("shogakukan_jdcn",
     re.compile(r"csbs\.shogakukan\.co\.jp/book/detail-volume\?cp=\d+&(?:amp;)?jdcn=(\d{8})")),
    ("shogakukan_book", re.compile(r"www\.shogakukan\.co\.jp/books/(\d+)")),
    ("gentosha_book", re.compile(r"gentosha-comics\.net/book/(b\d+)\.html")),
    ("shonengahosha_book", re.compile(r"shonengahosha\.co\.jp/book_Info\.php\?id=(\d+)")),
    ("comicryu_book", re.compile(r"comic-ryu\.jp/[^\s\"']*?/(\d+)")),
]

# A short link states nothing and resolves to something that might. Kept as its own kind so a
# caller can decide whether one redirect per volume is worth it.
SHORTENER = re.compile(r"(amzn\.asia|amzn\.to)/")


def isbn_of(url):
    """The ISBN a link states, in thirteen digits, or None where it states none.

    Order matters only in that a stated ISBN beats an ASIN: `s-manga.net/...?isbn=` is the
    publisher's own number, and nothing else on that URL competes with it.
    """
    u = str(url or "")
    m = STATED.search(u)
    if m:
        return _isbn.isbn13(m.group(1))
    m = FUTABASHA.search(u)
    if m:
        return _isbn.isbn13(m.group(1))
    m = ASIN.search(u)
    if m and _isbn.valid10(m.group(1)):
        return _isbn.isbn13(m.group(1))
    m = BARE13.search(u)
    if m:
        return _isbn.isbn13(re.sub(r"[^0-9]", "", m.group(0)))
    return None


def shop_id_of(url):
    """`(kind, id, volume)` for a link that carries only a shop's own identifier, else None.

    `volume` is filled where the shop addresses a single volume, as コミックシーモア does with
    `/title/340870/vol/2/`, and is None where the link is to the title as a whole.
    """
    u = str(url or "")
    for kind, pat in SHOP_ID:
        m = pat.search(u)
        if m:
            vol = m.group(2) if m.re.groups > 1 else None
            return kind, m.group(1), int(vol) if vol else None
    return None


def is_short(url):
    """Whether this link states nothing until it is followed."""
    return bool(SHORTENER.search(str(url or "")))


def one_isbn(urls):
    """The one ISBN a group of links agrees on, or None where they do not agree.

    WHY DISAGREEMENT IS SILENCE RATHER THAN A CHOICE. A platform's コミックス page is grouped by
    document order, and a volume that renders no link back to its series leaves its shop link to be
    picked up by the next volume's group. Two ISBNs in one group is exactly what that looks like,
    and it is also what a page listing a boxed set beside its volumes looks like. Either way the
    group no longer says which book belongs to the series, and guessing would attach a print run to
    the wrong serialisation. So a split group answers nothing and is counted.

    A link that states no ISBN does not count against agreement: a page offering Amazon, 楽天 and
    セブンネット for one book has three links and one number.
    """
    got = {i for i in (isbn_of(u) for u in urls or []) if i}
    return got.pop() if len(got) == 1 else None


def read(url):
    """One link as `{"url", "isbn"?, "shop"?, "shop_id"?, "volume"?, "short"?}`.

    A single shape for every link a platform offers, so the capture stores what a link said rather
    than which regular expression happened to match it.
    """
    out = {"url": str(url or "")}
    got = isbn_of(url)
    if got:
        out["isbn"] = got
        return out
    sid = shop_id_of(url)
    if sid:
        out["shop"], out["shop_id"] = sid[0], sid[1]
        if sid[2]:
            out["volume"] = sid[2]
        return out
    if is_short(url):
        out["short"] = True
    return out
