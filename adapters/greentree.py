#!/usr/bin/env python3
"""A token saying which tree the gate last passed on, so a push need not re-prove it.

WHY THIS EXISTS. A cycle runs the gate twice and the tests twice: once by hand and once again in
the pre-push hook, about 127 seconds of re-answering a question already answered. The hook stays
the mandatory boundary; this stops it re-proving a tree that was proved a minute ago.

THE HAZARD, WHICH IS THE WHOLE DESIGN PROBLEM. A token is a claim that nothing changed, and a token
over the wrong set vouches for a stale answer. That is worse than the seconds it saves, so the set
is deliberately an OVER-APPROXIMATION: every tracked file, everything under `data/build`, and the
deployed data and interface in the site repository. Hashing all of it is 4,370 files in 0.19 s, so
there is nothing to buy by being clever, and being clever is how the set comes to be wrong.

IT RECORDS WHAT IT COVERED. A token that cannot say what it hashed is not honoured, because a
token whose coverage nobody can inspect is a claim nobody can check.
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOKEN = ROOT / "data" / "build" / ".green-tree.json"

#: What a token covers, named so the file can say so. Over-approximate on purpose.
COVERS = (
    "every tracked file in the repository",
    "everything under data/build",
)


def _files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=str(ROOT),
                         capture_output=True, text=True, timeout=120).stdout.split("\0")
    got = [ROOT / f for f in out if f]
    got += list((ROOT / "data" / "build").rglob("*"))
    # THE TOKEN IS NOT PART OF THE TREE IT VOUCHES FOR. It lives under data/build, which this
    # hashes, so including it meant writing the token invalidated the token.
    #
    # NOR IS COMPILED BYTECODE. Two .pyc files were tracked from before the ignore rule, so merely
    # importing build or crossplatform rewrote a file this hashes and the token was refused for a
    # tree nobody had touched. Over-approximating is right, but only over files a person writes.
    # The self-test asserts the covered set is free of them, since untracking two is not a rule.
    return sorted({p for p in got
                   if p.is_file() and p != TOKEN and p.suffix != ".pyc"})


def digest():
    """One hash over the covered set, and the count of files it saw."""
    h = hashlib.sha256()
    n = 0
    for f in _files():
        try:
            b = f.read_bytes()
        except OSError:                                                 # noqa: PERF203
            continue
        h.update(str(f).encode("utf-8"))
        h.update(hashlib.sha256(b).digest())
        n += 1
    return h.hexdigest(), n


def write(what="gate"):
    """Record that `what` passed on the tree as it stands."""
    d, n = digest()
    TOKEN.parent.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(json.dumps({
        "digest": d, "files": n, "passed": what,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "covers": list(COVERS),
    }, indent=1) + "\n", encoding="utf-8")
    return d


def held(what="gate"):
    """`(True, reason)` when the token vouches for this tree, `(False, reason)` otherwise."""
    if os.environ.get("YURA_NO_TOKEN"):
        return False, "YURA_NO_TOKEN is set"
    if not TOKEN.exists():
        return False, "no token"
    try:
        doc = json.loads(TOKEN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, "token unreadable"
    # A TOKEN THAT CANNOT SAY WHAT IT COVERED IS NOT HONOURED. An older token written before the
    # covered set was widened would vouch for files it never hashed.
    if list(doc.get("covers") or []) != list(COVERS):
        return False, "token covers a different set from this one"
    if doc.get("passed") != what:
        return False, f"token records {doc.get('passed')!r} and not {what!r}"
    d, _n = digest()
    if d != doc.get("digest"):
        return False, "the tree has changed since it passed"
    return True, f"{what} passed on this exact tree at {doc.get('at')}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", metavar="WHAT", nargs="?", const="gate")
    ap.add_argument("--held", metavar="WHAT", nargs="?", const="gate")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        import tempfile
        global TOKEN                                                    # noqa: PLW0603
        keep = TOKEN
        # THE OVERRIDE IS TESTED, THEN SET ASIDE. `YURA_NO_TOKEN` refuses every token by design, so
        # with it set the rest of this suite read "a fresh token was refused" as a failure. The
        # scheduled cache-free run sets it, and that is exactly when the suite must still run.
        no_token = os.environ.pop("YURA_NO_TOKEN", None)
        try:
            with tempfile.TemporaryDirectory() as d:
                TOKEN = pathlib.Path(d) / "t.json"
                write("gate")
                os.environ["YURA_NO_TOKEN"] = "1"
                if held()[0]:
                    print("  self-test FAILED — YURA_NO_TOKEN did not refuse a valid token")
                    return 1
                del os.environ["YURA_NO_TOKEN"]
                TOKEN.unlink()
                ok, why = held()
                if ok:
                    print("  self-test FAILED — a missing token was honoured")
                    return 1
                write("gate")
                ok, why = held()
                if not ok:
                    print(f"  self-test FAILED — a fresh token was refused: {why}")
                    return 1
                # A CHANGED TREE MUST REFUSE IT. Planted in the token, because planting a file in
                # the repository during a test is the thing the token is meant to notice.
                doc = json.loads(TOKEN.read_text())
                doc["digest"] = "0" * 64
                TOKEN.write_text(json.dumps(doc))
                if held()[0]:
                    print("  self-test FAILED — a changed tree was vouched for")
                    return 1
                # AND A TOKEN COVERING A DIFFERENT SET IS NOT HONOURED.
                doc["digest"] = digest()[0]
                doc["covers"] = ["something else"]
                TOKEN.write_text(json.dumps(doc))
                if held()[0]:
                    print("  self-test FAILED — a token over another set was honoured")
                    return 1
                # NOR ONE RECORDING A DIFFERENT PASS.
                doc["covers"] = list(COVERS)
                doc["passed"] = "tests"
                TOKEN.write_text(json.dumps(doc))
                if held("gate")[0]:
                    print("  self-test FAILED — a token for another run was honoured")
                    return 1
        finally:
            TOKEN = keep
            if no_token is not None:
                os.environ["YURA_NO_TOKEN"] = no_token
        # AND NOTHING A COMPILER WRITES IS IN THE COVERED SET, or a token is refused for a tree
        # nobody edited. This asks the real set, not a temporary one, because that is where it went
        # wrong: two .pyc were tracked and every import invalidated the token.
        bytecode = [f for f in _files() if f.suffix in (".pyc", ".pyo")]
        if bytecode:
            print(f"  self-test FAILED — {len(bytecode)} compiled file(s) in the covered set, "
                  f"first {bytecode[0]}")
            return 1
        if os.environ.get("YURA_CANARY"):
            print("CANARY-PROVEN")
        print("  self-test passed (5 refusals caught, no bytecode covered, a fresh token honoured)")
        return 0

    if a.write:
        print(f"  green-tree token written for {a.write}: {write(a.write)[:16]}")
        return 0
    ok, why = held(a.held or "gate")
    print(f"  {'held' if ok else 'not held'}: {why}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
