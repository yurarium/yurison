#!/usr/bin/env python3
"""Generate the refactor tracker from the repository, so it cannot say more than is true.

WHY THIS IS A PROGRAM. The first round's tracker was hand-edited and it was wrong twice: a step was
marked done that had never been done, and a stage stayed "in progress" after its steps were
complete. Both were caught by the project owner reading the page, which is the wrong reader for
that fault. A hand-kept status is a second producer of "what is done".

WHAT IS DERIVED AND WHAT IS TYPED. Everything a machine can measure, it measures: the timings, the
fact inventory from what is on disk, the budget movements, the open residue by running the lints.
The one typed input is `docs/plan-2-state.yaml`, one line per item, because a status somebody
decided is not derivable from a tree.

    ./adapters/tracker.py            write the page
    ./adapters/tracker.py --check    refuse a state file that claims more than it says
    ./adapters/tracker.py --fast     skip the timings, which cost a full cycle to measure
    ./adapters/tracker.py --self-test
"""
import argparse
import html
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / "docs" / "plan-2-state.yaml"
OUT = ROOT / "docs" / "tracker.html"

STATES = ("todo", "doing", "done", "dropped")

#: The steps whose cost this plan is about. Timed by running them, so a headline number cannot go
#: stale while the page still shows it.
TIMED = (
    ("test.py", [sys.executable, "test.py"]),
    ("build.py --no-checks", [sys.executable, "build.py", "--no-checks"]),
    ("build.py", [sys.executable, "build.py"]),
    ("deploy.sh", ["./deploy.sh"]),
    ("check.py --gate", [sys.executable, "check.py", "--gate"]),
)


def state():
    """The typed half. `{}` when the file is missing, so a fresh clone still renders."""
    import yaml
    if not STATE.exists():
        return {}
    return yaml.safe_load(STATE.read_text(encoding="utf-8")) or {}


def problems(doc=None):
    """Every way the state file claims more than it says.

    THE SMALLEST GUARD AGAINST THE FAULT THIS EXISTS FOR. A `done` with no note is a status somebody
    typed without saying what changed, which is exactly how a step came to be marked complete that
    had never been started.
    """
    doc = state() if doc is None else doc
    out = []
    for name, stg in (doc.get("stages") or {}).items():
        for item in (stg.get("items") or []):
            i = item.get("id", "?")
            st = item.get("state")
            if st not in STATES:
                out.append(f"{i}: state {st!r} is not one of {', '.join(STATES)}")
            if st in ("done", "dropped") and not str(item.get("note") or "").strip():
                out.append(f"{i}: {st} with no note saying what changed")
    return out


def facts():
    """The inventory, read off disk. A fact is complete when all four parts are present."""
    d = ROOT / "adapters" / "facts"
    got = []
    if not d.is_dir():
        return got
    for p in sorted(d.iterdir()):
        if not p.is_dir() or not (p / "__init__.py").exists():
            continue
        got.append({
            "name": p.name,
            "entry": (p / "__init__.py").exists(),
            "tests": bool(list(p.glob("test_*.py"))),
            "checks": (p / "checks.py").exists(),
            "blindspot": (p / "BLINDSPOT.md").exists(),
        })
    return got


def _num(cmd):
    try:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
        return int((r.stdout or "0").strip().split()[0])
    except Exception:                                                   # noqa: BLE001
        return None


def residue(budgets=None):
    """The open counts, measured by running the lints. A number here cannot be claimed lower.

    `budgets` IS THE NUMBERS A RUN JUST MEASURED, and it exists because of what this cost. The gate
    regenerates this page, the page ran `mergecheck.py`, and mergecheck runs `check.py --runtime` as
    a child: every gate was a gate plus a whole second run of the checks, 20 s of the 86, and the
    child overwrote the report the gate had just written so eight source budgets were published as
    `value: null`. When a caller has measured them already, comparing against those is not a
    shortcut; it is the same comparison without the second run.
    """
    lint = ROOT / "adapters" / "lint"
    if budgets:
        sys.path.insert(0, str(lint))
        import mergecheck
        disagreeing = len(mergecheck.disagreements(got=dict(budgets)))
    else:
        disagreeing = _num([sys.executable, str(lint / "mergecheck.py"), "--quiet"])
    return {
        "impossibilities asserted with no evidence":
            _num([sys.executable, str(lint / "claims.py"), "--quiet"]),
        "reaches past a fact's entry point":
            _num([sys.executable, str(lint / "facts.py"), "--quiet"]),
        "budgets disagreeing with this tree": disagreeing,
        "worktrees left open":
            _num(["bash", "-c", "git worktree list | wc -l"]),
    }


