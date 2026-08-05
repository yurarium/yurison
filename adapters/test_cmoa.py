#!/usr/bin/env python3
"""cmoa.py: reading a shop's shelf, and not losing half of it on the second pass."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cmoa  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/cmoa.py"]

# Quoted from https://www.cmoa.jp/search/genre/37/?page=1 as served on 2026-08-04, with the
# whitespace collapsed and the cover, price and review blocks cut. Everything the parser reads is
# here verbatim, including the empty `end_m` span that is the only completion marker on the page.
FINISHED = """
<li class="search_result_box">
  <div class="search_result_box_left" id="ti167439" >
    <a href="/title/167439/" class="title" >
      <p><img src="https://cmoa.akamaized.net/data/image/title/x.jpg"
              alt="付き合ってあげてもいいかな" class="volume_img"></p>
    </a>
  </div>
  <div class="search_result_box_right">
    <div class="search_result_box_right_sec1 ">
      <p>
        <a href="/title/167439/" class="title" >
          付き合ってあげてもいいかな
        </a>
        <span class="end_m"></span>
      </p>
    </div>
    <div class="search_result_box_right_sec2 clfix">
      <div class="search_result_box_right_sec2left">
        <p >作家： <a href="/search/author/88689/">たみふる</a></p>
        <p >ジャンル： <a href="/search/genre/20/">少女マンガ</a></p>
        <p >雑誌・レーベル： <a href="/search/magazine/9654/">裏サンデー女子部</a></p>
      </div>
    </div>
  </div>
</li>
"""

# The same shelf, a running series with two imprints on the row and no marker of any kind.
RUNNING = """
<li class="search_result_box">
  <div class="search_result_box_left" id="ti76203" >
    <a href="/title/76203/" class="title" >
      <p><img src="https://cmoa.akamaized.net/data/image/title/y.jpg"
              alt="MURCIELAGO -ムルシエラゴ-" class="volume_img"></p>
    </a>
  </div>
  <div class="search_result_box_right">
    <div class="search_result_box_right_sec1 ">
      <p>
        <a href="/title/76203/" class="title" >
          MURCIELAGO -ムルシエラゴ-
        </a>
        <span class="new_m_b"></span><span class="down_m"></span><span class="free2_m"></span>
      </p>
    </div>
    <div class="search_result_box_right_sec2 clfix">
      <div class="search_result_box_right_sec2left">
        <p >作家： <a href="/search/author/36593/">よしむらかな</a></p>
        <p >ジャンル： <a href="/search/genre/13/">青年マンガ</a></p>
        <p >雑誌・レーベル： <a href="/search/magazine/489/">ヤングガンガン</a>
            <span class="margin_left3 margin_right3">/</span>
            <a href="/search/magazine/7106/">ヤングガンガンコミックス</a></p>
      </div>
    </div>
  </div>
</li>
"""

# An anthology, because a row can carry four 作家 links and a parser reading only the first
# would drop three authors per row without the count changing.
ANTHOLOGY = """
<li class="search_result_box">
  <div class="search_result_box_left" id="ti214434" ></div>
  <div class="search_result_box_right">
    <div class="search_result_box_right_sec1 ">
      <p><a href="/title/214434/" class="title" >社会人百合アンソロジー</a></p>
    </div>
    <div class="search_result_box_right_sec2 clfix">
      <p >作家： <a href="/search/author/1/">はるかわ陽</a> <a href="/search/author/2/">奥たまむし</a>
                <a href="/search/author/3/">さつま揚げ</a> <a href="/search/author/4/">雪子</a></p>
      <p >ジャンル： <a href="/search/genre/2/">女性マンガ</a></p>
      <p >雑誌・レーベル： <a href="/search/magazine/9107/">百合姫コミックス</a></p>
    </div>
  </div>
