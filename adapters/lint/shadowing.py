#!/usr/bin/env python3
"""Find names rebound so far from their first binding that the reuse is probably accidental.

WHY THIS EXISTS. Two bugs in one hour, both the same shape, both in build.py's main():

  `works`    rebound as a set of chapter titles inside the bulk-dating detector. Thirty lines
             later a loop did `w.get("grouping") for w in works` and got strings. The build
             crashed, which is the lucky case.
  `warnings` rebound by the feed-archive block. It already held the works with no content_tier,
             collected 1900 lines earlier, so the closing summary reported this block's warning
             count — zero — instead of "302 works have no content_tier". It did NOT crash. Real
             outstanding work silently read as done, and it shipped.

Python has no warning for this and a linter's "redefined" check is too noisy to keep on: rebinding
`r` in successive loops is idiomatic and fine. What is NOT fine is a name whose bindings are
hundreds of lines apart, because then the second author cannot see the first binding and the first
value is still live. Distance is the signal, so distance is what this measures.

It is deliberately not part of build.py. A build that fails because of a style rule is a build that
gets the rule deleted; this is run when the shape of the code changes, and its number is expected
to fall as main() is decomposed further.

Usage:  shadowing.py [file ...] [--span N] [--max N]
Exit 1 if the count exceeds --max, so it can gate a change if anyone wants it to.
"""
import argparse, ast, sys


def offenders(path, span):
    tree = ast.parse(open(path).read(), filename=path)
    out = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        at = {}
        for n in ast.walk(fn):
            # Store only. A read of an outer name is not a rebinding and is usually the point.
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                at.setdefault(n.id, []).append(n.lineno)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not fn:
                # A nested def has its own scope; its bindings are not this function's problem.
                for sub in ast.walk(n):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                        at.setdefault(sub.id, []).append(-1)
        for name, lines in at.items():
            lines = [l for l in lines if l > 0]
            if len(lines) > 1 and max(lines) - min(lines) > span:
                out.append((fn.name, name, min(lines), max(lines), len(lines)))
    return sorted(out, key=lambda o: -(o[3] - o[2]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", default=["build.py"])
    ap.add_argument("--span", type=int, default=300,
                    help="lines apart before a rebinding counts as out of sight")
    ap.add_argument("--max", type=int, default=None,
                    help="exit 1 if more than this many are found")
    a = ap.parse_args()

    total = 0
    for path in a.files:
        found = offenders(path, a.span)
        total += len(found)
        print(f"{path}: {len(found)} name(s) rebound more than {a.span} lines from first binding")
        for fn, name, lo, hi, n in found[:15]:
            print(f"    {name:20} in {fn}()  lines {lo}..{hi}  ({n} bindings, span {hi - lo})")
        if len(found) > 15:
            print(f"    … and {len(found) - 15} more")

    if a.max is not None and total > a.max:
        print(f"\nFAIL: {total} > --max {a.max}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
