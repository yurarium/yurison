#!/usr/bin/env python3
"""render/due.py: a rendered page is looked at on the days its next chapter is due."""
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import testkit  # noqa: E402
import due  # noqa: E402

COVERS = ["adapters/render/due.py"]

D = datetime.date.fromisoformat

# 作りたい女と食べたい女 on pixivコミック, Tuesdays. Its 3 November chapter was found on the 9th.
TUESDAYS = ["2026-09-29", "2026-10-13", "2026-10-20", "2026-10-27"]
# 私の推しは悪役令嬢。, the 8th of every month.
EIGHTHS = ["2026-07-08", "2026-08-08", "2026-09-08", "2026-10-08"]


def main(s):
    # ── the rhythms ───────────────────────────────────────────────────────────────────────────────
    s.eq(due.rhythm(TUESDAYS, D("2026-11-01")), ("weekday", 1, 7, 14),
         "dates on one weekday are a weekly rhythm, its step the shortest gap")
    s.eq(due.rhythm(["2026-09-01", "2026-09-29", "2026-10-27"], D("2026-11-01")), ("weekday", 1, 28, 28),
         "and a four-weekly one steps four weeks")
    s.eq(due.rhythm(EIGHTHS, D("2026-11-01")), ("monthday", 8, 30, 31),
         "dates on one day of the month are a monthly rhythm")
    s.eq(due.rhythm(["2026-10-01", "2026-10-11", "2026-10-22", "2026-11-01"], D("2026-11-02")),
         ("interval", 10, 10, 11), "and neither is a steady interval, its median gap")
    s.eq(due.rhythm(["2026-10-06", "2026-10-13"], D("2026-11-01")), None,
         "two dates are one gap, which is no rhythm")
    s.eq(due.rhythm(["2024-01-02", "2024-01-09", "2024-01-16"], D("2026-11-01")), None,
         "and a rhythm kept two years ago is not read")

    # ── due on the day, and for the grace days after it ──────────────────────────────────────────
    s.check(due.due(TUESDAYS, None, D("2026-11-03")).startswith("observed"),
            "a weekly work is due on its weekday")
    s.check(due.due(TUESDAYS, None, D("2026-11-05")),
            "and still due two days later, in case the chapter went up after the run")
    s.eq(due.due(TUESDAYS, None, D("2026-11-06")), None, "but not on the days between")
    s.check(due.due(TUESDAYS, None, D("2026-11-10")),
            "a week it missed is asked again on the next weekday")
    s.eq(due.due(TUESDAYS, None, D("2026-12-15")), None,
         "until three of its longest gaps have passed and the rhythm is given up")
    # 壊していいよ、すいかちゃん: weekly, then four-weekly. Its 18 September chapter came four weeks
    # after the last, past three weekly steps.
    suika = ["2026-07-10", "2026-07-17", "2026-07-24", "2026-08-21"]
    s.check(due.due(suika, None, D("2026-09-18")),
            "a rhythm that has slowed is still believed for three of its longest gaps")
    # 陰キャギャルでもイキがりたい！: the 8th in 2023, back on 8 September 2026.
    gal = ["2023-11-08", "2023-12-08", "2026-09-08"]
    s.check(due.due(gal, None, D("2026-10-08")),
            "a work back from a break keeps its day of the month")
    s.eq(due.rhythm(["2023-11-08", "2023-12-08", "2024-01-08"], D("2026-10-08")), None,
         "but not while it is still away")
    s.eq(due.rhythm(["2023-11-07", "2023-12-14", "2026-09-08"], D("2026-10-08")), None,
         "and not where the old dates kept no day")

    s.check(due.due(EIGHTHS, None, D("2026-11-08")), "a monthly work is due on its day")
    s.eq(due.due(EIGHTHS, None, D("2026-11-20")), None, "and not in the rest of the month")
    s.check(due.due(["2026-08-31", "2026-07-31", "2026-06-30", "2026-05-31"], None,
                    D("2026-09-30")),
            "the 31st falls on the last day of a shorter month")

    # ── the page's own word comes first ──────────────────────────────────────────────────────────
    s.check(due.due(TUESDAYS, {"next_update": "2026-11-07"}, D("2026-11-07")).startswith("announced"),
            "an announced date makes the page due on it, whatever the rhythm says")
    s.eq(due.due(["2026-11-07"], {"next_update": "2026-11-07"}, D("2026-11-08")), None,
         "but not once a chapter dated that day is held")
    third_friday = {"cadence": "毎月第3金曜"}
    s.check(due.due(["2026-09-18", "2026-10-16"], third_friday, D("2026-11-20")).startswith("stated"),
            "a stated cadence puts the page on its day, with two dates held")
    s.eq(due.due(["2026-09-18", "2026-10-16"], third_friday, D("2026-11-13")), None,
         "and not a week early")
    s.check(due.due(EIGHTHS, {"cadence": "毎月9日前後"}, D("2026-11-08")).startswith("observed"),
            "a cadence that pins no day leaves the decision to the dates we hold")

    # ── future dates, as マンガワン gives a chapter readable early ─────────────────────────────────
    s.eq(due.due(["2026-10-30", "2026-11-05", "2026-11-13"], None, D("2026-11-09")), None,
         "a chapter already dated ahead of today means the next one is not due yet")

    # ── the floor ────────────────────────────────────────────────────────────────────────────────
    s.eq(due.age_limit(TUESDAYS, None, D("2026-11-03"))[0], due.DUE_AGE,
         "a due page may be no older than today's run")
    s.eq(due.age_limit(TUESDAYS, None, D("2026-11-06"))[0], due.FLOOR_QUIET,
         "a page with a rhythm that is not due today waits for its floor")
    s.eq(due.age_limit(["2026-10-20", "2026-11-01"], None, D("2026-11-06"))[0], due.FLOOR_ACTIVE,
         "a recent work with no rhythm to read is looked at weekly")
    s.eq(due.age_limit(["2025-01-01"], None, D("2026-11-06"))[0], due.FLOOR_QUIET,
         "and a quiet one fortnightly")
    s.eq(due.age_limit([], None, D("2026-11-06"))[0], due.FLOOR_QUIET,
         "a page with no dates at all takes the quiet floor")

    # ── the dates are kept across runs, because a page shows a window ────────────────────────────
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d, "ledger", "dates.yaml")
        s.eq(due.load_history(p), {}, "no ledger yet is no dates")
        h = {}
        due.remember(h, "https://p/works/1", ["2026-10-13", "2026-10-20"])
        due.remember(h, "https://p/works/1", ["2026-10-27", "not a date"])
        due.remember(h, "", ["2026-10-27"])
        due.save_history(h, p)
        back = due.load_history(p)
    s.eq(back, {"https://p/works/1": {"2026-10-13", "2026-10-20", "2026-10-27"}},
         "a second read adds to the first, and nothing unreadable or unaddressed is kept")
    s.check(due.rhythm(back["https://p/works/1"], D("2026-11-01")),
            "and the dates read back are dates a rhythm can be read from")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "render.due"))
