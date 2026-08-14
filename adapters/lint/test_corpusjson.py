#!/usr/bin/env python3
"""adapters/lint/corpusjson: which modules still open a compiled file by path.

COVERS = ['adapters/lint/corpusjson.py']

WHAT CAN BE WRONG HERE IS WHAT IT MISSES, which is what put it in the tree. §13's readers were
converted one at a time and two CI runs died on the same class, the second on the file the first had
been fixed in. A lint that finds nine of eleven is the same failure one step later.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit                                                          # noqa: E402
from lint import corpusjson                                             # noqa: E402


def _tree(**files):
    d = pathlib.Path(tempfile.mkdtemp())
    for name, body in files.items():
        p = d / name.replace("__", "/")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return d


def _found(**files):
    d = _tree(**files)
    return {(pathlib.Path(f).name, what.split(",")[0])
            for f, _line, what in corpusjson.findings(sorted(d.rglob("*.py")), root=d)}


def main(s):
    # THE THREE SHAPES THE REAL READERS HAD, each of which was in the tree this morning.
    s.check(("a.py", "reads series.json") in _found(
        **{"a.py": 'import json\nx = json.loads(open("data/build/series.json").read())\n'}),
        "a path written whole is found")
    s.check(("b.py", "reads series.json") in _found(
        **{"b.py": 'x = (build / "series.json").read_text()\n'}),
        "and one assembled with a slash, where the name sits inside the callee")
    s.check(("c.py", "reads works.json") in _found(
        **{"c.py": 'x = json.loads(pathlib.Path(a.build / "works.json").read_text())["works"]\n'}),
        "and one nested two calls deep")

    # ── AND THE COUNTER-CASES, WHICH ARE WHY THIS IS NOT A SUBSTRING SEARCH ───────────────────
    #
    # A GREAT DEAL OF PROSE NAMES THESE FILES. The whole of §13's history is written in comments
    # beside the code that moved, and a lint counting mentions reported 219 findings, most of them
    # sentences. What makes a mention a finding is that it is being READ.
    s.eq(_found(**{"d.py": '"""series.json used to be read here."""\n# and works.json too\n'}), set(),
         "prose naming a corpus file is prose")
    s.eq(_found(**{"e.py": 'ap.add_argument("--series", help="a series.json to read instead")\n'}),
         set(), "and so is an argument's help text")
    s.eq(_found(**{"f.py": '(out / "series.json").write_text(payload)\n'}), set(),
         "writing one is not reading one, which is what `--emit-json` still does")
    s.eq(_found(**{"g.py": 'x = json.loads(open("data/build/titles.json").read())\n'}), set(),
         "and `titles.json` is not on the list: build.py still writes it and a pass still reads it")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
