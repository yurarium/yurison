# What `facts/edition` cannot see

It is handed one product title, one base reading, one held reading and two credit strings, and it
answers whether they are the same work. Everything it cannot see follows from that being all it is
given.

## It cannot see a product whose title states no base

Five of the 28 translated-edition products carry no separator, so `base` answers None and this
module has nothing to compare. The shop did not say what they translate and no amount of reading
the title will recover it. Those are a question for whoever holds the shop's own catalogue page,
which states the circle and the release date beside the product.

## It cannot see a work the corpus does not hold

Four products name a base title absent from the corpus entirely: `冷たい体温`, `ふたりの日記帳`,
`人間してる？` and `風の少女達へ`. A join needs two ends and this has one. Whether the English
edition may stand as the only record of a work is a question about scope rather than about matching.

## The reading it compares is an analyser's

`pass4_analyser` reads a coinage by guessing, and a doujinshi title is the population it is worst
at. Two titles that read alike to SudachiDict may not read alike to a reader, and two that read
differently to it may be one work. The creator test is what keeps that from merging strangers; it
does nothing about a match this misses.

## It cannot see that one circle published two works that read alike

The creator agreeing is necessary and is not sufficient. Every one of the 28 products is あとき on
アトキンソン, so a circle publishing `栖鴉` and a second work whose title happened to read `スミカ
カラス` would be merged by this rule with nothing to catch it. No case exists in the corpus as
measured, which is a statement about today's data rather than about the rule.

## It cannot see a translated edition the shop does not mark

`MARKER` is the six spellings BOOK☆WALKER uses today. A seventh, or a shop that marks a translation
some other way, is invisible here and the product reads as an ordinary work.
