#!/usr/bin/env python3
"""Whether the naming job's work may be committed, and what it cost.

The job runs unattended (docs/LAUNCH-PLAN.md section 5), so what it leaves is judged by this rather
than by its own account of itself. Three questions, one subcommand each:

  files   Did it change only what it may? `data/identity/works.yaml`, `data/names/curated.yaml`
          and `data/queue/unheld-works.yaml`. Anything else is refused outright.
  gate    Did it make the gate worse? Compared with the gate taken before it started, because the
          update may already have left a budget over for reasons that are not the job's, and a
          job held to a clean gate would never commit on such a day.
  usage   What did it use? One line appended to `data/ledger/claude-usage.jsonl`, which the weekly
          digest totals: turns, tokens, time, model, and what it minted and named.

    verdict.py files
    verdict.py gate --before gate-before.txt --after gate-after.txt
    verdict.py usage --result result.json --run 123 --model sonnet --outcome committed
"""
import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

ALLOWED = ("data/identity/works.yaml", "data/names/curated.yaml", "data/queue/unheld-works.yaml")
LEDGER = pathlib.Path("data/ledger/claude-usage.jsonl")
FAIL = re.compile(r"^\s*FAIL\s+(.+?):\s")


def changed(cwd="."):
    """Every path the working tree differs in from HEAD, untracked files included."""
    out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=cwd,
                         capture_output=True, text=True, check=True).stdout
    return sorted({line[3:].split(" -> ")[-1] for line in out.splitlines() if line.strip()})


def disallowed(paths, allowed=ALLOWED):
    """The paths outside what the job may change."""
    return [p for p in paths if p not in allowed]


def failing(gate_text):
    """The names of the checks a gate report lists as failing."""
    return {m.group(1) for m in map(FAIL.match, gate_text.splitlines()) if m}


def worse(before, after):
    """Checks failing after the job that were not failing before it, sorted."""
    return sorted(failing(after) - failing(before))


def counts(diff_text):
    """`(inducted, named)` from a unified diff: identifiers added, curated keys added."""
    inducted = len(re.findall(r'^\+  - id: w\d+$', diff_text, re.M))
    named = len(re.findall(r'^\+  "[^"]+":$', diff_text, re.M))
    return inducted, named


def record(result, run, model, outcome, diff_text, today=None):
    """The ledger line for one run, from Claude Code's `--output-format json` result."""
    u = result.get("usage") or {}
    inducted, named = counts(diff_text)
    return {"date": today or datetime.date.today().isoformat(), "run": str(run), "model": model,
            "outcome": outcome, "turns": result.get("num_turns"),
            "input_tokens": (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0)
            + (u.get("cache_creation_input_tokens") or 0),
            "output_tokens": u.get("output_tokens") or 0,
            "duration_ms": result.get("duration_ms"), "inducted": inducted, "named": named,
            "error": bool(result.get("is_error"))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("files")
    g = sub.add_parser("gate")
    g.add_argument("--before", required=True)
    g.add_argument("--after", required=True)
    u = sub.add_parser("usage")
    u.add_argument("--result", required=True)
    u.add_argument("--run", required=True)
    u.add_argument("--model", required=True)
    u.add_argument("--outcome", required=True)
    u.add_argument("--diff", default=None, help="the job's diff; read from git when omitted")
    a = ap.parse_args(argv)

    if a.cmd == "files":
        bad = disallowed(changed())
        for p in bad:
            print(f"  not the job's to change: {p}")
        return 1 if bad else 0
    if a.cmd == "gate":
        new = worse(pathlib.Path(a.before).read_text(), pathlib.Path(a.after).read_text())
        for n in new:
            print(f"  newly failing: {n}")
        return 1 if new else 0
    rp = pathlib.Path(a.result)
    result = json.loads(rp.read_text()) if rp.exists() and rp.stat().st_size else {}
    diff = (pathlib.Path(a.diff).read_text() if a.diff else
            subprocess.run(["git", "diff", "--", *ALLOWED], capture_output=True, text=True).stdout)
    line = record(result, a.run, a.model, a.outcome, diff)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    print(json.dumps(line, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
