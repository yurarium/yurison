#!/usr/bin/env python3
"""adapters/relational/emit: a corpus file built out of tables rather than beside them.

COVERS = ['adapters/relational/emit.py']

WHAT THIS HAS TO ASSERT AND WHY IT IS BYTE EQUALITY. An emitter that produces something ALMOST the
same as what the compiler produced is a second producer with a bug, which is the fault STORE-PLAN §6
exists to end rather than to introduce. Comparing parsed objects would let key order drift; comparing
text does not.

THE COMPARISON IS AGAINST THE SHIPPED FILE, which is available because §6 moves one domain at a time
and the file is still on disk from the run that wrote it. That window is the whole reason the plan
refuses a cutover: a domain moved with nothing to compare against is a domain moved on faith.

IT CAUGHT TWO REAL FAULTS on the first comparison, both taken on in §5h. 130 credits had their RAW
title filed as a spelling, where the registry answers for the FOLD of it, so `二三　夏一` shipped
beside `二三夏一`. And `アンソロジー` is a credit whose spelling was withdrawn and whose folded title
the registry still answers for, which the loader was dropping. Neither is visible from either side
alone.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit                                                          # noqa: E402
import relational                                                       # noqa: E402
from relational import emit                                             # noqa: E402

BUILD = pathlib.Path(__file__).resolve().parents[2] / "data" / "build"


def main(s):
    shipped = BUILD / "credits.json"
    if not shipped.exists():
        s.check(False, "the build must be present for an emitted file to be compared against one")
        return
    want = json.loads(shipped.read_text(encoding="utf-8"))

    # THE STORE IS BUILT FROM THE COMPILER'S ROWS, which is the direction §6 turns on. Reading
    # `data/build` here would prove only that the store round-trips its own input.
    source = {n: json.loads((BUILD / f"{n}.json").read_text(encoding="utf-8"))
              for n in ("series", "works") if (BUILD / f"{n}.json").exists()}
    db, _counts, refused = relational.build(path=":memory:", source=source)
    s.eq(refused, [], "the store takes the compiler's rows with nothing refused")

    got = emit.credits(db, want["generated"])
    s.eq(emit.as_text(got), emit.as_text(want),
         "`credits.json` emitted from the store is what the compiler wrote, byte for byte")

    # AND THE PARTS THAT WOULD BE EASY TO GET ALMOST RIGHT, named so a failure says which.
    s.eq(list(got), list(want), "the keys are in the file's own order")
    s.eq(len(got["credits"]), want["count"], "and the count is of what is actually there")
    roled = [(c, w) for c, v in got["credits"].items()
             for w in (v.get("works") or []) if w.get("roles")]
    s.check(roled, "AN EDGE CARRIES ITS ROLE, which the store held as 4,165 NULLs until §6 read "
                   "`roles` where the loader had asked for `role`")
    s.check(any(v.get("homophones") for v in got["credits"].values()),
            "a ruling that two credits are different people reaches the page from the store")
    s.check(any(v.get("kind") for v in got["credits"].values()),
            "and the registry's finer word for what a credit is, which `shape` cannot carry")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