</li>
"""

# The facet sidebar, as served, half-width parentheses and a thousands separator.
SIDEBAR = """
<div class="naviBlock searchPublisher"><h3 class="title">出版社で絞り込む</h3><ul class="ac_menu">
<li class="parent_1"><a href="/search/result/?genre_id=0000037&amp;publisher_id=0001814&amp;breadcrumbs=pi" class="ac_text">
    ナンバーナイン
    (595)
</a></li>
<li class="parent_1"><a href="/search/result/?genre_id=0000037&amp;publisher_id=0000052&amp;breadcrumbs=pi" class="ac_text">
    一迅社
    (450)
</a></li></ul></div>
"""

# A work page, quoted from https://www.cmoa.jp/title/167439/?page=1&order=up&disp_mode=easy as
# served on 2026-08-05, with the cover, price and cart blocks cut and volumes 3 to 14 removed. Every
# field the parser reads is here verbatim: the 作品情報 block with both dates and the ISBN, the
# unlabelled sub-genre row where 百合・GL is written, and the easy-mode volume list.
#
# The ISBN is quoted as the shop writes it, which is TEN digits. That is not an oddity of this one
# page; 一迅社 volumes carry thirteen and 小学館 volumes ten, and openBD answers only the long form.
WORK_PAGE = """
<h1 class="title_details_h1">付き合ってあげてもいいかな 1</h1>
<span class="font_12">作品ラインナップ&emsp;<span class="vol_release_text">全14巻完結</span></span>
<div id="comic_list">
  <ul class="title_vol_easy_box clearfix">
    <li class="title_vol_easy_box_in_th">
      <div class="title_check_box"><h3>
        <a href="/title/167439/">付き合ってあげてもいいかな 1</a>
      </h3></div>
    </li>
    <li class="title_vol_easy_box_in_th">
      <div class="title_check_box"><h3>
        <a href="/title/167439/vol/2/">付き合ってあげてもいいかな 2</a>
      </h3></div>
    </li>
  </ul>
</div>
<div class="related_text_box">
<div class="category_line"><div class="category_line_f_l_l">ジャンル</div>
  <div class="category_line_f_r_l"><span class="margin_r5">：</span>
  <a href="/search/genre/20/">少女マンガ</a></div></div>
<div class="category_line"><div class="category_line_f_r_l genre_detail">
  <a href="/search/genre/5/">恋愛</a>&nbsp;/&nbsp;<a href="/search/genre/37/">百合・GL</a>
  </div></div>
<div class="category_line"><div class="category_line_f_l_l">出版社</div>
  <div class="category_line_f_r_l"><span class="margin_r5">：</span>
  <a href="/search/publisher/22/">小学館</a></div></div>
<div class="category_line"><div class="category_line_f_l_l">雑誌・レーベル</div>
  <div class="category_line_f_r_l"><span class="margin_r5">：</span>
  <a href="/search/magazine/9654/">裏サンデー女子部</a></div></div>
<div class="category_line"><div class="category_line_f_l_l">配信開始日</div>
  <div class="category_line_f_r_l"><span class="margin_r5">：</span>2019年1月11日</div></div>
<div class="category_line"><div class="category_line_f_l_l">出版年月</div>
  <div class="category_line_f_r_l"><span class="margin_r5">：</span>2019年1月</div></div>
<div class="category_line"><div class="category_line_f_l_l">ISBN</div>
  <div class="category_line_f_r_l"><span class="margin_r5">：</span>
  <pre style="display:inline">4091287557</pre></div></div>
</div>
"""

# THE SHAPE MOST OF THIS SHELF IS IN, and the reason the capture cannot answer §6 for it. Quoted
# from https://www.cmoa.jp/title/222919/ on 2026-08-05. A digital distributor's page states a
# 配信開始日 and nothing else: no ISBN, no 出版年月. The page's own description says the file is
# the ebook edition of the author's 個人誌, so an earlier publication exists and the shop does not
# say when, which is why 配信開始日 must not be read as a publication date.
DIGITAL_ONLY = """
<span class="vol_release_text">1巻まで配信中！</span>
<div id="comic_list"><ul class="title_vol_easy_box clearfix">
  <li><div class="title_check_box"><h3>
    <a href="/title/222919/">#ミカちゃんともなちゃん</a>
  </h3></div></li>
