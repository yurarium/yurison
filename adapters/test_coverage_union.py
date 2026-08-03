#!/usr/bin/env python3
"""coverage_union.py: the normalisation that decides whether two rows are one work.

COVERS = ['adapters/coverage_union.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import coverage_union as cu


def main(s):
    s.eq(cu.norm("ＹＵＲＩ"), cu.norm("yuri"), "width and case fold together")
    s.eq(cu.norm("百合 の 花"), cu.norm("百合の花"), "spacing is not identity")
    s.eq(cu.norm("「百合」"), cu.norm("百合"), "brackets are not identity")
    s.ne(cu.norm("百合"), cu.norm("薔薇"), "different titles stay different")
    s.eq(cu.norm(None), "", "None normalises rather than raising")

    # THE INVISIBLE CHARACTER BUG. Web漫画アンテナ emits platform names carrying bidi and zero-width
    # marks, so 竹コミ with a U+200E in it compared unequal to 竹コミ and the same platform appeared
    # twice. Nothing is visible in a diff, which is why it is asserted rather than eyeballed.
    s.eq(cu.norm("竹コミ‎‏"), cu.norm("竹コミ"), "bidi marks are stripped")
    s.eq(cu.norm("百​合"), cu.norm("百合"), "a zero-width space is stripped")
    s.eq(cu.norm("﻿百合"), cu.norm("百合"), "a byte-order mark is stripped")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "coverage_union"))
