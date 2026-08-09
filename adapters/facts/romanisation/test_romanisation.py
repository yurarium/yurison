#!/usr/bin/env python3
"""facts/romanisation: kana to Latin, one entry point.

COVERS = ['adapters/facts/romanisation/__init__.py']

Most cases here are a wrong spelling this project shipped, kept because a romaniser fails silently:
it returns something that looks like a word whether or not it is the right one.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))
import testkit                                                          # noqa: E402
from facts import romanisation as r                                     # noqa: E402


def main(s):
    # THE THREE STYLES DISAGREE ABOUT ONE THING, which is how a long vowel is written. Anything
    # else differing between them is a fault, and this is the shape the browser ships.
    s.eq(r.romanise("ユウリ", "macron"), "Yūri", "macron writes a long vowel with a macron")
    s.eq(r.romanise("ユウリ", "double"), "Yuuri", "double writes it doubled")
    s.eq(r.romanise("ユウリ", "plain"), "Yuri", "plain drops the length")
    s.eq(set(r.styles("ユウリ")), set(r.STYLES), "styles() answers in all three")

    # THE PLAIN STYLE REMOVES A DIACRITIC, and いい has none to remove. Niina lost an i and became
    # Nina, which is a different name.
    s.eq(r.romanise("ニイナ", "plain"), "Niina", "plain keeps both i of いい")

    # AN APOSTROPHE INSIDE A NAME SURVIVES CAPITALISATION. Shin'ichi, never Shin'Ichi.
    s.check("'" in r.romanise("シンイチ", "macron", r.PERSON), "an internal apostrophe is kept")
    s.check("Ichi" not in r.romanise("シンイチ", "macron", r.PERSON),
            "and the letter after it is not capitalised")

    # A PERSONAL NAME HOLDS NO GRAMMATICAL PARTICLE. 宮原 都 reads `to`, which is also the particle
    # と, and lower-casing part of somebody's name is worse than capitalising a particle in a title.
    s.eq(r.romanise("ミヤハラ ト", "macron", r.PERSON), "Miyahara To",
         "a person's name capitalises every part")
    s.check(r.romanise("ユリ ノ ハナ", "macron", r.TITLE) != r.romanise("ユリ ノ ハナ", "macron", r.PERSON),
            "a title and a person are cased differently, which is the only thing kind decides")

    # FULL-WIDTH LATIN IS A WIDTH AND NOT A SPELLING. This is the case the two call sites disagreed
    # about: the build folded it and the floor did not, so `ＮＯＡＨ編集部` reached readers both as
    # `NOAH Editorial Department` and as `ＮＯＡＨEditorial Department`.
    s.eq(r.romanise("ＮＯＡＨ"), "NOAH", "full-width Latin folds to the same four letters")
    s.check("Ｍ" not in r.romanise("マンガタイムキララＭＡＸ"), "and folds inside a longer string")

    # A STYLE OR A KIND NOBODY OFFERS IS AN ERROR, not a silent fallback to macron. A caller that
    # passes 'hepburn' has a bug and should hear about it.
    for bad in ("hepburn", "MACRON", ""):
        try:
            r.romanise("ユリ", bad)
            s.check(False, f"style {bad!r} is refused")
        except ValueError:
            s.check(True, f"style {bad!r} is refused")
    try:
        r.romanise("ユリ", "macron", "organisation")
        s.check(False, "an unknown kind is refused")
    except ValueError:
        s.check(True, "an unknown kind is refused")

    # EMPTY IN, EMPTY OUT. The build asks for a rendering of every record it holds, including the
    # ones with no reading, and a crash there would be a fault in this module and not in the data.
    for empty in ("", None):
        s.eq(r.romanise(empty), empty, f"{empty!r} passes through")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
