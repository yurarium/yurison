#!/usr/bin/env python3
"""cycle: the two halves run together, and the proof is carried by one of them.

COVERS = ['cycle.py']

THE ONE THAT MATTERS is `--proved-by`. It tells the gate that another process is proving the checks
can fail, which is only sound while this driver reports failure when that process fails. A driver
that passed with a failing test half would have turned the flag into a way of skipping the proof.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cycle
import testkit


def main(s):
    fast, full = cycle.plan(False), cycle.plan(True)
    s.check("--proved-by" in fast["gate"], "the fast path tells the gate who is proving it")
    s.check("--proved-by" not in full["gate"], "--full has each half prove itself")
    s.check("--incremental" in fast["gate"] and "--incremental" not in full["gate"],
            "and --full re-answers every check rather than trusting a remembered pass")
    s.check(any("test.py" in x for x in fast["tests"]),
            "and the tests are the half that carries the proof")

    # A HALF THAT FAILS IS REPORTED AS FAILING. `_run` is what the driver reads its verdict from,
    # so a failing command has to arrive as a non-zero code and not as an exception.
    out = {}
    cycle._run("x", [sys.executable, "-c", "import sys; sys.exit(3)"], out)
    s.eq(out["x"][0], 3, "a failing half comes back with its exit code")
    cycle._run("y", [sys.executable, "-c", "print('fine')"], out)
    s.eq(out["y"][0], 0, "and a passing one with zero")
    s.check(out["y"][1].strip() == "fine", "its output is kept rather than thrown away")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "cycle"))
