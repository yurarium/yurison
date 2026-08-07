#!/usr/bin/env python3
"""workaddress.py: the work-level address a GigaViewer chapter page states for itself.

COVERS = ['adapters/gigaviewer/workaddress.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import workaddress as wa

# Trimmed from https://comic-days.com/episode/12207421983997344603, fetched 2026-08-07. The four
# series links a GigaViewer chapter page carries all name one id, which is why agreement is
# demanded rather than the first match taken.
CHAPTER = """<html><head>
<meta property="og:title" content="ファタールゲーム - ばったん / １４話　これはほとんど愛かもしれない（１） | コミックDAYS">
<link rel="alternate" type="application/atom+xml" title="Atom" href="https://comic-days.com/atom/series/2550912965643936966">
<link rel="alternate" type="application/rss+xml" title="RSS2.0" href="https://comic-days.com/rss/series/2550912965643936966">
<link rel="alternate" type="application/atom+xml" title="Atom (無料話のみ)" href="https://comic-days.com/atom/series/2550912965643936966?free_only=1">
<link rel="canonical" href="https://comic-days.com/episode/12207421983997344603" />
</head><body></body></html>"""

# https://ichicomi.com/series/2550912965923183647/first_episode, fetched 2026-08-07. HTTP 200,
# and the body is the platform's front page saying the page was not found.
SOFT_404 = """<html><head><meta property="og:title" content="一迅プラス"/>
</head><body><p>ページが見つかりません</p></body></html>"""

READER = """<html><head>
<meta property="og:title" content="雨夜の月 - くずしろ / 第１−１話 | コミックDAYS">
<link rel="alternate" type="application/atom+xml" href="https://comic-days.com/atom/series/3269632237268447047">
</head></html>"""


def main(s):
    s.eq(wa.series_id(CHAPTER), ("comic-days.com", "2550912965643936966"),
         "the chapter page states its own series, host and id together")

    # A page naming two series is not evidence about one work. Taking the first match would pick
    # by document order, which is the silent-wrong-answer shape this project keeps meeting.
    two = CHAPTER.replace("https://comic-days.com/rss/series/2550912965643936966",
                          "https://comic-days.com/rss/series/9999999999999999999")
    s.eq(wa.series_id(two), (None, None), "two different series ids on one page resolve to neither")

    # COUNTER-CASE. Not every page in the corpus is a GigaViewer chapter, and one that is not must
    # yield nothing rather than a guess. championcross.jp/episodes/... is the live example.
    s.eq(wa.series_id("<html><head><title>x</title></head></html>"), (None, None),
         "a page with no series link states no series")
    s.eq(wa.series_id(""), (None, None), "an empty page states no series")

    s.eq(wa.og_title(CHAPTER),
         "ファタールゲーム - ばったん / "
         "１４話　これはほとんど愛かも"
         "しれない（１） | コミックDAYS",
         "the og:title comes back whole")
    s.check(wa.og_title("<html></html>") is None, "a page with no og:title yields None")

    # THE THREE ORDERINGS THE PLATFORMS USE. Equality would fail on all of them.
    s.check(wa.names_work(wa.og_title(CHAPTER), "ファタールゲーム"),
            "work first, as コミックDAYS writes it")
    s.check(wa.names_work("第1話 / まとう君、ほころぶ"
                          "私 - 犬井あゆ | FEEL web",
                          "まとう君、ほころぶ私"),
            "chapter first, as FEEL web writes it")
    s.check(wa.names_work("[第1打]春雷卓球 - 平方昌宏 | "
                          "少年ジャンプ＋",
                          "春雷卓球"),
            "chapter bracketed in front, as 少年ジャンプ＋ writes it")

    # THE GUARD, AND WHAT IT IS FOR. A row whose url belongs to another work would otherwise
    # attach this work's identity to that work's address, which is the expensive direction.
    s.check(not wa.names_work(wa.og_title(CHAPTER), "大室家"),
            "a chapter page for another work does not name this one")
    # An empty title is contained in every string, so it would match everything.
    s.check(not wa.names_work(wa.og_title(CHAPTER), ""), "an empty work title names nothing")
    s.check(not wa.names_work(None, "ファタールゲーム"),
            "a missing og:title names nothing")

    s.eq(wa.feed_address("comic-days.com", "123"), "https://comic-days.com/atom/series/123",
         "the feed address")
    s.eq(wa.reader_address("comic-days.com", "123"),
         "https://comic-days.com/series/123/first_episode", "the reader address")

    s.check(wa.states_series(READER, "3269632237268447047"),
            "a reader page that names the series confirms the address")
    # THE SOFT 404. HTTP 200 with the front page. Status alone accepts this; naming the series
    # does not, and that is how 一迅プラス's missing route was found.
    s.check(not wa.states_series(SOFT_404, "2550912965923183647"),
            "a 200 that does not name the series confirms nothing")
    # COUNTER-CASE ON THE MATCH ITSELF: a longer id must not be read as containing a shorter one.
    s.check(not wa.states_series("<a href='/atom/series/32696322372684470479'>", "3269632237268447047"),
            "a series id that is a prefix of another does not confirm it")
    s.check(not wa.states_series(READER, None), "no series id confirms nothing")

    # resolve() end to end, with the fetch injected so this runs offline.
    pages = {"https://comic-days.com/episode/1": CHAPTER,
             "https://comic-days.com/series/2550912965643936966/first_episode": READER.replace(
                 "3269632237268447047", "2550912965643936966")}
    got = wa.resolve("https://comic-days.com/episode/1",
                     "ファタールゲーム", pages.get)
    s.eq(got["state"], "resolved", "a chapter page that names its series resolves")
    s.eq(got["feed"], "https://comic-days.com/atom/series/2550912965643936966",
         "the feed address is built from the id the page stated")
    s.eq(got["reader"], "https://comic-days.com/series/2550912965643936966/first_episode",
         "the reader address is kept when the page it returns names the same series")

    # The same row on a platform serving the soft 404: the feed address still stands, the reader
    # address is dropped rather than published as though it worked.
    soft = dict(pages)
    soft["https://comic-days.com/series/2550912965643936966/first_episode"] = SOFT_404
    got = wa.resolve("https://comic-days.com/episode/1",
                     "ファタールゲーム", soft.get)
    s.eq(got["state"], "resolved", "the feed address does not depend on the reader address")
    s.check(got["reader"] is None, "a reader address that does not resolve is dropped")

    s.eq(wa.resolve("https://x.jp/e/1", "w", lambda u: None)["state"], "unread",
         "a page that could not be fetched is unread, not absent")
    s.eq(wa.resolve("https://x.jp/e/1", "w", lambda u: "<html></html>")["state"], "no-series",
         "a page with no series link states no series")
    s.eq(wa.resolve("https://comic-days.com/episode/1", "大室家",
                    pages.get)["state"], "title-differs",
         "a page naming another work is reported rather than attached")

    return s


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).stem))
