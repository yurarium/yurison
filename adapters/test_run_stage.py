#!/usr/bin/env python3
"""run_stage.py and the Stage A manifest that drives it."""
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import run_stage

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main(s):
    # Substitution is what lets CI and a person run the same command with different roots.
    got = run_stage.expand(["a", "{CACHE}/giga", "--retrieved", "{R}"],
                           {"CACHE": "/c", "R": "2026-08-03"})
    s.eq(got, ["a", "/c/giga", "--retrieved", "2026-08-03"], "placeholders expand")
    s.eq(run_stage.expand(["plain"], {"R": "x"}), ["plain"], "text without a placeholder is left")

    spec = yaml.safe_load((ROOT / "adapters" / "stage-a.yaml").read_text())
    s.check(len(spec["commands"]) >= 10, "the manifest carries the stage")
    # EVERY STAGE MANIFEST, not only Stage A's: the rules below are what keep a failure named.
    cmds = [c for f in sorted((ROOT / "adapters").glob("stage-*.yaml"))
            for c in yaml.safe_load(f.read_text())["commands"]]

    ids = [c["id"] for c in cmds]
    s.eq(len(ids), len(set(ids)), "command ids are unique, so a failure names one command")

    for c in cmds:
        script = ROOT / c["argv"][0]
        s.check(script.exists(), f"{c['id']} points at a script that exists: {c['argv'][0]}")
        # Every adapter must be tolerated or the stage stops at the first flaky publisher. This is
        # the deliberate meaning of the old shell `|| true`, made explicit.
        s.check("optional" in c, f"{c['id']} states whether its failure may cost the run")

    # A cache placeholder is needed by anything that caches, or CI and local runs diverge silently.
    for c in cmds:
        if "--cache" in c["argv"]:
            i = c["argv"].index("--cache")
            s.check("{CACHE}" in c["argv"][i + 1], f"{c['id']} takes its cache root from the caller")


def outcomes(s):
    """A failing optional command is recorded and does not fail the stage; a required one does."""
    import json
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        (d / "ok.py").write_text("print('fine')\n")
        (d / "bad.py").write_text("import sys; print('the host said no'); sys.exit(2)\n")
        def run(required_bad):
            (d / "m.yaml").write_text(yaml.safe_dump({"sequential": True, "commands": [
                {"id": "fine", "optional": True, "argv": [str(d / "ok.py")]},
                {"id": "down", "optional": not required_bad, "argv": [str(d / "bad.py")]}]}))
            rep = d / "report.json"
            rep.unlink(missing_ok=True)
            rc = subprocess.run([sys.executable, str(ROOT / "adapters" / "run_stage.py"),
                                 str(d / "m.yaml"), "--retrieved", "2026-10-15", "--cache", str(d),
                                 "--report", str(rep)], capture_output=True, text=True).returncode
            return rc, json.loads(rep.read_text())
        rc, rep = run(False)
        s.eq(rc, 0, "an optional source failing is an outcome, so the stage succeeds")
        down = next(o for o in rep if o["id"] == "down")
        s.eq((down["ok"], down["error"], down["stage"]), (False, "the host said no", "m"),
             "and the report says which source failed, why, and in which stage")
        rc, _ = run(True)
        s.eq(rc, 1, "a required command failing fails the stage")

        # A WEEKLY COMMAND RUNS WHEN ITS LAST SUCCESS IS A WEEK OLD, OR HAS NEVER HAPPENED.
        led = d / "ledger.yaml"
        led.write_text(yaml.safe_dump({"sources": {"recent": {"last_ok": "2026-10-13"},
                                                   "stale": {"last_ok": "2026-10-01"}}}))
        cmds = [{"id": x, "every_days": 7} for x in ("recent", "stale", "never")] + [{"id": "each"}]
        s.eq([c["id"] for c in run_stage.due(cmds, "2026-10-15", str(led))],
             ["stale", "never", "each"], "a weekly command waits until it is due")


if __name__ == "__main__":
    sys.exit(testkit.run(lambda s: (main(s), outcomes(s)), "run_stage"))
