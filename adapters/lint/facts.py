#!/usr/bin/env python3
"""A fact has one owner: nothing outside a module may reach past its entry point.

WHY A LINT AND NOT A RULE IN PROSE. STANDING-INSTRUCTIONS section 3 has said "one producer of a
fact" for as long as the project has existed, and twelve shipped faults in one week were breaches of
it. The rule was right and unenforced. This is the enforcement.

WHAT IT REFUSES. A module under `adapters/facts/<name>/` has a public surface, which is whatever
`__init__.py` defines. Any file outside that directory may import the package and call it. No file
outside it may import a submodule, and no file outside it may name a private helper.

WHAT IT CANNOT SEE, stated because a check that hides its blind spot is worse than no check. It
reads import statements, so a caller reaching a module through `importlib.import_module` on a
computed name is invisible to it. It also says nothing about whether a caller SHOULD have used the
fact: a second implementation written from scratch, importing nothing, passes this and is exactly
the fault the rule is about. `facts/romanisation` was extracted out of four such assemblers and
only one of them imported anything it should not have.
"""
import argparse
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FACTS = ROOT / "adapters" / "facts"

# TWO FORMS, AND MY FIRST VERSION HAD ONLY ONE. `import facts.X.Y` puts the submodule in the
# dotted path; `from facts.X import Y` puts it in the imported names, which is the commoner way to
# write it and the one the self-test caught me missing.
IN_PATH = re.compile(r"^\s*(?:from|import)\s+(?:adapters\.)?facts\.(\w+)\.(\w+)", re.M)
IN_NAMES = re.compile(r"^\s*from\s+(?:adapters\.)?facts\.(\w+)\s+import\s+([^\n#]+)", re.M)


def owned(facts_dir=None):
    """The extracted facts, by directory name."""
    d = pathlib.Path(facts_dir or FACTS)
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir() and (p / "__init__.py").exists())


def findings(paths=None, facts_dir=None):
    """Every place outside a fact that reaches past its entry point.

    `facts_dir` is for the self-test, which builds a complete throwaway fact so that BOTH import
    forms are exercised. Pointing the canary at a real fact proved only the form whose submodule
    happens to exist, which for the first extracted fact was neither.
    """
    root = pathlib.Path(facts_dir or FACTS)
    facts = set(owned(root))
    if not facts:
        return []
    files = paths or [p for p in ROOT.rglob("*.py")
                      if ".git" not in p.parts and "data" not in p.parts]
    out = []
    for f in files:
        f = pathlib.Path(f)
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        inside = root in f.parents
        def report(m, fact, sub):
            if fact not in facts:
                return
            # A FACT MAY REACH ITS OWN INTERNALS. That is what being the owner means.
            if inside and f.parent.name == fact:
                return
            # A CANARY LIVES OUTSIDE THE REPOSITORY, so the path is only made relative when it
            # can be. Raising there would have made the self-test unable to run itself.
            try:
                where = str(f.relative_to(ROOT))
            except ValueError:
                where = str(f)
            out.append((where, text[:m.start()].count("\n") + 1, fact, sub))

        for m in IN_PATH.finditer(text):
            report(m, m.group(1), m.group(2))
        for m in IN_NAMES.finditer(text):
            fact = m.group(1)
            for raw in m.group(2).split(","):
                nm = raw.strip().split(" as ")[0].strip().strip("()")
                # A NAME IS A REACH-PAST ONLY IF IT IS A FILE. `from facts.romanisation import
                # romanise` asks for the entry point's own function and is the intended use;
                # `import kana` asks for a module the package happens to contain.
                if nm and (root / fact / f"{nm}.py").exists():
                    report(m, fact, nm)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true", help="print the count alone")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        # THE CANARY IS A REAL REACH-PAST, written into a temporary file rather than described. A
        # lint proved against a string it was handed is proved against its own regex.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            fake = pathlib.Path(d) / "facts" / "canary"
            fake.mkdir(parents=True)
            (fake / "__init__.py").write_text("")
            (fake / "inner.py").write_text("")
            caught = {}
            for label, line in (("in the path", "import facts.canary.inner"),
                                ("in the names", "from facts.canary import inner"),
                                ("aliased", "from facts.canary import inner as x")):
                bad = pathlib.Path(d) / "bad.py"
                bad.write_text(line + "\n")
                caught[label] = bool(findings([bad], facts_dir=fake.parent))
            # AND THE SHAPE THAT MUST NOT BE CAUGHT, because a lint that flags the intended use is
            # worse than none: the entry point's own names are what callers are for.
            ok = pathlib.Path(d) / "ok.py"
            ok.write_text("from facts.canary import romanise\n")
            quiet = not findings([ok], facts_dir=fake.parent)
        missed = [k for k, v in caught.items() if not v]
        if missed or not quiet:
            for k in missed:
                print(f"  self-test FAILED — the fact lint missed a reach-past {k}")
            if not quiet:
                print("  self-test FAILED — the fact lint flagged the entry point's own name")
            return 1
        # THE HARNESS'S WORD FOR IT. This self-test plants a case it must catch and one it
        # must leave alone, so it has already proved it can fail. `CANARY-PROVEN` is how
        # ./test.py --canary hears that; without it the module counts unproven forever.
        if os.environ.get("YURA_CANARY"):
            print("CANARY-PROVEN")
        print(f"  self-test passed ({len(caught)} forms caught, entry point left alone)")
        return 0

    got = findings()
    if a.quiet:
        print(len(got))
        return 0
    for path, line, fact, sub in got:
        print(f"{path}:{line}: reaches facts.{fact}.{sub}, past the entry point")
    print(f"{len(got)} reach(es) past an entry point; facts owned: {', '.join(owned()) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
