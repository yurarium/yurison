#!/usr/bin/env python3
"""adapters/relational: the schema, and the constraints that replace invariants.

COVERS = ['adapters/relational/__init__.py', 'adapters/relational/schema.sql']

EVERY ASSERTION HERE PLANTS A ROW THE SCHEMA MUST REFUSE. A constraint nobody has watched reject
something is indistinguishable from a column comment, which is the same argument `--self-test` makes
about a check.
"""
import pathlib
import sqlite3
import sys
import tempfile

# THE COLLISION IS GONE AND THE ORDER NO LONGER DECIDES ANYTHING. This package was called `store`
# beside `adapters/names/store.py`, and because it puts `names` on its own path, a bare
# `import store` inside it resolved to the NAME store. The path order was the workaround; the rename is
# the fix, and adapters/lint/shadowing.py is where that class of fault is watched.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit                                                          # noqa: E402
import relational                                                       # noqa: E402


def _fresh():
    d = tempfile.mkdtemp()
    db = relational.load_rulings(relational.create(pathlib.Path(d) / "t.db"))
    db.execute("INSERT INTO work (id, title, admitted_by) VALUES ('w00001','T','test')")
    db.execute("INSERT INTO credit (id, surface, kind) VALUES ('c00001','X','person')")
    db.execute("INSERT INTO publisher (id, name) VALUES ('h00001','P')")
    return db


def _refuses(s, db, sql, args, why):
    try:
        db.execute(sql, args)
        s.check(False, why)
    except sqlite3.IntegrityError:
        s.check(True, why)


