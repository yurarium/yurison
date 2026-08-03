#!/usr/bin/env python3
"""gigaviewer/releases.py: date normalisation and title classification, both pure."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases


def main(s):
    # JST is the project's clock. A feed stamp in UTC must land on the Japanese calendar day, or
    # a midnight-JST release is filed a day early for ever after.
    s.eq(releases.jst_date("2026-08-03T15:00:00Z"), "2026-08-04",
         "15:00 UTC is already tomorrow in Tokyo")
    s.eq(releases.jst_date("2026-08-03T00:00:00+09:00"), "2026-08-03",
         "a stamp already in JST is kept")
    s.eq(releases.jst_date("2026-08-03T14:59:59Z"), "2026-08-03",
         "one second before the boundary stays on the day")

    # Title normalisation feeds cross-platform identity, so width and case must fold together or
    # the same work appears twice.
    a = releases.norm_title("ＹＵＲＩ　ガール")
    b = releases.norm_title("YURI ガール")
    s.eq(a, b, "full-width and half-width normalise to one form")
    s.ne(releases.norm_title("あるある"), releases.norm_title("ないない"),
         "different titles stay different")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "gigaviewer.releases"))
