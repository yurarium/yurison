#!/usr/bin/env python3
"""yurinavi/calendar.py: release-calendar rows, quarantined rather than guessed apart.

COVERS = ['adapters/yurinavi/calendar.py']

Title and author run together in one cell, and splitting them reliably needs the publisher's own
record. REQUIREMENTS §6 says quarantine rather than guess, so the cell is kept whole.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import calendar as cal


def main(s):
    s.eq(cal.text("<p>a  <b>b</b>\n c</p>"), "a b c", "markup is stripped and space collapsed")
    s.eq(cal.text("<br>"), "", "markup alone yields empty")

    html = """
    <table>
      <tr><td>▼8月発売</td></tr>
      <tr><td>8/3 月</td><td></td><td>百合の花 (3) 山田太郎</td><td>一迅社</td></tr>
      <tr><td>8/10 月</td><td></td><td>薔薇の棘 (1) 佐藤花子</td><td>講談社</td></tr>
    </table>"""
    rows = cal.parse(html)
    s.check(len(rows) >= 2, "both dated rows are read")
    if len(rows) >= 2:
        r = rows[0]
        s.check(any("百合の花" in str(v) for v in r.values()),
                "the title cell survives into the row")
        s.check(any("一迅社" in str(v) for v in r.values()), "the publisher is captured")
        # The volume number is in brackets before the author, and is the one part that CAN be
        # separated safely, because a bracketed integer is unambiguous.
        s.check(any(str(v) == "3" or v == 3 for v in r.values()),
                "the volume number is extracted from the brackets")

    # A row with no date under no header cannot be placed in time, so it is dropped rather than
    # given a guessed date.
    s.eq(cal.parse("<table><tr><td>百合の花 (1) 作者</td><td>出版社</td></tr></table>"), [],
         "a row with no month or day is dropped rather than dated by guess")

    s.eq(cal.parse(""), [], "an empty page yields no rows")
    s.eq(cal.parse("<table></table>"), [], "an empty table yields no rows")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "yurinavi.calendar"))
