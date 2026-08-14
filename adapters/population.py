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
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "names"))


def _named(path):
    """The path, where a caller named one that is actually there. Otherwise nothing.

    A PATH THAT IS NOT THERE MEANS "USE THE STORE", and deciding it here is the whole point. Each
    caller used to test `.exists()` before handing the path over, which is a rule every call site
    has to remember: `adapters/status.py` remembered it for `series` and forgot it for `works` in
    the same two lines, and CI died on the second. The fourth run of the day lost to that, on the
    very class this module exists to close.

    IT IS NOT A SILENT FALLBACK ONTO STALE DATA. The store is the compiled form and a named file is
    the override for reading an OLDER build, so a name pointing at nothing is a caller asking for a
    build that is not there, and the answer is the current corpus rather than an error.
    """
    return path if path and pathlib.Path(path).exists() else None


def _store():
    import relational
    return relational.open_db()


def _rows(path):
    """The `series` array of a build's `series.json`."""
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8")).get("series") or []


def works_in_state(state, path=None):
    """Works whose serialisation state is `state`, with the title and byline a shelf searches on."""
    path = _named(path)
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
    path = _named(path)
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
    path = _named(path)
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
    path = _named(path)
    if path:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8")).get("releases") or []
    from relational import emit
    return emit.feed(_store())


def feed_window(path=None):
    """The releases the feed FILES hold: the rolling window, then each archived month in order.

    NOT `releases`, WHICH IS THE WHOLE LIST. The name passes walked `feed/current.json` and the
    archives, so the population they spent requests on was what a reader can reach rather than
    every row the run compiled. Handing them the whole list quietly widened that by 311 rows and
    209 people gained addresses from releases the window has rolled past.

    ROWS ARE NOT DEDUPLICATED, because the window overlaps the newest archive and the callers here
    count occurrences: an author's `urls` list carries one entry per row that credited them.
    """
    path = _named(path)
    if path:
        base = pathlib.Path(path)
        names = ["feed/current.json"] + [f"feed/{p.name}" for p in
                                         sorted((base / "feed").glob("[0-9]*.json"))]
        out = []
        for n in names:
            f = base / n
            if f.exists():
                out += json.loads(f.read_text(encoding="utf-8")).get("releases") or []
        return out
    from relational import emit
    feed = emit.feed_files(_store())
    order = ["feed/current.json"] + sorted(
        n for n in feed if re.fullmatch(r"feed/[0-9]{4}-[0-9]{2}\.json", n))
    out = []
    for name in order:
        if name in feed:
            out += (json.loads(feed[name]) or {}).get("releases") or []
    return out


def records(path=None):
    """The record layer, as `works.json` states it: one row per catalogued book run."""
    path = _named(path)
    if path:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8")).get("works") or []
    from relational import emit
    return emit.works(_store()).get("works") or []


def index(path=None):
    """The collapsed bibliographic index, as `index.json` states it."""
    path = _named(path)
    if path:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    from relational import emit
    return emit.index(_store())


def names(path=None):
    """The name map as `feed/names.json` states it: what the build spelled for every surface."""
    path = _named(path)
    if path:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    from relational import emit
    db = _store()
    return emit.names(db, dict(db.execute("SELECT key, value FROM run_report")).get(
        "generated") or "")
