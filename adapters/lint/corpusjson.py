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

#: The module allowed to name them, and the one that produces them. One entry each, on purpose.
ALLOWED = ("adapters/population.py", "adapters/relational/emit.py")


#: What counts as opening one. A bare mention is prose, and there is a great deal of prose about
#: these files: the whole of §13's history is written in comments beside the code that moved. What
#: makes a mention a finding is that it is being READ.
READS = {"read_text", "load", "loads", "open", "read_json"}


def _reads_corpus(node):
    """Whether a call opens a corpus file. The name may be built with `/`, so the whole call is
    walked rather than only its arguments: `(build / "series.json").read_text()` puts the constant
    inside the callee."""
    fn = node.func
    name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
    if name not in READS:
        return None
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            hit = next((c for c in CORPUS if c in n.value), None)
            if hit:
                return hit
    return None


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
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            hit = _reads_corpus(n)
            if hit:
                out.append((rel, n.lineno, f"reads {hit}, which only the store produces now"))
    return out


if __name__ == "__main__":
    got = findings()
    for path, line, what in got:
        print(f"{path}:{line}: {what}")
    print(f"{len(got)} module(s) name a corpus file")
    raise SystemExit(1 if got else 0)
