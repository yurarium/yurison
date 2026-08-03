#!/usr/bin/env python3
"""render/schedule_text.py: what a platform states about its own rhythm, and what it does not."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import testkit  # noqa: E402
import schedule_text as st  # noqa: E402

COVERS = ["adapters/render/schedule_text.py"]

# The two pages this was written from, verbatim.
WATATEN = "私に天使が舞い降りた！ 椋木ななつ 次回無料更新は8/5(水曜)予定です。 無料話更新：毎月第1水曜"
HERAMI = "平良深姉妹はどっちもヤんでる 金子ある 次回無料更新は8/21(金曜)予定です。 無料話更新：毎月第3金曜"


def main(s):
    s.eq(st.cadence(HERAMI), "毎月第3金曜", "the stated rhythm is kept in the platform's own words")
    s.eq(st.cadence(WATATEN), "毎月第1水曜", "and read the same way with a different day")
    s.eq(st.cadence("no schedule here"), None, "a page that states none says none")

    # The year is not printed, so it is resolved against the day the page was read.
    s.eq(st.next_update(HERAMI, "2026-08-01"), "2026-08-21", "a date later this year")
    s.eq(st.next_update("次回無料更新は1/5(月曜)予定です。", "2026-12-20"), "2027-01-05",
         "a date that has to roll into next year, because next is not behind us")
    s.eq(st.next_update("次回無料更新は8/5(水曜)予定です。", "2026-08-05"), "2026-08-05",
         "today counts as not in the past")
    s.eq(st.next_update("nothing", "2026-08-01"), None, "no announcement, no date")
    s.eq(st.next_update("次回無料更新は2/30(月曜)予定です。", "2026-08-01"), None,
         "a date that does not exist is not invented")

    # THE CLAIMS THIS WAS BUILT FOR. 17 July 2026 is a third Friday, which is why the report of an
    # update that day was consistent with the platform all along.
    s.check(st.fits("毎月第3金曜", "2026-07-17"), "the claimed date fits the stated cadence")
    s.check(st.fits("毎月第3金曜", "2026-08-21"), "as does the date the platform announces")
    s.check(not st.fits("毎月第3金曜", "2026-07-10"), "a second Friday does not")
    s.check(not st.fits("毎月第1水曜", "2026-07-11"), "nor a Saturday against a Wednesday cadence")
    s.check(st.fits("毎週木曜", "2026-08-06"), "a weekly cadence answers on its own day")
    s.check(not st.fits("毎週木曜", "2026-08-07"), "and not on another")

    # A cadence that does not pin a date must not be turned into one.
    s.eq(st.fits("隔週金曜", "2026-07-17"), None,
         "a fortnightly cadence names no particular Friday, so it decides nothing")
    s.eq(st.fits("毎月", "2026-07-17"), None, "nor does a month with no day in it")
    s.eq(st.fits(None, "2026-07-17"), None, "no cadence decides nothing")
    s.eq(st.fits("毎月第3金曜", None), None, "and neither does no date")
    s.eq(st.fits("毎月第3金曜", "not-a-date"), None, "or an unparseable one")

    # THE OTHER PLATFORMS. A survey of every page already in the fetch caches found the same fact
    # worded differently by each: マガポケ and ガンガンONLINE give a month and a day, カドコミ gives
    # a whole date, and カドコミ also says 未定 where it does not know.
    s.eq(st.next_update("次回更新：8月6日", "2026-08-03"), "2026-08-06",
         "ガンガンONLINE's month and day")
    s.eq(st.next_update("次回更新：1月6日", "2026-12-20"), "2027-01-06",
         "and it rolls into the next year the same way")
    s.eq(st.next_update("次回更新予定日：2026/09/14", "2026-08-03"), "2026-09-14",
         "カドコミ prints the year, so nothing is inferred")
    s.eq(st.next_update("次回更新予定日：2025/09/14", "2026-08-03"), "2025-09-14",
         "and a printed year is taken as printed even when it is behind us, "
         "because there is nothing to resolve")
    s.eq(st.next_update("次回更新予定日：2026/02/30", "2026-08-03"), None,
         "a printed date that does not exist is not invented")

    s.check(st.undecided("次回更新予定日：未定"), "未定 is a statement that the date is unsettled")
    s.check(not st.undecided("次回更新予定日：2026/09/14"), "a date is not 未定")
    s.check(not st.undecided("nothing here"), "and silence is not 未定 either")
    s.eq(st.read("次回更新予定日：未定", "2026-08-03"), {"next_update_undecided": True},
         "which is recorded, because it differs from a page that says nothing")
    s.eq(st.read("次回更新予定日：2026/09/14", "2026-08-03"), {"next_update": "2026-09-14"},
         "and is not recorded alongside a date it contradicts")

    s.eq(st.read(HERAMI, "2026-08-01"),
         {"cadence": "毎月第3金曜", "next_update": "2026-08-21"}, "both facts off one page")
    s.eq(st.read("nothing at all", "2026-08-01"), None, "and nothing where there is nothing")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
