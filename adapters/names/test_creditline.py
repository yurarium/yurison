#!/usr/bin/env python3
"""creditline.py: dividing a credit field the way the page is going to draw it.

COVERS = ['adapters/names/creditline.py']

WHAT THIS HAS TO PIN, and it is mostly counter-cases. Every rule in the module has a shape it would
break, and each one was found by a row in the corpus rather than by reasoning:

  the interpunct joins two people in 矢立肇・富野由悠季 and sits inside one name in さりい・Ｂ;

  a katakana part beside a kanji one is a printed READING in 紬めめ / ツムギメメ and a second
  ARTIST in [原作]王月よう / [漫画]アジイチ, which the tab this replaces got wrong in four bylines;

  a bracket holds a role in [著]嵩乃朔, a name in [BPS株式会社], a reading in 若（わか）, and an
  imprint note in 宮澤伊織(早川書房刊), and only the first two are people.

Offline: the store is a literal here. Nothing reads a file and nothing reaches a network.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import creditline  # noqa: E402

COVERS = ["adapters/names/creditline.py"]

# The store as the browser receives it, keyed folded. Six records, each one a state the division
# turns on: a reading it can compare against, a romanisation that licenses an interpunct split, and
# a record with neither, which is what stops one.
STORE = {
    "矢立肇": {"reading": "ヤダテハジメ", "romaji": {"macron": "Yadate Hajime"}},
    "富野由悠季": {"reading": "トミノヨシユキ", "romaji": {"macron": "Tomino Yoshiyuki"}},
    "さりい": {"reading": "サリイ", "romaji": {"macron": "Sarii"}},
    # A record with no romanisation, which is the half that must stop the split beside it.
    "B": {"en": "B", "basis": "stated"},
    "きづきあきら": {"reading": "キヅキアキラ", "romaji": {"macron": "Kizuki Akira"}},
    "とりいしづく": {"reading": "トリイシヅク", "romaji": {"macron": "Torii Shizuku"}},
    "紬めめ": {"reading": "ツムギメメ", "romaji": {"macron": "Tsumugi Meme"}},
}


def names(field):
    return [p["n"] for p in creditline.divide(field, STORE) if p.get("n")]


def main(s):
    # ── the interpunct, which nothing in the string resolves ──────────────────────────────────
    s.eq(names("矢立肇・富野由悠季"), ["矢立肇", "富野由悠季"],
         "an interpunct divides where the store states a reading for both halves")
    s.eq(names("さりい・Ｂ"), ["さりい・Ｂ"],
         "AND NOT WHERE IT DOES NOT. Ｂ has a record and is already Latin, so a looser test passed "
         "it and one artist became two. A sourced romanisation on both sides is the test")
    s.eq(names("るいす・まくられん"), ["るいす・まくられん"],
         "a name the store has never met keeps its interpunct, which is the answer inputs.py "
         "records for a caller that prints")

    # ── the reading printed beside the name ───────────────────────────────────────────────────
    s.eq(names("紬めめ / ツムギメメ"), ["紬めめ"],
         "a katakana part that spells another part's reading is that reading and not a person")
    s.eq(names("[原作]王月よう / [漫画]アジイチ"), ["王月よう", "アジイチ"],
         "A FIELD THAT STATES A JOB FOR EACH HALF NAMES TWO PEOPLE. The rule this replaces "
         "dropped アジイチ, フライ, ヨリフジ and サトウナンキ from four bylines in every language")
    s.eq(names("きづきあきら / サトウナンキ"), ["きづきあきら", "サトウナンキ"],
         "and where the store states a reading that is not the katakana beside it, the two are "
         "the duo they look like")
    s.eq(names("とりいしづく / トリイシズク"), ["とりいしづく"],
         "while a filing key that folds づ to ず still spells the same name")
    s.eq(names("河上大志郎 / カワカミダイシロウ"), ["河上大志郎"],
         "a pair the store can say nothing about keeps the positional answer, which is what this "
         "did before and is right far more often than not")
    s.eq(names("おぎしろ / みかみてれん / オギシロ / ミカミテレン"), ["おぎしろ", "みかみてれん"],
         "TWO PEOPLE AND THEIR TWO READINGS, which counting positions could read and which "
         "でかいるか / エリーゼ / エリーゼ / デカイルカ defeats, because the splitter folds the "
         "repeated name away and leaves an odd number")
    s.eq(names("シチサブロー / シチサブロー"), ["シチサブロー"],
         "a field written entirely in katakana keeps every name in it rather than emptying itself")

    # ── the notation a catalogue writes round a name ──────────────────────────────────────────
    s.eq(creditline.divide("[著]嵩乃朔 [ほか]", STORE),
         [{"n": "嵩乃朔", "r": "著"}, {"etc": 1}],
         "a role, a name and the word that says there are more contributors than the field lists")
    s.eq(creditline.divide("南部くまこ(作) / 東河みそ(絵)", STORE),
         [{"n": "南部くまこ", "r": "作"}, {"n": "東河みそ", "r": "絵"}],
         "a role in round brackets is a role, which neither renderer this replaces knew")
    s.eq(creditline.divide("南瓜かぷちー(表紙/漫画)", STORE), [{"n": "南瓜かぷちー", "r": "表紙/漫画"}],
         "and a compound role comes back spelt as the FIELD spells it, because that is the string "
         "the interface has to find in the field it is drawing")
    s.eq(names("[[翻訳協力]][BPS株式会社] / [著]時一二"), ["BPS株式会社", "時一二"],
         "A DOUBLED DELIMITER IS STILL ONE DELIMITER. Against the doubled form the splitter found "
         "no name at all, so a company credited on two works vanished from the byline")
    s.eq(names("[上田香子][訳]"), ["上田香子"],
         "and a name in one bracket beside a job in the next is the person, not the job")
    s.eq(names("あとき / 싱글벙글환상향"), ["あとき", "싱글벙글환상향"],
         "a pen name in a script this project makes no claim about is still a pen name")

    # ── what the division set aside, and what it lost ─────────────────────────────────────────
    s.eq(creditline._divide("若（わか）", STORE), ([{"n": "若"}], ["（わか）"]),
         "a reading in a bracket is handed back as the literal it is, so an English page can take "
         "it off without this rule being written twice")
    s.eq(creditline.coverage("[[翻訳協力]][BPS株式会社] / [著]時一二", STORE), "",
         "a field the division accounts for reports nothing left over")
    s.eq(creditline.coverage("宮澤伊織(早川書房刊)", STORE), "",
         "and a bracket the splitter drops on purpose is accounted for: an imprint note is not a "
         "contributor")
    s.eq(creditline.coverage("ヨン / 読切", STORE), "読切",
         "WHAT IT CANNOT ACCOUNT FOR IS REPORTED AND NOT SWALLOWED. A format tag in the author "
         "position is dropped by the splitter with good reason and is still something the field "
         "said, and this is the flag that stops the 発売 tab rebuilding a byline out of a "
         "division that does not cover it")
    s.eq(creditline.divide("", STORE), [], "an empty field divides into nothing")

    # ── the vocabulary the gloss table has to answer for ──────────────────────────────────────
    s.eq(creditline.roles_stated(["[著]嵩乃朔", "南部くまこ(作)"], STORE), ["作", "著"],
         "the roles a corpus states, which is what `every credit role has an English gloss` asks "
         "the interface about")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "creditline"))
