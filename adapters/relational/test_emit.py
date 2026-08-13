#!/usr/bin/env python3
"""adapters/relational/emit: a corpus file built out of tables rather than beside them.

COVERS = ['adapters/relational/emit.py']

WHAT THIS HAS TO ASSERT AND WHY IT IS BYTE EQUALITY. An emitter that produces something ALMOST the
same as what the compiler produced is a second producer with a bug, which is the fault STORE-PLAN §6
exists to end rather than to introduce. Comparing parsed objects would let key order drift; comparing
text does not.

THE COMPARISON IS AGAINST THE SHIPPED FILE, which is available because §6 moves one domain at a time
and the file is still on disk from the run that wrote it. That window is the whole reason the plan
refuses a cutover: a domain moved with nothing to compare against is a domain moved on faith.

IT CAUGHT TWO REAL FAULTS on the first comparison, both taken on in §5h. 130 credits had their RAW
title filed as a spelling, where the registry answers for the FOLD of it, so `二三　夏一` shipped
beside `二三夏一`. And `アンソロジー` is a credit whose spelling was withdrawn and whose folded title
the registry still answers for, which the loader was dropping. Neither is visible from either side
alone.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit                                                          # noqa: E402
import relational                                                       # noqa: E402
from relational import emit                                             # noqa: E402

BUILD = pathlib.Path(__file__).resolve().parents[2] / "data" / "build"


def main(s):
    shipped = BUILD / "credits.json"
    if not shipped.exists():
        s.check(False, "the build must be present for an emitted file to be compared against one")
        return
    want = json.loads(shipped.read_text(encoding="utf-8"))

    # THE STORE IS BUILT FROM THE COMPILER'S ROWS, which is the direction §6 turns on. Reading
    # `data/build` here would prove only that the store round-trips its own input.
    source = {n: json.loads((BUILD / f"{n}.json").read_text(encoding="utf-8"))
              for n in ("series", "works") if (BUILD / f"{n}.json").exists()}
    db, _counts, refused = relational.build(path=":memory:", source=source)
    s.eq(refused, [], "the store takes the compiler's rows with nothing refused")

    got = emit.credits(db, want["generated"])
    s.eq(emit.as_text(got), emit.as_text(want),
         "`credits.json` emitted from the store is what the compiler wrote, byte for byte")

    # AND THE PARTS THAT WOULD BE EASY TO GET ALMOST RIGHT, named so a failure says which.
    s.eq(list(got), list(want), "the keys are in the file's own order")
    s.eq(len(got["credits"]), want["count"], "and the count is of what is actually there")
    roled = [(c, w) for c, v in got["credits"].items()
             for w in (v.get("works") or []) if w.get("roles")]
    s.check(roled, "AN EDGE CARRIES ITS ROLE, which the store held as 4,165 NULLs until §6 read "
                   "`roles` where the loader had asked for `role`")
    s.check(any(v.get("homophones") for v in got["credits"].values()),
            "a ruling that two credits are different people reaches the page from the store")
    s.check(any(v.get("kind") for v in got["credits"].values()),
            "and the registry's finer word for what a credit is, which `shape` cannot carry")

    # ── A DOMAIN MAY NOT BE ITS OWN INPUT, WHICH BYTE EQUALITY CANNOT SEE ─────────────────────
    #
    # The store's credit tables were loaded from `credits.json`, the file this emits. Comparing
    # against a file still on disk proved the emitter and said nothing about where its input came
    # from, so a clean checkout built empty and emitted empty. CI found that; the second time, the
    # merge map alone was still being read from the file and every retired credit address lost its
    # forwarder. This is the assertion that catches both without deleting anything.
    s.check(source and "credits" not in source,
            "the store is built from the compiler's rows with no `credits.json` among them")
    s.check(got["merged"], "A RETIRED IDENTIFIER STILL RESOLVES, which is what a forwarder needs "
                           "and what an empty merge map silently removed from the site")
    s.eq(got["merged"], want["merged"],
         "and the map is the registry's, which is where a merge is actually recorded")

    # ── THE SECOND DOMAIN: `publishers.json` ─────────────────────────────────────────────────
    houses = BUILD / "publishers.json"
    if not houses.exists():
        s.check(False, "the build must be present for this file to be compared against one")
        return
    want_h = json.loads(houses.read_text(encoding="utf-8"))
    got_h = emit.publishers(db, want_h["generated"])
    s.eq(emit.as_text(got_h), emit.as_text(want_h),
         "`publishers.json` emitted from the store is what the compiler wrote, byte for byte")
    s.check(source and "publishers" not in source,
            "and the store was built with no `publishers.json` among its inputs either")

    # WHAT BYTE EQUALITY WOULD HAVE MISSED HERE, and did until each was chased down. The parties
    # were built from an unordered `SELECT id, record`, which SQLite served from the unique index on
    # `record`, so every works list came out in a sequence with nothing to do with the compiler's.
    # A line's years were measured off the BLOCK's dates where `parties` says each folded record
    # states its own. And `imprint.parent` as a foreign key dropped the one parent that resolves to
    # no line, which a publisher page shows.
    first = next(iter(got_h["publishers"].values()))
    s.eq(first["works"][:3], next(iter(want_h["publishers"].values()))["works"][:3],
         "a house's works are in the order its print rows are, not the order a table scan gives")
    s.check(any(l.get("parent") for h in got_h["publishers"].values() for l in h["lines"]),
            "a line inside a line names its parent, including the one that resolves to no line")

    # ── `feed/credit-keys.json`, WHICH IS A TABLE WRITTEN DOWN ───────────────────────────────
    keys = BUILD / "feed" / "credit-keys.json"
    if keys.exists():
        s.eq(emit.as_compact(emit.credit_keys(db)),
             emit.as_compact(json.loads(keys.read_text(encoding="utf-8"))),
             "`feed/credit-keys.json` is `credit_spelling` and comes out of it byte for byte")

    # ── `index.json`: THE COLLAPSE IS ARITHMETIC, THE IDENTITY IS THE STORE'S ────────────────
    idx = BUILD / "index.json"
    if idx.exists():
        want_i = json.loads(idx.read_text(encoding="utf-8"))
        got_i = emit.index(db)
        # NOT BYTE EQUALITY, AND THE REASON IS WORTH MORE THAN THE ASSERTION WOULD BE. `record_credit`
        # is the splitter's division of a creator field, and the splitter answers differently
        # depending on the INTERPUNCT RULINGS, which `build.py` derives from the corpus at run time
        # and holds in memory. A store built here has none, so `るいす・まくられん` divides in two
        # where the compiler kept it whole, and 6 rows differ. docs/GAPS.md carries it.
        s.eq(len(got_i), len(want_i), "the index holds one row per work, as the compiler wrote it")
        s.eq([r["id"] for r in got_i], [r["id"] for r in want_i],
             "in the same order and standing for the same records")
        s.eq([{k: v for k, v in r.items() if k != "ci"} for r in got_i],
             [{k: v for k, v in r.items() if k != "ci"} for r in want_i],
             "and identical in every field but the one the splitter's rulings reach")
        # WHAT THE COMPARISON CAUGHT. `ci` is the people the CREATOR FIELD names in ITS order, and
        # taking `work_credit` in row order reordered 217 lists into the order identifiers were
        # minted in. Then 17 more differed because the field has TWO divisions in this project:
        # `credit_part` holds what a page renders a byline from and `record_credit` holds what the
        # splitter minted against, and `index.json` resolves through the second.
        multi = [r for r in got_i if len(r.get("ci") or []) > 2]
        s.check(multi, "a row naming several people carries them in the field's own order")
        s.eq([r["ci"] for r in got_i if r["id"] == multi[0]["id"]],
             [r["ci"] for r in want_i if r["id"] == multi[0]["id"]],
             "which is the splitter's division and not the renderer's")
        s.check(any(len(r.get("ids") or []) > 1 for r in got_i),
                "AND A WORK COMPILED FROM TWO RECORDS KEEPS BOTH ADDRESSES, because a collapse "
                "that kept one would make the other unresolvable")

    # ── `works.json`: THE RECORD LAYER, ON PARSED EQUALITY ───────────────────────────────────
    #
    # NOT BYTE EQUALITY, AND `emit.works` says why: 11 key orders on the records and 38 on the
    # volumes, each an artefact of the order the compiler merged its sources. Asserting them would
    # assert the merge order. Every key's PRESENCE and every value is asserted instead.
    wf = BUILD / "works.json"
    if wf.exists():
        want_w = json.loads(wf.read_text(encoding="utf-8"))
        got_w = emit.works(db)
        s.eq(got_w["count"], want_w["count"], "one row per catalogue record")
        s.eq([r["work_id"] for r in got_w["works"]], [r["work_id"] for r in want_w["works"]],
             "in the order the compiler wrote them")
        s.eq(sum(len(r["volumes"]) for r in got_w["works"]),
             sum(len(r["volumes"]) for r in want_w["works"]),
             "AND EVERY VOLUME ROW THE RECORDS STATE, which §5f folded four of on the ISBN and had "
             "to stop: a record listing one book twice lists two rows")
        s.eq(got_w["works"], want_w["works"],
             "and every field of every record, parsed")


    # ── ONE NAME RECORD AS THE INTERFACE GETS IT, which `feed/names.json` is 6,000 of ──────────
    #
    # THE FILE IS NOT EMITTED YET and this is the piece it is built out of, so what is asserted is
    # that an entry comes out of the TABLES and says what the record says. The map itself waits on
    # a claim being able to belong to two records, which STORE-PLAN §6 carries.
    # THE RENDERINGS ARE THEIR OWN LOAD, because the compiler cannot hand the map over until it has
    # emitted the two files the map is assembled from. A rebuild reads the shipped one, which is
    # what this does.
    shipped_names = BUILD / "feed" / "names.json"
    if shipped_names.exists():
        relational.renderings(db, json.loads(shipped_names.read_text(encoding="utf-8")))
    got_n = None
    for rid, sid, kind, spelling in db.execute(
            "SELECT id, surface, kind, spelling FROM name_record WHERE kind = 'author'"
            " ORDER BY id"):
        entry = emit._entry(db, rid, sid, kind, spelling)
        if entry and entry.get("reading") and entry.get("romaji"):
            got_n = entry
            break
    s.check(got_n, "a name record renders out of the store")
    s.eq(sorted(got_n["romaji"]), ["double", "macron", "plain"],
         "in the reader's three styles, from `romanisation` and not from a string")
    s.check(got_n.get("reading_basis"),
            "and it says how the reading was arrived at, which is the claim's own basis")
    # ── AND THE WHOLE MAP, ON PARSED EQUALITY ─────────────────────────────────────────────────
    #
    # NOT BYTES, and the reason is the file's own shape: a fact is SHARED between the two keys that
    # reach it, the catalogued spelling and the shown one, so what is written is one object under
    # two keys and the order inside it follows whichever slot was filled first.
    if shipped_names.exists():
        want_n = json.loads(shipped_names.read_text(encoding="utf-8"))
        got_map = emit.names(db, want_n["generated"])
        s.eq(list(got_map), list(want_n), "`feed/names.json` has the sections the compiler wrote")
        for section in ("titles", "authors", "publishers", "imprints", "credit_parts",
                        "floor", "phrases"):
            s.eq(sorted(got_map[section]), sorted(want_n[section]),
                 f"`{section}` is keyed exactly as the file is")
        s.eq(got_map, want_n, "and every entry of every section says what the compiler wrote")

    s.check(not any(emit._entry(db, rid, sid, k, sp)
                    for rid, sid, k, sp in db.execute(
                        "SELECT id, surface, kind, spelling FROM name_record"
                        " WHERE entity = 'notation'")),
            "A NAME WITH A ROLE WELDED ON ANSWERS NOTHING, because the store holds the person "
            "separately and a lookup on the raw field has to reach them")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
