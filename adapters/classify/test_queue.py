#!/usr/bin/env python3
"""classify/queue.py: title normalisation and the content-tier vocabulary."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import queue as q


def main(s):
    # Normalisation decides whether two rows are the same work. Width, case and punctuation are
    # presentation; the identity underneath must survive all three.
    s.eq(q.norm("ＹＵＲＩ！"), q.norm("yuri!"), "width and case fold together")
    s.eq(q.norm("百合の 花"), q.norm("百合の花"), "internal space is not identity")
    s.eq(q.norm("「百合」"), q.norm("百合"), "japanese quotation marks are stripped")
    s.eq(q.norm("A-B"), q.norm("AB"), "a hyphen is not identity")
    s.ne(q.norm("百合"), q.norm("薔薇"), "different titles stay different")
    s.eq(q.norm(None), "", "None normalises to empty rather than raising")

    # Zero-width characters arrive from copy-paste and from some publishers' markup, and would
    # otherwise split one work into two silently.
    s.eq(q.norm("百​合"), q.norm("百合"), "a zero-width space is removed")

    # The tier vocabulary is the DEFINITIONS §3 list. close-relationship is the 広義 case, added
    # because a work centred on a close non-romantic relationship had nowhere to sit: it was
    # either miscoded as romance or denied its centrality.
    s.check("close-relationship" in q.TIERS, "the broad-sense tier exists")
    s.check("canonical-romance" in q.TIERS, "the explicit-romance tier exists")
    s.check("incidental" in q.TIERS, "the outside-the-boundary tier exists")
    s.eq(len(q.TIERS), len(set(q.TIERS)), "the tiers are distinct")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "classify.queue"))
