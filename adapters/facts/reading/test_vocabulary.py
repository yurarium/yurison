#!/usr/bin/env python3
"""facts/reading/vocabulary.py: which words in a string the analyser was guessing at.

COVERS = ['adapters/facts/reading/vocabulary.py',
          'adapters/names/analyser_vocabulary.py']

Every morpheme list here is what SudachiPy returns for that string, copied out of a run against
SudachiDict-core 20260723. Writing them out keeps the suite offline and lets a reader see the
analyser's answer beside the rule applied to it.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))

import testkit                                                          # noqa: E402
from facts.reading import vocabulary as v                               # noqa: E402

COMMON = ("名詞", "普通名詞", "一般", "*", "*", "*")
PROPER = ("名詞", "固有名詞", "一般", "*", "*", "*")
PARTICLE = ("助詞", "格助詞", "*", "*", "*", "*")
PRONOUN = ("代名詞", "*", "*", "*", "*", "*")


def main(s):
    # THE THREE TITLES THE OWNER REPORTED, each with the analyser's own answer for it.
    s.eq(v.doubt("レズ風俗アンソロジーリピーター",
                 [("レズ", COMMON, False), ("風俗", COMMON, False),
                  ("アンソロジー", COMMON, False), ("リピーター", COMMON, False)]),
         None, "風俗 is ordinary vocabulary and the mark has nothing to say about it")
    s.eq(v.doubt("百合アンソロジー",
                 [("百合", COMMON, False), ("アンソロジー", COMMON, False)]),
         None, "百合 is the word this database is about, read the way it is always read")
    s.eq(v.doubt("私に体",
                 [("私", PRONOUN, False), ("に", PARTICLE, False), ("体", COMMON, False)]),
         None, "and 私 and 体 are as fundamental as kanji get")

    # A PROPER NOUN KEEPS IT. This is the population the stored note names first, and the mark was
    # written for it.
    s.eq(v.doubt("東京物語", [("東京", PROPER, False), ("物語", COMMON, False)]),
         v.PROPER_NOUN, "a name in the string is what the analyser is worst at")

    # A WORD THE DICTIONARY DOES NOT HOLD KEEPS IT, whatever part of speech the analyser guessed.
    s.eq(v.doubt("葬焔", [("葬焔", COMMON, True)]),
         v.OUT_OF_VOCABULARY, "an out-of-vocabulary word was read by guessing at the characters")

    # THE THIRD SHAPE, WHICH NEITHER OF THE FIRST TWO CAN SEE. 単話 is タンワ and the analyser has
    # no entry for it, so it reads 単 and 話 as two ordinary in-vocabulary words and returns
    # タンハナシ with nothing flagged anywhere.
    s.eq(v.doubt("単話", [("単", COMMON, False), ("話", COMMON, False)]),
         v.SPLIT_COMPOUND, "a compound the dictionary does not hold is a coinage it read blind")
    s.eq(v.doubt("総選挙", [("総選挙", COMMON, False)]),
         None, "while the same compound held as one word is a lookup")

    # THE COUNTER-CASE FOR THAT RULE, and it is why the rule is about a kanji RUN and not about
    # adjacent morphemes. 女の子 is one morpheme spanning kana, and its two kanji are two runs of
    # one character each, neither of which any compound rule should be looking at.
    s.eq(v.doubt("女の子", [("女の子", COMMON, False)]), None, "one morpheme covers both runs")
    s.eq(v.doubt("恋と嘘", [("恋", COMMON, False), ("と", PARTICLE, False),
                           ("嘘", COMMON, False)]),
         None, "and two one-character words separated by kana are not a split compound")

    # IT CHECKS ITSELF. Morphemes that do not add up to the string are some other string's, and the
    # honest answer about this one is that nothing has been established.
    s.eq(v.doubt("総選挙", [("総選", COMMON, False)]),
         v.NOT_THIS_STRING, "morphemes that do not spell the surface answer nothing about it")
    s.eq(v.doubt("", []), v.NOT_THIS_STRING, "and neither does nothing at all")

    s.eq(v.ordinary("百合", [("百合", COMMON, False)]), True, "ordinary is doubt read as a yes/no")
    s.eq(v.ordinary("百合", [("百合", PROPER, False)]), False,
         "and 百合 tagged as a name is the same string with a different claim on it")

    # THE PASS THAT APPLIES IT. `proposals` takes the tokeniser as an argument precisely so this
    # runs with no dictionary installed.
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))
    import analyser_vocabulary as av

    class FakeMorpheme:
        def __init__(self, surface, pos, oov):
            self._s, self._p, self._o = surface, pos, oov

        def surface(self):
            return self._s

        def part_of_speech(self):
            return self._p

        def is_oov(self):
            return self._o

    TOKENS = {
        "百合アンソロジー": [FakeMorpheme("百合", COMMON, False),
                            FakeMorpheme("アンソロジー", COMMON, False)],
        "東京物語": [FakeMorpheme("東京", PROPER, False), FakeMorpheme("物語", COMMON, False)],
        "単話": [FakeMorpheme("単", COMMON, False), FakeMorpheme("話", COMMON, False)],
    }
    records = {
        "百合アンソロジー": {"reading": "ユリ アンソロジー", "reading_basis": "analyser"},
        "東京物語": {"reading": "トウキョウ モノガタリ", "reading_basis": "analyser"},
        "単話": {"reading": "タン ハナシ", "reading_basis": "analyser",
                 "reading_ordinary": True},
        "恋する小惑星": {"reading": "コイ スル アステロイド", "reading_basis": "stated"},
    }
    marked, why = av.apply(records, lambda t: TOKENS[t])
    s.eq(sorted(k for k, on in marked.items() if on), ["百合アンソロジー"],
         "one title stops being doubted")
    s.eq(records["百合アンソロジー"].get("reading_ordinary"), True, "and says so on the record")
    s.eq(records["東京物語"].get("reading_ordinary"), None, "a name in the title keeps the doubt")
    # A STALE MARK IS TAKEN OFF. `boundary.restate_donor_bases` takes the same line: a field saying
    # something about a record that stopped being true is worse than no field.
    s.eq(records["単話"].get("reading_ordinary"), None,
         "and a record that no longer qualifies loses the field rather than keeping it")
    s.eq(records["恋する小惑星"].get("reading_ordinary"), None,
         "a reading a source states is not this pass's business")
    s.eq(why[v.SPLIT_COMPOUND], 1, "the refusals are counted by kind")

    # IDEMPOTENT, because build.py calls it on every build.
    again, _ = av.apply(records, lambda t: TOKENS[t])
    s.eq(again, {}, "a second run has nothing to add")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
