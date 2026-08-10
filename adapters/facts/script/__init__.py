#!/usr/bin/env python3
"""Which writing system a string is in. Four questions, four names, one home.

WHY THIS IS A FACT. A census on 2026-08-10 found thirty distinct regexes asking some version of "is
this Japanese", and the answer decides whether a string reaches the English floor, so a
disagreement is reader-visible. They were not all wrong and they were not all the same question.

WHAT THE CORPUS SETTLED, measured over its 6,076 surfaces:

    `[\\u3040-ヿ一-鿿々]` and `[\\u3040-ヿ㐀-鿿豈-\\ufaff]` AGREE on every one of them. The second
    adds CJK extension A and the compatibility ideographs, and the corpus holds one character of
    the first block and none of the second, so the wider class costs nothing and is kept.

    `check.JAPANESE`, which also admits CJK punctuation and full-width forms, differs on 18:
    `ＦＬＯＷＥＲＣＨＩＬＤ`, `ＢＵＮＢＵＮ`, `【English ver】The Monsters of Summer`. Those are Latin
    in full-width and Latin inside Japanese brackets. That is Japanese TYPOGRAPHY with no Japanese
    SCRIPT, which is a different question and gets a different name.

AND ONE OF THEM WAS SIMPLY WRONG. `[ぁ-ゖァ-ヿ]` treats `・` as kana, because the interpunct sits at
U+30FB inside the katakana block. `flower・flower` and `百合百景・夜伽` came back as containing kana
under two of the three kana tests. A separator is not a letter.
"""
import re

#: Kana, and nothing that merely lives in the kana blocks. `ー` and `ヿ` are letters here, the first
#: because it carries a mora and the second because it is a katakana ligature; `・` is not, because
#: it separates. That distinction is the whole of `facts/credit`'s
#: interpunct rule and it has to hold here too.
_KANA = re.compile(r"[ぁ-ゖァ-ヺヽヾゝゞーヿ]")

#: Han, with the iteration mark and CJK extension A. The corpus holds one ext-A character, 多㐂, and
#: a test that missed it would say that name has no kanji.
_KANJI = re.compile(r"[一-鿿㐀-䶿々\uf900-\ufaff]")

#: Either. This is what most callers mean by "is this Japanese".
#: THE SAFETY NET SPANS WHOLE BLOCKS, where the letter tests above span letters. `has_script` is
#: what asks whether Japanese has reached an English page, and there the cost of missing something
#: is a reader seeing Japanese where they asked for English, so it takes the hiragana and katakana
#: blocks entire, unassigned slots and all. `test_interface` pins the block boundaries for exactly
#: this reason and caught it when the class was narrowed to assigned characters.
_SCRIPT = re.compile(r"[\u3040-\u30ff一-鿿㐀-䶿々\uf900-\ufaff]")

#: Script, or the punctuation and widths a Japanese text uses. A different question: it is true of
#: `ＦＬＯＷＥＲＣＨＩＬＤ`, which holds no Japanese letter at all.
_TYPOGRAPHY = re.compile(r"[\u3040-\u30ff一-鿿㐀-䶿々\uf900-\ufaff　-〿＀-￯]")


def has_kana(s):
    """Whether any character is kana. `・` is not, because a separator is not a letter."""
    return bool(_KANA.search(str(s or "")))


def has_kanji(s):
    """Whether any character is han, including the iteration mark and extension A."""
    return bool(_KANJI.search(str(s or "")))


def has_script(s):
    """Whether any character is written in Japanese. What most callers mean."""
    return bool(_SCRIPT.search(str(s or "")))


def has_typography(s):
    """Whether the string uses Japanese punctuation or widths, even with no Japanese letter.

    `ＦＬＯＷＥＲＣＨＩＬＤ` is true here and false for `has_script`, which is the distinction the
    eighteen differing surfaces are about.
    """
    return bool(_TYPOGRAPHY.search(str(s or "")))


def is_all_kana(s):
    """Whether every character is kana, allowing the spacing and separators a name carries."""
    t = str(s or "")
    return bool(t) and all(has_kana(c) or c in "・･ 　" for c in t)
