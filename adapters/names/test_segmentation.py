#!/usr/bin/env python3
"""segmentation.py: a boundary the reading has and the title does not."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import segmentation as seg  # noqa: E402

COVERS = ["adapters/names/segmentation.py"]


def main(s):
    # THE FAULT. A katakana word the title writes as one, cut into pieces by the analyser.
    s.eq(seg.split_runs("セイキマツブルー", "セイ キマツ ブルー"),
         [("セイキマツブルー", "セイ キマツ ブルー")], "a split katakana word is reported with both forms")
    s.eq(seg.split_runs("セイキマツブルー", "セイキマツブルー"), [],
         "and the same word unbroken is not")

    # WHAT MAKES THE OBVIOUS TEST WRONG. A reading is written word-separated, so particles stand
    # alone as one character. Flagging those marked 61% of the corpus, all of it correct.
    s.eq(seg.split_runs("100日後に咲く百合", "100 ニチゴ ニ サク ユリ"), [],
         "a particle standing alone is a reading doing its job")

    # A HIRAGANA RUN IS NOT ONE WORD and this refuses to guess: ゆりでなる is three.
    s.eq(seg.split_runs("ゆりでなる", "ユリ デ ナル"), [],
         "a hiragana run is not judged, because it is usually a phrase")
    s.check(seg.unmeasured("ゆりでなる♡えすぽわーる", "ユリ デ ナル ♡ エ スポ ワール"),
            "and a title carrying one is counted as unmeasured rather than clean")
    s.check(not seg.unmeasured("セイキマツブルー", "セイキマツブルー"),
            "while a katakana title is measurable and says so")

    # A reading of something else entirely is not a segmentation fault.
    s.eq(seg.split_runs("アルバイト", "ゼンゼン チガウ"), [], "an unalignable reading is not reported")
    s.eq(seg.split_runs("", ""), [], "and nothing in is nothing out")

    s.eq(seg.kata("えすぽわーる"), "エスポワール", "hiragana folds to katakana for the comparison")

    # REPAIR TAKES OUT SPACES AND NOTHING ELSE. A reading is a claim about pronunciation, so this
    # undoes a cut and never respells: the brackets and the full stop survive.
    s.eq(seg.repair("10年前（ナンバーナイン）", "10 ネン マエ （ナンバー ナイン）"),
         "10 ネン マエ （ナンバーナイン）", "a split word closes up and its brackets stay")
    s.eq(seg.repair("2DK、Gペン、アフタータイム。", "2DK、Gペン、アフター タイム。"),
         "2DK、Gペン、アフタータイム。", "and its full stop stays")
    s.eq(seg.repair("100日後に咲く百合", "100 ニチゴ ニ サク ユリ"), "100 ニチゴ ニ サク ユリ",
         "a correct reading is returned unchanged, particles and all")

    # WITH THE LEXICON, a hiragana loanword the corpus attests in katakana is repaired too.
    from names import lexicon as lx
    L = lx.build(["バケーションの話", "マドレーヌ日記"])
    s.eq(seg.repair("ばけーしょん魔王", "バ ケーション マオウ", L), "バケーション マオウ",
         "a hiragana loanword the corpus writes in katakana is closed up")
    s.eq(seg.repair("ゆりでなる", "ユリ デ ナル", L), "ユリ デ ナル",
         "and a hiragana phrase the corpus does not attest as a word is left alone")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
