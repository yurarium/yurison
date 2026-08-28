#!/usr/bin/env python3
"""The relational store: schema, loader, and the questions it makes askable.

DERIVED, AND NEVER A SOURCE OF TRUTH. Everything here is rebuilt from `data/build` plus the rulings
the facts hold, so deleting the database costs the time of one rebuild. It is not committed.

WHAT IT IS FOR, and it is not speed alone. Five invariants in `check.py` are foreign keys written
out as Python and run after the damage; two more stop being expressible at all, because a page can
only list what an edge says. `adapters/relational/schema.sql` names each one beside the constraint that
replaces it.

Usage:
    ./adapters/relational/__init__.py --build     compile data/build into data/relational.db
    ./adapters/relational/__init__.py --ask       run the standing questions and print the answers
"""
import argparse
import json
import pathlib
import re
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))

from facts import namekey as _namekey
from relational import delta as _delta                                  # noqa: E402
from relational import delta                                            # noqa: E402
from facts import reading as _reading                                   # noqa: E402
from names import provenance as _prov                                   # noqa: E402
from names import ruby as _rubymod                                      # noqa: E402
from facts import romanisation as _romanmod                             # noqa: E402

#: HOW A ROLE PHRASE DIVIDES, which `facts/credit/splitter.ROLE_PHRASE` already writes as the
#: separators a field puts between two jobs.
_ROLE_SEP = re.compile(r"[\s\u3000・･/／]+")

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = pathlib.Path(__file__).resolve().parent / "schema.sql"
DB = ROOT / "data" / "relational.db"
BUILD = ROOT / "data" / "build"

#: The standing questions, kept beside the schema that makes them one line each. Each was a script
#: or was unaskable before. They are the derivations `delta.py` recomputes and digests. Typed once
#: there: a question the store answers and a derivation whose digest gates the cascade are the same
#: thing, and two copies of the SQL would let a partial update and a full rebuild answer differently.
QUESTIONS = {name: spec["sql"] for name, spec in _delta.DERIVATIONS.items()}


def open_db(path=None):
    """A connection to an existing store, with the foreign keys ON.

    THE ONE OPENER, AND §5a IS THE WHOLE REASON IT EXISTS. `PRAGMA foreign_keys = ON` sits at the
    top of `schema.sql`, and it is a PER-CONNECTION setting that SQLite does not store in the file.
    `executescript` applied it to the connection doing the build and to nothing else, so every other
    reader of this database ran with the keys OFF: `ask`, `equivalent` and `delta.write` each opened
    with a bare `sqlite3.connect` and got 0.

    WHAT THAT COST. `INSERT INTO work_credit VALUES ('w-nope','c-nobody','x',0)` was accepted on any
    such connection. The header of `schema.sql` claims five `check.py` invariants have become
    foreign keys; that held for a full rebuild and held nowhere else, and §7's incremental path is
    exactly where it did not hold. It is the shape §2 met with `INSERT OR IGNORE`: a constraint that
    quietly does not apply reads as coverage.

    So nothing in this package calls `sqlite3.connect` directly any more. `adapters/lint/onewriter`
    already refuses a second writer; this is the same argument about a second OPENER.
    """
    db = sqlite3.connect(pathlib.Path(path or DB))
    db.execute("PRAGMA foreign_keys = ON")
    return db


def canary_copy(db, sql):
    """A private copy of `db` with `sql` applied, for a self-test to plant a violation in.

    ON A COPY AND NOT ON THE STORE, §10. `backup` into memory costs 25 ms for this database, so a
    self-test never writes to the file the next check reads, and a canary that failed to roll back
    could not silently become the corpus.

    HERE RATHER THAN IN `check.py`, because `adapters/lint/onewriter` refuses a second opener and is
    right to: the argument for one opener is `PRAGMA foreign_keys`, which a copy needs exactly as
    much as the original. It is applied below.
    """
    mem = sqlite3.connect(":memory:")
    db.backup(mem)
    mem.execute("PRAGMA foreign_keys = ON")
    mem.executescript(sql)
    return mem


def create(path=None):
    """A fresh database with the schema applied, carrying any quarantine forward.

    THE ONE THING HERE THAT IS NOT RECOMPUTABLE, and §5g is where that was faced. This file's header
    calls the store derived and says deleting it costs time alone, which is true of every table but
    one: a quarantined row is what an unattended run met and could not admit, and a rebuild that
    unlinks the file erases the only record that it happened. Measured before this changed: 1 row
    before a rebuild, 0 after.

    SO IT IS CARRIED ACROSS AND THE HEADER SAYS SO. A row stays quarantined until something admits
    it or §9 rules on it, and a rebuild is not either of those. What a rebuild does establish is
    that the loader still refuses it, which is why the row is kept rather than retried.
    """
    p = pathlib.Path(path or DB)
    p.parent.mkdir(parents=True, exist_ok=True)
    kept = []
    if p.exists():
        try:
            old = sqlite3.connect(p)
            kept = old.execute("SELECT target, refusal, row, came_from, at FROM quarantine").fetchall()
            old.close()
        except sqlite3.DatabaseError:
            kept = []                      # no quarantine to carry, which is the ordinary case
        p.unlink()
    db = open_db(p)
    db.executescript(SCHEMA.read_text(encoding="utf-8"))
    # `executescript` COMMITS AND THE PRAGMA SURVIVES IT, since it is connection state rather than a
    # statement in a transaction. Asserted rather than assumed, because everything below rests on it.
    if not db.execute("PRAGMA foreign_keys").fetchone()[0]:
        raise RuntimeError("foreign keys are off on a freshly created store")
    db.executemany("INSERT INTO quarantine (target, refusal, row, came_from, at)"
                   " VALUES (?,?,?,?,?)", kept)
    return db


