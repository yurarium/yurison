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

A `--cache` FLAG DEFAULTS, ALWAYS, AND `paths.cache()` IS THE DEFAULT. The tree had it both ways
and the split was arbitrary, so here is the rule and the argument for it.

`names/ndl_books.py` took `--cache` with no default, and a two hour sweep of 124 publisher labels
left nothing on disk because nobody passed one. That is §7: a run that needs somebody to remember
something is not finished. The case for requiring the flag is that these caches are large and sit
outside the repository, so an operator should say where the megabytes go. `cache()` answers that
without the flag: the location is derived from the repository's parent, it names no machine, one
environment variable moves all of them together, and `.githooks/leak-guard.sh` rejects a
build-machine path written into the source, so a hand-typed default could not be right anyway.

So the flag is for a caller who means to point somewhere else, and forgetting it costs nothing.
Two callers sharing one question share one default and cannot drift: `names/openbd_reading.py` and
`openbd/enrich.py` asked openBD the same thing into two directories for exactly as long as the
location was something a person typed.
"""
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE_ROOT = pathlib.Path(os.environ.get("YURI_CACHE") or ROOT.parent)
SITE_ROOT = pathlib.Path(os.environ.get("YURARIUM_SITE") or ROOT.parent / "yurarium.github.io")


def cache(name):
    """The cache directory for one adapter — cache("madb-cache")."""
    return CACHE_ROOT / name
