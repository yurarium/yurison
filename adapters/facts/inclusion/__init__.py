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

#: THE AGGREGATOR'S TAG, WHICH IS A COMPARATOR AND IS NOT A SHELF. §2 admits a work "a comparator
#: lists", and the unheld register names three: 百合ナビ's WEB連載 list, Web漫画アンテナ's 百合 tag,
#: and a licensed retailer's own 百合 shelf. Only the third is a shop, so `SHELF_NOTE` says the
#: wrong thing about the other two: an aggregator is not a retailer and shelves nothing.
#:
#: IT IS THE LARGER ROUTE NOW AND CARRIED NO RECORD AT ALL. 29 works were inducted in the week to
#: 2026-09-27 and every one came in on the antenna, while the works a shelf admits have carried
#: their grounds since 2026-08-04. A work whose own row cannot say what let it in is a work a
#: reader has to take on trust, which is the thing §2 asks the record to prevent.
TAG_LISTS = {
    "webcomics.jp": "百合 tag",
}

#: WHAT A TAG ADMISSION MEANS. Weaker than a shelf and said so: a shop stakes its catalogue on where
#: it files a book, while an aggregator collects what it notices. Presumptive and rebuttable like
#: the shelf, and a marketing_label like neither of them (§4).
TAG_NOTE = ("An aggregator listing a work under its yuri tag is a comparator (DEFINITIONS §2). "
            "It says the work exists and where, attests nothing about it, and is never a "
            "marketing_label (§4).")


def tag_of(site):
    """The tag a site's yuri listing is, or the generic phrase for one nobody has recorded."""
    return TAG_LISTS.get(site, "yuri tag")


def admission(comparator, shelf, retrieved, note, url=None):
    """One admission block, as the dict both the build and the store hand a reader.

    THE ONE PLACE THE SHAPE IS WRITTEN, §3. It was typed twice for a day: `admitted_by_tag` below
    builds the block a capture attaches, and `emit.series` rebuilds it out of the `admission` rows
    the loader wrote, and two spellings of one shape is how a reader comes to be served two. The
    values differ between the callers and the keys cannot, which is exactly the split this makes:
    the caller says what the admission SAYS and this says what an admission IS.
    """
    out = {"comparator": comparator, "shelf": shelf, "retrieved": retrieved, "note": note}
    if url:
        out["url"] = url
    return out


def admitted_by_tag(site, retrieved, url=None):
    """The admission a work gets from an aggregator's yuri tag, as a dict.

    A DICT, because this hands a row to `build.py` where `admitted_by` below writes YAML lines
    into a record file. The keys are `admission`'s keys either way, so what reaches a reader is one
    block whichever comparator put the work here.
    """
    return admission(site, tag_of(site), retrieved, TAG_NOTE, url)


def shelf_of(shop):
    """The shelf a shop's yuri section is, or the generic phrase for a shop nobody has recorded."""
    return SHELVES.get(shop, "yuri shelf")


def admitted_by(shops, retrieved, quote=str, addresses=None):
    """The `admitted_by:` YAML block naming each shop and the shelf that admitted the work.

    `quote` is the caller's own YAML string escaper, because the two routes carry different ones and
    which escaper is right is a property of the writer rather than of this rule.

    `addresses` is `{shop: that shop's own page for THIS work}`, and it is here because the block
    was naming a source a reader had no way to reach. コミックシーモア admitted 256 works, holds a
    page for every one of them, and not one of those works carried a link to it: `madb/by_isbn`
    computed the block once for a whole pass, so it could name the shop and could not name the
    title. The shop's page is a fact about our own act of admission, in the same sense the shelf and
    the date already here are, and it goes in the same block for the same reason.

    NOT THE SHOP'S ANSWER ABOUT THE WORK. The record's title, dates and volumes still come from
    whatever source the route is built on, which for the ISBN route is the national bibliography.
    This is an address and states nothing about the book.

    A SHOP WITH NO ADDRESS WRITES NO FIELD. §5: absence is a state, and an entry with no `shop_url`
    says the route could not tell which page on that shop this work is. An address invented by
    composing one out of an id would be indistinguishable from one a capture read.
    """
    addresses = addresses or {}
    lines = ["admitted_by:"]
    for shop in shops:
        lines += [f"  - comparator: {quote(shop)}",
                  f"    shelf: {quote(shelf_of(shop))}",
                  f"    retrieved: {retrieved}"]
        if addresses.get(shop):
            lines.append(f"    shop_url: {quote(addresses[shop])}")
        lines.append("    note: >-")
        lines += [f"      {part}" for part in _wrapped(SHELF_NOTE)]
    return lines


def _wrapped(text, width=92):
    """The sentence over as many lines as it takes, so a record stays readable at any indent."""
    import textwrap
    return textwrap.wrap(text, width=width)
