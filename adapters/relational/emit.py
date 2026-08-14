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
import pathlib
import re
import unicodedata
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))
from facts import division as _division                                 # noqa: E402
from facts import script as _script                                     # noqa: E402
from facts import serialisation as _ser                                 # noqa: E402
from names import provenance as _prov                                   # noqa: E402
from names import fold as _fold                                         # noqa: E402
from names import attach as _attach                                     # noqa: E402
from names import publishers as _pubmod                                 # noqa: E402
from facts import imprint as _impmod                                    # noqa: E402
from facts import namekey as _namekey                                   # noqa: E402
try:
    import pass4_analyser as _p4                                        # noqa: E402
except Exception:                                                       # noqa: BLE001
    _p4 = None


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


def works(db):
    """`works.json`, the RECORD layer: one catalogue record per row, with the volumes it lists.

    2,574 RECORDS AGAINST 3,038 WORKS, which is what makes this a different file from `series.json`
    rather than a longer one. Two records of one work each carry their own title as that catalogue
    wrote it, their own creator field, their own count and their own first publication.

    PARSED EQUALITY IS THE STANDARD HERE AND BYTE EQUALITY IS NOT, which is a weaker claim and is
    said out loud rather than discovered. The file has 11 distinct key orders on its records and 38
    on its volumes, and every one is an artefact of the order the compiler merged its sources: a
    volume that reached us from MADB first carries `madb_id` before `number`, one that reached us
    from a shop carries `number` before `delivered`. That is not a fact about a book, so asserting
    it would be asserting the merge order. What IS asserted is every key's PRESENCE and every
    value, which is the whole of what a reader is served.

    AN ABSENT KEY AND A NULL ARE DIFFERENT HERE, and the store says which by holding NULL: a record
    with no shop url has no `shop_url` key at all, while a first-publication block naming no date
    has `date: null`. The two are spelled apart in the file and are spelled apart here.
    """
    per_record = {}
    for (rec, number, number_n, designation, openbd, openbd_date, madb_id, isbn_source, cover,
         final, fsource, fprov, fvols, fret, vid) in db.execute(
            "SELECT record, number_raw, volume, designation, openbd, openbd_date, madb_id,"
            " isbn_source, cover_url, final_volume, final_source, final_provenance, final_volumes,"
            " final_retrieved, id FROM volume ORDER BY record, seq"):
        isbns = [i for i, in db.execute(
            "SELECT isbn FROM volume_isbn WHERE volume = ? ORDER BY seq", (vid,))]
        events = {k: (d, b, s, st) for k, d, b, s, st in db.execute(
            "SELECT kind, dated, dated_basis, source, basis_stated FROM edition WHERE volume = ?",
            (vid,))}
        vol = {}
        if madb_id:
            vol["madb_id"] = madb_id
        if number is not None:
            vol["number"] = number
        if designation is not None:
            vol["designation"] = designation
        if isbns:
            vol["isbn"] = isbns[0]
        printed = events.get("printing")
        if printed and printed[0] is not None:
            vol["published"] = printed[0]
        delivered = events.get("shop-delivery")
        if delivered and delivered[0] is not None:
            vol["delivered"] = delivered[0]
        if openbd is not None:
            vol["openbd"] = openbd
        if openbd_date is not None:
            vol["published_openbd"] = openbd_date
        if number_n is not None:
            vol["number_n"] = number_n
        if isbn_source is not None:
            vol["isbn_source"] = isbn_source
        # ONLY WHERE THE RECORD SAID SO. The loader derives a basis for every dated row and the
        # file ships the 127 the records state, which `basis_stated` is what tells apart.
        if printed and printed[3]:
            vol["published_basis"] = printed[1]
            vol["published_source"] = printed[2]
        if len(isbns) > 1:
            vol["editions"] = isbns
        if cover is not None:
            vol["cover_url"] = cover
        if final:
            vol["final_volume"] = True
            vol["final_volume_basis"] = {"source": fsource, "provenance": fprov,
                                         "volumes": fvols, "retrieved": fret}
        per_record.setdefault(rec, []).append(vol)

    sources = {}
    for rec, src in db.execute("SELECT record, source FROM record_source ORDER BY rowid"):
        sources.setdefault(rec, []).append(src)

    records_of = {}
    for rec, source, url, retrieved in db.execute(
            "SELECT record, source, url, retrieved FROM work_record ORDER BY rowid"):
        records_of.setdefault(rec, []).append(
            {"source": source, "retrieved": retrieved, "url": url})

    grounds = {}
    for rec, comparator, shelf, shop_url, url, retrieved, note, page in db.execute(
            "SELECT a.record, a.comparator, c.shelf, a.shop_url, a.url, a.retrieved, a.note,"
            " a.page FROM admission a LEFT JOIN comparator c ON c.name = a.comparator"
            " ORDER BY a.id"):
        # AN ABSENT KEY, NOT A NULL ONE. A ground admitted from a shelf with no shop page for the
        # work simply has no `shop_url`, and the file says so by leaving the key out.
        ground = {"comparator": comparator, "shelf": shelf, "retrieved": retrieved}
        if shop_url is not None:
            ground["shop_url"] = shop_url
        ground["note"] = note
        ground["url"] = url
        if page is not None:
            ground["page"] = page
        grounds.setdefault(rec, []).append(ground)

    claims = {}
    for rec, volumes, source, provenance, retrieved in db.execute(
            "SELECT record, volumes, source, provenance, retrieved FROM volume_claim ORDER BY id"):
        claims[rec] = {"source": source, "volumes": volumes, "retrieved": retrieved,
                       "provenance": provenance}

    out = []
    for (rid, work, title, yomi, ten, ten_basis, creator, creator_basis, n, group, label,
         lsource, lurl, lret, lnote, pub, imp, dist, shop, periodical) in db.execute(
            "SELECT id, work, title, yomi, title_en, title_en_basis, creator, creator_basis,"
            " volume_count, grouping, marketing_label, label_source, label_url, label_retrieved,"
            " label_note, publisher_raw, imprint_raw, distributor, shop_url, periodical"
            " FROM record ORDER BY rowid"):
        row = {"work_id": rid, "title": {"ja": title}}
        if ten is not None:
            row["title"]["en"] = ten
        if ten_basis is not None:
            row["title"]["en_basis"] = ten_basis
        if yomi is not None:
            row["title"]["yomi"] = yomi
        row["creator"] = creator
        if creator_basis is not None:
            row["creator_basis"] = creator_basis
        row["publisher"] = pub
        row["imprint"] = imp
        if dist is not None:
            row["distributor"] = dist
        row["volume_count"] = n
        row["grouping"] = group
        if periodical:
            row["periodical"] = True
        if shop is not None:
            row["shop_url"] = shop
        row["sources"] = sources.get(rid, [])
        row["records"] = records_of.get(rid, [])
        row["volumes"] = per_record.get(rid, [])
        if rid in claims:
            row["completed_claim"] = claims[rid]
        row["first_publication"] = _origin(db, rid)
        row["marketing_label"] = label or "none"
        row["marketing_label_basis"] = ({"source": lsource, "url": lurl, "retrieved": lret,
                                         "note": lnote}
                                        if any(x is not None for x in (lsource, lurl, lret, lnote))
                                        else None)
        if grounds.get(rid):
            row["admitted_by"] = grounds[rid]
        row["explicit_content"] = bool(_explicit(db, work))
        out.append(row)
    return {"count": len(out), "works": out}


