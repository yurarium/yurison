#!/usr/bin/env python3
"""Why a row carries the date it carries, or carries none. One vocabulary for one field.

WHY THIS IS A FACT. `date_basis` is a single field a reader is shown, and its terms were spread over
three modules: six in `recon/bookwalker_volumes`, one in `blurbdate`, one in `delivery`. Each module
owned the term it emits, which is right, and nothing owned the SPACE those terms live in, which is
how `VENUE_TYPE` came to answer for six of the eight and `build.py` came to know which module holds
the fallback sentence.

WHAT EACH FIELD IS.

    `dated`      whether the basis names an event that dates the row, or says why nothing does.
                 Four of the nine date the row and five explain a silence, and nothing said which
                 was which: `undated works say where and why` had to know it and got it from the
                 shape of the calling code.
    `venue_type` what sort of venue the row sits on, which is what a reader most needs when there is
                 no date to show: an imprint that prints nothing is a different state from one that
                 dates its other books. It is `None` for the two silences that know nothing about
                 the venue either, and for the two shop bases, which arrive by a path that never
                 asked. Those four were `None` from a `.get` on a table that held six of eight
                 terms, which reads exactly like an answer.
    `note`       one sentence saying what the term means, shown to a reader.

WHAT THIS DOES NOT DECIDE. Which basis a row gets. That is the capture's, and each capture keeps its
own `BASIS` naming the term it emits. This says what the terms are and what each one means.

FOUR SILENCES WERE ONE. `no-date-attested` was written over an imprint that prints nothing, a
chapter serial with no volumes, an imprint that dates its other books but not this one, and too
little read to tell those apart. Each wants something different done about it, and the flattened
field asked for one thing. `no-date-attested` survives for the source that said nothing about why.
"""

#: Every term the `date_basis` field can hold, and what each one means.
BASES = {
    "chapter-serial": {
        "dated": True,
        "venue_type": 'chapter-serial-imprint',
        "note":
        "Sold by the chapter on the shop's 話・連載 store. There are no volumes and no print "
        "edition, and the only date the shop states is 更新, the day the latest chapter went "
        "up, which is the most recent publication rather than the first.",
    },
    "no-date-attested": {
        "dated": False,
        "venue_type": None,
        "note":
        "No source consulted states a publication date, and none of them says why. Recorded "
        "undated rather than dated by inference.",
    },
    "no-print-date-stated": {
        "dated": False,
        "venue_type": 'imprint',
        "note":
        "The shop states no 底本発行日 for this work, and the imprint does state one elsewhere, "
        "so the imprint being digital-only does not account for it. Whether a print edition "
        "exists is unresolved.",
    },
    "no-print-edition": {
        "dated": False,
        "venue_type": 'digital-imprint',
        "note":
        "Digital-only. The shop states 底本発行日 on none of the volumes it holds under this "
        "imprint, so there is no print edition for it to carry a publication date. The "
        "absence is the format rather than a gap in the shop's record.",
    },
    "no-volumes-found": {
        "dated": False,
        "venue_type": None,
        "note":
        "The series page listed nothing this capture could read. Nobody has an answer about "
        "this work yet, which is not the same as the shop having none.",
    },
    "print-base-edition": {
        "dated": True,
        "venue_type": 'tankobon-imprint',
        "note":
        "The earliest 底本発行日 across the work's volumes, which is the publication date of the "
        "print edition the file was made from. A serialised work appeared in a magazine "
        "before its tankōbon and this shop never mentions the magazine, so this is the "
        "earliest publication the shop attests rather than the work's first.",
    },
    "print-edition-unknown": {
        "dated": False,
        "venue_type": 'imprint',
        "note":
        "The shop states no 底本発行日 for this work, and the shop holds too few volumes under "
        "the imprint to tell a digital-only label from a silence. Undecided rather than "
        "negative.",
    },
    "shop-blurb-print-date": {
        "dated": True,
        "venue_type": None,
        "note":
        "The shop's own description of this work states when the doujin edition it was made "
        "from was published. That is a printing, so it answers the work's first publication "
        "and the day the shop began delivering the file does not. The sentence is not "
        "recorded, because a shop's description is copyrighted; the date, the claim it was "
        "made under and the sales event named beside it are.",
    },
    "shop-delivery-date": {
        "dated": True,
        "venue_type": None,
        "note":
        "The day the shop began delivering this file, which is the earliest 配信開始日 across the "
        "volumes it holds. The shop states no print edition and no ISBN for this work, so no "
        "paper record is reachable and no catalogue can be asked. This dates the delivery "
        "and claims nothing about an earlier edition, which for a self-published work may "
        "never have had a recorded date at all.",
    },
}

#: WHAT A ROW WITH NO STATED BASIS TAKES. A capture that dates nothing and says nothing about why
#: leaves this, which is the only case the term was ever true of.
FALLBACK = "no-date-attested"


def bases():
    """Every term the field can hold."""
    return tuple(BASES)


def note(basis):
    """The sentence explaining a term, falling back to the one for an unexplained silence."""
    return BASES.get(basis, BASES[FALLBACK])["note"]


def venue_type(basis):
    """What sort of venue an undated row sits on. `None` for a basis that dates the row."""
    return (BASES.get(basis) or {}).get("venue_type")


def dates_the_row(basis):
    """Whether the basis names an event that dates the row, rather than saying why nothing does."""
    return bool((BASES.get(basis) or {}).get("dated"))
