#!/usr/bin/env python3
"""facts/namekey: how two spellings of a name are compared.

COVERS = ['adapters/facts/namekey/__init__.py']

Every case here is a pair the corpus actually holds, and each dimension is asserted on both sides:
what it merges, and what it must NOT merge. A key is only as good as what it keeps apart.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))
import testkit                                                          # noqa: E402
from facts import namekey as k                                          # noqa: E402


def main(s):
    # WIDTH IS TYPOGRAPHY. The project ruled this when `ＮＯＡＨEditorial Department` reached a
    # reader: full-width Latin is a width and not a spelling.
    s.eq(k.fold("ＮＯＡＨ"), "NOAH", "full-width Latin folds to the same letters")
    s.eq(k.fold("ﾊﾝｶｸ"), "ハンカク", "and half-width kana to the same kana")

    # THE SPACE IS TYPOGRAPHY TOO, and this is the dimension with the most evidence: 108 pairs in
    # the store differ only by it, every one of them one person.
    s.eq(k.fold("源 久也"), k.fold("源久也"), "a space between family and given name is not a name")
    s.eq(k.fold("山本　和音"), k.fold("山本和音"),
         "and the ideographic one, which NFKC maps to an ASCII space before it is removed")

    # WHAT THE IDENTITY KEY MUST NOT MERGE. Each of these merges real pairs and can also merge two
    # things that are not one, and a wrong join erases somebody.
    s.check(k.fold("TOBI") != k.fold("Tobi"), "case is kept, because it can be a styling")
    s.check(k.fold("さりい・B") != k.fold("さりいB"),
            "the interpunct is kept, because a ・ also separates two people")
    s.check(k.fold("森奈津子(作)") != k.fold("森奈津子"),
            "a bracket is kept, because it can disambiguate as well as annotate")

    # AND WHAT THE MATCHING KEY IS FOR. The same three, taken deliberately, by a caller asking
    # whether two records MIGHT be one.
    s.eq(k.loosely("TOBI"), k.loosely("Tobi"), "loosely folds case")
    s.eq(k.loosely("さりい・B"), k.loosely("さりいB"), "loosely drops the interpunct")
    s.eq(k.loosely("森奈津子(作)"), k.loosely("森奈津子"), "loosely drops the bracketed apparatus")
    s.eq(k.loosely("源 久也"), k.loosely("源久也"), "and it does everything fold does")

    # THE TWO ARE NOT THE SAME FUNCTION, which is the whole point of there being two.
    s.check(k.fold("くろば・Ｕ") != k.loosely("くろば・Ｕ"), "they answer different questions")

    # EMPTY AND MISSING PASS THROUGH, because the build asks for a key for every row it holds.
    for empty in ("", None):
        s.eq(k.fold(empty), "", f"fold({empty!r}) is empty")
        s.eq(k.loosely(empty), "", f"loosely({empty!r}) is empty")

    # THE CANONICAL KEY IS THE ONE THE BROWSER USES. `the interface folds a name key as the build
    # does` pins app.js against this, so a change here without a change there fails the gate.
    s.eq(k.fold("（私に）"), "(私に)", "the fold app.js implements is this one")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
