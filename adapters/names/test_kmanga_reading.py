#!/usr/bin/env python3
"""kmanga_reading.py: weighing a retailer's kana onto a name, and refusing what it cannot carry."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import kmanga_reading as km  # noqa: E402

COVERS = ["adapters/names/kmanga_reading.py"]


def title_page(title, credits_html):
    """One まんが王国 title page cut to the two parts this reads."""
    return (f"<html><head><title>{title}｜まんが王国</title></head><body>"
            '<dl class="book-info--detail"><dt class="book-info--detail-title">著者・作者</dt>'
            f'<dd class="book-info--detail-item">{credits_html}</dd>'
            '<dt class="book-info--detail-title">掲載雑誌</dt>'
            '<dd class="book-info--detail-item">'
            '<a href="/search/magazine/67">ビジネスジャンプ</a></dd></dl></body></html>')


def credit(author_id, name, gloss=None):
    span = f'<span class="f10">（{gloss}）</span>' if gloss else ""
    return f'<a class="gaevent-detail-thumb-right-author-{author_id}" ' \
           f'href="/search/author/{author_id}">{name}{span}</a>'


# Quoted from comic.k-manga.jp/title/100543 as served 2026-08-08, cut to the byline. Three credits,
# and the third carries no gloss at all: the shop stocks 堀賢一 and states no reading for him.
SOMMELIER = title_page("ソムリエ", credit(15816, "城アラキ", "じょうあらき")
                       + credit(12219, "松井勝法", "まついかつのり")
                       + credit(15966, "堀賢一"))

# One book by one person, the ordinary shape.
LIAR = title_page("LIAR GAME", credit(15404, "甲斐谷忍", "かいたにしのぶ"))

def tile(title_id, title, people):
    return ('<li class="book-list--target">'
            f'<a class="book-list--item" href="/title/{title_id}/pv">'
            f'<h2 class="book-list--title">{title}</h2>'
            '<p class="book-list--author hover-no-underline">'
            + "".join(f'<span class="book-list--author-item">{p}</span>' for p in people)
            + "</p></a></li>")


# A word search, as the shop answers one. The first book is somebody else's and matched on the
# title, which is the ordinary shape of a bare-name query and the reason the tile is read.
SEARCH = (tile("106164", "甲斐谷忍という名前の出てくる本", ["尾田栄一郎"])
          + tile("100543", "ソムリエ", ["城アラキ", "松井勝法", "堀賢一"])
          + tile("100543", "ソムリエ", ["城アラキ"]))


def main(s):
    s.eq(km.hits(SEARCH), [("106164", ["尾田栄一郎"]),
                           ("100543", ["城アラキ", "松井勝法", "堀賢一"])],
         "each book with the byline its own tile carries, and the repeat dropped")
    s.eq(km.hits("<html>no results</html>"), [], "and none where the search matched nothing")

    # THE TILE IS READ BEFORE A BOOK IS OPENED. The first hit here matched on the title and is by
    # somebody else, and opening it costs a request and settles nothing. On the first thirty names
    # this rule was 30 of the 96 requests.
    s.eq(km.books_for(SEARCH, "松井勝法"), ["100543"], "only the books whose byline names them")
    s.eq(km.books_for(SEARCH, "甲斐谷忍"), [],
         "a name matched inside a title is not a credit, however well it reads as one")
    s.eq(km.books_for(SEARCH, "城"), [], "and a fragment of a credit is not the credit")

    # A GLOSS BELONGS TO THE ANCHOR IT IS IN. Reading the names and the glosses as two lists and
    # zipping them pairs 松井勝法 with じょうあらき, which is one artist's reading on another
    # artist's name, and it is the failure 古川楊也 took a refutation to undo.
    s.eq(km.credits(SOMMELIER),
         [("城アラキ", "じょうあらき"), ("松井勝法", "まついかつのり"), ("堀賢一", "")],
         "each credit with its own gloss, and an empty one where the shop prints none")

    # SILENCE IS A STATE. 堀賢一 is stocked and unread, which is a different answer from a person
    # the shop has never heard of, and only the second is settled by looking somewhere else.
    s.eq(km.records({"100543": SOMMELIER}, "堀賢一"), [],
         "a credit with no gloss states no reading")

    s.eq([r["reading"] for r in km.records({"100543": SOMMELIER}, "松井勝法")], ["マツイカツノリ"],
         "the gloss beside the name, as the katakana the store holds")

    # A SEARCH HIT IS NOT AN IDENTIFICATION, and a surname is not a person. `/search/word/` matches
    # inside a title, so a book that came back has to name the person before it says anything.
    s.eq(km.records({"100543": SOMMELIER}, "松井"), [],
         "a surname does not answer for the full name")
    s.eq(km.records({"106164": LIAR}, "城アラキ"), [],
         "and a book that does not credit the person states nothing about them")

    s.eq(km.credits("<html>a redesigned page</html>"), [],
         "a page that no longer has the shape yields nothing rather than a heading")
    s.eq(km.credits(title_page("D", "")), [], "and neither does an empty byline")

    # THE GLOSS SLOT HAS TO HOLD KANA. A shop putting a romanisation or a note there would
    # otherwise be recorded as stating a Japanese reading.
    s.eq(km.records({"1": title_page("D", credit(1, "甲斐谷忍", "kaitani"))}, "甲斐谷忍"), [],
         "a romanisation in the gloss is not a reading")

    s.eq(km.author_url(SOMMELIER, "松井勝法"), "https://comic.k-manga.jp/search/author/12219",
         "the citation is the anchor the name sits in, not the one beside it")
    s.eq(km.author_url(SOMMELIER, "尾田栄一郎"), "", "and there is none for a name not on the page")

    # TWO BOOKS DISAGREEING IS A FINDING AND NOT A VOTE, which is `ndl_reading.settle`'s rule and
    # the reason this module does not carry a second copy of it.
    both = {"1": title_page("A", credit(1, "甲斐谷忍", "かいたにしのぶ")),
            "2": title_page("B", credit(1, "甲斐谷忍", "かいやしのぶ"))}
    s.eq(km.resolve(both, "甲斐谷忍")[0], None, "two glosses for one name settle nothing")
    s.eq(km.resolve({}, "甲斐谷忍")[1]["status"], "no-record", "and no book at all is its own answer")

    ev = km.resolve({"106164": LIAR}, "甲斐谷忍")[1]
    e = km.entry("甲斐谷忍", "カイタニシノブ", ev, "コウ ヒツジ タニシノブ",
                 "https://comic.k-manga.jp/search/author/15404", "2026-08-08")
    # THE BASIS IS THE WHOLE POINT. A retailer does not say where its kana came from, so recording
    # this as `stated` would put a source's name on a claim no source made.
    s.eq(e["reading_basis"], "researched", "a shop listing is weighed, never attributed")
    s.eq(e["reading_source_kind"], "derived", "and the conclusion is ours")
    s.check("まんが王国" in e["reading_note"], "the note names what was weighed")
    s.check("コウ ヒツジ タニシノブ" in e["reading_note"],
            "and the string it takes off the page, so the change can be argued with")
    s.check(e["reading_url"].endswith("/15404"), "with the page it was read from beside it")

    agreeing = km.entry("甲斐谷忍", "カイタニシノブ", ev, "カイタニ シノブ", "u", "2026-08-08")
    s.check("agrees" in agreeing["reading_note"],
            "an agreement is recorded as one; it is evidence and not a change")

    # THE WALK: one search per name, then only the books whose tile credits the person.
    pages = {"https://comic.k-manga.jp/search/word/%E6%9D%BE%E4%BA%95%E5%8B%9D%E6%B3%95": SEARCH,
             "https://comic.k-manga.jp/title/100543": SOMMELIER,
             "https://comic.k-manga.jp/title/106164": LIAR}
    got, unresolved, _health = km.entries(pages.get, {"松井勝法": "マツイ カツノリ"}, "2026-08-08")
    s.eq(sorted(got), ["松井勝法"], "the name is settled off the book that credits it")
    s.eq(got["松井勝法"]["reading"], "マツイカツノリ", "with the reading that book glosses")
    s.eq(unresolved, {}, "and nothing is left open")
    s.check("106164" not in str(got), "and the book that matched on its title was never opened")

    # A SHOP THAT ANSWERS NOTHING LOOKS EXACTLY LIKE A BATCH IT DOES NOT STOCK. The count of pages
    # that came back is the only thing that tells them apart, so it is asserted rather than read
    # off the result.
    _got, unres, (ok, answered, asked) = km.entries(lambda _u: "", {"甲斐谷忍": "コウ"},
                                                    "2026-08-08")
    s.eq(unres, {"甲斐谷忍": "no-page"}, "a search that did not come back settles nothing")
    s.eq((ok, answered, asked), (False, 0, 1), "and the run refuses to be read as a clean one")
    s.eq(km.healthy(0, 0)[0], True, "an empty queue is not an unhealthy run")

    # THE ORDER IS PART OF THE MODULE, because an hours-long run gets stopped and what it reached
    # is what a reader sees. Sorted by name, the symbols and the handles go first.
    series = [{"author": "松井勝法 / 城アラキ"}, {"author": "城アラキ"}, {"author": "堀賢一"}]
    s.eq([n for n, _g in km.by_reader_reach({"松井勝法": "", "城アラキ": "", "＊": ""}, series)],
         ["城アラキ", "松井勝法", "＊"], "most-credited first, and the name breaks the tie")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
