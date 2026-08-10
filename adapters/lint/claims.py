#!/usr/bin/env python3
"""A comment claiming something is impossible must name the test that proves it.

DECISION 8 OF THE REFACTOR PLAN, and it has a body count. `enFallback` in kari/app.js carried
"That last one should be unreachable, because the build floors every string every surface carries",
and readers were shown `???? · Bun?Bun` for two artists whose readings openBD and the publisher both
state. The budget docstring for Japanese-in-English said a name the store cannot render showing as
Japanese was "a finished state rather than a failure", which was a policy the owner had already
overruled. The all-or-nothing docstring said a line waits for its readings to arrive when sixty of
seventy were held by Latin pen names for which no reading was ever coming.

A confident wrong comment calcifies harder than a test. A test says THIS HAPPENS; a comment says AND
THAT IS CORRECT, which stops the next reader looking.

THE RULE. A comment saying what code DOES is free. A comment asserting that something can never
happen is a CLAIM, and a claim carries its evidence: name the test, the canary or the invariant that
proves it, or delete the sentence and let the code speak.

WHAT COUNTS AS EVIDENCE, kept deliberately loose: a test file, a function name, `--self-test`,
`--canary`, `invariant`, `budget`, or a section reference. The point is to make the author say where
to look, not to parse a citation.

WHAT IT CANNOT SEE. It reads comments, so an impossibility asserted in prose elsewhere, or believed
and never written down, is invisible. And it cannot tell whether the named test proves the claim,
only that one was named. Both are better than the nothing that was there.
"""
import argparse
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Phrasings that assert an impossibility. Deliberately narrow: "never" alone is ordinary English
#: ("a reading is never invented"), so the pattern wants the shape of a claim about the code.
#:
#: `never reached` WANTS A COPULA IN FRONT OF IT. Bare, it caught two sentences telling the history
#: of a fault that was fixed: a fix to the renderer "never reached" what it had already rendered,
#: and an author "never reached a row". Those are transitive past narrative and not claims about
#: what the code can do. The self-test keeps both as cases it must leave alone, beside "this branch
#: is never reached", so the narrowing is held to having lost nothing.
CLAIMS = re.compile(
    r"\b(should be unreachable|is unreachable|cannot happen|can never happen|never happens|"
    r"(?:is|are|was|were|be|been)\s+never\s+reached|never reachable|"
    r"is impossible|cannot occur|will never|can only ever)\b", re.I)

#: A gesture at something that could be checked. Loose on purpose. It read `proved` and `proven`
#: and not `proves`, so two comments that named their evidence in the present tense were reported
#: as naming nothing; the self-test now writes it that way.
EVIDENCE = re.compile(
    r"(test_\w+|--self-test|--canary|self_test|canary|invariant|budget|§\s*\d|section \d|"
    r"\bprov(?:e|es|ed|en|ing)\b|\bpinned\b|\bcaught\b)", re.I)

COMMENT = re.compile(r"^\s*(?:#|//|\*|/\*)\s?(.*)$")


def _tracked():
    out = subprocess.run(["git", "ls-files", "-z", "*.py", "*.js"], cwd=str(ROOT),
                         capture_output=True, text=True, timeout=60).stdout.split("\0")
    got = [ROOT / f for f in out if f and (ROOT / f).exists()]
    site = ROOT.parent / "yurarium.github.io"
    if site.is_dir():
        got += [p for p in (site / "kari").rglob("*.js") if "node_modules" not in p.parts]
    return got


