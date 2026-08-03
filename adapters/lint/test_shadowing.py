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


if __name__ == "__main__":
    sys.exit(testkit.run(main, "shadowing"))
