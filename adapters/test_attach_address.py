#!/usr/bin/env python3
"""attach_address.py: one address joins one work, its reason with it, and nothing else moves.

COVERS = ['adapters/attach_address.py']
"""
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import attach_address as aa                                             # noqa: E402
import testkit                                                          # noqa: E402

REG = """generated: 2026-08-13
works:
  - id: w00002
    title: "二"
    anchors:
      - "web:https://b.example/2"
  - id: w00001
    title: "一"
    anchors:
      - "web:https://a.example/1"
related:
"""


def main(s):
    text, err = aa.change(REG, "web:https://c.example/1", "w00001", "the same credits", "2026-10-16")
    doc = yaml.safe_load(text)
    one = next(w for w in doc["works"] if w["id"] == "w00001")
    s.eq((err, one["anchors"][-1], one["attached"][0]["basis"]),
         (None, "web:https://c.example/1", "the same credits"),
         "the address joins the work with its reason")
    s.eq([w["id"] for w in doc["works"]], ["w00002", "w00001"],
         "and the registry keeps its order, so the diff is the attachment")
    s.eq(len(doc["works"]), 2, "and nothing is minted")
    s.check("already held by w00002" in aa.change(REG, "web:https://b.example/2", "w00001", "x")[1],
            "an address another work holds is a merge, and refused")
    s.check(aa.change(REG, "web:https://c.example/1", "w00001", " ")[1],
            "a join with no basis is refused")
    s.check(aa.change(REG, "https://c.example/1", "w00001", "x")[1],
            "and so is a string that is not an anchor")
    s.check("w00009 is not in the registry" in aa.change(REG, "web:x", "w00009", "x")[1],
            "and an identifier the registry does not hold")
    gone, err = aa.change(REG, "web:https://b.example/2", None, "another work by its credits",
                          "2026-10-16")
    two = next(w for w in yaml.safe_load(gone)["works"] if w["id"] == "w00002")
    s.check(err is None and "web:https://b.example/2" not in two["anchors"] and two["detached"],
            "a detachment takes the address off and records why it must not come back")

    merged, err = aa.merge(REG, "w00002", "w00001", "the platform moved the story into the work")
    one = next(w for w in yaml.safe_load(merged)["works"] if w["id"] == "w00001")
    two = next(w for w in yaml.safe_load(merged)["works"] if w["id"] == "w00002")
    s.check(err is None and two["merged_into"] == "w00001" and "web:https://b.example/2" in one["anchors"],
            "a merge retires one work into the other, which answers to its address")
    s.check(aa.merge(merged, "w00002", "w00001", "again")[1], "a retired work is not merged twice")
    s.check(aa.merge(REG, "w00002", "w00001", "")[1], "and a merge with no basis is refused")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "attach_address"))