def findings(paths=None):
    """`[(path, line, sentence)]` for every impossibility asserted without evidence.

    A CLAIM IS READ WITH ITS NEIGHBOURS. The evidence often sits in the next sentence, so the whole
    comment BLOCK counts, not the one line the phrase landed on.
    """
    out = []
    for f in (paths or _tracked()):
        f = pathlib.Path(f)
        try:
            lines = f.read_text(encoding="utf-8").split("\n")
        except (OSError, UnicodeDecodeError):
            continue
        block, start = [], None
        for i, line in enumerate(lines + [""], 1):
            m = COMMENT.match(line)
            if m:
                if start is None:
                    start = i
                block.append(m.group(1))
                continue
            if block:
                text = " ".join(block)
                if CLAIMS.search(text) and not EVIDENCE.search(text):
                    hit = CLAIMS.search(text)
                    try:
                        where = str(f.relative_to(ROOT))
                    except ValueError:
                        where = str(f)
                    out.append((where, start, hit.group(0)))
                block, start = [], None
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            bad = pathlib.Path(d) / "bad.py"
            bad.write_text("# this should be unreachable, because the build covers every case\n"
                           "x = 1\n")
            good = pathlib.Path(d) / "good.py"
            good.write_text("# this should be unreachable, and test_thing.py plants one to prove it\n"
                            "x = 1\n")
            # PRESENT TENSE COUNTS TOO. `proves` was not in the evidence pattern, so two comments
            # naming the assertions right below them were reported as naming nothing.
            good2 = pathlib.Path(d) / "good2.py"
            good2.write_text("# it can only ever collapse an exact pair, which the four cases\n"
                             "# below are what proves\n"
                             "x = 1\n")
            plain = pathlib.Path(d) / "plain.py"
            plain.write_text("# a reading is never invented, which is a rule and not a claim\n"
                             "# about this code being unable to reach a branch\n"
                             "x = 1\n")
            caught = bool(findings([bad]))
            quiet_ok = not findings([good]) and not findings([good2])
            # THE REAL FILE THAT PROMPTED THIS, as it was: the exact sentence from kari/app.js.
            real = pathlib.Path(d) / "real.js"
            real.write_text("// a run the build never reached becomes question marks. That last one\n"
                            "// should be unreachable, because the build floors every string every\n"
                            "// surface carries.\n")
            caught_real = bool(findings([real]))
            # THE NARROWING, HELD TO HAVING LOST NOTHING. The first two are the sentences that
            # were reported and should not have been; the third is the shape the phrase is for.
            past = pathlib.Path(d) / "past.py"
            past.write_text("# a fix to the renderer never reached what it had already rendered,\n"
                            "# and 縁山 was established by search and then never reached a row\n"
                            "x = 1\n")
            branch = pathlib.Path(d) / "branch.py"
            branch.write_text("# this branch is never reached, because the caller filters first\n"
                              "x = 1\n")
            past_quiet = not findings([past])
            still_caught = bool(findings([branch]))
        if not past_quiet:
            print("  self-test FAILED — past narrative was read as a claim about the code")
            return 1
        if not still_caught:
            print("  self-test FAILED — 'is never reached' stopped being caught")
            return 1
        if not caught:
            print("  self-test FAILED — an unevidenced impossibility was not caught")
            return 1
        if not quiet_ok:
            print("  self-test FAILED — a claim naming its test was reported anyway")
            return 1
        if not caught_real:
            print("  self-test FAILED — the enFallback comment that prompted this was not caught")
            return 1
        # THE HARNESS'S WORD FOR IT. This self-test plants a case it must catch and one it must
        # leave alone, so it has already proved it can fail; `CANARY-PROVEN` is how ./test.py
        # --canary hears that, and without it the module counts as unproven forever.
        if os.environ.get("YURA_CANARY"):
            print("CANARY-PROVEN")
        print("  self-test passed (3 claims caught including the one that shipped a fault, "
              "2 left alone: an evidenced claim and past narrative)")
        return 0

    got = findings()
    if a.quiet:
        print(len(got))
        return 0
    for path, line, phrase in got:
        print(f"{path}:{line}: asserts {phrase!r} and names nothing that proves it")
    print(f"{len(got)} unevidenced impossibilit{'y' if len(got) == 1 else 'ies'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
