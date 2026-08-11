#!/usr/bin/env python3
"""facts/origin: where a work was first published, and what says so.

COVERS = ['adapters/facts/origin/__init__.py']

THE FAULT THIS FACT IS FOR is a field written as a constant. `first_publication.country` was the
literal "JP" in build.py twice and in cmoa_volumes.py once, so 2,564 works asserted Japan, none had
been asked, and the invariant over the field tested whether it was non-empty. DEFINITIONS §6 says
that field IS the inclusion test, and a test that cannot fail is not one.

WHAT IS ASSERTED HERE, AND WHY THE COUNTER-CASES ARE THE POINT. Two of these checks pin cases the
module must NOT decide: a translated Japanese classic, which is translated and Japanese, and a work
whose publisher puts it on a general line, which no line flag reaches. Both are the rule being wrong
in the direction it will be wrong again.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import imprint                                              # noqa: E402
from facts import origin                                               # noqa: E402


def main(s):
    # EVERY TERM IS COMPLETE. A term with no sentence reaches a reader as a slug, and a term
    # missing from the table takes the fallback, which then says the wrong thing confidently.
    for basis in origin.bases():
        entry = origin.BASES[basis]
        s.check(entry.get("note", "").strip(), f"the term carries a sentence: {basis}")
        s.check(entry.get("scope") in ("in", "out", "review", "unestablished"),
                f"and says what it settles about §6: {basis}")

    s.check(origin.FALLBACK in origin.bases(), "the fallback is itself a term")
    s.eq(origin.scope(origin.FALLBACK), "unestablished",
         "and it says the scope test has not run, which is what a record with no signal is in")
    s.check(not origin.attests(origin.FALLBACK), "so it attests nothing")

    # A TERM NOBODY DEFINED TAKES THE FALLBACK SENTENCE AND NOT A CRASH, and is not thereby given
    # a scope answer it has no claim to.
    s.eq(origin.note("a-term-nobody-defined"), origin.note(origin.FALLBACK),
         "an unknown term reads as a scope test nobody ran")
    s.eq(origin.scope("a-term-nobody-defined"), "unestablished", "and settles nothing")

    # ONE TERM PUTS JP IN THE FIELD AND IT IS NOT REACHABLE FROM A CATALOGUE. If a second one ever
    # does, the field is being filled from the Japanese edition again and this is where it shows.
    japanese = [b for b in origin.bases() if origin.BASES[b]["country"] == "JP"]
    s.eq(japanese, ["japanese-serialisation-attested"],
         "exactly one term attests Japan, and it names a serialisation venue")

    # ── THE SIGNALS ───────────────────────────────────────────────────────────────────────────
    #
    # A TRANSLATOR CREDIT IS READ THROUGH facts/credit, in the notation MADB actually writes: the
    # role sits in brackets BEFORE one name and after the other in the same string.
    s.eq(origin.roles_of("[上田香子][訳] / [作・画]ステファン・セジク")[0], "訳",
         "the role comes off the credit field where the catalogue put it")
    s.eq(origin.country_of(creator="[上田香子][訳] / [作・画]ステファン・セジク", rulings={}),
         (None, "translator-credited"),
         "a credited translator says the Japanese text is a translation, and names no country")

    # AND IT IS A LEAD, NOT A VERDICT. 現代語訳 is a Japanese classic put into modern Japanese: it
    # is translated and it was first published in Japan. A rule that retracted on this signal would
    # be wrong about every one of them, so the term asks for a reading instead.
    s.eq(origin.scope("translator-credited"), "review",
         "a translator credit is a lead, because a 現代語訳 is translated and Japanese")

    # A LINE FLAG IS READ OFF THE SHIPPED REGISTRY, not a fixture, because the flag is a claim
    # about a real line and a fixture would only prove this file agrees with itself.
    lines = imprint.load()
    idx = imprint.index(lines)
    s.check(origin.foreign_line("G-NOVELS", "", lines, idx),
            "G-NOVELS is reached from the publisher field, which is where MADB wrote the line")
    s.eq(origin.country_of(publisher="G-NOVELS", imprint="", rulings={},
                           lines=lines, imprint_index=idx),
         (None, "foreign-comics-line"),
         "and a book on it is a candidate for a ruling")

    # THE COUNTER-CASE THAT DECIDES THE WHOLE DESIGN. オルターエゴ is a Spanish original that
    # KADOKAWA publishes on MFC, the same line as its ordinary Japanese titles. No flag on any line
    # reaches it, which is why a per-work ruling exists at all.
    s.check(not origin.foreign_line("KADOKAWA", "MFC", lines, idx),
            "a general line carries translations and is not flagged, so nothing catches them there")
    s.eq(origin.country_of(publisher="一迅社", imprint="百合姫コミックス", rulings={},
                           lines=lines, imprint_index=idx),
         (None, origin.FALLBACK),
         "and an ordinary Japanese book states no country, rather than asserting one")

    # ── THE RULINGS ───────────────────────────────────────────────────────────────────────────
    #
    # READ FROM THE SHIPPED FILE. A ruling is the only thing that puts a country in the field, so a
    # test against an invented one would prove nothing about what the corpus ships.
    doc = origin.load()
    idx_r = origin.index(doc)
    s.check(idx_r, "the shipped ruling file holds rulings")

    # A RULING IS REACHABLE BY EITHER IDENTIFIER. The works list is keyed on the source record's id
    # and the series list on the identity id, and a ruling reaching one of them would leave the work
    # published on the other. That is §13's six-surfaces failure and it is what `records` is for.
    s.eq(origin.country_of(keys=["w01338"], rulings=idx_r), ("US", "publisher-states-origin"),
         "the identity id reaches the ruling")
    s.eq(origin.country_of(keys=["C418518"], rulings=idx_r), ("US", "publisher-states-origin"),
         "and so does the catalogue record id the works list is keyed on")
    s.eq(origin.country_of(keys=["w02084"], rulings=idx_r), ("ES", "publisher-states-origin"),
         "a ruling states the country its citation states")

    # A RULING BEATS THE SIGNAL, because it is somebody having read the page rather than a lead.
    s.eq(origin.country_of(keys=["w01338"], publisher="G-NOVELS",
                           creator="[上田香子][訳]", rulings=idx_r),
         ("US", "publisher-states-origin"),
         "the ruling wins over both signals that pointed at it")

    # A WORK NOBODY HAS RULED ON IS NOT IN THE FILE AND GETS NO ANSWER FROM IT.
    s.eq(origin.country_of(keys=["w00001"], rulings=idx_r), (None, origin.FALLBACK),
         "an unruled work states no country")

    # ONLY `out-of-scope` REFUSES. `review` records that somebody looked and could not settle it,
    # and a review that quietly withheld its own subject would be a filter nobody could observe.
    refused = origin.refusals(doc)
    s.check(refused, "the file refuses at least one work")
    s.check(all(r["withhold"] for r in refused), "every refusal is marked as one")
    reviewed = [r for r in (doc.get("rulings") or []) if r.get("disposition") == "review"]
    s.check(reviewed, "and the file records works examined and not ruled on")
    s.check(not any(r["work"] in {x.get("work") for x in reviewed} for r in refused),
            "a work under review is not refused")
    for r in (doc.get("rulings") or []):
        who = r.get("work") or r.get("imprint")
        s.check(r.get("why") and r.get("evidence"),
                f"every ruling states why and cites something: {who}")
        # EITHER QUESTION §6 ASKS. A ruling says where a work was first published or says the work
        # is not manga, and the two rest on different vocabularies: a term about a country cannot
        # settle a medium, so accepting either for either would let one excuse the other.
        s.check(r.get("country_basis") in origin.bases()
                or r.get("medium_basis") in origin.medium_bases(),
                f"and rests on a term one of the vocabularies holds: {who}")

    # A RULING OVER A LINE NAMES ITS WORKS, and every one of them has to be reachable, because the
    # refusal register and the run report are both built by walking them. パルソラ's prose imprint
    # is ruled once and names eleven; reading the top-level title alone saw none of them.
    over_a_line = [r for r in (doc.get("rulings") or []) if r.get("works")]
    s.check(over_a_line, "the file carries at least one ruling naming several works")
    for r in over_a_line:
        s.eq(len(origin.members(r)), len(r["works"]),
             f"every work the {r.get('imprint')} ruling names is expanded")
        for m in origin.members(r):
            s.check(m.get("work") and m.get("title"),
                    "and each carries the identifier and the title a register keys on")
    s.eq(origin.members({"work": "w1", "title": "x"}), [{"work": "w1", "title": "x"}],
         "a ruling about one work is its own member, which is every ruling written before this")

    # AND BOTH KINDS REACH THE REFUSAL REGISTER, which is what carries a work off the site.
    keys = origin.refused_keys(doc)
    for r in over_a_line:
        if r.get("disposition") == "out-of-scope":
            for m in origin.members(r):
                s.check(m["work"] in keys,
                        f"a work ruled out on a line is refused by identifier: {m['work']}")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "origin"))
