#!/usr/bin/env python3
"""kana.py: reading to romanisation, title casing, and furigana alignment.

Every case below is one this project got wrong and shipped. They are kept as tests so the fix
cannot be undone by a later tidy-up, which is what STANDING-INSTRUCTIONS §2 asks for.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import kana


def main(s):
    # Three styles, all derived from the kana and none from each other (NAMES-PLAN §8.1). That is
    # what makes the reader's choice of style possible at render time.
    # romanise() returns lower case; title_case() decides capitalisation. Keeping them separate is
    # what lets a title and a personal name be cased by different rules from the same reading.
    s.eq(kana.romanise("ユウリ", "macron"), "yūri", "macron style")
    s.eq(kana.romanise("ユウリ", "double"), "yuuri", "double-vowel style")
    s.eq(kana.romanise("ユウリ", "plain"), "yuri", "plain style")
    s.eq(kana.title_case(kana.romanise("ユウリ", "macron")), "Yūri", "cased for display")

    # Script tests, which the English-only invariant leans on.
    s.check(kana.has_kanji("君の名は"), "kanji detected")
    s.check(not kana.has_kanji("ユウリ"), "katakana is not kanji")
    s.check(kana.has_kana("ゆり"), "kana detected")
    s.check(kana.has_latin("Vチューバー"), "latin detected inside a mixed string")

    # Case conversion both ways, since readings are stored as kana and rendered from them.
    s.eq(kana.to_hiragana("ユウリ"), "ゆうり", "katakana to hiragana")
    s.eq(kana.to_katakana("ゆうり"), "ユウリ", "hiragana to katakana")

    # TITLE CASE. Particles stay lower case, but the rule was once greedy enough to lower-case 名
    # in 君の名は, and punctuation broke it so that (watakushi Ni) came out instead of (Watakushi ni).
    s.eq(kana.title_case("kimi no na wa"), "Kimi no Na wa", "particles stay down, words go up")
    s.eq(kana.title_case("(watakushi ni)"), "(Watakushi ni)",
         "a word after an opening bracket is still the start of a word")
    s.eq(kana.title_case("yuri", particles=False), "Yuri", "particles=False still capitalises")

    # ALIGNMENT. Furigana are placed per token with backtracking; a whole-string fallback used to
    # destroy good parses when one character could not be read.
    spans = kana.align("君の名は", "きみのなは")
    s.check(spans is not None, "alignment returns spans for a readable title")
    if spans:
        flat = "".join(t for t, _ in spans)
        s.eq(flat, "君の名は", "the spans reassemble the exact surface")
        rd = "".join(r or kana.to_hiragana(t) for t, r in spans)
        s.eq(rd, "きみのなは", "the spans reassemble the exact reading")
        s.check(all(r is None or kana.has_kana(r) for _, r in spans),
                "a ruby reading is kana or absent, never romaji")

    # A reading that cannot be aligned must fail cleanly rather than inventing a pairing.
    bad = kana.align("君の名は", "ぜんぜんちがう")
    s.check(bad is None or "".join(t for t, _ in bad) == "君の名は",
            "a mismatched reading does not corrupt the surface")

    # JUKUGO-RUBY. Splitting a compound's reading across its characters, so じょう sits over 情
    # rather than over 純情. Accepted only when it is certain, because a reading placed over the
    # wrong character is worse than one placed over the whole word: the reader cannot tell.
    s.eq(kana.jukugo_split("純情", "ジュンジョウ"), [("純", "ジュン"), ("情", "ジョウ")],
         "a compound splits where each part is a reading of its character")
    s.eq(kana.jukugo_split("学校", "ガッコウ"), [("学", "ガッ"), ("校", "コウ")],
         "and 促音便 is a sound change, not a different word")
    s.eq(kana.jukugo_split("雨夜", "アマヨ"), None,
         "a split the table cannot support is declined rather than guessed")
    s.eq(kana.jukugo_split("純", "ジュン"), None, "one character is already its own ruby")
    s.eq(kana.jukugo_split("純情", ""), None, "and no reading splits into nothing")
    # THE PROPERTY THAT MATTERS. Whatever comes back must still spell the reading, or the ruby
    # contradicts the romanisation built from the same string.
    for word, rd in (("純情", "ジュンジョウ"), ("悪役", "アクヤク"), ("令嬢", "レイジョウ")):
        got = kana.jukugo_split(word, rd)
        s.eq("".join(x[1] for x in got), rd, f"the split of {word} still spells its reading")
        s.eq("".join(x[0] for x in got), word, f"and still spells {word}")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "kana"))