def _origin(db, record):
    got = db.execute(
        "SELECT dated, date_source, date_basis, venue, venue_type, country, country_basis,"
        " country_note, note, date_event, date_followup, date_silence"
        " FROM work_origin WHERE record = ?", (record,)).fetchone()
    if not got:
        return None
    keys = ("date", "date_source", "date_basis", "venue", "venue_type", "country", "country_basis",
            "country_note", "note", "date_event", "date_followup", "date_silence")
    return {k: v for k, v in zip(keys, got) if not (v is None and k not in ("date", "country"))}


def _explicit(db, work):
    got = db.execute("SELECT explicit_content FROM work WHERE id = ?", (work,)).fetchone()
    return got[0] if got else 0


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


#: The sentence at the head of `checks.json`, with one home. `check.py` writes that file today and
#: this emits the site's, and a sentence written out twice is `facts with more than one home`
#: waiting to happen: the two copies had already drifted by a clause before this was noticed.
CHECKS_NOTE = ('Invariants are statements that are either true or the data is broken. At runtime a violation degrades to the fallback named in check.py and is counted here; at check-in the same violation blocks. Budgets are counts with no correct value, only a direction: they tighten automatically and loosen only by hand.')

#: The sentence at the head of `feed/names.json`.
NAMES_NOTE = ("English renderings and readings, keyed by NFKC-folded title/author. Joined onto "
              "feed rows at render time so archived months — which are never rewritten — still "
              "show current names.")


def names(db, generated):
    """`feed/names.json`, from `surface`, `name_record`, `claim`, `romanisation` and `ruby`.

    PARSED EQUALITY IS THE STANDARD, like `works.json` and for a plainer reason: a fact object here
    is SHARED between the two keys that reach it, the catalogued spelling and the shown one, so what
    the file holds is one object written twice and key order inside it follows whichever slot was
    filled first.

    THE JUDGEMENTS ARE ALL SOMEBODY ELSE'S. Which record answers for a fold is `names/fold`, which
    house a spelling names is `names/publishers`, which line it names was decided when the print
    parties were loaded, and what a claim may show for itself is `names/provenance`. This assembles.
    """
    people = _map(db, "author")
    return {"generated": generated, "note": NAMES_NOTE,
            "titles": _map(db, "title"), "authors": people,
            "publishers": _publishers(db, people), "imprints": _imprints(db),
            "credit_parts": _divisions(db),
            "floor": _romaji(db, "floor"), "phrases": _romaji(db, "phrase"),
            # WHAT AN ENGLISH PAGE CALLS EACH PLATFORM, READER-PLAN item 5. The interface held its
            # own table of these and it drifted from the register, leaving three names in Japanese
            # on an English page. A platform's English name is a fact about the platform, so it
            # travels with the rest of the names rather than being maintained a second time.
            "platforms": {n: e for n, e in db.execute(
                "SELECT name, en FROM platform_register WHERE en IS NOT NULL ORDER BY name")}}


def _raw(db, kind):
    """One population's entries, keyed by the spelling each record is filed under.

    THE ROW JOIN NEEDS BOTH MAPS. An exact hit on the spelling a row carries and a hit on its fold
    are two candidates and the fuller one wins, so an emitter holding only the folded map would
    decide that question by not being able to ask it.
    """
    out = {}
    for rid, sid, k, spelling in db.execute(
            "SELECT id, surface, kind, spelling FROM name_record WHERE kind = ? ORDER BY id",
            (kind,)):
        entry = _entry(db, rid, sid, k, spelling)
        if entry:
            out[spelling] = entry
    return out


def _map(db, kind):
    """One population's entries, keyed by the fold the site joins on.

    RENDERED FIRST AND FOLDED AFTER, which is the order `build.py` has always used and the reason
    a column saying which record won was taken back out. `names/fold` ranks what a reader is SHOWN,
    so a record whose rendering is withheld, or whose ruby its reading contradicts, has to be ranked
    on its entry.
    """
    out = _fold.fold_map(_raw(db, kind), _namekey.fold)[0]

    # A WITHHELD WORK'S TITLE MUST NOT SHIP EITHER. The register refuses the WORK, and this map is
    # keyed by the folded title and is published, so leaving it here would put the name and its
    # English rendering on the public site with only the work's rows removed. Third path of six,
    # and the reason each output was checked rather than the first one being taken as proof.
    if kind == "title":
        refused = {_namekey.fold(x) for x, in db.execute("SELECT title FROM withheld")}
        out = {k: v for k, v in out.items() if k not in refused}

    # A CATALOGUED SPELLING OF A TITLE IS THE SAME TITLE, and the store says which by holding the
    # alias. A cataloguer writes a subtitle after an ISBD colon where a platform writes it inside
    # 〜 〜, so eight works were rendered in English everywhere the series row is read and in
    # Japanese on the two tabs that draw the bibliographic record.
    for folded, target in db.execute(
            "SELECT s.folded, t.folded FROM surface s JOIN surface t ON t.id = s.alias_of"
            " WHERE s.kind = ? ORDER BY s.id", (kind,)):
        # AN ENTRY THAT EXISTS IS LEFT ALONE, and READER-PLAN item 11 is why that is worth
        # saying. A catalogued spelling with its own entry and no translation blocks the alias
        # that would give it one, so the same work is named in English on two tabs and romanised
        # on the third. Filling it from the target was tried twice, in the build and here, and
        # both broke `a work shows the English its record holds` on w03202: a fact object here is
        # SHARED between the catalogued spelling and the shown one, and the sharing has to be
        # untangled before the fill is safe.
        if target in out and folded not in out:
            out[folded] = dict(out[target], alias_of=target)
    return out


def _romaji(db, kind):
    """A romanisation map: one folded string, the three styles it is spelled in."""
    out = {}
    for folded, style, value in db.execute(
            "SELECT s.folded, r.style, r.value FROM surface s JOIN romanisation r ON r.surface = s.id"
            " WHERE s.kind = ? ORDER BY s.id", (kind,)):
        out.setdefault(folded, {})[style] = value
    # ONE STRING WHERE THE THREE STYLES AGREE, which is what the file holds and is not a shortcut:
    # a name with no long vowel and no doubled consonant is spelled the same way whichever style a
    # reader has chosen, and three copies of it would say the styles differ.
    styled = {}
    for folded, v in out.items():
        three = {s: v[s] for s in ("macron", "double", "plain") if s in v}
        styled[folded] = (next(iter(three.values())) if len(set(three.values())) == 1
                          else three)
    return styled


