#!/usr/bin/env python3
"""Publication dates for the queue rows an ISBN alone could not date, taken from the publisher.

WHY THIS EXISTS. `data/queue/cmoa-volumes.yaml` filed 49 works `isbn-stated-not-catalogued`: the
shop prints an ISBN, and neither the 文化庁メディア芸術データベース nor openBD has a record of it,
so §6's date went unanswered for want of one lookup. GAPS §17 measured where the answer is and
stopped at the terms of the aggregator that holds it.

THE PUBLISHER IS THE BETTER SOURCE, NOT MERELY THE SAFER ONE. Every one of these 49 is a book with
a publisher, and a publisher stating the date of its own book is first-hand where a bibliographic
aggregator is second-hand. REQUIREMENTS §1 puts publisher sites in Tier B against Tier A for the
catalogues, and that ordering settles which source to believe when two of them speak. Here no Tier
A catalogue speaks at all, so the question it settles does not arise, and what is left is that the
publisher is the party that published the book.

45 of the 49 are 一迅社, which runs its own bibliographic site keyed on the ISBN, so the bulk is one
host and one page shape. The other four are one book each at four publishers, and those URLs are
pinned in PAGES because a publisher site with one book wanted of it does not justify a crawler.

WHAT COUNTS AS A DATE HERE. 発売日 as the publisher states it, the day the publisher put the book on
sale. It is NOT the 奥付 convention the catalogues carry, which runs up to a month later;
`cmoa_volumes.PREFERENCE` records why that matters where both speak and why it does not arise here.

TWO GUARDS, AND THE SECOND ONE EARNED ITS PLACE ON THIS RUN. A page reached from the ISBN must
state that ISBN, because a site answering every unknown path with its newest book is the failure
this project meets most (STANDING-INSTRUCTIONS §4). And the page must be ABOUT the same book the
shop's row is about, because the shop's ISBN can be another book's: cmoa states 9784758062862 for
える・えるシスター 1巻, and 一迅社's own page for that ISBN is 白砂村 (7) by 今井神. Without the
title check that row would have been filed with a volume of a horror series' publication date and
would have read as answered. `REFUTED` records the one case and where the right page is.

Usage:  publisher_dates.py                  fetch what is outstanding and write the dates back
        publisher_dates.py --offline        parse only what the cache already holds
        publisher_dates.py --report         say what is outstanding and where each would be asked
"""
import argparse
import datetime
import json
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cmoa_volumes                                                            # noqa: E402
import identity                                                                # noqa: E402
import net                                                                     # noqa: E402
import paths                                                                   # noqa: E402
from recon import probe                                                        # noqa: E402

# What a stored date rests on. These are separate values on purpose: a reader has to be able to
# tell a publisher's own statement from an aggregator's record, and an aggregator-sourced row has
# to be findable again if a publisher page appears for it later.
BASIS = "publisher-own-page"

# A publication date does not change, so the cache answers before the host does, for a year.
AGE = 365

TARGET_BASIS = "isbn-stated-not-catalogued"


# ── 一迅社 ────────────────────────────────────────────────────────────────────────────────────
# data.ichijinsha.co.jp keys its pages on the eight digits between the 978-4 prefix and the check
# digit, so 9784758070041 is /detail/75807004. There is no robots.txt on that host at all.

def ichijinsha_url(isbn):
    """The 一迅社 book page for an ISBN."""
    return f"https://data.ichijinsha.co.jp/detail/{isbn[4:12]}"


# `<h2>少女美学</h2>` … `<p>ISBN 9784758070041 ／ A5版 定価：943円（税込） 発売日 2006-09-16</p>`.
# The ISBN and the date are taken from ONE match rather than from two searches, because the same
# page carries a Vue template for the series listing whose `release_date` placeholders sit under
# the same heading, and a lone date pattern would eventually find a rendered one of those.
ICHIJINSHA = re.compile(r"ISBN\s*(\d{13})[^<]*?発売日\s*(\d{4}-\d{2}-\d{2})")
ICHIJINSHA_TITLE = re.compile(r"<h2>(.*?)</h2>", re.S)


def ichijinsha_book(body):
    """`{isbn, title, date}` from a 一迅社 book page, or None where it states no book."""
    m = ICHIJINSHA.search(body or "")
    t = ICHIJINSHA_TITLE.search(body or "")
    if not m:
        return None
    return {"isbn": m.group(1), "date": m.group(2), "title": _text(t.group(1)) if t else None}


# ── 双葉社 ────────────────────────────────────────────────────────────────────────────────────
# www.futabasha.co.jp renders its book pages client-side, so the page itself states nothing a
# parser can read. Its own sitemap lists the book, and the sitemap's id is the ISBN followed by
# seven zeros; the site's script reads the bibliography from book-api.futabasha.co.jp, whose
# robots.txt is `Disallow:` with nothing after it. That endpoint is asked here instead of the page,
# because a JSON record the publisher serves is the same statement in a form that can be checked.

