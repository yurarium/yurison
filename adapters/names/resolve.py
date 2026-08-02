#!/usr/bin/env python3
"""Run the name passes, and answer "is it still working" without reading a log.

NAMES-PLAN §4 asks for progress to be legible from outside — a count of resolved / attempted /
remaining per pass. That is `resolve.py --status`, and it reads the same YAML the passes write, so
it can be run against a job that is mid-flight from another terminal.

WHY THE COUNTS ARE REPORTED TWICE. The plan's §2 census measured 965 authors and 1055 titles from
data/build/series.json alone. The passes actually run over a slightly larger set, because the feed
files carry works that have not yet become series rows. Reporting only the bigger number would make
every figure incomparable with the plan; reporting only the plan's would quietly drop names we hold.
So both are printed, with the plan's set as the denominator that matches §2 and §4a.

RESOLVED MEANS TWO DIFFERENT THINGS and the status output keeps them apart, because collapsing them
hides which half of the job is left:

  reading   we know how the name is SAID. This is what §8.1 stores, what the romanisation style
            toggle renders from, and what §5c's furigana needs.
  en        we hold a Latin string a source gave us — an official English title, or a name the
            person writes themselves. Absent is normal and not a gap: an author whose reading is
            known needs no stored `en`, because the rendering is generated per reader.

An author with a reading and no `en` is finished. A title with a reading and no `en` is not — it
still has no English name — which is why the two kinds report separately.

Usage:  resolve.py --status
        resolve.py --run 0,1        (no network)
        resolve.py --run 2 --source wikidata
"""
import argparse
import collections
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names import inputs, kana  # noqa: E402
from names.store import NameStore  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def report(store, build_dir):
    authors, titles, _, _by_title = inputs.load(build_dir)
    plan_authors, plan_titles = inputs.plan_baseline(build_dir)

    for kind, names, plan in (("authors", authors, plan_authors), ("titles", titles, plan_titles)):
        recs = store.records[kind]
        names = sorted(names)
        st = store.status(kind, names)
        print(f"\n=== {kind}  ({len(names)} held, {len(plan)} in the NAMES-PLAN §2 census) ===")
        print(f"  reading known      {st['reading']:5}   "
              f"({sum(1 for n in plan if recs.get(n, {}).get('reading')):>4} of the census set)")
        print(f"  English string     {st['en']:5}   "
              f"({sum(1 for n in plan if recs.get(n, {}).get('en')):>4} of the census set)")
        print(f"  either             {st['resolved']:5}")
        print(f"  nothing yet        {st['remaining']:5}")
        print(f"  asked and told no  {st['attempted_only']:5}")
        print(f"  conflicting claims {st['conflicts']:5}")
        # Candidates are held-but-unusable English titles. Counted separately because they are not
        # progress in the sense the other numbers mean — nothing can be displayed from them — but
        # they are also not work still to be searched for: the string is in hand and confirming it
        # is one fetch of a named page.
        cand = sum(1 for n in names if recs.get(n, {}).get("en_candidates"))
        cand_only = sum(1 for n in names
                        if recs.get(n, {}).get("en_candidates") and not recs.get(n, {}).get("en"))
        print(f"  unconfirmed English candidates {cand:5}   ({cand_only} with no usable `en`)")

        by_pass = collections.Counter()
        by_basis = collections.Counter()
        by_reading_basis = collections.Counter()
        for n in names:
            r = recs.get(n) or {}
            if not (r.get("reading") or r.get("en")):
                continue
            by_pass[r.get("reading_pass", r.get("en_pass"))] += 1
            if r.get("basis"):
                by_basis[r["basis"]] += 1
            if r.get("reading_basis"):
                by_reading_basis[r["reading_basis"]] += 1
        print(f"  first resolved by pass: {dict(sorted(by_pass.items(), key=lambda kv: (kv[0] is None, kv[0])))}")
        print(f"  english basis:          {dict(by_basis)}")
        print(f"  reading basis:          {dict(by_reading_basis)}")

        # What is left, by script — this is what sizes pass 3, so it is the number the plan wants.
        residue = collections.Counter(kana.script_class(n) for n in names
                                      if not (recs.get(n, {}).get("reading") or recs.get(n, {}).get("en")))
        print(f"  residue by script:      {dict(residue)}")

    tried = collections.Counter()
    for entries in store.attempts.values():
        for e in entries:
            tried[e.get("source")] += 1
    print(f"\nattempts recorded per source: {dict(tried)}")


def run_pass(which, build, out, cache, extra):
    scripts = {
        "0": ["pass0_cache.py"],
        "1": ["pass1_kana.py"],
        "2": ["pass2_bulk.py"],
    }
    if which not in scripts:
        print(f"pass {which} is not runnable here "
              f"({'see pass3_search.py' if which == '3' else 'no such pass'})", file=sys.stderr)
        return 2
    cmd = [sys.executable, str(HERE / scripts[which][0]), "--build", build, "--out", out]
    if which == "0":
        cmd += ["--cache", str(pathlib.Path.home() / "workspace")]
    elif which == "2":
        cmd += ["--cache", cache]
    return subprocess.call(cmd + extra)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--out", default="data/names")
    ap.add_argument("--cache", default=str(pathlib.Path.home() / "workspace/names-cache"))
    ap.add_argument("--run", help="comma-separated passes to run, in order (0,1,2)")
    ap.add_argument("--status", action="store_true", help="report progress and stop")
    args, extra = ap.parse_known_args(argv)

    if args.run:
        # 1 before 0: both are free and pass 1's readings are `surface`, the highest rank there is,
        # so nothing later can displace them and every other pass gets a smaller queue.
        for which in args.run.split(","):
            rc = run_pass(which.strip(), args.build, args.out, args.cache, extra)
            if rc:
                return rc

    store = NameStore(args.out)
    report(store, args.build)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
