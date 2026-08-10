#!/usr/bin/env python3
"""The relational store: schema, loader, and the questions it makes askable.

DERIVED, AND NEVER A SOURCE OF TRUTH. Everything here is rebuilt from `data/build` plus the rulings
the facts hold, so deleting the database costs the time of one rebuild. It is not committed.

WHAT IT IS FOR, and it is not speed alone. Five invariants in `check.py` are foreign keys written
out as Python and run after the damage; two more stop being expressible at all, because a page can
only list what an edge says. `adapters/store/schema.sql` names each one beside the constraint that
replaces it.

Usage:
    ./adapters/store/__init__.py --build     compile data/build into data/store.db
    ./adapters/store/__init__.py --ask       run the standing questions and print the answers
"""
import argparse
import json
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))

from facts import namekey as _namekey                                   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = pathlib.Path(__file__).resolve().parent / "schema.sql"
DB = ROOT / "data" / "store.db"
BUILD = ROOT / "data" / "build"

#: The standing questions, kept beside the schema that makes them one line each. Each was a script
#: or was unaskable before.
QUESTIONS = {
    "claims resting on a community database":
        "SELECT count(*) FROM claim WHERE source_kind = 'community-db'",
    "claims we would lose if NDL were withdrawn":
        "SELECT count(*) FROM claim WHERE source_kind = 'national-library'",
    "works naming nobody":
        "SELECT count(*) FROM work w LEFT JOIN work_credit e ON e.work = w.id "
        "WHERE e.work IS NULL",
    "names two sources disagree about":
        "SELECT count(*) FROM (SELECT subject FROM claim GROUP BY subject_kind, subject, predicate "
        "HAVING count(DISTINCT value) > 1)",
    "credits named by more than one work":
        "SELECT count(*) FROM (SELECT credit FROM work_credit GROUP BY credit HAVING count(*) > 1)",
}


def create(path=None):
    """A fresh database with the schema applied. Replaces any existing file."""
    p = pathlib.Path(path or DB)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        p.unlink()
    db = sqlite3.connect(p)
    db.executescript(SCHEMA.read_text(encoding="utf-8"))
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
    # SOURCE_KIND IS EVERY KIND THAT EXISTS; basis_admits_kind is which PAIRS are allowed. Keeping
    # those separate is what lets `analyser` be a real kind that states nothing.
    #
    # A GAP THE SCHEMA FOUND. 3,056 readings carry `reading_source_kind: analyser` and
    # READING_ATTRIBUTION has no row for it, because that table answers who may STATE a reading and
    # an analyser states nothing. The pair is admitted here against the `analyser` BASIS alone, so
    # a claim cannot say an analyser stated anything. Recorded in facts/reading/BLINDSPOT.md.
    kinds = {k for b in _rd.bases() for k in _rd.kinds_for(b)} | {"analyser"}
    for k in sorted(kinds):
        db.execute("INSERT INTO source_kind (name) VALUES (?)", (k,))
    for b in _rd.bases():
        for k in _rd.kinds_for(b):
            db.execute("INSERT OR IGNORE INTO basis_admits_kind (basis, source_kind) VALUES (?,?)",
                       (b, k))
    db.execute("INSERT OR IGNORE INTO basis_admits_kind (basis, source_kind) VALUES (?,?)",
               ("analyser", "analyser"))
    return db


def _kind_of(record):
    """The source kind for a claim, with a self-sourced one normalised to `derived`.

    `surface` and `title-furigana` are read off a name and a title the corpus already holds, so
    there is no address to record and the schema must not demand one. Saying `derived` is what the
    attribution table already means by it, and it keeps the CHECK simple enough to read.
    """
    from names import provenance as _prov
    if str(record.get("reading_source") or "") in set(getattr(_prov, "SELF_SOURCED", ())):
        return "derived"
    return record.get("reading_source_kind")


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


