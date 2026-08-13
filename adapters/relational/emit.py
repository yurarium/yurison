#!/usr/bin/env python3
"""The corpus files, written FROM the store rather than beside it. STORE-PLAN §6.

WHAT THIS SECTION IS FOR. §1 to §5k moved the data INTO the store and measured how much of what a
reader is served could be answered from it. That measure asks whether a fact is DERIVABLE and cannot
ask whether it is actually derived, because the emitter still read the JSON. This is where the
direction reverses: a file listed here is built out of tables, the code that built it from memory is
deleted, and the two can no longer disagree because there is only one of them.

PER DOMAIN, AND NEVER AS A CUTOVER. A domain moves when the store holds all of it, which is why the
order here is the order the modelling finished in rather than the order the files are written. A
half-migrated domain, where the store holds it and the JSON is still written directly, is two
producers of one fact and is worse than not having started.

THE PROOF IS BYTE EQUALITY, and it is what `test_emit.py` asserts. An emitter that produces
something ALMOST the same is a second producer with a bug, so the test compares the emitted text
against what `build.py` wrote and refuses a difference of any kind. That is available only while
both exist, which is exactly the window a per-domain migration gives.

WHAT THE STORE DOES NOT HOLD AND THIS SUPPLIES. The date the run happened and the prose note at the
head of each file. Neither is a fact about a work: the first describes the run, which `served.CORPUS`
already excludes from the measure, and the second is documentation addressed to whoever opens the
file. They are arguments here rather than columns.
"""
import json


#: The sentence at the head of `credits.json`, addressed to a reader of the file. It is not data
#: about a credit, so it is not in the store; it is what this file is for, so it is here.
CREDITS_NOTE = ("One record per credit, with the works it is named on and the role on each edge. "
                "Addresses are opaque and minted: a credit read three ways in a day would have "
                "broken a name-shaped one twice. Fetched only when a credit page is opened.")


def credits(db, generated):
    """`credits.json`, from `credit`, `work_credit`, `credit_spelling`, `identity_ruling`.

    THE ORDER IS THE STORE'S AND HAS TO BE STATED. A dict comes out in insertion order and the file
    is compared byte for byte, so every query here is ordered explicitly rather than relying on
    whatever a table scan happens to return.

    A WORK NOBODY HOLDS IS NOT ON A PERSON'S PAGE. The edge table's foreign key already refuses one,
    which is the same rule `credit_page_data` applied by filtering against the shipped rows, and it
    is the reason that filter can go: the store cannot hold the edge in the first place.
    """
    roles = {}
    for work, credit, role in db.execute(
            "SELECT work, credit, role FROM work_credit ORDER BY credit, work, role"):
        roles.setdefault((credit, work), []).append(role)

    spellings = {}
    for spelling, credit in db.execute(
            "SELECT spelling, credit FROM credit_spelling ORDER BY credit, spelling"):
        spellings.setdefault(credit, []).append(spelling)

    # A HOMOPHONE IS THE OTHER SIDE OF A RULING, so it is read off the ruling and its surfaces
    # rather than stored per credit. `identity_ruling_surface` holds the spellings that were
    # weighed and `credit_spelling` resolves each to the credit it reaches.
    homophones = {}
    for reading, basis, spelling, credit, surface in db.execute(
            "SELECT r.reading, r.basis, s.spelling, c.credit, cr.surface"
            " FROM identity_ruling r"
            " JOIN identity_ruling_surface s ON s.ruling = r.id"
            " LEFT JOIN credit_spelling c ON c.spelling = s.spelling"
            " LEFT JOIN credit cr ON cr.id = c.credit"
            " WHERE r.kind = 'homophone' ORDER BY r.id, s.spelling"):
        homophones.setdefault(reading, []).append((credit, surface, basis))

    out = {}
    for cid, surface, shape, registered in db.execute(
            "SELECT id, surface, kind, registered FROM credit ORDER BY id"):
        works = []
        for (credit, work) in sorted((k for k in roles if k[0] == cid), key=lambda k: k[1]):
            named = [r for r in roles[(credit, work)] if r]
            works.append({"id": work, **({"roles": named} if named else {})})
        fact = {"credit": surface, "shape": shape, "works": works}
        if spellings.get(cid):
            fact["spellings"] = spellings[cid]
        if registered:
            fact["kind"] = registered
        for reading, pairs in homophones.items():
            mine = [p for p in pairs if p[0] == cid]
            if not mine:
                continue
            others = [{"id": c, "credit": s, "reading": reading, "basis": b}
                      for c, s, b in pairs if c and c != cid]
            if others:
                fact.setdefault("homophones", []).extend(others)
        out[cid] = fact

    return {"generated": generated, "note": CREDITS_NOTE, "count": len(out), "credits": out,
            # A CHAIN IS NOT FOLLOWED HERE, which `credit_page_data` said and the store now makes
            # structural: `superseded` stores the LIVE survivor because §5d had to resolve a
            # two-hop chain before a foreign key would accept it, so what ships is already resolved.
            "merged": {i: c for i, c in db.execute(
                "SELECT id, credit FROM superseded WHERE credit IS NOT NULL ORDER BY id")}}


