#!/usr/bin/env python3
"""What produces each data file, and which scheduled outputs have gone stale.

The registry is `adapters/producers.yaml`, whose header says why it exists. This module is the one
reader: `entry` finds the entry a path falls under, `stale` lists the `run` files older than their
limit, and `main` writes those as failed outcomes into the run's report, where `runhealth.py`
counts them like any other source that is not working.

    producers.py --today 2026-10-15 --report R.json
"""
import argparse
import datetime
import fnmatch
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "adapters" / "producers.yaml"
DIRS = ("data/source", "data/coverage", "data/queue")
RETRIEVED = re.compile(r'^retrieved:\s*"?(\d{4}-\d{2}-\d{2})', re.M)


def load(path=REGISTRY):
    return (yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8")) or {}).get("entries") or []


def entry(path, entries):
    """The first entry whose patterns match `path`, relative to the repository, or None."""
    p = str(path)
    for e in entries:
        if any(fnmatch.fnmatchcase(p, pat) for pat in e.get("paths") or []):
            return e
    return None


def files(root=ROOT):
    """Every file under the registered directories, relative to `root`."""
    out = []
    for d in DIRS:
        base = pathlib.Path(root) / d
        if base.exists():
            out += [str(f.relative_to(root)) for f in sorted(base.rglob("*")) if f.is_file()]
    return out


def retrieved(path):
    """The `retrieved:` date a file states near its top, or None."""
    try:
        head = pathlib.Path(path).read_text(encoding="utf-8", errors="ignore")[:4000]
    except OSError:
        return None
    m = RETRIEVED.search(head)
    return m.group(1) if m else None


def stale(entries, today, root=ROOT):
    """`[(path, entry, date)]` for each `run` file older than its entry's `max_age_days`.

    A file stating no date under an entry that sets a limit is stale too: a producer that stopped
    writing the date has stopped saying how old its output is.
    """
    out = []
    t = datetime.date.fromisoformat(today)
    for f in files(root):
        e = entry(f, entries)
        if not e or e.get("status") != "run" or not e.get("max_age_days"):
            continue
        d = retrieved(pathlib.Path(root) / f)
        if not d or (t - datetime.date.fromisoformat(d)).days > int(e["max_age_days"]):
            out.append((f, e, d))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--today", required=True)
    ap.add_argument("--report", default=None)
    a = ap.parse_args(argv)
    got = stale(load(), a.today)
    # ONE OUTCOME PER PRODUCER, not per file, so a stuck adapter is one issue however many files.
    by = {}
    for f, e, d in got:
        by.setdefault(e.get("producer") or f, []).append((f, d))
    outcomes = [{"id": f"stale:{p}", "ok": False, "stage": "freshness",
                 "error": f"{len(fs)} file(s) past their age, e.g. {fs[0][0]} dated {fs[0][1] or 'nothing'}"}
                for p, fs in sorted(by.items())]
    fresh = {e.get("producer") for e in load() if e.get("status") == "run"} - set(by) - {None}
    outcomes += [{"id": f"stale:{p}", "ok": True, "stage": "freshness"} for p in sorted(fresh)]
    for o in outcomes:
        if not o["ok"]:
            print(f"  stale {o['id'][6:]}: {o['error']}")
    print(f"{len(by)} producer(s) with stale output, {len(fresh)} current")
    if a.report:
        rp = pathlib.Path(a.report)
        prior = json.loads(rp.read_text()) if rp.exists() else []
        rp.write_text(json.dumps(prior + outcomes, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
