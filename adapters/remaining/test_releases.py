#!/usr/bin/env python3
"""remaining/releases.py: the fallback routes, and the label-trimming they all need.

COVERS = ['adapters/remaining/releases.py']
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as rm


def main(s):
    # The HOST comes from the page fetched, not from the link. Some installs write the feed link
    # relative, and requiring the absolute form made the route decline silently on コミックゼノン
    # and 一迅プラス, whose feed links had been checked by hand.
    called = []

    def fake_get(url, *a, **k):
        called.append(url)
        if "free_only" in url:
            return "<feed></feed>"
        return ('<feed><entry><title>第1話</title><updated>2026-08-03T00:00:00Z</updated>'
                '<link href="/episode/1"/><author><name>作者</name></author></entry></feed>')

    real, rm.get = rm.get, fake_get
    try:
        rows = rm.from_giga('<a href="/atom/series/42">feed</a>', "https://comic-zenon.com/x")
        s.check(any("comic-zenon.com" in u for u in called),
                "a RELATIVE feed link still resolves, using the page's own host")
        s.check(rows, "and the route returns rows rather than declining")

        # A page with no feed link at all yields nothing rather than raising.
        called.clear()
        s.eq(rm.from_giga("<html>no feed</html>", "https://x.jp/y"), [],
             "no feed link means no rows")

        # A page URL that is not a URL cannot supply a host, so the route declines.
        s.eq(rm.from_giga('<a href="/atom/series/42">f</a>', "not a url"), [],
             "an unusable page URL declines rather than guessing a host")
    finally:
        rm.get = real

    # from_generic must reject anything without a date, and trim the label furniture that rendered
    # pages put next to the chapter: "第1話 … 更新日:" was arriving as the title.
    page = ('<script type="application/ld+json">'
            + json.dumps([{"name": "第1話 はじまり 更新日:", "datePublished": "2026-08-03"}])
            + "</script>")
    rows = rm.from_generic(page)
    for r in rows:
        s.check("更新日" not in r["title"], "the date's own label is trimmed off the chapter name")
    s.eq(rm.from_generic("<html></html>"), [], "a page with nothing extractable yields nothing")

    # Where the page names the element holding the chapter's title, try_markup marks the row exact
    # and this route must take it whole rather than cutting it down. The like and comment counts
    # beside a chapter used to end up in its name: 'Episode.3 -1 0 0' on フラコミlike!.
    listed = ('<ul><li><div class="episode-name">Episode.3 -1</div>'
              '<span>14</span><span>0</span><time>2025/12/26</time></li>'
              '<li><div class="episode-name">Episode.3 -2</div>'
              '<span>0</span><span>0</span><time>2026/01/09</time></li></ul>')
    got = [r["title"] for r in rm.from_generic(listed)]
    s.eq(got, ["Episode.3 -1", "Episode.3 -2"],
         "a named title element is taken whole, counts and all trailing furniture left behind")

    # A HOST WITH ITS OWN ADAPTER IS NOT RE-READ HERE, and this adapter asks one list rather than
    # keeping a copy. Its copy said comic.pixiv.net alone, so ニコニコ's meta line reached the
    # build as a chapter called `3話 無料` for お姉さんは女子小学生に興味があります。 beside 竹コミ's
    # 64 real ones. The counter-case is the whole reason this adapter exists: a GigaViewer host is
    # still its to try, because the platform pass is what skipped the work.
    s.check(rm.dedicated.covers("https://manga.nicovideo.jp/comic/31194"),
            "a host with a dedicated adapter is recognised through the shared list")
    s.check(rm.dedicated.covers("https://comic-zenon.com/episode/12207421983944323839") is None,
            "and a GigaViewer host is not, or the residue this adapter reaches goes unread")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "remaining.releases"))
