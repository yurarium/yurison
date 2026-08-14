#!/usr/bin/env python3
"""facts/worktitle: whether two titles name one work. STORE-PLAN §12.

COVERS = ['adapters/facts/worktitle/__init__.py']

WHAT CAN BE WRONG HERE IS WHAT IT FOLDS TOGETHER, in both directions. Folding too little duplicates
a series across sources; folding too much merges two works, and this project has done both. Every
assertion below is a pair the corpus really carries.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import worktitle                                             # noqa: E402


def main(s):
    fold = worktitle.norm_work

    # ── WIDTH, CASE AND PUNCTUATION FOLD, because the comparators and the platforms render all of
    # them inconsistently and folding is the only way a title matches across sources.
    for a, b, why in (
            ("彼氏の女友達がぐいぐい来る（私に）", "彼氏の女友達がぐいぐい来る(私に)",
             "full-width brackets are the same brackets"),
            ("citrus ２", "citrus 2", "and full-width digits the same digits"),
            ("やがて君になる！", "やがて君になる!", "and a full-width exclamation the same mark"),
            ("Bloom Into You", "bloom into you", "case folds"),
            ("私の百合は お仕事です!", "私の百合はお仕事です!", "and so does a space"),
            ("A-B", "AB", "and a hyphen, which a shop puts where a platform does not")):
        s.eq(fold(a), fold(b), why)

    # ── AND TWO THINGS THAT MUST NOT FOLD, each a merge this project actually made ─────────────
    #
    # `+` MARKS A SEQUEL. citrus and citrus+ are two works with two addresses on 一迅プラス, and
    # stripping it filed the sequel's releases under the original everywhere in the database.
    s.ne(fold("citrus"), fold("citrus+"), "a sequel is not its original")
    # THE LONG VOWEL MARK IS A LETTER, not punctuation: removing it merges genuinely different
    # titles.
    s.ne(fold("ゆるゆり"), fold("ゆるゆりー"), "and a long vowel mark is part of the word")

    # ── A DIRECTION MARK IS NOT A CHARACTER A READER SEES ─────────────────────────────────────
    s.eq(fold("やがて君になる​"), fold("やがて君になる"),
         "a zero-width space arrives from a capture and names nothing")

    # ── AND IT ANSWERS FOR NOTHING RATHER THAN RAISING, because a capture hands it whatever it
    # found, and an absent title is something the corpus records rather than a fault.
    s.eq(fold(None), "", "None normalises rather than raising")
    s.eq(fold(""), "", "and so does an empty title")

    # ── IT IS NOT `facts/namekey.fold`, WHICH IS THE DISTINCTION MOST EASILY LOST ──────────────
    #
    # That one is what the site joins its name map on, NFKC with spaces removed and nothing else.
    # This one decides whether two TITLES are one work and removes punctuation the other keeps, so
    # a title with a bracket in it folds here and does not there.
    from facts import namekey
    s.ne(fold("私の百合は(お仕事です)"), namekey.fold("私の百合は(お仕事です)"),
         "a work-title fold removes what a name-map key keeps")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
