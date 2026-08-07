#!/usr/bin/env python3
"""shop.py: the shop answers what it stocks, and a title alone is never a join."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import testkit                                                                 # noqa: E402
from shopquery import shop                                                     # noqa: E402

COVERS = ["adapters/shopquery/shop.py", "adapters/shopquery/capture.py"]

# Saved from https://bookwalker.jp/search/?word=%E5%8D%AF%E8%8A%B1%E3%82%8A%E3%82%8A%E3%81%8B&qcat=2
# on 2026-08-07, trimmed to the elements read. TWO RESULTS, and only one of them is the work: the
# author search returns コンカフェ嬢は恋を着る and also なかよし, the magazine she has drawn in. That
# second row is the whole reason `pick` exists and is kept in the fixture on purpose.
AUTHOR_SEARCH = """
<ul class="m-tile-list">
<li class="m-tile">
<div class="m-book-item ">
<a href="https://bookwalker.jp/series/490418/list/" class="m-thumb__image" data-series-id="490418"></a>
<div class="m-book-item__tag-box"><span class="a-tag-comic">マンガ</span>
<span class="a-tag-comp">完結</span></div>
<p class="m-book-item__title">
<a href="https://bookwalker.jp/series/490418/list/" data-series-id="490418"
   title="コンカフェ嬢は恋を着る（ＦＵＺコミックス）">
