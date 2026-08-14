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
    # §5a. THE TABLE WAS READ BY NOTHING, which is what made it decoration rather than a ruling.
    # A composite key on `claim` is where this ends up, and it may not go on while 105 rows would be
    # refused. 102 of them are English romanisations citing a community database, which is the
    # owner's ruling of 2026-08-09 that Wikidata may raise the floor on a romanisation meeting a
    # table written before it. The constraint is adopted when this reaches 0.
    #
    # TWO EXEMPTIONS, AND EACH IS A TABLE LOOKUP RATHER THAN A VOCABULARY WRITTEN INTO SQL. A basis
    # with no admitted kind at all has not been ruled on, and counting it would report a gap in the
    # vocabulary as a defect in the data; `back-converted` is in `division.BASES`, has no reading
    # attribution row, and 22 readings rest on it. A self-sourced claim owes no document because the
    # evidence is the name, and `_kind_of` says `derived` for it, which is true and loses the reason;
    # 327 claims are in that state and every one is a name already written in its own script.
    #
    # WITH BOTH, THIS AND `provenance.unadmitted` ANSWER 105 OVER THE SAME CORPUS BY DIFFERENT
    # ROUTES, one over the store and one over `data/names`. §14b: neither shares the other's blind
    # spot, and the weekly rebuild is where a divergence would show.
    "claims whose evidence their basis does not admit": {
        "sql": "SELECT count(*) FROM claim c WHERE c.source_kind IS NOT NULL "
               "AND c.source NOT IN (SELECT source FROM self_sourced) "
               "AND EXISTS (SELECT 1 FROM basis_admits_kind a WHERE a.basis = c.basis "
               "AND a.predicate = c.predicate) AND NOT EXISTS "
               "(SELECT 1 FROM basis_admits_kind a WHERE a.basis = c.basis "
               "AND a.predicate = c.predicate AND a.source_kind = c.source_kind)",
        "reads": ("claim", "basis_admits_kind", "self_sourced")},
    # A CYCLE IS THE ONE THING A CHECK CANNOT SAY. `alias_of <> id` stops a name pointing at itself
    # and nothing in SQL stops two pointing at each other, so this is the owner's "support querying
    # to verify logical constraints that cannot be so expressed", written out.
    # §5b MOVED THE ISBN AND THE DATE INTO SEPARATE TABLES, so `CHECK (isbn IS NULL OR dated IS NOT
    # NULL)` had nowhere to live: no CHECK reaches across two tables. `check.py` has held this at 0
    # since §3 and the store now asks it too, which is a weaker guarantee stated rather than lost.
    "volumes with an isbn and no date": {
        "sql": "SELECT count(*) FROM volume v WHERE EXISTS "
               "(SELECT 1 FROM volume_isbn i WHERE i.volume = v.id) AND NOT EXISTS "
               "(SELECT 1 FROM edition e WHERE e.volume = v.id AND e.dated IS NOT NULL)",
        "reads": ("volume", "volume_isbn", "edition")},
    # A BOOK CANNOT BE PRINTED AFTER THE SHOP DELIVERED IT, and holding both events is what made the
    # question askable at all. Reported rather than refused, because a delivery preceding a printing
    # is a real thing on this corpus and the pair is worth watching rather than blocking.
    "books a shop delivered before they were printed": {
        "sql": "SELECT count(*) FROM edition p JOIN edition d ON d.volume = p.volume "
               "WHERE p.kind = 'printing' AND d.kind = 'shop-delivery' "
               "AND p.dated IS NOT NULL AND d.dated IS NOT NULL AND d.dated < p.dated",
        "reads": ("edition",)},
    # `aliases pointing in a circle` WAS HERE AND IS GONE, which is the better end for a standing
    # question. It caught two-node cycles alone, and §5f made a cycle of any length unstateable by
    # forbidding a retired surface to point at another retired one. A question whose answer can no
    # longer be anything but 0 is the control §13 objects to.
    "names nothing in the corpus is identified by": {
        "sql": "SELECT count(*) FROM surface s WHERE s.kind IN ('title', 'author', 'publisher') "
               "AND NOT EXISTS (SELECT 1 FROM names n WHERE n.surface = s.id)",
        "reads": ("surface", "names")},
    # §5d. A FOLD NAMING TWO THINGS IS DATA AND NOT A FAULT, and a column could hold only the first.
    "names that name more than one thing": {
        "sql": "SELECT count(*) FROM (SELECT surface FROM names GROUP BY surface HAVING count(*) > 1)",
        "reads": ("names",)},
    # A RULING THAT TWO IDENTIFIERS ARE NOT ONE, which is what stops a later pass merging them
    # again. `delta.KINDS` names `merge` and `divide` and nothing recorded the decisions until now.
    # §5c. `verified` SITS ON THE NAME AND THE CLAIMS DISAGREE, which was unanswerable while nothing
    # said which of two rows a record stands behind. It counts the live claims alone now.
    "names two sources disagree about, live claims only": {
        "sql": "SELECT count(*) FROM (SELECT surface FROM claim WHERE displaced = 0 "
               "GROUP BY surface, predicate HAVING count(DISTINCT value) > 1)",
        "reads": ("claim",)},
    # A DATE CITED TO SOMETHING THAT IS NOT A PAGE. `CHECK (dated IS NULL OR cite IS NOT NULL)`
    # asks whether a citation exists and cannot ask what it is, so 915 rows cite the literal string
    # `ndl`. A CHECK on the shape would refuse them, and they are the corpus as it stands.
    "dates cited to something that is not a page": {
        "sql": "SELECT count(*) FROM edition WHERE dated IS NOT NULL AND cite IS NOT NULL "
               "AND cite NOT LIKE 'http%' AND cite NOT LIKE 'madb:%' AND cite NOT LIKE 'openbd:%'",
        "reads": ("edition",)},
    # 833 of 2,661, down from 906 once the print block's spelling is folded onto the registry's.
    # What is left is a line the registry does not carry, which is data rather than a join.
    "works on a house with no line named": {
        "sql": "SELECT count(*) FROM work_publisher WHERE imprint IS NULL",
        "reads": ("work_publisher",)},
    # §1a. WHAT THE COMPILER COULD NOT ADMIT. A quarantine that grows every day means the schema is
    # asserting something the data does not support, and the honest response then is to change the
    # model rather than to keep filtering. This is what tells that from a bad week of captures.
    "rows the store could not admit": {
        "sql": "SELECT count(*) FROM quarantine",
        "reads": ("quarantine",)},
    "identities somebody ruled apart": {
        "sql": "SELECT count(*) FROM identity_ruling WHERE kind IN ('keep', 'homophone')",
        "reads": ("identity_ruling",)},
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
    # A ROW THAT IS ALL KEY AND NO VALUE still exists or does not, and `SELECT  FROM` is a syntax
    # error. `print_row_record` is one: both its columns are the key, so the only thing a write can
    # say about it is whether the row is there.
    got = db.execute(f"SELECT {', '.join(values) if values else '1'} FROM {table} WHERE {where}",
                     tuple(key.values())).fetchone()
    if got is not None and (not values or list(got) == list(values.values())):
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


