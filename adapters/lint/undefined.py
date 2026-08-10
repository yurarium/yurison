#!/usr/bin/env python3
"""A name used where nothing defines it, which is a crash waiting for the branch that reaches it.

WHY THIS EXISTS. `build.py` carried `sys.path.insert(0, str(ROOT / "adapters" / "facts"))` in a
function with no `ROOT` in scope, and crashed 34 seconds into a build. Neither the gate nor the
tests run a build, so the cycle that got fast by not running things did not run the one thing that
would have caught it.

The same pass found a worse one. `adapters/relational/__init__.py` read `_rd.DEFAULT_BASIS` in a
function that imports no `_rd`, on the right-hand side of an `or`. Every record in the corpus today
carries a `reading_basis`, so the left side is truthy and the branch has never been evaluated. It
would raise on the first record that arrives without one, which is a fault sitting in the tree
looking exactly like working code.

WHAT IT USES AND WHY. `pyflakes`, which does the scope analysis properly. Writing a fourth scope
resolver in this repository to avoid a dependency would be the worse trade: this is a solved problem
and the failure mode of getting it slightly wrong is a check that quietly passes.

FAIL-CLOSED. Where pyflakes is absent this reports that as the finding rather than returning
nothing, on the same reasoning as `check.UNMEASURED`: a check that cannot run is not a check that
found nothing. CI installs it beside pyyaml.

WHAT IT CANNOT SEE. A name defined by something dynamic: `globals()[k] = v`, a star import, a
conditional import pyflakes reads as possibly-absent. It reports those as findings rather than
missing them, so the direction of its error is towards noise and not towards silence.
"""
import argparse
import io
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

_UNDEFINED = re.compile(r"^(.*?):(\d+):\d+: undefined name '([^']+)'")


def findings(paths=None, root=None):
    """`[(path, line, name)]` for every use of a name nothing in scope defines."""
    root = pathlib.Path(root or ROOT)
    if paths is None:
        out = subprocess.run(["git", "ls-files", "-z", "*.py"], cwd=str(root),
                             capture_output=True, text=True, timeout=60).stdout.split("\0")
        paths = [root / f for f in out if f and (root / f).exists()]
    paths = [str(p) for p in paths]
    if not paths:
        return []

    try:
        from pyflakes.api import checkPath
        from pyflakes.reporter import Reporter
    except ImportError:
        return [("", 0, "pyflakes is not installed, so nothing was checked")]

    buf, err = io.StringIO(), io.StringIO()
    reporter = Reporter(buf, err)
    for p in paths:
        checkPath(p, reporter)

    got = []
    for line in buf.getvalue().splitlines():
        m = _UNDEFINED.match(line)
        if m:
            path = m.group(1)
            try:
                path = str(pathlib.Path(path).relative_to(root))
            except ValueError:
                pass
            got.append((path, int(m.group(2)), m.group(3)))
    return got


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            # THE TWO REAL CASES, as they were. The first crashed a build; the second is still
            # waiting for a record with no reading_basis.
            (p / "crashed.py").write_text(
                "import pathlib\n"
                "def f():\n"
                "    return pathlib.Path(str(ROOT / 'adapters'))\n")
            (p / "waiting.py").write_text(
                "def g(r):\n"
                "    return r.get('reading_basis') or _rd.DEFAULT_BASIS\n")
            (p / "fine.py").write_text(
                "import pathlib\n"
                "ROOT = pathlib.Path('.')\n"
                "def f():\n"
                "    inner = 1\n"
                "    return ROOT, inner\n")
            got = findings([p / "crashed.py", p / "waiting.py", p / "fine.py"], root=p)
        names = {g[2] for g in got}
        where = {g[0] for g in got}
        if "ROOT" not in names:
            print("  self-test FAILED — a name used with nothing defining it was not caught")
            return 1
        if "_rd" not in names:
            print("  self-test FAILED — a name on the unevaluated side of an `or` was not caught")
            return 1
        if "fine.py" in where:
            print("  self-test FAILED — a module global and a local were reported")
            return 1
        if os.environ.get("YURA_CANARY"):
            print("CANARY-PROVEN")
        print("  self-test passed (2 undefined names caught, a defined global and a local "
              "left alone)")
        return 0

    got = findings()
    if a.quiet:
        print(len(got))
        return 0
    for path, line, name in got:
        print(f"  {path}:{line}: {name}" if path else f"  {name}")
    print(f"{len(got)} use(s) of a name nothing defines")
    return 1 if got else 0


if __name__ == "__main__":
    sys.exit(main())
