#!/usr/bin/env python3
"""What admitted a work, written the same way by every route that admits one.

WHY THIS IS A FACT. DEFINITIONS §2 admits a work a comparator lists and then requires knowing WHICH
comparator, so a reader can tell whether a work is here because a publisher called it yuri or
because a shop shelved it there. Two ingest routes wrote that record: `madb/by_isbn` and `bwingest`
each emitted the same four keys and the same sentence citing §2 and §4, differing only in where the
lines wrapped. Two copies of one rule about what the database contains, free to drift.

WHAT THIS DECIDES AND WHAT IT DOES NOT. It says what a shelf admission LOOKS LIKE and what the rule
behind it is. It does not decide whether a work is admitted, which weighs several signals and is
DEFINITIONS §6; and it does not rank the evidence, which is `adapters/classify/credence.py`.
`facts/marketing` owns the vocabulary of what counts as a platform calling a work yuri, and says the
same thing about admission from its own side.

A SHELF IS NEVER A MARKETING LABEL. §4 says so twice, and the sentence below carries it, because a
retailer's shelf is presumptive and rebuttable however strong a lead it is. That distinction is the
whole reason the record names the comparator rather than saying the work is yuri.
"""

#: Which shelf each shop's yuri section is, in the shop's own terms. One home: `bookwalker.jp` was
#: written here and in `bwingest` as a constant of its own, so two files said what one shop's shelf
#: is called.
SHELVES = {
    "cmoa.jp": "genre 37 (百合・GL)",
    "bookwalker.jp": "tag 14 (百合)",
}

#: WHAT A SHELF ADMISSION MEANS, in one sentence, cited. Written into every record a shelf admits,
#: so a reader meeting the row anywhere meets the same rule.
SHELF_NOTE = ("A licensed retailer's yuri shelf is a comparator (DEFINITIONS §2). Presumptive "
              "and rebuttable, and never a marketing_label (§4).")


def shelf_of(shop):
    """The shelf a shop's yuri section is, or the generic phrase for a shop nobody has recorded."""
    return SHELVES.get(shop, "yuri shelf")


def admitted_by(shops, retrieved, quote=str):
    """The `admitted_by:` YAML block naming each shop and the shelf that admitted the work.

    `quote` is the caller's own YAML string escaper, because the two routes carry different ones and
    which escaper is right is a property of the writer rather than of this rule.
    """
    lines = ["admitted_by:"]
    for shop in shops:
        lines += [f"  - comparator: {quote(shop)}",
                  f"    shelf: {quote(shelf_of(shop))}",
                  f"    retrieved: {retrieved}",
                  "    note: >-"]
        lines += [f"      {part}" for part in _wrapped(SHELF_NOTE)]
    return lines


def _wrapped(text, width=92):
    """The sentence over as many lines as it takes, so a record stays readable at any indent."""
    import textwrap
    return textwrap.wrap(text, width=width)
