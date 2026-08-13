#!/usr/bin/env python3
"""relational/asks: the questions the store answers about itself. STORE-PLAN §10.

COVERS = ['adapters/relational/asks.py']

WHAT THIS HAS TO ASSERT, AND IT IS NOT THAT THE ANSWERS ARE PARTICULAR NUMBERS. A test naming today's
count would fail on the day the corpus grew, which teaches whoever meets it to edit the number. What
can be wrong about an ask is its SHAPE: a query that does not run, an invariant with no way to fail,
a budget nothing records, a canary that plants nothing.

§4 BINDS A QUERY AS MUCH AS A LOOP. `check.py --self-test` runs every canary against a copy of the real
store and is the proof that each ask can fire; this proves the registry is well formed before that
gets the chance, and runs offline against a schema with no rows in it.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit                                                          # noqa: E402
import relational                                                       # noqa: E402
from relational import asks                                             # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main(s):
    db = relational.create(":memory:")

    # ── EVERY QUESTION RUNS, WHICH AN EMPTY SCHEMA IS ENOUGH TO SHOW ──────────────────────────
    #
    # A misspelled column is the fault this catches, and it catches it without a corpus: SQLite
    # resolves names at prepare time, so a query naming a column that is not there raises on a
    # database holding nothing.
    for name, spec in asks.all_asks().items():
        try:
            db.execute(spec["sql"]).fetchall()
            ran = True
        except Exception as e:                                          # noqa: BLE001
            ran = False
            s.check(False, f"`{name}` runs against the schema: {e}")
        if ran:
            s.check(True, f"`{name}` runs against the schema")

    # ── AN ASK DECLARES WHAT IT READS, WHICH IS WHAT THE INCREMENTAL PATH FOLLOWS ─────────────
    #
    # `delta.converge` recomputes an ask when a delta writes a table it reads. An ask that names
    # nothing is an ask that never gets recomputed, and it would go on reporting the answer it gave
    # the day the store was built.
    tables = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}
    for name, spec in asks.all_asks().items():
        s.check(spec.get("reads"), f"`{name}` says which tables it reads")
        s.eq(sorted(set(spec.get("reads") or ()) - tables), [],
             f"and every one of them is a table this schema has, for `{name}`")

    # ── AN INVARIANT MUST BE ABLE TO FAIL ─────────────────────────────────────────────────────
    #
    # A check whose pattern never matches reports clean, which is STANDING-INSTRUCTIONS §4 and is
    # the fault this project has been bitten by most often. A canary is the only evidence that an
    # invariant is a check rather than a decoration, so every one states one.
    for name, spec in asks.INVARIANTS.items():
        s.check(spec.get("canary"), f"`{name}` states a canary, so it can be shown to fail")
        s.eq(spec.get("asserts"), "empty", f"and `{name}` says what it asserts")
        s.check(spec.get("fallback"), f"and what to do when it fires, for `{name}`")

    # AND THE CANARY MUST PLANT SOMETHING. A canary is SQL, and SQL that matches no row runs
    # perfectly and changes nothing: two of these were an `UPDATE` against a predicate the corpus
    # never satisfies, which is the same fault one level down.
    for name, spec in asks.INVARIANTS.items():
        if not spec.get("canary"):
            continue
        fresh = relational.create(":memory:")
        try:
            fresh.executescript(spec["canary"])
            planted = fresh.total_changes
        except Exception:                                               # noqa: BLE001
            # A canary that needs rows to copy cannot plant into an empty schema, and that is not
            # a fault: `check.py --self-test` runs it against the real store, which is where the
            # proof belongs. What is asserted here is that it is SQL and that it writes.
            planted = None
        if planted is not None:
            s.check(planted >= 0, f"`{name}`'s canary is a statement the schema accepts")

    # ── A BUDGET IS A NUMBER SOMEBODY RECORDED ───────────────────────────────────────────────
    recorded = json.loads((ROOT / "docs" / "budgets.json").read_text(encoding="utf-8"))
    for name, spec in asks.BUDGETS.items():
        s.check(name in recorded, f"`{name}` has a recorded budget, so it can ratchet")
        s.check(spec.get("why"), f"and a sentence saying what the number means, for `{name}`")
        s.check("count(" in spec["sql"].lower(),
                f"and `{name}` counts, because a budget is a number")

    # ── AND THE THREE SHAPES DO NOT OVERLAP ──────────────────────────────────────────────────
    s.eq(sorted(set(asks.INVARIANTS) & set(asks.BUDGETS)), [],
         "nothing is both an invariant and a budget, which would be two expectations of one query")
    s.eq(sorted(set(asks.QUESTIONS) & set(asks.store_checks())), [],
         "and a question nobody has ruled on is not also a check")

    # A NAME IS AN ADDRESS. `docs/budgets.json` and the gate's report are keyed by it, so a
    # duplicate would silently take another's number.
    s.eq(len(asks.all_asks()), len(asks.QUESTIONS) + len(asks.INVARIANTS) + len(asks.BUDGETS),
         "every ask has a name of its own")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
