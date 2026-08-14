#!/usr/bin/env python3
"""The fold that decides whether two titles name one work. STORE-PLAN §12.

WHY THIS IS A MODULE. `bylines`, `bwingest` and `names/shop_reading` each did `from build import
norm_work`, which executes a 7,400-line compiler to get nineteen lines, and `check.py` reached it
the same way. It is the most-called function in this project, 141 sites in the compiler alone, and
it was the hardest one to ask.

IT IS A DIFFERENT FOLD FROM `facts/namekey`'s, deliberately. That one is what the SITE joins a name
map on, NFKC with spaces removed; this one decides whether two TITLES are the same work, and it
removes punctuation the other keeps. A title is compared across sources that render it differently,
and a name map is looked up with the string a row carries.
"""
import re
import unicodedata


def norm_work(s):
    """Normalise a work title for comparison.

    NFKC first. Without it （私に） and (私に) compare unequal, as do ２ and 2, and ！ and !.
    That duplicated series in the feed. The comparators and the platforms render all of these
    inconsistently, so folding them is the only way titles match across sources.

    The long vowel mark ー is deliberately NOT stripped: it is a letter in katakana, not
    punctuation, and removing it would merge genuinely different titles.

    Nor is '+', for the same reason and a sharper one: it marks a SEQUEL. citrus and citrus+ are
    two works with two URLs on 一迅プラス, and stripping it merged them into one everywhere in the
    database, filing the sequel's releases under the original. NFKC has already folded ＋ to +, so
    keeping it costs no cross-source matching.
    """
    s = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", s or "")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"""[\s\-.=、。･・!?,:;'"“”‘’()\[\]{}「」『』【】〈〉《》〔〕~〜_/\\|*&#@]""",
                  "", s.strip().lower())


