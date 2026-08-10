#!/usr/bin/env python3
"""facts/script: which writing system a string is in.

COVERS = ['adapters/facts/script/__init__.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))
import testkit                                                          # noqa: E402
from facts import script as sc                                          # noqa: E402


def main(s):
    s.check(sc.has_kana("ゆり"), "hiragana is kana")
    s.check(sc.has_kana("ユリ"), "and katakana")
    s.check(sc.has_kana("ビール"), "and the long vowel mark, which carries a mora")

    # THE BUG THIS FOUND. `・` sits at U+30FB inside the katakana block, so `[ぁ-ゖァ-ヿ]` called it
    # kana and `flower・flower` came back as containing kana. A separator is not a letter.
    s.check(not sc.has_kana("flower・flower"), "the interpunct is not kana")
    s.check(not sc.has_kana("百合百景"), "and kanji is not kana")
    s.check(not sc.has_kana("NOAH"), "nor Latin")

    s.check(sc.has_kanji("百合"), "han is kanji")
    s.check(sc.has_kanji("多㐂"), "including extension A, which the corpus holds once")
    s.check(sc.has_kanji("多分洋々"), "and the iteration mark")
    s.check(not sc.has_kanji("ユリ"), "kana is not kanji")

    s.check(sc.has_script("ゆり") and sc.has_script("百合"), "either counts as Japanese script")
    s.check(not sc.has_script("NOAH"), "Latin does not")

    # THE EIGHTEEN THAT DIFFERED. Latin in full-width, and Latin inside Japanese brackets: Japanese
    # typography with no Japanese letter in it.
    s.check(not sc.has_script("ＦＬＯＷＥＲＣＨＩＬＤ"), "full-width Latin is not Japanese script")
    s.check(sc.has_typography("ＦＬＯＷＥＲＣＨＩＬＤ"), "but it is Japanese typography")
    s.check(sc.has_typography("【English ver】"), "as are the brackets")
    s.check(not sc.has_typography("plain ascii"), "and plain ASCII is neither")

    s.check(sc.is_all_kana("ヤスダ コウスケ"), "a spaced kana name is all kana")
    s.check(sc.is_all_kana("くろば・Ｕ") is False, "one with Latin in it is not")
    s.check(not sc.is_all_kana(""), "and nothing is not all kana")

    for empty in ("", None):
        s.check(not sc.has_kana(empty) and not sc.has_script(empty), f"{empty!r} holds nothing")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
