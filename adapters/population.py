#!/usr/bin/env python3
"""The populations a capture pass works from, asked of the store. STORE-PLAN §13.

WHY THIS IS A MODULE AND NOT A LINE IN EACH PASS. Eleven adapters read `data/build/series.json` and
filtered it in Python, and the first four converted were about to hold four copies of the same six
lines: open the store, ask the registry, fall back to a file if one was named. That is the shape
STANDING-INSTRUCTIONS §3 refuses, and the copies drift in the way `shopquery` and `editions/capture`
already demonstrated, each docstring claiming to be the one producer of a population both computed.

THE QUERY IS NOT HERE EITHER. `relational/asks.POPULATIONS` holds it, because a population is a
question about the corpus and the corpus's questions have one home. What this adds is the calling
convention: which store, and what `--series` means when somebody passes one.

WHAT `--series` MEANS NOW. It used to default to `data/build/series.json`, so every one of these
passes needed a compile it never declared, and on a fresh runner with no build the pass died on a
missing path. The store is the default and a file is an override for running against an old build.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "names"))


def _store():
    import relational
    return relational.open_db()


def _rows(path):
    """The `series` array of a build's `series.json`."""
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8")).get("series") or []


def works_in_state(state, path=None):
    """Works whose serialisation state is `state`, with the title and byline a shelf searches on."""
    if path:
        return [w for w in _rows(path) if w.get("state") == state]
    from relational import asks
    return asks.population(_store(), "works in a state", state=state)


def works(path=None):
    """Every work the corpus holds, with its title and byline.

    FOR THE PASSES THAT ASK "IS THIS ONE OF OURS" about a title arriving from outside, which is a
    different question from any of the filtered ones and is why it is here rather than assembled by
    each caller out of a filtered population.
    """
    if path:
        return _rows(path)
    from relational import asks
    return asks.population(_store(), "works with their title and byline")
