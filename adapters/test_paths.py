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
    # The whole point: no absolute path from one machine appears anywhere in the result.
    s.eq(paths.CACHE_ROOT, paths.ROOT.parent, "the cache root is the repository's parent")
    s.eq(paths.cache("madb-cache"), paths.ROOT.parent / "madb-cache", "a named cache sits beside")
    s.check("Development" not in str(paths.ROOT.name), "the repo name is not a personal directory")

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
        s.eq(str(again.SITE_ROOT), "/tmp/site", "YURARIUM_SITE overrides the derivation")
    finally:
        del os.environ["YURARIUM_SITE"]
        importlib.reload(paths)


if __name__ == "__main__":
    sys.exit(testkit.run(main, "paths"))
