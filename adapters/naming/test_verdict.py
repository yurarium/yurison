#!/usr/bin/env python3
"""naming/verdict.py: what the naming job may commit, and the record of what it used.

COVERS = ['adapters/naming/verdict.py']
"""
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit                                                          # noqa: E402
import verdict as v                                                     # noqa: E402

BEFORE = """invariants:
  FAIL  every platform a reader is shown is registered: 1
  ok    the store refused no row
budgets (ratchet down only):
  FAIL  targets a capture wrote no row for: 10 (budget 6)
"""
AFTER_SAME = BEFORE + "  FAIL  credit fields an identifier does not cover: 166 (budget 154)\n"
AFTER_WORSE = BEFORE.replace("  ok    the store refused no row", "  FAIL  the store refused no row: 2")


def main(s):
    s.eq(v.disallowed(["data/names/curated.yaml", "data/identity/works.yaml"]),
         ["data/identity/works.yaml"], "the curated names are the job's to change, the registry not")
    s.eq(v.disallowed(["data/names/curated.yaml", "data/source/x.yaml", "build.py"]),
         ["data/source/x.yaml", "build.py"], "a capture or the code is not")
    s.eq(v.disallowed(["data/names/titles.yaml", "docs/tracker.html"]), [],
         "what curate --apply and the build rewrite is not counted against it")
    events = ['{"type":"system"}', '{"type":"result","num_turns":40,"duration_ms":600000,'
              '"usage":{"input_tokens":1000,"output_tokens":9000},"result":"work"}',
              'not json', '{"type":"result","num_turns":1,"duration_ms":1600,'
              '"usage":{"input_tokens":5,"output_tokens":61},"result":"a monitor timed out"}']
    f = v.fold(events)
    s.eq((f["num_turns"], f["duration_ms"], f["usage"]["output_tokens"], f["result"]),
         (41, 601600, 9061, "a monitor timed out"), "the whole session is summed, not its last wake")
    s.eq(v.fold(events + ['{"type":"result","structured_output":{"names":[]}}'])["structured_output"],
         {"names": []}, "and the answer a schema asked for is kept for integrate.py")

    s.eq(v.failing(BEFORE), {"every platform a reader is shown is registered"},
         "a failing invariant is read by name, and a failing budget is not counted")
    s.eq(v.worse(BEFORE, AFTER_SAME), [], "a budget that rose with the job's arrivals is not the job's")
    s.eq(v.worse(BEFORE, AFTER_WORSE), ["the store refused no row"], "an invariant the job broke is")

    diff = ('+  - id: w03322\n+    title: "新作"\n+  "新作":\n+    en: "New Work"\n'
            ' context\n+    note: >-\n')
    s.eq(v.counts(diff), (1, 1), "one identifier minted and one name written")
    line = v.record({"num_turns": 14, "duration_ms": 90000, "is_error": False,
                     "usage": {"input_tokens": 1000, "cache_read_input_tokens": 50000,
                               "output_tokens": 3000}},
                    run=7, model="sonnet", outcome="committed", diff_text=diff, today="2026-10-16")
    s.eq((line["turns"], line["input_tokens"], line["output_tokens"], line["inducted"], line["named"]),
         (14, 51000, 3000, 1, 1), "the ledger line carries turns, tokens and what changed")
    s.eq((line["fresh_input_tokens"], line["cache_read_tokens"], line["cache_write_tokens"]),
         (1000, 50000, 0), "with fresh input, cache reads and cache writes kept apart")
    s.eq(v.record({}, 7, "sonnet", "nothing", "", "2026-10-16")["turns"], None,
         "a run that produced no result still records itself")

    # THE WORKING TREE IS READ AS GIT SEES IT, untracked files included, so a file the job wrote
    # outside the allowed three cannot slip past by never having been added.
    with tempfile.TemporaryDirectory() as d:
        run = lambda *a: subprocess.run(["git", *a], cwd=d, check=True, capture_output=True)  # noqa: E731
        run("init", "-q")
        run("config", "user.email", "t@t")
        run("config", "user.name", "t")
        pathlib.Path(d, "kept.txt").write_text("a\n")
        run("add", ".")
        run("commit", "-qm", "x")
        pathlib.Path(d, "kept.txt").write_text("b\n")
        pathlib.Path(d, "new.txt").write_text("c\n")
        s.eq(v.changed(d), ["kept.txt", "new.txt"], "a modified and an untracked file are both seen")
        # WHAT THE COMPILE CHANGED BEFORE THE JOB IS NOT THE JOB'S.
        base = v.snapshot(d)
        s.eq(v.since(v.changed(d), base, d), [], "nothing has changed since the snapshot")
        pathlib.Path(d, "kept.txt").write_text("c\n")
        pathlib.Path(d, "job.txt").write_text("d\n")
        s.eq(v.since(v.changed(d), base, d), ["job.txt", "kept.txt"],
             "a file changed again after it, or new since it, is the job's")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "naming.verdict"))
