#!/usr/bin/env python3
"""credence.py: the order the work page states evidence in, and what it refuses to state.

COVERS = ['adapters/classify/credence.py']

A wrong answer here does not crash anything. It tells a reader that a shop's shelf is as good as a
publisher's imprint, or prints a claim with no readable term beside it, and nothing downstream
would notice. So the ordering is pinned outright, disagreement between sources is pinned as a case
of its own, and every rule that drops a row is pinned by the row it must drop.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit                                                              # noqa: E402
import credence                                                             # noqa: E402

# The two records this whole feature was read off, cut down to the fields it uses.
MADB_IMPRINT = {
    "marketing_label": "yuri",
    "marketing_label_basis": {"source": "madb", "retrieved": "2026-08-01",
                              "url": "https://mediaarts-db.artmuseums.go.jp/id/C270392"},
    "publisher": "一迅社", "imprint": "百合姫コミックス",
}
BOOKWALKER_SHELF = {
    "marketing_label": "none",
    "marketing_label_basis": {"source": "bookwalker", "retrieved": "2026-08-05",
                              "url": "https://bookwalker.jp/de001dd5ae/"},
    "publisher": "ライトリーズン", "imprint": "",
    "admitted_by": [{"comparator": "bookwalker.jp", "shelf": "tag 14 (百合)",
                     "retrieved": "2026-08-05"}],
}
KADOKOMI_TAG = {
    "marketing_label": "yuri", "tags": ["現代", "百合", "アイドル"],
    "marketing_label_basis": {"source": "kadokomi", "retrieved": "2026-08-07",
                              "url": "https://comic-walker.com/detail/KC_000031_S"},
}


def main(s):
    # ── the order, which is the whole point of the module ────────────────────────────────────
    s.eq(credence.rank("imprint"), 1, "the publisher's own imprint is the strongest evidence")
    s.eq(credence.rank("platform-tag"), 2, "the publisher's platform tag comes next")
    s.eq(credence.rank("shelf"), 4, "a licensed retailer's shelf is weaker than either")
    s.check(credence.rank("imprint") < credence.rank("platform-tag") < credence.rank("shelf"),
            "imprint outranks platform tag outranks retailer shelf")
    s.check(credence.rank("magazine") < credence.rank("shelf"),
            "a yuri magazine is §4 labelling and still outranks a §2 comparator")
    s.check(credence.rank("shelf") < credence.rank("listing"),
            "a shop that sells the edition outranks a site that only lists it")

    # An unranked kind stops the build. Sorting it silently would put it first in a table whose
    # heading promises strongest first, which is a claim nobody made.
    s.raises(ValueError, lambda: credence.rank("vibes"), "an unknown kind raises rather than sorts")

    # ── the term is a quotation, so the notation around it is not part of it ─────────────────
    s.eq(credence.shelf_term("tag 14 (百合)"), "百合", "the shop's own word, without its tag number")
    s.eq(credence.shelf_term("genre 37 (百合・GL)"), "百合・GL",
         "and コミックシーモア's word is a different claim, kept different")
    s.eq(credence.shelf_term("百合"), "百合", "a bare term needs no unwrapping")
    s.check(credence.shelf_term("tag 14") is None,
            "a shelf identifier with no word in it yields nothing to quote")
    s.check(credence.shelf_term("") is None, "and neither does an empty shelf")

    # GL is two letters and would match inside anything. The counter-case decided the anchor.
    s.eq(credence.stated_terms(["百合", "学園"]), ["百合"], "the yuri tag is picked out of the list")
    s.eq(credence.stated_terms(["百合", "GL"]), ["百合", "GL"],
         "both are kept, in the order the platform wrote them")
    s.eq(credence.stated_terms(["GLAMOROUS", "グルメ"]), [],
         "GL inside another word is not the GL tag")
    s.eq(credence.stated_terms(["ガールズラブ"]), ["ガールズラブ"], "the spelled-out form counts")
    s.eq(credence.stated_terms(None), [], "a record with no tags yields no terms")

    # ── one record at a time ─────────────────────────────────────────────────────────────────
    imp = credence.label_row(MADB_IMPRINT)
    s.eq(imp["kind"], "imprint", "a bibliography-recorded label is the publisher's imprint")
    s.eq(imp["source"], "一迅社", "and the row names the publisher, who made the claim")
    s.eq(imp["term"], "百合姫コミックス", "quoting the imprint rather than the word yuri")
    s.eq(imp["type"], "publisher", "typed for the kind of party speaking")
    s.eq(imp["read"], "2026-08-01", "with the day it was read")
    s.eq(imp["rank"], 1, "and the rank the page sorts on")
    s.check("rule" not in imp,
            "the clause it came from is a property of the kind and is written once per file")
    s.eq(sorted(credence.RULE), sorted(credence.RANK),
         "every ranked kind says which clause ranked it")
    s.eq(imp["url"], "https://mediaarts-db.artmuseums.go.jp/id/C270392",
         "the address is the page it was read from, which is the bibliography and not a shop")

    tag = credence.label_row(KADOKOMI_TAG, platform="カドコミ")
    s.eq(tag["kind"], "platform-tag", "a platform's own label is platform-side under §4")
    s.eq(tag["source"], "カドコミ", "named after the site that applied it")
    s.eq(tag["term"], "百合", "quoting the tag and not the record's internal value")

    shelf = credence.shelf_rows(BOOKWALKER_SHELF)
    s.eq(len(shelf), 1, "one row per comparator that admitted the work")
    s.eq(shelf[0]["kind"], "shelf", "a licensed retailer is a shelf")
    s.eq(shelf[0]["source"], "BOOK☆WALKER", "under the name the shop trades as")
    s.eq(shelf[0]["term"], "百合", "quoting the shelf")
    s.check("url" not in shelf[0],
            "and no address, because the record states none; a work page is not a shelf listing")

    # A comparator that sells nothing is not a retailer, whatever it lists.
    aggregated = credence.shelf_rows({"admitted_by": [
        {"comparator": "webcomics.jp", "shelf": "tag (百合)", "retrieved": "2026-08-01"}]})
    s.eq(aggregated[0]["kind"], "listing", "an aggregator is not a shop")
    s.eq(aggregated[0]["source"], "webcomics.jp",
         "and keeps its host, because nobody has given it another name")

    # ── what is refused ──────────────────────────────────────────────────────────────────────
    s.check(credence.label_row(BOOKWALKER_SHELF) is None,
            "a shop record carries marketing_label none, so it supports no label row (§4)")
    s.check(credence.label_row({"marketing_label": "yuri", "publisher": "某社", "imprint": "",
                                "marketing_label_basis": {"source": "madb"}}) is None,
            "a publisher-side label with no imprint to quote is dropped rather than paraphrased")

    # THE CASE THAT DECIDED THIS RULE. adapters/madb/extract.py selects VOLUMES on their 百合姫
    # brand and stores the SERIES record, whose own brand is often 一迅社's umbrella comics line.
    # 117 works carry `marketing_label: yuri` beside `imprint: IDコミックス`, and quoting that as
    # the reason a work is filed as yuri would show a reader a term making no such claim.
    s.check(credence.label_row({"marketing_label": "yuri", "publisher": "[発売]講談社",
                                "imprint": "IDコミックス",
                                "marketing_label_basis": {"source": "madb"}}) is None,
            "an umbrella imprint is not the yuri claim and is not quoted as one")
    for spelt in ("IDコミックス. Yurihime comics", "IDコミックス　／　Yuri-hime comics",
                  "百合姫コミックス", "百合姫books", "YURIHIME COMICS"):
        s.check(credence.label_row({"marketing_label": "yuri", "publisher": "一迅社",
                                    "imprint": spelt,
                                    "marketing_label_basis": {"source": "madb"}}) is not None,
                f"every spelling MADB uses for the 百合姫 line still counts: {spelt}")
    s.check(credence.label_row({"marketing_label": "yuri", "tags": ["学園"],
                                "marketing_label_basis": {"source": "kadokomi"}},
                               platform="カドコミ") is None,
            "and so is a platform label whose tags name no yuri term")
    s.check(credence.label_row({"marketing_label": "yuri", "imprint": "百合姫コミックス",
                                "publisher": "一迅社",
                                "marketing_label_basis": {"source": "webcomics"}}) is None,
            "a label whose basis is neither publisher nor platform is not §4 evidence")
    s.check(credence.label_row({}) is None, "and a record with no label supports nothing")

    # ── where sources disagree ───────────────────────────────────────────────────────────────
    # The commonest disagreement in the corpus: the publisher applied no yuri label and a shop
    # shelved the book as yuri anyway. Both are shown, and the shop does not become a label.
    disputed = dict(BOOKWALKER_SHELF, admitted_by=[
        {"comparator": "cmoa.jp", "shelf": "genre 37 (百合・GL)", "retrieved": "2026-08-05"},
        {"comparator": "bookwalker.jp", "shelf": "tag 14 (百合)", "retrieved": "2026-08-05"}])
    got = credence.rows(disputed)
    s.eq(len(got), 2, "two shops disagreeing about the word are two rows, not one merged claim")
    s.eq([r["term"] for r in got], ["百合", "百合・GL"],
         "each shop's own word survives, so a reader can see the two claims differ")
    s.check(all(r["kind"] == "shelf" for r in got), "and neither is promoted to a label")

    # The other direction: the publisher labelled it, the shop shelved it, and the platform
    # tagged it. Three claims about one work, and the order is what the reader is being sold.
    agreed = dict(MADB_IMPRINT, admitted_by=BOOKWALKER_SHELF["admitted_by"])
    both = credence.order(credence.rows(agreed)
                          + [credence.label_row(KADOKOMI_TAG, platform="カドコミ")])
    s.eq([r["kind"] for r in both], ["imprint", "platform-tag", "shelf"],
         "strongest first, whatever order the records were read in")
    s.eq([r["source"] for r in both], ["一迅社", "カドコミ", "BOOK☆WALKER"],
         "and each row names whoever made its claim")

    # A work whose record was read twice states its evidence once.
    s.eq(len(credence.order([credence.label_row(MADB_IMPRINT),
                             credence.label_row(MADB_IMPRINT)])), 1,
         "the same claim from the same source twice is one row")
    s.eq(len(credence.order([credence.label_row(MADB_IMPRINT),
                             credence.label_row(dict(MADB_IMPRINT, imprint="百合姫books"))])), 2,
         "two imprints from one publisher are two claims and stay two rows")

    s.eq(credence.rows({}), [], "a record with nothing to say produces no table")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "credence"))
