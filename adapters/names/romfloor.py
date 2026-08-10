#!/usr/bin/env python3
"""The Latin form under every English rendering, for a name no source can spell.

WHAT THE OWNER RULED, and this module is that ruling made mechanical. Showing incorrect kana in
Japanese is the least acceptable thing this project can do. Showing an unclear romanisation in
English, marked, beside a tooltip saying it is unclear, is REQUIRED where the alternative is
Japanese text under an English heading. So an English page has a floor: whatever the store holds,
some Latin string is always available, and the reader is told when it is ours.

WHY IT IS COMPUTED HERE AND NOT IN THE BROWSER. `kana.romanise` is the one romanisation this
project has, three styles derived from a reading and none from each other. A copy of it in
JavaScript would be the shape STANDING-INSTRUCTIONS §3 counts seven shipped bugs from, and the two
would disagree the first time a rule changed on one side. So the build spells every Japanese string
that can reach a rendering surface, ships the three spellings beside the readings, and kari/app.js
looks the answer up. The browser decides nothing about how a name is spelt.

WHAT IT IS WORTH, WHICH IS LESS THAN A READING. A run of kana is a reading already and romanising
it is arithmetic. A run of kanji is a guess: the analyser reads what it recognises, and where it
recognises nothing each character is read alone, which gives the character's dictionary reading and
not its reading in a compound. 抱き came out カカエ where it is ダキ. Every string this produces is
therefore marked in the interface, and the mark is doing the real work.

  floor("よつばますみ")   -> Yotsubamasumi        kana, mechanical
  floor("百合姫編集部")   -> Yurihime Editorial Department
  floor("檜乃坂耀季")     -> a per-character guess, marked

THE DESK SUFFIX IS GLOSSED RATHER THAN ROMANISED. 編集部 is a common noun meaning the editorial
department of a magazine, and `Be編集部` is a magazine's name beside it. The owner's ruling is that
a company and a department carry nothing like the reputational hazard of misnaming a person: the
first half is discoverable and the second can be answered with an opinion, the way a title can. So
the suffix is translated and the stem is floored. `Hyakugōhimehenshūbu` states nothing anybody
would recognise; `Yurihime Editorial Department` names a real desk.

Offline: the reading function is injected, so the test runs against a table it can read.
"""
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import kana as _kana                                                            # noqa: E402
from facts import romanisation as _romanisation  # noqa: E402
from facts import namekey as _namekey                                   # noqa: E402

STYLES = ("macron", "double", "plain")

# The scripts an English reader cannot read, spelled as kari/app.js spells the same class, plus the
# repeat mark.
#
# WRITTEN AS CODE POINTS, and `adapters/interface.py` records why. The compatibility-ideograph range
# typed with a literal character gets U+8C48, the ordinary character an editor inserts, and not
# U+F900, the compatibility ideograph the range meant. The class then ran from U+8C48 to U+FAFF and
# swallowed Hangul, so six credits naming Korean artists counted as Japanese. A range nobody can
# read by eye is a range that drifts.
#
# THE REPEAT MARK IS IN THE RUN AND NOT IN THE CHECK'S CLASS. U+3005 repeats the character before
# it, so it has to reach the analyser with its neighbour; leaving it out would cut a name in two and
# read each half alone.
_JA_CLASS = "\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\u3005"
JAPANESE = re.compile(f"[{_JA_CLASS}]")
# THE MIDDLE DOT IS PUNCTUATION SITTING INSIDE THE KANA BLOCK, and a run is what gets read aloud.
# U+30FB separates two elements of a name and `romanise` has nothing to say about it, so a run
# holding one came back a character short and kuroba U read `KurobaU`. Kept out of the run it lands
# in the text between runs, where `latinise` gives it the interpunct an English reader reads.
# U+30FC, the long vowel mark, is the opposite case and stays inside: it is part of how kana reads.
_RUN_CLASS = "\u3040-\u30fa\u30fc-\u30ff\u3400-\u9fff\uf900-\ufaff\u3005"
JAPANESE_RUN = re.compile(f"[{_RUN_CLASS}]+")