def stamp(db, at=None):
    """Say what this store is: the schema it was made against, and when. §11.

    A CONSUMER REFUSES ON THIS RATHER THAN TRUSTING IT. The published artefact carries no promise of
    format, so what a site build needs is a way to tell that the shape has moved; the digest of
    `schema.sql` changes exactly when the schema does, which a hand-typed number would not.
    """
    import hashlib
    # CREATED HERE TOO, so a store made before §11 gains one rather than refusing an update. The
    # same reasoning as `delta.ensure`: the file on disk outlives the schema that made it.
    db.execute("CREATE TABLE IF NOT EXISTS store_stamp (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    digest = hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
    db.execute("INSERT INTO store_stamp (key, value) VALUES ('schema', ?)"
               " ON CONFLICT(key) DO UPDATE SET value = excluded.value", (digest[:16],))
    # A DATE THE CALLER DID NOT STATE LEAVES THE ONE ALREADY THERE. A rebuild run by hand has no
    # date to give and should not blank the one the last compile stamped.
    if at:
        db.execute("INSERT INTO store_stamp (key, value) VALUES ('generated', ?)"
                   " ON CONFLICT(key) DO UPDATE SET value = excluded.value", (str(at),))
    db.execute(f"PRAGMA user_version = {int(digest[:7], 16)}")
    return digest[:16]


def load_rulings(db):
    """The basis table and the attribution table, taken from the facts that own them.

    ASKED, NOT COPIED. This is the whole reason the schema can hold them: `facts/division` states
    each basis once and `facts/reading` states which kind each basis admits, and both are read here
    rather than restated. A schema with its own copy of the vocabulary would be the drift again in
    a new file format.
    """
    from facts import division as _div
    from facts import reading as _rd

    for b in _div.BASES:
        db.execute("INSERT INTO basis (name, cited, donates, marked, counted) VALUES (?,?,?,?,?)",
                   (b, int(_div.cites_its_source(b)), int(_div.may_donate(b)),
                    int(_div.is_marked(b)), int(_div.counted_uncited(b))))
    # A BASIS READING KNOWS ABOUT AND DIVISION DOES NOT, or the other way round, still needs a row:
    # a claim cannot reference a basis the table has never heard of.
    for b in _rd.bases():
        db.execute("INSERT OR IGNORE INTO basis (name, cited, donates, marked, counted) "
                   "VALUES (?,0,0,1,1)", (b,))
    # AN ENGLISH BASIS ANSWERS NONE OF THE FOUR, and says so rather than saying no to each. They ask
    # what a READING's basis licenses, and `licensed` has no view on whether it may lend a division.
    for b in _rd.en_bases():
        db.execute("INSERT OR IGNORE INTO basis (name) VALUES (?)", (b,))
    # WHICH BASIS BELONGS TO WHICH CLAIM, ASKED OF THE FACTS THAT RANK THEM. `stated` is in both
    # vocabularies and means a different document in each, which is the pair this table exists to
    # tell apart. `romanisation` has no bases: it is a function of the reading and rests on nothing.
    #
    # THE READING VOCABULARY IS BOTH SETS AND NOT EITHER ONE. `reading.bases()` names the four a
    # source can STATE and `division.BASES` names the six a reading can REST on, and `analyser` is
    # in the second alone; registering the first alone refused 3,496 analyser readings the corpus
    # holds. It is the same union `basis` itself is filled from, ten lines above.
    for b in set(_rd.bases()) | set(_div.BASES):
        db.execute("INSERT OR IGNORE INTO basis_for_predicate (basis, predicate, rank) "
                   "VALUES (?,'reading',?)", (b, _div.rank(b)))
    for b in _div.BASES:
        db.execute("INSERT OR IGNORE INTO basis_for_predicate (basis, predicate, rank) "
                   "VALUES (?,'division',?)", (b, _div.rank(b)))
    for b in _rd.en_bases():
        db.execute("INSERT OR IGNORE INTO basis_for_predicate (basis, predicate, rank) "
                   "VALUES (?,'english',?)", (b, _rd.en_rank(b)))
    # SOURCE_KIND IS EVERY KIND THAT EXISTS; basis_admits_kind is which PAIRS are allowed. Keeping
    # those separate is what lets `analyser` be a real kind that states nothing.
    #
    # A GAP THE SCHEMA FOUND, and the answer is `facts/reading`'s and not this loader's. 3,056
    # readings carry `reading_source_kind: analyser` and READING_ATTRIBUTION has no row for it,
    # because that table answers who may STATE a reading and an analyser states nothing. The pair
    # was written here, which put a vocabulary decision in the code that reads the data; it is
    # `_rd.analyser_pair()` now, beside the table it is an exception to.
    #
    # IT WAS NOT EVERY KIND THAT EXISTS, WHICH §5 FOUND BY BEING REFUSED. This was assembled from
    # the READING attributions, so `bibliography` had no row: it is admitted for `official-jp` and
    # for nothing else, which is an ENGLISH basis, and 113 English names transcribed from a book's
    # own title page were refused. `facts/reading.SOURCE_KINDS` is the vocabulary itself and is
    # what this should always have asked.
    kinds = (set(_rd.SOURCE_KINDS) | {k for b in _rd.bases() for k in _rd.kinds_for(b)}
             | {_rd.analyser_pair()[1]})
    for k in sorted(kinds):
        db.execute("INSERT INTO source_kind (name) VALUES (?)", (k,))
    for s in _prov.SELF_SOURCED:
        db.execute("INSERT INTO self_sourced (source) VALUES (?)", (s,))
    # WHOSE SHELF ADMITS A WORK, ASKED OF THE FACT THAT STATES IT. `admission` held the comparator
    # and its shelf on every row, which is one pair repeated 1,867 times.
    from facts import inclusion as _inc
    for shop, shelf in _inc.SHELVES.items():
        db.execute("INSERT INTO comparator (name, shelf) VALUES (?,?)", (shop, shelf))
    # THE VOCABULARIES §5j GAVE A HOME TO, each asked of the fact that states it. A list written out
    # here instead would be the second copy every one of these was moved to avoid.
    from facts import dating as _dating
    from facts import identity as _ident
    from facts import serialisation as _ser
    from facts import credit as _credit
    for table, names in (("work_state_kind", _ser.STATES), ("state_saying", _ser.SAYS),
                         ("release_kind", _ser.RELEASE_KINDS),
                         ("anchor_scheme", _ident.ANCHOR_SCHEMES),
                         ("ruling_shape", _ident.RULING_SHAPES),
                         ("volume_basis", _dating.VOLUME_BASES),
                         ("role", _credit.roles())):
        for n in names:
            db.execute(f"INSERT OR IGNORE INTO {table} (name) VALUES (?)", (n,))
    # BOTH ATTRIBUTION TABLES, SCOPED BY THE CLAIM EACH ANSWERS FOR. This was filled from the reading
    # one alone, so `('translated','derived')` read as forbidden 2,767 times while `facts/reading`
    # admits it on its first line. `stated` means a different document for a reading than for an
    # English name, which is why the predicate is part of the key rather than a note beside it.
    # HOW MUCH EACH KIND OF EVIDENCE IS WORTH, asked of the module that decides it. The rank, the
    # party type and the clause each was read out of are one fact per KIND, not per row.
    sys.path.insert(0, str(ROOT / "adapters" / "classify"))
    from classify import credence as _cred_mod
    for _k, _rank in _cred_mod.RANK.items():
        db.execute("INSERT OR IGNORE INTO credence_kind (name, rank, type, rule) VALUES (?,?,?,?)",
                   (_k, _rank, _cred_mod.TYPE[_k], _cred_mod.RULE[_k]))
    for _h in ("volumes", "delivery-date", "attribution"):
        db.execute("INSERT OR IGNORE INTO holding (name) VALUES (?)", (_h,))
    for b in _rd.bases():
        for k in _rd.kinds_for(b):
            db.execute("INSERT OR IGNORE INTO basis_admits_kind (basis, predicate, source_kind)"
                       " VALUES (?,'reading',?)", (b, k))
    for b in _rd.en_bases():
        for k in _rd.en_kinds_for(b):
            db.execute("INSERT OR IGNORE INTO basis_admits_kind (basis, predicate, source_kind)"
                       " VALUES (?,'english',?)", (b, k))
    db.execute("INSERT OR IGNORE INTO basis_admits_kind (basis, predicate, source_kind)"
               " VALUES (?,'reading',?)", _rd.analyser_pair())
    return db


def _kind_of(record, claim="reading"):
    """The source kind for a claim, with a self-sourced one normalised to `derived`.

    `surface` and `title-furigana` are read off a name and a title the corpus already holds, so
    there is no address to record and the schema must not demand one. Saying `derived` is what the
    attribution table already means by it, and it keeps the CHECK simple enough to read.

    IT ASKED ONLY ABOUT THE READING UNTIL §5, and English claims arrived reading `platform` where
    the source is the name's own surface: 194 authors are already written in Latin, so their
    English IS their name and there is no page behind it. 194 rows were refused for want of an
    address to a document that does not exist, which is the same shape as the 382 §2 refused.
    """
    if str(record.get(f"{claim}_source") or "") in set(getattr(_prov, "SELF_SOURCED", ())):
        return "derived"
    return record.get(f"{claim}_source_kind")


def _rows(name, key, source=None):
    """The rows of a built collection as `(id_or_None, row)` pairs.

    `source` IS THE COMPILER'S OWN ROWS, WHICH IS WHAT §6 REVERSES. Reading `data/build` makes this
    store downstream of the artefact it is meant to replace, so `build.py` hands its structures
    straight in and the files stop being on the path at all.

    A COLLECTION KEYED BY ID IS NOT A LIST, and flattening it to `.values()` threw the identifier
    away. `credits.json` is a dict whose KEY is `c00001`, which sent me to the identity registry for
    something I already had.
    """
    d = (source or {}).get(name)
    if d is None:
        p = BUILD / f"{name}.json"
        if not p.exists():
            return []
        d = json.loads(p.read_text(encoding="utf-8"))
    got = d.get(key) if isinstance(d, dict) else d
    if isinstance(got, dict):
        return list(got.items())
    return [(None, r) for r in (got or [])]


def _flag(row, key):
    """A boolean the row STATES, as 0 or 1, and NULL where it states nothing.

    ABSENCE IS A STATE (§5). `late_discovered` is on 515 of 974 rows and false on some of them, and
    a column defaulting to 0 would say we had looked and found nothing where nobody had looked.
    """
    got = (row or {}).get(key)
    return None if got is None else int(bool(got))


def quarantine_row(db, sql, args, what, error, at=None):
    """Record a row the schema refused, so an unattended run can carry on. STORE-PLAN §1a.

    IT IS REACHABLE FROM A TEST, which a closure inside `build` was not. The path that matters here
    runs only when an update writes at 00:37, and a quarantine nobody has seen accept a row is the
    same thing as a constraint nobody has seen refuse one.
    """
    db.execute("INSERT INTO quarantine (target, refusal, row, came_from, at) VALUES (?,?,?,?,?)",
               (_target_of(sql), str(error),
                json.dumps(list(args), ensure_ascii=False, default=str), what, at or "unstamped"))
    return False


def _isbn(value):
    """An ISBN as the schema keys it: the digits alone, with any hyphen or space taken out.

    A HYPHEN IS TYPOGRAPHY. `9784091572882` and `978-4-09-157288-2` are one book, and
    keying on the string made them two rows, so "one ISBN is one book" never fired and hid two
    duplicate WORKS behind it. The table refuses anything that is not this form, so normalising here
    and refusing there are the same rule stated once each side of the insert.
    """
    got = str(value or "").replace("-", "").replace(" ", "").upper()
    return got if got else None


def _target_of(sql):
    """The table an INSERT or an UPDATE names, for the quarantine to file the row under."""
    words = str(sql).replace("(", " ").split()
    for i, w in enumerate(words):
        if w.upper() in ("INTO", "UPDATE") and i + 1 < len(words):
            return words[i + 1]
    return "?"


def _putter(db, refused, quarantine=False, at=None):
    """The one insert site, which records what the schema refused rather than relaxing it.

    A FACTORY BECAUSE TWO LOADERS NEED IT. `build` fills the store and `renderings` fills the part of
    it the compiler cannot hand over until later, and a second copy of this is how one of them would
    come to swallow a refusal the other counts.
    """
    def put(sql, args, what):
        try:
            db.execute(sql, args)
            return True
        except sqlite3.IntegrityError as e:                              # noqa: PERF203
            refused.append((what, str(e)))
            if quarantine:
                quarantine_row(db, sql, args, what, e, at)
            return False
    return put


def _surfacer(db):
    """`surface_id(kind, ja, subject_kind=None, subject=None)`, get-or-create, with its subjects.

    ONE PRODUCER OF A `surface` ROW (§3). Two loaders need those rows, the name store's claims and
    the build's renderings, and a second insert site is how the two would come to disagree about a
    fold.

    WHAT A NAME NAMES, ASKED OF THE REGISTRY AND NOT OF A TITLE MATCH. §5d. A credit is reached by
    every spelling that resolves to it, which is 2,473 spellings rather than the one `credits.json`
    happens to print. A work is reached by the FOLD of its title, because that is what the site joins
    on and the registry's own anchors are addresses rather than names.

    A FOLD MAY REACH TWO WORKS and both are recorded. `百合漫画短編集` names w01990 and w02284.

    THE CACHE IS READ BACK OFF THE STORE, so a call on a store an earlier pass built finds the rows
    that pass made instead of inserting a second one and being refused.
    """
    by_subject = {"credit": {}, "work": {}, "publisher": {}}
    for sp, cid in db.execute("SELECT spelling, credit FROM credit_spelling"):
        by_subject["credit"].setdefault(_namekey.fold(sp), []).append(cid)
    for s, cid in db.execute("SELECT surface, id FROM credit"):
        by_subject["credit"].setdefault(_namekey.fold(s), []).append(cid)
    for i, ttl in db.execute("SELECT id, title FROM work"):
        by_subject["work"].setdefault(_namekey.fold(ttl), []).append(i)
    for i, nm in db.execute("SELECT id, name FROM publisher"):
        by_subject["publisher"].setdefault(_namekey.fold(nm), []).append(i)
    surfaces = {(k, f): i for i, k, f in db.execute("SELECT id, kind, folded FROM surface")}

    def surface_id(kind, ja, subject_kind=None, subject=None, **cols):
        """The row for one string, made once, with every subject the registry says it names."""
        folded = _namekey.fold(str(ja or ""))
        if not folded:
            return None
        got = surfaces.get((kind, folded))
        if got is None:
            db.execute("INSERT INTO surface (kind, folded) VALUES (?,?)", (kind, folded))
            got = surfaces[(kind, folded)] = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            if subject_kind:
                for sub in ([subject] if subject else by_subject[subject_kind].get(folded, [])):
                    db.execute("INSERT OR IGNORE INTO names (surface, kind, work, credit,"
                               " publisher) VALUES (?,?,?,?,?)",
                               (got, kind,
                                sub if subject_kind == "work" else None,
                                sub if subject_kind == "credit" else None,
                                sub if subject_kind == "publisher" else None))
        for col, value in cols.items():
            if value is not None:
                db.execute(f"UPDATE surface SET {col} = ? WHERE id = ?", (value, got))
        return got

    return surface_id



def build(path=None, quarantine=False, at=None, source=None):
    """Compile `data/build` into the store. Returns `(db, counts, refused)`.

    REFUSED ROWS ARE THE POINT AND ARE COUNTED, not swallowed. A row the schema will not accept is
    a row the current pipeline can produce and should not, so the loader reports how many and why
    instead of relaxing a constraint to make the number go away.

    `quarantine` IS FOR THE UNATTENDED PATH AND FOR NOTHING ELSE, STORE-PLAN §1a. With it on, a
    refused row is written to the `quarantine` table with the constraint that refused it and the run
    continues, which is what lets an update at 00:37 populate what it can. A REBUILD leaves it off
    and fails on a refusal: the loader is wrong until shown otherwise, and it has been every time so
    far. `at` is the date to stamp a quarantined row with, passed in rather than read from the clock
    so a rebuild is reproducible.

    `source` IS §6. With it the compiler hands its own rows in and this store is built from them
    rather than from the files it wrote, which is the direction the whole plan turns on. Without
    it, `data/build` is read, which is what a rebuild and the weekly reconciliation do.
    """
    # A REBUILD READS `data/build` AND §13 STOPPED WRITING IT. Without a source the loader takes
    # the corpus JSON, and since `build.py --emit-json` became the only thing that writes those
    # files a rebuild on an ordinary tree loads no works at all: every `superseded` row then fails
    # its foreign key and the caller is handed 153 refusals to read, which says nothing about what
    # is actually wrong. The gate failed that way for three pushes.
    #
    # SAID ONCE, PLAINLY, BEFORE ANY OF IT. `build.py` is the compiler now; a rebuild from files
    # is a rebuild from files that are not there.
    if source is None:
        _corpus = ROOT / "data" / "build" / "series.json"
        if not _corpus.exists():
            raise SystemExit(
                f"no corpus JSON at {_corpus}: §13 stopped `build.py` writing it, so there is "
                "nothing here to rebuild from. `python3 build.py` compiles the store, and "
                "`build.py --emit-json` writes the files this path wants.")
    db = load_rulings(create(path))
    counts, refused = {}, []
    put = _putter(db, refused, quarantine, at)
    stamp(db, at)
    _load_all(db, source, put, counts, refused)
    db.commit()
    return db, counts, refused



def note(db, mapping):
    """Record scalars the run has to say about itself in `run_report`. Returns how many. §13.

    ONE STATEMENT FOR ONE TABLE, which is what `the store has one writer` asks and what the three
    passes that write here would otherwise break. `build.py` records the run's counts, `ledger.py`
    the depth of the window it holds, and the loader the feed's own shape; each computes something
    different and all three were about to carry their own INSERT. The check found the second and
    third the moment they appeared, which is the check working.

    SCALARS ONLY, AND THAT IS THE POINT OF THE TABLE. A value that wants to be a list or a mapping
    is a row somewhere else: `run_source`, `run_queue` and `run_drop` all exist because a census
    entry is a row, and putting one here as JSON text would rebuild the file this replaces. Nested
    counts arrive under a dotted key, `collapsed.samples`, and the emitter puts them back together.
    """
    n = 0
    for key, value in sorted((mapping or {}).items()):
        db.execute("INSERT OR REPLACE INTO run_report (key, value) VALUES (?,?)",
                   (key, None if value is None else str(value)))
        n += 1
    return n


def save(db, path=None):
    """Write a compiled store out to the file, replacing whatever was there. Returns the path.

    THE SCRATCH IS THE COMPLETE STORE AND REBUILDING FROM `source` IS NOT. `build.py` compiles into
    memory, hands the result the name map through `renderings`, and only then reconciles the file
    against it. The two paths that could not reconcile, a clean checkout with no file and a delta
    the schema refused, both called `build(source=...)` again, and `source` is the compiler's ROWS
    with no renderings in it: the store came out holding titles, authors and publishers and none of
    the 17,263 floor and phrase surfaces that are what an English page falls back to.

    EVERY STORE CI HAS EVER PUBLISHED WAS THAT ONE, because a fresh checkout has no file by
    definition. It went unseen while the site was served JSON this repository wrote from the
    scratch; the day §11 made the site emit `feed/names.json` from the published store, `floor`
    arrived empty and every Japanese run in English mode rendered as one `?` per character. 25,172
    of them on the front page.

    SO THE FILE IS A COPY OF THE SCRATCH rather than a second compile of the same inputs. There is
    only one compile per run now, which is also the only way to be sure the published store and the
    store this run checked are the same store.
    """
    # AND THE SOURCE IS COMMITTED FIRST, WHICH IS NOT TIDINESS. `Connection.backup` asks SQLite for
    # a read lock, and an open write transaction on the source refuses it; Python's binding answers
    # a refusal by sleeping a quarter second and trying again, with no attempt limit, so a scratch
    # with one uncommitted INSERT in it hangs the call for ever rather than raising. `renderings`
    # leaves exactly that open, which is how this was found: a test that never finished.
    db.commit()
    path = pathlib.Path(path or DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    out = sqlite3.connect(path)
    try:
        db.backup(out)
        out.commit()
    finally:
        out.close()
    return path


def renderings(db, doc, put=None, surface_id=None, counts=None):
    """The derived name map, loaded into the store. STORE-PLAN §6.

    A SEPARATE STEP BECAUSE THE MAP IS DOWNSTREAM OF TWO FILES THE STORE EMITS. `floor` is every
    string the interface will render, and it is assembled by walking the credit pages and the
    publisher pages, which are `emit.credits` and `emit.publishers` and come out of a store that
    already exists. So the compiler builds the store, emits those two, assembles the map, and hands
    it back here. A rebuild with no compiler in front of it reads `data/build` instead, which is
    what `build()` does when nothing hands it a map.

    THE HELPERS ARE REBUILT WHERE NOTHING PASSES THEM, so this is callable on a store that was made
    by an earlier call. `surface_id` is get-or-create either way, so a store that already holds a
    fold finds the row it made instead of a second row under the same key.
    """
    refused = []
    if put is None:
        put = _putter(db, refused)
    if surface_id is None:
        surface_id = _surfacer(db)
    if counts is None:
        counts = {}

    def entries(section):
        """One section's entries, with a key that is already its own fold taken first.

        SOME KEYS IN THIS FILE ARE NOT FOLDED AND THE SITE CAN ONLY LOOK UP FOLDED ONES, which §5
        found by seeing one publisher's romanisation vanish. 62 of 386 publisher keys and 112 of 399
        imprint keys hold a space NFKC keeps, and `app.js` reaches every one of them through
        `foldKey`, so 24 publishers collapse onto 12 folded keys and 5 of those pairs hold different
        things. `いんどの宮殿！` carries the English and `いんどの宮殿!` carries the identifier, and
        the second is the one a reader's lookup lands on.

        THAT IS A FAULT IN THE BUILD AND NOT IN THIS LOADER, so it is recorded in docs/GAPS.md and
        deferred. What this does is stop the store's copy depending on which spelling the emitter
        happened to write first: the entry the SITE can reach is the one that wins here.
        """
        rows = list((doc.get(section) or {}).items())
        return sorted(rows, key=lambda kv: _namekey.fold(kv[0]) != kv[0])

    def romanise(sid, got):
        """The three styles, where a string means all three agree."""
        styles = ({"plain": got, "macron": got, "double": got} if isinstance(got, str)
                  else (got or {}))
        for style, value in styles.items():
            if value and style in ("plain", "macron", "double"):
                put("INSERT OR IGNORE INTO romanisation (surface, style, value) VALUES (?,?,?)",
                    (sid, style, value), f"romanisation {style}")

    for section, kind, subject_kind in (("titles", "title", "work"), ("authors", "author", "credit"),
                                        ("publishers", "publisher", "publisher")):
        for folded, r in entries(section):
            sid = surface_id(kind, folded, subject_kind, r.get("id"))
            if sid is None:
                continue
            romanise(sid, r.get("romaji"))
            for i, span in enumerate(r.get("ruby") or []):
                text, reading = (list(span) + [None, None])[:2]
                if text:
                    put("INSERT OR IGNORE INTO ruby (surface, seq, text, reading) VALUES (?,?,?,?)",
                        (sid, i, text, reading), f"ruby {folded} {i}")

    # A TITLE STANDING FOR ANOTHER, resolved after every title has a row, since an alias may be read
    # before the name it points at.
    for folded, r in entries("titles"):
        if r.get("alias_of"):
            here, there = surface_id("title", folded), surface_id("title", r["alias_of"])
            if here and there and here != there:
                put("UPDATE surface SET alias_of = ? WHERE id = ?", (there, here),
                    f"alias {folded}")

    # THE TWO ROMANISATION MAPS. `floor` answers for any Japanese run that can reach a surface, in
    # the three styles; `phrases` answers for a whole chapter name or credit line in one. They are
    # different populations of string and each is keyed by the same fold as everything else.
    for folded, got in entries("floor"):
        sid = surface_id("floor", folded)
        if sid is not None:
            romanise(sid, got)
    for folded, got in entries("phrases"):
        sid = surface_id("phrase", folded)
        # THE MACRON STYLE, AND SAYING SO IS THE POINT. `phrases` ships one spelling and the site
        # renders it unchanged, so filing it under a style names which spelling a reader is getting
        # rather than leaving a bare string to be mistaken for all three.
        if sid is not None and got:
            put("INSERT OR IGNORE INTO romanisation (surface, style, value) VALUES (?,'macron',?)",
                (sid, got), f"phrase {folded}")
    counts["romanisation"] = db.execute("SELECT count(*) FROM romanisation").fetchone()[0]
    counts["ruby"] = db.execute("SELECT count(*) FROM ruby").fetchone()[0]

    for folded, r in entries("credit_parts"):
        sid = surface_id("credit-line", folded)
        if sid is None:
            continue
        put("INSERT INTO credit_division (surface, kind, joiner, partial)"
        " VALUES (?,'credit-line',?,?)",
            (sid, r.get("j") or "", int(bool(r.get("part")))), f"division {folded}")
        for i, part in enumerate(r.get("p") or []):
            if not part.get("n") and not part.get("etc"):
                continue
            put("INSERT OR IGNORE INTO credit_part (surface, seq, name, name_folded, role, etc)"
                " VALUES (?,?,?,?,?,?)",
                (sid, i, part.get("n"), _namekey.fold(part["n"]) if part.get("n") else None,
                 part.get("r"), int(bool(part.get("etc")))),
                f"part {folded} {i}")
            # A FIELD MAY STATE SEVERAL JOBS AT ONCE, `企画・監修`, and a multi-valued column is the
            # one shape a relational store may not keep. The separators are the splitter's own.
            for atom in _ROLE_SEP.split(str(part.get("r") or "")):
                if atom:
                    put("INSERT OR IGNORE INTO credit_part_role (surface, seq, role)"
                        " VALUES (?,?,?)", (sid, i, atom), f"role {folded} {i} {atom}")
        for text in (r.get("drop") or []):
            put("INSERT OR IGNORE INTO credit_dropped (surface, text) VALUES (?,?)",
                (sid, text), f"dropped {folded}")
    counts["credit_part"] = db.execute("SELECT count(*) FROM credit_part").fetchone()[0]

    # THE STRINGS A CATALOGUE WRITES A LINE UNDER, which is the population `feed/names.json` keys
    # its imprints map by. What the line IS comes from the registry and is loaded with the imprint
    # rows themselves; this is only the surface a reader's lookup lands on.
    for folded, _r in entries("imprints"):
        surface_id("imprint", folded)
    counts["surface"] = db.execute("SELECT count(*) FROM surface").fetchone()[0]

    return counts, refused



def _load_all(db, source, put, counts, refused):
    """Everything a compile puts in the store. One loader, called by a rebuild and by a delta.

    EXTRACTED SO `apply` AND `build` CANNOT DIVERGE, §7. A delta that compiled its rows differently
    from a rebuild would make the weekly reconciliation report the difference between two loaders
    rather than a fault in the incremental path, which is the one thing that reconciliation exists
    to be able to say.
    """


    import yaml
    IDENT = ROOT / "data" / "identity"

    def _yaml(name):
        f = IDENT / f"{name}.yaml"
        return (yaml.safe_load(f.read_text(encoding="utf-8")) or {}) if f.exists() else {}

    seen_credit = {}
    for _k, r in _rows("series", "series", source):
        wid = r.get("id")
        if not wid or not str(wid).startswith("w"):
            continue
        put("INSERT OR IGNORE INTO work (id, title, first_publication, first_event,"
            " explicit_content) VALUES (?,?,?,?,?)",
            (wid, r.get("work") or "", r.get("first"), r.get("first_event"),
             int(bool(r["explicit_content"])) if r.get("explicit_content") is not None else None),
            f"work {wid}")
    counts["work"] = db.execute("SELECT count(*) FROM work").fetchone()[0]

    # FROM THE REGISTRY AND NOT FROM `credits.json`, WHICH THIS STORE NOW EMITS. §6 moved that file
    # to `emit.credits`, and loading the tables behind it from the file would make the file its own
    # input: a clean checkout has no `credits.json` until the store writes one, so the store would
    # build empty and emit empty. CI found that within the hour, on a run where the local tree still
    # had yesterday's file to read.
    #
    # `data/identity/credits.yaml` IS THE SOURCE ANYWAY, and `credit_spelling`, `superseded` and
    # `identity_ruling` have been read from it since §5d. This brings the last two tables of the
    # domain onto the same footing.
    import credit_identity as _cid_mod
    for r in (_yaml("credits").get("credits") or []):
        cid, surface = r.get("id"), r.get("credit")
        if not cid or not surface or r.get("merged_into"):
            continue
        if surface in seen_credit:
            refused.append((f"credit {cid}", f"surface already held by {seen_credit[surface]}"))
            continue
        seen_credit[surface] = cid
        put("INSERT INTO credit (id, surface, kind, registered) VALUES (?,?,?,?)",
            (cid, surface, _cid_mod.shape_of(r.get("kind")), r.get("kind")), f"credit {cid}")
    counts["credit"] = db.execute("SELECT count(*) FROM credit").fetchone()[0]

    # FROM THE REGISTRIES, FOR THE THIRD TIME AND THE LAST. `publishers.json` is emitted by §6, so
    # loading these from it would make the file its own input, which is the fault CI caught on
    # `credits.json` and which then took every retired credit forwarder off the site. The rule this
    # settles into: a table behind a file the store EMITS is loaded from the source that file was
    # compiled from, never from the file.
    import publisher_identity as _phid_mod
    from facts import imprint as _imp_mod
    for e in (_yaml("publishers").get("publishers") or []):
        pid, raw = e.get("id"), e.get("publisher")
        if not pid or not raw or e.get("merged_into"):
            continue
        put("INSERT OR IGNORE INTO publisher (id, name) VALUES (?,?)",
            (pid, _phid_mod.publisher_of(raw)), f"publisher {pid}")
    # A LINE BELONGS TO THE HOUSES THE REGISTRY NAMES, and `data/names/imprints.yaml` is where that
    # is stated rather than in the file a publisher page is drawn from.
    _by_name = {n: i for i, n in db.execute("SELECT id, name FROM publisher")}
    for line in _imp_mod.load(ROOT / "data" / "names" / "imprints.yaml"):
        for house in (line.get("publishers") or []):
            hid = _by_name.get(_phid_mod.publisher_of(house))
            if hid and line.get("name"):
                put("INSERT OR IGNORE INTO imprint (publisher, name) VALUES (?,?)",
                    (hid, line["name"]), f"imprint {line['name']}")
    # THE LINE'S OWN SLUG AND THE UMBRELLA IT SITS INSIDE, FROM THE REGISTRY THAT STATES THEM. This
    # was read out of `feed/names.json`'s imprints map, which is the registry rendered for a browser,
    # and `publishers.json` needs it: a line with no slug has no page to point at. §6 moved the map
    # behind `renderings`, which a compiler cannot call until it has emitted the very file this
    # feeds, so reading the derived form here would have made one file's emission wait on its own.
    for line in _imp_mod.load(ROOT / "data" / "names" / "imprints.yaml"):
        for house in (line.get("publishers") or []):
            db.execute("UPDATE imprint SET slug = ?, parent_name = ?,"
                       " parent = (SELECT p.id FROM imprint p WHERE"
                       " p.name = ? AND p.publisher = imprint.publisher AND p.id <> imprint.id)"
                       " WHERE name = ? AND publisher ="
                       " (SELECT id FROM publisher WHERE name = ?)",
                       (line.get("id"), line.get("parent"), line.get("parent"), line.get("name"),
                        _phid_mod.publisher_of(house)))
            db.execute("UPDATE imprint SET adult = 1 WHERE name = ? AND publisher ="
                       " (SELECT id FROM publisher WHERE name = ?)",
                       (line.get("name"), _phid_mod.publisher_of(house))
                       ) if line.get("adult") else None
    counts["publisher"] = db.execute("SELECT count(*) FROM publisher").fetchone()[0]
    counts["imprint"] = db.execute("SELECT count(*) FROM imprint").fetchone()[0]

    # THE EDGE, WHICH IS WHERE THE FOREIGN KEYS EARN THEIR PLACE. A credit identifier naming nobody
    # is refused here rather than counted later.
    # ── the identity registry, §5d ───────────────────────────────────────────────────────────────
    #
    # THE STORE HAS NEVER READ THIS AND THE ENTITY WAS ALWAYS THERE. `data/identity/` holds the
    # spellings that reach a person, the addresses that reach a work, and the rulings behind both.
    # THE MERGE MAP FIRST, because an anchor may still name a retired identifier and one address
    # reaching two works would refuse. `merged` is a map from the retired id to its survivor.
    # FROM THE REGISTRY, NOT FROM THE FILE THIS STORE EMITS. The credit half read
    # `data/build/credits.json`, which §6 moved to `emit.credits`, so on the run after that file was
    # deleted the merge map came back EMPTY and `pages.forwarders` removed the stub at every retired
    # credit address. An address published once has to keep resolving, which is the whole reason a
    # retired identifier is kept at all.
    #
    # THE SAME FAULT AS THE CREDIT TABLES, ONE TABLE DEEPER, and the same lesson: byte equality
    # proved the emit while the old file was still on disk, and only deleting it showed what the
    # store could not rebuild. `merged_into` in `data/identity/credits.yaml` is where a credit merge
    # is recorded, exactly as it is for a work.
    survivor, retired = {}, []
    # FROM THE REGISTRY, NOT FROM THE FILE THIS STORE EMITS, which is the fourth time that fault has
    # been found and the first time a DEPLOY found it. The work half read `data/build/series.json`,
    # which §6 now writes out of `superseded` itself, so a clean checkout built an empty merge map,
    # emitted an empty one, and `pages.forwarders` deleted the stub at all 153 retired work
    # addresses. `data/identity/works.yaml` states the merge, exactly as the credit half does.
    for f, col in (("works", "work"), ("credits", "credit"), ("publishers", "publisher")):
        for e in (_yaml(f).get(f) or []):
            if e.get("merged_into") and e.get("id"):
                survivor[str(e["id"])] = str(e["merged_into"])
                retired.append((str(e["id"]), col))

    def _live(i):
        """An identifier with every retirement followed. `merged` records one hop at a time."""
        for _ in range(8):
            if i not in survivor:
                return i
            i = survivor[i]
        return i

    # THE CHAIN IS FOLLOWED BEFORE THE ROW IS WRITTEN. `w01234` names `w01220` as its survivor and
    # `w01220` was retired in its turn, so storing the map as written puts a foreign key against an
    # identifier the corpus no longer holds. What a retired id resolves to is the LIVE one.
    for gone, col in retired:
        put(f"INSERT INTO superseded (id, {col}) VALUES (?,?)", (gone, _live(gone)),
            f"superseded {gone}")
    counts["superseded"] = db.execute("SELECT count(*) FROM superseded").fetchone()[0]

    held_work = {r[0] for r in db.execute("SELECT id FROM work")}
    # A RETIRED ENTRY AND ITS SURVIVOR LIST THE SAME ADDRESS, which is what a merge means: 165
    # anchors appear under both. Resolving each to the live identifier makes them one row, and the
    # loader says so rather than letting the primary key absorb it. Measured after resolving, NO
    # address reaches two different live works, which is what makes the key worth having.
    anchored = {}
    for w in (_yaml("works").get("works") or []):
        wid = _live(w.get("id"))
        if wid not in held_work:
            continue                          # a registry entry for a work the corpus dropped
        for a_ in (w.get("anchors") or []):
            scheme, _, address = str(a_).partition(":")
            if not address or anchored.get((scheme, address)) == wid:
                continue
            anchored[(scheme, address)] = wid
            put("INSERT INTO work_anchor (scheme, address, work) VALUES (?,?,?)",
                (scheme, address, wid), f"anchor {a_}")
    counts["work_anchor"] = db.execute("SELECT count(*) FROM work_anchor").fetchone()[0]

    held_credit, spelt = {r[0] for r in db.execute("SELECT id FROM credit")}, {}
    # A CREDIT ANSWERS FOR THE FOLD OF ITS OWN TITLE AS WELL AS FOR ITS ANCHORS, which is
    # `credit_spellings`'s second clause and applies to a live entry only. §5h put the RAW title in
    # instead, and 130 credits are titled with a full-width space the fold removes, `二三　夏一`
    # against `二三夏一`, so the store held 130 spellings the registry does not answer for and §6's
    # emitter wrote them into `credits.json`. Comparing bytes against the file build.py produces is
    # what caught it, which is the whole reason §6 keeps both while a domain moves.
    import credit_identity as _cid
    for c in (_yaml("credits").get("credits") or []):
        cid = _live(c.get("id"))
        if cid not in held_credit:
            continue
        for a_ in (c.get("anchors") or []):
            _scheme, _, spelling = str(a_).partition(":")
            if not spelling or spelt.get(spelling) == cid:
                continue
            spelt[spelling] = cid
            put("INSERT INTO credit_spelling (spelling, credit, anchor) VALUES (?,?,1)",
                (spelling, cid), f"spelling {spelling}")
        if not c.get("merged_into"):
            k = _cid.credit_key(c.get("credit") or c.get("title") or "")
            if k and spelt.get(k) is None:
                spelt[k] = cid
                put("INSERT INTO credit_spelling (spelling, credit) VALUES (?,?)", (k, cid),
                    f"spelling {k}")
    counts["credit_spelling"] = db.execute("SELECT count(*) FROM credit_spelling").fetchone()[0]

    # THE RULINGS, which are what make a merge and a divide safe to repeat.
    def _ruling(kind, subject, r, spellings):
        spellings = [s for s in spellings if s]
        if not r.get("basis") or not spellings:
            refused.append((f"ruling {kind}", "a ruling with no reasoning is a preference"))
            return
        # THE SPELLING AS WRITTEN, AND THE IDENTIFIER IT MEANS. `credit_spelling` is what resolves
        # one to the other, so the ruling can be joined to the identity it preserves, which is the
        # one thing it is for.
        keeps = r.get("keep")
        cid = db.execute("SELECT credit FROM credit_spelling WHERE spelling = ?",
                         (keeps,)).fetchone() if keeps else None
        db.execute("INSERT INTO identity_ruling (kind, subject, about, reading, shape, basis,"
                   " keeps, keeps_credit) VALUES (?,?,?,?,?,?,?,?)",
                   (kind, subject, sorted(spellings)[0], r.get("reading"), r.get("shape"),
                    r["basis"], keeps, cid[0] if cid else None))
        rid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        for sp in spellings:
            db.execute("INSERT OR IGNORE INTO identity_ruling_surface (ruling, spelling)"
                       " VALUES (?,?)", (rid, sp))

    for r in (_yaml("credit-rulings").get("rulings") or []):
        _ruling(r.get("decision") or "keep", "credit", r, r.get("surfaces") or [])
    for r in (_yaml("credits").get("homophones") or []):
        _ruling("homophone", "credit", r,
                [x.get("credit") for x in (r.get("credits") or []) if isinstance(x, dict)])
    counts["identity_ruling"] = db.execute("SELECT count(*) FROM identity_ruling").fetchone()[0]

    # THE EDGES COME FROM THE REGISTRY TOO, for the same reason. A work the store does not hold is
    # refused by the foreign key, which is the rule `credit_page_data` applied by filtering against
    # the shipped rows and is why that filter could go.
    held_work_ids = {x[0] for x in db.execute("SELECT id FROM work")}
    for r in (_yaml("credit-works").get("credits") or []):
        cid = r.get("id")
        for w in (r.get("works") or []):
            wid = w.get("id") if isinstance(w, dict) else w
            # A WORK THE STORE DOES NOT HOLD IS NOT ON A PERSON'S PAGE. The registry keeps an edge
            # to a work withheld on content grounds and to one merged away, and `credit_page_data`
            # filtered both against the shipped rows.
            #
            # THE RETIRED ID IS NOT FOLLOWED, AND THAT IS A FAITHFUL COPY OF A FAULT. Resolving it
            # through `superseded` adds 5 edges, because a credit named on a work that was later
            # merged keeps pointing at the retired identifier and the filter then drops it. So a
            # work merge silently takes credit edges with it. §6 emits what the compiler produced
            # and proves it byte for byte; changing what a page shows is a separate change with its
            # own reason, and docs/GAPS.md carries the 5.
            if wid not in held_work_ids:
                continue
            # `roles`, PLURAL, AND THE COLUMN WAS EMPTY BECAUSE THIS ASKED FOR `role`. §5b read the
            # 4,165 NULLs and concluded the roles were not on this route, on the strength of one
            # letter. 568 edges state one or more, and an edge naming two jobs is two rows, which
            # is what `(work, credit, coalesce(role, ''))` was keyed for all along.
            roles = w.get("roles") if isinstance(w, dict) else None
            for role in (roles or [None]):
                if cid and wid:
                    put("INSERT OR IGNORE INTO work_credit (work, credit, role) VALUES (?,?,?)",
                        (wid, cid, role), f"edge {cid}->{wid}")
    counts["work_credit"] = db.execute("SELECT count(*) FROM work_credit").fetchone()[0]


    # WHICH WORKS ARE NOT PUBLISHED, from the ruling that refuses them. A withheld work leaves six
    # separate surfaces and each was found only by looking after the previous fix appeared to have
    # worked; the name map is one of them, so the register has to reach the store that emits it.
    from facts import origin as _origin_mod
    for _ref in _origin_mod.refusals(_origin_mod.load()):
        if _ref.get("title"):
            put("INSERT OR IGNORE INTO withheld (title, reason) VALUES (?,?)",
                (_ref["title"], _ref.get("reason") or _ref.get("why")), f"withheld {_ref['title']}")
    # AND WHAT A SOURCE FLAGGED ON CONTENT GROUNDS, acted on or not. `run.json` carried this and
    # the check that reads it exists because a register nothing consumes reads as a control that is
    # working: five works were flagged `not published` for the life of the project and all five
    # were live.
    # THE PLATFORMS THE PROJECT HAS WRITTEN DOWN, READER-PLAN item 4. `facts/platform` reads the
    # register and this stores it, so the check comparing what a reader is shown against what is
    # recorded can be a query rather than a script.
    from facts import platform as _plat_mod
    for _p in _plat_mod.registered():
        put("INSERT OR IGNORE INTO platform_register (name, slug, publisher, host, en)"
            " VALUES (?,?,?,?,?)",
            (_p["name"], _p.get("id"), _p.get("publisher"), _p.get("host"), _p.get("en")),
            f"platform register {_p['name']}")

    from facts import content as _content_mod
    # AND THE MARKETING FLAGS, which are the other half of the register the check compares against.
    # Read off the titles the store already holds rather than off the rows the compiler was handed,
    # so a rebuild and a delta see the same population.
    _titles = [r[0] for r in db.execute("SELECT title FROM work")]
    for _flag in list(_content_mod.flags().values()) + list(
            _content_mod.marketing(_titles).values()):
        # `published` IS WHAT HAPPENED and the loader cannot know it: a work reaches the site
        # through the emitters, and this runs before any of them. It is recorded as the negation
        # of the decision, which is what the register asserts, and `content flags are accounted
        # for` checks the bytes rather than believing this column.
        put("INSERT OR IGNORE INTO content_flag (title, source, reason, withhold, published)"
            " VALUES (?,?,?,?,?)",
            (_flag["title"], _flag.get("source"), _flag.get("reason"),
             int(bool(_flag.get("withhold"))), 0),
            f"content flag {_flag['title']}")

    # AND EVERY RULING, REFUSED OR NOT. A ruling may name several works on one line and each of
    # them is a row; `origin.members` is the one producer of that expansion and `build.py` reports
    # the same list through it, so a loop reading `works` here would be a second one to keep in
    # step. `review` rulings are here too, which is why this is not `withheld`.
    for _rul in (_origin_mod.load() or {}).get("rulings") or []:
        for _mem in _origin_mod.members(_rul):
            if not _mem.get("work"):
                continue
            put("INSERT OR IGNORE INTO scope_ruling (work, title, disposition, country,"
                " country_basis, medium, medium_basis, source) VALUES (?,?,?,?,?,?,?,?)",
                (_mem["work"], _mem.get("title"), _rul.get("disposition"), _rul.get("country"),
                 _rul.get("country_basis"), _rul.get("medium"), _rul.get("medium_basis"),
                 (_rul.get("evidence") or [{}])[0].get("source") if _rul.get("evidence")
                 else _rul.get("source")),
                f"scope ruling {_mem['work']}")
    counts["withheld"] = db.execute("SELECT count(*) FROM withheld").fetchone()[0]

    # ── the names, and what is claimed about each ────────────────────────────────────────────────
    #
    # ONE PRODUCER OF A `surface` ROW (§3), and it is `surface_id` below. Two loaders need those
    # rows, the name store's claims and the build's renderings, and a second insert site is how the
    # two would come to disagree about a fold.
    # WHAT A NAME NAMES, ASKED OF THE REGISTRY AND NOT OF A TITLE MATCH. §5d. A credit is reached by
    # every spelling that resolves to it, which is 2,473 spellings rather than the one
    # `credits.json` happens to print. A work is reached by the FOLD of its title, because that is
    # what the site joins on and the registry's own anchors are addresses rather than names; the
    # fold is what §5c's 55 nameless works were missing, since `work.title` holds `一畳間まんきつ
    # 暮らし！` and NFKC turns the exclamation mark into an ASCII one.
    #
    # A FOLD MAY REACH TWO WORKS and both are recorded. `百合漫画短編集` names w01990 and w02284.
    surface_id = _surfacer(db)
    seen_claims = {}

    # ONE ROW IS ONE CLAIM. The store holds a reading and its provenance as nine `reading_*` keys on
    # a record; here each claim is a row, so a second opinion is a second ROW and a conflict is data.
    # That is what makes "where do two sources disagree about one name" a query at all.
    #
    # READ FROM `data/names/*.yaml` AND NOT FROM THE BUILD, because the note, the address and the
    # date it was reviewed are in the source and the shipped form compresses them. STORE-PLAN §6 is
    # where the direction reverses; until then this is the fuller of the two.
    #
    # KEYED ON `facts/namekey.KINDS`, so the store's populations and the name store's cannot drift
    # apart. The values are what each population is a name OF, and the surface kinds it files under.
    subject_of = dict(zip(_namekey.KINDS, ("credit", "publisher", "work")))
    surface_kind = dict(zip(_namekey.KINDS, ("author", "publisher", "title")))
    for f, subject_kind in subject_of.items():
        path = ROOT / "data" / "names" / f"{f}.yaml"
        if not path.exists():
            continue
        rows = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("names", {})
        for name, r in rows.items():
            if not isinstance(r, dict):
                continue
            # A NAME THE CORPUS IDENTIFIES NOTHING FOR STILL HOLDS ITS CLAIMS, which is the fault
            # this section was written for: the loader used to skip it, silently, so 890 readings
            # and every English rendering in the corpus were absent from a store reporting no
            # refusals. A surface is what a claim hangs off, and a surface needs no identifier.
            sid = surface_id(surface_kind[f], name, subject_kind)
            if sid is None:
                continue
            # THE JUDGEMENT BELONGS TO THE RECORD THAT WAS JUDGED, §5h. These were columns on the
            # FOLD and two spellings folding together overwrote each other, losing 14 rulings.
            put("INSERT INTO name_record (kind, spelling, surface, verified, uncertain, ordinary,"
                " transliterates, entity, basis, translation_refused)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (surface_kind[f], name, sid,
                 None if r.get("verified") is None else int(bool(r["verified"])),
                 int(bool(r.get("reading_uncertain"))), int(bool(r.get("reading_ordinary"))),
                 r.get("transliterates"), r.get("entity"), r.get("basis"),
                 r.get("translation_refused")),
                f"name_record {f} {name}")
            # AND THE SPANS IT SHOWS OVER ITS OWN SPELLING, where that is not the fold. `仲谷 鳰`
            # folds onto `仲谷鳰` and its furigana part the name where the fold's read it as one
            # word, so a row showing this record has to show these. `names/ruby` owns the rule and
            # `build.py` asks the same function.
            # EVERY RECORD, NOT ONLY THE ONES SPELLED DIFFERENTLY FROM THEIR FOLD. Storing only
            # those left the rest falling back to the FOLD's spans, which are the winning record's,
            # so a record that spells the name closed up showed the spaced record's parting.
            # AND THE READING SPELT IN LATIN, which is a function of THIS record's reading:
            # 春結千晶 is held twice, once with an analyser's ハル ケツ チアキ and once with
            # ハルユウチアキ off the shop that sells the artist's books.
            if r.get("reading"):
                for _style, _value in _romanmod.styles(
                        r["reading"], _romanmod.PERSON if surface_kind[f] == "author"
                        else _romanmod.TITLE).items():
                    if _value and _style in ("plain", "macron", "double"):
                        put("INSERT OR IGNORE INTO romanisation (surface, record, style, value)"
                            " VALUES (?,(SELECT id FROM name_record WHERE kind = ? AND"
                            " spelling = ?),?,?)",
                            (sid, surface_kind[f], name, _style, _value),
                            f"romanisation {name} {_style}")
            for _i, _span in enumerate(_rubymod.spans(
                    name, r, surface_kind[f] == "author" and not r.get("entity")) or ()):
                _text, _read = (list(_span) + [None, None])[:2]
                if _text:
                    put("INSERT OR IGNORE INTO ruby (surface, record, seq, text, reading)"
                        " VALUES (?,(SELECT id FROM name_record WHERE kind = ? AND"
                        " spelling = ?),?,?,?)",
                        (sid, surface_kind[f], name, _i, _text, _read), f"ruby {name} {_i}")
            # AND THE CLAIMS BELOW BELONG TO IT, §6. Hung off the fold alone they arrived in one
            # heap wherever two spellings fold together, and the entry a reader is shown has to
            # come from one record or it contradicts itself.
            rec_id = db.execute("SELECT id FROM name_record WHERE kind = ? AND spelling = ?",
                                (surface_kind[f], name)).fetchone()
            rec_id = rec_id[0] if rec_id else None
            for predicate, cite in (("reading", "reading"), ("english", "en")):
                # EVERY FORM WE HOLD AND NOT ONLY THE LIVE ONE. A displaced claim is kept rather
                # than discarded (§1), and `en_conflicts` is where the store keeps it; as rows they
                # are what the site ships as `en_forms` and no second shape is needed for them.
                #
                # A DISPLACED CLAIM BRINGS ITS OWN PROVENANCE AND NOTHING ELSE, which §5 got wrong
                # by building each conflict from the live record. It carries `basis`, `source` and
                # `value` and no more, so 333 English and 598 reading conflicts were admitted
                # holding the LIVE claim's page, kind, dates and note. That is one entry with two
                # claims and one citation between them, which is the exact fault `provenance` was
                # written for, reintroduced one layer down. §5a found it by asking whether each
                # claim's evidence is of a kind its basis admits.
                #
                # THE RECORD'S OWN NOTE TRAVELS WITH IT AND NOTHING ELSE DOES. A conflicts entry
                # has no room for one, and `researched` demands the reasoning, so 4 displaced
                # readings refused. The reasoning does exist: it is in the record's `note`, where
                # the reviewer wrote why the earlier answer was replaced. Carrying that is not the
                # borrowing this comment warns about, because a note explains the record while a
                # url, a kind and a date each assert a specific document for a specific claim.
                held = [r] + [{cite: c.get("value"), _prov.BASIS_FIELD[cite]: c.get("basis"),
                               f"{cite}_source": c.get("source"),
                               "note": r.get("note") or r.get(f"{cite}_note")}
                              for c in (r.get(f"{cite}_conflicts") or []) if isinstance(c, dict)]
                for i, claim in enumerate(held):
                    value = claim.get(cite)
                    basis = (_prov.basis_of(claim, cite)
                             or (_reading.DEFAULT_BASIS if cite == "reading" else None))
                    if not value or not basis:
                        continue
                    cited = _prov.cite(claim, cite) or {}
                    # ONE CLAIM SAID TWICE IS ONE CLAIM, and §5b's key is what made that sayable.
                    # 112 author spellings fold to another's key, `BUNBUN` and `ＢＵＮＢＵＮ` among
                    # them, so two records reach one surface and repeat each other; a conflicts
                    # list also carries values the live claim already holds. Skipped here rather
                    # than left to the index, because a loader that relies on a constraint to
                    # absorb what it knowingly emits is the `INSERT OR IGNORE` of §2 again.
                    # ONE CLAIM SAID TWICE IS ONE CLAIM AND TWO RECORDS SAYING IT ARE TWO EDGES.
                    # Skipping the second outright filed the claim against whichever record was
                    # read first, so the record the file renders from could be missing the reading
                    # it states.
                    ident = (sid, predicate, value, basis, claim.get(f"{cite}_source") or "",
                             cited.get("url") or claim.get(f"{cite}_url") or "",
                             claim.get(f"{cite}_at") or "", claim.get(f"{cite}_reviewed") or "")
                    if ident in seen_claims:
                        put("INSERT OR IGNORE INTO claim_record (claim, record) VALUES (?,?)",
                            (seen_claims[ident], rec_id), f"claim edge {f} {name}")
                        continue
                    ok = put(
                        "INSERT INTO claim (surface, kind, predicate, value, basis, source,"
                        " source_kind, retrieved, reviewed, url, isbn, note, displaced)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (sid, surface_kind[f], predicate, value, basis,
                         claim.get(f"{cite}_source"),
                         _kind_of(claim, cite), claim.get(f"{cite}_at"),
                         claim.get(f"{cite}_reviewed"),
                         cited.get("url") or claim.get(f"{cite}_url"),
                         cited.get("isbn"), claim.get(f"{cite}_note") or claim.get("note"),
                         # WHICH ANSWER THE RECORD STANDS BEHIND. Index 0 is the live claim and
                         # every later one came out of a conflicts list, which is a claim somebody
                         # moved aside. Without this the store held two readings and a `verified`
                         # flag with no way to say which one a person ruled on, 638 times.
                         int(i > 0)),
                        f"claim {predicate} {f} {name}" + (f" [{i}]" if i else ""))
                    # ONLY WHERE THE CLAIM WENT IN. `put` swallows a refusal and returns False,
                    # and `last_insert_rowid()` does not know that: it answers with the PREVIOUS
                    # successful insert's id, so a refused claim filed its edge against whichever
                    # claim happened to go in before it. Every record after that point in the load
                    # carries somebody else's reading, which is how 1,752 authors in a published
                    # store came to be spelled from another person's name.
                    #
                    # UNDER `--unattended` THE RUN CONTINUES PAST A REFUSAL, §1a, which is what
                    # makes this a corruption rather than a crash: the quarantine keeps the night
                    # alive and this quietly rewired the names while it did.
                    if not ok:
                        continue
                    seen_claims[ident] = db.execute(
                        "SELECT last_insert_rowid()").fetchone()[0]
                    put("INSERT OR IGNORE INTO claim_record (claim, record) VALUES (?,?)",
                        (seen_claims[ident], rec_id), f"claim edge {f} {name}")
            # WHERE A NAME PARTS, AND ONLY WHERE SOMETHING SAYS WHAT THAT RESTS ON. 680 records
            # hold a boundary and 660 of them state their source as PROSE: `the kana in its own
            # surface`, `the National Diet Library's author heading on record R100000002-…`. Prose
            # is not a basis and inventing one for it here would put a ruling in the loader.
            # docs/GAPS.md carries the 660.
            #
            # DONE IN §5c FOR EVERY NAME THAT STATES ONE, and the earlier reading of this was
            # wrong. §5 argued `undivided` needed no column because the store holds the reading and
            # whether the credit is a person; the flag turns on whether a parting point is STATED,
            # and 889 names state one: 680 in `reading_boundary` and 276 in `reading_family` and
            # `reading_given`, which together are the divided form of the name. The store held 20.
            #
            # THE BASIS IS THE RECORD'S OWN WHERE THE BOUNDARY DOES NOT NAME ONE. `facts/division`
            # says a `cited` basis gave the division with the reading, which is what a catalogue
            # printing `美鈴, ちょこ` does, so the reading's basis is the division's basis unless
            # the record says otherwise. The 660 boundaries stating their source in prose keep it
            # as the note, and docs/GAPS.md carries the fact that prose is not a basis.
            divided = (" ".join(x for x in (r.get("reading_family"), r.get("reading_given")) if x)
                       if r.get("reading_family") or r.get("reading_given") else None)
            if r.get("reading_boundary") or divided:
                basis = (r.get("reading_boundary_basis") or r.get("reading_basis")
                         or _reading.DEFAULT_BASIS)
                # THROUGH THE SAME DEDUPE AS THE REST, since two spellings folding to one surface
                # state one division between them.
                ident = (sid, "division", divided or r.get("reading") or "", basis, "", "", "", "")
                if ident in seen_claims:
                    put("INSERT OR IGNORE INTO claim_record (claim, record) VALUES (?,?)",
                        (seen_claims[ident], rec_id), f"claim edge division {name}")
                    continue
                # A CITED BASIS GAVE THE DIVISION WITH THE READING, which is what
                # `facts/division.cites_its_source` means and what a catalogue printing `美鈴, ちょこ`
                # does. So the division carries the reading's own citation. §5c wrote none at all,
                # and 219 `stated` divisions then sat in the hole §5f closed in the CHECK above:
                # admitted for saying nothing, refused for naming a kind.
                from facts import division as _division
                lends = _division.cites_its_source(basis)
                cited = (_prov.cite(r) or {}) if lends else {}
                # THE ADDRESS THE RECORD HOLDS, NOT THE ONE A READER MAY BE SHOWN. `cite` withholds
                # the NDL OpenSearch route because that host's robots.txt disallows it, and 9
                # divisions rest on a reading held that way. The address exists and is recorded;
                # whether to put it in front of a reader is §6's question about a page, and a store
                # that dropped it would be answering a display question with a missing fact.
                if not put(
                    "INSERT INTO claim (surface, kind, predicate, value, basis, source,"
                    " source_kind, url, isbn, note, basis_stated)"
                    " VALUES (?,?,'division',?,?,?,?,?,?,?,?)",
                    (sid, surface_kind[f], divided or r.get("reading") or "", basis,
                     r.get("reading_source") if lends else None,
                     _kind_of(r) if lends else None,
                     (cited.get("url") or r.get("reading_url")) if lends else None,
                     cited.get("isbn"),
                     r.get("reading_boundary") or r.get("reading_note"),
                     int(bool(r.get("reading_boundary_basis")))),
                    f"claim division {f} {name}"):
                    # THE SAME GUARD AS THE CLAIM ABOVE, and for the same reason: a refused insert
                    # leaves `last_insert_rowid()` answering with the previous one's id, and the
                    # edge is then filed against another record's claim.
                    continue
                seen_claims[ident] = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                put("INSERT OR IGNORE INTO claim_record (claim, record) VALUES (?,?)",
                    (seen_claims[ident], rec_id), f"claim edge division {name}")
    counts["surface"] = db.execute("SELECT count(*) FROM surface").fetchone()[0]
    counts["name_record"] = db.execute("SELECT count(*) FROM name_record").fetchone()[0]
    counts["claim"] = db.execute("SELECT count(*) FROM claim").fetchone()[0]

    # ── the renderings, which are what a reader is actually shown ────────────────────────────────
    #
    # `feed/names.json` IS THE DERIVED FORM AND `renderings` IS WHERE IT LANDS. The romanisations,
    # the ruby spans, the credit divisions and the two romanisation maps are all functions of a
    # reading and of the rules `adapters/names` holds; none of that judgement moves, and
    # STORE-PLAN §3 is where the reason is written out. What changes is that the answer is a row.
    #
    # A COMPILER HANDS THE MAP IN LATER AND SAYS SO BY LEAVING IT OUT. The map is built out of the
    # credit pages and the publisher pages, which this store emits, so `build.py` cannot have it
    # yet when it calls this and calls `renderings` itself once it does. Reading the file here for
    # a compiler that is about to rewrite it would load the LAST run's renderings, which is the
    # domain-is-its-own-input fault §6 has already been bitten by three times.
    if source is None or "names" in source:
        names = BUILD / "feed" / "names.json"
        doc = ((source or {}).get("names") if source else None) or (
            json.loads(names.read_text(encoding="utf-8")) if names.exists() else {})
        renderings(db, doc, put, surface_id, counts)

    # WHERE A BYLINE WAS SEEN, §5e. 3,399 credit-line surfaces existed and nothing connected one to
    # the work it appeared on. One line appears on many works, so it is an edge and not a column.
    for _k, r in _rows("series", "series", source):
        wid, field = r.get("id"), r.get("author")
        if wid and field:
            sid = surface_id("credit-line", field)
            if sid is not None:
                put("INSERT OR IGNORE INTO work_byline (work, surface, kind, field)"
                    " VALUES (?,?,'credit-line',?)", (wid, sid, field), f"byline {wid}")
        for i, part in enumerate(r.get("credits") or []):
            if part.get("name"):
                put("INSERT OR IGNORE INTO work_byline_part (work, seq, name, role, basis)"
                    " VALUES (?,?,?,?,?)",
                    (wid, i, part["name"], part.get("role"), part.get("basis")),
                    f"byline part {wid} {i}")
    counts["work_byline"] = db.execute("SELECT count(*) FROM work_byline").fetchone()[0]
    counts["work_byline_part"] = db.execute(
        "SELECT count(*) FROM work_byline_part").fetchone()[0]
    # ── the two tables the schema declared and nothing ever wrote ───────────────────────────────
    #
    # WHY THEY WERE EMPTY, established 2026-08-13 rather than assumed. `schema.sql` and this loader
    # arrived in one commit, the loader was written for the identity spine, and nothing came back
    # for the rest. So `edition` and `work_publisher` carried columns, constraints and an index and
    # held no rows, which is a schema asserting something nothing had ever tested against data.
    # STORE-PLAN §2.


    # ── the print rows a run is made of, §6 ─────────────────────────────────────────────────────
    #
    # `publishers.json` AND THE PRINT HALF OF `series.json` BOTH WAIT ON THESE. A house's row count
    # and a line's are counts of these rows, and `facts/imprint.census` measures the years a
    # spelling covers from them, so neither file can be emitted while they are only in the JSON.
    pub_id = {n: i for i, n in db.execute("SELECT id, name FROM publisher")}
    print_block = {}
    for _k, r in _rows("series", "series", source):
        wid = r.get("id")
        for blk in (r.get("print") or []):
            rec = blk.get("work_id")
            if rec:
                print_block[rec] = blk
            if not wid or not rec:
                continue
            if not put("INSERT INTO print_row (work, record, publisher, publisher_raw,"
                       " imprint_raw, distributor, label, first, last, volumes, shop_url,"
                       " delivered_from, periodical) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (wid, rec, pub_id.get(blk.get("publisher")), blk.get("publisher"),
                        blk.get("imprint"), blk.get("distributor"), blk.get("label"),
                        blk.get("first"), blk.get("last"), blk.get("volumes"),
                        blk.get("shop_url"), blk.get("delivered_from"),
                        int(bool(blk.get("periodical")))), f"print_row {rec}"):
                continue
            pid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            for other in (blk.get("work_ids") or [rec]):
                put("INSERT OR IGNORE INTO print_row_record (print_row, record) VALUES (?,?)",
                    (pid, other), f"print record {other}")
    counts["print_row"] = db.execute("SELECT count(*) FROM print_row").fetchone()[0]

    # THE SEATS ON EACH ROW, WITH THE JUDGEMENT ALREADY MADE. `publisher_identity.anchor` decides
    # which house a spelling names and `facts/imprint.resolve` which line, and both run HERE so the
    # emitter groups rows without re-deciding anything. That is §3's rule for the whole plan: the
    # judgement stays in the compiler and what moves is where the answer is written.
    import publisher_identity as _phid
    from facts import imprint as _imp
    from facts import printblock as _pblk
    _lines = _imp.load(ROOT / "data" / "names" / "imprints.yaml")
    _lidx = _imp.index(_lines)
    _house_of = {}
    for _e in (_yaml("publishers").get("publishers") or []):
        if _e.get("merged_into") or not _e.get("id"):
            continue
        for _a in (_e.get("anchors") or []):
            _house_of.setdefault(str(_a), str(_e["id"]))
    _imprint_id = {}
    for _i, _pub, _nm in db.execute("SELECT id, publisher, name FROM imprint"):
        _imprint_id[(_pub, _nm)] = _i
    # `ORDER BY id` BECAUSE AN UNORDERED SELECT IS NOT INSERTION ORDER. `SELECT id, record` is
    # covered entirely by the unique index on `record`, so SQLite scans that instead of the table
    # and hands the rows back in record order. The parties then came out in a sequence that had
    # nothing to do with the compiler's, and every works list in `publishers.json` was reordered.
    for pid, rec in db.execute("SELECT id, record FROM print_row ORDER BY id").fetchall():
        blk = print_block.get(rec)
        if blk is None:
            continue
        for _seq, party in enumerate(_pblk.parties(blk)):
            for seat in _phid.SEATS:
                raw = str(party.get(seat) or "").strip()
                if not raw:
                    continue
                hid = _house_of.get(_phid.anchor(raw) or "")
                imp_raw = str(party.get("imprint") or "").strip()
                line = _imp.resolve(_phid.publisher_of(party.get("publisher") or ""),
                                    imp_raw, _lidx) if imp_raw else None
                put("INSERT INTO print_party (print_row, seq, seat, publisher_raw, publisher,"
                    " imprint_raw, imprint, first, last) VALUES (?,?,?,?,?,?,?,?,?)",
                    (pid, _seq, seat, raw, hid, imp_raw or None,
                     _imprint_id.get((hid, (line or {}).get("name"))) if line else None,
                     party.get("first"), party.get("last")),
                    f"print party {rec} {seat}")
    counts["print_party"] = db.execute("SELECT count(*) FROM print_party").fetchone()[0]

    # WORK TO PUBLISHER, OFF THE PRINT PARTIES. §2 read it from `publishers.json`'s own `works`
    # list, on the reasoning that going by way of the print blocks would rebuild a join the
    # publisher pass had already made. §6 emits that file, so reading it here would make it its own
    # input; and the reasoning no longer holds, because `print_party` already carries the join the
    # publisher pass made. The edge is the same edge, derived from the rows rather than from a file.
    for wid, pid, seat, imp in db.execute(
            "SELECT r.work, p.publisher, p.seat, max(p.imprint) FROM print_party p"
            " JOIN print_row r ON r.id = p.print_row"
            " WHERE p.publisher IS NOT NULL GROUP BY r.work, p.publisher, p.seat"
            " ORDER BY r.work, p.publisher, p.seat"):
        put("INSERT OR IGNORE INTO work_publisher (work, publisher, seat, imprint)"
            " VALUES (?,?,?,?)", (wid, pid, seat, imp), f"work_publisher {wid}->{pid}")
    counts["work_publisher"] = db.execute("SELECT count(*) FROM work_publisher").fetchone()[0]

    # ── whether a work is running, and the byline it prints, §5e ────────────────────────────────
    for _k, r in _rows("series", "series", source):
        wid = r.get("id")
        if not wid or r.get("state") is None:
            continue
        put("INSERT INTO work_state (work, state, basis, basis_ja, completed_basis,"
            " completed_basis_ja) VALUES (?,?,?,?,?,?)",
            (wid, r["state"], r.get("state_basis"), r.get("state_basis_ja"),
             r.get("completed_basis"), r.get("completed_basis_ja")), f"work_state {wid}")
        # THE COMPETING CLAIMS, which are the disagreement rule applied to something other than a
        # name: 271 works hold a source, a term, a date and a page each.
        for cl in (r.get("state_claims") or []):
            if isinstance(cl, dict) and cl.get("source"):
                put("INSERT OR IGNORE INTO state_claim (work, source, says, term, url, read)"
                    " VALUES (?,?,?,?,?,?)",
                    (wid, cl["source"], cl.get("says"), cl.get("term"), cl.get("url"),
                     cl.get("read")), f"state_claim {wid}")
    counts["work_state"] = db.execute("SELECT count(*) FROM work_state").fetchone()[0]

    # WHY A WORK IS FILED AS YURI, AND WHAT ELSE WAS READ FOR IT. Two lists kept apart on purpose:
    # a volume count says nothing about whether a work is yuri, and running them together would make
    # the classification look better supported than it is.
    for _k, r in _rows("series", "series", source):
        wid = r.get("id")
        if wid not in held_work:
            continue
        for ev in (r.get("evidence") or []):
            if ev.get("kind") and ev.get("source") and ev.get("term"):
                put("INSERT INTO evidence (work, kind, source, term, url, page, read)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (wid, ev["kind"], ev["source"], ev["term"], ev.get("url"), ev.get("page"),
                     ev.get("read")), f"evidence {wid} {ev['kind']}")
        for i, ph in enumerate(r.get("sourced_from") or []):
            if ph.get("source") and ph.get("holds"):
                put("INSERT INTO provenance (work, seq, source, holds, url, read)"
                    " VALUES (?,?,?,?,?,?)",
                    (wid, i, ph["source"], ph["holds"], ph.get("url"), ph.get("read")),
                    f"provenance {wid} {i}")
    counts["evidence"] = db.execute("SELECT count(*) FROM evidence").fetchone()[0]
    counts["provenance"] = db.execute("SELECT count(*) FROM provenance").fetchone()[0]
    counts["state_claim"] = db.execute("SELECT count(*) FROM state_claim").fetchone()[0]

    # EDITIONS. `works.json` is keyed by the RECORD identifier a catalogue or a shop issued, and
    # `edition.work` is a `w` identifier, so the print blocks supply the bridge: `work_ids` names
    # every record a series row's run is made of.
    of_record, shop_of, held_isbn, held_event = {}, {}, {}, set()
    seen_grounds = set()
    for _k, r in _rows("series", "series", source):
        wid = r.get("id")
        for blk in (r.get("print") or []):
            for rec in (blk.get("work_ids") or []):
                of_record.setdefault(rec, wid)
                if blk.get("shop_url"):
                    shop_of.setdefault(rec, blk["shop_url"])
    for _k, w in _rows("works", "works", source):
        wid = of_record.get(w.get("work_id"))
        if not wid:
            continue                          # a record no series row's run names
        # THE PAGE THE RECORD ITSELF CAME FROM, which is where most volume dates are checkable.
        # A volume states `madb_id` only where the bulk dataset named one per book; a volume dated
        # by the catalogue that issued the whole record cites that record. 209 volumes were being
        # refused as uncitable while their work carried
        # `records: [{source: madb, url: .../id/C418820}]`, and the work_id IS that page's id.
        of_work = next((r.get("url") for r in (w.get("records") or []) if r.get("url")), None)
        for seq, v in enumerate(w.get("volumes") or []):
            # BOTH EVENTS, NOT WHICHEVER ONE FITS. A volume states a printing date, a delivery
            # date, or both, and 812 state two that differ. The `if/elif` that used to stand here
            # kept the printing and dropped the delivery, which looked like a choice and was the
            # shape: `edition` held one row per book with `isbn UNIQUE`, so the second event had
            # nowhere to go. §5b split the book from the event and both are held now.
            events = []
            if v.get("published"):
                events.append(("printing", v["published"]))
            # EVEN WHERE IT EQUALS THE PRINTING. §5b skipped those as redundant and they are not:
            # the record states that a shop delivered the book on a date, and that the catalogue
            # gives the same date for the printing is a fact about the two agreeing rather than a
            # reason to hold one of them. `works.json` ships both and could not be emitted without.
            if v.get("delivered"):
                events.append(("shop-delivery", v["delivered"]))
            if not events:
                events.append(("printing", None))
            # AND WHERE A READER CAN GO AND SEE IT. `CHECK (dated IS NULL OR cite IS NOT NULL)` is
            # the schema refusing a date nobody can check, which is the same rule
            # `per-book dates cite their page` states for the shop capture.
            # THE NEAREST PAGE FIRST, and each of these is somewhere a reader can go and look.
            # The shop is last for a delivery and second to last for a printing whose date the
            # shop is the only witness to: `published == delivered` with nothing else naming it
            # means the date IS the shop's, and saying so is more honest than refusing it.
            shop = shop_of.get(w.get("work_id"))
            cite = (f"madb:{v['madb_id']}" if v.get("madb_id") else
                    v.get("published_source") or v.get("isbn_source") or
                    (f"openbd:{v['isbn']}" if v.get("openbd") == "present" and v.get("isbn")
                     else None) or
                    of_work or
                    (shop if v.get("delivered") else None))
            # THE BOOK FIRST, ONCE, AND THEN WHAT HAPPENED TO IT.
            # THE RECORD'S OWN DESIGNATION AND NOTHING ELSE. §5e synthesised one from `number`
            # where the volume had no integer position, on the reasoning that a number which is a
            # word is a name. The reasoning holds and the column was the wrong home for it: §6 added
            # `number_raw`, which is that same string as the record wrote it, so
            # `coalesce(designation, number_raw)` answers "what is this volume called" without a
            # field the record states carrying something it does not say.
            designation = v.get("designation")
            # THE RECORD'S ROWS ARE ITS ROWS, AND AN ISBN IS STILL ONE BOOK. `C433149` numbers
            # volume 5 twice, `9784199509322` on one row and `978-4-19-950932-2` on the other, so
            # the two rows describe one book. §5f folded them into one `volume`, which is the right
            # reading of an ISBN and the wrong reading of a RECORD: `works.json` is the record layer
            # and lists both rows, so the store held 6,104 where the corpus states 6,108 and the
            # file could not be emitted from it without dropping four.
            #
            # SO BOTH ROWS ARE KEPT AND THE ISBN IS ATTACHED ONCE. `volume_isbn` still says one ISBN
            # is one book, the second row simply carries none, and
            # `works whose records number one volume twice` goes on counting the shape where it has
            # always been counted. A store that silently held fewer rows than the record states was
            # answering a question about books with a number about our filing.
            # THE PRIMARY FIRST AND THEN THE REST AS THE RECORD LISTS THEM, deduplicated on the
            # normalised form so a hyphenated repeat of the leader does not become a second entry.
            isbns = []
            for _raw in ([v["isbn"]] if v.get("isbn") else []) + list(v.get("editions") or []):
                _norm = _isbn(_raw)
                if _norm and _norm not in isbns:
                    isbns.append(_norm)
            vol = None
            if vol is None:
                fv = (v.get("final_volume_basis")
                      if isinstance(v.get("final_volume_basis"), dict) else {})
                if not put("INSERT INTO volume (work, record, seq, volume, designation, number_raw,"
                           " openbd, openbd_date, madb_id, isbn_source, cover_url, final_volume,"
                           " final_source, final_provenance, final_volumes, final_retrieved)"
                           " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (wid, w.get("work_id"), seq, v.get("number_n"), designation,
                            v.get("number"), v.get("openbd"), v.get("published_openbd"),
                            v.get("madb_id"), v.get("isbn_source"), v.get("cover_url"),
                            int(bool(v.get("final_volume"))), fv.get("source"),
                            fv.get("provenance"), fv.get("volumes"), fv.get("retrieved")),
                           f"volume {wid} {isbns[0] if isbns else designation or '?'}"):
                    continue
                vol = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            # EVERY ISBN THE BOOK CARRIES. 81 volumes list two, a regular printing and a special
            # edition, and the store kept one of them.
            for _n, isbn in enumerate(isbns):
                if isbn not in held_isbn:
                    held_isbn[isbn] = vol
                    put("INSERT INTO volume_isbn (seq, isbn, volume) VALUES (?,?,?)",
                        (_n, isbn, vol), f"isbn {isbn}")
            # A PLAIN INSERT, DELIBERATELY. `OR IGNORE` here swallowed 382 volumes on the first
            # run and reported `refused 0`, because SQLite treats the conflict as handled and
            # raises nothing for `put` to catch. A constraint that quietly drops a row is worse
            # than no constraint: it looks like coverage. STORE-PLAN §1a is about exactly this.
            # WHAT THE DATE RESTS ON. Stated where the volume says so, derived from the same
            # evidence the citation uses where it does not, and NULL where nothing names it: a
            # basis nobody can point at is worth less than an admitted silence.
            for kind, dated in events:
                basis = (v.get("published_basis")
                         or ("madb-tankobon" if v.get("madb_id") else None)
                         or ("openbd-registration" if v.get("openbd") == "present" and v.get("isbn")
                             else None)
                         or ("shop-delivery" if kind == "shop-delivery" else None))
                # A DELIVERY'S BASIS IS THE SHOP, whatever the printing beside it rests on.
                if kind == "shop-delivery":
                    basis = "shop-delivery"
                # ONE EVENT OF EACH KIND PER BOOK, and a record numbering one volume twice states
                # the same event twice. The rows were folded above on the ISBN that identifies the
                # book, so the second copy is the same printing and not a second one.
                if (vol, kind) in held_event:
                    continue
                held_event.add((vol, kind))
                # WHO SAYS SO, AND WHERE, SEPARATELY. The old single column held `ndl` on 906
                # rows, which names a source and locates nothing; an address locates and names at
                # once, so it fills both.
                where = cite if kind == "printing" else (shop or cite)
                who = (v.get("published_source") if kind == "printing" else None) or (
                    "madb" if str(where or "").startswith("madb:") else None) or (
                    "shop" if kind == "shop-delivery" else None) or where
                put("INSERT INTO edition (volume, dated, kind, dated_basis, basis_stated,"
                    " source, cite) VALUES (?,?,?,?,?,?,?)",
                    (vol, dated, kind, basis,
                     int(bool(v.get("published_basis")) and kind == "printing"), who,
                     where if str(where or "").startswith(("http", "madb:", "openbd:")) else None),
                    f"edition {kind} {wid} {v.get('isbn') or v.get('designation') or '?'}")
    # ── the grounds, and what a source says the run is, §5c ──────────────────────────────────────
    #
    # BOTH WERE COLUMNS ON `work` AND BOTH WERE READ FROM THE WRONG FILE. `series.json` carries
    # neither, so `admitted_by` was the word `'unstated'` on all 3,040 rows under a NOT NULL, and
    # `volume_count` was NULL on all of them, while `works.json` held structured grounds on 1,887
    # records. `explicit_content` is filled from the same place and is False on every one, which is
    # now a measured answer rather than a column default.
    from facts import credit as _credit_fact
    _spelling_to_credit = {s: c for s, c in db.execute("SELECT spelling, credit FROM credit_spelling")}
    visible = {r.get("id"): r.get("visibility") for _k, r in _rows("series", "series", source)
               if r.get("visibility")}
    for _k, w in _rows("works", "works", source):
        wid = of_record.get(w.get("work_id"))
        if not wid:
            continue
        # LOOKED AND FALSE, WHICH THE COLUMN COULD NOT SAY WHILE IT DEFAULTED TO 0.
        db.execute("UPDATE work SET explicit_content = ? WHERE id = ?",
                   (int(bool(w.get("explicit_content"))), wid))
        # HOW IT IS PRESENTED, AND WHETHER IT IS. `marketing_label` is publisher-side labelling
        # under DEFINITIONS §4 and `visibility` is the §13 register.
        mb = w.get("marketing_label_basis") if isinstance(w.get("marketing_label_basis"), dict) else {}
        # VISIBILITY IS ON THE SERIES ROW AND §5e READ IT HERE, which is `admitted_by`'s fault
        # again: `build.py` puts it there from `data/rebuttals.yaml` and `works.json` never carries
        # one, so the §13 register the comment names was empty on all 2,461 rows.
        if (w.get("marketing_label") and w.get("marketing_label") != "none") or visible.get(wid):
            put("INSERT OR IGNORE INTO work_presentation (work, label, visibility, source, url,"
                " retrieved, note) VALUES (?,?,?,?,?,?,?)",
                (wid, w.get("marketing_label") if w.get("marketing_label") != "none" else None,
                 visible.get(wid), mb.get("source"),
                 mb.get("url"), mb.get("retrieved"), mb.get("note")), f"presentation {wid}")
        for g in (w.get("admitted_by") or []):
            if not isinstance(g, dict):
                continue
            put("INSERT INTO admission (record, work, comparator, shop_url, url, page,"
                " retrieved, note) VALUES (?,?,?,?,?,?,?,?)",
                (w.get("work_id"), wid, g.get("comparator"), g.get("shop_url"), g.get("url"),
                 g.get("page"), g.get("retrieved"), g.get("note")),
                f"admission {w.get('work_id')}")
        # A COUNT A SOURCE STATES, AND 72 WORKS HAVE RECORDS THAT DISAGREE, which is why this is a
        # row with its source beside it rather than a column that would have to pick one.
        # A COMPLETED CLAIM ONLY, WHICH IS 330 RECORDS. §5c filled this from `volume_count` where no
        # claim existed, so 2,574 rows sat here and `record.volume_count` said the same thing again.
        # A source saying a run is COMPLETE at n volumes is a different statement from a catalogue
        # counting the volumes it holds, and `works.json` ships them as different fields.
        claimed = w.get("completed_claim") if isinstance(w.get("completed_claim"), dict) else {}
        n = claimed.get("volumes")
        if isinstance(n, int):
            # THE RECORD MAKES THE CLAIM AND THE SOURCE IS WHERE IT GOT IT. §5i: these were one
            # column, so a record identifier stood in for a source 2,244 times and the key could
            # not tell two records of one catalogue apart.
            put("INSERT INTO volume_claim (work, record, volumes, source, provenance, retrieved)"
                " VALUES (?,?,?,?,?,?)",
                (wid, w.get("work_id"), n, claimed.get("source"), claimed.get("provenance"),
                 claimed.get("retrieved")), f"volume_claim {wid}")

        # THE RECORD ITSELF, which is the layer `works.json` is written at.
        put("INSERT INTO record (id, work, title, yomi, title_en, title_en_basis, creator,"
            " creator_folded, creator_basis,"
            " volume_count, grouping, content_tier, marketing_label, shop_url, periodical,"
            " label_source, label_url, label_retrieved, label_note,"
            " publisher_raw, imprint_raw, distributor)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (w.get("work_id"), wid, (w.get("title") or {}).get("ja") or "",
             (w.get("title") or {}).get("yomi"), (w.get("title") or {}).get("en"),
             (w.get("title") or {}).get("en_basis"), w.get("creator"),
             _namekey.fold(w.get("creator") or "") or None, w.get("creator_basis"),
             w.get("volume_count"), w.get("grouping"), w.get("content_tier"),
             w.get("marketing_label") if w.get("marketing_label") != "none" else None,
             w.get("shop_url"), int(bool(w.get("periodical"))),
             (w.get("marketing_label_basis") or {}).get("source"),
             (w.get("marketing_label_basis") or {}).get("url"),
             (w.get("marketing_label_basis") or {}).get("retrieved"),
             (w.get("marketing_label_basis") or {}).get("note"),
             w.get("publisher"), w.get("imprint"), w.get("distributor")),
            f"record {w.get('work_id')}")
        # THE PEOPLE THE FIELD NAMES, IN ITS ORDER, resolved through the spelling map. The splitter
        # is asked here so no consumer needs one, which is what `index.json` used to do inline.
        _seen_cid, _n = set(), 0
        for _nm, _rd, _role in _credit_fact.split_detail(str(w.get("creator") or "")):
            _hit = _spelling_to_credit.get(_namekey.fold(_nm))
            if _hit and _hit not in _seen_cid:
                _seen_cid.add(_hit)
                put("INSERT OR IGNORE INTO record_credit (record, seq, credit) VALUES (?,?,?)",
                    (w.get("work_id"), _n, _hit), f"record_credit {w.get('work_id')}")
                _n += 1
        for src_name in (w.get("sources") or []):
            put("INSERT OR IGNORE INTO record_source (record, source) VALUES (?,?)",
                (w.get("work_id"), src_name), f"record_source {src_name}")

        # WHERE AND WHEN IT FIRST APPEARED, AND THE RECORDS IT WAS COMPILED FROM.
        fp = w.get("first_publication") if isinstance(w.get("first_publication"), dict) else {}
        if fp:
            put("INSERT INTO work_origin (record, work, dated, date_source, date_basis, venue,"
                " venue_type, country, country_basis, country_note, note, date_event,"
                " date_followup, date_silence) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (w.get("work_id"), wid,
                 fp.get("date"), fp.get("date_source"), fp.get("date_basis"), fp.get("venue"),
                 fp.get("venue_type"), fp.get("country"), fp.get("country_basis"),
                 fp.get("country_note"), fp.get("note"), fp.get("date_event"),
                 fp.get("date_followup"), fp.get("date_silence")), f"work_origin {wid}")
        # THE RECORD LAYER AGAIN: two catalogue records of one work each name their own sources.
        for rec in (w.get("records") or []):
            if isinstance(rec, dict) and rec.get("source"):
                put("INSERT OR IGNORE INTO work_record (record, work, source, url, retrieved)"
                    " VALUES (?,?,?,?,?)",
                    (w.get("work_id"), wid, rec["source"], rec.get("url"), rec.get("retrieved")),
                    f"work_record {w.get('work_id')} {rec['source']}")
    counts["record"] = db.execute("SELECT count(*) FROM record").fetchone()[0]
    counts["record_credit"] = db.execute("SELECT count(*) FROM record_credit").fetchone()[0]
    counts["work_origin"] = db.execute("SELECT count(*) FROM work_origin").fetchone()[0]
    counts["work_record"] = db.execute("SELECT count(*) FROM work_record").fetchone()[0]
    counts["admission"] = db.execute("SELECT count(*) FROM admission").fetchone()[0]
    counts["volume_claim"] = db.execute("SELECT count(*) FROM volume_claim").fetchone()[0]

    counts["volume"] = db.execute("SELECT count(*) FROM volume").fetchone()[0]
    counts["edition"] = db.execute("SELECT count(*) FROM edition").fetchone()[0]

    _load_feed(db, source, put, counts)


    return counts


