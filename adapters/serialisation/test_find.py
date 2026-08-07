#!/usr/bin/env python3
"""find.py: the two searches that ask where a printed book was serialised, and the join test.

The fixtures are cut from live pages read on 2026-08-07 and shortened to the markup the parsers
look at. Each one that pins a bug says which bug.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import find as F                                                               # noqa: E402
import testkit                                                                 # noqa: E402

# ニコニコ漫画's search for 運命のヤマダ. One result, which is the worked example of this pass:
# 芳文社's book, and 芳文社 runs COMIC FUZ, and the serialisation is here.
NICO_SEARCH = """
<div class="header__result-summary">
  <span class="header__result-summary__query-string">&#8220 運命のヤマダ &#8221</span> の検索結果：1
</div>
<div class="search_result">
  <div class="search_result__item">
    <div class="search_result__item__thumbnail">
      <a href="/comic/72312?track=keyword_search">
        <img alt="運命のヤマダダダダダダダダダダ" class="lazyload">
      </a>
    </div>
    <div class="search_result__item__info">
      <div class="search_result__item__info--title">
        <a href="/comic/72312?track=keyword_search">
          運命のヤマダダダダダダダダダダ
        </a>
      </div>
      <div class="search_result__item__info--author">
        おにぎりパクパク
      </div>
      <div class="search_result__item__info--others">
        <div class="search_result__item__info--others-last_updated-inner">
          <time datetime="2026-07-16T11:00:00+09:00">2026/07/16</time>
        </div>
      </div>
    </div>
  </div>
</div>
<div class="footer"><div class="footer__pager"></div></div>
"""

# The zero case. THE BUG THIS PINS: an empty result list and a fetch that returned an error page
# are the same value, and only one of them may be recorded as "this platform does not carry it".
NICO_EMPTY = """
<div class="header__result-summary">
  <span class="header__result-summary__query-string">&#8220 zzzz &#8221</span> の検索結果：0
</div>
<div class="search_result"></div>
<div class="footer"></div>
"""

# Web漫画アンテナ, the shape that is easy to miss: one match renders the WORK's page, not a list.
# THE BUG THIS PINS: a parser reading only `.entry` blocks reports nothing found for every
# exact-title hit, which is the entire population this pass searches for.
ANT_ONE = """
<div id="main">
<div class="comic-info">
  <div class="comic-thumb"><a href="https://manga.nicovideo.jp/comic/72312" target="_blank">
    <img alt="運命のヤマダダダダダダダダダダ"></a></div>
  <div class="comic-title">
    <h2><a href="https://manga.nicovideo.jp/comic/72312" target="_blank">運命のヤマダダダダダダダダダダ</a></h2>
  </div>
  <div class="comic-site"><a href="https://webcomics.jp/seiga">ニコニコ漫画</a></div>
  <div class="comic-author"> 作者: おにぎりパクパク</div>
</div>
</div>
"""

# The list shape, with a truncated visible title beside a whole one in the thumbnail's alt text.
ANT_MANY = """
<div class="entry" data-comic-no="90973">
  <div class="entry-thumb"><a href="https://comic-walker.com/detail/KC_004197_S" target="_blank">
    <img alt="安達としまむら"></a></div>
  <div class="entry-title ellipsis1"><a href="https://comic-walker.com/detail/KC_004197_S">安達としま...</a></div>
  <div class="entry-site"><a href="https://webcomics.jp/comic-walker">カドコミ</a></div>
</div>
<div class="entry" data-comic-no="92017">
  <div class="entry-thumb"><a href="https://manga.nicovideo.jp/comic/41839" target="_blank">
    <img alt="安達としまむら"></a></div>
  <div class="entry-title ellipsis1"><a href="https://manga.nicovideo.jp/comic/41839">安達としまむら</a></div>
  <div class="entry-site"><a href="https://webcomics.jp/seiga">ニコニコ漫画</a></div>
