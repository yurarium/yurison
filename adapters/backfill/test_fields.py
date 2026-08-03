#!/usr/bin/env python3
"""backfill/fields.py: filling gaps from a work's own page.

COVERS = ['adapters/backfill/fields.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import fields as bf


def main(s):
    s.eq(bf.host_of("https://Comic-Days.com/episode/1"), "comic-days.com",
         "the host is lower-cased, so comparisons hold")
    s.eq(bf.host_of("http://x.jp/a/b"), "x.jp", "http works the same as https")
    s.eq(bf.host_of("not a url"), "", "junk yields empty rather than raising")
    s.eq(bf.host_of(None), "", "None yields empty")

    # The feed carries author and access; free_only distinguishes the two, and the ABSENCE of a
    # free list must not silently mark everything purchase.
    page = '<html><link href="/atom/series/42"></html>'
    xml = ('<feed><entry><title>第1話</title><updated>2026-08-03T00:00:00Z</updated>'
           '<author><name>作者</name></author><link href="/episode/1"/></entry>'
           '<entry><title>第2話</title><updated>2026-08-10T00:00:00Z</updated>'
           '<link href="/episode/2"/></entry></feed>')

    def fake_get(url, limit=None):
        if "free_only" in url:
            return '<feed><link href="/episode/1"/></feed>'
        if "/atom/series/" in url:
            return xml
        return page

    real, bf.get = bf.get, fake_get
    try:
        author, rows = bf.gigaviewer_feed("https://x.jp/series/1", page)
        s.eq(author, "作者", "the author is taken from the first entry that names one")
        s.eq(len(rows), 2, "both entries are read")
        s.eq(rows[0]["updated"], "2026-08-03", "the timestamp is trimmed to a date")
        s.eq(rows[0].get("access_modes"), ["free"], "an episode in the free feed is free")
        s.eq(rows[1].get("access_modes"), ["purchase"], "one absent from it is not")

        # A page with no feed link yields nothing rather than a guess.
        s.eq(bf.gigaviewer_feed("https://x.jp/series/1", "<html>no link</html>"), (None, []),
             "no feed link means no rows")
    finally:
        bf.get = real


if __name__ == "__main__":
    sys.exit(testkit.run(main, "backfill.fields"))
