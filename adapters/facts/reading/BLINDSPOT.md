# What `facts/reading` cannot see

## It owns what may be believed, not what was read

The table says a national library may state a reading. It cannot say the library was read
correctly, that the right record was matched, or that the kana were copied without a slip. The
source adapters do that work and this module takes their word for the basis they claim.

## It cannot see a source claiming the wrong kind for itself

An adapter writes its own `reading_source_kind`. Nothing here checks that a thing calling itself
`national-library` is one. `curate.py` refuses a pair the table disallows, which catches a kind
that is wrong in an interesting way and not one that is wrong in a plausible way.

## The readings themselves are elsewhere

Six `*_reading.py` adapters and five naming passes produce readings. They stayed with their
sources, because fetching from openBD is about openBD. So the population this module governs is
large and none of it is visible from here.

## `researched` demands a note and this module cannot read one

The row exists to mean a reviewer weighed evidence, and the argument for that basis is that it
carries a note saying what was weighed. `curate.problems` enforces the note. Nothing here would
notice if that enforcement went away.

## Its rulings have dates and no expiry

The `community-db` row records a decision made and reversed inside one day, 2026-08-09. That
history is a comment, and a comment cannot warn anybody. A future round that re-argues the same
point will find the argument written down only if it reads the file it is editing.
