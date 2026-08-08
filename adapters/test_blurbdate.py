#!/usr/bin/env python3
"""blurbdate.py: a shop stating a printing dates the book, and a number in a plot summary does not.

EVERY LITERAL HERE IS A MATCHED CONSTRUCTION AND NOT A DESCRIPTION. A shop's あらすじ is copyrighted
(REQUIREMENTS §2), so the story around each of these is deliberately absent and nothing here is long
enough to be one. The previous round cut two fixtures out of the cmoa cache and deleted them before
committing, for the same reason.
"""
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit  # noqa: E402
import blurbdate as B  # noqa: E402
import delivery as D  # noqa: E402

COVERS = ["adapters/blurbdate.py"]

# Fixed so a year bound cannot start refusing a test in January. The corpus holds a 2026-02
# printing already, which is the case the bound has to admit.
TODAY = datetime.date(2026, 8, 8)


def main(s):
    # ── THE FORMS THE SHOP WRITES, EACH ONE OFF A PAGE IN THE CACHE ──
    s.eq(B.stated("（２０２２年５月発行の創作百合同人誌です）", today=TODAY),
         ("2022-05", B.EV_ISSUE), "the form the brief names, in full-width digits")
    s.eq(B.stated("（初出:2020年2月コミティア）本作は同人誌です", today=TODAY),
         ("2020-02", B.EV_FIRST_APPEARANCE), "初出 is where it appeared and says so")
    s.eq(B.stated("2016年発行の同人誌です", today=TODAY), ("2016", B.EV_ISSUE),
         "a year with no month is a year, and is not padded to January")
    s.eq(B.stated("2018年に発行した同人誌です。", today=TODAY), ("2018", B.EV_ISSUE),
         "and the same claim with a particle in the way")
    s.eq(B.stated("本作は同人誌です 2023.12.3 COMITIA146 発行/32p", today=TODAY),
         ("2023-12-03", B.EV_ISSUE), "a dotted date with the event between it and 発行")
    s.eq(B.stated("本作は同人誌です 2024/5/26 COMITIA148 発行/32p", today=TODAY),
         ("2024-05-26", B.EV_ISSUE), "and a slashed one")
    s.eq(B.stated("2026年2月22日《COMITIA155》にて発刊した同人誌です", today=TODAY),
         ("2026-02-22", B.EV_ISSUE), "発刊 is the same claim as 発行")
    s.eq(B.stated("2023年のコミティアに出した本です。本作は同人誌です", today=TODAY),
         ("2023", B.EV_ISSUE), "出した is how one seller says it")
    s.eq(B.stated("2024年1月の関西コミティアで頒布した同人誌です", today=TODAY),
         ("2024-01", B.EV_ISSUE), "頒布 at an event is the book being issued")
    # `※初出：COMITIA150（2024年11月発行同人誌）` states both claims in one sentence. The number
    # belongs to the word beside it, so 発行 is reported and 初出 is not.
    s.eq(B.stated("※初出：COMITIA150（2024年11月発行同人誌）", today=TODAY),
         ("2024-11", B.EV_ISSUE), "the claim word beside the date wins over one further off")

    # ── THE EARLIEST OF SEVERAL, WHICH IS THE COMMON CASE AND NOT AN EDGE ──
    s.eq(B.stated("本作は同人誌です 2019年6月発行のペーパー漫画も収録 （2018年11月発行）",
                  today=TODAY),
         ("2018-11", B.EV_ISSUE), "a book reprinting a convention paper is older than the paper")
    s.eq(B.stated("（２０２３年９月発行＆１２月発行の創作百合同人誌合本版です）", today=TODAY),
         ("2023-09", B.EV_ISSUE), "a 合本版 is dated from the first of the books bound into it")
    s.eq(len(B.dates("（２０２３年９月発行＆１２月発行の創作百合同人誌合本版です）", today=TODAY)),
         1, "and the second date carries no year of its own, so only one is read")

    # ── THE COUNTER-CASES, WRITTEN BEFORE THE PATTERNS ──
    # The three the previous round pinned are inherited from `delivery.edition_statement` instead
    # of being restated here, so a date cannot be read off a page that never said what edition it
    # was. Each of these would be claimed by a rule that only looked for a year and 発行.
    s.eq(B.stated("同人誌風マンガとして2023年5月発行", today=TODAY), (None, None),
         "同人誌風 is a commercial book in the style of one, and its date is not a doujinshi's")
    s.eq(B.stated("コミティアの人気作家が2021年に発表した連載", today=TODAY), (None, None),
         "コミティアの人気作家 describes the author, so the year is about her and not this book")
    s.eq(B.stated("参加した同人誌即売会で、2019年に発行された本を手に取り", today=TODAY),
         (None, None), "a scene in the story can hold a printing and still be a scene")
    # These reach the date rule and are refused by it.
    s.eq(B.stated("本作は同人誌です 1000年後の地球で目覚めた女の子", today=TODAY), (None, None),
         "a year in the plot is out of the range a printing can fall in")
    s.eq(B.stated("本作は同人誌です 2025年5月現在は読み切りの状態です", today=TODAY), (None, None),
         "現在 says what is true today and leans on no publishing word")
    s.eq(B.stated("本作は同人誌です 2011年～2014年にかけて個人誌で発表した作品を再録", today=TODAY),
         (None, None), "a range names the years an author worked and dates no edition")
    s.eq(B.stated("本作は同人誌です 2023～2025年までに発行した同人誌の再録集です", today=TODAY),
         (None, None), "and so does a range written the other way up")
    s.eq(B.stated("本作は同人誌です 創作百合同人誌15冊発刊記念", today=TODAY), (None, None),
         "15冊 is a count of books standing next to a publishing word")
    s.eq(B.stated("本作は同人誌です ※全51ページ、彩未が結婚でこの地を離れて12年", today=TODAY),
         (None, None), "a page count and a duration are not four digits and never were")
    s.eq(B.stated("本作は同人誌です 著者個人誌『夢落 2021年3月号』に描き下し原稿を追加", today=TODAY),
         (None, None), "an issue label inside a title states no printing of this file")
    s.eq(B.stated("", today=TODAY), (None, None), "no description at all yields no date")
    s.eq(B.stated(None, today=TODAY), (None, None), "and neither does no argument")

    # A YEAR BOUND THAT MOVES WITH THE CALENDAR. A shop lists a book before its event, so next
    # year is admitted and the year after is somebody's typing error.
    s.eq(B.stated("2027年2月発行の同人誌です", today=TODAY), ("2027-02", B.EV_ISSUE),
         "a printing announced for next year is a date the shop stated")
    s.eq(B.stated("2031年2月発行の同人誌です", today=TODAY), (None, None),
         "and one five years out is not")

    # 発売 IS NOT ON THE LIST, and this is the case that keeps it off: a shop announcing another
    # book's release date in the same box would otherwise date this file from it.
    s.eq(B.stated("本作は同人誌です 続編は2026年3月発売予定", today=TODAY), (None, None),
         "発売 announces a different book and states nothing about this one")

    # ── THE SALES EVENT, RECORDED AND NEVER TURNED INTO A DATE ──
    s.eq(B.sold_at("（コミックマーケット102発行・同人誌）"), (B.COMIKET, 102),
         "the event the brief names, recorded as an event")
    s.eq(B.sold_at("C95で頒布した同人誌の電子版です"), (B.COMIKET, 95),
         "and the abbreviation the same seller uses elsewhere")
    s.eq(B.sold_at("COMITIA148で頒布の本の電子版です"), (B.COMITIA, 148), "COMITIA in Latin")
    s.eq(B.sold_at("コミティア152で頒布したピュア百合漫画です"), (B.COMITIA, 152), "and in kana")
    # 関西コミティア RUNS ITS OWN NUMBERS. 関西コミティア68 and COMITIA68 are years apart, so a
    # table keyed on the number alone would have dated this row from the wrong series.
    s.eq(B.sold_at("関西コミティア68で販売した、オリジナル百合漫画です"), (B.COMITIA_KANSAI, 68),
         "the regional series is told apart from the one whose name it contains")
    s.eq(B.sold_at("2024年1月の関西コミティアで頒布した"), (B.COMITIA_KANSAI, None),
         "an event named without a number is still the event")
    s.eq(B.sold_at("2022年コミティアにて発行しました本と同じ内容"), (B.COMITIA, None),
         "and that row is dated from its year, which the shop did state")
    s.eq(B.sold_at("百合マンガです"), None, "a description naming no event answers none")
    s.eq(B.sold_at(None), None, "and so does no description")
    s.check(B.stated("（コミックマーケット102発行・同人誌）", today=TODAY) == (None, None),
            "an event number is not read as a date, which is this module's one refusal by choice")

    # ── WHAT A PROMOTED ROW HAS TO CARRY ──
    s.eq(B.precision("2024-05-26"), "day", "the precision is read off the value")
    s.eq(B.precision("2024-05"), "month", "so nothing stores it twice and lets the two disagree")
    s.eq(B.precision("2024"), "year", "a year is a year and is not a January")
    s.eq(B.precision(None), None, "and no date has no precision")
    s.check(B.BASIS in B.BASIS_NOTE, "the basis carries the sentence explaining it")
    s.check(all(k in B.EVENT_NOTE for k in (B.EV_ISSUE, B.EV_FIRST_APPEARANCE)),
            "and so does each of the two claims a date can be made under")
    s.check(B.BASIS != D.BASIS, "a printing and a delivery are not one basis under two names")

    # ── A PRINTING REFUSES A DELIVERY DATE, WHEREVER THE PRINTING WAS STATED ──
    # `delivery.promote` owns this refusal so it has one home. It is told about the blurb's date
    # instead of being made to find it, since the blurb is not on the volume rows it reads.
    s.eq(D.promote([{"delivered": "2023-05-01"}], stated_print="2022-05"),
         (None, D.REFUSED_BLURB), "a date the shop stated in its own description refuses it")
    s.eq(D.promote([{"delivered": "2023-05-01"}]), ("2023-05-01", None),
         "and the same volumes with nothing stated still promote")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
