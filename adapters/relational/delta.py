#!/usr/bin/env python3
"""Apply a change to the store without recompiling it, and follow only what actually moved.

WHY THIS EXISTS. Compiling the whole store from `data/build` takes a rebuild. Most of what arrives
is one capture: a work gains an edition, a credit gains a reading, two credits turn out to be one
person. Recompiling everything to record that is the shape the rest of this plan is about.

THE WHOLE DESIGN IS ONE SENTENCE: the cascade is gated on OUTPUT change and never on input change.
A write that produces the value already there is a no-op and cascades nothing. A derivation is a
pure function of the store, recomputed as freely as SQL allows, and downstream work happens only
where a digest moved.

MEASURED, BECAUSE THE FIRST VERSION OF THE PLAN GUESSED THE OTHER WAY. Scanning every credit
surface is 1.2 ms, grouping every credit by its works 4.1 ms, grouping all 4,989 claims 2.4 ms. The
expensive thing was never the reduction. It is rewriting a class of rows, and that happens only
when the answers move, which in the common case is few of them or none. So a reduction over
everything is fine; assuming its output changed is not.

CONVERGENCE IS THE CORRECTNESS ARGUMENT, and it is why this needs no comparison against a rebuild.
Recompute what a delta touches, follow the digests that moved, stop when nothing moves. A pure
derivation plus an idempotent write means the fixed point a delta converges to is the fixed point a
rebuild produces, so equivalence is a property of the construction. Most deltas settle in one pass.

WHAT THIS DOES NOT PROVE, and it is the reason for the weekly rebuild in CI. Every focused test
here is written against the same `reads` declarations the updater uses, so a wrong declaration
satisfies both. A whole rebuild set beside a store that has only ever been updated shares nothing
with those declarations, which is the §14b requirement.
"""
import hashlib
import json

#: How a delta can change the store. Deletion and retraction are the interesting ones: an output
#: whose input disappeared has nothing left to notice it, and a digest never recomputed never moves.
KINDS = ("insert", "update", "delete", "merge", "divide", "retract")

#: What each derivation is, and which tables it reads. `reads` is a declaration and the one thing
#: here that can be wrong without any test noticing, which is what the weekly rebuild is for.
DERIVATIONS = {
    "claims resting on a community database": {
        "sql": "SELECT count(*) FROM claim WHERE source_kind = 'community-db'",
        "reads": ("claim",)},
    "claims we would lose if NDL were withdrawn": {
        "sql": "SELECT count(*) FROM claim WHERE source_kind = 'national-library'",
        "reads": ("claim",)},
    "works naming nobody": {
        "sql": "SELECT count(*) FROM work w LEFT JOIN work_credit e ON e.work = w.id "
               "WHERE e.work IS NULL",
        "reads": ("work", "work_credit")},
    "names two sources disagree about": {
        "sql": "SELECT count(*) FROM (SELECT surface FROM claim "
               "GROUP BY surface, predicate HAVING count(DISTINCT value) > 1)",
        "reads": ("claim",)},
    "names nothing in the corpus is identified by": {
        "sql": "SELECT count(*) FROM surface WHERE kind IN ('title', 'author', 'publisher') "
               "AND work IS NULL AND credit IS NULL AND publisher IS NULL",
        "reads": ("surface",)},
    "credits named by more than one work": {
        "sql": "SELECT count(*) FROM (SELECT credit FROM work_credit GROUP BY credit "
               "HAVING count(*) > 1)",
        "reads": ("work_credit",)},
}


def ensure(db):
    """The table a derivation's last answer lives in. Created here so an older store gains it."""
    db.execute("CREATE TABLE IF NOT EXISTS derivation ("
               " name TEXT PRIMARY KEY,"
               " digest TEXT NOT NULL,"
               " value TEXT NOT NULL)")
    return db


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def write(db, table, key, values):
    """Write a row and say whether anything actually changed. An idempotent write is the whole trick.

    `key` is the column-to-value mapping that identifies the row, `values` what it should hold. A
    write producing what is already there returns False, and a False here is what stops the cascade.
    """
    where = " AND ".join(f"{c} IS ?" for c in key)
    got = db.execute(f"SELECT {', '.join(values)} FROM {table} WHERE {where}",
                     tuple(key.values())).fetchone()
    if got is not None and list(got) == list(values.values()):
        return False
    if got is None:
        cols = list(key) + [c for c in values if c not in key]
        row = [key[c] if c in key else values[c] for c in cols]
        db.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES "
                   f"({', '.join('?' * len(cols))})", row)
        return True
    db.execute(f"UPDATE {table} SET {', '.join(f'{c} = ?' for c in values)} WHERE {where}",
               tuple(values.values()) + tuple(key.values()))
    return True


def drop(db, table, key):
    """Delete a row and say whether one was there. The delta kind these systems get wrong."""
    where = " AND ".join(f"{c} IS ?" for c in key)
    cur = db.execute(f"DELETE FROM {table} WHERE {where}", tuple(key.values()))
    return cur.rowcount > 0


def recompute(db, names=None, derivations=None):
    """Recompute derivations and return the names whose ANSWER moved, not whose input did."""
    ensure(db)
    reg = derivations if derivations is not None else DERIVATIONS
    moved = []
    for name in (names if names is not None else list(reg)):
        spec = reg.get(name)
        if not spec:
            continue
        value = [list(r) for r in db.execute(spec["sql"]).fetchall()]
        d = _digest(value)
        was = db.execute("SELECT digest FROM derivation WHERE name = ?", (name,)).fetchone()
        if was and was[0] == d:
            continue
        db.execute("INSERT INTO derivation (name, digest, value) VALUES (?,?,?) "
                   "ON CONFLICT(name) DO UPDATE SET digest = excluded.digest, "
                   "value = excluded.value", (name, d, json.dumps(value, ensure_ascii=False)))
        moved.append(name)
    return moved


def dependents(names, derivations=None):
    """Which derivations read what these ones produce. Empty today, and the loop needs it anyway."""
    reg = derivations if derivations is not None else DERIVATIONS
    out = set()
    for name, spec in reg.items():
        if name in names:
            continue
        if set(spec.get("depends_on") or ()) & set(names):
            out.add(name)
    return sorted(out)


def converge(db, touched, derivations=None, limit=16):
    """Follow the digests that moved until nothing moves. Returns `(moved, passes)`.

    `touched` is the set of TABLES a delta wrote. Everything reading one of them is recomputed,
    which is milliseconds, and only a derivation whose answer changed sends the loop round again.
    """
    reg = derivations if derivations is not None else DERIVATIONS
    first = [n for n, s in reg.items() if set(s.get("reads") or ()) & set(touched)]
    moved, passes, wave = [], 0, first
    while wave and passes < limit:
        passes += 1
        got = recompute(db, wave, reg)
        moved += [n for n in got if n not in moved]
        wave = dependents(got, reg)
    if passes >= limit:
        raise RuntimeError(f"derivations did not settle in {limit} passes; last wave {wave}")
    return moved, passes


def value(db, name):
    """The last answer recorded for a derivation, or None if it has never been computed."""
    got = db.execute("SELECT value FROM derivation WHERE name = ?", (name,)).fetchone()
    return json.loads(got[0]) if got else None
