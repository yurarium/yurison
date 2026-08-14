#!/usr/bin/env python3
"""Modules that open a corpus JSON file by path. STORE-PLAN §13.

WHY THIS EXISTS, AND IT IS A BUG PROTOCOL FAILURE THAT PUT IT HERE. §13 stopped `build.py` writing
the corpus JSON, and the readers were converted one at a time as each was noticed. Two CI runs died
in a row on the same class, `adapters/names/inputs.py` twice over, because the fix each time was to
the case in front of me rather than to the class. Nine more were sitting behind them.

WHAT IT LOOKS FOR. A string literal naming one of the compiled files, anywhere a module might hand
it to `open` or `read_text`. That is coarser than following the value, and coarse is right here: a
path built up in pieces is exactly what the last round of this hid behind, and a module that merely
NAMES one of these files in code is a module somebody should look at.

WHAT IT DOES NOT COUNT. `adapters/population.py`, which is the one place allowed to read them, and
the emitters, which produce them. Comments and docstrings are stripped first, so the many places
that explain the history are not findings. A `--series` argument's help text is prose.
"""
import ast
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tree as _tree                                                    # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The compiled files. `titles.json` is not among them: `build.py` still writes it and
#: `gigaviewer/releases.py` still reads it, which is a pair §13 has not reached.
CORPUS = ("series.json", "works.json", "index.json", "credits.json", "publishers.json",
          "credit-keys.json", "feed/names.json")

#: WHO MAY NAME THEM, AND WHY EACH IS HERE. `population` is the one reader and `emit` produces
#: them. `build.py` still writes them under `--emit-json`. `check.py` builds the map of emitted
#: texts three checks scan, so the names are its keys. `facts/served` DECLARES the set, which is
#: what makes it the register. `names/inputs` names two in a table of which field to read from
#: which shape, and reads neither by path.
#:
#: EVERY ENTRY IS A HOLE and the list is meant to stay this short. A file added here stops being
#: watched, which is the trade `adapters/lint/onewriter.py` makes with the same shape.
ALLOWED = ("adapters/population.py", "adapters/relational/emit.py", "build.py", "check.py",
           "adapters/facts/served/__init__.py", "adapters/names/inputs.py",
           "adapters/lint/corpusjson.py")


#: WHAT COUNTS AS WRITING ONE, which is the only executable mention that is not a finding.
#: `build.py --emit-json` still writes these, deliberately.
WRITES = {"write_text", "dump", "write"}

#: A keyword whose value is prose meant for a person rather than a path.
PROSE_KEYWORDS = {"help", "description", "metavar", "note"}

#: The reader itself, under the names the tree imports it by. A path HANDED TO it is the override
#: every converted pass kept, `--series`, so a person can run against an old build; naming a file
#: on the way into the one reader is the opposite of the fault this counts.
READER = {"population", "_population", "_pop"}


def _is_prose(node, parents):
    """Whether this string is written for a person rather than used as a path.

    THE RULE STARTED AS "IS IT INSIDE A READ" AND THAT WAS WRONG. `adapters/status.py` held
    `read = lambda n: json.loads((b / n).read_text())` and then `read("series.json")`, so the name
    and the open were in different statements and this reported the file clean. It went to CI and
    the run died on it: the third round trip on one class, and the second time this lint's own
    stated blind spot was the thing that bit. A blind spot written down is still a blind spot.

    SO EVERY EXECUTABLE MENTION IS A FINDING and the exceptions are enumerated. There are three: a
    docstring, an argument's help text, and a write.
    """
    for p in parents:
        if isinstance(p, ast.keyword) and p.arg in PROSE_KEYWORDS:
            return True
        if isinstance(p, ast.Call):
            fn = p.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name in WRITES:
                return True
            # HANDED TO THE READER. `population.series(build / "series.json")` names the file on
            # its way INTO the one place allowed to open it.
            owner = fn.value if isinstance(fn, ast.Attribute) else None
            if isinstance(owner, ast.Name) and owner.id in READER:
                return True
            if isinstance(owner, ast.Call) and getattr(owner.func, "id", None) in READER:
                return True
    return False


def _docstrings(tree):
    """Every docstring's identity: the first statement of a module, class or function body."""
    out = set()
    for n in ast.walk(tree):
        body = getattr(n, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                out.add(id(first.value))
    return out


def findings(paths=None, root=None):
    """`[(path, line, what)]` for every module naming a corpus file outside the allowed two."""
    root = pathlib.Path(root or ROOT)
    files = [pathlib.Path(p) for p in paths] if paths else [
        f for f in _tree.own_files(".py", root=root)
        if not any(x in f.parts for x in ("data", "__pycache__", "node_modules"))]
    out = []
    for f in sorted(files):
        rel = str(f.relative_to(root)).replace("\\", "/") if f.is_relative_to(root) else str(f)
        if rel in ALLOWED or "/test_" in rel or pathlib.Path(rel).name.startswith("test_"):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        docs = _docstrings(tree)
        # PARENTS ARE TRACKED ON THE WAY DOWN, `ast` offering no way to ask a node for its own.
        stack = [(tree, ())]
        while stack:
            node, parents = stack.pop()
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in docs):
                hit = next((c for c in CORPUS if c in node.value), None)
                if hit and not _is_prose(node, parents):
                    out.append((rel, node.lineno, f"names {hit}, which only the store produces"))
            for child in ast.iter_child_nodes(node):
                stack.append((child, (node,) + parents))
    return sorted(out)


if __name__ == "__main__":
    got = findings()
    for path, line, what in got:
        print(f"{path}:{line}: {what}")
    print(f"{len(got)} module(s) name a corpus file")
    raise SystemExit(1 if got else 0)
