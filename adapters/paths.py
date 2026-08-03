#!/usr/bin/env python3
"""Where the out-of-repo caches and the site repository live.

WHY THIS EXISTS. Fetch caches are deliberately outside the repository: they are large, they are not
source, and REQUIREMENTS keeps them uncommitted. Their location used to be written out as an
absolute path under one user's home directory, in nineteen docstrings and eight defaults.

That was wrong twice over. It disclosed one machine's directory layout, and it was a functional
coupling: `check.py` and `deploy.sh` only worked if the site repository sat at exactly that path,
so any move would have broken the build for reasons that had nothing to do with the change.

Neither needs stating. The caches sit beside the repository and so does the site repo, so the
repository's parent is the root of both. Derive it and the machine drops out of the code.

Override with `YURI_CACHE` (caches) or `YURARIUM_SITE` (published site) if the layout differs.
"""
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE_ROOT = pathlib.Path(os.environ.get("YURI_CACHE") or ROOT.parent)
SITE_ROOT = pathlib.Path(os.environ.get("YURARIUM_SITE") or ROOT.parent / "yurarium.github.io")


def cache(name):
    """The cache directory for one adapter — cache("madb-cache")."""
    return CACHE_ROOT / name