def _divisions(db):
    """`credit_parts`: how a byline divides into the people in it, and what each of them did."""
    out = {}
    for sid, folded, joiner, partial in db.execute(
            "SELECT d.surface, s.folded, d.joiner, d.partial FROM credit_division d"
            " JOIN surface s ON s.id = d.surface ORDER BY d.surface"):
        parts = []
        for name, role, etc in db.execute(
                "SELECT name, role, etc FROM credit_part WHERE surface = ? ORDER BY seq", (sid,)):
            parts.append({"etc": 1} if etc else
                         {"n": name, **({"r": role} if role else {})})
        fact = {"j": joiner, "p": parts}
        if partial:
            fact["part"] = True
        dropped = [x for x, in db.execute(
            "SELECT text FROM credit_dropped WHERE surface = ? ORDER BY text", (sid,))]
        if dropped:
            fact["drop"] = dropped
        out[folded] = fact
    return out


def _parties(db):
    """The catalogued seats, as the rows a name census walks: one party, one pseudo-block.

    `print_party` IS ALREADY THE FOLDED RECORDS AS WELL AS THE SHOWN ONE, which is what
    `facts/printblock.parties` yields and what the publisher census has to see. So each party is
    given its own block here rather than a block being rebuilt around it.
    """
    return [{"print": [{seat: pub, "imprint": imp}]} for seat, pub, imp in db.execute(
        "SELECT seat, publisher_raw, imprint_raw FROM print_party ORDER BY id")]


def _imprints(db):
    """`imprints`: which line a catalogued imprint string names, keyed by the string and its fold.

    THE RESOLUTION IS ALREADY MADE. `facts/imprint.resolve` decided which line each catalogued
    spelling names when the print parties were loaded, so this reads the answer off the edge and
    matches nothing itself. A spelling the registry does not answer for is absent, which is a state
    and not a gap: the interface keeps showing the catalogued string.

    ONLY STRINGS THE CORPUS CARRIES. A map holding every spelling in the registry would answer for
    strings no row has, and `imprint spellings no row carries` would have nothing to measure.
    """
    houses = {}
    for name, house in db.execute(
            "SELECT i.name, p.name FROM imprint i JOIN publisher p ON p.id = i.publisher"
            " ORDER BY i.id"):
        houses.setdefault(name, []).append(house)
    out = {}
    for raw, name, slug, parent, adult in db.execute(
            "SELECT DISTINCT y.imprint_raw, i.name, i.slug, i.parent_name, i.adult"
            " FROM print_party y JOIN imprint i ON i.id = y.imprint"
            " WHERE y.imprint_raw IS NOT NULL ORDER BY y.id"):
        fact = {"id": slug, "name": name}
        if parent:
            fact["parent"] = parent
        fact["publishers"] = houses.get(name) or []
        if adult:
            fact["adult"] = True
        for key in (raw, _impmod.match_key(raw)):
            if key:
                out.setdefault(key, fact)
    return out


def _publishers(db, people):
    """`publishers`, keyed by the string the catalogue holds AND by the string the interface shows.

    THE WHOLE OF THE RULE IS `names/publishers`, including which record answers for a string and
    what an answer looks like. Three readings of that one fact existed once; the module's is the
    only one now, and this hands it the store's rows.

    A HOUSE WITH NO ENGLISH NAME IS STILL A HOUSE WITH AN ADDRESS. The map holds only names
    something could render, which is right for a rendering and wrong for a link: 27 of the houses
    have no English at all, so keying the identifier off a rendering would make exactly the smaller
    publishers unreachable.
    """
    store = {}
    for rid, sid, kind, spelling in db.execute(
            "SELECT id, surface, kind, spelling FROM name_record WHERE kind = 'publisher'"
            " ORDER BY id"):
        entry = _entry(db, rid, sid, kind, spelling)
        if entry:
            store[spelling] = entry
    rows = _parties(db)
    out = _pubmod.render(store, people, _pubmod.corpus_names_from_rows(rows))
    for key, fact in list(out.items()):
        got = _house(db, key)
        if got and not fact.get("id"):
            # The fact is shared between the raw key and the shown one, so it is copied before it
            # is written to: two keys legitimately answer for one house, and one of them naming a
            # different house would be a link pointing away from the name beside it.
            out[key] = dict(fact, id=got)
    # AND A LINE'S OWN NAME IS A NAME. `MFC キューンシリーズ` was in the map under a key nothing
    # asks for, so 35 rows showed the line in Japanese in English-only mode: the skip has to ask
    # what the reader's lookup asks, which is the string and its NFKC form and not a fold that
    # removes spaces.
    for fact in {id(v): v for v in _imprints(db).values()}.values():
        name = fact.get("name")
        if not name or name in out or unicodedata.normalize("NFKC", name) in out:
            continue
        one = _pubmod.render(store, people, {("imprint", name): {
            "kind": "imprint", "raw": name, "shown": name, "volumes": 1}})
        rendered = one.get(name) or one.get(_namekey.fold(name))
        if rendered:
            out.setdefault(name, rendered)
            out.setdefault(_namekey.fold(name), rendered)
    for row in rows:
        for party in row["print"]:
            name = str(party.get("publisher") or "").strip()
            got = _house(db, name)
            if not got:
                continue
            for key in (name, _pubmod.publisher_of(name),
                        _namekey.fold(_pubmod.publisher_of(name))):
                if key and key not in out:
                    out[key] = {"id": got}
    return out


def _house(db, spelling):
    """Which house a catalogued spelling names, as the registry's anchors answer it."""
    got = db.execute("SELECT publisher FROM print_party WHERE publisher_raw = ?"
                     " AND publisher IS NOT NULL", (spelling,)).fetchone()
    return got[0] if got else None


_MINTED = {}


def _minted(db):
    """`{folded spelling: credit}`, which is the registry's anchors and not what a fold reaches.

    `アンソロジー` IS WHY THE TWO ARE DIFFERENT. Its spelling was withdrawn and the folded name still
    reaches the credit through `names`, so an edge-based lookup hands a reader a link to an address
    the registry no longer mints. What answers here is what a page can be opened at.
    """
    got = _MINTED.get(id(db))
    if got is None:
        got = _MINTED[id(db)] = {}
        for spelling, credit in db.execute(
                "SELECT spelling, credit FROM credit_spelling WHERE anchor = 1"
                " ORDER BY id"):
            got.setdefault(_namekey.fold(spelling), credit)
    return got


