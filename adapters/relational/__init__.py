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
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))

from facts import namekey as _namekey                                   # noqa: E402
from relational import delta as _delta                                  # noqa: E402
from relational import delta                                            # noqa: E402
from facts import reading as _reading                                   # noqa: E402
from names import provenance as _prov                                   # noqa: E402

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
    """A fresh database with the schema applied. Replaces any existing file."""
    p = pathlib.Path(path or DB)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        p.unlink()
    db = open_db(p)
    db.executescript(SCHEMA.read_text(encoding="utf-8"))
    # `executescript` COMMITS AND THE PRAGMA SURVIVES IT, since it is connection state rather than a
    # statement in a transaction. Asserted rather than assumed, because everything below rests on it.
    if not db.execute("PRAGMA foreign_keys").fetchone()[0]:
        raise RuntimeError("foreign keys are off on a freshly created store")
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
    # BOTH ATTRIBUTION TABLES, SCOPED BY THE CLAIM EACH ANSWERS FOR. This was filled from the reading
    # one alone, so `('translated','derived')` read as forbidden 2,767 times while `facts/reading`
    # admits it on its first line. `stated` means a different document for a reading than for an
    # English name, which is why the predicate is part of the key rather than a note beside it.
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


def _rows(name, key):
    """The rows of a built collection as `(id_or_None, row)` pairs.

    A COLLECTION KEYED BY ID IS NOT A LIST, and flattening it to `.values()` threw the identifier
    away. `credits.json` is a dict whose KEY is `c00001`, which sent me to the identity registry for
    something I already had.
    """
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


def _target_of(sql):
    """The table an INSERT or an UPDATE names, for the quarantine to file the row under."""
    words = str(sql).replace("(", " ").split()
    for i, w in enumerate(words):
        if w.upper() in ("INTO", "UPDATE") and i + 1 < len(words):
            return words[i + 1]
    return "?"


