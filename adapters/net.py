#!/usr/bin/env python3
"""One fetch, shared: per-host politeness, recorded outcomes, and a cache with two ages.

NAMED net.py, NOT http.py. Adapters put `adapters/` on sys.path, and a module called http.py
shadows the stdlib `http` package for every one of them, so importing urllib.request fails with
"No module named 'http.client'". Written down because http.py is the obvious name and the failure
is remote from the cause.

WHY THIS EXISTS. Every adapter grew its own `fetch()`, and they agreed on nothing that mattered:

  POLITENESS WAS GLOBAL, NOT PER HOST. Each adapter slept PAUSE seconds after every request while
  walking a serial list that visits 27 different hosts. Sleeping 1.2 s after ichicomi before
  requesting comic-days buys neither host anything, and it is why Stage A spent 43 minutes of a
  38-minute stage asleep. Politeness is owed to a SERVER, so the pause is enforced per host here
  and hosts run concurrently. No host sees traffic any faster than it did before.

  OUTCOMES WERE THROWN AWAY. Callers caught (HTTPError, URLError, OSError) and kept
  `type(e).__name__`. So a 404 and a 503 were the same event, which makes "this work is gone"
  impossible to establish and "try again tomorrow" impossible to distinguish from it. Status codes
  are kept now, and a permanent status is marked as such.

  REDIRECTS WERE INVISIBLE. urlopen follows them silently and nobody compared the final URL to the
  requested one, so a work that MOVED was read happily at its new address while we went on
  publishing the old one. The final URL comes back with every result.

  ONE CACHE AGE FOR EVERYTHING. `max_age_days=1` is right for a chapter feed, where freshness is
  the entire point of the run, and wrong for a series listing that changes a few times a year. Two
  ages, chosen by the caller.

WHAT THIS DOES NOT DO. It does not decide that a work is gone. One 404 during a deploy is not
evidence of anything; only a run of them is, and counting that run across runs belongs to
adapters/checkstate.py, which persists. This layer reports what happened once, accurately.
"""
import collections
import concurrent.futures
import pathlib
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (compatible; yurarium/1.0; +https://yurarium.github.io) "
      "bibliographic metadata collection")

# Seconds between requests TO THE SAME HOST. Unchanged from the per-adapter values it replaces;
# the gain is concurrency across hosts, not a shorter pause.
PAUSE = 1.2
TIMEOUT = 40

# Cache ages, in days. A chapter feed is the reason the run exists, so it is never served stale.
# A series listing or discovery page changes a few times a year and costs a request every time.
AGE_FEED = 1
AGE_LISTING = 14

# A status that will still be true tomorrow, so a repeat is evidence rather than noise.
PERMANENT = {404, 410}

Result = collections.namedtuple("Result", "text status final_url moved from_cache error host")

_locks = collections.defaultdict(threading.Lock)
_last = collections.defaultdict(float)
_locks_guard = threading.Lock()


def _host_lock(host):
    with _locks_guard:
        return _locks[host]


def _wait(host):
    """Hold the host's slot until PAUSE has elapsed since its last request."""
    lock = _host_lock(host)
    with lock:
        gap = time.time() - _last[host]
        if gap < PAUSE:
            time.sleep(PAUSE - gap)
        _last[host] = time.time()


def cache_key(url):
    """A filename for one URL, distinct per host.

    THE HOST GOES IN FRONT AND IS NOT TRUNCATED. The key used to be the last 120 characters of the
    sanitised URL, which is right for ordinary paths and wrong the moment a query string is long:
    a percent-encoded Japanese title is 90 characters on its own, so the host fell off the front
    and two different sites asked the same question shared one cache entry. Searching
    manga.nicovideo.jp and webcomics.jp for one title served ニコニコ's page to both, and the
    second site was recorded as having answered when it had never been read. Any adapter that
    caches several hosts in one directory has the shape.
    """
    host = re.sub(r"[^A-Za-z0-9]", "_", urllib.parse.urlparse(url).netloc)
    return f"{host}__{re.sub(r'[^A-Za-z0-9]', '_', url)[-120:]}"


def fetch(url, cache, max_age_days=AGE_FEED):
    """Fetch one URL, returning a Result. Never raises for an HTTP or network condition.

    A caller that only wants the body can read `.text` and check it for None, which is what the
    adapters did before. A caller that wants to know WHY there is no body has `.status`, `.error`
    and `.moved` to look at.
    """
    host = urllib.parse.urlparse(url).netloc
    cache = pathlib.Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / cache_key(url)

    if f.exists() and (time.time() - f.stat().st_mtime) / 86400 < max_age_days:
        return Result(f.read_text(encoding="utf-8", errors="replace"),
                      200, url, None, True, None, host)

    _wait(host)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            text = r.read().decode("utf-8", "replace")
            final = r.geturl()
            # Compared on the normalised form: a trailing slash or a changed scheme is not a move.
            moved = final if _differs(url, final) else None
            f.write_text(text)
            return Result(text, r.status, final, moved, False, None, host)
    except urllib.error.HTTPError as e:
        return Result(None, e.code, url, None, False, f"HTTP {e.code}", host)
    except urllib.error.URLError as e:
        return Result(None, None, url, None, False, f"network: {e.reason}", host)
    except (OSError, ValueError) as e:
        return Result(None, None, url, None, False, f"{type(e).__name__}: {e}", host)


def _differs(a, b):
    def n(u):
        p = urllib.parse.urlparse(u)
        return (p.netloc.lower(), p.path.rstrip("/"), p.query)
    return n(a) != n(b)


def is_permanent(result):
    """Whether this outcome would still hold tomorrow. Absence of a body is not enough."""
    return result.status in PERMANENT


def fetch_many(urls, cache, max_age_days=AGE_FEED, workers=8, on_result=None):
    """Fetch across hosts concurrently while each host stays strictly serial at PAUSE.

    Workers bound total concurrency; the per-host lock does the actual rate limiting, so raising
    `workers` never makes any single host see faster traffic. It only lets idle time on one host
    be spent on another.
    """
    out = {}
    if not urls:
        return out
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, u, cache, max_age_days): u for u in urls}
        for fut in concurrent.futures.as_completed(futures):
            u = futures[fut]
            try:
                out[u] = fut.result()
            except Exception as e:                     # a bug here must not lose the whole batch
                out[u] = Result(None, None, u, None, False, f"{type(e).__name__}: {e}",
                                urllib.parse.urlparse(u).netloc)
            if on_result:
                on_result(u, out[u])
    return out
