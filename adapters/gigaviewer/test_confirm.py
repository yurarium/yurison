#!/usr/bin/env python3
"""gigaviewer/confirm.py: which half of a page title is the work.

COVERS = ['adapters/gigaviewer/confirm.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import confirm as gc


def main(s):
    # THE ORDER IS NOT FIXED across installs, which is the whole point. Taking whichever half comes
    # first recorded an episode title as the work: なとりとしずは entered the feed as
    # "第1話 もう一度". The half carrying " - " is the work and author, wherever it falls.
    w, a = gc.identity("<title>大室家 - なもり / 第1話</title>")
    s.eq(w, "大室家", "work first: the work is taken from the named half")
    s.eq(a, "なもり", "and so is the author")

    w, a = gc.identity("<title>第1話 もう一度 / なとりとしずは - 鮎川あお</title>")
    s.eq(w, "なとりとしずは", "work LAST: the episode half is not mistaken for the work")
    s.eq(a, "鮎川あお", "and the author still comes from the named half")

    # The site name after a bar is furniture.
    w, _ = gc.identity("<title>大室家 - なもり / 第1話 | 一迅プラス</title>")
    s.eq(w, "大室家", "the site name is dropped")

    # With no " - " anywhere there is no author, and guessing one would invent a person.
    w, a = gc.identity("<title>単独のタイトル</title>")
    s.eq(w, "単独のタイトル", "a lone title is the work")
    s.check(a is None, "and no author is invented")

    s.eq(gc.identity("<html>no title</html>"), (None, None), "a page with no title yields nothing")

    xml = ('<feed><entry><title>第1話</title><updated>2026-08-03T00:00:00Z</updated>'
           '<link href="https://x.jp/e/1"/></entry>'
           '<entry><title>第2話</title></entry></feed>')
    eps = gc.episodes(xml)
    s.eq(len(eps), 1, "an entry without a date is skipped, not half-recorded")
    s.eq(eps[0]["updated"], "2026-08-03", "the timestamp is trimmed to a date")
    s.eq(eps[0]["url"], "https://x.jp/e/1", "the link is carried")
    s.eq(gc.episodes("<feed></feed>"), [], "an empty feed yields nothing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "gigaviewer.confirm"))
