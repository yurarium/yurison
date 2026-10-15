#!/usr/bin/env python3
"""Which sources failed this run, which keep failing, and the issues that say so.

WHY THIS EXISTS. An update went red whenever one adapter failed, and the owner ruled on 2026-10-15
that this is the wrong signal: a run should succeed whenever it could do its work, and a source
that is down for a day is an outcome to record, not a failure to email about. What was missing was
the record. A source that failed once and recovered and a source dead for a fortnight looked the
same, a warning in one run's log, so neither reached anybody.

WHAT IT KEEPS. `data/ledger/source-health.yaml` holds, per source, when it last worked, when it
last failed, how many runs in a row it has failed and the last error. Every stage writes its
outcomes to one report through `run_stage.py --report`, and checks that are not stages (the field
audit, the self-test) add theirs with `--outcome`.

WHAT IT RAISES. A source failing `THRESHOLD` runs in a row gets one GitHub issue, labelled
`source-health`, updated each run while it stays down and closed when it recovers. One email per
new problem rather than one per run. `plan` is the decision and is tested; `sync` applies it with
`gh` and is the only part that touches the network.

    runhealth.py record --report R.json [--outcome id=ok|fail:message ...] --date D [--run URL]
    runhealth.py plan                  # the issue actions, as JSON, against the open issues
    runhealth.py sync                  # apply them with gh
"""
import argparse
import json
import pathlib
import subprocess
import sys

import yaml

LEDGER = pathlib.Path("data/ledger/source-health.yaml")
#: RUNS IN A ROW BEFORE A SOURCE IS AN ISSUE. Twice-daily runs make three about a day and a half,
#: long enough that a host's bad morning passes unreported and short enough that a changed page is
#: in front of somebody before a week of a platform's updates is missed.
THRESHOLD = 3
LABEL = "source-health"
TITLE = "Source failing: {id}"


def load(path=LEDGER):
    p = pathlib.Path(path)
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def record(ledger, outcomes, date, run=None):
    """The ledger with this run's outcomes folded in. A source not run this time is left as it was."""
    sources = dict((ledger or {}).get("sources") or {})
    for o in outcomes:
        cur = dict(sources.get(o["id"]) or {})
        cur["stage"] = o.get("stage") or cur.get("stage")
        if o.get("ok"):
            cur.update(last_ok=date, consecutive=0, failing_since=None, error=None)
        else:
            cur["consecutive"] = int(cur.get("consecutive") or 0) + 1
            cur["last_failed"] = date
            cur["failing_since"] = cur.get("failing_since") or date
            cur["error"] = (o.get("error") or "").strip()[:300] or "no message"
            if run:
                cur["last_run"] = run
        sources[o["id"]] = {k: v for k, v in cur.items() if v is not None}
    return {"updated": date, "sources": dict(sorted(sources.items()))}


def failing(ledger, threshold=THRESHOLD):
    """`{source: entry}` for every source failing at least `threshold` runs in a row."""
    return {k: v for k, v in ((ledger or {}).get("sources") or {}).items()
            if int(v.get("consecutive") or 0) >= threshold}


def body(sid, e):
    """The issue text: what failed, since when, and where to look."""
    lines = [f"`{sid}` ({e.get('stage') or 'unknown stage'}) has failed "
             f"{e.get('consecutive')} update runs in a row, since {e.get('failing_since')}.",
             "", f"Last error: `{e.get('error') or 'no message'}`"]
    if e.get("last_ok"):
        lines += ["", f"Last worked: {e['last_ok']}. Its last good capture is still published."]
    else:
        lines += ["", "It has not worked since this ledger began."]
    if e.get("last_run"):
        lines += ["", f"Latest failing run: {e['last_run']}"]
    lines += ["", "This issue updates each run and closes itself when the source recovers. "
                  "A code change is a session's job: see docs/LAUNCH-PLAN.md section 6."]
    return "\n".join(lines)


def plan(ledger, open_issues, threshold=THRESHOLD):
    """The actions that make the open issues match the ledger.

    `open_issues` is `{title: number}` for the open `source-health` issues. A failing source with no
    issue gets one opened; one that has an issue gets it updated; an issue whose source is no longer
    failing is closed.
    """
    down = failing(ledger, threshold)
    want = {TITLE.format(id=k): (k, v) for k, v in down.items()}
    out = []
    for title, (sid, e) in sorted(want.items()):
        if title in open_issues:
            out.append({"action": "update", "number": open_issues[title], "title": title,
                        "body": body(sid, e)})
        else:
            out.append({"action": "open", "title": title, "body": body(sid, e)})
    for title, number in sorted(open_issues.items()):
        if title not in want:
            out.append({"action": "close", "number": number, "title": title,
                        "body": "Recovered: it has worked again since this issue was opened."})
    return out


def _parse_outcome(s):
    """`id=ok` or `id=fail:message`."""
    sid, _, rest = s.partition("=")
    ok = rest == "ok"
    return {"id": sid, "ok": ok, "error": "" if ok else rest.partition(":")[2],
            "stage": "checks"}


def _gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def open_issues_now():
    got = json.loads(_gh("issue", "list", "--label", LABEL, "--state", "open",
                         "--json", "number,title", "--limit", "200") or "[]")
    return {i["title"]: i["number"] for i in got}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--report", nargs="*", default=[])
    r.add_argument("--outcome", nargs="*", default=[])
    r.add_argument("--date", required=True)
    r.add_argument("--run", default=None)
    sub.add_parser("plan")
    sub.add_parser("sync")
    a = ap.parse_args(argv)

    if a.cmd == "record":
        outcomes = []
        for f in a.report:
            p = pathlib.Path(f)
            if p.exists():
                outcomes += json.loads(p.read_text(encoding="utf-8"))
        outcomes += [_parse_outcome(x) for x in a.outcome]
        led = record(load(), outcomes, a.date, a.run)
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text("# Written by adapters/runhealth.py each run; see its docstring.\n"
                          + yaml.safe_dump(led, allow_unicode=True, sort_keys=False, width=200),
                          encoding="utf-8")
        bad = [o["id"] for o in outcomes if not o.get("ok")]
        print(f"{len(outcomes)} outcome(s) recorded, {len(bad)} failed"
              + (f": {', '.join(sorted(bad))}" if bad else ""))
        for k, v in failing(led).items():
            print(f"  {k}: {v['consecutive']} runs in a row since {v['failing_since']}")
        return 0
    actions = plan(load(), open_issues_now())
    if a.cmd == "plan":
        print(json.dumps(actions, ensure_ascii=False, indent=1))
        return 0
    try:
        _gh("label", "create", LABEL, "--color", "D93F0B",
            "--description", "a source failing several update runs in a row")
    except subprocess.CalledProcessError:
        pass                                    # it exists already
    for x in actions:
        if x["action"] == "open":
            _gh("issue", "create", "--title", x["title"], "--body", x["body"], "--label", LABEL)
        elif x["action"] == "update":
            _gh("issue", "edit", str(x["number"]), "--body", x["body"])
        else:
            _gh("issue", "close", str(x["number"]), "--comment", x["body"])
        print(f"  {x['action']:6} {x['title']}")
    print(f"{len(actions)} issue action(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
