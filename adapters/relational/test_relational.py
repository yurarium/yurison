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
             "INSERT INTO claim (surface,kind,predicate,value,basis,note)"
             " VALUES (1,'title','reading','ヨミ','researched',NULL)", (),
             "a researched claim with no note is refused")
    db.execute("INSERT INTO claim (surface,kind,predicate,value,basis,note)"
               " VALUES (1,'title','reading','ヨミ','researched','weighed X')")
    s.check(True, "and one with a note is accepted")

    # A STATED CLAIM NAMES WHERE IT CAME FROM. The stage-three invariant, as a constraint.
    _refuses(s, db,
             "INSERT INTO claim (surface,kind,predicate,value,basis,source_kind,url)"
             " VALUES (1,'title','reading','ヨミ','stated','national-library',NULL)", (),
             "a stated claim with no address is refused")
    db.execute("INSERT INTO claim (surface,kind,predicate,value,basis,source_kind,url)"
               " VALUES (1,'title','reading','ヨミA','stated','national-library','https://x')")
    s.check(True, "and one with an address is accepted")
    # SELF-SOURCED NEEDS NO ADDRESS, because a kana surface reads as itself and there is nothing to
    # point at. Two title-furigana claims were refused until the loader said `derived`.
    db.execute("INSERT INTO claim (surface,kind,predicate,value,basis,source_kind)"
               " VALUES (1,'title','reading','ヨミB','stated','derived')")
    s.check(True, "a self-sourced stated claim needs no address")

    # §5b: WHAT IDENTIFIES A CLAIM. It had nothing, so `delta.write` could not address a row twice
    # and neither an upsert nor a retraction was expressible, which is what stood between this store
    # and §7. Ten groups were byte-identical on all eleven non-id columns.
    _refuses(s, db, "INSERT INTO claim (surface,kind,predicate,value,basis,source_kind)"
                    " VALUES (1,'title','reading','ヨミB','stated','derived')", (),
             "the same claim said twice is one claim")
    db.execute("INSERT INTO claim (surface,kind,predicate,value,basis,source,source_kind,url)"
               " VALUES (1,'title','reading','ヨミA','stated','openBD','publisher-jp','https://y')")
    s.eq(db.execute("SELECT count(*) FROM claim WHERE value = 'ヨミA'").fetchone()[0], 2,
         "TWO SOURCES AGREEING STAY TWO ROWS, which is what `claims resting on a community "
         "database` counts and why the source is part of the key")

    # A BASIS OR A KIND NOBODY HAS RULED ON IS REFUSED, which is the drift this replaces: the
    # vocabulary has one home and a foreign key has no second copy to disagree with.
    _refuses(s, db,
             "INSERT INTO claim (surface,kind,predicate,value,basis) "
             "VALUES (1,'title','reading','ヨミ','invented')", (),
             "a basis nobody ruled on is refused")
    _refuses(s, db,
             "INSERT INTO claim (surface,kind,predicate,value,basis,source_kind,url)"
             " VALUES (1,'title','reading','ヨミ','stated','wikipedia','https://x')", (),
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
    db.execute("INSERT INTO volume (work, record, seq) VALUES ('w00001', 'C000001', 0)")
    vol = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("INSERT INTO volume_isbn (seq, isbn, volume) VALUES (0, '9784778320614', ?)", (vol,))
    db.execute("INSERT INTO edition (volume, dated, kind, source, cite) VALUES"
               " (?, '2009-08', 'printing', 'madb', 'madb:M400412')", (vol,))
    db.execute("INSERT INTO edition (volume, dated, kind, source, cite) VALUES"
               " (?, '2014-03', 'shop-delivery', 'shop', 'https://shop/x')", (vol,))
    s.eq(db.execute("SELECT count(*) FROM edition WHERE volume = ?", (vol,)).fetchone()[0], 2,
         "one book holds a printing and a delivery, which it could not before")
    _refuses(s, db, "INSERT INTO edition (volume, dated, kind, source, cite) VALUES"
                    " (?, '2015-01', 'printing', 'madb', 'madb:M2')", (vol,),
             "and one of each kind, so a second printing of one book is refused")

    # A DATE NOBODY CAN FOLLOW IS REFUSED, the rule `per-book dates cite their page` states for the
    # shop capture, moved to where it cannot be reported after the fact because the row never lands.
    _refuses(s, db, "INSERT INTO edition (volume, dated, kind) VALUES (?, '2018-08', 'serialisation')",
             (vol,), "a date that names no source is refused rather than counted")

    # A VOLUME OF A WORK NOBODY HOLDS, and an event on a volume nobody holds.
    _refuses(s, db, "INSERT INTO volume (work, record, seq) VALUES ('w99999', 'C000002', 0)", (),
             "a volume may not name a work the store does not hold")
    _refuses(s, db, "INSERT INTO edition (volume, kind) VALUES (99999, 'printing')", (),
             "and an event may not name a volume that does not exist")

    # ONE ISBN IS ONE BOOK AND ONE BOOK MAY CARRY SEVERAL. 81 volumes list two, a regular printing
    # and a special edition, which `volume.isbn UNIQUE` could say only half of.
    db.execute("INSERT INTO volume_isbn (seq, isbn, volume) VALUES (1, '9784757540248', ?)", (vol,))
    s.eq(db.execute("SELECT count(*) FROM volume_isbn WHERE volume = ?", (vol,)).fetchone()[0], 2,
         "one book carries a second ISBN for its other printing")
    db.execute("INSERT INTO volume (work, record, seq) VALUES ('w00001', 'C000003', 0)")
    other = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    _refuses(s, db, "INSERT INTO volume_isbn (seq, isbn, volume) VALUES (0, '9784778320614', ?)", (other,),
             "and an ISBN already held is refused, so the half that matters is unweakened")

    # AND THE KIND IS A CLOSED SET, so a date's meaning cannot be invented per row.
    _refuses(s, db, "INSERT INTO edition (volume, kind) VALUES (?, 'guessed')", (vol,),
             "printing, shop-delivery and serialisation are the only kinds there are")

    # ── WHAT §3 ADDED: A VOLUME IS CALLED SOMETHING, AND ITS DATE RESTS ON SOMETHING ──────────
    #
    # `volume` is a position and an integer answers it. 983 volumes are called `上`, `創刊号` or
    # `2017年1月号`, which no integer holds, and the column for that did not exist until §3.
    db.execute("INSERT INTO volume (work, designation, record, seq) VALUES ('w00001', '創刊号', 'C000004', 0)")
    s.eq(db.execute("SELECT designation FROM volume WHERE designation IS NOT NULL").fetchone()[0],
         "創刊号", "a volume carries the word it is called, not a number standing in for it")

    # AN ISBN AND NO DATE IS NO LONGER A CHECK, because no CHECK reaches across two tables. It is a
    # standing question the store answers, which is weaker, and saying so is the point.
    s.check("volumes with an isbn and no date" in relational.QUESTIONS,
            "the constraint §3 adopted became a question §5b can still ask")
    s.eq(db.execute(relational.QUESTIONS["volumes with an isbn and no date"]).fetchone()[0], 0,
         "and the volume above holds a date, so nothing answers to it here")
    db.execute("INSERT INTO volume (work, record, seq) VALUES ('w00001', 'C000005', 0)")
    undated = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("INSERT INTO volume_isbn (seq, isbn, volume) VALUES (0, '9784088900000', ?)", (undated,))
    s.eq(db.execute(relational.QUESTIONS["volumes with an isbn and no date"]).fetchone()[0], 1,
         "while an ISBN nobody dated is found, which is what the CHECK used to refuse")

    # A BASIS NOBODY CAN NAME IS A BASIS NOBODY CAN WEIGH.
    _refuses(s, db, "INSERT INTO edition (volume, dated, source, cite, kind, dated_basis) VALUES"
                    " (?, '2019-01','madb','madb:M2','serialisation','somebody said so')", (vol,),
             "the four bases a volume date can rest on are the only ones there are")
    # AND SILENCE IS ALLOWED, because 1,219 volumes state no basis and an admitted silence beats
    # a basis invented to satisfy a column.
    db.execute("INSERT INTO edition (volume, dated, source, cite, kind) VALUES"
               " (?, '2019-02','madb','madb:M3','serialisation')", (vol,))
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
    db.execute("INSERT INTO work_publisher (work, publisher, seat, imprint) VALUES"
               " ('w00001','h00001','publisher',?)", (imp,))
    s.eq(db.execute("SELECT imprint FROM work_publisher").fetchone()[0], imp,
         "a work carries the line it is published on, not merely the house")
    # §6: AND THE SEAT, because a house that only distributed the book did not publish it. §2 read
    # this edge off a works list that counted any seat, so 193 distributor edges sat here as though
    # they had.
    db.execute("INSERT INTO work_publisher (work, publisher, seat) VALUES"
               " ('w00001','h00001','distributor')")
    s.eq(db.execute("SELECT count(*) FROM work_publisher WHERE work='w00001'").fetchone()[0], 2,
         "one house in two seats on one work is two edges and says which is which")
    _refuses(s, db, "INSERT INTO work_publisher (work, publisher, seat) VALUES"
                    " ('w00001','h00001','printer')", (),
             "and a seat outside the pair is refused")
    try:
        db.execute("INSERT INTO work_publisher (work, publisher, seat) VALUES"
                   " ('w00001','h99999','publisher')")
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
    db.execute("INSERT INTO claim (surface, kind, predicate, value, basis) VALUES (?,?,?,?,?)",
               (orphan, "title", "english", "A Book Nobody Has Read", "translated"))
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
    _refuses(s, db, "INSERT INTO claim (surface,kind,predicate,value,basis) "
                    "VALUES (?,'title','english','X','analyser')", (orphan,),
             "an English name resting on a reading basis is refused")
    _refuses(s, db, "INSERT INTO claim (surface,kind,predicate,value,basis) "
                    "VALUES (?,'title','reading','ヨミ','licensed')", (orphan,),
             "and a reading resting on an English one is refused the same way")

    # `en_forms` IS THIS TABLE READ BACK, which is why neither it nor `en` needs a column. Every
    # form is a row and the one the site shows is the highest-ranked of them.
    for basis, value in (("official-jp", "Even if we become adults"),
                         ("licensed", "Even Though We’re Adults"),
                         ("translated", "Even After Becoming an Adult")):
        db.execute("INSERT INTO claim (surface, kind, predicate, value, basis) VALUES (?,?,?,?,?)",
                   (orphan, "title", "english", value, basis))
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
    db.execute("INSERT INTO credit_division (surface, kind, joiner)"
               " VALUES (?,'credit-line',', ')", (line,))
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

    # ── §5f: THE CONSTRAINTS THAT STILL DID NOT FIRE ──────────────────────────────────────────
    #
    # THE CITATION CHECK WAS THREE-VALUED AND PASSED ON WHAT IT COULD NOT SEE. With a NULL source
    # kind the last disjunct is NULL, the whole expression is NULL, and a CHECK passes on NULL, so
    # a `stated` claim saying nothing about its evidence was admitted while the same claim naming
    # its evidence was refused. 221 rows were in the hole, 219 of them §5c's divisions.
    _refuses(s, db, "INSERT INTO claim (surface,kind,predicate,value,basis,source) VALUES"
                    " (?,'title','reading','ZZZ','stated','a source that printed it')", (orphan,),
             "a stated claim that names no evidence at all is refused, which it was not")
    s.check(db.execute("SELECT 'x' = 'derived'").fetchone()[0] == 0
            and db.execute("SELECT NULL = 'derived'").fetchone()[0] is None,
            "the SQL behind it: a comparison against NULL answers NULL and a CHECK passes on that")

    # AND IT ASKS ONLY OF A CLAIM THE RECORD STANDS BEHIND. A conflicts entry holds a basis, a
    # source and a value with nowhere to put an address, and demanding a document for something
    # nobody asserts any more would mean dropping the disagreement to satisfy a rule about
    # assertions.
    db.execute("INSERT INTO claim (surface,kind,predicate,value,basis,source,displaced) VALUES"
               " (?,'title','reading','ZZY','stated','ndlsearch.ndl.go.jp',1)", (orphan,))
    s.check(True, "a displaced stated claim with no address is kept")

    # A CIRCLE IS UNSTATEABLE RATHER THAN COUNTED, which is the project owner's ruling. A retired
    # surface may not point at another retired one, so no arrangement of any length closes.
    db.execute("INSERT INTO surface (kind, folded) VALUES ('title','canonical')")
    canon = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("INSERT INTO surface (kind, folded, alias_of) VALUES ('title','variant',?)", (canon,))
    variant = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    _refuses(s, db, "INSERT INTO surface (kind, folded, alias_of) VALUES ('title','chain',?)",
             (variant,), "a chain of aliases is refused, so no cycle of any length can form")
    _refuses(s, db, "UPDATE surface SET alias_of = ? WHERE id = ?", (variant, canon),
             "and closing a two-step circle is refused from the other end")
    db.execute("INSERT INTO surface (kind, folded, alias_of) VALUES ('title','variant2',?)", (canon,))
    s.eq(db.execute("SELECT count(*) FROM surface WHERE alias_of = ?", (canon,)).fetchone()[0], 2,
         "while two aliases onto one canonical row are admitted, which is the real case")
    s.check("aliases pointing in a circle" not in relational.QUESTIONS,
            "AND THE STANDING QUESTION IS GONE: it caught two-node cycles alone, and an answer that "
            "can no longer be anything but 0 is the control §13 objects to")
    _refuses(s, db, "INSERT INTO surface (kind, folded, alias_of) VALUES ('author','wrongkind',?)",
             (canon,), "an alias points at a surface of its own kind, by the same composite key")

    # AN ISBN IS THE IDENTIFIER AND NOT A SPELLING OF IT. 940 of 3,371 arrived hyphenated, so
    # `9784091572882` and `978-4-09-157288-2` were two rows and one ISBN was not one book. It hid
    # two duplicate WORKS for as long as it stood.
    db.execute("INSERT INTO volume (work, record, seq) VALUES ('w00001','C000900',0)")
    isbnvol = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    _refuses(s, db, "INSERT INTO volume_isbn (seq, isbn, volume) VALUES (0, '978-4-09-157288-2', ?)",
             (isbnvol,), "a hyphenated ISBN cannot enter, so the key cannot be evaded by spelling")
    _refuses(s, db, "INSERT INTO volume_isbn (seq, isbn, volume) VALUES (0, 'nonsense', ?)", (isbnvol,),
             "nor can anything that is not an ISBN")
    db.execute("INSERT INTO volume_isbn (seq, isbn, volume) VALUES (0, '412345678X', ?)", (isbnvol,))
    s.check(True, "and the older ten-character form, whose check digit may be X, is admitted")

    # A PRESENCE CONSTRAINT SATISFIED BY THE EMPTY STRING IS NOT ONE.
    _refuses(s, db, "INSERT INTO claim (surface,kind,predicate,value,basis,note) VALUES"
                    " (?,'title','reading','ZZW','researched','')", (orphan,),
             "a researched claim with an empty note is refused, which it was not")
    _refuses(s, db, "INSERT INTO work (id,title) VALUES ('w00019','')", (),
             "and a work with an empty title")

    # ── §5g: A ROW §7 CAN ADDRESS ─────────────────────────────────────────────────────────────
    #
    # `delta.write` identifies a row by a column-to-value mapping, and `volume.id` was a rowid
    # handed out by the order `works.json` happened to iterate.
    s.check("volume_source" in [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='index'")],
        "a volume is addressable by the record that states it and its position in that record")
    _refuses(s, db, "INSERT INTO volume (work, record, seq) VALUES ('w00001','C000900',0)", (),
             "so one record cannot state the same position twice")

    # ── §6: THE RECORD LAYER, WHICH IS NOT THE WORK LAYER ─────────────────────────────────────
    #
    # `works.json` holds 2,574 CATALOGUE RECORDS against 3,038 works, and two records of one work
    # each state their own first publication and their own sources. Keying either on the work kept
    # whichever was read first: `work_origin` reported 2,459 rows where the corpus has 2,574.
    db.execute("INSERT INTO work_origin (record, work, dated, venue) VALUES"
               " ('C100','w00001','2008-05','F×COMICS')")
    db.execute("INSERT INTO work_origin (record, work, dated, venue) VALUES"
               " ('bw-9','w00001','2008-06','BOOK☆WALKER')")
    s.eq(db.execute("SELECT count(*) FROM work_origin WHERE work='w00001'").fetchone()[0], 2,
         "two records of one work each state their own first publication")
    _refuses(s, db, "INSERT INTO work_origin (record, work) VALUES ('C100','w00001')", (),
             "and one record states it once")
    _refuses(s, db, "INSERT INTO work_origin (record, work) VALUES ('C200','w99999')", (),
             "against a work the store holds")

    # ── §6: A PRINT ROW IS A CATALOGUE RECORD AS A SHELF WOULD COUNT IT ───────────────────────
    #
    # A work carrying two editions under one line is TWO rows and ONE work, which is why a house's
    # `rows` and its `works` are different numbers on a publisher page.
    db.execute("INSERT INTO publisher (id, name) VALUES ('h00009','芳文社')")
    db.execute("INSERT INTO print_row (work, record, publisher, imprint_raw, volumes) VALUES"
               " ('w00001','C100','h00009','まんがタイムKRコミックス',6)")
    db.execute("INSERT INTO print_row (work, record, publisher, imprint_raw, volumes) VALUES"
               " ('w00001','C101','h00009','まんがタイムKRコミックス',4)")
    s.eq(db.execute("SELECT count(*) FROM print_row WHERE work='w00001'").fetchone()[0], 2,
         "one work is two print rows where two records describe it")
    _refuses(s, db, "INSERT INTO print_row (work, record) VALUES ('w00002','C100')", (),
             "and one catalogue record is one row, which is the key §7 addresses it by")

    # THE SPELLING AS CATALOGUED IS KEPT, because the census measures which years a spelling covers
    # and can only do that from what the rows actually say.
    s.eq(db.execute("SELECT imprint_raw FROM print_row WHERE record='C100'").fetchone()[0],
         "まんがタイムKRコミックス", "the imprint is held as the catalogue wrote it")
    pid = db.execute("SELECT id FROM print_row WHERE record='C100'").fetchone()[0]
    db.execute("INSERT INTO print_row_record (print_row, record) VALUES (?,'C100')", (pid,))
    db.execute("INSERT INTO print_row_record (print_row, record) VALUES (?,'bw-9')", (pid,))
    s.eq(db.execute("SELECT count(*) FROM print_row_record WHERE print_row = ?", (pid,))
         .fetchone()[0], 2,
         "and every record folded into a row stays resolvable, which is what `work_ids` is for")

    # ── §5j: A VOCABULARY WITH ONE HOME, AND A KEY INTO IT ────────────────────────────────────
    #
    # EACH OF THESE WAS FREE TEXT. A CHECK written in the schema would have been a SECOND home for
    # the vocabulary, so in every case the ruling moved into `facts/` first and the key followed.
    from facts import dating as _dating
    from facts import identity as _ident
    from facts import serialisation as _ser
    from facts import credit as _credit
    for table, names in (("work_state_kind", _ser.STATES), ("state_saying", _ser.SAYS),
                         ("release_kind", _ser.RELEASE_KINDS),
                         ("anchor_scheme", _ident.ANCHOR_SCHEMES),
                         ("ruling_shape", _ident.RULING_SHAPES),
                         ("volume_basis", _dating.VOLUME_BASES)):
        held = {r[0] for r in db.execute(f"SELECT name FROM {table}")}
        s.eq(sorted(held), sorted(names),
             f"{table} is the fact that states it, asked rather than restated")
    _refuses(s, db, "INSERT INTO work_state (work, state) VALUES ('w00002','running')", (),
             "a state no fact states is refused")
    _refuses(s, db, "INSERT INTO work_anchor (scheme, address, work) VALUES"
                    " ('ftp','x','w00001')", (), "and an anchor scheme nobody has ruled on")

    # `hiatus` HAS NO ROWS AND IS IN THE VOCABULARY ANYWAY. `build.py` writes it where a run has
    # skipped two consecutive slots, and a set assembled from the rows the corpus happens to hold
    # would refuse the first work that went on one. Reading the PRODUCERS is what found it.
    s.check("hiatus" in _ser.STATES, "a state the compiler can write is a state the store admits")
    db.execute("INSERT INTO work_state (work, state) VALUES ('w00002','hiatus')")
    s.check(True, "so a work going on hiatus is admitted rather than refused")

    # A FIELD MAY STATE SEVERAL JOBS AT ONCE, and a multi-valued column is the one shape a
    # relational store may not keep. 11 of the 39 role strings are a phrase joining atoms.
    s.check("企画・監修" not in _credit.roles() and "企画" in _credit.roles()
            and "監修" in _credit.roles(),
            "`企画・監修` is two jobs the splitter knows and one string the field wrote")
    db.execute("INSERT INTO credit_part (surface, seq, name, role) VALUES (?,1,'あ','企画・監修')",
               (line,))
    for atom in ("企画", "監修"):
        db.execute("INSERT INTO credit_part_role (surface, seq, role) VALUES (?,1,?)",
                   (line, atom))
    s.eq(db.execute("SELECT count(*) FROM credit_part_role WHERE surface = ?", (line,)).fetchone()[0],
         2, "so the phrase is kept as written and the jobs are held as rows")
    _refuses(s, db, "INSERT INTO credit_part_role (surface, seq, role) VALUES (?,1,'そうさ')",
             (line,), "and a job the splitter does not know is refused")

    # ── §5k: A DATE SAYS IT IS A DATE ─────────────────────────────────────────────────────────
    _refuses(s, db, "INSERT INTO work (id,title,first_publication) VALUES"
                    " ('w00021','T','yesterday afternoon')", (),
             "a date written in prose is refused, which it was not")
    db.execute("INSERT INTO work (id,title,first_publication) VALUES ('w00022','T','2024-03')")
    db.execute("INSERT INTO work (id,title,first_publication) VALUES ('w00023','T','2024-03-05')")
    s.eq(db.execute("SELECT count(*) FROM work WHERE first_publication IS NOT NULL").fetchone()[0],
         2, "while a partial date and a whole one are both admitted, which the corpus holds")

    # ── §1a: WHAT THE COMPILER COULD NOT ADMIT ────────────────────────────────────────────────
    #
    # An update runs unattended and must go on running. A refused row either fails the job or is
    # dropped in silence, and the second is worse because nothing says it happened.
    db.execute("INSERT INTO quarantine (target, refusal, row, came_from, at) VALUES"
               " ('claim','FOREIGN KEY constraint failed','[1,\"reading\"]',"
               "'claim reading authors X','2026-08-13')")
    s.eq(db.execute("SELECT count(*) FROM quarantine").fetchone()[0], 1,
         "a row the schema refused is held with the constraint that refused it")
    _refuses(s, db, "INSERT INTO quarantine (target, row, at) VALUES ('claim','[]','x')", (),
             "and a quarantined row that does not say what refused it is itself refused")

    # THE PATH THAT MATTERS RUNS AT 00:37 WITH NOBODY PRESENT, so it is watched here. A quarantine
    # nobody has seen accept a row is the same thing as a constraint nobody has seen refuse one.
    try:
        db.execute("INSERT INTO work_credit (work, credit) VALUES ('w99999','c00001')")
        s.check(False, "the row this is about must be refused in the first place")
    except sqlite3.IntegrityError as e:
        relational.quarantine_row(db, "INSERT INTO work_credit (work, credit) VALUES (?,?)",
                                  ("w99999", "c00001"), "edge from a capture", e, "2026-08-13")
    held = db.execute("SELECT target, row, came_from FROM quarantine ORDER BY id DESC").fetchone()
    s.eq(held[0], "work_credit", "a refused row is filed under the table it was going to")
    s.check("w99999" in held[1],
            "and the row is kept as the loader had it, so a person sees the data")
    s.eq(held[2], "edge from a capture", "with what produced it, so a deferral can name the adapter")
    s.eq(db.execute("SELECT count(*) FROM work_credit WHERE work = 'w99999'").fetchone()[0], 0,
         "AND NOTHING WAS ADMITTED: the quarantine is a record of a refusal, not a way round one")
    s.check("rows the store could not admit" in relational.QUESTIONS,
            "IT IS COUNTED, because a quarantine growing every day means the model is wrong and "
            "not that the captures were, and nothing else can tell those apart")

    # ── §5e: THE DISAGREEMENT RULE APPLIED TO SOMETHING OTHER THAN A NAME ─────────────────────
    #
    # Every one of the 3,040 works carries a state and 271 hold competing source claims about
    # whether the work is running. `claim` is scoped to names by its own CHECK, so the store had
    # one shape for one kind of disagreement and none for this.
    db.execute("INSERT INTO work_state (work, state, basis) VALUES"
               " ('w00001','completed','the newest chapter is titled 最終話')")
    db.execute("INSERT INTO state_claim (work, source, says, term, url) VALUES"
               " ('w00001','カドコミ','running','ongoing','https://comic-walker.com/x')")
    db.execute("INSERT INTO state_claim (work, source, says, term) VALUES"
               " ('w00001','ニコニコ漫画','completed','完結')")
    # §5j: THE READING IS A CLOSED SET AND THE PLATFORM'S OWN WORD IS NOT. `完結` and `finished`
    # are what two platforms print; `completed` is what we take them to mean.
    _refuses(s, db, "INSERT INTO state_claim (work, source, says) VALUES"
                    " ('w00002','コミッククリア','finished')", (),
             "a reading outside the vocabulary is refused, and the platform's word is kept beside it")
    s.eq(db.execute("SELECT count(*) FROM state_claim WHERE work='w00001'").fetchone()[0], 2,
         "two sources disagreeing about whether a work is running are two rows")
    _refuses(s, db, "INSERT INTO work_state (work, state) VALUES ('w00002','running')", (),
             "and the states are the seven the interface draws, not an eighth invented per row")
    _refuses(s, db, "INSERT INTO work_state (work, state) VALUES ('w00001','print')", (),
             "one work is in one state")

    # THE §13 REGISTER, and publisher-side labelling, which are different questions from the shelf
    # a work was admitted on.
    _refuses(s, db, "INSERT INTO work_presentation (work, visibility) VALUES ('w00001','hidden')",
             (), "a visibility outside the register is refused")
    db.execute("INSERT INTO work_presentation (work, label, visibility, source) VALUES"
               " ('w00001','yuri','marginal','madb')")
    s.eq(db.execute("SELECT label FROM work_presentation").fetchone()[0], "yuri",
         "and a label the publisher applied is held with where it came from")

    # THE BYLINE AS A WORK PRINTS IT. One line appears on many works, so it is an edge.
    db.execute("INSERT INTO surface (kind, folded) VALUES ('credit-line','原作あ／作画い')")
    line0 = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.execute("INSERT INTO work_byline (work, surface, kind)"
               " VALUES ('w00001', ?, 'credit-line')", (line0,))
    db.execute("INSERT INTO work_byline (work, surface, kind)"
               " VALUES ('w00002', ?, 'credit-line')", (line0,))
    s.eq(db.execute("SELECT count(*) FROM work_byline WHERE surface = ?", (line0,)).fetchone()[0],
         2, "one byline reaches two works, which a column on the surface could not say")

    # ── §5c: WHAT THE STORE SAID IT HELD AND DID NOT ──────────────────────────────────────────
    #
    # `admitted_by` WAS A NOT NULL HOLDING THE WORD `'unstated'` ON ALL 3,040 ROWS, because the
    # loader read it from `series.json` and the grounds are on `works.json`, structured, on 1,887
    # records. A NOT NULL whose every value is the word for null reports as filled.
    s.check("admitted_by" not in [r[1] for r in db.execute("pragma table_info(work)")],
            "the placeholder column is gone and the grounds are a table")
    db.execute("INSERT INTO admission (record, work, comparator, note) VALUES"
               " ('C900','w00001','cmoa.jp','DEFINITIONS §2, presumptive')")
    # §5j: THE SHELF IS THE COMPARATOR'S, NOT THE ROW'S. It was a second column repeating one pair
    # across 1,867 rows, which is a functional dependency on the comparator rather than on the row.
    s.eq(db.execute("SELECT c.shelf FROM admission a JOIN comparator c ON c.name = a.comparator")
         .fetchone()[0], "genre 37 (百合・GL)",
         "a work is admitted on a comparator, and the shelf is the comparator's own")
    _refuses(s, db, "INSERT INTO admission (record, work, comparator) VALUES"
                    " ('C901','w00002','someshop.jp')", (),
             "and a comparator no fact states is refused")
    _refuses(s, db, "INSERT INTO admission (record, work) VALUES ('C902','w99999')", (),
             "grounds for a work nobody holds are refused")

    # `volume_count` WAS NULL ON ALL 3,040 FOR THE SAME REASON, and it does not come back as a
    # column: 72 works have records stating DIFFERENT counts, so one column would have to pick and
    # discard a disagreement. How many are HELD is `count(volume)`, which is the other side of it.
    s.check("volume_count" not in [r[1] for r in db.execute("pragma table_info(work)")],
            "a count a source states is not a property of the work")
    db.execute("INSERT INTO volume_claim (work, record, volumes, source) VALUES"
               " ('w00001','C000100',6,'cmoa.jp')")
    db.execute("INSERT INTO volume_claim (work, record, volumes, source) VALUES"
               " ('w00001','bw-100',5,'cmoa.jp')")
    s.eq(db.execute("SELECT count(*) FROM volume_claim WHERE work='w00001'").fetchone()[0], 2,
         "TWO RECORDS OF ONE CATALOGUE DISAGREEING ABOUT THE RUN ARE TWO ROWS, which the old key "
         "could not hold: it keyed on a column that was the source 329 times and the record 2,244")
    _refuses(s, db, "INSERT INTO volume_claim (work, record, volumes) VALUES ('w00001','C000100',4)",
             (), "and one record states one count")
    _refuses(s, db, "INSERT INTO volume_claim (work, record, volumes) VALUES ('w00001','C000101',-1)",
             (), "while a negative run is refused")

    # WHICH ANSWER THE RECORD STANDS BEHIND. 638 surfaces carried a `verified` flag beside two or
    # more readings, and nothing said which one a person ruled on.
    db.execute("INSERT INTO claim (surface, kind, predicate, value, basis, source, displaced) VALUES"
               " (?,'title','reading','ヨミC','surface','x',1)", (orphan,))
    s.eq(db.execute("SELECT count(*) FROM claim WHERE displaced = 1 AND value = 'ヨミC'")
         .fetchone()[0], 1, "a claim somebody moved aside is kept and says so")
    _refuses(s, db, "INSERT INTO claim (surface, kind, predicate, value, basis, displaced) VALUES"
                    " (?,'title','reading','ヨミD','surface',2)", (orphan,),
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
    _refuses(s, db, "INSERT INTO identity_ruling (kind, subject, about, basis) VALUES"
                    " ('homophone','credit','x',NULL)", (),
             "a ruling with no reasoning is a preference and is refused")
    db.execute("INSERT INTO identity_ruling (kind, subject, about, reading, basis) VALUES"
               " ('homophone','credit','蒼井','アオイ','two spellings with no character in common')")
    s.eq(db.execute("SELECT count(*) FROM identity_ruling").fetchone()[0], 1,
         "and one with its reasoning is held")
    _refuses(s, db, "INSERT INTO identity_ruling (kind, subject, about, basis) VALUES"
                    " ('guessed','credit','y','x')", (),
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
    _refuses(s, db, "INSERT INTO volume (work, volume, record, seq) VALUES ('w00001',-5, 'C000006', 0)", (),
             "a negative volume number is refused")

    # `romanisation` WAS DECLARED LEGAL AND MADE UNSTATEABLE by the composite key, which is a schema
    # contradicting itself. It is out of the enum, so the contradiction is gone rather than hidden.
    _refuses(s, db, "INSERT INTO claim (surface,kind,predicate,value,basis) "
                    "VALUES (?,'title','romanisation','Yuri','translated')", (orphan,),
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
