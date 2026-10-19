#!/usr/bin/env python3
"""budgetkind.py: which budgets the corpus grows, and the reason a rise there is accepted with.

COVERS = ['adapters/budgetkind.py']
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import budgetkind as bk                                                 # noqa: E402
import testkit                                                          # noqa: E402


def main(s):
    s.eq(bk.kind("works showing a romanisation"), "arrival", "a queue new works join is an arrival")
    s.eq(bk.kind("works whose first publication country is unattested"), "report",
         "a number nobody is working in a direction is a report")
    s.eq(bk.kind("a budget written tomorrow"), "regression", "and anything unnamed stays strict")
    s.check(not bk.ARRIVAL & bk.REPORT, "no budget is two kinds")

    with tempfile.TemporaryDirectory() as d:
        led = pathlib.Path(d) / "arrivals.jsonl"
        first, _ = bk.accept([("uncertain readings", 63, 65)], {"works": 3000, "credits": 2400},
                          ledger=led, today="2026-10-16")
        s.check("the first rise recorded for it" in first[0] and "+2" in first[0],
                "the first acceptance says how far it rose and that nothing came before it")
        again, _ = bk.accept([("uncertain readings", 65, 66)], {"works": 3012, "credits": 2405},
                          ledger=led, today="2026-10-17")
        s.check("+12 works, +5 credits" in again[0],
                "a later one says how far the corpus grew since the last")
        ok, refused = bk.accept([("author names romanised as one word", 1268, 1284)],
                                {"works": 3014, "credits": 2408}, ledger=led, today="2026-10-19")
        s.eq((ok, [r[0] for r in refused]), ([], ["author names romanised as one word"]),
             "a rise of 16 while the corpus gained five is refused as a regression, not accepted")
        ok, _ = bk.accept([("author readings no source states", 500, 501)],
                          {"works": 3014, "credits": 2408}, ledger=led, today="2026-10-19")
        s.check(len(ok) == 1, "and a budget with no rise of its own is held to the latest baseline")
        lines = [json.loads(x) for x in led.read_text().splitlines()][:2]
        s.eq([(x["date"], x["was"], x["now"]) for x in lines],
             [("2026-10-16", 63, 65), ("2026-10-17", 65, 66)], "each acceptance is one ledger line")
        s.eq(bk.accept([], {}, ledger=pathlib.Path(d) / "none.jsonl"), ([], []),
             "and accepting nothing writes nothing")
        s.check(not (pathlib.Path(d) / "none.jsonl").exists(), "not even an empty file")

    ctx = {"identity": [{"id": "w1"}, {"id": "w2", "merged_into": "w1"}],
           "credits": {"credits": [{"id": "c1"}, {"id": "c2"}]}}
    s.eq(bk.corpus_of(ctx), {"works": 1, "credits": 2}, "the corpus is the live registry entries")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "budgetkind"))
