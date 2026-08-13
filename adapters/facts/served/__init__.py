#!/usr/bin/env python3
"""What the site is served, field by field, and which of those fields the store could answer.

WHY THIS EXISTS. STORE-PLAN makes the relational store the sole compiled form, and every section of
it is a migration. A migration with no number is a sequence of changes that feel like progress, so
this is the number: how much of what a reader is served still reaches them without passing through
the store. It starts at the identity spine and must end at everything.

IT ASKS ABOUT WHAT THE SITE SERVES, NOT ABOUT WHAT THE STORE HOLDS. A budget counting tables would
rise by adding a table nobody reads. The population here is the files `deploy.sh` copies, so the
only way to move it is to make a field the site actually gets answerable from the store.

WHAT IT CANNOT SEE, and STORE-PLAN §1 says so outright: a field derivable in principle and not in
fact, because the emitter still reads the JSON. Derivability is what this measures and emission is
what proves it, which is why §6 is a section of its own rather than a footnote here.
"""
import json
import pathlib
import re

#: The corpus files `deploy.sh` copies into `kari/data`. `checks.json`, `status.json` and `run.json`
#: are deliberately absent: they are the RUN's report on itself rather than data about works, and
#: requiring the gate's own findings to come from the store would be a category error. The line is
#: between what a reader's page is built from and what describes the run that built it.
CORPUS = ("index.json", "works.json", "series.json", "credits.json", "publishers.json")

#: A key that reads as a field name rather than as data.
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_map(d):
    """Whether a dict is keyed by DATA rather than by field name.

    THE PROBLEM THIS SOLVES. `feed/names.json` is keyed by folded title and holds 3,301 of them, so
    walking it naively reports 3,301 field paths that are one field. Collapsing every map to `{}`
    took the corpus from 137,131 paths to something a person can read.

    TWO SIGNALS, EITHER OF WHICH IS ENOUGH, because one alone gets a real case wrong.

      THE KEYS READ AS DATA. `authors` in names.json is keyed `*sow*` and `2C=がろあ`, which no
      record would call a field. This is what catches a map whose values vary in shape, and the
      string-valued maps `floor` and `phrases`, where there are no value keys to compare.

      THE VALUES SHARE A SMALL VOCABULARY. A map of records has many entries drawing on a handful
      of fields between them. This is what catches a map whose keys happen to look like identifiers,
      which `credits.json` keyed by `c01876` would otherwise slip through as.

    THE COUNTER-CASE THAT DECIDES THE DESIGN, and it is why neither signal is used alone. A
    `series.json` row has 31 keys and almost all of its values are scalars, so a rule reading "many
    keys, simple values" as a map would collapse the single most important record in the corpus into
    one path and report near-total coverage. Its keys ARE field names, so the first signal refuses
    it, and its values are not dicts, so the second never fires.
    """
    if not isinstance(d, dict) or len(d) <= 8:
        return False
    keys = list(d)
    named = sum(1 for k in keys if IDENTIFIER.match(str(k)))
    if named * 2 < len(keys):
        return True
    vals = [v for v in list(d.values())[:12]]
    if vals and all(isinstance(v, dict) for v in vals):
        seen = set()
        for v in vals:
            seen |= set(v)
        return len(seen) <= 40
    return False


def paths(doc, limit=30, depth=8):
    """Every distinct field path in one document, with lists and data-keyed maps collapsed.

    `limit` samples a list or a map rather than walking all of it, because a path that appears in
    the first thirty rows and nowhere else is not a field anybody is served differently.
    """
    out = set()

    def walk(v, at, d):
        if d > depth:
            return
        if isinstance(v, dict):
            if is_map(v):
                out.add(at + "{}")
                for x in list(v.values())[:limit]:
                    walk(x, at + "{}", d + 1)
                return
            for k, x in v.items():
                here = f"{at}.{k}" if at else str(k)
                out.add(here)
                walk(x, here, d + 1)
        elif isinstance(v, list):
            for x in v[:limit]:
                walk(x, at + "[]", d + 1)

    walk(doc, "", 0)
    return out


def served(build="data/build"):
    """`{file: {path}}` for every corpus file the site is served, feed months included."""
    root = pathlib.Path(build)
    out = {}
    for name in CORPUS:
        f = root / name
        if f.exists():
            out[name] = paths(json.loads(f.read_text(encoding="utf-8")))
    feed = root / "feed"
    if feed.is_dir():
        for f in sorted(feed.glob("*.json")):
            out[f"feed/{f.name}"] = paths(json.loads(f.read_text(encoding="utf-8")))
    return out


#: WHICH SHIPPED FIELDS THE STORE COULD ANSWER TODAY, as `file:path-prefix`. A declaration, because
#: nothing can infer that `series[].work` is `work.title`; the mapping is a design decision and
#: belongs where a reader can disagree with it.
#:
#: IT IS DELIBERATELY A PREFIX LIST AND NOT ONE ENTRY PER FIELD. A per-field list would be a second
#: thing to keep in step with the schema, which is the fault `_input_keys` refuses in `check.py`.
#: Each section of STORE-PLAN adds the prefixes it has modelled, so the list grows once per domain.
#:
#: THE SPINE, PLUS WHAT §2 FILLED AND §3 MODELLED. `edition` holds 6,108 rows and `work_publisher`
#: 2,661, so a volume's ISBN, number, designation, date, kind and the basis that date rests on are
#: all answerable, and so is which house and line a work is published under.
STORE_ANSWERS = (
    "index.json:id",
    "index.json:t",
    "series.json:series[].id",
    "series.json:series[].work",
    "series.json:series[].first",
    "works.json:works[].work_id",
    "works.json:works[].publisher",
    "works.json:works[].imprint",
    "works.json:works[].volumes[].isbn",
    "works.json:works[].volumes[].number_n",
    "works.json:works[].volumes[].published",
    "works.json:works[].volumes[].delivered",
    "works.json:works[].volumes[].designation",
    "works.json:works[].volumes[].published_basis",
    "works.json:works[].volumes[].published_source",
    "works.json:works[].volumes[].isbn_source",
    "works.json:works[].volumes[].madb_id",
    "credits.json:credits{}.id",
    "credits.json:credits{}.name",
    "publishers.json:publishers{}.id",
    "publishers.json:publishers{}.name",
    # §4: what a platform offers of a work, and what it published.
    "series.json:series[].sources[].platform",
    "series.json:series[].sources[].url",
    "series.json:series[].sources[].chapters",
    "series.json:series[].sources[].free",
    "series.json:series[].sources[].free_timed",
    "series.json:series[].sources[].priced",
    "series.json:series[].sources[].latest",
    "series.json:series[].sources[].partial",
    "series.json:series[].sources[].retrieved",
    "feed/current.json:releases[].id",
    "feed/current.json:releases[].wid",
    "feed/current.json:releases[].work",
    "feed/current.json:releases[].plat_name",
    "feed/current.json:releases[].ep",
    "feed/current.json:releases[].pub",
    "feed/current.json:releases[].url",
    "feed/current.json:releases[].type",
    "feed/current.json:releases[].seen",
)


def around(build="data/build"):
    """Every `file:path` the site is served that the store could not answer, sorted."""
    claimed = set(STORE_ANSWERS)
    out = []
    for name, ps in served(build).items():
        for p in sorted(ps):
            key = f"{name}:{p}"
            if key in claimed or any(key.startswith(c + ".") for c in claimed):
                continue
            out.append(key)
    return sorted(out)