def _entry(db, rec_id, surface, kind, spelling):
    """One name record as the interface gets it, or None where it should not answer a lookup.

    THE FIELDS ARE IN THE ORDER `render` WRITES THEM, because the file is compared and a dict comes
    out in insertion order. What each one is and why it is withheld where it is withheld is on that
    function; nothing is decided again here.

    THE CLAIMS COME FROM ONE RECORD AND THAT IS THE WHOLE POINT OF `claim_record`. An entry is one
    record's account of a name: its reading, its English, its marks and its citation. Assembled from
    whichever record of the fold happened to hold each field, it would ship a name nobody wrote.
    """
    got = db.execute(
        "SELECT verified, uncertain, ordinary, transliterates, entity, basis FROM name_record"
        " WHERE id = ?", (rec_id,)).fetchone()
    if not got:
        return None
    verified, uncertain, ordinary, transliterates, entity, en_basis = got
    if entity == "notation":
        return None
    person = kind == "author" and not entity

    live = {}
    forms = {}
    for (predicate, value, basis, source, source_kind, retrieved, reviewed, url, isbn, note, gone,
         stated) in db.execute(
             "SELECT predicate, value, basis, source, source_kind, retrieved, reviewed, url,"
             " isbn, note, displaced, basis_stated FROM claim"
             " WHERE id IN (SELECT claim FROM claim_record WHERE record = ?)"
             " ORDER BY displaced, id", (rec_id,)):
        if predicate == "english" and basis in ("official-jp", "licensed", "translated"):
            forms.setdefault(basis, value)
        if not gone and predicate not in live:
            live[predicate] = (value, basis, source, source_kind, retrieved, reviewed, url, isbn,
                               note, stated)

    out = {}
    reading = live.get("reading")
    if reading:
        out["reading"] = reading[0]
        # THIS RECORD'S SPANS WHERE IT HAS ITS OWN, and the fold's otherwise.
        ruby = [[text, read] for text, read in db.execute(
            "SELECT text, reading FROM ruby WHERE surface = ? AND record = ? ORDER BY seq",
            (surface, rec_id))]
        if ruby:
            out["ruby"] = ruby
        styles = {s: v for s, v in db.execute(
            "SELECT style, value FROM romanisation WHERE surface = ? AND record = ?",
            (surface, rec_id))}
        if styles:
            out["romaji"] = {k: styles[k] for k in ("macron", "double", "plain") if k in styles}
        # UNDIVIDED IS NOT A COLUMN ANYWHERE and this is why it does not need to be: it is the
        # reading and whether the credit is a person, and `facts/division` owns where a name parts.
        division = live.get("division")
        if person and not _division.cuts(reading[0]):
            out["undivided"] = True
        elif person and division and division[9]:
            # AND ONLY WHERE THE RECORD ANSWERED FOR THE DIVISION. A division that states no basis
            # of its own takes the reading's, which is right and is not a statement about where the
            # parting point came from, so marking it would put a mark on 771 names 20 of them
            # earned. `claim.basis_stated` is the difference.
            out["division_basis"] = division[1]
    if transliterates:
        out["transliterates"] = transliterates
    english = live.get("english")
    if english:
        out["en"] = _latin(english[0])
    if en_basis:
        out["basis"] = en_basis
    if forms:
        out["en_forms"] = forms
    if reading and reading[1]:
        out["reading_basis"] = reading[1]
    for claim, which, key in ((reading, "reading", "reading_cite"),
                              (english, "en", "en_cite")):
        cite = _cite(claim, which)
        if cite:
            out[key] = cite
    # THE MARK SAYS THE READING MIGHT BE WRONG, so it is drawn only where something was GUESSED.
    # Every clause is `render`'s, because a second reading of when to doubt a name is a second
    # answer: a surface already in kana was transcribed rather than read, ordinary vocabulary in a
    # title is not a coinage, and a researched or stated reading is somebody's answer already.
    mechanical = spelling and not _script.needs_reading(spelling)
    plain = ordinary and reading and reading[1] == "analyser"
    if (verified == 0 and not mechanical and not plain
            and (not reading or reading[1] not in ("researched", "stated"))):
        out["unverified"] = True
    if uncertain:
        out["uncertain"] = True
    if out and entity:
        out["entity"] = entity
    # THE ADDRESS OF THE RECORD THIS NAME IS, which is not a rendering: it does not depend on the
    # reader's language, style or name order. A title gets none, because a work's identifier is
    # already on its own row. A name the registry credits nothing is a state and not a gap.
    if out and kind == "author":
        # ASKED OF THE REGISTRY'S SPELLINGS, not of what the fold reaches. `アンソロジー` is a credit
        # whose spelling was WITHDRAWN and whose folded name the surface still reaches, so the edge
        # answers where the registry does not, and a link would go to an address nothing mints.
        got = _minted(db).get(_namekey.fold(spelling))
        if got:
            out["id"] = got
    return out or None


#: A source's convention for showing both names at once, `HINO Arashi (日野アラシ)`. The bracketed
#: part is not part of the name and it puts Japanese back on an English page.
_BOTH_NAMES = re.compile(r"[（(][ぁ-ヿ一-鿿\s]+[)）]\s*$")


def _latin(en):
    """An English name as the file carries it: punctuation an English reader can read.

    ONE PRODUCER OF THE TRANSFORM, `names/pass4_analyser.latinise`, which normalises the typography
    and touches no letter. The store holds what the name record says, which is the claim; this is
    the same string spelled for the page it is going on, and `render` does exactly this much to it.
    """
    if not en:
        return en
    if _BOTH_NAMES.search(en):
        en = re.sub(r"\s*[（(][^)）]*[)）]\s*$", "", en)
    return _p4.latinise(en) if _p4 else en


def _cite(claim, which):
    """What a reader can go and check, ASKED OF `names/provenance` and not decided here.

    Which claims owe a document, which addresses may be shown, and what an ISBN standing in for a
    closed route looks like are all that module's, and a second copy of any of them would be the
    one that disagrees. This rebuilds the record shape it takes and asks.
    """
    if not claim:
        return None
    value, basis, source, source_kind, _retrieved, reviewed, url, _isbn, _note, _st = claim
    return _prov.cite({which: value, _prov.BASIS_FIELD[which]: basis, f"{which}_source": source,
                       f"{which}_source_kind": source_kind, f"{which}_reviewed": reviewed,
                       f"{which}_url": url}, which)


#: The sentence at the head of `series.json`.
SERIES_NOTE = ("Built from full chapter histories in data/source/, not from the 60-day feed window. "
               "One row per WORK; its platforms are listed as sources, because they differ in "
               "coverage rather than in what they are.")


