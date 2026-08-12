#!/usr/bin/env python3
"""shopjoin.py: which work we hold a shop's capture row is about.

COVERS = ['adapters/shopjoin.py']

WHAT THIS HAS TO PROVE is what the join REFUSES. A join that reaches more works is trivially
available here, by asking on the title alone, and it would attach コミックシーモア's volume count
for one work to a different work with the same name. `トワ・エ・モア` is a 1996 コンパス anthology
and a 2024 講談社 series, and that pair is why the rule is what it is. So every case below is
asserted in both directions: what reaches a work, and what is declined and left uncounted.

The counts in the module's docstring come from the capture on disk. Nothing here reads it: these
are the shapes, written out, so the suite runs offline and says the same thing on a machine with no
data directory.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import shopjoin                                                         # noqa: E402
import testkit                                                          # noqa: E402

# One work we hold, as the shipped collections carry it: a series row with a print block, and the
# works record its volumes live on.
SERIES = [
    {"id": "w01268", "work": "MURCIÉLAGO -ムルシエラゴ-",
     "print": [{"work_id": "C338361", "work_ids": ["C338361", "bw-15279"],
                "publisher": "スクウェア・エニックス", "volumes": 32}]},
    {"id": "w00402", "work": "citrus",
     "print": [{"work_id": "C357075", "work_ids": ["C357075"], "publisher": "一迅社",
                "volumes": 10}]},
    # A work whose MADB record names the distributor where the shop names the publisher.
    {"id": "w00900", "work": "配本のみ",
     "print": [{"work_id": "C9", "work_ids": ["C9"], "publisher": "", "distributor": "講談社",
                "volumes": 3}]},
    # A row with no print block states no volumes and is not indexed at all.
    {"id": "w09999", "work": "ウェブだけ", "print": []},
]
WORKS = [
    {"work_id": "C338361", "volumes": [{"number": "1", "isbn": "9784757542907"},
                                       {"number": "2", "isbn": "9784757542914"}]},
    {"work_id": "bw-15279", "volumes": [{"number": 1}]},          # BOOK☆WALKER states no ISBN
    {"work_id": "C357075", "volumes": [{"number": "1", "isbn": "9784758072649"}]},
    {"work_id": "C9", "volumes": [{"number": "1"}]},
]


def main(s):
    idx = shopjoin.index(SERIES, WORKS)

    # ── AN ISBN IDENTIFIES AN EDITION, so a shared one settles it ─────────────────────────────
    s.eq(shopjoin.match({"shelf_title": "MURCIELAGO -ムルシエラゴ-", "publisher": "スクエニ",
                         "volumes": [{"volume": 1, "isbn": "9784757542907"}]}, idx),
         ("w01268", "isbn"),
         "a shared ISBN joins the shop's row to the work, whatever either side calls the title")
    s.eq(shopjoin.match({"shelf_title": "MURCIELAGO", "volumes": [{"isbn": "978-4-7575-4290-7"}]},
                        idx)[0],
         "w01268", "and the ISBN is compared as an ISBN, so the hyphenated form is the same book")

    # ── A TITLE AND A HOUSE TOGETHER IDENTIFY A WORK ──────────────────────────────────────────
    s.eq(shopjoin.match({"shelf_title": "citrus", "publisher": "一迅社"}, idx), ("w00402", "house"),
         "a title and the house behind it join where no ISBN is shared")
    s.eq(shopjoin.match({"shelf_title": "配本のみ", "publisher": "講談社"}, idx)[0], "w00900",
         "the shop's publisher answers against our DISTRIBUTOR seat, which is the same company in "
         "the seat MADB happened to file it in")

    # ── AND A TITLE ALONE IDENTIFIES NOTHING ──────────────────────────────────────────────────
    #
    # THE CASE THE WHOLE RULE IS FOR. Taking this would attach one work's volume count to another
    # work with the same name, and the corpus really does hold titles like `放課後` and `先生`.
    s.eq(shopjoin.match({"shelf_title": "citrus", "publisher": "別の出版社"}, idx),
         (None, "unjoined"), "a title whose house disagrees is not joined")
    s.eq(shopjoin.match({"shelf_title": "citrus"}, idx), (None, "unjoined"),
         "and a row naming no house at all is not joined on the title it shares")
    # BOTH HALVES OF THAT, because the guard in `match` and the index's own keys each enforce it
    # and a test that pinned only the guard went green with the guard removed. `配本のみ` has an
    # empty `publisher` and a distributor, and its empty seat must not become a key that a shop row
    # naming no publisher could answer.
    s.check(all(house for _t, house in idx["house"]),
            "no key in the index carries an empty house, so an unnamed publisher matches nothing")
    s.eq(shopjoin.match({"shelf_title": "ウェブだけ", "publisher": "一迅社"}, idx),
         (None, "unjoined"), "a work with no print block has no volumes to compare and is not "
                             "reachable, so nothing can be said about its length")

    # ── AMBIGUITY IS DECLINED, NEVER RESOLVED ─────────────────────────────────────────────────
    two = shopjoin.index(
        SERIES + [{"id": "wDUP", "work": "citrus", "print": [{"work_id": "X", "work_ids": ["X"],
                                                              "publisher": "一迅社"}]}], WORKS)
    s.eq(shopjoin.match({"shelf_title": "citrus", "publisher": "一迅社"}, two), (None, "ambiguous"),
         "two works answering to one shop row is a question about OUR records, so neither is taken")

    # ── A SHOP SELLS EDITIONS AND THIS COMPARES WORKS ─────────────────────────────────────────
    #
    # `まんがの作り方【お試し版】` carries the work's own ISBN and holds one volume where the work
    # has eight. Counted as the work's length it turned an agreement into a disagreement of 8 to 1.
    s.check(not shopjoin.counts_volumes({"shelf_title": "まんがの作り方【お試し版】"}),
            "a free sample states nothing about how long the work is")
    s.check(not shopjoin.counts_volumes({"shelf_title": "旧約マザーグール【分冊版】"}),
            "nor does a work split into parts sold separately")
    s.check(shopjoin.counts_volumes({"shelf_title": "まんがの作り方"}),
            "while the work itself does, which is the row the count belongs to")

    rows = [{"shelf_title": "MURCIELAGO -ムルシエラゴ-", "volumes_stated": 29,
             "volumes": [{"isbn": "9784757542907"}]},
            {"shelf_title": "MURCIELAGO -ムルシエラゴ-【お試し版】", "volumes_stated": 1,
             "volumes": [{"isbn": "9784757542907"}]}]
    got = shopjoin.joined(rows, idx)
    s.eq(sorted(got), ["w01268"], "so the work is reached")
    s.eq(got["w01268"]["volumes_stated"], 29,
         "AND IT IS THE WORK'S OWN ROW THAT REACHES IT; the sample's count of 1 would have read as "
         "the shop contradicting a 29 volume series")

    # TWO REAL PRODUCTS UNDER ONE IDENTITY ARE NOT A CLAIM EITHER. `Qualia -Envy-` and
    # `Qualia -Jealousy-` are one work to us and two series to the shop, so neither states its
    # length and picking one would be picking at random.
    both = [{"shelf_title": "Qualia -Envy-", "volumes_stated": 1,
             "volumes": [{"isbn": "9784758072649"}]},
            {"shelf_title": "Qualia -Jealousy-", "volumes_stated": 1,
             "volumes": [{"isbn": "9784758072649"}]}]
    s.eq(shopjoin.joined(both, idx), {},
         "a work two shop rows speak about is left out rather than answered by whichever sorted "
         "first")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
