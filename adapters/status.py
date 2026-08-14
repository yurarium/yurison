#!/usr/bin/env python3
"""The build's own status, as one file the status page reads and recomputes nothing from.

WHY THIS EXISTS. status.html grew by accretion and computed its own numbers from whatever files it
happened to load, which is two producers of one fact and it has already disagreed with itself: the
budget records 232 works without an English name and counting the built rows gives 236. A page that
reports the health of the system cannot be a second source of the numbers it reports.

WHO READS IT. A person wants the sentence. Whoever maintains this wants the table under it, and
needs it complete rather than rounded, because "maintain it" means reading the detail and acting on
it. So every section here carries both: a count to state, and the rows behind it.

WHAT IT DOES NOT DO YET. Connector health is a delta, not a status. An adapter that returns ten
chapters where it returned 147 last week has raised no error and passed every check we run, and
that is exactly how マガポケ sat at a ten-episode window for months. Answering it needs a per-run
ledger to compare against, which does not exist. Until it does, this reports what can be known from
one run: which sources were read, how many rows each holds, and how old the capture is.
"""
import datetime
import glob
import json
import pathlib
import sys

# ITS OWN DIRECTORY, SAID RATHER THAN ASSUMED, the same as `adapters/ledger.py` and found the same
# way. `the pipeline runs from a clean checkout` selects a file by whether it imports `facts`,
# `names`, `testkit`, `lint` or `relational`; this one imported none of them until §13 gave it
# `from_store`, so the pattern had never matched and two imports that only ever worked because the
# script's own directory happens to be on the path read as clean (STANDING-INSTRUCTIONS §4).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "names"))

import captures  # noqa: E402
import population  # noqa: E402
import delivery  # noqa: E402
import yaml
import yamlfast  # noqa: F401,E402   for its effect: yaml.safe_load reads through libyaml


# What the run DID, in the active voice, because the section asks what it did. A key like
# `thin_sitemap` is a name for whoever wrote it, and a page showing it raw asks the reader to know
# the codebase.
MEANS = {
    "duplicate_chapters": "Merged chapters that two sources described separately",
    "thin_sitemap": "Replaced sitemap rows where a fuller capture of the same work existed",
    "resolver": "Dropped rows the catch-all reader produced that a named adapter already covered",
    "samples": "Held back promotional read-throughs of finished volumes as print candidates",
    "discovery-candidate": "Admitted works that a discovery list names",
    "platform-genre": "Admitted works that a platform files under its own yuri genre",
}


def delta(now, before):
    """What CHANGED, which is what an update is. Absent a previous run, nothing is claimed.

    This is the ledger in miniature: the file it overwrites is the only record of the run before,
    so it is read first. It cannot yet see a connector returning less than it did, because that
    needs per-connector history rather than these totals, and that is the next piece of work.
    """
    if not before:
        return {}
    out = {}
    for k, v in (now or {}).items():
        b = (before or {}).get(k)
        if isinstance(v, int) and isinstance(b, int) and v != b:
            out[k] = v - b
    return out


# WHAT WE EXPECT EACH SOURCE TO RETURN, declared per source because platforms differ in what they
# publish. A capture can succeed and return the wrong shape without raising anything: マガポケ served
# ten faultless episodes where the platform published 147, and no row count or staleness saw it.
#
# A DEVIATION IS A GAP IN THE EXPECTATION UNTIL IT IS CHECKED. The first version of this declared
# a date mandatory everywhere and reported 353 COMIC FUZ rows as malformed. They are not: that
# platform states no updatedDate on its coin chapters, which build.py has documented since the day
# dropping them made every paid chapter there invisible. The expectation was wrong, not the
# capture, so the expectation is what changed. What this measures is agreement with a declaration
# somebody made, and its value is that a RISE means something moved.
SHAPE = ("title", "updated")
EXPECT = {
    # COMIC FUZ dates a coin chapter two ways and neither is a publication date: some carry none
    # at all, 70 of 球詠's 228 among them, and others carry a 公開予定 months ahead, which
    # REQUIREMENTS §5 reads as a schedule. Requiring a date here would report both as damage.
    "comicfuz": ("title",),
}


