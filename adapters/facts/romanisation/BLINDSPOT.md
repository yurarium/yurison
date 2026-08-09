# What `facts/romanisation` cannot see

A module that cannot say what it does not see is unfinished. This is the list, and it is the first
place to look when a romanisation is wrong and this module's tests are green.

## It takes a reading as given

The module is handed kana and asked for Latin. It has no opinion on whether the kana are the right
kana, where a source got them, or whether anyone stated them. `Uedakyōko` is a correct romanisation
of `ウエダキョウコ`, and whether that reading is right belongs to the `reading` fact.

## It cannot see a word boundary the reading does not carry

Spacing comes from the reading. An unspaced reading romanises as one word, and this module will not
guess where it divides, because a guessed division is a false claim about a person's name. 1,191
names are in that state and the budget `author names romanised as one word` counts them. Deciding
where a name divides belongs to the `division` fact.

## It does not know what kind of thing it is spelling, beyond one bit

The caller says PERSON or TITLE, and that decides only whether a grammatical particle may be
lower-cased. The module cannot tell a pen name from a company from a chapter heading, so a caller
that passes the wrong kind gets a plausible wrong answer with no complaint.

## It is blind to how its output is assembled afterwards

The four faults that produced this module were all assembly, not spelling. A caller that stitches
several renderings into a line, or splices Latin text between them, is doing something this module
cannot inspect. `normalise` exists for exactly that caller and is public for that reason, and
nothing here can prove it was called.

`build._floored` is the standing example: it joined floored runs with the raw text between them and
its docstring said it was asking the one romaniser. It was assembling a fourth pipeline.

## It cannot see the browser

`kari/app.js` selects a precomputed style and never romanises, which is why this fact is Python-side
only. If the interface ever spells anything itself, this module will not know and its tests will
stay green.

## Its own tests share one table with the subject

The tests assert on output strings, so they do not share `kana.BASE` or `DIGRAPH`. They do share the
three style names, so a style renamed in both places at once would pass. `budget_kana_left_in_a_romanisation`
is the check that does not share a table: it reads the finished string and asks whether any character
in it is kana.
