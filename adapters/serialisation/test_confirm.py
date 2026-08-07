#!/usr/bin/env python3
"""confirm.py: what a platform page says about itself, and whether that agrees with a book.

Fixtures are cut from pages read on 2026-08-07: ニコニコ漫画, カドコミ, コミックDAYS (GigaViewer)
and ビッコミ (comici). Each one that pins a bug says which bug.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import confirm as C                                                            # noqa: E402
import testkit                                                                 # noqa: E402

# GigaViewer writes `series - author / episode | site` into one element.
DAYS = ('<title>14gの逃避行 - 七福あくび / 【コミックDAYS読み切り】14gの逃避行 | 月マガ基地</title>'
        '<meta property="og:title" content="14gの逃避行 - 七福あくび / 読み切り | 月マガ基地">'
        '<a class="author" href="https://www.hatena.ne.jp/comicdays_unei/">運営</a>')

# comici writes `series - author,author | site`.
BIGCOMICS = ('<title>酒と鬼は二合まで - 羽柴実里,zinbei | ビッコミ（ビッグコミックス）</title>'
             '<meta property="og:title" content="酒と鬼は二合まで">')

# ニコニコ: the copyright line is the only place a Japanese platform routinely names the publisher.
NICO = ('<title>運命のヤマダダダダダダダダダダ / おにぎりパクパク おすすめ無料漫画 - ニコニコ漫画</title>'
        '<small class="copyright">(C)おにぎりパクパク/芳文社</small>')

# カドコミ's work object. Shortened to the two keys read.
KADOKOMI = ('<script id="__NEXT_DATA__" type="application/json">'
            '{"props":{"pageProps":{"dehydratedState":{"queries":[{"state":{"data":'
            '{"work":{"title":"安達としまむら","authors":['
            '{"name":"柚原もけ","role":"漫画"},{"name":"入間人間","role":"原作"}]}}}}]}}}}'
            '</script><title>安達としまむら｜カドコミ</title>')

# THE COUNTER-CASE THIS WHOLE FILE EXISTS FOR. A platform page carries the site's catalogue in its
# navigation, so a document-wide search for a name agrees with everything. Only the fields that
# describe THIS page may be read.
SIDEBAR = ('<title>ストロベリークォーツ - 甘城なつき | くらげバンチ</title>'
           '<aside class="recommend"><a href="/series/x">けがわとなかみ / 水瀬るるう</a></aside>')


def main(s):
    # ── what a page says about itself ─────────────────────────────────────────────────────────
    d = C.describes_page(DAYS)
    s.check(any("七福あくび" in x for x in d["lines"]),
            "the author in a GigaViewer title is kept")
    s.check(not any("月マガ基地" in x for x in d["lines"]),
            "the site brand after the bar is dropped, so it cannot agree with a publisher")
    s.eq(d["credits"], [], "a title element is a line and never a credit, however it reads")

    s.check(any("zinbei" in x for x in C.describes_page(BIGCOMICS)["lines"]),
            "a comici title names both creators")

    side = C.describes_page(SIDEBAR)
    s.check(not any("水瀬るるう" in x for x in side["lines"] + side["credits"]),
            "a recommendation in the sidebar is not something the page says about itself")
    s.check(not any("けがわとなかみ" in x for x in side["lines"] + side["credits"]),
            "and neither is the other series it advertises")

    s.eq(C.describes_page(""), {"lines": [], "credits": []},
         "an empty document describes nothing")
    s.eq(C.describes_page("<html><body>no title, no meta</body></html>"),
         {"lines": [], "credits": []}, "and neither does one with no descriptive field")

    jl = C.describes_page('<script type="application/ld+json">'
                          '{"@type":"Book","author":{"name":"雪尾ゆき"}}</script>')
    s.eq(jl["credits"], ["雪尾ゆき"], "a JSON-LD author is read, and as a credit")
    s.eq(C.describes_page('<script type="application/ld+json">{not json}</script>'),
         {"lines": [], "credits": []},
         "and malformed JSON-LD is skipped rather than raised on")

    # ── platform readers ──────────────────────────────────────────────────────────────────────
    n = C.nico_says(NICO)
    s.check("芳文社" in n["credits"], "ニコニコ's copyright line is a credit")
    s.check("おにぎりパクパク" in n["credits"], "and so is the author it states")

    k = C.kadokomi_says(KADOKOMI)
    s.eq(sorted(k["credits"]), ["入間人間", "柚原もけ"], "カドコミ's work object names every credit")
    s.eq(k["lines"], ["安達としまむら"], "and the work's own title is the line")
    s.check(C.kadokomi_says("<title>某作品｜カドコミ</title>")["lines"],
            "a カドコミ page whose work object is gone falls back to its title rather than to "
            "silence")

    s.check("芳文社" in C.says_of("https://manga.nicovideo.jp/comic/72312", NICO)["credits"],
            "a ニコニコ address is routed to ニコニコ's reader")
    s.check("柚原もけ" in C.says_of("https://comic-walker.com/detail/KC_004197_S",
                                    KADOKOMI)["credits"],
            "and a カドコミ address to カドコミ's")

    # ── the verdict ───────────────────────────────────────────────────────────────────────────
    v, ev = C.verdict("おにぎりパクパク", "芳文社", n)
    s.eq(v, "agreed", "a creator named on both sides agrees")
    s.check("おにぎりパクパク" in ev, "and the evidence says which name")

    v, ev = C.verdict("別の人", "芳文社", n)
    s.eq(v, "agreed", "the copyright line settles it on the publisher where no person agrees")
    s.check("芳文社" in ev, "and says so")

    v, _ = C.verdict("水瀬るるう", "一迅社", n)
    s.eq(v, "differs", "a page whose credit names somebody else is a refusal")

    # THE CORRECTION THIS PARSER MOST NEEDED. A title element carrying only the work title, or the
    # work title and the site's name, contradicts nothing. THE BUG THIS PINS: 87 leads were refused
    # because `フツーの恋って何？ - 路草` was read as naming a rival author, and 路草 is the site.
    v, ev = C.verdict("いくたはな", "太田出版", C.describes_page("<title>フツーの恋って何？ - 路草</title>"))
    s.eq(v, "undecided", "a page stating no author refuses nothing")
    s.check("no author" in ev, "and says that is why")

    v, _ = C.verdict("", "講談社", n)
    s.eq(v, "undecided", "an anthology crediting nobody cannot be joined on a name")

    v, _ = C.verdict("七福あくび", "講談社", {"lines": [], "credits": []})
    s.eq(v, "undecided", "a page that could not be read decides nothing")

    # `ほか` CLOSES A CREDIT. 奏 : 青春バンド百合アンソロジー is credited `浅見百合子 ほか` and the
    # ニコニコ page names 浅見百合子 first of nine. THE BUG THIS PINS: the name being matched with
    # was "浅見百合子 ほか" and nobody is called that, so the join was refused.
    v, _ = C.verdict("浅見百合子 ほか", "講談社",
                     {"lines": ["奏 青春バンド百合アンソロジー"],
                      "credits": ["浅見百合子(漫画) 飴野(漫画) ヨルモ(漫画)"]})
    s.eq(v, "agreed", "a credit closed with ほか still names its first contributor")

    # A ONE-LETTER OR TWO-LETTER NAME CANNOT BE MATCHED INSIDE A LONGER STRING. `ED` credits
    # リリウム・テラリウム and appears inside half the Latin on any page, so it has to be a whole
    # part of a line. THE BUG THIS PINS: substring matching agreed with every page it was shown.
    v, _ = C.verdict("ED", "一迅社", {"lines": ["FRIENDS - 誰か"], "credits": ["誰か"]})
    s.eq(v, "differs", "a two-letter name buried in another word does not agree")
    v, _ = C.verdict("ED", "一迅社", {"lines": ["リリウム・テラリウム - ED"], "credits": []})
    s.eq(v, "agreed", "while the same name standing on its own does")

    # ── COMIC FUZ, where the title element says nothing and the payload says everything ───────
    # THE BUG THIS PINS: reading only the title element filed all 20 芳文社 leads as undecided,
    # because FUZ prints the work's name there and puts the author in __NEXT_DATA__.
    FUZ = ('<title>スローループ｜COMIC FUZ</title>'
           '<script id="__NEXT_DATA__" type="application/json">'
           '{"props":{"pageProps":{"manga":{"mangaName":"スローループ"},'
           '"authorships":[{"author":{"authorName":"うちのまいこ"}}],'
           '"tags":[{"name":"金曜日"},{"name":"まんがタイムきららフォワード"},'
           '{"name":"まんがタイムKRコミックス"}]}}}</script>')
    f = C.fuz_says(FUZ)
    s.check("うちのまいこ" in f["credits"], "FUZ's author is read out of its payload")
    s.check("まんがタイムKRコミックス" in f["credits"], "and so is the imprint it tags")
    s.eq(f["lines"], ["スローループ"], "the work's own name is the line")
    s.check(C.fuz_says("<title>某作品｜COMIC FUZ</title>")["lines"],
            "a FUZ page with no payload falls back to its title rather than to silence")
    s.check("うちのまいこ" in C.says_of("https://comic-fuz.com/manga/1541", FUZ)["credits"],
            "a FUZ address is routed to FUZ's reader")

    v, ev = C.verdict("うちのまいこ", "芳文社", f)
    s.eq(v, "agreed", "the author agrees")

    # THE IMPRINT IS THE THIRD FIELD RUNBOOK §11 ACCEPTS, and here it is the one that answers: the
    # bibliography prints まんがタイムKRコミックス on the volume and FUZ tags the series with it.
    v, ev = C.verdict("別の人", "芳文社", f, "まんがタイムKRコミックス")
    s.eq(v, "agreed", "and where no person does, the imprint can")
    s.check("imprint" in ev, "and the evidence says which field settled it")

    v, _ = C.verdict("別の人", "芳文社", f, "IDコミックス")
    s.eq(v, "differs", "an imprint that is not the one tagged settles nothing")

    # ── leads ─────────────────────────────────────────────────────────────────────────────────
    doc = {"asked": [{"id": "w1", "title": "T",
                      "nico_hits": [{"url": "https://manga.nicovideo.jp/comic/1"}],
                      "antenna_hits": [
                          {"url": "https://manga.nicovideo.jp/comic/1", "site": "ニコニコ漫画"},
                          {"url": "https://comic-walker.com/detail/X", "site": "カドコミ"}]}]}
    got = C.leads(doc)
    s.eq(len(got), 2, "one address found by both searches is one lead, not two")
    s.eq(sorted(u for _w, u, _p in got),
         ["https://comic-walker.com/detail/X", "https://manga.nicovideo.jp/comic/1"],
         "and both distinct addresses are kept")
    s.eq(C.leads({}), [], "a search file with nothing in it produces no leads")

    # A 試し読み host is not a serialisation (DEFINITIONS §6), and build.py already refuses to
    # count its instalments as chapters. A lead there would leave an anchor with no row behind it.
    promo = {"asked": [{"id": "w1", "title": "T", "antenna_hits": [
        {"url": "https://ddnavi.com/x", "site": "ダ・ヴィンチニュース"},
        {"url": "https://comic-walker.com/detail/X", "site": "カドコミ"}]}]}
    s.eq([u for _w, u, _p in C.leads(promo, ("ddnavi.com",))],
         ["https://comic-walker.com/detail/X"], "a promotional host is not a lead")
    s.check("ddnavi.com" in C.promo_hosts(),
            "and the list of them is build.py's, so the two cannot disagree")


if __name__ == "__main__":
    sys.exit(testkit.run(main, pathlib.Path(__file__).name))
