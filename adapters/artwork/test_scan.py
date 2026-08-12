#!/usr/bin/env python3
"""artwork/scan.py: what survives a cancelled reading of 1,339 covers.

COVERS = ['adapters/artwork/scan.py']

THE PROPERTY UNDER TEST IS RESUMPTION, and nothing else here matters as much. A person reading the
artwork gets through a few dozen at a sitting, and the value of the record is entirely that the next
sitting starts where the last one stopped.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import scan                                                            # noqa: E402
import testkit                                                         # noqa: E402


def _round_trip(s):
    with tempfile.TemporaryDirectory() as d:
        scan.STATE = pathlib.Path(d) / "examined.json"
        rows = scan.load()
        s.eq(rows, {}, "a state file that does not exist yet reads as nothing examined")

        scan.mark(rows, "a.jpg", "作品A", "title", "Throwing Step!")
        # AN EMPTY ANSWER IS A RECORD. A cover carrying no Latin and no ruby has been RULED ON, and
        # without writing that down the next pass opens it again to learn the same nothing. This is
        # the whole reason the file holds more than a list of finds.
        scan.mark(rows, "b.jpg", "作品B", "none")
        scan.save(rows)

        again = scan.load()
        s.eq(sorted(again), ["a.jpg", "b.jpg"], "both survive a save and a reload")
        s.eq(again["a.jpg"]["found"], "title", "what was seen is kept")
        s.eq(again["a.jpg"]["detail"], "Throwing Step!", "and what it said")
        s.eq(again["b.jpg"]["found"], "none", "a cover with nothing on it stays ruled on")
        s.check(again["a.jpg"]["at"], "each row carries when it was read")

        # THE QUEUE IS WHAT IS LEFT, which is the resumption itself.
        queue = ["a.jpg", "b.jpg", "c.jpg", "d.jpg"]
        s.eq([f for f in queue if f not in again], ["c.jpg", "d.jpg"],
             "a second sitting is handed only the covers nobody has opened")


def _survives_a_kill(s):
    with tempfile.TemporaryDirectory() as d:
        scan.STATE = pathlib.Path(d) / "examined.json"
        scan.STATE.write_text("{ half written when the process died")
        rows = scan.load()
        s.eq(rows, {}, "a truncated state file reads as empty rather than raising")
        scan.mark(rows, "a.jpg", "作品A", "title")
        scan.save(rows)
        s.eq(len(scan.load()), 1, "and the next save repairs it")
        s.check(not scan.STATE.with_suffix(".tmp").exists(),
                "the write is atomic, so a kill mid-save leaves the old file and no debris")


def _reread_replaces(s):
    """Looking again at a cover replaces what was said about it rather than adding a second row."""
    with tempfile.TemporaryDirectory() as d:
        scan.STATE = pathlib.Path(d) / "examined.json"
        rows = {}
        scan.mark(rows, "a.jpg", "作品A", "none")
        scan.mark(rows, "a.jpg", "作品A", "title", "found on a second look")
        scan.save(rows)
        got = scan.load()
        s.eq(len(got), 1, "one row for one image")
        s.eq(got["a.jpg"]["found"], "title", "and the later reading is the one kept")


def main(s):
    real = scan.STATE
    try:
        _round_trip(s)
        _survives_a_kill(s)
        _reread_replaces(s)
    finally:
        scan.STATE = real


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