def build(path=None, quarantine=False, at=None):
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
    """
    db = load_rulings(create(path))
    counts, refused = {}, []

    def put(sql, args, what):
        try:
            db.execute(sql, args)
            return True
        except sqlite3.IntegrityError as e:                              # noqa: PERF203
            refused.append((what, str(e)))
            if quarantine:
                quarantine_row(db, sql, args, what, e, at)
            return False

    seen_credit = {}
    for _k, r in _rows("series", "series"):
        wid = r.get("id")
        if not wid or not str(wid).startswith("w"):
            continue
        put("INSERT OR IGNORE INTO work (id, title, first_publication, first_event,"
            " explicit_content) VALUES (?,?,?,?,?)",
            (wid, r.get("work") or "", r.get("first"), r.get("first_event"),
             int(bool(r.get("explicit_content")))), f"work {wid}")
    counts["work"] = db.execute("SELECT count(*) FROM work").fetchone()[0]

    for cid, r in _rows("credits", "credits"):
        surface = r.get("credit")
        if not cid or not surface:
            continue
        if surface in seen_credit:
            refused.append((f"credit {cid}", f"surface already held by {seen_credit[surface]}"))
            continue
        seen_credit[surface] = cid
        put("INSERT INTO credit (id, surface, kind) VALUES (?,?,?)",
            (cid, surface, r.get("shape") or "unknown"), f"credit {cid}")
    counts["credit"] = db.execute("SELECT count(*) FROM credit").fetchone()[0]

    for _k, r in _rows("publishers", "publishers"):
        pid, nm = r.get("id"), r.get("name")
        if not pid or not nm:
            continue
        if put("INSERT OR IGNORE INTO publisher (id, name) VALUES (?,?)", (pid, nm),
               f"publisher {pid}"):
            for line in (r.get("lines") or r.get("seats") or []):
                nmm = line.get("name") if isinstance(line, dict) else line
                if nmm:
                    put("INSERT OR IGNORE INTO imprint (publisher, name) VALUES (?,?)",
                        (pid, nmm), f"imprint {nmm}")
    counts["publisher"] = db.execute("SELECT count(*) FROM publisher").fetchone()[0]
    counts["imprint"] = db.execute("SELECT count(*) FROM imprint").fetchone()[0]

    # THE EDGE, WHICH IS WHERE THE FOREIGN KEYS EARN THEIR PLACE. A credit identifier naming nobody
    # is refused here rather than counted later.
    for cid, r in _rows("credits", "credits"):
        for i, w in enumerate(r.get("works") or []):
            wid = w.get("id") if isinstance(w, dict) else w
            role = w.get("role") if isinstance(w, dict) else None
            if cid and wid:
                put("INSERT OR IGNORE INTO work_credit (work, credit, role) VALUES (?,?,?)",
                    (wid, cid, role), f"edge {cid}->{wid}")
    counts["work_credit"] = db.execute("SELECT count(*) FROM work_credit").fetchone()[0]

    # ── the identity registry, §5d ───────────────────────────────────────────────────────────────
    #
    # THE STORE HAS NEVER READ THIS AND THE ENTITY WAS ALWAYS THERE. `data/identity/` holds the
    # spellings that reach a person, the addresses that reach a work, and the rulings behind both.
    import yaml
    IDENT = ROOT / "data" / "identity"

    def _yaml(name):
        f = IDENT / f"{name}.yaml"
        return (yaml.safe_load(f.read_text(encoding="utf-8")) or {}) if f.exists() else {}

    # THE MERGE MAP FIRST, because an anchor may still name a retired identifier and one address
    # reaching two works would refuse. `merged` is a map from the retired id to its survivor.
    survivor, retired = {}, []
    for f, key, col in (("series", "merged", "work"), ("credits", "merged", "credit")):
        doc = BUILD / f"{f}.json"
        if not doc.exists():
            continue
        for gone, kept in (json.loads(doc.read_text(encoding="utf-8")).get(key) or {}).items():
            survivor[gone] = kept
            retired.append((gone, col))

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
    for c in (_yaml("credits").get("credits") or []):
        cid = _live(c.get("id"))
        if cid not in held_credit:
            continue
        for a_ in (c.get("anchors") or []):
            _scheme, _, spelling = str(a_).partition(":")
            if not spelling or spelt.get(spelling) == cid:
                continue
            spelt[spelling] = cid
            put("INSERT INTO credit_spelling (spelling, credit) VALUES (?,?)",
                (spelling, cid), f"spelling {spelling}")
    counts["credit_spelling"] = db.execute("SELECT count(*) FROM credit_spelling").fetchone()[0]

    # THE RULINGS, which are what make a merge and a divide safe to repeat.
    def _ruling(kind, subject, r, spellings):
        if not r.get("basis"):
            refused.append((f"ruling {kind}", "a ruling with no reasoning is a preference"))
            return
        db.execute("INSERT INTO identity_ruling (kind, subject, reading, shape, basis, keeps)"
                   " VALUES (?,?,?,?,?,?)",
                   (kind, subject, r.get("reading"), r.get("shape"), r["basis"], r.get("keep")))
        rid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        for sp in spellings:
            if sp:
                db.execute("INSERT OR IGNORE INTO identity_ruling_surface (ruling, spelling)"
                           " VALUES (?,?)", (rid, sp))

    for r in (_yaml("credit-rulings").get("rulings") or []):
        _ruling(r.get("decision") or "keep", "credit", r, r.get("surfaces") or [])
    for r in (_yaml("credits").get("homophones") or []):
        _ruling("homophone", "credit", r,
                [x.get("credit") for x in (r.get("credits") or []) if isinstance(x, dict)])
    counts["identity_ruling"] = db.execute("SELECT count(*) FROM identity_ruling").fetchone()[0]

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
    by_subject = {"credit": {}, "work": {}, "publisher": {}}
    for sp, cid in db.execute("SELECT spelling, credit FROM credit_spelling"):
        by_subject["credit"].setdefault(_namekey.fold(sp), []).append(cid)
    for s, cid in db.execute("SELECT surface, id FROM credit"):
        by_subject["credit"].setdefault(_namekey.fold(s), []).append(cid)
    for i, ttl in db.execute("SELECT id, title FROM work"):
        by_subject["work"].setdefault(_namekey.fold(ttl), []).append(i)
    for i, nm in db.execute("SELECT id, name FROM publisher"):
        by_subject["publisher"].setdefault(_namekey.fold(nm), []).append(i)
    surfaces, seen_claims = {}, set()

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
            sid = surface_id(surface_kind[f], name, subject_kind,
                             verified=(None if r.get("verified") is None
                                       else int(bool(r["verified"]))),
                             uncertain=int(bool(r.get("reading_uncertain"))) or None,
                             ordinary=int(bool(r.get("reading_ordinary"))) or None,
                             transliterates=r.get("transliterates"))
            if sid is None:
                continue
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
                    ident = (sid, predicate, value, basis, claim.get(f"{cite}_source") or "")
                    if ident in seen_claims:
                        continue
                    seen_claims.add(ident)
                    put("INSERT INTO claim (surface, predicate, value, basis, source, source_kind,"
                        " retrieved, reviewed, url, isbn, note, displaced)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (sid, predicate, value, basis, claim.get(f"{cite}_source"),
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
                ident = (sid, "division", divided or r.get("reading") or "", basis, "")
                if ident in seen_claims:
                    continue
                seen_claims.add(ident)
                put("INSERT INTO claim (surface, predicate, value, basis, note)"
                    " VALUES (?,'division',?,?,?)",
                    (sid, divided or r.get("reading") or "", basis,
                     r.get("reading_boundary") or r.get("reading_note")),
                    f"claim division {f} {name}")
    counts["surface"] = db.execute("SELECT count(*) FROM surface").fetchone()[0]
    counts["claim"] = db.execute("SELECT count(*) FROM claim").fetchone()[0]

    # ── the renderings, which are what a reader is actually shown ────────────────────────────────
    #
    # `feed/names.json` IS THE DERIVED FORM AND THIS IS WHERE IT LANDS. The romanisations, the ruby
    # spans, the credit divisions and the two romanisation maps are all functions of a reading and
    # of the rules `adapters/names` holds; none of that judgement moves, and STORE-PLAN §3 is where
    # the reason is written out. What changes is that the answer is a row.
    names = BUILD / "feed" / "names.json"
    doc = json.loads(names.read_text(encoding="utf-8")) if names.exists() else {}

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

    # WHERE A BYLINE WAS SEEN, §5e. 3,399 credit-line surfaces existed and nothing connected one to
    # the work it appeared on. One line appears on many works, so it is an edge and not a column.
    for _k, r in _rows("series", "series"):
        wid, field = r.get("id"), r.get("author")
        if wid and field:
            sid = surface_id("credit-line", field)
            if sid is not None:
                put("INSERT OR IGNORE INTO work_byline (work, surface) VALUES (?,?)",
                    (wid, sid), f"byline {wid}")
    counts["work_byline"] = db.execute("SELECT count(*) FROM work_byline").fetchone()[0]

    for folded, r in entries("credit_parts"):
        sid = surface_id("credit-line", folded)
        if sid is None:
            continue
        put("INSERT INTO credit_division (surface, joiner, partial) VALUES (?,?,?)",
            (sid, r.get("j") or "", int(bool(r.get("part")))), f"division {folded}")
        for i, part in enumerate(r.get("p") or []):
            if part.get("n"):
                put("INSERT OR IGNORE INTO credit_part (surface, seq, name, role)"
                    " VALUES (?,?,?,?)", (sid, i, part["n"], part.get("r")), f"part {folded} {i}")
        for text in (r.get("drop") or []):
            put("INSERT OR IGNORE INTO credit_dropped (surface, text) VALUES (?,?)",
                (sid, text), f"dropped {folded}")
    counts["credit_part"] = db.execute("SELECT count(*) FROM credit_part").fetchone()[0]

    # THE LINE'S OWN NAME AND ITS PARENT, which the imprint registry states and nothing carried into
    # the store. An imprint row exists per publisher already; this is the same fact keyed the way a
    # reader reaches it.
    for folded, r in entries("imprints"):
        surface_id("imprint", folded)
        for house in (r.get("publishers") or []):
            db.execute("UPDATE imprint SET slug = ?, parent = ? WHERE name = ? AND publisher ="
                       " (SELECT id FROM publisher WHERE name = ?)",
                       (r.get("id"), r.get("parent"), r.get("name"), house))
    counts["surface"] = db.execute("SELECT count(*) FROM surface").fetchone()[0]

    # ── the two tables the schema declared and nothing ever wrote ───────────────────────────────
    #
    # WHY THEY WERE EMPTY, established 2026-08-13 rather than assumed. `schema.sql` and this loader
    # arrived in one commit, the loader was written for the identity spine, and nothing came back
    # for the rest. So `edition` and `work_publisher` carried columns, constraints and an index and
    # held no rows, which is a schema asserting something nothing had ever tested against data.
    # STORE-PLAN §2.

    # WORK TO PUBLISHER, read off `publishers.json`'s own `works` list, which IS the edge. Going by
    # way of the print blocks would have rebuilt a join the publisher pass has already made.
    # KEYED ON THE FOLD AS WELL AS THE SPELLING, §5c. The print blocks write one line as
    # `Yuri-hime comics`, `Yurihime comics` and `IDコミックス　／　Yurihime comics`, and an exact
    # match on the name left 906 of 2,661 rows with no imprint at all. The registry's own slug is
    # what identifies a line; folding the spelling is what reaches it from a print block.
    imprint_id = {}
    for i, pub, nm in db.execute("SELECT id, publisher, name FROM imprint"):
        imprint_id[(pub, nm)] = i
        imprint_id.setdefault((pub, _namekey.fold(nm).lower()), i)

    def _imprint(pid, name):
        if not name:
            return None
        got = imprint_id.get((pid, name))
        if got is not None:
            return got
        return imprint_id.get((pid, _namekey.fold(str(name)).lower()))
    # THE IMPRINT A WORK IS PUBLISHED UNDER lives on the print block rather than on the publisher,
    # because one house runs several lines and a work sits on one of them.
    work_imprint = {}
    for _k, r in _rows("series", "series"):
        wid = r.get("id")
        for blk in (r.get("print") or []):
            if wid and blk.get("publisher") and blk.get("imprint"):
                work_imprint.setdefault((wid, blk["publisher"]), blk["imprint"])
    pub_name = {i: n for i, n in db.execute("SELECT id, name FROM publisher")}
    for _k, r in _rows("publishers", "publishers"):
        pid = r.get("id")
        for wid in (r.get("works") or []):
            imp = work_imprint.get((wid, pub_name.get(pid)))
            put("INSERT INTO work_publisher (work, publisher, imprint) VALUES (?,?,?)",
                (wid, pid, _imprint(pid, imp)), f"work_publisher {wid}->{pid}")
    counts["work_publisher"] = db.execute("SELECT count(*) FROM work_publisher").fetchone()[0]

    # ── whether a work is running, and the byline it prints, §5e ────────────────────────────────
    for _k, r in _rows("series", "series"):
        wid = r.get("id")
        if not wid or r.get("state") is None:
            continue
        put("INSERT INTO work_state (work, state, basis) VALUES (?,?,?)",
            (wid, r["state"], r.get("state_basis") or r.get("completed_basis")),
            f"work_state {wid}")
        # THE COMPETING CLAIMS, which are the disagreement rule applied to something other than a
        # name: 271 works hold a source, a term, a date and a page each.
        for cl in (r.get("state_claims") or []):
            if isinstance(cl, dict) and cl.get("source"):
                put("INSERT OR IGNORE INTO state_claim (work, source, says, term, url, read)"
                    " VALUES (?,?,?,?,?,?)",
                    (wid, cl["source"], cl.get("says"), cl.get("term"), cl.get("url"),
                     cl.get("read")), f"state_claim {wid}")
    counts["work_state"] = db.execute("SELECT count(*) FROM work_state").fetchone()[0]
    counts["state_claim"] = db.execute("SELECT count(*) FROM state_claim").fetchone()[0]

    # EDITIONS. `works.json` is keyed by the RECORD identifier a catalogue or a shop issued, and
    # `edition.work` is a `w` identifier, so the print blocks supply the bridge: `work_ids` names
    # every record a series row's run is made of.
    of_record, shop_of = {}, {}
    for _k, r in _rows("series", "series"):
        wid = r.get("id")
        for blk in (r.get("print") or []):
            for rec in (blk.get("work_ids") or []):
                of_record.setdefault(rec, wid)
                if blk.get("shop_url"):
                    shop_of.setdefault(rec, blk["shop_url"])
    for _k, w in _rows("works", "works"):
        wid = of_record.get(w.get("work_id"))
        if not wid:
            continue                          # a record no series row's run names
        # THE PAGE THE RECORD ITSELF CAME FROM, which is where most volume dates are checkable.
        # A volume states `madb_id` only where the bulk dataset named one per book; a volume dated
        # by the catalogue that issued the whole record cites that record. 209 volumes were being
        # refused as uncitable while their work carried
        # `records: [{source: madb, url: .../id/C418820}]`, and the work_id IS that page's id.
        of_work = next((r.get("url") for r in (w.get("records") or []) if r.get("url")), None)
        for v in (w.get("volumes") or []):
            # BOTH EVENTS, NOT WHICHEVER ONE FITS. A volume states a printing date, a delivery
            # date, or both, and 812 state two that differ. The `if/elif` that used to stand here
            # kept the printing and dropped the delivery, which looked like a choice and was the
            # shape: `edition` held one row per book with `isbn UNIQUE`, so the second event had
            # nowhere to go. §5b split the book from the event and both are held now.
            events = []
            if v.get("published"):
                events.append(("printing", v["published"]))
            if v.get("delivered") and v.get("delivered") != v.get("published"):
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
            # A NUMBER THAT IS A WORD IS A DESIGNATION. 28 volumes are called `難問編`, `沼編` or
            # `上巻`, carry no integer position, and carried no designation either, so the store
            # held nothing at all about what they are called. `build.volume_number` produced no
            # integer for them, which is the signal that the string is a name and not a position.
            designation = v.get("designation")
            if not designation and v.get("number_n") is None and v.get("number"):
                designation = str(v["number"])
            if not put("INSERT INTO volume (work, volume, designation) VALUES (?,?,?)",
                       (wid, v.get("number_n"), designation),
                       f"volume {wid} {v.get('isbn') or designation or '?'}"):
                continue
            vol = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            # EVERY ISBN THE BOOK CARRIES. 81 volumes list two, a regular printing and a special
            # edition, and the store kept one of them.
            for isbn in dict.fromkeys([v["isbn"]] if v.get("isbn") else []).keys() | set(
                    v.get("editions") or []):
                put("INSERT INTO volume_isbn (isbn, volume) VALUES (?,?)", (isbn, vol),
                    f"isbn {isbn}")
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
                put("INSERT INTO edition (volume, dated, kind, dated_basis, cite)"
                    " VALUES (?,?,?,?,?)",
                    (vol, dated, kind, basis, cite if kind == "printing" else (shop or cite)),
                    f"edition {kind} {wid} {v.get('isbn') or v.get('designation') or '?'}")
    # ── the grounds, and what a source says the run is, §5c ──────────────────────────────────────
    #
    # BOTH WERE COLUMNS ON `work` AND BOTH WERE READ FROM THE WRONG FILE. `series.json` carries
    # neither, so `admitted_by` was the word `'unstated'` on all 3,040 rows under a NOT NULL, and
    # `volume_count` was NULL on all of them, while `works.json` held structured grounds on 1,887
    # records. `explicit_content` is filled from the same place and is False on every one, which is
    # now a measured answer rather than a column default.
    for _k, w in _rows("works", "works"):
        wid = of_record.get(w.get("work_id"))
        if not wid:
            continue
        if w.get("explicit_content"):
            db.execute("UPDATE work SET explicit_content = 1 WHERE id = ?", (wid,))
        # HOW IT IS PRESENTED, AND WHETHER IT IS. `marketing_label` is publisher-side labelling
        # under DEFINITIONS §4 and `visibility` is the §13 register.
        mb = w.get("marketing_label_basis") if isinstance(w.get("marketing_label_basis"), dict) else {}
        if w.get("marketing_label") or w.get("visibility"):
            put("INSERT OR IGNORE INTO work_presentation (work, label, visibility, source, url,"
                " retrieved, note) VALUES (?,?,?,?,?,?,?)",
                (wid, w.get("marketing_label"), w.get("visibility"), mb.get("source"),
                 mb.get("url"), mb.get("retrieved"), mb.get("note")), f"presentation {wid}")
        for g in (w.get("admitted_by") or []):
            if isinstance(g, dict):
                put("INSERT INTO admission (work, comparator, shelf, shop_url, url, retrieved,"
                    " note) VALUES (?,?,?,?,?,?,?)",
                    (wid, g.get("comparator"), g.get("shelf"), g.get("shop_url"), g.get("url"),
                     g.get("retrieved"), g.get("note")), f"admission {wid}")
        # A COUNT A SOURCE STATES, AND 72 WORKS HAVE RECORDS THAT DISAGREE, which is why this is a
        # row with its source beside it rather than a column that would have to pick one.
        claimed = w.get("completed_claim") if isinstance(w.get("completed_claim"), dict) else {}
        n = claimed.get("volumes") if claimed.get("volumes") is not None else w.get("volume_count")
        if isinstance(n, int):
            put("INSERT OR IGNORE INTO volume_claim (work, volumes, source, provenance, retrieved)"
                " VALUES (?,?,?,?,?)",
                (wid, n, claimed.get("source") or w.get("work_id"), claimed.get("provenance"),
                 claimed.get("retrieved")), f"volume_claim {wid}")
    counts["admission"] = db.execute("SELECT count(*) FROM admission").fetchone()[0]
    counts["volume_claim"] = db.execute("SELECT count(*) FROM volume_claim").fetchone()[0]

    counts["volume"] = db.execute("SELECT count(*) FROM volume").fetchone()[0]
    counts["edition"] = db.execute("SELECT count(*) FROM edition").fetchone()[0]

    # ── what a platform offers, and what it published ───────────────────────────────────────────
    # STORE-PLAN §4. A platform is named rather than slugged: six display names carry two capture
    # slugs each, so keying on `plat` would split コミックDAYS into two platforms.
    held = {r[0] for r in db.execute("SELECT id FROM work")}
    for _k, r in _rows("series", "series"):
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

    for _k, r in _rows("series", "series"):
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
                " latest, partial, retrieved) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (wid, o["platform"], o.get("url"), o.get("chapters") or 0, o.get("free") or 0,
                 o.get("free_timed") or 0, o.get("priced") or 0, o.get("latest"),
                 int(bool(o.get("partial"))), o.get("retrieved")),
                f"offer {wid}@{o['platform']}")
    counts["offer"] = db.execute("SELECT count(*) FROM offer").fetchone()[0]

    # WHICH WORK A RELEASE BELONGS TO, by the identifier it carries and then by the folded title.
    # An exact title match resolves 944 of 974; these two resolve 971, and the 3 left carry no
    # identifier at all. Suspecting the rule before the data is what §2 taught, twice.
    by_fold = {}
    for _k, r in _rows("series", "series"):
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
    ap.add_argument("--equivalent", action="store_true",
                    help="rebuild from scratch and compare every derivation against the store as "
                         "it stands; what the scheduled CI run does")
    a = ap.parse_args()

    if a.equivalent:
        return 0 if equivalent() else 1

    if a.build or not a.ask:
        db, counts, refused = build()
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
        if refused:
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
