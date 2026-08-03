#!/usr/bin/env python3
"""Run every test in the repository, offline, and report which modules have none.

  ./test.py              run everything
  ./test.py --canary     prove every suite is capable of failing
  ./test.py --untested   list modules with no test, and print the count check.py budgets
  ./test.py --list       show what would run

DISCOVERY, NOT A LIST. CI used to name three test files, so a fourth would have sat unrun
indefinitely. Anything matching test_*.py, *_test.py or acceptance.py is collected, and so is any
module exposing --self-test. Adding a test cannot be forgotten because nothing has to be told.

OFFLINE IS ENFORCED, NOT REQUESTED. Every child runs with socket creation blocked. This is the
part that does the real work: a module you cannot test without a network has not separated its pure
logic from its I/O, so the guard turns "well factored" from a judgement somebody makes into a
condition the machine checks. Tests that need fixtures keep them in the repository.

WHY A SUBPROCESS PER TEST. The guard has to be installed before the module under test imports
anything, sys.modules must not leak between suites, and a test that segfaults or hangs must not
take the run with it. A process boundary gives all three.
"""
import argparse
import concurrent.futures
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
SKIP_DIRS = {".git", "data", "__pycache__", ".github", "node_modules"}

# Installed into every child before the test imports anything. Blocking at socket creation catches
# urllib, http.client and anything else, without needing to know which the module uses.
GUARD = """
import socket as _s

class Offline(Exception):
    pass

def _refuse(*a, **k):
    raise Offline(
        "this test tried to reach the network. Tests run offline: separate the fetch from the "
        "logic and test the logic, or add a fixture under data/fixtures/.")

# Block CONNECTING, not the socket type. An earlier version replaced socket.socket with a function
# and broke `import ssl`, which does `class SSLSocket(socket)`: the guard took down the import
# machinery instead of the network, and three suites failed for a reason that had nothing to do
# with them. Creating a socket is harmless; using one is what tests may not do.
_s.socket.connect = _refuse
_s.socket.connect_ex = _refuse
_s.create_connection = _refuse
_s.socket.sendto = _refuse
"""


def modules():
    for p in sorted(ROOT.rglob("*.py")):
        if SKIP_DIRS & set(p.parts) or p.name == "test.py":
            continue
        yield p


def is_test(p):
    return (p.name.startswith("test_") or p.name.endswith("_test.py")
            or p.name == "acceptance.py")


def has_self_test(p):
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return "--self-test" in t or "def _self_test" in t


def subjects(p):
    """Which modules a test file is taken to cover.

    A test names its subjects in a `COVERS = [...]` list. Without one, a file called test_foo.py is
    taken to cover foo.py beside it. Explicit beats inferred, because several tests here exercise a
    module that is not their namesake.
    """
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return set()
    m = re.search(r"^COVERS\s*=\s*\[(.*?)\]", t, re.S | re.M)
    if m:
        return {s.strip().strip("'\"") for s in m.group(1).split(",") if s.strip().strip("'\"")}
    stem = re.sub(r"^test_|_test$", "", p.stem)
    sib = p.parent / f"{stem}.py"
    return {str(sib.relative_to(ROOT))} if sib.exists() else set()


def collect():
    """Return (runnables, covered) where runnables are (label, argv) and covered is a path set."""
    runnables, covered = [], set()
    for p in modules():
        rel = str(p.relative_to(ROOT))
        if is_test(p):
            runnables.append((rel, [sys.executable, str(p)]))
            covered |= subjects(p)
            covered.add(rel)                      # a test file is covered by being run
        elif has_self_test(p):
            runnables.append((f"{rel} --self-test", [sys.executable, str(p), "--self-test"]))
            covered.add(rel)
    return runnables, covered


def run_one(label, argv, canary, timeout=300):
    env = dict(os.environ)
    env["PYTHONSTARTUP"] = ""
    if canary:
        env["YURA_CANARY"] = "1"
    # -c installs the guard, then execs the target with its own __name__ == "__main__".
    # Running a script normally puts ITS OWN directory on sys.path, and several tests here rely on
    # that to import a sibling. runpy does not, so the entry is restored explicitly; without it
    # test_crossplatform.py failed on `from crossplatform import ...` for reasons of harness
    # plumbing rather than anything about the code under test.
    target = pathlib.Path(argv[1]).resolve()
    boot = GUARD + (
        "import runpy, sys\n"
        f"sys.path.insert(0, {str(target.parent)!r})\n"
        f"sys.argv = {argv[1:]!r}\n"
        f"runpy.run_path({str(target)!r}, run_name='__main__')\n")
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "-c", boot], capture_output=True, text=True,
                           cwd=ROOT, env=env, timeout=timeout)
        return label, r.returncode, round(time.time() - t0, 1), r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return label, 124, timeout, "", f"timed out after {timeout}s"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canary", action="store_true", help="prove each suite can fail")
    ap.add_argument("--untested", action="store_true", help="list modules with no test")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="print the untested count only")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    runnables, covered = collect()
    allmods = {str(p.relative_to(ROOT)) for p in modules()}
    untested = sorted(allmods - covered)

    if a.untested or a.quiet:
        if a.quiet:
            print(len(untested))
        else:
            print(f"{len(untested)} of {len(allmods)} modules have no test\n")
            for m in untested:
                print(f"   {m}")
        return 0

    if a.list:
        for label, _ in runnables:
            print(f"   {label}")
        print(f"\n{len(runnables)} runnable, {len(untested)} modules untested")
        return 0

    print(f"{len(runnables)} suite(s), offline" + (", inverted (canary)" if a.canary else ""))
    bad, vacuous, unproven = [], [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        futs = [pool.submit(run_one, l, v, a.canary) for l, v in runnables]
        for f in concurrent.futures.as_completed(futs):
            label, rc, secs, out, err = f.result()
            # Whole output, unfiltered, on stdout. Filtering build output has swallowed a traceback
            # three times in this project (STANDING-INSTRUCTIONS §1).
            body = (out + err).rstrip()
            if rc == 0 and a.canary and "CANARY-PROVEN" not in body:
                # It passed while inverted, which means inversion never reached it. A suite that
                # ignores the canary is not thereby proven; saying so is the whole point.
                unproven.append(label)
                print(f"  ?    {label}  {secs}s  (not canary-aware)")
            elif rc == 0:
                print(f"  ok   {label}  {secs}s")
            elif rc == 2:
                vacuous.append(label)
                print(f"  VAC  {label}  {secs}s")
            else:
                bad.append(label)
                print(f"  FAIL {label}  rc={rc}  {secs}s")
            if body and rc != 0:
                print("\n".join(f"         {l}" for l in body.splitlines()))

    print(f"\n{len(runnables) - len(bad) - len(vacuous) - len(unproven)} passed, {len(bad)} failed, "
          f"{len(vacuous)} vacuous, {len(unproven)} unproven; {len(untested)} module(s) untested")
    if bad:
        print("failed: " + ", ".join(sorted(bad)))
    if vacuous:
        print("vacuous (asserts nothing that can fail): " + ", ".join(sorted(vacuous)))
    if unproven:
        print("not canary-aware (passed inversion untouched, so unproven): "
              + ", ".join(sorted(unproven)))
    # Unproven is a gap to close, not a failure to block on: the four --self-test modules plant
    # their own canaries internally and are proven by construction, they just do not say so in
    # this harness's words. Migrating them is tracked by the count.
    return 1 if (bad or vacuous) else 0


if __name__ == "__main__":
    sys.exit(main())
