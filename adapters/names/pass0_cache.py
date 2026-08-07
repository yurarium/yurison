#!/usr/bin/env python3
"""Pass 0 — everything already on disk, at zero network cost (NAMES-PLAN §3.1, §4a).

WHAT §4a MEASURED AND WHY IT MATTERS. Sampling 278 cached pages, 65% carried a Latin social handle
and that looked like a shortcut until the handles were counted per host: almost all are the
platform's own footer links. `comicdays_team` appears on 372 of giga-series-cache's pages,
`SundayWebry` on 71, `yuri_navi` on 2656 of yurinavi-cache's 2663. So the filter is not optional —
without it pass 0 would confidently assign one publisher's marketing account as the Latin name of
several hundred different authors. Any handle appearing on more than half of a host's pages is the
host's own and is discarded.

WHERE THIS DISAGREES WITH §3.1, AND THE MEASUREMENT THAT SETTLED IT. The plan says a handle next to
a byline "is the author's own Latin rendering and outranks anything we would compute". That is true
of `jiangsal` → Sal Jiang. It is not true of `o4510_9chi9`, the only handle kadokomi-cache yields,
which is not a rendering of anybody's name.

Run over all 6316 cached files, the whole corpus produces FOUR unambiguous handle-to-author
associations, and of the two that are even name-shaped one is `yamadayoshinob` (a truncated handle,
not the name "Yamada Yoshinobu") and the other is `news_mynavi_jp` (a news site that happened to be
the only account on a page mentioning one author). Publishing either as a person's English name
would misname them, which §1 rates as the one error worth building the whole standard around — and
a rule with a 50% error rate over a sample of two is not a rule, it is a coin toss.

So handles are recorded as EVIDENCE and never promoted to a rendering. That is not a loss: their
real value is to pass 3, which wants exactly this for its narrow `"作者名" site:` queries (§3.6),
and a query hint that turns out wrong costs one search instead of a person's name.

WHAT PASS 0 IS ACTUALLY GOOD FOR, in yield order:

  1. The 64 authors and 21 titles whose surface is ALREADY Latin. No lookup, no reading needed, no
     ambiguity: `Sal Jiang` is the author's own rendering because the platform printed it. This is
     the largest and by far the most certain part of pass 0, and §3.1 does not mention it.
  2. Bracketed kana glosses in the credit line — 博（ひろ）. Extracted in inputs.py; recorded here.
  3. Handles, filtered as above — as search hints for pass 3, not as names.

NO FURIGANA EXTRACTOR. §4a found ruby markup on 0 of 278 sampled pages. This checks that claim once
over every cached file rather than trusting it, because it is cheap to check and expensive to be
wrong about, but it does not build a parser for a thing that is not there.
"""
import argparse
import collections
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names import inputs, kana  # noqa: E402
from names.store import NameStore  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import paths

HANDLE = re.compile(r"(?:twitter\.com|x\.com)/(?:#!/)?([A-Za-z0-9_]{2,20})(?=[/?\"'<>\s]|$)")
PIXIV_USER = re.compile(r"pixiv\.net/users/(\d+)")
RUBY = re.compile(r"<ruby[\s>]", re.I)

# Twitter's own paths, which are not handles at all.
NOT_HANDLES = {
    "intent", "share", "home", "i", "hashtag", "search", "widgets", "privacy", "tos", "settings",
    "about", "login", "signup", "explore", "messages", "notifications", "compose", "download",
    "en", "ja", "help", "status", "statuses", "www",
}

# A handle only becomes a name when it looks like one: letters and separators, no digit soup. This
# is deliberately strict — the cost of a false positive is a misnamed person (§1), and the cost of
# a false negative is that pass 3 looks the name up anyway.
NAME_SHAPED = re.compile(r"^[A-Za-z][A-Za-z]*(?:[_.-][A-Za-z]+){0,2}$")

# Caches holding print-side API responses. §2: the print half is out of scope and its readings are
# already on disk; reading them here would blur the two halves for no gain.
SKIP_CACHES = {"madb-cache", "openbd-cache", "pixiv-api-adapter-retired"}

