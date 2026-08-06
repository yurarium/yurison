#!/usr/bin/env python3
"""pass4_analyser.py: the fallback that reads a name when no dictionary can.

COVERS = ['adapters/names/pass4_analyser.py']

Almost every case here is a wrong reading this project shipped. They are kept because the analyser
fails SILENTLY when it fails: it returns something plausible, never an error.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import pass4_analyser as p4


def main(s):
    # Script tests the rest of the module leans on.
    s.check(p4.has_kanji("田口"), "kanji detected")
    s.check(not p4.has_kanji("タグチ"), "katakana is not kanji")
    s.check(p4.is_kana_ch("ア"), "katakana is kana")
    s.check(not p4.is_kana_ch("A"), "a latin letter is not kana")
    s.eq(p4.kata("ゆり"), "ユリ", "readings are normalised to katakana")

    # A LETTER READ AS A UNIT was a real defect: Sudachi reads M as メートル and L as リットル, so
    # furigana appeared over Latin. The letter's own NAME is the only legitimate reading.
    s.check("M" in p4.LETTER_NAME, "single letters have their own names")
    s.eq(p4.LETTER_NAME["V"], "ブイ", "V reads as its name, which is why Vチューバー is allowed")
    s.eq(len(p4.LETTER_NAME), 26, "all 26 letters are covered, not a handful")

    # PARTICLE SOUND. 114 readings carried ハ where the word is spoken ワ, because は as a particle
    # is not は as a syllable. The fix is part-of-speech, and the table records the two cases.
    s.eq(p4.PARTICLE_SOUND.get("は"), "ワ", "は as a particle sounds ワ")
    s.eq(p4.PARTICLE_SOUND.get("へ"), "エ", "へ as a particle sounds エ")

    # An override table exists because some readings are simply known: 私 in a title is watashi,
    # and the analyser preferred ワタクシ until told otherwise.
    s.check(isinstance(p4.READING_OVERRIDE, dict), "an override table exists")
    s.check(len(p4.READING_OVERRIDE) > 0, "and it is populated")

    # Credit lines are not titles. 原作／宮澤伊織 was once romanised wholesale, producing
    # "Gensaku Kigō Miyazawa Iori": the role is a label to translate, the name is a name.
    s.check(p4.is_credit_line("原作／宮澤伊織"), "a credit line is recognised by its role marker")
    s.check(not p4.is_credit_line("君の名は"), "an ordinary title is not a credit line")

    s.check(p4.has_japanese("第1話"), "japanese detected")
    s.check(not p4.has_japanese("Chapter 1"), "plain english is not japanese")

    # Unihan gives on-yomi. It must return kana or nothing, never a romanised string, because
    # everything downstream derives romanisation FROM the kana (NAMES-PLAN §8.1).
    on = p4.unihan_on("山")
    s.check(on is None or all(p4.is_kana_ch(c) or c in "ー・" for c in on),
            f"a Unihan reading is kana or absent, got {on!r}")

    # THE FAILURE `fell_back` CANNOT SEE. Sudachi reports trouble only when it has no reading at
    # all. With no entry for a compound it reads each character as its own token, and each reading
    # is defensible alone: 葬焔 came back ソウ ホノオ, an on beside a kun, and nothing had failed so
    # nothing was flagged. Both halves of the test are needed, because adjacent single-character
    # tokens are ordinary: 100日後 is 日 + 後 reading ニチ ゴ, and there are 43 such pairs in the
    # catalogue against 4 that mix kinds.
    class FakeTok:
        def __init__(self, pairs):
            self.pairs = pairs

        def tokenize(self, s, mode=None):
            return [type("M", (), {"surface": (lambda self, v=a: v),
                                   "reading_form": (lambda self, v=b: v)})()
                    for a, b in self.pairs]

    s.check(p4.unrecognised_compound(FakeTok([("葬", "ソウ"), ("焔", "ホノオ")]), "葬焔"),
            "a compound split into an on reading and a kun reading is flagged")
    s.check(not p4.unrecognised_compound(FakeTok([("日", "ニチ"), ("後", "ゴ")]), "日後"),
            "two on readings side by side are how a compound normally reads")
    s.check(not p4.unrecognised_compound(FakeTok([("職場", "ショクバ")]), "職場"),
            "a 重箱 reading the analyser knows arrives whole and cannot be caught this way")
    s.check(not p4.unrecognised_compound(FakeTok([("私", "ワタシ"), ("の", "ノ"), ("本", "ホン")]),
                                         "私の本"),
            "characters separated by a particle are not a compound")

    # A VOLUME IS NOT A CHAPTER. 巻 was missing from the counter list, so ４巻 第３９話 matched the
    # bare-number branch as chapter four and the real chapter fell into the subtitle and was
    # romanised: "Ch. 4 Maki Dai 39Wa". 53 chapter names begin with a volume number.
    plain = lambda t: t                                                      # noqa: E731
    s.eq(p4.chapter_en("４巻 第３９話「瞑目アリア」", plain), 'Vol. 4, Ch. 39 “瞑目アリア”',
         "the volume is read off the front and the chapter inside is read as a chapter")
    s.eq(p4.chapter_en("2巻 第26話", plain), "Vol. 2, Ch. 26", "and full-width digits are the same")

    # THE SAME LABEL, WRAPPED. A bracket around a chapter label is punctuation, and CHAPTER_PAT
    # anchors at the start, so a wrapper made it miss and the whole thing was romanised. 186
    # phrases read "( Dai 18Wa ) Shippai no Tatsujin" and "[Dai 100Wa]shin Awasete".
    s.eq(p4.chapter_en("【第100話】心合わせて", plain), "Ch. 100 心合わせて",
         "a chapter in a lenticular bracket is a chapter")
    s.eq(p4.chapter_en("（第18話）失敗の達人", plain), "Ch. 18 失敗の達人",
         "and one in full-width parentheses is the same statement")
    s.eq(p4.chapter_en("[#49]Pair", plain), "Ch. 49 Pair",
         "a hash label in half-width brackets too")

    # A PLATFORM'S ROW INDEX IS NOT THE WORK'S CHAPTER NUMBER. コミックDAYS prefixes its own row number: "100.第94話しんゆうのたのみ" is row 100 carrying chapter 94, and it rendered
    # "Ch. 100 . Dai 94 Hanashi ...", wrong in the number as well as the romanising.
    s.eq(p4.chapter_en("100.第94話しんゆうのたのみ", plain), "Ch. 94 しんゆうのたのみ",
         "the work's own label outranks the list position it sits at")
    s.eq(p4.chapter_en("1.第1話", plain), "Ch. 1", "even where the two agree")
    s.eq(p4.chapter_en("07Chapter.12第6話-2", plain), "Ch. 6-2",
         "a row index carrying its own word is still a row index")

    # THE PREFIX MUST BE INDEX MATERIAL AND NOTHING ELSE. That is what keeps a real title safe:
    # 恋する第3惑星 has 第3 in it and is not chapter three of anything.
    s.eq(p4.chapter_en("恋する第3惑星", plain), None,
         "a title that happens to contain 第N is not a chapter label")

    # THE FALLBACK AGAIN. Where what follows the prefix is not a chapter label, the prefix stays.
    s.eq(p4.chapter_en("12.普通の話", plain), "Ch. 12 普通の話",
         "a bare number keeps its place when nothing better is claimed")
    s.check("." not in (p4.chapter_en("12.普通の話", plain) or "").split(" ", 2)[-1][:1],
            "and the separator belongs to neither the number nor the subtitle")

    # THE FALLBACK, and it is the reason this is safe. A bracket whose contents are not a chapter
    # is left exactly as it was, so a wrapper nobody anticipated costs nothing.
    s.eq(p4.chapter_en("【お知らせ】更新", plain), None,
         "a notice in a bracket is not a chapter and is not made into one")
    s.eq(p4.chapter_en("（前編）はじまり", plain), "Part 1 はじまり",
         "and a bracketed part marker still reads as the part it is")
    s.eq(p4.chapter_en("3巻発売フェア", plain), "Vol. 3 発売フェア",
         "a volume followed by something that is not a chapter keeps the volume")
    s.eq(p4.chapter_en("第12話 テスト", plain), "Ch. 12 テスト",
         "a chapter with no volume is unchanged")

    # A CIRCLED DIGIT IS A PART MARKER. NFKC folds it into the number beside it, so Step.14① came
    # out "Step.141", which reads as chapter one hundred and forty-one.
    s.eq(p4.part_marks("Step.14①"), "Step.14 (1)", "the part is bracketed, not absorbed")
    s.eq(p4.part_marks("第90話②"), "第90話 (2)", "wherever it sits")
    s.eq(p4.part_marks("no marker here"), "no marker here", "and a name without one is untouched")
    s.eq(p4.chapter_en("第90話②", plain), "Ch. 90-2",
         "a chapter-shaped name still hyphenates its part, which is the form that sorts")

    # THE CACHE INVALIDATES ITSELF. Every entry in phrases.yaml is derived, and the file was
    # written once per string and never revisited, so a fix to the renderer never reached what it
    # had already rendered. Three faults in one day came from that, each correct and invisible
    # until the file was emptied by hand. The fingerprint has to move when the renderer moves, and
    # stay put when it does not; a version number somebody remembers to bump is the same bug.
    before = p4.renderer_fingerprint()
    s.eq(p4.renderer_fingerprint(), before, "the same renderer fingerprints the same")
    was = p4.EXTRA_EN["番外編"]
    try:
        p4.EXTRA_EN["番外編"] = "Side story"
        s.check(p4.renderer_fingerprint() != before,
                "changing what a chapter renders as changes the fingerprint")
    finally:
        p4.EXTRA_EN["番外編"] = was
    s.eq(p4.renderer_fingerprint(), before, "and putting it back puts the fingerprint back")


    # LATIN IS READ AS ITSELF. Sudachi lowercases it, returning `jk` for `ＪＫ`, so `ＪＫすぷらっしゅ！`
    # was stored with a reading of `jk ス プラッ シュ！`: a case the analyser invented.
    s.eq(p4.latin_reading("ＪＫ"), "JK", "full-width letters fold to the same letters, cased as written")
    s.eq(p4.latin_reading("S"), "S", "half-width Latin, which was always right, is unchanged")
    s.eq(p4.latin_reading("ＦＬＯＳ　ＣＯＭＩＣ"), "FLOS COMIC", "and a run of them, spaces folded too")
    s.eq(p4.latin_reading("すぷらっしゅ"), None, "kana is not Latin, so the analyser answers for it")
    s.eq(p4.latin_reading("×"), None, "nor is a symbol carrying no letters")
    s.eq(p4.latin_reading(""), None, "and an empty surface reads as nothing")

if __name__ == "__main__":
    sys.exit(testkit.run(main, "pass4_analyser"))
