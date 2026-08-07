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
    # A SPACED SURFACE AGAINST A SPACED READING. The solver takes the first split that fits and
    # tries the shortest first, so with the spaces stripped 狗之餌 took one kana and 廃狼 took the
    # other eight. The boundary is written on both sides and is used.
    s.eq(kana.align("狗之餌 廃狼", "イヌノエサ ハイロウ"),
         [("狗之餌", "イヌノエサ"), (" ", None), ("廃狼", "ハイロウ")],
         "a boundary written on both sides places the split")
    s.eq(kana.align("宮原 都", "ミヤハラ ミヤコ"),
         [("宮原", "ミヤハラ"), (" ", None), ("都", "ミヤコ")],
         "and does so where a naive split would still have fitted")
    # COUNTS MUST MATCH. A reading is word-separated and a surface is not, so spaces that do not
    # correspond say nothing and the whole-string search has to run as before.
    s.check(kana.align("ゆりでなるえすぽわーる", "ユリ デ ナル エスポワール"),
            "a reading spaced where the surface is not still aligns")
    # PUNCTUATION THE READING KEEPS IS ANCHORED ON. Letting a mark consume nothing let the kanji
    # run beside it swallow the mark: 翡翠 read ひ while 北 read すい、きた.
    s.eq(kana.align("翡翠、北", "ヒスイ、キタ"),
         [("翡翠", "ヒスイ"), ("、", None), ("北", "キタ")],
         "a mark the reading states pins the runs either side of it")
    # AND A READING THAT DROPS IT STILL ALIGNS, which is why the strict pass is a preference and
    # not a rule. 「」 appear in the surface and in neither reading.
    s.check(kana.align("「触れたい」は恋の始まり", "フレタイワコイノハジマリ"),
            "a reading that drops the surface's marks still aligns")
    # A SURFACE SPACED BEFORE A MARK. The reading's spaces come out, so a run of ` ～` has one
    # character the reading can spell and one it cannot. Requiring the whole run made the strict
    # pass fail and the kanji run beside it swallow the mark.
    s.eq(kana.align("百合探偵少女 ～朱理推～", "ユリ タンテイ ショウジョ   ～ アカリ スイ ～"),
         [("百合探偵少女", "ユリタンテイショウジョ"), (" ～", None),
          ("朱理推", "アカリスイ"), ("～", None)],
         "a run spaced before a mark still anchors on the mark")
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

    # A TITLE THAT FAILS TO ALIGN GETS NO FURIGANA AT ALL, so one unmatched character costs the
    # whole line. 169 of 842 kanji titles were in that state, and between them two causes account
    # for it: a particle spelled as it sounds, and punctuation the reading drops.
    s.eq(kana.align("あの子は優しすぎる。", "アノコワヤサシスギル。"),
         [("あの", None), ("子", "コ"), ("は", None), ("優", "ヤサ"), ("しすぎる。", None)],
         "the topic は reads ワ, and still anchors")
    s.check(kana.align("うさぎはかく語りき", "ウサギワカクカタリキ"),
            "including where it sits inside a longer run of kana")
    s.check(kana.align("この恋を星には願わない", "コノコイオホシニワネガワナイ"),
            "and を reading オ does the same")
    s.check(kana.align("「触れたい」は恋の始まり", "フレタイワコイノハジマリ"),
            "a reading that drops the surface's brackets still anchors")
    s.check(kana.align("「触れたい」は恋の始まり", "「フレタイ」ワコイノハジマリ"),
            "and one that keeps them is matched as written")

    # THREE MORE WAYS THE SAME CHARACTER IS WRITTEN ONE WAY AND READ ANOTHER, each of which cost
    # a whole title its furigana.
    s.check(kana.align("ゆりづくしの教室で", "ユリズクシノキョウシツデ"),
            "四つ仮名: づ and ず are one sound, and a reading records the sound")
    s.check(kana.align("アラサー美女は地味女に餌付けされる", "アラサアビジョワジミオンナニエズケサレル"),
            "a long vowel written ー and spelled out as a vowel are the same reading")
    s.check(kana.align("阿佐ヶ谷サキュバス同人物語", "アサガヤサキュバスドウニンモノガタリ"),
            "ヶ in a place name is read が, not as a small ケ")
    s.check(kana.align("竹ヶ原", "タケガハラ") and kana.align("竹ヶ原", "タケカハラ"),
            "and it takes either voicing, because both occur in real names")

    # A CHARACTER NOBODY CAN SEE. Three titles are stored with げ written as け followed by
    # U+3099 COMBINING VOICED SOUND MARK. The mark is not kana, so it fell out of every comparison
    # and left the surface one character longer than its reading, and the title lost its furigana.
    s.check(kana.align("銀玉の価値を上\u3051\u3099る方法", "ギンダマノカチヲアゲルホウホウ"),
            "a decomposed kana aligns the same as the composed one it renders as")

    # THE COMPARISON IS ASYMMETRIC AND ITS CALLERS MUST KNOW IT. A surface は may sound like わ;
    # a surface わ is never written は. Passing reading and surface the wrong way round rejected
    # correct ruby on three titles while the alignment that produced it was right.
    spans = kana.align("あの子は優しすぎる。", "アノコワヤサシスギル。")
    s.check(kana.ruby_spells(spans, "アノコワヤサシスギル。"),
            "ruby carrying the surface's は spells a reading that records ワ")
    s.check(kana.ruby_spells(kana.align("阿佐ヶ谷サキュバス同人物語", "アサガヤサキュバスドウニンモノガタリ"),
                             "アサガヤサキュバスドウニンモノガタリ"),
            "and ruby over ヶ spells a reading that records ガ")

    # WHICH TWO VOWELS MAKE THE LONG ONE. 女王 is ジョ オ ウ. Taking the オ into ジョ leaves the ウ
    # as a syllable of its own and gives jōu, which romanises nothing: the long vowel is オウ.
    s.eq(kana.romanise("ジョオウ", "macron"), "joō", "the long vowel is the pair that ends the run")
    s.eq(kana.romanise("ジョオウサマ", "macron"), "joōsama", "and the rest of the word follows it")
    s.eq(kana.romanise("ジョオウ", "double"), "joou", "the doubled style is unaffected either way")

    # A VOWEL KANA ONLY DEFERS TO WHAT FOLLOWS IT. Where nothing follows that would lengthen it,
    # the ordinary merge stands, which is most of the language.
    s.eq(kana.romanise("コオリ", "macron"), "kōri", "こおり is kōri; the オ has nothing to defer to")
    s.eq(kana.romanise("オオキイ", "macron"), "ōkii", "and おおきい keeps its long ō")
    s.eq(kana.romanise("トオル", "macron"), "tōru", "as does とおる")
    s.eq(kana.romanise("ジョウ", "macron"), "jō", "a plain じょう is one long vowel, not two")

    # ー IS NOT A VOWEL and cannot begin a long vowel of its own, so it never defers.
    s.eq(kana.romanise("オーウチ", "macron"), "ōuchi", "オー holds its lengthening across a following ウ")

    # THE COUNTER-CASE. The substitution must not invent an alignment: a reading that genuinely
    # does not spell the surface still fails, because ruby over the wrong character is the thing
    # this whole function is careful about.
    s.eq(kana.align("雨夜の月", "ゼンゼンチガウヨミ"), None,
         "a reading that does not spell the surface is still refused")
    s.eq(kana.align("あの子は優しすぎる。", "アノコワゼンゼンチガウ"), None,
         "and a partial match past the anchor does not carry it")
    s.eq(kana.align("ゆりづくしの教室で", "ユリズクシノキョウシツ"), None,
         "a reading missing the end of the title is still refused")
    s.eq(kana.align("アラサー美女", "アラサイビジョ"), None,
         "and ー stands for the vowel it lengthens, not for any vowel")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "kana"))
