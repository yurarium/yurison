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


if __name__ == "__main__":
    sys.exit(testkit.run(main, "remaining.releases"))
