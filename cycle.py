#!/usr/bin/env python3
"""Run the gate and the tests at once, because neither reads what the other writes.

WHY THIS EXISTS. A cycle ran `./check.py --gate` and then `./test.py`, 52 s and then 30 s, on two
cores of a machine with more. They are independent: the gate reads `data/build` and the tests read
source and their own fixtures, offline. Nothing in either writes what the other reads.

AND THEY WERE BOTH PROVING THE SAME THING. `./test.py` runs `check.py --self-test` as one of its
suites, 16 s, and `--gate` runs the very same self-test before it will pass anything, 16 s again.
Two proofs of one property in one cycle. Here the tests carry it and the gate is told so, which is
only sound because THIS driver fails if the test half fails: `--proved-by` is not a way to skip the
proof, it is a statement that the proof is running in the other process and its verdict counts.

    ./cycle.py              gate and tests together
    ./cycle.py --full       both halves prove themselves, nothing is assumed, no token is honoured

`--full` is the path the scheduled CI run takes. It is slower on purpose: a cycle that only ever
runs the fast path has never checked that the fast path agrees with anything.
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent


#: Where a check keeps an answer it worked out before. `--full` moves this aside rather than
#: deleting it, so a scheduled run that disagrees with the incremental one leaves both to compare.
CACHE = ROOT / "data" / "cache"


def _run(name, cmd, out, env=None):
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    out[name] = (p.returncode, p.stdout, p.stderr, time.perf_counter() - t0)


def plan(full=False):
    """The two commands, as a pair, so a test can ask what `--full` changes without running them."""
    gate = [sys.executable, str(ROOT / "check.py"), "--gate"]
    tests = [sys.executable, str(ROOT / "test.py")]
    if not full:
        # THE TESTS CARRY THE PROOF and this process refuses to report success without them.
        gate += ["--proved-by", "tests"]
        # AND THEY RUN ONLY WHAT MOVED. `check.py --self-test` is keyed on check.py, on the harness
        # AND on data/build, because it plants its canaries in the real context; skipping it means
        # every one of those is byte for byte what it was when the canaries were last all caught.
        # That is the same claim the green-tree token makes, and `--full` refuses both.
        tests += ["--changed"]
    return {"gate": gate, "tests": tests}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true",
                    help="each half proves itself; no token, no assumption")
    a = ap.parse_args()

    cmds = plan(a.full)
    env = dict(os.environ)
    stashed = None
    if a.full:
        # NOTHING WORKED OUT EARLIER COUNTS. The token is refused, and the per-file cache is moved
        # aside rather than deleted so a disagreement between this run and the incremental one has
        # both answers still on disk to compare.
        env["YURA_NO_TOKEN"] = "1"
        if CACHE.is_dir():
            stashed = CACHE.with_name("cache.set-aside")
            if stashed.is_dir():
                shutil.rmtree(stashed)
            CACHE.rename(stashed)

    out = {}
    threads = [threading.Thread(target=_run, args=(n, c, out, env)) for n, c in cmds.items()]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - t0

    for name in ("tests", "gate"):
        code, so, se, secs = out[name]
        print(f"\n── {name}, {secs:.1f}s " + "─" * 60)
        print(so.rstrip())
        if se.strip():
            print(se.rstrip(), file=sys.stderr)

    if stashed is not None:
        print(f"cache-free run; the incremental cache is at {stashed.name} for comparison")

    failed = [n for n in out if out[n][0] != 0]
    serial = sum(out[n][3] for n in out)
    print(f"\n{wall:.1f}s together, {serial:.1f}s if they had run one after the other")
    if failed:
        print(f"NO GO: {', '.join(sorted(failed))} failed")
        return 1
    print("all right")
    return 0


if __name__ == "__main__":
    sys.exit(main())