def _load_feed(db, source, put, counts):
    """The platforms, the offers and the releases. One loader, called by a rebuild and by a delta.

    EXTRACTED SO `apply` AND `build` CANNOT DIVERGE, §7. A delta that compiled its rows differently
    from a rebuild would make the weekly reconciliation report the difference between two loaders
    rather than a fault in the incremental path, which is the one thing that reconciliation exists
    to be able to say.
    """
    # ── what a platform offers, and what it published ───────────────────────────────────────────
    # STORE-PLAN §4. A platform is named rather than slugged: six display names carry two capture
    # slugs each, so keying on `plat` would split コミックDAYS into two platforms.
    held = {r[0] for r in db.execute("SELECT id FROM work")}
    for _k, r in _rows("series", "series", source):
        for o in (r.get("sources") or []):
            if o.get("platform"):
                put("INSERT OR IGNORE INTO platform (name) VALUES (?)", (o["platform"],),
                    f"platform {o['platform']}")
    # THE COMPILER'S OWN ROWS, §6. Read from `data/build/feed` this was the store taking its input
    # from the files it emits, which on a fresh checkout is nothing and on any run is the last run's.
    releases = (source or {}).get("releases")
    if releases is None:
        feed = ROOT / "data" / "build" / "feed"
        releases = []
        if feed.is_dir():
            for f in sorted(feed.glob("current.json")) + sorted(feed.glob("[0-9]*.json")):
                releases += (json.loads(f.read_text(encoding="utf-8")) or {}).get("releases") or []
    for rel in releases:
        if rel.get("plat_name"):
            put("INSERT OR IGNORE INTO platform (name) VALUES (?)", (rel["plat_name"],),
                f"platform {rel['plat_name']}")
    # THE CENSUS BEHIND `feed/meta.json`, which is what the run saw of each platform. The rows come
    # from the compiler because they are the capture's own answer; a rebuild reads nothing here and
    # the columns stay NULL, which is the truthful state for a store built without a capture.
    # FROM THE COMPILER, OR FROM THE FILE A COMPILER WROTE. Every other collection here falls back
    # to `data/build`, and this one did not, so a rebuild had no census and the weekly comparison
    # reported the platforms, the lapsed listings and the two queues as divergences.
    # FROM THE COMPILER, OR FROM THE FILE THAT CARRIES THE SAME FIELDS. Every other collection here
    # falls back to `data/build` and this one did not, so a store compiled by anything but `build.py`
    # held no report at all: the update workflow rebuilds the store in a step of its own, that store
    # is the one published, and `emit.feed_files` reads the window's width out of this table. With it
    # empty the feed emitted NO files, and the site's build then deleted the ones it was serving as
    # stale. `feed/meta.json` states all four fields, which is where they were read back from.
    run = (source or {}).get("run")
    if run is None:
        _m = BUILD / "feed" / "meta.json"
        got = json.loads(_m.read_text(encoding="utf-8")) if _m.exists() else {}
        run = {k: got[k] for k in ("window_days", "archive_from", "samples_dropped", "generated")
               if k in got}
    for key, value in (run or {}).items():
        put("INSERT OR REPLACE INTO run_report (key, value) VALUES (?,?)",
            (key, None if value is None else str(value)), f"run report {key}")
    meta = (source or {}).get("meta")
    if meta is None:
        _m = BUILD / "feed" / "meta.json"
        meta = json.loads(_m.read_text(encoding="utf-8")) if _m.exists() else {}
    for _i, p_ in enumerate(meta.get("platforms") or []):
        if p_.get("name"):
            put("INSERT OR IGNORE INTO platform (name) VALUES (?)", (p_["name"],),
                f"platform {p_['name']}")
            db.execute("UPDATE platform SET slug = ?, publisher = ?, series = ?, retrieved = ?,"
                       " census_seq = ? WHERE name = ?",
                       (p_.get("id"), p_.get("publisher"), p_.get("series"), p_.get("retrieved"),
                        _i, p_["name"]))
    for _i, (name, m) in enumerate((meta.get("platform_meta") or {}).items()):
        put("INSERT OR IGNORE INTO platform (name) VALUES (?)", (name,), f"platform {name}")
        db.execute("UPDATE platform SET rank = ?, overlap = ?, meta_seq = ? WHERE name = ?",
                   (m.get("rank"), m.get("overlap"), _i, name))
    for l_ in (meta.get("lapsed") or []):
        if l_.get("work") and l_.get("platform"):
            put("INSERT OR IGNORE INTO platform (name) VALUES (?)", (l_["platform"],),
                f"platform {l_['platform']}")
            put("INSERT OR IGNORE INTO lapsed_listing (work, platform, latest_chapter, behind_by,"
                " status) VALUES (?,?,?,?,?)",
                (l_["work"], l_["platform"], l_.get("latest_chapter"), l_.get("behind_by"),
                 l_.get("status")), f"lapsed {l_['work'][:20]}")
    for c_ in (meta.get("print_candidates") or []):
        put("INSERT INTO print_candidate (work_title, author, platform, label, sample_count,"
            " sample_url, status) VALUES (?,?,?,?,?,?,?)",
            (c_.get("work_title"), c_.get("author"), c_.get("platform"), c_.get("label"),
             c_.get("sample_count"), c_.get("sample_url"), c_.get("status")),
            f"print candidate {str(c_.get('work_title'))[:20]}")
    for w_ in (meta.get("web_works") or []):
        basis = w_.get("marketing_label_basis") or {}
        found = w_.get("discovered_via") or {}
        if not put("INSERT INTO web_work (title, url, platform, status, label, marketing_label,"
                   " label_source, label_url, label_retrieved, label_note, content_tier,"
                   " found_source, found_signal, found_url, oneshot)"
                   " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (w_.get("title"), w_.get("url"), w_.get("platform"), w_.get("status"),
                    w_.get("label"), w_.get("marketing_label"), basis.get("source"),
                    basis.get("url"), basis.get("retrieved"), basis.get("note"),
                    w_.get("content_tier"), found.get("source"), found.get("signal"),
                    found.get("url"), _flag(w_, "oneshot")),
                   f"web work {str(w_.get('title'))[:20]}"):
            continue
        wwid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        for i, tag in enumerate(w_.get("tags") or []):
            put("INSERT OR IGNORE INTO web_work_tag (web_work, seq, tag) VALUES (?,?,?)",
                (wwid, i, tag), f"web work tag {i}")
        for i, cr in enumerate(w_.get("authors") or []):
            put("INSERT OR IGNORE INTO web_work_credit (web_work, seq, name, role)"
                " VALUES (?,?,?,?)", (wwid, i, cr.get("name"), cr.get("role")),
                f"web work credit {i}")
    counts["platform"] = db.execute("SELECT count(*) FROM platform").fetchone()[0]
    counts["lapsed_listing"] = db.execute("SELECT count(*) FROM lapsed_listing").fetchone()[0]
    counts["web_work"] = db.execute("SELECT count(*) FROM web_work").fetchone()[0]

    for _k, r in _rows("series", "series", source):
        wid = r.get("id")
        if wid not in held:
            continue
        for o in (r.get("sources") or []):
            if not o.get("platform") or not o.get("url"):
                continue
            # `chapters` IN THE BUILD COUNTS INSTALMENTS, which is the conflation the schema note
            # above is about. The column is named for what it holds; the field is read as it is
            # written, because renaming it in the build is a change to what the site is served.
            put("INSERT INTO offer (work, platform, url, instalments, free, free_timed, priced,"
                " latest, latest_work_level, partial, retrieved, format)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (wid, o["platform"], o.get("url"), o.get("chapters") or 0, o.get("free") or 0,
                 o.get("free_timed") or 0, o.get("priced") or 0, o.get("latest"),
                 int(bool(o.get("latest_work_level"))) if o.get("latest") else None,
                 int(bool(o.get("partial"))), o.get("retrieved"), o.get("format") or "standard"),
                f"offer {wid}@{o['platform']}")
    counts["offer"] = db.execute("SELECT count(*) FROM offer").fetchone()[0]

    # ── what the work's serialisation is, over the offers it runs on ────────────────────────────
    #
    # THE ROW THE FILE SHOWS IS THE FIRST OFFER, which `build.py` sorted so the platform that can
    # speak for the work comes first: a listing whose every date is an import stamp cannot say when
    # a work last updated, however many instalments it holds.
    for _k, r in _rows("series", "series", source):
        wid = r.get("id")
        if wid not in held:
            continue
        first = (r.get("sources") or [{}])[0]
        chosen = db.execute("SELECT id FROM offer WHERE work = ? AND platform = ? AND url = ?",
                            (wid, first.get("platform"), first.get("url"))).fetchone()
        put("INSERT INTO serialisation (work, offer, chapters, chapters_stated, latest, latest_ep,"
            " first, oneshot, oneshot_inferred, collection, series_url)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (wid, chosen[0] if chosen else None, r.get("chapters") or 0, r.get("chapters_stated"),
             r.get("latest"), r.get("latest_ep") or None, r.get("first"),
             int(bool(r.get("oneshot"))), int(bool(r.get("oneshot_inferred"))),
             r.get("collection"), r.get("series_url")), f"serialisation {wid}")
        for slot in (r.get("skipped") or []):
            dated, title = (list(slot) + [None, None])[:2]
            if title:
                put("INSERT OR IGNORE INTO skipped_slot (work, dated, title) VALUES (?,?,?)",
                    (wid, dated or "", title), f"skipped {wid}")
        nxt = r.get("stated_next") or {}
        if nxt.get("platform"):
            put("INSERT INTO stated_next (work, platform, cadence, next_update,"
                " next_update_undecided, next_from_cadence) VALUES (?,?,?,?,?,?)",
                (wid, nxt["platform"], nxt.get("cadence"), nxt.get("next_update"),
                 int(bool(nxt.get("next_update_undecided"))),
                 nxt.get("next_from_cadence")), f"stated_next {wid}")
    counts["serialisation"] = db.execute("SELECT count(*) FROM serialisation").fetchone()[0]
    counts["skipped_slot"] = db.execute("SELECT count(*) FROM skipped_slot").fetchone()[0]
    counts["stated_next"] = db.execute("SELECT count(*) FROM stated_next").fetchone()[0]

    # WHICH WORK A RELEASE BELONGS TO, by the identifier it carries and then by the folded title.
    # An exact title match resolves 944 of 974; these two resolve 971, and the 3 left carry no
    # identifier at all. Suspecting the rule before the data is what §2 taught, twice.
    by_fold = {}
    for _k, r in _rows("series", "series", source):
        if r.get("id") in held and r.get("work"):
            by_fold.setdefault(_namekey.fold(r["work"]), r["id"])
    seen_rel = set()
    for rel in releases:
        rid = rel.get("id")
        # THE FEED SERVES 13 RELEASES TWICE, because its rolling window overlaps the archived
        # month. Collapsed here on purpose rather than left for the primary key to swallow: a
        # constraint that quietly absorbs a row reads as coverage, which is §2's lesson.
        if not rid or rid in seen_rel or not rel.get("plat_name"):
            continue
        seen_rel.add(rid)
        wid = rel.get("wid") if rel.get("wid") in held else by_fold.get(
            _namekey.fold(rel.get("work") or ""))
        ch = rel.get("channel") or {}
        put("INSERT INTO release (id, work, platform, instalment, published, url, kind, first_seen,"
            " work_raw, author, author_basis, plat_slug, adv, web, basis, conf, why, moved, ident,"
            " provenance, series_url, feed_date, free, free_from, access_basis, became_free,"
            " access_changed, date_means, event, event_basis, event_inferred, type_basis,"
            " preferred, preferred_reason, is_preferred, discovered_on, late_discovered,"
            " episode_count, free_episodes, started, work_level, in_collection, syndicated,"
            " origin_note, origin_unknown, same_title_elsewhere, ahead_n, ahead_ep,"
            " ahead_next_free, ahead_next_ep, channel_name, channel_host, channel_origin,"
            " channel_home, channel_syndicated, access_stated, channel_stated)"
            " VALUES (" + ",".join("?" * 57) + ")",
            (rid, wid, rel["plat_name"], rel.get("ep"), rel.get("pub"), rel.get("url"),
             rel.get("type"), rel.get("seen"),
             rel.get("work"), rel.get("author"), rel.get("author_basis"), rel.get("plat"),
             int(bool(rel.get("adv"))), rel.get("web"), rel.get("basis"), rel.get("conf"),
             rel.get("why"), rel.get("moved"), rel.get("ident"), rel.get("provenance"),
             rel.get("series_url"), rel.get("feed_date"), int(bool(rel.get("free"))),
             rel.get("free_from"), rel.get("access_basis"),
             _flag(rel, "became_free"), rel.get("access_changed"), rel.get("date_means"),
             rel.get("kind"), rel.get("kind_basis"), _flag(rel, "kind_inferred"),
             rel.get("type_basis"), rel.get("preferred"), rel.get("preferred_reason"),
             int(bool(rel.get("is_preferred"))), rel.get("discovered_on"),
             _flag(rel, "late_discovered"), rel.get("episode_count"), rel.get("free_episodes"),
             rel.get("started"), _flag(rel, "work_level"), _flag(rel, "in_collection"),
             _flag(rel, "syndicated"), rel.get("origin_note"), _flag(rel, "origin_unknown"),
             rel.get("same_title_elsewhere"), rel.get("ahead_n"), rel.get("ahead_ep"),
             rel.get("ahead_next_free"), rel.get("ahead_next_ep"),
             ch.get("name") or rel.get("channel_name"), ch.get("host"), ch.get("origin"),
             ch.get("home"), _flag(ch, "syndicated"),
             int("access_modes" in rel), int("channel" in rel)), f"release {rid[:40]}")
        for i, mode in enumerate(rel.get("access_modes") or []):
            put("INSERT OR IGNORE INTO release_access_mode (release, seq, mode) VALUES (?,?,?)",
                (rid, i, mode), f"access mode {rid[:30]}")
        for i, other in enumerate(rel.get("also_on") or []):
            put("INSERT OR IGNORE INTO release_also_on (release, seq, platform) VALUES (?,?,?)",
                (rid, i, other), f"also on {rid[:30]}")
    counts["release"] = db.execute("SELECT count(*) FROM release").fetchone()[0]
    counts["release unplaced"] = db.execute(
        "SELECT count(*) FROM release WHERE work IS NULL").fetchone()[0]
    return counts