def series(db, generated):
    """`series.json`, the WORK layer: one row per work, with the platforms it runs on.

    PARSED EQUALITY, like `works.json`, and for the same reason: the rows carry 30-odd key orders,
    each an artefact of which fields the compiler happened to attach to which kind of row.

    THE RENDERINGS ARE JOINED ON BY `names/attach`, the same function `build.py` asks, because a
    row's `work_en` is not a lookup: two candidate records are weighed and a byline naming several
    people is composed from them. A copy of that rule here would be the one that disagrees.
    """
    titles_raw, authors_raw = _raw(db, "title"), _raw(db, "author")
    titles_folded = _fold.fold_map(titles_raw, _namekey.fold)[0]
    authors_folded = _fold.fold_map(authors_raw, _namekey.fold)[0]
    rows = []
    for (wid, chapters, stated, latest, latest_ep, first, oneshot, inferred, collection,
         series_url, offer_id) in db.execute(
            "SELECT work, chapters, chapters_stated, latest, latest_ep, first, oneshot,"
            " oneshot_inferred, collection, series_url, offer FROM serialisation"
            " ORDER BY rowid"):
        # `latest_work_level` TRAVELS WITH THE DATE, READER-PLAN item 2. The date reached the
        # reader and the mark saying what it dates did not, so the tooltip the site had been given
        # never fired: a fix half-shipped is a fix nobody can see.
        sources = [{"platform": p, "url": u, "chapters": n, "free": f, "free_timed": ft,
                    "priced": pr, "latest": la, "partial": bool(pa), "format": fmt,
                    "retrieved": re_,
                    **({"latest_work_level": True} if wl else {})}
                   for p, u, n, f, ft, pr, la, pa, fmt, re_, wl in db.execute(
                       "SELECT platform, url, instalments, free, free_timed, priced, latest,"
                       " partial, format, retrieved, latest_work_level FROM offer"
                       " WHERE work = ? ORDER BY id", (wid,))]
        # THE ROW THE FILE SHOWS IS THE CHOSEN OFFER'S, and the rest follow it in the order they
        # were loaded, which is the order the compiler ranked them in.
        sources.sort(key=lambda s: s["url"] != _url_of(db, offer_id))
        best = next((s for s in sources if s["url"] == _url_of(db, offer_id)), None)
        state = db.execute(
            "SELECT state, basis, basis_ja, completed_basis, completed_basis_ja FROM work_state"
            " WHERE work = ?", (wid,)).fetchone() or (None, None, None, None, None)
        row = {"chapters": chapters, "partial": bool(sources) and all(s["partial"] for s in sources),
               "latest": latest, "latest_ep": latest_ep or "", "first": first,
               "state": state[0], "oneshot": bool(oneshot),
               "completed_basis": state[3], "state_basis": state[1],
               "free": best["free"] if best else 0,
               "free_timed": best["free_timed"] if best else 0,
               "priced": best["priced"] if best else 0,
               "url": best["url"] if best else None, "series_url": series_url,
               "sources": sources, "collection": collection, "id": wid,
               "skipped": [[d, t] for d, t in db.execute(
                   "SELECT dated, title FROM skipped_slot WHERE work = ?"
                   " ORDER BY dated DESC, title DESC", (wid,))]}
        if stated is not None:
            row["chapters_stated"] = stated
        if inferred:
            row["oneshot_inferred"] = True
        # A KEY THAT IS ALWAYS THERE AND SOMETIMES NULL, which is what the two row paths write and
        # is not the same as a key that is absent: a work with a serialisation is ASKED whether its
        # ending has a reason in Japanese and answers no, and a print-only row is never asked.
        if sources:
            row["completed_basis_ja"] = state[4]
            row["state_basis_ja"] = state[2]

        title, first_event, ident = db.execute(
            "SELECT title, first_event, id FROM work WHERE id = ?", (wid,)).fetchone()
        row["work"] = title
        if first_event:
            row["first_event"] = first_event
        row["author"], credits = _byline(db, wid)
        if credits:
            row["credits"] = credits
        row["evidence"] = _evidence(db, wid)
        row["state_claims"] = [
            {"source": s_, "says": sa, "term": te, "read": rd, **({"url": u} if u else {})}
            for s_, sa, te, rd, u in db.execute(
                "SELECT source, says, term, read, url FROM state_claim WHERE work = ?"
                " ORDER BY id", (wid,))]
        held = _provenance(db, wid)
        if held:
            row["sourced_from"] = held
        nxt = db.execute(
            "SELECT platform, cadence, next_update, next_update_undecided, next_from_cadence"
            " FROM stated_next WHERE work = ?", (wid,)).fetchone()
        if sources:
            row["stated_next"] = None
        if nxt:
            block = {}
            if nxt[2] is not None:
                block["next_update"] = nxt[2]
            if nxt[1] is not None:
                block["cadence"] = nxt[1]
            if nxt[3]:
                block["next_update_undecided"] = True
            if nxt[4]:
                block["next_from_cadence"] = nxt[4]
            block["platform"] = nxt[0]
            row["stated_next"] = block
        blocks = _print_blocks(db, wid)
        if blocks:
            row["print"] = blocks
        # WHAT THE PRIMARY RECORD SAYS BEYOND ITS PRINT RUN. The row shows the record the block is
        # drawn from, so its follow-up event, its shop's completion claim and the reason its creator
        # field names nobody all come from that record and not from whichever names the run.
        # AND ONLY WHERE THE RECORD IS WHAT THE ROW IS. A work with a serialisation takes its
        # dates from the platforms that publish it, so the catalogue record's follow-up event and
        # the reason its creator field names nobody belong to a row the record alone made.
        primary = blocks[0]["work_id"] if blocks and not sources else None
        if primary:
            got = db.execute("SELECT date_followup FROM work_origin WHERE record = ?",
                             (primary,)).fetchone()
            if got and got[0]:
                row["first_followup"] = got[0]
            got = db.execute("SELECT creator_basis FROM record WHERE id = ?",
                             (primary,)).fetchone()
            if got and got[0]:
                row["author_basis"] = got[0]
        # A SHOP'S COMPLETION CLAIM RIDES ONLY WHERE NOTHING ELSE SPEAKS. Where a serialisation is
        # watched, the platform decides the state and a shop marking the run 完結 is a disagreement
        # counted elsewhere rather than a fact about the row.
        if not sources:
            row["completed_claim"] = None
        for block in (blocks if not sources else []):
            got = db.execute(
                "SELECT source, volumes, retrieved, provenance FROM volume_claim WHERE record = ?",
                (block["work_id"],)).fetchone()
            if got:
                row["completed_claim"] = {"source": got[0], "volumes": got[1],
                                          "retrieved": got[2], "provenance": got[3]}
                break
        seen = db.execute("SELECT visibility FROM work_presentation WHERE work = ?",
                          (wid,)).fetchone()
        if seen and seen[0]:
            row["visibility"] = seen[0]
        # THE NEWEST THING THAT HAPPENED, WHICHEVER KIND IT WAS. `latest` answers only when the
        # serialisation last updated, so a work whose volume shipped last month reads as a year
        # stale. Month against day: a volume states 2024-03 and a chapter 2024-03-18, so the
        # comparison is made on the part both sides always carry.
        events = [(latest, "chapter")] + [(b.get("last") or b.get("first"), "volume")
                                          for b in blocks]
        events = [(d, k) for d, k in events if d]
        if events:
            row["latest_any"], row["latest_any_kind"] = max(
                events, key=lambda dk: (str(dk[0])[:7], str(dk[0])))
        got = _attach.title(title, titles_raw, titles_folded, _namekey.fold)
        if got:
            row["work_en"] = got
        got = _attach.author(row["author"], authors_raw, authors_folded, _namekey.fold)
        if got:
            row["author_en"] = got
        rows.append(row)
    return {"series": rows, "generated": generated, "note": SERIES_NOTE,
            "credence": {k: v for k, v in db.execute(
                "SELECT name, rule FROM credence_kind ORDER BY rank")},
            "thresholds": _ser.THRESHOLDS,
            "merged": {i: w for i, w in db.execute(
                "SELECT id, work FROM superseded WHERE work IS NOT NULL ORDER BY id")}}


