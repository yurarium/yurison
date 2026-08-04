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


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
