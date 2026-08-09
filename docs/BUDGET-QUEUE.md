# Working the budgeted gaps, in series

Started 2026-08-08. One gap at a time, each closed by filling it rather than by narrowing what
counts. A gap that cannot be closed is recorded here with the reason, which is a different state
from one nobody has looked at.

**How to resume.** Read the table. The first row not marked done is the next one. Each closed row
names the commit so the reasoning can be found without re-deriving it.

## Order, and why

Value first, where value is what a reader meets, then tractability. Engineering debt is last because
it measures nothing about the data.

| # | budget | at start | state |
|---|---|---:|---|
| 1 | renderings still Japanese in English mode | 334 | in progress |
| 2 | citations withheld from readers | 244 | **done, 36** (an ISBN cites where a query cannot) |
| 2b | the 36 that remain | 36 | queued: 21 reachable via NDL /books/ from a work they are credited on; the other 15 want a platform byline, a shop page or the artist's own account, per §14c |
| 3 | nicovideo works with no rights | 189 | **done, 60** (capture re-run with the fixed pattern; 3 of the residue state only the platform's own ©DWANGO, 57 have no cached page and belong to the capture measure) |
| 4 | imprint strings that reach no line | 139 | **done, 18** (100 were the field repeating its publisher and moved to a measure that says so; 21 genuine lines added; the 18 left are magazines and companies, which are not lines) |
| 5 | one work under two names in a list | 71 | **done, 53** (9 merged on identical title plus shared credit; the rest fold equal with titles that differ, which is where an earlier round found 3 of 41 were bad anchors, so each wants a ruling) |
| 6 | labels with nothing to quote | 49 | **done, 0** (the YH spellings placed on 百合姫コミックス, so the line the reader is shown carries the term; bare IDコミックス still not the yuri line) |
| 7 | credits carrying their own cataloguing | 38 | **examined, unchanged**: this counts a working filter and not a debt. All 38 are a person with a role welded on, correctly withheld so the lookup reaches the person; 34 of the 38 have a person record that reads BETTER than the welded one, which reads the notation aloud (`アオ ト ヒビキ ( エ )` against `アオト ヒビキ`). It falls when captures stop welding, which is upstream in the capture and not curation. |
| 8 | updates naming a work we do not hold | 27 | queued |
| 9 | titles carrying cataloguing punctuation | 23 | **done, 0** (8 editions merged; the measure now counts what a reader is shown and not a record's faithful transcription of an edition; two publisher rulings; the last edition filed under its canonical name) |
| 10 | credits the corpus files as a venue | 20 | **done, 16** (4 ruled companies; the 16 left are artists who self-publish, which the measure was written to expect) |
| 11 | credit fields an identifier does not cover | 19 | queued |
| 12 | unreadable bookwalker rows | 15 | queued |
| 13 | incomplete attested rows | 14 | queued |
| 14 | one page cited for two claims | 12 | queued |
| 15 | undated cmoa candidates | 11 | queued |
| 16 | captures with no floor | 11 | queued |
| 17 | credit pages listing a work that does not name them | 8 | queued |
| 18 | credit identifiers naming nobody | 5 | queued |
| 19 | targets a capture wrote no row for | 4 | queued |
| 20 | titles shorter than their own reading | 3 | queued |
| 21 | names rendered two ways | 2 | queued |
| 22 | scraped counters in chapter names | 1 | queued |

**Held back, and why.** The name backlog (author readings 312, kana divisions 263, works showing a
romanisation 180, titles with no translation 171, works without English 104, uncertain readings 53,
publisher readings 16) has its own task recorded under "search the unsettled names one at a time",
because it is slow by nature and a sweep is what produced the residue. Engineering debt (stock
phrasing 903, invented markup 75, shadowed names 41, adapters off net.py 35, three as an organising
shape 27, interface reads outside an entry point 13) measures the codebase and not the corpus.

**What closing a gap may not mean.** Suppressing a mark, hiding a row, narrowing the measure, or
falling back to a romanisation where a real name is obtainable. A number that falls because the
question got smaller has told nobody anything.

## Wikidata is noncanonical and raises the floor. Ruled 2026-08-09, closed

**The project owner's ruling, verbatim:** "treat wikidata as noncanonical. use it to raise the floor
on romaji, including additional required searches". Setting the question up, earlier the same day:
"I would accept wikidata as an improved basis for any fallback romanisations (with overcoming their
fallback basis)". And the correction, made after the first implementation shipped: "important
correction to wikidata instructions: I mistyped 'without overcoming their fallback basis'".

**So the ruling is: a better string, and not a better claim.** Wikidata may raise the floor on the
romanisation a reader SEES. It does not overcome the fallback basis of the record, so a name resting
on a fallback goes on resting on one and stays in every count of the gap. That is what the rest of
this section is written against; the first implementation read the sentence without the "without"
and had these records leaving the fallback population, which is recorded below because it is the
expensive half of the knowledge.

Wikidata is analogous to Wikipedia. It never STATES a name. It is better than a machine guess and
worse than anything a publisher or the national library prints, and its job is to lift a name off
the mechanical floor. A pass earlier that day had put `community-db` in
`curate.READING_ATTRIBUTION["stated"]`, arguing that a reading is a transcription and a user-edited
base can print kana correctly without having standing over a person's name. The ruling overturns it.

**The basis is `community-printed`**, which says what it is: a community database printed the kana
and nobody with standing over the name has spoken. It outranks `analyser` and `back-converted`, it
sits below `researched`, `surface` and `stated`, and it satisfies no check asking whether a source
stated the reading. `curate.STATED_BASES` is the one list that answers that question and it carries
`stated` alone.

**Where the basis is admitted and where it is refused**, reviewed one list at a time under the
correction. It survives in three places, all of which decide which STRING is used and none of which
decides what a record may claim: `store.READING_RANK` and `build._READING_BASIS`, which pick the
better of two spellings of one person, and `pass4_analyser.wants_reading`, which lets a kana surface
take its own spelling back. It survives in `provenance.SOURCED`, because the Wikidata item page is a
document a reader can open and a marked fallback needs the route to it more than a stated reading
does. It survives in `boundary.SETTLED_BASES`, so a division may still be lent, with
`boundary.donor_basis` naming the origin on the record that receives it. It leaves
`curate.DIVIDING_BASES`, which is the list of bases whose division arrived cited, and it was never
in `curate.STATED_BASES`, `check.STATES_A_READING` or `openbd_reading.SETTLED`, all three of which
the correction reinforces.

**The division stands and is counted, and it is no longer counted as cited.** 68 of the 73 readings
carry P734 and P735, so the kana arrive divided, and 20 more records took a space from one of them
through `boundary.fill`. Refusing the space alone would take the harder half of a single editor's
claim and return 88 people to a glued romanisation. `check.UNCITED_DIVISIONS_COUNTED` is what admits
the basis past `a division cites its source`, beside `back-converted` and for the same reason: a
weak claim is still a claim, and what keeps it honest is a number somebody can watch.
`divisions resting on a community database` is that number, and `reading_boundary_basis` carries the
origin onto a record that borrowed a division rather than leaving it behind on the donor. Filling
that field is no longer enough to count as a citation either, which is the same correction one
record further on: a loan does not make a division cited.

**The mark.** A `community-printed` reading is `verified: false`, so it draws the `[?]` superscript,
whose tooltip says the reading comes from a community-edited database and that no publisher or
library confirms it. Under the correction that superscript carries the floor's own class, which is
the mark every rendering an English page spelled for itself already had, so these names are marked
exactly as a fallback is marked and `renderings resting on a mechanical romanisation` counts them.
The tooltip stays the specific sentence: the class is what the count reads, and naming the database
is what tells a reader where to go and settle it. The dotted underline says a claim is ours or that
a name's division is unknown, and neither is true here.

**The search that followed.** Every author name the project holds or renders has now been offered to
Wikidata: 1,887 names were asked for the first time, in 19 batched requests. It answered with a
reading for 132, of which 126 landed on names openBD, MADB, the National Diet Library or a reviewer
had already settled. Five of those contradicted the stronger source and lost. Six raised the floor.
221 names gained an English label. Four names were never offered, because a publisher, a platform
and the artist's own page had already settled both their reading and their English name.

Wikidata holds almost nothing for the names this project cannot read, and that is the finding. It is
worth having and it is not the route that closes the reading gap.

Note that `boundary.py` still refuses a subset of Wikidata rows for a different reason: some are
MangaUpdates romanisations converted back into kana, which is `back-converted` and never a donor.
That refusal is untouched by the ruling.

**What the budgets did, so the integrator can re-measure against it.** `renderings resting on a
mechanical romanisation` went 44 to 628, which is 584 renderings of the 73 names rejoining the count
they should never have left. `divisions resting on a community database` held at 88 and now carries
the whole weight of the admission, since the invariant stopped treating an anonymous edit as a
citation. Nothing fell.

`credits carrying their own cataloguing` went 38 to 46 for a reason that is not this ruling and is
not a fault either. It counts store records the build publishes no rendering for, and eight records
were added to the store by the round below without a build being run over them, which is what
STANDING-INSTRUCTIONS §14a means by a number that is true of one tree. A build ships all eight and
takes it back to 38. The integrator measures it again on the merge result rather than believing
either figure.

A question the correction raises and does not answer: 1,914 renderings carry `unc` without the floor
class, which is a reading a morphological analyser produced or one assembled character by character.
Those rest on less than a Wikidata edit does, and they sit outside a measure that now counts the
stronger case, which is the shape STANDING-INSTRUCTIONS §14b warns about. `author readings no source
states` counts the 393 records behind them, so the population is not invisible. Whether the floor
class should widen to take the renderings is a ruling nobody has made, and deciding it as a side
effect of this correction is the mistake this correction exists to undo.

## The interpunct in a credit is settled by evidence. Closed 2026-08-09

This was left open by the round above: `pass4_analyser.is_credit_line` refused any string holding an
interpunct, so `くろば・Ｕ` could not enter the name store even though `credits.split_credits` handed
it over whole.

Measuring the class found the larger half of it. ・ is a separator for the splitter that feeds the
store, so seven people were already IN the store cut in half, with a registry identifier minted for
each half, and five of them reached a reader that way: `Kuro Ba, U`, `Sarii, B`, `Jei, Katō`,
`Ana, C, Sanchesu` and `Buririanto, Buraun`.

**What decides it.** A ・ separates people where every piece it separates is credited somewhere else
on its own. The bibliography lists 機動戦士ガンダム 水星の魔女 青春フロンティア as
`HISADAKE / 富野由悠季 / 波多ヒロ / 矢立肇`, which is a source writing 矢立肇・富野由悠季 apart on
the work that joins them, and nothing anywhere credits くろば or Ｕ alone.

**Where the evidence may not come from**, which is the whole of the care in it. The name store and
the credit registry both hold records for くろば and for Ｕ, because the splitter under question put
them there, so a rule that asks either agrees with the split that made it: all twelve strings read as
two people, including the seven that are one. That rule was live, in `creditline`, and it is why the
site drew `Jei, Katō`. `adapters/names/interpunct.py` reads the evidence off credit fields holding no
・ at all, which is 8,812 of the corpus's 8,865 and none of the ones under question.

Two rules were tried and rejected. Script shape, that a ・ separates people where every piece holds a
kanji, gets eleven of twelve right and is wrong about `スタジオクロマト・スタジオコロリド`, two
animation studios with no kanji between them. Piece count, that three pieces means a foreign name,
fits four examples and states nothing.

The residue a person is owed is zero, and `interpunct credits nobody has ruled on` is what says so.
`data/identity/interpunct-rulings.yaml` is where an answer goes, and it is a different file from
`credit-rulings.yaml`, which settles pairs of credits sharing one reading and was here first.