def _index_columns(db, name):
    """The columns a unique index addresses, read from its SQL where `index_info` gives none.

    ONLY `coalesce(column, default)`, which is the whole of what this schema writes. The default
    maps NULL onto a sentinel and changes nothing about WHICH column identifies the row, so keying
    on the column is keying on the index. Anything else in an expression is something this has not
    been taught to read, and it answers nothing rather than guessing.
    """
    sql = db.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
                     (name,)).fetchone()
    if not sql or not sql[0]:
        return None
    inside = sql[0][sql[0].index("(") + 1:sql[0].rindex(")")]
    out, depth, item = [], 0, ""
    for ch in inside:
        if ch == "," and depth == 0:
            out.append(item.strip())
            item = ""
            continue
        depth += (ch == "(") - (ch == ")")
        item += ch
    out.append(item.strip())
    cols = []
    for part in out:
        m = re.fullmatch(r"coalesce\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,.*\)", part,
                         re.I | re.S)
        if m:
            cols.append(m.group(1))
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part):
            cols.append(part)
        else:
            return None
    return cols


def natural_key(db, table):
    """The columns that address a row of `table`, for a delta to write against.

    NOT THE ROWID, which is the trap. `claim.id` is an INTEGER PRIMARY KEY handed out in insertion
    order, so two compiles of the same corpus number the same claim differently and a reconcile
    keyed on it would report every row as changed. What identifies a claim is `claim_identity`, the
    unique index §5b spent a section giving it, and that is what this finds: the narrowest UNIQUE
    index the table declares, then a composite primary key, then every column.
    """
    info = list(db.execute(f"PRAGMA table_info({table})"))
    pk = [r[1] for r in sorted((r for r in info if r[5]), key=lambda r: r[5])]
    if len(pk) > 1:
        return pk
    rowid = set(pk) if _is_rowid_alias(db, table, info, pk) else set()
    uniques = []
    for _seq, name, unique, origin, partial in db.execute(f"PRAGMA index_list({table})"):
        if not unique or partial:
            continue
        cols = [r[2] for r in db.execute(f"PRAGMA index_info({name})")]
        # AN EXPRESSION HAS NO COLUMN NAME, and `coalesce(source, '')` is half of what identifies a
        # claim. `PRAGMA index_info` gives None for it, so the index has to be read from its own SQL.
        #
        # WHAT IT COST WHILE THIS GAVE UP. Seven unique indexes in this schema are written that way
        # and every one of them named a table whose delta was refused: `claim`, `state_claim`,
        # `romanisation`, `ruby`, `names`, `admission`, `work_credit`. The key fell through to EVERY
        # COLUMN, which addresses more rows than the index does, so the reconcile wrote two rows the
        # index holds as one and SQLite refused the commit. The run recovers by rebuilding the file
        # whole, which is why this was a line of noise on most builds rather than a failure, and it
        # meant the incremental path was doing nothing on the tables that matter most.
        if not all(cols):
            cols = _index_columns(db, name) or cols
        #
        # AND AN INDEX HOLDING THE ROWID IS NO KEY AT ALL. `surface` declares `UNIQUE (kind, folded)`
        # and `UNIQUE (id, kind)`, both two columns wide, and taking the second made every row look
        # new on every compile because the id is handed out by insertion order.
        if all(cols) and not (set(cols) & rowid) and (origin != "pk" or len(cols) > 1):
            uniques.append(cols)
    if uniques:
        return min(uniques, key=len)
    if pk and not _is_rowid_alias(db, table, info, pk):
        return pk
    # EVERY COLUMN EXCEPT THE ROWID, which is the honest fallback where the only unique index is
    # over an EXPRESSION. `claim_identity` is keyed on `coalesce(source, '')` and `PRAGMA
    # index_info` gives no column name for it, so this cannot read that key; what it can say is that
    # two rows agreeing on everything they state are the same row, and that the number the insert
    # handed out is not part of what they state. Keying on `id` would have called every row changed.
    return [r[1] for r in info if r[1] not in rowid]