# WHAT AN EDITORIAL DESK IS CALLED IN ENGLISH. The WORDS come from `entities.KINDS`, which already
# classifies a credit ending in one of them as a desk rather than a person; this adds only the
# gloss. `test_romfloor` asserts the two sets are equal, so a word added there without an English
# answer here fails rather than silently romanising.
DESK_EN = {
    "編集部": "Editorial Department",
    "編纂室": "Compilation Office",
    "資料室": "Reference Room",
}

# Full-width punctuation is typography and not content. `pass4_analyser.latinise` is the one table
# and this consumes it; a second copy here would drift the way §3 describes.
_LATINISE = None


def _latinise(text):
    """The width and punctuation fold, asked of the one module that owns it.

    It used to reach `pass4_analyser.latinise` directly, which was correct and left the step as
    something each caller had to remember. Three of the four callers remembered.
    """
    return _romanisation.normalise(text)


def desk_parts(text):
    """`(stem, English for the suffix)` for a credit naming an editorial desk, or None.

    THE SUFFIX HAS TO CLOSE THE STRING. 編集部 inside a longer credit is somebody's field rather
    than the whole of what the credit names, and a rule matching anywhere would translate a word
    out of the middle of a name.
    """
    s = str(text or "").strip()
    for word, en in DESK_EN.items():
        if s.endswith(word):
            return s[:-len(word)].strip(), en
    return None


def _expand_repeat(run):
    """U+3005 written out as the character it repeats.

    THE ANALYSER ANSWERS WITH A CATEGORY AND NOT A SOUND. Asked to read 々 alone it says キゴウ,
    its word for 補助記号, which `per_char` refuses, so a run holding one could not be read at all
    and 依々恋々 had no floor. The mark means "the character before this one again", which is a fact
    about the writing rather than a reading, so it is resolved before anything is asked to read.
    """
    out = []
    for ch in run:
        out.append(out[-1] if ch == "\u3005" and out else ch)
    return "".join(out)


def _run_reading(run, read):
    """A katakana reading for one Japanese run, or None when a character cannot be read.

    KANA IS ALREADY THE READING and must not be handed to an analyser. Asked to read ますみ the
    analyser answers with the word it thinks that is, and よつばますみ is a pen name it has never
    seen: the reading of kana is the kana. Only a run holding kanji is a question.
    """
    if _kana.kana_only(run):
        return _kana.to_katakana(run)
    # Written out before anything is asked to read it, so both the whole-run question and the
    # per-character one below see a character rather than a mark meaning "again".
    run = _expand_repeat(run)
    got = read(run)
    if got and not _kana.has_kanji(got):
        return _kana.to_katakana(got)
    # PER CHARACTER, WHICH IS THE WEAKEST ANSWER AND THE ONE THAT IS ALWAYS THERE. A character read
    # alone gives its dictionary reading, and a Japanese name overwhelmingly takes a reading the
    # dictionary does not carry, so this is wrong more often than it is right. It is still Latin,
    # it is still marked, and the alternative is kanji on an English page.
    out = []
    for ch in run:
        if not JAPANESE.match(ch):
            out.append(ch)
            continue
        if _kana.is_kana(ch):
            out.append(_kana.to_katakana(ch))
            continue
        r = read(ch)
        if not r or _kana.has_kanji(r):
            return None
        out.append(_kana.to_katakana(r))
    return "".join(out)


