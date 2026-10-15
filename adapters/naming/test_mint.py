#!/usr/bin/env python3
"""naming/mint.py: which awaiting works are minted without a person, and how.

COVERS = ['adapters/naming/mint.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit                                                          # noqa: E402
import mint                                                             # noqa: E402

REG = """works:
  - id: w00001
    title: null
    anchors:
      - "madb:bw-held"
  - id: w00009
    title: "x"
    anchors:
      - "web:https://a/1"
related:
  - a: w00001
    b: w00009
"""


def main(s):
    rows = [{"work": "新しい本", "records": ["bw-new"], "addresses": [], "platforms": []},
            {"work": "連載", "records": ["bw-2"], "addresses": ["https://p/1"], "platforms": ["P"]},
            {"work": "既に", "records": ["bw-held"], "addresses": [], "platforms": []},
            {"work": "記録なし", "records": [], "addresses": [], "platforms": []}]
    ok = mint.mintable(rows)
    s.eq([r["work"] for r in ok], ["新しい本", "既に"],
         "a print-only row is mintable; one with a web address or no record is not")

    text, made = mint.mint(REG, ok)
    s.eq(made, [("w00010", "新しい本")], "the next id after the highest, for the new record only")
    s.check('  - id: w00010\n    title: null\n    anchors:\n      - "madb:bw-new"\n' in text,
            "anchored on its record and titled by it, the way every print work is")
    s.check(text.index("w00010") < text.index("\nrelated:"), "written before the related section")
    s.check(text.count('"madb:bw-held"') == 1, "an anchor another entry holds is not minted twice")
    s.eq(mint.mint(REG, []), (REG, []), "nothing to mint leaves the registry as it was")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "naming.mint"))
