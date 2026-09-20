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

    cache_age(s)


def cache_age(s):
    """A cached page past its age is not the answer, which is the bug of 2026-09-21.

    THE HOST IS STUBBED RATHER THAN REACHED, so a hit and a miss are told apart by whether it was
    asked, which is the thing that actually distinguishes them. Reaching the network here would
    fail under the runner's block for a reason that has nothing to do with the rule.
    """
    import os, tempfile, time as _t
    d = pathlib.Path(tempfile.mkdtemp())
    f = d / "calendar.html"
    f.write_text("cached page")
    asked = []

    class _R:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return "live page".encode()

    def _stub(req, timeout=None):
        asked.append(getattr(req, "full_url", req))
        return _R()

    real_open, real_sleep = cal.urllib.request.urlopen, cal.time.sleep
    cal.urllib.request.urlopen, cal.time.sleep = _stub, lambda *_a: None
    try:
        s.eq(cal.fetch(d), "cached page", "a page cached today is read from the cache")
        s.eq(len(asked), 0, "and the host is not asked for it")
        old = _t.time() - 8 * 86400
        os.utime(f, (old, old))
        s.eq(cal.fetch(d), "live page", "one eight days old is read from the host instead")
        s.eq(len(asked), 1, "which is the request an unbounded cache never made")
    finally:
        cal.urllib.request.urlopen, cal.time.sleep = real_open, real_sleep


if __name__ == "__main__":
    sys.exit(testkit.run(main, "yurinavi.calendar"))