def main(s):
    db = _fresh()

    # AN EDGE NAMING NOBODY IS REFUSED. `every credit identifier resolves` and `a shipped identifier
    # resolves` are Python that runs after the damage; here the row cannot be written.
    _refuses(s, db, "INSERT INTO work_credit VALUES ('w00001','c99999',NULL,0)", (),
             "an edge to a credit that does not exist is refused")
    _refuses(s, db, "INSERT INTO work_credit VALUES ('w99999','c00001',NULL,0)", (),
             "an edge to a work that does not exist is refused")

    # ONE ROW PER IDENTIFIER, and one identifier per name.
    _refuses(s, db, "INSERT INTO work (id, title, admitted_by) VALUES ('w00001','other','t')", (),
             "a second work under one id is refused")
    _refuses(s, db, "INSERT INTO credit (id, surface, kind) VALUES ('c00002','X','person')", (),
             "a second credit under one surface is refused")

    # AN IDENTIFIER HAS A SHAPE. `w`, `c`, `h` are the project's and a typo is not an id.
    _refuses(s, db, "INSERT INTO work (id, title, admitted_by) VALUES ('nope','T','t')", (),
             "an identifier of the wrong shape is refused")

    # AN IMPRINT BELONGS TO A HOUSE THAT EXISTS.
    _refuses(s, db, "INSERT INTO imprint (publisher, name) VALUES ('h99999','L')", (),
             "an imprint under a house that does not exist is refused")

    # A RESEARCHED CLAIM CARRIES ITS REASONING. This one is not hypothetical: the loader refuses
    # eight rows the corpus holds today, all `researched` from `yurarium` with no note.
    _refuses(s, db,
             "INSERT INTO claim (subject_kind,subject,predicate,value,basis,note)"
             " VALUES ('work','w00001','reading','ヨミ','researched',NULL)", (),
             "a researched claim with no note is refused")
    db.execute("INSERT INTO claim (subject_kind,subject,predicate,value,basis,note)"
               " VALUES ('work','w00001','reading','ヨミ','researched','weighed X')")
    s.check(True, "and one with a note is accepted")

    # A STATED CLAIM NAMES WHERE IT CAME FROM. The stage-three invariant, as a constraint.
    _refuses(s, db,
             "INSERT INTO claim (subject_kind,subject,predicate,value,basis,source_kind,url)"
             " VALUES ('work','w00001','reading','ヨミ','stated','national-library',NULL)", (),
             "a stated claim with no address is refused")
    db.execute("INSERT INTO claim (subject_kind,subject,predicate,value,basis,source_kind,url)"
               " VALUES ('work','w00001','reading','ヨミ','stated','national-library','https://x')")
    s.check(True, "and one with an address is accepted")
    # SELF-SOURCED NEEDS NO ADDRESS, because a kana surface reads as itself and there is nothing to
    # point at. Two title-furigana claims were refused until the loader said `derived`.
    db.execute("INSERT INTO claim (subject_kind,subject,predicate,value,basis,source_kind)"
               " VALUES ('work','w00001','reading','ヨミ','stated','derived')")
    s.check(True, "a self-sourced stated claim needs no address")

    # A BASIS OR A KIND NOBODY HAS RULED ON IS REFUSED, which is the drift this replaces: the
    # vocabulary has one home and a foreign key has no second copy to disagree with.
    _refuses(s, db,
             "INSERT INTO claim (subject_kind,subject,predicate,value,basis) "
             "VALUES ('work','w00001','reading','ヨミ','invented')", (),
             "a basis nobody ruled on is refused")
    _refuses(s, db,
             "INSERT INTO claim (subject_kind,subject,predicate,value,basis,source_kind,url)"
             " VALUES ('work','w00001','reading','ヨミ','stated','wikipedia','https://x')", (),
             "a source kind nobody ruled on is refused")

    # THE RULINGS ARE ASKED FOR AND NOT RESTATED, which is the whole reason the schema may hold
    # them. If these tables ever disagree with the facts, the loader copied instead of asking.
    from facts import division as _div
    from facts import reading as _rd
    got = {b: (c, d_, m, n) for b, c, d_, m, n
           in db.execute("SELECT name, cited, donates, marked, counted FROM basis")}
    for b in _div.BASES:
        s.eq(got[b], (int(_div.cites_its_source(b)), int(_div.may_donate(b)),
                      int(_div.is_marked(b)), int(_div.counted_uncited(b))),
             f"the basis table agrees with facts/division about {b}")
    pairs = {(b, k) for b, k in db.execute("SELECT basis, source_kind FROM basis_admits_kind")}
    for b in _rd.bases():
        for k in _rd.kinds_for(b):
            s.check((b, k) in pairs, f"the attribution table carries {b}/{k}")

    # THE QUESTIONS RUN. Each was a script or was unaskable; a broken one would answer nothing.
    for q, sql in relational.QUESTIONS.items():
        db.execute(sql).fetchone()
    s.check(True, "every standing question is valid SQL against this schema")

    # ── THE TWO TABLES §2 FILLED, AND THE CONSTRAINTS THEY BRING WITH THEM ────────────────────
    #
    # Both were declared with columns, constraints and an index and never written to, from the
    # commit that created the schema until 2026-08-13. A constraint nothing has ever inserted
    # against asserts nothing, which is the same argument this file opens with.
    db = relational.create(":memory:")
    db.execute("INSERT INTO work (id, title, admitted_by) VALUES ('w00001', 'x', 'shelf')")
    db.execute("INSERT INTO publisher (id, name) VALUES ('h00001', '芳文社')")
    db.execute("INSERT INTO imprint (publisher, name) VALUES ('h00001', 'まんがタイムKR')")
    imp = db.execute("SELECT id FROM imprint").fetchone()[0]

    # A DATE NOBODY CAN FOLLOW IS REFUSED, which is the whole of what `edition` adds. The rule is
    # the same one `per-book dates cite their page` states for the shop capture, moved to where it
    # cannot be reported after the fact because the row never lands.
    try:
        db.execute("INSERT INTO edition (work, dated, kind) VALUES ('w00001', '2018-08', 'printing')")
        s.check(False, "a dated edition with no citation must not be accepted")
    except sqlite3.IntegrityError:
        s.check(True, "a date with no page behind it is refused rather than counted")
    db.execute("INSERT INTO edition (work, dated, kind, cite) VALUES"
               " ('w00001', '2018-08', 'printing', 'madb:M309963')")
    s.eq(db.execute("SELECT count(*) FROM edition").fetchone()[0], 1,
         "and the same row with a citation is admitted")

    # AN EDITION OF A WORK NOBODY HOLDS. The foreign key is what makes this unstateable rather than
    # a number somebody reads later.
    try:
        db.execute("INSERT INTO edition (work, kind) VALUES ('w99999', 'printing')")
        s.check(False, "an edition may not name a work the store does not hold")
    except sqlite3.IntegrityError:
        s.check(True, "an edition of an unheld work is refused by the foreign key")

    # ONE ISBN IS ONE BOOK. Dated, because §3 made an ISBN without a date unstateable and this
    # assertion is about the ISBN rather than about the date.
    db.execute("INSERT INTO edition (work, isbn, dated, cite, kind) VALUES"
               " ('w00001','9784778320614','2008-05','madb:M309963','printing')")
    try:
        db.execute("INSERT INTO edition (work, isbn, dated, cite, kind) VALUES"
                   " ('w00001','9784778320614','2008-05','madb:M309963','printing')")
        s.check(False, "two editions must not share one ISBN")
    except sqlite3.IntegrityError:
        s.check(True, "an ISBN already held is refused, so one ISBN is one book")

    # AND THE KIND IS A CLOSED SET, so a date's meaning cannot be invented per row.
    try:
        db.execute("INSERT INTO edition (work, kind) VALUES ('w00001', 'guessed')")
        s.check(False, "an edition kind outside the set must be refused")
    except sqlite3.IntegrityError:
        s.check(True, "printing, shop-delivery and serialisation are the only kinds there are")

    # ── WHAT §3 ADDED: A VOLUME IS CALLED SOMETHING, AND ITS DATE RESTS ON SOMETHING ──────────
    #
    # `volume` is a position and an integer answers it. 983 volumes are called `上`, `創刊号` or
    # `2017年1月号`, which no integer holds, and the column for that did not exist until §3.
    db.execute("INSERT INTO edition (work, designation, kind) VALUES ('w00001', '創刊号', 'printing')")
    s.eq(db.execute("SELECT designation FROM edition WHERE designation IS NOT NULL").fetchone()[0],
         "創刊号", "a volume carries the word it is called, not a number standing in for it")

    # AN ISBN IS A KEY INTO EVERY DATED REGISTRY THERE IS, so holding one and no date means nobody
    # asked. The budget was 0 and is now unstateable.
    try:
        db.execute("INSERT INTO edition (work, isbn, kind) VALUES ('w00001','9784088900000','printing')")
        s.check(False, "an ISBN with no date must not be accepted")
    except sqlite3.IntegrityError:
        s.check(True, "an ISBN with no date is refused: the registries it keys into all state one")
    db.execute("INSERT INTO edition (work, isbn, dated, cite, kind) VALUES"
               " ('w00001','9784088900000','2019-01','madb:M1','printing')")
    s.check(True, "and the same ISBN with a date and a citation is admitted")

    # A BASIS NOBODY CAN NAME IS A BASIS NOBODY CAN WEIGH.
    try:
        db.execute("INSERT INTO edition (work, dated, cite, kind, dated_basis) VALUES"
                   " ('w00001','2019-01','madb:M2','printing','somebody said so')")
        s.check(False, "a date basis outside the set must be refused")
    except sqlite3.IntegrityError:
        s.check(True, "the four bases a volume date can rest on are the only ones there are")
    # AND SILENCE IS ALLOWED, because 1,219 volumes state no basis and an admitted silence beats
    # a basis invented to satisfy a column.
    db.execute("INSERT INTO edition (work, dated, cite, kind) VALUES"
               " ('w00001','2019-02','madb:M3','printing')")
    s.check(True, "a date with no stated basis is admitted rather than given one")

    # WORK TO PUBLISHER, and the imprint it is published under.
    db.execute("INSERT INTO work_publisher (work, publisher, imprint) VALUES ('w00001','h00001',?)",
               (imp,))
    s.eq(db.execute("SELECT imprint FROM work_publisher").fetchone()[0], imp,
         "a work carries the line it is published on, not merely the house")
    try:
        db.execute("INSERT INTO work_publisher (work, publisher) VALUES ('w00001', 'h99999')")
        s.check(False, "a work may not be published by a house the store does not hold")
    except sqlite3.IntegrityError:
        s.check(True, "and a publisher nobody holds is refused by the foreign key")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
