#!/usr/bin/env python3
"""bookwalker_volumes.py: what a shop states about a volume, and what it must not be read as."""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bookwalker_volumes as bv  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import testkit  # noqa: E402

COVERS = ["adapters/recon/bookwalker_volumes.py"]

# Quoted from https://bookwalker.jp/de283e72a6-6281-4d78-898e-04faab9a4ade/ on 2026-08-05, trimmed
# to the fields read. A print work: the shop states BOTH dates, and they are four days apart.
PRINT_VOLUME = '''
<script type="application/ld+json">
{
    "@context": "http://schema.org",
    "@type": "Product",
    "name": "＃ギャルとギャルの百合（１）",
    "url": "https://bookwalker.jp/de283e72a6-6281-4d78-898e-04faab9a4ade/",
    "offers": {"@type": "Offer", "price": 759, "priceCurrency": "JPY"}
}
</script>
<script> window.BW_R18_BASE_URL = "https://r18.bookwalker.jp"; </script>
<dl class="t-c-detail-about-information__data">
  <dt>シリーズ</dt>
  <dd><a href="https://bookwalker.jp/series/568145/list/" class="c-o-single-link --medium"
        data-action-label="series">＃ギャルとギャルの百合（サンデーうぇぶりコミックス）</a></dd>
  <dt>著者</dt>
  <dd><ul class="t-c-detail-about-information__list">
    <li><a href="https://bookwalker.jp/author/1/" data-action-label="author">イノウエ(著)</a></li>
  </ul></dd>
  <dt>レーベル</dt>
  <dd><a href="https://bookwalker.jp/label/1/" data-action-label="label">サンデーうぇぶりコミックス</a></dd>
  <dt>出版社</dt>
  <dd><a href="https://bookwalker.jp/company/1/" data-action-label="publisher">小学館</a></dd>
  <dt>カテゴリ</dt>
  <dd><a href="https://bookwalker.jp/category/2/" data-action-label="category">マンガ</a></dd>
  <dt>配信開始日</dt><dd>2025/12/26</dd>
  <dt>底本発行日</dt><dd>2025/12/31</dd>
  <dt>ページ概数</dt><dd><button type="button">198</button></dd>
</dl>
'''

# Quoted from https://bookwalker.jp/de89a94759-ce00-4f23-ba8c-3492b27ee330/ on 2026-08-05. A
# digital-first doujin imprint: NO 底本発行日 at all, which is the majority shape on this shelf and
# the reason first_publication cannot be answered for most of it.
DIGITAL_VOLUME = '''
<script type="application/ld+json">
{"@context": "http://schema.org", "@type": "Product", "name": "#ふれない"}
</script>
<script> window.BW_R18_BASE_URL = "https://r18.bookwalker.jp"; </script>
<dl class="t-c-detail-about-information__data">
  <dt>シリーズ</dt>
  <dd><a href="https://bookwalker.jp/series/999999/list/" data-action-label="series">#ふれない（百合コレ）</a></dd>
  <dt>著者</dt>
  <dd><ul><li><a href="https://bookwalker.jp/author/2/" data-action-label="author">蒼井紫(著)</a></li></ul></dd>
  <dt>レーベル</dt><dd><a href="https://bookwalker.jp/label/2/">百合コレ</a></dd>
  <dt>出版社</dt><dd><a href="https://bookwalker.jp/company/2/">ナンバーナイン</a></dd>
  <dt>カテゴリ</dt><dd><a href="https://bookwalker.jp/category/2/">マンガ</a></dd>
  <dt>配信開始日</dt><dd>2025/10/24</dd>
  <dt>ページ概数</dt><dd><button type="button">17</button></dd>
</dl>
'''

# Quoted from https://bookwalker.jp/de07b14596.../ on 2026-08-05, 新書館's ひらり、コミックス. Two
# things at once: no シリーズ row, so a standalone volume states no series; and the print date runs
# five weeks BEFORE the delivery date, where the 百合姫 row above runs two weeks after it.
STANDALONE_VOLUME = '''
<script type="application/ld+json">
{"@context": "http://schema.org", "@type": "Product", "name": "お姫様のひみつ"}
</script>
<dl class="t-c-detail-about-information__data">
  <dt>著者</dt>
  <dd><ul><li><a href="https://bookwalker.jp/author/28863/">森永みるく(著)</a></li></ul></dd>
  <dt>レーベル</dt><dd><a href="https://bookwalker.jp/label/844/">ひらり、コミックス</a></dd>
  <dt>出版社</dt><dd><a href="https://bookwalker.jp/company/56/">新書館</a></dd>
  <dt>カテゴリ</dt><dd><a href="https://bookwalker.jp/category/2/">マンガ</a></dd>
  <dt>配信開始日</dt><dd>2015/7/3</dd>
  <dt>底本発行日</dt><dd>2015/5/29</dd>
</dl>
'''