def _url_of(db, offer_id):
    got = db.execute("SELECT url FROM offer WHERE id = ?", (offer_id,)).fetchone()
    return got[0] if got else None


def _byline(db, work):
    """`(the credit field, the people in it)`, rebuilt from the division the store holds.

    THE ROW'S OWN DIVISION AND NOT THE NAME MAP'S. `credit_part` divides the FOLDED line for a
    renderer and answers for every credit field in the corpus; this is what the row states, which is
    a shorter list: 491 rows name a job and the rest name people with no job stated.
    """
    got = db.execute("SELECT field FROM work_byline WHERE work = ?", (work,)).fetchone()
    credits = [{"name": n, **({"role": r} if r else {}), **({"basis": b} if b else {})}
               for n, r, b in db.execute(
                   "SELECT name, role, basis FROM work_byline_part WHERE work = ? ORDER BY seq",
                   (work,))]
    return (got[0] if got and got[0] else ""), credits


def _evidence(db, work):
    """Every source that speaks to whether this work is yuri, strongest first.

    THE ORDER IS THE RANK'S AND THE RANK IS THE KIND'S, `classify/credence`, which is why neither is
    a column on the row: 2,366 rows carrying a number that depends only on a word.
    """
    return [{"kind": k, "rank": rank, "type": ty, "source": s, "term": t, "read": rd,
             **({"url": u} if u else {}), **({"page": pg} if pg else {})}
            for k, rank, ty, s, t, rd, u, pg in db.execute(
                "SELECT e.kind, c.rank, c.type, e.source, e.term, e.read, e.url, e.page"
                " FROM evidence e JOIN credence_kind c ON c.name = e.kind WHERE e.work = ?"
                " ORDER BY c.rank, e.source, e.term", (work,))]


def _provenance(db, work):
    """What else was read for this work, in the order the records were walked."""
    return [{"source": s, "holds": h, "read": rd, **({"url": u} if u else {})}
            for s, h, rd, u in db.execute(
                "SELECT source, holds, read, url FROM provenance WHERE work = ? ORDER BY seq",
                (work,))]


def _print_blocks(db, work):
    """One block per print run, with every catalogue record the run was folded from.

    `folded_names` IS WHAT THE OTHER RECORDS CALL THE PARTIES, which the block itself does not show.
    Three passes count publisher and imprint names off these blocks and every one of them was
    counting one record per block, so 36 line names dropped out of the shipped name map the moment
    runs began folding.
    """
    out = []
    for (pid, record, pub, imp, dist, label, first, last, volumes, shop, delivered,
         periodical) in db.execute(
            "SELECT id, record, publisher_raw, imprint_raw, distributor, label, first, last,"
            " volumes, shop_url, delivered_from, periodical FROM print_row WHERE work = ?"
            " ORDER BY id", (work,)):
        block = {"work_id": record, "shop_url": shop, "volumes": volumes, "publisher": pub}
        if dist:
            block["distributor"] = dist
        block["imprint"] = imp
        block["first"] = first
        if delivered:
            block["delivered_from"] = delivered
        block["last"] = last
        block["label"] = label
        if periodical:
            block["periodical"] = True
        block["work_ids"] = [r for r, in db.execute(
            "SELECT record FROM print_row_record WHERE print_row = ? ORDER BY rowid", (pid,))]
        folded = {}
        for seq, seat, raw, imp_raw, pfirst, plast in db.execute(
                "SELECT seq, seat, publisher_raw, imprint_raw, first, last FROM print_party"
                " WHERE print_row = ? AND seq > 0 ORDER BY seq, id", (pid,)):
            got = folded.setdefault(seq, {})
            got[seat] = raw
            for key, value in (("imprint", imp_raw), ("first", pfirst), ("last", plast)):
                if value and key not in got:
                    got[key] = value
        if folded:
            block["folded_names"] = [
                {k: got[k] for k in ("publisher", "distributor", "imprint", "first", "last")
                 if got.get(k)}
                for _seq, got in sorted(folded.items())]
        out.append(block)
    return out


