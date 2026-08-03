#!/usr/bin/env python3
"""reachable/check.py: deciding whether a work is still there.

COVERS = ['adapters/reachable/check.py']

Every branch here is a claim about a third party's site, so a false "gone" removes a work that
exists. The empty-feed branch matters most: GigaViewer keeps serving a withdrawn work's page, so
the page looking fine proves nothing.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import check as rc

BIG = "<html>" + ("x" * 3000) + "</html>"


def main(s):
    def with_fetch(fn, url="https://x.jp/series/1"):
        real, rc.fetch = rc.fetch, fn
        try:
            return rc.probe(url)
        finally:
            rc.fetch = real

    state, code, why = with_fetch(lambda u, limit=None: ("", 404))
    s.eq(state, "gone", "404 means gone")
    s.eq(why, "status", "and says the status said so")
    s.eq(with_fetch(lambda u, limit=None: ("", 410))[0], "gone", "410 means gone")

    # No body at all is NOT gone. It may be us being refused, and treating that as a withdrawal
    # would delete works whenever a publisher blocked the fetcher.
    s.eq(with_fetch(lambda u, limit=None: (None, 403))[0], "blocked",
         "no response is blocked rather than gone")

    # A stub page is a redirect target or an error page dressed as a 200.
    s.eq(with_fetch(lambda u, limit=None: ("<html>tiny</html>", 200))[0], "gone",
         "a page too small to be a work is gone")

    s.eq(with_fetch(lambda u, limit=None: (BIG.replace("xxx", "公開終了", 1), 200))[0], "withdrawn",
         "a page saying 公開終了 is withdrawn")

    # A full page with no feed and no notice is present. This is the case that must NOT be
    # over-read, or every unusual layout becomes a withdrawal.
    s.eq(with_fetch(lambda u, limit=None: (BIG, 200))[0], "present",
         "an ordinary full page is present")

    # THE EMPTY FEED. The page still serves, so nothing above fires; the platform states the
    # absence only by returning a feed with no entries.
    def feed_empty(u, limit=None):
        if "/atom/series/" in u:
            return ("<feed></feed>", 200)
        return (BIG + '<link href="/atom/series/99">', 200)
    s.eq(with_fetch(feed_empty)[0], "withdrawn", "an empty series feed is the platform saying so")

    def feed_full(u, limit=None):
        if "/atom/series/" in u:
            return ("<feed><entry><title>第1話</title></entry></feed>", 200)
        return (BIG + '<link href="/atom/series/99">', 200)
    s.eq(with_fetch(feed_full)[0], "present", "a feed with entries means the work is there")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "reachable.check"))
