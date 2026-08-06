#!/usr/bin/env python3
"""isbn_dates.py: reading two fields out of a 665 MB file without loading it."""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from madb import isbn_dates  # noqa: E402

COVERS = ["adapters/madb/isbn_dates.py"]

# Two records quoted from metadata101.json of MADB release 1.2.18, with the fields the parser does
# not read cut. The indentation is the file's own and is load-bearing: the record boundary is the
# brace at indent 4, and nested objects sit at 6 and 8.
#
# The second record is the shape that makes the field readers necessary. MADB writes a name as a
# bare string where it has no reading and as a LIST of the string and a ja-hrkt reading where it
# has one, and it writes a date to the month for most books and to the day for some.
BULK = """{
  "@context": {},
  "@graph": [
    {
      "@id": "https://mediaarts-db.artmuseums.go.jp/id/M1032568",
      "@type": "class:MangaBook",
      "schema:creator": [
        "ほしのなつみ",
        {
          "@value": "ホシノナツミ",
          "@language": "ja-hrkt"
        }
      ],
      "schema:datePublished": "2024-08-06",
      "schema:isbn": "9784785977382",
      "schema:publisher": "少年画報社"
    },
    {
      "@id": "https://mediaarts-db.artmuseums.go.jp/id/M0000001",
      "@type": "class:MangaBook",
      "schema:datePublished": "2019-01",
      "schema:isbn": "9784091287557",
      "schema:publisher": "小学館"
    },
    {
      "@id": "https://mediaarts-db.artmuseums.go.jp/id/M0000002",
      "@type": "class:MangaBook",
      "schema:datePublished": "",
      "schema:publisher": "一迅社"
    }
  ]
}
"""


def main(s):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / isbn_dates.VOLUMES
        p.write_text(BULK)

        got = list(isbn_dates.records(p))
        s.eq(len(got), 3, "three records, and the nested objects inside them are not records")
        s.eq(got[0]["schema:publisher"], "少年画報社", "each one parses as a whole record")

        idx = isbn_dates.build(p)
        s.eq(idx.get("9784785977382"), "2024-08-06", "a date to the day is kept to the day")
        s.eq(idx.get("9784091287557"), "2019-01", "and a date to the month stays a month")
        s.eq(len(idx), 2, "a record with no ISBN and no date is not an entry with empty values")

        # THE FIRST DATE FOR AN ISBN WINS. An ISBN identifies one edition, so a second record
        # carrying it is a duplicate catalogue entry rather than a second publication.
        twice = pathlib.Path(d) / "twice.json"
        twice.write_text(BULK.replace('"@id": "https://mediaarts-db.artmuseums.go.jp/id/M0000002",'
                                      '\n      "@type": "class:MangaBook",'
                                      '\n      "schema:datePublished": "",',
                                      '"@id": "https://mediaarts-db.artmuseums.go.jp/id/M0000002",'
                                      '\n      "@type": "class:MangaBook",'
                                      '\n      "schema:isbn": "9784091287557",'
                                      '\n      "schema:datePublished": "2024-12",'))
        s.eq(isbn_dates.build(twice).get("9784091287557"), "2019-01",
             "a duplicate catalogue entry does not overwrite the first date")

    # PAIRS ARE REJECTED RATHER THAN REPAIRED. A record stating a publisher and nothing else is not
    # an ISBN with an empty date, and a date field the catalogue left blank is not the year 0.
    s.eq(isbn_dates.pair({"schema:isbn": "9784091287557", "schema:datePublished": "2019-01"}),
         ("9784091287557", "2019-01"), "the ordinary case")
    s.eq(isbn_dates.pair({"schema:isbn": "978-4-09-128755-7",
                          "schema:datePublished": "2019-01"})[0], "9784091287557",
         "a hyphenated ISBN is the same ISBN")
    s.eq(isbn_dates.pair({"schema:isbn": "9784091287557", "schema:datePublished": ""}), None,
         "no date, no entry")
    s.eq(isbn_dates.pair({"schema:datePublished": "2019-01"}), None, "no ISBN, no entry")
    s.eq(isbn_dates.pair({"schema:isbn": "9784091287557",
                          "schema:datePublished": "2019年1月"}), None,
         "and a date that is not an ISO date is refused rather than half-read")
    s.eq(isbn_dates.pair({"schema:isbn": ["9784091287557"],
                          "schema:datePublished": "2019"}),
         ("9784091287557", "2019"),
         "a field MADB wrote as a list reads the same, and a bare year is a real precision")

    # THE KEY IS THE THIRTEEN-DIGIT FORM WHICHEVER FORM THE CATALOGUE PRINTED, and until
    # 2026-08-06 it was not. MADB prints 126,318 of its 355,323 ISBNs in ten digits, so a third of
    # the national bibliography answered nothing to a thirteen-digit question and read exactly
    # like a catalogue with no record of the book.
    s.eq(isbn_dates.pair({"schema:isbn": "4840115222", "schema:datePublished": "2006-04"}),
         ("9784840115223", "2006-04"),
         "ハニー＆ハニー, filed by a shop as an ISBN no catalogue holds, in the file all along")
    s.eq(isbn_dates.pair({"schema:isbn": "4396763387", "schema:datePublished": "2004-08"}),
         ("9784396763381", "2004-08"), "and フリー・ソウル beside it")
    # THE COUNTER-CASE. A record whose ISBN field holds something that is not an ISBN is refused,
    # not keyed on a truncated number that would collide with a real one.
    s.eq(isbn_dates.pair({"schema:isbn": "978475807480", "schema:datePublished": "2019-01"}), None,
         "twelve digits is not an ISBN and is not padded into one")

    # THE FLOOR. A truncated download and a smaller catalogue look identical from here, and the
    # national bibliography does not shrink.
    s.eq(isbn_dates.healthy({str(i): "2019-01" for i in range(isbn_dates.MIN_DATED)})[0], True,
         "a whole dataset clears the floor")
    s.eq(isbn_dates.healthy({"9784091287557": "2019-01"})[0], False,
         "and one ISBN out of a third of a million does not")
    s.eq(isbn_dates.healthy({})[0], False, "nor does nothing at all")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
