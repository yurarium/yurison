#!/usr/bin/env python3
"""Run a stage's adapters concurrently, one host apiece, and report what each did.

WHY THIS EXISTS. Stage A ran eleven adapter invocations strictly one after another, and each one
addresses a different publisher. Measured on the only CI run that completed the stage, it took
2,285 seconds, of which the great majority is `time.sleep`: every adapter pauses between its own
requests, and while it sleeps the other ten wait for it.

The pause is a courtesy owed to a SERVER. Two adapters reading different publishers have no reason
to queue behind each other, and each still walks its own host serially at its own rate, so no
publisher sees traffic any faster than before. The stage now takes as long as its slowest adapter
rather than the sum of all of them.

WHY NOT A GITHUB ACTIONS MATRIX. Eleven jobs would parallelise the same way and bill eleven
job-minutes, because Actions rounds every job up to a whole minute. One job with eleven concurrent
children bills once. With the schedule off and minutes metered, that decides it.

WHY A MANIFEST. The commands used to live inline in the workflow, where they could not be run by
hand in the form CI uses, and where a shell `|| true` hid which of them had failed. The manifest is
diffable, runnable locally, and names each command so the report can say which one broke.
"""
import argparse
import concurrent.futures
import pathlib
import subprocess
import sys
import time

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def expand(argv, subs):
    out = []
    for a in argv:
        for k, v in subs.items():
            a = a.replace("{" + k + "}", v)
        out.append(a)
    return out


def run_one(cmd, subs, dry=False):
    argv = [sys.executable] + expand(cmd["argv"], subs)
    if dry:
        return cmd["id"], 0, 0, " ".join(argv[1:]), ""
    t0 = time.time()
    r = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT)
    return cmd["id"], r.returncode, round(time.time() - t0), r.stdout[-1500:], r.stderr[-1500:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    spec = yaml.safe_load(pathlib.Path(a.manifest).read_text())
    cmds = [c for c in spec["commands"] if not a.only or c["id"] in a.only]
    subs = {"R": a.retrieved, "CACHE": a.cache}

    t0 = time.time()
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        futs = {pool.submit(run_one, c, subs, a.dry_run): c for c in cmds}
        for f in concurrent.futures.as_completed(futs):
            cid, rc, secs, out, err = f.result()
            rows.append((cid, rc, secs))
            print(f"  {'ok  ' if rc == 0 else 'FAIL'} {cid:26} {secs:5}s", flush=True)
            # Output is printed WHOLE and unfiltered. Piping build output through grep has swallowed
            # a traceback three times in this project (STANDING-INSTRUCTIONS §1).
            if out.strip():
                print("\n".join(f"       | {l}" for l in out.strip().splitlines()), flush=True)
            # To STDOUT, not stderr. A CI log, a background capture or a pipe routinely keeps
            # one stream and drops the other, and the whole point of this driver is that a failing
            # adapter is visible rather than swallowed. Writing the reason somewhere it can be
            # separated from its own heading is the same mistake in a new place.
            if rc != 0 and err.strip():
                print("\n".join(f"       ! {l}" for l in err.strip().splitlines()), flush=True)

    total = max(round(time.time() - t0), 1)
    serial = sum(s for _, _, s in rows)
    failed = [c for c, rc, _ in rows if rc != 0]
    required_failed = [c for c in failed
                       if not next(x for x in cmds if x["id"] == c).get("optional")]
    print(f"\n{len(rows)} commands in {total}s wall; {serial}s if run one after another "
          f"({serial / total:.1f}x)")
    if failed:
        print(f"failed ({len(failed)}): {', '.join(sorted(failed))}")
    # An optional adapter failing must not cost the run, which is what the shell `|| true` meant.
    # A required one failing must, or the stage reports success having fetched nothing.
    if required_failed:
        print(f"REQUIRED command(s) failed: {', '.join(required_failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
