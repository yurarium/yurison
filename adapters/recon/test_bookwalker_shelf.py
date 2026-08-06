#!/usr/bin/env python3
"""bookwalker_shelf.py: reading a shop's yuri shelf without reading a classification into it."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bookwalker_shelf as bs  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import testkit  # noqa: E402

COVERS = ["adapters/recon/bookwalker_shelf.py"]

# Quoted from https://bookwalker.jp/tag/14/?qcat=2 on 2026-08-04, trimmed to the fields read.
# A series tile: no author anywhere in it, which is the whole reason the author field is thin.
SERIES_ROW = '''
<div class="m-book-item ">
<div class="m-book-item__thumb-block"><div class="m-thumb">
  <a href="https://bookwalker.jp/series/409505/list/" class="m-thumb__image" data-series-id="409505">
  <img class="lazy" alt="ＩＤＯＬ×ＩＤＯＬ　ＳＴＯＲＹ！（ＦＵＺコミックス）"/></a>
</div></div>
<div class="m-book-item__info-block"><div class="m-book-item__secondary">
  <div class="m-book-item__tag-box"><span class="a-tag-comic">マンガ</span></div>
  <p class="m-book-item__title">
    <a href="https://bookwalker.jp/series/409505/list/" class="m-book-item__title"
       title="ＩＤＯＬ×ＩＤＯＬ　ＳＴＯＲＹ！（ＦＵＺコミックス）">
      ＩＤＯＬ×ＩＤＯＬ　ＳＴＯＲＹ！（ＦＵＺコミックス）
    </a>
  </p>
  <p class="m-book-item__label">ＦＵＺコミックス</p>
</div>
<div class="m-book-item__series"><span class="ico-txt">シリーズ13冊</span></div>
<ul class="m-book-item__btn-box">
  <li><a href="https://bookwalker.jp/de3a1fc17e-d0b2-466f-8a40-05ae2e7649eb/">1巻</a></li>
</ul>
</div></div>
'''

# A finished series, from the same page. The shop states it with a tag on the row, so the shelf
# answers the completion question in one pass instead of one request per work.
DONE_ROW = '''
<div class="m-book-item ">
  <div class="m-book-item__tag-box"><span class="a-tag-comic">マンガ</span>
    <span class="a-tag-comp">完結</span></div>
  <p class="m-book-item__title">
    <a href="https://bookwalker.jp/series/381470/list/" class="m-book-item__title">
      どうしたら幼馴染の彼女になれますか！？（バンブーコミックス）
    </a>
  </p>
  <p class="m-book-item__label">バンブーコミックス</p>
  <div class="m-book-item__series"><span class="ico-txt">シリーズ5冊</span></div>
</div>
'''

# A standalone volume, from the same page. This one HAS an author, and its title carries no
# imprint in parentheses, so the two shapes disagree about every field that matters.
SINGLE_ROW = '''
<div class="m-book-item ">
  <div class="m-book-item__tag-box"><span class="a-tag-comic">マンガ</span></div>
  <p class="m-book-item__title">
    <a href="https://bookwalker.jp/de2e1cfdd3-cd86-4dd1-b330-c694f7c3c64c/"
       class="m-book-item__title">
      ガールズ×ヴァンパイア【描き下ろし付き電子特別版】　1
    </a>
  </p>
  <p class="m-book-item__author">
    漫画:
    千種みのり
    他
  </p>
  <p class="m-book-item__label">少年チャンピオン・コミックス</p>
</div>
'''

# Quoted from https://bookwalker.jp/tag/14/?wa=1 on 2026-08-04. A different template for a
# different store, and this one prints the author.
WA_ROW = '''
<div class="o-tile--series o-warensai-tile"><div class="o-tile-inner"><div class="o-tile-book-info">
  <div class="m-thumb-box"><a class="a-thumb-img" href="https://bookwalker.jp/series/312229/">
    <span class="a-ttsk-label-logo" aria-label="タテスクコミック" role="img"></span>
    <img class="lazy" alt="やがて君になる【タテスク】（タテスクコミック）"/></a></div>
  <h2 class="o-tile-ttl">
    <a href="https://bookwalker.jp/series/312229/">やがて君になる【タテスク】（タテスクコミック）</a>
  </h2>
  <p class="o-tile-book-author">仲谷 鳰</p>
</div>
<div class="o-tile-under-box"><p class="o-tile-count">シリーズ115冊</p></div>
</div></div>
'''

COUNT = '<div class="o-contents-section__search_count">1～60件目/全2153件</div>'

# Quoted from https://bookwalker.jp/series/269861/list/ on 2026-08-06, trimmed. A listing row as
# the shop really wraps it, followed by what the shop prints AFTER the listing. The wrapper and
# the cart list inside it are the point: the row ends at its own `</li>`, and the `</li>` of the
# cart is not it.
WRAPPED_ROW = '''
<ul class="m-tile-list"><li class="m-tile">
<div class="m-book-item ">
  <div class="m-book-item__tag-box"><span class="a-tag-comic">マンガ</span></div>
  <p class="m-book-item__title">
    <a href="https://bookwalker.jp/de084ab05a-417f-4264-8f92-cc5cf12eb6cd/"
       class="m-book-item__title">安達としまむら 公式コミックアンソロジー</a>
  </p>
  <p class="m-book-item__label">電撃コミックスNEXT</p>
  <ul class="m-book-item__btn-box"><li><a href="/cart/">カートを見る</a></li></ul>
</div>
</li></ul>
'''

# The 関連するシリーズ block, printed after the listing on a series page that has one. It carries
# `href="https://bookwalker.jp/series/..."`, which is what the last row used to swallow.
TRAILING = '''
<div class="relatedseries-advise">
  <a href="https://bookwalker.jp/series/17875/list/">安達としまむら（電撃文庫）</a>
  <span class="a-tag-comp">完結</span><span class="ico-txt">シリーズ12冊</span>
</div>
'''

FACETS = ('<li><a href="/tag/14/?order=rank&amp;qtag=42" rel="nofollow" data-ga-category="絞り込み"'
          ' data-action-label="ジャンル-完結">完結<span class="search-bookNum">(486)</span></a></li>'
          '<li><a href="/tag/14/?order=rank&amp;qtag=1083" rel="nofollow"'
          ' data-action-label="ジャンル-同人誌・個人出版">同人誌・個人出版'
          '<span class="search-bookNum">(378)</span></a></li>')


def main(s):
    rows = bs.parse_listing(SERIES_ROW + DONE_ROW + SINGLE_ROW)
    s.eq(len(rows), 3, "three rows on the page, three rows out")

    a, b, c = rows
    s.eq(a["id"], "409505", "a series tile is identified by its series id")
    s.eq(a["id_kind"], "series", "and says so")
    # THE TRAP THIS AVOIDS. The same tile links to de3a1fc17e-... , the uuid of volume 1. Taking
    # that as the row's identity files a 13-volume series under one of its volumes.
    s.eq(a["url"], "https://bookwalker.jp/series/409505/",
         "the series URL, not the first volume's, even though both are on the tile")
    s.eq(a["title"], "ＩＤＯＬ×ＩＤＯＬ　ＳＴＯＲＹ！", "the imprint comes off the title")
    s.eq(a["imprint"], "ＦＵＺコミックス", "and is kept, because it is the publisher's own label")
    s.eq(a["volumes"], 13, "the shop counts the volumes for us")
    s.eq(a["author"], None, "a series tile names no author, and inventing one is not on offer")
    s.eq(a["completed_marker"], False, "no marker on a running series")

    s.eq(b["completed_marker"], True, "and one on a finished series")
    s.eq(b["imprint"], "バンブーコミックス", "read off the label field")

    s.eq(c["id_kind"], "detail", "a standalone volume is identified by its uuid")
    s.eq(c["id"], "2e1cfdd3-cd86-4dd1-b330-c694f7c3c64c", "which is the one in its own URL")
    s.eq(c["author"], "漫画: 千種みのり 他", "and this shape does carry an author")
    # A standalone title has no （レーベル） appended, so the imprint has to come from the label
    # field. Splitting on brackets here would have eaten 【描き下ろし付き電子特別版】.
    s.eq(c["title"], "ガールズ×ヴァンパイア【描き下ろし付き電子特別版】　1",
         "and its title is left alone")
    s.eq(c["imprint"], "少年チャンピオン・コミックス", "with the imprint from the label field")
    s.eq(c["imprint_in_title"], None, "and nothing claimed to have come from the title")

    w = bs.parse_warensai(WA_ROW)
    s.eq(len(w), 1, "the 話・連載 store parses too")
    s.eq(w[0]["author"], "仲谷 鳰", "and this template prints the author")
    s.eq(w[0]["kind_tag"], "タテスク", "a タテスク badge is a fact about the row")
    s.eq(w[0]["id"], "312229", "with a series id like the other store")

    # THE COUNTER-CASE FOR THE IMPRINT SPLIT, checked before believing the rule. Half-width
    # parentheses appear inside real titles and stripping them renames the work; only the
    # full-width pair the shop appends is an imprint.
    s.eq(bs.split_imprint("ヒロイン(仮)"), ("ヒロイン(仮)", None),
         "half-width parentheses are part of the title")
    s.eq(bs.split_imprint("MURCIÉLAGO -ムルシエラゴ-"), ("MURCIÉLAGO -ムルシエラゴ-", None),
         "and a title with no bracket keeps all of itself")
    s.eq(bs.split_imprint("作品名（レーベル）"), ("作品名", "レーベル"), "while the shop's suffix comes off")
    s.eq(bs.split_imprint("（分冊版）（orSiS）"), ("（分冊版）", "orSiS"),
         "and only the last one comes off, because 分冊版 is not a label")

    s.eq(bs.censored_marker("百合えっち短編集"), None,
         "sexual content is not the test; this shelf is all-ages and the work is already held")
    s.eq(bs.censored_marker("【棒消し修正版】作品名"), "棒消し",
         "an edition re-cut to clear the filter is the adult work under another cover")
    s.eq(bs.censored_marker("作品名【Ｒ－１８版】"), "R18版", "full-width and hyphenated alike")
    s.eq(bs.censored_marker("作品名 全年齢版"), "全年齢版",
         "and a work needing an all-ages edition had an adult one first")

    # THE SHOP RENDERS AN ABSENT IMPRINT AS ――, and 143 rows on this shelf have one. Stored as
    # written it is a publisher called "――" on a seventh of the shelf, which is the plausible
    # wrong value STANDING-INSTRUCTIONS §4 is about. Absence is a state.
    s.eq(bs.parse_listing('<div class="m-book-item ">'
                          '<p class="m-book-item__title"><a class="m-book-item__title" '
                          'href="https://bookwalker.jp/series/1/">作品名</a></p>'
                          '<p class="m-book-item__label">――</p></div>')[0]["imprint"], None,
         "no imprint is no imprint, not a publisher named ――")

    s.eq(bs.author_names("漫画: 千種みのり 他"), ["千種みのり"],
         "the role prefix and the 他 that closes a truncated list are not part of a name")
    s.eq(bs.author_names("原作: 桃田　ロウ 作画: 甘城なつき"), ["桃田　ロウ", "甘城なつき"],
         "two roles, two people")
    # THE COUNTER-CASE. Splitting on whitespace would cut 桃田　ロウ in half, and most of the pen
    # names on this shelf carry an ideographic space in exactly that position.
    s.eq(bs.author_names("著: 森島 明子"), ["森島 明子"], "a name keeps the space inside it")
    s.eq(bs.author_names("アンソロジー"), ["アンソロジー"],
         "and an unattributed anthology is recorded as what the shop said, not dropped")
    # 編 is a role too, and a rule that only knew 編集 filed one row's author as
    # "編: コミックニュータイプ", which is a colon and a magazine rather than a person.
    s.eq(bs.author_names("編: コミックニュータイプ"), ["コミックニュータイプ"],
         "the editor prefix comes off like any other role")
    s.eq(bs.author_names(""), [], "an empty field names nobody")

    # THE CAP IS SPENT ON THE NAMES THAT NEED IT. A kana name answers itself and a Latin name has
    # no kana reading to state, so neither should consume a lookup.
    s.eq(bs.reading_route("あとき"), "surface", "kana is its own reading")
    s.eq(bs.reading_route("ｋｉｒｅｒｏ"), "latin", "full-width Latin is still Latin")
    s.eq(bs.reading_route("Rion Nomiya"), "latin", "and so is a romanised pen name")
    s.eq(bs.reading_route("桜庭友紀"), "lookup", "a name with kanji in it needs somebody to state it")
    s.eq(bs.reading_route("若（わか）"), "lookup",
         "and so does one that only looks settled: the kanji is still unread")
    s.eq(bs.reading_route(""), None, "no name, no route")

    s.eq(bs.shelf_authors([{"author": "著: 森島 明子", "title": "作品A"},
                           {"author": "著: 森島 明子", "title": "作品B"},
                           {"author": None, "title": "作品C"}]),
         {"森島 明子": ["作品A", "作品B"]},
         "one person, both their works, and a row naming nobody contributes nobody")

    s.eq(bs.total(COUNT), 2153, "the shop states the size of the shelf")
    s.eq(bs.total("<html>no count</html>"), None, "and where it does not, the answer is not a guess")

    f = bs.facet_counts(FACETS)
    s.eq(f["ジャンル-完結"][0], 486, "facet sizes are read off the page")
    s.eq(f["ジャンル-同人誌・個人出版"][1], "/tag/14/?order=rank&qtag=1083",
         "with the URL the shop gives, so a moved facet is absent rather than silently empty")
    s.eq("ジャンル-存在しない" in f, False, "and a facet that is not there is not there")

    # A ROW ENDS AT ITS OWN `</li>`, AND THAT IS WHAT THE LAST ROW NEVER HAD. Until 2026-08-06 a
    # row ran to the next row or, for the last one, to the end of the document, so everything the
    # shop printed after the listing belonged to the final row. On a series page that means the
    # 関連するシリーズ block, whose `/series/<id>/` link then became the row's identity, and
    # bookwalker_volumes keeps only rows identified by a volume uuid. A listing is sorted newest
    # first, so the row this dropped is the OLDEST volume and `first_publication` was chosen from
    # a set with the first volume missing.
    last = bs.parse_listing(WRAPPED_ROW + TRAILING)
    s.eq(len(last), 1, "the last row survives the markup printed after the listing")
    s.eq(last[0]["id_kind"], "detail",
         "and is still a volume, not the related series advertised underneath it")
    s.eq(last[0]["id"], "084ab05a-417f-4264-8f92-cc5cf12eb6cd", "with its own uuid")
    s.eq(last[0]["completed_marker"], False,
         "the 完結 tag below the listing belongs to the related series, not to this row")
    s.eq(last[0]["volumes"], None, "nor does the related series' volume count attach to it")
    # THE COUNTER-CASE FOR THE `</li>` RULE. A row nests a cart list of its own, so stopping at
    # the first `</li>` would end the row inside itself and lose whatever the shop prints after
    # the cart. Reading the label proves the row was not cut short there.
    s.eq(last[0]["imprint"], "電撃コミックスNEXT", "the whole row is read, cart list and all")
    # AND THE ROW BEFORE THE LAST ONE, which the old shape got right and must keep getting right.
    two = bs.parse_listing(WRAPPED_ROW + WRAPPED_ROW + TRAILING)
    s.eq([r["id_kind"] for r in two], ["detail", "detail"], "two rows, both volumes")

    s.eq(bs.parse_listing(""), [], "no page, no rows")
    s.eq(bs.parse_listing('<div class="m-book-item ">no title</div>'), [],
         "and a row with no title is dropped rather than recorded as a work with no name")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