</ul></div>
<div class="category_line"><div class="category_line_f_l_l">ジャンル</div>
  <div class="category_line_f_r_l"><span class="margin_r5">：</span>
  <a href="/search/genre/20/">少女マンガ</a></div></div>
<div class="category_line"><div class="category_line_f_l_l">出版社</div>
  <div class="category_line_f_r_l"><span class="margin_r5">：</span>
  <a href="/search/publisher/1793/">クロスフォリオ出版</a></div></div>
<div class="category_line"><div class="category_line_f_l_l">雑誌・レーベル</div>
  <div class="category_line_f_r_l"><span class="margin_r5">：</span>
  <a href="/search/magazine/10106/">BLIC-GL</a></div></div>
<div class="category_line"><div class="category_line_f_l_l">配信開始日</div>
  <div class="category_line_f_r_l"><span class="margin_r5">：</span>2021年5月28日</div></div>
"""


# The full list at /search/other/?type=publisher, which writes the same numbers full-width.
OTHER = """
<li><a href="/search/result/?genre_id=0000037&amp;publisher_id=0001814&amp;breadcrumbs=pi">
    ナンバーナイン （595）
</a></li>
<li><a href="/search/result/?genre_id=0000037&amp;publisher_id=0002032&amp;breadcrumbs=pi">
    ライトリーズン （90）
