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
    db.execute("INSERT INTO work (id, title) VALUES ('w00001','T')")
    db.execute("INSERT INTO credit (id, surface, kind) VALUES ('c00001','X','person')")
    db.execute("INSERT INTO publisher (id, name) VALUES ('h00001','P')")
    db.execute("INSERT INTO surface (kind, folded) VALUES ('title','T')")
    db.execute("INSERT INTO names (surface, kind, work) VALUES (1,'title','w00001')")
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
    _refuses(s, db, "INSERT INTO work_credit (work,credit) VALUES ('w00001','c99999')", (),
             "an edge to a credit that does not exist is refused")
    _refuses(s, db, "INSERT INTO work_credit (work,credit) VALUES ('w99999','c00001')", (),
             "an edge to a work that does not exist is refused")

    # §5b: AND THE SAME EDGE TWICE. `PRIMARY KEY (work, credit, role)` permitted NULLs, every one of
    # the 4,165 rows has a NULL role, so the key degenerated and one edge inserted three times.
    db.execute("INSERT INTO work_credit (work,credit) VALUES ('w00001','c00001')")
    _refuses(s, db, "INSERT INTO work_credit (work,credit) VALUES ('w00001','c00001')", (),
             "one work names one person once, which the old key could not say")
    db.execute("INSERT INTO work_credit (work,credit,role) VALUES ('w00001','c00001','原作')")
    s.eq(db.execute("SELECT count(*) FROM work_credit").fetchone()[0], 2,
         "and the same person in a second role on the same work is a second edge")
    s.check("seq" not in [r[1] for r in db.execute("pragma table_info(work_credit)")],
            "`seq` is gone: it was documented as byline order and numbered the wrong thing")

    # ONE ROW PER IDENTIFIER, and one identifier per name.
    _refuses(s, db, "INSERT INTO work (id, title) VALUES ('w00001','other')", (),
             "a second work under one id is refused")
    _refuses(s, db, "INSERT INTO credit (id, surface, kind) VALUES ('c00002','X','person')", (),
             "a second credit under one surface is refused")

    # AN IDENTIFIER HAS A SHAPE. `w`, `c`, `h` are the project's and a typo is not an id.
    _refuses(s, db, "INSERT INTO work (id, title) VALUES ('nope','T')", (),
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
               " VALUES (1,'reading','ヨミA','stated','national-library','https://x')")
    s.check(True, "and one with an address is accepted")
    # SELF-SOURCED NEEDS NO ADDRESS, because a kana surface reads as itself and there is nothing to
    # point at. Two title-furigana claims were refused until the loader said `derived`.
    db.execute("INSERT INTO claim (surface,predicate,value,basis,source_kind)"
               " VALUES (1,'reading','ヨミB','stated','derived')")
    s.check(True, "a self-sourced stated claim needs no address")

    # §5b: WHAT IDENTIFIES A CLAIM. It had nothing, so `delta.write` could not address a row twice
    # and neither an upsert nor a retraction was expressible, which is what stood between this store
    # and §7. Ten groups were byte-identical on all eleven non-id columns.
    _refuses(s, db, "INSERT INTO claim (surface,predicate,value,basis,source_kind)"
                    " VALUES (1,'reading','ヨミB','stated','derived')", (),
             "the same claim said twice is one claim")
    db.execute("INSERT INTO claim (surface,predicate,value,basis,source,source_kind,url)"
               " VALUES (1,'reading','ヨミA','stated','openBD','publisher-jp','https://y')")
    s.eq(db.execute("SELECT count(*) FROM claim WHERE value = 'ヨミA'").fetchone()[0], 2,
         "TWO SOURCES AGREEING STAY TWO ROWS, which is what `claims resting on a community "
         "database` counts and why the source is part of the key")

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
    pairs = {(b, p_, k) for b, p_, k
             in db.execute("SELECT basis, predicate, source_kind FROM basis_admits_kind")}
    for b in _rd.bases():
        for k in _rd.kinds_for(b):
            s.check((b, "reading", k) in pairs, f"the attribution table carries {b}/{k}")

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
    db.execute("INSERT INTO work (id, title) VALUES ('w00001', 'x')")
    db.execute("INSERT INTO publisher (id, name) VALUES ('h00001', '芳文社')")
    db.execute("INSERT INTO imprint (publisher, name) VALUES ('h00001', 'まんがタイムKR')")
    imp = db.execute("SELECT id FROM imprint").fetchone()[0]

    # ── §5b SPLIT THE BOOK FROM THE EVENT, AND THAT IS WHAT THESE NOW ASSERT ─────────────────
    #
    # 812 volumes state a printing date and a shop delivery date that differ, and `edition` held one
    # row per book with `isbn UNIQUE`, so the second event had nowhere to go. The loader's `if/elif`
    # keeping the printing and dropping the delivery was forced by the shape, not chosen.
    db.execute("INSERT INTO volume (work, isbn) VALUES ('w00001','9784778320614')")
    vol = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("INSERT INTO edition (volume, dated, kind, cite) VALUES"
               " (?, '2009-08', 'printing', 'madb:M400412')", (vol,))
    db.execute("INSERT INTO edition (volume, dated, kind, cite) VALUES"
               " (?, '2014-03', 'shop-delivery', 'https://shop/x')", (vol,))
    s.eq(db.execute("SELECT count(*) FROM edition WHERE volume = ?", (vol,)).fetchone()[0], 2,
         "one book holds a printing and a delivery, which it could not before")
    _refuses(s, db, "INSERT INTO edition (volume, dated, kind, cite) VALUES"
                    " (?, '2015-01', 'printing', 'madb:M2')", (vol,),
             "and one of each kind, so a second printing of one book is refused")

    # A DATE NOBODY CAN FOLLOW IS REFUSED, the rule `per-book dates cite their page` states for the
    # shop capture, moved to where it cannot be reported after the fact because the row never lands.
    _refuses(s, db, "INSERT INTO edition (volume, dated, kind) VALUES (?, '2018-08', 'serialisation')",
             (vol,), "a date with no page behind it is refused rather than counted")

    # A VOLUME OF A WORK NOBODY HOLDS, and an event on a volume nobody holds.
    _refuses(s, db, "INSERT INTO volume (work) VALUES ('w99999')", (),
             "a volume may not name a work the store does not hold")
    _refuses(s, db, "INSERT INTO edition (volume, kind) VALUES (99999, 'printing')", (),
             "and an event may not name a volume that does not exist")

    # ONE ISBN IS ONE BOOK, which is now a statement about the book rather than about an event.
    _refuses(s, db, "INSERT INTO volume (work, isbn) VALUES ('w00001','9784778320614')", (),
             "an ISBN already held is refused, so one ISBN is one book")

    # AND THE KIND IS A CLOSED SET, so a date's meaning cannot be invented per row.
    _refuses(s, db, "INSERT INTO edition (volume, kind) VALUES (?, 'guessed')", (vol,),
             "printing, shop-delivery and serialisation are the only kinds there are")

    # ── WHAT §3 ADDED: A VOLUME IS CALLED SOMETHING, AND ITS DATE RESTS ON SOMETHING ──────────
    #
    # `volume` is a position and an integer answers it. 983 volumes are called `上`, `創刊号` or
    # `2017年1月号`, which no integer holds, and the column for that did not exist until §3.
    db.execute("INSERT INTO volume (work, designation) VALUES ('w00001', '創刊号')")
    s.eq(db.execute("SELECT designation FROM volume WHERE designation IS NOT NULL").fetchone()[0],
         "創刊号", "a volume carries the word it is called, not a number standing in for it")

    # AN ISBN AND NO DATE IS NO LONGER A CHECK, because no CHECK reaches across two tables. It is a
    # standing question the store answers, which is weaker, and saying so is the point.
    s.check("volumes with an isbn and no date" in relational.QUESTIONS,
            "the constraint §3 adopted became a question §5b can still ask")
    s.eq(db.execute(relational.QUESTIONS["volumes with an isbn and no date"]).fetchone()[0], 0,
         "and the volume above holds a date, so nothing answers to it here")
    db.execute("INSERT INTO volume (work, isbn) VALUES ('w00001','9784088900000')")
    s.eq(db.execute(relational.QUESTIONS["volumes with an isbn and no date"]).fetchone()[0], 1,
         "while an ISBN nobody dated is found, which is what the CHECK used to refuse")

    # A BASIS NOBODY CAN NAME IS A BASIS NOBODY CAN WEIGH.
    _refuses(s, db, "INSERT INTO edition (volume, dated, cite, kind, dated_basis) VALUES"
                    " (?, '2019-01','madb:M2','serialisation','somebody said so')", (vol,),
             "the four bases a volume date can rest on are the only ones there are")
    # AND SILENCE IS ALLOWED, because 1,219 volumes state no basis and an admitted silence beats
    # a basis invented to satisfy a column.
    db.execute("INSERT INTO edition (volume, dated, cite, kind) VALUES"
               " (?, '2019-02','madb:M3','serialisation')", (vol,))
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
    db.execute("INSERT INTO work (id, title) VALUES ('w00001','ゆり')")
    db.execute("INSERT INTO credit (id, surface, kind) VALUES ('c00001','作者','person')")
    db.execute("INSERT INTO surface (kind, folded) VALUES ('title','よんだことのないほん')")
    orphan = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("INSERT INTO claim (surface, predicate, value, basis) VALUES (?,?,?,?)",
               (orphan, "english", "A Book Nobody Has Read", "translated"))
    s.eq(db.execute("SELECT count(*) FROM claim").fetchone()[0], 1,
         "a name the corpus identifies nothing for still holds its claims")

    # §5d: WHAT A NAME NAMES IS AN EDGE. Three nullable columns on `surface` said a name names at
    # most one thing, and `百合漫画短編集` names w01990 and w02284 while `Girls Love` names w01001
    # and w01108, so one work of each pair took the English and the reading and the other got none.
    db.execute("INSERT INTO work (id, title) VALUES ('w00002','T2')")
    db.execute("INSERT INTO names (surface, kind, work) VALUES (?, 'title', 'w00002')", (orphan,))
    db.execute("INSERT INTO names (surface, kind, work) VALUES (?, 'title', 'w00001')", (orphan,))
    s.eq(db.execute("SELECT count(*) FROM names WHERE surface = ?", (orphan,)).fetchone()[0], 2,
         "one folded title names two works and both are recorded")
    _refuses(s, db, "INSERT INTO names (surface, kind, work) VALUES (?, 'title', 'w00001')",
             (orphan,), "and the same edge twice is still one edge")

    # A NAME RESOLVES TO A SUBJECT OF ITS OWN KIND. The kind travels with the edge so the pair can
    # be a foreign key, which is what keeps a title from naming a person.
    _refuses(s, db, "INSERT INTO names (surface, kind, credit) VALUES (?, 'title', 'c00001')",
             (orphan,), "a title naming a person is refused")
    _refuses(s, db, "INSERT INTO names (surface, kind, work) VALUES (?, 'author', 'w00001')",
             (orphan,), "and the edge's kind must be the surface's own, by the composite key")
    db.execute("INSERT INTO surface (kind, folded) VALUES ('phrase','第1話')")
    ph = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    _refuses(s, db, "INSERT INTO names (surface, kind, work) VALUES (?, 'phrase', 'w00001')",
             (ph,), "a chapter label names nothing at all, because it is not a name")
    _refuses(s, db, "INSERT INTO names (surface, kind, work) VALUES (?, 'title', 'w99999')",
             (orphan,), "a name pointing at a work nobody holds is refused, not left unresolved")

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

    # ── §5c: WHAT THE STORE SAID IT HELD AND DID NOT ──────────────────────────────────────────
    #
    # `admitted_by` WAS A NOT NULL HOLDING THE WORD `'unstated'` ON ALL 3,040 ROWS, because the
    # loader read it from `series.json` and the grounds are on `works.json`, structured, on 1,887
    # records. A NOT NULL whose every value is the word for null reports as filled.
    s.check("admitted_by" not in [r[1] for r in db.execute("pragma table_info(work)")],
            "the placeholder column is gone and the grounds are a table")
    db.execute("INSERT INTO admission (work, comparator, shelf, note) VALUES"
               " ('w00001','cmoa.jp','genre 37 (百合・GL)','DEFINITIONS §2, presumptive')")
    s.eq(db.execute("SELECT shelf FROM admission").fetchone()[0], "genre 37 (百合・GL)",
         "and a work is admitted on grounds that name the comparator and the shelf")
    _refuses(s, db, "INSERT INTO admission (work) VALUES ('w99999')", (),
             "grounds for a work nobody holds are refused")

    # `volume_count` WAS NULL ON ALL 3,040 FOR THE SAME REASON, and it does not come back as a
    # column: 72 works have records stating DIFFERENT counts, so one column would have to pick and
    # discard a disagreement. How many are HELD is `count(volume)`, which is the other side of it.
    s.check("volume_count" not in [r[1] for r in db.execute("pragma table_info(work)")],
            "a count a source states is not a property of the work")
    db.execute("INSERT INTO volume_claim (work, volumes, source) VALUES ('w00001',6,'cmoa.jp')")
    db.execute("INSERT INTO volume_claim (work, volumes, source) VALUES ('w00001',5,'bookwalker')")
    s.eq(db.execute("SELECT count(*) FROM volume_claim WHERE work='w00001'").fetchone()[0], 2,
         "two sources disagreeing about the run are two rows, which is the rule everywhere else")
    _refuses(s, db, "INSERT INTO volume_claim (work, volumes) VALUES ('w00001',-1)", (),
             "and a negative run is refused")

    # WHICH ANSWER THE RECORD STANDS BEHIND. 638 surfaces carried a `verified` flag beside two or
    # more readings, and nothing said which one a person ruled on.
    db.execute("INSERT INTO claim (surface, predicate, value, basis, source, displaced) VALUES"
               " (?,'reading','ヨミC','surface','x',1)", (orphan,))
    s.eq(db.execute("SELECT count(*) FROM claim WHERE displaced = 1").fetchone()[0], 1,
         "a claim somebody moved aside is kept and says so")
    _refuses(s, db, "INSERT INTO claim (surface, predicate, value, basis, displaced) VALUES"
                    " (?,'reading','ヨミD','surface',2)", (orphan,),
             "and displaced is a yes or a no")

    # ── §5d: THE IDENTITY REGISTRY, WHICH THE STORE HAD NEVER READ ────────────────────────────
    #
    # ONE ADDRESS REACHES ONE WORK, which is how this project identifies one and is the constraint
    # the store never had. `works.yaml` holds 5,400 anchors across 3,240 works.
    db.execute("INSERT INTO work_anchor (scheme, address, work) VALUES ('madb','C418820','w00001')")
    _refuses(s, db, "INSERT INTO work_anchor (scheme, address, work) VALUES"
                    " ('madb','C418820','w00002')", (),
             "one address may not reach two works")
    db.execute("INSERT INTO work_anchor (scheme, address, work) VALUES"
               " ('web','https://x/1','w00001')")
    s.eq(db.execute("SELECT count(*) FROM work_anchor WHERE work = 'w00001'").fetchone()[0], 2,
         "and one work is reached by several, which is how 1,308 of them are held")

    # EVERY SPELLING THAT REACHES ONE PERSON. `credit.surface UNIQUE` kept one and discarded the
    # rest, so a byline written `スズキフミエ` never reached c00016, whose kept spelling is 鈴木二三江.
    db.execute("INSERT INTO credit_spelling (spelling, credit) VALUES ('鈴木二三江','c00001')")
    db.execute("INSERT INTO credit_spelling (spelling, credit) VALUES ('スズキフミエ','c00001')")
    s.eq(db.execute("SELECT count(*) FROM credit_spelling WHERE credit='c00001'").fetchone()[0], 2,
         "one person is written two ways and both reach them")
    _refuses(s, db, "INSERT INTO credit_spelling (spelling, credit) VALUES ('鈴木二三江','c00002')",
             (), "and one spelling reaches one person, once retirements are resolved")

    # A RETIRED IDENTIFIER RESOLVES TO A LIVE ONE, AND THE CHAIN IS FOLLOWED. `w01234` names
    # `w01220` as its survivor and `w01220` was retired in its turn, so storing the map as written
    # puts a foreign key against an identifier the corpus no longer holds.
    db.execute("INSERT INTO superseded (id, work) VALUES ('w09999','w00001')")
    _refuses(s, db, "INSERT INTO superseded (id, work) VALUES ('w09998','w01220')", (),
             "a survivor the store does not hold is refused rather than stored as a dead pointer")
    _refuses(s, db, "INSERT INTO superseded (id, work, credit) VALUES"
                    " ('w09997','w00001','c00001')", (),
             "and exactly one survivor, since an identifier was retired into one thing")

    # A RULING THAT TWO IDENTIFIERS ARE NOT ONE. `delta.KINDS` names `merge` and `divide`, and a
    # store that can merge and holds no record of a decision to keep them apart will merge again.
    _refuses(s, db, "INSERT INTO identity_ruling (kind, subject, basis) VALUES"
                    " ('homophone','credit',NULL)", (),
             "a ruling with no reasoning is a preference and is refused")
    db.execute("INSERT INTO identity_ruling (kind, subject, reading, basis) VALUES"
               " ('homophone','credit','アオイ','two spellings with no character in common')")
    s.eq(db.execute("SELECT count(*) FROM identity_ruling").fetchone()[0], 1,
         "and one with its reasoning is held")
    _refuses(s, db, "INSERT INTO identity_ruling (kind, subject, basis) VALUES"
                    " ('guessed','credit','x')", (),
             "the kinds a ruling can be are the ones the registry writes")

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
    _refuses(s, db, "INSERT INTO work (id,title,first_event) "
                    "VALUES ('w00009','T','banana')", (),
             "a first event outside the pair is refused now that the NULL is out of the list")

    # AN IDENTIFIER HAS A WIDTH AND NOT ONLY A PREFIX. `w[0-9]*` admitted `w1garbage`, and it
    # admitted the short ids `test_delta.py` had been planting since it was written.
    _refuses(s, db, "INSERT INTO work (id,title) VALUES ('w1garbage','T')", (),
             "an identifier with rubbish after the digits is refused")
    _refuses(s, db, "INSERT INTO work (id,title) VALUES ('w1','T')", (),
             "and so is one too short to be an identifier this project issues")

    # A VOLUME BEFORE THE FIRST ONE.
    _refuses(s, db, "INSERT INTO volume (work, volume) VALUES ('w00001',-5)", (),
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
