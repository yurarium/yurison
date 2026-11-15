#!/usr/bin/env python3
"""naming/induct.py: a web work is minted unless it may be one we hold, and its series feed comes too.

COVERS = ['adapters/naming/induct.py']
"""
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import induct as ni                                                     # noqa: E402

REG = """works:
  - id: w00010
    title: "古い作品"
    anchors:
      - "web:https://ichicomi.com/episode/1"
related:
  - a: w00010
    b: w00010
"""
EP = "https://ichicomi.com/episode/99"
PAGE = ('<link rel="alternate" type="application/atom+xml" '
        'href="https://ichicomi.com/atom/series/555" />')


def main(s):
    held = [{"id": "w00010", "work": "古い作品", "author": "甲"},
            {"id": "w00011", "work": "月夜の恋　第二部", "author": "乙"}]
    new = {"work": "だって恋は月夜に", "author": "丙", "addresses": [EP]}
    text, made, doubts = ni.induct(REG, [new], held, {EP: PAGE}, "2026-10-16")
    doc = yaml.safe_load(text)
    s.eq(made, [("w00011", "だって恋は月夜に")], "a new web work is minted on the next identifier")
    w = doc["works"][-1]
    s.eq(w["anchors"], [f"web:{EP}", "web:https://ichicomi.com/atom/series/555"],
         "on its address, and on the series feed its chapter page links")
    s.check("links its own series feed" in w["attached"][0]["basis"]
            and str(w["attached"][0]["retrieved"]) == "2026-10-16",
            "the feed is attached with the page it was read from, and when")
    s.eq(list(doc["related"][0]), ["a", "b"], "and the entry goes before related:, in works")

    s.eq(ni.induct(REG, [{**new, "work": "古い作品 "}], held, {}, "2026-10-16")[2][0][1],
         "w00010 '古い作品', the same title", "a title we hold is held for a person, not minted")
    s.check(ni.induct(REG, [{**new, "work": "月夜の恋　第三部", "author": "乙"}], held, {},
                      "2026-10-16")[1] == [],
            "and so is one by the same author starting the way a held one does")
    s.check(ni.induct(REG, [{**new, "work": "月夜の恋　第三部", "author": "丁"}], held, {},
                      "2026-10-16")[1] != [],
            "but a shared start by another author is not doubt")
    taken = {**new, "addresses": ["https://ichicomi.com/episode/1"]}
    s.eq(ni.induct(REG, [taken], [], {}, "2026-10-16")[1], [],
         "an address already another work's anchor is refused")

    # A CHAPTER ADDRESS UNDER ITS WORK'S OWN is anchored at both, since the build asks the second.
    ep2 = "https://pocket.shonenmagazine.com/title/03368/episode/446347"
    ep1 = "https://pocket.shonenmagazine.com/title/03368/episode/446346"
    mp = {"work": "瑠夏と杏珠の逃避行", "author": "清水幸", "addresses": [ep2]}
    text, made, _ = ni.induct(REG, [mp], [], {}, "2026-11-14")
    w = yaml.safe_load(text)["works"][-1]
    s.eq(w["anchors"], [f"web:{ep2}", "web:https://pocket.shonenmagazine.com/title/03368"],
         "a マガポケ chapter is anchored at the work's own address as well")
    s.eq((w.get("attached") or [{}])[0].get("anchor"), "web:https://pocket.shonenmagazine.com/title/03368",
         "with the reduction stated as its basis")
    from facts import identity
    s.eq(identity.for_row({"url": ep1, "work": mp["work"]}, identity.index(yaml.safe_load(text)["works"])),
         made[0][0], "so the build finds the work from any of its chapters")
    s.eq(ni.induct(text, [{**mp, "addresses": [ep1]}], [], {}, "2026-11-15")[1], [],
         "and the next chapter of a work minted already is not minted again")
    s.eq(ni.work_addresses([EP]), [], "an address with no work inside it is left as it is")
    s.eq(ni.series_feed(EP, PAGE.replace("ichicomi.com/atom", "other.com/atom")), None,
         "a feed on another host is not this chapter's series")
    s.eq(ni.series_feed("https://ichicomi.com/title/1", PAGE), None,
         "and only a chapter page is read for one")
    ruled_in = {**new, "work": "認めた"}
    s.eq(ni.inductable([new, {"work": "印刷", "addresses": []}, {**new, "work": "保留"}, ruled_in],
                       {"保留": {"disposition": "held"}, "認めた": {"disposition": "in"}}),
         [new, ruled_in], "a web row nobody has ruled on is considered, and one ruled in; one held is not")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "naming.induct"))