</a></li>
"""


def main(s):
    fin = cmoa.rows(FINISHED)
    s.eq(len(fin), 1, "one row, one title")
    r = fin[0]
    s.eq(r["title_id"], "167439", "the id comes off the row's own element")
    s.eq(r["title"], "付き合ってあげてもいいかな", "and the title off the text link, not the alt text")
    s.eq(r["authors"], ["たみふる"], "the 作家 link is the author")
    s.eq(r["genre"], "少女マンガ", "the demographic genre is what ジャンル carries on the row")
    s.eq(r["labels"], ["裏サンデー女子部"], "and 雑誌・レーベル is the imprint, kept apart from it")
    s.eq(r["completed"], True, "an empty end_m span is the shop's whole 完結 marker")
    s.eq(r["url"], "https://www.cmoa.jp/title/167439/", "the work page it points at")

    # THE COUNTER-CASE, checked before believing the marker. MURCIELAGO runs, and its row carries
    # three other decorative spans, so `end_m` distinguishes rather than merely being present.
    run = cmoa.rows(RUNNING)[0]
    s.eq(run["completed"], False, "a running series carries no end_m, among spans that are not it")
    s.eq(run["labels"], ["ヤングガンガン", "ヤングガンガンコミックス"],
         "a row states every imprint, and the magazine is one of them")
    s.eq(run["title"], "MURCIELAGO -ムルシエラゴ-", "a latin title survives the tag stripping")

    s.eq(cmoa.rows(ANTHOLOGY)[0]["authors"],
         ["はるかわ陽", "奥たまむし", "さつま揚げ", "雪子"],
         "an anthology row names four authors and all four are kept")

    s.eq(len(cmoa.rows(FINISHED + RUNNING + ANTHOLOGY)), 3, "three rows on a page of three")
    s.eq(cmoa.rows(""), [], "and no page, no rows")
    s.eq(cmoa.rows("<li class=\"search_result_box\">nothing useful</li>"), [],
         "a box with no id and no title yields nothing rather than a row of Nones")

    s.eq(cmoa.total("<span> 検索結果1,869件中 1～100件を表示 </span>"), 1869,
         "the shelf total is read with its separator")
    s.eq(cmoa.total("no count here"), None, "and absent where the page does not say")

    s.eq(cmoa.facet(SIDEBAR, "publisher"), [("0001814", "ナンバーナイン", 595),
                                            ("0000052", "一迅社", 450)],
         "the sidebar facet, half-width parentheses and all")
    s.eq(cmoa.facet(OTHER, "publisher"), [("0001814", "ナンバーナイン", 595),
                                          ("0002032", "ライトリーズン", 90)],
         "and the full list, which writes the same numbers full-width")

    # THE EXCLUSION. Each marker names a censored edition of an adult work, which REQUIREMENTS
    # excludes outright; the marker is returned so the exclusion can be counted per marker.
    s.eq(cmoa.censored_marker("【棒消し修正版】ある百合の話"), "棒消し", "a bar-erased edition")
    s.eq(cmoa.censored_marker("ある百合の話【R-18版】"), "R-18版", "an adult edition sold as one")
    s.eq(cmoa.censored_marker("ある百合の話【R18版】"), "R18版", "written without the hyphen")
    s.eq(cmoa.censored_marker("ある百合の話【白抜き修正】"), "白抜き修正", "a white-out")
    s.eq(cmoa.censored_marker("ある百合の話 修正版"), "修正版", "and the loose marker on its own")
    s.eq(cmoa.censored_marker("ある百合の話【Ｒ－１８版】"), "R-18版",
         "full-width writes the same marker and must match it")

    # 全年齢版, verified against the shop rather than reasoned about: 六番目の課長's author page
    # lists 微睡むラブカ filed アダルトマンガ and 微睡むラブカ-全年齢版- filed 青年マンガ, so the
    # all-ages edition is the same work as the adult one and the shop says so itself.
    s.eq(cmoa.censored_marker("微睡むラブカ-全年齢版-"), "全年齢版",
         "an all-ages edition names the adult edition it was cut from")
    s.eq(cmoa.censored_marker("Office Sweet 365(全年齢版)"), "全年齢版",
         "in whichever brackets the seller used")

    # THE COUNTER-CASE THE RULE WOULD BREAK, which is why this is not a substring search for 修正版.
    # 加筆修正 is authorial revision, an ordinary reissue with nothing censored about it.
    s.eq(cmoa.censored_marker("ある百合の話【加筆修正版】"), None,
         "a revised-and-expanded reissue is not a censored one")
    # THE OTHER NEAR MISS. 完全版 is a collected reissue and 11 titles on this shelf carry it; a
    # rule reaching for 版 would take all eleven.
    s.eq(cmoa.censored_marker("総合タワーリシチ 完全版"), None,
         "a collected edition is not an edition of anything adult")
    s.eq(cmoa.censored_marker("ある百合の話"), None, "and an ordinary title is not marked at all")
    s.eq(cmoa.censored_marker(""), None, "nor is nothing")

    # MERGING, which is the failure this capture is most likely to have. A second pass must add to
    # the first rather than replace it, and neither pass carries every field.
    doc, added = cmoa.merge({}, [{"cmoa_title_id": "1", "title": "あ", "publisher": None}], page=1)
    s.eq(added, 1, "the first page adds its rows")
    doc, added = cmoa.merge(doc, [{"cmoa_title_id": "2", "title": "い"}], page=2)
    s.eq(added, 1, "and the second adds its own")
    s.eq([t["cmoa_title_id"] for t in doc["titles"]], ["1", "2"],
         "with page one still in the file, which is the whole point of merging")
    s.eq(doc["pages_captured"], [1, 2], "and both pages recorded as captured")

    doc, added = cmoa.merge(doc, [{"cmoa_title_id": "1", "publisher": "一迅社"}])
    s.eq(added, 0, "a publisher pass adds no titles")
    s.eq(doc["titles"][0]["publisher"], "一迅社", "it fills the field the listing row could not")
    s.eq(doc["titles"][0]["title"], "あ", "and leaves alone the fields it does not carry")

    # A FIELD MUST NOT BE ERASED BY A PASS THAT DOES NOT CARRY IT. This is the specific way the
    # merge would fail silently: a well-formed file, the right number of rows, emptied columns.
    doc, _ = cmoa.merge(doc, [{"cmoa_title_id": "1", "publisher": None, "authors": []}])
    s.eq(doc["titles"][0]["publisher"], "一迅社", "an absent value overwrites nothing")

    doc, _ = cmoa.merge(doc, [{"cmoa_title_id": "2", "completed": False}])
    s.eq(doc["titles"][0]["publisher"], "一迅社", "and false is a value, not an absence")
    s.eq(doc["titles"][1]["completed"], False, "so it is written")

    s.eq(cmoa.merge({"titles": [{"cmoa_title_id": "9"}]}, [])[0]["titles"],
         [{"cmoa_title_id": "9"}], "an empty pass loses nothing at all")

    # DOUJIN IS A FACT ABOUT THE SELLER. The list is evidence-only, so the counter-case matters
    # more than the case: a publisher nobody has established is False, and False is not a finding.
    s.eq(cmoa.is_doujin("ナンバーナイン", ["百合コレ"]), True, "the distributor the recon named")
    s.eq(cmoa.is_doujin("ナンバーナイン", []), True, "by its own name, whatever the label says")
    s.eq(cmoa.is_doujin("どこか", ["百合コレ"]), True, "or by the label, whoever is named beside it")
    s.eq(cmoa.is_doujin("一迅社", ["百合姫コミックス"]), False,
         "and a commercial imprint is not on the list")
    s.eq(cmoa.is_doujin("ライトリーズン", ["ライトリーズン"]), False,
         "nor is a publisher that reads like one and was never established")
    s.eq(cmoa.is_doujin(None, None), False, "no publisher, no claim")

    # ── The work page, which is where a date has to come from ────────────────────────────────
    w = cmoa.work(WORK_PAGE, "167439")
    s.eq(w["publisher"], "小学館", "the publisher a listing row does not carry")
    s.eq(w["imprint"], "裏サンデー女子部", "and the imprint, kept apart from it")
    s.eq(w["genres"], ["少女マンガ", "恋愛", "百合・GL"],
         "百合・GL is in the unlabelled sub-genre row, so a parser reading labels alone loses it")
    s.eq(w["volumes_stated"], 14, "the shop's own sentence says fourteen volumes")
    s.eq(w["completed"], True, "and says the series finished")
    s.eq([v["volume"] for v in w["volumes"]], [1, 2],
         "while the list on this page names two, which is the disagreement worth seeing")
    s.eq(w["volumes"][0]["url"], "https://www.cmoa.jp/title/167439/",
         "volume 1 is the entry whose link is the bare work URL")
    s.eq(w["volumes"][1]["url"], "https://www.cmoa.jp/title/167439/vol/2/",
         "and every later volume has a page of its own")
    s.eq(w["detail_volume"], 1, "so the ISBN and the dates below belong to volume 1")
    s.eq(w["isbn"], "9784091287557",
         "the ten-digit ISBN the shop wrote, converted to the form openBD answers")
    s.eq(w["published"], "2019-01", "出版年月 is a publication date and is kept as a month")
    s.eq(w["distribution_started"], "2019-01-11",
         "配信開始日 is the day the shop started selling the file, under its own name")

    # THE COUNTER-CASE, and it is the majority of this shelf rather than an edge. A digital
    # distributor states a 配信開始日 and nothing else, so the date field must come back empty
    # rather than borrowing the one date on the page.
    dig = cmoa.work(DIGITAL_ONLY, "222919")
    s.eq(dig["isbn"], None, "no ISBN on a page that states none")
    s.eq(dig["published"], None, "and no publication date invented from the one date present")
    s.eq(dig["distribution_started"], "2021-05-28", "which is recorded, under its own name")
    s.eq(dig["volumes_stated"], 1, "1巻まで配信中 says one volume")
    s.eq(dig["completed"], False, "and says nothing about the series being finished")
    s.eq(dig["publisher"], "クロスフォリオ出版", "the publisher still reads")

    s.eq(cmoa.work("", "1")["volumes"], [], "an empty page yields no volumes rather than one None")
    s.eq(cmoa.work("", "1")["isbn"], None, "and no fields guessed from nothing")

    # DATES KEEP THE PRECISION THEY WERE GIVEN. Padding 2019年1月 to a day would put a fact in the
    # field that decides scope which no source ever stated.
    s.eq(cmoa.iso_date("2015年9月19日"), "2015-09-19", "a full date, zero-padded")
    s.eq(cmoa.iso_month("2019年1月"), "2019-01", "a month stays a month")
    s.eq(cmoa.iso_date("2019年1月"), None, "and a month is not read as a date")
    s.eq(cmoa.iso_month("２０１９年１月"), "2019-01", "full-width digits are the same date")
    s.eq(cmoa.iso_date(""), None, "nothing states nothing")

    # ISBN-10 TO 13. Checked against openBD rather than against the algorithm: 4091287557 is
    # 付き合ってあげてもいいかな 1, and openBD answers for 9784091287557 with pubdate 201901, which
    # is the same month cmoa states. Two sources, one fact, agreeing.
    s.eq(cmoa.isbn13("4091287557"), "9784091287557", "a ten-digit ISBN becomes a thirteen")
    s.eq(cmoa.isbn13("4-09-128755-7"), "9784091287557", "hyphens and all")
    s.eq(cmoa.isbn13("9784758074803"), "9784758074803", "a thirteen is already one")
    s.eq(cmoa.isbn13("n/a"), None, "and a field that is not an ISBN yields none")
    s.eq(cmoa.isbn13(""), None, "nor does an empty one")
    s.eq(cmoa.isbn13(None), None, "nor a missing one")

    s.eq(cmoa.stated_volumes("<span class=\"vol_release_text\">全14巻完結</span>"), (14, True),
         "全14巻完結 is fourteen volumes and finished")
    s.eq(cmoa.stated_volumes("<span class=\"vol_release_text\">3巻まで配信中！</span>"), (3, False),
         "and 3巻まで配信中 is three volumes and still running")
    s.eq(cmoa.stated_volumes("nothing of the sort"), (None, False),
         "a page that does not say gives no count, rather than zero")

    # A VOLUME IS NUMBERED BY ITS LINK, NEVER BY ITS NAME. This shelf holds titles ending in a
    # number, and reading one out of the name would eventually number a work by its own title.
    numbered = ('<div class="title_check_box"><h3><a href="/title/9/vol/7/">'
                'ぼくらの7日間戦争 2</a></h3></div>')
    s.eq(cmoa.volumes(numbered, "9")[0]["volume"], 7,
         "the link says seven and the name's trailing 2 is part of the title")

    s.eq(cmoa.work_url("167439"),
         "https://www.cmoa.jp/title/167439/?page=1&order=up&disp_mode=easy",
         "the page that lists every volume and prints no synopsis under any of them")
    s.eq(cmoa.volume_url("167439", 1), "https://www.cmoa.jp/title/167439/",
         "volume 1 is the work URL itself")
    s.eq(cmoa.volume_url("167439", 2), "https://www.cmoa.jp/title/167439/vol/2/",
         "and the rest hang off it")

    s.eq(cmoa.shelf_url(3, publisher_id="0001814"),
         "https://www.cmoa.jp/search/result/?genre_id=0000037&sort=14&page=3"
         "&publisher_id=0001814", "the shelf narrowed to one publisher")
    s.eq(cmoa.shelf_url(1, complete_only=True),
         "https://www.cmoa.jp/search/result/?genre_id=0000037&sort=14&page=1&complete_flg=1",
         "and narrowed to what the shop calls finished")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
