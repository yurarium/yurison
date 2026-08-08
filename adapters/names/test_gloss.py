#!/usr/bin/env python3
"""gloss.py: a bracketed reading answers for the run before it and for nothing else."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import gloss as g  # noqa: E402
from names import provenance  # noqa: E402

COVERS = ["adapters/names/gloss.py"]


# A stand-in for the analyser, holding the readings SudachiPy gives for the fragments below. The
# values were taken from it once and written down, so this suite says what the rule does with an
# analyser's answer without needing one at run time (STANDING-INSTRUCTIONS §12: offline).
READINGS = {
    "したい竜宮さんは上陸しました": ("シタイ リュウグウサン ワ ジョウリク シマシタ",
                                     [["したい", None], ["竜宮", "りゅうぐう"], ["さんは", None],
                                      ["上陸", "じょうりく"], ["しました", None]]),
    "結婚したい竜宮さんは上陸しました": ("ケッコン シタイ リュウグウサン ワ ジョウリク シマシタ",
                                         [["結婚", "けっこん"]]),
    "恋する": ("コイ スル", [["恋", "こい"], ["する", None]]),
    "にラーメンを食べる方法": ("ニ ラーメン ヲ タベル ホウホウ",
                                [["にラーメンを", None], ["食", "た"], ["べる", None],
                                 ["方法", "ほうほう"]]),
    "豹藤さんは": ("ヒョウ フジサン ワ", [["豹", "ひょう"], ["藤", "ふじ"], ["さんは", None]]),
    "したい": ("シタイ", [["したい", None]]),
    # No spans: a fragment of kana annotates nothing, which is the case that leaves a title with a
    # reading and no ruby.
    "ロックは": ("ロック ワ", None),
    "の嗜みでして": ("ノ タシナミデシテ", [["の", None], ["嗜", "たしな"], ["みでして", None]]),
}


def read(fragment):
    return READINGS.get(fragment, (None, None))


def main(s):
    # THE CASE THIS EXISTS FOR. The work is 恋する小惑星 and the bracket says how 小惑星 is said
    # there, so the title loses the bracket and the reading keeps what it said.
    s.eq(g.plain("恋する小惑星（アステロイド）"), "恋する小惑星",
         "the gloss comes out of the name")
    s.eq(g.glosses("恋する小惑星（アステロイド）"), [("小惑星", "アステロイド")],
         "and it is a reading of the run written before it")
    s.eq(g.compose("恋する小惑星（アステロイド）", read)[0], "コイ スル アステロイド",
         "which is what the title is read as, against ショウワクセイ off the characters")

    # THE COUNTER-CASE, AND THE WHOLE OF THE RULE. らぶらぶ is printed over 結婚 and says nothing
    # about 竜宮 four characters later. 竜宮 is リュウグウ, the undersea palace of the 浦島太郎
    # tale, settled in data/names/curated.yaml against a national bibliography reading of
    # タツノミヤ. A rule letting the gloss reach past its own run reproduces that error.
    counter = "結婚(らぶらぶ)したい竜宮さんは上陸しました"
    s.eq(g.plain(counter), "結婚したい竜宮さんは上陸しました",
         "the name is the title without the bracket")
    s.eq(g.compose(counter, read)[0], "ラブラブ シタイ リュウグウサン ワ ジョウリク シマシタ",
         "結婚 is read as its gloss and 竜宮 is read as 竜宮")
    s.check("タツノミヤ" not in g.compose(counter, read)[0],
            "the surname the gloss was once blamed for is nowhere in the answer")
    s.eq(read("結婚したい竜宮さんは上陸しました")[0],
         "ケッコン シタイ リュウグウサン ワ ジョウリク シマシタ",
         "and the analyser alone answers ケッコン, which is the reading the gloss overrules")

    # A GLOSS IN THE MIDDLE AND ONE AT THE END, so the fragments either side are both exercised.
    s.eq(g.compose("永久（とこしえ）にラーメンを食べる方法", read)[0],
         "トコシエ ニ ラーメン ヲ タベル ホウホウ", "a gloss at the head leaves the tail alone")
    s.eq(g.compose("豹藤さんは攻略（おと）したい", read)[0], "ヒョウ フジサン ワ オト シタイ",
         "and one in the middle leaves both sides alone")

    # THE RUBY IS CUT FROM THE SAME PIECES, so it spells the reading it is stored beside.
    _reading, spans = g.compose(counter, read)
    s.eq(spans[0], ["結婚", "らぶらぶ"], "the glossed run is one span holding what the bracket said")
    s.eq("".join(x[0] for x in spans), "結婚したい竜宮さんは上陸しました",
         "and the bases add up to the name, which is what check.py asks of a shipped row")
    s.eq(g.compose("ロックは淑女(レディ)の嗜みでして", read)[1], None,
         "a fragment the analyser gives no spans for leaves the title with a reading and no ruby")

    # WHAT IS NOT A GLOSS. Each of these would lose a piece of the title to a looser rule.
    s.eq(g.plain("リリーズ【タテスク】"), "リリーズ【タテスク】",
         "a square bracket marks a format in this corpus and is never a reading")
    s.eq(g.plain("神様の恋【タテスク】"), "神様の恋【タテスク】",
         "including after a kanji, which is the shape no title here happens to have yet")
    s.eq(g.plain("念願の悪役令嬢【ラスボス】の身体を手に入れたぞ!"),
         "念願の悪役令嬢【ラスボス】の身体を手に入れたぞ!",
         "a square bracket is refused on the bracket alone, whatever kana are inside it")
    s.eq(g.plain("あなたの未来を許さない（コミック）"), "あなたの未来を許さない（コミック）",
         "and a format label in round brackets is refused by name")
    s.eq(g.plain("神様の恋（コミック）"), "神様の恋（コミック）",
         "including where a kanji run puts it in the position a gloss would sit")
    s.eq(g.plain("トワ・エ・モア（パルシィ）"), "トワ・エ・モア（パルシィ）",
         "a katakana head is not a kanji run, so a platform name in brackets stays")
    s.eq(g.plain("SHWD(シュード)"), "SHWD(シュード)",
         "and a Latin head is left whole, because an imprint sits in that position too")
    s.eq(g.plain("超深宇宙より愛をこめて【読み切り版】"), "超深宇宙より愛をこめて【読み切り版】",
         "a one-shot beside its own serialisation keeps the marker that says so")
    s.eq(g.plain("彼氏の女友達がぐいぐい来る（私に）"), "彼氏の女友達がぐいぐい来る（私に）",
         "a bracket the author wrote holds a kanji, so nothing in it looks like a reading")
    s.eq(g.compose("ふつうの話", read), (None, None),
         "a title with no gloss states no reading of its own")

    # A SPACE BEFORE THE BRACKET, on the two rows that need it.
    s.eq(g.plain("監獄街 (プリズンタウン) へようこそ!"), "監獄街へようこそ!",
         "the national bibliography spaces the bracket and means the same thing")
    s.eq(g.plain("恋する小惑星 (アステロイド)"), "恋する小惑星",
         "which is how it writes the work COMIC FUZ writes without the space")

    # THE STORE. Written where nothing but a machine has answered, and never over a person.
    names = {}
    written, disagreed, left = g.fill(
        names, {"恋する小惑星": "恋する小惑星（アステロイド）"}, read, "2026-08-08")
    s.eq(written, {"恋する小惑星": "コイ スル アステロイド"}, "an unanswered title takes the gloss")
    s.eq(names["恋する小惑星"]["reading_basis"], "stated", "a printed reading is stated")
    s.eq(names["恋する小惑星"]["reading_source"], "title-furigana",
         "and it says where the kana were printed")
    s.check(not provenance.owes_a_document(names["恋する小惑星"]),
            "the title states it, so no page is owed and none is invented")
    s.eq((disagreed, left), ([], 0), "nothing else happened")

    held = {"恋する小惑星": {"reading": "コイ スル ショウワクセイ", "reading_basis": "analyser"}}
    g.fill(held, {"恋する小惑星": "恋する小惑星（アステロイド）"}, read, "2026-08-08")
    s.eq(held["恋する小惑星"]["reading"], "コイ スル アステロイド",
         "a guess is what the gloss is for and is replaced")

    curated = {"恋する小惑星": {"reading": "コイ スル ホシ", "reading_basis": "researched"}}
    _w, dis, _l = g.fill(curated, {"恋する小惑星": "恋する小惑星（アステロイド）"}, read,
                         "2026-08-08")
    s.eq(curated["恋する小惑星"]["reading"], "コイ スル ホシ",
         "a reviewer's decision is not overwritten by a build")
    s.eq([x[0] for x in dis], ["恋する小惑星"], "the disagreement is reported instead")

    agreed = {"結婚したい竜宮さんは上陸しました": {
        "reading": "ラブラブ シタイ リュウグウ サン ワ ジョウリク シマシタ",
        "reading_basis": "researched"}}
    _w2, dis2, left2 = g.fill(agreed, {"結婚したい竜宮さんは上陸しました": counter}, read,
                              "2026-08-08")
    s.eq(dis2, [], "the curated answer for the counter-case and the rule agree")
    s.eq(left2, 0, "and agreement is not a write")

    s.eq(g.fill_store({}, read), ({}, [], 0), "nothing glossed, nothing to record")
    s.eq(g.fill_store({"x": "y"}, None), ({}, [], 0),
         "and no analyser is the documented fallback, not an error")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