def futabasha_url(isbn):
    return f"https://book-api.futabasha.co.jp/book_details?jdcn_code={isbn}0000000&media=1"


def futabasha_book(body):
    """`{isbn, title, date}` from 双葉社's book_details JSON, or None."""
    try:
        info = ((json.loads(body or "") or {}).get("book_details") or {}).get("book_informations")
    except ValueError:
        return None
    if not info or not info.get("release_dt"):
        return None
    return {"isbn": info.get("isbn_code"), "title": info.get("book_name"),
            "date": info["release_dt"][:10]}


# ── 幻冬舎コミックス, and any other publisher whose page is server-rendered HTML ───────────────
# `発売日 2014年11月21日` in the 書誌情報 block. Anchored on the label rather than taken as the
# first date on the page: these pages carry a navigation column and a related-titles list, and a
# bare date pattern would eventually read one of those.
RELEASE_LABELLED = re.compile(r"(?:発売日|発行日|発行年月日|刊行日)\D{0,4}"
                              r"(\d{4})年\s*(\d{1,2})月(?:\s*(\d{1,2})日)?")
RELEASE_SUFFIXED = re.compile(r"(\d{4})年\s*(\d{1,2})月(?:\s*(\d{1,2})日)?\s*発売")
PAGE_ISBN = re.compile(r"ISBN\D{0,4}((?:97[89][-\s]?)?[\d-]{9,17}[\dX])")
PAGE_TITLE = re.compile(r"<title>(.*?)</title>", re.S | re.I)


