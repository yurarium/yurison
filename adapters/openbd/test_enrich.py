#!/usr/bin/env python3
"""openbd/enrich.py: dates that never claim more precision than the source gave.

COVERS = ['adapters/openbd/enrich.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import enrich as e


def main(s):
    s.eq(e.pubdate("20260803"), "2026-08-03", "a full date becomes ISO")
    # The important one. openBD gives YYYYMM for many older volumes, and padding it to the first of
    # the month would invent a publication day that nothing attests.
    s.eq(e.pubdate("202608"), "2026-08", "a year and month stay a year and month")
    s.eq(e.pubdate("2026"), "2026", "a bare year stays a bare year")
    s.eq(e.pubdate(""), "", "nothing in, nothing out")
    s.eq(e.pubdate(None), "", "None does not raise")
    s.eq(e.pubdate("2026-08-03"), "2026-08-03", "punctuation in the input is tolerated")
    s.eq(e.pubdate("garbage"), "", "text with no digits yields nothing")

    s.eq(e.yaml_str('a "b"'), '"a \\"b\\""', "quotes are escaped for YAML")

    # THE SECOND CATALOGUE, and the rule that keeps it from agreeing with itself.
    ob = {"summary": {"pubdate": "201905"}}
    idx = {"9784091287557": "2019-01"}
    v = {"isbn": "9784091287557"}
    s.eq(e.answer(v, ob, idx, "madb"), ("2019-05", e.OPENBD),
         "openBD is asked first, because the registration is what this layer carries")
    s.eq(e.answer(v, None, idx, "madb"), ("2019-01", e.MADB),
         "MADB answers a volume its own extraction left undated")
    s.eq(e.answer(v, None, idx, "bookwalker"), ("2019-01", e.MADB),
         "and answers for a work whose primary record is not the bibliography")

    # The counter-case, and the one that matters. A madb-sourced volume that ALREADY states a date
    # must not have MADB's index written beside it: extract.py read that date off the same records
    # isbn_dates indexes, so the row would read as a second catalogue confirming the first.
    s.eq(e.answer({"isbn": "9784091287557", "published": "2019-01"}, None, idx, "madb"), ("", ""),
         "MADB never restates a date the MADB record already holds")
    # A shop's record holding a date is a different matter: the catalogue is a genuine second voice.
    s.eq(e.answer({"isbn": "9784091287557", "published": "2019-03"}, None, idx, "bookwalker"),
         ("2019-01", e.MADB), "a retailer's date does not silence the bibliography")

    s.eq(e.answer({"isbn": "9784091287557"}, None, {}, "madb"), ("", ""),
         "no release pinned, no answer, and no guess")
    s.eq(e.answer({}, ob, idx, "madb"), ("", ""), "a volume with no ISBN reaches neither catalogue")
    s.eq(e.answer(v, {"summary": {}}, {}, "madb"), ("", ""),
         "openBD holding a record but no pubdate yields no date")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "openbd.enrich"))
