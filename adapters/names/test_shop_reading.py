#!/usr/bin/env python3
"""shop_reading.py: the title reading a shop states, in a field and again in the blurb."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import shop_reading as sr  # noqa: E402

COVERS = ["adapters/names/shop_reading.py"]

# Quoted from the served BOOK☆WALKER page for 豹藤さんは攻略（おと）したい.
PAGE = ('<meta name="keywords" content="豹藤さんは攻略（おと）したい,ヒョウドウサンハオトシタイ,'
        '由井ひな子,みんなのコミック,マンガ,電子書籍"/>\n'
        '<meta name="description" content="【電子書籍を読むならBOOK☆WALKER（ブックウォーカー）'
        '試し読み無料！】高１の豹藤（ひょうどう）くどきは可愛い「女子」が大好き。"/>')

# The shape the self-check exists for: a title with a comma in it pushes the reading along a field.
COMMA = ('<meta name="keywords" content="ふたり、ならんで,フタリナランデ,某,某社,マンガ,電子書籍"/>')


def main(s):
    s.eq(sr.title_reading(PAGE), ("豹藤さんは攻略（おと）したい", "ヒョウドウサンハオトシタイ"),
         "the shop's own keywords field states the whole title's reading")
    s.eq(sr.title_reading(COMMA), ("ふたり、ならんで", "フタリナランデ"),
         "and a comma inside the title does not shift which field is read")

    # THE URL IS NOT THE WORK. A shop URL reused for another edition answers happily with somebody
    # else's reading and nothing in the response says so.
    s.eq(sr.title_reading(PAGE, want="豹藤さんは攻略（おと）したい"),
         ("豹藤さんは攻略（おと）したい", "ヒョウドウサンハオトシタイ"),
         "a page that agrees which work it is answers")
    s.eq(sr.title_reading(PAGE, want="まったく別の作品"), None,
         "and one that names a different work yields nothing")

    s.eq(sr.title_reading("<html>no keywords at all</html>"), None, "no field, no reading")
    s.eq(sr.title_reading('<meta name="keywords" content="題名,Some Imprint,マンガ"/>'), None,
         "and a keywords field whose second value is Latin is an imprint, not a reading")

    s.eq(sr.blurb_furigana(PAGE), [("豹藤", "ひょうどう")],
         "the blurb glosses the surname on first use, which is the same reading written again")
    # ブックウォーカー in the boilerplate is a gloss on a Latin word and must not be collected as a
    # kanji reading; 「女子」 is quoted rather than glossed.
    s.check(all(k != "BOOK☆WALKER" for k, _ in sr.blurb_furigana(PAGE)),
            "and the shop's own name in the boilerplate is not a Japanese gloss")
    s.eq(sr.furigana_pairs("そこで彼女は笑った（笑）。"), [],
         "a bracketed kana with no kanji in front of it is not furigana")
    s.eq(sr.furigana_pairs("犬井（いぬい）と犬井（いぬい）"), [("犬井", "いぬい")],
         "a gloss repeated in one blurb is one pair")


    # THE SHOP SELLS A VOLUME AND THE CORPUS HOLDS A SERIES.
    s.eq(sr.title_reading('<meta name="keywords" content="100日後に咲く百合,'
                          'ヒャクニチゴニサクユリ001,某,マンガ"/>'),
         ("100日後に咲く百合", "ヒャクニチゴニサクユリ"),
         "the volume number the shop appends to the reading comes off")
    s.eq(sr.without_volume("BLUE 2", "ブルー2"), "ブルー2",
         "and stays on where the title itself ends in a number")
    s.eq(sr.without_volume("100日後に咲く百合", "ヒャクニチゴニサクユリ"), "ヒャクニチゴニサクユリ",
         "digits at the front of a title are part of it and are not the trigger")

    e = sr.entry("豹藤さんは攻略（おと）したい", "ヒョウドウサンハオトシタイ", "https://bookwalker.jp/x",
                 "ヒョウ フジサン ワ コウリャク シタイ", "2026-08-06", [("豹藤", "ひょうどう")])
    s.eq(e["reading_basis"], "stated", "a shop stating the registered yomi is `stated`")
    s.eq(e["reading_source_kind"], "platform", "with the platform as the evidence")
    s.check("ひょうどう" in e["reading_note"],
            "and the note carries the second statement, so a reviewer can see the two agree")
    s.check("replaces" in e["reading_note"], "and says what it replaced")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, __file__))
