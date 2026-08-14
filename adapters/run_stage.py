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
    return (cmd["id"], r.returncode, round(time.time() - t0),
            _both_ends(r.stdout), _both_ends(r.stderr))


def _both_ends(s, keep=1500):
    """The output, or its two ends with a line saying what was dropped between them.

    THE TAIL ALONE HID THE START OF EVERY CHATTY ADAPTER. This kept the last 1,500 characters while
    the comment below claimed the output was printed whole, so `gigaviewer-platform-feeds` began
    mid-sentence and a reader could not tell that from an adapter that starts abruptly. A traceback's
    CAUSE is at the top and its type is at the bottom, so keeping one end is the wrong half half the
    time; this keeps both and says how much is missing.
    """
    s = s or ""
    if len(s) <= keep * 2:
        return s
    dropped = len(s) - keep * 2
    return f"{s[:keep]}\n… {dropped} character(s) dropped from the middle …\n{s[-keep:]}"


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
        # SAID WHERE A RUNNER WILL SHOW IT. A failing adapter that only appears halfway down a log
        # is a failing adapter nobody reads about, and every command in this manifest is optional,
        # so the step itself goes green.
        for c in sorted(failed):
            print(f"::warning title=adapter failed::{c} wrote nothing this run")
    # AN ADAPTER FAILING MUST NOT COST THE NIGHT AND MUST NOT BE SILENT, which are different
    # things and were confused here. `optional` stops a failure from ending the RUN, and the
    # workflow's `continue-on-error` is what carries the night's data to the compile and the
    # publish; what this returns is whether anything failed AT ALL, so the step goes red and the
    # job's last step can fail it after the data is out. The comment in `update.yml` has described
    # this behaviour since it was written, while every command in the manifest was marked optional
    # and nothing could ever return 1.
    if required_failed:
        print(f"REQUIRED command(s) failed: {', '.join(required_failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
