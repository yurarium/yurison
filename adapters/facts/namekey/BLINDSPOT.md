# What `facts/namekey` cannot see

It answers two questions and the whole of its design is keeping them apart. `fold` is the IDENTITY
key: NFKC and the space, which are typography and nothing else. `loosely` and `match_key` are for
MATCHING, and a caller opts into them by name.

## The identity key is deliberately weaker than a person's judgement

Measured over 6,076 surfaces: the space merges 108 pairs and every one of them is one person, 源 久也
and 源久也. Case merges 4, the interpunct 3 and brackets 57, and each of those can also merge two
things that are not one. The project ruled that a wrong join erases a person while a wrong split
invents one, so `fold` takes only typography.

The cost is real and is the point. くろば・Ｕ and くろばＵ are two keys here. Two people whose names
differ only by a bracketed note are two keys. Nothing in this module can tell that either pair is
one person, and nothing in it should: that is a ruling somebody records.

## A fold cannot see what a name is FOR

The same string is a work in one field and a person in another. This is handed a string with no idea
which, and the caller's `KINDS` is the only thing that says. A key collision between populations is
therefore invisible here, and `credits the corpus files as a venue` is where that shows up.

## NFKC is a standard and not a rule about Japanese

It folds a circled digit into the number beside it, so `Step.14①` normalises to `Step.141`. Part
markers are handled before a key is taken, in `pass4_analyser.part_marks`, and a caller that folds
first loses the distinction with nothing to notice it. The module cannot see the order it was called
in.

## `match_key` is five rules and not one

Five folds that answered the matching question stayed separate rather than being merged, because
they genuinely differ: one strips bracket characters and keeps the contents, another strips the
whole span. A caller reaching for "the" match key is choosing one of them, and choosing wrong looks
like a fold that is slightly too kind.
