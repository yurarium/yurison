#!/usr/bin/env python3
"""lexicon.py: a word is one word because somebody wrote it as one."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import lexicon as lex  # noqa: E402

COVERS = ["adapters/names/lexicon.py"]


def main(s):
    titles = ["Citrusコミックアンソロジー", "SSSS.GRIDMAN コミックアンソロジー",
              "GP-KIDS東方ファンブック", "スローライフのすすめ", "ゆりでなる♡えすぽわーる"]
    L = lex.build(titles)
    s.eq(L.get("コミックアンソロジー"), 2, "a run two titles write unbroken is attested twice")
    s.eq(L.get("ファンブック"), 1, "and one title is one attestation")
    s.check("エスポワール" not in L, "a hiragana run attests nothing about katakana, being unread")

    # THE POINT OF THE FLOOR. A run seen once may be a typo or a one-off; a run seen often is a word.
    s.check(lex.known("コミックアンソロジー", L, floor=2), "a well attested run passes a floor of two")
    s.check(not lex.known("ファンブック", L, floor=2), "and a run seen once does not")

    # HIRAGANA IS LOOKED UP AS KATAKANA, which is the whole reason this exists.
    s.check(lex.known("こみっくあんそろじー", L), "a hiragana spelling finds its katakana word")

    # What attests nothing.
    s.eq(lex.runs("ーーーー"), [], "a run of one repeated character is not a word")
    s.eq(lex.runs("アイ"), [], "and a run too short to be worth claiming is not collected")
    s.eq(lex.build([]), {}, "no titles, no lexicon")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
