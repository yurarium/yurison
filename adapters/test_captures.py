#!/usr/bin/env python3
"""captures.py: parse a big capture once, and notice when it changes."""
import json
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import captures  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/captures.py"]


def main(s):
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        cap, root = d / "cap.yaml", d / "cache"
        cap.write_text("works:\n  - title: A\n")

        captures._MEMO.clear()
        s.eq(captures.load(cap, root)["works"][0]["title"], "A", "a capture is parsed and returned")
        s.eq(len(list(root.glob("*.json"))), 1, "and a sidecar is written beside it")

        # THE SIDECAR IS WHAT IS READ NEXT TIME, which is the point. Proved by making it disagree
        # with the source: if the YAML were re-read, the answer would be A.
        side = next(root.glob("*.json"))
        side.write_text(json.dumps({"works": [{"title": "FROM CACHE"}]}))
        captures._MEMO.clear()
        s.eq(captures.load(cap, root)["works"][0]["title"], "FROM CACHE",
             "a second ask is answered from the sidecar rather than from YAML")

        # A CAPTURE THAT WAS REWRITTEN MUST NOT BE ANSWERED FROM THE OLD PARSE. The key carries the
        # size and the modification time, so a rewrite misses.
        time.sleep(0.01)
        cap.write_text("works:\n  - title: B\n  - title: C\n")
        captures._MEMO.clear()
        s.eq(len(captures.load(cap, root)["works"]), 2, "a rewritten capture is parsed again")

        # Same size, different content, different mtime: the mtime is why this is caught.
        time.sleep(0.01)
        cap.write_text("works:\n  - title: X\n  - title: Y\n")
        captures._MEMO.clear()
        s.eq(captures.load(cap, root)["works"][0]["title"], "X",
             "and so is one rewritten to the same length")

        # WITHIN ONE PROCESS the memo answers, which is the repeat this was written for: four
        # budgets and status.py asked for the same file in one deploy.
        captures._MEMO.clear()
        first = captures.load(cap, root)
        s.check(captures.load(cap, root) is first, "one parse per file per process")

        # A truncated sidecar is a miss, not an error. The source is still on disk.
        side = next(root.glob("*.json"))
        side.write_text("{ this is not json")
        captures._MEMO.clear()
        s.eq(captures.load(cap, root)["works"][0]["title"], "X",
             "a corrupt sidecar falls back to the capture rather than raising")

        s.eq(captures.load(d / "absent.yaml", root), {},
             "a capture that is not there is empty, which is what every caller does with one")

        # An unwritable cache costs speed and nothing else.
        captures._MEMO.clear()
        s.eq(captures.load(cap, d / "nowhere" / "deep" / "cache")["works"][0]["title"], "X",
             "and a cache directory that cannot be written still returns the right answer")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
