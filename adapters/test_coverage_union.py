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

    # This normaliser strips "+", where webcomics/coverage.py keeps it. The consequence is that
    # 少年ジャンプ+ normalises to 少年ジャンプ here, so the web platform and the magazine would merge
    # if both ever appeared as platform names. Neither does today, so it is recorded rather than
    # changed: which behaviour is correct is a decision about identity, not a tidy-up.
    s.eq(cu.norm("少年ジャンプ+"), cu.norm("少年ジャンプ"),
         "the plus is stripped here, unlike in webcomics/coverage.py")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "coverage_union"))
