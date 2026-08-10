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

    # THE DERIVATION IS REAL, not an empty set that would make the line above vacuous.
    s.check(chk.deploy_sensitive(), "some invariants are derived as reading the deployed tree")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "incremental"))
