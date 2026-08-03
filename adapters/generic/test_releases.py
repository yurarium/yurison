#!/usr/bin/env python3
"""generic/releases.py: chapter labels dug out of scraped text runs.

COVERS = ['adapters/generic/releases.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as gr


def main(s):
    # Leading and trailing space goes; internal runs are left, because a chapter label's own
    # spacing is content and the caller collapses it where it needs to.
    s.eq(gr.clean("  a  b  "), "a  b", "surrounding whitespace is stripped, internal is kept")
    s.eq(gr.clean("ＹＵＲＩ"), "YURI", "width is normalised")
    s.eq(gr.clean(None), "", "None cleans to empty rather than raising")
    # The invisible characters that broke comparisons elsewhere in this codebase.
    s.eq(gr.clean("百​合"), "百合", "a zero-width space is removed")

    # A row with no date is not a release, whatever else it carries. §6: a guessed date is worse
    # than none, because it reorders the feed and nothing downstream can tell it was invented.
    rows = gr.episodes("", "markup")
    s.eq(rows, [], "an empty page yields nothing")

    # CHAPTERISH is what decides whether a scraped string is a chapter label at all. It has to
    # accept the numbering styles publishers actually use, or a platform comes back with a
    # fraction of its chapters.
    s.check(gr.CHAPTERISH.search("第1話"), "第N話 is a chapter label")
    s.check(gr.CHAPTERISH.search("第12話"), "so is a multi-digit one")
    s.check(gr.CHAPTERISH.search("１２話"), "and a full-width one")
    s.check(not gr.CHAPTERISH.search("お知らせ"), "an announcement is not a chapter label")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "generic.releases"))
