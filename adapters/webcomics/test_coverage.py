#!/usr/bin/env python3
"""webcomics/coverage.py: the antenna's normalisation.

COVERS = ['adapters/webcomics/coverage.py']

The antenna is Tier C: it says a work exists and where, and nothing it says becomes a record. What
it DOES decide is whether two mentions are one work, so the normalisation below is load-bearing.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import coverage as wc


def main(s):
    s.eq(wc.norm("ＹＵＲＩ"), wc.norm("yuri"), "width and case fold")
    s.eq(wc.norm("百合 の 花"), wc.norm("百合の花"), "spacing is not identity")
    s.ne(wc.norm("百合"), wc.norm("薔薇"), "different titles stay different")
    s.eq(wc.norm(None), "", "None normalises rather than raising")

    # The invisible characters this source actually emits. 竹コミ with a U+200E compared unequal to
    # 竹コミ, so one platform appeared as two and nothing showed in a diff.
    s.eq(wc.norm("竹コミ‎‏"), wc.norm("竹コミ"), "bidi marks are stripped")
    s.eq(wc.norm("百​合"), wc.norm("百合"), "a zero-width space is stripped")
    s.eq(wc.norm("﻿竹コミ"), wc.norm("竹コミ"), "a byte-order mark is stripped")

    # TWO NORMALISERS, ONE JOB, AND THEY DISAGREE. coverage_union.norm strips "+" and this one
    # keeps it, so 少年ジャンプ+ and 花とゆめ+ lose their plus on one path and not the other. No
    # collision exists in the current data, because the magazines 少年ジャンプ and 花とゆめ are not
    # platform names here, so this is latent rather than live. Both behaviours are pinned so the
    # difference cannot be erased by tidying one into the other without deciding which is right.
    s.eq(wc.norm("少年ジャンプ+"), "少年ジャンプ+", "this source keeps the plus")
    s.ne(wc.norm("少年ジャンプ+"), wc.norm("少年ジャンプ"), "so the platform is distinct from the magazine")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "webcomics.coverage"))
