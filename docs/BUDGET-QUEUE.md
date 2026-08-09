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
fallback basis)".

So Wikidata is analogous to Wikipedia. It never STATES a name. It is better than a machine guess and
worse than anything a publisher or the national library prints, and its job is to lift a name off
the mechanical floor. A pass earlier that day had put `community-db` in
`curate.READING_ATTRIBUTION["stated"]`, arguing that a reading is a transcription and a user-edited
base can print kana correctly without having standing over a person's name. The ruling overturns it.

**The basis is `community-printed`**, which says what it is: a community database printed the kana
and nobody with standing over the name has spoken. It outranks `analyser` and `back-converted`, it
sits below `researched`, `surface` and `stated`, and it satisfies no check asking whether a source
stated the reading. `curate.STATED_BASES` is the one list that answers that question and it carries
`stated` alone.

**The division stands and is counted.** 68 of the 73 readings carry P734 and P735, so the kana
arrive divided, and 20 more records took a space from one of them through `boundary.fill`. Refusing
the space alone would take the harder half of a single editor's claim and return 62 people to a
glued romanisation. `divisions resting on a community database` is the budget that says how many,
and `reading_boundary_basis` is what carries the mark onto a record that borrowed a division rather
than leaving the doubt behind on the donor.

**The mark.** A `community-printed` reading is `verified: false`, so it draws the `[?]` superscript,
whose tooltip says the reading comes from a community-edited database and that no publisher or
library confirms it. The superscript is the honest mark because the doubt is about the SOUNDS. The
dotted underline says a claim is ours or that a name's division is unknown, and neither is true here.

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

**Left open by this round.** `pass4_analyser.is_credit_line` refuses any string holding an
interpunct, so `くろば・Ｕ` cannot enter the name store even though `credits.split_credits` hands it
over whole. ・ separates two people in 矢立肇・富野由悠季 and sits inside one name in さりい・Ｂ, and
`inputs.SEPARATORS_WHOLE_NAMES` already records that the right answer differs by caller. Deciding it
for the store is its own round.
