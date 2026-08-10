#!/usr/bin/env python3
"""What this fact is checked on. Beside the fact, so the check cannot drift from the rule.

The count asks a question only this module can answer: which titles a reader is shown still hold a
catalogue's own punctuation. It lived in `check.py`, which meant the rule was in one file and the
measure of the rule in another, and the two were free to disagree about what a mark is.

`check.py` imports this through the entry point and registers it under its published name.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import cataloguing                                                      # noqa: E402

#: An equals sign in any spelling, anywhere in the string. DELIBERATELY LOOSER THAN THE SPLIT.
#: `cataloguing.areas` acts on ` = ` alone, one sign with spaces both sides and Latin on the right
#: before any colon, so this reports the cases the split refused (§14b) and a person then rules on
#: each. Three were carried here as refusals that "stay visible instead of being defined out of the
#: count", and all three are in `RULED` now: `ルミナス = ブルー` is one name a house prints with a
#: sign in it, `School zone = スクールゾーン` runs the languages the other way round, and
#: `ニニンがシノブ伝ぷらす = 2×2=SHINOBUDEN+` has two signs and was read off the publisher's page.
#: The sentence outlived the work it described, which is what moving the count beside the rule is
#: for. What this pattern catches now is the NEXT one, before anybody has looked it up.
#: Three spellings and not two: ゠ is U+30A0, the katakana double hyphen, which is how the sign is
#: written between the halves of a transliterated foreign name. check.py held this class and this
#: module held a copy without it for the length of one commit.
EQUALS_ANY = re.compile(r"[=＝゠]")


def titles_carrying_cataloguing_punctuation(titles):
    """How many of `titles` still carry a catalogue's apparatus.

    WHAT A READER IS SHOWN IS THE WORK, and a record is a transcription of one edition. Counting
    records put 13 of 15 here for MADB rows faithfully carrying `X : 完全版` for a reissue now filed
    under the work it reissues, which is §5 keeping a source record as it arrived.

    A SIGN A PUBLISHER PRINTS IS NOT PUNCTUATION, so `RULED` is asked before the pattern.
    """
    bad = 0
    for title in titles:
        title = str(title or "")
        if title in cataloguing.RULED:
            continue
        if EQUALS_ANY.search(title) or cataloguing.edition_statement(title):
            bad += 1
    return bad


#: What `check.py` registers, keyed on the published name of the count.
CHECKS = {"titles carrying cataloguing punctuation": titles_carrying_cataloguing_punctuation}
