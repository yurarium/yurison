#!/usr/bin/env python3
"""The week in one issue: how the runs went, what keeps failing, what moved, what it cost.

WHY THIS EXISTS. The owner asked on 2026-10-15 for a weekly digest beside the per-source issues and
the status page. A per-source issue reaches somebody when one thing breaks; this is for what no
single issue says: how many runs there were, which sources wobbled and recovered, which budgets
moved and by how much, and how much of the subscription the naming job used.

`compose` builds the text from what the repository already records and is tested. `main` gathers
those records with git and the ledger files, and the workflow posts the result.

    digest.py --since 2026-10-08 > digest.md
"""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys

import yaml

HEALTH = pathlib.Path("data/ledger/source-health.yaml")
USAGE = pathlib.Path("data/ledger/claude-usage.jsonl")
ARRIVALS = pathlib.Path("data/ledger/budget-arrivals.jsonl")
BUDGETS = "docs/budgets.json"


def budget_moves(before, after):
    """`[(name, was, now)]` for every budget whose value changed, largest move first."""
    out = []
    for k in sorted(set(before) | set(after)):
        a, b = before.get(k), after.get(k)
        if a != b:
            out.append((k, a, b))
    return sorted(out, key=lambda x: -abs((x[2] or 0) - (x[1] or 0))
                  if isinstance(x[1], (int, float)) and isinstance(x[2], (int, float)) else 0)


def over(db_path):
    """`[(name, measured, recorded)]` for every budget the published store measured above its
    recorded value, largest excess first.

    WHY THE DIGEST ASKS. A data budget that rises does not block anything (`check.py
    --data-advisory`): the count moved because the world did, and accepting it is a person's
    decision. Until 2026-10-15 a person ran the gate every day and saw each rise; unattended, a rise
    is printed in a run log nobody opens. The store keeps what every run measured, so the digest
    reads it and a count left over its ceiling is in front of somebody once a week.
    """
    if not db_path or not pathlib.Path(db_path).exists():
        return []
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import relational
    try:
        rows = relational.open_db(db_path).execute(
            "SELECT name, value, budget, measure FROM check_result WHERE kind = 'budget'").fetchall()
    except Exception:                                                       # noqa: BLE001
        return []
    return rows


def exceeding(rows, measures=("regression", "source", None)):
    """The `(name, value, budget)` rows above their budget whose measure is one of `measures`,
    largest excess first.

    A REGRESSION IS WHAT A PERSON IS ASKED ABOUT. An arrival over its value is the corpus growing
    since the last gate accepted it, listed apart; a report has no ceiling to be over. A row from
    a store written before `measure` existed counts as a regression, which is what every budget
    was then.
    """
    rows = [r for r in rows if r[1] is not None and r[2] is not None and r[1] > r[2]
            and (r[3] if len(r) > 3 else None) in measures]
    return sorted([tuple(r[:3]) for r in rows], key=lambda r: (-(r[1] - r[2]), r[0]))


def compose(since, until, runs, health, moves, usage, above=(), grown=(), accepted=()):
    """The digest's markdown."""
    sources = (health or {}).get("sources") or {}
    down = {k: v for k, v in sources.items() if int(v.get("consecutive") or 0) > 0}
    wobbled = {k: v for k, v in sources.items()
               if not v.get("consecutive") and str(v.get("last_failed") or "") >= since}
    L = [f"# Week of {since} to {until}", ""]
    L += ["## Runs", "",
          f"{runs} update run(s) committed data this week."
          + (" None did, so the schedule or the workflow needs a look." if not runs else ""), ""]
    L += ["## Sources", ""]
    if down:
        L.append("Failing now:")
        for k, v in sorted(down.items(), key=lambda kv: -int(kv[1].get("consecutive") or 0)):
            L.append(f"- `{k}`: {v.get('consecutive')} run(s) in a row since "
                     f"{v.get('failing_since')}. {v.get('error') or ''}".rstrip())
    else:
        L.append("Every source worked on its latest run.")
    if wobbled:
        L += ["", "Failed this week and recovered:"]
        L += [f"- `{k}`, last failed {v.get('last_failed')}" for k, v in sorted(wobbled.items())]
    L += ["", "## Budgets", ""]
    if moves:
        L += [f"- `{k}`: {a} to {b}" for k, a, b in moves[:30]]
        if len(moves) > 30:
            L.append(f"- and {len(moves) - 30} more")
    else:
        L.append("No budget moved.")
    if above:
        L += ["", "Over their recorded value in the latest store, so somebody should look at why "
              "and accept or fix each:"]
        L += [f"- `{k}`: {v} against {b}" for k, v, b in above]
    if grown:
        L += ["", "Queues the corpus grows, above the value last accepted, which the next gate "
              "accepts with a reason:"]
        L += [f"- `{k}`: {v} against {b}" for k, v, b in grown]
    if accepted:
        L += ["", f"{len(accepted)} rise(s) accepted as arrivals this week "
              "(data/ledger/budget-arrivals.jsonl):"]
        L += [f"- {x.get('date')}: {x.get('reason')}" for x in accepted[-15:]]
    L += ["", "## Naming job", ""]
    if usage:
        turns = sum(int(u.get("turns") or 0) for u in usage)
        tin = sum(int(u.get("input_tokens") or 0) for u in usage)
        tout = sum(int(u.get("output_tokens") or 0) for u in usage)
        done = sum(int(u.get("named") or 0) for u in usage)
        minted = sum(int(u.get("inducted") or 0) for u in usage)
        cached = sum(int(u.get("cache_read_tokens") or 0) for u in usage)
        looked = sum(int(u.get("reviewed") or 0) for u in usage)
        L.append(f"{len(usage)} session(s), {turns} turns, {tin:,} input and {tout:,} output "
                 f"tokens; {done} name(s) written, {looked} one-shot verdict(s) recorded and "
                 f"{minted} work(s) inducted.")
        if cached:
            L.append(f"Of the input, {cached:,} tokens were cache reads.")
    else:
        L.append("No runs recorded.")
    return "\n".join(L) + "\n"


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    today = datetime.date.today()
    ap.add_argument("--since", default=(today - datetime.timedelta(days=7)).isoformat())
    ap.add_argument("--store", default=None, help="the published store, for budgets over their value")
    a = ap.parse_args(argv)

    runs = len([l for l in _git("log", f"--since={a.since}", "--format=%s").splitlines()
                if l.startswith("update: run")])
    health = yaml.safe_load(HEALTH.read_text(encoding="utf-8")) if HEALTH.exists() else {}
    base = _git("rev-list", "-1", f"--before={a.since}", "HEAD").strip()
    before = json.loads(_git("show", f"{base}:{BUDGETS}") or "{}") if base else {}
    after = json.loads(pathlib.Path(BUDGETS).read_text(encoding="utf-8"))
    accepted = []
    if ARRIVALS.exists():
        for line in ARRIVALS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                x = json.loads(line)
                if str(x.get("date") or "") >= a.since:
                    accepted.append(x)
    rows = over(a.store) if a.store else []
    usage = []
    if USAGE.exists():
        for line in USAGE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                u = json.loads(line)
                if str(u.get("date") or "") >= a.since:
                    usage.append(u)
    sys.stdout.write(compose(a.since, today.isoformat(), runs, health,
                             budget_moves(before, after), usage,
                             exceeding(rows), exceeding(rows, ("arrival",)), accepted))
    return 0


if __name__ == "__main__":
    sys.exit(main())
