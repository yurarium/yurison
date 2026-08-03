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


if __name__ == "__main__":
    sys.exit(testkit.run(main, "openbd.enrich"))
