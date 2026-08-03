#!/usr/bin/env python3
"""shogakukan/releases.py: chapters, badges, and the announced-but-unpublished case.

COVERS = ['adapters/shogakukan/releases.py']
"""
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as sk


def row(title, y, m, d, badge=None):
    b = f'<img alt="{badge}">' if badge else ""
    return (f'<li class="bg-white"><img alt="{title} の話サムネイル">'
            f'<time>{y}/{m}/{d}</time>{b}</li>')


def main(s):
    today = dt.date(2026, 8, 3)

    rows = {r["title"]: r for r in sk.chapters(
        row("第1話", 2026, 7, 1) + row("第2話", 2026, 8, 3) + row("第3話", 2026, 9, 1), today)}

    # A future date is 次回更新予定: announced, not published. Publishing it would put a chapter in
    # the feed that nobody can open.
    s.check("第3話" not in rows, "a future-dated chapter is announced, not released")
    s.check("第2話" in rows, "a chapter dated today IS published")
    s.eq(rows["第1話"]["updated"], "2026-07-01", "the date is padded and normalised")

    # Three badges, and the middle one means readable now. Collapsing it into purchase is the
    # mistake made on two other platforms in this codebase.
    b = {r["title"]: r.get("access_modes") for r in sk.chapters(
        row("A", 2026, 1, 1, "無料") + row("B", 2026, 1, 2, "チケット")
        + row("C", 2026, 1, 3, "黄色いCマーク") + row("D", 2026, 1, 4), today)}
    s.eq(b["A"], ["free"], "無料 is free")
    s.eq(b["B"], ["free-timed"], "チケット is readable now, not a purchase")
    s.eq(b["C"], ["purchase"], "the coin mark is a purchase")
    s.check(b["D"] is None, "a chapter with no badge records no access rather than a guess")

    # A row missing either half is skipped rather than half-recorded.
    s.eq(sk.chapters('<li class="bg-white"><time>2026/1/1</time></li>', today), [],
         "a row with no title is skipped")
    s.eq(sk.chapters("", today), [], "an empty page yields nothing")

    # Authors: several credited, in order, without repeats.
    dom = ('<a href="/author/1">山田太郎</a><a href="/author/2">佐藤花子</a>'
           '<a href="/author/1">山田太郎</a>')
    s.eq(sk.authors(dom), "山田太郎 / 佐藤花子", "authors are joined once each, in order")
    s.check(sk.authors("<html>none</html>") is None, "no author link yields None")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "shogakukan.releases"))