def _is_rowid_alias(db, table, info, pk):
    """Whether the primary key is a bare INTEGER rowid, which no two compiles agree on.

    A KEY THAT POINTS AT SOMETHING IS NOT A ROWID, however it is typed. `credit_division.surface` is
    an INTEGER PRIMARY KEY and it is also a foreign key into `surface`, so it means the same thing
    in every compile; treating it as a rowid keyed the whole table on `(kind, joiner, partial)` and
    a reconcile then tried to move one division onto another's surface.
    """
    if len(pk) != 1:
        return False
    if not any(r[1] == pk[0] and (r[2] or "").upper() == "INTEGER" for r in info):
        return False
    return not any(r[3] == pk[0] for r in db.execute(f"PRAGMA foreign_key_list({table})"))


def _addresses(db, table):
    """The columns holding a rowid the insert handed out, which addresses a row and states nothing."""
    info = list(db.execute(f"PRAGMA table_info({table})"))
    pk = [r[1] for r in sorted((r for r in info if r[5]), key=lambda r: r[5])]
    return set(pk) if _is_rowid_alias(db, table, info, pk) else set()


def _table_order(db):
    """Tables in dependency order, parents first, so a child is written after what it points at."""
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        " ORDER BY name")]
    deps = {t: {r[2] for r in db.execute(f"PRAGMA foreign_key_list({t})") if r[2] != t}
            for t in tables}
    out, seen = [], set()

    def visit(t, stack=()):
        if t in seen or t in stack or t not in deps:
            return
        for parent in sorted(deps[t]):
            visit(parent, stack + (t,))
        seen.add(t)
        out.append(t)

    for t in tables:
        visit(t)
    return out


