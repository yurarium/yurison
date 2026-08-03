#!/usr/bin/env python3
"""ganganonline/releases.py: publishing windows, and what an announced chapter is not.

COVERS = ['adapters/ganganonline/releases.py']
"""
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as gg


def main(s):
    today = dt.date(2026, 8, 3)

    D = {"chapters": [
        {"mainText": "第1話", "status": 1, "publishingPeriod": "2026/07/01 〜 2026/09/01 0:00"},
        {"mainText": "第2話", "status": 1, "publishingPeriod": "2026/07/08 〜"},
        {"mainText": "第3話", "status": 3, "publishingPeriod": "2026/08/10 〜"},
        {"mainText": "第4話", "status": 1},
        {"mainText": "第5話", "status": 2, "publishingPeriod": "2026/01/01 〜 2026/02/01 0:00"},
        {"status": 1, "publishingPeriod": "2026/07/01 〜"},
    ]}
    rows = {r["title"]: r for r in gg.chapters(D, today)}

    # status 3 is 次回更新: announced, not published. Publishing it would put a chapter in the feed
    # that nobody can read.
    s.check("第3話" not in rows, "an announced chapter is not a release")

    # A chapter with no window has no date, and a release row without a date is not a release.
    s.check("第4話" not in rows, "a chapter with no stated window is skipped")

    # A row with no title says nothing about anything.
    s.eq(len(rows), 3, "only the three real chapters survive")

    s.eq(rows["第1話"]["updated"], "2026-07-01", "the window start is the release date")
    s.eq(rows["第1話"]["access_modes"], ["free"], "a window still open is free")
    s.eq(rows["第2話"]["access_modes"], ["free"], "an open-ended window is free")
    s.eq(rows["第5話"]["access_modes"], ["purchase"], "status 2 is a purchase")

    # A window that has closed means it is no longer free, even at status 1.
    closed = gg.chapters({"chapters": [
        {"mainText": "第9話", "status": 1,
         "publishingPeriod": "2026/01/01 〜 2026/02/01 0:00"}]}, today)
    s.eq(closed[0]["access_modes"], ["purchase"], "a window that has ended is no longer free")

    start, end = gg.period("2026/07/01 〜 2026/09/01 0:00")
    s.eq(start, dt.date(2026, 7, 1), "the start is read")
    s.eq(end, dt.date(2026, 9, 1), "the end is read")
    s.check(gg.period("2026/07/01 〜")[1] is None, "an open-ended window has no end")
    s.eq(gg.period("nonsense"), (None, None), "unparsable text yields no window")

    s.check(gg.state("<html>no data</html>") is None, "a page without the block yields None")
    s.check(gg.state('<script id="__NEXT_DATA__">not json</script>') is None,
            "malformed JSON yields None rather than raising")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "ganganonline.releases"))
