#!/usr/bin/env python3
"""facts/edition: which work a translated edition translates.

COVERS = ['adapters/facts/edition/__init__.py']

Every title below is one BOOK☆WALKER holds. The case that matters is the pair the corpus could not
join: the shop files the original in kana and writes the base title of three of its translations in
kanji, so no fold reaches them and the reading has to.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import edition as ed                                         # noqa: E402

SAME = lambda a, b: a == b                                              # noqa: E731


def main(s):
    # ── THE BASE TITLE THE SHOP STATES ────────────────────────────────────────────────────────
    s.eq(ed.base("【English ver.】Reimu is Easily Embarrassed-はずかしがりやのれいむさん"),
         "はずかしがりやのれいむさん", "the Japanese title after the hyphen is what it translates")
    s.eq(ed.base("【한국어 ver.】부끄럼쟁이레이무씨-はずかしがりやの霊夢さん"),
         "はずかしがりやの霊夢さん", "and the same for a Korean edition, in the shop's own spelling")
    s.eq(ed.base("【English ver.】AyaSana Compilation To the Girls of the Wind-風の少女達へ"),
         "風の少女達へ", "the LAST field, so a translated name may hold spaces and words of its own")
    s.eq(ed.base("【English ver.】Diary of Two -ふたりの日記帳"), "ふたりの日記帳",
         "a space before the hyphen changes nothing")
    s.eq(ed.base("栖鴉"), None, "a work that is not a translated edition names no base")
    s.eq(ed.base("【English ver.】Something With No Base"), None,
         "and a product carrying no separator says nothing about what it translates, which five do")
    s.eq(ed.language("【中国語版】容易害羞的灵梦小姐-はずかしがりやの霊夢さん"), "中国語版",
         "the marker says which language, in the shop's own words")

    # ── THE READING IS THE BRIDGE, AND THIS IS THE WHOLE POINT ────────────────────────────────
    #
    # BOOK☆WALKER files the original はずかしがりやのれいむさん in kana and writes the Korean and
    # Spanish editions' base title as はずかしがりやの霊夢さん. `namekey.fold` is strict and
    # `loosely` adds case, brackets and a catalogue's name separator; none of them reaches a
    # kanji/kana pair. Both spellings read ハズカシガリ ヤ ノ レイムサン and the analyser says so
    # for either one.
    KANJI, KANA = "ハズカシガリ ヤ ノ レイムサン", "ハズカシガリ ヤ ノ レイムサン"
    s.check(ed.same_work(KANJI, KANA, "あとき", "あとき", SAME),
            "a kanji spelling meets its kana one through the reading they share")
    s.check(ed.same_work("スミカカラス", "スミカ カラス", "あとき", "あとき", SAME),
            "and the analyser's word breaks are its own, so they are not part of the claim")

    # ── THE COUNTER-CASE THAT KEEPS IT FROM MERGING STRANGERS ─────────────────────────────────
    #
    # Every one of the 28 translated-edition products is あとき on アトキンソン. A match on the base
    # title alone would merge two of that circle's works the moment two of them read alike, which
    # is why the creator has to agree. `ndl_volumes` refuses a record on the same test.
    s.check(not ed.same_work(KANJI, KANA, "あとき", "べつの人", SAME),
            "readings agreeing is not enough; a different creator is a different work")
    s.check(not ed.same_work("スミカ カラス", "クミチョウタチ ノ ナカヨシ", "あとき", "あとき", SAME),
            "and one circle's two works stay two, because their readings differ")
    s.check(not ed.same_work(None, KANA, "あとき", "あとき", SAME),
            "a base nothing could read joins nothing rather than joining everything")
    s.check(not ed.same_work(KANJI, "", "あとき", "あとき", SAME),
            "and so does a held work nothing could read")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