def _migrate(db, fresh):
    """Give an existing store the tables and columns the schema has gained since it was made.

    A STORE OUTLIVES THE SCHEMA THAT MADE IT, which is what `delta.ensure` has always said about one
    table and is true of all of them once the store is updated rather than replaced. An addition is
    applied here; anything else is refused loudly, because a column that has CHANGED or gone cannot
    be reconciled and a store carrying half of two schemas is worse than one that says so.

    Returns what it did, so a run can say it rather than doing it silently.
    """
    done = []
    held = {r[0]: r[1] for r in db.execute(
        "SELECT name, sql FROM sqlite_master WHERE type IN ('table', 'index')")}
    for name, kind, sql in fresh.execute(
            "SELECT name, type, sql FROM sqlite_master WHERE type IN ('table', 'index')"
            " AND sql IS NOT NULL ORDER BY type DESC, name"):
        if name not in held:
            db.execute(sql)
            done.append(f"+{kind} {name}")
    for table, in fresh.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"):
        mine = {r[1]: r for r in db.execute(f"PRAGMA table_xinfo({table})")}
        if not mine:
            continue
        for r in fresh.execute(f"PRAGMA table_xinfo({table})"):
            if r[1] in mine:
                continue
            if r[6] or r[3]:
                # A GENERATED COLUMN OR A NOT NULL WITH NO DEFAULT cannot be added to rows that
                # exist. Rebuilding is the honest answer and this says so rather than half-doing it.
                raise RuntimeError(
                    f"{table}.{r[1]} cannot be added to a store that already has rows; "
                    "delete data/relational.db and let the next run rebuild it")
            db.execute(f"ALTER TABLE {table} ADD COLUMN {r[1]} {r[2] or ''}")
            done.append(f"+column {table}.{r[1]}")
    # `derivation` IS THE STORE'S OWN MEMORY AND NOT THE SCHEMA'S, made by `delta.ensure` on
    # whichever store is in front of it, so a scratch that has never converged does not have one.
    gone = [t for t, in db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        if t != "derivation"
        and not fresh.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                              (t,)).fetchone()]
    if gone:
        raise RuntimeError(f"the schema no longer has {', '.join(gone)}; delete "
                           "data/relational.db and let the next run rebuild it")
    return done


