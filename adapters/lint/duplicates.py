#!/usr/bin/env python3
"""A fact with more than one home, found by looking instead of by remembering.

WHY THIS EXISTS. STANDING-INSTRUCTIONS section 3 says one producer of a fact, and the way that rule
gets broken is not by importing something twice. It is by typing the same tuple, the same dict of
keys or the same regex into a second file, which no import lint can see. A census on 2026-08-10
found thirteen functions called `fold` giving three incompatible answers to one question, a yuri
label vocabulary in three homes deciding what the database admits, and six implementations of kana
to katakana.

An inventory somebody writes by hand is a list nobody checked, so this looks.

WHAT IT LOOKS FOR:

    a collection of string literals assigned at module level, in two or more files
    a dict literal whose KEYS match another's, in two or more files
    a regex compiled from the same pattern, in two or more files
    a function whose body is identical to another's once names are blanked

WHAT IT CANNOT SEE, which is most of the problem and is why the number is a floor. A rule written
as different code in two places is invisible. So is a vocabulary built at runtime, a threshold
repeated as a bare number, and a fact split between a file and a comment. The thirteen folds were
found by this, and their DISAGREEMENT was found by running them, which no static pass would do.
"""
import argparse
import ast
import collections
import hashlib
import json
import os
import pathlib
import sys

# WHICH FILES ARE THIS REPOSITORY'S OWN is asked of git, in one place, because an agent
# worktree at .claude/worktrees/ is a second copy of this repo inside it and walking counted
# every file once per tree. See `lint/tree`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tree as _tree                                                    # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
ALLOW = ROOT / "docs" / "duplicates-allowed.yaml"

#: A collection this small is a coincidence and not a vocabulary.
MIN_ITEMS = 2
MIN_KEYS = 3
MIN_PATTERN = 8
MIN_BODY_STATEMENTS = 4


def _sources(paths=None, tests=False):
    if paths:
        return [pathlib.Path(p) for p in paths]
    # ASKED OF GIT (`lint/tree`), because an agent worktree at .claude/worktrees/ is a second copy
    # of this repository inside it, and walking counted every file once per tree.
    out = []
    for f in _tree.own_files(".py"):
        if any(x in f.parts for x in ("data", "__pycache__")):
            continue
        if not tests and (f.name.startswith("test_") or f.name == "testkit.py"):
            continue
        out.append(f)
    return sorted(out)


def _blank(node):
    """A function body with every name and attribute blanked, so two spellings of one rule collide."""
    class B(ast.NodeTransformer):
        def visit_Name(self, n):
            return ast.copy_location(ast.Name(id="_", ctx=n.ctx), n)

        def visit_arg(self, n):
            return ast.copy_location(ast.arg(arg="_"), n)

        def visit_Attribute(self, n):
            self.generic_visit(n)
            return ast.copy_location(ast.Attribute(value=n.value, attr="_", ctx=n.ctx), n)

    t = B().visit(ast.parse(ast.unparse(node)))
    return hashlib.sha256(ast.dump(t).encode()).hexdigest()


def findings(paths=None):
    """`[(kind, what, [files])]` for every fact this can see in more than one home."""
    vocab, dicts, pats, bodies = (collections.defaultdict(set) for _ in range(4))
    for f in _sources(paths):
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        name = str(f.relative_to(ROOT)) if ROOT in f.parents or f.is_relative_to(ROOT) else str(f)
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and isinstance(n.value, (ast.Tuple, ast.Set, ast.List)):
                vals = tuple(sorted(e.value for e in n.value.elts
                                    if isinstance(e, ast.Constant) and isinstance(e.value, str)))
                if len(vals) >= MIN_ITEMS and len(vals) == len(n.value.elts):
                    vocab[vals].add(name)
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict):
                ks = tuple(sorted(k.value for k in n.value.keys
                                  if isinstance(k, ast.Constant) and isinstance(k.value, str)))
                if len(ks) >= MIN_KEYS and len(ks) == len(n.value.keys):
                    dicts[ks].add(name)
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "compile" and n.args
                    and isinstance(n.args[0], ast.Constant)
                    and isinstance(n.args[0].value, str)
                    and len(n.args[0].value) >= MIN_PATTERN):
                pats[n.args[0].value].add(name)
            if isinstance(n, ast.FunctionDef) and len(n.body) >= MIN_BODY_STATEMENTS:
                try:
                    bodies[_blank(n)].add(f"{name}:{n.name}")
                except (SyntaxError, ValueError, RecursionError):
                    pass

    allowed = _allowed()
    out = []
    for kind, d, fmt in (("vocabulary", vocab, lambda k: ", ".join(k)[:60]),
                         ("dict keys", dicts, lambda k: ", ".join(k)[:60]),
                         ("regex", pats, lambda k: k[:60]),
                         ("function body", bodies, lambda k: k[:12])):
        for key, where in d.items():
            files = {w.split(":")[0] for w in where}
            if len(files) < 2:
                continue
            what = fmt(key)
            if any(a in what or all(a in w for w in where) for a in allowed):
                continue
            out.append((kind, what, sorted(where)))
    return sorted(out)


def _allowed():
    """Cases somebody has argued for, so the count is a list of open ones and not a wall."""
    if not ALLOW.exists():
        return []
    try:
        import yaml
        doc = yaml.safe_load(ALLOW.read_text(encoding="utf-8")) or {}
        return [str(x.get("match", "")) for x in (doc.get("allowed") or []) if x.get("match")]
    except Exception:                                                   # noqa: BLE001
        return []


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "a.py").write_text('STYLES = ("macron", "double", "plain")\n')
            (p / "b.py").write_text('ROMAJI = ("macron", "double", "plain")\n')
            (p / "c.py").write_text('ONLY_HERE = ("alpha", "beta", "gamma")\n')
            got = findings([p / "a.py", p / "b.py", p / "c.py"])
            caught = [g for g in got if "macron" in g[1]]
            quiet = [g for g in got if "alpha" in g[1]]
            # AND A REGEX IN TWO HOMES, because the census found fifteen of those.
            # A LITERAL DUPLICATE ON PURPOSE. A mechanical pass over the tree rewrote this fixture
            # into a shared constant on 2026-08-10, which made the canary correct and therefore
            # useless. A canary is the one place a duplicate belongs.
            dup = 'import re\nX = re.compile(r"<dup>(.*?)</dup>")\n'
            (p / "d.py").write_text(dup)
            (p / "e.py").write_text(dup.replace("X =", "Y ="))
            rx = [g for g in findings([p / "d.py", p / "e.py"]) if g[0] == "regex"]
        if not caught:
            print("  self-test FAILED — a vocabulary in two homes was not caught")
            return 1
        if quiet:
            print("  self-test FAILED — a vocabulary in ONE home was reported")
            return 1
        if not rx:
            print("  self-test FAILED — a regex in two homes was not caught")
            return 1
        if os.environ.get("YURA_CANARY"):
            print("CANARY-PROVEN")
        print("  self-test passed (2 kinds caught, a single home left alone)")
        return 0

    got = findings()
    if a.json:
        print(json.dumps([{"kind": k, "what": w, "where": f} for k, w, f in got], indent=1))
        return 0
    if a.quiet:
        print(len(got))
        return 0
    for kind, what, where in got:
        print(f"  {kind:14} {what}")
        for w in where:
            print(f"        {w}")
    print(f"{len(got)} fact(s) with more than one home")
    return 0


if __name__ == "__main__":
    sys.exit(main())
