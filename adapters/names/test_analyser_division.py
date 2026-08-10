#!/usr/bin/env python3
"""analyser_division: a glued analyser reading takes the division the analyser already made.

COVERS = ['adapters/names/analyser_division.py']

OFFLINE, so the tokeniser is supplied. What is being tested is which records the pass OFFERS to
divide, and the answer has to be none of the ones a morpheme boundary would have split.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import analyser_division as m                                           # noqa: E402

SURNAME = ("名詞", "固有名詞", "人名", "姓")
GIVEN = ("名詞", "固有名詞", "人名", "名")
COMMON = ("名詞", "普通名詞", "一般", "*")


class _Morph:
    def __init__(self, surface, reading, pos):
        self._s, self._r, self._p = surface, reading, pos

    def surface(self):
        return self._s

    def reading_form(self):
        return self._r

    def part_of_speech(self):
        return self._p


class _Tok:
    """A tokeniser that answers from a table, so the suite runs with no dictionary installed."""

    def __init__(self, table):
        self.table = table

    def tokenize(self, s):
        return [_Morph(*t) for t in self.table.get(s, [(s, s, COMMON)])]


def main(s):
    tok = _Tok({
        "上田香子": [("上田", "ウエダ", SURNAME), ("香子", "キョウコ", GIVEN)],
        "くろば": [("くろ", "クロ", COMMON), ("ば", "バ", COMMON)],
        "ゆり山": [("ゆり", "ユリ", GIVEN), ("山", "サン", COMMON)],
    })
    records = {
        "上田香子": {"reading": "ウエダキョウコ", "reading_basis": "analyser"},
        "くろば": {"reading": "クロバ", "reading_basis": "analyser"},
        "ゆり山": {"reading": "ユリサン", "reading_basis": "analyser"},
    }
    got = m.proposals(records, tokenise=tok)
    s.eq(got, {"上田香子": "ウエダ キョウコ"},
         "only the record whose halves the analyser calls a surname and a given name")

    # A READING THAT IS NOT THE ANALYSER'S IS NOT THIS PASS'S BUSINESS. A stated reading with no
    # division is somebody's transcription and the analyser has no standing to respace it.
    stated = {"上田香子": {"reading": "ウエダキョウコ", "reading_basis": "stated"}}
    s.eq(m.proposals(stated, tokenise=tok), {}, "a stated reading is left alone")

    # NOR IS ONE THAT ALREADY DIVIDES, or a division somebody supplied would be overwritten by a
    # weaker one, which is the direction that erases.
    divided = {"上田香子": {"reading": "ウエダ キョウコ", "reading_basis": "analyser"}}
    s.eq(m.proposals(divided, tokenise=tok), {}, "a reading that already divides is left alone")
    held = {"上田香子": {"reading": "ウエダキョウコ", "reading_basis": "analyser",
                        "reading_boundary": "somebody else's"}}
    s.eq(m.proposals(held, tokenise=tok), {},
         "and so is one that already records where its division came from")

    # THE BASIS IT WRITES IS THE ANALYSER'S, which cites nobody and stays marked.
    s.eq(m.BASIS, "analyser", "the division rests on the analyser and says so")

    # A MISSING TOKENISER WRITES NOTHING rather than dividing nothing quietly, which is the same
    # answer the pass gives on a machine without sudachi.
    s.eq(m.proposals(records, tokenise=None) if m._tokeniser() is None else {}, {},
         "no tokeniser, no proposals")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "analyser_division"))
