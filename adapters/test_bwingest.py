#!/usr/bin/env python3
"""bwingest.py: a shop that states no ISBN, joined on a title and reviewed after."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bwingest as bw  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/bwingest.py"]


def work(**kw):
    base = {"shop_id": "u1", "url": "https://bookwalker.jp/de-u1/", "publisher": "一迅社",
            "imprint": "百合姫コミックス", "authors": ["袴田めら"], "completed": True,
            "first_publication": {"venue": "一迅社", "date_basis": "no-print-edition"},
            "volumes": [
                {"title": "初恋姉妹 1", "series_title": "初恋姉妹", "printed": "2014-02-14",
                 "delivered": "2016-08-01"},
                {"title": "初恋姉妹 2", "series_title": "初恋姉妹", "delivered": "2016-08-01"}]}
    base.update(kw)
    return base


def main(s):
    r = bw.record(work(), "2026-08-06")
    s.eq(r["title"], "初恋姉妹", "the series name is the work's title where the shop groups it")
    s.eq(r["volume_count"], 2, "with as many volumes as the shop showed")
    s.eq(r["first_published"], "2014-02-14",
         "dated by the print edition the file was made from, which is a publication of the work")

    # THE DELIVERY DATE IS NEVER THE PUBLICATION DATE. It is the day the shop began selling a file
    # and runs years late on a back catalogue: 2016 for a 2014 book, above.
    s.eq(r["volumes"][0]["delivered"], "2016-08-01", "recorded, because it is a fact about the shop")
    s.eq(r["volumes"][1].get("published"), None, "and never promoted where no print date is stated")

    undated = bw.record(work(volumes=[{"title": "x", "series_title": "x", "delivered": "2020-01-01"}]),
                        "2026-08-06")
    s.eq(undated["first_published"], None, "a work the shop never dates is undated")
    s.eq(undated["date_basis"], "no-print-edition", "and says why, rather than borrowing a date")

    # A SINGLE VOLUME IS ITS OWN TITLE. 528 rows have no series grouping because the work is one
    # book, and its volume title is the work's name.
    one = bw.record(work(volumes=[{"title": "結婚するってよ", "series_title": None}]), "2026-08-06")
    s.eq(one["title"], "結婚するってよ", "a lone volume's title is the work's title")
    s.eq(one["volumes"][0]["number"], None, "and it carries no volume number, having no siblings")

    # A multi-volume work with no series name loses the number from the title, not from the words.
    two = bw.record(work(volumes=[{"title": "ふたりの話 1", "series_title": None},
                                  {"title": "ふたりの話 2", "series_title": None}]), "2026-08-06")
    s.eq(two["title"], "ふたりの話", "a volume number is stripped from a borrowed title")

    # NOTHING CAPTURED IS NOT A WORK WITHOUT A NAME. 284 rows read no volumes at all.
    s.eq(bw.record(work(volumes=[]), "2026-08-06"), None,
         "a work the capture could not open is skipped rather than invented")

    # THE EDITION LABEL IS NOT PART OF THE NAME. BOOK☆WALKER writes it into the volume title on
    # 771 of 2,093 works, and leaving it there put a Latin imprint inside a Japanese reading:
    # ヒメチャン ワ オモイ オンナ （fuz コミックス）.
    s.eq(bw.strip_imprint("雪解けとアガパンサス（電撃コミックスNEXT）"),
         ("雪解けとアガパンサス", "電撃コミックスNEXT"), "the label comes off and is kept as the imprint")
    s.eq(bw.strip_imprint("ふつうの話")[0], "ふつうの話", "a title without one is untouched")
    s.eq(bw.strip_imprint("わたしが恋人になれるわけないじゃん（※ムリじゃなかった!?）")[0],
         "わたしが恋人になれるわけないじゃん（※ムリじゃなかった!?）",
         "and a bracket that is part of the title is not an edition label")
    lab = bw.record(work(imprint=None, volumes=[{"title": "作品名（百合姫コミックス）",
                                                 "series_title": "作品名（百合姫コミックス）"}]),
                    "2026-08-06")
    s.eq((lab["title"], lab["imprint"]), ("作品名", "百合姫コミックス"),
         "so a record takes the imprint from the title where the shop states none")

    # A MATCHING TITLE DECIDES WHICH PILE, NEVER A MERGE. トワ・エ・モア is one title over two
    # unrelated works, which is why this cannot be allowed to join anything by itself.
    recs = [{"_key": "a", "title": "A"}, {"_key": "b", "title": "B"}]
    new, review = bw.split(recs, {"b"})
    s.eq([x["title"] for x in new], ["A"], "a title we do not hold is a new work")
    s.eq([x["title"] for x in review], ["B"], "and one we do hold waits for a person")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
