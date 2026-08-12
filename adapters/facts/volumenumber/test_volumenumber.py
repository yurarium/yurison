#!/usr/bin/env python3
"""facts/volumenumber: the volume number a shop's product title states.

COVERS = ['adapters/facts/volumenumber/__init__.py']

EVERY TITLE BELOW IS ONE BOOK☆WALKER HOLDS. The fault this replaces published the item's POSITION
in a shop listing as its volume number, so the cases that matter are the ones where the position
and the number disagree, and each of them is a record named in VOLUMES-PLAN §2.

What the module must refuse is as important as what it reads. A number it cannot read is None, and
None is the honest answer; a number invented from a position is what put volumes 30, 31 and 32 into
a work that has 29.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import volumenumber as vn                                    # noqa: E402

MURCIELAGO = "MURCIÉLAGO -ムルシエラゴ-"


def main(s):
    # ── THE RECORD THE FAULT WAS FOUND ON ─────────────────────────────────────────────────────
    #
    # The shop's 32 products are 29 volumes and 3 free samples, and the last product is volume 29.
    # Position said 32, and the corpus published a work with 32 volumes.
    s.eq(vn.stated("【最新刊】MURCIÉLAGO -ムルシエラゴ- 29巻", MURCIELAGO), "29",
         "the last of 32 products states that it is volume 29, and the shop's badge is not a name")
    s.eq(vn.stated("MURCIELAGO -ムルシエラゴ- 3巻", MURCIELAGO), "3",
         "AND THE ACCENT IS NOT A DIFFERENT SERIES; the shop files the series with É and this "
         "volume without, so a strict prefix test fails on the exact record this was written for")
    s.check(vn.is_sample("MURCIÉLAGO -ムルシエラゴ- 1巻【無料お試し版】"),
            "a free sample is not a volume, which is where 3 of the 32 went")
    s.eq(vn.stated("MURCIÉLAGO -ムルシエラゴ- 1巻【無料お試し版】", MURCIELAGO), "1",
         "though it still says which volume it samples, so nothing is lost by reading it")
    s.check(not vn.is_sample("【最新刊】MURCIÉLAGO -ムルシエラゴ- 29巻"),
            "and an ordinary volume is not a sample")

    # ── THE LISTING IS NOT IN VOLUME ORDER, WHICH POSITION ASSUMED ────────────────────────────
    #
    # パロスの剣 lists 【最新刊】3巻 first, so volume 3 was published as volume 1 and volume 1 as
    # volume 2. なないろ黒蝶 runs 1, 3, 2, 4. Neither is recoverable by sorting; only the titles
    # say which is which.
    s.eq([vn.stated(t, "パロスの剣") for t in
          ("【最新刊】パロスの剣　3巻", "パロスの剣　1巻", "パロスの剣　2巻")],
         ["3", "1", "2"], "the first item in the listing is volume 3 and says so")
    s.eq([vn.stated(t, "[カラー版]なないろ黒蝶～KillerAngel") for t in
          ("[カラー版]なないろ黒蝶～KillerAngel　〈女子高生殺し屋集団〉1巻",
           "[カラー版]なないろ黒蝶～KillerAngel　〈眼帯の下の紅い目〉3巻",
           "[カラー版]なないろ黒蝶～KillerAngel　4巻〈報酬30億円のターゲット〉")],
         ["1", "3", "4"],
         "a subtitle on either side of the number is read past, in listing order 1, 3, 4")

    # ── HOW ELSE THE SHOP WRITES IT ───────────────────────────────────────────────────────────
    s.eq(vn.stated("花の三騎士 （1）", "花の三騎士"), "1", "a bracketed number")
    s.eq(vn.stated("わたし、二番目の彼女でいいから。 ２", "わたし、二番目の彼女でいいから。"), "2",
         "a bare full-width number, past the punctuation the title itself ends in")
    s.eq(vn.stated("むぎの日常 vol.1", "むぎの日常"), "1", "vol.N")
    s.eq(vn.stated("夢の端々（下）", "夢の端々"), "下", "and a two volume set numbered by word")
    s.eq(vn.stated("お江戸とてシャン〈完全版〉下", "お江戸とてシャン〈完全版〉"), "下",
         "including where the word follows an edition statement")
    s.eq(vn.stated("【作品名】　１", "作品名"), "1",
         "the series title inside a bracket is still the series title")

    # ── AND WHAT IT REFUSES ───────────────────────────────────────────────────────────────────
    #
    # THE COUNTER-CASE THAT DECIDES THE DESIGN. `『citrus +』小冊子` is a series of booklets, and
    # each booklet's title names the volume of `citrus +` it came with. Reading that number would
    # file booklet 1 as volume 5. The series title is not inside the product title, so nothing is
    # read, which is the right answer for the right reason.
    s.eq(vn.stated("『citrus +』5巻特装版小冊子電子版", "『citrus +』小冊子"), None,
         "a number belonging to ANOTHER work is not this product's volume number")
    s.eq(vn.stated("【最新刊】ドSさんはヤキモチちゃんが大好き", "百合シリーズ"), None,
         "a shop umbrella holding differently named books numbers nothing")

    # ── A POSITION IN A SEQUENCE, OR A LABEL ──────────────────────────────────────────────────
    #
    # THE LINE THIS MODULE DRAWS, ruled by the project owner 2026-08-12. `2017年1月号` is a LABEL:
    # a magazine's naming scheme is not stable across its own life, and コミック百合姫 has run
    # `Vol. 7 Winter 2007` quarterly, then bimonthly, then unnumbered, and only now monthly by
    # cover date, so a Vol. 7 and a 2017年1月号 are not two points on one line. Nothing is derived
    # from a label. `創刊号` is a POSITION, said in words.
    s.eq(vn.stated("コミック百合姫 2017年1月号[雑誌]", "コミック百合姫"), None,
         "an issue named by its cover date states no volume number")
    s.eq(vn.designation("コミック百合姫 2017年1月号[雑誌]", "コミック百合姫"), "2017年1月号",
         "and what it IS called comes back whole, with the shop's format tag off")
    s.eq(vn.stated("ガレット 創刊号", "ガレット"), "創刊号",
         "the inaugural issue answers with the shop's own word and not with the number it means")
    s.check(vn.stated("ガレット 創刊号", "ガレット") in "ガレット 創刊号",
            "WHICH IS IN THE PRODUCT TITLE, so `a volume number is the shop's own` stays pure "
            "arithmetic; `build.volume_number` is the one place a designation becomes an integer")
    s.eq(vn.stated("ガレット No.2", "ガレット"), "2",
         "and the rest of ガレット runs on ordinary numbers, which is why it is not a label case")

    # A LABEL FOR AN INSTALMENT THAT IS NOT AN ISSUE AT ALL. `メガネさんシリーズ` is a shop umbrella
    # over separately named books, so the product's own name is the whole of what it says.
    s.eq(vn.designation("お昼のメガネさん", "メガネさんシリーズ"), "お昼のメガネさん",
         "a product the series title does not name answers with its own name")
    s.eq(vn.designation("淡影の甘露", "淡影の甘露"), None,
         "and a product that IS the work says nothing the work's own title does not")
    s.eq(vn.designation("レミ咲短編集「you」", "レミ咲短編集「you」"), None,
         "including where the titles differ only in punctuation the fold ignores")

    # THE SHOP SAYS WHAT A PRODUCT IS AND WE DO NOT INFER IT.
    s.check(vn.is_periodical("コミック百合姫 2017年1月号[雑誌]"),
            "BOOK☆WALKER writes its own word for a magazine and that is what is read")
    s.check(not vn.is_periodical("ガレット No.2"),
            "ガレット is a magazine and carries no such tag, so it is not marked one: a rule "
            "inferring the format from a date-shaped name would miss it and mark others wrongly")

    s.eq(vn.stated("ガレット 2019年5月号", "ガレット"), None, "a monthly issue is not a volume")

    # A NAME THAT ENDS IN DIGITS IS A NAME, and here it is not even a question: the digits are
    # inside the series title, so nothing is left over to read.
    s.eq(vn.stated("あやめ14", "あやめ14"), None,
         "a work whose own name ends in a number states no volume number by having one")
    s.eq(vn.stated("ラブフェロモンNo.5", "ラブフェロモンNo.5"), None,
         "and the same where the name ends in something shaped exactly like a volume marker")

    # NO SERIES TO COMPARE AGAINST IS NO ANSWER, not a fallback to reading the end of the title.
    s.eq(vn.stated("何かの本 3巻", None), None, "with no series title there is no evidence")
    s.eq(vn.stated("何かの本 3巻", ""), None, "and an empty one is the same state")
    s.eq(vn.beyond_series("何かの本 3巻", "べつの本"), None,
         "a product whose title does not name the series answers nothing rather than guessing")

    # THE ONE THING IT MUST NEVER DO. A caller that cannot read a number must not reach for the
    # item's position, so the module offers no position and no default: None is the whole answer.
    s.eq(vn.stated("", ""), None, "an empty title states no number")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
