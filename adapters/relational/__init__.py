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

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = pathlib.Path(__file__).resolve().parent / "schema.sql"
DB = ROOT / "data" / "relational.db"
BUILD = ROOT / "data" / "build"

#: The standing questions, kept beside the schema that makes them one line each. Each was a script
#: or was unaskable before. They are the derivations `delta.py` recomputes and digests. Typed once
#: there: a question the store answers and a derivation whose digest gates the cascade are the same
#: thing, and two copies of the SQL would let a partial update and a full rebuild answer differently.
QUESTIONS = {name: spec["sql"] for name, spec in _delta.DERIVATIONS.items()}


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
    # A GAP THE SCHEMA FOUND, and the answer is `facts/reading`'s and not this loader's. 3,056
    # readings carry `reading_source_kind: analyser` and READING_ATTRIBUTION has no row for it,
    # because that table answers who may STATE a reading and an analyser states nothing. The pair
    # was written here, which put a vocabulary decision in the code that reads the data; it is
    # `_rd.analyser_pair()` now, beside the table it is an exception to.
    kinds = {k for b in _rd.bases() for k in _rd.kinds_for(b)} | {_rd.analyser_pair()[1]}
    for k in sorted(kinds):
        db.execute("INSERT INTO source_kind (name) VALUES (?)", (k,))
    for b in _rd.bases():
        for k in _rd.kinds_for(b):
            db.execute("INSERT OR IGNORE INTO basis_admits_kind (basis, source_kind) VALUES (?,?)",
                       (b, k))
    db.execute("INSERT OR IGNORE INTO basis_admits_kind (basis, source_kind) VALUES (?,?)",
               _rd.analyser_pair())
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
                (kind, sid, "reading", r["reading"],
                 r.get("reading_basis") or _reading.DEFAULT_BASIS,
                 r.get("reading_source"), _kind_of(r), r.get("reading_at"),
                 r.get("reading_url"), r.get("reading_note")),
                f"claim {kind} {sid}")
    counts["claim"] = db.execute("SELECT count(*) FROM claim").fetchone()[0]

    # ── the two tables the schema declared and nothing ever wrote ───────────────────────────────
    #
    # WHY THEY WERE EMPTY, established 2026-08-13 rather than assumed. `schema.sql` and this loader
    # arrived in one commit, the loader was written for the identity spine, and nothing came back
    # for the rest. So `edition` and `work_publisher` carried columns, constraints and an index and
    # held no rows, which is a schema asserting something nothing had ever tested against data.
    # STORE-PLAN §2.

    # WORK TO PUBLISHER, read off `publishers.json`'s own `works` list, which IS the edge. Going by
    # way of the print blocks would have rebuilt a join the publisher pass has already made.
    imprint_id = {(pub, nm): i for i, pub, nm in
                  db.execute("SELECT id, publisher, name FROM imprint")}
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
                (wid, pid, imprint_id.get((pid, imp))), f"work_publisher {wid}->{pid}")
    counts["work_publisher"] = db.execute("SELECT count(*) FROM work_publisher").fetchone()[0]

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
            # WHAT KIND OF EVENT THE DATE IS, which the schema asks for and the corpus states in
            # which field carries it: a printing is dated by a catalogue, a delivery by a shop.
            if v.get("published"):
                kind, dated = "printing", v["published"]
            elif v.get("delivered"):
                kind, dated = "shop-delivery", v["delivered"]
            else:
                kind, dated = "printing", None
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
            # A PLAIN INSERT, DELIBERATELY. `OR IGNORE` here swallowed 382 volumes on the first
            # run and reported `refused 0`, because SQLite treats the conflict as handled and
            # raises nothing for `put` to catch. A constraint that quietly drops a row is worse
            # than no constraint: it looks like coverage. STORE-PLAN §1a is about exactly this.
            put("INSERT INTO edition (work, isbn, volume, dated, kind, cite)"
                " VALUES (?,?,?,?,?,?)",
                (wid, v.get("isbn"), v.get("number_n"), dated, kind, cite),
                f"edition {wid} {v.get('isbn') or v.get('number') or '?'}")
    counts["edition"] = db.execute("SELECT count(*) FROM edition").fetchone()[0]

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
        db = sqlite3.connect(DB)
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
        for what, why in refused[:6]:
            print(f"      {what}: {why}")
    if a.ask:
        db = sqlite3.connect(DB)
        for q, n in ask(db).items():
            print(f"  {n:7}  {q}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
