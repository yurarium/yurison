#!/usr/bin/env python3
"""isbn.py: the one form two catalogues can be asked the same question in."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import isbn  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/isbn.py"]


def main(s):
    s.eq(isbn.isbn13("9784758074803"), "9784758074803", "a thirteen is already one")
    s.eq(isbn.isbn13("4091287557"), "9784091287557", "and a ten becomes one")
    s.eq(isbn.isbn13("4-09-128755-7"), "9784091287557", "hyphens and all")
    s.eq(isbn.isbn13("978-4-09-128755-7"), "9784091287557", "either way round")

    # THE TWO THAT PAID FOR THIS MODULE. Both are コミックシーモア ISBNs filed under
    # `isbn-stated-not-catalogued`, meaning no catalogue asked had a record of them. MADB held
    # both, printed in ten digits, and a thirteen-digit index over the same file could not see
    # them. 126,318 records at release 1.2.18 are in that position.
    s.eq(isbn.isbn13("4840115222"), "9784840115223", "ハニー＆ハニー, which MADB holds and dates")
    s.eq(isbn.isbn13("4396763387"), "9784396763381", "and フリー・ソウル beside it")

    # A CHECK DIGIT IS RECOMPUTED, NOT CARRIED OVER. The ten-digit and thirteen-digit forms use
    # different arithmetic, so copying the last character across produces a number that looks like
    # an ISBN and matches nothing.
    s.eq(isbn.isbn13("4758070046"), "9784758070041",
         "少女美学, whose check digit is 6 in ten digits and 1 in thirteen")
    s.eq(isbn.isbn13("400000001X"), "9784000000017", "an X check digit is dropped with the rest")

    # NOT AN ISBN IS NOT A SHORTER ISBN. A lookup keyed on half a number answers nothing, which
    # reads exactly like a book nobody registered (STANDING-INSTRUCTIONS §4).
    s.eq(isbn.isbn13("n/a"), None, "a field that is not an ISBN yields none")
    s.eq(isbn.isbn13(""), None, "nor does an empty one")
    s.eq(isbn.isbn13(None), None, "nor a missing one")
    s.eq(isbn.isbn13("978475807480"), None, "nor twelve digits")
    s.eq(isbn.isbn13("49123456789"), None, "nor eleven")
    s.eq(isbn.isbn13("4912345678901234"), None, "nor a longer run of digits")

    # THE CHECK DIGIT, FACTORED OUT so that a caller completing a publisher's own numbering and
    # `isbn13` converting a ten cannot disagree about the arithmetic.
    s.eq(isbn.check13("978410772966"), "8", "新潮社 772966 completes to 978-4-10-772966-8")
    s.eq(isbn.check13("978475807004"), "1", "and 少女美学 to 9784758070041")

    # WHAT valid10 IS FOR. An Amazon ASIN is an ISBN-10 for a printed book and an opaque code for
    # a Kindle edition. Both are ten characters, so shape alone cannot tell them apart and the
    # check digit is what does.
    s.check(isbn.valid10("4253013929"), "a 秋田書店 print ASIN is an ISBN-10")
    s.check(isbn.valid10("400000008X"), "an X check digit is an ISBN-10")
    s.check(not isbn.valid10("400000001X"),
            "and the X that test_isbn already used elsewhere is not one, which is why isbn13 "
            "converts without validating and this function is separate from it")
    s.check(not isbn.valid10("B0CW1FS2V1"), "a Kindle ASIN is not")
    s.check(not isbn.valid10("4253013920"), "nor is the same number with the check digit wrong")
    s.check(not isbn.valid10("9784253013925"), "nor a thirteen-digit ISBN")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
