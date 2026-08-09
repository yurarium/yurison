#!/usr/bin/env python3
"""interpunct.py: whether a ・ separates two people or sits inside one person's name.

COVERS = ['adapters/facts/credit/interpunct.py',
          'adapters/facts/credit/__init__.py']

WHAT THIS HAS TO PIN, and every case in it is a credit field this corpus really carries.

  BOTH DIRECTIONS OF THE RULE. `矢立肇・富野由悠季` is two people and the bibliography writes them
  apart on the same work; `くろば・Ｕ` is one person and nothing anywhere credits くろば or Ｕ alone.
  A rule tested in one direction only is a rule that has been shown to say yes.

  THE EVIDENCE THE RULE MAY NOT USE. The name store holds records for くろば and for Ｕ, because
  the splitter under question put them there, so a rule that asks the store answers SEVERAL for all
  twelve strings and the site publishes `Kuro Ba, U`. The fixture below carries those records on
  purpose, and the assertion is that the answer does not change when they are there.

  THE SHAPE RULE THAT WAS REJECTED. `スタジオクロマト・スタジオコロリド` holds no kanji and is two
  animation studios, which is the counter-case that killed "every piece holds a kanji means two
  people". It is pinned so the shape rule cannot come back without failing here first.

Offline: the fields, the splitter and the ruling file are all literals. Nothing reads a file and
nothing reaches a network.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))

import testkit  # noqa: E402
from facts.credit import interpunct  # noqa: E402

COVERS = ["adapters/facts/credit/interpunct.py",
          "adapters/facts/credit/__init__.py"]

# Credit fields as the corpus spells them. The four holding an interpunct are every shape the
# question comes in; the rest are what the evidence is read from, and each is a field that really
# credits the person it names.
FIELDS = [
    # THE FOUR UNDER QUESTION.
    "くろば・Ｕ",
    "工藤マコト / 矢立肇・富野由悠季",
    "米田タロウ / スタジオクロマト・スタジオコロリド",
    "ハマノーン / ブリリアント・ブラウン",
    # THE EVIDENCE. Each of these is a field with no interpunct in it, which is the only kind this
    # module reads, and each states one of the pieces above on its own.
    "矢立肇 / 公野櫻子 / 田中天 / つむみ",
    "HISADAKE / 富野由悠季 / 波多ヒロ / 矢立肇",
    "スタジオクロマト / スタジオコロリド / 米田タロウ",
    # AND A FIELD THAT SAYS NOTHING ABOUT ANY OF THEM, so the attested set is not simply everything.
    "[著]文尾文",
]


def split(field):
    """The splitter, stubbed: parts on the ordinary separators, with the interpunct kept inside one.

    A stub rather than `inputs.split_credits_detail` because this suite is about the rule and not
    about the notation, and a stub that could not keep a ・ inside a part would make every
    assertion below pass for the wrong reason. `test_inputs.py` is where the real splitter is
    pinned against the same two strings.
    """
    out = []
    for part in re.split(r"[/／、,，&＆]", str(field or "")):
        part = re.sub(r"^\[[^\]]*\]", "", part).strip()
        if part:
            out.append(part)
    return out


def main(s):
    s.eq(split("工藤マコト / 矢立肇・富野由悠季"), ["工藤マコト", "矢立肇・富野由悠季"],
         "the stub keeps an interpunct inside a part, which every assertion below depends on")

    attested = interpunct.attested_apart(FIELDS, split)
    s.check("矢立肇" in attested,
            "a name a field with no interpunct credits on its own is evidence")
    s.check("くろば" not in attested and "Ｕ".lower() not in attested,
            "and a piece that appears nowhere except inside the string under question is not")
    s.check("矢立肇・富野由悠季" not in attested,
            "a field holding an interpunct contributes nothing at all, which is what stops the "
            "evidence being read out of the question")

    # ── the rule, in both directions ──────────────────────────────────────────────────────────
    s.eq(interpunct.role("くろば・Ｕ", attested), interpunct.ONE,
         "nothing credits くろば or Ｕ alone, so the ・ is a character in one person's name")
    s.eq(interpunct.role("矢立肇・富野由悠季", attested), interpunct.SEVERAL,
         "and the bibliography lists 富野由悠季 and 矢立肇 apart on the same work, so it separates")
    s.eq(interpunct.role("ブリリアント・ブラウン", attested), interpunct.ONE,
         "a pen name in katakana either side of a ・ is one artist until something credits a half")
    s.eq(interpunct.role("スタジオクロマト・スタジオコロリド", attested), interpunct.SEVERAL,
         "THE COUNTER-CASE THAT KILLED THE SHAPE RULE. No kanji anywhere in it, and the "
         "bibliography lists the two studios apart on 超かぐや姫!, so shape would have joined them")
    s.eq(interpunct.role("工藤マコト", attested), interpunct.ONE,
         "a name with no interpunct in it is one person, which is an answer and not a default")

    # ── the state a person is asked about ─────────────────────────────────────────────────────
    s.eq(interpunct.role("矢立肇・くろば", attested), interpunct.UNDECIDED,
         "one piece credited alone and one never is evidence pointing both ways, and a wrong "
         "split invents a person while a wrong join erases one")
    s.eq(interpunct.unruled(FIELDS + ["矢立肇・くろば"], split), ["矢立肇・くろば"],
         "so it is what the budget counts, by name, rather than being decided quietly")
    s.eq(interpunct.unruled(FIELDS, split), [],
         "and the corpus as it stands owes nobody a ruling")

    # ── a person's ruling wins, and an unanswered one holds ───────────────────────────────────
    ruled = {interpunct.key.fold("矢立肇・富野由悠季"): interpunct.ONE,
             interpunct.key.fold("くろば・Ｕ"): None}
    s.eq(interpunct.settle("矢立肇・富野由悠季", attested, ruled), interpunct.ONE,
         "a ruling in the file overturns the corpus, because it is a judgement and this is a count")
    s.eq(interpunct.settle("くろば・Ｕ", attested, ruled), interpunct.UNDECIDED,
         "and a key written with no answer under it holds the string instead of settling it")
    s.eq(interpunct.settle("ブリリアント・ブラウン", attested, ruled), interpunct.ONE,
         "a string the file says nothing about is the rule's, so there is one answer per string")

    # ── what the callers are handed ───────────────────────────────────────────────────────────
    got = interpunct.settled(FIELDS, split)
    s.eq(got, {interpunct.key.fold("くろば・Ｕ"): interpunct.ONE,
               interpunct.key.fold("ブリリアント・ブラウン"): interpunct.ONE,
               interpunct.key.fold("矢立肇・富野由悠季"): interpunct.SEVERAL,
               interpunct.key.fold("スタジオクロマト・スタジオコロリド"): interpunct.SEVERAL},
         "BOTH ANSWERS TRAVEL, because the two callers default in opposite directions: the store "
         "splits a ・ and a printed byline keeps it, so a map of only the names to keep whole "
         "would leave one of them wrong")

    # ── THE BLIND SPOT THE OLD RULE HAD, pinned as a difference (§14b) ────────────────────────
    #
    # The store holds くろば, Ｕ, ブリリアント and ブラウン because the splitter put them there.
    # `creditline._is_a_name_of_its_own` asked the store, so it answered SEVERAL for every one of
    # these and the site published `Kuro Ba, U`. Adding those records to the evidence must change
    # nothing, and this is the assertion that says so.
    polluted = set(attested) | {interpunct.key.fold(x) for x in
                                ("くろば", "Ｕ", "ブリリアント", "ブラウン", "さりい", "Ｂ")}
    s.eq(interpunct.role("くろば・Ｕ", attested), interpunct.ONE,
         "the answer with the evidence read honestly")
    s.eq(interpunct.role("くろば・Ｕ", polluted), interpunct.SEVERAL,
         "AND WHAT THE STORE WOULD HAVE SAID, which is the wrong answer and the reason the "
         "evidence may not be read off anything the splitter produced")

    # ── the ruling file, read as it ships ─────────────────────────────────────────────────────
    here = pathlib.Path(__file__).resolve().parents[2] / interpunct.RULINGS
    s.eq(interpunct.load_rulings(here), {},
         "the file ships with no rulings in it, because the corpus settles every string it holds")
    s.eq(interpunct.load_rulings(here.parent / "no-such-file.yaml"), {},
         "and an absent file is an empty set of rulings rather than an error at build time")


    # THE FACT'S OWN SURFACE: the ruling is held, and holding it is what makes the default safe.
    from facts import credit as cf

    before = cf.rulings()
    try:
        cf.use_rulings({})
        s.eq([n for n, _ in cf.split("くろば・Ｕ")], ["くろば", "Ｕ"],
             "with no ruling installed, a ・ separates")
        cf.use_rulings({cf.key.fold("くろば・Ｕ"): cf.ONE})
        s.eq([n for n, _ in cf.split("くろば・Ｕ")], ["くろば・Ｕ"],
             "with the ruling installed, one person stays whole")
        # AND THE OTHER DIRECTION, because a rule that only ever joins would pass the case above
        # and quietly glue two people together.
        cf.use_rulings({cf.key.fold("矢立肇・富野由悠季"): cf.SEVERAL})
        s.eq(len(cf.split("矢立肇・富野由悠季")), 2, "two people ruled apart stay apart")
        # IGNORING THE RULING IS AN ACT, which is the whole point of inverting the default.
        cf.use_rulings({cf.key.fold("くろば・Ｕ"): cf.ONE})
        s.eq([n for n, _ in cf.split_unruled("くろば・Ｕ")], ["くろば", "Ｕ"],
             "split_unruled ignores it deliberately")
        s.eq(cf.rulings(), cf.rulings(), "rulings() answers a copy, never the live map")
        cf.rulings()["planted"] = "one"
        s.check("planted" not in cf.rulings(), "and mutating that copy changes nothing")
    finally:
        cf.use_rulings(before)


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
