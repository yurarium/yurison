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


def as_text(payload):
    """The file as `build.py` writes one, so a comparison is of bytes and not of parsed objects."""
    return json.dumps(payload, ensure_ascii=False, indent=1)
