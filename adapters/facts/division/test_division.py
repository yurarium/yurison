#!/usr/bin/env python3
"""facts/division: what standing a division has.

COVERS = ['adapters/facts/division/__init__.py']

The four sets this replaces were consistent when it was written, and the point is that they stay so
by construction. These assertions pin the rulings the table encodes, so a column changed without a
ruling behind it fails here.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))
import testkit                                                          # noqa: E402
from facts import division as d                                         # noqa: E402


def main(s):
    # A SOURCE THAT STATED THE READING STATED THE DIVISION WITH IT. A catalogue printing
    # `美鈴, ちょこ` gave both at once, so it owes no separate citation.
    for b in ("stated", "researched", "surface"):
        s.check(d.cites_its_source(b), f"{b} arrives already cited")
        s.check(d.may_donate(b), f"{b} may lend its division")
        s.check(not d.is_marked(b), f"{b} needs no mark")

    # THE OWNER'S RULING OF 2026-08-09, and the correction to it the same day: Wikidata raises the
    # floor on a romanisation WITHOUT overcoming the fallback basis. So it is shown and lent, and
    # it never counts as anybody having stated where a person's name divides.
    s.check(not d.cites_its_source("community-printed"), "a community database states nothing")
    s.check(d.may_donate("community-printed"), "and may still lend, because it raises the floor")
    s.check(d.is_marked("community-printed"), "and a reader is told")
    s.check(d.counted_uncited("community-printed"), "and it is counted, not blocked")

    # A ROMANISATION READ BACKWARDS is a reconstruction of a reconstruction. Never lent.
    s.check(not d.may_donate("back-converted"), "a back-converted division is never lent")
    s.check(d.counted_uncited("back-converted"), "the few that exist are counted")

    # A GUESS IS RETIRED, NOT TOLERATED. のぴやか梢 was shown as `No Pi Ya Ka Kozue` because an
    # analyser split every kana and the record asserted it. A guessed division is a false claim
    # about a real person's name, which is worse than no division.
    s.check(not d.cites_its_source("analyser"), "an analyser cites nothing")
    s.check(not d.may_donate("analyser"), "and lends nothing")
    s.check(not d.counted_uncited("analyser"), "and is not tolerated as a counted residue")

    # THE RELATIONSHIPS THE FOUR SETS USED TO HOLD BY HAND. These are now facts about one table,
    # which is the whole point, so they are cheap to assert and would have been impossible to
    # violate quietly.
    s.check(d.bases_where("cited") <= d.bases_where("donates"),
            "anything cited may be lent")
    s.check(not (d.bases_where("cited") & d.bases_where("marked")),
            "nothing both cites its source and needs a mark")
    s.check(not (d.bases_where("cited") & d.bases_where("counted")),
            "a cited division is not also counted as uncited")

    # AN UNKNOWN BASIS ANSWERS NO TO EVERYTHING. A record carrying a basis nobody has ruled on must
    # not be believed by default, and a typo in a basis name is exactly that case.
    for q in (d.cites_its_source, d.may_donate, d.is_marked, d.counted_uncited):
        s.check(not q("stated "), "a basis nobody ruled on is believed for nothing")
        s.check(not q(None), "and neither is a missing one")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
