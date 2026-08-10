# What `facts/imprint` cannot see

It answers which line a catalogued imprint string names, from a registry somebody curated. The
failure it can commit is folding two lines into one, and no count can see that: a wrong join leaves
one entry where two belonged and the page looks tidier for it.

## The registry is the answer and nothing here can grow it

`data/names/imprints.yaml` says which spellings are one line. A string no entry answers for is
reported as unresolved, which is a number somebody works down by reading a publisher's own page. A
string somebody placed under the wrong line is not reported at all, because the registry is what
this module believes.

`imprint strings no entry answers for` is the count of the first kind. There is no count of the
second, and the suite's counter-cases are what stands in for one: 一迅社 runs ten lines under one
umbrella and a substring rule for the yuri line eats four of them, so each of those is asserted to
land somewhere else, against the shipped registry rather than a fixture.

## A restyled logotype and a different line look the same

The 百合姫 line's Latin logotype lost its hyphen at books published in 2015, and both catalogues
turn over in the same year. Reading that as one line is a judgement made from dates and volumes, and
a house that renames a line while keeping its numbering is indistinguishable from one that restyled
a logo.

## It says nothing about who prints the book

An imprint is the house's own and gets no identifier. Which house a line belongs to is
`publisher_identity`, and where a distributor sits on the edge between a house and a book is the
project owner's ruling of 2026-08-08 rather than anything derivable here.

## The separator is a cataloguer's and changes with the decade

MADB writes a brand as a list, as `A　／　B`, as `A. B` and as `A : B` in different years, and the
same pair occurs in both orders. Splitting on the separator is reading one cataloguer's notation of
one period, and a notation nobody has seen yet reads as a single unfamiliar string.
