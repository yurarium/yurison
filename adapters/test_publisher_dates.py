#!/usr/bin/env python3
"""publisher_dates.py: reading a publisher's own date, and refusing a page about another book."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import publisher_dates as pd  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/publisher_dates.py"]

# The 既刊詳細 block of https://data.ichijinsha.co.jp/detail/75807004 as served on 2026-08-07, cut
# to what the parser reads. The Vue template underneath it is kept, because its `release_date`
# placeholder is the thing a looser date pattern would eventually find instead.
ICHIJINSHA = """
<h2>少女美学</h2>
<ul id="authors"><li><a class="author" href="/author/CHI-RAN">CHI-RAN</a></li></ul>
<p>ISBN 9784758070041 ／ A5版 定価：943円（税込）　発売日 2006-09-16</p>
<div class="books" v-if="books"><ul><li v-for="b in books">
<p class="additional" v-cloak>{{ b.release_date }}</p>
</li></ul></div>
"""

# The same page for the ISBN cmoa states against える・えるシスター 1巻. 一迅社 says that number is
# volume 7 of a horror series, and this is the pair the title guard exists for.
SHIRASUNAMURA = """
<h2>白砂村 (7)</h2>
<p>ISBN 9784758062862 ／ B6版 定価：607円（税込）　発売日 2011-11-26</p>
"""

# 幻冬舎コミックス, https://www.gentosha-comics.net/book/b519294.html, cut to the 書誌情報. The
# navigation above it on the real page carries no date, and the related-titles list below it does.
GENTOSHA = """
<title>ユリ熊嵐 (1) - 幻冬舎コミックス</title>
<dl><dt>レーベル</dt><dd>バーズコミックス</dd>
<dt>ISBN</dt><dd>9784344832565</dd>
<dt>発売日</dt><dd>2014年11月21日</dd>
<dt>定価</dt><dd>693円</dd></dl>
<div class="related"><span>2020年09月07日</span></div>
"""

# 双葉社 serves its bibliography as JSON from book-api.futabasha.co.jp; the page itself renders
# client-side and states nothing a parser can read.
FUTABASHA = ('{"book_details":{"book_informations":{"isbn_code":"9784575834772",'
             '"book_name":"GIRL\\u00d7GIRL\\u00d7BOY\\u2015\\u4e59\\u5973\\u306e\\u7948\\u308a\\u2015",'
             '"release_dt":"2008-04-28","start_dt":"2013-08-08"}}}')


def main(s):
    # ── THE ORDINARY CASE ────────────────────────────────────────────────────────────────────
    got = pd.ichijinsha_book(ICHIJINSHA)
    s.eq(got["date"], "2006-09-16", "the publisher's own 発売日 is the date")
    s.eq(got["isbn"], "9784758070041", "read from the same match as the date, not searched apart")
    s.eq(got["title"], "少女美学", "and the book the page is about")
    s.eq(pd.accept(got, "9784758070041", "少女美学", False), ("2006-09-16", None),
         "ISBN and title both agree, so the date stands")

    s.eq(pd.ichijinsha_url("9784758070041"), "https://data.ichijinsha.co.jp/detail/75807004",
         "the page id is the eight digits between the 978-4 prefix and the check digit")
    s.eq(pd.ichijinsha_url("9784825100114"), "https://data.ichijinsha.co.jp/detail/82510011",
         "including 一迅社's newer 4-8251 prefix")

    # ── THE GUARD THAT EARNED ITS PLACE ──────────────────────────────────────────────────────
    # cmoa states 9784758062862 for える・えるシスター 1巻 and 一迅社 says that ISBN is 白砂村 (7).
    # Without the title check this row would have been filed with a horror series' publication
    # date and would have read as answered. Everything about the page is otherwise in order: it
    # parses, it states the ISBN asked for, and it states a date.
    wrong = pd.ichijinsha_book(SHIRASUNAMURA)
    s.eq(wrong["isbn"], "9784758062862", "the page does state the ISBN that was asked about")
    s.eq(wrong["date"], "2011-11-26", "and it does state a date")
    s.eq(pd.accept(wrong, "9784758062862", "える・えるシスター", False)[0], None,
         "and the date is still refused, because the page is about a different book")
    s.eq(pd.accept(wrong, "9784758062862", "える・えるシスター", True)[0], None,
         "pinning the URL does not waive the title check either")

    # THE COUNTER-CASE, so the guard is not tightened into rejecting real pairs. 一迅社 writes
    # レンアイ♥女子課 where the shop shelves レンアイ・女子課, and the publisher writes the volume
    # number into a title the shop states bare.
    s.check(pd.same_work("レンアイ♥女子課 第一巻", "レンアイ・女子課"),
            "a decorative mark is presentation and never a different work")
    s.check(pd.same_work("犬神さんと猫山さん (1)巻", "犬神さんと猫山さん"),
            "nor is the volume number the publisher prints and the shop does not")
    s.check(not pd.same_work("白砂村 (7)", "える・えるシスター"),
            "and two different works are still two different works")
    s.check(not pd.same_work(None, "少女美学"), "a page whose title did not parse agrees with nothing")

    # A page reached FROM the ISBN has to state that ISBN back, because a site that answers every
    # unknown path with its newest book is indistinguishable from one that answered.
    s.eq(pd.accept(got, "9784758070065", "少女美学", False)[0], None,
         "a derived URL that returns a different ISBN is refused")
    # A URL resolved by hand from the title was not found through the ISBN, so it may legitimately
    # carry a different one: that is how the refuted row above gets its date from the right page.
    s.eq(pd.accept(got, "9784758062862", "少女美学", True), ("2006-09-16", None),
         "a pinned URL is confirmed by the title instead")
    s.eq(pd.accept(None, "9784758070041", "少女美学", False)[0], None, "no record, no date")
    s.eq(pd.accept({"isbn": "9784758070041", "title": "少女美学", "date": None},
                   "9784758070041", "少女美学", False)[0], None,
         "a page that states the book and no date yields no date")

    # ── THE OTHER PUBLISHERS ─────────────────────────────────────────────────────────────────
    g = pd.html_book(GENTOSHA)
    s.eq(g["date"], "2014-11-21", "発売日 is read off its label, not taken as the first date seen")
    s.eq(g["isbn"], "9784344832565", "with the ISBN the page states beside it")
    s.eq(pd.accept(g, "9784344832565", "ユリ熊嵐", True), ("2014-11-21", None),
         "and the page is about the book the shop's row is about")

    f = pd.futabasha_book(FUTABASHA)
    s.eq(f["date"], "2008-04-28", "双葉社 states its release date as a field, so it is read as one")
    s.eq(f["isbn"], "9784575834772", "against the ISBN in the same record")
    s.eq(pd.futabasha_book("<html>not json</html>"), None,
         "a page served where JSON was expected yields nothing rather than raising")
    s.eq(pd.futabasha_url("9784575834772"),
         "https://book-api.futabasha.co.jp/book_details?jdcn_code=97845758347720000000&media=1",
         "the id 双葉社's own sitemap uses is the ISBN and seven zeros")

    # ── WHICH ROWS THIS PASS IS FOR ──────────────────────────────────────────────────────────
    # Read off the stored basis, so a row another pass dates drops out without a second list of it.
    doc = {"works": {
        "1": {"first_publication_basis": "isbn-stated-not-catalogued", "publisher": "一迅社",
              "shelf_title": "少女美学",
              "volumes": [{"volume": 1, "isbn": "9784758070041"}, {"volume": 2}]},
        "2": {"first_publication_basis": "madb-tankobon", "publisher": "一迅社",
              "shelf_title": "初恋姉妹", "volumes": [{"volume": 1, "isbn": "9784758070027"}]},
        "3": {"first_publication_basis": "isbn-stated-not-catalogued", "publisher": "一迅社",
              "shelf_title": "no isbn", "volumes": [{"volume": 1}]}}}
    s.eq(pd.targets(doc), [("9784758070041", "一迅社", "1", "少女美学")],
         "a dated row is not asked about again, and a row with no ISBN has nothing to ask with")

    s.eq(pd.page_for("9784832240179", "芳文社"), (None, None),
         "a book whose publisher has no page for it falls through to the aggregator")
    s.eq(pd.page_for("9784758062862", "一迅社")[0],
         "https://data.ichijinsha.co.jp/detail/75806119",
         "the refuted row is pinned to the page for the work rather than for the shop's ISBN")

    # The publisher's ISBN is recorded beside the shop's rather than replacing it, because the file
    # is a capture of what the shop says and the disagreement is the part worth keeping.
    refuted = {"works": {"72289": {"volumes": [
        {"volume": 1, "isbn": "9784758062862", "printed_source": "https://x/"}]}}}
    pd.note_refuted(refuted)
    v = refuted["works"]["72289"]["volumes"][0]
    s.eq(v["isbn"], "9784758062862", "the shop's ISBN is left exactly as the shop stated it")
    s.eq(v["publisher_isbn"], "9784758061193", "and the publisher's own number sits beside it")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