コンカフェ嬢は恋を着る（ＦＵＺコミックス）
</a>
</p>
<p class="m-book-item__label">ＦＵＺコミックス</p>
<div class="m-book-item__series"><span class="ico-txt">シリーズ3冊</span></div>
<ul class="m-book-item__btn-box">
<li><a href="https://bookwalker.jp/de286eb300-ea25-41f1-8918-aee33bfeeead/"><span class="ico">1巻</span></a></li>
<li><a href="https://bookwalker.jp/de8c546680-ed18-40ff-bc63-b4395376b5f9/"><span class="ico">2巻</span></a></li>
</ul>
</div>
</li>
<li class="m-tile">
<div class="m-book-item ">
<a href="https://bookwalker.jp/series/46180/list/" class="m-thumb__image" data-series-id="46180"></a>
<div class="m-book-item__tag-box"><span class="a-tag-comic">マンガ</span></div>
<p class="m-book-item__title">
<a href="https://bookwalker.jp/series/46180/list/" data-series-id="46180" title="なかよし（なかよし）">
なかよし（なかよし）
</a>
</p>
<p class="m-book-item__label">なかよし</p>
<ul class="m-book-item__btn-box">
<li><a href="https://bookwalker.jp/dea987c8ae-e9a5-4311-9030-65e562c6dbc5/"><span class="ico">1巻</span></a></li>
</ul>
</div>
</li>
</ul>
"""

# Saved from https://bookwalker.jp/de286eb300-ea25-41f1-8918-aee33bfeeead/ on 2026-08-07, trimmed to
# the 作品情報 rows. NO ISBN APPEARS ANYWHERE ON THE PAGE, which is the fact that decides how
# by_shop_query.py has to reach the bibliography.
VOLUME_PAGE = """
<dl class="t-c-detail-about-information">
<dt>シリーズ</dt><dd><a href="/series/490418/">コンカフェ嬢は恋を着る（ＦＵＺコミックス）</a></dd>
<dt>著者</dt><dd><a href="/author/1/">卯花りりか</a>(著)</dd>
<dt>レーベル</dt><dd><a href="/label/1/">ＦＵＺコミックス</a></dd>
<dt>出版社</dt><dd><a href="/company/1/">芳文社</a></dd>
<dt>配信開始日</dt><dd>2024/11/5</dd>
</dl>
"""

# A page whose markup changed: the tile wrapper is there and the title block is not. A parser that
# answers with a row full of Nones here is worse than one that answers with nothing, because the
# capture would store a hit that names no work.
BROKEN = '<ul class="m-tile-list"><li class="m-tile"><div class="m-book-item "></div></li></ul>'


def main(s):
    rows = shop.tiles(AUTHOR_SEARCH)
    s.eq(len(rows), 2, "both results are read, including the one that is not the work")
    first = rows[0]
    s.eq(first["series_id"], "490418", "the series the tile identifies")
    s.eq(first["title_listed"], "コンカフェ嬢は恋を着る（ＦＵＺコミックス）", "the title as listed")
    s.eq(first["imprint"], "ＦＵＺコミックス", "the shop prints the publisher's own label")
    s.eq(first["volumes_stated"], 3, "and how many volumes it stocks")
    s.eq(first["completed_marker"], True, "完結 on the tile, which costs no extra request")
    s.eq(len(first["volume_urls"]), 2, "with a link to each volume it listed")
    s.eq(rows[1]["completed_marker"], False,
         "and a running series carries no marker, so the tag distinguishes")

    s.eq(shop.tiles(BROKEN), [], "a tile with no title block produces no row at all")
    s.eq(shop.tiles(""), [], "and neither does an empty answer")

    # THE FILTER. An author search answers with everything that author is on, and only one of the
    # two names the work. Without this the capture would store なかよし as a print edition of
    # コンカフェ嬢は恋を着る, which is the wrong-join class this whole route is built around.
    kept = shop.pick(rows, "コンカフェ嬢は恋を着る")
    s.eq(len(kept), 1, "only the result whose title names the work is kept")
    s.eq(kept[0]["series_id"], "490418", "and it is the right one")
    s.eq(shop.pick(rows, "citrus"), [], "a work the shop does not stock keeps nothing")

    # The imprint the shop appends to a series name has to fold away, or every FUZ work misses.
    s.eq(shop.title_agrees("コンカフェ嬢は恋を着る（ＦＵＺコミックス）", "コンカフェ嬢は恋を着る"),
         True, "the appended imprint is bracketed matter and folds away")
    s.eq(shop.title_agrees("トワ・エ・モア", "トワ・エ・モア"), True, "identical titles agree")
    s.eq(shop.title_agrees("citrus+", "citrus"), True,
         "and a title extending ours agrees, which is why a person still has to")
    s.eq(shop.title_agrees("なかよし（なかよし）", "コンカフェ嬢は恋を着る"), False,
         "an unrelated series does not")
    s.eq(shop.title_agrees("", "コンカフェ嬢は恋を着る"), False, "and an empty title agrees with nothing")

    got = shop.details(VOLUME_PAGE)
    s.eq(got["author"], "卯花りりか(著)", "the credit, as the shop writes it")
    s.eq(got["imprint"], "ＦＵＺコミックス", "the imprint")
    s.eq(got["publisher"], "芳文社", "the publisher, which is the field a bibliography agrees on")
    s.eq(got["delivered"], "2024/11/5", "and the date the file went on sale, which is not a "
                                        "publication date and is never offered as one")
    s.eq(shop.names(got["author"]), {"卯花りりか"},
         "the role bracket folds away without a second parser for it")

    # THE JOIN RULE, AND THE COUNTER-CASE IT EXISTS FOR. A title that agrees and a person who does
    # not is a candidate and never a join.
    s.eq(shop.classify(got["author"], "卯花りりか"), "creator",
         "a shared person is what makes a hit a join")
    s.eq(shop.classify(got["author"], "卯花りりか,中村朱里"), "creator",
         "and one shared person out of several is enough")
    s.eq(shop.classify("大友克洋(著)", "菅野マナミ"), "title-only",
         "two different people on one title is a candidate, never a join")
    s.eq(shop.classify(None, "卯花りりか"), "title-only",
         "a shop that printed no credit cannot agree")
    s.eq(shop.classify(got["author"], None), "title-only",
         "and neither can a work this database credits to nobody")

    s.eq(shop.query_url("卯花りりか"),
         "https://bookwalker.jp/search/?word=%E5%8D%AF%E8%8A%B1%E3%82%8A%E3%82%8A%E3%81%8B&qcat=2",
         "the マンガ store, which is the same restriction the shelf capture used")


if __name__ == "__main__":
    suite = testkit.Suite("shopquery/shop.py")
    main(suite)
    raise SystemExit(suite.report())