# §4a's filter is per HOST, and a cache directory is not one. giga-series-cache alone holds
# comic-days.com, sunday-webry.com, comic-action.com and several more, so counting against the
# directory hides a platform account inside a bigger denominator: `comicdays_team` is on 372 of the
# directory's 2126 files — under half, so it survives — but on nearly every comic-days page, which
# is what the rule was written to catch. The adapters name their cache files after the URL, so the
# host is recoverable from the filename; where it is not (kadokomi's KC_000031_S.html) the cache
# directory is a single host anyway and stands in for it.
CACHE_HOST = re.compile(r"^https?_+([a-z0-9_-]*?(?:_co)?_(?:com|jp|net|org|tv|info|moe|io))(?:_|$)")


def cache_host(cache_name, path):
    m = CACHE_HOST.match(pathlib.Path(path).name)
    return m.group(1) if m else cache_name


def scan_cache(cache_root, verbose=False):
    """One read of every cached file, keeping the handles it found but NOT the file.

    Holding 6000 pages of HTML in memory to search them later is around a gigabyte for no reason —
    the second stage only cares about the few hundred files that carried a non-platform handle, and
    the OS page cache makes re-reading those effectively free. So this stage records where handles
    were and forgets everything else.

    Returns (per_file, host_pages, host_handles, ruby_pages, files_scanned).
    """
    root = pathlib.Path(cache_root)
    per_file = {}
    host_pages = collections.Counter()
    host_handles = collections.defaultdict(collections.Counter)
    ruby_pages = scanned = 0

    for cache in sorted(root.glob("*-cache")):
        if cache.name in SKIP_CACHES:
            continue
        for f in sorted(cache.rglob("*")):
            if not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if len(text) > 4_000_000:
                continue
            host = cache_host(cache.name, f)
            host_pages[host] += 1
            scanned += 1
            if RUBY.search(text):
                ruby_pages += 1
            found = {h for h in HANDLE.findall(text) if h.lower() not in NOT_HANDLES}
            for h in found:
                host_handles[host][h] += 1
            if found:
                per_file[str(f)] = (host, found)
        if verbose:
            print(f"  scanned {cache.name}", file=sys.stderr)

    return per_file, host_pages, host_handles, ruby_pages, scanned


def platform_handles(host_pages, host_handles):
    """§4a's filter: a handle on more than half a host's pages belongs to the host, not an author.

    A host with only a page or two in the cache cannot support the test — one handle on one page is
    trivially "all of them" — so hosts under a floor are skipped rather than having every handle on
    them written off as the platform's.
    """
    out = set()
    for host, handles in host_handles.items():
        pages = host_pages[host]
        if pages < 4:
            continue
        for h, n in handles.items():
            if n > pages / 2:
                out.add(h)
    return out


