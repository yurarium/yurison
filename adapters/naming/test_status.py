#!/usr/bin/env python3
"""naming/status_items.py and integrate_status.py: which works are asked whether they are one-shots,
and how the answers reach the register.

COVERS = ['adapters/naming/status_items.py', 'adapters/naming/integrate_status.py']
"""
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import integrate_status as ist                                          # noqa: E402
import status_items as si                                               # noqa: E402
import testkit                                                          # noqa: E402

REG = """source: hand review
works:
  既に:
    verdict: 'oneshot'
    basis: 'x'
"""


def ok_answer():
    return {"verdict": "oneshot", "basis": "読切バッジがある。", "basis_en": "It carries a 読切 badge.",
            "source_kind": "platform", "source_url": "https://example.jp/w"}


def main(s):
    rows = [{"work": "太刀んぼ キルコ", "chapters": 1, "state": "unknown", "latest": "2026-10-13",
             "latest_ep": "1話", "url": "https://manga-one.com/viewer/285495",
             "sources": [{"platform": "マンガワン", "url": "https://manga-one.com/viewer/285495"}]},
            {"work": "つるこさん", "chapters": 1, "state": "oneshot", "oneshot_inferred": True,
             "latest": "2026-10-18"},
            {"work": "言われた", "chapters": 1, "state": "oneshot", "oneshot_inferred": False},
            {"work": "既に", "chapters": 1, "state": "unknown"},
            {"work": "長い", "chapters": 30, "state": "unknown"},
            {"work": "断片", "chapters": 1, "state": "unknown", "partial": True}]
    got = [r["work"] for r in si.undecided(rows, {"既に": {}}, "2026-10-18")]
    s.eq(got, ["つるこさん", "太刀んぼ キルコ"],
         "a single instalment whose status rests on nothing stated is asked about, newest first")
    it = si.item(rows[0])
    s.eq((it["instalment"], it["platforms"], it["pages"]),
         ("1話", ["マンガワン"], ["https://manga-one.com/viewer/285495"]),
         "with the instalment we hold and the page to read, once")

    loose = {"既に": {"verdict": "unsettled", "reviewed": "2026-09-01"}}
    s.check("既に" in [r["work"] for r in si.undecided(rows, loose, "2026-10-18")],
            "an unsettled verdict older than a month is asked again")
    s.check("既に" not in [r["work"] for r in si.undecided(
        rows, {"既に": {"verdict": "unsettled", "reviewed": "2026-10-10"}}, "2026-10-18")],
        "and a recent one is not")
    again = REG.replace("verdict: 'oneshot'", "verdict: 'unsettled'")
    text, written, _ = ist.integrate(again, [{**ok_answer(), "key": "既に"}], {"既に"}, "2026-10-18")
    doc = yaml.safe_load(text)["works"]
    s.eq((written, doc["既に"]["verdict"]), ([("既に", "oneshot")], "oneshot"),
         "and its new answer replaces the unsettled one")
    asked = {"太刀んぼ キルコ", "つるこさん", "黙る", "既に"}
    ok = {"key": "太刀んぼ キルコ", "verdict": "oneshot", "basis": "マンガワンの読切一覧に載っている。",
          "basis_en": "マンガワン lists it among its 読切.", "source_kind": "platform",
          "source_url": "https://manga-one.com/search/result?tag-id=81"}
    ser = {"key": "つるこさん", "verdict": "serialised", "basis": "第2話の配信予定がある。",
           "source_kind": "platform", "source_url": "https://www.sunday-webry.com/x"}
    text, written, refused = ist.integrate(REG, [ok, ser, {**ok, "key": "既に"}], asked, "2026-10-18")
    doc = yaml.safe_load(text)["works"]
    s.eq(written, [("太刀んぼ キルコ", "oneshot"), ("つるこさん", "serialised")],
         "sound verdicts are written")
    s.eq((doc["太刀んぼ キルコ"]["source"], doc["太刀んぼ キルコ"]["reviewed"]),
         ("manga-one.com", "2026-10-18"), "citing the page's host, dated")
    s.eq(dict(refused), {"既に": "already reviewed", "黙る": "no answer"},
         "a work already reviewed is never overwritten, and one left unanswered is reported")
    bad = [{**ok, "basis_en": ""}, {**ser, "verdict": "completed"}, {**ser, "source_url": ""}]
    _, written, refused = ist.integrate(REG, bad, asked, "2026-10-18")
    why = [w for _, w in refused]
    s.eq(written, [], "and an unsound one is not")
    s.check("basis_en" in why[0], "a one-shot verdict a reader is shown needs its English")
    s.check("not one of" in why[1], "the job cannot call a work completed")
    s.check("needs the page" in why[2], "and a verdict citing no page is refused")
    loose = ist.entry({"key": "x", "verdict": "unsettled", "basis": "ページが消えていた — 移動先なし"},
                      "2026-10-18")
    s.check("—" not in loose["basis"] and "source_url" not in loose,
            "an unsettled answer keeps only what it looked at, with no em dash")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "naming.status"))