def build(path=None):
    """Compile `data/build` into the store. Returns `(db, counts, refused)`.

    REFUSED ROWS ARE THE POINT AND ARE COUNTED, not swallowed. A row the schema will not accept is
    a row the current pipeline can produce and should not, so the loader reports how many and why
    instead of relaxing a constraint to make the number go away.
    """
    db = load_rulings(create(path))
    counts, refused = {}, []

    def put(sql, args, what):
        try:
            db.execute(sql, args)
            return True
        except sqlite3.IntegrityError as e:                              # noqa: PERF203
            refused.append((what, str(e)))
            return False

    seen_credit = {}
    for _k, r in _rows("series", "series"):
        wid = r.get("id")
        if not wid or not str(wid).startswith("w"):
            continue
        put("INSERT OR IGNORE INTO work (id, title, first_publication, first_event, volume_count,"
            " explicit_content, admitted_by) VALUES (?,?,?,?,?,?,?)",
            (wid, r.get("work") or "", r.get("first"), r.get("first_event"),
             r.get("volumes"), int(bool(r.get("explicit_content"))),
             r.get("admitted_by") or "unstated"), f"work {wid}")
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
                put("INSERT OR IGNORE INTO work_credit (work, credit, role, seq) VALUES (?,?,?,?)",
                    (wid, cid, role, i), f"edge {cid}->{wid}")
    counts["work_credit"] = db.execute("SELECT count(*) FROM work_credit").fetchone()[0]

    # ── the claims, which is the table the schema exists for ────────────────────────────────────
    # ONE ROW IS ONE CLAIM. The store holds a reading and its provenance as nine `reading_*` keys on
    # a record; here each claim is a row, so a second opinion is a second ROW and a conflict is data.
    # That is what makes "where do two sources disagree about one name" a query at all.
    import yaml
    # KEYED ON `facts/namekey.KINDS`, so the store's populations and the name store's cannot
    # drift apart. The values are what each population is a name OF.
    subject_of = dict(zip(_namekey.KINDS, ("credit", "publisher", "work")))
    ids_for = {"credit": {r["surface"]: r["id"] for r in
                          db.execute("SELECT surface, id FROM credit").fetchall()
                          and [{"surface": s, "id": i} for s, i in
                               db.execute("SELECT surface, id FROM credit")]},
               "work": {t: i for i, t in db.execute("SELECT id, title FROM work")},
               "publisher": {n: i for i, n in db.execute("SELECT id, name FROM publisher")}}
    for f, kind in subject_of.items():
        path = ROOT / "data" / "names" / f"{f}.yaml"
        if not path.exists():
            continue
        rows = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("names", {})
        for surface, r in rows.items():
            if not isinstance(r, dict) or not r.get("reading"):
                continue
            sid = ids_for[kind].get(surface)
            if not sid:
                continue                      # a name the corpus holds no identified subject for
            put("INSERT INTO claim (subject_kind, subject, predicate, value, basis, source,"
                " source_kind, retrieved, url, note) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (kind, sid, "reading", r["reading"], r.get("reading_basis") or "analyser",
                 r.get("reading_source"), _kind_of(r), r.get("reading_at"),
                 r.get("reading_url"), r.get("reading_note")),
                f"claim {kind} {sid}")
    counts["claim"] = db.execute("SELECT count(*) FROM claim").fetchone()[0]

    db.commit()
    return db, counts, refused


def ask(db):
    """Every standing question, answered."""
    return {q: db.execute(sql).fetchone()[0] for q, sql in QUESTIONS.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--ask", action="store_true")
    a = ap.parse_args()

    if a.build or not a.ask:
        db, counts, refused = build()
        for k, v in counts.items():
            print(f"  {k:14} {v}")
        print(f"  {'refused':14} {len(refused)}")
        for what, why in refused[:6]:
            print(f"      {what}: {why}")
    if a.ask:
        db = sqlite3.connect(DB)
        for q, n in ask(db).items():
            print(f"  {n:7}  {q}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