</div>
<div class="footer-navi"><a href="https://webcomics.jp/mylist">マイリスト</a></div>
"""

ANT_NONE = """
<div id="main"><div class="list"><div class="search-message">
「毒百合乙女童話」に関係する漫画が見つかりませんでした。<br>
</div></div></div>
"""


def main(s):
    # ── query forms ───────────────────────────────────────────────────────────────────────────
    s.eq(F.queries("運命のヤマダダダダダダダダダダ"), ["運命のヤマダダダダダダダダダダ"],
         "a plain title offers one query and not three copies of itself")
    s.eq(F.queries("シナモン = Cinnamon : 人外×人間百合アンソロジー")[1], "シナモン",
         "ISBD apparatus is dropped for the second attempt")
    s.eq(F.queries("付き合ってあげてもいいかな【単話】")[-1], "付き合ってあげてもいいかな",
         "a bracketed edition marker is dropped for the last attempt")
    s.check(all(q for q in F.queries("  ")) and F.queries("") == [],
            "an empty title produces no queries at all")

    # ── ニコニコ search ────────────────────────────────────────────────────────────────────────
    r = F.nico_results(NICO_SEARCH)
    s.eq(len(r), 1, "one result parsed from the ニコニコ search page")
    s.eq(r[0]["comic_id"], "72312", "the work id is read off the result link")
    s.eq(r[0]["title"], "運命のヤマダダダダダダダダダダ", "the title is read whole")
    s.eq(r[0]["author"], "おにぎりパクパク", "the author is read")
    s.eq(r[0]["updated"], "2026-07-16", "the update date is the machine-readable attribute")
    s.eq(r[0]["url"], "https://manga.nicovideo.jp/comic/72312",
         "the tracking query is dropped from the address we keep")

    s.eq(F.nico_results(NICO_EMPTY), [], "a search with no matches parses as no matches")
    s.check(F.nico_searched(NICO_EMPTY), "an empty result page is still an answer")
    s.check(not F.nico_searched("<html>an error page</html>"),
            "a page with no result summary is not an answer and must not count as an absence")

    # ── Web漫画アンテナ ───────────────────────────────────────────────────────────────────────
    one = F.antenna_results(ANT_ONE)
    s.check(one["answered"], "a single-match page counts as answered")
    s.eq(len(one["works"]), 1, "the single-match page yields one work")
    s.eq(one["works"][0]["url"], "https://manga.nicovideo.jp/comic/72312",
         "the platform address is read off the single-match page")
    s.eq(one["works"][0]["author"], "おにぎりパクパク",
         "the single-match page states an author the list form does not")
    s.eq(one["works"][0]["site"], "ニコニコ漫画", "the platform is named")

    many = F.antenna_results(ANT_MANY)
    s.eq(len(many["works"]), 2, "both entries in a list are read")
    s.eq(many["works"][0]["title"], "安達としまむら",
         "the whole title comes from the thumbnail alt, not the truncated visible one")
    s.eq(sorted(w["site"] for w in many["works"]), ["カドコミ", "ニコニコ漫画"],
         "each entry keeps its own platform")

    none = F.antenna_results(ANT_NONE)
    s.check(none["answered"] and none["works"] == [],
            "a stated absence is an answer with no works")
    s.check(not F.antenna_results("")["answered"],
            "an empty body is not an answer and must not be filed as an absence")

    # ── the join test ─────────────────────────────────────────────────────────────────────────
    v, shared = F.agrees("おにぎりパクパク", "芳文社", "おにぎりパクパク", ["おにぎりパクパク", "芳文社"])
    s.eq(v, "agreed", "a shared author agrees")
    s.eq(shared, ["おにぎりパクパク"], "the agreeing name is reported")

    v, _ = F.agrees("おにぎりパクパク", "芳文社", "", ["おにぎりパクパク", "芳文社"])
    s.eq(v, "agreed", "the copyright line settles a pairing whose author field is empty")

    v, _ = F.agrees("嵩乃朔", "芳文社", "", ["おにぎりパクパク", "芳文社"])
    s.eq(v, "agreed", "the publisher agrees even where no person does")

    # THE COUNTER-CASE. A platform sidebar advertising the author's other series is the failure the
    # previous pass measured three times, and it must be refused rather than left open.
    v, _ = F.agrees("水瀬るるう", "一迅社", "西沢5ミリ", ["西沢5ミリ", "KADOKAWA"])
    s.eq(v, "differs", "two named sides sharing nobody is a refusal")

    v, _ = F.agrees("", "講談社", "おにぎりパクパク", ["おにぎりパクパク", "芳文社"])
    s.eq(v, "unknown", "an anthology crediting nobody leaves the pair undecided")

    v, _ = F.agrees("嵩乃朔", "KADOKAWA", "", [])
    s.eq(v, "unknown", "a platform naming nobody leaves the pair undecided")

    # ── the lead filter ───────────────────────────────────────────────────────────────────────
    s.check(F.title_matches("運命のヤマダダダダダダダダダダ", "運命のヤマダダダダダダダダダダ"),
            "identical titles match")
    s.check(F.title_matches("付き合ってあげてもいいかな【単話】", "付き合ってあげてもいいかな"),
            "a bracketed marker does not stop a match")
    s.check(F.title_matches("スカーレット 1", "スカーレット"),
            "a trailing volume number does not stop a match")
    s.check(not F.title_matches("スカーレット", "スカーレットは知っている"),
            "a title that merely starts the same does not match")
    s.check(not F.title_matches("", "スカーレット"), "an empty title matches nothing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, pathlib.Path(__file__).name))
