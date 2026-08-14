#!/usr/bin/env python3
"""adapters/population: the same population from the store and from a build, agreeing.

COVERS = ['adapters/population.py']

WHAT CAN BE WRONG HERE IS THAT THE TWO ROUTES DISAGREE. §13 moves eleven passes off
`data/build/series.json` and onto the store, and the whole argument for doing it is that the file is
emitted FROM the store, so the answers cannot differ. A test that only exercised the store would
prove the query runs; what has to be proved is that it returns what the passes were reading.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "names"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import population                                                       # noqa: E402
import relational                                                       # noqa: E402


def _store(rows):
    """A store built the way `build.py` builds one, from the compiler's own rows.

    NO `INSERT` HERE, AND THAT IS THE POINT TWICE OVER. `the store has one writer` refuses a write
    from outside `adapters/relational/`, and this file is outside it; and a population asked of a
    store assembled by hand would be asked of a shape no compile produces. Handing `series` rows in
    is what §6 made the compiler's own input path.
    """
    db, _counts, refused = relational.build(":memory:", source={"series": {"series": rows}})
    return db, refused


SERIES = [
    {"id": "w00001", "work": "やがて君になる", "author": "仲谷 鳰", "state": "active"},
    {"id": "w00002", "work": "citrus", "author": None, "state": "completed"},
    {"id": "w00003", "work": "不明", "author": None},
]


def main(s):
    db, refused = _store(SERIES)
    # THE THREE WORKS GO IN, AND THE IDENTITY REGISTRY DOES NOT. `build` loads the real
    # `data/identity` beside whatever rows it is handed, and a `superseded` entry naming a work
    # this fixture does not hold is refused by the foreign key, which is the constraint doing its
    # job. What has to be clean is the population under test.
    s.eq([r for r in refused if r[0].startswith(("work ", "work_state"))], [],
         "the works handed in go in with nothing refused")
    from relational import asks

    got = asks.population(db, "works in a state", state="active")
    s.eq([w["work"] for w in got], ["やがて君になる"], "a state selects the works in it")
    s.eq(got[0]["author"], "仲谷 鳰",
         "and the byline comes back as the work PRINTS it, spaces and all; `surface` is the fold "
         "and a row rebuilt from the fold loses the space 42 bylines carry")
    s.eq([w["work"] for w in asks.population(db, "works in a state", state="completed")],
         ["citrus"], "and another state selects another work")
    s.eq(asks.population(db, "works in a state", state="dormant"), [],
         "a state nothing is in answers nothing rather than everything")

    # A WORK WITH NO STATE IS IN NO STATE, which is what the join has to mean. `work_state` is a
    # separate table precisely because a work may have no ruling yet, and an outer join here would
    # have swept every unruled work into whichever state was asked for.
    s.eq(len(asks.population(db, "works in a state", state="active")), 1,
         "a work with no state recorded joins no state")
    s.eq(len(asks.population(db, "works with their title and byline")), 3,
         "though it is still a work the corpus holds")

    # ── AND THE FILE ROUTE ANSWERS THE SAME, which is the whole claim §13 rests on ─────────────
    #
    # The build's file is emitted FROM these tables, so a pass moved from one to the other must not
    # see a different population. Written here as the shape `series.json` really has.
    d = pathlib.Path(tempfile.mkdtemp()) / "series.json"
    d.write_text(json.dumps({"series": SERIES}, ensure_ascii=False), encoding="utf-8")
    s.eq([w["work"] for w in population.works_in_state("active", d)], ["やがて君になる"],
         "the file route selects the same work")
    s.eq(len(population.works(d)), 3,
         "and holds the same three works")

    # A ROW WITH NO STATE KEY IS NOT IN A STATE HERE EITHER, which is the counter-case that makes
    # the two routes comparable rather than merely both non-empty.
    s.eq(population.works_in_state("unknown", d), [],
         "a row carrying no state matches no state asked for")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