#: The sentence at the head of `publishers.json`.
PUBLISHERS_NOTE = ("One record per publishing house, holding the imprint lines it runs with the "
                   "spellings each line is catalogued under and the years those cover. Publishers "
                   "and distributors share one namespace: the seat is on the edge to the book.")


def publishers(db, generated):
    """`publishers.json`, from `publisher`, `imprint`, `print_row` and `print_party`.

    NO JUDGEMENT IS LEFT IN HERE AND THAT IS THE POINT. Which house a catalogued spelling names and
    which line an imprint string names were both decided by the compiler and written onto
    `print_party`, so this counts rows and spans years and decides nothing. An emitter that resolved
    a spelling for itself would be the second implementation §3 refuses, and it would be the one
    that disagrees, because the registry is where the rulings live.

    A ROW IS A PARTY AND A WORK IS A WORK. A house's `rows` counts the seats it holds on print rows
    and its `works` counts the works behind them, which is why a work with two editions under one
    line contributes two rows and one work.

    A SPELLING NO LINE ANSWERS FOR IS SHOWN AS ITSELF. `imprint` is NULL on those parties, and the
    file keys them by the spelling with `resolved: false`, because a page hiding them would report a
    house as having fewer lines than its books say it has.
    """
    # THE ORDER IS THE ROWS' AND NOT THE TABLE'S. A house appears in this file when its first print
    # row does, so iterating `publisher` by id would reorder every house and every works list.
    house = {}
    name_of = {i: n for i, n in db.execute("SELECT id, name FROM publisher")}

    line_name = {i: (n, p) for i, p, n in db.execute("SELECT id, publisher, name FROM imprint")}
    line_parent = {i: p for i, p in db.execute("SELECT id, parent_name FROM imprint")}

    for hid, seat, wid, imp, imp_raw, first, last in db.execute(
            "SELECT p.publisher, p.seat, r.work, p.imprint, p.imprint_raw, p.first, p.last"
            " FROM print_party p JOIN print_row r ON r.id = p.print_row"
            " ORDER BY p.id"):
        if hid is None:
            continue
        fact = house.setdefault(hid, {"id": hid, "name": name_of.get(hid), "rows": 0,
                                      "works": [], "seats": [], "lines": {}})
        fact["rows"] += 1
        if seat not in fact["seats"]:
            fact["seats"].append(seat)
        if wid and wid not in fact["works"]:
            fact["works"].append(wid)
        # THE LINE BELONGS TO THE PUBLISHER'S SEAT. A house that only shipped the book did not put
        # its own line on it.
        if seat != "publisher" or not imp_raw:
            continue
        key = str(imp) if imp else f"?{imp_raw}"
        slot = fact["lines"].setdefault(key, {
            "id": None, "name": imp_raw, "parent": None, "resolved": False,
            "rows": 0, "works": [], "spellings": {}})
        if imp:
            nm, _pub = line_name[imp]
            slot.update({"id": _slug(db, imp), "name": nm, "resolved": True,
                         "parent": line_parent.get(imp)})
        slot["rows"] += 1
        if wid and wid not in slot["works"]:
            slot["works"].append(wid)
        spell = slot["spellings"].setdefault(imp_raw, {"raw": imp_raw, "rows": 0,
                                                       "years": [None, None]})
        spell["rows"] += 1
        _span(spell["years"], first, last)

    out = {}
    for hid, fact in house.items():
        fact["lines"] = sorted(fact["lines"].values(), key=lambda x: (-x["rows"], x["name"]))
        for line in fact["lines"]:
            line["spellings"] = sorted(line["spellings"].values(), key=lambda x: -x["rows"])
        out[hid] = fact
    return {"generated": generated, "note": PUBLISHERS_NOTE, "count": len(out), "publishers": out,
            "merged": {i: w for i, w in db.execute(
                "SELECT id, publisher FROM superseded WHERE publisher IS NOT NULL ORDER BY id")}}


def credit_keys(db):
    """`feed/credit-keys.json`, which IS `credit_spelling` and nothing else.

    45 KB AGAINST `credits.json`'s 457, and that is the reason it exists as its own file: a search
    needs a spelling and an identifier, and the works hang off `ci` on rows the page already holds.
    So it never fetches the credit records to answer a question about a person.

    THE ORDER IS THE REGISTRY'S, which is the order the rows were written in. A search does not care
    and a byte comparison does.
    """
    return {s: c for s, c in db.execute("SELECT spelling, credit FROM credit_spelling ORDER BY id")}


