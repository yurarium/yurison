#!/usr/bin/env python3
"""出版書誌データベース (Books.or.jp), asked only for the books no publisher will answer for.

WHEN THIS RUNS, AND IT IS NOT FIRST. `adapters/publisher_dates.py` asks each book's own publisher
and answers 47 of the 49 rows filed `isbn-stated-not-catalogued`. This is for the remainder, where
the publisher has closed the page, never had one, or no longer lists the book: 芳文社's site
returns nothing for エンドレスルーム or for its author, and neither ぶんか社 nor 主婦と生活社 has a
record of シークレットガーデン, a 1995 エメラルドコミックス volume. The order matters and it is the
project owner's, recorded in GAPS §19 with the reasoning.

THE TERMS QUESTION, SETTLED BY THE OWNER ON 2026-08-07. Books' 利用規約 第4条 reserves JPO's rights
in the information on the site and forbids reproducing or diverting it without permission, and GAPS
§17 stopped there rather than guess. The owner's decision is that a publication date is a fact, it
carries no copyright, Japan has no sui generis database right, and Article 12-2 protects a
database's selection and structure rather than the facts inside it. Resolving ISBNs already held
takes none of the selection. What is left is a contractual term of uncertain force, and the
decision is to rely on that reading where the publisher route has genuinely failed. Every row this
module fills is marked `books-or-jp-registration` so it can be found and replaced the day a
publisher page appears.

発行年月日 AND NOT 発売日, WHICH IS THE OPPOSITE OF THE PUBLISHER ROUTE'S CHOICE. Books states both,
and on these records 発行年月日 is a month while 発売日 renders that month as its first day:
シークレットガーデン is 1995年09月 and 1995年09月01日. DEFINITIONS §6 names a first-of-the-month
standing in for a month-precision record as one of the three dates that have already produced a
wrong answer in this project, so the field that never invents a day is the one taken. A publisher
stating 発売日 2006-09-16 for its own book is stating a day it chose, which is why that route reads
the other field.

ONE REQUEST AT A TIME AND SLOWLY. The host starts refusing a sequential reader after about forty
requests; a 2026-08-06 sweep of all 49 lost its last six that way. PAUSE is set for a run of a
handful and would want raising again for a run of hundreds.

Usage:  booksorjp.py             fill what the publisher route could not, and write it back
        booksorjp.py --offline   parse only what the cache holds
        booksorjp.py --report    say what is outstanding, fetch nothing
"""
import argparse
import datetime
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cmoa_volumes                                                            # noqa: E402
import net                                                                     # noqa: E402
import paths                                                                   # noqa: E402
import publisher_dates                                                         # noqa: E402
from recon import probe                                                        # noqa: E402

BASIS = "books-or-jp-registration"
HOST = "www.books.or.jp"
AGE = 365

# Seconds between requests. `net.PAUSE` is 1.2 and this host will not take that: the measured
# sweep died at roughly forty requests. Enforced by sleeping before each fetch rather than by
# raising net.PAUSE, which is shared with every other host and would slow all of them.
PAUSE = 8

# `ISBN：9784391905533<br>…<br>発行年月日：1995年09月<br>発売日：1995年09月01日` in the 書誌 block.
FIELD = re.compile(r"(ISBN|出版社|発行年月日|発売日)：\s*([^<。]*)")
TITLE = re.compile(r"<title>(.*?)(?:\s*[|｜].*)?</title>", re.S | re.I)
YMD = re.compile(r"(\d{4})年\s*(\d{1,2})月(?:\s*(\d{1,2})日)?")


def url(isbn):
    return f"https://{HOST}/book-details/{isbn}"


def book(body):
    """`{isbn, title, publisher, date, on_sale}` from a Books book page, or None where it holds none.

    `date` is 発行年月日 at the precision the page states it. `on_sale` is 発売日, kept so a reader
    can see the pair the module docstring is about, and never used as the publication date.
    """
    fields = dict(FIELD.findall(body or ""))
    if not fields.get("ISBN"):
        return None
    t = TITLE.search(body or "")
    return {"isbn": re.sub(r"[^0-9X]", "", fields["ISBN"]),
            "title": re.sub(r"\s+", " ", t.group(1)).strip() if t else None,
            "publisher": (fields.get("出版社") or "").strip(),
            "date": _date(fields.get("発行年月日")), "on_sale": _date(fields.get("発売日"))}


