#!/usr/bin/env python3
"""platform_reading.py: the reading a platform prints under its own author's name."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import platform_reading as pr  # noqa: E402

COVERS = ["adapters/names/platform_reading.py"]

# Quoted from the served ヤンマガWeb author page for 宇藤あかり.
AUTHOR = '''<div class="author-meta">
  <div class="author-name">
    <h1 class="author-name-text">
      宇藤あかり
    </h1>
    <span class="mt-1 author-name-ruby">うどうあかり</span>
  </div>
  <div class="author-share"><div class="mod-icon-heart">2,212</div></div>
</div>'''

# Quoted from the served ガチ恋やめて series page, shortened. The footer links to the author index
# and to other authors' pages, which is why the index link must not be read as an author.
SERIES = '''<ul class="detailv2-outline-author">
  <li><a href="/comics/authors/ab98e06795e9503b3ce831cadf2a6048"><h2>宇藤あかり</h2></a></li>
</ul>
<div class="detailv2-recommend">
  <a href="/comics/authors/747240b865970738bd79d754e64b1a94">光彩</a>
  <a href="/comics/authors">マンガの作者一覧</a>
</div>'''


def main(s):
    s.eq(pr.name_and_reading(AUTHOR), ("宇藤あかり", "ウドウアカリ"),
         "the platform's own reading, as the katakana the store holds")

    # THE FIELD CAN BE EMPTY AND THAT IS A STATE. A page with a name and no ruby says the platform
    # has not filled it in, which is silence and not a reason to derive one.
    s.eq(pr.name_and_reading(AUTHOR.replace(
        '<span class="mt-1 author-name-ruby">うどうあかり</span>', "")), None,
        "a page with no ruby states no reading")
    s.eq(pr.name_and_reading("<html>a redesigned page</html>"), None,
         "and neither does a page that no longer has the shape")

    # THE RUBY SLOT HAS TO HOLD KANA. A platform putting a handle or a romanisation there would
    # otherwise be recorded as stating a Japanese reading.
    s.eq(pr.name_and_reading(AUTHOR.replace("うどうあかり", "udo_akari")), None,
         "a romanisation in the ruby slot is not a reading")

    s.eq(pr.author_links(SERIES),
         ["https://yanmaga.jp/comics/authors/ab98e06795e9503b3ce831cadf2a6048",
          "https://yanmaga.jp/comics/authors/747240b865970738bd79d754e64b1a94"],
         "every author page the work links to, and the index page is not one")
    s.eq(pr.author_links("<html>nothing here</html>"), [], "and none where there are none")

    e = pr.entry("宇藤あかり", "ウドウアカリ", "https://yanmaga.jp/comics/authors/ab98",
                 "ウトウ アカリ", "2026-08-06")
    s.eq(e["reading_basis"], "stated", "a platform stating its own author's reading is `stated`")
    s.eq(e["reading_source_kind"], "platform", "and the evidence is the platform")
    s.check("ウトウ アカリ" in e["reading_note"],
            "the note says what it replaced, because 宇藤 is ウドウ here and an analyser read ウトウ")
    s.check("agrees" in pr.entry("光彩", "コウサイ", "u", "コウサイ", "2026-08-06")["reading_note"],
            "and says so where it confirms the guess instead of replacing it")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, __file__))
