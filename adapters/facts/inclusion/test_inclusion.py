#!/usr/bin/env python3
"""facts/inclusion: what admitted a work, written the same way by every route that admits one.

COVERS = ['adapters/facts/inclusion/__init__.py']

THE FAULT THIS IS FOR is two ingest routes writing the same record. `madb/by_isbn` and `bwingest`
each emitted four keys and a sentence citing DEFINITIONS §2 and §4, differing only in where the
lines wrapped, and each held its own idea of what bookwalker's shelf is called.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import inclusion                                             # noqa: E402


def main(s):
    block = inclusion.admitted_by(["bookwalker.jp"], "2026-08-10")
    s.eq(block[0], "admitted_by:", "the block names the field")
    s.check(any("comparator: bookwalker.jp" in l for l in block), "and the shop that admitted it")
    s.check(any("shelf: tag 14 (百合)" in l for l in block),
            "and which shelf, in the shop's own terms, since §2 requires knowing WHICH comparator")
    s.check(any("retrieved: 2026-08-10" in l for l in block), "and when it was read")

    # THE RULE TRAVELS WITH THE RECORD. A reader meeting the row anywhere meets the same sentence,
    # and it says the thing §4 says twice: a shop's shelf is never a marketing label.
    note = " ".join(l.strip() for l in block if "DEFINITIONS" in l or "rebuttable" in l)
    s.check("DEFINITIONS §2" in note, "the record cites the clause that admits it")
    s.check("never a marketing_label" in note and "§4" in note,
            "and the clause that keeps a shelf out of a marketing label")

    # TWO SHOPS ARE TWO ENTRIES AND EACH CARRIES ITS OWN SHELF, which is the case that made the
    # shared shape worth having: one route writes several, the other writes one.
    two = inclusion.admitted_by(["bookwalker.jp", "cmoa.jp"], "2026-08-10")
    s.eq(sum(1 for l in two if l.startswith("  - comparator:")), 2, "one entry per shop")
    s.check(any("genre 37" in l for l in two), "and cmoa's shelf is its own")

    # A SHOP NOBODY HAS RECORDED GETS THE GENERIC PHRASE, and not a KeyError and not another shop's
    # shelf. A new comparator is a thing somebody adds; until then the record says what it knows.
    s.eq(inclusion.shelf_of("a-shop-nobody-recorded"), "yuri shelf",
         "an unrecorded shop is admitted by a yuri shelf and no more than that")
    s.check("shelf: yuri shelf" in " ".join(
        inclusion.admitted_by(["a-shop-nobody-recorded"], "2026-08-10")),
        "which is what the record says")

    # THE CALLER'S OWN ESCAPER IS USED, because the two routes carry different ones and which is
    # right is a property of the writer.
    quoted = inclusion.admitted_by(["x"], "2026-08-10", quote=lambda v: f"<<{v}>>")
    s.check(any("<<x>>" in l for l in quoted), "the caller escapes its own strings")

    # AND THE SHOP'S OWN PAGE FOR THE WORK, because a comparator named with no address is a
    # citation a reader cannot follow. 230 shipped rows named コミックシーモア and offered no way
    # to reach it.
    addressed = inclusion.admitted_by(["cmoa.jp"], "2026-08-10",
                                      addresses={"cmoa.jp": "https://www.cmoa.jp/title/1132/"})
    s.check(any("shop_url: https://www.cmoa.jp/title/1132/" in l for l in addressed),
            "the entry states where the shop that admitted the work sells it")
    s.eq(addressed.index("    note: >-"), 5,
         "and the address stands beside the shelf, above the sentence that says what a shelf means")

    # A SHOP WITH NO ADDRESS WRITES NO FIELD (§5: absence is a state). An entry with no `shop_url`
    # says the route could not tell which page this work is; an empty one would read as a page.
    plain = inclusion.admitted_by(["cmoa.jp"], "2026-08-10", addresses={"bookwalker.jp": "x"})
    s.check(not any("shop_url" in l for l in plain),
            "an address for another shop puts nothing on this shop's entry")
    s.check(not any("shop_url" in l for l in
                    inclusion.admitted_by(["cmoa.jp"], "2026-08-10", addresses={"cmoa.jp": ""})),
            "and an empty address is not written out as one")

    # TWO SHOPS TAKE THEIR OWN ADDRESSES, which is what makes this a rule rather than one shop's
    # special case: the field was derivable for exactly one shop before, and that was the fault.
    pair = inclusion.admitted_by(["bookwalker.jp", "cmoa.jp"], "2026-08-10",
                                 addresses={"bookwalker.jp": "https://bookwalker.jp/de1/",
                                            "cmoa.jp": "https://www.cmoa.jp/title/1132/"})
    s.eq(sum(1 for l in pair if l.strip().startswith("shop_url:")), 2, "one address per shop")
    s.check(pair.index("    shop_url: https://bookwalker.jp/de1/")
            < pair.index("  - comparator: cmoa.jp"),
            "and each address sits under the shop it belongs to, not the next one")

    # ── AN AGGREGATOR'S TAG, WHICH IS A COMPARATOR AND IS NOT A SHELF ─────────────────────────
    #
    # §2 admits a work "a comparator lists" and names three: 百合ナビ's WEB連載 list, the antenna's
    # 百合 tag, and a retailer's 百合 shelf. Only the third is a shop, and until 2026-09-27 the
    # only sentence this module had said "a licensed retailer's yuri shelf", which is false of the
    # route that admitted all 29 works inducted in the week to that date.
    tag = inclusion.admitted_by_tag("webcomics.jp", "2026-09-27",
                                    "https://webcomics.jp/tag/%E7%99%BE%E5%90%88")
    s.eq(tag["comparator"], "webcomics.jp", "the entry names the site that listed the work")
    s.eq(tag["shelf"], "百合 tag", "and the listing in the site's own terms")
    s.eq(tag["retrieved"], "2026-09-27", "with the day the listing was read")
    s.eq(tag["url"], "https://webcomics.jp/tag/%E7%99%BE%E5%90%88",
         "and an address a reader can return to")
    s.check("never a marketing_label" in tag["note"],
            "the note carries §4, because a comparator listing is not a publisher calling it yuri")
    s.check("retailer" not in tag["note"] and "shelf" not in tag["note"],
            "and says nothing about shops, which is what SHELF_NOTE would have claimed")

    s.eq(set(tag) - {"url"}, set(inclusion.admitted_by_tag("webcomics.jp", "2026-09-27")),
         "an entry with no address simply has no url, since absence is a state (§5)")
    s.eq(tag.keys() | {"shop_url"},
         {"comparator", "shelf", "retrieved", "note", "url", "shop_url"},
         "and the keys are the shelf entry's keys, so a reader meets one block either way")

    s.eq(inclusion.tag_of("webcomics.jp"), "百合 tag", "a site nobody has recorded is not assumed")
    s.eq(inclusion.tag_of("nowhere.test"), "yuri tag",
         "and one nobody has recorded gets the generic phrase rather than a guess")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "inclusion"))
