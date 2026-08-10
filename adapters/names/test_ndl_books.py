#!/usr/bin/env python3
"""ndl_books.py: taking a title's stated reading off an NDL record page, and refusing the wrong one."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import ndl_books as nb  # noqa: E402

COVERS = ["adapters/names/ndl_books.py"]

# Cut from https://ndlsearch.ndl.go.jp/books/R100000002-I026095900 as served 2026-08-08, keeping
# the markup exactly as it arrives. The hydration comments inside the tags are Vue's and are the
# reason a naive tag strip leaves `<!--[-->` sitting in the middle of every value.
URARA = """<dl>
<dt class="has-text-sub" data-v-5bfa0419><!--[-->タイトル<!--]--></dt>
<dd data-v-5bfa0419><!--[--><span><!--[-->うらら迷路帖<!--]--></span><!--]--></dd>
<dt class="has-text-sub" data-v-5bfa0419><!--[-->タイトルよみ<!--]--></dt>
<dd data-v-5bfa0419><!--[--><span><!--[-->ウララ メイロチョウ<!--]--></span><!--]--></dd>
<dt data-v-5bfa0419><!--[-->巻次・部編番号<!--]--></dt>
<dd data-v-5bfa0419><!--[-->1<!--]--></dd>
<dt data-v-5bfa0419><!--[-->著者<!--]--></dt>
<dd data-v-5bfa0419><!--[-->はりかも&nbsp;著<!--]--></dd>
<dt data-v-5bfa0419><!--[-->出版者<!--]--></dt>
<dd data-v-5bfa0419><!--[-->芳文社<!--]--></dd>
<dt data-v-5bfa0419><!--[-->資料種別<!--]--></dt>
<dd data-v-5bfa0419><!--[-->図書<!--]--></dd>
<dt data-v-5bfa0419><!--[-->資料種別<!--]--></dt>
<dd data-v-5bfa0419><!--[-->電子書籍<!--]--></dd>
</dl>"""

# The other book the same search returns. Same author, same shelf, different work, and its own
# reading. This is what a title check is FOR: without one it answers for うらら迷路帖.
ANTHOLOGY = """<dl>
<dt><!--[-->タイトル<!--]--></dt><dd><!--[-->うらら迷路帖アンソロジーコミック<!--]--></dd>
<dt><!--[-->タイトルよみ<!--]--></dt><dd><!--[-->ウララ メイロチョウ アンソロジー コミック<!--]--></dd>
</dl>"""

# A record with no reading transcribed at all, which is the ordinary state of an ebook-only entry.
NO_READING = """<dl>
<dt><!--[-->タイトル<!--]--></dt><dd><!--[-->うらら迷路帖<!--]--></dd>
<dt><!--[-->出版者<!--]--></dt><dd><!--[-->芳文社<!--]--></dd>
</dl>"""

SEARCH = """<a href="/books/R100000002-I026095900"><img src="cover.jpg"></a>
<a href="/books/R100000002-I026095900">うらら迷路帖 1</a>
<a href="/books/R100000002-I026964517">うらら迷路帖 2</a>
<a href="/books/R100000002-I026964517">うらら迷路帖 2</a>
<a href="/en/books/R100000002-I028032719">うらら迷路帖アンソロジーコミック</a>"""


def main(s):
    f = nb.fields(URARA)
    s.eq(f["タイトルよみ"], "ウララ メイロチョウ", "the kana a national library states for the title")
    s.eq(f["タイトル"], "うらら迷路帖", "beside the title it states it for")
    s.eq(f["著者"], "はりかも 著", "with the entity unescaped, since &nbsp; is markup and not a name")
    # FIRST OCCURRENCE WINS, and the page repeats 資料種別 on every record. Nothing here depends on
    # it today; the point is that the copy read is the one at the top of the table rather than
    # whichever the template emitted last.
    s.eq(f["資料種別"], "図書", "the first copy of a repeated label, not the last")

    s.eq(nb.reading(URARA, "うらら迷路帖"), "ウララ メイロチョウ", "the record answers for its work")
    # THE CHECK THIS MODULE EXISTS FOR. Both records come back from one search, both are about a
    # book with these characters at the front of its title, and only one of them is this work.
    s.eq(nb.reading(ANTHOLOGY, "うらら迷路帖"), None,
         "a longer title is a different book and does not answer for this one")
    s.eq(nb.reading(URARA, "うらら迷路帖アンソロジーコミック"), None, "and it does not answer in reverse")
    s.eq(nb.reading(NO_READING, "うらら迷路帖"), None, "a record transcribing no reading states none")
    s.eq(nb.reading("", "うらら迷路帖"), None, "and neither does no record at all")

    # OUR TITLE CARRIES A PLATFORM'S APPARATUS AND THE BOOK DOES NOT. 【タテスク】 is a vertical-scroll
    # edition, （BC） an imprint, 【連載版】 a chapter sold on its own: none of it is on a title page.
    s.eq(nb.reading(URARA, "うらら迷路帖【タテスク】"), "ウララ メイロチョウ",
         "the platform's edition marker is apparatus and comes off before comparing")
    s.eq(nb.match_key("みんな私のはらのなか【連載版】（BC）"), nb.match_key("みんな私のはらのなか"),
         "two groups of apparatus, and both come off")
    s.eq(nb.match_key("ロイヤルテーラー"), nb.match_key("ロイヤルテーラー"), "and a title with none is untouched")
    # THE COUNTER-CASE THAT KEEPS THE RULE HONEST. A bracket in the MIDDLE of a title is content:
    # 少女たちの痕(きずあと)にくちづけを prints its own furigana gloss there, and cutting it would
    # make a different work's record answer for this one.
    s.ne(nb.match_key("少女たちの痕(きずあと)にくちづけを"), nb.match_key("少女たちの痕にくちづけを"),
         "a bracket inside a title is part of the title")
    s.eq(nb.match_key("恋する小惑星"), "恋する小惑星", "and the folded form is still the title")
    s.ne(nb.match_key("恋する小惑星"), nb.match_key("恋する小惑星アンソロジー"),
         "a prefix is not a match; that is how the wrong book answers")

    # THE QUERY IS ALLOWED TO BE LOOSER THAN THE MATCH. Searching the whole stored title found
    # nothing for thirteen works NDL holds, because our string carries a subtitle and a platform's
    # brackets and the catalogue's does not.
    s.eq(nb.search_terms("遠山えま百合集 : センセイとの時間。"),
         ["遠山えま百合集 : センセイとの時間。", "遠山えま百合集"],
         "the whole title first, then the title proper")
    s.eq(nb.search_terms("ゆうやけトリップ【単話版】"),
         ["ゆうやけトリップ【単話版】", "ゆうやけトリップ"], "and the platform's apparatus comes off")
    s.eq(nb.search_terms("魔王と百合"), ["魔王と百合"],
         "a title with neither is searched once, not four times")

    s.eq(nb.record_ids(SEARCH),
         ["R100000002-I026095900", "R100000002-I026964517", "R100000002-I028032719"],
         "each result once, in the order the search ranked them")
    s.eq(nb.record_ids(""), [], "and a search that matched nothing links to nothing")

    r, ev = nb.settle(["ウララ メイロチョウ", "ウララ メイロチョウ"])
    s.eq(r, "ウララ メイロチョウ", "volumes of one series agree, which is the ordinary case")
    s.eq(ev["status"], "stated", "and agreement is what makes the reading sourced")
    # SPACING IS NOT DISAGREEMENT, but on the title side it is not settled the way
    # ndl_reading.settle settles it either. Four volumes of うらら迷路帖 are transcribed by four
    # cataloguers and one of them puts a space inside ウララ; taking the longest form, which is
    # what the author-side rule does for a good reason of its own, ships `Ura Ra Meirochō`.
    r, ev = nb.settle(["ウラ ラ メイロチョウ", "ウララ メイロチョウ",
                       "ウララ メイロチョウ", "ウララ メイロチョウ"])
    s.eq(r, "ウララ メイロチョウ", "the division the records agree on, not the longest one")
    s.eq(ev["status"], "stated", "since the two spell the same reading")
    s.eq(ev["divisions"], ["ウラ ラ メイロチョウ", "ウララ メイロチョウ"],
         "with the disagreement kept, because the tie-break is a preference")
    # AN EVEN SPLIT TAKES THE CLOSED-UP FORM. 優雅なる is one word and two of the four records
    # divide it anyway; a space nobody agreed on is not a boundary that was found.
    r, _ = nb.settle(["ユウガ ナル", "ユウガナル", "ユウガ ナル", "ユウガナル"])
    s.eq(r, "ユウガナル", "an even split keeps the fewest spaces")
    s.eq(nb.settle(["マオウ ト ユリ", "マオウ ト ユリ"])[1].get("divisions"), None,
         "and records that agree report no disagreement to look at")
    r, ev = nb.settle(["カイイブ", "ケイイブ"])
    s.eq(r, None, "two different readings settle nothing")
    s.eq(ev["status"], "conflicting", "and say so, because one record is about another book")
    s.eq(ev["readings"], ["カイイブ", "ケイイブ"], "keeping both for whoever looks next")
    s.eq(nb.settle([])[1]["status"], "no-record", "silence is a state and not an empty answer")
    s.eq(nb.settle(["", "  "])[1]["status"], "no-record", "and a blank transcription is silence")

    s.eq(nb.record_url("R100000002-I026095900"),
         "https://ndlsearch.ndl.go.jp/books/R100000002-I026095900", "the record page")
    s.eq(nb.search_url("うらら迷路帖"),
         "https://ndlsearch.ndl.go.jp/search?cs=bib&keyword="
         "%E3%81%86%E3%82%89%E3%82%89%E8%BF%B7%E8%B7%AF%E5%B8%96", "and the bibliographic search")
    # THE RULE ROBOTS.TXT IMPOSES, ENFORCED RATHER THAN REMEMBERED. `/api` is disallowed, and
    # ndl_reading.py's three rounds went out on it because the rule lived in a docstring.
    s.raises(ValueError, lambda: nb.build_url("/api/opensearch", creator="x"),
             "the disallowed path cannot be built, so it cannot be fetched by mistake")
    s.raises(ValueError, lambda: nb.build_url("/statistics"),
             "nor any other path robots.txt withholds")

    sweep(s)


def sweep(s):
    """What the run writes down, with every request answered from this file and none sent.

    THE BUG THESE PIN. A sweep against NDL meets 503 for asking too fast, and a 503 arrives at the
    caller as a page that is not there, which is the same shape as a work the library does not
    hold. Reading the first as the second writes the work off, and nothing ever asks again. So the
    two cases are separated here by what reaches the ledger and not only by what is printed.
    """
    import contextlib
    import io
    import json
    import tempfile

    import net
    from names import store as store_mod

    EMPTY = "<html>no results</html>"

    def run(answers, titles, extra=()):
        """main() with `answers` standing in for the network, and a store of its own."""
        sent = []

        def fake_fetch(url, cache, max_age_days=None, attempts=None):
            sent.append(url)
            return answers(url)

        with tempfile.TemporaryDirectory() as d:
            tpath = pathlib.Path(d) / "titles.txt"
            tpath.write_text("\n".join(titles))
            real = net.fetch
            net.fetch = fake_fetch
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    nb.main(["--titles", str(tpath), "--no-cache", "--store", d, *extra])
                rows = [json.loads(x) for x in out.getvalue().splitlines() if x.startswith("{")]
                return rows, store_mod.NameStore(d).attempts, sent
            finally:
                net.fetch = real

    refused = net.Result(None, 503, "u", None, False, "HTTP 503", "ndlsearch.ndl.go.jp", 5)
    answered = net.Result(EMPTY, 200, "u", None, False, None, "ndlsearch.ndl.go.jp", 1)

    rows, attempts, _ = run(lambda url: refused, ["怪異部"])
    s.eq(rows[0]["status"], "fetch-failed", "a refused search is reported as a fetch that failed")
    s.eq(attempts, {}, "and NOTHING is written down, because 503 is evidence about us")

    rows, attempts, _ = run(lambda url: answered, ["怪異部"])
    s.eq(rows[0]["status"], "no-record", "a search NDL answered and that held nothing is a miss")
    s.eq([e["source"] for e in attempts["怪異部"]], ["ndl-books"],
         "and that one IS written down, so the next run does not pay for it again")

    # THE RECORD PAGE, which is where the swallow used to be: a refusal here was caught and the
    # loop moved on, so the title reported `no-record` for a record NDL declined to serve.
    found = net.Result('<a href="/books/R100000002-I026095900">x</a>', 200, "u", None, False,
                       None, "ndlsearch.ndl.go.jp", 1)
    rows, attempts, _ = run(lambda url: refused if "/books/" in url else found, ["怪異部"])
    s.eq(rows[0]["status"], "fetch-failed", "a refused RECORD page is a fetch that failed too")
    s.eq(attempts, {}, "and writes down no absence for the work it was about")

    # AND THE SAVING. A title whose absence is on file is not asked about at all.
    def with_prior(answers, titles, at):
        with tempfile.TemporaryDirectory() as d:
            st = store_mod.NameStore(d)
            st.attempt(titles[0], None, nb.SOURCE)
            st.attempts[titles[0]][0]["at"] = at
            st.compact()
            sent = []

            def fake_fetch(url, cache, max_age_days=None, attempts=None):
                sent.append(url)
                return answers(url)

            tpath = pathlib.Path(d) / "titles.txt"
            tpath.write_text("\n".join(titles))
            real = net.fetch
            net.fetch = fake_fetch
            try:
                with contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    nb.main(["--titles", str(tpath), "--no-cache", "--store", d])
            finally:
                net.fetch = real
            return sent

    s.eq(with_prior(lambda url: answered, ["怪異部"], store_mod.today()), [],
         "a fresh absence costs no request at all")
    s.check(with_prior(lambda url: answered, ["怪異部"], "2019-01-01"),
            "and an old one is asked again, because a catalogue gains records")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