def feed(db, rows=None):
    """Every release the store holds, as the feed writes one, newest field order and all.

    ONE EMITTER FOR THE WINDOW AND FOR EVERY ARCHIVED MONTH, because a row is the same row wherever
    it is filed: what differs is the date filter over it. The archive is re-derived on every build
    and what is locked is the ROW SET rather than the bytes, which is what lets a name the store has
    since corrected reach a month that was published before the correction.

    `rows` NARROWS IT TO A SET OF IDENTIFIERS, in the order the caller wants them.
    """
    titles_raw, authors_raw = _raw(db, "title"), _raw(db, "author")
    titles_folded = _fold.fold_map(titles_raw, _namekey.fold)[0]
    authors_folded = _fold.fold_map(authors_raw, _namekey.fold)[0]
    out = []
    for r in db.execute(
            "SELECT id, work_raw, instalment, kind, adv, web, published, first_seen, basis, conf,"
            " why, moved, url, series_url, author, author_basis, plat_slug, platform, ident,"
            " free_from, discovered_on, late_discovered, access_basis, became_free,"
            " access_changed, date_means, provenance, free, ahead_n, ahead_ep, ahead_next_free,"
            " ahead_next_ep, event, event_basis, event_inferred, type_basis, preferred,"
            " preferred_reason, is_preferred, feed_date, work, episode_count, free_episodes,"
            " started, work_level, in_collection, syndicated, origin_note, origin_unknown,"
            " same_title_elsewhere, channel_name, channel_host, channel_origin, channel_home,"
            " channel_syndicated, access_stated, channel_stated FROM release ORDER BY rowid"):
        (rid, work, ep, kind, adv, web, pub, seen, basis, conf, why, moved, url, series_url,
         author, author_basis, plat, plat_name, ident, free_from, discovered_on, late_discovered,
         access_basis, became_free, access_changed, date_means, provenance, free, ahead_n,
         ahead_ep, ahead_next_free, ahead_next_ep, event, event_basis, event_inferred, type_basis,
         preferred, preferred_reason, is_preferred, feed_date, wid, episode_count, free_episodes,
         started, work_level, in_collection, syndicated, origin_note, origin_unknown,
         same_title, channel_name, channel_host, channel_origin, channel_home,
         channel_syndicated, access_stated, channel_stated) = r
        row = {"id": rid, "work": work, "ep": ep, "type": kind, "adv": bool(adv), "web": web,
               "pub": pub, "seen": seen, "basis": basis, "conf": conf, "why": why, "moved": moved,
               "url": url}
        if series_url is not None:
            row["series_url"] = series_url
        row["author"] = author
        if author_basis is not None:
            row["author_basis"] = author_basis
        row["plat"] = plat
        row["plat_name"] = plat_name
        row["ident"] = ident
        row["free_from"] = free_from
        if discovered_on is not None or late_discovered is not None:
            row["discovered_on"] = discovered_on
            row["late_discovered"] = bool(late_discovered)
        modes = [m for m, in db.execute(
            "SELECT mode FROM release_access_mode WHERE release = ? ORDER BY seq", (rid,))]
        if access_stated:
            row["access_modes"] = modes
        if access_basis is not None:
            row["access_basis"] = access_basis
        if became_free is not None:
            row["became_free"] = bool(became_free)
            row["access_changed"] = access_changed
        if date_means is not None:
            row["date_means"] = date_means
        row["provenance"] = provenance
        row["free"] = bool(free)
        if ahead_n is not None:
            row["ahead_n"] = ahead_n
            row["ahead_ep"] = ahead_ep
            row["ahead_next_free"] = ahead_next_free
            row["ahead_next_ep"] = ahead_next_ep
        row["kind"] = event
        row["kind_basis"] = event_basis
        if event_inferred is not None:
            row["kind_inferred"] = bool(event_inferred)
        if type_basis is not None:
            row["type_basis"] = type_basis
        row["preferred"] = preferred
        if preferred_reason is not None:
            row["preferred_reason"] = preferred_reason
        row["also_on"] = [p for p, in db.execute(
            "SELECT platform FROM release_also_on WHERE release = ? ORDER BY seq", (rid,))]
        row["is_preferred"] = bool(is_preferred)
        if episode_count is not None or free_episodes is not None or started is not None:
            row["episode_count"] = episode_count
            row["free_episodes"] = free_episodes
            row["started"] = started
        if work_level is not None:
            row["work_level"] = bool(work_level)
        if in_collection is not None:
            row["in_collection"] = bool(in_collection)
        if syndicated is not None:
            row["syndicated"] = bool(syndicated)
        if origin_note is not None:
            row["origin_note"] = origin_note
        if origin_unknown is not None:
            row["origin_unknown"] = bool(origin_unknown)
        if same_title is not None:
            row["same_title_elsewhere"] = same_title
        if channel_name is not None:
            row["channel_name"] = channel_name
        if channel_stated:
            row["channel"] = ({"name": channel_name, "host": channel_host,
                               "syndicated": bool(channel_syndicated), "origin": channel_origin,
                               "home": channel_home} if channel_host is not None else None)
        row["feed_date"] = feed_date
        if wid is not None:
            row["wid"] = wid
        got = _attach.title(work, titles_raw, titles_folded, _namekey.fold)
        if got:
            row["work_en"] = got
        got = _attach.author(author, authors_raw, authors_folded, _namekey.fold)
        if got:
            row["author_en"] = got
        out.append(row)
    if rows is None:
        return out
    held = {r["id"]: r for r in out}
    return [held[i] for i in rows if i in held]


def meta(db, generated, window_days, archive_from, archive_months, samples_dropped):
    """`feed/meta.json`: what the run saw of each platform, and what it has not confirmed yet.

    THE ARGUMENTS ARE THE RUN'S OWN REPORT ON ITSELF, which is why they are arguments. How wide the
    window is, which months are archived and how many promotional samples were set aside describe
    what this build did rather than what the corpus holds, and `served.CORPUS` already excludes
    `run.json` and `checks.json` on exactly that reasoning. What IS in the store is everything the
    census learned: the platforms, how far each listing has fallen behind, and the two queues.

    THE QUEUES ARE PUBLISHED BECAUSE A READER CAN CHECK THEM. DEFINITIONS §2 admits a work on stated
    grounds, and a queued row is those grounds waiting for the confirmation that makes it a record.
    """
    platforms = [{"id": slug, "name": name, "publisher": pub, "series": series,
                  "retrieved": retrieved}
                 for name, slug, pub, series, retrieved in db.execute(
                     "SELECT name, slug, publisher, series, retrieved FROM platform"
                     " WHERE census_seq IS NOT NULL ORDER BY census_seq")]
    works = []
    for (wid, title, url, platform, status, label, marketing, lsource, lurl, lret, lnote, tier,
         fsource, fsignal, furl, oneshot) in db.execute(
            "SELECT id, title, url, platform, status, label, marketing_label, label_source,"
            " label_url, label_retrieved, label_note, content_tier, found_source, found_signal,"
            " found_url, oneshot FROM web_work ORDER BY id"):
        works.append({
            "title": title, "url": url, "platform": platform, "status": status,
            "tags": [t for t, in db.execute(
                "SELECT tag FROM web_work_tag WHERE web_work = ? ORDER BY seq", (wid,))],
            "label": label,
            "authors": [{"name": n, "role": r} for n, r in db.execute(
                "SELECT name, role FROM web_work_credit WHERE web_work = ? ORDER BY seq", (wid,))],
            "marketing_label": marketing,
            "marketing_label_basis": {"source": lsource, "url": lurl, "retrieved": lret,
                                      "note": lnote},
            "content_tier": tier,
            "discovered_via": {"source": fsource, "signal": fsignal, "url": furl},
            "oneshot": bool(oneshot)})
    return {
        "platforms": platforms,
        # WORKS A COMPARATOR REPORTS AS UPDATING THAT THE PLATFORM'S OWN HISTORY CONTRADICTS. The
        # table is the platform census and a contradiction is a row in it; none stands today, which
        # is a state and not an omission.
        "contradicted": [],
        "print_candidates": [{"work_title": w, "author": a, "sample_count": n, "sample_url": u,
                              "label": lab, "status": st, "platform": p}
                             for w, a, n, u, lab, st, p in db.execute(
                                 "SELECT work_title, author, sample_count, sample_url, label,"
                                 " status, platform FROM print_candidate ORDER BY id")],
        "web_works": works,
        "samples_dropped": samples_dropped,
        "platform_meta": {name: {"rank": rank, "overlap": overlap}
                          for name, rank, overlap in db.execute(
                              "SELECT name, rank, overlap FROM platform"
                              " WHERE meta_seq IS NOT NULL ORDER BY meta_seq")},
        "lapsed": [{"work": w, "platform": p, "latest_chapter": n, "behind_by": b, "status": st}
                   for w, p, n, b, st in db.execute(
                       "SELECT work, platform, latest_chapter, behind_by, status"
                       " FROM lapsed_listing ORDER BY rowid")],
        "archive_months": archive_months,
        "archive_from": archive_from,
        "window_days": window_days,
        "generated": generated}


