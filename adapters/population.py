#!/usr/bin/env python3
"""The populations a capture pass works from, asked of the store. STORE-PLAN §13.

WHY THIS IS A MODULE AND NOT A LINE IN EACH PASS. Eleven adapters read `data/build/series.json` and
filtered it in Python, and the first four converted were about to hold four copies of the same six
lines: open the store, ask the registry, fall back to a file if one was named. That is the shape
STANDING-INSTRUCTIONS §3 refuses, and the copies drift in the way `shopquery` and `editions/capture`
already demonstrated, each docstring claiming to be the one producer of a population both computed.

THE QUERY LIVES IN `relational/asks.POPULATIONS`, because a population is a question about the
corpus and the corpus's questions have one home. What this adds is the calling convention: which
store, and what `--series` means when somebody passes one.

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


def series(path=None):
    """Every work as `series.json` states it, from the store that emits that file.

    THE WHOLE ROW, FOR THE PASSES THAT NEED THE WHOLE ROW. `bylines`, `feedgap`, `credit_identity`
    and `publisher_identity` read a work's platforms, its print edition, its url and its state
    together, and a narrow query per pass would be four queries reproducing one row badly. The
    emitter that produces `series.json` already answers exactly this, so asking IT is asking the
    store, and what disappears is the file in between.

    IT IS NOT A SHORTCUT AROUND §13. The point of the section is that a question about the compiled
    form is asked of the compiled form rather than sent out through a file and read back; a pass
    calling the emitter has no compile to wait for and no path to miss.
    """
    if path:
        return _rows(path)
    import relational
    from relational import emit
    db = _store()
    return emit.series(db, dict(db.execute("SELECT key, value FROM run_report")).get(
        "generated") or "").get("series") or []


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


def releases(path=None):
    """Every release the run compiled, as `feed.json` states them.

    `emit.feed` IS THE ONE PRODUCER and this is the whole list rather than the window. The feed
    FILES are the rolling window plus the archived months, which overlap and between them hold
    fewer rows than the run compiled, so assembling this from them would have measured a different
    population from the one `acceptance.py` has always measured.
    """
    if path:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8")).get("releases") or []
    from relational import emit
    return emit.feed(_store())


def records(path=None):
    """The record layer, as `works.json` states it: one row per catalogued book run."""
    if path:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8")).get("works") or []
    from relational import emit
    return emit.works(_store()).get("works") or []


def index(path=None):
    """The collapsed bibliographic index, as `index.json` states it."""
    if path:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    from relational import emit
    return emit.index(_store())
