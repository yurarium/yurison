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

BEFORE = """budgets (ratchet down only):
  FAIL  targets a capture wrote no row for: 10 (budget 6)
  ok    incomplete attested rows: 40
"""
AFTER_SAME = BEFORE + "  ok    one page cited for two claims: 1\n"
AFTER_WORSE = BEFORE + "  FAIL  titles showing a romanisation nobody has ruled on: 1 (budget 0)\n"


def main(s):
    s.eq(v.disallowed(["data/names/curated.yaml", "data/identity/works.yaml"]), [],
         "the registry and the curated names are the job's to change")
    s.eq(v.disallowed(["data/names/curated.yaml", "docs/budgets.json", "build.py"]),
         ["docs/budgets.json", "build.py"], "a budget or the code is not")

    s.eq(v.failing(BEFORE), {"targets a capture wrote no row for"}, "a failing check is read by name")
    s.eq(v.worse(BEFORE, AFTER_SAME), [], "a budget already over before the job is not the job's")
    s.eq(v.worse(BEFORE, AFTER_WORSE), ["titles showing a romanisation nobody has ruled on"],
         "a check the job made fail is")

    diff = ('+  - id: w03322\n+    title: "新作"\n+  "新作":\n+    en: "New Work"\n'
            ' context\n+    note: >-\n')
    s.eq(v.counts(diff), (1, 1), "one identifier minted and one name written")
    line = v.record({"num_turns": 14, "duration_ms": 90000, "is_error": False,
                     "usage": {"input_tokens": 1000, "cache_read_input_tokens": 50000,
                               "output_tokens": 3000}},
                    run=7, model="sonnet", outcome="committed", diff_text=diff, today="2026-10-16")
    s.eq((line["turns"], line["input_tokens"], line["output_tokens"], line["inducted"], line["named"]),
         (14, 51000, 3000, 1, 1), "the ledger line carries turns, tokens and what changed")
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
