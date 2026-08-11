#!/usr/bin/env python3
"""nobody: creator fields that name no person.

COVERS = ['adapters/facts/credit/nobody.py']

THE FAULT THIS IS FOR. A shop puts something in the creator field for every book it sells and has
nobody to put for an anthology, so BOOK☆WALKER and GigaViewer both write `アンソロジー`, the FORMAT
of the book. It went through the credit splitter like a byline, `credits.is_a_person` had no shape
to refuse a plain word by, and the registry minted c01868: a credit page headed アンソロジー telling
a reader in two languages that these are the works that name this person, listing nine anthologies,
one with the role 著 beside it. In English it was called Ansorojī.

WHY A TABLE AND NOT A PATTERN. The two refusals that already exist test how a string is BUILT:
digits and punctuation, or a number followed by a sentence. This is a word, spelled the way a pen
name is spelled. Nothing about its shape separates it from one, so the separation is meaning and
meaning is written down with a reason on each row.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))
import testkit                                                          # noqa: E402
from facts.credit import nobody                                         # noqa: E402


def main(s):
    s.check(nobody.NOT_A_CREDIT, "there is at least one string to refuse")

    # ── the refusal ────────────────────────────────────────────────────────────────────────────
    s.eq(nobody.not_a_credit("アンソロジー"), "many-unnamed",
         "the format of a book written where its author goes is not a credit")
    s.eq(nobody.not_a_credit(" アンソロジー "), "many-unnamed", "and surrounding space is not a name")
    # THE CATALOGUE'S NOTATION IS NOT PART OF WHAT THE FIELD SAYS. MADB writes `[著]アンソロジー` for
    # the same book BOOK☆WALKER writes `アンソロジー` for, and matching the bare string alone saw one
    # and missed the other: 乙女ゲームの破滅フラグ…公式アンソロジー kept an empty byline with nothing
    # saying why, which reads as a book nobody made.
    for wrapped in ("[著]アンソロジー", "[[著]]アンソロジー", "アンソロジー(著)", "アンソロジー（著）"):
        s.eq(nobody.not_a_credit(wrapped), "many-unnamed", f"notation stripped: {wrapped}")
    # AND STRIPPING STOPS AT THE NAME. A pen name is not a role in brackets.
    s.eq(nobody.not_a_credit("アンソロジー編集部"), None,
         "a name merely containing the word is left alone, notation or not")

    # ── AND THE COUNTER-CASE, which is what keeps this from eating bylines ─────────────────────
    # A pen name may contain the word, and a title certainly may; only the WHOLE field counts.
    for real in ("アンソロジー編集部", "百合アンソロジー", "桜庭友紀", "タイザン5", "あとき"):
        s.eq(nobody.not_a_credit(real), None, f"{real} is left alone")
    s.eq(nobody.not_a_credit(""), None, "an empty field states nothing to refuse")
    s.eq(nobody.not_a_credit(None), None, "and neither does a missing one")

    # ── every row says what it is and what it states instead ──────────────────────────────────
    for surface, (basis, why) in nobody.NOT_A_CREDIT.items():
        s.check(basis in nobody.BASIS, f"{surface} states a basis this module defines: {basis!r}")
        s.check(len((why or "").strip()) > 40,
                f"{surface} records what the string is and why it is not a name")
    s.eq(set(nobody.surfaces()), set(nobody.NOT_A_CREDIT),
         "and the surfaces are reachable without reading the table")

    # ── THE GATE CONSULTS IT, which is the whole point: a table nothing asks is a comment ──────
    import credits                                                      # noqa: PLC0415
    s.check(not credits.is_a_person("アンソロジー"),
            "is_a_person refuses it, so nothing downstream mints an identifier")
    s.check(credits.is_a_person("桜庭友紀"), "and still admits a person")
    # The two older refusals are untouched by this one.
    s.check(not credits.is_a_person("#1(1)"), "a chapter number is still not a person")
    s.check(credits.is_a_person("タイザン5"), "and a pen name holding a digit still is")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "nobody"))
