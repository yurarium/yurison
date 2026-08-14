#!/usr/bin/env python3
"""check.py --incremental: a pass is remembered against everything it could have read.

COVERS = ['check.py']

THE CLAIM UNDER TEST is that a remembered answer is only ever "this said nothing on exactly these
inputs". Two ways that could be wrong, and both are here: a check that FOUND something must not be
remembered, and a key must move when any class of input moves.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit

import importlib.util as _u
_spec = _u.spec_from_file_location("chk", pathlib.Path(__file__).resolve().parents[1] / "check.py")
chk = _u.module_from_spec(_spec)
_spec.loader.exec_module(chk)


def main(s):
    keys = chk._input_keys()
    s.eq(sorted(keys), ["code", "data", "site"], "there are three classes of input")
    s.check(all(len(v) == 64 for v in keys.values()), "each is a digest of what is in that class")

    a = chk._verify_key("a check", keys, set())
    s.eq(a, chk._verify_key("a check", keys, set()), "the same inputs give the same key")
    s.ne(a, chk._verify_key("another check", keys, set()),
         "two checks on the same inputs do not share a key, or one would vouch for the other")

    # EVERY CLASS MOVES THE KEY. A class that did not would let a check be skipped after exactly
    # the change it exists to notice.
    for cls in ("code", "data"):
        moved = dict(keys, **{cls: "0" * 64})
        s.ne(a, chk._verify_key("a check", moved, set()), f"a change under {cls} moves the key")

    # AND `site` MOVES IT ONLY FOR A CHECK THAT READS THE SITE, which is what deploy_sensitive
    # derives. A check that never looks at the deployed tree should not be re-run by a deploy.
    moved = dict(keys, site="0" * 64)
    s.eq(a, chk._verify_key("a check", moved, set()),
         "a deploy does not re-run a check that never reads the deployed tree")
    s.ne(chk._verify_key("a check", keys, {"a check"}),
         chk._verify_key("a check", moved, {"a check"}),
         "and it does re-run one that does")

    # THE DEPLOYED TREE IS NOT THIS REPOSITORY'S ANY MORE, §11. `deploy_sensitive` derived which
    # invariants read it, and none does: what a reader is SHOWN is checked where it is rendered, so
    # the `site` key below is what a check would have to name and nothing names it. The two
    # assertions above still hold, and the third has nothing left to be true about.

    # ── THE PROOF IS REMEMBERED ON THE SAME TERMS AS A CHECK ──────────────────────────────────
    #
    # `check.py --self-test` was 24.7s of a 79.6s gate and the largest single cost once
    # `--incremental` became the default on 2026-08-13. It asks whether the CHECKS can detect a
    # fault, so it depends on the checking code and on the build it plants canaries in, which is
    # exactly what `_verify_key` hashes. It gets no key of its own design.
    s.check(chk.SELF_TEST.startswith(" "),
            "the name it is remembered under starts with a space, so no real check can collide "
            "with it: every real name comes from INVARIANTS or BUDGETS_DEF and none is spelled so")
    real = {n for n, _f in chk.INVARIANTS} | {n for n, _f, _w in chk.BUDGETS_DEF}
    s.check(chk.SELF_TEST not in real, "and nothing in either list has taken it")

    proof = chk._verify_key(chk.SELF_TEST, keys, set())
    s.eq(proof, chk._verify_key(chk.SELF_TEST, keys, set()),
         "the same code and build remember the same proof")
    # AND IT MOVES WITH THE CODE, which is the whole of why it may be remembered at all. A proof
    # kept across an edit to check.py would vouch for checks nobody has run.
    moved = dict(keys); moved["code"] = "0" * 64
    s.ne(proof, chk._verify_key(chk.SELF_TEST, moved, set()),
         "an edit anywhere in the tracked code re-proves rather than trusting the last answer")
    moved = dict(keys); moved["data"] = "0" * 64
    s.ne(proof, chk._verify_key(chk.SELF_TEST, moved, set()),
         "and so does a change to the build, because the canaries are planted in the real context")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "incremental"))
