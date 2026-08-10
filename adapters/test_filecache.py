#!/usr/bin/env python3
"""filecache: a per-file answer is reused only while the file and the rule are both unchanged.

COVERS = ['adapters/filecache.py']

A CACHE IS A CLAIM THAT NOTHING CHANGED, so every case here is a way that claim could be wrong.
The interesting one is the rule change: a cache that survives it turns a check into a check that
has silently stopped asking, which is worse than the seconds it saves.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import filecache
import testkit


def main(s):
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        a, b = root / "a.txt", root / "b.txt"
        a.write_text("one tic here\n")
        b.write_text("nothing\n")
        rule = root / "rule.py"
        rule.write_text("PATTERN = 'tic'\n")
        cache = root / "cache.json"

        seen = []

        def run(paths):
            seen.append(sorted(p.name for p in paths))
            return {p: p.read_text().count("tic") for p in paths}

        total, scanned = filecache.counted([a, b], [rule], run, cache)
        s.eq((total, scanned), (1, 2), "a cold run measures every file and totals them")

        total, scanned = filecache.counted([a, b], [rule], run, cache)
        s.eq((total, scanned), (1, 0), "a second run with nothing changed measures nothing")

        # A CHANGED FILE IS MEASURED AND ITS NEIGHBOUR IS NOT.
        a.write_text("tic tic\n")
        total, scanned = filecache.counted([a, b], [rule], run, cache)
        s.eq((total, scanned), (2, 1), "only the file whose content moved is measured again")
        s.eq(seen[-1], ["a.txt"], "and it is the one that moved")

        # RESTORED CONTENT IS THE OLD ANSWER, because the key is the bytes and not the clock.
        a.write_text("one tic here\n")
        total, scanned = filecache.counted([a, b], [rule], run, cache)
        s.eq((total, scanned), (1, 0), "a file restored to an earlier state needs no measuring")

        # THE CASE THAT MATTERS MOST. Change the rule and every remembered answer is about a
        # question nobody is asking any more.
        rule.write_text("PATTERN = 'tic'  # now counts differently\n")
        total, scanned = filecache.counted([a, b], [rule], run, cache)
        s.eq(scanned, 2, "a changed rule throws the whole cache away")

        # A FILE ADDED IS MEASURED; A FILE DROPPED STOPS COUNTING. The caller supplies the set, so
        # nothing is inferred from what the cache happens to hold.
        c = root / "c.txt"
        c.write_text("tic tic tic\n")
        total, scanned = filecache.counted([a, b, c], [rule], run, cache)
        s.eq((total, scanned), (4, 1), "a new file is measured and added to the total")
        total, scanned = filecache.counted([a, b], [rule], run, cache)
        s.eq((total, scanned), (1, 0), "a file no longer in the set stops counting")

        # A CORRUPT CACHE IS NOT A WRONG ANSWER.
        cache.write_text("{not json")
        total, scanned = filecache.counted([a, b], [rule], run, cache)
        s.eq((total, scanned), (1, 2), "an unreadable cache is measured again rather than trusted")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "filecache"))
