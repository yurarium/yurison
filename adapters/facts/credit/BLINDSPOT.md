# What `facts/credit` cannot see

## It holds the ruling and does not compute it

`interpunct.settled` needs the corpus's credit fields to work out which ・ the evidence can settle,
so the build computes the answers and calls `use_rulings` once. Nothing here can tell whether that
happened. A run that forgets the call gets the unruled split everywhere and no complaint, which is
the old failure with a smaller surface rather than a fixed one.

The honest guard is that `build.py` installs it beside the computation, three lines apart.

## The default is inverted, and the old argument still exists

`split` and `split_detail` still take `ruled`, so a caller can pass a different map. That is
deliberate, because `interpunct.settled` has to evaluate candidate rulings. It also means a caller
can still pass the wrong one, and nothing here would know.

## It cannot see a second splitter

Twenty-six of thirty-one splitter calls bypassed the ruling before this. The import lint stops a
caller reaching past the entry point; it does not stop one calling `names.inputs.split_authors`
directly, which is a module this fact wraps rather than owns. Moving the splitter itself is the
next slice and it is not done.

## It says nothing about whether a name is a person

`entities` decides that. A credit field naming a committee, a magazine or an editorial desk splits
here exactly as a list of people would.

## Its interpunct rule rests on evidence that can move

A ・ separates people where every piece is credited somewhere else on its own. That is a statement
about the corpus as it stands, so a work arriving tomorrow can change the answer for a name settled
today. `interpunct-rulings.yaml` exists for the cases where a person overrules the corpus, and
nothing warns when the corpus changes its own mind.
