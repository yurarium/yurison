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
        db.execute("INSERT INTO claim (surface, predicate, value, basis, source, source_kind)"
                   " VALUES (1,'reading','ヨミ','surface','x','derived')")
        db.execute("INSERT INTO claim (surface, predicate, value, basis, source, source_kind)"
                   " VALUES (1,'reading','ベツ','surface','y','derived')")
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


if __name__ == "__main__":
    sys.exit(testkit.run(main, "delta"))
