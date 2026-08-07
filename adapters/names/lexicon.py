#!/usr/bin/env python3
"""Katakana words the corpus itself attests, so a reading stops cutting them up.

WHY A LEXICON AT ALL. `adapters/names/segmentation.py` can tell that a reading split a word the
title writes as one, but only where the title writes it in KATAKANA. Where a title writes a loanword
in hiragana for effect, `ゆりでなる♡えすぽわーる`, nothing in the script says whether the run is one
word or a phrase: `ゆりでなる` is three words and its reading is right, `えすぽわーる` is espoir and its
reading is wrong. 1,147 titles carry such a run and no rule about scripts can judge them.

WHERE THE WORDS COME FROM, AND WHY IT IS NOT A DOWNLOAD. Publishers write compounds unbroken. Every
contiguous katakana run a title states IS an attestation that those characters are one unit, made by
the people who named the work. The corpus holds thousands of them, so the evidence is already here
and needs no source anyone could disagree with. A word earns its place by appearing unbroken in a
title, and the file records how many titles attest it, so a run seen once is distinguishable from
コミックアンソロジー seen forty times.

WHAT IT IS NOT. Not a dictionary of Japanese, and not authority over how a word is pronounced. It
answers one question: has anybody, naming a work in this corpus, written these characters as one
run. That is enough to refuse a split and not enough to propose a reading.
"""
import re

KATA_RUN = re.compile(r"[ァ-ヺー]{4,}")
# ー alone, or a run that is one repeated character, attests nothing.
TRIVIAL = re.compile(r"^(.)\1*$|^ー+$")


def kata(s):
    """Hiragana to katakana, so a hiragana run can be looked up."""
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in str(s or ""))


def runs(title):
    """Every contiguous katakana run in a title that is long enough to be a word."""
    return [r for r in KATA_RUN.findall(str(title or "")) if not TRIVIAL.match(r)]


def build(titles):
    """`{word: how many titles write it unbroken}` over every title given."""
    seen = {}
    for t in titles:
        for r in set(runs(t)):
            seen[r] = seen.get(r, 0) + 1
    return seen


def known(word, lex, floor=1):
    """Whether the corpus attests this run as one word, at or above `floor` titles."""
    return lex.get(kata(word), 0) >= floor
