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

    # A TITLE THE CORPUS HOLDS WAITS FOR A PERSON. MADB credits nobody on an anthology, so the
    # title is all that shows a new record is a book BOOK☆WALKER already listed.
    go, back = mint.titled_like_held(
        [{"work": "セフレ沼から抜け出せないっ!百合えっちアンソロジー"}, {"work": "新しい本"}],
        ["セフレ沼から抜け出せないっ！百合えっちアンソロジー"])
    s.eq(([r["work"] for r in go], [t for _r, t in back]),
         (["新しい本"], ["セフレ沼から抜け出せないっ！百合えっちアンソロジー"]),
         "a record titled like a held work is held back, across the width of its punctuation")

    # JOINS FIRST: a record the platform route placed goes to the work holding that page.
    import yaml
    entries = yaml.safe_load(REG)["works"]
    got = mint.as_attachments({"retrieved": "2026-11-01", "joins": [
        {"platform_url": "https://a/1", "madb_work_id": "C1", "agreement": "agreed"},
        {"platform_url": "https://a/1", "madb_work_id": "C2", "agreement": "differs"},
        {"platform_url": "https://nobody/", "madb_work_id": "C3", "agreement": "agreed"}]}, entries)
    s.eq([(j["anchor"], j["id"]) for j in got["joins"]], [("madb:C1", "w00009")],
         "a platform join lands on the work holding the page; a disagreeing or unplaced one does not")
    shaped = {"joins": [{"anchor": "madb:C9", "id": "w00009", "basis": "b"}]}
    s.eq(mint.as_attachments(shaped, entries), shaped, "a join already naming its anchor passes as is")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "naming.mint"))
