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

WHY THE COUNT IS NOT SIMPLY FALLING. The obvious remedy is to decompose main(). Two blocks came
out cleanly (write_feed_split, write_run_record) because they are the tail of the pipeline: they
read finished data and write files. The rest does not come out, and the reason is worth recording
so it is not attempted again from scratch.

Extracting the first-sighting-ledger section — a block with its own section comment, apparently one
concern — stranded ELEVEN names that main() still needed afterwards. Five were real state
(`lapsed`, `print_candidates`, `promoted`, `queue`, `web_works`). The other six were LOOP VARIABLES:
`c`, `k`, `key`, `r`, `v`, `w`, bound in one section and read in a later one.

That is the finding. main() is not a long function with tidy sections; its sections communicate
through names that look local and are not, and loop variables are load-bearing across hundreds of
lines. Decomposition therefore has to thread state explicitly rather than lift blocks, which is a
larger change than it appears and must be done with the byte-comparison harness in place.

Until then this lint is the mitigation: it cannot stop the hazard, but it names every place the
hazard lives, and the budget in docs/budgets.json stops the number growing.

AND THE SAME FAULT AT MODULE SCOPE, which is `--modules`. `adapters/store/` sat beside
`adapters/names/store.py`, and because the package put `names` on its own sys.path a bare
`import store` inside it resolved to the NAME store. Nothing warned; whichever directory came
first won, and the workaround was a comment telling the next reader not to reorder two lines. That
is the same shape as `warnings` above: a name whose second binding is invisible from the first, and
silence when it goes wrong. The rename to `adapters/relational` is the fix and this is the guard.

Usage:  shadowing.py [file ...] [--span N] [--max N]
        shadowing.py --modules       two importable modules answering to one name
Exit 1 if the count exceeds --max, so it can gate a change if anyone wants it to.
"""
import argparse, ast, collections, pathlib, re, sys

# WHICH FILES ARE THIS REPOSITORY'S OWN is asked of git, in one place, because an agent
# worktree at .claude/worktrees/ is a second copy of this repo inside it and walking counted
# every file once per tree. See `lint/tree`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tree as _tree                                                    # noqa: E402


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


ROOT = pathlib.Path(__file__).resolve().parents[2]


#: A directory a module puts on sys.path. `[^)]*` was wrong here and reported nothing at all,
#: because `Path(__file__)` closes a bracket before `parents[` is reached; the fixture in
#: test_shadowing.py is what said so.
_INSERT = re.compile(r'sys\.path\.insert\(.*?parents\[(\d+)\](?P<tail>(?:\s*/\s*"[^"]+")*)')


def _reachable(root):
    """`{directory: {names importable bare from it}}` for every directory the tree puts on the path.

    MEASURED, NOT LISTED. Thirty-odd directories go on sys.path across this tree and the list moves
    with the code, so reading the inserts is the only way the answer stays true.
    """
    out = collections.defaultdict(set)
    # ASKED OF GIT (`lint/tree`), so a nested worktree does not report every insert three times.
    for f in _tree.own_files(".py", root=root):
        if any(x in f.parts for x in ("data", "__pycache__", "node_modules")):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        here = set()
        for m in _INSERT.finditer(text):
            try:
                d = f.resolve().parents[int(m.group(1))]
            except IndexError:
                continue
            for part in re.findall(r'"([^"]+)"', m.group("tail")):
                d = d / part
            if d.is_dir():
                here.add(d)
        if here:
            out[frozenset(here)].add(f)
    return out


def collisions(root=None):
    """`[(name, [paths])]` for a name two modules answer to WHERE BOTH ARE ON ONE PATH.

    THIRTEEN `releases.py` ARE NOT A COLLISION. Each names one platform, a caller writes
    `gigaviewer.releases` through the `adapters` entry, and the platform's own directory goes on the
    path only while that platform's code runs. The fault is a name reachable BARE from two
    directories that some module puts on the path at the same time, which is how a bare
    `import store` inside `adapters/store` found `adapters/names/store.py`.

    SUITES ARE RUN BY PATH and never imported by name, so two directories may both hold a
    `test_store.py`. `__init__.py` is read as the name of its directory, since that is the name an
    importer writes.
    """
    root = pathlib.Path(root or ROOT).resolve()

    def bare(d):
        got = {}
        for f in d.iterdir():
            if f.is_dir() and (f / "__init__.py").exists():
                got[f.name] = f / "__init__.py"
            elif (f.suffix == ".py" and not f.name.startswith("test_")
                  and f.name not in ("testkit.py", "__init__.py")):
                # A directory's own `__init__.py` is its package marker and not a name anyone
                # imports; counting it made every pair of packages on one path a collision.
                got[f.stem] = f
        return got

    found = {}
    for together in _reachable(root):
        listing = {d: bare(d) for d in together if d.is_dir()}
        for a in listing:
            for b in listing:
                if a is b:
                    continue
                for name in set(listing[a]) & set(listing[b]):
                    if listing[a][name] != listing[b][name]:
                        found.setdefault(name, set()).update(
                            (listing[a][name], listing[b][name]))
    return sorted((n, sorted(str(p.relative_to(root)) for p in v)) for n, v in found.items())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", default=["build.py"])
    ap.add_argument("--modules", action="store_true",
                    help="report importable names two files answer to")
    ap.add_argument("--span", type=int, default=300,
                    help="lines apart before a rebinding counts as out of sight")
    ap.add_argument("--max", type=int, default=None,
                    help="exit 1 if more than this many are found")
    a = ap.parse_args()

    if a.modules:
        got = collisions()
        for name, paths in got:
            print(f"  {name}: {', '.join(paths)}")
        print(f"{len(got)} name(s) two modules answer to")
        return 1 if got and a.max is not None and len(got) > a.max else 0

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
