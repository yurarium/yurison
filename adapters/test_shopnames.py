#!/usr/bin/env python3
"""shopnames.py: the shop's title for each book, by ISBN, and nothing read into it."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import shopnames as sn  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/shopnames.py"]


def main(s):
    doc = {"works": [
        {"url": "https://www.cmoa.jp/title/194025/", "volumes": [
            {"title": "Qualia -Envy-", "isbn": "9784823600272"}]},
        {"url": "https://www.cmoa.jp/title/194026/", "volumes": [
            {"title": "Qualia -Jealousy-", "isbn": "978-4-8236-0028-9",
             "url": "https://www.cmoa.jp/title/194026/"}]},
        {"volumes": [{"title": "名前だけ"}, {"isbn": "9784758022217"}]},
        {"volumes": [{"title": "一つ目の名前", "isbn": "9784000000002"}]},
        {"volumes": [{"title": "二つ目の名前", "isbn": "9784000000002"}]},
    ]}
    got = sn.names(doc)
    s.eq([(r["isbn"], r["title"]) for r in got],
         [("9784823600272", "Qualia -Envy-"), ("9784823600289", "Qualia -Jealousy-")],
         "each book is named as the shop names it, keyed by its ISBN in thirteen digits")
    s.eq(got[0]["url"], "https://www.cmoa.jp/title/194025/",
         "and the listing's address stands in where the volume states none")
    s.check(all(r["isbn"] != "9784000000002" for r in got),
            "an ISBN the shop files under two titles names nothing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "shopnames"))
