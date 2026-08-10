#!/usr/bin/env python3
"""Pass 3 — automated search. NOT IMPLEMENTED: the seam only (NAMES-PLAN §3.6, §4).

WHY THIS FILE IS A STUB. §3.6 is unambiguous that pass 3 must use a metered search API — Google's
Programmable Search JSON API, or a Bing/Brave/Kagi equivalent — and NOT a results page:

    "Never: scraping a search results page. That is the specific thing that angers a search engine,
     and it is not the same as querying its API."

No such key exists for this project yet. Writing the pass anyway would mean either shipping code
that cannot run, or quietly substituting the one technique the plan rules out — and the second is
the sort of thing that gets discovered later, from an IP block. So the pass stops at the seam, and
the seam is real: everything pass 3 needs that is not the search call itself already exists and is
already exercised by pass 2.

WHAT IS ALREADY BUILT, so that adding a key is the whole job:

  the resolver interface   resolver.Resolver — say which kinds you speak to, what a hit adds, how
                           many names fit in a request, and how to turn names into facts. drive()
                           supplies pacing, batching, ordering and error handling.
  attempt recording        drive() writes one attempt per name the source answered nothing for, so
                           §3.6's "one query per name, not per attempt" holds across restarts by
                           construction: store.open_for() will not offer the name again. This is
                           the property that makes a metered quota safe to spend.
  the response cache       resolver.HttpCache writes every response to disk before parsing it and
                           serves it forever after, keyed on URL plus body. §3.6's "cache the
                           result forever; a name searched is never searched again" is therefore
                           already true — and a parser fix costs no quota at all.
  the outage rule          a source that fails to answer raises SourceUnavailable and NO attempt is
                           written. For a metered API this matters more than anywhere else: a
                           quota-exhausted 429 must leave the name open for tomorrow, not spend it.
  query material           pass 0 records a `handles` field on authors it found a social handle
                           for. §3.6 wants narrow queries — `"作者名" site:pixiv.net` beats a bare
                           name — and a known handle is the narrowest query available.

WHAT REMAINS, and the two decisions inside it that are not mechanical:

  1. The API call. One query per name, cache.get() through HttpCache so it is stored before it is
     read. Roughly twenty lines.

  2. Deciding what a result MEANS, which is the hard part and is not a search problem. A hit gives
     a page, not a reading. Turning a pixiv profile or an interview into a kana reading needs the
     same exactness pass 2's matchers apply — the name on the page must be the name we asked about,
     and the reading must be stated on it rather than inferred from it. A confident extraction from
     an approximate page is precisely the "plausible reading with no source behind it, presented as
     if it had one" of §1.

  3. What basis to record. A reading read off an author's own profile is `stated`. A reading
     inferred from a page that merely mentions them is not, and if pass 3 cannot tell the two
     apart it must record the weaker one — that is what pass 4's unverified label is for (§5d), and
     it is a finished state rather than a failure.

WHAT PASS 3 MUST NOT DO, restated here because this file is where somebody will be tempted:

  - No scraping of a search results page, under any framing, including "just this once to test".
  - No morphological analyser output recorded as a sourced reading. §5c: "a tokeniser's confident
    output on a pen name is not a sourced reading and must never be recorded as one." SudachiPy and
    fugashi are permissively licensed and available, and their output on a pen name is a guess — a
    guess is pass 4's business and carries pass 4's label.
  - No KANJIDIC2 or JMdict. CC BY-SA, avoidable, and §5c settled it.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names.resolver import Resolver, SourceUnavailable  # noqa: E402
from facts import namekey as _namekey                                   # noqa: E402


class SearchResolver(Resolver):
    """The pass 3 seam. Drop in an API key and a result-reading rule; drive() does the rest."""

    name = "search"
    kinds = _namekey.RESEARCHABLE_KINDS
    provides = "either"
    batch = 1  # §3.6: one query per name, and the quota is the pacing.

    def __init__(self, api_key=None, engine_id=None, store=None):
        self.api_key = api_key
        self.engine_id = engine_id
        self.store = store

    def query_for(self, kind, ja):
        """The narrow query §3.6 asks for, built from what earlier passes already learned.

        Kept here rather than in the unwritten lookup() because it needs nothing that does not
        exist: a handle from pass 0 makes the narrowest query available, and the fallback is the
        site-scoped form the plan gives as its example.
        """
        if kind == "authors" and self.store:
            handles = (self.store.records["authors"].get(ja) or {}).get("handles") or []
            if handles:
                return f'"{ja}" ({" OR ".join(handles)})'
            return f'"{ja}" site:pixiv.net OR site:x.com'
        return f'"{ja}" 英題 OR "English title"'

    def lookup(self, kind, names, cache):
        raise SourceUnavailable(
            "pass 3 is not implemented: it requires a metered search API key, which this project "
            "does not have. NAMES-PLAN §3.6 rules out the alternative (scraping a results page). "
            "See this module's docstring for what is already built and what remains."
        )


def main(argv=None):
    print(__doc__.strip(), file=sys.stderr)
    print("\nNOT RUNNABLE. No search API key exists for this project.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
