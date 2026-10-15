#!/usr/bin/env python3
"""producers.yaml: every data file says what produces it, and the code names nothing undeclared.

COVERS = ['adapters/producers.py']

THE CHECK THAT MAKES "RAN ONCE, NEVER WIRED" A FAILING TEST. A new file under data/source,
data/coverage or data/queue, or a new path in the code, fails here until the registry says what
keeps it current. Read against the working tree, because the tree is what gets merged.
"""
import pathlib
import re
import sys
import tempfile

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import producers as pr                                                  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
LITERAL = re.compile(r'''["'](data/(?:source|coverage|queue)/[^"'\s{}]+)["']''')


def code_paths():
    """`{literal: [file]}` for every data path the build, the checks and the adapters name."""
    out = {}
    for f in [ROOT / "build.py", ROOT / "check.py"] + sorted((ROOT / "adapters").rglob("*.py")):
        if f.name.startswith("test_") or "/lint/" in str(f):
            continue
        for m in LITERAL.finditer(f.read_text(encoding="utf-8", errors="ignore")):
            out.setdefault(m.group(1), []).append(str(f.relative_to(ROOT)))
    return out


def stage_ids():
    out = set()
    for f in (ROOT / "adapters").glob("stage-*.yaml"):
        for c in yaml.safe_load(f.read_text())["commands"]:
            out.add(f"{f.stem}:{c['id']}")
    return out


def main(s):
    entries = pr.load()
    s.check(len(entries) > 20, "the registry is read")

    unclaimed = [f for f in pr.files() if not pr.entry(f, entries)]
    s.eq(unclaimed[:10], [], "every file under the three directories is claimed by an entry")

    # A FILE THE CODE NAMES MUST BE COVERED, whether or not it exists yet: an output nothing has
    # written is still a file somebody must say produces. A glob or a directory names no file of
    # its own, and every file under it is held to the rule above.
    uncovered = []
    for lit, where in sorted(code_paths().items()):
        if "*" in lit or not lit.endswith((".yaml", ".md", ".json")):
            continue
        if not pr.entry(lit, entries):
            uncovered.append(f"{lit} ({where[0]})")
    s.eq(uncovered[:10], [], "every data path the code names is covered by an entry")

    ids = stage_ids()
    bad = []
    for e in entries:
        s.check(e.get("status") in ("run", "hand", "frozen", "retired"),
                f"{e.get('paths')} states a known status")
        p = e.get("producer") or ""
        if e.get("status") == "run":
            if p.endswith("*"):
                ok = any(i.startswith(p[:-1]) for i in ids)
            else:
                ok = p in ids
            if not ok:
                bad.append(p)
    s.eq(bad, [], "every `run` entry names a command a stage manifest actually runs")

    # FRESHNESS, against files planted with dates.
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "data/source/x").mkdir(parents=True)
        (root / "data/source/x/new.yaml").write_text("retrieved: 2026-10-14\n")
        (root / "data/source/x/old.yaml").write_text("retrieved: 2026-09-15\n")
        (root / "data/source/x/silent.yaml").write_text("works: []\n")
        (root / "data/source/x/hand.yaml").write_text("retrieved: 2026-01-01\n")
        reg = [{"paths": ["data/source/x/hand.yaml"], "status": "hand"},
               {"paths": ["data/source/x/*.yaml"], "status": "run", "producer": "p",
                "max_age_days": 3}]
        got = sorted(pathlib.Path(f).name for f, _, _ in pr.stale(reg, "2026-10-15", root))
        s.eq(got, ["old.yaml", "silent.yaml"],
             "a run file older than its limit, or stating no date, is stale; a hand file never is")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "producers"))
