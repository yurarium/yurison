#!/usr/bin/env python3
"""cmoa_shelf.py: one re-read of the shop's 百合・GL shelf, folded into what is held.

COVERS = ['adapters/cmoa_shelf.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import cmoa_shelf as cs                                                 # noqa: E402

ROW = {"title_id": "1", "title": "あの子", "authors": ["誰か"], "author_ids": ["9"],
       "genre": "青年マンガ", "labels": ["百合姫コミックス"], "completed": True,
       "url": "https://www.cmoa.jp/title/1/"}


def main(s):
    e = cs.entry(ROW, "2026-10-16")
    s.eq((e["cmoa_title_id"], e["label"], e["completed"], e["seen"]),
         ("1", ["百合姫コミックス"], True, "2026-10-16"), "a row becomes the document's own shape")
    s.check("publisher" not in e, "the genre pass names no publisher, which the merge then keeps")
    e = cs.entry(ROW, "2026-10-16", publisher="一迅社")
    s.eq((e["publisher"], e["doujin"]), ("一迅社", False), "the publisher pass names it")
    s.eq(cs.entry(dict(ROW, title="あの子【棒消し修正版】"), "2026-10-16"), None,
         "a censored edition is not written")

    # WALKED UNTIL THE SHOP'S OWN COUNT, or an empty page, whichever comes first.
    asked = []
    book = {1: "p1", 2: "p2", 3: "p3"}
    real_rows, real_total = cs.cmoa.rows, cs.cmoa.total
    cs.cmoa.rows = lambda h: [{"title_id": h}] * 2 if h else []
    cs.cmoa.total = lambda h: 4
    try:
        stated, rows = cs.pages(lambda u: (asked.append(u), book.get(int(u)))[1], str)
    finally:
        cs.cmoa.rows, cs.cmoa.total = real_rows, real_total
    s.eq((stated, len(rows), asked), (4, 4, ["1", "2"]), "it stops once the stated total is read")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "cmoa_shelf"))
