#!/usr/bin/env python3
"""madb_reading.py: the creator reading MADB has always carried and nothing read."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import madb_reading as mr  # noqa: E402

COVERS = ["adapters/names/madb_reading.py"]

HRKT = "ja-hrkt"


def rec(creator, name="ある本", publisher="一迅社", ident="M1"):
    return {"schema:creator": creator, "schema:name": name,
            "schema:publisher": publisher, "schema:identifier": ident}


# Quoted from metadata101.json of release 1.2.18.
ONE = rec(["ほしのなつみ", {"@value": "ホシノナツミ", "@language": HRKT}])
ROLE = rec(["[著]石渡治", {"@value": "イシワタオサム", "@language": HRKT}])
YEARED = rec(["篠原健太", {"@value": "シノハラケンタ 1974-", "@language": HRKT}])

# TWO PEOPLE, TWO SHAPES, and the second is why this test exists. The names are in one order and
# the readings in another, so the first of each are not each other's: 城之内寧々 is ジョウノウチネネ
# and カワナアメ is 川奈あめ.
TWO_ELEMENTS = rec(["城之内寧々", "川奈あめ",
                    {"@value": "カワナアメ", "@language": HRKT},
                    {"@value": "ジョウノウチネネ", "@language": HRKT}])
TWO_IN_ONE = rec(["[著]畠山耕太郎 /松田康志",
                  {"@value": "ハタヤマコウタロウマツダヤスシ", "@language": HRKT}])

BARE = rec("高倉ゆり")


def main(s):
    s.eq(mr.credit_reading(ONE), ("ほしのなつみ", "ホシノナツミ"),
         "the credit and the reading MADB files beside it")
    s.eq(mr.credit_reading(ROLE), ("石渡治", "イシワタオサム"),
         "with the cataloguing role off the name")
    s.eq(mr.credit_reading(YEARED), ("篠原健太", "シノハラケンタ"),
         "and the birth year off the reading")

    # THE BUG THIS MODULE SHIPPED WITH. Reading the first name and the first reading paired
    # 城之内寧々 with 川奈あめ's, and it was caught on four names only because their other records
    # disagreed. A person credited only ever beside somebody else would have been misnamed with
    # nothing to notice.
    s.eq(mr.credit_reading(TWO_ELEMENTS), None,
         "a record naming two people yields nothing, because MADB does not pair them")
    s.eq(mr.credit_reading(TWO_IN_ONE), None,
         "and neither does one naming two people in a single string with one reading")
    s.eq(mr.credit_reading(BARE), None, "a credit with no reading beside it is not a reading")
    s.eq(mr.credit_reading({}), None, "and neither is a record with no credit at all")

    idx = mr.index([ONE, ROLE, TWO_ELEMENTS, BARE])
    s.eq(sorted(idx), sorted(["ほしのなつみ", "石渡治"]),
         "the index holds only what the pairing rule accepted")

    s.eq(mr.resolve(idx, "ほしのなつみ")[0], "ホシノナツミ", "and answers for a name it holds")
    s.eq(mr.resolve(idx, "城之内寧々")[0], None,
         "and states nothing for a person it refused to pair")
    s.eq(mr.resolve(idx, "城之内寧々")[1]["status"], "no-record",
         "which is a finding rather than an error")

    # A DISAGREEMENT IS NOT A MAJORITY TO TAKE. 白沢まりも is filed both シラサワマリモ and
    # シロサワマリモ across 46 records, and one of those may be somebody else.
    split = mr.index([rec(["白沢まりも", {"@value": "シラサワマリモ", "@language": HRKT}]),
                      rec(["白沢まりも", {"@value": "シロサワマリモ", "@language": HRKT}])])
    s.eq(mr.resolve(split, "白沢まりも")[0], None, "two readings for one name settle nothing")
    s.eq(mr.resolve(split, "白沢まりも")[1]["status"], "conflicting", "and say why")

    found, unresolved = mr.entries(idx, {"ほしのなつみ": None, "城之内寧々": "ジョウノウチ ネネ"},
                                   "2026-08-06")
    s.eq(sorted(found), ["ほしのなつみ"], "an entry is proposed only where the catalogue states one")
    s.eq(found["ほしのなつみ"]["reading_basis"], "stated",
         "a national catalogue stating a reading is `stated`")
    s.eq(found["ほしのなつみ"]["reading_source_kind"], "national-library",
         "and the evidence is a national cataloguing authority")
    s.check("ある本" in found["ほしのなつみ"]["reading_note"],
            "the note names a record a reviewer can go and check")
    s.eq(unresolved["城之内寧々"], "no-record", "and the rest are reported, not guessed at")

    # HEALTH. A release file that failed to load and a catalogue with no readings both give an
    # empty index, settle nothing, and report a clean run.
    s.eq(mr.healthy(idx)[0], False, "an index of two names is a load that went wrong")
    s.eq(mr.healthy({str(i): [] for i in range(6000)})[0], True,
         "and a full release clears the floor")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, __file__))
