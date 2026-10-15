#!/usr/bin/env python3
"""remaining/targets.py: which listed works the remaining route is asked to reach.

COVERS = ['adapters/remaining/targets.py']
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import targets as rt                                                    # noqa: E402

M = "https://pocket.shonenmagazine.com/title/"


def main(s):
    nobody = lambda u: False                                             # noqa: E731
    cands = [{"title": "A", "platforms": ["X"], "urls": ["https://x.example/a"]},
             {"title": "B", "platforms": ["X"], "urls": ["https://x.example/b"]},
             {"title": "C", "platforms": ["P", "M"], "urls": ["https://p.example/c", M + "03338"]},
             {"title": "D", "platforms": ["F"], "urls": ["https://comic-fuz.com/manga/1"]}]

    got = rt.targets(cands, {}, nobody)
    s.eq([r["title"] for r in got], ["A", "B", "C", "D"], "a work nothing holds is a target")
    s.eq(got[2]["platform"], "P", "the platform is the one named beside the address used")

    n = rt.norm_work
    held = {n("A"): {"https://x.example/a"}, n("B"): {""}}
    s.eq([r["title"] for r in rt.targets(cands, held, nobody)], ["C", "D"],
         "a work held at its own address, or at none, is reached")

    # 怨霊日和's shape: the capture holds the one-shot's page, and the candidate is the serial's.
    serial = [{"title": "C", "platforms": ["M"], "urls": [M + "03338"]}]
    s.eq([r["title"] for r in rt.targets(serial, {n("C"): {M + "03125"}}, nobody)], ["C"],
         "a work held only at another work's page on the same site is still a target")
    s.eq(rt.targets(cands[2:3], {n("C"): {M + "03125"}}, nobody), [],
         "and one with an address on another site cannot be told apart, so it is reached")

    s.eq([r["title"] for r in rt.targets(cands, {}, lambda u: "comic-fuz.com" in u)], ["A", "B", "C"],
         "a host a dedicated adapter reads is left to it")
    s.eq(rt.targets([{"title": "E", "urls": []}], {}, nobody), [], "a candidate with no address has no target")

    # ITS OWN ROUTE'S CAPTURE IS NOT A HOLDING, so a work it reached stays asked.
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "webpages").mkdir()
        (root / "webpages/remaining.yaml").write_text("works:\n  - work_title: A\n    url: https://x.example/a\n")
        (root / "webpages/other.yaml").write_text("works:\n  - work_title: B\n    url: https://x.example/b\n")
        held = rt._candidates.held_at(root, skip=rt.OWN)
        s.eq([r["title"] for r in rt.targets(cands[:2], held, nobody)], ["A"],
             "what the remaining route holds keeps its target; another capture's holding does not")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "remaining.targets"))
