# What `facts/printblock` cannot see

It answers one question: which publishing parties a print block on a series row stands for. It is
handed a block and it reads what is on the block.

## It cannot see whether the block was built correctly

`folded_names` is written by `build.py` when it merges the catalogue records of one print run, and
this module trusts it. A run merged that should have stayed apart, or a record whose names were
dropped before the block was written, is invisible here: `parties` faithfully reports a wrong
answer. `print_runs` in build.py is where that decision is made and `test_build.py` is where it is
pinned.

## It cannot see what a block SHOWS

A page draws one publisher and one line, from the block itself. This yields the folded records
beside it, which nothing renders. So a name that reaches this module is a name the build must be
able to spell, and that is not the same set as the names on the work page. A caller that treated
`parties` as the list of what a reader sees would be counting names nobody is shown.

## A folded record with no name at all disappears

`folded_names` holds only fields a record states, and a record stating none of them contributes no
entry. The count of parties is therefore not the count of catalogue records in the run, and the
identifiers, which `work_ids` carries, are the only reliable answer to how many there were.

## The dates it carries are the folded record's own, unreconciled

`first` and `last` come from each record as catalogued. Two records describing one run can date it
differently, and nothing here decides which is right; the imprint census measures a span from
whichever record carries the imprint, which is the question it is asking, and any pass wanting the
run's own dates should read the block, where build.py has already taken the earliest and the latest.