def timings(fast=False):
    """Seconds per step, by running each one. Skipped under `--fast`, which says so on the page."""
    if fast:
        return {}
    got = {}
    for label, cmd in TIMED:
        t = time.time()
        try:
            subprocess.run(cmd, cwd=str(ROOT), capture_output=True, timeout=900)
            got[label] = round(time.time() - t, 1)
        except Exception:                                               # noqa: BLE001
            got[label] = None
    return got


def measure(fast=False, budgets=None):
    """Everything the page shows that is not typed."""
    return {"facts": facts(), "residue": residue(budgets), "timings": timings(fast),
            "measured_at": time.strftime("%Y-%m-%d %H:%M")}


def render(doc, m):
    """The page. Kept here so what is shown and what is measured cannot drift apart."""
    e = html.escape
    chips = {"done": "owned", "doing": "partial", "todo": "unowned", "dropped": "next"}
    words = {"done": "Done", "doing": "In progress", "todo": "Not started", "dropped": "Dropped"}

    items = [i for s in (doc.get("stages") or {}).values() for i in (s.get("items") or [])]
    done = sum(1 for i in items if i.get("state") == "done")

    rows = []
    for key, stg in sorted((doc.get("stages") or {}).items()):
        its = stg.get("items") or []
        d = sum(1 for i in its if i.get("state") == "done")
        live = any(i.get("state") == "doing" for i in its)
        body = "".join(
            f'<tr><td class="s"><span class="chip {chips.get(i.get("state"), "unowned")}">'
            f'{words.get(i.get("state"), "?")}</span></td>'
            f'<td><b>{e(str(i.get("id")))}</b> {e(str(i.get("title")))}'
            + (f'<div class="where">{e(str(i["note"]))}</div>' if i.get("note") else "")
            + "</td></tr>" for i in its)
        rows.append(
            f'<div class="stage{" live" if live else ""}"><div class="num">{e(key)}</div>'
            f'<div><h3>{e(str(stg.get("title", "")))}</h3>'
            f'<table class="items"><tbody>{body}</tbody></table></div>'
            f'<span class="chip {"owned" if d == len(its) else "partial" if d else "unowned"}">'
            f'{d} of {len(its)}</span></div>')

    tim = "".join(f'<div class="stat"><span class="k">{e(k)}</span>'
                  f'<span class="v">{v if v is not None else "?"}<span class="u">s</span></span>'
                  f'</div>' for k, v in (m["timings"] or {}).items())
    if not tim:
        tim = ('<div class="empty">Timings not measured on this run. '
               '<code>./adapters/tracker.py</code> without <code>--fast</code> measures them.</div>')

    fac = "".join(
        f'<tr><td class="n">{e(f["name"])}</td>'
        + "".join(f'<td class="c">{"yes" if f[k] else "NO"}</td>'
                  for k in ("entry", "tests", "checks", "blindspot"))
        + "</tr>" for f in m["facts"])

    res = "".join(f'<tr><td>{e(k)}</td><td class="c">{v if v is not None else "?"}</td></tr>'
                  for k, v in m["residue"].items())

    return f"""<title>Yurarium refactor, second round</title>
<style>
 :root {{ --bg:#f7f6f9; --card:#fff; --ink:#1c1b22; --dim:#6b6878; --faint:#918da0; --rule:#e0dce8;
   --acc:#3b3a8f; --accs:#ecebf6; --red:#a93b2c; --reds:#f8ebe8; --grn:#3f6b4e; --grns:#e8f0ea;
   --amb:#8a6a1f; --ambs:#f7f0dd;
   --serif:Georgia,"Iowan Old Style",serif;
   --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
   --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }}
 @media (prefers-color-scheme:dark) {{ :root {{ --bg:#15141a; --card:#1d1c24; --ink:#e8e6ef;
   --dim:#a09cae; --faint:#726e80; --rule:#2e2c39; --acc:#9c9ae8; --accs:#24233a; --red:#e0806f;
   --reds:#33211e; --grn:#8fbf9f; --grns:#1c2820; --amb:#d6b45e; --ambs:#2b2517; }} }}
 :root[data-theme="dark"] {{ --bg:#15141a; --card:#1d1c24; --ink:#e8e6ef; --dim:#a09cae;
   --faint:#726e80; --rule:#2e2c39; --acc:#9c9ae8; --accs:#24233a; --red:#e0806f; --reds:#33211e;
   --grn:#8fbf9f; --grns:#1c2820; --amb:#d6b45e; --ambs:#2b2517; }}
 :root[data-theme="light"] {{ --bg:#f7f6f9; --card:#fff; --ink:#1c1b22; --dim:#6b6878;
   --faint:#918da0; --rule:#e0dce8; --acc:#3b3a8f; --accs:#ecebf6; --red:#a93b2c; --reds:#f8ebe8;
   --grn:#3f6b4e; --grns:#e8f0ea; --amb:#8a6a1f; --ambs:#f7f0dd; }}
 body {{ background:var(--bg); color:var(--ink); font-family:var(--sans); font-size:15px;
   line-height:1.6; -webkit-font-smoothing:antialiased; }}
 .wrap {{ max-width:1000px; margin:0 auto; padding:40px 24px 96px; display:flex;
   flex-direction:column; gap:40px; }}
 .eyebrow {{ font-family:var(--mono); font-size:11px; letter-spacing:.12em; text-transform:uppercase;
   color:var(--faint); }}
 h1 {{ font-family:var(--serif); font-weight:400; font-size:clamp(28px,4vw,38px); line-height:1.15;
   text-wrap:balance; margin-top:6px; }}
 h1 em {{ font-style:italic; color:var(--acc); }}
 .lede {{ color:var(--dim); max-width:62ch; margin-top:12px; }}
 h2 {{ font-family:var(--serif); font-weight:400; font-size:21px; }}
 .sec {{ display:flex; flex-direction:column; gap:16px; }}
 .band {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:1px;
   background:var(--rule); border:1px solid var(--rule); border-radius:4px; overflow:hidden; }}
 .stat {{ background:var(--card); padding:14px 16px; display:flex; flex-direction:column; gap:3px; }}
 .stat .k {{ font-family:var(--mono); font-size:10.5px; letter-spacing:.09em; text-transform:uppercase;
   color:var(--faint); }}
 .stat .v {{ font-family:var(--serif); font-size:25px; font-variant-numeric:tabular-nums; }}
 .stat .u {{ font-size:14px; color:var(--dim); }}
 .stages {{ display:grid; gap:12px; }}
 .stage {{ display:grid; grid-template-columns:38px 1fr auto; gap:14px; align-items:start;
   background:var(--card); border:1px solid var(--rule); border-radius:4px; padding:14px 16px; }}
 .stage.live {{ border-color:var(--acc); }}
 .stage .num {{ font-family:var(--serif); font-size:24px; color:var(--faint); }}
 .stage.live .num {{ color:var(--acc); }}
 .stage h3 {{ font-size:15px; font-weight:600; }}
 table {{ border-collapse:collapse; width:100%; font-size:13.5px; }}
 .items td {{ padding:6px 0; border:0; vertical-align:top; }}
 .items td.s {{ width:110px; }}
 .scroll {{ overflow-x:auto; border:1px solid var(--rule); border-radius:4px; background:var(--card); }}
 .scroll td, .scroll th {{ padding:9px 13px; border-bottom:1px solid var(--rule); text-align:left; }}
 .scroll tr:last-child td {{ border-bottom:0; }}
 .scroll th {{ font-family:var(--mono); font-size:10.5px; letter-spacing:.08em;
   text-transform:uppercase; color:var(--faint); font-weight:400; }}
 td.n {{ font-family:var(--mono); font-size:12.5px; }}
 td.c {{ font-variant-numeric:tabular-nums; text-align:right; }}
 .where {{ color:var(--dim); font-size:12.5px; }}
 .chip {{ display:inline-block; font-family:var(--mono); font-size:10.5px; letter-spacing:.05em;
   text-transform:uppercase; padding:2px 7px; border-radius:3px; white-space:nowrap; }}
 .chip.owned {{ background:var(--grns); color:var(--grn); }}
 .chip.partial {{ background:var(--ambs); color:var(--amb); }}
 .chip.unowned {{ background:var(--reds); color:var(--red); }}
 .chip.next {{ background:var(--accs); color:var(--acc); }}
 .empty {{ color:var(--faint); font-style:italic; padding:16px; background:var(--card);
   border:1px dashed var(--rule); border-radius:4px; }}
 code {{ font-family:var(--mono); font-size:.88em; background:var(--accs); color:var(--acc);
   padding:1px 5px; border-radius:3px; }}
 footer {{ border-top:1px solid var(--rule); padding-top:18px; color:var(--faint); font-size:12.5px; }}
</style>
<div class="wrap">
 <header>
  <div class="eyebrow">Yurarium · second round · generated {e(m["measured_at"])}</div>
  <h1>A common cycle in <em>under a minute</em>, and the residue the first round left</h1>
  <p class="lede">This page is generated by <code>adapters/tracker.py</code>. Every number is
   measured from the tree when it runs; the only typed input is one status line per item, and a
   status claiming <code>done</code> without saying what changed fails the check the gate runs.</p>
 </header>

 <section class="sec"><h2>A cycle, timed</h2><div class="band">{tim}</div></section>

 <section class="sec"><h2>Stages, {done} of {len(items)} items done</h2>
  <div class="stages">{"".join(rows)}</div></section>

 <section class="sec"><h2>Facts, read off disk</h2><div class="scroll"><table>
  <thead><tr><th>fact</th><th>entry</th><th>tests</th><th>checks</th><th>blind spot</th></tr></thead>
  <tbody>{fac}</tbody></table></div></section>

 <section class="sec"><h2>Open residue, measured by running the lints</h2><div class="scroll"><table>
  <tbody>{res}</tbody></table></div></section>

 <footer>Plan of record: <code>docs/REFACTOR-PLAN-2.md</code>. Statuses:
  <code>docs/plan-2-state.yaml</code>. Regenerate with <code>./adapters/tracker.py</code>.</footer>
</div>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="refuse a state file that over-claims")
    ap.add_argument("--fast", action="store_true", help="skip the timings")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        bad = {"stages": {"A": {"items": [
            {"id": "A1", "state": "done"},                  # done with no note
            {"id": "A2", "state": "invented"},               # not a state
            {"id": "A3", "state": "done", "note": "did it"},  # fine
            {"id": "A4", "state": "todo"},                   # fine
        ]}}}
        got = problems(bad)
        ok = len(got) == 2 and any("A1" in g for g in got) and any("A2" in g for g in got)
        if not ok:
            print(f"  self-test FAILED — tracker --check reported {got}")
            return 1
        if problems({"stages": {"A": {"items": [{"id": "x", "state": "todo"}]}}}):
            print("  self-test FAILED — a plain todo was reported as a problem")
            return 1
        if os.environ.get("YURA_CANARY"):
            print("CANARY-PROVEN")
        print("  self-test passed (2 over-claims caught, a plain todo left alone)")
        return 0

    if a.check:
        got = problems()
        for g in got:
            print(f"  {g}")
        if a.quiet:
            print(len(got))
        elif not got:
            print("  every item states what it claims")
        return 1 if got else 0

    doc = state()
    bad = problems(doc)
    if bad:
        print("  the state file over-claims; refusing to render:")
        for g in bad:
            print(f"    {g}")
        return 1
    OUT.write_text(render(doc, measure(a.fast)), encoding="utf-8")
    print(f"  wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
