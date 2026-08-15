#!/usr/bin/env python3
"""What each source returned, run over run, so a capture that shrank is visible.

WHY THIS EXISTS. GAPS §8. A connector that returns ten chapters where it returned 147 has raised
nothing and passed every check we run: the rows are well formed, the fields are all present, and
the file is fresh. マガポケ sat like that for months and only a person going to look found it.
Staleness cannot see it and a row count cannot either, because there was nothing to compare
against. This is that comparison.

WHAT A DROP MEANS, AND WHEN IT MEANS NOTHING. A host that is down or misbehaving must not raise an
alarm about the data, because the data has not changed: a well-behaved adapter refuses to write a
thin result, so the file on disk still holds the last good capture and its `retrieved` date does not
advance. That is the case this treats as quiet. What it reports is the dangerous one, a source that
was RE-FETCHED and came back with materially less, because that is a capture which has already
overwritten something good.

A source seen for the first time is not a drop. Neither is one that grew.

WHAT THIS DOES NOT COVER. A selector that matches the wrong element returns the right number of
well-formed rows carrying wrong values, and no count will ever see that. GAPS §8 records the
landmark declaration as the answer to it.
"""
import datetime
import pathlib
import sys

# ITS OWN DIRECTORY, SAID RATHER THAN ASSUMED. Running `python3 adapters/ledger.py` puts this
# directory on the path and importing the file any other way does not, so `import captures` below
# worked from the workflow and failed from anywhere else. `the pipeline runs from a clean checkout`
# is the check that says so, and it had never looked here: it selects a file by whether it imports
# `facts`, `names`, `testkit`, `lint` or `relational`, this one imported none of them until §13,
# and a check whose pattern never matches reports clean (STANDING-INSTRUCTIONS §4).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "names"))

import captures  # noqa: E402
import yaml
import yamlfast  # noqa: F401,E402   for its effect: yaml.safe_load reads through libyaml

# How much a re-fetched source may shrink before it is worth reporting. A capture legitimately
# loses a few rows when a platform withdraws chapters, and 冷たくて柔らか alone lost a stretch of 64
# that way. A fifth of a source is not that.
DROP_SHARE = 0.20
# Below this a proportion is noise: a source holding nine rows that returns seven has not broken.
DROP_FLOOR = 20
KEEP = 40


def snapshot(root):
    """{source: {files, works, rows, retrieved}} read from the source tree as it stands."""
    out = {}
    for d in sorted(pathlib.Path(root).glob("*")):
        if not d.is_dir():
            continue
        files = works = rows = 0
        newest = ""
        for f in sorted(d.glob("*.yaml")):
            try:
                # Shared with every other reader of these files in the same deploy, and cached on
                # disk between deploys. This pass walks the whole source tree to count rows, which
                # made it the slowest stage once the other two stopped re-parsing.
                doc = captures.load(f)
            except Exception:                                               # noqa: BLE001
                continue
            files += 1
            got = doc.get("retrieved")
            if got and str(got) > newest:
                newest = str(got)
            for w in (doc.get("works") or []):
                if not isinstance(w, dict):
                    continue
                works += 1
                rows += len(w.get("chapters") or w.get("episodes") or [])
        if files:
            out[d.name] = {"files": files, "works": works, "rows": rows, "retrieved": newest}
    return out


def compare(now, before):
    """[{source, was, now, lost, share}] for sources re-fetched into materially less.

    `before` absent, or a source absent from it, yields nothing: a first sighting is not a drop.
    A source whose `retrieved` has not advanced was not re-fetched, so whatever is on disk is the
    last good capture and there is nothing to report. That is what makes this quiet when a host is
    down rather than noisy.
    """
    out = []
    for name, cur in (now or {}).items():
        old = (before or {}).get(name)
        if not old:
            continue
        if str(cur.get("retrieved") or "") <= str(old.get("retrieved") or ""):
            continue                                  # not re-fetched; the file is untouched
        was, is_ = old.get("rows") or 0, cur.get("rows") or 0
        lost = was - is_
        if lost <= 0 or was < DROP_FLOOR:
            continue
        share = lost / was
        if share >= DROP_SHARE:
            out.append({"source": name, "was": was, "now": is_, "lost": lost,
                        "share": round(share, 3)})
    return sorted(out, key=lambda x: -x["share"])


