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
import ast
import concurrent.futures
import json
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
        "logic and test the logic, or capture the page it wanted. "
        "adapters/fixtures.py capture <name> --url <url> --cached-as <dir/entry> --keep <anchor> "
        "cuts a real page down into data/fixtures/ and records where it came from.")

# Block CONNECTING, not the socket type. An earlier version replaced socket.socket with a function
# and broke `import ssl`, which does `class SSLSocket(socket)`: the guard took down the import
# machinery instead of the network, and three suites failed for a reason that had nothing to do
# with them. Creating a socket is harmless; using one is what tests may not do.
_s.socket.connect = _refuse
_s.socket.connect_ex = _refuse
_s.create_connection = _refuse
_s.socket.sendto = _refuse
"""


def has_code(p):
    """Whether there is anything in the file to test.

    A package marker is empty by design and an __init__.py that only re-exports has no behaviour of
    its own. Counting those as untested would leave a number that can never reach zero, and a
    target nobody can hit is a target everyone stops looking at. Anything with a def, a class or a
    statement counts.
    """
    try:
        tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return True                      # unparseable is a problem, not an exemption
    return any(not isinstance(n, (ast.Import, ast.ImportFrom, ast.Expr))
               or (isinstance(n, ast.Expr) and not isinstance(n.value, ast.Constant))
               for n in tree.body)


def modules():
    for p in sorted(ROOT.rglob("*.py")):
        # A hidden directory is somebody's working space, not part of the project. An agent left
        # .tmp-c2/q.py in the tree mid-run and it counted as an untested module, which failed a
        # budget over a file nobody had written for this repository.
        if (SKIP_DIRS & set(p.parts) or p.name == "test.py"
                or any(part.startswith(".") and part not in (".", "..") for part in p.parts)):
            continue
        if not has_code(p):
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
    # A MENTION IS NOT A DECLARATION. `adapters/facts/division/checks.py` carries the words
    # `--self-test` inside a docstring explaining another module, and was discovered as a suite that
    # then could not be inverted, so it counted as unproven forever. A module HAS a self-test when
    # it accepts the flag.
    return ('add_argument("--self-test"' in t or "add_argument('--self-test'" in t
            or '"--self-test" in sys.argv' in t or "def _self_test" in t)


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


#: What a suite passing is remembered against. `data/cache` is outside `data/build`, which the
#: green-tree token hashes, so writing this during a run cannot invalidate that token.
PASSED = ROOT / "data" / "cache" / "tests.json"


def freshness(runnables):
    """`{label: digest}` over each suite's own file and everything it says it covers.

    A SUITE IS SKIPPED ONLY WHEN EVERYTHING IT NAMES IS UNCHANGED, so the question is what it names.
    `COVERS` is the declaration and a namesake module is the fallback, both of which `subjects()`
    already answers. `testkit.py` and this file are in every key, because a change to the harness
    can change any verdict.

A FIXTURE IS PART OF THE SUBJECT. A parser test is a claim about a page somebody captured, so any
    `data/fixtures/...` path written in the suite goes into its key: editing the captured page and
    not the parser must still re-run the test.

    WHAT IT CANNOT SEE, and why `--canary` and `cycle.py --full` never use it: a suite that reads a
    data file or a module it does not name, or builds a fixture path out of pieces. Such a suite
    passes on a tree where its real subject moved, and the only cure is the full run. A suite that
    names NOTHING has no key here and is always run.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import filecache
    harness = [ROOT / "test.py", ROOT / "adapters" / "testkit.py"]
    got = {}
    for label, argv in runnables:
        own = pathlib.Path(argv[1])
        named = [ROOT / s for s in subjects(own)] if own.name.startswith("test_") else [own]
        if not named:
            continue
        try:
            text = own.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        # AND THE BUILD OUTPUT, for a suite that reads it. `check.py --self-test` plants its
        # canaries in the real context, so its verdict is a function of data/build as much as of
        # check.py; keyed on its own file alone it would be skipped after a rebuild that changed
        # what the canaries land in.
        if "data/build" in text or '"data" / "build"' in text:
            named += sorted(x for x in (ROOT / "data" / "build").rglob("*")
                            if x.is_file() and x.name != ".green-tree.json")
        for m in re.findall(r"data/fixtures/[\w./-]+", text):
            # A SUITE OFTEN NAMES THE DIRECTORY and reads whatever captures are in it, so a path
            # that is a directory expands to its files. Hashing the directory itself hashes nothing.
            at = ROOT / m
            named += sorted(x for x in at.rglob("*") if x.is_file()) if at.is_dir() else [at]
        got[label] = filecache.digest([own, *named, *harness])
    return got


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
    ap.add_argument("--changed", action="store_true",
                    help="run only suites whose own file or declared subjects have moved since "
                         "they last passed")
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

    keys, skipped = {}, []
    if a.changed and not a.canary:
        keys = freshness(runnables)
        held = {}
        if PASSED.exists():
            try:
                held = json.loads(PASSED.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                held = {}
        fresh = [(l, v) for l, v in runnables if keys.get(l) and held.get(l) == keys[l]]
        skipped = [l for l, _v in fresh]
        runnables = [(l, v) for l, v in runnables if l not in set(skipped)]

    print(f"{len(runnables)} suite(s), offline" + (", inverted (canary)" if a.canary else "")
          + (f"; {len(skipped)} unchanged since they last passed" if skipped else ""))
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

    if a.changed and not a.canary:
        # ONLY A SUITE THAT PASSED IS REMEMBERED. A failing one keeps its old key, so it is run
        # again next time even if nothing moved.
        held = {}
        if PASSED.exists():
            try:
                held = json.loads(PASSED.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                held = {}
        ran_bad = set(bad) | set(vacuous)
        for label, _v in runnables:
            if label not in ran_bad and keys.get(label):
                held[label] = keys[label]
        try:
            PASSED.parent.mkdir(parents=True, exist_ok=True)
            PASSED.write_text(json.dumps(held, indent=1), encoding="utf-8")
        except OSError:
            pass

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
