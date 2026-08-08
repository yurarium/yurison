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
| 7 | credits carrying their own cataloguing | 38 | queued |
| 8 | updates naming a work we do not hold | 27 | queued |
| 9 | titles carrying cataloguing punctuation | 23 | queued |
| 10 | credits the corpus files as a venue | 20 | queued |
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
