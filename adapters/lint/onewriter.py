#!/usr/bin/env python3
"""Nothing writes to the relational store except the module that compiles it.

WHY THIS EXISTS. The store is DERIVED: everything in it is rebuilt from `data/build` plus the
rulings the facts hold, so deleting the database costs one rebuild and nothing else. That property
is the whole reason it is allowed to be load-bearing, and it survives exactly as long as one module
is the only thing that writes. A pass that reaches in to fix one row makes the database a source of
truth nobody declared, and the next rebuild silently throws that row away.

`adapters/lint/facts.py` proves nothing reaches past a fact's entry point. This is the same
argument for the store: one writer, named, and checked by looking rather than by remembering.

WHAT IT LOOKS FOR, outside `adapters/relational`:

    a statement that changes the database, passed to execute, executemany or executescript
    a connection opened to the store's own file

WHAT IT CANNOT SEE. SQL assembled at runtime out of pieces, and a write reached through a helper
this cannot follow. Both are why the rule is also written down in the store's own docstring: a lint
narrows the ways to break a rule, and it does not replace saying what the rule is.

    ./adapters/lint/onewriter.py             report every writer outside the compiler
    ./adapters/lint/onewriter.py --quiet     print the count alone
    ./adapters/lint/onewriter.py --self-test
"""
import argparse
import ast
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The module allowed to write, as a path fragment. One entry, on purpose.
COMPILER = "adapters/relational/"

#: A statement that changes the database rather than asking it something.
WRITES = re.compile(r"^\s*(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|PRAGMA\s+\w+\s*=)",
                    re.I)

_EXEC = {"execute", "executemany", "executescript"}


def findings(paths=None, root=None):
    """`[(path, line, what)]` for every write to the store outside the compiler."""
    root = pathlib.Path(root or ROOT)
    files = [pathlib.Path(p) for p in paths] if paths else [
        f for f in root.rglob("*.py")
        if not any(x in f.parts for x in (".git", "data", "__pycache__", "node_modules"))]

    out = []
    for f in sorted(files):
        rel = str(f.relative_to(root)) if f.is_relative_to(root) else str(f)
        # THE COMPILER MAY WRITE, and so may its own suite, which plants rows the schema must
        # refuse. A test that could not write could not prove a constraint rejects anything.
        if COMPILER in rel.replace("\\", "/"):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in _EXEC and n.args
                    and isinstance(n.args[0], ast.Constant)
                    and isinstance(n.args[0].value, str)
                    and WRITES.match(n.args[0].value)):
                out.append((rel, n.lineno, n.args[0].value.strip().split("\n")[0][:60]))
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "connect"
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "sqlite3"):
                out.append((rel, n.lineno, "opens its own connection to a database"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            (p / "adapters" / "relational").mkdir(parents=True)
            (p / "adapters" / "relational" / "__init__.py").write_text(
                'db.execute("INSERT INTO work (id) VALUES (?)", (1,))\n')
            (p / "elsewhere.py").write_text(
                'db.execute("INSERT INTO work (id) VALUES (?)", (1,))\n')
            (p / "reader.py").write_text(
                'db.execute("SELECT id FROM work WHERE title = ?", (t,))\n')
            (p / "opener.py").write_text('import sqlite3\nc = sqlite3.connect("x.db")\n')
            got = findings(root=p)
        where = {g[0] for g in got}
        if "elsewhere.py" not in where:
            print("  self-test FAILED — a write outside the compiler was not caught")
            return 1
        if "opener.py" not in where:
            print("  self-test FAILED — a second connection was not caught")
            return 1
        if any("relational" in w for w in where):
            print("  self-test FAILED — the compiler's own write was reported")
            return 1
        if "reader.py" in where:
            print("  self-test FAILED — a SELECT was read as a write")
            return 1
        if os.environ.get("YURA_CANARY"):
            print("CANARY-PROVEN")
        print("  self-test passed (2 writers caught, the compiler and a reader left alone)")
        return 0

    got = findings()
    if a.quiet:
        print(len(got))
        return 0
    for path, line, what in got:
        print(f"  {path}:{line}: {what}")
    print(f"{len(got)} write(s) to the store outside {COMPILER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
