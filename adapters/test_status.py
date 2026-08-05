#!/usr/bin/env python3
"""status.py: one producer of every number the status page shows."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import status  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/status.py"]

RUN = {"generated": "2026-08-05", "releases": 209, "works": 1046, "platforms": 50,
       "sources": [
           {"source": "madb", "files": 302, "works": 302, "rows": 646, "retrieved": "2026-08-01",
            "age_days": 4, "in_scope": True, "empty": False},
           {"source": "comicfuz", "files": 2, "works": 43, "rows": 2389,
            "retrieved": "2026-08-03", "age_days": 2, "in_scope": True, "empty": False}]}
# An invariant carries `violations`, not `ok`. Counting the wrong key read 0 of 13 passing
# on a page whose whole job is to say whether they do.
CHECKS = {"invariants": [{"name": "a", "violations": 0}, {"name": "b", "violations": 3}],
          "budgets": []}
SERIES = [{"work": "A", "state": "active", "chapters": 10, "id": "w1",
           "work_en": {"en": "A", "basis": "translated"}},
          {"work": "B", "state": "print", "chapters": 0, "id": "w2",
           "print": [{"volumes": 3}], "work_en": {}},
          {"work": "C", "state": "print", "chapters": 0, "print": [{"volumes": 1}]}]
INDEX = [{"volumes": [{"isbn": "1"}, {"isbn": "2"}]}]


def main(s):
    # A CAPTURE CAN SUCCEED AND RETURN THE WRONG SHAPE. マガポケ served ten faultless episodes where
    # the platform published 147, and no row count or staleness could see it.
    #
    # THE EXPECTATION IS DECLARED PER SOURCE, and a deviation is a gap in the declaration until
    # somebody checks. Requiring a date everywhere called 353 COMIC FUZ rows malformed; that
    # platform publishes none on a coin chapter, so the expectation was what was wrong.
    s.eq(status.EXPECT["comicfuz"], ("title",),
         "a source that publishes no date is not expected to return one")
    s.check("updated" in status.SHAPE, "while the default expects one")
    c2 = status.connectors(RUN, {"comicfuz": (2384, 2031)})
    fuz = [x for x in c2 if x["source"] == "comicfuz"][0]
    s.eq(fuz["malformed"], 353, "rows missing a field a chapter should carry are counted")
    s.eq([x for x in c2 if x["source"] == "madb"][0]["checked_rows"], 0,
         "and a source with no chapter rows claims nothing about its shape")

    c = status.connectors(RUN)
    s.eq([x["source"] for x in c], ["madb", "comicfuz"],
         "the stalest capture is named first, because staleness is the health one run can show")
    s.eq(c[0]["rows"], 646, "with the rows it holds")
    s.eq(status.connectors({}), [], "no run, no connectors")

    st = status.statistics(SERIES, INDEX)
    s.eq(st["works"], 3, "every work is counted")
    s.eq(st["states"], {"print": 2, "active": 1}, "states are counted, commonest first")
    s.eq(st["print_only"], 2, "and a work published only in volumes is distinguished")
    s.eq(st["with_identifier"], 2, "a work registered since the last identity run has none")
    s.eq(st["volumes"], 2, "volumes come from the print index, not from the series rows")
    s.eq(st["chapters"], 10, "a print work contributes no chapters rather than crashing the sum")

    # A BUDGET ON THE CODE IS NOT A FACT ABOUT THE MANGA. How many comments read as stock phrasing
    # is a development requirement, and putting it beside the corpus debts implies they are alike.
    d, e = status.split_budgets({"uncertain readings": 14, "three as an organising shape": 28,
                                 "modules without a test": 0})
    s.eq(d, {"uncertain readings": 14}, "a debt about the corpus stays with the corpus")
    s.eq(sorted(e), ["modules without a test", "three as an organising shape"],
         "and a requirement on the code is kept apart")

    out = status.outstanding(SERIES, {"uncertain readings": 14}, {"classification": 302,
                                                                 "bookwalker-yuri": 2443,
                                                                 "cmoa-yuri": 19,
                                                                 "english-licences": 87})
    by = {x["key"]: x for x in out}
    # THE COUNT AND THE ROWS BEHIND IT. A page that states a number without the rows cannot be
    # maintained from, and a number rounded for a human is a number nobody can act on.
    s.eq(by["english_names"]["count"], 2, "works with no English name are counted")
    s.eq(by["english_names"]["rows"], ["B", "C"], "and named, so the work can be done")
    s.eq(by["shelf_rows"]["count"], 2462, "captured candidates are counted across both shelves")

    # WHO CAN DO IT is the distinction that decides what happens next.
    s.eq(by["content_tier"]["kind"], "decision", "a classification needs a person to choose")
    s.eq(by["english_names"]["kind"], "research", "a name is mechanical and simply unattempted")
    s.eq(by["data_debts"]["kind"], "debt", "a corpus budget is a debt that ratchets down")
    # A DEVELOPMENT REQUIREMENT IS NOT PUBLISHED. The gate blocks a deploy on it, which is where it
    # belongs; shipping it would have the site claim responsibility the build does not own.
    s.check("development" not in by, "a code budget reaches the page at all")

    # AN UPDATE IS WHAT CHANGED. Reporting only the totals says what exists, which is a different
    # question and the one the statistics section already answers.
    s.eq(status.delta({"works": 1234, "chapters": 10}, {"works": 1220, "chapters": 10}),
         {"works": 14}, "only what moved is reported, and by how much")
    s.eq(status.delta({"works": 5}, None), {},
         "with no previous run, nothing is claimed about change")
    s.eq(status.delta({"works": 5}, {}), {}, "and an empty one claims nothing either")
    s.check("thin_sitemap" in status.MEANS,
            "a measure named for whoever wrote it carries a description for whoever reads it")

    # A CHECK ON HOW THIS IS MADE IS NOT A CHECK ON THE DATABASE. Whether our prose reads as stock
    # phrasing is a development requirement and the update has no bearing on it.
    C2 = {"invariants": CHECKS["invariants"] +
          [{"name": "no stock phrasing in public text", "violations": 0}], "budgets": []}
    # THE LEDGER'S VERDICT TRAVELS WITH THE SOURCE IT IS ABOUT, so the table can show it beside
    # the row count it contradicts.
    c3 = status.connectors(RUN, None, {"madb": {"was": 646, "now": 60, "share": 0.907}})
    s.eq([x["drop"]["was"] for x in c3 if x["source"] == "madb"], [646],
         "a source the ledger flagged carries what it held before")
    s.eq([x["drop"] for x in c3 if x["source"] == "comicfuz"], [None],
         "and one it did not flag carries nothing")

    doc = status.build(RUN, C2, SERIES, INDEX, {"x": 1}, {})
    s.eq(len(doc["gate"]["invariants"]), 2, "the data checks are the ones counted")
    s.check("development_checks" not in doc["gate"],
            "and a check on how this is made is not shipped either")
    s.eq(doc["gate"]["invariants_passing"], 1, "a failing invariant is not counted as passing")
    s.eq(doc["last_run"]["releases"], 209, "the run reports itself; this file does not re-derive it")
    s.check(doc["generated"].startswith("20"), "and the file says when it was made")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
