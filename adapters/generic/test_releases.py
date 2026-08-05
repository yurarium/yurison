#!/usr/bin/env python3
"""generic/releases.py: chapter labels dug out of scraped text runs.

COVERS = ['adapters/generic/releases.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as gr

# Quoted from https://manga-park.com/title/91107, two chapters, with the thumbnail and tracking
# attributes dropped. The like count and the comment count are <span>s of their own in info-footer,
# and the chapter's name has an element of its own in info-body. Flattening the <li> ran the three
# together, which is how 男装メイドは尽くしたい's chapters were stored as '3話① 26 8'.
MANGA_PARK = """
<ul class="chapter-list">
  <li data-url="/chapter/737190" data-chapter-id="737190" data-chapter-name="4">
    <div class="chapter-container pointer">
      <div class="info">
        <div class="info-body">
          <p class="chapterTitle txtColorSubjectSP" data-truncation="2">3話①</p>
        </div>
        <div class="info-footer">
          <div class="flex"><div class="right"><span class="txtColorSubjectSP">26</span></div></div>
          <div class="flex"><div class="right"><span class="txtColorSubjectSP">8</span></div></div>
          <div class="date"><span class="txtColorSubjectSP">2025/6/19</span></div>
        </div>
      </div>
    </div>
  </li>
  <li data-url="/chapter/742001" data-chapter-id="742001" data-chapter-name="7">
    <div class="chapter-container pointer">
      <div class="info">
        <div class="info-body">
          <p class="chapterTitle txtColorSubjectSP" data-truncation="2">4話②＜完＞</p>
        </div>
        <div class="info-footer">
          <div class="flex"><div class="right"><span class="txtColorSubjectSP">23</span></div></div>
          <div class="flex"><div class="right"><span class="txtColorSubjectSP">24</span></div></div>
          <div class="date"><span class="txtColorSubjectSP">2025/7/10</span></div>
        </div>
      </div>
    </div>
  </li>
</ul>
"""

# Quoted from https://firecross.jp/ebook/series/541. Two things go wrong on a flat reading: the
# counts again, and the <li> that try_markup splits on sits INSIDE the episode rather than round
# it, so a block begins in the middle of the previous episode and its 無料 button arrives as the
# next chapter's prefix. The name has an element of its own, so neither survives reading the node.
FIRECROSS = """
<div class="ebookSeries_episodeList">
  <div js-shop-item class="shop-item--episode" id="ep12220" data-id="12220">
    <div class="shop-item-info">
      <span class="shop-item-info-name">第0話</span>
      <div class="shop-item-info-meta">
        <span class="shop-item-info-release">公開：2024/4/15</span>
      </div>
      <div class="shop-item-info-footer">
        <div class="commentCountSet">
          <p class="countValue"><span>32</span></p>
          <p class="countValue"><span>1</span></p>
        </div>
        <ul class="shop-item-btnset"><li class="shop-item-btn">無料</li></ul>
      </div>
    </div>
  </div>
  <div js-shop-item class="shop-item--episode" id="ep12221" data-id="12221">
    <div class="shop-item-info">
      <span class="shop-item-info-name">第1話</span>
      <div class="shop-item-info-meta">
        <span class="shop-item-info-release">公開：2024/4/29</span>
      </div>
      <div class="shop-item-info-footer">
        <div class="commentCountSet">
          <p class="countValue"><span>33</span></p>
          <p class="countValue"><span>0</span></p>
        </div>
        <ul class="shop-item-btnset"><li class="shop-item-btn">50</li></ul>
      </div>
    </div>
  </div>
</div>
"""

# The counter-case, in the two shapes the fix has to survive. A chapter whose name ENDS in a number
# is ordinary. pixivコミック numbers its chapters EPISODE 01 to EPISODE 30, and any rule that
# removes trailing digits from an assembled title destroys it. The number is cut as a text NODE
# instead, which cannot touch this one: 'EPISODE 30' is one node and the count is another.
# The first item names its title element, the second does not, so both paths are covered.
TRAILING_NUMBER = """
<ul>
  <li><div class="episode-name">EPISODE 30</div>
      <span class="like">12</span><time>2026/01/05</time></li>
  <li><div class="ep-body">EPISODE 29</div>
      <span class="like">7</span><time>2025/12/22</time></li>
</ul>
"""


def titles(html):
    return [e["title"] for e in gr.episodes(html, "markup")]


def main(s):
    # Leading and trailing space goes; internal runs are left, because a chapter label's own
    # spacing is content and the caller collapses it where it needs to.
    s.eq(gr.clean("  a  b  "), "a  b", "surrounding whitespace is stripped, internal is kept")
    s.eq(gr.clean("ＹＵＲＩ"), "YURI", "width is normalised")
    s.eq(gr.clean(None), "", "None cleans to empty rather than raising")
    # The invisible characters that broke comparisons elsewhere in this codebase.
    s.eq(gr.clean("百​合"), "百合", "a zero-width space is removed")

    # A row with no date is not a release, whatever else it carries. §6: a guessed date is worse
    # than none, because it reorders the feed and nothing downstream can tell it was invented.
    rows = gr.episodes("", "markup")
    s.eq(rows, [], "an empty page yields nothing")

    # CHAPTERISH is what decides whether a scraped string is a chapter label at all. It has to
    # accept the numbering styles publishers actually use, or a platform comes back with a
    # fraction of its chapters.
    s.check(gr.CHAPTERISH.search("第1話"), "第N話 is a chapter label")
    s.check(gr.CHAPTERISH.search("第12話"), "so is a multi-digit one")
    s.check(gr.CHAPTERISH.search("１２話"), "and a full-width one")
    s.check(not gr.CHAPTERISH.search("お知らせ"), "an announcement is not a chapter label")

    # THE BUG. 193 stored chapter names ended in the like and comment counts printed beside them,
    # and a reader saw those as part of the chapter's name.
    mp = titles(MANGA_PARK)
    s.eq(mp, ["3話①", "4話②＜完＞"], "マンガPark's chapter names come back without the counts")
    for t in mp:
        s.check("26" not in t and " 8" not in t, f"no counter is left in {t!r}")

    fc = titles(FIRECROSS)
    s.eq(fc, ["第0話", "第1話"], "ファイアCROSS's names come back without counts, price or date")
    for t in fc:
        s.check("無料" not in t and "公開" not in t,
                f"the neighbouring episode's button is not part of {t!r}")

    # THE COUNTER-CASE, which is why the counts are cut as nodes rather than as trailing digits.
    s.eq(titles(TRAILING_NUMBER), ["EPISODE 30", "EPISODE 29"],
         "a chapter whose name ends in a number keeps it, however the page names its title element")

    # A title element the page did NOT name is left to the flat reading, which is what keeps
    # ダ・ヴィンチニュース's headings whole. Its chapter number sits in a badge and its title in an
    # <h2> wrapped round an <a>, so there is no single node to read and the run of text is the
    # best available answer.
    ddnavi = ('<li class="archives-list__item"><a href="/article/d1385572/a/">'
              '<span class="badge-number">第1回</span></a><div class="archives-list__info">'
              '<h2 class="archives-list__title"><a href="/article/d1385572/a/">'
              'ギャルが乙女ゲームの“モブキャラ”に転生！</a></h2>'
              '<p class="archives-list__date">2024/9/7</p></div></li>')
    s.check(any("ギャル" in t for t in titles(ddnavi)),
            "a heading the page did not mark as one node keeps its subtitle")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "generic.releases"))
