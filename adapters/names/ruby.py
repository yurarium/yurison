#!/usr/bin/env python3
"""The furigana a record carries, as spans over the string it was written for.

WHY THIS IS A MODULE. The spans are a function of the reading and of the SPELLING they sit over, so
`仲谷 鳰` and `仲谷鳰` do not get the same answer: one parts the name in two and the other reads it
as one word. `feed/names.json` ships one entry per FOLD, and a row showing the record filed under
the spaced spelling has to show that record's spans, so the store needs both and cannot derive the
second from the first. STORE-PLAN §6, and §3 is why the rule is here rather than copied.

FURIGANA OVER A PERSON'S NAME HAS TO REST ON SOMETHING. An analyser is at its weakest on pen names
and it does not decline: 古川楊也 is stored ホシノ カツラ, which is a different person's name, and
it was being printed over theirs. A reading a source states, or that a person researched and cited,
gets furigana; a machine's guess does not, and nothing replaces it.

THE RUBY MUST SPELL THE READING. Spans and readings are produced by different paths, the analyser
tokenises while a sourced reading arrives whole, and nothing forced them to agree: three records
ended up reading ワタシ while their ruby said わたくし, which is one record contradicting itself on
the same line of the page. So stored spans are used only when they reconstruct the stored reading.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kana as _kana                                                    # noqa: E402
import pass4_analyser as _p4                                            # noqa: E402

#: A reading nobody answers for, which is what withholds furigana from a personal name. ASKED OF
#: `pass4_analyser`, which owns which bases are a machine's answer: it is the same set the register
#: table may take back, because both questions are `did anybody state this`.
GUESSED = _p4.OVERRULABLE


def spans(spelling, rec, is_person=False):
    """The ruby a record shows over `spelling`, or None where it shows none."""
    reading = (rec or {}).get("reading")
    if not reading:
        return None
    if is_person and rec.get("reading_basis") in GUESSED:
        return None
    got = rec.get("furigana_spans")
    if got and not _kana.ruby_spells(got, reading):
        got = None
    if not got:
        # The reading keeps its spaces. Where the surface is spaced the same way they are the
        # boundary, and align() strips them itself when they are not.
        aligned = _kana.align(spelling, reading)
        got = [[t, _kana.to_hiragana(x) if x else None] for t, x in aligned] if aligned else None
    # THE UNIT OF RUBY IS THE WORD. A run cut into one span per character is mono-ruby, which the
    # typesetting rules distinguish from jukugo-ruby and do not prefer for a compound, and the split
    # was a claim nobody made: 総選挙 is one word read ソウセンキョ, and そう over 総 with きょ over
    # 挙 came from a table of per-character readings the analyser never consulted.
    got = _katakana(got, rec.get("ruby_katakana"))
    return got if got and any(x[1] for x in got) else None


def _katakana(got, words):
    """The spans with each word in `words` carrying its ruby in katakana, as one span.

    RUBY IS SET IN HIRAGANA EXCEPT WHERE THE SOURCE SETS IT IN KATAKANA, and a reading cannot say
    which: the store writes every reading in katakana, so トウヒコウ and エスケープ look alike in it.
    The difference is that エスケープ is a loanword the title puts over 逃避行 in place of its
    reading, and マガポケ's banner prints it in katakana, as ruby of that kind is printed. Converting
    it to えすけーぷ is a spelling nobody printed. So `ruby_katakana` names the words, written by a
    person who looked at the ruby, and no rule guesses them.

    ONE SPAN PER WORD, because ruby of this kind belongs to the word: the aligner may part 逃避行
    and still spell the reading, and エス over 逃避 with ケープ over 行 is a division nobody set.
    """
    if not got or not words:
        return got
    out = [list(x) for x in got]
    for word in words:
        for i in range(len(out)):
            text, j = "", i
            while j < len(out) and len(text) < len(word):
                text += out[j][0]
                j += 1
            if text == word and all(x[1] for x in out[i:j]):
                read = _kana.to_katakana("".join(x[1] for x in out[i:j]))
                out[i:j] = [[word, read]]
                break
    return out