def apply(db, source=None, quarantine=False, at=None, fresh=None):
    """Bring an existing store to what the compiler now says, without replacing it. §7.

    THE PRODUCTION CALLER `delta.write` NEVER HAD. The incremental design has been in this
    repository since the store was, argued and tested and never once run by anything but its own
    tests, which makes it a hypothesis rather than a path. What it claims is that an idempotent
    write plus a pure derivation converges on the fixed point a rebuild produces; this is what puts
    the claim in front of real captures.

    THE DIFFERENCE FROM `build` IS WHAT SURVIVES. A rebuild makes a store from nothing, so every
    derivation digest starts empty and every row is new. This takes the store that exists and writes
    only what moved: a row the capture did not change is not written, a row it no longer states is
    DROPPED, and only a derivation whose ANSWER changed cascades. Deletion is the kind these systems
    get wrong, and a table reconciled against the rows that should be there is what sees it.

    THE ROWS COME FROM THE SAME LOADER A REBUILD USES, compiled into memory and then diffed, so a
    delta cannot compile differently from a rebuild. What that costs is one in-memory build; what it
    buys is that the weekly reconciliation reports faults in the incremental path rather than in a
    second loader.

    A SURROGATE ID IS NOT A FACT AND IS NOT CARRIED ACROSS. `name_record.id` is handed out by the
    insert that made the row, so the same record has one number here and another in the scratch
    compile, and an edge copied across verbatim would point at whatever happened to hold that number.
    Every such id is translated through the natural key of the row it addresses, which is why the
    tables are walked parents first.

    Returns `(counts, refused, moved)`: what moved per table, what the schema refused, and which
    derivations changed answer.
    """
    refused = []
    _delta.ensure(db)
    # THE SCRATCH MAY BE HANDED IN, and `build.py` hands one in because it has one. Its store is
    # complete only after the name map is loaded, which happens two hundred lines after the compile
    # that produced it, and a scratch compiled here without those renderings would drop 52,000 rows
    # the run puts straight back.
    if fresh is None:
        fresh, _c, refused_fresh = build(":memory:", source=source, quarantine=quarantine, at=at)
        refused += refused_fresh
    # THE KEYS ARE CHECKED AT COMMIT AND NOT AT EACH STATEMENT, which is what makes a reconcile
    # order-free within a table. A parent dropped before its children is a violation only if it is
    # still one when the transaction ends. Deferring is not relaxing: the same constraints refuse
    # the same rows, one moment later.
    #
    # AND IT HAS TO BE SET INSIDE THE TRANSACTION IT APPLIES TO. SQLite switches the flag off at
    # every COMMIT, and Python's sqlite3 in its default mode makes a bare PRAGMA its own
    # transaction, so setting it before the first write set it and immediately lost it.
    db.isolation_level = None
    migrated = _migrate(db, fresh)
    db.execute("BEGIN")
    db.execute("PRAGMA defer_foreign_keys = ON")
    counts, touched, translate = {}, set(), {}
    for table in _table_order(fresh):
        # THE QUARANTINE AND THE DERIVATIONS ARE THE STORE'S OWN MEMORY, not the compiler's answer.
        # §5g carries a quarantined row forward across rebuilds precisely so it is not lost, and
        # reconciling it against a scratch that never saw yesterday's refusals would delete it.
        #
        # AND SO IS THE RUN'S REPORT ON ITSELF, §13, for the same reason one step later. The
        # census, the drops and what the checks answered are all written AFTER the compile by the
        # passes that compute them, so a scratch has none of them by construction. Reconciling
        # against it dropped all 127 check rows on every build, and the gate that asks whether the
        # store carries them failed on the run after a build and passed on the run after that: a
        # check alternating with nothing wrong is worse than no check, because the first person to
        # see it green stops reading it.
        if table in THE_STORE_S_OWN:
            continue
        # WHAT A ROW STATES, WHICH IS NOT EVERY COLUMN IT HAS. A generated column cannot be written
        # at all, and a rowid handed out by an insert addresses the row and states nothing.
        cols = [r[1] for r in db.execute(f"PRAGMA table_xinfo({table})") if not r[6]]
        key = natural_key(fresh, table)
        mine = _addresses(db, table)
        stated = [c for c in cols if c not in key and c not in mine]
        # WHICH OF THIS TABLE'S COLUMNS HOLD A NUMBER THAT MEANS SOMETHING ELSE HERE. Keyed by the
        # column a foreign key points AT rather than by its table, because the chain runs further
        # than one hop: `credit_dropped.surface` points at `credit_division.surface`, which is
        # itself a surface id, so translating only the tables that own a rowid left the second hop
        # holding the scratch's numbers and the commit refused it.
        points_at = {}
        for r in db.execute(f"PRAGMA foreign_key_list({table})"):
            parent, column, parent_col = r[2], r[3], r[4]
            if parent_col is None:
                parent_col = next(iter(_addresses(db, parent)), None)
            got = translate.get((parent, parent_col))
            if got:
                points_at[column] = got
        rows = []
        for r in fresh.execute(f"SELECT {', '.join(cols)} FROM {table}"):
            row = dict(zip(cols, r))
            for column, mapping in points_at.items():
                if row.get(column) is not None:
                    row[column] = mapping.get(row[column], row[column])
            rows.append(row)
        try:
            written, dropped, unchanged = _delta.reconcile(db, table, key, rows, stated, mine)
        except sqlite3.IntegrityError as e:
            # NAMING THE TABLE, because a delta that fails says only what the schema refused and a
            # reader then has forty tables to guess between. The first one to fail unattended cost
            # a reproduction attempt that never succeeded.
            raise sqlite3.IntegrityError(
                f"{table} refused a delta keyed on {key}: {e}") from e
        counts[table] = (written, dropped, unchanged)
        if written or dropped:
            touched.add(table)
        # AND WHAT THIS TABLE'S OWN NUMBERS BECAME, for the children walked after it. Its address,
        # which the insert handed out here and there and which agree about nothing; and any column
        # already translated on the way in, since a child pointing at THAT column needs the same map.
        if mine:
            addr = next(iter(mine))
            here = {tuple(r[:-1]): r[-1] for r in db.execute(
                f"SELECT {', '.join(key)}, {addr} FROM {table}")}
            # THE FRESH KEY IS TRANSLATED BEFORE IT IS LOOKED UP, exactly as the rows were on the
            # way in. `claim`'s natural key CONTAINS a surrogate, `surface`, so the live side of
            # this map was keyed on live surface ids and the fresh side on the scratch's. Almost
            # nothing matched, and where a scratch id happened to collide with a different live
            # one, `claim.id` was mapped onto somebody else's claim.
            #
            # WHAT THAT COST. 1,752 authors in the published store read as other people: 古賀由人
            # came out フルベ リョウ, against its own ruby, and 117 works lost the English byline
            # that is composed from those readings. It appeared only where a compile ran against a
            # store an EARLIER compile had made from different data, which is what CI does every
            # night with the name passes in between and what no single local build reproduces.
            fresh_key = []
            for r in fresh.execute(f"SELECT {', '.join(key)}, {addr} FROM {table}"):
                row = dict(zip(key, r[:-1]))
                for column, mapping in points_at.items():
                    if row.get(column) is not None:
                        row[column] = mapping.get(row[column], row[column])
                fresh_key.append((tuple(row[c] for c in key), r[-1]))
            translate[(table, addr)] = {
                got: here[k] for k, got in fresh_key if k in here}
        for column, mapping in points_at.items():
            translate[(table, column)] = mapping
    moved, _passes = _delta.converge(db, touched)
    # AND EVERY BASE ANSWER IS RE-ASKED, WHICH THE CASCADE ALONE DOES NOT DO. A digest that has gone
    # stale never heals: convergence recomputes what a write TOUCHED, so an answer recorded before a
    # change that has since stopped moving its tables stays wrong for ever, and the weekly
    # reconciliation found exactly one of those, `names nothing in the corpus is identified by`
    # recorded at 593 where the store says 637. Re-asking all fifteen costs 0.02 s, which is less
    # than the argument for not doing it. `converge` still gates the CASCADE, which is where the
    # cost would actually be.
    moved += [n for n in _delta.recompute(db) if n not in moved]
    stamp(db, at)
    counts["schema"] = (len(migrated), 0, 0)
    db.execute("COMMIT")
    return counts, refused, moved


