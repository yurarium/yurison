#!/usr/bin/env python3
"""Which work a translated edition translates.

WHY THIS EXISTS. BOOK☆WALKER sells translations of the same doujinshi as separate products, titled
`【English ver.】Reimu is Easily Embarrassed-はずかしがりやのれいむさん`: the translated name, a
hyphen, and the Japanese title of the work it translates. The shop states the relation itself, and
the corpus already uses it. 16 works carry an `official-jp` English name taken from that pairing,
and `w02056` holds the Japanese original with its Chinese and English editions as one work.

WHERE IT FAILED, AND WHY NO FOLD COULD FIX IT. The shop files that original in kana,
`はずかしがりやのれいむさん`, and writes the base title of three of its translated editions in kanji,
`はずかしがりやの霊夢さん`. `namekey.fold` is the identity key and is deliberately strict; `loosely`
adds case, brackets and the separator a catalogue puts between the parts of a name, and none of
those reach a kanji/kana pair. A spelling cannot be folded into a reading.

SO THE READING IS THE BRIDGE. Both spellings read `ハズカシガリ ヤ ノ レイムサン`, and the analyser
says so for either one. That is not a new mechanism: reading a title is what `pass4_analyser` is
for, and comparing two titles through their readings is what this module adds.

THE CREATOR HAS TO AGREE, and that is the counter-case rather than a detail. A doujinshi circle
publishes many works: every one of the 28 translated-edition products is あとき on アトキンソン, so a
match on the base title alone would merge two of that circle's works the moment two of them read
alike. `ndl_volumes` refuses a record whose creator disagrees for the same reason, and this refuses
one for the same reason.
"""
import re

#: The shop's own marker for a translated edition, in the six spellings it uses.
MARKER = re.compile(r"^【([^】]*(?:ver\.?|Ver\.?|語版|한국어)[^】]*)】\s*(.*)$")

#: The hyphen the shop puts between the translated name and the Japanese one. Both widths appear.
SEP = re.compile(r"\s*[-‐]\s*")


def base(title):
    """The Japanese title a translated-edition product names, or None where it names none.

    THE LAST FIELD AND NOT THE SECOND, because a translated name may hold a hyphen of its own:
    `Reimu se Avergüenza Fácilmente` does not, and `AyaSana Compilation To the Girls of the Wind`
    could. Five of the 28 products carry no separator at all and answer None here, which is the
    honest answer: the shop did not say what they translate.
    """
    m = MARKER.match(str(title or "").strip())
    if not m:
        return None
    parts = [p.strip() for p in SEP.split(m.group(2)) if p.strip()]
    return parts[-1] if len(parts) > 1 else None


def language(title):
    """What the shop calls the language of a translated edition, or None."""
    m = MARKER.match(str(title or "").strip())
    return m.group(1).strip() if m else None


def same_work(base_reading, held_reading, product_creator, held_creator, agree):
    """Whether a product's base title and a held work are the same work.

    TWO CLAIMS, BOTH REQUIRED. The readings agree, which is what carries a kanji spelling to its
    kana one. And the creators agree, which is what stops one circle's works merging into each
    other. `agree` is handed in rather than decided here, because whether two credit strings name
    one person is `facts/credit`'s question and this module has no business holding a second
    opinion about it.
    """
    if not base_reading or not held_reading:
        return False
    if _flat(base_reading) != _flat(held_reading):
        return False
    return bool(agree(product_creator, held_creator))


def _flat(reading):
    """A reading as it compares: the analyser's word breaks are its own and are not the claim."""
    return "".join(str(reading or "").split())