def conforms(root):
    """{source: (rows, rows carrying every field a chapter row should)}.

    Read from the source files rather than from the build, because by the time a row reaches the
    build the missing field has already been filled in or dropped, and this is asking what the
    capture actually returned.
    """
    out = {}
    for d in sorted(pathlib.Path(root).glob("*")):
        if not d.is_dir():
            continue
        total = good = 0
        for f in sorted(d.glob("*.yaml")):
            try:
                doc = captures.load(f)
            except Exception:                                               # noqa: BLE001
                continue
            for w in (doc.get("works") or []):
                if not isinstance(w, dict):
                    continue
                for c in (w.get("chapters") or w.get("episodes") or []):
                    if not isinstance(c, dict):
                        continue
                    total += 1
                    good += all(c.get(k) for k in EXPECT.get(d.name, SHAPE))
        if total:
            out[d.name] = (total, good)
    return out


def connectors(run, shape=None, drops=None):
    """Per-source capture, newest first by age, with what the ledger says about each."""
    out = []
    for s in run.get("sources") or []:
        tot, good = (shape or {}).get(s.get("source"), (0, 0))
        out.append({"source": s.get("source"), "files": s.get("files"), "works": s.get("works"),
                    "rows": s.get("rows"), "retrieved": s.get("retrieved"),
                    "age_days": s.get("age_days"), "in_scope": bool(s.get("in_scope")),
                    "empty": bool(s.get("empty")),
                    "checked_rows": tot, "well_formed": good,
                    "malformed": tot - good,
                    "drop": (drops or {}).get(s.get("source"))})
    return sorted(out, key=lambda x: (-(x["age_days"] or 0), x["source"] or ""))


LABELS = {
    "works": "works", "chapters": "chapters", "volumes": "volumes",
    "print_works": "works with a print edition", "print_only": "works published only in volumes",
    "with_identifier": "works carrying an identifier",
    # THE WEAKEST DATE IN THE DATABASE, NAMED FOR WHAT IT IS. A reader seeing "delivery dated" in a
    # delta line has to be able to tell it from a printing without opening anything, so the label
    # says which event was dated and does not say "first published".
    "delivery_dated": "works dated by the day a shop began delivering the file",
}


def statistics(series, index):
    """What the database holds. One producer: these are counted here and nowhere else."""
    states = {}
    for w in series:
        states[w.get("state") or "unknown"] = states.get(w.get("state") or "unknown", 0) + 1
    _d = delivery.tally(series)
    basis = {}
    for w in series:
        b = (w.get("work_en") or {}).get("basis")
        basis[b or "none"] = basis.get(b or "none", 0) + 1
    return {
        "works": len(series),
        "states": dict(sorted(states.items(), key=lambda kv: -kv[1])),
        "english_basis": dict(sorted(basis.items(), key=lambda kv: -kv[1])),
        "print_works": sum(1 for w in series if w.get("print")),
        "print_only": sum(1 for w in series if w.get("state") == "print"),
        "volumes": sum(len(w.get("volumes") or []) for w in index),
        "with_identifier": sum(1 for w in series if w.get("id")),
        "chapters": sum(w.get("chapters") or 0 for w in series),
        # THE TOTAL AND NOT THE FOLLOW-UP SPLIT, and the reason is that the split cannot be
        # computed for this population. DEFINITIONS §6 says that for a doujinshi a platform sells,
        # the delivery day may be the only datable event in the work's history, so a number counting
        # these as outstanding would never fall. The state that a better source COULD answer needs
        # the shop's own description of the edition, and every row here came from BOOK☆WALKER, whose
        # descriptions are not held offline: 1,065 of 1,084 sort to `unclassified`. Publishing that
        # as a follow-up figure of 0 would read as nothing to do, which is not what it means. The
        # split and the sentence for each of its states are in run.json.
        "delivery_dated": _d["rows"],
    }


