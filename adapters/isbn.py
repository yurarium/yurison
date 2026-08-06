#!/usr/bin/env python3
"""One form of an ISBN, so that two catalogues keyed on it can be asked the same question.

WHY THIS EXISTS, AND WHAT IT COST TO NOT HAVE IT. Four modules had a function called `isbn13`.
Two of them converted a ten-digit ISBN to its thirteen-digit form and two only stripped the
punctuation out, and nothing said which was which. `madb/isbn_dates.py` was one of the strippers,
so the index it builds over the national bibliography was keyed on the ISBN as the catalogue
happened to print it. 126,318 of the 355,323 ISBN-bearing records in metadata101 at release 1.2.18
are printed in ten digits, 35.5% of the bibliography, and no thirteen-digit question could reach
any of them. コミックシーモア's 51 uncatalogued ISBNs were the visible end of it: two of them were
in the file all along, under the other form.

THE RULE THAT FOLLOWS. An ISBN is stored and compared in its thirteen-digit form, because that is
what openBD answers on and what every retailer in this corpus states on a book printed since 2007.
Converting the other way would have to guess a 978 or 979 prefix back off, and 979 has no
ten-digit form at all.

WHAT IT REFUSES. A field that is not an ISBN comes back as None rather than as a shorter string.
`n/a`, an empty cell and a magazine's JAN code all reach this function, and a lookup keyed on
half of one of those returns nothing in a way that reads exactly like a book nobody registered
(STANDING-INSTRUCTIONS §4).

WHAT IT DOES NOT CHECK. The check digit. A retailer's typo is a real thing and this would be the
place to catch it, but refusing an ISBN on that ground means the row silently loses its only
route to a catalogue. The catalogues themselves answer nothing for a mistyped number, which is the
same result reached without this module having to be right about the arithmetic.
"""
import re


def isbn13(raw):
    """An ISBN as thirteen digits, converting a ten-digit one, or None where it is not an ISBN.

    Both retailers state both forms: 一迅社 volumes on コミックシーモア carry 9784758074803 and
    小学館 volumes 4091287557, and MADB prints whichever the record it imported carried.
    """
    d = re.sub(r"[^0-9Xx]", "", str(raw or "")).upper()
    if len(d) == 13 and d.isdigit():
        return d
    if len(d) != 10:
        return None
    core = "978" + d[:9]
    check = (10 - sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(core)) % 10) % 10
    return core + str(check)
