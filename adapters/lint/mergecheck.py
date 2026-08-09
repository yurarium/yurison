#!/usr/bin/env python3
"""Compare a branch's recorded budgets against what the merge result actually measures.

STANDING-INSTRUCTIONS section 14a says a budget ratcheted in a branch is true of that branch alone
and must be re-measured on the merge result. That has been a person remembering, and it has failed:
`stock phrasing in comments` was ratcheted honestly to 898 in a worktree and measured 903 on main,
because the walk counted CLAUDE.md, which is ignored and exists only in the main tree. The branch
was right about its own tree and wrong about the repository.

WHAT IT DOES. Reads `docs/budgets.json` as the branch left it, measures every budget here, and
prints the ones that disagree. Run it after a merge and before a commit that claims the branch's
numbers.

    ./adapters/lint/mergecheck.py            compare and report
    ./adapters/lint/mergecheck.py --quiet    print the count of disagreements alone
    ./adapters/lint/mergecheck.py --self-test

WHAT IT CANNOT SEE, stated because a check hiding its blind spot is worse than none. It compares
NUMBERS. A branch that changed what a budget MEANS, so the same number now counts something else,
agrees with itself here and is exactly the case section 14a's prose is also bad at.
"""
import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUDGETS = ROOT / "docs" / "budgets.json"


def recorded():
    """The budgets as the file holds them."""
    if not BUDGETS.exists():
        return {}
    return json.loads(BUDGETS.read_text(encoding="utf-8"))


def measured():
    """Every budget, measured here and now.

    Runs `check.py --runtime` as a child and reads what it wrote, which is the same path the build
    takes. Section 14b: it does not import check.py and re-run the functions, because a budget that
    behaves differently in-process from how it behaves in a run is the fault this is looking for.
    """
    subprocess.run([sys.executable, str(ROOT / "check.py"), "--runtime"],
                   capture_output=True, text=True, timeout=600)
    out = ROOT / "data" / "build" / "checks.json"
    if not out.exists():
        return {}
    doc = json.loads(out.read_text(encoding="utf-8"))
    rows = doc.get("budgets") or doc.get("gate", {}).get("budgets") or []
    got = {}
    for r in rows:
        name, value = r.get("name"), r.get("value")
        if name is not None and value is not None:
            got[name] = value
    return got


def disagreements(rec=None, got=None):
    """`[(name, recorded, measured)]` where the file and the tree do not agree."""
    rec = recorded() if rec is None else rec
    got = measured() if got is None else got
    out = []
    for name, value in sorted(got.items()):
        was = rec.get(name)
        if was is not None and was != value:
            out.append((name, was, value))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        # THE CANARY IS A DISAGREEMENT PLANTED IN THE PAIR, not in the repository. Comparing two
        # dicts is the whole of the logic and this proves it reports and does not merely run.
        rec = {"a": 10, "b": 5, "c": 1}
        got = {"a": 10, "b": 7, "c": 0}
        bad = dict((n, (w, m)) for n, w, m in disagreements(rec, got))
        ok = bad == {"b": (5, 7), "c": (1, 0)}
        if not ok:
            print(f"  self-test FAILED — mergecheck reported {bad}")
            return 1
        # AND A BUDGET THE FILE DOES NOT HOLD IS NOT A DISAGREEMENT, because a new key is a new key
        # and not a regression.
        if disagreements({"a": 1}, {"a": 1, "new": 9}):
            print("  self-test FAILED — a new budget was reported as a disagreement")
            return 1
        print("  self-test passed (2 disagreements caught, a new key left alone)")
        return 0

    bad = disagreements()
    if a.quiet:
        print(len(bad))
        return 0
    for name, was, now in bad:
        arrow = "rose" if now > was else "fell"
        print(f"  {name}: recorded {was}, measures {now} here ({arrow})")
    print(f"{len(bad)} budget(s) disagree with the merge result"
          if bad else "  every recorded budget agrees with what this tree measures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