def append(runs, snap, at=None, keep=KEEP):
    """The run history with this run on the end, oldest dropped past `keep`.

    Append-only within the window. A run is a record of what was true once and rewriting one would
    make the comparison meaningless, which is the same rule the feed archives keep.
    """
    row = {"at": at or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "sources": snap}
    return ((runs or []) + [row])[-keep:]


def main(argv=None):
    import argparse, json                                                   # noqa: E401

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", default="data/source")
    ap.add_argument("--file", default="data/ledger/runs.yaml")
    ap.add_argument("--out", default="data/build/ledger.json")
    # THE SAME FLAG `build.py` AND `check.py` CARRY. The drops go in the store; this writes the
    # file only where a person asked for one.
    ap.add_argument("--emit-json", action="store_true", help="also write --out")
    a = ap.parse_args(argv)

    p = pathlib.Path(a.file)
    doc = yaml.safe_load(p.read_text()) if p.exists() else None
    runs = (doc or {}).get("runs") or []
    snap = snapshot(a.source)
    previous = runs[-1]["sources"] if runs else None
    drops = compare(snap, previous)

    runs = append(runs, snap)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(
        {"note": "What each source returned, run over run. Append-only within a window of "
                 f"{KEEP}. A source that was not re-fetched is not compared: see adapters/ledger.py.",
         "runs": runs}, allow_unicode=True, sort_keys=False))

    # THE STORE IS WHERE THIS GOES, §13. `_store` puts the same four numbers in `run_drop` and
    # `run_report`, and `status.from_store` reads them there. The file had one reader, `status.py`,
    # which stopped opening it; `--emit-json` keeps it for a person looking at a run by hand.
    _store(drops, len(runs), runs[-2]["at"] if len(runs) > 1 else None)
    if a.emit_json:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(
            {"runs_held": len(runs), "previous_at": runs[-2]["at"] if len(runs) > 1 else None,
             "drops": drops, "sources": snap}, ensure_ascii=False, indent=1))
    for d in drops:
        print(f"  DROP {d['source']}: {d['was']} -> {d['now']} rows "
              f"({d['share']:.0%} lost) after a re-fetch")
    print(f"ledger: {len(snap)} source(s), {len(runs)} run(s) held, {len(drops)} drop(s)")
    return 0


def _store(drops, runs_held, previous_at):
    """The drops and the window's depth, into the store. STORE-PLAN §13.

    THE THIRD SMALL WRITE OF A RUN, and the third for the same reason: this is computed here, after
    the compile, because it compares today's capture against the runs this file holds. `build.py`
    writes the census and `check.py` the checks; each owns what it computes, which is §3 rather
    than three copies of one idea.

    A FAILURE COSTS THE DROPS AND NOT THE RUN. `data/ledger/runs.yaml` is already written by the
    time this is reached and is the record of account; `the store carries this run's census` is
    what fails at check-in if the store stops receiving any of it.
    """
    try:
        here = pathlib.Path(__file__).resolve().parent
        sys.path.insert(0, str(here / "names"))
        sys.path.insert(0, str(here))
        import relational as _r
        from relational import delta as _d
        if not _r.DB.exists():
            return
        db = _r.open_db()
        _d.ensure(db)
        _d.reconcile(db, "run_drop", ["source"],
                     [{"source": d["source"], "was": d["was"], "now": d["now"],
                       "share": round(float(d["share"]), 6)} for d in drops])
        _r.note(db, {"ledger.runs_held": runs_held, "ledger.previous_at": previous_at})
        db.commit()
    except Exception as why:                                                # noqa: BLE001
        print(f"ledger: the store was not updated ({why.__class__.__name__}: {why})")


if __name__ == "__main__":
    raise SystemExit(main())
