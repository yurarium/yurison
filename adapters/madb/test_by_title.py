#!/usr/bin/env python3
"""by_title.py: a title proposes a join and a person's name is what settles it."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from madb import by_title  # noqa: E402

COVERS = ["adapters/madb/by_title.py"]


def rec(name, creator, publisher, brand, date, isbn):
    return {"schema:name": name, "schema:creator": creator, "schema:publisher": publisher,
            "schema:brand": brand, "schema:datePublished": date, "schema:isbn": isbn}


# Quoted from metadata101.json of MADB release 1.2.18, trimmed to the fields read.
#
# 星川銀座四丁目 is the case that decides which date is taken. BOOK☆WALKER sells KADOKAWA's 2017
# MFC reissue and the bibliography holds 芳文社's 2010 original, and the work was first published
# in 2010.
HOSHIKAWA = [rec(["星川銀座四丁目", {"@value": "ホシカワ ギンザ ヨンチョウメ", "@language": "ja-hrkt"}],
                 "[著]玄鉄絢", "芳文社", "Manga time KR comics", "2010-08", "9784832279315"),
             rec(["星川銀座四丁目", {"@value": "ホシカワ ギンザ ヨンチョウメ", "@language": "ja-hrkt"}],
                 "[著]玄鉄絢", "KADOKAWA", "MFC", "2017-03", "9784040691176")]

# 一迅社's Memories by 菅野マナミ against the two books that share its folded title. This is the
# whole reason the person rule exists: neither of these is the work, and the earlier of them is
# from 1991.
MEMORIES = [rec("MEMORIES", "[著]大友克洋", "講談社", "", "", "4063196658"),
            rec(["Memories", {"@value": "メモリーズ", "@language": "ja-hrkt"}],
                "[著]つづき春", "大陸書房", "MENUETT COMICS", "1991-05-05", "4803333181")]

# A katakana PEN NAME, which is the shape `extract.people` cannot keep: it reads the reading and
# the name as one string and drops any all-katakana part as a reading.
ISE = [rec(["伊勢さんと志摩さん", {"@value": "イセサン ト シマサン", "@language": "ja-hrkt"}],
           ["トクヲツム", {"@value": "トクヲツム", "@language": "ja-hrkt"}],
           "芳文社", "芳文社コミックス", "2018-11", "9784832236455")]


def main(s):
    row = {"work_id": "bw-18872", "title": {"ja": "星川銀座四丁目"}, "creator": "玄鉄絢",
           "publisher": "KADOKAWA", "volumes": [{"delivered": "2017-03-01"}]}
    got = by_title.answer(row, HOSHIKAWA)
    s.eq(got[0], "2010-08", "the earliest agreeing volume, not the edition the shop sells")
    s.eq(got[1], "9784832279315", "with the ISBN of the volume that supplied the date")
    s.eq(got[2]["people_agreed"], 2, "and the evidence that convinced it")

    # THE COUNTER-CASE, AND THE REASON FOR THE RULE. Two books share this folded title and neither
    # is the work. Taking the earliest on a title match alone would date a 百合姫 volume to 1991.
    memo = {"work_id": "bw-x", "title": {"ja": "Memories"}, "creator": "菅野マナミ"}
    s.eq(by_title.answer(memo, MEMORIES), None, "a title match with no person agreeing is refused")
    s.eq(by_title.agreeing(memo, MEMORIES), [], "and nothing about it counts as agreement")

    # A ROW NAMING NOBODY AGREES WITH NOBODY. An anthology credited to アンソロジー has no person,
    # and treating that as a free pass would make the rule a title match.
    anon = {"work_id": "bw-y", "title": {"ja": "Memories"}, "creator": ""}
    s.eq(by_title.agreeing(anon, MEMORIES), [], "our side naming nobody agrees with nothing")
    s.eq(by_title.agreeing({"work_id": "z", "title": {"ja": "t"}, "creator": "大友克洋"},
                           [rec("MEMORIES", "", "講談社", "", "2000-01", "9784000000017")]), [],
         "and the bibliography naming nobody agrees with nothing either")

    # A KATAKANA PEN NAME IS A NAME. `extract.people` returns nothing for this record, so the join
    # was refused for トクヲツム, ヨドカワ and ポルリン alike until `credits` read the primary half.
    s.eq(by_title.credits(ISE[0]), {"トクヲツム"}, "the pen name survives, the reading is not read")
    ise = {"work_id": "bw-186882", "title": {"ja": "伊勢さんと志摩さん【単話版】"},
           "creator": "トクヲツム"}
    s.eq(by_title.answer(ise, ISE)[0], "2018-11", "so the row joins")

    # AN EDITION MARKER FOLDS AWAY AND A SEPARATE PUBLICATION DOES NOT. 【単話版】 names the
    # edition the shop sells, so the row above matched the tankōbon under its own title. 小冊子 is
    # a booklet given away with a volume, is not bracketed, and must not match the work.
    by = by_title.index(HOSHIKAWA)
    hits, _ = by_title.match([{"work_id": "a", "title": {"ja": "星川銀座四丁目【単行本版】"},
                               "creator": "玄鉄絢"}], by)
    s.eq(sorted(hits), ["a"], "a bracketed edition marker does not stop the join")
    hits, review = by_title.match([{"work_id": "b", "title": {"ja": "星川銀座四丁目　小冊子"},
                                    "creator": "玄鉄絢"}], by)
    s.eq(hits, {}, "and a giveaway booklet is a different publication, so it joins nothing")
    s.eq(review, [], "with nothing to review either, because no title matched")

    # A REFUSAL SAYS WHICH REFUSAL IT WAS. "Nobody agreed" wants a person found; "agreed but no
    # volume states a date and an ISBN" wants a different catalogue. Collapsing them into one null
    # loses the remedy (STANDING-INSTRUCTIONS §5).
    _, why = by_title.match([memo], by_title.index(MEMORIES))
    s.eq(why[0]["why"], "no person agreed", "the title matched and the people did not")
    undatable = [rec("作品名", "[著]甲", "出版社", "", "", "")]
    _, why = by_title.match([{"work_id": "c", "title": {"ja": "作品名"}, "creator": "甲"}],
                            by_title.index(undatable))
    s.eq(why[0]["why"], "agreed, and no agreeing volume states both a date and an ISBN",
         "the people agreed and the bibliography holds no dated edition")

    # WHETHER A ROW IS STILL UNDATED IS READ OFF ITS VOLUMES. `date_basis` says WHY a row has no
    # date and stays on the record after one is found, so a reader going by it would offer the
    # same row for ever.
    s.eq(by_title.undated({"date_basis": "no-print-date-stated",
                           "volumes": [{"delivered": "2021-01-01"}]}), True,
         "a volume with only a shop's delivery date is undated")
    s.eq(by_title.undated({"date_basis": "no-print-date-stated",
                           "volumes": [{"delivered": "2021-01-01", "published": "2020-12"}]}),
         False, "and one with a publication date is not, whatever the basis still says")
    s.eq(by_title.undated({"volumes": []}), True, "no volumes, no date")

    # THE ISBN IS STORED IN ONE FORM. MADB prints a third of its ISBNs in ten digits and every
    # question this repository asks is thirteen-digit.
    ten = [rec("作品名", "[著]甲", "出版社", "", "2006-04", "4840115222")]
    s.eq(by_title.dated_volumes(ten)[0][1], "9784840115223", "a ten-digit ISBN is stored as thirteen")
    s.eq(by_title.dated_volumes([rec("作品名", "[著]甲", "出版社", "", "2006-04", "")]), [],
         "and a record with no ISBN supplies no volume to date from")

    s.eq(by_title.match([], {}), ({}, []), "no rows, no answers and nothing to review")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
