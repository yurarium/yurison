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

    # THE OUTCOME, which is the distinction the 503 policy turns on. Both of these carry no body,
    # and a caller that decided on `.text is None` would write both down as "the catalogue holds
    # nothing", which is how a rate-limited sweep concludes the National Diet Library is empty.
    held = net.Result("<html>", 200, "u", None, False, None, "h")
    s.eq(net.outcome(held), net.ANSWERED, "a body is an answer")
    s.eq(net.outcome(gone), net.ABSENT, "404 is the host saying there is nothing here")
    s.eq(net.outcome(flaky), net.REFUSED, "503 is the host declining to say")
    s.eq(net.outcome(net.Result(None, None, "u", None, False, "network: timed out", "h")),
         net.REFUSED, "a timeout is a refusal, not an absence")
    s.eq(net.outcome(net.Result(None, 403, "u", None, False, "HTTP 403", "h")),
         net.REFUSED, "403 is a refusal too, though waiting will not fix it")
    s.check(gone.text is None and flaky.text is None,
            "the two outcomes are indistinguishable by .text, which is why outcome() exists")

    # AND THE CALLER CANNOT READ ONE AS THE OTHER. body() gives back None for an absence and raises
    # for a refusal, so the mistake has to be made deliberately.
    s.eq(net.body(held), "<html>", "an answer comes back as itself")
    s.eq(net.body(gone), None, "an absence comes back as None, which a caller may record")
    s.raises(net.Refused, lambda: net.body(flaky), "a refusal raises instead of reading as a miss")
    s.check(net.is_refusal(flaky) and not net.is_refusal(gone),
            "is_refusal is the same test without the exception")

    # WHAT IS WORTH ASKING AGAIN. 404 must never be retried: it is an answer, and re-asking it
    # would spend the run's politeness budget on facts already established.
    s.check(503 in net.RETRY and 429 in net.RETRY, "the two rate-limit statuses are retried")
    s.check(not (net.PERMANENT & net.RETRY), "nothing is both an answer and worth re-asking")
    s.check(403 not in net.RETRY, "a refusal a person must fix is not retried")

    # BACKOFF IS PER HOST AND SHARED. THE BUG THIS PINS: with the wait held per request, eight
    # workers each meet the 503 separately, each sleep on their own, and the host keeps seeing the
    # same rate. The penalty sits beside the pause, so one worker's refusal lengthens the gap every
    # other worker must leave for that host.
    net._penalty.clear()
    first = net._penalise("slow.example")
    second = net._penalise("slow.example")
    s.eq(first, net.BACKOFF_MIN, "the first refusal costs BACKOFF_MIN")
    s.eq(second, net.BACKOFF_MIN * 2, "a second refusal doubles it")
    s.eq(net._penalty["quick.example"], 0.0, "and the other 26 hosts are not slowed")
    for _ in range(20):
        net._penalise("slow.example")
    s.eq(net._penalty["slow.example"], net.BACKOFF_MAX, "the backoff is capped")
    net._forgive("slow.example")
    s.eq(net._penalty["slow.example"], net.BACKOFF_MAX / 2,
         "an answer halves the penalty; clearing it would put the run back at the refused rate")
    net._penalty.clear()

    # A LONGER PAUSE IS ASKED FOR PER HOST. NDL wants seconds between requests and comic-days does
    # not, and raising the module-wide PAUSE for one of them slows all 27.
    net.PAUSES.clear()
    net.set_pause("ndlsearch.example", 3.0)
    s.eq(net.PAUSES["ndlsearch.example"], 3.0, "a host can ask for a longer gap")
    net.set_pause("ndlsearch.example", 0.1)
    s.eq(net.PAUSES["ndlsearch.example"], 3.0, "and the gap is never shortened")
    net.PAUSES.clear()

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

    # THE KEY IS INJECTIVE OVER THE WHOLE URL, and these two pin the ways it stopped being.
    #
    # A key built by substituting unsafe characters maps every kanji and kana to `_`, so every
    # Japanese title collapsed to ONE filename: `search-遠山えま百合集` read back `search-怪異部`'s
    # page, which reported as `no-record` and could not be told from a book NDL does not hold.
    s.ne(net.cache_key("https://ndl.example/search?keyword=遠山えま百合集"),
         net.cache_key("https://ndl.example/search?keyword=怪異部"),
         "two Japanese titles on one host get different cache keys")

    # And a key that keeps only the tail collides for two long URLs differing near the front, which
    # is every openBD batch: fifty ISBNs, and two batches ending in the same handful of books.
    tail = "," + ",".join(f"978400000{n:04d}" for n in range(40))
    s.ne(net.cache_key("https://api.example/get?isbn=9784000000001" + tail),
         net.cache_key("https://api.example/get?isbn=9784000000002" + tail),
         "two long queries differing only at the front get different cache keys")
    s.check(len(net.cache_key("https://a.jp/" + "x" * 4000)) < 200,
            "a key stays short enough to be a filename")

    # THE OLD KEYS ARE STILL DERIVABLE, because 62,000 pages sit under them and fetch renames what
    # it finds rather than re-fetching it.
    for legacy in net.LEGACY_KEYS:
        s.ne(legacy("https://a.jp/x"), net.cache_key("https://a.jp/x"),
             f"{legacy.__name__} differs from the current key, so adoption is doing something")

    # THE COPY FOUR ADAPTERS MADE. No host and no hash, and a Japanese URL is almost all
    # underscores under it, so what is left to tell two names apart is a handful of characters at
    # the end. The longest author name already lands on exactly 140 with the truncation eating the
    # constant prefix, which is the margin being gone.
    long_a = "https://comic.example/search?word=" + "%E7%99%BE%E5%90%88" * 20 + "A"
    long_b = "https://comic.example/search?word=" + "%E7%99%BE%E5%90%88" * 20 + "B"
    s.ne(net.cache_key(long_a), net.cache_key(long_b),
         "two long Japanese queries differing at the end get different keys")
    s.check(net._adapter_key(long_a) != net._adapter_key(long_b),
            "the old key survives this pair, which is why nothing is broken today")

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

    # ADOPTING A PAGE CACHED UNDER THE OLD KEY. Changing the key shape without this would have
    # thrown away every cache directory on the machine, which is 60,000 pages in capture-cache
    # alone, to gain an injectivity that only long query strings need.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        url = "https://a.jp/atom/series/1"
        (d / net._legacy_key(url)).write_text("the old page")
        got = net.fetch(url, d, max_age_days=365)
        s.eq(got.text, "the old page", "a page cached under the old key is still served")
        s.check(got.from_cache, "and is served from the cache, without a request")
        s.check((d / net.cache_key(url)).exists(),
                "adoption renames it, so the directory heals as it is read")
        s.check(not (d / net._legacy_key(url)).exists(), "and the old name is gone")

    # THE SHAPE THE ADAPTERS COPIED, which is where kmanga-cache's 1,700 pages live.
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        url = "https://comic.example/search?word=%E7%99%BE%E5%90%88"
        (d / net._adapter_key(url)).write_text("the adapter's page")
        s.eq(net.cached(url, d).text, "the adapter's page",
             "a page an adapter cached under its own key is still served")
        s.check((d / net.cache_key(url)).exists(), "and moves to the shared name")

    # A RECORDED FAILURE IS NOT A PAGE. Those adapters wrote `__ERROR__ ...` into the cache when a
    # host would not answer, so a brief outage left a file that every later run read back and
    # counted as the page not existing. Adopting one would carry it under a name this layer
    # promises never holds a refusal.
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        url = "https://shop.example/de0e8cf604"
        (d / net._adapter_key(url)).write_text("__ERROR__ HTTPError HTTP Error 503")
        s.eq(net.cached(url, d), None, "a cached failure is not served as a page")
        s.check(not (d / net._adapter_key(url)).exists(),
                "it is dropped, so the next run asks again instead of inheriting the outage")

    # Cache ages differ by kind. A chapter feed is the reason the run exists; a listing is not.
    s.check(net.AGE_FEED < net.AGE_LISTING,
            "a chapter feed is refetched sooner than a slow-changing listing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "net"))
