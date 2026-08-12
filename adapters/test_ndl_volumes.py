#!/usr/bin/env python3
"""ndl_volumes.py: the ISBNs no ISBN-keyed catalogue can reach.

COVERS = ['adapters/ndl_volumes.py']

WHAT THIS HAS TO PROVE is that the pass fills a silence and never argues with a catalogue. Every
row it can reach holds no ISBN by definition, and a row that holds one was answered by a source
keyed on it; a second opinion about a printed book is `isbndate.resolve`'s question and not this
one's. So the cases below are the fill, the refusal to overwrite, and the join.

Nothing here reaches a network: the replies are written out in the shape the served API returns.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ndl_volumes as nv                                                # noqa: E402
import testkit                                                          # noqa: E402


def item(title, creator, issued, isbn, vol=""):
    return (f"<item><title>{title}</title><dc:title>{title}</dc:title>"
            f"<dc:creator>{creator}</dc:creator><dcndl:volume>{vol}</dcndl:volume>"
            f"<dc:publisher>スクウェア・エニックス</dc:publisher>"
            f"<dcterms:issued>{issued}</dcterms:issued><dcndl:genre>漫画</dcndl:genre>"
            f'<dc:identifier xsi:type="dcndl:ISBN">{isbn}</dc:identifier></item>')


# MURCIÉLAGO as NDL served it on 2026-08-12: the name punctuated `よしむら, かな`, the volumes MADB
# stops short of, and the spin-off the same search returns.
MURCIELAGO = "<channel>" + "".join([
    item("Murciélago", "よしむら, かな", "2021.10", "978-4-7575-7538-7", "20"),
    item("Murciélago", "よしむら, かな", "2022.3", "978-4-7575-7835-7", "21"),
    item("Murciélago", "よしむら, かな", "2023.4", "978-4-7575-8534-8", "23"),
    item("アラーニァ : murciélago byproduct", "よしむら, かな", "2018.6", "978-4-7575-5761-1", "1"),
    item("カラクムルにおける「王朝交替」について", "佐藤,孝裕", "2019.3", "978-0-0000-0000-1"),
])


def main(s):
    got = nv.record(MURCIELAGO, "よしむらかな")
    s.eq(sorted(v["volume"] for v in got), ["1", "20", "21", "23"],
         "the volumes NDL holds under this author, the spin-off's own volume 1 among them")
    s.eq([v["published"] for v in got if v["volume"] == "21"], ["2022-03"],
         "READ INTO THE CORPUS'S FORM; NDL writes 2022.3 and `openbd.enrich.pubdate` reads that as "
         "nothing, which is why the shape a source writes is normalised where its quirks live")
    s.check(all("佐藤" not in (v["title"] or "") for v in got),
            "and a paper on Calakmul's dynastic succession is not a volume of this work")

    # ── THE FILL, WHICH IS THE WHOLE POINT ────────────────────────────────────────────────────
    #
    # MADB holds MURCIÉLAGO to volume 20 and the rows past it come from BOOK☆WALKER, which states
    # no ISBN on any of 5,968 volumes read. Those rows can reach no ISBN-keyed catalogue at all.
    vols = [{"number": "20", "isbn": "9784757575387", "published": "2021-10"},
            {"number": "21", "delivered": "2022-03-25"},
            {"number": "23", "delivered": "2023-04-25"},
            {"number": "29", "delivered": "2026-07-24"}]
    s.eq(nv.apply(got, vols), 2, "the two rows NDL answers for and the corpus could not")
    s.eq(vols[1]["isbn"], "978-4-7575-7835-7", "volume 21 gains the ISBN")
    s.eq(vols[1]["published"], "2022-03", "and the date, which the ISBN would have fetched anyway")
    s.eq(vols[1]["published_basis"], "national-library", "saying where it came from")
    s.check("isbn" not in vols[3],
            "AND VOLUME 29 IS LEFT ALONE, because NDL lags the newest volume: the shop delivered "
            "it in July and the catalogue holds to 28. A pass that invented one would be worse "
            "than a pass that waits")

    # ── AND IT ARGUES WITH NOTHING ────────────────────────────────────────────────────────────
    s.eq(vols[0]["isbn"], "9784757575387",
         "a row that already holds an ISBN keeps the one the catalogue keyed on gave it")
    s.eq(vols[0]["published"], "2021-10", "and its date, which this pass has no standing to move")
    held = [{"number": "20", "isbn": "9784757575387", "published": "2021-10"}]
    s.eq(nv.apply(got, held), 0, "so a run already answered is not touched at all")

    # A NUMBER IS A NUMBER WHATEVER THE PADDING, which is the same rule the volume merge uses.
    padded = [{"number": "021", "delivered": "2022-03-25"}]
    s.eq(nv.apply(got, padded), 1, "a padded row still meets the volume it is")

    # ── WHO IS ASKED, AND WHO CANNOT BE ───────────────────────────────────────────────────────
    series = [{"id": "w1", "work": "MURCIÉLAGO", "author": "よしむらかな",
               "print": [{"work_ids": ["bw1"]}]},
              {"id": "w2", "work": "全部あるやつ", "author": "だれか",
               "print": [{"work_ids": ["C1"]}]},
              {"id": "w3", "work": "作者不明", "author": "", "print": [{"work_ids": ["bw2"]}]}]
    works = [{"work_id": "bw1", "volumes": [{"number": "21"}, {"number": "22"}]},
             {"work_id": "C1", "volumes": [{"number": "1", "isbn": "9784"}]},
             {"work_id": "bw2", "volumes": [{"number": "1"}]}]
    ask = nv.wanted(series, works)
    s.eq([w["work"] for w in ask], ["MURCIÉLAGO"],
         "only the work with rows holding no ISBN, and only where an author can be agreed with")
    s.eq(ask[0]["missing"], 2, "ordered by how much is missing, so a run stopped early answers most")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
