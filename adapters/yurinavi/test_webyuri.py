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

    cache_age(s)


def cache_age(s):
    """A cached page past its age is not the answer, which is the bug of 2026-09-21.

    THE HOST IS STUBBED RATHER THAN REACHED, so a hit and a miss are told apart by whether it was
    asked, which is the thing that actually distinguishes them. Reaching the network here would
    fail under the runner's block for a reason that has nothing to do with the rule.
    """
    import os, tempfile, time as _t
    d = pathlib.Path(tempfile.mkdtemp())
    f = d / "web_yuri.html"
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

    real_open, real_sleep = wy.urllib.request.urlopen, wy.time.sleep
    wy.urllib.request.urlopen, wy.time.sleep = _stub, lambda *_a: None
    try:
        s.eq(wy.fetch(d), "cached page", "a page cached today is read from the cache")
        s.eq(len(asked), 0, "and the host is not asked for it")
        old = _t.time() - 8 * 86400
        os.utime(f, (old, old))
        s.eq(wy.fetch(d), "live page", "one eight days old is read from the host instead")
        s.eq(len(asked), 1, "which is the request an unbounded cache never made")
    finally:
        wy.urllib.request.urlopen, wy.time.sleep = real_open, real_sleep


if __name__ == "__main__":
    sys.exit(testkit.run(main, "yurinavi.webyuri"))
