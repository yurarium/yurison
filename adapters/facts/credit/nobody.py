#!/usr/bin/env python3
"""Creator fields that name no person, and what each one says instead.

WHY THIS IS A FACT AND NOT A FILTER. A shop puts something in the creator field for every book it
sells, and for an anthology it has nobody to put. BOOK☆WALKER and GigaViewer both write
`アンソロジー` there, which is the FORMAT of the book. The string went through the credit splitter
like any byline, `credits.is_a_person` had no reason to refuse a plain word, and the registry minted
c01868 for it: a credit page at credit/c01868/ headed アンソロジー, telling a reader in two languages
that these are "the yuri works in this database that name this person", listing nine anthologies,
one of them with the role 著 beside it. In English mode the person was called Ansorojī.

TWO REFUSALS ALREADY EXIST AND NEITHER REACHES THIS. `NOT_A_PERSON` tests whether a credit is made
only of digits and punctuation, and `CHAPTER_HEADING` tests for a number followed by a sentence.
Both are SHAPES. This is a word, spelled the way any pen name is spelled, and no shape separates it
from one. What separates it is meaning, so it is a table with a reason on every row.

WHAT REPLACES IT IS NOT A NAME EITHER. The field is not empty and must not read as though nobody
made the book: an anthology has many authors and the shop has declined to list them. So each row
carries a `basis` the interface renders in the reader's own language, the way `publisher_basis` and
`PUB_UNKNOWN` already handle a book whose publisher a catalogue does not state. Nothing is minted,
nothing is linked, and no page is built, because there is no person here to have one.

THIS DOES NOT SAY THE CONTRIBUTORS ARE UNKNOWN. It says this source did not name them. Another
source may, and `docs/GAPS.md` carries the follow-up.
"""

#: `surface: (basis, why)`. `basis` is the key the interface renders; `why` is what the string is.
NOT_A_CREDIT = {
    "アンソロジー": (
        "many-unnamed",
        "The format of the book written where its author goes. BOOK☆WALKER states it on 9 records "
        "and GigaViewer on 47. An anthology has many contributors and neither source lists them, "
        "so this names no person and never did. It had an identifier, c01868, and a credit page.",
    ),
    "アンソロ": (
        "many-unnamed",
        "The clipped form of アンソロジー, admitted with it because the two are one word and a "
        "capture that meets the short form should not mint what the long one may not.",
    ),
    "オムニバス": (
        "many-unnamed",
        "An omnibus of separate stories, named by its format for the same reason an anthology is. "
        "No record carries it today; it is here because it is the same act by the same sources.",
    ),
}

#: What each basis means, for a reader of this module. The interface holds its own bilingual copy,
#: which is a rendering decision and not this fact.
BASIS = {
    "many-unnamed": "the work has several authors and the source names none of them",
}


def not_a_credit(name):
    """The basis a creator field states instead of a person, or None where it names one."""
    return (NOT_A_CREDIT.get(str(name or "").strip()) or (None, None))[0]


def reason(name):
    """Why this string is not a credit, or None."""
    return (NOT_A_CREDIT.get(str(name or "").strip()) or (None, None))[1]


def surfaces():
    """Every creator field that names no person."""
    return tuple(NOT_A_CREDIT)


if __name__ == "__main__":
    for surface, (basis, why) in NOT_A_CREDIT.items():
        print(f"{surface}  ->  {basis}\n    {why}\n")
