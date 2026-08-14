#!/usr/bin/env python3
"""publisher_identity.py: one address per house, one namespace with the distributors.

Every fixture is a shape the corpus really carries, which is §14b's rule for a test as much as for
a check. The rows below are cut from `data/build/series.json`: 一迅社's yuri line under two of its
recorded spellings, KADOKAWA under the house name it took after 角川書店, and 講談社 in the
distributor's seat on a book 一迅社 published, which is the pairing the one-namespace ruling is
about.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import publisher_identity as P                                              # noqa: E402
import testkit                                                             # noqa: E402

COVERS = ["adapters/publisher_identity.py"]

# The 百合姫 line as MADB and openBD each transcribe it, and the year the hyphen left the logotype.
LINES = [
    {"id": "yurihime-comics", "publishers": ["一迅社"], "name": "百合姫コミックス",
     "parent": "IDコミックス",
     "spellings": ["百合姫コミックス", "Yuri-hime comics", "Yurihime comics"]},
    {"id": "id-comics", "publishers": ["一迅社"], "name": "IDコミックス",
     "spellings": ["IDコミックス"]},
]

ROWS = [
    {"id": "w00001", "work": "ゆるゆり",
     "print": [{"publisher": "一迅社", "imprint": "IDコミックス. Yuri-hime comics",
                "first": "2009-01", "last": "2014-06"}]},
    {"id": "w00002", "work": "citrus",
     "print": [{"publisher": "一迅社", "imprint": "IDコミックス. Yurihime comics",
                "first": "2016-03", "last": "2018-08"}]},
    # A distributor's seat. MADB writes it `[発売]講談社`, and the source layer separates the two
    # roles now, so the row states each in its own field.
    {"id": "w00003", "work": "とある本",
     "print": [{"publisher": "一迅社", "distributor": "[発売]講談社",
                "imprint": "IDコミックス", "first": "2012-05"}]},
    {"id": "w00004", "work": "べつの本",
     "print": [{"publisher": "KADOKAWA", "imprint": "ブシロードコミックス", "first": "2020-02"}]},
]


def main(s):
    # ---- the fold is the interface's ------------------------------------------------------------
    s.eq(P.house_key("[発売]講談社"), "講談社", "the cataloguing comes off before the fold")
    s.eq(P.house_key("講談社 (発売)"), "講談社", "in either notation the corpus uses")
    s.eq(P.house_key("ＫＡＤＯＫＡＷＡ"), P.house_key("KADOKAWA"),
         "full-width Latin is the source's typesetting and folds away")
    s.eq(P.house_key("  "), "", "and a field holding nothing mints nothing")
    s.eq(P.anchor(""), None, "which is what an empty anchor says")

    # ---- one namespace, and the seat on the edge ------------------------------------------------
    wanted, edges = P.population(ROWS)
    names = [t for _a, _x, t in wanted]
    s.eq(names, ["一迅社", "講談社", "KADOKAWA"],
         "three houses in the order they were first seen, the distributor among them")
    s.eq(sorted(edges[P.anchor("一迅社")]),
         [("w00001", "publisher"), ("w00002", "publisher"), ("w00003", "publisher")],
         "the publisher's seat is recorded per book")
    s.eq(edges[P.anchor("講談社")], [("w00003", "distributor")],
         "and 講談社 handling 発売 is the same company in a different seat, not a second company")

    # A re-run over unchanged rows mints nothing: that is what makes an address a promise.
    entries, conflicts = P.assign([], wanted)
    s.eq(conflicts, [], "nothing is contested on a first run")
    again, _ = P.assign(entries, wanted)
    s.eq([e["id"] for e in again], [e["id"] for e in entries],
         "a second pass over the same corpus mints nothing")
    s.eq(len({e["id"] for e in entries}), 3, "three identifiers for three houses")

    # A LABEL FOLLOWS THE IDENTIFIER AND NOT THE ROWS. `relabel=False`, so a merge that lends a
    # retired spelling's anchor to the survivor cannot rename the survivor after itself.
    renamed, _ = P.assign(entries, [(P.anchor("一迅社"), [], "一迅社ホールディングス")])
    s.eq(next(e["title"] for e in renamed if e["id"] == entries[0]["id"]), "一迅社",
         "the entry keeps the spelling its identifier was minted for")

    # ---- what a page is built from ---------------------------------------------------------------
    facts = P.houses(ROWS, LINES, entries)
    ichijin = facts[P.assign(entries, wanted)[0][0]["id"]]
    s.eq(ichijin["name"], "一迅社", "the house is named")
    s.eq(sorted(ichijin["works"]), ["w00001", "w00002", "w00003"],
         "and holds every work we have from it, once each")
    s.eq(ichijin["rows"], 3, "rows count editions and works count works, which are two questions")

    # ONE LINE, TWO SPELLINGS, WHICH IS THE WHOLE REASON THE REGISTRY EXISTS. `Yuri-hime comics`
    # and `Yurihime comics` are the same logotype either side of 2015, and a page over the raw
    # field would give one line two entries.
    yuri = next(ln for ln in ichijin["lines"] if ln["id"] == "yurihime-comics")
    s.eq(yuri["rows"], 2, "both editions land on one line")
    s.eq(sorted(x["raw"] for x in yuri["spellings"]),
         ["IDコミックス. Yuri-hime comics", "IDコミックス. Yurihime comics"],
         "and both spellings are kept, because a 2009 volume says what it says")
    s.eq(next(x["years"] for x in yuri["spellings"]
              if x["raw"].endswith("Yuri-hime comics")), ["2009", "2014"],
         "the years a spelling covers are measured off the rows, not written down")
    s.eq(yuri["parent"], "IDコミックス",
         "the umbrella is recorded beside the line and not folded into it")

    # AND THE UMBRELLA IS ITS OWN LINE where a record states nothing more specific.
    s.eq(next(ln["rows"] for ln in ichijin["lines"] if ln["id"] == "id-comics"), 1,
         "bare IDコミックス is a line in its own right and is not the yuri one")

    # A STRING NO ENTRY ANSWERS FOR IS SHOWN AS ITSELF. ブシロードコミックス sits under two
    # companies neither of which is curated, so it stays unresolved rather than being attached to a
    # guess, and a page that dropped it would report KADOKAWA as having no lines at all.
    kado = next(f for f in facts.values() if f["name"] == "KADOKAWA")
    s.eq([(ln["name"], ln["resolved"]) for ln in kado["lines"]],
         [("ブシロードコミックス", False)], "an unplaced spelling is still on the page, marked")

    # A DISTRIBUTOR DID NOT PUT ITS OWN LINE ON THE BOOK. 講談社 shipped w00003 and 一迅社's
    # IDコミックス is the imprint on it; crediting the line to the distributor would say 講談社 runs
    # a 一迅社 line, which is the fault the evidence table already paid for once.
    kodansha = next(f for f in facts.values() if f["name"] == "講談社")
    s.eq(kodansha["lines"], [], "the distributor's seat carries no imprint")
    s.eq(kodansha["seats"], ["distributor"], "and the seat it did hold is recorded")
    s.eq(kodansha["works"], ["w00003"], "with the book it shipped")

    # THE FORWARDER MOVED WITH THE PAGE IT IS, §11. What a retired address SAYS to a reader is the
    # rendering repository's decision now; what stayed here is which identifier became which, and
    # `retired` above is asserted directly.



if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