# Budgets and checks that measure the CODE rather than the manga. They are NOT PUBLISHED. The gate
# already blocks a deploy on them, which is where they belong: a site carrying them would be
# claiming responsibility for something the build does not own, and a reader looking at the health
# of a database has no use for how many comments read as stock phrasing.
ENGINEERING = {"modules without a test", "shadowed names in build.py",
               "stock phrasing in comments", "three as an organising shape"}

# The same distinction among the invariants, and the same outcome: these are gated at deployment
# and are not shipped.
ENGINEERING_CHECKS = {"no stock phrasing in public text",
                      "no build-machine paths in published files",
                      "deployed data matches built"}


def split_budgets(budgets):
    """(data, engineering). Both are carried; only one belongs beside the corpus."""
    data = {k: v for k, v in budgets.items() if k not in ENGINEERING}
    eng = {k: v for k, v in budgets.items() if k in ENGINEERING}
    return data, eng


def outstanding(series, budgets, queues):
    """Work nobody has done, grouped by who can do it. That is the distinction that decides action.

    `decision` needs a person to choose. `research` is mechanical and simply unattempted. `debt` is
    a budget that should ratchet down. `candidate` is captured evidence admitted to nothing.
    """
    no_en = [w["work"] for w in series if not (w.get("work_en") or {}).get("en")]
    no_tier = queues.get("classification", 0)
    _data, _ = split_budgets(budgets)
    return [
        {"kind": "decision", "key": "content_tier", "count": no_tier,
         "what": "Classify print works no one has given a content_tier, the axis inclusion rests on"},
        {"kind": "research", "key": "english_names", "count": len(no_en),
         "what": "Name in English the works that carry only a romanisation",
         "rows": sorted(no_en)},
        {"kind": "candidate", "key": "shelf_rows",
         "count": queues.get("bookwalker-yuri", 0) + queues.get("cmoa-yuri", 0),
         "what": "Decide which captured retailer shelf rows this database admits"},
        {"kind": "candidate", "key": "english_licences", "count": queues.get("english-licences", 0),
         "what": "Apply the licences read from the licensor, and hold the works they name that we lack"},
        {"kind": "debt", "key": "data_debts", "count": sum(1 for v in _data.values() if v),
         "what": "Bring down counts that may only ratchet downward", "rows": _data},
    ]


def build(run, checks, series, index, budgets, queues, previous=None, shape=None,
          ledger=None):
    """The whole file. Nothing here is computed twice and nothing is rounded."""
    inv = checks.get("invariants") or []
    _data_inv = [i for i in inv if i.get('name') not in ENGINEERING_CHECKS]
    stats = statistics(series, index)
    prev_stats = (previous or {}).get("statistics") or {}
    return {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "since_last": {"at": (previous or {}).get("generated"),
                       "statistics": delta(stats, prev_stats)},
        "means": MEANS,
        "labels": LABELS,
        "last_run": {
            "at": run.get("generated"),
            "releases": run.get("releases"), "works": run.get("works"),
            "platforms": run.get("platforms"), "series_rows": run.get("series_rows"),
            "identification": run.get("identification") or {},
            "collapsed": run.get("collapsed") or {},
        },
        "gate": {
            # An invariant records `violations`, not `ok`. Counting a key it does not have made
            # every check read as failing on a page whose whole job is to say whether they do.
            "invariants_passing": sum(1 for i in _data_inv if not (i.get("violations") or 0)),
            "invariants": _data_inv,
            # Filtered for the same reason: the gate owns these and the site does not.
            "budgets": [b for b in (checks.get("budgets") or [])
                        if b.get("name") not in ENGINEERING],
        },
        "connectors": connectors(run, shape,
                                 {d["source"]: d for d in (ledger or {}).get("drops") or []}),
        "ledger": {"runs_held": (ledger or {}).get("runs_held", 0),
                   "previous_at": (ledger or {}).get("previous_at"),
                   "drops": (ledger or {}).get("drops") or []},
        "outstanding": outstanding(series, budgets, queues),
        "statistics": stats,
    }


