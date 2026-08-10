#!/usr/bin/env python3
"""Which of the words in a string an analyser was actually guessing at.

WHY THIS EXISTS. `pass4_analyser` stamps every reading it produces `verified: false`, and the note
it stores beside each one gives the mark its justification: "reading guessed by a morphological
analyser, not stated by any source; analysers are weakest on pen names and coinages". That names
two populations, and the mark was being drawn on neither. 私 in `私に体、売ってみない?`, 風俗 in
`レズ風俗アンソロジーリピーター` and 百合 in `いちゃらぶしかない百合アンソロジーコミックsugar`
are ordinary dictionary words in their ordinary readings, and the last of them is the word this
database is about.

THE OWNER RULED ON 2026-08-10: "for such fundamental kanji, the lack of special information should
just be evidence that they have the obvious readings, for a title". This is that ruling written
down where the code can ask it.

WHAT THE ANALYSER IS ASKED HERE, AND WHY IT IS A DIFFERENT QUESTION. Not for a reading. Sudachi
tags every morpheme with a part of speech and says whether the dictionary held it at all, and
segmenting text and labelling it is the job a morphological analyser is built for. Producing the
reading of a coinage is the job it cannot decline and is bad at. So the doubt is decided by the
first and applies to the second, which is the same shape as `facts/division/boundary.from_analyser`:
a morpheme boundary became a NAME boundary only where the analyser said 固有名詞 人名 姓 and then
名, and here an analyser reading becomes an unmarked one only where the analyser says every word in
the string is ordinary vocabulary it holds.

WHAT KEEPS THE DOUBT, each of them measured against the title store before it was written.

  A PROPER NOUN. 固有名詞 is the analyser saying this is a name, a place or a title, which is the
  population the note names first. 396 of 2,663 analyser-read titles hold one.

  A WORD THE DICTIONARY DOES NOT HOLD. `is_oov` is the analyser saying it had no entry and read the
  characters anyway, which is the other population the note names. 355 titles hold one.

  A COMPOUND THE DICTIONARY DOES NOT HOLD, which neither of the first two can see and which is 419
  more. Where SudachiDict has no entry for a kanji compound it quietly reads each character as a
  word of its own, and each of those characters IS an ordinary in-vocabulary morpheme: 単話 comes
  back 単/タン + 話/ハナシ, which is タンハナシ for a word every reader says タンワ, and 残蝕 comes
  back ザン + ショク with nothing anywhere reporting a difficulty. So a kanji run the analyser did
  not cover with one morpheme is a coinage by the analyser's own admission, whatever the parts are.

  `pass4_analyser.unrecognised_compound` sees a NARROWER version of this, and deliberately: it
  fires only where the split pair mixes an on reading with a kun one, because it feeds a separate
  mark that says the reading was assembled character by character. 100日後 is 日 + 後 and is read
  correctly, so it is not worth a reader's attention there. It is worth it here, because the
  question is not "is this reading probably wrong" but "did anything establish this reading", and
  a compound nobody has an entry for establishes nothing.

RULES TRIED AND REJECTED, so they are not re-derived.

  ONE READING IN THE DICTIONARY, meaning the analyser had no choice to get wrong. It reads well and
  it contradicts the ruling: `Dictionary.lookup` gives 体 three readings, 女 six and 私 five, and
  those are exactly the fundamental kanji the owner names. A rule that doubts 体 because カラダ,
  テイ and タイ are all attested doubts the whole of ordinary Japanese.

  THE ANALYSER'S CHOICE BETWEEN ATTESTED READINGS, which is the failure 抱かれたい女 really had:
  イダカレタイ is the literary reading of a word said ダカレタイ, and every morpheme in that title
  is ordinary in-vocabulary vocabulary, so nothing here keeps its mark. SudachiPy exposes no
  ranking between the entries for one surface, so there is nothing to test on. That failure is
  answered where it belongs, in `pass4_analyser.READING_OVERRIDE`, and the residue is stated rather
  than hidden: this says the analyser was not guessing about which WORDS it read, and it says
  nothing about register.

WHAT THIS IS NOT ASKED ABOUT. People. NAMES-PLAN §1 keeps a different standard for a person's name,
because a mis-read title is a small correctable error about a book and a mis-read name misnames
somebody under their own work, and §5c says the mark on an author is where it is doing the real
work. An author name is also the case the note was written for. The caller restricts this to
titles; nothing here would stop it being asked about a person, and the reason it is not is a ruling
and not an oversight.
"""
import re

#: A kanji run the analyser must cover with a single morpheme. 々 repeats the character before it
#: and belongs to the run it sits in: 段々 is one word or it is a coinage, and either way it is not
#: two runs.
KANJI_RUN = re.compile(r"[一-鿿々]{2,}")

#: Why the doubt stands, as a value a caller can count. Silence about which of these applied is how
#: a pass that stopped finding anything reads exactly like a pass with nothing left to find.
PROPER_NOUN = "a proper noun, where an analyser is weakest"
OUT_OF_VOCABULARY = "a word the dictionary does not hold"
SPLIT_COMPOUND = "a compound the dictionary does not hold, read a character at a time"
NOT_THIS_STRING = "the morphemes are not this string's"
READING_HAS_MOVED = "the analyser no longer reads it the way the record holds it"

PROPER = "固有名詞"


def doubt(surface, morphemes):
    """Why an analyser reading of `surface` is a guess, or None where every word in it is ordinary.

    `morphemes` is `[(surface, part_of_speech, is_oov)]` in order, as the analyser returned them.
    Tuples rather than the analyser's own objects, so this is a rule a test can state in one line
    and a fixture can hold.

    IT CHECKS ITSELF, like `boundary.from_analyser`. The morphemes must concatenate to exactly the
    string they are supposed to be of, or they are some other string's and answer nothing about
    this one. A caller re-tokenising a stored record after the dictionary moved under it is the way
    that happens, and the honest answer there is that the doubt stands.
    """
    surface = str(surface or "")
    parts = list(morphemes or ())
    if not surface or not parts:
        return NOT_THIS_STRING
    if "".join(str(p[0] or "") for p in parts) != surface:
        return NOT_THIS_STRING
    for _s, pos, oov in parts:
        if oov:
            return OUT_OF_VOCABULARY
        if PROPER in tuple(pos or ()):
            return PROPER_NOUN
    # WHERE EACH MORPHEME BEGINS, by arithmetic on the surfaces rather than by asking the analyser
    # for an offset. The concatenation above is what makes that sound, and it keeps the argument
    # this function takes to something a test can write out.
    spans, at = [], 0
    for p in parts:
        spans.append((at, at + len(str(p[0] or ""))))
        at += len(str(p[0] or ""))
    for run in KANJI_RUN.finditer(surface):
        if not any(a <= run.start() and run.end() <= b for a, b in spans):
            return SPLIT_COMPOUND
    return None


def ordinary(surface, morphemes):
    """Whether every word in `surface` is ordinary vocabulary the analyser holds."""
    return doubt(surface, morphemes) is None
