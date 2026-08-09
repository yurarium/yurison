#!/usr/bin/env python3
"""What this fact is checked on. Lives beside the fact so a check cannot drift from its subject.

WHY HERE AND NOT IN check.py. A check kept away from the thing it checks is how
`check.STATES_A_READING` came to be a hand-written copy of `curate.READING_ATTRIBUTION` that had
already drifted when somebody looked. `check.py` imports these and registers them; the definition
lives with the fact.
"""
import re

#: Any kana character. Deliberately its own pattern and not one borrowed from `kana.py`: a check
#: that shares its subject's table cannot catch the subject's table being wrong (section 14b).
KANA_ANY = re.compile(r"[぀-ゟ゠-ヿ]")


def kana_left_in_a_romanisation(ctx):
    """Values the shipped names file offers in place of Japanese that still hold a kana character.

    A romanisation exists so that a reader who cannot read kana has something to read, so one kana
    left in it is the whole point of the string undone. `kana.romanise` emits a character it has no
    table entry for, which is the right default for ☆ and × and was wrong for kana: ＲＤーＳｏｕｎｄｓ
    shipped as `RDー Sounds` because the ー lengthened nothing, and 竹ヶ原 romanised as `takeヶhara`.

    WHAT IT ASKS THAT THE PRODUCER DOES NOT (section 14b). `romanise` decides what to emit by
    looking a mora up in BASE, DIGRAPH and PUNCT; this looks at the finished string and asks whether
    any character in it is kana. It shares no table with the subject and would have caught both
    faults above on the shipped bytes, which is where a reader met them.

    IT COVERS THE COMPOSED CREDIT LINES TOO, and that is where the one remaining case is:
    西沢5ミリ renders as `Nishisawa 5 ミリ`, a credit whose parts are rendered one at a time and one
    of whose parts has no rendering. That is `credits`, not `kana`, so the number is not zero and
    naming why is better than scoping it out.
    """
    n = ctx["names_shipped"] or {}
    bad = 0
    for kind in ("titles", "authors", "publishers", "credit_parts", "phrases"):
        for v in (n.get(kind) or {}).values():
            vals = list((v.get("romaji") or {}).values()) if isinstance(v, dict) else [v]
            for s in vals:
                if isinstance(s, str) and KANA_ANY.search(s):
                    bad += 1
    return bad