def _date(s):
    """`1995年09月` as `1995-09` and `2011年04月12日` as `2011-04-12`. No day is invented."""
    m = YMD.search(s or "")
    if not m:
        return None
    y, mo, d = m.group(1), int(m.group(2)), m.group(3)
    return f"{y}-{mo:02d}-{int(d):02d}" if d else f"{y}-{mo:02d}"


def accept(found, isbn, shop_title):
    """The date this record may be believed for, as `(date, why_not)`.

    The same two guards `publisher_dates.accept` applies, for the same reason: the page has to be
    the book asked for AND the book the shop's row is about. One of the 49 rows carries an ISBN
    that belongs to another title entirely, and an aggregator will answer for that ISBN just as
    confidently as the publisher did.
    """
    if not found or not found.get("date"):
        return None, "no 発行年月日 stated"
    if found.get("isbn") != isbn:
        return None, f"the record states ISBN {found.get('isbn')}, not {isbn}"
    if not publisher_dates.same_work(found.get("title"), shop_title):
        return None, f"the record is for {found.get('title')!r}, not {shop_title!r}"
    return found["date"], None


def fetch(isbn, cache, offline=False):
    """One book page, at this host's pace. Returns the body or None."""
    u = url(isbn)
    f = pathlib.Path(cache) / net.cache_key(u)
    if f.exists():
        return f.read_text(encoding="utf-8", errors="replace")
    if offline:
        return None
    time.sleep(PAUSE)
    return net.fetch(u, cache, max_age_days=AGE).text


def run(doc, cache, offline=False, rules=None):
    """Fill what the publisher route left, and fold it in."""
    dates, sources, refused, misses = {}, {}, [], []
    for isbn, _publisher, tid, shop_title in publisher_dates.targets(doc):
        if rules is not None and not probe.allowed(f"/book-details/{isbn}", rules):
            refused.append((isbn, url(isbn)))
            continue
        body = fetch(isbn, cache, offline)
        date, why = accept(book(body), isbn, shop_title)
        if date:
            dates[isbn], sources[isbn] = date, url(isbn)
        else:
            misses.append((isbn, tid, shop_title, why or "no page fetched"))
    doc, filled, disagreements = cmoa_volumes.apply_dates(doc, dates, BASIS, sources)
    return doc, dates, refused, misses, filled, disagreements


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", default="data/queue/cmoa-volumes.yaml")
    ap.add_argument("--cache", default=str(paths.cache("booksorjp-cache")))
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)

    doc = cmoa_volumes.load(a.capture)
    todo = publisher_dates.targets(doc)
    if a.report:
        print(f"{len(todo)} row(s) the publisher route did not answer")
        for isbn, publisher, tid, title in todo:
            print(f"  {isbn}  {publisher or '?':<12} {tid:>7}  {title}")
        return 0

    rules = [] if a.offline else probe.robots_rules(HOST)["disallow"]
    if not a.offline:
        print(f"  robots.txt {HOST}: {len(rules)} rule(s) for User-agent: *")
    doc, dates, refused, misses, filled, disagreements = run(doc, a.cache, a.offline, rules)
    doc["retrieved"] = doc.get("retrieved") or datetime.date.today().isoformat()
    pathlib.Path(a.capture).write_text(cmoa_volumes.yaml_document(doc))
    print(f"{len(dates)} of {len(todo)} dated from Books.or.jp; {filled} volume(s) filled, "
          f"{disagreements} disagreement(s)")
    for isbn, u in refused:
        print(f"  robots.txt refuses {u} ({isbn})")
    for isbn, tid, title, why in misses:
        print(f"  {isbn} {tid} {title}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
