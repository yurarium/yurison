#!/usr/bin/env python3
"""naming/worklist.py: what the naming job is handed, and what it is not.

COVERS = ['adapters/naming/worklist.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import worklist as nq                                                     # noqa: E402


def main(s):
    series = [{"id": "w1", "work": "あの子", "work_en": {"basis": "romaji"}, "latest": "2026-10-01"},
              {"id": "w2", "work": "この子", "work_en": {"basis": "romaji"}, "latest": "2026-10-09"},
              {"id": "w3", "work": "その子", "work_en": {"basis": "translated"}, "latest": "2026-10-10"},
              {"id": "w4", "work": "どの子", "work_en": {"basis": "romaji"}, "latest": "2026-10-11"}]
    got = nq.untitled(series, decided={"どの子"})
    s.eq([w["id"] for w in got], ["w2", "w1"],
         "a romanised title nobody decided is queued, newest first; a decided or named one is not")

    rel = [{"work": "新作", "plat_name": "P", "url": "https://p/1"},
           {"work": "新作", "plat_name": "P", "url": "https://p/2"},
           {"work": "あの子", "plat_name": "P", "url": "https://p/3"},
           {"work": "却下", "plat_name": "Q", "url": "https://q/1"}]
    ruled = {nq.feedgap.textnorm.norm("却下"): {"disposition": "out"}}
    got = nq.unruled(rel, series, ruled)
    s.eq([(w["work"], w["platforms"], len(w["urls"])) for w in got], [("新作", ["P"], 2)],
         "a work the feed names, held by nothing and ruled on by nobody, is queued once")

    held = {nq.feedgap.textnorm.norm("保留"): {"disposition": "held"}}
    s.eq([w["work"] for w in nq.unruled_awaiting([{"work": "保留"}, {"work": "新規"}], held)], ["新規"],
         "a work the owner holds is left out of the job's queue")
    s.check("Nothing to do" in nq.render({"awaiting": [], "untitled": [], "unruled": []}),
            "an empty queue says so, which is what keeps the job from starting")
    md = nq.render({"awaiting": [{"work": "私の魂", "platforms": ["COMICリュウ"], "addresses": ["u"]}],
                    "untitled": [], "unruled": []})
    s.check("私の魂" in md and "## Works awaiting an identifier" in md, "a work to induct is listed")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "naming.worklist"))
