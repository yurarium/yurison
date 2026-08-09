#!/usr/bin/env python3
"""boundary.py: a division is carried from a source or the name stays whole."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import boundary as b  # noqa: E402

COVERS = ["adapters/names/boundary.py"]


def main(s):
    # THE CASE THIS EXISTS FOR. 五十嵐純 gets its boundary from a stated reading; いがらしゆみこ
    # has none in its surface and romanised as one word.
    s.eq(b.carry("いがらしゆみこ", "イガラシ ユミコ"), "イガラシ ユミコ",
         "a stated division reaches a kana name written in one run")
    s.eq(b.cuts("イガラシ ユミコ"), (4,), "a division is an offset into the flattened reading")
    s.eq(b.cuts("イガラシユミコ"), (), "and a run states none")

    # OUR KANA, THEIR BOUNDARY. This is the whole safety argument, so it is pinned on the pair
    # openbd_reading.normalised names: the store holds とりいしづく off its own surface and openBD
    # files the same person トリイ シズク, with づ folded to ず by the collation.
    s.eq(b.carry("とりいしづく", "トリイ シズク"), "トリイ シヅク",
         "a filing key supplies the division and never the kana")
    s.eq(b.carry("いづみやおとは", "イズミヤ オトハ"), "イヅミヤ オトハ",
         "the same, on the name that first showed the fold")

    # WHAT MUST NOT BE CARRIED.
    s.eq(b.carry("わらびもちきなこ", "ワラビモチキナコ"), None,
         "a donor stating no division states nothing")
    s.eq(b.carry("わらびもちきなこ", "ワラビ モチキナ"), None,
         "and one that does not correspond is refused: seven kana against eight")
    s.eq(b.carry("わらびもちきなこ", "ワラビモチ キナコ"), "ワラビモチ キナコ",
         "the division this name really has, which is nonetheless only as good as its donor")
    s.eq(b.carry("あきやまはる", "アキヤマ ハルカ"), None,
         "a longer reading is a different name, whatever it shares with this one")
    s.eq(b.carry("いがらしゆみこ", " イガラシユミコ"), None,
         "a space at the edge is punctuation, not a claim about the name")

    # THE NAME THAT IS ONE WORD, which is the population this must never improve. ぬるめた's own
    # tankōbon cover prints こかむも in Latin as Kokamumo, set by the publisher, so the unsplit
    # rendering is already right and a rule that inferred a surname would break it against a
    # published form. Nothing states a division, so nothing is taken.
    s.eq(b.settle("こかむも", [])[1], b.NO_DONOR, "こかむも stays Kokamumo")
    s.eq(b.settle("こかむも", [("コカムモ", "a record with no division in it")])[1],
         b.NO_CORRESPONDENCE, "and a donor that divides nothing adds nothing")

    # DISAGREEMENT IS AN ANSWER. Two sources dividing it differently leave it whole.
    got, why = b.settle("あおたゆきこ", [("アオタ ユキコ", "one"), ("アオ タユキコ", "two")])
    s.eq(got, None, "two divisions of one name settle nothing")
    s.eq(why, b.DISAGREEMENT, "and the refusal says which kind it was")
    got, why = b.settle("あおたゆきこ", [("アオタ ユキコ", "one"), ("アオタ・ユキコ", "two")])
    s.eq(got, "アオタ ユキコ", "an interpunct and a space are the same division")
    s.eq(sorted(why), ["one", "two"], "and both donors are named")
    s.eq(b.settle("わらびもちきなこ", [])[1], b.NO_DONOR, "no donor is its own reason")

    # WHICH RECORDS ARE ASKED ABOUT.
    s.check(b.wants_boundary("いがらしゆみこ", {"reading": "イガラシユミコ"}),
            "a kana name read as one run is asked about")
    s.check(not b.wants_boundary("くわばら たもつ", {"reading": "クワバラ タモツ"}),
            "a surface that divides itself has already answered")
    s.check(not b.wants_boundary("五十嵐純", {"reading": "イガラシジュン"}),
            "a name holding a kanji is the stated reading's business, not this module's")
    s.check(not b.wants_boundary("タイザン5", {"reading": "タイザン5"}),
            "a digit has to be read before it can be divided")
    s.check(not b.wants_boundary("なもり", {"reading": "ナモリ"}),
            "and a name too short to divide is not a question")

    # AND THE GENERAL QUESTION, which is the one `fill` asks. A name holding a kanji was excluded
    # on the reasoning that a stated reading brings its own division, and 太陽まりい is the
    # counter-case: the media-arts catalogue states タイヨウマリイ, correctly, with no division in
    # it at all, so the ordinary path answered and left the person romanised as one word.
    s.check(b.wants_division("太陽まりい", {"reading": "タイヨウマリイ"}),
            "a kanji name whose stated reading states no division is asked about")
    s.check(not b.wants_boundary("太陽まりい", {"reading": "タイヨウマリイ"}),
            "and a donor that supplies no kana still cannot answer for it")
    s.check(not b.wants_division("冬木先輩", {"reading": "フユキ センパイ"}),
            "a reading that already divides is settled, whoever divided it")
    s.check(not b.wants_division("タイザン5", {"reading": "タイザン5"}),
            "a digit in the reading has to be read before the name can be divided")

    # THE STORE'S OWN JOIN, and the basis rule that keeps a guess out of it.
    names = {
        "タグチケンジ": {"reading": "タグチケンジ", "reading_basis": "surface"},
        "田口ケンジ": {"reading": "タグチ ケンジ", "reading_basis": "stated"},
        "ニシマゴメユキ": {"reading": "ニシマゴメユキ", "reading_basis": "surface"},
        "西馬ごめゆき": {"reading": "ニシマ ゴメユキ", "reading_basis": "analyser"},
    }
    s.eq([d for _r, d in b.store_donors(names, "タグチケンジ")], ["田口ケンジ"],
         "the same reading under another spelling states this name's division")
    s.eq(b.store_donors(names, "ニシマゴメユキ"), [],
         "an analyser's boundary is not evidence, which is madb_reading.py's argument")

    added, refusals = b.fill(names)
    s.eq(added, {"タグチケンジ": "タグチ ケンジ"}, "the settled name divides")
    s.eq(names["タグチケンジ"]["reading_boundary"], "田口ケンジ", "and says where it came from")
    s.eq(refusals[b.NO_DONOR], 1, "the unsettled one is counted, not mangled")
    s.eq(b.fill(names)[0], {}, "a second run finds nothing left to do")

    # THE SAME PERSON UNDER TWO SPELLINGS OF THEIR OWN NAME, which is where a kanji surface gets
    # divided without anybody guessing. 山本和音 and 山本 和音 are one artist and the corpus holds
    # both; the spaced one states the division and the closed one had none.
    two = {"山本和音": {"reading": "ヤマモトカズネ", "reading_basis": "stated"},
           "山本 和音": {"reading": "ヤマモト カズネ", "reading_basis": "stated"}}
    got, _left = b.fill(two)
    s.eq(got, {"山本和音": "ヤマモト カズネ"}, "the division carries onto the reading of a kanji name")
    s.eq(two["山本和音"]["reading_boundary"], "山本 和音", "and names the record it came from")

    # THE STORE ON DISK, which is what build.py's autopilot calls.
    import tempfile
    import yaml
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / "authors.yaml"
        p.write_text(yaml.safe_dump({"names": {
            "アイザキウタウ": {"reading": "アイザキウタウ", "reading_basis": "surface"},
            "相崎うたう": {"reading": "アイザキ ウタウ", "reading_basis": "stated"}}},
            allow_unicode=True))
        added, _left = b.fill_store(p)
        s.eq(added, {"アイザキウタウ": "アイザキ ウタウ"}, "the store on disk divides too")
        back = yaml.safe_load(p.read_text())["names"]["アイザキウタウ"]
        s.eq(back["reading"], "アイザキ ウタウ", "and the file holds it")
        s.eq(back["reading_boundary"], "相崎うたう", "with the record it came from")
    s.eq(b.fill_store(pathlib.Path(tmp) / "gone.yaml"), ({}, {}),
         "no store is the documented fallback, not an error")

    # ── The division that was written into prose, and the migration that moved it ─────────────
    # `ndl_heading.entry` and `openbd_reading.boundary_entries` stated where a name divides in
    # `reading_note`. 293 records cited it there and nowhere else, so every count reading
    # `reading_boundary` read them as sourceless and could not tell 293 from 0.
    s.eq(b.divisions("ワラビモチ キナコ"), 2, "a reading in two pieces states one division")
    s.eq(b.divisions("わらびもちきなこ"), 1, "and an unbroken surface states none")
    s.eq(b.divisions("さりい・Ｂ"), 1,
         "an interpunct is a character in a name here, which is why this is not `cuts`")
    s.eq(len(b.cuts("トリイ・シヅク")), 1, "while a donor writing one is dividing the name")

    NDL = ("The National Diet Library's author heading on record R100000002-I031868330 divides "
           "this person as 'アクタ リンコ'. The kana here are the name's own surface.")
    s.eq(b.donors_named_in(NDL),
         ["the National Diet Library's author heading on record R100000002-I031868330"],
         "the heading names the record it was read off")
    # THE SENTENCE THAT WRITES A FULL STOP INSIDE ITSELF, and the first pattern stopped at it: 37
    # records kept their division in prose because openBD's own note says `e.g.` in the middle.
    OPENBD = ("openBD's collationkey on 8 volume(s), e.g. 'きみが死ぬまで恋をしたい 3' (講談社), "
              "divides this name as 'アオノ ナチ'. It divides 'アオノナチ'.")
    s.eq(b.donors_named_in(OPENBD), ["openBD's collationkey"],
         "a full stop inside the sentence does not end it")
    s.eq(b.donors_named_in("まんが王国 prints this reading in the byline of the 2 book(s) it sells "
                           "under this name."), [],
         "a note that argues only about the sounds names no donor")
    s.eq(b.donors_named_in(None), [], "and a record with no note names none either")

    moved, left = b.from_notes({
        "わらびもちきなこ": {"reading": "ワラビモチ キナコ", "reading_source_kind": "derived",
                             "reading_note": NDL},
        "あおのなち": {"reading": "アオノ ナチ", "reading_source_kind": "derived",
                       "reading_note": OPENBD},
        "こかむも": {"reading": "コカムモ", "reading_source_kind": "derived"},
        "山本和音": {"reading": "ヤマモト カズネ", "reading_source_kind": "national-library"},
        "生肉": {"reading": "ナマ ニク", "reading_source_kind": "derived",
                 "reading_note": "the shop files them under these kana"}})
    s.eq(sorted(moved), ["あおのなち", "わらびもちきなこ"],
         "a division stated in prose moves into the field")
    s.eq(sorted(left), ["生肉"],
         "and a record whose kana are ours and whose prose names nobody is reported, not skipped")
    s.eq(b.from_notes({"わらびもちきなこ": {"reading": "ワラビモチ キナコ",
                                            "reading_boundary": "already said",
                                            "reading_note": NDL}}), ({}, {}),
         "a record that already names its donor is left alone, so a second run costs nothing")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
