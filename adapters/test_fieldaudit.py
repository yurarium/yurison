#!/usr/bin/env python3
"""fieldaudit: a platform that lost a field across its own rows, told from one that never had it.

COVERS = ['adapters/fieldaudit.py']

WHY THE THRESHOLDS ARE THE SUBJECT. Each rule was separated after the shape before it hid
something: a bare total of three failed a run on four rows that were four platforms each
publishing an update the way they publish it, and the rows stating no access were quietly consuming
the tripwire that was meant to catch a lost title. A threshold nobody tests is a number somebody
picked.
"""
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fieldaudit                                                       # noqa: E402
import testkit                                                          # noqa: E402

COVERS = ["adapters/fieldaudit.py"]


def _db(rows_):
    """A store holding just the two tables the audit reads. `rows_` is (plat, ep, author, modes)."""
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE release (id TEXT PRIMARY KEY, work TEXT, platform TEXT, "
               "instalment TEXT, author TEXT, work_raw TEXT, provenance TEXT)")
    db.execute("CREATE TABLE release_access_mode (release TEXT, seq INT, mode TEXT)")
    for i, (plat, ep, author, modes) in enumerate(rows_):
        db.execute("INSERT INTO release VALUES (?,?,?,?,?,?,'attested')",
                   (f"r{i}", f"w{i}", plat, ep, author, f"work {i}"))
        for k in range(modes):
            db.execute("INSERT INTO release_access_mode VALUES (?,?,?)", (f"r{i}", k, "free"))
    # A ROW THAT IS NOT ATTESTED IS NOT AUDITED. A predicted or reported row states no chapter, so
    # counting one as a lost field would report a debt nobody owes.
    db.execute("INSERT INTO release VALUES ('r-pred','w','ある platform',NULL,NULL,'w','predicted')")
    db.commit()
    return db


def main(s):
    # ── WHAT THE AUDIT READS ──────────────────────────────────────────────────────────────────
    got = fieldaudit.rows(_db([("マガポケ", "第1話", "作者", 1), ("マガポケ", "", "作者", 0)]))
    s.eq(len(got), 2, "only attested rows are audited")
    s.eq([r["access"] for r in got], [1, 0], "and each carries how many access modes it states")

    # ── A ROW MISSING A NAME, AND ONE MISSING ONLY ITS PRICE ──────────────────────────────────
    #
    # The two are counted apart because they are different faults. An empty string and whitespace
    # are both "no episode title": a selector that matches the wrong element returns the element.
    mixed = fieldaudit.rows(_db([
        ("A", "第1話", "作者", 1),      # complete
        ("A", "", "作者", 1),           # no episode title
        ("A", "   ", "作者", 1),        # whitespace is not a title either
        ("A", "第2話", None, 1),        # no author
        ("A", "第3話", "作者", 0),      # named, states no access
    ]))
    s.eq(len(fieldaudit.unnamed(mixed)), 3, "a blank, a whitespace title and a missing author")
    s.eq([r["ep"] for r in fieldaudit.unpriced(mixed)], ["第3話"],
         "and a row is unpriced only where it is otherwise complete")

    # ── A MOVED SELECTOR TAKES OUT ITS OWN PLATFORM ───────────────────────────────────────────
    #
    # Three rows is the floor because a platform publishing one or two updates says nothing either
    # way, and half its rows is what tells a moved selector from a work published without a byline.
    lost = fieldaudit.rows(_db([("A", "", "作者", 1)] * 3 + [("A", "第1話", "作者", 1)]))
    s.eq(fieldaudit.moved(lost), [("A", 3, 4)], "three of four rows is a platform that lost it")
    s.eq(fieldaudit.moved(fieldaudit.rows(_db([("A", "", "作者", 1)] * 2
                                              + [("A", "第1話", "作者", 1)] * 2))), [],
         "two is under the floor, whatever share of the platform it is")
    s.eq(fieldaudit.moved(fieldaudit.rows(_db([("A", "", "作者", 1)] * 3
                                              + [("A", "第1話", "作者", 1)] * 4))), [],
         "and three of seven is a handful rather than a selector")

    # SCATTERED ACROSS PLATFORMS IS NOT A MOVED SELECTOR, which is the case that failed a run: four
    # rows on three platforms in two shapes, each publishing an update the way it does.
    scattered = fieldaudit.rows(_db([
        ("ニコニコ漫画", "", "作者", 1), ("ニコニコ漫画", "", "作者", 1),
        ("ヤンジャン+", "読み切り", None, 1), ("きら星ポータル", "読み切り", None, 1)]
        + [("ニコニコ漫画", "第1話", "作者", 1)] * 8))
    s.eq(fieldaudit.moved(scattered), [], "no platform is over its share")
    s.eq(fieldaudit.findings(scattered), [], "so the run is not stopped")

    # ── AND A DRIFT ACROSS EVERYTHING STILL TRIPS ─────────────────────────────────────────────
    #
    # A change to a shared renderer shows up as a few rows everywhere and no platform over its
    # share, which per-platform counting cannot see.
    wide = fieldaudit.rows(_db(
        [(f"P{i}", "", "作者", 1) for i in range(fieldaudit.SPREAD + 1)]
        + [(f"P{i}", "第1話", "作者", 1) for i in range(fieldaudit.SPREAD + 1) for _ in range(3)]))
    s.eq(fieldaudit.moved(wide), [], "one lost row per platform is nobody's selector")
    s.eq(len(fieldaudit.findings(wide)), 1, "and the spread rule is what catches it")
    s.check("spread too widely" in fieldaudit.findings(wide)[0],
            "saying which of the three rules fired")

    # ── ROWS STATING NO ACCESS ARE THEIR OWN NUMBER ───────────────────────────────────────────
    #
    # マガポケ is read by two routes and one of them carries access on none of its chapters, so a
    # work reached only by the feed states none. Counted with the lost titles, those consumed the
    # tripwire meant to catch the first row that really lost one.
    quiet = fieldaudit.rows(_db([("マガポケ", "第1話", "作者", 0)] * fieldaudit.NO_ACCESS))
    s.eq(fieldaudit.findings(quiet), [], "the route asymmetry is allowed for")
    louder = fieldaudit.rows(_db([("マガポケ", "第1話", "作者", 0)] * (fieldaudit.NO_ACCESS + 1)))
    s.eq(len(fieldaudit.findings(louder)), 1, "one row past it is a finding")
    s.check("state no access" in fieldaudit.findings(louder)[0], "and says so in its own words")

    # ── THE HEALTHY ANSWER ────────────────────────────────────────────────────────────────────
    s.eq(fieldaudit.findings(fieldaudit.rows(_db([("A", "第1話", "作者", 1)] * 40))), [],
         "a capture with every field on every row stops nothing")
    s.eq(fieldaudit.findings([]), [],
         "and a run that captured nothing has no field to have lost, which the count says instead")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
