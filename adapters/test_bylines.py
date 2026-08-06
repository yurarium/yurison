#!/usr/bin/env python3
"""bylines.py: reading the byline a platform prints beside a work it publishes."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bylines  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/bylines.py"]

# Quoted from the served このはな綺譚 page, shortened. The second author-list is the first
# RECOMMENDED work below the fold, which is the trap: it is the same markup, and taking every
# match credits この花綺譚 to three people who had nothing to do with it.
BOOST = '''<input type="search" placeholder="作品名・作者名を入力してください"/>
<h1 class="comic-title">このはな綺譚</h1>
<ul class="author-list">
  <li class="author"><a href="/author/%E5%A4%A9%E4%B9%83%E5%92%B2%E5%93%89">天乃咲哉</a></li>
</ul>
<h3 class="title">悪役令嬢、庶民に堕ちる</h3>
<ul class="author-list">
  <li class="author">原作：<a href="/author/x">緋月紫砲</a></li>
  <li class="author">作画：<a href="/author/y">おひたし熱郎</a></li>
  <li class="author">キャラクター原案：<a href="/author/z">切符</a></li>
</ul>'''

# Quoted from the served ガチ恋やめて series page.
YANMAGA = '''<h1 class="detailv2-outline-title">ガチ恋やめて</h1>
<ul class="detailv2-outline-author">
  <li class="detailv2-outline-author-item">
    <a href="/comics/authors/ab98e06795e9503b3ce831cadf2a6048"><h2>宇藤あかり</h2></a>
  </li>
</ul>
<div class="detailv2-recommend"><div class="detail-footer-title">同じ作者の作品</div></div>'''

# Quoted from the served この百合はフィクションです page. The synopsis reuses the class the byline
# uses, so a rule matching `txtColorSubject` alone returns the plot.
PARK = '''<h1 class="txtColorSubject">この百合はフィクションです</h1>
<p class="author txtColorSubject">むちゃハム</p>
<p class="txtColorSubject">アイドルグループのメンバー・伊達沙愛良と直江めぐむは……</p>
<p class="author">天乃忍</p>'''

# Quoted from the served 研究棟の真夜中ごはん page. ファイアCROSS writes the role into the name.
FIRECROSS = '''<script type="application/ld+json">[{"@type": "BreadcrumbList",
"itemListElement": []}, {"@type": "BookSeries", "name": "\\u7814\\u7a76",
"author": [{"@type": "Person", "name": "\\u590f\\u6cb3\\u3082\\u304b\\uff08\\u6f2b\\u753b\\uff09"},
{"@type": "Person", "name": "\\u795e\\u5ca1\\u9ce5\\u4e43\\uff08\\u539f\\u4f5c\\uff09"}]}]</script>'''

# GANMA! wraps its Person in an @graph and credits one person.
GANMA = ('<script type="application/ld+json">{"@context":"https://schema.org","@graph":'
         '[{"@type":"BreadcrumbList"},{"@type":"Book","author":{"@type":"Person",'
         '"name":"\\u7b4b\\u8089\\u2606\\u592a\\u90ce","sameAs":""}}]}</script>')

# Quoted from the served ナナシの転生 page. The franchise's owner is credited as a Person in the
# author list, and named as the publisher in the same graph.
FIRECROSS_HOUSE = (
    '<script type="application/ld+json">{"@type":"BookSeries","author":['
    '{"@type":"Person","name":"\\u7dcb\\u6708\\u30a2\\u30ad\\u30e9\\uff08\\u6f2b\\u753b\\uff09"},'
    '{"@type":"Person","name":"\\u30db\\u30d3\\u30fc\\u30b8\\u30e3\\u30d1\\u30f3'
    '\\uff08\\u539f\\u4f5c\\uff09"}],"publisher":{"@type":"Organization",'
    '"name":"\\u30db\\u30d3\\u30fc\\u30b8\\u30e3\\u30d1\\u30f3\\uff08\\u30b3\\u30df\\u30c3\\u30af'
    '\\u30d5\\u30a1\\u30a4\\u30a2\\uff09"}}</script>')


def main(s):
    s.eq(bylines.from_comicboost(BOOST), [("天乃咲哉", "")],
         "comicブースト credits the work under its own title and not the shelf below it")

    # THE COUNTER-CASE THE ANCHOR EXISTS FOR. Without the h1 anchor the first author-list on a
    # page could belong to anything, and this page proves the shape repeats.
    s.eq(bylines.from_comicboost(BOOST.replace('<h1 class="comic-title">このはな綺譚</h1>', "")),
         [], "and reads nothing at all where the work's own title is not on the page")

    s.eq(bylines.from_yanmaga(YANMAGA), [("宇藤あかり", "")], "ヤンマガWeb's series-page byline")
    s.eq(bylines.from_yanmaga("<html>an episode page</html>"), [],
         "and nothing from a page that carries no series byline")

    s.eq(bylines.from_mangapark(PARK), [("むちゃハム", "")],
         "マンガPark credits the work, not the recommendation further down")

    # THE LABEL ARRIVES ON EITHER SIDE OF THE COLON, and both shapes are マンガPark's.
    s.eq(bylines.from_mangapark(
        '<p class="author txtColorSubject">陽気婢 御坊：原案監修 丸山ゴンザレス：協力</p>'),
        [("陽気婢", ""), ("御坊", "原案監修"), ("丸山ゴンザレス", "協力")],
        "several credits in one paragraph, the role read from whichever side of the colon it is on")
    s.eq(bylines.from_mangapark(
        '<p class="author txtColorSubject">原作：来須みかん（ツギクル）　漫画：霜月かいり</p>'),
        [("来須みかん（ツギクル）", "原作"), ("霜月かいり", "漫画")],
        "and the same paragraph with the labels in front instead")
    # THE COUNTER-CASE FOR SPLITTING ON SPACE. 宮原　都 is one person.
    s.eq(bylines.from_mangapark('<p class="author txtColorSubject">宮原　都</p>'),
         [("宮原　都", "")],
         "an unlabelled paragraph is one credit, however many spaces are in it")

    s.eq(bylines.from_jsonld(FIRECROSS), [("夏河もか", "漫画"), ("神岡鳥乃", "原作")],
         "schema.org author, with the role ファイアCROSS writes into the name taken off it")
    s.eq(bylines.from_jsonld(GANMA), [("筋肉☆太郎", "")],
         "and a single Person nested inside an @graph")
    s.eq(bylines.from_jsonld(FIRECROSS_HOUSE), [("緋月アキラ", "漫画")],
         "a credit that is the record's own publisher is the rights holder, not a pen name")
    s.eq(bylines.from_jsonld("<html>no ld+json here</html>"), [], "no graph, no author")
    s.eq(bylines.from_jsonld('<script type="application/ld+json">{oh dear</script>'), [],
         "and a graph that will not parse is silence rather than a crash")

    # A ROLE IS NOT PART OF A NAME. Both shapes reach us, and a credit taken whole invents a
    # person called 原作：緋月紫砲.
    s.eq(bylines.one_credit("原作：緋月紫砲"), ("緋月紫砲", "原作"), "a role label in front")
    s.eq(bylines.one_credit("夏河もか（漫画）"), ("夏河もか", "漫画"), "and a role in brackets after")
    s.eq(bylines.one_credit("白き乙女の人狼（ウェアウルフ）"), ("白き乙女の人狼（ウェアウルフ）", ""),
         "but a bracket holding anything else is part of the name and stays")
    s.eq(bylines.credits("漫画：白梅ナズナ／原作：まきぶろ／キャラクターデザイン：紫 真依"),
         [("白梅ナズナ", "漫画"), ("まきぶろ", "原作"), ("紫 真依", "キャラクターデザイン")],
         "pixivコミック's one-string credit, split on its own separator")
    s.eq(bylines.one_credit("特別協賛：カルピス"), ("特別協賛：カルピス", ""),
         "a colon with a role word on neither side is left whole rather than half-stripped")

    s.eq(bylines.credit_line([("白梅ナズナ", "漫画"), ("まきぶろ", "原作")]), "白梅ナズナ / まきぶろ",
         "the credit written the way every other source writes one, in the order listed")
    s.eq(bylines.credit_line([("A", "原作"), ("A", "作画")]), "A",
         "one person credited twice is one person")

    # THE URL THE CORPUS HOLDS IS NOT ALWAYS THE WORK'S PAGE.
    s.eq(bylines.series_url("https://yanmaga.jp/comics/TANGO/0887c82c0482f0b770e2af3a19275b62"),
         "https://yanmaga.jp/comics/TANGO", "ヤンマガWeb's episode hash comes off")
    s.eq(bylines.series_url("https://yanmaga.jp/comics/TANGO"),
         "https://yanmaga.jp/comics/TANGO", "and a series URL is left as it is")
    s.eq(bylines.series_url("https://comic-boost.com/content/00010001"),
         "https://comic-boost.com/content/00010001", "every other host keeps its URL")
    s.eq(bylines.series_url("https://comic.pixiv.net/works/7926"),
         "https://comic.pixiv.net/api/app/works/v5/7926",
         "pixivコミック draws its page in the browser, so the endpoint behind it is read instead")
    s.eq(bylines.host_headers("https://comic.pixiv.net/api/app/works/v5/7926")
         .get("X-Requested-With"), "pixivcomic", "with the header that endpoint is fed")
    s.eq(bylines.host_headers("https://comic-boost.com/content/00010001"), {},
         "and nothing extra anywhere else")

    # Quoted from the served works/v5/7926 payload, with the fields this reads.
    s.eq(bylines.from_pixivcomic(
        '{"data":{"official_work":{"id":7926,'
        '"author":"漫画：白梅ナズナ／原作：まきぶろ／キャラクターデザイン：紫 真依"}}}'),
        [("白梅ナズナ", "漫画"), ("まきぶろ", "原作"), ("紫 真依", "キャラクターデザイン")],
        "pixivコミック's own catalogue endpoint")
    s.eq(bylines.from_pixivcomic('{"data":{}}'), [], "an envelope with no work in it is silence")
    s.eq(bylines.from_pixivcomic("<html>an error page</html>"), [],
         "and so is a response that is not JSON at all")

    # ── the print half: a shop's contributor line-up ────────────────────────────────────────
    # Quoted from data/queue/admitted.yaml, one row per shop for one anthology.
    shelf = [
        {"title": "SM百合えっちアンソロジー", "shop": "bookwalker.jp",
         "authors": ["著者: 伊月クロ 他"]},
        {"title": "SM百合えっちアンソロジー", "shop": "cmoa.jp",
         "authors": ["伊月クロ", "三本ひより", "檜原フキ"]},
        {"title": "百合姫Wildrose", "shop": "cmoa.jp", "authors": ["アンソロジー"]},
        {"title": "百合 + カノジョ", "shop": "cmoa.jp", "authors": ["Be編集部"]},
    ]
    key = lambda t: t                                                          # noqa: E731
    s.eq(bylines.shelf_credits(shelf, key, "SM百合えっちアンソロジー"),
         ["伊月クロ", "三本ひより", "檜原フキ"],
         "コミックシーモア's whole line-up, and not BOOK☆WALKER's truncation of it")
    s.eq(bylines.shelf_credits(shelf, key, "SM百合えっちアンソロジー", shop="bookwalker.jp"),
         ["著者: 伊月クロ 他"],
         "the shop is the caller's choice, so the exclusion above is a decision and not an accident")
    # THE PLACEHOLDER IS THE TRAP. コミックシーモア files 29 works under `アンソロジー`, and taken
    # as a credit it becomes a pen name with 29 works and a reading.
    s.eq(bylines.shelf_credits(shelf, key, "百合姫Wildrose"), [],
         "`アンソロジー` says what the book is and names nobody")
    s.eq(bylines.shelf_credits(shelf, key, "名のない本"), [], "a work the shop does not carry")

    s.eq(bylines.groups_among(["Be編集部", "伊月クロ"]), ["Be編集部"],
         "an editorial department is a credit and not a person, and is marked rather than dropped")
    s.eq(bylines.groups_among(["編集長"]), [],
         "and a word merely containing 編集 is not one")

    # THE SECOND RUN ERASED THE FIRST. The corpus reads this pass's output, so a work it settled
    # is credited to somebody on the next run, drops out of the queue, and is written out of the
    # file — which unsettles it. Both halves of the oscillation report a clean run.
    got = [{"w": "settled by this pass", "a": "天乃咲哉"},
           {"w": "credited by the platform", "a": "缶乃"},
           {"w": "nobody", "a": ""}]
    q = bylines.outstanding(got, lambda x: x["a"], lambda x: x["w"], {"settled by this pass"})
    s.eq([x["w"] for x in q], ["settled by this pass", "nobody"],
         "the queue keeps what this pass already answered, so re-running does not undo it")
    s.eq([x["w"] for x in bylines.outstanding(got, lambda x: x["a"], lambda x: x["w"], set())],
         ["nobody"], "and holds only the uncredited on a first run, when it has claimed nothing")

    # AN UNLISTED HOST IS READ BY NOTHING. Speculative parsing is what this module refuses.
    s.eq(bylines.byline("https://manga-one.com/viewer/290902", BOOST), [],
         "a host with no proven shape returns nothing, whatever the page happens to contain")
    s.eq(bylines.byline("https://comic-boost.com/content/00010001", BOOST), [("天乃咲哉", "")],
         "and a listed host is read by its own shape")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, __file__))
