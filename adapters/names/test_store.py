#!/usr/bin/env python3
"""store.py: what counts as the same reading, and what counts as a conflict."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import store


def main(s):
    # Word boundaries are a presentation choice, not a disagreement. A kana surface carries no
    # space; a source that separates family from given does. Treating that as a conflict filled the
    # review list with 23 non-conflicts, and a review list nobody trusts is a review list nobody
    # reads.
    s.check(store.same_reading("アオタユキコ", "アオタ ユキコ"), "spacing alone is not a conflict")
    s.check(store.same_reading("アオタ　ユキコ", "アオタユキコ"),
            "a full-width space is not a conflict either")
    s.check(store.same_reading("ユリ", "ユリ"), "identical readings agree")

    # A real disagreement must still register, or the check is worthless in the other direction.
    s.check(not store.same_reading("アオタユキコ", "アオタミチコ"),
            "different readings are a genuine conflict")
    s.check(not store.same_reading("ユリ", "サクラ"), "unrelated readings disagree")

    s.eq(len(store.today()), 10, "today() is an ISO date")
    s.check(store.today().count("-") == 2, "and is dashed, so it sorts as a string")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "store"))
