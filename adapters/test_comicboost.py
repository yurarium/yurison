#!/usr/bin/env python3
"""comicboost.py: reading a chapter list a reconnaissance pass called unreadable."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import comicboost as cb  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/comicboost.py"]

# Quoted from the served 百合にはさまる男は死ねばいい!? page, shortened to two rows.
PAGE = '''<meta property="og:title" content="百合にはさまる男は死ねばいい！？｜comicブースト｜さらに面白く">
<div class="book-product-list-item-meta-wrapper">
  <h4 class="title">第7話</h4>
  <div class="left"><div class="free"><span>無料</span></div></div>
  <div class="right"><p class="update-date">2023/05/19</p></div>
</div>
<div class="book-product-list-item-meta-wrapper">
  <h4 class="title">第6話</h4>
  <div class="left"></div>
  <div class="right"><p class="update-date">2023/05/19</p></div>
</div>'''


def main(s):
    s.eq(cb.work_title(PAGE), "百合にはさまる男は死ねばいい！？",
         "the work's name, without the platform's furniture after it")
    s.eq(cb.work_title("<html>nothing</html>"), "", "and nothing where the page says nothing")

    ch = cb.chapters(PAGE)
    s.eq([c["title"] for c in ch], ["第7話", "第6話"], "each chapter in the order listed")
    s.eq(ch[0]["updated"], "2023-05-19", "with its own date, normalised")
    s.eq(ch[0]["access_modes"], ["free"], "and the access state stated beside it")
    s.eq(ch[1]["access_modes"], ["purchase"], "which differs per row")

    # THE PAIRING IS THE POINT. Reading titles and dates as two lists and zipping them pairs a
    # title with somebody else's date the moment one row lacks a date, and every row still looks
    # plausible afterwards.
    gap = PAGE.replace('<div class="right"><p class="update-date">2023/05/19</p></div>\n</div>\n'
                       '<div class="book-product-list-item-meta-wrapper">\n  <h4 class="title">'
                       '第6話</h4>', '<h4 class="title">第6話</h4>', 1)
    got = cb.chapters(gap)
    s.check(all(c["updated"] == "2023-05-19" for c in got),
            "a row with no date of its own does not borrow the next row's")

    s.eq(cb.chapters(""), [], "no page, no chapters")
    s.eq(cb.chapters("<h4 class=\"title\">第1話</h4>"), [],
         "and a title with no date is not a dated chapter")

    # THE TARGETS FOLLOW THE CANDIDATES. 葵とおねーちゃん was announced and listed on 2026-10-13 at
    # a comicブースト address with a stray `?=s`, and the only list this read was kept by hand.
    spec = {"works": [{"title": "白妙様、秘密ですよ", "url": "https://comic-boost.com/content/01650001"}]}
    cands = [{"title": "葵とおねーちゃん", "urls": ["https://comic-boost.com/content/01780001",
                                                 "https://comic-boost.com/content/01780001?=s"]},
             {"title": "白妙様、秘密ですよ", "urls": ["https://comic-boost.com/content/01650001/"]},
             {"title": "他所", "urls": ["https://comic-walker.com/detail/KC_1_S"]}]
    s.eq(cb.targets(spec, cands),
         [{"title": "白妙様、秘密ですよ", "url": "https://comic-boost.com/content/01650001"},
          {"title": "葵とおねーちゃん", "url": "https://comic-boost.com/content/01780001"}],
         "the hand-kept list, then each candidate's series page once, and nothing from another site")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "comic-boost.yaml"
        f.write_text("works:\n  - work_title: a\n    url: https://comic-boost.com/content/1\n"
                     "  - work_title: b\n    url: https://comic-boost.com/content/2\n",
                     encoding="utf-8")
        s.eq([w["work_title"] for w in cb.carry_over(f, ["https://comic-boost.com/content/2"])],
             ["a"], "a work this run did not reach is written back rather than dropped")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
