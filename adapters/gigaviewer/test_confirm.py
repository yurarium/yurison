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
    late = gc.episodes('<feed><entry><title>第1話</title><updated>2026-05-25T15:00:00Z</updated>'
                       '<link href="https://h/episode/1"/></entry></feed>')
    s.eq(late[0]["updated"], "2026-05-26", "and it is the date in Japan, a day on from 15:00Z")
    s.eq(eps[0]["url"], "https://x.jp/e/1", "the link is carried")
    s.eq(gc.episodes("<feed></feed>"), [], "an empty feed yields nothing")

    # EARLIER CONFIRMATIONS ARE ASKED AGAIN, and kept as they were when the asking fails.
    import tempfile
    from collections import defaultdict
    with tempfile.TemporaryDirectory() as d:
        pathlib.Path(d, "gv-confirmed.yaml").write_text(
            "works:\n  - work_title: Old\n    url: https://h/episode/42\n"
            "    discovered_via: {source: yurinavi, article: https://a/1}\n"
            "    chapters:\n      - {title: 第1話, updated: 2026-08-01, url: https://h/episode/42}\n")
        prior = gc.revisits(d, {"gv": {"host": "h"}, "other": {"host": "o"}})
    s.eq([(c["platform"], c["platform_code"], c["source"]) for c in prior], [("gv", "42", "yurinavi")],
         "an earlier confirmation becomes a candidate on its platform, provenance and all")
    got = gc.targets([{"platform": "gv", "platform_code": "42"}, {"platform": "gv", "platform_code": "7"}],
                     prior)
    s.eq(len(got), 2, "a work the queue still names is asked once")
    s.eq(len(gc.targets([], prior)), 1, "and one it no longer names is still asked")
    kept = gc.kept(defaultdict(list), prior)
    s.eq([(w["work_title"], w["episodes"][0]["title"]) for w in kept["gv"]], [("Old", "第1話")],
         "a refresh that failed keeps the earlier record and its chapters")
    fresh = defaultdict(list, {"gv": [{"url": "https://h/episode/42", "work_title": "New"}]})
    s.eq([w["work_title"] for w in gc.kept(fresh, prior)["gv"]], ["New"],
         "a refresh that worked replaces it")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "gigaviewer.confirm"))
