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
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))
from facts import division as _division                                 # noqa: E402
from facts import script as _script                                     # noqa: E402
from names import provenance as _prov                                   # noqa: E402
from names import fold as _fold                                         # noqa: E402
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


#: The sentence at the head of `feed/names.json`.
NAMES_NOTE = ("English renderings and readings, keyed by NFKC-folded title/author. Joined onto "
              "feed rows at render time so archived months — which are never rewritten — still "
              "show current names.")


def _map(db, kind):
    """One population's entries, keyed by the fold the site joins on.

    RENDERED FIRST AND FOLDED AFTER, which is the order `build.py` has always used and the reason
    a column saying which record won was taken back out. `names/fold` ranks what a reader is SHOWN,
    so a record whose rendering is withheld, or whose ruby its reading contradicts, has to be ranked
    on its entry.
    """
    rendered = {}
    for rid, sid, k, spelling in db.execute(
            "SELECT id, surface, kind, spelling FROM name_record WHERE kind = ? ORDER BY id",
            (kind,)):
        entry = _entry(db, rid, sid, k, spelling)
        if entry:
            rendered[spelling] = entry
    out = _fold.fold_map(rendered, _namekey.fold)[0]

    # A CATALOGUED SPELLING OF A TITLE IS THE SAME TITLE, and the store says which by holding the
    # alias. A cataloguer writes a subtitle after an ISBD colon where a platform writes it inside
    # 〜 〜, so eight works were rendered in English everywhere the series row is read and in
    # Japanese on the two tabs that draw the bibliographic record.
    for folded, target in db.execute(
            "SELECT s.folded, t.folded FROM surface s JOIN surface t ON t.id = s.alias_of"
            " WHERE s.kind = ? ORDER BY s.id", (kind,)):
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
        ruby = [[text, read] for text, read in db.execute(
            "SELECT text, reading FROM ruby WHERE surface = ? ORDER BY seq", (surface,))]
        if ruby:
            out["ruby"] = ruby
        styles = {s: v for s, v in db.execute(
            "SELECT style, value FROM romanisation WHERE surface = ?", (surface,))}
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
        got = db.execute("SELECT credit FROM names WHERE surface = ? AND credit IS NOT NULL"
                         " ORDER BY credit", (surface,)).fetchone()
        if got:
            out["id"] = got[0]
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
