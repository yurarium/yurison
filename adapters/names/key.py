#!/usr/bin/env python3
"""The one definition of "this is the same name key", for the store that holds renderings.

WHAT THE KEY IS FOR. `data/build/feed/names.json` maps a Japanese title or person to the reading,
the romanisation and the English this project holds for it. The map is keyed on the Japanese string,
and the same work reaches us spelled several ways that mean nothing: （私に） from one platform and
(私に) from another, a full-width space where a catalogue puts a half-width one. So a lookup folds
before it asks, and everything that folds together is one key.

WHY IT IS A MODULE. Three places decided this independently. `build.py` folded with NFKC and then
stripped spaces, `kari/app.js` did the same in JavaScript, and `names/curate.py` folded with NFKC
alone, which meant "names a work we hold" had two meanings and a key differing by a space answered
differently depending on who asked. That is STANDING-INSTRUCTIONS §3 exactly, and it was found by a
reader counting marked titles on a live page against a measure that had been written against the
stricter fold and reported a number the page contradicted.

WHAT NFKC DOES AND WHAT IT LEAVES. It folds width, so ＡＢ and AB are one key, and it folds
U+3000 to an ordinary space, which is why stripping ASCII spaces afterwards covers both. It does
NOT fold an exclamation mark away, so `勝たん` and `勝たん！` stay two keys: MADB drops the ！ from
its subtitle field and keeps it in the reading, and the pair has to be joined by a person deciding
rather than by a rule that would also join titles that differ.

THE COPY IN THE BROWSER. `foldKey` in `kari/app.js` is this function in JavaScript, and it cannot
import this one. `the interface folds a name key as the build does` in check.py is what holds the
two together, because names.json is keyed on the folded form ALONE: a disagreement about the fold
does not degrade a lookup, it loses it.

NOT `identity.fold`, WHICH ANSWERS A DIFFERENT QUESTION. That one decides whether two records are
the same WORK, so it also strips bracketed matter and decorative punctuation: 【合本版】 comes off
because a collected edition is the work it collects. A name key must not do that, or one rendering
would serve two titles a reader can tell apart.
"""
import unicodedata


def fold(t):
    """The lookup key for a Japanese name or title."""
    return unicodedata.normalize("NFKC", t or "").replace(" ", "")


def spaced(a, b):
    """Whether two keys are one key only because spaces were stripped.

    A KEY THAT APPLIES BY ACCIDENT. `curate.py` used to fold with NFKC alone, on the reasoning that
    a key differing by a full-width bracket is one work under two spellings while a key differing by
    a stray space is a typo that happens to work. The reasoning is sound and the implementation was
    not: it gave the project two definitions of the same key. The distinction is kept here, as its
    own question, so a hand-typed key can still be reported to whoever typed it without the
    "does it apply" answer depending on who is asking.
    """
    nfkc = lambda s: unicodedata.normalize("NFKC", s or "")            # noqa: E731
    return fold(a) == fold(b) and nfkc(a) != nfkc(b)