def index(db):
    """`index.json`, the search list: one row per WORK, holding every record's address.

    THE COLLAPSE IS ARITHMETIC AND THE IDENTITY IS THE STORE'S. `one_row_per_work` read the registry
    to decide which records are one work, and `record.work` already carries that answer, so nothing
    here re-decides it. What is left is the rules that follow from it, each of which the compiler
    argued for and none of which is a judgement about identity.

      THE NAME IS THE FIRST RECORD'S BY IDENTIFIER, which prefers a C-number's bare title to a
      `madb-t-` record's ISBD line, so `School zone = スクールゾーン` never reaches the list.

      THE LENGTH IS THE DISTINCT VOLUME NUMBERS THE RECORDS STATE, not their sum and not the
      larger. MADB holds ゆるゆり as 21 volumes and as 11, overlapping, so adding them reports a
      work as twice its length; スクールゾーン is 1 to 3 in one record and 4 and 5 in the other, so
      the larger is 3 where the run is 5. And every volume has to state a number, or the union is
      counting a subset and would report a work as shorter than one of its own records says.

      THE DATE IS THE EARLIEST ANY RECORD STATES.

    A RECORD WITH NO IDENTITY STAYS ITS OWN ROW, which cannot arise here: the store cannot hold a
    record whose work is not a work, so the case the compiler guarded against is unstateable.
    """
    numbers, per_record = {}, {}
    for rec, raw in db.execute(
            "SELECT record, number_raw FROM volume ORDER BY record, seq"):
        per_record.setdefault(rec, []).append(raw or "")

    rows, at = [], {}
    for rid, work, title, yomi, creator, n, label, tier, group in db.execute(
            "SELECT id, work, title, yomi, creator, volume_count, marketing_label,"
            " content_tier, grouping FROM record ORDER BY rowid"):
        # `none` AND `""` ARE THIS FILE'S SPELLING OF AN ABSENCE, which is a format decision and not
        # a fact. §5i took the word `none` out of `work_presentation` because a word standing for
        # absence makes `label IS NOT NULL` lie; the file has always written it, so the emitter
        # writes it back, the same way a record with no reading ships an empty `y`.
        row = {"id": rid, "t": title, "y": yomi or "", "c": creator or "", "n": n,
               "d": _origin_date(db, rid), "l": label or "none", "ct": tier, "g": group}
        if work not in at:
            row["ids"] = [rid]
            at[work] = row
            numbers[work] = list(per_record.get(rid) or [])
            rows.append(row)
            continue
        kept = at[work]
        kept["ids"].append(rid)
        numbers[work] += list(per_record.get(rid) or [])
        kept["n"] = max(kept.get("n") or 0, n or 0)
        if row["d"] and (not kept.get("d") or row["d"] < kept["d"]):
            kept["d"] = row["d"]
    for work, row in at.items():
        vols = numbers.get(work) or []
        if len(row["ids"]) > 1 and vols and all(vols):
            row["n"] = max(row["n"] or 0, len(set(vols)))

    # THE CREDITS EACH ROW RESOLVES TO, so a search reaches a person by any spelling the registry
    # unifies rather than only by the characters this row carries. The raw field stays in `c`: where
    # a credit resolves to nothing it is still searched, so the join strictly gains matches.
    #
    # IN THE BYLINE'S ORDER AND NOT THE REGISTRY'S. The field names its people in an order somebody
    # chose, and `credit_part` holds that division with its sequence; taking `work_credit` in row
    # order instead reordered 217 of these lists into whatever order the identifiers were minted in.
    named = {}
    for record, credit in db.execute(
            "SELECT record, credit FROM record_credit ORDER BY record, seq"):
        named.setdefault(record, []).append(credit)
    for row in rows:
        if named.get(row["id"]):
            row["ci"] = named[row["id"]]
    return rows


def _origin_date(db, record):
    """The date the record states, or NULL where it states none and `""` where it states nothing.

    THE TWO ABSENCES ARE DIFFERENT AND THE FILE KEEPS THEM APART. A record with a first-publication
    block naming no date ships `null`; one with no block at all ships `""`, because the compiler
    reads `first_publication` and then `.get("date", "")` off whatever it found.
    """
    got = db.execute("SELECT dated FROM work_origin WHERE record = ?", (record,)).fetchone()
    return got[0] if got else ""


def _slug(db, imprint_id):
    got = db.execute("SELECT slug FROM imprint WHERE id = ?", (imprint_id,)).fetchone()
    return got[0] if got else None


def _span(years, first, last):
    """Extend a `[from, to]` pair by a row's own dates, as `facts/imprint` measures a span."""
    for value in (first, last):
        if not value:
            continue
        y = str(value)[:4]
        if not years[0] or y < years[0]:
            years[0] = y
        if not years[1] or y > years[1]:
            years[1] = y


def as_text(payload):
    """The file as `build.py` writes one, so a comparison is of bytes and not of parsed objects."""
    return json.dumps(payload, ensure_ascii=False, indent=1)


def as_compact(payload):
    """The same, for the files written without indentation because a browser loads them on sight."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
