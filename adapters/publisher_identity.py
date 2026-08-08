#!/usr/bin/env python3
"""Stable identifiers for the houses this corpus names, and what each one's page is built from.

WHY THIS EXISTS, AND WHY IT IS A SECOND MODULE RATHER THAN A BRANCH IN THE FIRST. A credit is a
string somebody wrote in an author field and has to be found by splitting it. A publisher is a
field of its own, already normalised by `names.publishers.publisher_of`, and it comes with an
imprint beside it that `names.imprints` has already resolved to a line. The two share
`adapters/identity.py`, which is where the minting, the merging and the retirement live; they
share nothing else, and folding them together would mean one module holding two populations'
worth of reasoning about what counts as the same thing.

WHAT AN IDENTIFIER PROMISES is what it promises for a work and for a credit: that it never moves
and never disappears. Assignment is append-only, lives in `data/identity/publishers.yaml`, and a
house whose two spellings turn out to be one house does not lose an id. The retired one gains
`merged_into`, still resolves, and lends its anchors to the survivor.

WHY OPAQUE. The same reason as everywhere else, and the publisher side has its own version of it:
角川書店 became KADOKAWA and the older records were not rewritten, so a name-shaped address minted
in 2013 would be wrong now and could not be corrected without breaking every link to it. 華葉 was
read ハナハ, then カヨウ, then カバ inside one day on the author side. A name survives neither a
renaming nor a merge.

PUBLISHERS AND DISTRIBUTORS ARE ONE NAMESPACE, which is the project owner's ruling of 2026-08-08.
講談社 handling 発売 for 一迅社 is the same company in a different seat, so the role belongs on the
edge between the house and the book and not in a second registry. `names.publishers.NAME_FIELDS`
already normalises `distributor` with the same function, which is the shape the ruling confirms.
The corpus holds 164 houses under this rule and exactly one distributor name, 講談社, which is also
a publisher, so the ruling costs one identifier and saves a duplicate page.

AN IMPRINT IS THE HOUSE'S OWN AND GETS NO IDENTIFIER HERE. `data/names/imprints.yaml` already
gives each line a curated id, and a line belongs to the house that runs it, so it is content on a
publisher page. That is DEFINITIONS' own shape, where a line is the publisher's and the publisher
answers for it.

WHAT A PAGE IS BUILT FROM, and why the assembly is here. `houses()` produces, per identifier, the
lines that house runs with the rows and the years each spelling covers, and the works this database
holds from it. Both the pre-rendered page and the interface read that one structure, so neither can
disagree with the other about which imprint a book is under, and `imprints.census` stays the only
thing that decides which line a string names.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "names"))

import identity                                                             # noqa: E402
from names import imprints as _imprints                                     # noqa: E402
from names.publishers import publisher_of                                   # noqa: E402

PREFIX = "h"
ANCHOR = "publisher:"

# The directory a house's record lives under. `publisher` and not `house`, because that is the word
# the corpus, the interface and DEFINITIONS all use for the field; the identifier is opaque, so the
# word carries no claim beyond naming which registry answers for it.
ROOT = "publisher"

# WHICH SEAT THE HOUSE HELD ON THIS BOOK. One namespace, so the seat is a property of the pairing
# and travels on the edge, exactly as a credit's role does.
SEATS = ("publisher", "distributor")


def house_key(name):
    """The comparison key for a house, which is `publisher_of` and then the interface's own fold.

    ONE FOLD, SHARED WITH THE SHIPPED MAP. `feed/names.json` keys its publisher entries by the
    catalogued string and by that string NFKC-folded with spaces removed, so an anchor folded any
    other way would give a page an identifier the name map cannot answer for. That is the same trap
    `credit_identity.credit_key` is written against, and the same invariant catches it.
    """
    import unicodedata
    return unicodedata.normalize("NFKC", publisher_of(name) or "").replace(" ", "").strip()


def anchor(name):
    key = house_key(name)
    return f"{ANCHOR}{key}" if key else None


def population(rows):
    """`(wanted, edges)`: the houses to mint for, and which works each is named on in which seat.

    ORDERED BY FIRST APPEARANCE, so a re-run over unchanged data mints nothing and a growing corpus
    appends. `wanted` is in `identity.assign`'s shape so the minting is that function rather than a
    second one.

    A HOUSE IS MINTED FROM A PRINT ROW AND ONLY FROM A PRINT ROW. A web serialisation names a
    platform, and a platform is not a publisher: カドコミ is KADOKAWA's web arm and the field that
    says so is `platform`, which has its own vocabulary and its own English map. Minting here from
    a platform would put a second address on a company that already has one.
    """
    wanted, seen, edges = [], set(), {}
    for r in rows or ():
        wid = str(r.get("id")) if r.get("id") else None
        for pr in (r.get("print") or ()):
            for seat in SEATS:
                raw = str(pr.get(seat) or "").strip()
                a = anchor(raw)
                if not a:
                    continue
                if a not in seen:
                    seen.add(a)
                    wanted.append((a, [], publisher_of(raw)))
                if wid:
                    slot = edges.setdefault(a, [])
                    if (wid, seat) not in slot:
                        slot.append((wid, seat))
    return wanted, edges


def assign(entries, wanted):
    """Mint what is unminted, keeping every existing assignment.

    `relabel=False` for the reason a credit takes it: the label is the spelling the identifier was
    minted for, and a merge lends the retired spelling's anchor to the survivor, so following the
    rows would let a losing spelling become the survivor's own name.
    """
    return identity.assign(entries, wanted, PREFIX, relabel=False)


def houses(rows, lines, entries):
    """`{id: fact}` for every live house: its name, its lines, and the works we hold from it.

    THE ONE PRODUCER OF A PUBLISHER PAGE'S CONTENT. `imprints.census` decides which line a
    catalogued string names and measures the years each spelling covers; this groups that answer by
    house and hangs the works off it. The pre-rendered page and the interface both read what comes
    out, so the two cannot come to disagree about which line a book is under, and neither of them
    re-derives a span from the rows.

    WHAT A LINE'S ROW COUNT IS. Print rows, not works: a work carrying two editions under one line
    is two rows, which is what the census counts and what a reader looking at a shelf would count.
    The work list beside it is deduplicated, so the two numbers answer different questions and say
    so by being named differently.

    A HOUSE WITH ONE WORK STILL GETS AN ENTRY. The owner's ruling is that these are URL-holding
    objects minted for all of them, so a thin page answers the question of what to put on it, and
    withholding the address does not. 68 of the 164 houses here carry exactly one work.
    """
    live = identity.index(entries)
    by_line, _unresolved = _imprints.census(rows, lines)
    out = {}
    for r in rows or ():
        wid = str(r.get("id")) if r.get("id") else None
        for pr in (r.get("print") or ()):
            for seat in SEATS:
                raw = str(pr.get(seat) or "").strip()
                a = anchor(raw)
                hid = live.get(a) if a else None
                if not hid:
                    continue
                fact = out.setdefault(hid, {"id": hid, "name": publisher_of(raw), "rows": 0,
                                            "works": [], "seats": [], "lines": {}})
                fact["rows"] += 1
                if seat not in fact["seats"]:
                    fact["seats"].append(seat)
                if wid and wid not in fact["works"]:
                    fact["works"].append(wid)
                # The imprint belongs to the publisher's seat and not to the distributor's: a house
                # that only shipped the book did not put its own line on it.
                imp = str(pr.get("imprint") or "").strip()
                if seat != "publisher" or not imp:
                    continue
                line = _imprints.resolve(publisher_of(pr.get("publisher") or ""), imp,
                                         _imprints.index(lines))
                key = line["id"] if line else f"?{_imprints.fold(imp)}"
                slot = fact["lines"].setdefault(key, {
                    "id": line["id"] if line else None,
                    # A STRING NO LINE ANSWERS FOR IS SHOWN AS ITSELF, not dropped and not invented
                    # into a line. `imprint strings that reach no line` is the count of these, and
                    # a page that hid them would report a house as having fewer lines than its
                    # books say it has.
                    "name": (line or {}).get("name") or imp,
                    "parent": (line or {}).get("parent"),
                    "resolved": bool(line), "rows": 0, "works": [], "spellings": {}})
                slot["rows"] += 1
                if wid and wid not in slot["works"]:
                    slot["works"].append(wid)
                spell = slot["spellings"].setdefault(imp, {"raw": imp, "rows": 0, "years": [None, None]})
                spell["rows"] += 1
                _imprints._span(spell["years"], pr.get("first"), pr.get("last"))
    for fact in out.values():
        fact["lines"] = sorted(fact["lines"].values(), key=lambda x: (-x["rows"], x["name"]))
        for line in fact["lines"]:
            line["spellings"] = sorted(line["spellings"].values(), key=lambda x: -x["rows"])
    # `by_line` is asked for nothing here and is deliberately still computed: it is the census's own
    # answer, and calling it is what keeps this module from being a second reader of the registry.
    del by_line
    return out


def retired(entries):
    """{retired id: the id it became}, for the forwarders a merge has to leave behind."""
    return {str(e["id"]): str(e["merged_into"]) for e in entries or ()
            if e.get("merged_into") and e.get("id")}


def forwarders(entries, root=ROOT):
    """{path: html} for every retired house id, through `stubs` rather than a second renderer."""
    import stubs

    live = {str(e["id"]) for e in entries or () if e.get("id") and not e.get("merged_into")}
    return stubs.forwarders(root, live, retired(entries))


def load(path):
    """(entries, doc) from a publisher registry, or ([], {}) where there is none.

    `publisher` is the file's word for what `identity.assign` calls `title`, mapped here rather
    than in nine places, exactly as the credit registry maps `credit`.
    """
    import yaml

    f = pathlib.Path(path or "")
    if not f.exists():
        return [], {}
    doc = yaml.safe_load(f.read_text()) or {}
    entries = []
    for e in doc.get("publishers") or []:
        e = dict(e)
        e["title"] = e.pop("publisher", None)
        entries.append(e)
    return entries, doc


def save(path, entries, generated):
    """Write the registry whole. Append-only in content: nothing here drops an entry."""
    import json

    js = lambda v: json.dumps(v, ensure_ascii=False)                        # noqa: E731
    L = ["# Publisher identifiers. Append-only: an id is never reassigned and never withdrawn.",
         "#",
         "# ONE NAMESPACE FOR PUBLISHERS AND DISTRIBUTORS, ruled by the project owner 2026-08-08.",
         "# 講談社 handling 発売 for 一迅社 is the same company in a different seat, so the seat is",
         "# recorded on the edge to the book and never as a second company.",
         "#",
         "# An anchor is the name with its cataloguing removed and then folded the way",
         "# feed/names.json folds it, NFKC with spaces removed. A merged entry keeps `merged_into`,",
         "# stays resolvable, and lends its anchors to the survivor, because an address published",
         "# once has to keep working.",
         "#",
         "# See adapters/publisher_identity.py.",
         f"generated: {generated}", "publishers:"]
    for e in sorted(entries, key=lambda x: x.get("id") or ""):
        L.append(f"  - id: {e['id']}")
        L.append(f"    publisher: {js(e.get('title'))}")
        if e.get("merged_into"):
            L.append(f"    merged_into: {e['merged_into']}")
            L.append(f"    merge_basis: {js(e.get('merge_basis'))}")
        L.append("    anchors:")
        for x in e.get("anchors") or []:
            L.append(f"      - {js(x)}")
        if e.get("attached"):
            L.append("    attached:")
        for at in e.get("attached") or []:
            L.append(f"      - anchor: {js(at.get('anchor'))}")
            L.append(f"        basis: {js(at.get('basis'))}")
            L.append(f"        retrieved: {at.get('retrieved')}")
    L.append("")
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L))


def rows_from(build):
    import json

    return list(json.loads((pathlib.Path(build) / "series.json").read_text()).get("series") or [])


def main(argv=None):
    import argparse, collections, datetime                                  # noqa: E401

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--registry", default="data/identity/publishers.yaml")
    ap.add_argument("--imprints", default="data/names/imprints.yaml")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    today = datetime.date.today().isoformat()
    rows = rows_from(a.build)
    entries, _doc = load(a.registry)
    before = len(entries)
    wanted, edges = population(rows)
    entries, conflicts = assign(entries, wanted)

    lines = _imprints.load(pathlib.Path(a.imprints))
    facts = houses(rows, lines, entries)
    live = [e for e in entries if not e.get("merged_into")]
    one = sum(1 for f in facts.values() if len(f["works"]) == 1)
    ten = sum(1 for f in facts.values() if len(f["works"]) >= 10)
    unresolved = sum(1 for f in facts.values() for ln in f["lines"] if not ln["resolved"])
    seats = collections.Counter(s for f in facts.values() for s in f["seats"])
    print(f"{len(entries)} publisher identifier(s), {len(entries) - before} new; "
          f"{len(live)} live, {len(entries) - len(live)} retired into another")
    print(f"  {len(facts)} house(s) with a page to build: {one} holding one work, "
          f"{ten} holding ten or more; seats {dict(seats)}")
    print(f"  {sum(len(f['lines']) for f in facts.values())} line(s) across them, "
          f"{unresolved} of them a string no registry entry answers for")
    for c in conflicts:
        print(f"    CONTESTED {c['anchor']}: held by {c['held_by']}, claimed by {c['wanted_by']}")
    if a.dry_run:
        return 0
    save(a.registry, entries, today)
    print(f"  -> {a.registry} ({sum(len(v) for v in edges.values())} edge(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
