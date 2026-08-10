# What `facts/origin` cannot see

It answers which term `first_publication.country` rests on. Almost everything it can say is that
nobody has asked, and the list below is why that is the honest answer rather than a temporary one.

## No source in this pipeline states a first publication venue

MADB, openBD, コミックシーモア and BOOK☆WALKER catalogue the Japanese edition of a book. None of
them holds a field for where the work first appeared, so the term `japanese-serialisation-attested`
is reachable only by a person reading a publisher's page and writing a ruling. The count of works
whose country is unattested is therefore a standing measure of unfinished research. It comes down
one work at a time and no fetch closes it in bulk.

## A work first published abroad and one first published in Japan look the same

Both arrive as a Japanese book with a Japanese publisher, a 978-4 ISBN and a Japanese title. That is
the shape this module was written for, and outside its two signals it cannot tell them apart. The
corpus is therefore not a list of works published in Japan; it is a list of works with a Japanese
edition, and the difference is 2,562 works nobody has checked.

## The two signals both catch the loud cases only

A translator credit is written where a catalogue troubled to write one. MADB wrote 訳 on exactly one
of the 3,048 rows here, and BOOK☆WALKER, which supplied most of the corpus, states an 著者 and no
role at all for the great majority. A work localised without a named translator, or credited to the
original author alone, produces nothing.

A line flag is a fact about a line, and a house that carries a translation on a general line defeats
it completely. This is measured rather than feared: オルターエゴ is on KADOKAWA's MFC, the line that
also carries its ordinary Japanese MF titles, so no flag on any line would ever have reached it.

## The registry is somebody's reading and cannot grow itself

`foreign_edition` in `data/names/imprints.yaml` is set by hand from a publisher's own page. A line
that begins publishing translations, or one somebody has not looked at, carries no flag and produces
no candidate. There is no count of lines nobody has read, because nothing here knows what a line is
for until a person says.

## `review` is a lead and this module cannot tell a stale one from a live one

A work sitting on `review` because somebody looked and could not settle it reads identically to one
nobody has returned to. `data/scope.yaml` carries the reasoning and the date, which is where a
reader finds out which; nothing in the module notices.

## It says nothing about the date, and the date is where the field is usually wrong

`first_publication.date` is `facts/dating`'s and is mostly the earliest 単行本 or the day a shop
began delivering a file. A work serialised for years before its first volume carries a date that is
late by those years, and this module neither knows nor helps. §6 turns on WHERE, so the two are kept
apart on purpose, and a reader wanting to know how good the date is has to read the other term.