def reconcile(db, table, key_columns, rows, value_columns=None, addresses=()):
    """Bring one table to exactly `rows`, through `write` and `drop`. Returns what changed.

    THE PRODUCTION CALLER §7 WAS MISSING. `write` and `drop` have existed since the store did and
    nothing outside their own tests ever called one, which means the incremental path was a design
    with no exercise: the argument for it is that an idempotent write plus a pure derivation
    converges on the same fixed point a rebuild does, and an argument nothing runs is a hypothesis.

    WHY A WHOLE TABLE RATHER THAN A DIFF THE CAPTURE HANDS OVER. A capture knows what it saw and
    does not know what has GONE, and the delta kind these systems get wrong is deletion: an output
    whose input disappeared has nothing left to notice it. Handed the rows that should be there,
    this can see both, and the write that produces the value already present returns False and
    cascades nothing, which is the whole trick.

    `rows` is an iterable of column-to-value mappings, each holding the key columns and the values.
    Returns `(written, dropped, unchanged)`.
    """
    # A ROW'S ADDRESS IS NEVER WRITTEN, whatever the caller worked out. `claim.id` is handed out by
    # the insert that made the row, so carrying one across from another compile inserts a row under
    # a number something else already has; the first unattended run to meet new claims died on
    # exactly that, `UNIQUE constraint failed: claim.id`, and the caller's key was right. Stripping
    # it here makes the class unstateable rather than making one caller careful.
    addresses = set(addresses or ())
    key_columns = [c for c in key_columns if c not in addresses]
    value_columns = list(value_columns or ())
    if not value_columns:
        # INFERRED FROM A ROW WHERE THE CALLER SAID NOTHING, which is the convenience that put the
        # address back. `claim` is the one table whose natural key is every column it has but its
        # rowid, so it is the only caller that reaches this line, and it reached it with `id` in
        # the row: stripping addresses BEFORE the inference stripped a list that was then rebuilt
        # from the row itself. It cost a night's run and did not show until a claim was NEW, since
        # a row that already matches is never inserted.
        for row in rows:
            value_columns = [c for c in row if c not in key_columns]
            break
    value_columns = [c for c in value_columns if c not in addresses]
    want = {}
    for row in rows:
        want[tuple(row.get(c) for c in key_columns)] = row
    held = {tuple(r) for r in db.execute(
        f"SELECT {', '.join(key_columns)} FROM {table}").fetchall()}

    written = unchanged = 0
    for k, row in want.items():
        if write(db, table, {c: row.get(c) for c in key_columns},
                 {c: row.get(c) for c in value_columns}):
            written += 1
        else:
            unchanged += 1
    dropped = 0
    for k in held - set(want):
        if drop(db, table, dict(zip(key_columns, k))):
            dropped += 1
    return written, dropped, unchanged