# Several people on one book, from https://bookwalker.jp/de5f304615.../ on 2026-08-05. Each name is
# its own anchor, so flattening the dd would join six people into one string.
MANY_AUTHORS = '''
<script type="application/ld+json">
{"@context": "http://schema.org", "@type": "Product", "name": "ある百合の短編"}
</script>
<dl class="t-c-detail-about-information__data">
  <dt>著者</dt>
  <dd><ul>
    <li><a href="https://bookwalker.jp/author/3/">あとき(著者)</a></li>
    <li><a href="https://bookwalker.jp/author/4/">Ｍａｇｐｉｅ(訳者)</a></li>
    <li><a href="https://bookwalker.jp/author/5/">ＩｃｅＦａｉｒｙ(訳者)</a></li>
  </ul></dd>
  <dt>レーベル</dt><dd><a href="https://bookwalker.jp/label/3/">アトキンソン</a></dd>
  <dt>出版社</dt><dd><a href="https://bookwalker.jp/company/3/">アトキンソン</a></dd>
  <dt>配信開始日</dt><dd>2023/7/14</dd>
</dl>
'''

# Quoted from https://bookwalker.jp/series/382866/list/ on 2026-08-05, trimmed. The 話・連載 store,
# where 293 of the admitted rows live. It states a chapter count, a label, a publisher and its own
# genre tags, and the only date on it is 更新: the day the LATEST chapter went up.
SERIAL_PAGE = '''
<title>【話・連載】0距離sentiment（ナンバーナイン） - 話・連載（マンガ） - BOOK☆WALKER</title>
<p class="o-ttsk-card__update-date">2022/11/4(金) <span class="nowrap">更新</span></p>
<h1 class="o-ttsk-card__title">0距離sentiment（ナンバーナイン）</h1>
<ul class="o-ttsk-card__author-list">
  <li><a href="https://bookwalker.jp/author/216431/?wa=1">やナい<span>（著）</span></a></li>
</ul>
<ul class="o-ttsk-card__tag-list">
  <li><a href="https://bookwalker.jp/tag/1491/?wa=1"><span>#</span>青年マンガ</a></li>
  <li><a href="https://bookwalker.jp/tag/2/?wa=1"><span>#</span>男性向け</a></li>
  <li><a href="https://bookwalker.jp/tag/14/?wa=1"><span>#</span>百合</a></li>
</ul>
<dl class="o-ttsk-card__data">
  <dt>レーベル</dt><dd><a href="https://bookwalker.jp/label/11249/?wa=1">百合コレ</a></dd>
  <dt>出版社</dt><dd><a href="https://bookwalker.jp/company/1419/?wa=1">ナンバーナイン</a></dd>
</dl>
<h2 class="p-episode__title a-ttsk-title--icon">全1話</h2>
'''

# Quoted from https://bookwalker.jp/de07b14596.../ on 2026-08-05, the imprint field as the shop
# renders it for a book that has none. 43 volumes of this capture were filed under ―― before this
# fixture existed.
NO_LABEL_VOLUME = '''
<script type="application/ld+json">
{"@context": "http://schema.org", "@type": "Product", "name": "2332"}
</script>
<dl class="t-c-detail-about-information__data">
  <dt>著者</dt><dd><ul><li><a href="https://bookwalker.jp/author/9/">真くん(著者)</a></li></ul></dd>
  <dt>レーベル</dt><dd>――</dd>
  <dt>出版社</dt><dd><a href="https://bookwalker.jp/company/9/">ライトリーズン</a></dd>
  <dt>カテゴリ</dt><dd><a href="https://bookwalker.jp/category/2/">マンガ</a></dd>
  <dt>配信開始日</dt><dd>2020/11/2</dd>
</dl>
'''

# What a fetch that went wrong looks like. It is a page, it is 200, it has a shell, and it states
# no book. This is the shape the floor exists to tell apart from a quiet day.
ERROR_SHELL = '''
<html><head><title>BOOK☆WALKER</title>
<script> window.BW_R18_BASE_URL = "https://r18.bookwalker.jp"; </script>
</head><body><div class="error">ただいまアクセスが集中しています</div></body></html>
'''


