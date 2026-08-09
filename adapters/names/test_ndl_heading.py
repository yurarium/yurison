#!/usr/bin/env python3
"""ndl_heading.py: taking a name's division off an NDL author heading, and refusing the wrong one.

THE PAGES ARE REAL. Every assertion about markup runs against `data/fixtures/ndl/`, cut out of
pages this project actually fetched, because the fault this module can have is subtle and lives in
the markup: the name sits inside an anchor and the reading is bare text after it, and a fixture
somebody typed out would have whatever separation its author imagined.

THE COUNTER-CASE IS THE POINT OF THE THIRD FIXTURE. Searching NDL by author for いがらしゆみこ
returns 五十嵐 由美子 as well, a different spelling read the same way, and a module that took the
first heading it found would have divided one artist's name from another artist's record.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import fixtures  # noqa: E402
import testkit  # noqa: E402
from names import ndl_heading as nh  # noqa: E402

COVERS = ["adapters/names/ndl_heading.py"]


def main(s):
    taiyo = fixtures.load("ndl/author-heading-divides-a-pen-name")
    igarashi = fixtures.load("ndl/author-heading-divides-an-all-kana-name")
    other = fixtures.load("ndl/author-heading-about-another-person")

    # ── the field, as the catalogue writes it ──────────────────────────────────────────────────
    s.eq(nh.headings(taiyo), [("太陽 まりい", "タイヨウ マリイ")],
         "the heading divides both the name and its reading")
    s.eq(nh.headings(igarashi), [("いがらし ゆみこ", "イガラシ ユミコ")],
         "a birth year is cataloguing apparatus and comes off both halves")
    s.eq(nh.headings(other), [("五十嵐 由美子", "イガラシ ユミコ")],
         "a heading about somebody else is still read; it is refused later, by name")

    # ── the two names this whole round is about ───────────────────────────────────────────────
    #
    # 太陽まりい is the report. MADB states タイヨウマリイ, which is correct and closed up, so the
    # romanisation was `Taiyōmarii` as one word. いがらしゆみこ is the same fault in the shape it
    # was first raised in, months earlier: a name written entirely in kana, where the surface
    # cannot help because there is no kanji boundary in it.
    s.eq(nh.divide(taiyo, "太陽まりい", "タイヨウマリイ"), "タイヨウ マリイ",
         "太陽まりい divides where the national library divides it")
    s.eq(nh.divide(igarashi, "いがらしゆみこ", "イガラシユミコ"), "イガラシ ユミコ",
         "and so does an all-kana name")

    # ── and what it refuses ───────────────────────────────────────────────────────────────────
    s.eq(nh.divide(other, "いがらしゆみこ", "イガラシユミコ"), None,
         "五十嵐 由美子 is read the same way and is a different name; it divides nothing")
    s.eq(nh.stated(other, "いがらしゆみこ"), None,
         "and the refusal happens on the name, before the reading is looked at")
    s.eq(nh.divide(taiyo, "太陽まりい", "タイヨウマリコ"), None,
         "a heading that does not correspond to the kana we hold carries no offsets onto them")
    s.eq(nh.divide(taiyo, "缶乃", "カンノ"), None,
         "and a name the page says nothing about gets nothing")

    # A HEADING THAT STATES NO DIVISION IS NOT A DIVISION OF LENGTH ONE. 缶乃 is filed カンノ, one
    # element, and `boundary.cuts` finds no offsets in it, so nothing is carried and the name keeps
    # the form it had. The interesting half is that this is DIFFERENT from no heading at all, and
    # `sweep` reports the two apart.
    s.eq(nh.headings(fixtures.load("ndl/author-heading-divides-a-pen-name"))[0][1].count(" "), 1,
         "one space, one division; the module never invents a second")

    # ── where the entry points ────────────────────────────────────────────────────────────────
    e = nh.entry(taiyo, "太陽まりい", "タイヨウマリイ", "2026-08-09", "R100000002-I034377994")
    s.eq(e["reading"], "タイヨウ マリイ", "the entry publishes our kana, divided")
    s.eq(e["reading_basis"], "surface",
         "not `stated`: the kana are the name's own and only the division is the library's")
    s.eq(e["source_url"], "http://id.ndl.go.jp/auth/entity/001124707",
         "and it cites the authority record for the PERSON, not the book it was found on")
    s.check("R100000002-I034377994" in e["reading_note"],
            "the note names the record the heading was read from")
    s.check("タイヨウマリイ" in e["reading_note"],
            "and says what it replaced, so a reviewer can disagree with the change")
    s.eq(nh.entry(other, "いがらしゆみこ", "イガラシユミコ", "2026-08-09"), None,
         "no division, no entry")

    # ── the sweep asks for the person and not for the book ────────────────────────────────────
    #
    # ndl_books.py searches by TITLE and checks the record is about that title. This searches by
    # AUTHOR, so any record the person is credited on will do and the check is the heading's name.
    s.check("q-author" in nh.search_url("太陽まりい"),
            "the search is by author, which is what makes one request answer for every book")
    s.raises(ValueError, lambda: nh.search_url("x") and _forbidden(),
             "a path robots.txt disallows cannot be built at all")

    pages = {nh.search_url("太陽まりい"): '<a href="/books/R100000002-I034377994">x</a>',
             "https://ndlsearch.ndl.go.jp/books/R100000002-I034377994": taiyo}
    settled, refused = nh.sweep({"太陽まりい": "タイヨウマリイ"}, pages.get)
    s.eq(sorted(settled), ["太陽まりい"], "one search and one record page settle the name")
    s.eq(refused, {}, "and nothing is left over to write down as an absence")

    # A PERSON NDL HOLDS NO RECORD FOR IS `no-record`, WHICH IS A FINDING AND NOT A FAILURE. Most
    # of this corpus is web serialisation with no printed book, and the library catalogues on
    # deposit. Recorded so the next run does not pay for it again.
    _, none = nh.sweep({"缶乃": "カンノ"}, lambda url: None)
    s.eq(none, {"缶乃": "no-record"}, "silence from the catalogue is recorded as silence")

    # AND A HEADING THAT NAMES THE PERSON AND DIVIDES THEM NOWHERE IS A DIFFERENT ANSWER AGAIN.
    # The catalogue has looked at this name and files it as one element, which is worth more than
    # never having asked, and is the answer for every one-element pen name in the corpus.
    kanno = fixtures.load("ndl/author-heading-states-no-division")
    s.eq(nh.headings(kanno), [("缶乃", "カンノ")], "one element, no comma, nothing to divide")
    s.eq(nh.divide(kanno, "缶乃", "カンノ"), None, "so nothing is carried and the name stays whole")
    seen = {nh.search_url("缶乃"): '<a href="/books/R100000002-I025450568">x</a>',
            "https://ndlsearch.ndl.go.jp/books/R100000002-I025450568": kanno}
    _, why = nh.sweep({"缶乃": "カンノ"}, seen.get)
    s.eq(why, {"缶乃": "heading-states-no-division"},
         "and the pass says so, rather than reporting it as a name nobody has asked about")

    # THE FIRST RECORD IS NOT THE ONLY RECORD. いがらしゆみこ's search returns 五十嵐 由美子 first
    # here, and a sweep that stopped at the first page would report the name unreachable. It reads
    # on, which is the whole reason `max_records` is more than one.
    both = {nh.search_url("いがらしゆみこ"):
            '<a href="/books/R100000002-I030068167">a</a><a href="/books/R100000002-I030604186">b</a>',
            "https://ndlsearch.ndl.go.jp/books/R100000002-I030068167": other,
            "https://ndlsearch.ndl.go.jp/books/R100000002-I030604186": igarashi}
    got, left = nh.sweep({"いがらしゆみこ": "イガラシユミコ"}, both.get)
    s.eq(sorted(got), ["いがらしゆみこ"], "the second record answers where the first did not")
    s.eq(left, {}, "and nothing is recorded as an absence")


def _forbidden():
    from names import ndl_books
    return ndl_books.build_url("/api/opensearch")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
