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

#: A reading nobody answers for, which is what withholds furigana from a personal name.
GUESSED = ("analyser", "back-converted")


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
    return got if got and any(x[1] for x in got) else None
