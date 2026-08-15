#!/usr/bin/env python3
"""gigaviewer/releases.py: date normalisation and title classification, both pure."""
import json
import pathlib
import sys
import tempfile

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

    # ── STAGE A RUNS BEFORE THE COMPILE, AND THIS PASS MUST SURVIVE IT ────────────────────────
    #
    # THE RUN THIS COST. `known_titles` moved from reading `data/build/titles.json` to asking the
    # store, and `population` refuses to open a store that is not there. This pass runs in stage A,
    # where on a fresh runner nothing has compiled yet, so it exited 1, the platform went unread
    # for the day, and the run reported a failing adapter after publishing.
    #
    # WHAT IT COSTS IS SAID RATHER THAN ASSUMED. With no corpus every work has to be rediscovered
    # through the Tier C yardstick, which is the weaker evidence, and a pass that quietly compared
    # against nothing would look exactly like one comparing against everything.
    import io
    import contextlib
    import relational
    was, out = relational.DB, io.StringIO()
    try:
        relational.DB = pathlib.Path(tempfile.mkdtemp()) / "nothing.db"
        with contextlib.redirect_stdout(out):
            got = releases.known_titles([])
    finally:
        relational.DB = was
    s.eq(got, {}, "with no corpus to ask, nothing is established")
    s.check("Tier C yardstick alone" in out.getvalue(),
            "and the pass says what it is falling back to rather than going quiet")
    s.check("run ./build.py" in out.getvalue(), "naming what would do better")

    # A NAMED BUILD IS STILL READ, which is how somebody runs this against an older compile.
    # BOTH HALVES, because a build holds both and this asks for both: the web titles and the print
    # catalogue. A run comparing against one of them would report nothing about the other.
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "titles.json").write_text(json.dumps({"titles": ["やがて君になる"]}, ensure_ascii=False),
                                   encoding="utf-8")
    (d / "index.json").write_text(json.dumps([{"t": "citrus"}], ensure_ascii=False),
                                  encoding="utf-8")
    try:
        relational.DB = pathlib.Path(tempfile.mkdtemp()) / "nothing.db"
        with contextlib.redirect_stdout(io.StringIO()):
            got = releases.known_titles([], str(d))
    finally:
        relational.DB = was
    s.eq(sorted(got.values()), ["citrus", "やがて君になる"],
         "a build directory a caller named answers where the store cannot")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "gigaviewer.releases"))
