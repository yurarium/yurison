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

  A REFUSAL LOOKED LIKE AN ABSENCE. This layer kept the status code and then handed back a Result
  whose `.text` was None for a 404 and None for a 503, so the distinction it had gone to the
  trouble of preserving was thrown away by the first caller that asked for the body. NDL refuses
  anything faster than a request every few seconds, and a sweep that reads those refusals as
  bodies-that-are-not-there concludes the national library holds nothing about anybody. `outcome()`
  names what a fetch established, and `body()` raises on the outcome that is not an answer.

  NOTHING RETRIED A 503, WHICH IS THE ONE STATUS THAT ASKS TO BE RETRIED. See THE 503 POLICY below.

THE 503 POLICY, and why the backoff is per host and not per request. A 503 is the server saying it
will not serve this now, so the useful response is to ask again later, and the useless one is to
ask again immediately with seven other workers doing the same. The pause a host is owed is already
per host here, so the penalty is too: a refusal lengthens the gap every caller of that host must
leave, and an answer halves it back down. One worker meeting a 503 slows the whole run against that
host and leaves the other 26 alone.

  WHAT IS RETRIED is the set of statuses that say "not now": 429, 500, 502, 503, 504, and a
  network-level failure, which is the same event seen from further away. A 403 or a 451 is a
  refusal too, and it is NOT retried, because asking again produces the same answer and the fix is
  a person deciding something.

  WHAT IS NEVER RETRIED is 404 and 410. Those are answers.

WHAT THIS DOES NOT DO. It does not decide that a work is gone. One 404 during a deploy is not
evidence of anything; only a run of them is, and counting that run across runs belongs to
adapters/checkstate.py, which persists. This layer reports what happened once, accurately.
"""
import collections
import concurrent.futures
import hashlib
import os
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

# Hosts that want more than PAUSE, by name. `set_pause` fills this.
#
# WHY NOT `net.PAUSE = max(net.PAUSE, 1.6)`, WHICH IS WHAT THREE ADAPTERS DO TODAY. That raises the
# gap for EVERY host in the process because one of them is delicate, so a run that touches NDL pays
# NDL's pause on all 27. Those callers still work, since PAUSE stays the default, but a new caller
# should name the host it is being polite to.
PAUSES = {}

# ATTEMPTS counts the first request, so 5 means one request and four retries.
#
# THE NUMBERS COME FROM NDL, which is the host that made this necessary: it answers 503 to anything
# faster than roughly one request every few seconds, and a first sweep at 1.6 s between requests had
# 61 of 100 titles refused. Backing off from 4 s and doubling reaches about a minute of waiting
# across five attempts, which is longer than any burst of refusals that sweep produced.
ATTEMPTS = 5
BACKOFF_MIN = 4.0
BACKOFF_MAX = 64.0

# A status that will still be true tomorrow, so a repeat is evidence rather than noise.
PERMANENT = {404, 410}

# Statuses where waiting is the thing that helps. 500 is in because a busy origin behind a proxy
# answers with one, and out of the retry set it would be indistinguishable from a 403.
RETRY = {429, 500, 502, 503, 504}

# What a fetch can mean. A caller that writes down an absence must branch on this and not on
# whether `.text` came back None, because it comes back None for two of the three.
ANSWERED, ABSENT, REFUSED = "answered", "absent", "refused"

# Cache ages, in days. A chapter feed is the reason the run exists, so it is never served stale.
# A series listing or discovery page changes a few times a year and costs a request every time.
AGE_FEED = 1
AGE_LISTING = 14

Result = collections.namedtuple(
    "Result", "text status final_url moved from_cache error host attempts",
    defaults=(1,))

_locks = collections.defaultdict(threading.Lock)
_last = collections.defaultdict(float)
_penalty = collections.defaultdict(float)
_locks_guard = threading.Lock()


class Refused(Exception):
    """The host declined to answer. Says nothing about the thing that was asked for."""


def set_pause(host, seconds):
    """Ask for a longer gap between requests to one host. Never shortens one."""
    PAUSES[host] = max(PAUSES.get(host, PAUSE), seconds)


def _host_lock(host):
    with _locks_guard:
        return _locks[host]


def _wait(host):
    """Hold the host's slot until this host's gap has elapsed since its last request.

    The gap is the host's pause plus whatever it has earned by refusing. Both are read inside the
    lock, so a penalty a worker records is paid by every other worker queued on that host and not
    only by the one that met the 503.
    """
    lock = _host_lock(host)
    with lock:
        need = PAUSES.get(host, PAUSE) + _penalty[host]
        gap = time.time() - _last[host]
        if gap < need:
            time.sleep(need - gap)
        _last[host] = time.time()


def _penalise(host):
    """This host refused. Double what everyone must wait for it, from BACKOFF_MIN."""
    with _host_lock(host):
        _penalty[host] = min(max(_penalty[host] * 2, BACKOFF_MIN), BACKOFF_MAX)
        return _penalty[host]


def _forgive(host):
    """This host answered. Halve the penalty; drop it once it is not worth carrying.

    HALVED AND NOT CLEARED. A host at its limit alternates between answering and refusing, and
    clearing on the first answer puts the run straight back to the rate that earned the refusal.
    """
    with _host_lock(host):
        _penalty[host] = 0.0 if _penalty[host] < 0.5 else _penalty[host] / 2


def cache_key(url):
    """A filename for one URL, distinct per host and injective over the whole URL.

    THE HOST GOES IN FRONT AND IS NOT TRUNCATED. The key used to be the last 120 characters of the
    sanitised URL, which is right for ordinary paths and wrong the moment a query string is long:
    a percent-encoded Japanese title is 90 characters on its own, so the host fell off the front
    and two different sites asked the same question shared one cache entry. Searching
    manga.nicovideo.jp and webcomics.jp for one title served ニコニコ's page to both, and the
    second site was recorded as having answered when it had never been read. Any adapter that
    caches several hosts in one directory has the shape.

    THE HASH IS WHAT MAKES IT INJECTIVE, and the readable part is only for a person looking at the
    directory. Two things collapsed keys before it. Substituting unsafe characters maps every kanji
    and every kana to `_`, so `search-遠山えま百合集` and `search-怪異部` became one filename and the
    second title read back the first title's page, which then reported as `no-record` and could not
    be told from a book NDL does not hold. And a 120 character tail collides for any two URLs that
    differ only near the front, which is every openBD batch: 50 ISBNs in a query string share their
    last 120 characters with any batch ending in the same handful of books. A cache that answers
    the wrong question is worse than no cache.
    """
    host = re.sub(r"[^A-Za-z0-9]", "_", urllib.parse.urlparse(url).netloc)[:48]
    return (f"{host}__{re.sub(r'[^A-Za-z0-9]', '_', url)[-96:]}"
            f"__{hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]}")


def _legacy_key(url):
    """This module's own key before the hash. `host__` then the sanitised tail."""
    host = re.sub(r"[^A-Za-z0-9]", "_", urllib.parse.urlparse(url).netloc)
    return f"{host}__{re.sub(r'[^A-Za-z0-9]', '_', url)[-120:]}"


