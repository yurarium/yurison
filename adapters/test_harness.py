#!/usr/bin/env python3
"""Tests for the test harness. Without these, everything else it reports is unverified.

COVERS = ['test.py', 'adapters/testkit.py']
"""
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _run(body, args=()):
    """Write a throwaway suite, run it through test.py's own child boot, return (rc, output)."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", dir=ROOT, delete=False) as f:
        f.write(body)
        p = pathlib.Path(f.name)
    try:
        sys.path.insert(0, str(ROOT))
        import importlib
        t = importlib.import_module("test")
        label, rc, _, out, err = t.run_one(str(p), [sys.executable, str(p)],
                                           canary=("canary" in args))
        return rc, out + err
    finally:
        p.unlink(missing_ok=True)


NET = '''
import urllib.request
urllib.request.urlopen("https://example.com", timeout=5).read()
print("REACHED THE NETWORK")
'''

REAL = '''
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
import testkit
def main(s):
    s.eq(1 + 1, 2, "arithmetic")
sys.exit(testkit.run(main, "real"))
'''

VACUOUS = '''
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
import testkit
def main(s):
    pass
sys.exit(testkit.run(main, "vacuous"))
'''


def main(s):
    # The guard must stop a real outbound request, and say why.
    rc, out = _run(NET)
    s.ne(rc, 0, "a test reaching the network must fail")
    s.check("REACHED THE NETWORK" not in out, "the request must not have completed")
    s.check("offline" in out.lower(), "the failure must explain the offline rule")

    # A suite asserting something real passes normally and FAILS when inverted.
    rc, _ = _run(REAL)
    s.eq(rc, 0, "a real suite passes")
    rc, out = _run(REAL, ("canary",))
    s.eq(rc, 0, "a real suite is reported healthy under inversion")
    s.check("all can fail" in out, "canary mode says the checks can fail")

    # A suite asserting nothing is vacuous, inverted or not.
    rc, out = _run(VACUOUS)
    s.eq(rc, 2, "a suite with no checks is vacuous")
    s.check("VACUOUS" in out, "and says so")

    # Discovery must not depend on a hand-maintained list.
    sys.path.insert(0, str(ROOT))
    import importlib
    t = importlib.import_module("test")
    runnables, covered = t.collect()
    s.check(len(runnables) >= 8, "discovery finds the existing suites")
    s.check(any("check.py" in l for l, _ in runnables), "a --self-test module is collected")
    s.check("adapters/testkit.py" in covered, "COVERS is honoured over the name convention")

    # WHERE THE CHECKOUT SITS IS NOT THIS REPOSITORY'S BUSINESS. The hidden-directory rule read the
    # ABSOLUTE path, so a checkout under `.claude/worktrees/agent-*` had a dot in every path it
    # owned and discovered none of its own files: 0 suites, "0 passed, 0 failed", exit 0. The three
    # assertions above are the ones that would have caught it and they live in a file that was
    # thrown away first, which is why the rule is pinned here directly (§14b).
    with tempfile.TemporaryDirectory() as tmp:
        at = pathlib.Path(tmp) / ".hidden" / "wt"
        (at / "adapters").mkdir(parents=True)
        (at / "adapters" / "thing.py").write_text("def f():\n    return 1\n")
        # The counter-case, and the case the rule was written for: a dot-directory INSIDE the
        # checkout is still somebody's working space and is still skipped.
        (at / ".tmp-c2").mkdir()
        (at / ".tmp-c2" / "q.py").write_text("x = 1\n")
        real, t.ROOT = t.ROOT, at
        try:
            found = {str(p.relative_to(at)) for p in t.modules()}
        finally:
            t.ROOT = real
        s.check("adapters/thing.py" in found,
                "a checkout under a dot-directory still discovers its own modules")
        s.check(".tmp-c2/q.py" not in found,
                "and a dot-directory inside the checkout is still skipped")

    # AND A RUN OF NOTHING IS NOT A PASS. With discovery broken there was no signal at all: the
    # runner reported success having executed no suite, at pre-push and in both workflows.
    with tempfile.TemporaryDirectory() as tmp:
        copy = pathlib.Path(tmp) / "test.py"
        copy.write_text((ROOT / "test.py").read_text())
        r = subprocess.run([sys.executable, str(copy), "--list"], capture_output=True, text=True)
        s.ne(r.returncode, 0, "a runner that discovered no suite exits non-zero")
        s.check("Discovery is broken" in (r.stdout + r.stderr),
                "and says the runner is broken rather than that everything passed")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "harness"))
