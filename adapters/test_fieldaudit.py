#!/usr/bin/env python3
"""fieldaudit: a platform that lost a field across its own rows, told from one that never had it.

COVERS = ['adapters/fieldaudit.py']

WHY THE THRESHOLDS ARE THE SUBJECT. Each rule was separated after the shape before it hid
something: a bare total of three failed a run on four rows that were four platforms each publishing
an update the way they publish it, and the rows stating no access were quietly consuming the
tripwire meant to catch a lost title. A threshold nobody tests is a number somebody picked.

NO DATABASE IS BUILT HERE, AND THE LINT WAS RIGHT ABOUT WHY. This suite opened its own sqlite and
planted rows in it, and `adapters/lint/onewriter.py` counts that as a second writer of the store:
the exemption belongs to the compiler and its own suite, and a fixture spelling the schema out here
is a second statement of the schema as well. The query is a population in `relational/asks.py` now,
asked where the corpus's questions live, and what this module owns is the reading of the answer.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fieldaudit                                                       # noqa: E402
import testkit                                                          # noqa: E402

COVERS = ["adapters/fieldaudit.py"]


def _rows(rows_):
    """Rows as the store's population returns them. `rows_` is (platform, ep, author, modes)."""
    return [{"id": f"r{i}", "plat": plat, "ep": ep, "author": author,
             "work": f"work {i}", "access": modes}
            for i, (plat, ep, author, modes) in enumerate(rows_)]


def main(s):
    # ── THE QUESTION IS THE STORE'S, AND IT ASKS FOR WHAT THE AUDIT READS ─────────────────────
    #
    # A population that stopped returning `access` would make every row look unpriced, so the
    # columns are named here rather than assumed from the rows a run happens to have.
    from relational import asks
    sql = asks.POPULATIONS[fieldaudit.POPULATION]["sql"]
    for column in ("plat", "ep", "author", "work", "access"):
        s.check(f" AS {column}" in sql, f"the population names {column}")
    s.check("provenance = 'attested'" in sql, "and asks only about attested rows")

    # ── A ROW MISSING A NAME, AND ONE MISSING ONLY ITS PRICE ─────────────────────────────────
    #
    # The two are counted apart because they are different faults. An empty string and whitespace
    # are both "no episode title": a selector matching the wrong element returns that element.
    mixed = _rows([
        ("A", "第1話", "作者", 1),      # complete
        ("A", "", "作者", 1),           # no episode title
        ("A", "   ", "作者", 1),        # whitespace is not a title either
        ("A", "第2話", None, 1),        # no author
        ("A", "第3話", "作者", 0),      # named, states no access
    ])
    s.eq(len(fieldaudit.unnamed(mixed)), 3, "a blank, a whitespace title and a missing author")
    s.eq([r["ep"] for r in fieldaudit.unpriced(mixed)], ["第3話"],
         "and a row is unpriced only where it is otherwise complete")

    # ── A MOVED SELECTOR TAKES OUT ITS OWN PLATFORM ──────────────────────────────────────────
    #
    # Three rows is the floor because a platform publishing one or two updates says nothing either
    # way, and half its rows is what tells a moved selector from a work published without a byline.
    lost = _rows([("A", "", "作者", 1)] * 3 + [("A", "第1話", "作者", 1)])
    s.eq(fieldaudit.moved(lost), [("A", 3, 4)], "three of four rows is a platform that lost it")
    s.eq(fieldaudit.moved(_rows([("A", "", "作者", 1)] * 2 + [("A", "第1話", "作者", 1)] * 2)), [],
         "two is under the floor, whatever share of the platform it is")
    s.eq(fieldaudit.moved(_rows([("A", "", "作者", 1)] * 3 + [("A", "第1話", "作者", 1)] * 4)), [],
         "and three of seven is a handful rather than a selector")

    # SCATTERED ACROSS PLATFORMS IS NOT A MOVED SELECTOR, which is the case that failed a run: four
    # rows on three platforms in two shapes, each publishing an update the way it does.
    scattered = _rows([("ニコニコ漫画", "", "作者", 1), ("ニコニコ漫画", "", "作者", 1),
                       ("ヤンジャン+", "読み切り", None, 1), ("きら星ポータル", "読み切り", None, 1)]
                      + [("ニコニコ漫画", "第1話", "作者", 1)] * 8)
    s.eq(fieldaudit.moved(scattered), [], "no platform is over its share")
    s.eq(fieldaudit.findings(scattered), [], "so the run is not stopped")

    # ── AND A DRIFT ACROSS EVERYTHING STILL TRIPS ────────────────────────────────────────────
    #
    # A change to a shared renderer shows up as a few rows everywhere and no platform over its
    # share, which per-platform counting cannot see.
    wide = _rows([(f"P{i}", "", "作者", 1) for i in range(fieldaudit.SPREAD + 1)]
                 + [(f"P{i}", "第1話", "作者", 1)
                    for i in range(fieldaudit.SPREAD + 1) for _ in range(3)])
    s.eq(fieldaudit.moved(wide), [], "one lost row per platform is nobody's selector")
    s.eq(len(fieldaudit.findings(wide)), 1, "and the spread rule is what catches it")
    s.check("spread too widely" in fieldaudit.findings(wide)[0],
            "saying which rule fired, because they mean different things")

    # ── ROWS STATING NO ACCESS ARE THEIR OWN NUMBER ──────────────────────────────────────────
    #
    # マガポケ is read by two routes and one of them carries access on none of its chapters, so a
    # work reached only by the feed states none. Counted with the lost titles, those consumed the
    # tripwire meant to catch the first row that really lost one.
    quiet = _rows([("マガポケ", "第1話", "作者", 0)] * fieldaudit.NO_ACCESS)
    s.eq(fieldaudit.findings(quiet), [], "the route asymmetry is allowed for")
    louder = _rows([("マガポケ", "第1話", "作者", 0)] * (fieldaudit.NO_ACCESS + 1))
    s.eq(len(fieldaudit.findings(louder)), 1, "one row past it is a finding")
    s.check("state no access" in fieldaudit.findings(louder)[0], "and says so in its own words")

    # ── THE HEALTHY ANSWER ───────────────────────────────────────────────────────────────────
    s.eq(fieldaudit.findings(_rows([("A", "第1話", "作者", 1)] * 40)), [],
         "a capture with every field on every row stops nothing")
    s.eq(fieldaudit.findings([]), [],
         "and a run that captured nothing has no field to have lost, which the count says instead")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
