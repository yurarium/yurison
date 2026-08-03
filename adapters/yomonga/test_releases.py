#!/usr/bin/env python3
"""yomonga/releases.py: free windows, including the ones that have already closed.

COVERS = ['adapters/yomonga/releases.py']
"""
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as ym


def ep(name, y, m, d, ends=None):
    end = f'<span class="publish-end-date">{ends}</span>' if ends else ""
    return (f'<div class="episode-list"><span class="update-date">{y}/{m}/{d}</span>'
            f'<span class="episode-name">{name}</span>{end}</div>')


def main(s):
    today = dt.date(2026, 8, 3)

    s.eq(ym.episodes("", today), [], "an empty page yields no episodes")

    rows = {r["title"]: r for r in ym.episodes(
        ep("第1話", 2026, 7, 1) +
        ep("第2話", 2026, 7, 8, "2026/09/01") +
        ep("第3話", 2026, 6, 1, "2026/07/01"), today)}
    s.eq(len(rows), 3, "all three episodes are read")
    s.eq(rows["第1話"]["updated"], "2026-07-01", "single-digit months and days are padded")

    # No stated end means listed as readable, so free.
    s.eq(rows["第1話"]["access_modes"], ["free"], "no stated end means free")
    s.eq(rows["第2話"]["access_modes"], ["free"], "a window still open is free")
    s.eq(rows["第2話"]["free_until"], "2026-09-01", "and the end is carried for the reader")

    # THE ONE THAT MATTERS. A window that closed last month is not free now, and reporting it as
    # free sends a reader to a paywall, which is the single thing this field exists to prevent.
    s.eq(rows["第3話"]["access_modes"], ["purchase"], "a window that has passed is no longer free")
    s.eq(rows["第3話"]["free_until"], "2026-07-01", "the past end is still recorded as a fact")

    # An episode missing either half is skipped rather than half-recorded.
    s.eq(ym.episodes('<div class="episode-list"><span class="episode-name">x</span></div>', today),
         [], "an episode with no date is skipped")

    # The author block sits among promotional furniture, and a banner is not a person.
    s.eq(ym.author('<p>漫画：山田太郎</p>'), "山田太郎", "an author is read from the credit")
    s.check(ym.author('<p>漫画：バナー</p>') is None, "a banner is refused as an author")
    s.check(ym.author("<html>nothing</html>") is None, "a page with no author yields None")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "yomonga.releases"))
