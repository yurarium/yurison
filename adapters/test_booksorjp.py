#!/usr/bin/env python3
"""booksorjp.py: taking 発行年月日 and never the first of the month that stands in for it."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import booksorjp as bj  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/booksorjp.py"]

# The 書誌 block of https://www.books.or.jp/book-details/9784391905533 as served on 2026-08-07.
# 発行年月日 is a month and 発売日 renders that month as its first day, which is the pair this
# module's field choice turns on.
SHUFU = """
<title>シークレットガーデン | 本の総合カタログBooks 出版書誌データベース</title>
<div class="otherdata"><p class="text-body text-color">ISBN：9784391905533<br>雑誌コード：5231323
<br>出版社：主婦と生活社<br>判型：新書<br>定価：660円（本体）<br>発行年月日：1995年09月
<br>発売日：1995年09月01日<span class='readonly'>。</span></p></div>
"""

# https://www.books.or.jp/book-details/9784832240179, where 発売日 states a real day. The rule has
# to be one rule, so this record is read the same way as the one above.
HOUBUNSHA = """
<title>エンドレスルーム | 本の総合カタログBooks 出版書誌データベース</title>
<div class="otherdata"><p class="text-body text-color">ISBN：9784832240179<br>出版社：芳文社
<br>判型：A5<br>ページ数：146ページ<br>定価：848円（本体）<br>発行年月日：2011年04月
<br>発売日：2011年04月12日<span class='readonly'>。</span></p></div>
"""


def main(s):
    # ── THE FIELD THAT NEVER INVENTS A DAY ───────────────────────────────────────────────────
    # DEFINITIONS §6 names a first-of-the-month standing in for a month-precision record as one of
    # the dates that has already produced a wrong answer here. 発行年月日 is a month on both of
    # these records and 発売日 turns one of them into 1995-09-01, so the month is what is stored.
    r = bj.book(SHUFU)
    s.eq(r["date"], "1995-09", "発行年月日 is stored at the precision the record states it")
    s.eq(r["on_sale"], "1995-09-01",
         "発売日 is kept visible and is not the publication date, because its day is the month")
    s.eq(r["isbn"], "9784391905533", "with the ISBN the record is filed under")
    s.eq(r["publisher"], "主婦と生活社",
         "and the publisher, which is not the one the shop's row names")
    s.eq(r["title"], "シークレットガーデン", "the site's own suffix is not part of the title")

    h = bj.book(HOUBUNSHA)
    s.eq(h["date"], "2011-04", "the same field on a record whose 発売日 states a real day")
    s.eq(h["on_sale"], "2011-04-12", "so that the day is visible without being believed")
    s.eq(bj.book("<html>no record here</html>"), None,
         "a page holding no 書誌 block yields nothing rather than a half-filled record")
    s.eq(bj._date(None), None, "and a field that is not there is not a date")

    # ── THE SAME TWO GUARDS AS THE PUBLISHER ROUTE ───────────────────────────────────────────
    # An aggregator answers for a wrong ISBN as confidently as a publisher does, and one of the 49
    # rows carries an ISBN that belongs to another title.
    s.eq(bj.accept(r, "9784391905533", "シークレットガーデン"), ("1995-09", None),
         "ISBN and title agree, so the date stands")
    s.eq(bj.accept(r, "9784391905534", "シークレットガーデン")[0], None,
         "a record for a different ISBN is refused")
    s.eq(bj.accept(r, "9784391905533", "える・えるシスター")[0], None,
         "and so is a record for a different book")
    s.eq(bj.accept(None, "9784391905533", "シークレットガーデン")[0], None, "no record, no date")

    s.eq(bj.url("9784832240179"), "https://www.books.or.jp/book-details/9784832240179",
         "one page per ISBN, which is the whole of what this asks the site")
    s.check(bj.PAUSE > 5, "the host refuses a sequential reader at net.PAUSE, so this one is slower")

    cache_age(s)


def cache_age(s):
    """A record cached past `AGE` is fetched again, which `if f.exists()` stepped over.

    `net.fetch` IS STUBBED, because that is the call this module hands `max_age_days=AGE` and the
    short-circuit above it was what stopped the age ever being consulted. Asking whether the stub
    ran is asking whether the cache was declined.
    """
    import os, tempfile, time as _t
    d = pathlib.Path(tempfile.mkdtemp())
    isbn = "9784088900001"
    f = d / bj.net.cache_key(bj.url(isbn))
    f.write_text("cached page")
    asked = []

    class _Result:
        text = "live page"

    def _stub(u, cache, max_age_days=None, **k):
        asked.append((u, max_age_days))
        return _Result()

    real_fetch, real_sleep = bj.net.fetch, bj.time.sleep
    bj.net.fetch, bj.time.sleep = _stub, lambda *_a: None
    try:
        s.eq(bj.fetch(isbn, d), "cached page", "a record cached today is read from the cache")
        s.eq(len(asked), 0, "and the host is not asked for it")

        old = _t.time() - (bj.AGE + 5) * 86400
        os.utime(f, (old, old))
        s.eq(bj.fetch(isbn, d), "live page", "one past AGE is fetched again")
        s.eq(asked[0][1], bj.AGE, "and the age this module declares is what it asks for")

        s.eq(bj.fetch(isbn, d, offline=True), "cached page",
             "while offline reads the cache at any age, having no other answer")
        s.eq(len(asked), 1, "without reaching for the host")
    finally:
        bj.net.fetch, bj.time.sleep = real_fetch, real_sleep


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
