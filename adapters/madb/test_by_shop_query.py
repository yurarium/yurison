#!/usr/bin/env python3
"""by_shop_query.py: the shop proposes a work, and the bibliography still has to agree on a person."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit                                                                 # noqa: E402
from madb import by_shop_query, by_title                                       # noqa: E402

COVERS = ["adapters/madb/by_shop_query.py"]


def rec(name, creator, publisher, brand, date, isbn):
    return {"schema:name": name, "schema:creator": creator, "schema:publisher": publisher,
            "schema:brand": brand, "schema:datePublished": date, "schema:isbn": isbn,
            "schema:identifier": isbn}


# Quoted from metadata101.json of MADB release 1.2.18, trimmed to the fields read. The catalogue
# writes the title without the imprint the shop appends to it.
KONKAFE = [rec("コンカフェ嬢は恋を着る", "[著]卯花りりか", "芳文社", "FUZコミックス",
               "2024-11", "9784832290518"),
           rec("コンカフェ嬢は恋を着る", "[著]卯花りりか", "芳文社", "FUZコミックス",
               "2025-04", "9784832291270")]

# The counter-case, and the reason a shop hit is not enough on its own. Two books share this folded
# title and neither is the work: 大友克洋's MEMORIES from 講談社 and a 1991 大陸書房 book.
MEMORIES = [rec("MEMORIES", "[著]大友克洋", "講談社", "", "1990-11", "4063196658"),
            rec("Memories", "[著]つづき春", "大陸書房", "MENUETT COMICS", "1991-05", "4803333181")]

# A capture row the shop and the database agree about, in the shape adapters/shopquery/capture.py
# writes. The shop appends the imprint to the series name and prints the role after the credit.
AGREED = {"work_url": "https://comic-fuz.com/manga/3455", "id": "w00537",
          "work": "コンカフェ嬢は恋を着る", "author": "卯花りりか", "platform": "COMIC FUZ",
          "query": "author",
          "hits": [{"series_url": "https://bookwalker.jp/series/490418/list/",
                    "title_listed": "コンカフェ嬢は恋を着る（ＦＵＺコミックス）",
                    "shop_author": "卯花りりか(著)", "imprint": "ＦＵＺコミックス",
                    "publisher": "芳文社", "volumes_stated": 3, "completed_marker": True,
                    "agreement": "creator"}]}

# The same shape for a hit the shop matched on the title alone. by_shop_query must not read it.
TITLE_ONLY = {"work_url": "https://example.jp/x", "id": "w09999", "work": "Memories",
              "author": "菅野マナミ",
              "hits": [{"series_url": "https://bookwalker.jp/series/1/list/",
                        "title_listed": "Memories", "shop_author": "大友克洋(著)",
                        "publisher": "講談社", "agreement": "title-only"}]}

# A row the shop answered nothing about. Neither list may take it.
NO_HIT = {"work_url": "https://example.jp/y", "id": "w09998", "work": "誰も知らない",
          "author": "誰か", "hits": [], "notes": ["author query returned no title this database "
                                                  "recognises"]}


def capture(tmp, works):
    import json
    p = pathlib.Path(tmp) / "shop-query.yaml"
    p.write_text(json.dumps({"source": "bookwalker.jp", "works": works}, ensure_ascii=False))
    return [str(p)]


def main(s):
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        paths = capture(tmp, [AGREED, TITLE_ONLY, NO_HIT])
        got = by_shop_query.leads(paths)
        s.eq(sorted(got), ["https://comic-fuz.com/manga/3455"],
             "only the row the shop and this database agree about is a lead")
        s.eq(got["https://comic-fuz.com/manga/3455"]["id"], "w00537",
             "keyed on the platform address, carrying the work identifier")

        only = by_shop_query.title_only(paths)
        s.eq([r["work"] for r in only], ["Memories"],
             "a title-only hit is recorded so the refusal is visible")
        s.eq(only[0]["shop_author"], "大友克洋(著)",
             "with both credits, so the question can be settled by looking")
        s.eq([r["work"] for r in by_shop_query.title_only(capture(tmp, [NO_HIT]))], [],
             "and a work the shop stocks nothing for is neither a lead nor a candidate")

    lead = got["https://comic-fuz.com/manga/3455"]
    s.check("卯花りりか" in by_shop_query.credit(lead),
            "both sides of the agreement are offered to the bibliography")
    keys = by_shop_query.titles(lead)
    s.check(by_title.keys("コンカフェ嬢は恋を着る") <= keys,
            "the platform's spelling is one of the forms looked up")
    s.check(by_title.keys("コンカフェ嬢は恋を着る（ＦＵＺコミックス）") <= keys,
            "and the shop's, whose appended imprint folds onto the same key")
    s.check("コンカフェ嬢は恋を着る" in keys,
            "so the catalogue's own bare spelling is what both arrive at")

    index = by_title.index(KONKAFE + MEMORIES)
    vols = by_shop_query.answer(lead, index)
    s.eq(len(vols), 2, "the bibliography answers with the volumes it holds under that name")
    s.eq({v["schema:isbn"] for v in vols}, {"9784832290518", "9784832291270"},
         "and they are the right ones")

    # THE COUNTER-CASE. The shop's own agreement does not carry into the bibliography. This lead
    # matches two catalogue records by title and neither names anybody it credits, so nothing is
    # written and the work is reported as unanswered.
    wrong = dict(AGREED, work="Memories", author="菅野マナミ",
                 hits=[dict(AGREED["hits"][0], title_listed="Memories",
                            shop_author="菅野マナミ(著)")])
    s.eq(by_shop_query.answer(wrong, index), [],
         "a title matching the catalogue with no person agreeing is refused")

    # And the shape of the refusal is the person and not the title: give the same lead a credit the
    # catalogue does share and it joins, which is what proves the title was never doing the work.
    right = dict(wrong, author="大友克洋", hits=[dict(wrong["hits"][0], shop_author="大友克洋(著)")])
    s.eq(len(by_shop_query.answer(right, index)), 1,
         "the same title joins once a person agrees, so the person is what decides")

    lines = by_shop_query.identified_by(lead, "2026-08-07")
    s.check(any("bookwalker.jp" in x for x in lines), "the record names the shop that was asked")
    s.check(any("series/490418" in x for x in lines), "and the answer it gave")
    s.eq(by_shop_query.LABEL_SHOP[0], "none",
         "stock is not publisher-side labelling, so the axis stays none (DEFINITIONS §4)")


if __name__ == "__main__":
    suite = testkit.Suite("madb/by_shop_query.py")
    main(suite)
    raise SystemExit(suite.report())