def from_store(db, previous=None):
    """The whole document, with every input taken from the store. STORE-PLAN §13.

    THE ONE PRODUCER STAYS `build` ABOVE, and this only changes where its inputs come from. The
    status page is the site's to build under §11 and the site has a store and nothing else, so a
    second assembler over there would be a second answer to "what did this run do".

    `age_days` IS COMPUTED HERE, because the store refuses to hold it: `retrieved` is a fact about
    a capture and the age is a fact about today, and a stored age is wrong by morning. `connectors`
    sorts on it, so it has to exist by the time that runs.

    WHAT IT CANNOT TAKE FROM THE STORE IS THE PREVIOUS DOCUMENT, which is the file this is about to
    replace and is the only record of the run before it. The caller passes it, because the caller
    is the one that knows where its own copy lives.
    """
    from relational import emit

    run = emit.run(db)
    generated = run.get("generated") or ""
    for s in run["sources"]:
        s["age_days"] = _age(generated, s.get("retrieved"))
    checks = emit.checks(db)
    stored = dict(db.execute("SELECT key, value FROM run_report"))
    return build(
        run, checks,
        emit.series(db, generated).get("series") or [],
        emit.works(db).get("works") or [],
        {b["name"]: b["budget"] for b in checks["budgets"] if b.get("budget") is not None},
        {n: d for n, d in db.execute("SELECT name, depth FROM run_queue ORDER BY name")},
        previous,
        {s["source"]: (s.get("stated_rows") or 0, s.get("conforming_rows") or 0)
         for s in run["sources"]},
        {"runs_held": int(stored.get("ledger.runs_held") or 0),
         "previous_at": stored.get("ledger.previous_at"),
         "drops": [{"source": src, "was": was, "now": now, "lost": was - now, "share": share}
                   for src, was, now, share in db.execute(
                       "SELECT source, was, now, share FROM run_drop ORDER BY share DESC")]})


def _age(generated, retrieved):
    """Days between the run's date and a capture's, or nothing where either is missing."""
    try:
        return (datetime.date.fromisoformat(generated)
                - datetime.date.fromisoformat(retrieved)).days
    except (TypeError, ValueError):
        return None


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--queues", default="data/queue")
    ap.add_argument("--budgets", default="docs/budgets.json")
    ap.add_argument("--out", default="data/build/status.json")
    a = ap.parse_args(argv)

    b = pathlib.Path(a.build)
    read = lambda n: json.loads((b / n).read_text())                        # noqa: E731
    run, checks = read("run.json"), read("checks.json")
    # THE STORE, §13. This went through a `read` lambda, so the filename and the open were in
    # different statements and the lint reported the file clean; CI found it instead.
    series = population.series(b / "series.json" if (b / "series.json").exists() else None)
    index = population.records(b / "works.json")
    budgets = json.loads(pathlib.Path(a.budgets).read_text())

    queues = {}
    for f in sorted(glob.glob(f"{a.queues}/*.yaml")):
        d = captures.load(f)
        rows = next((v for v in d.values() if isinstance(v, list)), [])
        queues[pathlib.Path(f).stem] = len(rows)

    # Read what this run is about to overwrite. It is the only record of the run before it.
    outp = pathlib.Path(a.out)
    previous = json.loads(outp.read_text()) if outp.exists() else None
    led = b / "ledger.json"
    doc = build(run, checks, series, index, budgets, queues, previous,
                conforms("data/source"), json.loads(led.read_text()) if led.exists() else None)
    outp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    print(f"status: {doc['statistics']['works']} works, {len(doc['connectors'])} connector(s), "
          f"{len(doc['outstanding'])} outstanding group(s) -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
