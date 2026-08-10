#!/usr/bin/env python3
"""facts/dating: one vocabulary for the field that says why a row carries the date it carries.

COVERS = ['adapters/facts/dating/__init__.py']

THE FAULT THIS FACT IS FOR is a field whose terms lived in three modules. `VENUE_TYPE` answered for
six of eight and the other two got `None` from a `.get`, which reads exactly like an answer; and
`build.py` had to know which of the three captures holds the fallback sentence.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import dating                                                # noqa: E402


def main(s):
    # EVERY TERM IS COMPLETE. A term with no sentence reaches a reader as a bare slug, and a term
    # missing from the table gets the fallback sentence, which then says the wrong thing confidently.
    for basis in dating.bases():
        entry = dating.BASES[basis]
        s.check(entry.get("note", "").strip(), f"the term carries a sentence: {basis}")
        s.check("dated" in entry, f"and says whether it dates the row or explains a silence: {basis}")

    s.check(dating.FALLBACK in dating.bases(), "the fallback is itself a term")
    s.check(not dating.dates_the_row(dating.FALLBACK),
            "and it explains a silence, since it is what a row with no stated basis takes")

    # A TERM NOBODY HAS HEARD OF GETS THE FALLBACK SENTENCE AND NOT A CRASH, which is what makes a
    # capture free to add one. It must not thereby get a venue type it has no claim to.
    s.eq(dating.note("a-term-nobody-defined"), dating.note(dating.FALLBACK),
         "an unknown term reads as an unexplained silence")
    s.eq(dating.venue_type("a-term-nobody-defined"), None,
         "and is given no venue type, which would be a claim about a venue nobody looked at")
    s.check(not dating.dates_the_row("a-term-nobody-defined"),
            "and does not count as dating the row")

    # THE TWO KINDS ARE BOTH POPULATED, or `dates_the_row` would be a constant and every check
    # asking it would be vacuous.
    dated = [b for b in dating.bases() if dating.dates_the_row(b)]
    silent = [b for b in dating.bases() if not dating.dates_the_row(b)]
    s.check(dated and silent, "some terms date the row and some explain why nothing does")
    s.check(len(silent) >= 4,
            "and the silences are told apart, which is what four terms written over one bought")

    # THE PRODUCERS NAME TERMS THIS TABLE HOLDS. Each capture owns which term it emits; the table
    # owns what the terms are. If a capture renames one, this is where the two stop agreeing.
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1].parent))
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1].parent / "recon"))
    import blurbdate                                                    # noqa: E402
    import delivery                                                     # noqa: E402
    s.check(blurbdate.BASIS in dating.bases(), "blurbdate's term is in the vocabulary")
    s.check(delivery.BASIS in dating.bases(), "and so is delivery's")
    s.check(dating.dates_the_row(delivery.BASIS),
            "a delivery date dates the row, whatever else is unresolved about the printing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "dating"))