def _text(html):
    """Visible text, scripts removed, so a date inside a template cannot read as a stated one."""
    s = re.sub(r"<(script|style).*?</\1>", " ", html or "", flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def html_book(body):
    """`{isbn, title, date}` from a server-rendered publisher page, or None."""
    text = _text(body)
    m = RELEASE_LABELLED.search(text) or RELEASE_SUFFIXED.search(text)
    if not m:
        return None
    y, mo, d = m.group(1), int(m.group(2)), m.group(3)
    date = f"{y}-{mo:02d}-{int(d):02d}" if d else f"{y}-{mo:02d}"
    isbn = PAGE_ISBN.search(text)
    title = PAGE_TITLE.search(body or "")
    return {"isbn": re.sub(r"[^0-9X]", "", isbn.group(1)) if isbn else None,
            "title": _text(title.group(1)) if title else None, "date": date}


# The four books that are not 一迅社, and the one 一迅社 row whose ISBN belongs to another book.
# Resolved by hand and pinned, because one book at one publisher does not justify a crawler and a
# pinned URL is checkable by a reader in a way a search result is not. `None` means the publisher
# route has been tried and has failed, and the row falls to `adapters/booksorjp.py`; the reason is
# in GAPS §19 for each.
PAGES = {
    "9784344832565": ("https://www.gentosha-comics.net/book/b519294.html", html_book),
    "9784575834772": (futabasha_url("9784575834772"), futabasha_book),
    "9784391905533": (None, None),
    "9784832240179": (None, None),
    "9784758062862": ("https://data.ichijinsha.co.jp/detail/75806119", ichijinsha_book),
}

# Where the shop's ISBN denotes a different book from the row it sits on. The publisher's page is
# authority on what its own ISBN means, so the shop's number is refuted rather than reconciled, and
# the publisher's own ISBN for the work is stored beside it so a reader sees both.
REFUTED = {
    "9784758062862": "9784758061193",
}


def page_for(isbn, publisher):
    """`(url, parser)` for one book, or `(None, None)` where no publisher page has been resolved."""
    if isbn in PAGES:
        return PAGES[isbn]
    if isbn.startswith(("9784758", "9784825")) or (publisher or "") == "一迅社":
        return ichijinsha_url(isbn), ichijinsha_book
    return None, None


# Presentation the two sides write differently and neither means a different work. `identity.fold`
# already does width, spacing, brackets and ordinary punctuation; this drops the decorative marks
# it keeps, because 一迅社 titles レンアイ♥女子課 what the shop shelves as レンアイ・女子課.
DECORATIVE = re.compile(r"[^\w]", re.U)


def same_work(page_title, shop_title):
    """Whether the publisher's page is about the book the shop's row is about.

    Containment either way rather than equality, because the publisher writes the volume number
    into the title (`犬神さんと猫山さん (1)巻`) and the shop states the series name alone. That is
    loose enough to accept every real pair on this shelf and still refuses 白砂村 against
    える・えるシスター, which is the pair it exists for.
    """
    if not page_title or not shop_title:
        return False
    a = DECORATIVE.sub("", unicodedata.normalize("NFKC", identity.fold(page_title)))
    b = DECORATIVE.sub("", unicodedata.normalize("NFKC", identity.fold(shop_title)))
    return bool(a) and bool(b) and (a in b or b in a)


def accept(found, isbn, shop_title, pinned):
    """The date a page may be believed for, as `(date, why_not)`.

    A page reached FROM the ISBN has to state that ISBN back. A page resolved by hand from the
    title does not, since it was found another way and may carry the ISBN the shop got wrong;
    what it has to do is be about the same work. Both are required to name the work.
    """
    if not found or not found.get("date"):
        return None, "no date stated"
    if not same_work(found.get("title"), shop_title):
        return None, f"the page is about {found.get('title')!r}, not {shop_title!r}"
    if not pinned and found.get("isbn") != isbn:
        return None, f"the page states ISBN {found.get('isbn')}, not {isbn}"
    return found["date"], None


def targets(doc):
    """`[(isbn, publisher, shop_id, title)]` for every row the catalogues could not date.

    Read off the stored basis rather than off a list kept somewhere, so a row another pass dates
    drops out of here without anyone maintaining the same fact twice (STANDING-INSTRUCTIONS §3).
    """
    out = []
    for tid, w in sorted((doc.get("works") or {}).items(), key=lambda kv: int(kv[0])):
        if w.get("first_publication_basis") != TARGET_BASIS:
            continue
        first = next((v for v in (w.get("volumes") or []) if v.get("volume") == 1), None)
        if first and first.get("isbn"):
            out.append((first["isbn"], w.get("publisher"), tid, w.get("shelf_title")))
    return out


def robots_gate(hosts, offline=False):
    """`{host: [disallowed paths]}`, printed, so a check nobody can see is not mistaken for one.

    `recon/probe.py` holds the parse and its test holds a real robots.txt, so the rule set matched
    against is the whole file rather than a prefix of it. A host serving no robots.txt reports no
    rules, which is what a missing file means.
    """
    rules = {}
    for host in hosts:
        rules[host] = [] if offline else probe.robots_rules(host)["disallow"]
        if not offline:
            print(f"  robots.txt {host}: {len(rules[host])} rule(s) for User-agent: *")
    return rules


def run(doc, cache, offline=False, rules=None):
    """Ask each outstanding book's publisher and fold in what it answers.

    Returns `(doc, dates, refused, misses, filled, disagreements)`.
    """
    dates, sources, refused, misses = {}, {}, [], []
    for isbn, publisher, tid, shop_title in targets(doc):
        url, parser = page_for(isbn, publisher)
        if not url:
            misses.append((isbn, tid, shop_title, "no publisher page for this book"))
            continue
        host, path = url.split("/")[2], "/" + url.split("/", 3)[3]
        if rules is not None and not probe.allowed(path, rules.get(host) or []):
            refused.append((isbn, url))
            continue
        r = net.cached(url, cache) if offline else net.fetch(url, cache, max_age_days=AGE)
        date, why = accept(parser(r.text) if r and r.text else None, isbn, shop_title,
                           isbn in PAGES)
        if date:
            dates[isbn], sources[isbn] = date, url
        else:
            misses.append((isbn, tid, shop_title,
                           f"{url}: {why or ('no cached copy' if r is None else 'not fetched')}"))
    doc, filled, disagreements = cmoa_volumes.apply_dates(doc, dates, BASIS, sources)
    note_refuted(doc)
    return doc, dates, refused, misses, filled, disagreements


def note_refuted(doc):
    """Record the publisher's own ISBN where it contradicts the shop's, beside the shop's.

    The shop's number is left as the shop states it. This file is a capture of what cmoa says and
    silently rewriting it would lose the disagreement, which is the part worth keeping.
    """
    for w in (doc.get("works") or {}).values():
        for v in w.get("volumes") or []:
            if v.get("isbn") in REFUTED and v.get("printed_source"):
                v["publisher_isbn"] = REFUTED[v["isbn"]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", default="data/queue/cmoa-volumes.yaml")
    ap.add_argument("--cache", default=str(paths.cache("publisher-cache")))
    ap.add_argument("--offline", action="store_true", help="parse only what the cache holds")
    ap.add_argument("--report", action="store_true", help="list what is outstanding, fetch nothing")
    a = ap.parse_args(argv)

    doc = cmoa_volumes.load(a.capture)
    todo = targets(doc)
    if a.report:
        print(f"{len(todo)} row(s) filed {TARGET_BASIS}")
        for isbn, publisher, tid, title in todo:
            print(f"  {isbn}  {publisher or '?':<10} {tid:>7}  {page_for(isbn, publisher)[0]}")
        return 0

    hosts = sorted({page_for(i, p)[0].split("/")[2] for i, p, _, _ in todo if page_for(i, p)[0]})
    rules = robots_gate(hosts, a.offline)
    doc, dates, refused, misses, filled, disagreements = run(doc, a.cache, a.offline, rules)
    doc["retrieved"] = doc.get("retrieved") or datetime.date.today().isoformat()
    pathlib.Path(a.capture).write_text(cmoa_volumes.yaml_document(doc))
    print(f"{len(dates)} of {len(todo)} dated from the publisher's own page; "
          f"{filled} volume(s) filled, {disagreements} disagreement(s)")
    for isbn, url in refused:
        print(f"  robots.txt refuses {url} ({isbn})")
    for isbn, tid, title, why in misses:
        print(f"  {isbn} {tid} {title}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
