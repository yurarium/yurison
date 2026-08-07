#!/usr/bin/env python3
"""platforms.py: where each web-manga engine writes the links to the shops selling its volumes.

The fixtures are cut from the live pages read on 2026-08-07 and shortened to what the parser looks
at. Each one that pins a bug says which bug.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import platforms as P                                                          # noqa: E402
import stores as S                                                             # noqa: E402
import testkit                                                                 # noqa: E402

# 少年ジャンプ+, whose sidebar is followed by the Hatena bookmark strip and then the page footer.
# THE BUG THIS PINS: the block used to run to the end of the document, so every footer link joined
# the last volume's group. `stores.one_isbn` was then deciding between a volume's shops and the
# whole site navigation.
JUMP = """
<div class="series-book-details test-series-book-details">
  <h3 class="series-book-details-title">最新巻情報</h3>
  <div class="series-book-detail">
    <div class="book-cover-content">
      <a href="https://zebrack-comic.shueisha.co.jp/title/197654?type=volume"><img alt="春雷卓球 1 (ジャンプコミックス)" /></a>
    </div>
    <a href="https://www.amazon.co.jp/x-ebook/dp/B0GJ4B8MWH/ref=sr_1_1" class="amazon-link">a</a>
    <a href="https://ebookjapan.yahoo.co.jp/books/963338/" class="ebookjapan-link">e</a>
  </div>
</div>
<div class="series-bookmark-comments test-hatenabookmark-comment"></div>
<a href="https://www.amazon.co.jp/dp/4088938933">a footer link that is not this volume</a>
"""

# となりのヤングジャンプ, two blocks: the volume and an illustration book beside it.
TONARI = """
<div class="series-book-details test-series-book-details">
  <div class="series-book-detail">
    <a href="https://www.s-manga.net/items/contents.html?isbn=978-4-08-893893-6"><img alt="明日ちゃんのセーラー服 16" /></a>
    <a href="https://amzn.asia/d/001sasSb" class="amazon-link">a</a>
    <a href="https://books.rakuten.co.jp/rb/18577212/" class="rakutenbooks-link">r</a>
  </div>
  <div class="series-book-detail">
    <a href="https://www.s-manga.net/items/contents.html?isbn=978-4-08-792749-8"><img alt="博イラスト集" /></a>
  </div>
