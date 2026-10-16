#!/usr/bin/env python3
"""Whether the naming job's work may be committed, and what it cost.

The job runs unattended (docs/LAUNCH-PLAN.md section 5), so what it leaves is judged by this rather
than by its own account of itself. Three questions, one subcommand each:

  snapshot  What already differs from HEAD before it starts, which the compile causes.
  files   Did it change only what it may, against that snapshot? `data/identity/works.yaml`, `data/names/curated.yaml`
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

#: The one file the job's answers are written into, by integrate.py. Claude itself writes nothing:
#: it runs in an empty directory with web tools alone, so this is the check on the script.
ALLOWED = ("data/names/curated.yaml",)
#: WHAT THE JUDGING REWRITES. `curate.py --apply` writes the name store and the build stamps
#: docs/tracker.html, and the gate lowers a budget whose count fell in docs/budgets.json, so their
#: output cannot count against the job.
REGENERATED = ("data/names/", "docs/tracker.html", "data/ledger/", "docs/budgets.json")
LEDGER = pathlib.Path("data/ledger/claude-usage.jsonl")
FAIL = re.compile(r"^\s*FAIL\s+(.+?):\s")


def changed(cwd="."):
    """Every path the working tree differs in from HEAD, untracked files included."""
    out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=cwd,
                         capture_output=True, text=True, check=True).stdout
    return sorted({line[3:].split(" -> ")[-1] for line in out.splitlines() if line.strip()})


def disallowed(paths, allowed=ALLOWED):
    """The paths outside what the job may change or the commands it runs regenerate."""
    return [p for p in paths if p not in allowed and not p.startswith(REGENERATED)]


def fold(lines):
    """One result from Claude Code's `stream-json` events: every turn and token summed.

    EVERY STRETCH OF THE SESSION, summed. The job runs builds in the background and Claude Code wakes
    again when each ends, so `--output-format json` reported the final wake alone: one turn and 1.6
    seconds for a session that wrote fifteen names. Each `result` event is one stretch of the
    session; the summary is the last one's text.
    """
    out = {"num_turns": 0, "duration_ms": 0, "is_error": False, "result": "",
           "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                     "cache_creation_input_tokens": 0}}
    for line in lines:
        try:
            e = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(e, dict) or e.get("type") != "result":
            continue
        out["num_turns"] += int(e.get("num_turns") or 0)
        out["duration_ms"] += int(e.get("duration_ms") or 0)
        out["is_error"] = out["is_error"] or bool(e.get("is_error"))
        out["result"] = e.get("result") or out["result"]
        # THE ANSWER ITSELF, where the job was started with `--json-schema`: the last stretch to
        # give one gave the job's answer, and integrate.py reads it from here.
        if e.get("structured_output") is not None:
            out["structured_output"] = e["structured_output"]
        for k in out["usage"]:
            out["usage"][k] += int((e.get("usage") or {}).get(k) or 0)
    return out


def snapshot(cwd="."):
    """`{path: digest}` for every path that differs from HEAD before the job starts.

    THE COMPILE BEFORE THE JOB WRITES FILES TOO. docs/tracker.html carries a timestamp, so the first
    run of the job, on 2026-10-16, was refused for changing it when Claude had changed nothing at
    all. The job is judged on what differs from this, not on what differs from HEAD.
    """
    import hashlib
    out = {}
    for path in changed(cwd):
        f = pathlib.Path(cwd) / path
        out[path] = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
    return out


def since(paths, baseline, cwd="."):
    """The paths whose content is not what the snapshot recorded before the job."""
    now = snapshot(cwd)
    return [p for p in paths if p not in baseline or now.get(p) != baseline.get(p)]


def failing(gate_text):
    """The names of the INVARIANTS a gate report lists as failing.

    BUDGETS ARE NOT THE JOB'S TO HOLD. A work it inducts arrives with credits and readings nobody
    has researched, and counts like `credit fields an identifier does not cover` rise with it, which
    is the arrival rather than a fault: a push is not blocked by them either (`--data-advisory`),
    and the weekly digest lists every budget left over its value. The job cannot change code, so a
    code budget cannot move under it. What it must not do is break an invariant.
    """
    section, out = None, set()
    for line in gate_text.splitlines():
        if line.startswith("invariants:"):
            section = "invariants"
        elif line.startswith("budgets"):
            section = "budgets"
        m = FAIL.match(line)
        if m and section == "invariants":
            out.add(m.group(1))
    return out


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
            # THE THREE PRICE DIFFERENTLY, and their sum hid which one a run spent: 2.5 million on
            # the first run was almost all cache reads of the same repository context, read again
            # on every turn. Kept apart so a run can be read for what it cost.
            "fresh_input_tokens": u.get("input_tokens") or 0,
            "cache_read_tokens": u.get("cache_read_input_tokens") or 0,
            "cache_write_tokens": u.get("cache_creation_input_tokens") or 0,
            "duration_ms": result.get("duration_ms"), "inducted": inducted, "named": named,
            "error": bool(result.get("is_error"))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("snapshot")
    fo = sub.add_parser("fold")
    fo.add_argument("--stream", required=True)
    fl = sub.add_parser("files")
    fl.add_argument("--baseline", default=None, help="a snapshot taken before the job")
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

    if a.cmd == "fold":
        src = pathlib.Path(a.stream)
        print(json.dumps(fold(src.read_text(encoding="utf-8").splitlines() if src.exists() else []),
                         ensure_ascii=False))
        return 0
    if a.cmd == "snapshot":
        print(json.dumps(snapshot(), ensure_ascii=False))
        return 0
    if a.cmd == "files":
        paths = changed()
        if a.baseline:
            paths = since(paths, json.loads(pathlib.Path(a.baseline).read_text()))
        bad = disallowed(paths)
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
