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


if __name__ == "__main__":
    sys.exit(testkit.run(main, "pass4_analyser"))
