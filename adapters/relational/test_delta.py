#!/usr/bin/env python3
"""delta: a change is applied without a recompile, and only a moved answer cascades.

COVERS = ['adapters/relational/delta.py']

ONE FOCUSED TEST PER DELTA KIND, because the correctness argument is convergence and convergence is
only worth anything if every kind of change reaches it. Deletion and retraction get the most
attention: an output whose input disappeared has nothing left to notice it, and a digest that is
never recomputed never moves.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit                                                          # noqa: E402
import relational                                                       # noqa: E402
from relational import delta                                            # noqa: E402


def _db(d):
    db = delta.ensure(relational.load_rulings(relational.create(pathlib.Path(d) / "t.db")))
    db.execute("INSERT INTO work (id, title) VALUES ('w00001','T')")
    db.execute("INSERT INTO work (id, title) VALUES ('w00002','U')")
    db.execute("INSERT INTO credit (id, surface, kind) VALUES ('c00001','X','person')")
    db.execute("INSERT INTO credit (id, surface, kind) VALUES ('c00002','Y','person')")
    delta.recompute(db)
    return db


def main(s):
    with tempfile.TemporaryDirectory() as d:
        db = _db(d)

        # INSERT. A work gains a credit, and exactly the derivations reading that table move.
        assert delta.write(db, "work_credit", {"work": "w00001", "credit": "c00001"}, {"role": "art"})
        moved, passes = delta.converge(db, {"work_credit"})
        s.check("works naming nobody" in moved, "a work that now names somebody changes the count")
        s.eq(passes, 1, "and it settles in one pass")

        # THE SAME WRITE AGAIN IS A NO-OP, which is the whole design in one assertion.
        s.check(not delta.write(db, "work_credit", {"work": "w00001", "credit": "c00001"},
                                {"role": "art"}),
                "a write producing the value already there changes nothing")
        s.eq(delta.converge(db, {"work_credit"})[0], [],
             "so nothing downstream is recomputed into a new answer")

        # UPDATE. The role moves; no derivation here reads it, so the cascade is empty even though
        # an input plainly changed. Gating on input change is the failure this avoids.
        s.check(delta.write(db, "work_credit", {"work": "w00001", "credit": "c00001"},
                            {"role": "story"}),
                "a real change to a row is a change")
        s.eq(delta.converge(db, {"work_credit"})[0], [],
             "an input that moved without moving any answer cascades nothing")

        # DELETE. The input disappears and the count has to notice.
        before = delta.value(db, "works naming nobody")
        s.check(delta.drop(db, "work_credit", {"work": "w00001", "credit": "c00001"}),
                "the row was there and is gone")
        s.check("works naming nobody" in delta.converge(db, {"work_credit"})[0],
                "a deleted input moves the answer that rested on it")
        s.ne(delta.value(db, "works naming nobody"), before, "and the recorded answer moved back")
        s.check(not delta.drop(db, "work_credit", {"work": "w00001", "credit": "c00001"}),
                "deleting what is already gone is not a change")

        # MERGE. Two credits turn out to be one person: the rows naming the second are repointed
        # and the second is dropped. `credits named by more than one work` is what should move.
        db.execute("INSERT INTO work_credit (work, credit, role) VALUES ('w00001','c00001','art')")
        db.execute("INSERT INTO work_credit (work, credit, role) VALUES ('w00002','c00002','art')")
        delta.recompute(db)
        s.eq(delta.value(db, "credits named by more than one work"), [[0]],
             "two credits on one work each, so neither is named twice")
        db.execute("UPDATE work_credit SET credit = 'c00001' WHERE credit = 'c00002'")
        db.execute("DELETE FROM credit WHERE id = 'c00002'")
        moved, _p = delta.converge(db, {"work_credit", "credit"})
        s.check("credits named by more than one work" in moved,
                "a merge makes one credit answer for two works, and the count says so")
        s.eq(delta.value(db, "credits named by more than one work"), [[1]], "which is one")

        # DIVIDE, the opposite: one credit was two people. A wrong join erases a person and a wrong
        # split invents one, so both directions have to be reachable and both have to be noticed.
        db.execute("INSERT INTO credit (id, surface, kind) VALUES ('c00003','Y','person')")
        db.execute("UPDATE work_credit SET credit = 'c00003' WHERE work = 'w00002'")
        moved, _p = delta.converge(db, {"work_credit", "credit"})
        s.check("credits named by more than one work" in moved, "dividing moves it back")
        s.eq(delta.value(db, "credits named by more than one work"), [[0]], "to none")

        # RETRACT. A claim is withdrawn rather than corrected, which leaves no row to look at.
        db.execute("INSERT INTO surface (kind, folded) VALUES ('title','ゆり')")
        db.execute("INSERT INTO names (surface, kind, work) VALUES (1,'title','w00001')")
        db.execute("INSERT INTO claim (surface, kind, predicate, value, basis, source, source_kind)"
                   " VALUES (1,'title','reading','ヨミ','surface','x','derived')")
        db.execute("INSERT INTO claim (surface, kind, predicate, value, basis, source, source_kind)"
                   " VALUES (1,'title','reading','ベツ','surface','y','derived')")
        s.check("names two sources disagree about" in delta.converge(db, {"claim"})[0],
                "two sources on one predicate is a disagreement")
        db.execute("DELETE FROM claim WHERE value = 'ベツ'")
        s.check("names two sources disagree about" in delta.converge(db, {"claim"})[0],
                "and retracting one ends it, which is the case a stale digest would miss")
        s.eq(delta.value(db, "names two sources disagree about"), [[0]], "the answer is none")

        # A DERIVATION NOBODY TOUCHED IS NOT RECOMPUTED INTO A NEW ANSWER, which is what makes the
        # gating worth having rather than a longer way to run every query.
        s.eq(delta.converge(db, {"nothing_reads_this"}), ([], 0),
             "a delta touching a table no derivation reads costs no passes")

    # CONVERGENCE OVER A CHAIN. Nothing in the real registry depends on another derivation today,
    # so the loop would be untested by the tree as it stands. This is the shape it exists for.
    with tempfile.TemporaryDirectory() as d:
        db = _db(d)
        chain = {
            "a": {"sql": "SELECT count(*) FROM work", "reads": ("work",)},
            "b": {"sql": "SELECT count(*) FROM work", "reads": (), "depends_on": ("a",)},
            "c": {"sql": "SELECT count(*) FROM work", "reads": (), "depends_on": ("b",)},
        }
        moved, passes = delta.converge(db, {"work"}, chain)
        s.eq(sorted(moved), ["a", "b", "c"], "a change follows the chain to its end")
        s.eq(passes, 3, "in one pass per link")
        s.eq(delta.converge(db, {"work"}, chain), ([], 1),
             "and running it again moves nothing, which is the fixed point")

        # A LOOP HAS TO STOP RATHER THAN SPIN. A registry someone writes wrong must fail loudly.
        cyc = {"x": {"sql": "SELECT random()", "reads": ("work",), "depends_on": ("y",)},
               "y": {"sql": "SELECT random()", "reads": (), "depends_on": ("x",)}}
        try:
            delta.converge(db, {"work"}, cyc, limit=4)
            s.check(False, "a registry that cannot settle is refused")
        except RuntimeError:
            s.check(True, "a registry that cannot settle is refused")

    s.eq(sorted(delta.KINDS), sorted(["insert", "update", "delete", "merge", "divide", "retract"]),
         "and every delta kind named above has a case here")

    # THE COMPARISON THAT SHARES NOTHING WITH THE DECLARATIONS. `--equivalent` sets a store that has
    # only been updated beside one compiled from source. It cannot be run here, since a rebuild
    # reads data/build and this suite is offline, so the two pieces it rests on are tested instead:
    # a digest per table that moves when a row does, and a report that names rows rather than counts.
    with tempfile.TemporaryDirectory() as da, tempfile.TemporaryDirectory() as db2:
        a, b = _db(da), _db(db2)
        s.eq(relational._table_digests(a), relational._table_digests(b),
             "two stores built the same way digest the same")
        b.execute("INSERT INTO work (id, title) VALUES ('w00003','V')")
        s.ne(relational._table_digests(a)["work"], relational._table_digests(b)["work"],
             "and one extra row moves the digest of its table alone")
        s.eq(relational._table_digests(a)["credit"], relational._table_digests(b)["credit"],
             "leaving every other table where it was")
        rows = relational._first_differing_rows(a, b, "work")
        s.check(any("w00003" in r for r in rows), "the report names the row and not the count")
        s.check(any(r.startswith("only in a rebuild") for r in rows),
                "and says which side it is missing from")


    # ── RECONCILE: A WHOLE TABLE BROUGHT TO THE ROWS THAT SHOULD BE THERE, §7 ────────────────
    #
    # THE PRODUCTION CALLER `write` AND `drop` NEVER HAD. A capture knows what it saw and does not
    # know what has GONE, so the updater is handed the rows that should be there and works out both
    # directions itself. What is asserted here is each of the three answers a row can get.
    with tempfile.TemporaryDirectory() as d:
        db = _db(d)
        db.execute("INSERT INTO work_credit (work, credit, role) VALUES ('w00001','c00001','art')")
        db.execute("INSERT INTO work_credit (work, credit, role) VALUES ('w00002','c00002','art')")
        delta.recompute(db)

        rows = [{"work": "w00001", "credit": "c00001", "role": "art"},     # unchanged
                {"work": "w00002", "credit": "c00002", "role": "story"}]   # changed
        written, dropped, unchanged = delta.reconcile(
            db, "work_credit", ["work", "credit"], rows, ["role"])
        s.eq((written, dropped, unchanged), (1, 0, 1),
             "a row that moved is written, a row that did not is left alone")
        s.eq(db.execute("SELECT role FROM work_credit WHERE work = 'w00002'").fetchone()[0],
             "story", "and the value that moved is the one that is there now")

        # AND THE ROW THE CAPTURE NO LONGER STATES IS DROPPED, which is the delta kind these
        # systems get wrong: an output whose input disappeared has nothing left to notice it.
        written, dropped, unchanged = delta.reconcile(
            db, "work_credit", ["work", "credit"], rows[:1], ["role"])
        s.eq((written, dropped, unchanged), (0, 1, 1), "a row no longer stated is dropped")
        s.eq(db.execute("SELECT count(*) FROM work_credit").fetchone()[0], 1,
             "and it is gone from the table rather than marked")
        moved, _passes = delta.converge(db, {"work_credit"})
        s.check("works naming nobody" in moved,
                "AND THE DROP CASCADES, which an updater that only ever wrote would never see")

        # A ROW THAT IS ALL KEY AND NO VALUE still exists or does not. `print_row_record` is one,
        # and `SELECT  FROM` is a syntax error, so this asked for nothing and raised.
        db.execute("INSERT INTO print_row (id, work, record) VALUES (1,'w00001','r1')")
        written, dropped, _u = delta.reconcile(
            db, "print_row_record", ["print_row", "record"], [{"print_row": 1, "record": "r1"}])
        s.eq((written, dropped), (1, 0), "a row with no value columns can still be written")
        written, dropped, unchanged = delta.reconcile(
            db, "print_row_record", ["print_row", "record"], [{"print_row": 1, "record": "r1"}])
        s.eq((written, dropped, unchanged), (0, 0, 1), "and writing it again changes nothing")

    # ── AND THE INFERENCE MUST NOT PUT THE ADDRESS BACK ──────────────────────────────────────
    #
    # THE FAULT THIS IS WRITTEN FROM COST A NIGHT'S RUN. `reconcile` infers the value columns from a
    # row where the caller names none, and the strip that keeps a rowid out of a write ran BEFORE
    # that inference, so the inference rebuilt the list from the row and put `id` back. `claim` is
    # the one table whose natural key is every column but its rowid, so it is the only caller that
    # reaches the inference, and it only inserts when a claim is NEW: an update that brought in one
    # new name died on `UNIQUE constraint failed: claim.id`, having carried the other compile's
    # number across.
    with tempfile.TemporaryDirectory() as d:
        db = _db(d)
        db.execute("INSERT INTO surface (kind, folded) VALUES ('author','x')")
        sid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        key = ["surface", "kind", "predicate", "value", "basis"]
        # A ROW CARRYING AN `id` FROM SOMEWHERE ELSE, which is what a scratch compile hands over.
        row = {"id": 9999, "surface": sid, "kind": "author", "predicate": "reading",
               "value": "カナリア", "basis": "analyser"}
        written, _dropped, _u = delta.reconcile(db, "claim", key, [row], None, {"id"})
        s.eq(written, 1, "a row whose key is every column but the rowid is written")
        s.ne(db.execute("SELECT id FROM claim WHERE value = 'カナリア'").fetchone()[0], 9999,
             "AND THE STORE GAVE IT ITS OWN ADDRESS, rather than the one the other compile used")
        written, _dropped, unchanged = delta.reconcile(db, "claim", key, [row], None, {"id"})
        s.eq((written, unchanged), (0, 1),
             "and writing it again changes nothing, which a carried id would have made impossible")

    # ── THE KEY A RECONCILE ADDRESSES A ROW BY IS NOT THE ROWID ──────────────────────────────
    #
    # `claim.id` is handed out in insertion order, so two compiles of one corpus number the same
    # claim differently and a reconcile keyed on it would call every row changed. What identifies a
    # claim is the unique index §5b gave it.
    with tempfile.TemporaryDirectory() as d:
        db = _db(d)
        s.check("id" not in relational.natural_key(db, "claim"),
                "a claim is addressed by what it says, not by the order it was inserted in")
        s.eq(relational.natural_key(db, "work"), ["id"],
             "a work is addressed by the identifier the registry minted")
        s.eq(sorted(relational.natural_key(db, "work_credit")), ["credit", "role", "work"],
             "and an edge by the three columns its unique index names")

        # ── AN INDEX WRITTEN AS AN EXPRESSION STILL NAMES ITS COLUMNS ────────────────────────
        #
        # `PRAGMA index_info` gives None for `coalesce(record, 0)`, and this used to give up and
        # key on EVERY COLUMN, which addresses more rows than the index does. The reconcile then
        # wrote two rows the index holds as one and SQLite refused the commit: seven tables in this
        # schema are indexed that way and every one of them was refused on most builds, the run
        # recovering by rebuilding the file whole. The incremental path was doing nothing on
        # `claim`, `state_claim`, `romanisation`, `ruby`, `names`, `admission` and `work_credit`.
        #
        # `work_credit` ABOVE PASSED FOR THE WRONG REASON, which is how this stayed invisible: its
        # only other column is the rowid, so every-column and the index happen to agree. The tables
        # below are the ones where they do not.
        s.eq(relational.natural_key(db, "romanisation"), ["surface", "record", "style"],
             "the expression's own column is what the key names, and `value` is not in it")
        s.eq(relational.natural_key(db, "state_claim"), ["work", "source", "says"],
             "and a claim about a state is addressed by the three the index declares")
        s.check("note" not in relational.natural_key(db, "claim"),
                "a claim's key is its identity index rather than everything it states")

        # ── A COLUMN POINTING AT ITS OWN TABLE IS RESOLVED AFTER THE ROWS EXIST ──────────────
        #
        # `surface.alias_of` names another surface, and the map from the scratch's numbers to this
        # store's is built FROM the reconcile, so on the way in there is nothing to translate it
        # with. It carried the scratch's id across untranslated, and where that number happened to
        # be the live id of the row carrying it, `alias_of IS NULL OR alias_of <> id` refused the
        # whole commit. The full rebuild resolves aliases in a second pass for this reason.
        db.execute("INSERT INTO surface (kind, folded) VALUES ('title', 'canon')")
        db.execute("INSERT INTO surface (kind, folded) VALUES ('title', 'variant')")
        canon = db.execute("SELECT id FROM surface WHERE folded = 'canon'").fetchone()[0]
        variant = db.execute("SELECT id FROM surface WHERE folded = 'variant'").fetchone()[0]
        db.execute("UPDATE surface SET alias_of = ? WHERE id = ?", (canon, variant))
        s.eq(db.execute("SELECT alias_of FROM surface WHERE id = ?", (variant,)).fetchone()[0],
             canon, "a variant points at the spelling it stands for")
        import sqlite3 as _sq
        try:
            db.execute("UPDATE surface SET alias_of = id WHERE id = ?", (variant,))
            s.check(False, "no surface may stand for itself")
        except _sq.IntegrityError:
            s.check(True,
                    "no surface may stand for itself, which is the check the delta was tripping")

        # ── AND THE DELTA CARRIES IT ACROSS, ONCE, AND THEN STOPS ────────────────────────────
        #
        # TWO FAULTS LIVED HERE AND THE SECOND WAS HIDDEN BY THE FIRST. `surface` declares a
        # composite self-reference, `(alias_of, wants, kind) REFERENCES surface (id, retired,
        # kind)`, so deferring every column of a key that names this table deferred `wants`, which
        # is GENERATED and may not be inserted, and `kind`, which is half the natural key and
        # stopped being compared. Only `alias_of` actually holds this table's address.
        #
        # AND DEFERRING IT LEAVES `surface` STATING NOTHING, so `reconcile` infers the value
        # columns back off the row it was handed. A row still carrying the key wrote NULL over
        # every alias on every build and the second pass put them back: a store that had not moved
        # reported 118 rows written, for ever. The row must not carry the column at all.
        scratch = relational.create(":memory:")
        scratch.execute("INSERT INTO surface (kind, folded) VALUES ('title', 'canon2')")
        scratch.execute("INSERT INTO surface (kind, folded) VALUES ('title', 'variant2')")
        c2 = scratch.execute("SELECT id FROM surface WHERE folded = 'canon2'").fetchone()[0]
        v2 = scratch.execute("SELECT id FROM surface WHERE folded = 'variant2'").fetchone()[0]
        scratch.execute("UPDATE surface SET alias_of = ? WHERE id = ?", (c2, v2))
        live = relational.create(":memory:")
        counts, refused, _moved = relational.apply(live, fresh=scratch)
        s.eq(refused, [], "a scratch holding an alias is applied without the commit being refused")
        got = live.execute("SELECT alias_of FROM surface WHERE folded = 'variant2'").fetchone()[0]
        mine = live.execute("SELECT id FROM surface WHERE folded = 'canon2'").fetchone()[0]
        s.eq(got, mine,
             "and the alias names THIS store's canonical row, not the number the scratch used")
        counts2, refused2, _m2 = relational.apply(live, fresh=scratch)
        s.eq(refused2, [], "applying the same scratch again refuses nothing")
        s.eq(counts2.get("surface", (0, 0, 0))[0], 0,
             "AND WRITES NOTHING, which is what a delta converging means; the alias is already "
             "where it belongs and re-stating it every build is the bug this asserts against")

        # ONLY `coalesce`, WHICH IS THE WHOLE OF WHAT THIS SCHEMA WRITES. An expression this has
        # not been taught to read answers nothing rather than guessing a column out of it.
        db.execute("CREATE TABLE probe (a TEXT, b TEXT)")
        db.execute("CREATE UNIQUE INDEX probe_one ON probe (a, lower(b))")
        s.eq(relational._index_columns(db, "probe_one"), None,
             "an expression that is not a coalesce is one this may not key on")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "delta"))
