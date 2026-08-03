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
    cmds = spec["commands"]
    s.check(len(cmds) >= 10, "the manifest carries the stage")

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


if __name__ == "__main__":
    sys.exit(testkit.run(main, "run_stage"))
