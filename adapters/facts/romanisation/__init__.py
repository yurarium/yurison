#!/usr/bin/env python3
"""How a kana reading becomes Latin script. One entry point, three styles, two kinds of name.

WHY THIS IS ONE FACT. Romanising runs kana to Latin, then capitals, then the punctuation and
width an English reader can read. Before this module the three were assembled at each
call site, and the two call sites did not assemble the same pipeline. `build.py` applied all three;
`romfloor.py` applied the first two. So `ＮＯＡＨ編集部` came out `NOAH Editorial Department` when the
store held a reading and `ＮＯＡＨEditorial Department` when the floor spelled it, and the difference
reached readers as part of `full-width forms in English renderings`.

That is the test for a fact: two places could disagree, and they did.

WHAT THE CALLER STILL DECIDES, and it is one thing. A person's name and a title capitalise
differently, because a grammatical particle cannot occur inside a personal name: 宮原 都 is read
`to`, which is also the particle と, and lower-casing part of somebody's name is worse than
capitalising a particle in a title. The caller says which it has; it does not say how either is
spelled.

WHAT IT DOES NOT OWN. The READING is somebody else's fact, and this module takes one as given and
says nothing about whether it is right or where it divides. See BLINDSPOT.md.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))

import kana as _kana                                                    # noqa: E402

STYLES = ("macron", "double", "plain")

PERSON = "person"
TITLE = "title"


def normalise(text):
    """Punctuation and width an English reader can read, without touching letters.

    PUBLIC, BECAUSE A CALLER THAT ASSEMBLES ITS OWN STRING STILL OWES THIS STEP. `build._floored`
    joins floored runs with the raw text between them, and its docstring said it was asking the one
    romaniser while in fact it was assembling a fourth pipeline that stopped here. Anything that
    builds a rendering out of parts finishes with this call.

    FULL-WIDTH LATIN IS A WIDTH AND NOT A SPELLING. `ＮＯＡＨ` and `NOAH` are the same four letters,
    and a reader who asked for English did not ask for the wide ones. This is the step `romfloor`
    was missing, which is why a desk name spelled by the floor kept its full-width letters while the
    same name spelled from a stored reading lost them.
    """
    if not text:
        return text
    try:
        import pass4_analyser as _p4
    except Exception:                                                   # noqa: BLE001
        # THE CALLER build.py REPLACED GUARDED THIS, so the module keeps the guarantee: a missing
        # analyser degrades the punctuation and never fails the build. It is caught rather than
        # checked because the import reaches sudachipy, which is the part that can be absent.
        return text
    return _p4.latinise(text)


def romanise(reading, style="macron", kind=TITLE):
    """A kana reading as Latin script, in one style, capitalised for what it names.

    `style` is one of STYLES and decides only how a long vowel is written (NAMES-PLAN section 8.1).
    `kind` is PERSON or TITLE and decides only whether a particle may be lower-cased.
    """
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}, not {style!r}")
    if kind not in (PERSON, TITLE):
        raise ValueError(f"kind must be {PERSON!r} or {TITLE!r}, not {kind!r}")
    if not reading:
        return reading
    spelled = _kana.romanise(reading, style)
    cased = _kana.title_case(spelled, particles=(kind == TITLE))
    return normalise(cased)


def styles(reading, kind=TITLE):
    """All three styles of one reading, which is the shape the build ships to the browser.

    The browser holds all three because the style is the reader's choice and none of the three is
    derivable from the others: Yūri, Yuuri and Yuri all come from the kana and none from each other.
    """
    return {s: romanise(reading, s, kind) for s in STYLES}
