# What `facts/division` cannot see

## The source adapters stayed outside, on purpose

`boundary.py` and `analyser_division.py` moved in, because deriving a division and retiring a
guessed one is this fact. `ndl_heading.py` and `openbd_reading.py` did not, because parsing a
library catalogue and reading a publisher's collation key are about those sources. They import this
module and hand it what they found.

So a source that starts producing a wrong division still passes every assertion here. This module
can say the basis is `stated` and cannot say the catalogue was read correctly.

## A basis nobody has ruled on answers no to everything

That is the safe default and it is also silent. A typo in a basis name, or a source inventing a new
one, degrades to "believed for nothing" without anybody being told. Nothing here counts unknown
bases, so a whole source could go quietly unbelieved.

## It cannot see whether a mark reached the reader

`is_marked` says a reader is owed an explanation. Whether `kari/app.js` draws one is a different
question, answered by the interface checks. A basis marked here and unmarked on the page would
satisfy this module completely.

## The four sets it replaced could still be re-copied

`adapters/lint/facts.py` catches an import that reaches past the entry point. It does not catch a
caller that writes `("stated", "researched", "surface")` down again from scratch, which is precisely
how the four sets came to exist. The lint's own blind spot and this one are the same blind spot.

## Two of its checks stayed behind, and they are the producer-facing ones

`kana names with no stated division` asks about kana surfaces and `author names romanised as one
word` asks about a rendering. Both are about what a producer did, and the producers have not moved,
so the checks would have arrived before their subjects. They move when `boundary`, `ndl_heading`,
`openbd_reading` and `analyser_division` do.

## Its consistency assertions are now cheap, and that is worth remembering

`bases_where("cited") <= bases_where("donates")` was once a real claim about two hand-kept lists.
It is now a fact about one dictionary, so it can no longer fail in the way it used to. It is kept
because it states a ruling, and it should not be mistaken for evidence that the sets agree.
