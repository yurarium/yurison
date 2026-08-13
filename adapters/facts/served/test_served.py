#!/usr/bin/env python3
"""facts/served: what a reader is served, and how much of it reaches them around the store.

COVERS = ['adapters/facts/served/__init__.py']

THE WHOLE MODULE TURNS ON TELLING A MAP FROM A RECORD, so most of this file is that. Get it wrong
one way and 3,301 folded titles are reported as 3,301 fields; get it wrong the other way and the
31-field series row collapses to one path and the budget reports near-total coverage of a store that
holds almost none of it. The second is the dangerous direction, because it reads as success.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import served                                                # noqa: E402

#: A `series.json` row as the build writes it: many keys, nearly all values scalar. The counter-case.
SERIES_ROW = {k: "x" for k in (
    "author", "author_en", "chapters", "collection", "completed_basis", "evidence", "first", "free",
    "free_timed", "id", "latest", "latest_any", "latest_ep", "oneshot", "partial", "priced",
    "print", "series_url", "skipped", "sourced_from", "sources", "state", "state_basis",
    "state_claims", "stated_next", "url", "work", "work_en", "publisher", "imprint", "volumes")}


def main(s):
    # ── A MAP IS KEYED BY DATA ────────────────────────────────────────────────────────────────
    #
    # `feed/names.json` holds 3,301 titles under folded keys, and walking it naively reported them
    # as 3,301 separate fields. The whole corpus came to 137,131 paths, which is a number nobody can
    # act on.
    names_like = {f"タイトル{i}": {"en": "x", "reading": "y", "basis": "translated"} for i in range(12)}
    s.check(served.is_map(names_like), "a map keyed by Japanese titles is data, not fields")
    odd_shapes = {"*sow*": {"en": "x"}, "2C=がろあ": {"basis": "romaji", "reading": "y"},
                  **{f"名前{i}": {"en": "x", "id": i} for i in range(10)}}
    s.check(served.is_map(odd_shapes),
            "AND ITS VALUES NEED NOT AGREE: author records vary, so a rule comparing their shapes "
            "missed this one and reported 29,316 paths for one field")
    floor_like = {f"語{i}": "romanised" for i in range(12)}
    s.check(served.is_map(floor_like),
            "a map of strings is still a map, which the shape rule cannot see at all")
    ids = {f"c{i:05d}": {"name": "x", "works": []} for i in range(12)}
    s.check(served.is_map(ids),
            "and keys that look like identifiers are caught by the vocabulary its values share")

    # ── THE COUNTER-CASE THAT DECIDES THE DESIGN ──────────────────────────────────────────────
    #
    # A rule reading "many keys, simple values" as a map would swallow this row whole and report
    # one path where there are 31, which is the single most consequential misreading available
    # here: it would say the store covers the corpus while holding almost none of it.
    s.eq(len(SERIES_ROW), 31, "the row really does carry this many fields")
    s.check(not served.is_map(SERIES_ROW),
            "a series row is a RECORD: its keys are field names, so it is never collapsed")
    s.check(not served.is_map({"a": 1, "b": 2}), "and a small dict is a record whatever its keys")

    # ── WALKING ───────────────────────────────────────────────────────────────────────────────
    doc = {"series": [dict(SERIES_ROW, work_en={"en": "A", "basis": "translated"})]}
    ps = served.paths(doc)
    s.check("series[].work" in ps, "a list collapses to one element's paths")
    s.check("series[].work_en.en" in ps, "and nesting is followed")
    s.check(not any(p.startswith("series[0]") for p in ps), "an index is never part of a path")
    deep = served.paths({"m": {f"キー{i}": {"a": {"b": {"c": 1}}} for i in range(12)}})
    s.check("m{}" in deep, "a map contributes its own path once")
    s.check(not any("キー" in p for p in deep), "and none of its keys appear as fields")

    # ── WHAT IS CLAIMED, AND WHAT THAT MEANS ──────────────────────────────────────────────────
    #
    # The declaration is prefixes rather than one entry per field, because a per-field list is a
    # second thing to keep in step with the schema. Nothing a table cannot answer may be claimed,
    # which is why this file changed when §2 filled `edition` and `work_publisher`.
    s.check(all(":" in c for c in served.STORE_ANSWERS),
            "every claim names the file it is a path in, since two files share path shapes")
    # §2 FILLED `edition` AND `work_publisher`, so what they answer may be claimed and is.
    s.check(any("volumes[].isbn" in c for c in served.STORE_ANSWERS),
            "a volume's ISBN is claimed: the edition table holds one row per volume")
    s.check(any("works[].publisher" in c for c in served.STORE_ANSWERS),
            "and the house a work is published under, which work_publisher now carries")
    # WHAT IS STILL NOT CLAIMED, and each absence is a section of STORE-PLAN rather than an
    # oversight. A designation is `上` or `創刊号` or `2017年1月号`, and `edition.volume` is an
    # INTEGER, so the schema has nowhere to put one.
    s.check(not any("designation" in c for c in served.STORE_ANSWERS),
            "a volume's designation is not claimed: the column is an integer and 創刊号 is not one")
    s.check(not any("work_en" in c or "romaji" in c for c in served.STORE_ANSWERS),
            "and no rendering is claimed: the store has no table for one")

    # A CLAIM COVERS WHAT HANGS OFF IT. `series.json:series[].id` answers for the id itself, and a
    # deeper path under a claimed prefix is answered with it rather than counted again.
    s.check(served.CORPUS and "checks.json" not in served.CORPUS,
            "the run's report on itself is not corpus data and is not counted")
    s.check("status.json" not in served.CORPUS and "run.json" not in served.CORPUS,
            "nor is the status page's data or the run summary")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
