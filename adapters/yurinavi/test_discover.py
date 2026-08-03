#!/usr/bin/env python3
"""yurinavi/discover.py: reading work titles out of editorial headlines.

COVERS = ['adapters/yurinavi/discover.py']

百合ナビ is Tier C: it says a work exists and where, and nothing it says becomes a record. What it
must get right is WHICH strings are titles, because a headline read wrongly enters a work that
does not exist into the discovery queue.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import discover as d


def main(s):
    # WordPress appends the site name, which is not part of the headline.
    s.eq(d.headline_of("<title>「百合の花」が完結 | 百合ナビ</title>"), "「百合の花」が完結",
         "the site name is removed")
    s.eq(d.headline_of("<title>ニュース｜百合ナビ</title>"), "ニュース",
         "a full-width bar separates it too")
    s.eq(d.headline_of("<title>ただの見出し</title>"), "ただの見出し",
         "a headline without the suffix is unchanged")
    s.eq(d.headline_of("<html>no title</html>"), "", "a page without a title yields empty")

    # Titles are QUOTED in Japanese headlines. Taking the whole headline would enter sentences as
    # works, which is the failure this guards against.
    s.eq(d.titles_in("「百合の花」と『薔薇の棘』が完結"), ["百合の花", "薔薇の棘"],
         "both bracket styles are read")
    s.eq(d.titles_in("完結のお知らせ"), [], "an unquoted headline names no work")
    s.eq(d.titles_in("「あ」が完結"), [], "a one-character quote is too short to be a title")

    # A 60-character ceiling stops a quoted sentence being taken as a title.
    long_quote = "「" + ("あ" * 80) + "」"
    s.eq(d.titles_in(long_quote), [], "a quote too long to be a title is not one")

    # Signals decide what KIND of event a headline reports. Five are tracked; 完結 is not among
    # them, because a completion is read from the platform rather than from editorial coverage.
    s.eq(d.signal_of("「百合の花」新連載スタート"), "new-serial", "a new serialisation is a signal")
    s.eq(d.signal_of("「百合の花」読み切り掲載"), "oneshot", "a one-shot is a signal")
    s.eq(d.signal_of("単行本第1巻が発売"), "new-volume", "a volume release is a signal")
    s.eq(d.signal_of("「百合の花」アニメ化決定"), "adaptation", "an adaptation is a signal")
    s.check(d.signal_of("「百合の花」が完結") is None,
            "a completion is not a discovery signal; the platform states that")
    s.check(d.signal_of("なんの変哲もない文章") is None, "an ordinary headline carries none")

    # Commercial headlines are ignored outright, and the ignore list wins over a signal that would
    # otherwise match: a sale on a new volume is still a sale.
    s.check(d.signal_of("単行本発売記念セール開催") is None, "a sale is ignored despite 発売")
    s.check(d.signal_of("新連載記念キャンペーン") is None, "a campaign is ignored despite 新連載")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "yurinavi.discover"))