def main(s):
    # THE TWO DATES ARE DIFFERENT FACTS AND THE MODULE MUST NOT MERGE THEM.
    v = bv.volume(PRINT_VOLUME, "283e72a6-6281-4d78-898e-04faab9a4ade")
    # The VOLUME's own title, which is the one the shelf never showed. The shelf carried the series
    # title, and the volume number in this one is what tells a nine-volume run apart from a work.
    s.eq(v["title"], "＃ギャルとギャルの百合（１）", "the volume's own title, from the shop's payload")
    s.eq(v["uuid"], "283e72a6-6281-4d78-898e-04faab9a4ade", "carrying the id it was fetched by")
    s.eq(v["delivered"], "2025-12-26", "配信開始日 is the day the shop started selling the file")
    s.eq(v["printed"], "2025-12-31", "底本発行日 is the print edition's publication date")
    s.eq(v["publisher"], "小学館", "the publisher comes from the field, not from the imprint")
    s.eq(v["imprint"], "サンデーうぇぶりコミックス", "and the imprint from its own field")
    s.eq(v["series_id"], "568145",
         "the volume names its series, so a standalone row still joins to one")
    s.eq(v["authors"], ["イノウエ"], "the role suffix comes off the name")
    s.eq(v["category"], "マンガ", "and the shop's category is read rather than assumed")

    # ISBN IS NEVER STATED. The assertion is on the negative because the whole openBD and NDL route
    # depends on it, and a reader needs to see that the field was looked for and was not there.
    s.eq(v["isbn"], None, "no volume page on this site carries an ISBN")
    s.eq(bv.volume(DIGITAL_VOLUME)["isbn"], None, "not on a digital-first imprint either")

    # THE MAJORITY SHAPE. No 底本発行日 anywhere, so §6 has nothing to work with.
    d = bv.volume(DIGITAL_VOLUME)
    s.eq(d["printed"], None, "a digital-first imprint states no print date")
    s.eq(d["delivered"], "2025-10-24", "only the day the shop began selling it")
    s.eq(bv.first_publication([d]), (None, "no-print-date-stated"),
         "and a delivery date is NOT promoted into a first publication date")

    # THE DELIVERY DATE IS NOT EVEN A CONSISTENT BOUND, which is why it cannot stand in.
    st = bv.volume(STANDALONE_VOLUME)
    s.eq(st["printed"] < st["delivered"], True, "here the print edition came first")
    s.eq(v["printed"] > v["delivered"], True, "and here the file did; the order is not fixed")
    s.eq(st["series_id"], None, "a volume with no シリーズ row states no series")
    s.eq(st["series_title"], None, "and inventing one from the title is not done")

    s.eq(bv.volume(MANY_AUTHORS)["authors"], ["あとき", "Ｍａｇｐｉｅ", "ＩｃｅＦａｉｒｙ"],
         "each anchor is a person; flattening the dd would make six people one name")

    # FIRST PUBLICATION IS THE EARLIEST PRINT DATE ACROSS THE VOLUMES, and the series page lists
    # them out of order, so taking the first listed would date a work by whichever volume the shop
    # happened to put at the top.
    vols = [{"printed": "2023-04-01", "delivered": "2023-04-01"},
            {"printed": "2021-09-15", "delivered": "2021-09-20"},
            {"printed": None, "delivered": "2024-01-01"}]
    s.eq(bv.first_publication(vols), ("2021-09-15", "print-base-edition"),
         "the earliest print date, not the first row listed")
    s.eq(bv.first_publication([]), (None, "no-volumes-found"),
         "no volumes is not a work with no date; it is a work nobody read")
    s.eq(bv.first_publication([{"printed": None, "delivered": None}]),
         (None, "no-print-date-stated"),
         "and a volume read but undated is not the same state as a volume nobody read")

    # THE TWO SILENCES, WHICH IS WHAT §6 NOW HANGS ON. "The shop states no print date" and "there
    # is no print edition" are different sentences, and only the second explains itself. They are
    # told apart by what the row's own imprint does across the WHOLE capture, so the counter-case
    # is a print imprint that happens to be silent about one book: that must NOT be filed as
    # digital-only, because the imprint's own record contradicts it.
    digital = [{"imprint": "百合コレ", "publisher": "ナンバーナイン", "printed": None,
                "delivered": "2025-10-24"} for _ in range(6)]
    printy = [{"imprint": "百合姫コミックス", "publisher": "一迅社", "printed": "2021-11-01",
               "delivered": "2021-10-18"} for _ in range(5)]
    silent = [{"imprint": "百合姫コミックス", "publisher": "一迅社", "printed": None,
               "delivered": "2024-06-25"}]
    corpus = [{"store": "単行本", "first_publication_date": None, "volumes": digital},
              {"store": "単行本", "first_publication_date": "2021-11-01", "volumes": printy},
              {"store": "単行本", "first_publication_date": None, "volumes": silent}]
    stats = bv.imprint_print_dates(corpus)
    s.eq(stats["百合コレ"], (6, 0), "the imprint's record is counted over every volume of it read")
    s.eq(stats["百合姫コミックス"], (6, 5), "including the volumes belonging to other works")
    s.eq(bv.date_basis(corpus[0], stats)[0], "no-print-edition",
         "an imprint that dates none of its volumes is digital-only, and that explains the gap")
    s.eq(bv.date_basis(corpus[2], stats)[0], "no-print-date-stated",
         "THE COUNTER-CASE: a print imprint silent about one book is not thereby digital-only")
    s.eq("digital-only" in bv.date_basis(corpus[0], stats)[1].lower(), True,
         "and the row carries the sentence that explains itself")
    s.eq("unresolved" in bv.date_basis(corpus[2], stats)[1], True,
         "while the unexplained one says it is unresolved rather than implying an answer")
    s.eq(bv.date_basis(corpus[1], stats)[0], "print-base-edition", "a dated work states its date")

    # BELOW THE THRESHOLD NOBODY CAN TELL, and saying so beats guessing in either direction. Four
    # undated volumes from an unknown label is not evidence that the label prints nothing.
    thin = [{"store": "単行本", "first_publication_date": None,
             "volumes": [{"imprint": "ちいさなレーベル", "publisher": "某社", "printed": None,
                          "delivered": "2024-01-01"} for _ in range(4)]}]
    s.eq(bv.date_basis(thin[0], bv.imprint_print_dates(thin))[0], "print-edition-unknown",
         "too few volumes to tell a digital-only imprint from a silence")
    s.eq(bv.MIN_IMPRINT_VOLUMES, 5, "and the threshold is stated rather than left to a magic number")

    # THE LABEL FALLS BACK TO THE PUBLISHER WHERE THE SHOP RENDERS NO IMPRINT. 178 admitted rows
    # carry the shop's ―― for an absent label, and pooling them under one empty key would let
    # ナンバーナイン's record answer for 一迅社's.
    s.eq(bv.imprint_key({"imprint": None, "publisher": "ライトリーズン"}), "ライトリーズン",
         "no imprint, so the publisher is the grouping")
    s.eq(bv.imprint_key({"imprint": "百合コレ", "publisher": "ナンバーナイン"}), "百合コレ",
         "and the imprint wins where the shop states one")
    s.eq(bv.imprint_key({}), None, "with nothing to group by, nothing is grouped")

    # THE ―― BUG, WHICH SHIPPED HERE AFTER bookwalker_shelf.py HAD ALREADY PAID FOR IT. The shop
    # renders an absent label as ――, and this module stored it as an imprint on 43 volumes. That
    # was not merely an ugly field: `imprint_key` then pooled every unlabelled book in the capture
    # into one bucket, and 2 dated volumes out of 43 unrelated ones were enough to answer
    # `no-print-date-stated` for all of them.
    s.eq(bv.label("――"), None, "the shop's rendering of an absent label is not a label")
    s.eq(bv.label("ーー"), None, "nor the katakana-lengthener form of the same rendering")
    s.eq(bv.label("百合コレ"), "百合コレ", "and a real label survives, which is the counter-case")
    s.eq(bv.label("――ダッシュではじまる"), "――ダッシュではじまる",
         "a title-like label that merely STARTS with the dash is kept: the rule is the whole field")
    s.eq(bv.volume(NO_LABEL_VOLUME)["imprint"], None, "read off a page, the same answer")
    s.eq(bv.volume(NO_LABEL_VOLUME)["publisher"], "ライトリーズン", "the publisher is still there")
    s.eq(bv.imprint_key(bv.volume(NO_LABEL_VOLUME)), "ライトリーズン",
         "so an unlabelled book groups under its own publisher instead of under ――")

    # A CHAPTER SERIAL EXPLAINS ITSELF TOO, and never by way of its 更新 date.
    b, note = bv.date_basis({"store": "話・連載", "first_publication_date": None, "volumes": []},
                            stats)
    s.eq(b, "chapter-serial", "sold by the chapter, so there is no volume and no print edition")
    s.eq("更新" in note, True, "and the note names the date the shop does state, to rule it out")

    # ONE DEFINITION OF WHAT A TERM MEANS. build.py writes the same explanation onto a work record,
    # where the capture's imprint counts are not to hand, so the sentence has to come from here
    # rather than be typed out a second time.
    s.eq(note.startswith(bv.BASIS_NOTE["chapter-serial"]), True,
         "the note a capture writes opens with the term's own definition")
    s.eq(bv.date_basis(corpus[0], stats)[1].startswith(bv.BASIS_NOTE["no-print-edition"]), True,
         "and so does the one that then adds which imprint decided it")
    # THE VOCABULARY IS ONE TABLE NOW and both maps are keyed from it, so comparing them to each
    # other says nothing. What this capture can still usefully assert is that every term IT emits
    # is in that vocabulary and carries a sentence; whether the vocabulary is internally consistent
    # is `adapters/facts/dating/test_dating.py`, beside the table.
    for basis in ("print-base-edition", "chapter-serial", "no-print-edition",
                  "no-print-date-stated", "print-edition-unknown", "no-volumes-found"):
        s.check(basis in bv.BASIS_NOTE and bv.BASIS_NOTE[basis],
                f"the term this capture emits is defined: {basis}")
    s.eq("no-date-attested" in bv.BASIS_NOTE, True,
         "including the one no capture returns, which build.py needs for a source that said nothing")

    # THE COUNTER-CASE THAT WOULD HAVE CONDEMNED THE WHOLE SHELF. Every page on this site carries
    # BW_R18_BASE_URL in its head. A designation test run over the markup rather than over the
    # stated fields excludes all 2,438 rows and reports the shelf as pornography.
    s.eq("R18" in PRINT_VOLUME, True, "the R18 string really is on an ordinary volume page")
    s.eq(bv.exclusion(v), None, "and it excludes nothing, because the fields are what is tested")
    s.eq(bv.exclusion({"title": "ある百合の話【Ｒ－１８版】", "imprint": "百合コレ",
                       "publisher": "ナンバーナイン"}) is None, False,
         "a full-width R-18 marking in the volume's own title does exclude it")
    s.eq(bv.exclusion({"title": "ふつうの百合", "imprint": "秋水社ORIGINAL",
                       "publisher": "秋水社"}) is None, False,
         "and so does an adult imprint the series title never showed")
    s.eq(bv.exclusion({"title": "加筆修正版 百合の話", "imprint": "百合姫コミックス",
                       "publisher": "一迅社"}) is None, False,
         "修正版 is caught by the shelf's own marker list, which treats it as a lead")

    # THE 話・連載 STORE IS A DIFFERENT KIND OF THING, and reading it with the volume parser
    # returns nothing, which would file 293 admitted rows as "no volumes found". That is this
    # capture failing, reported as the shop having no volumes to state.
    import bookwalker_shelf as shelf  # noqa: PLC0415
    s.eq(shelf.parse_listing(SERIAL_PAGE), [],
         "the volume-store parser reads no rows off a 話・連載 page, which is the trap")
    w = bv.warensai(SERIAL_PAGE, "382866")
    s.eq(w["chapters"], 1, "the shop states how many chapters it sells")
    s.eq(w["imprint"], "百合コレ", "the shorter table is read by the same dt/dd reader")
    s.eq(w["publisher"], "ナンバーナイン", "publisher and label are both on it")
    s.eq(w["authors"], ["やナい"], "and the author, with the role in a span rather than in text")
    s.eq(w["updated"], "2022-11-04", "更新 is a date and is parsed as one")
    s.eq("百合" in w["genre"], True, "the work's own genre tags, which the shelf never showed")
    s.eq(bv.warensai(ERROR_SHELL), None,
         "and a page with no 話・連載 card is a failed fetch, not an empty serial")

    ser = bv.work_row({"shop_id": "382866", "url": "https://bookwalker.jp/series/382866/"},
                      [], None, True, w)
    s.eq(ser["first_publication_basis"], "chapter-serial-no-publication-date",
         "a chapter serial gets its own basis rather than being filed as a failed read")
    s.eq(ser["first_publication_date"], None, "更新 is the LATEST chapter and is not promoted")
    s.eq(ser["last_updated"], "2022-11-04", "it is kept, under a name that says what it is")
    s.eq(ser["store"], "話・連載", "and the row says which of the shop's two stores it came from")
    s.eq(bv.work_row({"shop_id": "1", "url": "https://bookwalker.jp/series/1/"}, [], None,
                     True)["first_publication_basis"], "no-volumes-found",
         "while a series page that yielded neither volumes nor a card stays a failure")

    # THE SERIAL PAGE CARRIES THE WORK'S OWN GENRE TAGS, so a designation can appear here that
    # nothing earlier in the pipeline could have seen.
    s.eq(bv.exclusion(w), None, "青年マンガ and 男性向け designate nothing")
    s.eq(bv.exclusion({"title": "ある話", "genre": "アダルトマンガ 百合"}) is None, False,
         "the shop filing it under its adult genre does")

    # A PAGE THAT STATES NO TITLE IS A FAILED FETCH AND NOT A WORK WITH NO NAME.
    s.eq(bv.volume(ERROR_SHELL), None, "an error shell yields no volume")
    s.eq(bv.volume(""), None, "and neither does nothing at all")
    s.eq(bv.info_table(ERROR_SHELL), {}, "there is no information table to read")

    # THE FLOOR IS A SHARE, because the failure to catch is a pass that stopped partway rather
    # than one that returned nothing. A loop dying after forty of nine thousand fetches comes back
    # with forty good volumes and reads as a slow day.
    s.eq(bv.healthy(100, 100)[0], True, "a pass where every page parsed is healthy")
    s.eq(bv.healthy(100, 60)[0], True, "and so is one where most did")
    s.eq(bv.healthy(100, 49)[0], False, "under half is the host, not the shelf")
    s.eq(bv.healthy(100, 0)[0], False, "and nothing at all is certainly the host")
    s.eq(bv.healthy(0, 0)[0], True, "a pass that asked nothing has nothing to be thin about")
    s.eq(bv.MIN_SAMPLE >= 20, True,
         "and the share is not consulted on a sample one timeout could tip")

    # THE CARRY-OVER, WHICH IS THE FAILURE THIS PROJECT HAS PAID FOR THREE TIMES. A second pass
    # writes the whole file from state that was loaded from the file, so a pass reaching one work
    # must leave the earlier ones exactly where they were rather than replacing them with its own.
    import tempfile  # noqa: PLC0415
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "volumes.yaml"
        first = {"retrieved": "2026-08-05", "admitted": 2438, "excluded": {}, "fetches": {},
                 "works": {"a": bv.work_row({"shop_id": "a", "url": "https://bookwalker.jp/dea/"},
                                            [bv.volume(PRINT_VOLUME, "a")]),
                           "b": bv.work_row({"shop_id": "b", "url": "https://bookwalker.jp/deb/"},
                                            [bv.volume(DIGITAL_VOLUME, "b")])}}
        bv._write(out, first)
        second = bv._read(out, 2438)
        s.eq(sorted(second["works"]), ["a", "b"], "a resumed pass starts from what is on disk")
        s.eq(second["works"]["a"]["first_publication_date"], "2025-12-31",
             "with the dates it already had, read back through YAML unchanged")
        s.eq(second["works"]["a"]["volumes"][0]["uuid"], "a",
             "and the volumes under them, which is what makes the row worth not refetching")
        second["works"]["c"] = bv.work_row({"shop_id": "c", "url": "https://bookwalker.jp/dec/"},
                                           [bv.volume(STANDALONE_VOLUME, "c")])
        bv._write(out, second)
        third = bv._read(out, 2438)
        s.eq(sorted(third["works"]), ["a", "b", "c"],
             "and the pass that added one work kept the two it never touched")
        s.eq(bv._read(pathlib.Path(tmp) / "absent.yaml", 2438)["works"], {},
             "while a file that is not there resumes from nothing rather than failing")

        # THE CHECKPOINT MUST NOT BE THE THING THAT LOSES THE FILE. `write_text` truncates and then
        # fills, so a kill inside the gap leaves a half file, `_read` returns blank, and the next
        # pass rebuilds from nothing. That is the failure the checkpoint exists to prevent, arriving
        # through the checkpoint. Caught by a poll that read the file mid-write during the real run.
        s.eq(out.exists(), True, "the file is there after a write")
        s.eq(sorted(p.name for p in pathlib.Path(tmp).iterdir() if p.suffix == ".partial"), [],
             "and no .partial is left behind, so the rename happened rather than a copy")
        bv._write(out, third)
        s.eq(len(bv._read(out, 2438)["works"]), 3,
             "a second write over a live file leaves it readable, not half-written")

        # A ROW WRITTEN BY AN OLDER VERSION IS RE-DERIVED, NOT TRUSTED. The summary above a row's
        # volumes is a function of those volumes, and a file holding rows from two versions with
        # nothing forcing them to agree is the shape this project has shipped seven bugs in.
        text = out.read_text().replace('first_publication_date: "2025-12-31"',
                                       'first_publication_date: "1999-01-01"')
        out.write_text(text)
        healed = bv._read(out, 2438)
        s.eq(healed["works"]["a"]["first_publication_date"], "2025-12-31",
             "a summary that disagrees with the volumes under it loses to the volumes")

        # A 話・連載 row survives the round trip as one, rather than turning into a work whose
        # volumes nobody could read.
        serial_state = dict(healed)
        serial_state["works"] = {"w": bv.work_row(
            {"shop_id": "w", "url": "https://bookwalker.jp/series/w/"}, [], None, True,
            bv.warensai(SERIAL_PAGE, "w"))}
        bv._write(out, serial_state)
        back = bv._read(out, 2438)["works"]["w"]
        s.eq(back["first_publication_basis"], "chapter-serial-no-publication-date",
             "the chapter serial is still a chapter serial after a resume")
        s.eq(back["chapters"], 1, "with the chapter count the shop stated")
        s.eq(back["last_updated"], "2022-11-04", "and its 更新 date, still not promoted to §6")

    # DATES ARE PARSED OR THEY ARE NOTHING. The shop does not zero-pad, and a date field holding
    # the string the shop rendered for a human sorts, prints and is not a date.
    s.eq(bv.iso_date("2020/11/2"), "2020-11-02", "an unpadded date is still a date")
    s.eq(bv.iso_date("2025/12/26"), "2025-12-26", "and a padded one is unchanged")
    s.eq(bv.iso_date("近日発売"), None, "a rendering for a human is not a date")
    s.eq(bv.iso_date("2020/13/2"), None, "and neither is an impossible one")
    s.eq(bv.iso_date(""), None, "nor an empty field")

    # THE ROW CARRIES ITS OWN PROVENANCE, so a reader can tell a dated work from an undated one
    # without recomputing anything.
    r = bv.work_row({"shop_id": "568145", "url": "https://bookwalker.jp/series/568145/"},
                    [bv.volume(PRINT_VOLUME), bv.volume(DIGITAL_VOLUME)],
                    completed="completed", series_read=True)
    s.eq(r["first_publication_date"], "2025-12-31", "the only print date on offer")
    s.eq(r["first_publication_venue"], "小学館", "the publisher of the volume that gave the date")

    # THE VENUE IS FOUND BY THE DATE, NOT BY POSITION. The row list is sorted on printed-or-
    # delivered, so a volume with no print date and an early delivery date sorts to the front, and
    # reading the publisher off the first row would credit the date to a different book.
    mixed = bv.work_row(
        {"shop_id": "z", "url": "https://bookwalker.jp/series/z/"},
        [{"printed": "2020-01-01", "delivered": "2020-02-01", "publisher": "一迅社",
          "title": "巻2", "imprint": "百合姫コミックス", "authors": ["某"]},
         {"printed": None, "delivered": "2019-01-01", "publisher": "ナンバーナイン",
          "title": "巻1", "imprint": "百合コレ", "authors": ["某"]}])
    s.eq(mixed["volumes"][0]["title"], "巻1", "the undated volume really does sort first")
    s.eq(mixed["first_publication_date"], "2020-01-01", "and the print date is still the answer")
    s.eq(mixed["first_publication_venue"], "一迅社",
         "credited to the publisher of the volume that stated it, not to the first row")
    s.eq(r["volumes_found"], 2, "both volumes are kept, dated or not")
    s.eq(r["dates_stated"], 1, "and the row says how many of them the shop dated")
    s.eq(r["isbns_stated"], 0, "which for ISBNs is always none")
    s.eq(bv.work_row({"shop_id": "1", "url": "https://bookwalker.jp/series/1/"}, [],
                     None, True)["first_publication_venue"], None,
         "a work nobody read has no venue either: absence is a state, not a default")

    # THE SERIES THE SHELF NEVER LINKED. A row captured at one volume has a first publication drawn
    # from a sample of one, so the question is which rows still have a series page to open.
    held = {
        "one-volume-of-a-series": {"series_read": False, "store": "単行本",
                                   "volumes": [{"uuid": "u1", "series_id": "555"}]},
        "already-read": {"series_read": True, "store": "単行本",
                         "volumes": [{"uuid": "u2", "series_id": "556"}]},
        "standalone": {"series_read": False, "store": "単行本",
                       "volumes": [{"uuid": "u3", "series_id": None}]},
        "chapter-serial": {"series_read": False, "store": "話・連載", "volumes": []},
        "read-at-three": {"series_read": False, "store": "単行本",
                          "volumes": [{"uuid": "u4", "series_id": "557"},
                                      {"uuid": "u5", "series_id": "557"},
                                      {"uuid": "u6", "series_id": "557"}]},
        "two-series-named": {"series_read": False, "store": "単行本",
                             "volumes": [{"uuid": "u7", "series_id": "558"},
                                         {"uuid": "u8", "series_id": "559"}]},
    }
    got = bv.series_to_follow(held)
    s.eq(("one-volume-of-a-series", "555") in got, True,
         "a row read at one volume that names a series is work outstanding")
    s.eq(("already-read", "556") in got, False, "a series already read is not asked for twice")
    s.eq(any(k == "standalone" for k, _ in got), False,
         "a volume naming no series is the shop answering, not the shop staying silent")
    s.eq(any(k == "chapter-serial" for k, _ in got), False,
         "and a 話・連載 work has no volume list to go and read")
    # THE COUNTER-CASE. Depth is not the test. A row read at three volumes whose series page nobody
    # opened may still be missing the fourth, and dropping it because it looks deep enough is how
    # the fault got here in the first place.
    s.eq(("read-at-three", "557") in got, True,
         "a row read at several volumes is still unread as a series")
    s.eq(any(k == "two-series-named" for k, _ in got), False,
         "volumes disagreeing about which series they belong to is a question, never a fetch")
    s.eq(got, sorted(got), "the list is ordered, so a capped pass resumes where it stopped")
    s.eq(len(got), 2, "and it holds only the rows with something left to read")

    # A SERIES LISTING IS PAGINATED AND THIS MODULE READ PAGE ONE. Six captured rows hold exactly
    # 60 volumes and nothing holds between 39 and 60, which is a page size showing through as a
    # property of the shelf. 付き合ってあげてもいいかな【単話】 was recorded at 60 against 133.
    s.eq(bv.SERIES_PAGE, 60, "the page size is stated rather than left as a magic number")
    s.eq(bv.series_list_url("188653"), "https://bookwalker.jp/series/188653/list/",
         "page one is the bare listing path, which is the URL the shelf capture stores")
    s.eq(bv.series_list_url("188653", 3),
         "https://bookwalker.jp/series/188653/list/?order=release&qser=188653&page=3",
         "and a later page copies the pager's own query rather than inventing one")
    s.eq(bv.another_page(60, 1), True, "a full page may not be the last one")
    s.eq(bv.another_page(59, 1), False, "a short page is the shop saying there is no more")
    s.eq(bv.another_page(0, 1), False, "and an empty one certainly is")
    s.eq(bv.another_page(60, bv.MAX_SERIES_PAGES), False,
         "with a stop, so a pager that never ends cannot spend a whole run on one series")

    # ROWS READ BEFORE THE PAGER EXISTED ARE ASKED AGAIN, and only those. `pages_read` is what
    # tells a row cut at 60 from a series that genuinely holds 60, so a row that has been read
    # whole is never asked a third time.
    cut = {"188653": {"series_read": True, "store": "単行本", "pages_read": None,
                      "url": "https://bookwalker.jp/series/188653/",
                      "volumes": [{"uuid": f"u{i}"} for i in range(60)]},
           "188654": {"series_read": True, "store": "単行本", "pages_read": 2,
                      "url": "https://bookwalker.jp/series/188654/",
                      "volumes": [{"uuid": f"v{i}"} for i in range(60)]},
           "188655": {"series_read": True, "store": "単行本", "pages_read": None,
                      "url": "https://bookwalker.jp/series/188655/",
                      "volumes": [{"uuid": f"w{i}"} for i in range(59)]}}
    again = dict(bv.series_to_follow(cut))
    s.eq(again.get("188653"), "188653", "a row sitting exactly on the page size is re-read")
    s.eq("188654" in again, False, "a row whose pages were counted is not re-read")
    s.eq("188655" in again, False, "and a row that never reached a page boundary was never cut")

    # DAMAGE BEFORE DISCOVERY. A truncated row states a first publication chosen from a truncated
    # list, so a capped pass repairs it before it goes looking for series nobody has opened.
    mixed = dict(cut)
    mixed["000000"] = {"series_read": False, "store": "単行本",
                       "url": "https://bookwalker.jp/de000/",
                       "volumes": [{"uuid": "x", "series_id": "999999"}]}
    s.eq(bv.series_to_follow(mixed)[0][0], "188653",
         "the row cut at a page boundary is asked first, before the one nobody has read")

    # THE READER STATES WHETHER IT AGREES WITH THE SHOP. Both faults this listing has had were
    # invisible: page one of a paginated listing and a whole listing look the same, and so do a
    # series with four volumes read as three and a series that has three. 全N件 is the one number
    # on the page that can contradict the list, so it is asked rather than the read being trusted.
    s.eq(bv.listing_short(["a", "b", "c"], 3), False, "three volumes read, three volumes stated")
    s.eq(bv.listing_short(["a", "b"], 3), True,
         "and a volume short is a listing to read again rather than a series with two volumes")
    s.eq(bv.listing_short([], 1), True,
         "the shape all 16 unreadable series had: one volume stated and none read")
    # A LISTING THAT STATES NOTHING IS NOT A LISTING THAT AGREES. Silence about the count is the
    # template having moved, which is how both earlier faults arrived (STANDING-INSTRUCTIONS §4).
    s.eq(bv.listing_short(["a"], None), True, "no stated count, no agreement")
    s.eq(bv.listing_short([], None), True, "and nothing read off a page that states nothing")
    # The counter-case for reading MORE than stated, which would be the pager serving a page
    # twice. It is a disagreement like any other and not a bonus.
    s.eq(bv.listing_short(["a", "b", "c", "d"], 3), True, "a volume too many disagrees too")

    # A ROW IS CONFIRMED BY CARRYING THE SHOP'S OWN COUNT, and every row captured before the
    # reader asked for it carries none. Those rows were read by a reader that dropped the last
    # row of a listing wherever the shop printed a related-series block underneath, and a listing
    # is sorted newest first, so the volume dropped is the one the date comes from.
    unconfirmed = {"1": {"series_read": True, "store": "単行本", "volumes_stated": None,
                         "url": "https://bookwalker.jp/series/1/",
                         "volumes": [{"uuid": "a"}, {"uuid": "b"}]},
                   "2": {"series_read": True, "store": "単行本", "volumes_stated": 2,
                         "url": "https://bookwalker.jp/series/2/",
                         "volumes": [{"uuid": "c"}, {"uuid": "d"}]},
                   "3": {"series_read": False, "store": "単行本",
                         "url": "https://bookwalker.jp/de3/",
                         "volumes": [{"uuid": "e", "series_id": "300"}]},
                   "4": {"series_read": True, "store": "話・連載", "volumes_stated": None,
                         "url": "https://bookwalker.jp/series/4/", "volumes": []}}
    conf = dict(bv.series_unconfirmed(unconfirmed))
    s.eq(conf.get("1"), "1", "a row read before the count was asked for is read again")
    s.eq("2" in conf, False, "and one that carries the shop's count is not")
    # THE COUNTER-CASE. An unread row is already `series_to_follow`'s, and counting it here would
    # make one request look like two pieces of work.
    s.eq("3" in conf, False, "a row nobody has read is the other list's, not this one's")
    s.eq("4" in conf, False, "and the 話・連載 store has no volume listing to confirm")

    # WHAT `work_row` PRODUCES IS WHAT `_write` WRITES, held against each other here because
    # keeping two lists in step by hand is exactly what failed. `volumes_stated` was added to the
    # row and not to the field list, so the marker saying a listing had been checked against the
    # shop's own count was dropped on the way to disk. The repair pass then re-read the same 1,879
    # rows every run, finished each one, and left the file saying none had been read. No fetch
    # failed and no volume was wrong; the number simply never moved (STANDING-INSTRUCTIONS §4).
    row = bv.work_row({"shop_id": "1", "url": "https://bookwalker.jp/series/1/"},
                      [{"uuid": "a", "printed": "2020-01", "publisher": "P",
                        "imprint": "I", "title": "T"}],
                      "completed", True, None, 1, 3)
    produced = set(row)
    s.eq(sorted(produced - set(bv.ROW_SCALARS) - set(bv.ROW_SHAPED)), [],
         "every field a row carries is one the file writes")
    s.eq(sorted((set(bv.ROW_SCALARS) | set(bv.ROW_SHAPED)) - produced), [],
         "and every field the file writes is one a row carries")

    # AND THE ROUND TRIP, WHICH IS THE ONE THAT WOULD HAVE CAUGHT BOTH. `_read` re-derives every
    # row through `work_row` on the way in, deliberately, so the summary is provably a function of
    # the volumes. What that cannot re-derive is the facts about the READING: whether the listing
    # was opened, how many pages of it were read, what the shop said the count was, and the
    # completion tag. `volumes_stated` was left out of the write list and then out of the read
    # call, and each time a pass confirmed hundreds of rows, wrote them correctly, and read them
    # back as though nothing had happened.
    with tempfile.TemporaryDirectory() as d:
        path = pathlib.Path(d) / "capture.yaml"
        bv._write(path, {"retrieved": "2026-08-06", "admitted": 1, "works": {"1": row},
                         "excluded": {}, "fetches": {}})
        back = bv._read(path, 1)["works"]["1"]
        for field in ("series_read", "pages_read", "volumes_stated", "completed"):
            s.eq(back.get(field), row.get(field),
                 f"{field} survives being written and read back")
        s.eq(back["first_publication_date"], "2020-01", "and the date is re-derived, not stored")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
