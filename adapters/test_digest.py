#!/usr/bin/env python3
"""digest.py: the week's runs, failing sources, budget moves and naming usage, in one text.

COVERS = ['adapters/digest.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import digest as dg                                                     # noqa: E402


def main(s):
    moves = dg.budget_moves({"a": 1, "b": 10, "c": 5}, {"a": 1, "b": 4, "c": 6, "d": 2})
    s.eq([m[0] for m in moves], ["b", "c", "d"], "only moved budgets are listed, largest first")
    s.eq(moves[0], ("b", 10, 4), "the largest move first")

    health = {"sources": {
        "comicboost": {"consecutive": 4, "failing_since": "2026-10-12", "error": "HTTP 503"},
        "kadokomi": {"consecutive": 0, "last_failed": "2026-10-13", "last_ok": "2026-10-14"},
        "magapoke": {"consecutive": 0, "last_ok": "2026-10-14"}}}
    usage = [{"date": "2026-10-14", "turns": 12, "input_tokens": 1000, "output_tokens": 200,
              "named": 3, "inducted": 1}]
    text = dg.compose("2026-10-08", "2026-10-15", 14, health, moves, usage)
    s.check("`comicboost`: 4 run(s) in a row since 2026-10-12. HTTP 503" in text,
            "a source still failing is named with how long and why")
    s.check("`kadokomi`, last failed 2026-10-13" in text, "and one that wobbled and recovered")
    s.check("magapoke" not in text, "but not one that never failed")
    s.check("`b`: 10 to 4" in text, "budget moves are listed")
    s.check("1 run(s), 12 turns, 1,000 input and 200 output tokens; 3 name(s) written and 1 work(s)"
            in text, "and the naming job's usage is totalled")
    # A BUDGET LEFT OVER ITS VALUE is listed from the store, largest excess first.
    import sqlite3, tempfile
    with tempfile.TemporaryDirectory() as d:
        db = pathlib.Path(d) / "s.sqlite"
        c = sqlite3.connect(db)
        c.execute("CREATE TABLE check_result (kind TEXT, name TEXT, value INTEGER, budget INTEGER)")
        c.executemany("INSERT INTO check_result VALUES (?,?,?,?)",
                      [("budget", "a", 10, 6), ("budget", "b", 3, 3), ("budget", "c", 9, 8),
                       ("invariant", "d", 2, None), ("budget", "e", None, 4)])
        c.commit()
        s.eq(dg.over(db), [("a", 10, 6), ("c", 9, 8)], "budgets over their value, largest first")
        s.eq(dg.over(pathlib.Path(d) / "missing.sqlite"), [], "no store is no list, not a crash")
    text2 = dg.compose("2026-10-08", "2026-10-15", 1, {}, [], [], above=[("a", 10, 6)])
    s.check("`a`: 10 against 6" in text2, "and the digest names each one")

    quiet = dg.compose("2026-10-08", "2026-10-15", 0, {}, [], [])
    s.check("None did, so the schedule or the workflow needs a look." in quiet,
            "a week with no runs says so rather than reading as a quiet week")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "digest"))
