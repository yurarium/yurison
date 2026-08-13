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
    db.execute("INSERT INTO surface (kind, folded, work) VALUES ('title','T','w00001')")
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
             "INSERT INTO claim (surface,predicate,value,basis,note)"
             " VALUES (1,'reading','ヨミ','researched',NULL)", (),
             "a researched claim with no note is refused")
    db.execute("INSERT INTO claim (surface,predicate,value,basis,note)"
               " VALUES (1,'reading','ヨミ','researched','weighed X')")
    s.check(True, "and one with a note is accepted")

    # A STATED CLAIM NAMES WHERE IT CAME FROM. The stage-three invariant, as a constraint.
    _refuses(s, db,
             "INSERT INTO claim (surface,predicate,value,basis,source_kind,url)"
             " VALUES (1,'reading','ヨミ','stated','national-library',NULL)", (),
             "a stated claim with no address is refused")
    db.execute("INSERT INTO claim (surface,predicate,value,basis,source_kind,url)"
               " VALUES (1,'reading','ヨミ','stated','national-library','https://x')")
    s.check(True, "and one with an address is accepted")
    # SELF-SOURCED NEEDS NO ADDRESS, because a kana surface reads as itself and there is nothing to
    # point at. Two title-furigana claims were refused until the loader said `derived`.
    db.execute("INSERT INTO claim (surface,predicate,value,basis,source_kind)"
               " VALUES (1,'reading','ヨミ','stated','derived')")
    s.check(True, "a self-sourced stated claim needs no address")

    # A BASIS OR A KIND NOBODY HAS RULED ON IS REFUSED, which is the drift this replaces: the
    # vocabulary has one home and a foreign key has no second copy to disagree with.
    _refuses(s, db,
             "INSERT INTO claim (surface,predicate,value,basis) "
             "VALUES (1,'reading','ヨミ','invented')", (),
             "a basis nobody ruled on is refused")
    _refuses(s, db,
             "INSERT INTO claim (surface,predicate,value,basis,source_kind,url)"
             " VALUES (1,'reading','ヨミ','stated','wikipedia','https://x')", (),
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

    # ── §4: WHAT A PLATFORM OFFERS, AND WHAT IT PUBLISHED ─────────────────────────────────────
    db.execute("INSERT INTO platform (name) VALUES ('ニコニコ漫画')")

    # AN OFFER IS A LISTING, NOT A PLATFORM, and keying it `(work, platform)` refused 11 rows that
    # were all right to exist. 不器用ビンボーダンス has three ニコニコ漫画 listings at three
    # addresses; one platform can carry one work several times over.
    for u, n in (("https://manga.nicovideo.jp/comic/41035", 100),
                 ("https://manga.nicovideo.jp/comic/56736", 100),
                 ("https://manga.nicovideo.jp/comic/70296", 67)):
        db.execute("INSERT INTO offer (work, platform, url, instalments) VALUES (?,?,?,?)",
                   ("w00001", "ニコニコ漫画", u, n))
    s.eq(db.execute("SELECT count(*) FROM offer").fetchone()[0], 3,
         "one work has three listings on one platform, and each is its own offer")
    try:
        db.execute("INSERT INTO offer (work, platform, url, instalments) VALUES"
                   " ('w00001','ニコニコ漫画','https://manga.nicovideo.jp/comic/41035',1)")
        s.check(False, "the same listing twice must be refused")
    except sqlite3.IntegrityError:
        s.check(True, "and the same address twice is one listing, refused")

    # AN INSTALMENT IS NOT A CHAPTER. The column counts what a platform sells separately, which is
    # often a part of a chapter; naming it `chapters` is how the site came to print `11/11 free`
    # for a work running 24 instalments against 11 chapters.
    s.check("instalments" in [r[1] for r in db.execute("pragma table_info(offer)")],
            "the column says what it counts, so the conflation cannot be inherited silently")
    s.check("chapters" not in [r[1] for r in db.execute("pragma table_info(offer)")],
            "and the word that did both jobs is not in this schema")

    # A RELEASE MAY NAME NO WORK, which the plan expected to refuse and the data corrected. 971 of
    # 974 resolve by the identifier a release carries or by the folded title; the 3 that do not
    # carry no identifier at all and are works WORKS-PLAN §3 left without a page. A release is an
    # event somebody observed, and refusing it would push a fact the site is served out of the
    # store, which this model may not do.
    db.execute("INSERT INTO release (id, platform, instalment) VALUES ('r1','ニコニコ漫画','第1話')")
    s.eq(db.execute("SELECT count(*) FROM release WHERE work IS NULL").fetchone()[0], 1,
         "a release nobody has placed is held and counted rather than dropped")
    # BUT A DANGLING WORK IS STILL REFUSED, which is the difference between unplaced and wrong.
    try:
        db.execute("INSERT INTO release (id, work, platform) VALUES ('r2','w99999','ニコニコ漫画')")
        s.check(False, "a release naming a work the store does not hold must be refused")
    except sqlite3.IntegrityError:
        s.check(True, "naming a work that does not exist is refused; naming none is allowed")
    # AND A PLATFORM NOBODY HOLDS, because the offer belongs to a platform we have a name for.
    try:
        db.execute("INSERT INTO release (id, platform) VALUES ('r3','どこか')")
        s.check(False, "a release on an unknown platform must be refused")
    except sqlite3.IntegrityError:
        s.check(True, "and the platform is a foreign key, so it cannot be invented per row")

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

    # ── §5: A CLAIM IS ABOUT A NAME, AND A NAME MAY NAME NOTHING ──────────────────────────────
    #
    # THE FAULT THIS SECTION EXISTS FOR. `claim` was keyed on an identifier, so a name resolving to
    # nothing had nowhere to hang and the loader skipped it: 890 readings and every one of the
    # 4,174 English renderings the corpus holds were absent from a store reporting no refusals.
    db = relational.load_rulings(relational.create(":memory:"))
    db.execute("INSERT INTO work (id, title, admitted_by) VALUES ('w00001','ゆり','shelf')")
    db.execute("INSERT INTO credit (id, surface, kind) VALUES ('c00001','作者','person')")
    db.execute("INSERT INTO surface (kind, folded) VALUES ('title','よんだことのないほん')")
    orphan = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("INSERT INTO claim (surface, predicate, value, basis) VALUES (?,?,?,?)",
               (orphan, "english", "A Book Nobody Has Read", "translated"))
    s.eq(db.execute("SELECT count(*) FROM claim").fetchone()[0], 1,
         "a name the corpus identifies nothing for still holds its claims")

    # A NAME RESOLVES TO A SUBJECT OF ITS OWN KIND, and a string that is not a name resolves to
    # none. Three real foreign keys rather than one polymorphic column, so a dangling identifier is
    # refused instead of stored and read back later as a join that failed.
    _refuses(s, db, "INSERT INTO surface (kind, folded, credit) VALUES ('title','x','c00001')", (),
             "a title naming a person is refused")
    _refuses(s, db, "INSERT INTO surface (kind, folded, work) VALUES ('phrase','x','w00001')", (),
             "and a chapter label names nothing at all, because it is not a name")
    _refuses(s, db, "INSERT INTO surface (kind, folded, work) VALUES ('title','x','w99999')", (),
             "a name pointing at a work nobody holds is refused, not silently unresolved")

    # THE TWO VOCABULARIES ARE DIFFERENT AND OVERLAP ON ONE WORD. `stated` means a source printed
    # the kana and it also means a source printed the English; nothing before §5 could tell a claim
    # resting on the wrong one, because `basis` alone admitted either for either.
    _refuses(s, db, "INSERT INTO claim (surface,predicate,value,basis) "
                    "VALUES (?,'english','X','analyser')", (orphan,),
             "an English name resting on a reading basis is refused")
    _refuses(s, db, "INSERT INTO claim (surface,predicate,value,basis) "
                    "VALUES (?,'reading','ヨミ','licensed')", (orphan,),
             "and a reading resting on an English one is refused the same way")

    # `en_forms` IS THIS TABLE READ BACK, which is why neither it nor `en` needs a column. Every
    # form is a row and the one the site shows is the highest-ranked of them.
    for basis, value in (("official-jp", "Even if we become adults"),
                         ("licensed", "Even Though We’re Adults"),
                         ("translated", "Even After Becoming an Adult")):
        db.execute("INSERT INTO claim (surface, predicate, value, basis) VALUES (?,?,?,?)",
                   (orphan, "english", value, basis))
    won = db.execute(
        "SELECT c.value FROM claim c JOIN basis_for_predicate b"
        " ON b.basis = c.basis AND b.predicate = c.predicate"
        " WHERE c.surface = ? AND c.predicate = 'english' ORDER BY b.rank DESC", (orphan,))
    s.eq(won.fetchone()[0], "Even if we become adults",
         "the work's own English outranks a licensor's, by the ranking the facts state")
    s.eq(db.execute("SELECT count(*) FROM claim WHERE predicate = 'english'").fetchone()[0], 4,
         "and the forms it beat are held beside it rather than discarded")

    # AN ENGLISH BASIS ANSWERS NONE OF DIVISION'S FOUR QUESTIONS, and says so rather than saying no
    # to each. All four or none, so a half-filled row cannot be read as though the blanks meant no.
    s.check(db.execute("SELECT cited FROM basis WHERE name = 'licensed'").fetchone()[0] is None,
            "nothing about `licensed` says whether it may lend a division")
    _refuses(s, db, "INSERT INTO basis (name, cited) VALUES ('half', 1)", (),
             "a basis answering one of the four and not the rest is refused")

    # RUBY IS SPANS OVER THE SURFACE AND NOT A BLOB, which is the carrier this store exists to stop
    # being. A span with no reading is a run of the surface that takes none.
    db.execute("INSERT INTO ruby (surface, seq, text, reading) VALUES (?,0,'百合','ゆり')", (orphan,))
    db.execute("INSERT INTO ruby (surface, seq, text) VALUES (?,1,'の')", (orphan,))
    s.eq(db.execute("SELECT count(*) FROM ruby WHERE reading IS NULL").fetchone()[0], 1,
         "a span the surface reads for itself carries no ruby and is still a span")
    _refuses(s, db, "INSERT INTO ruby (surface, seq, text) VALUES (?,0,'again')", (orphan,),
             "and one position holds one span")

    # THE THREE STYLES ARE THREE ROWS. `plain`, `macron` and `double` are what a reader chooses
    # between, and a fourth spelling is not one of them.
    db.execute("INSERT INTO romanisation (surface, style, value) VALUES (?,'macron','Yuri')",
               (orphan,))
    _refuses(s, db, "INSERT INTO romanisation (surface, style, value) VALUES (?,'wapuro','Yuri')",
             (orphan,), "a romanisation style outside the reader's three is refused")

    # A CREDIT PART BELONGS TO A DIVISION, so parts cannot accumulate under a line nothing divided.
    _refuses(s, db, "INSERT INTO credit_part (surface, seq, name) VALUES (?,0,'X')", (orphan,),
             "a part with no division above it is refused")
    db.execute("INSERT INTO surface (kind, folded) VALUES ('credit-line','あ／い')")
    line = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("INSERT INTO credit_division (surface, joiner) VALUES (?,', ')", (line,))
    db.execute("INSERT INTO credit_part (surface, seq, name, role) VALUES (?,0,'あ','原作')", (line,))
    s.eq(db.execute("SELECT role FROM credit_part").fetchone()[0], "原作",
         "and the role sits on the part, because one line names two people doing two jobs")

    # ONE STRING PER KIND. The fold is the key the feed joins on, so a second row under one folded
    # key would be two answers to the question an archived month asks.
    _refuses(s, db, "INSERT INTO surface (kind, folded) VALUES ('credit-line','あ／い')", (),
             "a second surface under one folded key is refused")
    db.execute("INSERT INTO surface (kind, folded) VALUES ('title','あ／い')")
    s.eq(db.execute("SELECT count(*) FROM surface WHERE folded = 'あ／い'").fetchone()[0], 2,
         "and one string is a title and a credit line at once, which is what the kind is for")

    # ── §5a: THE CONSTRAINTS THAT DID NOT FIRE ────────────────────────────────────────────────
    #
    # THE PRAGMA IS PER-CONNECTION AND THE FILE DOES NOT REMEMBER IT. `schema.sql` line 23 applied
    # to the loader's connection and to nothing else, so `ask`, `equivalent` and `delta.write` each
    # ran with the keys off and a dangling edge inserted. This is the assertion that the one opener
    # turns them on, and it is a test about a CONNECTION rather than about a row.
    import tempfile as _tf
    _p = pathlib.Path(_tf.mkdtemp()) / "fk.db"
    relational.create(_p).close()
    reopened = relational.open_db(_p)
    s.eq(reopened.execute("PRAGMA foreign_keys").fetchone()[0], 1,
         "a store reopened after the build has its foreign keys on")
    _refuses(s, reopened, "INSERT INTO work_credit VALUES ('w99999','c99999',NULL,0)", (),
             "so an edge naming nobody is refused on a fresh connection, not only during a build")

    # A LIST HOLDING NULL MAKES A CHECK PASS ON EVERYTHING. `'banana' IN ('publication', NULL)` is
    # NULL, and a CHECK passes on NULL, so this column constrained nothing until §5a.
    s.check(db.execute("SELECT 'banana' IN ('publication','shop-delivery',NULL)").fetchone()[0]
            is None, "the SQL behind it: a comparison against a list holding NULL answers NULL")
    _refuses(s, db, "INSERT INTO work (id,title,admitted_by,first_event) "
                    "VALUES ('w00009','T','t','banana')", (),
             "a first event outside the pair is refused now that the NULL is out of the list")

    # AN IDENTIFIER HAS A WIDTH AND NOT ONLY A PREFIX. `w[0-9]*` admitted `w1garbage`, and it
    # admitted the short ids `test_delta.py` had been planting since it was written.
    _refuses(s, db, "INSERT INTO work (id,title,admitted_by) VALUES ('w1garbage','T','t')", (),
             "an identifier with rubbish after the digits is refused")
    _refuses(s, db, "INSERT INTO work (id,title,admitted_by) VALUES ('w1','T','t')", (),
             "and so is one too short to be an identifier this project issues")

    # A VOLUME BEFORE THE FIRST ONE.
    _refuses(s, db, "INSERT INTO edition (work, volume, kind) VALUES ('w00001',-5,'printing')", (),
             "a negative volume number is refused")

    # `romanisation` WAS DECLARED LEGAL AND MADE UNSTATEABLE by the composite key, which is a schema
    # contradicting itself. It is out of the enum, so the contradiction is gone rather than hidden.
    _refuses(s, db, "INSERT INTO claim (surface,predicate,value,basis) "
                    "VALUES (?,'romanisation','Yuri','translated')", (orphan,),
             "a romanisation is not a claim about a name and the predicate no longer pretends")

    # THE ATTRIBUTION TABLE IS SCOPED BY THE CLAIM IT ANSWERS FOR, and was filled from the reading
    # side alone, so `('translated','derived')` read as forbidden 2,767 times.
    pairs = {(b, p_, k) for b, p_, k in
             db.execute("SELECT basis, predicate, source_kind FROM basis_admits_kind")}
    s.check(("translated", "english", "derived") in pairs,
            "a translation of ours rests on derived evidence, which the English table admits")
    s.check(("translated", "reading", "derived") not in pairs,
            "and the same basis says nothing about a reading, which is why the predicate is keyed")
    for b in _rd.en_bases():
        for k in _rd.en_kinds_for(b):
            s.check((b, "english", k) in pairs, f"the English attribution carries {b}/{k}")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
