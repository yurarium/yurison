#!/usr/bin/env python3
"""shadowing.py: names rebound so far apart the reuse is probably accidental.

The lint exists because two shipped bugs had this exact shape, one of which reported "302 works
have no content_tier" as 0 and shipped.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import shadowing


def _write(body):
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    f.write(body)
    f.close()
    return f.name


def main(s):
    # The real shape: a name bound early, rebound hundreds of lines later, first value still live.
    far = "def f():\n    works = []\n" + "    x = 1\n" * 400 + "    works = set()\n    return works\n"
    p = _write(far)
    try:
        found = shadowing.offenders(p, span=300)
        s.check(any(n == "works" for _, n, _, _, _ in found), "a distant rebinding is reported")
    finally:
        pathlib.Path(p).unlink(missing_ok=True)

    # The counter-case matters more. Rebinding a loop variable is idiomatic and must NOT fire, or
    # the lint gets switched off and the real hazard goes with it.
    near = "def f():\n    for r in a:\n        pass\n    for r in b:\n        pass\n"
    p = _write(near)
    try:
        s.eq(shadowing.offenders(p, span=300), [], "an adjacent rebinding is not reported")
    finally:
        pathlib.Path(p).unlink(missing_ok=True)

    # A nested function has its own scope, so its bindings are not the outer function's problem.
    nested = ("def f():\n    works = []\n" + "    x = 1\n" * 400 +
              "    def g():\n        works = 1\n        return works\n    return works\n")
    p = _write(nested)
    try:
        found = shadowing.offenders(p, span=300)
        s.check(not any(n == "works" and fn == "g" for fn, n, _, _, _ in found),
                "a nested def's own binding is not charged to the outer function")
    finally:
        pathlib.Path(p).unlink(missing_ok=True)

    # It must still work on the file it was written for.
    real = shadowing.offenders(str(pathlib.Path(__file__).resolve().parents[2] / "build.py"), 300)
    s.check(isinstance(real, list), "it runs on build.py without raising")

    # ── The same fault at module scope ──────────────────────────────────────────────────────────
    #
    # THE TREE THAT SHIPPED IT, rebuilt: a package called `store` that puts a sibling `names` on
    # the path, where a second `store.py` lives. A bare `import store` inside the package found the
    # other one, and nothing said so.
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "names").mkdir()
        (root / "store").mkdir()
        (root / "names" / "store.py").write_text("X = 1\n")
        (root / "store" / "__init__.py").write_text(
            'import sys, pathlib\n'
            'sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))\n'
            'sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n')
        got = dict(shadowing.collisions(root))
        s.check("store" in got, "two modules answering to `store` on one path are reported")

    # THE COUNTER-CASE IS THE WHOLE DESIGN. Thirteen platforms each hold a `releases.py` and that
    # is correct: a caller writes `gigaviewer.releases`, and a platform's own directory reaches the
    # path only while that platform runs. Reporting those would make the check a wall and the wall
    # would be switched off.
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        for platform in ("gigaviewer", "kadokomi"):
            (root / platform).mkdir()
            (root / platform / "releases.py").write_text("X = 1\n")
            (root / platform / "run.py").write_text(
                'import sys, pathlib\n'
                'sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n')
        s.eq(shadowing.collisions(root), [],
             "a per-platform module reached through its package is not a collision")

    # AND THE TREE AS IT STANDS, which is the claim the rename makes.
    s.eq(shadowing.collisions(), [], "no name in this tree is answered by two modules on one path")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "shadowing"))
