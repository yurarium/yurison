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
    db = load_rulings(create(path))
    counts, refused = {}, []

    put = _putter(db, refused, quarantine, at)

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
    for gone, kept in ((json.loads((BUILD / "series.json").read_text(encoding="utf-8"))
                        .get("merged") or {}).items() if (BUILD / "series.json").exists() else ()):
        survivor[gone] = kept
        retired.append((gone, "work"))
    for f, col in (("credits", "credit"), ("publishers", "publisher")):
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
                " transliterates, entity, basis) VALUES (?,?,?,?,?,?,?,?,?)",
                (surface_kind[f], name, sid,
                 None if r.get("verified") is None else int(bool(r["verified"])),
                 int(bool(r.get("reading_uncertain"))), int(bool(r.get("reading_ordinary"))),
                 r.get("transliterates"), r.get("entity"), r.get("basis")),
                f"name_record {f} {name}")
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
                    put("INSERT INTO claim (surface, kind, predicate, value, basis, source,"
                        " source_kind, retrieved, reviewed, url, isbn, note, displaced, record)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                         int(i > 0), rec_id),
                        f"claim {predicate} {f} {name}" + (f" [{i}]" if i else ""))
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
                put("INSERT INTO claim (surface, kind, predicate, value, basis, source,"
                    " source_kind, url, isbn, note, record, basis_stated)"
                    " VALUES (?,?,'division',?,?,?,?,?,?,?,?,?)",
                    (sid, surface_kind[f], divided or r.get("reading") or "", basis,
                     r.get("reading_source") if lends else None,
                     _kind_of(r) if lends else None,
                     (cited.get("url") or r.get("reading_url")) if lends else None,
                     cited.get("isbn"),
                     r.get("reading_boundary") or r.get("reading_note"), rec_id,
                     int(bool(r.get("reading_boundary_basis")))),
                    f"claim division {f} {name}")
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
                put("INSERT OR IGNORE INTO work_byline (work, surface, kind)"
                    " VALUES (?,?,'credit-line')", (wid, sid), f"byline {wid}")
    counts["work_byline"] = db.execute("SELECT count(*) FROM work_byline").fetchone()[0]
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
        for party in _pblk.parties(blk):
            for seat in _phid.SEATS:
                raw = str(party.get(seat) or "").strip()
                if not raw:
                    continue
                hid = _house_of.get(_phid.anchor(raw) or "")
                imp_raw = str(party.get("imprint") or "").strip()
                line = _imp.resolve(_phid.publisher_of(party.get("publisher") or ""),
                                    imp_raw, _lidx) if imp_raw else None
                put("INSERT INTO print_party (print_row, seat, publisher_raw, publisher,"
                    " imprint_raw, imprint, first, last) VALUES (?,?,?,?,?,?,?,?)",
                    (pid, seat, raw, hid, imp_raw or None,
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

    # ── what a platform offers, and what it published ───────────────────────────────────────────
    # STORE-PLAN §4. A platform is named rather than slugged: six display names carry two capture
    # slugs each, so keying on `plat` would split コミックDAYS into two platforms.
    held = {r[0] for r in db.execute("SELECT id FROM work")}
    for _k, r in _rows("series", "series", source):
        for o in (r.get("sources") or []):
            if o.get("platform"):
                put("INSERT OR IGNORE INTO platform (name) VALUES (?)", (o["platform"],),
                    f"platform {o['platform']}")
    feed = ROOT / "data" / "build" / "feed"
    releases = []
    if feed.is_dir():
        for f in sorted(feed.glob("current.json")) + sorted(feed.glob("[0-9]*.json")):
            releases += (json.loads(f.read_text(encoding="utf-8")) or {}).get("releases") or []
    for rel in releases:
        if rel.get("plat_name"):
            put("INSERT OR IGNORE INTO platform (name) VALUES (?)", (rel["plat_name"],),
                f"platform {rel['plat_name']}")
    counts["platform"] = db.execute("SELECT count(*) FROM platform").fetchone()[0]

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
                " latest, partial, retrieved, format) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (wid, o["platform"], o.get("url"), o.get("chapters") or 0, o.get("free") or 0,
                 o.get("free_timed") or 0, o.get("priced") or 0, o.get("latest"),
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
                 int(bool(nxt.get("next_from_cadence")))), f"stated_next {wid}")
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
        put("INSERT INTO release (id, work, platform, instalment, published, url, kind, first_seen)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (rid, wid, rel["plat_name"], rel.get("ep"), rel.get("pub"), rel.get("url"),
             rel.get("type"), rel.get("seen")), f"release {rid[:40]}")
    counts["release"] = db.execute("SELECT count(*) FROM release").fetchone()[0]
    counts["release unplaced"] = db.execute(
        "SELECT count(*) FROM release WHERE work IS NULL").fetchone()[0]

    db.commit()
    return db, counts, refused



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



def ask(db):
    """Every standing question, answered."""
    return {q: db.execute(sql).fetchone()[0] for q, sql in QUESTIONS.items()}


def equivalent(db=None):
    """Rebuild from nothing and set every derivation beside the store as it stands.

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

    fresh, _counts, _refused = build(path=ROOT / "data" / "relational-rebuilt.db")
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
        "AND name <> 'derivation' ORDER BY name")]


def _table_digests(db):
    """`{table: (rows, digest)}` over every row in a stable order."""
    import hashlib
    out = {}
    for t in _tables(db):
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({t})")]
        order = ", ".join(f'"{c}"' for c in cols)
        h = hashlib.sha256()
        n = 0
        for row in db.execute(f'SELECT {order} FROM "{t}" ORDER BY {order}'):
            h.update(repr(row).encode("utf-8"))
            n += 1
        out[t] = (n, h.hexdigest())
    return out


def _first_differing_rows(a, b, table, limit=3):
    """A few rows one store holds and the other does not, so a report says what to look at."""
    cols = [r[1] for r in a.execute(f"PRAGMA table_info({table})")]
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
    ap.add_argument("--equivalent", action="store_true",
                    help="rebuild from scratch and compare every derivation against the store as "
                         "it stands; what the scheduled CI run does")
    a = ap.parse_args()

    if a.equivalent:
        return 0 if equivalent() else 1

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