def feed_files(db):
    """The feed as the site serves it: a window, one file per archived month, and the report.

    THE SPLIT IS A FACT ABOUT THE FILES AND IT MOVED WITH THEM, §11. Which releases belong in the
    window and which in a month was decided in the pipeline while the pipeline wrote them; the
    store carries what the run stated, `window_days` and `archive_from`, and the split falls out of
    those and the dates the releases carry.

    A MONTH FILE HOLDS THE WHOLE MONTH, including the days the window still covers. The alternative
    makes a file's contents depend on the day the build ran, so a month written once would be frozen
    half complete and the same month written a week later would disagree with it.

    THE MONTH IN PROGRESS IS NOT ARCHIVED. It is not finished, so writing it would either publish an
    incomplete month or require rewriting it tomorrow. What IS rewritten every build is the months
    that are done: the row set is what is locked, not the bytes, so a name the store has since
    corrected reaches a month published before the correction.
    """
    import datetime
    report = dict(db.execute("SELECT key, value FROM run_report"))
    generated = report.get("generated") or ""
    window = int(report.get("window_days") or 14)
    archive_from = report.get("archive_from") or "9999-99"
    rows = feed(db)
    dated = [(str(r.get("feed_date") or r.get("pub") or "")[:10], r) for r in rows]

    out = {}
    if generated:
        today = datetime.date.fromisoformat(generated)
        # DAYS MINUS ONE, so the window is exactly that many calendar days counting today.
        # Subtract the full 14 and the tab shows fifteen date headings under a control that says
        # 直近14日, and an interface counting differently from its own label is what makes a reader
        # distrust the counts that matter.
        first = str(today - datetime.timedelta(days=window - 1))
        out["feed/current.json"] = as_text({
            "releases": [r for d, r in dated if d >= first],
            "window_days": window, "from": first, "to": generated, "generated": generated})

    months = sorted({d[:7] for d, _r in dated if len(d) >= 7
                     and archive_from <= d[:7] < generated[:7]}, reverse=True)
    for month in months:
        out[f"feed/{month}.json"] = as_text({
            "releases": [r for d, r in dated if d[:7] == month],
            "month": month, "generated": generated})

    out["feed/meta.json"] = as_text(meta(
        db, generated, window, archive_from, months, int(report.get("samples_dropped") or 0)))
    return out


# ── THE RUN'S REPORT ON ITSELF, §13 ───────────────────────────────────────────────────────────
#
# THESE ARE NOT THE CORPUS AND THEY SHIP ANYWAY. `served.CORPUS` excludes `run.json`,
# `checks.json` and `status.json` because they describe what a RUN did rather than what the
# database holds, and the status page is built from all three. §11 made that page the site's to
# build, and the project owner ruled on 2026-08-14 that the store carries the report rather than
# the pipeline publishing three small files beside it.
#
# WHAT IS MISSING FROM `run` HERE, SAID PLAINLY. `build.py`'s own `run.json` carries `claims` and
# `gaps`, 186 KB between them, and those are the corpus rather than the run: claims are in
# `claim` and `claim_record`, and a gap is a query over `work` and `offer`. They belong in the
# emitters that already answer for those tables, and putting them here would make a report file
# the way to reach corpus data for a second time.
def run(db):
    """`run.json`: what this run did, from `run_report` and `run_source`."""
    got = dict(db.execute("SELECT key, value FROM run_report"))

    def number(key):
        raw = got.get(key)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    # THE DOTTED KEYS COME BACK APART. `run_report` holds scalars, so `collapsed.samples` is a row
    # and `collapsed` is not; the shape a reader is served puts them back the way `status.py`
    # reads them.
    sections = {}
    for key in got:
        if "." not in key:
            continue
        head, tail = key.split(".", 1)
        if head == "ledger":
            continue
        sections.setdefault(head, {})[tail] = number(key)
    return {"generated": got.get("generated") or "",
            "releases": number("releases"), "platforms": number("platforms"),
            "works": number("works"), "series_rows": number("series_rows"),
            "sources": [{"source": s, "files": f, "works": w, "rows": r, "retrieved": ret,
                         "in_scope": bool(sc), "empty": bool(e),
                         "stated_rows": st, "conforming_rows": cf}
                        for s, f, w, r, ret, sc, e, st, cf in db.execute(
                            "SELECT source, files, works, rows, retrieved, in_scope, empty,"
                            " stated_rows, conforming_rows FROM run_source ORDER BY source")],
            **{k: sections.get(k) or {} for k in ("identification", "collapsed")}}


def checks(db):
    """`checks.json`: every check with what it answered, from `check_result` and `check_finding`."""
    findings = {}
    for kind, name, finding in db.execute(
            "SELECT kind, name, finding FROM check_finding ORDER BY kind, name, seq"):
        findings.setdefault((kind, name), []).append(finding)
    rows = list(db.execute("SELECT kind, name, value, budget, why, not_measured, seconds"
                           " FROM check_result ORDER BY seq, name"))
    return {
        "generated": dict(db.execute("SELECT key, value FROM run_report")).get("generated") or "",
        # AN INVARIANT RECORDS `violations` AND NOT `ok`, which the status page counts on: reading
        # a key it does not have made every check render as failing on the page whose whole job is
        # to say whether they do.
        "invariants": [{"name": n, "violations": v or 0, "examples": findings.get((k, n)) or []}
                       for k, n, v, _b, _w, _nm, _s in rows if k == "invariant"],
        # AND A BUDGET THE RUN DID NOT MEASURE CARRIES `value: null` AND SAYS WHY, so a reader can
        # tell "nothing to report" from "not asked". The store refuses a row that says neither.
        "budgets": [{"name": n, "means": w, "budget": b, "value": v,
                     **({"not_measured": nm} if nm else {})}
                    for k, n, v, b, w, nm, _s in rows if k == "budget"],
        # WHICH CHECK COST WHAT, so the next slow one is visible without guessing. A zero is
        # kept: it says the check ran and cost nothing, where an absent key says nothing at all.
        "seconds": {n: s for k, n, _v, _b, _w, _nm, s in sorted(
            rows, key=lambda r: -(r[6] or 0)) if s is not None},
        "note": CHECKS_NOTE,
    }