def run(store, authors, titles, cache_root, verbose=False):
    stats = collections.Counter()

    # 1. Latin surfaces. Nothing to look up: the platform printed the author's own rendering, so it
    #    is `stated` and verified. There is no kana reading and there should not be one — a Latin
    #    pen name is not a transliteration of anything (§1).
    for kind, names in (("authors", authors), ("titles", titles)):
        for ja in names:
            if kana.script_class(ja) != "latin":
                continue
            if store.records[kind].get(ja, {}).get("en"):
                continue
            store.record(kind, ja,
                         en=ja,
                         # `official-jp` — the top of the title precedence, and the only place
                         # these passes legitimately reach it. The string was printed on the
                         # Japanese platform's own page as the work's title, so it IS the work's
                         # English name rather than anyone's rendering of it.
                         basis="stated" if kind == "authors" else "official-jp",
                         source_kind="platform",
                         script="latin",
                         source="surface",
                         note="already Latin on the platform's own page; no romanisation involved",
                         **{"pass": 0})
            stats[f"{kind}-latin"] += 1
        store.maybe_compact()

    # 2. Kana glosses that came out of the credit line itself (inputs._peel_bracket).
    for ja, meta in authors.items():
        if meta.get("reading") and not store.records["authors"].get(ja, {}).get("reading"):
            store.record("authors", ja,
                         reading=meta["reading"],
                         reading_basis="stated",
                         source="credit-line-furigana",
                         # THE PAGE THE BRACKET WAS PRINTED ON, which this pass already held and
                         # threw away. `inputs.collect` files every address a credit was seen at
                         # under the author, so the reading claimed a source for 博 and named a
                         # method instead of a place. First of the URLs because they are the same
                         # credit line seen on several episodes of one work, so any of them shows
                         # the bracket; where the pass saw nothing, nothing is recorded.
                         source_url=(meta.get("urls") or [None])[0],
                         source_kind="platform",
                         note="the platform printed the reading in brackets beside the name",
                         **{"pass": 0})
            stats["author-gloss"] += 1

    # 3. Handles. One pass over every cached file, then the §4a filter, then proximity.
    if verbose:
        print("scanning caches…", file=sys.stderr)
    per_file, host_pages, host_handles, ruby_pages, scanned = scan_cache(cache_root, verbose)
    stats["files-scanned"] = scanned
    stats["hosts"] = len(host_pages)
    stats["pages-with-ruby"] = ruby_pages
    platform = platform_handles(host_pages, host_handles)
    stats["platform-handles-filtered"] = len(platform)

    # An author's handle is one that appears on a page that also names them. Where a page names
    # several authors, or offers several handles, the association is ambiguous and is dropped
    # entirely rather than guessed — this is the case §1 says costs a real person their name.
    #
    # Matching 975 names against a page one at a time is a million substring searches; one
    # alternation regex does the same job in a single pass, and longest-first ordering stops a
    # short name shadowing a longer one that contains it.
    by_author = collections.defaultdict(set)
    findable = sorted((a for a in authors if len(a) >= 2), key=len, reverse=True)
    name_re = re.compile("|".join(re.escape(a) for a in findable)) if findable else None
    for path, (cache, found) in sorted(per_file.items()):
        usable = {h for h in found if h not in platform}
        if not usable or name_re is None:
            continue
        try:
            text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        named = set(name_re.findall(text))
        if len(named) != 1 or len(usable) != 1:
            stats["handle-ambiguous"] += 1
            continue
        by_author[next(iter(named))].add(next(iter(usable)))

    # A handle that turns up beside two different authors belongs to neither of them — it is a
    # magazine, a collaborator's account, or a mention. Co-occurrence was only ever circumstantial;
    # co-occurring with several people removes even that.
    claimed = collections.Counter(h for hs in by_author.values() for h in hs)
    shared = {h for h, n in claimed.items() if n > 1}
    stats["handle-shared-dropped"] = len(shared)
    by_author = {a: hs - shared for a, hs in by_author.items()}
    by_author = {a: hs for a, hs in by_author.items() if hs}

    for ja, handles in sorted(by_author.items()):
        stats["handle-evidence"] += 1
        if any(NAME_SHAPED.match(h) for h in handles):
            # Counted, never acted on — see the module docstring. If this number ever grows enough
            # to justify a promotion rule, the rule can be written then, against real evidence
            # rather than against §3.1's expectation of what handles would turn out to be.
            stats["handle-name-shaped"] += 1
        store.record("authors", ja,
                     handles=sorted(handles),
                     source="cache-handle",
                     note="Latin handle co-occurring with this byline in a cached page. Evidence "
                          "for pass 3's narrow site: query, NOT a rendering of the name.",
                     **{"pass": 0})
        store.maybe_compact()

    # Everything pass 0 could have found something for and did not. Recorded so a rerun skips it
    # and so §4a's "nothing to find here" bucket is populated rather than looking like open work.
    for kind, names in (("authors", authors), ("titles", titles)):
        for ja in names:
            r = store.records[kind].get(ja, {})
            if r.get("en") or r.get("reading") or store.tried(ja, "cache"):
                continue
            store.attempt(ja, 0, "cache")
            stats[f"{kind}-miss"] += 1
        store.maybe_compact()

    store.compact()
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--out", default="data/names")
    ap.add_argument("--cache", default=str(paths.CACHE_ROOT))
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    authors, titles, _, _by_title = inputs.load(args.build)
    store = NameStore(args.out)
    stats = run(store, authors, titles, args.cache, args.verbose)
    for k, v in sorted(stats.items()):
        print(f"{k:32} {v}")
    print()
    print("authors", store.status("authors", authors))
    print("titles ", store.status("titles", titles))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
