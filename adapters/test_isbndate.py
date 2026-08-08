#!/usr/bin/env python3
"""isbndate.py: a finer date is taken only where it is the same fact said more exactly.

COVERS = ['adapters/isbndate.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import isbndate as d
import testkit


def main(s):
    s.eq(d.precision("2013-05-24"), "day", "a full date is day precision")
    s.eq(d.precision("2013-05"), "month", "a year and month is month precision")
    s.eq(d.precision("2013"), "year", "a bare year is year precision")
    s.eq(d.precision(""), "", "nothing states no precision")
    s.eq(d.precision(None), "", "None does not raise")

    # THE PAIR THE MODULE EXISTS FOR. One fact at two precisions against two different facts.
    s.eq(d.relation("2013-05", "2013-05-24"), d.SHARPENS,
         "a day inside the month we hold is the same fact said more exactly")
    s.eq(d.relation("2013-05", "2013-06-02"), d.DISAGREES,
         "a day in another month is a second source disagreeing, never a rounding")

    # THE COUNTER-CASE THAT WOULD BREAK A NAIVE PREFIX TEST. 2013-05 is a prefix of the string
    # 2013-05-24 and it is NOT a prefix of 2013-0, so a comparison done the other way round would
    # read a coarser answer as a sharper one.
    s.eq(d.relation("2013-05-24", "2013-05"), d.RESTATES,
         "a month around the day we hold adds nothing and takes nothing away")
    s.eq(d.relation("2026-03-02", "2026-02"), d.DISAGREES,
         "a month that does not contain the day we hold is a disagreement, not a restatement")

    s.eq(d.relation("", "2020-07"), d.FILLS, "a date where we hold none is worth taking")
    s.eq(d.relation(None, "2020-07"), d.FILLS, "and a missing key is the same as an empty one")
    s.eq(d.relation("2020-07", ""), d.SILENT, "a catalogue with no record has not corrected us")
    s.eq(d.relation("2020-07", None), d.SILENT, "and neither has a missing key")
    s.eq(d.relation("", ""), d.SILENT, "two silences are silence")
    s.eq(d.relation("2020-07", "2020-07"), d.AGREES, "the same date twice is agreement")
    s.eq(d.relation("2020-07", "2020-08"), d.DISAGREES, "two months are two claims")
    s.eq(d.relation("2020", "2020-07"), d.SHARPENS, "a month inside the year we hold sharpens it")
    s.eq(d.relation("2020", "2021-07"), d.DISAGREES, "a month outside it does not")

    # openBD writes YYYYMMDD and YYYYMM, so the comparison has to normalise before it compares.
    # `enrich.pubdate` is the one producer of that string and this module imports it.
    s.eq(d.relation("2013-05", "20130524"), d.SHARPENS, "the raw openBD form is normalised first")
    s.eq(d.relation("2013-05", "201305"), d.AGREES, "and so is the month form")

    s.eq(d.resolve("2013-05", "2013-05-24"), ("2013-05-24", d.SHARPENS), "the sharper date wins")
    s.eq(d.resolve("2013-05", "2013-06-02"), ("2013-05", d.DISAGREES),
         "and a disagreeing one does not, however precise it is")
    s.eq(d.resolve("", "2020-07"), ("2020-07", d.FILLS), "a hole is filled")
    s.eq(d.resolve("2013-05-24", "2013-05"), ("2013-05-24", d.RESTATES),
         "precision already held is never given back")
    s.eq(d.resolve("2020-07", None), ("2020-07", d.SILENT), "silence changes nothing")

    rows = [{"isbn": "1", "published": "2013-05"},
            {"isbn": "2", "published": "2013-05"},
            {"isbn": "3"},
            {"isbn": "4", "published": "2013-05-24"},
            {"published": "2013-05"}]
    got = d.survey(rows, {"1": "2013-05-24", "2": "2013-06-02", "3": "2020-07", "4": "2013-05"})
    s.eq(got, {d.SHARPENS: 1, d.DISAGREES: 1, d.FILLS: 1, d.RESTATES: 1},
         "a survey counts each relation and skips a volume with no ISBN")

    works = [{"work_id": "W1", "volumes": [{"isbn": "1", "published": "2013-05"},
                                           {"isbn": "2"},
                                           {"number": "3"}]},
             {"work_id": "W2", "volumes": [{"isbn": "4"}]},
             {"work_id": "W3"}]
    s.eq(d.undated_isbn_volumes(works), ["W1 2", "W2 4"],
         "the measure counts a volume stating an ISBN and no date, and nothing else")
    s.eq(d.undated_isbn_volumes([]), [], "an empty corpus measures as empty")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "isbndate"))
