#!/usr/bin/env python3
"""facts/printblock: every catalogue record a merged print block stands for.

COVERS = ['adapters/facts/printblock/__init__.py']

WHAT THIS HAS TO PROVE is a count, not a rendering. Three passes take publisher and imprint names
off `series[].print[]`: the name map, the imprint census and the publisher pages. While a block was
one record they were counting records; the moment build.py began folding a print run's records into
one block they were counting blocks, and the difference was 36 line names that dropped out of the
name map while the volume rows went on drawing them. So the property is that a folded block yields
what its records yielded before the fold, unchanged and undeduplicated.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import printblock as pb                                      # noqa: E402

# The real pair: MADB files 捏造トラップ's volumes 1, 2, 3 and 5 under one heading and 4 and 6 under
# `捏造トラップ : NTR`, and the two records name the line differently.
PRIMARY = {"work_id": "C360665", "publisher": "一迅社", "imprint": "IDコミックス　／　Yurihime comics",
           "first": "2015-07", "last": None, "volumes": 4}
SECOND = {"work_id": "madb-t-de1410efb48e", "publisher": "一迅社", "imprint": "Yurihime comics",
          "distributor": "講談社", "first": "2017-05", "last": None, "volumes": 2}


def main(s):
    # ── A BLOCK THAT FOLDED NOTHING IS ITSELF, AND NOTHING MORE ───────────────────────────────
    s.eq(list(pb.parties(PRIMARY)), [PRIMARY], "a block with no folded records yields one party")
    s.eq(pb.folded_names([PRIMARY]), [], "and writing one from a single block writes nothing")

    # ── AND A FOLDED BLOCK YIELDS WHAT ITS RECORDS YIELDED BEFORE THE FOLD ────────────────────
    got = pb.folded_names([PRIMARY, SECOND])
    s.eq(len(got), 1, "one entry per record folded in, the primary excepted")
    s.eq(got[0]["imprint"], "Yurihime comics",
         "CARRYING THE LINE THE BLOCK STOPPED SHOWING; this is the name that reached a reader as "
         "???? once the census could no longer see it")
    s.eq(got[0]["distributor"], "講談社", "and the party the primary record does not name")
    s.eq(got[0]["first"], "2017-05",
         "with the folded record's OWN dates, so an imprint's span is measured where the imprint is")
    s.check("work_id" not in got[0],
            "and nothing else; a party is a name and a date, and `work_ids` is where the "
            "identifiers are answered")

    block = dict(PRIMARY, folded_names=got)
    seen = list(pb.parties(block))
    s.eq(len(seen), 2, "so the passes that count names see both records again")
    s.eq([p.get("imprint") for p in seen], ["IDコミックス　／　Yurihime comics", "Yurihime comics"],
         "each line counted once, undeduplicated, which is what a census of catalogued spellings is")
    s.eq(seen[0], block, "the block itself comes first and comes whole")

    # A RECORD THAT NAMES NOBODY CONTRIBUTES NOTHING, which is why the number of parties is not the
    # number of records and `work_ids` is the only honest answer to how many there were.
    s.eq(pb.folded_names([PRIMARY, {"work_id": "x", "volumes": 1, "publisher": "", "imprint": None}]),
         [], "a folded record stating no party at all adds no party")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
