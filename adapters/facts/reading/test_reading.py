#!/usr/bin/env python3
"""facts/reading: what may be believed about how a name is read, and on whose word.

COVERS = ['adapters/facts/reading/__init__.py']

Every assertion here pins a ruling somebody made. A row changed without a ruling behind it fails.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))
import testkit                                                          # noqa: E402
from facts import reading as r                                          # noqa: E402


def main(s):
    # A NATIONAL CATALOGUING AUTHORITY MAY STATE A READING. The NDL records a transcription beside
    # the creator for every book it holds, and 79 of 82 author readings settled that way came from
    # it. It is the only route that reaches most pen names at all.
    s.check(r.may_state("stated", "national-library"), "the national library may state a reading")
    s.check(r.may_state("stated", "publisher-jp"), "and so may the publisher")
    s.check(r.may_state("stated", "author"), "and the artist's own page, which is better and rarer")

    # THE OWNER'S RULING OF 2026-08-09, made and reversed inside one day. A pass admitted Wikidata
    # as `stated`, arguing a reading is a transcription. The owner overruled it: Wikidata is
    # noncanonical and raises the floor on romaji without overcoming the fallback basis.
    s.check(not r.may_state("stated", "community-db"),
            "a community database does not STATE a reading")
    s.check(r.may_state("community-printed", "community-db"),
            "it has a row of its own, which is what noncanonical means here")

    # `researched` MEANS A REVIEWER WEIGHED EVIDENCE, so it admits the kinds that are evidence and
    # not attribution. A reading with no reasoning behind it is a guess wearing a label.
    s.check(r.may_state("researched", "community-db"), "a wiki is evidence a reviewer may weigh")
    s.check(not r.may_state("researched", "national-library"),
            "a library needs no reviewer to speak for it")

    # A KANA TITLE IS ITS OWN READING, and nobody stated it because nobody had to.
    s.check(r.may_state("surface", "derived"), "a kana surface derives its own reading")

    # `states_a_reading` IS THE UNION OVER THE STATED BASES, and it is exactly the list check.py
    # used to hold by hand. That copy had drifted when somebody looked at it.
    s.eq(set(r.states_a_reading()), set(r.kinds_for("stated")),
         "what states a reading is the stated row, with nothing added")
    s.check("community-db" not in r.states_a_reading(),
            "and the overruled kind is not in it")

    # A BASIS OR A KIND NOBODY RULED ON IS BELIEVED FOR NOTHING. A typo is exactly this case.
    s.eq(r.kinds_for("stated "), (), "a basis nobody ruled on admits no source")
    s.check(not r.may_state("stated", "wikipedia"), "and an unruled kind is refused")
    s.check(not r.may_state(None, None), "as is a missing pair")

    # THE STATED BASES ARE A SUBSET OF THE RULED ONES, which is what made the hand-written copy
    # possible to write and possible to get wrong.
    s.check(set(r.STATED_BASES) <= set(r.bases()), "every stated basis is a ruled basis")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
