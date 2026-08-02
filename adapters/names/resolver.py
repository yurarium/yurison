#!/usr/bin/env python3
"""The shape every name source has, and the machinery that is the same for all of them.

NAMES-PLAN §4 describes four passes that differ only in where the answer comes from — and §7 sets
rules (cache before parse, one request at a time, batch where the API allows) that apply to all of
them identically. Writing that once means pass 3 arrives as a class with one method rather than as
a second copy of the pacing, caching, checkpointing and attempt-recording logic, each free to drift
from the first.

A source implements Resolver: it says which kinds of name it can speak to, what a hit would give
us, how many names it can take at once, and how to turn a batch into facts. Everything else —
skipping what is already resolved, skipping what this source has already been asked, writing each
fact to the journal as it lands, recording the misses, pacing the requests — is drive().

THE CACHE WRITES BEFORE IT PARSES. §4: "every external response is cached to disk before it is
parsed, so re-parsing after a bug fix costs nothing". That ordering is the whole point and it is
easy to get subtly wrong by parsing into a variable and writing the file afterwards, which loses
the response on any parser exception — exactly the case the rule exists for. Here the bytes hit the
disk and the parse reads them back.

FAILURE IS NOT AN ANSWER, and this is the rule with teeth. A 5xx, a timeout, or a source that has
been switched off tells us nothing about a name. If drive() recorded those as attempts, the names
would be permanently marked "asked, nothing found" and never retried — a few minutes of somebody
else's outage would become a permanent hole in our data. So a transport failure raises
SourceUnavailable and the pass stops for that source with nothing written against any name. Only a
source that replied, and replied without the name in it, produces an attempt.
"""
import hashlib
import pathlib
import time
import urllib.error
import urllib.request

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"


class SourceUnavailable(Exception):
    """The source did not answer. Says nothing about any name, so nothing is recorded."""


class Fact(dict):
    """One claim about one name, in the vocabulary store.record() takes."""


class HttpCache:
    """Every response on disk under a stable key, so the whole job re-derives offline.

    The key includes the request body, because a GraphQL POST's URL is identical for every query
    and hashing only the URL would collapse a thousand distinct batches into one cache entry.
    """

    def __init__(self, root, pause=1.0, offline=False):
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.pause = pause
        # §4 promises "the whole job can be re-derived offline". Offline mode makes that a mode
        # rather than a hope: anything not already on disk is treated as the source being
        # unavailable, so a parser fix can be replayed over months of stored responses with a
        # guarantee — not merely a strong expectation — that it sends nothing and spends no quota.
        self.offline = offline
        self.requests = 0
        self.hits = 0
        self.declined = 0
        self._last = 0.0

    def path(self, tag, url, body=None):
        key = hashlib.sha256((url + "\n" + (body or "")).encode("utf-8")).hexdigest()[:24]
        return self.root / f"{tag}-{key}.json"

    def get(self, tag, url, body=None, headers=None, method=None, max_age_days=None):
        """Return the response text, from disk if we already have it.

        Raises SourceUnavailable for anything that is not a usable reply. A 4xx that carries a body
        is returned rather than raised, because APIs answer "no such thing" with 404 and a JSON
        explanation, and that IS an answer — the caller decides.
        """
        f = self.path(tag, url, body)
        if f.exists():
            if max_age_days is None or (time.time() - f.stat().st_mtime) / 86400 < max_age_days:
                self.hits += 1
                return f.read_text(encoding="utf-8")

        if self.offline:
            self.declined += 1
            raise SourceUnavailable(f"{tag}: offline mode, and this response is not cached")

        # §7: one request at a time per host, with the pacing the adapters already use.
        wait = self.pause - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)

        data = body.encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"User-Agent": UA, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode("utf-8", "replace")
                status = r.status
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", "replace")
            # 429 and 5xx are "come back later", never "this name does not exist".
            if e.code == 429 or e.code >= 500:
                raise SourceUnavailable(f"{tag} HTTP {e.code}") from e
            text, status = body_text, e.code
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            raise SourceUnavailable(f"{tag}: {e}") from e
        finally:
            self._last = time.time()
            self.requests += 1

        # Written before it is parsed, and before the status is judged — a 403 body is the evidence
        # that a source is switched off, and evidence is worth keeping.
        f.write_text(text, encoding="utf-8")
        if status >= 400 and not text.strip():
            raise SourceUnavailable(f"{tag} HTTP {status} with no body")
        return text


