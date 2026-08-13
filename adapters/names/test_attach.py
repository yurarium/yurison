#!/usr/bin/env python3
"""names/attach: which rendering a row shows for its title and for its byline.

COVERS = ['adapters/names/attach.py']

WHY THE JOIN MOVED HERE. `feed/names.json` is keyed by NAME and a row is keyed by WORK, and
STORE-PLAN §6 needs the store to reach the same answer, since `series.json` and both feed files
carry `work_en` and `author_en` on every row. What is asserted below is what a second implementation
of the join would get wrong, because each of these was a live fault once.
"""
import pathlib
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))
import testkit                                                          # noqa: E402
from names import attach                                                # noqa: E402


def _fold(t):
    return unicodedata.normalize("NFKC", t or "").replace(" ", "")


def main(s):
    # ── AN EXACT MATCH IS NOT AUTOMATICALLY THE BETTER ONE ────────────────────────────────────
    #
    # The same work reaches us spelled 勝たん！～ and 勝たん!～ and the store holds a record for
    # each: the curated one carries the translation, the other only an automatic reading. Taking
    # the exact hit first meant whichever spelling the interface happened to display decided
    # whether the work had an English name at all.
    thin = {"basis": "romaji", "reading": "カタン"}
    full = {"en": "We Can't Lose", "basis": "translated"}
    s.eq(attach.title("勝たん！", {"勝たん！": thin}, {"勝たん!": full}, _fold), full,
         "the fuller record wins over the record the exact spelling reaches")
    s.eq(attach.title("勝たん！", {"勝たん！": full}, {}, _fold), full,
         "and an exact hit answers where the fold has nothing")
    s.eq(attach.title("知らない題", {}, {}, _fold), None,
         "a title nothing holds a record for renders as the Japanese it is")

    # ── AN EDITION IS THE SAME WORK AND TAKES THE SAME NAME ───────────────────────────────────
    #
    # やがて君になる is Bloom Into You and やがて君になる【タテスク】 was showing a full
    # romanisation, because the marker makes a different key. Nine rows were in that state.
    plain = {"en": "Bloom Into You", "basis": "licensed", "en_forms": {"licensed": "Bloom Into You"}}
    got = attach.title("やがて君になる【タテスク】", {"やがて君になる": plain}, {}, _fold)
    s.check(got and got.get("en", "").startswith("Bloom Into You"),
            "an edition takes the English of the work it is an edition of")
    s.check(got and got.get("en") != plain["en"],
            "AND SAYS WHICH EDITION IT IS, so two editions of one work do not reach a reader "
            "under one name with nothing to tell them apart")
    s.eq(got.get("en_of_edition_from"), "やがて君になる",
         "and where the name was carried from, so a count can tell it from one somebody wrote")
    s.eq(attach.title("やがて君になる", {"やがて君になる": plain}, {}, _fold), plain,
         "while the plain title is left exactly as it is")

    # ONLY THE ENGLISH IS TAKEN, never the reading or the ruby: those belong to the string they
    # were read from, and the marker is part of this row's string.
    s.check("reading" not in (got or {}), "the reading does not travel with it")

    # ── A BYLINE NAMING SEVERAL PEOPLE HAS NO RECORD OF ITS OWN ───────────────────────────────
    one = {"en": "Nio Nakatani", "basis": "romaji", "reading": "ナカタニ ニオ",
           "romaji": {"macron": "Nakatani Nio", "double": "Nakatani Nio", "plain": "Nakatani Nio"}}
    s.eq(attach.author("仲谷鳰", {"仲谷鳰": one}, {}, _fold), one,
         "a byline naming one person is that person's record")
    s.eq(attach.author("仲谷 鳰", {}, {"仲谷鳰": one}, _fold), one,
         "and the fold answers where the field spaces the name")
    s.eq(attach.author("", {}, {}, _fold), None, "an empty field renders nothing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