def _adapter_key(url):
    """The key four adapters wrote before net.py owned the question.

    `re.sub(r"[^A-Za-z0-9]", "_", url)[-140:] + ".html"`, copied by hand into shop_reading,
    platform_reading, bylines and kmanga_reading. It has no host in it and no hash, and a Japanese
    URL is almost all underscores under that substitution, so the collision space is far smaller
    than 140 characters looks. Measured over 2,336 author names it collides nowhere today, and the
    longest name lands on exactly 140 characters with the truncation already eating the constant
    prefix, so the margin is gone rather than comfortable.
    """
    return re.sub(r"[^A-Za-z0-9]", "_", url)[-140:] + ".html"


# Every filename a page might already be sitting under. Read the old name, write the new.
#
# THE KEY IS ONE PRODUCER'S JOB (STANDING-INSTRUCTIONS §3), and it was four before this. A module
# that decides for itself how a URL becomes a filename decides for itself how it collides, and the
# two shapes below cover about 62,000 pages on this machine: capture-cache, kmanga-cache,
# byline-cache, shop-reading-cache and the rest. Re-fetching them to gain the hash would cost far
# more than the collisions it prevents, so `_adopt` renames what it finds and the directories heal
# as they are read. This list and `_adopt` can be deleted once they have.
LEGACY_KEYS = (_legacy_key, _adapter_key)


def _adopt(cache, url, f):
    """Move a page cached under an older key to the current one; say whether there is now a file.

    A LEGACY FILE BEGINNING `__ERROR__` IS DROPPED AND NOT ADOPTED. shop_reading, platform_reading
    and bylines wrote their failures into the cache as a page with that marker, so a host that was
    briefly down left an answer on disk that every later run read back and counted as the page not
    existing. Adopting one would carry that under a name this layer promises never holds a refusal.
    Deleting it is the heal: the next run asks again.
    """
    if f.exists():
        return True
    for key in LEGACY_KEYS:
        old = cache / key(url)
        if not old.exists():
            continue
        try:
            if old.read_bytes()[:9] == b"__ERROR__":
                old.unlink()
                continue
            os.replace(old, f)
        except OSError:             # another worker got there first, or the name is unusable
            return f.exists()
        return True
    return False


