#!/usr/bin/env python3
"""stores.py: what a shop link says about the edition behind it.

Every URL below was taken from a platform page during the survey on 2026-08-07, so the counter-cases
are the ones that actually appear rather than ones imagined for the test.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import stores                                                                  # noqa: E402
import testkit                                                                 # noqa: E402


def main(s):
    # STATED. 集英社 puts the number in the query string, 双葉社 pads it with zeros in the path.
    s.eq(stores.isbn_of("https://www.s-manga.net/items/contents.html?isbn=978-4-08-894279-7"),
         "9784088942797", "s-manga states the ISBN in its query string")
    s.eq(stores.isbn_of("https://www.futabasha.co.jp/book/97845758625770000000?type=1"),
         "9784575862577", "双葉社 pads its ISBN to twenty digits")

    # AN ASIN, WHICH IS THE WHOLE REASON valid10 EXISTS. Both of these came off one
    # チャンピオンクロス store page: the printed volume and the Kindle file of the same book.
    s.eq(stores.isbn_of("https://www.amazon.co.jp/dp/4253013929"), "9784253013925",
         "a print ASIN is an ISBN-10 and converts")
    s.eq(stores.isbn_of("https://www.amazon.co.jp/dp/B0CW1FS2V1"), None,
         "a Kindle ASIN states no ISBN and must not be turned into one")
    s.eq(stores.isbn_of("http://www.amazon.co.jp/o/ASIN/4046079126/pixiv-comic-22"),
         "9784046079121", "pixivコミック's ad_books link uses the /o/ASIN/ form")
    s.eq(stores.isbn_of("https://images-na.ssl-images-amazon.com/images/P/4046079126.09._SX140_.jpg"),
         "9784046079121", "and its cover URL names the same ASIN")
    s.eq(stores.isbn_of("https://www.amazon.co.jp/exec/obidos/ASIN/4199508783/comicryu0d-22"),
         "9784199508783", "COMICリュウ uses the obidos form")

    # A SEARCH LINK STATES NOTHING. カドコミ gives most shops a title search, and reading a number
    # out of one of these would be reading it out of a title string.
    for u in ["https://booklive.jp/search/keyword?keyword=%E5%92%B2",
              "https://piccoma.com/web/search/result?word=%E5%92%B2",
              "https://honto.jp/ebook/search_09-saledate.html?detailFlg=1&pbNm=KADOKAWA",
              "https://manga.line.me/search_product/list?word=%E5%92%B2"]:
        s.eq(stores.isbn_of(u), None, f"a keyword search states no ISBN: {u[:40]}")

    # SHOP IDS. These identify an edition without stating its number, so they are kept as ids and
    # the page is what gets asked.
    s.eq(stores.shop_id_of("https://www.cmoa.jp/title/344812/?pg=title_ditail&title_id=344812"),
         ("cmoa_title", "344812", None), "a cmoa title link carries the title id")
    s.eq(stores.shop_id_of("https://www.cmoa.jp/title/340870/vol/2/"),
         ("cmoa_title", "340870", 2), "and a volume link carries the volume too")
    s.eq(stores.shop_id_of("https://www.shinchosha.co.jp/book/772966/"),
         ("shinchosha_book", "772966", None), "新潮社 carries its own book id")
    s.eq(stores.shop_id_of("https://www.gentosha-comics.net/book/b671924.html"),
         ("gentosha_book", "b671924", None), "幻冬舎コミックス likewise")

    # THE INFERENCE THIS MODULE REFUSES. 新潮社's id IS the ISBN body, so 978-4-10-772966-8 is one
    # line of arithmetic away. Decoding it would put a valid ISBN belonging to whatever book that
    # scheme actually numbers into the capture, and a wrong ISBN reaches the bibliography and joins
    # a print run to the wrong serialisation.
    s.eq(stores.isbn_of("https://www.shinchosha.co.jp/book/772966/"), None,
         "a publisher's own numbering is not decoded into an ISBN")
    s.eq(stores.isbn_of("https://www.shogakukan.co.jp/books/09854740"), None,
         "nor 小学館's")

    # A SHORT LINK IS ITS OWN STATE. Neither an ISBN nor a shop id until it is followed.
    s.check(stores.is_short("https://amzn.asia/d/0hb0gFoH"), "amzn.asia is a short link")
    s.check(not stores.is_short("https://www.amazon.co.jp/dp/4253013929"),
            "a full product link is not")

    # THE ONE SHAPE A CAPTURE STORES.
    s.eq(stores.read("https://www.amazon.co.jp/dp/4253013929"),
         {"url": "https://www.amazon.co.jp/dp/4253013929", "isbn": "9784253013925"},
         "read() gives the ISBN where one is stated")
    s.eq(stores.read("https://www.cmoa.jp/title/340870/vol/2/"),
         {"url": "https://www.cmoa.jp/title/340870/vol/2/", "shop": "cmoa_title",
          "shop_id": "340870", "volume": 2},
         "and the shop id where one is not")
    s.eq(stores.read("https://example.invalid/nothing"),
         {"url": "https://example.invalid/nothing"},
         "and nothing at all for a link that carries neither")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