def ask(db):
    """Every standing question, answered."""
    return {q: db.execute(sql).fetchone()[0] for q, sql in QUESTIONS.items()}


REBUILT = ROOT / "data" / "relational-rebuilt.db"


def equivalent(db=None, rebuilt=None):
    """Set every derivation of a from-scratch store beside the store as it stands.

    `rebuilt` IS A STORE SOMEBODY ELSE COMPILED, and `build.py --rebuild-to` is what compiles it.
    This used to call `build()` with no source, which loads `data/build`; §13 stopped writing those
    files, so the weekly run had nothing to read. Recreating them for this one comparison would put
    the JSON back as an intermediate to keep an old code path alive, which is the opposite of what
    §13 is for.

    THE FROM-SCRATCH STORE IS THE ONE `build.py` ALREADY MAKES. Every run compiles a complete
    scratch in memory from the compiler's own rows and reconciles the live store against it, and
    that scratch shares nothing with the incremental path: it is what a rebuild means now, and no
    file is involved.

    THE CHECK THAT SHARES NOTHING WITH THE INCREMENTAL PATH, which is what §14b asks for. Every
    focused test in `test_delta.py` is written against the same `reads` declarations the updater
    uses, so a wrong declaration satisfies the updater and the test together. A rebuild does not
    consult those declarations at all: it computes every derivation from a store compiled from
    source, and a difference is a bug in the updater.

    IT REPORTS AND DOES NOT REPAIR. Overwriting the incremental store with the rebuilt one would
    hide the fault until the next divergence, which is later and harder.
    """
    if db is None:
        db = open_db()
    delta.ensure(db)
    # THE RECORDED ANSWER, not a fresh one. A wrong `reads` declaration leaves a derivation that was
    # never recomputed, so its digest never moved and the store still reports yesterday's number.
    # Recomputing here before comparing would repair exactly the fault this exists to find.
    held = {n: delta.value(db, n) for n in delta.DERIVATIONS}
    # AND THE ROWS, because two stores can agree on five counts and hold different data. Cheap: one
    # ordered digest per table.
    held_rows = _table_digests(db)

    if rebuilt is None:
        rebuilt = REBUILT
    if not pathlib.Path(rebuilt).exists():
        raise SystemExit(
            f"no from-scratch store at {rebuilt}: compile one with "
            "`python3 build.py --rebuild-to {rebuilt}`, which writes the scratch it already makes. "
            "§13 stopped `data/build` existing, so there is nothing to rebuild from files.")
    fresh = open_db(rebuilt)
    delta.ensure(fresh)
    delta.recompute(fresh)
    rebuilt = {n: delta.value(fresh, n) for n in delta.DERIVATIONS}
    rebuilt_rows = _table_digests(fresh)

    differ = [(n, held.get(n), rebuilt.get(n)) for n in delta.DERIVATIONS
              if held.get(n) != rebuilt.get(n)]
    rows = [(t, held_rows.get(t), rebuilt_rows.get(t))
            for t in sorted(set(held_rows) | set(rebuilt_rows))
            if held_rows.get(t) != rebuilt_rows.get(t)]
    for name, was, now in differ:
        print(f"  DIFFERS  {name}: the store says {was!r}, a rebuild says {now!r}")
    for table, was, now in rows:
        print(f"  DIFFERS  table {table}: {(was or ['?'])[0]} rows here, "
              f"{(now or ['?'])[0]} in a rebuild")
        for r in _first_differing_rows(db, fresh, table):
            print(f"      {r}")
    print(f"{len(differ)} of {len(delta.DERIVATIONS)} derivation(s) and {len(rows)} table(s) "
          f"differ between the store and a rebuild")
    return not (differ or rows)


def _tables(db):
    return [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "AND name NOT IN ('derivation', 'store_stamp') ORDER BY name")]


def _comparable(db, table):
    """The columns two stores can be compared on: what a row STATES, never where it sits.

    A SURROGATE ID IS NOT A FACT, §7. `surface.id` is handed out by the insert that made the row, so
    a store that has been UPDATED and a store rebuilt from nothing number the same surface
    differently and every table reachable from one differed. That is the reconciliation reporting
    the order of two inserts as a divergence, which is exactly the noise that would train a reader
    to ignore it.
    """
    cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
    mine = _addresses(db, table)
    return [c for c in cols if c not in mine] or cols


def _end_of_chain(db, table, column, depth=6):
    """The `(table, column)` a foreign key ultimately addresses, where that is somebody's rowid.

    THE CHAIN RUNS FURTHER THAN ONE HOP. `credit_part_role.surface` points at
    `credit_part(surface)`, which points at `credit_division(surface)`, which is a `surface(id)`,
    and only the last of the four is a rowid.
    """
    if column is None or depth <= 0:
        return None
    if column in _addresses(db, table):
        return (table, column)
    for r in db.execute(f"PRAGMA foreign_key_list({table})"):
        if r[3] == column:
            got = _end_of_chain(db, r[2], r[4] or next(iter(_addresses(db, r[2])), None), depth - 1)
            if got:
                return got
    return None


def _labels(db):
    """`{(table, address): {id: what the row it addresses actually says}}`.

    A SURROGATE ID IS NOT A FACT AND DROPPING IT IS NOT THE ANSWER EITHER, §7. Two stores number the
    same surface differently, so comparing the numbers reports the order of two inserts as a
    divergence; but dropping the column compares an EDGE without its endpoint, and 44 edges pointing
    somewhere else compared equal. What is compared is what the number means.
    """
    out = {}
    for table in _tables(db):
        addr = next(iter(_addresses(db, table)), None)
        if not addr:
            continue
        key = natural_key(db, table)
        if key == [addr]:
            continue
        out[(table, addr)] = {r[-1]: tuple(r[:-1]) for r in db.execute(
            f"SELECT {', '.join(key)}, {addr} FROM {table}")}
    return out


def _reaches_an_address(db, table, column, depth=4):
    """Whether a column holds a number that is somebody's rowid, however many hops away.

    THE CHAIN RUNS FURTHER THAN ONE HOP, which the first version of this missed twice.
    `credit_part_role.surface` points at `credit_part(surface)`, which points at
    `credit_division(surface)`, which is a `surface(id)`, and only the last of the four is a rowid.
    Stopping at the first hop left three tables comparing the order two inserts ran in.
    """
    if column is None or column in _addresses(db, table):
        return True
    if depth <= 0:
        return False
    return any(r[3] == column and _reaches_an_address(db, r[2], r[4], depth - 1)
               for r in db.execute(f"PRAGMA foreign_key_list({table})"))


#: WHAT A COMPILE DOES NOT PRODUCE. The quarantine and the derivations are the store's memory
#: across rebuilds, §5g and §7, and the run's report is written after the compile by `build.py`,
#: `check.py` and `ledger.py`. A scratch has none of them, so neither `apply` nor the weekly
#: comparison may read their absence as a difference.
THE_STORE_S_OWN = ("quarantine", "derivation", "store_stamp",
                   "run_source", "run_queue", "run_drop", "check_result", "check_finding")

#: AND ONE TABLE THAT IS BOTH. `run_report` takes four keys from the compile, the feed window and
#: the run's date, and twelve more from `build.py`'s census, `check.py` and the ledger afterwards.
#: `apply` must keep reconciling it or the live store's window would never be updated; a comparison
#: against a scratch must not, because the scratch has only the four by construction.
WRITTEN_AFTER_THE_COMPILE = THE_STORE_S_OWN + ("run_report",)


def _table_digests(db):
    """`{table: (rows, digest)}` over every row in a stable order, addresses read as what they mean.

    THE STORE'S OWN MEMORY IS LEFT OUT, the same list `apply` skips and for the same reason. The
    quarantine, the derivations and the run's report are written AFTER a compile by the passes that
    produce them, so a from-scratch store has none of them by construction: comparing them reported
    `run_source 13 rows here, 0 in a rebuild` and said nothing about whether the delta had drifted.
    """
    import hashlib
    labels = _labels(db)
    out = {}
    for t in _tables(db):
        if t in WRITTEN_AFTER_THE_COMPILE:
            continue
        cols = _comparable(db, t)
        ends = {c: _end_of_chain(db, t, c) for c in cols}
        order = ", ".join(f'"{c}"' for c in cols)
        h = hashlib.sha256()
        n = 0
        for row in db.execute(f'SELECT {order} FROM "{t}" ORDER BY {order}'):
            said = tuple(labels.get(ends[c], {}).get(v, v) if ends.get(c) else v
                         for c, v in zip(cols, row))
            h.update(repr(sorted(map(repr, said))).encode("utf-8") if False else repr(said).encode("utf-8"))
            n += 1
        out[t] = (n, h.hexdigest())
    return out


def _first_differing_rows(a, b, table, limit=3):
    """A few rows one store holds and the other does not, so a report says what to look at."""
    cols = _comparable(a, table)
    order = ", ".join(f'"{c}"' for c in cols)
    left = {tuple(r) for r in a.execute(f'SELECT {order} FROM "{table}"')}
    right = {tuple(r) for r in b.execute(f'SELECT {order} FROM "{table}"')}
    out = [f"only in the store:  {r}" for r in sorted(left - right, key=repr)[:limit]]
    out += [f"only in a rebuild:  {r}" for r in sorted(right - left, key=repr)[:limit]]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--ask", action="store_true")
    # THE UNATTENDED PATH, WHICH §1a's TABLE HAD NO WRITER FOR. `update.yml` runs at 00:37 with
    # nobody present and ran `--build`, which FAILS on a refusal, so a row the schema would not
    # admit either took the whole run down or, under `continue-on-error`, vanished with it. With
    # this flag the row is recorded and the run goes on populating what it can, which is the whole
    # of what the project owner asked for. A rebuild anywhere a person is present leaves it off.
    ap.add_argument("--unattended", action="store_true",
                    help="quarantine a row the schema refuses and carry on, rather than failing; "
                         "for a scheduled update, never for a rebuild somebody is watching")
    ap.add_argument("--at", help="the date to stamp a quarantined row with")
    ap.add_argument("--publish", metavar="PATH",
                    help="write the store out under this name, stamped, for release. §11")
    ap.add_argument("--equivalent", action="store_true",
                    help="rebuild from scratch and compare every derivation against the store as "
                         "it stands; what the scheduled CI run does")
    a = ap.parse_args()

    if a.equivalent:
        return 0 if equivalent() else 1

    if a.publish:
        # WHAT CROSSES THE LINE, §11. A copy under the name a consumer expects, vacuumed so the
        # artefact is the data and not the space a rebuild left behind, and stamped so a consumer
        # can refuse a shape it does not know. This is the whole of what this repository publishes.
        import shutil
        db = open_db()
        stamp(db)
        db.commit()
        # OUTSIDE THE TRANSACTION, which SQLite requires and Python's sqlite3 opens for you.
        db.isolation_level = None
        db.execute("VACUUM")
        out = pathlib.Path(a.publish)
        shutil.copyfile(DB, out)
        held = dict(open_db(out).execute("SELECT key, value FROM store_stamp"))
        print(f"published {out} ({out.stat().st_size / 1e6:.1f} MB), schema {held.get('schema')}, "
              f"generated {held.get('generated') or 'unstated'}")
        return 0

    if a.build or not a.ask:
        db, counts, refused = build(quarantine=a.unattended, at=a.at)
        for k, v in counts.items():
            print(f"  {k:14} {v}")
        print(f"  {'refused':14} {len(refused)}")
        for what, why in refused[:12]:
            print(f"      {what}: {why}")
        # A FULL REBUILD REFUSES NOTHING, AND THIS IS WHAT STOPS QUARANTINE BECOMING AN EXCUSE.
        #
        # STORE-PLAN §1a gives an UNATTENDED update somewhere to put a row it cannot admit, so the
        # run continues. The risk the project owner named on 2026-08-13 is that the same mechanism
        # becomes a reason not to integrate data that should be integrated: a refusal is easier to
        # set aside than to understand.
        #
        # §2 IS THE EVIDENCE THAT THE RISK IS REAL. 382 volumes were refused on the citation CHECK
        # and every one of them was this loader reading only the volume when the work record named
        # the page its date came from. Not one was data that could not be represented. A quarantine
        # would have absorbed all 382 and the rule would still be wrong.
        #
        # SO THE TWO PATHS ANSWER DIFFERENTLY, which is the same split `--runtime` and `--gate`
        # already make. A rebuild runs where somebody is present, on every pull request and in the
        # weekly equivalence job, and it FAILS on a refusal: the loader is wrong until shown
        # otherwise. The incremental path runs at 00:37 with nobody watching and quarantines
        # instead. Locked in on 2026-08-13 while the count was 0, because a rule adopted when the
        # number is already zero costs nothing to keep and everything to regain.
        if refused and a.unattended:
            print(f"\n  {len(refused)} row(s) quarantined; the run continues. STORE-PLAN §9 is "
                  f"what deals with them, and `rows the store could not admit` counts them.")
        elif refused:
            print(f"\nFAIL: a full rebuild refused {len(refused)} row(s). Suspect the loader "
                  f"before the data: every refusal §2 met was the loader.")
            return 1
    if a.ask:
        db = open_db()
        for q, n in ask(db).items():
            print(f"  {n:7}  {q}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
