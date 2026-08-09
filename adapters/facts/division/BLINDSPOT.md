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

## Its checks are all here now, and the reason two were held is worth remembering

`kana names with no stated division` and `author names romanised as one word` were left in check.py
on the argument that they ask about producers and the producers had not moved. `boundary.py` moved
in, which retired that argument, and the checks followed. The argument was sound when made and
became a reason not to finish about ten minutes later, which is the shape to watch for.

## Its consistency assertions are now cheap, and that is worth remembering

`bases_where("cited") <= bases_where("donates")` was once a real claim about two hand-kept lists.
It is now a fact about one dictionary, so it can no longer fail in the way it used to. It is kept
because it states a ruling, and it should not be mistaken for evidence that the sets agree.
