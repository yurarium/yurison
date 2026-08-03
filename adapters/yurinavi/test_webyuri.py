#!/usr/bin/env python3
"""yurinavi/webyuri.py: the web-update table, kept raw where it cannot be split safely.

COVERS = ['adapters/yurinavi/webyuri.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import webyuri as wy


def main(s):
    html = """
    <table>
      <tr><td>▼8月更新</td></tr>
      <tr><td>3 月</td><td>百合の花 山田太郎（コミックDAYS）</td></tr>
      <tr><td>10 月</td><td>薔薇の棘 佐藤花子（一迅プラス）</td></tr>
      <tr><td>17 月</td><td>レイアウト用セル</td></tr>
    </table>"""
    rows = wy.parse(html)
    s.eq(len(rows), 2, "only cells ending in a bracketed platform are works")

    r = rows[0]
    s.eq(r["platform"], "コミックDAYS", "the platform is taken from the brackets")
    s.eq(r["month"], 8, "the month comes from the header above")
    s.eq(r["day"], 3, "the day comes from the row's first cell")
    # Title and author share a cell and cannot be split without the publisher's record, so the
    # head is kept raw. §6: quarantine rather than guess.
    s.eq(r["raw"], "百合の花 山田太郎", "title and author stay together, unsplit")

    s.eq(rows[1]["month"], 8, "the header applies to every row under it, not just the first")
    s.eq(rows[1]["day"], 10, "and each row carries its own day")

    s.eq(wy.parse(""), [], "an empty page yields nothing")
    # The first cell is the day column, so a work cell only ever appears from the second onward.
    orphan = wy.parse("<table><tr><td>3 月</td><td>百合の花（コミックDAYS）</td></tr></table>")
    s.eq(orphan[0]["month"], None, "a row with no header above has no month, rather than a guess")
    s.eq(orphan[0]["day"], 3, "though its own day is still read")
    s.eq(wy.parse("<table><tr><td>百合の花（コミックDAYS）</td></tr></table>"), [],
         "a single-cell row has no work cell, since the first column is the day")

    # The same invisible-character problem as the antenna, since this is the same source family.
    s.eq(wy.norm("竹コミ‎‏"), wy.norm("竹コミ"), "bidi marks are stripped")
    s.eq(wy.norm("ＹＵＲＩ"), wy.norm("yuri"), "width and case fold")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "yurinavi.webyuri"))