class Resolver:
    """A source of names. Subclasses implement lookup(); drive() does everything else."""

    name = "unnamed"
    kinds = ()          # which of ("authors", "titles") this source can speak to
    provides = "either"  # what a hit would add: "reading" | "en" | "either"
    batch = 1

    def lookup(self, kind, names, cache):
        """Ask about `names`; return {ja: [Fact, ...]} for the ones answered.

        A name absent from the returned mapping was asked about and not found — drive() records
        that as an attempt. Raise SourceUnavailable if the source did not answer at all.
        """
        raise NotImplementedError


def drive(resolver, store, kind, names, cache, limit=None, verbose=False, on_batch=None):
    """Run one resolver over one kind of name, checkpointing as it goes.

    Returns a stats dict. Stops early and cleanly on SourceUnavailable — the names in the batch
    that failed are left untouched, so the next run picks them up as though nothing happened.
    """
    if kind not in resolver.kinds:
        return {"skipped": "wrong kind"}

    todo = store.open_for(kind, names, resolver.name, resolver.provides)
    if limit:
        todo = todo[:limit]
    stats = {"asked": 0, "hit": 0, "partial": 0, "miss": 0, "batches": 0, "unavailable": None}
    size = getattr(resolver, f"{kind[:-1]}_batch", None) or resolver.batch

    for i in range(0, len(todo), size):
        chunk = todo[i:i + size]
        try:
            found = resolver.lookup(kind, chunk, cache)
        except SourceUnavailable as e:
            # Nothing is written for this chunk. §4's attempt ledger stays honest: it records only
            # what a source actually said, so a source being down never costs us a name.
            stats["unavailable"] = str(e)
            if getattr(cache, "offline", False):
                # Offline is not an outage. A name whose response was never fetched is simply not
                # replayable, and stopping at the first of those would abandon every cached name
                # after it — which for a batch-of-one source is most of them. Skip and carry on;
                # still nothing recorded, so the name stays open for a run that can reach the net.
                stats["not-cached"] = stats.get("not-cached", 0) + len(chunk)
                continue
            break
        stats["batches"] += 1
        stats["asked"] += len(chunk)
        for ja in chunk:
            facts = found.get(ja) or []
            for fact in facts:
                store.record(kind, ja, source=resolver.name, **fact)
            # An attempt is recorded whenever the source failed to supply what it PROVIDES — which
            # is not the same as returning nothing. A source can answer with an English title it is
            # not allowed to publish (a community database's, which lands in en_candidates) and
            # thereby leave the name exactly as unresolved as a miss would have. Counting that as a
            # hit is a slow leak rather than a visible bug: nothing is wrong in the data, but the
            # name is never marked as asked, so every future run queries it again forever and the
            # cost stops being bounded. Resolved-is-final only holds if "asked" is recorded for
            # every outcome that did not resolve.
            if store.supplies(kind, ja, resolver.provides):
                stats["hit"] += 1
            elif facts:
                store.attempt(ja, 2, resolver.name)
                stats["partial"] += 1
            else:
                store.attempt(ja, 2, resolver.name)
                stats["miss"] += 1
        store.maybe_compact(50)
        if on_batch:
            on_batch(stats)
        if verbose:
            print(f"  {resolver.name}/{kind}: {stats['asked']}/{len(todo)} asked, "
                  f"{stats['hit']} hit, {cache.requests} requests", flush=True)

    store.compact()
    return stats
