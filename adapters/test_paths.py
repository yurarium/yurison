#!/usr/bin/env python3
"""paths.py: locations derived from the repository rather than written down."""
import importlib
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import paths


def main(s):
    # THE DEFAULT IS ONLY THE DEFAULT WHERE NOTHING IS SET, and the environment this runs in may
    # already carry an override: CI sets YURI_CACHE so `acceptance.py` reads the pages Stage 0
    # fetched, and this suite then asserted the derivation against a value somebody had chosen.
    # The variable is cleared for the two lines that are about the derivation, and restored, since
    # the rest of the suite is about the override working.
    _held = os.environ.pop("YURI_CACHE", None)
    fresh = importlib.reload(paths)
    try:
        # The whole point: no absolute path from one machine appears anywhere in the result.
        s.eq(fresh.CACHE_ROOT, fresh.ROOT.parent, "the cache root is the repository's parent")
        s.eq(fresh.cache("madb-cache"), fresh.ROOT.parent / "madb-cache",
             "a named cache sits beside")
        s.check("Development" not in str(fresh.ROOT.name),
                "the repo name is not a personal directory")
    finally:
        if _held is not None:
            os.environ["YURI_CACHE"] = _held
        importlib.reload(paths)

    # Overridable, because the derivation is a default and not a law.
    os.environ["YURI_CACHE"] = "/tmp/elsewhere"
    try:
        again = importlib.reload(paths)
        s.eq(str(again.CACHE_ROOT), "/tmp/elsewhere", "YURI_CACHE overrides the derivation")
    finally:
        del os.environ["YURI_CACHE"]
        importlib.reload(paths)

    os.environ["YURARIUM_SITE"] = "/tmp/site"
    try:
        again = importlib.reload(paths)
        s.eq(str(again.SITE_ROOT), "/tmp/site", "YURARIUM_SITE says where a site checkout is")
    finally:
        del os.environ["YURARIUM_SITE"]
        importlib.reload(paths)


if __name__ == "__main__":
    sys.exit(testkit.run(main, "paths"))
