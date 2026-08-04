#!/usr/bin/env python3
"""bookwalker.py: reading a shop's completion marker, and only about the right work."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bookwalker as bw  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/bookwalker.py"]

TAIL = " - マンガ（漫画）│電子書籍無料試し読み・まとめ買いならBOOK☆WALKER"

# Both quoted from the served pages, which is the whole evidence for the rule.
DONE = f"<title>【完結】コンカフェ嬢は恋を着る（ＦＵＺコミックス）{TAIL}</title>"
RUNNING = f"<title>きみが死ぬまで恋をしたい（百合姫コミックス）{TAIL}</title>"


def main(s):
    s.eq(bw.status(DONE, "コンカフェ嬢は恋を着る"), "completed",
         "the shop marks a finished series in front of its name")

    # THE COUNTER-CASE, checked before believing the rule. きみが死ぬまで恋をしたい updates every
    # month and its page carries no 完結 at all, so the marker distinguishes rather than decorates.
    s.eq(bw.status(RUNNING, "きみが死ぬまで恋をしたい"), None,
         "and a running series carries no marker, which is not evidence either way")

    # A MARKER READ OFF SOMEBODY ELSE'S PAGE IS WORSE THAN NO ANSWER. A title search routinely
    # returns a different series, so the page has to name the work that was asked about.
    s.eq(bw.status(DONE, "まったく別の作品"), None,
         "a completed page for another work says nothing about this one")
    s.eq(bw.status(DONE, "コンカフェ"), "completed",
         "while a work whose name the page contains is the work the page is about")

    # Width and spacing differ between our catalogue and the shop, and must not decide it.
    s.eq(bw.status("<title>【完結】ＡＢＣの日々" + TAIL + "</title>", "ABCの日々"), "completed",
         "full-width and half-width name the same series")

    s.eq(bw.status("", "any"), None, "no page, no answer")
    s.eq(bw.status("<html>no title here</html>", "any"), None, "and no title, no answer")

    s.eq(bw.series_ids('a href="https://bookwalker.jp/series/490418/" '
                       'b href="https://bookwalker.jp/series/490418/" '
                       'c href="https://bookwalker.jp/series/190256/"'),
         ["490418", "190256"], "each series once, in the order the search lists them")
    s.eq(bw.series_ids("nothing"), [], "and none where the search found none")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
