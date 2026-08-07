#!/usr/bin/env python3
"""Readings that split a word the title writes as one.

WHY THIS EXISTS. `ゆりでなる♡えすぽわーる` is stored as `ユリ デ ナル ♡ エ スポ ワール`. えすぽわーる is
espoir, one word, and the analyser cut it into three. The reading is present and well formed, so
nothing counts it as missing, and the romanisation built from it shows a reader "E Supo Waaru".

WHY THE OBVIOUS TEST DOES NOT WORK. Looking at the reading alone and flagging short katakana tokens
marks 61% of the corpus, because a Japanese reading is written word-separated and ガ, ト, ニ and ノ
are particles doing exactly what they should. `# ウチラ ガ サイキョウ` is correct. The fault is only
visible against the SOURCE: a boundary in the reading that the title does not have.

WHAT THIS DETECTS, AND WHAT IT DELIBERATELY DOES NOT. A run the title writes in unbroken KATAKANA is
one lexical item in nearly every case, because that is what katakana is for, so a reading that
splits it is wrong. A run the title writes in hiragana is not: `ゆりでなる` is three words and its
reading `ユリ デ ナル` is right. So a hiragana loanword written for effect, which is the very case
that prompted this, is out of reach here and is counted separately as unmeasured. Reporting a
precise number for the part that can be tested is worth more than a large one covering both.
"""
import re

KANA_RUN = re.compile(r"[ァ-ヺー]{4,}")
HIRA_RUN = re.compile(r"[ぁ-ゖー]{4,}")


def kata(s):
    """Hiragana to katakana, so a title's run can be compared with a katakana reading."""
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in str(s or ""))


def split_runs(title, reading):
    """Runs the title writes as one unbroken katakana word and the reading breaks up.

    Returns `[(run, as the reading has it)]`. A run absent from the reading altogether is not a
    segmentation fault and is not reported: the reading may be of something else, and this says
    nothing about a reading it cannot align.
    """
    rd = str(reading or "")
    flat = rd.replace(" ", "").replace("　", "")
    out = []
    for run in KANA_RUN.findall(str(title or "")):
        if run in rd:
            continue                       # present unbroken; nothing to report
        if run not in flat:
            continue                       # not this reading's material at all
        # Present once the spaces come out, so the reading introduced every boundary in it.
        i = flat.index(run)
        spaced, seen = [], 0
        for tok in rd.split(" "):
            if seen + len(tok) > i and seen < i + len(run):
                spaced.append(tok)
            seen += len(tok)
        out.append((run, " ".join(t for t in spaced if t)))
    return out


def unmeasured(title, reading):
    """Whether the title carries a long hiragana run, which this cannot judge either way."""
    return bool(HIRA_RUN.search(str(title or ""))) and bool(reading)


def repair(title, reading, lex=None):
    """The reading with the boundaries removed that the title does not have.

    ONLY SPACES COME OUT. The segment is rewritten as itself without its spaces, so anything else
    inside it survives: `（ナンバー ナイン）` becomes `（ナンバーナイン）` and keeps its brackets,
    and `アフター タイム。` keeps its full stop. Nothing is added, reordered or respelt, because a
    reading is somebody's claim about pronunciation and this is only undoing a cut.

    `lex` is the corpus's own katakana lexicon (adapters/names/lexicon.py). Given one, a hiragana
    run the corpus attests as a single katakana word is repaired too, which is the class the script
    rule cannot see: `ばけーしょん` is バケーション and the analyser reads it as running text.
    """
    out = str(reading or "")
    for _run, spaced in split_runs(title, out):
        if " " in spaced:
            out = out.replace(spaced, spaced.replace(" ", ""))
    if lex:
        from names import lexicon as _lex
        for run in HIRA_RUN.findall(str(title or "")):
            word = _lex.kata(run)
            if not _lex.known(run, lex) or word in out:
                continue
            flat = out.replace(" ", "")
            if word not in flat:
                continue
            # Find the spaced form of that word in the reading and close it up.
            i, seen, seg = flat.index(word), 0, []
            for tok in out.split(" "):
                if seen + len(tok) > i and seen < i + len(word):
                    seg.append(tok)
                seen += len(tok)
            joined = " ".join(t for t in seg if t)
            if " " in joined:
                out = out.replace(joined, joined.replace(" ", ""))
    return out
