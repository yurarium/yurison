#!/usr/bin/env python3
"""The areas of a title as a bibliography writes it, and which of them is the work's name.

WHAT ISBD PUNCTUATION IS. A catalogue transcribes a book's title page under the International
Standard Bibliographic Description, which marks each area of the title with a punctuation mark
before it. Two of them reach this project through MADB:

    ` = `   the 並列タイトル: the same title in another language, as the title page prints it.
            `リリィシステム = LILY SYSTEM` is one work with one name and the publisher's own
            English beside it.
    ` : `   other title information: a subtitle, or an edition statement.

Both were being stored whole, so `恋愛遺伝子XX = The Romance Gene XX` was the work's name as far
as everything downstream could tell. A reader saw the punctuation, a search had to match it, and
two records of one work compared unequal: several pairs shipped as duplicates and were merged by
hand on 2026-08-07.

WHY THIS IS ITS OWN MODULE. Four capture routes write into `data/source/madb/` and every one of
them wants the same answer to "what is this work called". They reach it through
`madb/extract.render`, which is where the record shape is decided, and `render` reaches it through
here. Copying the split into each route is the shape STANDING-INSTRUCTIONS §3 is written about: the
copies would answer differently the first time one of them learned about a new mark.

THE TWO MARKS ARE NOT THE SAME CASE, and treating them alike is the mistake to avoid.

A parallel title is the SAME NAME in another language, so taking it off the Japanese loses nothing:
the English is kept and offered as the work's official English name, which outranks any
romanisation we could derive. Other title information is CONTENT. `ギャルメイドと悪役令嬢 :
おじょーさま、お世話させていただきます` says something about the book that its first six words do
not, and a rule that cut it would be deleting what a publisher printed. So the subtitle is kept on
whichever of the two names it belongs to, which `areas` decides and explains.

An edition statement, `恋愛遺伝子XX : 完全版`, sits in the same area and does a different job: it
names a reissue of a work the catalogue already holds. Telling the two apart takes a closed set,
which is `EDITIONS` below, taken from the reader interface so that the backend cannot recognise an
edition the interface has no name for.

WHAT WILL NOT SPLIT. Each refusal costs a real record and each is deliberate:

    `ルミナス = ブルー`                 a parallel half holding Japanese is not a translation. This
                                        is one title written with an equals sign in it.
    `School zone = スクールゾーン`      the same shape the other way round. Nothing here can say
                                        which half the publisher considers the name.
    `ニニンがシノブ伝ぷらす = 2×2=SHINOBUDEN+`
                                        more than one equals sign leaves no way to tell where the
                                        name ends, and guessing would invent one.
    `X : Y = Z`                         ISBD writes the parallel title BEFORE the other title
                                        information. An equals sign after a colon is not the mark
                                        this module knows, so the string stays whole.

WHERE ELSE ISBD PUNCTUATION IS READ, and why those readers are not folded in here. `madb/by_title.
keys`, `madb/by_platform_isbn._forms` and `serialisation/find.queries` each split a title on the
same marks, and none of them is producing a name: they generate the several forms a title can be
LOOKED UP under, so they want the loosest possible split and are allowed to be wrong in ways a
stored name may not be. This module answers what the work is called; those answer what to search
for.
"""
import re
from collections import namedtuple

# Kana and CJK. A parallel title holding any of it is not an English name.
JAPANESE = re.compile(r"[぀-ヿ㐀-鿿豈-﫿]")

# ISBD puts a space on both sides of the mark, which is what tells the punctuation apart from a
# character inside a name. `2×2=SHINOBUDEN+` and `A:B` carry no ISBD mark at all.
EQUALS = re.compile(r"\s+=\s+")
COLON = re.compile(r"\s+:\s+")

# THE EDITION STATEMENTS THIS PROJECT RECOGNISES. Taken from `EDITION_EN` in the reader interface
# (`kari/app.js`), which glosses each one in English so that a work is not stranded in Japanese by
# a two-character suffix. The vocabulary lives there because that is where a reader meets it, and
# it is copied here rather than extended: a second list would let the backend recognise an edition
# the interface cannot name.
#
# A CLOSED SET IS THE WHOLE POINT. Anything else after ` : ` is a subtitle, which is content, and
# the reason this is a fixed list instead of a pattern is that no pattern can tell a reissue from a
# description of the book.
EDITIONS = ("完全版", "電子単行本", "新装版", "合本版", "分冊版", "雑誌掲載版")

# name         the work's name: the title proper, with any other title information belonging to it
# parallel     the English name the title page printed beside it, and its own subtitle, or ''
# other        the other title information, whichever of the two names it belongs to, or ''
Areas = namedtuple("Areas", "name parallel other")


def areas(title):
    """One catalogued title split into the areas ISBD marked in it.

    WHICH NAME THE SUBTITLE BELONGS TO, which is the question a plain split gets wrong. ISBD writes
    `title proper = parallel title : other title information` and does not say which of the two
    names the last area describes, so the language does:

        `シナモン = Cinnamon : 人外×人間百合アンソロジー`   the subtitle is Japanese, so it is the
                                                            Japanese book's, and the name is
                                                            `シナモン : 人外×人間百合アンソロジー`
        `ザ・ファブル = THE FABLE : The silent-killer is living in this town`
                                                            the tagline is English and follows an
                                                            English name, so it is the English
                                                            name's. Nobody writes the Japanese
                                                            title with it attached.

    Neither area is thrown away in either case. What changes is which of the two names carries it.

    Everything but the parallel title is copied out of the original as written, so a subtitle
    nobody asked about is not reformatted on its way past.
    """
    s = str(title or "").strip()
    c = COLON.search(s)
    other = s[c.end():].strip() if c else ""
    head = s[:c.start()] if c else s

    e = EQUALS.search(head)
    if not e:
        return Areas(s, "", other)
    ja, en = head[:e.start()].strip(), head[e.end():].strip()
    # A second equals sign anywhere in the string means the mark is not doing the one job this
    # module knows about, so nothing is split and nothing is guessed. An empty area on either side
    # of the mark is a transcription with a piece missing, and `X = : Y` is refused for that:
    # reading Y as the parallel title would be repairing the catalogue.
    if not ja or not en or s.count("=") != 1 or JAPANESE.search(en):
        return Areas(s, "", other)
    if c and JAPANESE.search(other):
        return Areas(s[:e.start()] + s[c.start():], en, other)
    return Areas(ja, s[e.end():], other)


def title_proper(title):
    """The work's name, with the parallel title taken off and the subtitle left on."""
    return areas(title).name


def parallel_title(title):
    """The English name a title page printed after ` = `, or '' where it printed none."""
    return areas(title).parallel


def other_title_information(title):
    """Whatever ISBD's ` : ` introduced, subtitle or edition statement alike, or ''."""
    return areas(title).other


def edition_statement(title):
    """The edition this title names a reissue under, or '' where it names none.

    Only a member of `EDITIONS` counts. A subtitle is not an edition statement and this must never
    guess that it is: the cost of a wrong yes is a work's own description read as apparatus and
    dropped, which is unrecoverable from the record afterwards.
    """
    other = areas(title).other
    return other if other in EDITIONS else ""
