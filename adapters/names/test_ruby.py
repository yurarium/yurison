#!/usr/bin/env python3
"""names/ruby: the furigana a record shows, over the spelling it was written for.

COVERS = ['adapters/names/ruby.py']

WHY THE RULE MOVED HERE. STORE-PLAN §6 needs the store to reach the same spans the build does, and
they are a function of the reading AND of the spelling they sit over, so `仲谷 鳰` and `仲谷鳰` do
not get the same answer. A second implementation would be the one that disagrees, and each assertion
below is a fault that shipped once.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))
import testkit                                                          # noqa: E402
from names import ruby                                                  # noqa: E402


def main(s):
    stated = {"reading": "ナカタニ ニオ", "reading_basis": "stated"}

    # ── THE SPANS ARE OVER A SPELLING, AND THE FOLD IS A DIFFERENT SPELLING ───────────────────
    spaced = ruby.spans("仲谷 鳰", stated, is_person=True)
    closed = ruby.spans("仲谷鳰", stated, is_person=True)
    s.check(spaced != closed,
            "a spaced spelling and its fold do not get the same furigana")
    s.eq("".join(t for t, _r in spaced), "仲谷 鳰", "and each set spells its own surface")
    s.eq("".join(t for t, _r in closed), "仲谷鳰", "including the one with no space in it")

    # ── FURIGANA OVER A PERSON'S NAME HAS TO REST ON SOMETHING ────────────────────────────────
    #
    # An analyser is at its weakest on pen names and it does not decline: 古川楊也 is stored
    # ホシノ カツラ, which is a different person's name, and it was being printed over theirs.
    guessed = {"reading": "ナカタニ ニオ", "reading_basis": "analyser"}
    s.eq(ruby.spans("仲谷鳰", guessed, is_person=True), None,
         "a machine's guess at a person's name gets no furigana")
    s.check(ruby.spans("仲谷鳰", guessed, is_person=False),
            "AND A TITLE KEEPS ITS OWN, because a title read wrongly is an error and a name read "
            "wrongly misnames somebody")

    # ── THE RUBY MUST SPELL THE READING ───────────────────────────────────────────────────────
    #
    # Spans and readings are produced by different paths and nothing forced them to agree: three
    # records read ワタシ while their ruby said わたくし, one record contradicting itself.
    contradicts = {"reading": "ワタシ", "reading_basis": "stated",
                   "furigana_spans": [["私", "わたくし"]]}
    got = ruby.spans("私", contradicts)
    s.check(got != [["私", "わたくし"]],
            "stored spans that do not reconstruct the stored reading are not used")

    agrees = {"reading": "ワタシ", "reading_basis": "stated", "furigana_spans": [["私", "わたし"]]}
    s.eq(ruby.spans("私", agrees), [["私", "わたし"]], "and spans that do are kept as they are")

    # ── RUBY THE SOURCE SETS IN KATAKANA STAYS IN KATAKANA ────────────────────────────────────
    #
    # マガポケ's banner prints エスケープ over 逃避行, and the reading cannot say so, because the
    # store writes every reading in katakana. Shown as えすけーぷ, it was a spelling nobody printed.
    escape = {"reading": "ルカ ト アンジュ ノ エスケープ", "reading_basis": "stated"}
    plain = ruby.spans("瑠夏と杏珠の逃避行", escape)
    s.eq(plain[-1], ["逃避行", "えすけーぷ"], "ruby is hiragana unless somebody says otherwise")
    marked = ruby.spans("瑠夏と杏珠の逃避行", dict(escape, ruby_katakana=["逃避行"]))
    s.eq(marked[-1], ["逃避行", "エスケープ"], "and the word a person marked keeps its katakana")
    s.eq(marked[:-1], plain[:-1], "while the rest of the title stays in hiragana")
    parted = {"reading": "エスケープ", "reading_basis": "stated",
              "furigana_spans": [["逃避", "えす"], ["行", "けーぷ"]]}
    s.eq(ruby.spans("逃避行", dict(parted, ruby_katakana=["逃避行"])), [["逃避行", "エスケープ"]],
         "as one span over the word, however the aligner parted it")
    s.eq(ruby.spans("逃避行", dict(parted, ruby_katakana=["逃亡"])), parted["furigana_spans"],
         "and a word that is not there changes nothing")

    # ── AND A STRING WITH NOTHING TO READ TAKES NONE ──────────────────────────────────────────
    s.eq(ruby.spans("ナカタニ", {"reading": "ナカタニ", "reading_basis": "surface"}), None,
         "a surface already in kana carries no furigana, because there is nothing over it to say")
    s.eq(ruby.spans("仲谷鳰", {}), None, "and a record with no reading shows nothing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
