#!/usr/bin/env python3
"""Which engine a platform runs, and what asking it for a series' volumes costs.

WHY A TABLE. The 43 platforms in this database sit on a handful of engines, and the survey on
2026-08-07 established that the engine decides everything: where the shop links are, whether the
page is server-rendered, and how many requests one work costs. Adding a platform is a row here.

The `steps` value is the chain a work goes through, and it is stated because the cost differs by an
order of magnitude. `page` alone is one request for a work we already hold the URL of.
`page -> shop -> book` is three, and 219 カドコミ works at three requests each is a run rather than
a lookup.
"""

# A platform's host, the engine behind it, and the chain of requests reaching an ISBN.
#
#   giga        GigaViewer's series sidebar carries `series-book-details`, one block per collected
#               volume with a link to every shop the publisher offers. Server-rendered, so one
#               request. Where the link is a publisher's own book page rather than a shop stating
#               a number, a second request reads the number off that page.
#   comici      A series page names `/store_items/<id>` per volume; the item page carries the
#               shop row, and Amazon's print entry in it states the ISBN-10.
#   kadokomi    `__NEXT_DATA__` on /detail/<code> carries a shop row per volume. None of them
#               states a number: コミックシーモア's title id is the identifier, and cmoa's own work
#               page is where the ISBN is written.
#   pixiv       `works/<id>/ad_books` answers with the printed books, as Amazon product links whose
#               ASIN is the ISBN-10. The whole volume run, in one request.
#   gangan      ガンガンONLINE renders its own 単行本 section with a shop-banner row per volume.
#   comicboost  A series page links 幻冬舎コミックス's own book page per volume, which states it.
#   yanmaga     The series page links 講談社's product page, which states it in a meta tag. The URL
#               this database holds is the viewer, so the series page is its parent path.
ENGINES = {
    # ── GigaViewer ────────────────────────────────────────────────────────────────────────────
    "comic-days.com": ("giga", "コミックDAYS"),
    "tonarinoyj.jp": ("giga", "となりのヤングジャンプ"),
    "ichicomi.com": ("giga", "一迅プラス"),
    "www.sunday-webry.com": ("giga", "サンデーうぇぶり"),
    "shonenjumpplus.com": ("giga", "少年ジャンプ+"),
    "magcomi.com": ("giga", "MAGCOMI"),
    "comic-action.com": ("giga", "webアクション"),
    "comic-zenon.com": ("giga", "コミックゼノン"),
    "kuragebunch.com": ("giga", "くらげバンチ"),
    "comic-ogyaaa.com": ("giga", "COMIC OGYAAA!!"),
    "comic-earthstar.com": ("giga", "コミック アース・スター"),
    "comicborder.com": ("giga", "コミックボーダー"),
    "comic-gardo.com": ("giga", "コミックガルド"),
    "comic-trail.com": ("giga", "コミックトレイル"),
    "comic-seasons.com": ("giga", "Seasons"),
    "feelweb.jp": ("giga", "FEEL web"),
    "www.comic-ryu.jp": ("giga", "COMICリュウ"),
    "comic-y-ours.com": ("giga", "COMIC Y-OURS"),
    "ourfeel.jp": ("giga", "OUR FEEL"),
    # ── Comici ────────────────────────────────────────────────────────────────────────────────
    "bigcomics.jp": ("comici", "ビッコミ"),
    "championcross.jp": ("comici", "チャンピオンクロス"),
    "takecomic.jp": ("comici", "竹コミ"),
    "kimicomi.com": ("comici", "キミコミ"),
    "g-comi.jp": ("comici", "Gコミ"),
    "youngchampion.jp": ("comici", "ヤングチャンピオン"),
    "hanayume.com": ("comici", "花とゆめ+"),
    "comicride.jp": ("comici", "ライコミ"),
    "heros-web.com": ("comici", "HERO'S Web"),
    "comic.j-nbooks.jp": ("comici", "COMICリュエル"),
    "asacomi.jp": ("comici", "アサコミ"),
    "mangacross.jp": ("comici", "マンガクロス"),
    # ── one platform, one engine ──────────────────────────────────────────────────────────────
    "comic-walker.com": ("kadokomi", "カドコミ"),
    "comic.pixiv.net": ("pixiv", "pixivコミック"),
    "www.ganganonline.com": ("gangan", "ガンガンONLINE"),
    "comic-boost.com": ("comicboost", "comicブースト"),
    "yanmaga.jp": ("yanmaga", "ヤンマガWeb"),
}

STEPS = {
    "giga": "page",
    "comici": "page -> store item",
    "kadokomi": "page -> shop title page",
    "pixiv": "api",
    "gangan": "page",
    "comicboost": "page -> publisher book page",
    "yanmaga": "series page -> publisher book page",
}

# Platforms whose pages were read during the survey and carry no link to any shop selling a printed
# edition. Recorded so that "not checked" and "checked, nothing there" stay different answers.
# The reason is what makes each of them worth keeping.
NO_ROUTE = {
    "comic-fuz.com": ("COMIC FUZ",
                      "volumes are sold inside the platform's own store and no page links out. "
                      "The rendered series page names the imprint and offers no ISBN."),
    "pocket.shonenmagazine.com": ("マガポケ",
                                  "no 単行本 section and no outbound shop link on the rendered "
                                  "page. Its title API answers `invalid hash.` without a request "
                                  "signature the site's own bundle computes, and this project "
                                  "does not replay one."),
    "manga-park.com": ("マンガPark",
                       "the rendered series page carries no volume section and no outbound link "
                       "beyond the app stores and 白泉社's privacy policy."),
    "manga-one.com": ("マンガワン",
                      "no outbound shop link on the pages read, rendered or served. Its own "
                      "navigation carries a コミックス heading whose target was not found: "
                      "/comics answers with 404, and finding where it went is the one loose end "
                      "on this platform."),
    "www.corocoro.jp": ("コロコロオンライン", "no outbound shop link in the served page."),
    "www.123hon.com": ("コミックノヴァ", "no outbound shop link in the served page."),
    "flowercomics.jp": ("フラコミlike!", "no outbound shop link in the served page."),
    "manga.nicovideo.jp": ("ニコニコ漫画",
                           "the served page links BOOK☆WALKER, which states no ISBN anywhere."),
    "zerosumonline.com": ("ゼロサムオンライン", "no outbound shop link in the served page."),
    "www.yomonga.com": ("マンガよもんが",
                        "links booklive, Renta! and an amzn.asia short link, none of which "
                        "states a number without being followed."),
}


def engine_of(url):
    """`(engine, platform_name)` for a work's platform URL, or None where none is known."""
    import urllib.parse
    host = urllib.parse.urlparse(str(url or "")).netloc.lower()
    return ENGINES.get(host)


def host_of(url):
    import urllib.parse
    return urllib.parse.urlparse(str(url or "")).netloc.lower()