def floor(text, read):
    """`{style: Latin}` for a Japanese string, or None where a character of it cannot be read.

    `read(s)` answers with a katakana reading for `s`, or None. The build passes the analyser with
    Unihan behind it; the test passes a small table, which is what keeps this suite offline.

    None IS A STATE AND NOT A FAILURE (§5). It says nothing in this project can read the string,
    which is a fact worth counting rather than papering over, and `build.py` counts it.
    """
    s = str(text or "")
    if not s.strip():
        return None
    if not JAPANESE.search(s):
        # Already Latin, so there is no floor to compute. NFKC is a width fold and not a reading.
        return None
    desk = desk_parts(s)
    if desk:
        stem, en = desk
        if not stem:
            return {st: en for st in STYLES}
        inner = floor(stem, read) if JAPANESE.search(stem) else None
        if inner:
            return {st: f"{inner[st]} {en}" for st in STYLES}
        if not JAPANESE.search(stem):
            return {st: f"{_latinise(stem)} {en}" for st in STYLES}
        return None
    out = {}
    for style in STYLES:
        spelled = []
        at = 0
        for m in JAPANESE_RUN.finditer(s):
            # THE TEXT BETWEEN RUNS GOES THROUGH RAW AND IS FOLDED AT THE END. `latinise` strips its
            # argument, so folding each fragment as it was taken swallowed the space between two
            # runs and `サリイ ビー` came out `SariiBii`, one name where the source wrote two.
            spelled.append(s[at:m.start()])
            reading = _run_reading(m.group(0), read)
            if reading is None:
                return None
            # PERSON, because a personal name holds no grammatical particle: 都 in a name is a
            # character read `to` and not the particle と. Every string this module floors is a name
            # or a fragment of one.
            #
            # THROUGH facts/romanisation SO THE FLOOR SPELLS WHAT THE STORE SPELLS. This assembled
            # its own pipeline and stopped one step short of the build's, so `ＮＯＡＨ編集部` came out
            # `ＮＯＡＨEditorial Department` here and `NOAH Editorial Department` from a stored
            # reading. One entry point, and the width fold is no longer a thing a caller can forget.
            spelled.append(_romanisation.romanise(reading, style, _romanisation.PERSON))
            at = m.end()
        spelled.append(s[at:])
        got = _latinise("".join(spelled))
        # §4: TEST FOR THE BAD VALUE. A rule that let a character through would produce a string
        # that reads as English and carries Japanese in the middle of it, which is the exact fault
        # this module exists to make impossible. Refused here rather than shipped.
        if not got or JAPANESE.search(got):
            return None
        out[style] = got
    return out


def runs_within(text):
    """Every maximal Japanese run inside a string, longest first.

    WHY THE RUNS AND NOT ONLY THE WHOLE STRING. The interface renders a credit field IN PLACE: it
    replaces the names it can and leaves the field's own brackets, separators and roles alone, so a
    company nobody divided out sits between two rendered names as a bare run of kanji. A map keyed
    only on whole fields answers nothing for that run. Keyed on the runs as well, the composition
    has an answer for every part of every string it can be handed.
    """
    got = {m.group(0) for m in JAPANESE_RUN.finditer(str(text or ""))}
    return sorted(got, key=len, reverse=True)


def fold(s):
    """The key kari/app.js looks up, which is `foldKey`: NFKC with the spaces removed.

    ASKED OF `facts/namekey`, which owns it. Thirteen functions called `fold` disagreed on
    real input until 2026-08-10, and one invariant pinned one of them while the rest
    answered to nobody. This one was already the identity key and is unchanged.
    """
    return _namekey.fold(s)


def build(strings, read, runs_of=()):
    """`({key: Latin or {style: Latin}}, [strings nothing could read])` for the shipped map.

    `runs_of` names the strings whose Japanese RUNS are wanted as keys of their own, which is the
    credit fields and nothing else: those are the only strings the interface composes IN PLACE, and
    a run between two brackets is what it hands over. Expanding every title the same way added four
    thousand keys nothing would ever look up.

    A KEY IS A STRING WHERE THE THREE STYLES AGREE, and an object where they differ. Two thirds of
    these hold no long vowel, so there is nothing for the styles to disagree about and writing the
    same spelling three times cost half a megabyte on a file that loads on every visit.
    """
    want = {s for s in (str(x or "").strip() for x in strings) if s and JAPANESE.search(s)}
    for s in runs_of:
        want.update(runs_within(s))
    out, unread = {}, []
    for s in sorted(want):
        key = fold(s)
        if key in out:
            continue
        got = floor(s, read)
        if not got:
            unread.append(s)
            continue
        out[key] = got[STYLES[0]] if len(set(got.values())) == 1 else got
    return out, unread