def outcome(result):
    """ANSWERED, ABSENT or REFUSED: what this fetch established.

    ABSENT is the host stating there is nothing at this address. REFUSED is the host declining to
    state anything, which includes a 503, a 403, a timeout and a DNS failure. Only ABSENT is
    evidence about the thing asked for, and writing a REFUSED down as an absence is how a
    rate-limited sweep teaches a catalogue to hold nothing.
    """
    if result.text is not None:
        return ANSWERED
    if result.status in PERMANENT:
        return ABSENT
    return REFUSED


def is_refusal(result):
    """Whether the host declined to answer. The test a caller branches on before recording a miss."""
    return outcome(result) == REFUSED


def body(result):
    """The page, or None where the host said there is none. Raises Refused where it said nothing.

    THIS IS THE POINT OF THE THREE-WAY OUTCOME, and it exists because `.text` cannot carry it.
    `.text` is None for a 404 and None for a 503, so a caller reading the body and writing
    `no-record` on None cannot tell a book the library does not hold from a request it declined.
    Going through here makes that mistake raise instead. `adapters/names/resolver.py` reached the
    same conclusion first and calls its exception SourceUnavailable: a transport failure is not an
    answer, and a pass that meets one stops rather than recording anything against any name.
    """
    if outcome(result) == REFUSED:
        raise Refused(f"{result.host} refused {result.final_url}: "
                      f"{result.error or result.status} after {result.attempts} attempt(s)")
    return result.text


def cached(url, cache):
    """What the cache holds for this URL, as a Result, or None where it holds nothing.

    This is what an adapter's `--offline` is: replay whatever was fetched before and send nothing.
    It goes through the same key and the same adoption as `fetch`, because an offline run that
    looked for the file under a different name would report every page as missing and every work
    as unanswered, which is the shape of an empty capture (STANDING-INSTRUCTIONS §4).
    """
    cache = pathlib.Path(cache)
    f = cache / cache_key(url)
    if not _adopt(cache, url, f):
        return None
    return Result(f.read_text(encoding="utf-8", errors="replace"), 200, url, None, True, None,
                  urllib.parse.urlparse(url).netloc, 0)


def fetch(url, cache, max_age_days=AGE_FEED, attempts=ATTEMPTS):
    """Fetch one URL, returning a Result. Never raises for an HTTP or network condition.

    A caller that only wants the body can read `.text` and check it for None, which is what the
    adapters did before. A caller that DECIDES SOMETHING from the absence of a body must go through
    `body()` or `outcome()`, because `.text` is None for a refusal as well as for an absence.

    `cache` may be None, for a caller that keeps its own store of the parsed answer and has no use
    for the bytes. `names/openbd_reading.py` is the case: it holds one record per ISBN, its request
    URLs are batches that never repeat, and a file cache beside that store would be a second answer
    to the same question (STANDING-INSTRUCTIONS §3).

    A REFUSAL IS NEVER CACHED. Only the success branch writes, so a 503 during a sweep cannot be
    served back tomorrow as though the host had answered it.
    """
    host = urllib.parse.urlparse(url).netloc
    f = None
    if cache is not None:
        cache = pathlib.Path(cache)
        cache.mkdir(parents=True, exist_ok=True)
        f = cache / cache_key(url)
        if _adopt(cache, url, f) and (time.time() - f.stat().st_mtime) / 86400 < max_age_days:
            return Result(f.read_text(encoding="utf-8", errors="replace"),
                          200, url, None, True, None, host, 0)

    result = None
    for attempt in range(1, max(1, attempts) + 1):
        _wait(host)
        result = _once(url, host, f)._replace(attempts=attempt)
        if outcome(result) != REFUSED:
            _forgive(host)
            return result
        # A refusal the host chose and will choose again. Waiting changes nothing; a person must.
        if result.status is not None and result.status not in RETRY:
            break
        if attempt < attempts:
            _penalise(host)
    return result


def _once(url, host, f):
    """One request, with the outcome recorded and nothing raised."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            text = r.read().decode("utf-8", "replace")
            final = r.geturl()
            # Compared on the normalised form: a trailing slash or a changed scheme is not a move.
            moved = final if _differs(url, final) else None
            if f is not None:
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


def fetch_many(urls, cache, max_age_days=AGE_FEED, workers=8, on_result=None,
               attempts=ATTEMPTS):
    """Fetch across hosts concurrently while each host stays strictly serial at its own pause.

    Workers bound total concurrency; the per-host lock does the actual rate limiting, so raising
    `workers` never makes any single host see faster traffic. It only lets idle time on one host
    be spent on another. A host that starts refusing slows down for every worker at once, because
    the penalty lives beside the pause and is read under the same lock.
    """
    out = {}
    if not urls:
        return out
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, u, cache, max_age_days, attempts): u for u in urls}
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
