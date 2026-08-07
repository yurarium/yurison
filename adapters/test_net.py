#!/usr/bin/env python3
"""net.py: per-host pacing, recorded outcomes, and the move test.

No network here, which is the point: everything below is the logic that had to be separated from
the fetch before any of it could be tested at all.
"""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import net


def main(s):
    # A MOVE is a change of host or path, and nothing else. Comparing raw strings would report a
    # move every time a server added a trailing slash, and then "moved" would mean nothing.
    s.check(not net._differs("https://a.jp/x", "https://a.jp/x/"),
            "a trailing slash is not a move")
    s.check(not net._differs("http://a.jp/x", "https://a.jp/x"),
            "an upgrade to https is not a move")
    s.check(net._differs("https://a.jp/x", "https://b.jp/x"), "a different host is a move")
    s.check(net._differs("https://a.jp/x", "https://a.jp/y"), "a different path is a move")

    # PERMANENCE. The whole reason status codes are kept is that 404 and 503 mean different things:
    # one is evidence a work is gone, the other is evidence of nothing.
    gone = net.Result(None, 404, "u", None, False, "HTTP 404", "h")
    flaky = net.Result(None, 503, "u", None, False, "HTTP 503", "h")
    s.check(net.is_permanent(gone), "404 is permanent")
    s.check(not net.is_permanent(flaky), "503 is not permanent")
    s.check(not net.is_permanent(net.Result(None, None, "u", None, False, "network: x", "h")),
            "a network error is not permanent; it may be our end")

    # CACHE KEYS must be filesystem-safe and must not collide across different URLs.
    a, b = net.cache_key("https://a.jp/atom/series/1"), net.cache_key("https://a.jp/atom/series/2")
    s.ne(a, b, "different URLs get different cache keys")
    s.check(all(c.isalnum() or c == "_" for c in a), "a cache key is safe as a filename")

    # TWO HOSTS, ONE QUERY. THE BUG THIS PINS: the key was the last 120 characters of the
    # sanitised URL, so a long query string pushed the host off the front and two different sites
    # asked the same question shared a cache entry. Searching manga.nicovideo.jp and webcomics.jp
    # for one Japanese title returned ニコニコ's page for both, and the second site was recorded as
    # having answered when it had never been read. Any adapter caching several hosts in one
    # directory has this shape; editions/capture.py walks five engines into one.
    long_q = "%E5%87%9B%E3%81%A8%E3%81%97%E3%81%A6%E3%82%AB%E3%83%AC%E3%83%B3" * 3
    s.ne(net.cache_key(f"https://one.example/search?q={long_q}"),
         net.cache_key(f"https://two.example/search?q={long_q}"),
         "two hosts asked the same long question get different cache keys")

    # PACING is per host. This is the safety argument for running hosts concurrently, so it is
    # asserted rather than assumed: two requests to one host are separated by at least PAUSE.
    t0 = time.time()
    net._wait("one.example")
    net._wait("one.example")
    same = time.time() - t0
    s.check(same >= net.PAUSE * 0.9, f"two calls on one host waited {same:.2f}s, expected >= PAUSE")

    # ...and two DIFFERENT hosts do not wait for each other, which is where the time is saved.
    t0 = time.time()
    net._wait("alpha.example")
    net._wait("beta.example")
    across = time.time() - t0
    s.check(across < net.PAUSE * 0.5,
            f"two calls on different hosts took {across:.2f}s; they should not queue")

    # Cache ages differ by kind. A chapter feed is the reason the run exists; a listing is not.
    s.check(net.AGE_FEED < net.AGE_LISTING,
            "a chapter feed is refetched sooner than a slow-changing listing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "net"))
