#!/usr/bin/env python3
"""openbd_reading.py: taking a publisher's registered reading off a book, and refusing the rest."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import openbd_reading as ob  # noqa: E402

COVERS = ["adapters/names/openbd_reading.py"]


def book(isbn, title, publisher, people):
    """One openBD record, cut to the fields this reads. `people` is [(content, collationkey)]."""
    return {isbn: {
        "summary": {"isbn": isbn, "title": title, "publisher": publisher},
        "onix": {"DescriptiveDetail": {"Contributor": [
            {"SequenceNumber": str(i + 1),
             "PersonName": {k: v for k, v in (("content", n), ("collationkey", r)) if v}}
            for i, (n, r) in enumerate(people)]}}}}


# Quoted from api.openbd.jp as served 2026-08-05. Two volumes of one series, filed under the same
# registration, which is the ordinary shape: agreement comes free and a disagreement is a finding.
SWEET = {**book("9784758070003", "ストロベリーシェイクsweet 1", "一迅社",
                [("林家, 志弦", "ハヤシヤ, シズル")]),
         **book("9784758070010", "ストロベリーシェイクsweet 2", "一迅社",
                [("林家, 志弦", "ハヤシヤ, シズル")])}

# An anthology, where the reading wanted is not the first one on the record.
TWO = book("9784758071000", "アンソロジー", "一迅社",
           [("天野, しゅにんた", "アマノ, シュニンタ"), ("東雲, 水生", "シノノメ, ミズオ")])

# openBD holds nothing for this ISBN. It answers with a null in place of the record, and a null is
# a state: it means the book is not in the registration, not that the fetch failed.
ABSENT = {"9784758079999": None}

# A registration with the name and no reading. The name alone is already on the shelf, so this
# record states nothing and must not be counted as if it did.
NO_KEY = book("9784758071111", "名前だけ", "一迅社", [("寝路", None)])


def main(s):
    reading, ev = ob.resolve(SWEET, "林家志弦")
    s.eq(reading, "ハヤシヤ シズル", "the registration's comma becomes the space the store uses")
    s.eq(ev["status"], "stated", "and the publisher stating it is what makes it a reading")
    s.eq(ev["records"], 2, "resting on both volumes rather than on one of them")
    s.eq(ev["examples"][0], ("ストロベリーシェイクsweet 1", "一迅社"),
         "each named so a reviewer can go and look")

    s.eq(ob.resolve(TWO, "東雲水生")[0], "シノノメ ミズオ",
         "the second contributor's reading, not the first one on the record")
    s.eq(ob.resolve(TWO, "天野しゅにんた")[0], "アマノ シュニンタ", "and the first for the first")

    # A PARTIAL MATCH IS NOT A MATCH, the rule that keeps one artist's reading off another's work.
    s.eq(ob.resolve(SWEET, "林家")[0], None, "a surname does not answer for a full name")
    s.eq(ob.resolve(SWEET, "林家志弦子")[0], None, "and a longer name is a different person")
    s.eq(ob.resolve(SWEET, "")[0], None, "no name, no answer")

    # SILENCE HAS TO SURVIVE THE PARSE. openBD returns a null per ISBN it does not hold, and a
    # record with no collationkey states no reading. Both are `no-record`, and neither may raise or
    # be filled in from the characters.
    r, ev = ob.resolve(ABSENT, "寝路")
    s.eq(r, None, "an ISBN openBD does not hold settles nothing")
    s.eq(ev["status"], "no-record", "and says so as a state")
    s.eq(ev["records"], 0, "counted as none rather than reported as one")
    s.eq(ob.resolve(NO_KEY, "寝路")[0], None, "a name with no reading beside it is not a reading")
    s.eq(ob.contributors(None), [], "a missing record has no contributors, and does not raise")
    s.eq(ob.contributors({"onix": {}}), [], "nor does a record with nothing under onix")
    s.eq(ob.resolve({}, "寝路")[1]["status"], "no-record", "nothing asked, nothing found")

    # TWO REGISTRATIONS DISAGREEING settle nothing, because one of them may be somebody else. This
    # is `ndl_reading.settle`'s rule and the test is here so that reusing it is what is asserted.
    both = {**book("9784758072000", "A", "一迅社", [("灯", "アカシ")]),
            **book("9784758072001", "B", "一迅社", [("灯", "アカリ")])}
    r, ev = ob.resolve(both, "灯")
    s.eq(r, None, "two readings for one written name settle nothing")
    s.eq(ev["status"], "conflicting", "and are reported as the finding they are")
    s.eq(ev["readings"], ["アカシ", "アカリ"], "with both kept for whoever looks")

    # The split and unsplit forms of one reading are not a conflict, and the split one wins.
    same = {**book("9784758073000", "A", "一迅社", [("東雲, 水生", "シノノメ, ミズオ")]),
            **book("9784758073001", "B", "一迅社", [("東雲水生", "シノノメミズオ")])}
    s.eq(ob.resolve(same, "東雲水生")[0], "シノノメ ミズオ",
         "one reading written two ways keeps the form carrying the boundary")

    # WHAT A PROPOSED ENTRY CLAIMS, and what it must not. `stated` by a `publisher-jp` source is
    # the pair curate.py demands, and the note has to say what the reading replaced: an entry that
    # silently overwrites a guess is indistinguishable from one that restates it.
    found, unresolved = ob.entries(SWEET, {"林家志弦": "ハヤシヤ シヅル"}, "2026-08-05")
    e = found["林家志弦"]
    s.eq(e["reading"], "ハヤシヤ シズル", "the publisher's reading, replacing the analyser's")
    s.eq(e["reading_basis"], "stated", "stated, because a publisher said it")
    s.eq(e["reading_source_kind"], "publisher-jp", "and the publisher is the evidence for it")
    s.check("ハヤシヤ シヅル" in e["reading_note"], "the note names the guess it replaces")
    s.check("9784758070003" in e["source_url"], "and links the registration it was read from")
    s.eq(unresolved, {}, "nothing left over when the reading is settled")

    _, unresolved = ob.entries(ABSENT, {"寝路": "ネジ"}, "2026-08-05")
    s.eq(unresolved, {"寝路": "no-record"},
         "a name openBD cannot answer for is reported, not filled in")

    # A READING THAT IS NOT KATAKANA IS NOT APPLIED. curate.py refuses one, and a proposal that
    # cannot be applied reports success here and fails there, which is a round trip for nothing.
    kanji = book("9784758074000", "C", "一迅社", [("八色", "八色")])
    _, unresolved = ob.entries(kanji, {"八色": "ヤイロ"}, "2026-08-05")
    s.eq(unresolved, {"八色": "not-katakana"},
         "a registration echoing the characters back states no reading")

    # A HOST IN TROUBLE LOOKS EXACTLY LIKE A SHELF NOBODY REGISTERED, so the pass refuses to read a
    # payload that is null all the way down rather than reporting nought settled as a finding.
    s.eq(ob.healthy(SWEET), (True, 2, 2), "records to read is the ordinary case")
    s.eq(ob.healthy({**SWEET, **ABSENT}), (True, 2, 3),
         "and a few ISBNs openBD has dropped is the inventory being an inventory")
    s.eq(ob.healthy(ABSENT)[0], False, "every record null is a floor, not a result")
    s.eq(ob.healthy({})[0], True, "asking about nothing is not a failure to answer")

    # A TRUNCATED ANSWER IS THE CASE "at least one record" MISSES. A batch loop that dies after the
    # first batch comes back holding a few of many, settles a few names, and reads as a thin day.
    thin = {**SWEET, **{f"978475809{n:04d}": None for n in range(20)}}
    s.eq(ob.healthy(thin), (False, 2, 22), "two records out of twenty-two is a fetch that stopped")
    s.eq(ob.healthy({**SWEET, **{"9784758079998": None, "9784758079997": None}})[0], True,
         "and the floor is half, so two held of four is still a run worth reading")

    s.eq(ob.query(["9784758070003", "9784758070010"]),
         "https://api.openbd.jp/v1/get?isbn=9784758070003%2C9784758070010",
         "one request carries the whole series, which is why this route is affordable")

    # MADB's role brackets are cataloguing rather than the name. `[作画]蔵王大志 / [原作]影木栄貴`
    # is two people, and reading it as one string finds neither of them.
    credits = ob.madb_credits(str(pathlib.Path(__file__).resolve().parents[2]
                                  / "data" / "source" / "madb"))
    s.check("東雲水生" in credits, "a credit is found under the name without its role")
    s.check(all(not c.startswith("[") for c in credits), "no credit keeps its role bracket")

    # MADB ALSO PUTS THE NAME IN A BRACKET: `[上田香子][訳]`, with the role in the next group. A
    # stripper that removed one leading group left `[訳]` standing where a person should be, and a
    # role is not a person. Which group is the name is decided by what it is spelt out of.
    s.eq(ob.credit_name("[上田香子][訳]"), "上田香子", "a bracketed name keeps its content")
    s.eq(ob.credit_name("[作・画]ステファン・セジク"), "ステファン・セジク",
         "a leading role is still dropped, middle dot and all")
    s.eq(ob.credit_name("[訳]"), "", "and a credit that is only a role names nobody")
    s.eq(ob.credit_name("東雲水生"), "東雲水生", "a bare name is untouched")
    s.eq(ob.credit_name("[[著]]椿木とりか"), "椿木とりか", "a doubled delimiter is still one")
    # AND SOME OF THEM ARE TEN DIGITS. Six books from 2006 and 2007 carry a pre-2007 ISBN-10 in
    # MADB, so a check that every ISBN is thirteen digits is a rule the data itself refutes. It was
    # written that way first and caught here, which is the counter-case being worth more than the
    # rule (STANDING-INSTRUCTIONS §2).
    s.check(all(i.isdigit() and len(i) in (10, 13) for v in credits.values() for i in v),
            "and every ISBN collected is one, in either of the two lengths in use")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