</div>
<div class="series-profile-details"><a href="https://www.amazon.co.jp/dp/4088938933">not a volume</a></div>
"""

COMICI_SERIES = """
<div class="series-store"><h2 class="series-store-h">単行本情報</h2>
<a class="series-store-item-link" href="/store_items/6081">two</a>
<a class="series-store-item-btn" href="/store_items/popup/6081">購入</a>
<a class="series-store-item-link" href="/store_items/5678">one</a>
<div class="series-store-more"><a class="series-store-more-link" href="/store_items/series/570/1">
<span class="series-store-more-label">全2冊</span></a></div></div>
"""

COMICI_ITEM = """
<a href="https://www.amazon.co.jp/dp/B0CW1FS2V1" class="store-detail-buy-btn">kindle</a>
<a href="https://www.cmoa.jp/title/340870/vol/2/" class="store-detail-buy-btn">cmoa</a>
<a href="https://www.amazon.co.jp/dp/4253013929" class="store-detail-buy-btn">print</a>
"""

KADOKOMI = ('<script id="__NEXT_DATA__" type="application/json">'
            '{"props":{"pageProps":{"dehydratedState":{"queries":[{"state":{"data":{'
            '"work":{"code":"KC_006662_S","title":"\\u54b2\\u304d\\u305d\\u3081",'
            '"ratingLevel":"adult","internal":{"labelNames":["\\u767e\\u5408\\u5036\\u697d\\u90e8"]}},'
            '"comics":{"total":1,"result":[{"id":"a","title":"1\\u5dfb","release":"2026-01-07",'
            '"stores":[{"code":"comic_cmoa","url":"https://www.cmoa.jp/title/344812/?pg=x"},'
            '{"code":"amazon","url":"https://www.amazon.co.jp/s?k=x"}]}]}}}}]}}}}'
            '</script>')

PIXIV = ('{"data":{"ad_books":[{"id":1,"title":"x (KITORA)",'
         '"image_url":"https://images-na.ssl-images-amazon.com/images/P/4046079126.09._SX140_.jpg",'
         '"amazon_url":"http://www.amazon.co.jp/o/ASIN/4046079126/pixiv-comic-22"}]}}')

GANGAN = """
<div class="Volume2_volume__thumbnail__x"><p class="Volume2_volume__name__paNqo">裏世界ピクニック 16巻</p>
<a href="http://www.amazon.co.jp/gp/product/4301005153?ie=UTF8">a</a></div>
<div class="Volume2_volume__thumbnail__x"><p class="Volume2_volume__name__paNqo">裏世界ピクニック 15巻</p>
<a href="http://www.amazon.co.jp/gp/product/4757581211?ie=UTF8">a</a></div>
"""


def main(s):
    # ── GigaViewer sidebar ───────────────────────────────────────────────────────────────────
    b = P.gigaviewer_books(JUMP)
    s.eq(len(b), 1, "少年ジャンプ+ renders one volume block")
    s.eq(b[0]["title"], "春雷卓球 1 (ジャンプコミックス)", "the volume's own stated title is kept")
    s.check(all("4088938933" not in u for u in b[0]["urls"]),
            "the footer link after the block does not join it, which is the bug this pins")
    s.eq(S.one_isbn(b[0]["urls"]), None,
         "少年ジャンプ+ offers only digital editions, so no ISBN is stated and none is invented")

    t = P.gigaviewer_books(TONARI)
    s.eq(len(t), 2, "となりのヤングジャンプ renders a block per book")
    s.eq(S.one_isbn(t[0]["urls"]), "9784088938936", "the volume's ISBN comes off the cover link")
    s.eq(S.one_isbn(t[1]["urls"]), "9784087927498", "and the illustration book keeps its own")
    s.check(all("4088938933" not in u for blk in t for u in blk["urls"]),
            "the author-profile block that follows is outside the region")

    s.eq(P.gigaviewer_books("<html>a page with no sidebar</html>"), [],
         "a series with no collected volume yields nothing rather than a guess")

    # ── GigaViewer /comics grouping ──────────────────────────────────────────────────────────
    comics = ('<a href="https://www.s-manga.net/items/contents.html?isbn=978-4-08-894279-7">buy</a>'
              '<a href="https://tonarinoyj.jp/episode/111">第一話</a>'
              '<a href="https://www.s-manga.net/items/contents.html?isbn=978-4-08-894403-6">buy</a>'
              '<a href="https://tonarinoyj.jp/episode/222">第一話</a>')
    g = P.gigaviewer_comics(comics, "tonarinoyj.jp")
    s.eq(len(g), 2, "each episode link closes the group before it")
    s.eq(g[0]["episode_url"], "https://tonarinoyj.jp/episode/111", "in document order")
    s.eq(S.one_isbn(g[0]["book_urls"]), "9784088942797", "and the group states one ISBN")

    # THE HAZARD. An item rendering no episode link leaves its book to the next group, which would
    # attach a print run to the wrong serialisation. Two ISBNs in one group is what that looks
    # like, and `one_isbn` refuses it rather than picking.
    leaky = ('<a href="https://www.s-manga.net/items/contents.html?isbn=978-4-08-894279-7">a</a>'
             '<a href="https://www.s-manga.net/items/contents.html?isbn=978-4-08-894403-6">b</a>'
             '<a href="https://tonarinoyj.jp/episode/222">第一話</a>')
    lk = P.gigaviewer_comics(leaky, "tonarinoyj.jp")
    s.eq(len(lk), 1, "the leaked book lands in the next group")
    s.eq(S.one_isbn(lk[0]["book_urls"]), None,
         "and the group is refused, because it no longer says which book belongs to the series")

    # ── Comici ───────────────────────────────────────────────────────────────────────────────
    ci = P.comici_store_items(COMICI_SERIES)
    s.eq(ci["items"], ["6081", "5678"], "the series page names a store item per volume, newest first")
    s.eq(ci["all_url"], "/store_items/series/570/1", "and links the whole list")
    s.eq(ci["stated"], 2, "and states how many there are")
    s.eq(P.comici_store_items("<html>nothing</html>"),
         {"items": [], "all_url": None, "stated": None}, "a series with no volumes states nothing")

    links = P.comici_store_links(COMICI_ITEM)
    s.eq(len(links), 3, "the item page's shop row is read whole")
    s.eq(S.one_isbn(links), "9784253013925",
         "the print Amazon entry states the ISBN and the Kindle one beside it does not compete")

    # ── カドコミ ─────────────────────────────────────────────────────────────────────────────
    k = P.kadokomi_next_data(KADOKOMI)
    s.eq(k["code"], "KC_006662_S", "the work code comes off the page's own state")
    s.eq(k["rating"], "adult", "and KADOKAWA's own rating on its own work")
    s.eq(k["labels"], ["百合倶楽部"], "and the imprint labels, which are publisher-side evidence")
    s.eq(len(k["comics"]), 1, "one collected volume")
    s.eq(S.shop_id_of(k["comics"][0]["stores"][0]["url"]), ("cmoa_title", "344812", None),
         "whose コミックシーモア link carries the title id this route rests on")
    s.eq(S.isbn_of(k["comics"][0]["stores"][1]["url"]), None,
         "while its Amazon link is a keyword search stating nothing")
    s.eq(P.kadokomi_next_data("<html>no state</html>"), None, "a page with no state yields none")

    # ── pixivコミック ────────────────────────────────────────────────────────────────────────
    px = P.pixiv_ad_books(PIXIV)
    s.eq(len(px), 1, "ad_books answers with the printed books")
    s.eq(S.one_isbn([px[0]["amazon_url"], px[0]["image_url"]]), "9784046079121",
         "the product link and the cover path name the same ASIN, so they agree")
    s.eq(P.pixiv_ad_books("not json"), [], "a body that is not JSON yields nothing, not an error")

    # ── ガンガンONLINE ───────────────────────────────────────────────────────────────────────
    gg = P.ganganonline_books(GANGAN)
    s.eq(len(gg), 2, "one entry per volume in the 単行本 section")
    s.eq(gg[0]["title"], "裏世界ピクニック 16巻", "with the volume's own name")
    s.eq(S.one_isbn(gg[1]["urls"]), "9784757581210", "and its shop banner's ASIN")

    # ── comicブースト and ヤンマガWeb ─────────────────────────────────────────────────────────
    boost = ('<a class="comic-list-side-by-side-item" '
             'href="https://www.gentosha-comics.net/book/b671924.html"><img/></a>')
    s.eq(P.comicboost_books(boost), ["https://www.gentosha-comics.net/book/b671924.html"],
         "comicブースト links 幻冬舎コミックス's own book page per volume")

    s.eq(P.yanmaga_series_url("https://yanmaga.jp/comics/%E4%B9%99/d895fc7298bc7"),
         "https://yanmaga.jp/comics/%E4%B9%99",
         "the ヤンマガWeb address held here is the viewer; its parent is the series page")
    s.eq(P.yanmaga_series_url("https://yanmaga.jp/comics/%E4%B9%99"),
         "https://yanmaga.jp/comics/%E4%B9%99", "a series page is already one")
    ym = ('<a class="mod-banner-comics-link ga-comics-banner" '
          'href="https://www.kodansha.co.jp/comic/products/0000427633">第2巻</a>')
    s.eq(P.yanmaga_books(ym), ["https://www.kodansha.co.jp/comic/products/0000427633"],
         "and it links 講談社's product page")

    # ── publisher pages ──────────────────────────────────────────────────────────────────────
    s.eq(P.publisher_isbn('<meta name="shc-isbn" content="9784107729668">', "www.shinchosha.co.jp"),
         "9784107729668", "新潮社 states it in a meta tag")
    s.eq(P.publisher_isbn("<th>ISBN</th>\n\t\t<td>9784344856981</td>", "www.gentosha-comics.net"),
         "9784344856981", "幻冬舎コミックス in a table, across the whitespace between them")
    s.eq(P.publisher_isbn('<meta property="books:isbn" content="9784065438503" />',
                          "www.kodansha.co.jp"), "9784065438503", "講談社 in the Open Graph tag")

    # THE COUNTER-CASE THAT DECIDED THE SHAPE. 小学館's page for one book carries four other books'
    # ISBNs in its related listings, so a pattern matching the first thirteen-digit run returns
    # somebody else's number. The field name is what makes it the book's own.
    shoga = ('&quot;isbn_cd&quot;:&quot;9784091234560&quot;, related: 978-4-09-851261-4 '
             '&quot;isbn13_cd&quot;:&quot;9784098547401&quot;')
    s.eq(P.publisher_isbn(shoga, "www.shogakukan.co.jp"), "9784098547401",
         "小学館's own field wins over a related title's number on the same page")

    s.eq(P.publisher_isbn("<th>ISBN</th><td>9784344856981</td>", "example.invalid"), None,
         "a host with no pattern is not read by another publisher's, and says so with None")

    # ── a shop id followed into the publisher's own catalogue ────────────────────────────────
    # ビッコミ gives every shop a keyword search except 小学館's comic database, whose JDCN carries
    # the book code. The code names the page; the page states the number.
    s.eq(S.shop_id_of("http://csbs.shogakukan.co.jp/book/detail-volume?cp=7100&amp;"
                      "jdcn=098632590000d0000000"),
         ("shogakukan_jdcn", "09863259", None), "the JDCN's first eight digits are the book code")
    s.eq(P.publisher_page("shogakukan_jdcn", "09863259"),
         "https://www.shogakukan.co.jp/books/09863259", "which names the catalogue page")

    # THE GUARD. A site answering an unknown path with its newest book is the failure this project
    # meets most. Where the code is the middle of the number, the number is the check.
    s.check(P.states_id("9784098632596", "shogakukan_jdcn", "09863259"),
            "ベラドンナの恋人's page states an ISBN carrying the code it was reached by")
    s.check(not P.states_id("9784098547401", "shogakukan_jdcn", "09863259"),
            "and a page answering with another book is refused")
    s.check(P.states_id("9784344856981", "gentosha_book", "b671924"),
            "a catalogue serial with no relation to the ISBN has nothing to check against")
    s.check(not P.states_id(None, "gentosha_book", "b671924"),
            "and a page stating no number is never a pass")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
