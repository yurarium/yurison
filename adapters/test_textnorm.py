#!/usr/bin/env python3
"""textnorm.py: the one comparison form, and the character it must not strip.

COVERS = ['adapters/textnorm.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import textnorm
import coverage_union
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "webcomics"))
import coverage


def main(s):
    n = textnorm.norm

    # THE CHARACTER THAT MUST SURVIVE. 少年ジャンプ+ is Shueisha's web platform; 少年ジャンプ is the
    # print magazine. Stripping the plus merges a platform with a magazine, which is what the two
    # drifted copies of this function disagreed about.
    s.ne(n("少年ジャンプ+"), n("少年ジャンプ"), "the plus distinguishes platform from magazine")
    s.ne(n("花とゆめ+"), n("花とゆめ"), "and again for the other one")
    s.eq(n("少年ジャンプ+"), "少年ジャンプ+", "and it survives untouched")

    # Presentation folds.
    s.eq(n("ＹＵＲＩ"), n("yuri"), "width and case")
    s.eq(n("百合 の 花"), n("百合の花"), "internal spacing")
    s.eq(n("「百合」"), n("百合"), "decorative brackets")
    s.eq(n("百合！？"), n("百合"), "trailing punctuation")
    s.eq(n(None), "", "None normalises rather than raising")

    # Invisible characters, which are the reason this is a function and not a .lower() call.
    s.eq(n("竹コミ‎‏"), n("竹コミ"), "bidi marks")
    s.eq(n("百​合"), n("百合"), "zero-width space")
    s.eq(n("﻿百合"), n("百合"), "byte-order mark")

    # Content does not fold.
    s.ne(n("百合"), n("薔薇"), "a different word is a different work")

    # ONE PRODUCER. The drift this module exists to end must not come back: both callers have to be
    # the same function, not merely agree today.
    s.check(coverage_union.norm is textnorm.norm, "coverage_union uses the shared function itself")
    s.check(coverage.norm is textnorm.norm, "and so does webcomics/coverage")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "textnorm"))
