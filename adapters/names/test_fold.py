#!/usr/bin/env python3
"""names/fold: which record answers for a name several spellings fold onto.

COVERS = ['adapters/names/fold.py']

WHY THE RULE MOVED HERE. It was a closure in `build.py`, and STORE-PLAN §6 needs the store to reach
the same answer: `feed/names.json` ships one entry per fold, and an emitter ranking the records for
itself would be a second implementation of a judgement, which is the shape §3 counts seven shipped
bugs from. What is asserted below is what a second implementation would get wrong.
"""
import pathlib
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))
import testkit                                                          # noqa: E402
from names import fold as foldmod                                       # noqa: E402


def _fold(t):
    return unicodedata.normalize("NFKC", t or "").replace(" ", "")


def main(s):
    rich = {"en": "Keeps Coming On Strong (At Me)", "basis": "translated"}
    bare = {"basis": "romaji"}

    # ── THE WINNER DOES NOT DEPEND ON WHICH SPELLING ARRIVED FIRST ────────────────────────────
    #
    # 彼氏の女友達がぐいぐい来る(私に) is held twice, once with full-width brackets and once
    # without, and a dict comprehension let the last writer win. A curated translation was written
    # to the store, applied cleanly, and dropped on the way to the page with nothing reporting it.
    first = foldmod.fold_map({"来る(私に)": rich, "来る（私に）": bare}, _fold)
    second = foldmod.fold_map({"来る（私に）": bare, "来る(私に)": rich}, _fold)
    s.eq(first[0], second[0], "the surviving record does not depend on the order they arrive in")
    s.eq(first[2], second[2], "and neither does whose record the entry is rendered from")
    s.eq(first[2]["来る(私に)"], "来る(私に)",
         "which is the spelling the winning record is filed under, not the folded key")
    s.eq(first[1], [("来る(私に)", 1)], "a collision is reported rather than passed over")
    s.eq(foldmod.fold_map({"球詠": bare}, _fold)[1], [], "a name held once reports no collision")

    # ── AN ENGLISH NAME OUTWEIGHS FIELD COUNT, AND ITS BASIS OUTWEIGHS BOTH ───────────────────
    s.check(foldmod.fullness({"en": "x"}) > foldmod.fullness({"reading": "x", "basis": "y"}),
            "an English name outweighs a record that merely has more fields")
    curated = {"en": "I Can See Them, Aizawa!", "basis": "translated"}
    scraped = {"en": "I See You, Aizawa-san!", "basis": "romaji", "reading": "x",
               "ruby": [["a", "b"]], "furigana_spans": [["a", "b"]], "note": "n"}
    s.check(foldmod.fullness(curated) > foldmod.fullness(scraped),
            "a translation beats a romanisation carrying more fields")
    s.eq(foldmod.fold_map({"見えてますよ! 愛沢さん": scraped, "見えてますよ！愛沢さん": curated},
                          _fold)[0]["見えてますよ!愛沢さん"]["en"], curated["en"],
         "and the fold keeps the translated one whichever order they arrive in")

    # AND THE SAME FAULT ON THE READING, found by `a person is spelled one way`. 春結千晶 is held
    # twice and the spaced copy holds an analyser's reading; a reader was shown it with a [?]
    # beside it while a sourced reading of the same person sat in the file.
    sourced = {"reading": "ハルユウチアキ", "reading_basis": "stated"}
    guessed = {"reading": "ハル ケツ チアキ", "reading_basis": "analyser",
               "ruby": [["a", "b"]], "furigana_spans": [["a", "b"]], "reading_uncertain": True}
    s.check(foldmod.fullness(sourced) > foldmod.fullness(guessed),
            "a reading a source states beats a machine's carrying more fields")
    s.eq(foldmod.fold_map({"春結 千晶": guessed, "春結千晶": sourced}, _fold)[2]["春結千晶"],
         "春結千晶", "and the record the entry is rendered from is the one that states it")

    # A RECORD THAT IS NOT A RECORD SCORES NOTHING rather than raising, because the name store is
    # hand-edited YAML and a mistyped entry must not stop a build.
    s.eq(foldmod.fullness("not a record"), (0, 0, 0, 0), "a value that is not a record says nothing")

    # THE RANKS ARE THE NAME STORE'S OWN, not a copy. A copy is what drifted before anybody looked.
    s.check(foldmod.EN_BASIS.get("licensed", 0) > foldmod.EN_BASIS.get("romaji", 0),
            "a licensed English name outranks our own romanisation")
    s.check(foldmod.READING_BASIS.get("stated", 0) > foldmod.READING_BASIS.get("analyser", 0),
            "and a stated reading outranks an analyser's")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
