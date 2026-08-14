# The store as the compiled form: a plan

Written 2026-08-13 from the project owner's statement of intent: the SQLite store is the sole
compiled form of the data, updated incrementally from update runs, reconciled occasionally to prove
the incremental path works, designed as a relational model rather than a carrier for blobs,
embodying every constraint that can be expressed and answering by query for those that cannot. No
data reaches the live site around it. What the site then reads is a separate question and evolves
separately.

## 0. Where this starts, measured

The machinery this asks for exists in miniature and the gap is coverage and direction.

| | present |
|---|---|
| incremental update | `delta.write`, `delta.converge`, gated on output change; **no production caller** |
| reconciliation | `relational.equivalent()`, run weekly by `equivalence.yml` |
| constraints | `schema.sql`, `PRAGMA foreign_keys = ON`, now built on every pull request |
| queries for what constraints cannot say | `delta.DERIVATIONS`, five of them |
| one writer | `adapters/lint/onewriter.py`, enforced |

And the gap:

| | build | store |
|---|---|---|
| size | 26 MB | 2.3 MB |
| a work's fields | 31 keys on a series row | 7 columns |
| volumes | 6,108 | `edition`: **0 rows** |
| releases | 974 in the window | no table |
| publisher links | | `work_publisher`: **0 rows** |
| names, readings, romaji, ruby | 3,169 titles in `feed/names.json` | no table |

**TWO TABLES WERE DESIGNED AND NEVER FILLED.** `edition` and `work_publisher` are in the schema
with columns and constraints and no rows have ever been written to them. Nothing about that is
recorded anywhere, so the first thing this plan does is find out whether they are unfinished or
abandoned.

**THE DIRECTION IS BACKWARDS TODAY.** `relational.build` reads `data/build/*.json` and compiles the
store from it, so the store is downstream of the artefact it is meant to replace. Every section
below moves one domain to the other side of that line.

| | stage | needs |
|---|---|---|
| §1 | Measure what travels around the store | done 2026-08-13 |
| §1a | Somewhere for what a constraint refuses | done 2026-08-13 |
| §2 | Fill the two tables that were designed and never written | done 2026-08-13 |
| §3 | Volumes, editions and the print run | done 2026-08-13 |
| §4 | Releases and the per-platform offer | done 2026-08-13 |
| §5 | Renderings, which are derived from a source that stays where it is | done 2026-08-13 |
| §5a | The constraints that do not fire | done 2026-08-13 |
| §5b | A row nothing can address twice | done 2026-08-13 |
| §5d | A name is an identity here, and it must not be | done 2026-08-13 |
| §5c | What the store says it holds and does not | done 2026-08-13 |
| §5e | The domains still outside the store | done 2026-08-13; the residue is §6's queue |
| §5f | The constraints that still do not fire | done 2026-08-13 |
| §5g | A row §7 can address, and a quarantine that survives | done 2026-08-13 |
| §5h | A judgement belongs to the record that was judged | done 2026-08-13 |
| §5i | A column that means two things | done 2026-08-13 |
| §5j | A vocabulary with one home, and a key into it | done 2026-08-13 |
| §5k | A date says it is a date | done 2026-08-13 |
| §6 | The compiler writes the store; the JSON is emitted from it | DONE 2026-08-13. Every corpus file is emitted from the store and the budget is 0 |
| §7 | Incremental on every update, reconciled weekly | done 2026-08-14 |
| §8 | Turn the schedule on | §7, and TODO-github-setup §C's conditions |
| §9 | The maintenance pass, and what it works from | §1a |
| §10 | An invariant is a query on the store | done 2026-08-14; the queue of what else could move is in the section |
| §11 | The store is the artefact; the site builds from it | done 2026-08-14 |
| §12 | A test the length of what it tests | begun 2026-08-14; it never finishes |
| §13 | Nothing here reads the JSON | §10, §11 |

**WHERE §5a TO §5e CAME FROM.** An agent with no part in writing any of this reviewed
`schema.sql` on 2026-08-13, given the domain, the owner's intent above and the standing
instructions, and deliberately not given this plan, the refusal counts, or any account of why a
table is shaped as it is. It rebuilt the store and probed the constraints with real inserts. Every
figure below was then re-measured here before being written down, because a review taken on trust
is a second opinion nobody checked.

It found the identity spine, the surface and claim split, and the decompositions sound. What it
found wrong divides into constraints that never run, tables no row can be addressed in twice,
columns filled with a placeholder, and an identity built on a spelling. Those are §5a to §5d. §5e
is what it found the model cannot say at all.

## 1. Measure what travels around the store

**WHY THIS IS FIRST.** Every section after it is a migration, and a migration with no number is a
sequence of changes that feel like progress. The measure is the acceptance test for the whole plan:
it starts at roughly the identity spine and must end at everything.

**WHAT TO COUNT.** For each field the site is served, whether it is derivable from the store. The
answer is a percentage of shipped fields and a list of the ones that are not, which is the work
queue for §2 to §5 and needs no separate list to keep in step.

**WHERE IT LIVES.** A budget, so it ratchets. `data reaching the site around the store` counts
fields with no path through it, and it reaches 0 when the plan is done. It cannot be gamed by
adding tables, because it is asked of what the site SERVES rather than of what the store holds.

**WHAT IT CANNOT SEE, §14b.** A field derivable in principle and not in fact, because the emitter
still reads the JSON. That is why §6 stands as its own section: derivability is the measure and
emission is the proof, and this budget only asks the first.

**DONE 2026-08-13, OPENING AT 701 OF 707.** `adapters/facts/served` enumerates the field paths in
the corpus files `deploy.sh` copies, and `data reaching the site around the store` counts those the
store could not answer. Six paths are claimed today, all of them identity: an id and a title in each
of the four files that carry one.

**TELLING A MAP FROM A RECORD IS THE WHOLE MODULE**, and it decides whether the number means
anything. `feed/names.json` holds 3,301 titles under folded keys, so walking it naively reported
137,131 paths for a corpus that has 707. Two signals collapse a map: keys that are not field names,
which catches `authors` keyed `*sow*` and the string-valued `floor` and `phrases`; and values that
share a small vocabulary, which catches a map keyed by something identifier-shaped like `c01876`.

**THE COUNTER-CASE IS THE ONE THAT WOULD HAVE READ AS SUCCESS.** A `series.json` row has 31 keys and
nearly all its values are scalars, so a rule reading "many keys, simple values" as a map would
collapse the most important record in the corpus to one path and report near-total coverage of a
store holding almost none of it. Its keys are field names, so the first signal refuses it. The test
pins that row at 31 fields and asserts it is never collapsed.

**IT MISSED A THIRD KIND OF MAP, FOUND WHILE §5 WAS BEING SCOPED, AND 155 OF THE 675 WERE ONE
FIELD.** `series.json:merged` maps a retired work id to the work that absorbed it, 151 entries, and
`credits.json:merged` holds 6 more. The keys pass as field names and the values are bare strings, so
the two signals above both stay silent. A third signal reads an ISSUED SERIES: every key sharing one
prefix and one digit width, which no record's field names do. The size floor is waived for it alone,
because six entries are record-sized and are still distinguishable by being called `c00154`.

**SO 675 BECOMES 520 FOR A MEASUREMENT REASON AND NOT FOR WORK DONE**, recorded here because a
budget that falls on its own is the one thing a ratchet cannot tell from progress. Nothing about the
store changed. The error was in the safe direction, over-counting rather than under-counting, which
is why it survived: an inflated number reads as work remaining rather than as coverage.

**WHAT IS DELIBERATELY OUT OF THE POPULATION.** `checks.json`, `status.json` and `run.json` are
copied to the site and describe the RUN rather than the corpus. Requiring the gate's own findings to
come from the store would be a category error, and `served.CORPUS` draws that line where a reader
can disagree with it.

## 1a. Somewhere for what a constraint refuses

**THE RULE THIS PROTECTS, stated by the project owner 2026-08-13.** An update runs unattended and
must go on running, populating whatever it can. Data that cannot be merged or represented
consistently is surfaced so that a person, or somebody working on their instruction, can deal with
it afterwards. Nothing about moving to a relational store may weaken that.

**THE PLAN AS FIRST WRITTEN BROKE IT IN TWO PLACES.** §4 said a release naming a work we do not hold
"stops being a budget and starts being a refused insert", and §3 said a constraint makes a fault
"unstateable". Both are right where a person is present and wrong at 00:37 JST. A refused insert in
an unattended run either fails the job or drops the row silently, and the second is worse because
nothing says it happened.

**THE PROJECT ALREADY ANSWERS THIS AND THE ANSWER HAS TO SURVIVE.** `data/queue` holds 35 files
that exist to be worked by hand. `check.py --runtime` counts and reports and never fails while
`--gate` fails, which is the same split one layer up. `update.yml` marks five steps
`continue-on-error` on purpose. What changes under this plan is only that a schema refuses at
INSERT time, before any report could be written, which is earlier and harder than a check that runs
afterwards.

**WHAT TO BUILD.** The loader attempts the insert, catches the integrity error, and writes the row
to a quarantine table carrying the constraint that refused it, the source record it came from, and
when. The run continues. Nothing is lost and nothing is admitted.

**THIS KEEPS "NO DATA TRAVELS AROUND THE STORE" TRUE IN THE STRONG SENSE.** Even the data that could
not be modelled is IN the store, in a table of its own, rather than in a file beside it or in a log
nobody reads. A queue file remains the right place for a DECISION somebody has to make; the
quarantine is the record of what the compiler could not admit, and the two are different things.

**HOW IT IS MEASURED.** A budget counting quarantined rows, which ratchets like every other. It is
the number that tells a bad week of captures from a wrong model, and keeping that distinction
visible is why it must be counted and watched.

**THE FAILURE MODE TO WATCH, and it is why this section exists rather than a paragraph in §3.** A
constraint that is routinely violated has stopped being a constraint and become a filter. Quarantine
makes an unattended run survivable; a quarantine that grows every day means the schema is asserting
something the data does not support, and the honest response is to change the model rather than to
keep filtering. Without the budget those two look identical from outside.

**RECONCILIATION COMPARES QUARANTINES TOO.** §7's weekly rebuild sets a fresh compile beside an
incrementally updated store. If it compares only admitted rows, an incremental path that quietly
discarded what a rebuild keeps would pass. So the quarantine is part of what must agree, and a
difference in it is a divergence exactly as much as a difference in `work`.

**A FULL REBUILD REFUSES NOTHING, AND THAT IS WHAT STOPS THIS BECOMING AN EXCUSE.** The project
owner named the risk on 2026-08-13: the existence of a quarantine must not become a reason to leave
data unintegrated. A refusal is always easier to set aside than to understand.

§2 IS THE EVIDENCE THAT THE RISK IS REAL, and it happened before any quarantine existed to tempt
anybody. 382 volumes were refused on the citation constraint. Every one was the loader reading only
the volume when the work's own record named the page its date came from. **Not one was data that
could not be represented.** A quarantine would have absorbed all 382, the number would have looked
like honest work, and the rule would still be wrong today.

So the two paths answer differently, which is the split `--runtime` and `--gate` already make one
layer up. A REBUILD runs where somebody is present, on every pull request and in the weekly
equivalence job, and it FAILS on a refusal: the loader is wrong until shown otherwise. The
INCREMENTAL path runs at 00:37 with nobody watching, and quarantines so the run continues.

`relational --build` exits non-zero on any refusal as of 2026-08-13, locked in while the count was
0. A rule adopted when the number is already zero costs nothing to keep and a great deal to regain,
and `gate.yml` already builds the store on every pull request, so nothing new has to run for it to
bite.

**IT HAS NOT BEEN BUILT, AND §5's REVIEW IS WHERE THAT STOPPED BEING FREE.** The table does not
exist. Nothing has needed it, because every run so far has been a full rebuild with somebody
present, which is the path that FAILS on a refusal by design. Two constraints will now meet correct
data the moment an unattended run has one: `CHECK (isbn IS NULL OR dated IS NOT NULL)` was locked
while the count was 0, and the budget it replaced says in its own docstring that its floor is not
zero, since openBD holds no record at all for 245 of the corpus's 2,321 ISBNs. An announced volume
carries an ISBN before any registry states a date. `edition`'s inability to hold a printing and a
delivery for one book, §5b, is the other.

Neither is a reason to relax a constraint. Both are reasons the quarantine has to exist before §7
turns an unattended run loose, and its absence is now the gap rather than a plan for one.

**AND THE SCHEMA FILE IS NOT THE WHOLE SCHEMA.** `derivation` is created by `delta.ensure` and
`_tables` excludes it by name, so a reader of `schema.sql` cannot tell what the database holds. The
quarantine must not arrive the same way.

**DONE 2026-08-13, IN `schema.sql` WHERE A READER FINDS IT.** `quarantine` holds the row as the
loader had it, the constraint that refused it, what produced it and when. `build(quarantine=True)`
is the unattended path and a rebuild leaves it off, so the two answer differently exactly as this
section argues. `rows the store could not admit` counts it and is 0.

**AND THE PATH IS WATCHED WORKING RATHER THAN DECLARED.** It runs at 00:37 with nobody present, so
`quarantine_row` is reachable from a test, which a closure was not, and the test plants a refused row,
sees it filed under the table it was going to, and then asserts that NOTHING was admitted. A
quarantine nobody has seen accept a row is the same thing as a constraint nobody has seen refuse
one, which is the argument this whole file makes about controls.

**WHAT THIS MEANS FOR A ROW IN QUARANTINE.** It is there because an unattended run met it and had
nowhere else to put it. The next rebuild will refuse it and fail, so it cannot be left: either the
loader learns it, the model changes, or §9 records a ruling that makes it representable. The
quarantine holds a row for hours, and it is a shock absorber rather than a shelf.

## 2. Fill the two tables that were designed and never written

**FIND OUT WHY FIRST.** `edition` has seven columns including `isbn`, `volume`, `dated` and `cite`,
and `work_publisher` is the edge that would make `publisher pages listing a work from another
house` unstateable, which `schema.sql` claims as one of the two invariants that stop being
checkable. Both are empty. Somebody designed them and stopped, and the reason is not in the file.

The likeliest reading is that they were written when the schema was designed and the loader was
built for the spine alone, so nothing ever populated them. If that is right this section is small
and is the cheapest real coverage in the plan. If it is wrong, the reason is worth more than the
work.

**WHAT IT PROVES.** That a domain can be added to the loader without disturbing the spine, which is
the pattern §3 to §5 repeat at increasing size.

**DONE 2026-08-13, AND THE REASON WAS THE DULL ONE.** `schema.sql` and the loader arrived in one
commit, the loader was written for the identity spine, and nothing came back for the rest. So both
tables carried columns, constraints and an index and had never been inserted against. No decision
was reversed and none had been recorded.

`work_publisher` holds 2,661 rows, 1,755 of them naming the line as well as the house, read off
`publishers.json`'s own `works` list because that IS the edge; going by way of the print blocks
would have rebuilt a join the publisher pass had already made. `edition` holds 6,108, one per
volume, 3,290 with an ISBN and 3,672 printings against 2,436 shop deliveries.

**THE LOADER WAS HIDING ITS OWN REFUSALS AND THE FIRST RUN LOOKED PERFECT.** `INSERT OR IGNORE`
dropped 382 volumes and reported `refused 0`, because SQLite treats the conflict as handled and
raises nothing for the loader to catch. A constraint that quietly drops a row is worse than no
constraint, since it reads as coverage. Plain `INSERT` made the 382 visible, every one of them
`CHECK (dated IS NULL OR cite IS NOT NULL)`.

The refusals turned out to be my rule's doing. 173 of the 382 were volumes whose
`published` equals their `delivered`, so the date IS the shop's and the shop is the citation. The
other 209 sit under a work whose record names the page it came from: `C418820` carries
`records: [{source: madb, url: .../id/C418820}]`, and the work_id is that page's own id. My rule
read only the volume. Citing the record's page admits all 6,108 with none refused, and the
constraint was never relaxed to get there.

**WHAT IS STILL NOT MODELLED, and it is §3's opening.** `edition.volume` is an INTEGER, so a
designation cannot go in it: `上`, `創刊号` and `2017年1月号` are what a volume is called and the
schema has nowhere to put one. 983 volumes carry a designation today.

## 3. Volumes, editions and the print run

**THE JUDGEMENT STAYS IN THE COMPILER, and this is the load-bearing idea of the whole plan.**
`build.py` is 7,678 lines and most of it is judgement: which print records describe one run, what a
designation means, when a delivery date may stand for a publication date, which of two catalogues
wins. None of that moves. What changes is where the answer is written. A migration that tried to
re-express the judgement in SQL would be a rewrite of the project's hardest reasoning against a
deadline set by a schema.

**WHAT THE SCHEMA HAS TO CARRY.** A volume with its designation and its number, an ISBN where one
exists, a date with its basis and its source, and the record each fact came from. `claim` already
holds that shape for other facts and is the pattern to follow rather than a second one to invent.

One constraint is worth having here on its own. `volumes with an isbn and no date` is a zero budget
today, enforced by a check. As a schema constraint it becomes unstateable in the admitted tables,
which is what §1a's quarantine is for: an unattended run that meets one records the row and carries
on rather than failing or dropping it.

**DONE 2026-08-13.** `edition` grew what a volume is called, what its date rests on, and a refusal
for an ISBN nobody dated. The loader fills all 6,108 rows and none is refused.

  A DESIGNATION, which is the fault this section opened on. `volume` is a position and an integer
  answers it; 983 volumes are called `上`, `創刊号` or `2017年1月号`, and no integer holds one. The
  schema grew a column rather than the corpus losing a fact to a type.

  A BASIS FOR THE DATE, following `claim`'s pattern rather than reusing its table, which is scoped
  by its own CHECK to what a NAME is. A closed set of four, because a basis nobody can name is a
  basis nobody can weigh: 2,436 shop deliveries, 2,326 from the MADB 単行本 dataset, 78 national
  library, 49 openBD. 1,219 rows state none and are admitted saying so, since an admitted silence
  beats a basis invented to satisfy a column.

  `CHECK (isbn IS NULL OR dated IS NOT NULL)`. An ISBN is a key into every dated registry there is,
  so a volume holding one and no date means nobody asked. Locked in while the count was 0.

**WHAT WAS DELIBERATELY NOT CONSTRAINED.** No row carries both a number and a designation today,
all 983 against 4,091. That is left as an observation and not written in as a CHECK, because
`build.volume_number` reads 創刊号 as the first issue, so a designation can legitimately acquire a
position, and a constraint on an accident refuses the first correct row that meets it.

**THE NEW CONSTRAINT BROKE A TEST WRITTEN AN HOUR EARLIER**, which is the system working. §2's
assertion that one ISBN is one book inserted an undated ISBN twice, and §3 made that unstateable.
The test carries a date now, because what it asserts is about the ISBN rather than about the date.

`data reaching the site around the store` falls 696 to 693.

## 4. Releases and the per-platform offer

974 releases in the window and a per-platform `sources` array on every series row: what a platform
holds, what it charges for, and when it last updated. `schema.sql`'s own comment says these are
properties of the platform's offer and not of the work, which is a relational statement already.

**WHAT BECOMES EXPRESSIBLE.** A release belongs to a work and to a platform, both by foreign key, so
a release naming a work we do not hold is refused rather than counted. `updates naming a work we do
not hold` is 18 today, and those 18 are the reason §1a comes first: this is the commonest way a
capture arrives faster than the corpus can admit it, so it is the case the quarantine will carry
most often and the one that must never cost an unattended run its other work.

**DONE 2026-08-13, WITH THREE OF THIS SECTION'S ASSUMPTIONS CORRECTED BY THE DATA.** `platform` 50,
`offer` 1,820, `release` 961, none refused.

  A PLATFORM IS ITS NAME, NOT THE ADAPTER THAT READ IT. Six display names carry two capture slugs
  each: コミックDAYS arrives as `comic-days` and `backfill`, 一迅プラス as `ichicomi` and
  `claim-resolved`. Keying on the slug would have split one platform into two.

  AN OFFER IS A LISTING, NOT A PLATFORM. Keyed `(work, platform)` the loader refused 11 rows and
  every one was right to exist: 不器用ビンボーダンス has three ニコニコ漫画 listings at three
  addresses, and 田所さん two. All 1,820 state a url, so the address is an identity the data holds.

  A RELEASE MAY NAME NO WORK. This section expected the foreign key to refuse one that does, and
  measured, an exact title match resolves 944 of 974 while the identifier a release carries or the
  folded title resolves 971. The 3 that resolve to nothing carry no identifier at all and are the
  GigaViewer works WORKS-PLAN §3 left without a page. A release is an event somebody observed and
  the work is a join that may not have been made, so `release.work` is nullable: a DANGLING work is
  refused, an ABSENT one is admitted and counted. Refusing those 3 would push a fact the site is
  served out of the store, which is the one thing this model may not do.

**THE ACCESS COUNTS ARE NOT CONSTRAINED TO SUM.** 87 of 1,820 offers state modes adding to more
than the instalments counted. A CHECK would have refused all 87, and the interface already says
`12 free · 3 to buy · 5 not recorded` in its own words, so the arithmetic is a fact about the
capture rather than a rule the data breaks.

**AN INSTALMENT IS NOT A CHAPTER**, raised by the project owner while this section was being
written and named into the schema before it shipped. `offer.instalments` counts what a platform
sells separately, which is often a part of a chapter. There are three counts and the corpus holds
one; `docs/GAPS.md` carries the rest, including that what a reader is SHOWN is a separate question
and out of this plan's scope.

`data reaching the site around the store` falls 693 to 675.

## 5. Renderings, which are derived from a source that stays where it is

**`data/names` IS A SOURCE AND DOES NOT MOVE.** `curated.yaml` is hand-edited, the store is
journal-backed, and `curate.py` is a person's tool. What belongs in the relational store is the
DERIVED rendering: the English a row shows, the reading behind it, the romanisation styles, the
ruby spans, and the basis and source of each. That is `feed/names.json`, 3.8 MB, and it is the
largest domain in the plan.

It goes last because it is the biggest, it is the one whose shape is least like a table today, and
every check that runs the interface reads it, so getting it wrong is visible everywhere at once.

**WHAT IT WOULD BUY.** `a work shows the English its record holds` and `the interface folds a name
key as the build does` are both reconciliations between two producers, which §5 of GATE-PLAN argues
is evidence there should be one. A single keyed table is that one producer.

**DONE 2026-08-13. A CLAIM IS ABOUT A NAME AND NOT ABOUT A THING**, which is the fault the section
turned on and it was costing the store most of the domain. `claim` was keyed on `subject_kind` and
an identifier, so a name resolving to nothing had nowhere to hang and the loader skipped it with a
bare `continue`: 890 readings and every one of the 4,174 English renderings the corpus holds were
missing from a store that reported no refusals. `surface` is the keyed table both sides were
talking about, keyed on `facts/namekey.fold` because that is what the site joins on.

`surface` 27,294, `claim` 11,077 against 5,005, `romanisation` 53,472, `ruby` 14,067,
`credit_part` 4,951, none refused.

  `en_forms` IS THE CLAIM TABLE READ BACK, and it is why neither it nor `en` needed a column. Every
  English form is a row, `basis_for_predicate` carries the ranking as data, and the one the site
  shows is `ORDER BY rank DESC LIMIT 1`. A displaced form is kept beside it rather than discarded.

  THE TWO VOCABULARIES OVERLAP ON ONE WORD AND MEAN DIFFERENT DOCUMENTS BY IT. `stated` is a source
  printing the kana and it is also a source printing the English, and `claim.basis` alone admitted
  either for either. The compound key `(basis, predicate)` is what makes an English name resting on
  `analyser` unstateable.

  RUBY IS SPANS AND NOT A BLOB, `credit_part` is parts and not a list, and `romanisation` is three
  rows and not a nested object. A JSON list in a TEXT column is the carrier this store exists to
  stop being, so each became the table its shape already was.

**THREE OF THE 3,690 FIRST REFUSALS WERE THE LOADER AND NONE WERE THE DATA**, which is §1a's rule
holding for the third time. `_kind_of` asked only about the reading, so 194 English names whose
source is the name's own Latin surface were refused for want of an address to a document that does
not exist. `basis_for_predicate` was filled from `reading.bases()`, which names the four a source
can STATE and not the six a reading can REST on, so 3,496 analyser readings had no admitted pair.
And `source_kind`, whose comment says it is every kind that exists, was assembled from the reading
attributions alone, so `bibliography` had no row and 113 English names transcribed from a book's
own title page were refused.

**WHAT THE STORE CANNOT REPRODUCE, MEASURED RATHER THAN ASSUMED.** Setting the store beside the
file the site is served: romanisations, ruby and credit divisions match at 0 of 3,301, 9,743, 7,479
and 3,399; author readings match at 0 of 2,389. English titles differ on 18 of 3,186, and each is
the compiler's own derivation over a title the store holds, either a name already in Latin or a
base title plus an edition marker. §6 is what settles those, since derivability is what §1 measures
and emission is what proves it.

Setting the two side by side also found a fault neither side could see
alone. 62 of 386 publisher keys and 112 of 399
imprint keys in `feed/names.json` hold a space, and every lookup the site makes folds it away, so
those entries are unreachable. 5 publisher pairs hold different things under one folded key and the
reachable one is the poorer: `いんどの宮殿！` carries the English, `いんどの宮殿!` carries the
identifier, and a reader lands on the second. The build sees two keys it wrote, the interface gets
an answer to what it asked, and only a table with one row per fold shows the pair. Documented in
`docs/GAPS.md` and deferred as pipeline work; the loader prefers the entry a reader can reach.

`data reaching the site around the store` falls 520 to 391, and `feed/names.json` from 87 paths to
2, both of them the file's own datestamp and note.

## 5a. The constraints that do not fire

**THIS IS FIRST BECAUSE EVERY SECTION BEFORE IT CLAIMED SOMETHING THAT IS NOT TRUE OUTSIDE THE
LOADER.** `PRAGMA foreign_keys = ON` is line 23 of `schema.sql` and it is a PER-CONNECTION setting.
`executescript` applies it to the connection doing the build and to nothing else, and SQLite does
not store it in the file. A plain `sqlite3.connect('data/relational.db')` reports 0 and accepts
`INSERT INTO work_credit VALUES ('w-nope','c-nobody','x',0)` without complaint. `ask`, `equivalent`
and `delta.write` all open exactly that way.

So the header's claim that five `check.py` invariants have become foreign keys holds for a full
rebuild and for nothing else, and §7's incremental path is precisely where it does not hold. It is
the same shape as the fault §2 met: a constraint that quietly does not apply reads as coverage.
The fix is that one place opens this database and turns the pragma on, and nothing else calls
`sqlite3.connect` directly.

One column carried a check that passed on everything. `work.first_event` read `CHECK (first_event IN
('publication', 'shop-delivery', NULL))`. A comparison against a list holding NULL answers NULL for
anything not matching, and a CHECK passes on NULL, so `'banana'` inserted. `edition.kind`,
`claim.predicate`, `surface.kind` and `credit.kind` all omit the NULL and all constrain properly;
this column was the one exception and had asserted nothing since the day it was written.

**A TABLE THAT READS AS ENFORCEMENT AND IS DECORATION**, which is §13 caught in my own schema.
`basis_admits_kind` carries the ruling on which evidence each basis admits, its comment calls it
"that ruling as a table instead of as a Python dict", and no foreign key or check anywhere reaches
it. 4,749 of the 10,597 claims that carry a source kind hold a pair it forbids, led by
`('translated','derived')` at 2,767.

**DONE 2026-08-13, AND THE 4,749 WERE THREE FAULTS OF MINE STACKED ON ONE REAL ONE.** The table was
filled from the READING attribution alone, and `facts/reading` holds two: the English one admits
`('translated','derived')` on its first line. Loading both, scoped by predicate, leaves 1,227.

  A DISPLACED CLAIM WAS WEARING THE LIVE CLAIM'S CITATION, which §5 did and this found. A
  conflicts entry holds `basis`, `source` and `value` and no more, and the loader built each one
  from the whole record, so 333 English and 598 reading conflicts were admitted holding the live
  claim's page, kind, dates and note. That is one entry with two claims and one citation between
  them, which is the exact fault `provenance` exists to catch. Fixing it leaves 454.

  A BASIS NOBODY HAS RULED ON IS NOT A DEFECT IN THE DATA. `back-converted` is in `division.BASES`,
  owes a document by `provenance.SOURCED`, and `READING_ATTRIBUTION` has never carried a row for
  it, so 22 readings rest on a basis nothing can admit or refuse. That is a gap in the vocabulary
  and it is in docs/GAPS.md.

  A NAME THAT STATES ITSELF OWES NOTHING, and the store had thrown away the reason. `_kind_of`
  normalises a self-sourced claim to the kind `derived`, which is true and which leaves nothing in
  the row saying the evidence is the name itself; 327 claims then read as unadmitted. `self_sourced`
  is now a table filled from `provenance.SELF_SOURCED`, so the question can be asked in SQL without
  a second copy of the vocabulary.

**WHAT IS LEFT IS 105 AND IT IS A REAL FINDING.** 102 are English romanisations citing a community
database: `ATTRIBUTION` admits `derived` for `romaji` and nothing else, and the project owner ruled
on 2026-08-09 that Wikidata may raise the floor on a romanisation. The table was written before the
ruling and the data now disagrees with it 102 times. 2 are publisher names on `official-jp` citing
the national library, and 1 is a kana surface citing a platform.

**AND THE TWO ROUTES AGREE EXACTLY**, which is what makes the number worth anything. `check.py`
counts it over `data/names` and the store counts it over `claim` joined to `basis_admits_kind` and
`self_sourced`, both answering 105 with the rule owned once by `facts/reading`. Neither shares the
other's blind spot, so a loader dropping rows would show as a divergence rather than as agreement.
The composite key goes on `claim` when the count is 0.

**AND ONE VALUE THE SCHEMA DECLARED LEGAL AND MADE UNSTATEABLE.** `claim.predicate` admitted
`'romanisation'` and `basis_for_predicate` holds no romanisation row, so the composite foreign key
refused every such claim. §5 decided a romanisation is a function of the reading and belongs in its
own table, which is right, and the predicate should have gone at the same time. It has now.
`edition.kind = 'serialisation'` stays, and the difference is that an enum member nothing has
produced yet refuses nothing and asserts nothing false.

**THE WEAKER CHECKS, AS ONE BATCH, ALL ADOPTED WHILE NOTHING VIOLATED THEM.** `edition.volume` took
a negative number and now will not. `id GLOB 'w[0-9]*'` refused `'wanted'` and admitted
`'w1garbage'`; it is the full five digits now, and it immediately caught `test_delta.py`, which had
been planting `w1` and `c1` since it was written. A two-step alias cycle is the one thing no CHECK
can say, so `aliases pointing in a circle` is a standing question instead, which is the owner's
"support querying to verify logical constraints that cannot be so expressed" in its first use.

**`release.kind` IS LEFT UNCONSTRAINED ON PURPOSE.** Its five values are written in `build.py` and
nowhere else, so a CHECK here would be their second home, which is the fault every ruling table in
this schema exists to prevent. The vocabulary needs a `facts/` module first, and that is pipeline
work under §9's boundary.

## 5b. A row nothing can address twice

**THE LARGEST TABLE HAS NO KEY, AND THAT IS WHAT BLOCKS §7.** Ten groups of `claim` rows are
byte-identical on all eleven non-id columns. No subset of columns identifies a claim, so
`delta.write`'s split into a key and its values has nothing to key on, and neither an upsert nor a
retraction can be expressed. Re-running a name pass would multiply claims rather than replace them.
"Updated incrementally to the extent possible" is not reachable while the table carrying most of
the corpus has no row anyone can address a second time.

**DONE 2026-08-13. A CLAIM IS ITS NAME, WHAT IS SAID ABOUT IT, THE ANSWER, THE BASIS AND THE
SOURCE.** Two rows agreeing on all five are one claim said twice, and 51 were, most of them because
112 author spellings fold onto another's key: `BUNBUN` and `ＢＵＮＢＵＮ` reach one surface and
repeat each other, and a conflicts list also carries values the live claim already holds. Two
SOURCES giving the same answer stay two rows, because `claims resting on a community database`
counts them separately and should. The index coalesces the source, since 20 claims name none and a
NULL in a unique index constrains nothing, which is the trap `work_credit` was in.

The loader skips a duplicate rather than leaving the index to absorb it. A loader relying on a
constraint to swallow what it knowingly emits is the `INSERT OR IGNORE` of §2 again.

**`work_credit`'s PRIMARY KEY CONSTRAINS NOTHING.** All 4,165 rows have `role IS NULL`, SQLite
permits NULLs in a rowid table's primary key, and so the same edge inserts three times running. The
section header above it reads "the edges, which are where roles live" and the role is empty corpus
wide, because `credits.json` writes its works list as `{"id": "w00205"}` with no role in it. Either
the roles are elsewhere and this column should be filled from there, or they are not held at all
and the comment is describing an intention.

`seq` is documented as "the order the field wrote them in" and the loader numbers each CREDIT's
works rather than each WORK's credits. 2,222 edges carry `seq = 0` and 185 of the 375 works with
more than one credit have the same seq on every edge, so byline order cannot be recovered. It also
sits outside the key, so it cannot break the tie it was meant to break.

**DONE 2026-08-13, AND `seq` IS GONE RATHER THAN CORRECTED.** A column holding a wrong answer is
worse than no column, and the right answer is not on this route: `credits.json` writes its works
list as `{"id": "w00205"}`, while 631 name-and-role pairs sit on `series[].credits[]` and are
reachable only by joining a NAME to a credit identifier. Both the roles and the order arrive with
§5d. The key is a unique index over `coalesce(role, '')`, which is the same intent the primary key
had and which fires.

**A VOLUME HAS NO IDENTITY EXCEPT ITS ISBN**, and that is why `edition` cannot hold both events for
one book while its own comment says the two events are the point. 812 volumes state a printing date
and a delivery date that differ. Holding both needs two rows, `isbn UNIQUE` refuses the second, and
dropping the ISBN from the second leaves nothing tying it to the first. `(work, volume)` cannot
serve either, because 13 works carry a reissue and w00174 legitimately holds volume 2 twice at
different ISBNs. So the loader's choice to keep the printing and discard the delivery is forced by
the shape and was never a decision.

The comment also cites `a delivery date never stands beside a printing` as the Python saying these
are different events. That invariant says a work dated from a shop's 配信開始日 holds no publication
date from anywhere else, which is a rule about one work's date field and not about two rows. The
citation is doing work it cannot do and needs replacing along with the key.

**DONE 2026-08-13. THE BOOK AND THE EVENT ARE TWO TABLES.** `volume` is the thing on a shelf, 6,108
of them, and `edition` is something that happened to it on a date, 6,920, keyed `(volume, kind)`.
The 812 extra rows are exactly the volumes that state two dates, so nothing is discarded any more.

  THERE IS NO KEY ON A VOLUME BEYOND ITS ISBN AND THE DATA IS WHY. 92 rows share a work, a position
  and a designation with another, 40 of them holding no ISBN at all. 13 works carry a reissue, so
  w00174 legitimately holds volume 2 twice at different ISBNs, and a UNIQUE over the three would
  refuse a real thing this project holds. The surrogate id is the honest answer.

  ONE CONSTRAINT WAS LOST AND IS RECORDED RATHER THAN ABSORBED. `CHECK (isbn IS NULL OR dated IS
  NOT NULL)` had both facts on one row and no CHECK reaches across two tables, so it is the standing
  question `volumes with an isbn and no date`, which `check.py` has held at 0 since §3.

  AND ONE QUESTION BECAME ASKABLE THAT NEVER WAS. `books a shop delivered before they were printed`
  answers 552. Nothing could ask it while the store held one event per book, and
  `adapters/cmoa_volumes.py` had measured the same shape from the capture side and left it there.

## 5c. What the store says it holds and does not

**DONE 2026-08-13, AND EVERY ONE OF THE THREE COLUMNS TURNED OUT TO BE A CLAIM.** `admission` holds
1,887 grounds across 1,816 works, naming a comparator, a shelf, a page and a date. `volume_claim`
holds 2,573, because 72 works have records stating DIFFERENT counts and one column would have to
pick one and discard a disagreement. `explicit_content` is filled from the same file and is False on
every row, which is a measured answer rather than a column default. Both columns are gone from
`work`, for the reason `seq` went: a column holding a placeholder reports as filled.

`data reaching the site around the store` falls 388 to 380.

**THREE COLUMNS ON `work` ARE SATISFIED BY A PLACEHOLDER.** `admitted_by TEXT NOT NULL` reads
`'unstated'` on all 3,040 rows, and its comment says a row with no grounds is a work nobody decided
to include. The grounds exist: `works.json` carries a structured `admitted_by` on 1,887 records
with a comparator, a shelf, a url, a date and a note citing DEFINITIONS §2. The loader reads the
field from `series.json`, which has no such key. `volume_count` is NULL on all 3,040 for the same
reason and `explicit_content` is 0 on all of them. A NOT NULL whose every value is the word for
null is worse than a nullable column, because it reports as filled.

**55 WORKS CARRY NO NAME AT ALL**, found here while checking the review's collision figure rather
than reported by it. Every one has its folded title in `feed/names.json`. The loader resolves a
name to a work by exact match against `work.title`, and NFKC folds `！` to `!`, so
`一畳間まんきつ暮らし！` never matches the raw title it came from. Indexing the subjects by the same
fold the table is keyed on resolves all 55. Done by §5d, which replaced the title match with the
fold, and the count is 0.

**869 NAMES WHOSE PARTING POINT THE CORPUS STATES ARE RECORDED AS HAVING NONE.** §5 argued that
`undivided` needed no column because the store holds the reading and whether the credit is a
person, which is everything the flag is computed from. That is wrong. The flag turns on whether a
parting point is STATED: 680 authors carry `reading_boundary` and 276 carry `reading_family` or
`reading_given`, 889 between them, and the store holds 20 division claims because the loader demands
a `reading_boundary_basis` that 660 records write as prose. Either the column comes back or the
division claims are loaded from the fields that state one.

**`verified` SITS ON THE NAME WHILE THE CLAIMS DISAGREE.** 638 surfaces carry a non-NULL `verified`
and two or more distinct reading values, so the flag cannot say which reading a person ruled on.
That is the flattening `claim` was introduced to end, reintroduced one table over.

**DONE 2026-08-13, AND IT COST ONE COLUMN.** A conflicts entry is a claim somebody moved aside, and
`claim.displaced` says so, which is what `verified` was missing a referent for. It also corrects a
number: `names two sources disagree about` reports 1,001, and only 107 of those are two LIVE claims.
The other 894 are a live answer beside one already set aside, which is not two sources disagreeing.

**A CITATION THAT CITES NOTHING SATISFIES `edition`'s CHECK.** 915 rows cite the literal string
`'ndl'`, and 2,818 cite a series-level page, one of them shared by 119 volumes. The check the
comment names, `per-book dates cite their page`, is about per-book pages specifically, and 3,733 of
the 6,108 dated rows carry a citation that does not witness the date. `cite = 'nonsense'` inserts.

A CHECK on the shape would refuse the 915, which are the corpus as it stands, so `dates cited to
something that is not a page` counts them instead and answers 915. A CHECK asking whether a citation
EXISTS cannot ask what it is.

**`imprint` IS KEYED ON A SPELLING AND A LINE IS IDENTIFIED BY ITS SLUG.** 906 of 2,661
`work_publisher` rows carry no imprint, because the print blocks spell one line as `Yuri-hime
comics`, `Yurihime comics` and `IDコミックス　／　Yurihime comics` and the loader matches by exact
name. 125 of 306 imprint rows have no slug. 47 work and publisher pairs have more than one print
block and 15 name different imprints, of which the loader keeps the first without counting the
rest. `parent` is free text and one value resolves to no imprint.

Folding the print block's spelling onto the registry's takes 906 to 833, and `works on a house with
no line named` counts what is left. Those are lines the registry does not carry, which is data to
find rather than a join to fix, and the multi-block case goes to §5e with the byline.

## 5d. A name is an identity here, and it must not be

**THIS IS THE ONE THAT NEEDS A RULING BEFORE IT NEEDS CODE.** `schema.sql` opens by saying a name is
not an identity, that two artists share a pen name and one artist changes theirs. Then
`surface UNIQUE (kind, folded)` makes the folded name the identity of a title, and `credit.surface
UNIQUE` makes a spelling the identity of a person.

What that costs today. Two title folds collide, `百合漫画短編集` and `GirlsLove`, and in each case
one work takes the English and the reading while the other gets neither. 220 credits carry a second
spelling in `credits.json`, the store keeps one, and every alternate sits in `surface` as an author
name resolving to nobody, so a byline written `スズキフミエ` never reaches `c00016`.

**THE ENTITY ALREADY EXISTS AND THIS STORE HAS NEVER READ IT.** The review reasoned from the schema
and concluded there is nothing underneath a credit to merge into, and the first draft of this
section accepted that and asked for a ruling on whether a person is a thing this project holds.
The ruling was made long ago and `data/identity/` is where it lives. DEFINITIONS §4 states it
outright: identity is a human judgement, declared and not inferred.

  `credits.yaml` holds 2,255 credits with 2,473 `credit:` anchors between them, and 220 of them
  carry more than one. The anchors ARE the spellings, so `credit.id` has been an entity all along
  and the loader took one spelling off `credits.json` and made it the key.

  `works.yaml` holds 3,240 works with 5,400 anchors, `madb:` and `web:` addresses rather than
  titles, 1,308 with more than one. The project identifies a work by where it was found. Resolving
  a name to a work by matching `work.title`, which is what the loader does, is a join this project
  does not make anywhere else, and §5c's 55 nameless works and this section's two colliding folds
  are both symptoms of it.

  `credit-rulings.yaml` holds 230 decisions, 220 merges and 7 keeps and 2 withdrawals and one that
  is not a credit at all, each with the surfaces, the shape and the reasoning. `credits.yaml` holds
  7 homophones, which are rulings that two credits sharing a reading are different people.
  `distinct-titles.yaml` is the same instrument for works and is empty, with a header explaining
  that date-span disjointness was tried, flagged 57 pairs and was wrong about every one.

**SO THIS IS A LOADING PROBLEM AND NOT A MODELLING ONE.** Four tables, and none of them invents
anything: the spellings that reach a credit, the addresses that reach a work, an edge from a name
to what it names, and the rulings. `PRIMARY KEY (scheme, address)` on the anchors is the real
identity constraint and it is checkable, which nothing in the store currently is.

**THE MERGE MAP COMES FIRST, AND IT IS ALREADY MEASURED.** 158 addresses reach two works today and
5 spellings reach two credits, and every one is a retired identifier sitting beside its survivor.
`series.json:merged` carries 151 of those and `credits.json:merged` 6. That map is unmodelled, it
is two of the 391 paths §1 still counts, and until the store holds it the anchor constraint would
refuse 163 rows that are correct. It is the same map that was miscounted as 151 separate fields
until the morning of 2026-08-13.

**WHAT IS ACTUALLY LEFT TO DECIDE**, once the loading is done, is narrow. Which spelling a credit
shows when it has several, for which `credit-rulings.yaml` already carries a `keep` field. Whether
a homophone ruling belongs in the same table as a merge, since one says two identifiers are one and
the other says they are two. And whether `credit-rulings.yaml`'s stated `count` of 86 against 230
entries in its own list is a stale field or a different population, which has to be settled before
anything loads it.

**AND THE RULINGS ARE WHAT MAKE §7 SAFE.** `delta.KINDS` names `merge` and `divide`. A store that
can merge two identifiers and holds no record that somebody ruled them apart will merge them again
on the next run, and the 7 homophones are exactly the cases where the evidence says do not.

**DONE 2026-08-13.** `superseded` 157, `work_anchor` 5,190, `credit_spelling` 2,468,
`identity_ruling` 237 with the surfaces each ruled on, and `names` 5,653 edges. None refused.

  WORKS WITH NO NAME AT ALL: 55 BEFORE, 0 AFTER. The loader matched a name to a work on `work.title`
  exactly, and NFKC folds `！` to `!`, so `一畳間まんきつ暮らし！` never matched the title it came
  from. Every population is indexed on the fold the table is keyed on now.

  A FOLD NAMING TWO WORKS IS RECORDED TWICE RATHER THAN ONCE. `names that name more than one thing`
  answers 2, which is `百合漫画短編集` and `GirlsLove`, and each work now carries the English and the
  reading that one of them used to take from the other.

  THE CHAIN HAS TO BE FOLLOWED BEFORE THE ROW IS WRITTEN, which one refusal proved. `w01234` names
  `w01220` as its survivor and `w01220` was retired in its turn, so the map as written puts a
  foreign key against an identifier the corpus no longer holds. `merged` records one hop at a time.

  AND 165 ANCHORS ARE LISTED TWICE, under a retired id and under its survivor, which is what a merge
  means. Resolved, NO address reaches two different live works, which is what makes
  `PRIMARY KEY (scheme, address)` worth adopting: the identity constraint this store has never had.

`data reaching the site around the store` falls 391 to 388, because the merge map is modelled and
was three of the paths it counted.

## 5e. The domains still outside the store

**§1's BUDGET IS 391 AND THESE ARE MOST OF IT.** §6 emits the JSON from the store, and it cannot
emit a field the store has no table for, so this section is what stands between §5 and §6.

A work's STATE, which is on all 3,040 rows: `print`, `oneshot`, `unknown`, `completed`, `active`,
`dormant`, `slow`, with `state_basis` on 948. 271 works carry `state_claims`, and those are
competing source claims about whether a work is running, each with a source, a term, a date and a
url. That is the disagreement rule applied to something other than a name, and `claim` is scoped to
names by its own CHECK, so the model has one answer for one kind of disagreement and none for this.

Admission EVIDENCE, on 2,276 works, 92 of them with more than one. `work.admitted_by` is a single
text column standing where a table belongs, which is the same fault as §5c's placeholder seen from
the other side.

VISIBILITY on 6 works, `rebutted` and `marginal`, which is the register DEFINITIONS §13 describes.
`marketing_label` on 351. The BYLINE as a work prints it: 3,399 credit-line surfaces exist and
nothing connects one to the work it appeared on, and the fix is an edge and not a column, because
one line can appear on many works. The reissue RUN a printing belongs to, which has no identity, so
81 volumes listing two ISBNs under one record cannot say the two are one book twice. And 30 volumes
whose number is a string with no integer in it, `難問編` and `上巻`, carrying neither a number nor a
designation.

**OPENED 2026-08-13, WITH THE STATE AND THE BYLINE MODELLED.** `work_state` 3,040, `state_claim`
271, `work_presentation` 2,461 and `work_byline` 3,018, none refused.

  THE DISAGREEMENT RULE NOW REACHES SOMETHING OTHER THAN A NAME. 271 works hold competing source
  claims about whether they are running, each with a source, the term the page printed and the
  reading we took from it. Keeping both the term and the reading is what lets a later reader
  disagree with the reading rather than with the source.

  THE BYLINE IS AN EDGE, which is where the review's suggestion and this plan part company: it
  counted the byline among what `surface`'s CASE check wrongly forbids, and forbidding it is right,
  because one line appears on many works and a column could only ever hold the first.

  ONE ISBN IS ONE BOOK AND ONE BOOK MAY CARRY SEVERAL, which `volume.isbn UNIQUE` could say only
  half of. 81 volumes list two, a regular printing and a special edition, and the store kept one.
  `volume_isbn` is keyed on the ISBN, so the half that matters is unweakened, and 3,371 are held
  against 3,290 before.

  A NUMBER THAT IS A WORD IS A DESIGNATION. 28 volumes are called `難問編`, `沼編` or `上巻` and
  carried neither a position nor a designation, so the store held nothing about what they are
  called. `build.volume_number` producing no integer is the signal that the string is a name.

**WHAT IS LEFT IS §6's QUEUE AND IT IS 369 PATHS.** The admission evidence went in §5c, and what
remains is mostly the feed's own months, `feed/meta.json`, the interface's thresholds and the
per-source `evidence` and `sourced_from` arrays. None of it is a modelling question of the kind
§5a to §5e were: each is a shape to move, and §6 moves them one domain at a time as it emits.

## 5f. The constraints that still do not fire

**THE SAME BUG AS §5a, FOUR LINES FURTHER DOWN THE SAME FILE.** `claim`'s citation CHECK reads
`basis <> 'stated' OR url IS NOT NULL OR isbn IS NOT NULL OR source_kind = 'derived'`. When
`source_kind` is NULL the last disjunct is NULL, the whole expression is NULL, and a CHECK passes on
NULL. So a `stated` claim that says nothing at all about its evidence is ADMITTED, and the same
claim naming `national-library` is REFUSED. The constraint penalises the provenance it exists to
demand.

221 live rows are in the hole and 219 of them are mine: §5c's division branch never writes a source
kind, so every `stated` division escapes by construction. §5a fixed this exact shape on
`work.first_event` and wrote beside it that every comparable column omits the NULL. `coalesce(
source_kind, '') = 'derived'` is the fix, and the 2 readings left over cite `ndlsearch.ndl.go.jp`
with no address, which is the state the comment says cannot be checked, refreshed or argued with.

**A CIRCLE CAN BE MADE UNSTATEABLE RATHER THAN COUNTED, WHICH IS THE PROJECT OWNER'S OBSERVATION AND
IT IS RIGHT.** `aliases pointing in a circle` was written as a standing question because no CHECK
can walk a graph, and the review then found it catches two-node cycles alone. The better answer is
to forbid a retired row from pointing at another retired row:

    retired  INTEGER GENERATED ALWAYS AS (alias_of IS NOT NULL) STORED,
    wants    INTEGER GENERATED ALWAYS AS (CASE WHEN alias_of IS NULL THEN NULL ELSE 0 END) STORED,
    UNIQUE (id, retired),
    FOREIGN KEY (alias_of, wants) REFERENCES surface (id, retired)

Tested on 2026-08-13: a chain is refused, a two-step circle is refused, retiring a row others point
at is refused, and two aliases onto one canonical row are admitted, which is the real case. A cycle
of ANY length becomes unstateable, because every row in one must be retired while every target must
be current. 18 alias rows today, no chains, so it is free to adopt.

IT FORBIDS CHAINS, WHICH IS STRONGER THAN FORBIDDING CIRCLES, and that is a rule about how a rename
is recorded rather than only about cycles. It is the same discipline §5d had to apply by hand when
`w01234` named a survivor that had itself been retired. `superseded` gets the property for free,
because a retired work id is not a row in `work` at all; `alias_of` is self-referential inside one
table and the generated column is how it says the same thing.

The composite key is used once and applies five times. `names` carries `(surface, kind)` against
`surface(id, kind)` so a title cannot name a person. `work_byline`, `credit_division`, `claim` and
`surface.alias_of` all reference `surface(id)` with the same requirement and none of them has it: a
title as a byline, a title divided into people, and a reading claim on a chapter label were all
accepted. No live row violates any of them, which is when a constraint is free to adopt.

**AND `volume_isbn` KEYED ON THE STRING RATHER THAN THE ISBN.** 940 of 3,371 were hyphenated and 34
books were held under two spellings, so "one ISBN is one book" was defeated by a hyphen.

**THE PROJECT OWNER RULED ON BOTH HALVES OF THIS, 2026-08-13, AND THE SECOND RULING IS THE BETTER
ONE.** First: an ISBN identifies a work by definition, so one reaching two works means something is
broken rather than something to note. Then: the normalised form belongs IN THE SCHEMA, preventing a
duplicate from entering, rather than in an invariant watching from outside. So `volume_isbn.isbn`
takes 13 digits or the older 10 with its X, the loader strips the punctuation on the way in, and a
hyphenated spelling cannot land at all. Nothing external has to be consulted to know one ISBN is one
book.

WHAT IT WAS HIDING was two duplicate works, and they are merged rather than deferred: `w01603` into
`w01245` and `w02055` into `w01463`, each on the evidence that both records credit one artist and
list the same books by ISBN. `data/identity/works.yaml` carries the reasoning. It also hid one
record numbering volume 5 twice, once bare and once hyphenated, which is
`works whose records number one volume twice` seen with the evidence that settles it: same ISBN,
same book, so the loader folds the rows rather than making two.

AND THE MERGE COST TWO BUDGETS, WHICH IS RECORDED RATHER THAN EDITED AWAY. `volume numbers a page
draws twice` rose 5 to 10 and `works holding more volumes than the shop states` 25 to 26, because
each merge brings two catalogues' volume lists onto one row and MADB dates ゆりてつ's first three
volumes to the 24th where BOOK☆WALKER says the 19th. `merge_volumes` keeps rows apart when their
dates disagree, which §1 says is right: which catalogue is correct is not a question a string
comparison answers, and folding them would answer it by discarding one.

**THE SMALLER ONES, AS ONE BATCH.** Every presence constraint is satisfied by the empty string: a
researched claim with `note = ''`, a work with `title = ''`, a ruling with `basis = ''`, all
accepted. `identity_ruling.keeps` is a spelling and 0 of its 220 values resolve to an identifier,
seven lines below `superseded`'s comment boasting of a real foreign key rather than a string nobody
checks. And the footer's own example query no longer runs: §5d moved `surface.work` to the `names`
edge and left the comment naming the column.

## 5g. A row §7 can address, and a quarantine that survives

**`volume` HAS NO KEY AND IT IS THE TABLE AN UPDATE TOUCHES MOST.** `delta.write` addresses a row by
a column-to-value mapping and `volume.id` is a rowid assigned by the iteration order of
`works.json`, with `edition` keyed on top of it. `admission` and `identity_ruling` have no unique
index either. So the three tables §5c and §5d added can be inserted into and never updated, which is
where §5b left `claim` and is the same argument.

2,818 volumes carry no ISBN and 66 of those share a work, a position and a designation with another,
so the answer is a key derived from the SOURCE RECORD and its ordinal rather than a UNIQUE over the
three columns, which would refuse the reissue `volume`'s own comment cites. `count(volume)` is the
schema's stated answer to how many volumes are held and it over-reports by 13 across 9 works, which
is the same absence seen from the other end.

**AND §1a's QUARANTINE HAS NO PRODUCER.** Nothing outside the tests passes `quarantine=True`, so
`rows the store could not admit` reads 0 and will read 0 for ever. That is §13 with the polarity
reversed, a register with a consumer and no producer, and STANDING-INSTRUCTIONS §4 in the same
breath: a check whose pattern never matched anything reports clean.

Worse, `create()` unlinks the file, so a rebuild ERASES the quarantine: 1 row before, 0 after,
measured. The comment argues that being in the store rather than in a file beside it is the point,
and a rebuild deleting it is what that argument has to answer. Either the quarantine survives a
rebuild, and the header calling this database derived and disposable is wrong about one table, or it
does not, and the claim buys nothing. §7 cannot start until this is settled, because the unattended
run is the only thing that writes it.

## 5h. A judgement belongs to the record that was judged

**`surface` IS KEYED ON THE FOLD AND CARRIES FOUR COLUMNS THAT ARE NOT PROPERTIES OF A FOLD.**
`verified`, `uncertain`, `ordinary` and `transliterates` describe the RECORD a person ruled on, and
two spellings folding to one key collide on them. The loader resolves the collision by overwriting,
so 14 `verified: true` rulings are erased.

`今東ともよ` is the case to keep. The store folds `今東　ともよ`, whose reading the National Diet
Library states and which a person verified, onto `今東ともよ`, whose reading is an analyser's and
which nobody verified. Both readings land live, and the surface says verified 0. 84 surfaces carry a
flag beside two or more live readings. Under STANDING-INSTRUCTIONS §6 an unverified reading is
marked to a reader, so once §6 emits from the store this ships as marking a national library reading
as unverified.

THE FOUR DISAGREE WITH EACH OTHER ABOUT HOW TO COLLIDE. `verified` is last-writer-wins and
`uncertain` is a sticky OR, because the loader coerces False to None so it can be set and never
cleared. This is the fault `claim.displaced` was added to fix, solved within a record and left open
across records, and the answer is the same one: the judgement belongs on a row keyed by the raw
spelling, with `surface` keeping the fold and nothing else.

**AND TWO THINGS THE LOADER STILL READS FROM THE WRONG FILE**, which is §5c's fault twice more.
`visibility` is on the SERIES row, 4 rebutted and 2 marginal from `data/rebuttals.yaml`, and §5e read
it from `works.json` where it is NULL on every row. So `work_presentation.visibility` is empty and
its comment calls it the §13 register. And `credit_spelling` is documented as every spelling that
reaches one person while 131 credits' own `credit.surface` is absent from it, so a consumer must
union two tables to ask one question, which the loader does at `by_subject` and nothing else knows.

## 5i. A column that means two things

**WHY THESE COME BEFORE §6 AND THE OTHER TWO DO NOT.** §6 emits from these tables, so a column whose
value does not say what it is gets emitted, and one of the four is keyed on today.

`volume_claim.source` holds a source on 329 rows and a record identifier on 2,244. The loader
falls back to `work_id` where no claim names a source, and `volume_claim_one` keys on the column, so
two records from one catalogue stating one count are two rows rather than the one disagreement this
table exists to hold. "Which sources disagree about this run" cannot be asked at all. The claim
belongs to the RECORD that makes it, which is the key, and `source` says where that record got it.

**`edition.cite` PACKS A SCHEME AND AN IDENTIFIER INTO ONE STRING.** 3,635 are a url,
2,375 are `madb:C418820`, and 906 are the bare word `ndl`, which names a source and locates nothing.
`work_anchor` splits exactly this into a scheme and an address and gets a key out of it, so the file
disagrees with itself about how a citation is held.

A DATE NAMES ITS SOURCE ALWAYS, which every row can satisfy and is what `per-book dates cite their
page` is really asserting. Whether that source also gives a page a reader can open is a second
question, and `dates cited to something that is not a page` counts the 906 rather than refusing rows
the corpus is right to hold.

**TWO COLUMNS SAY ABSENCE WITH A VALUE THAT MEANS SOMETHING ELSE.** `work.explicit_content` is
`NOT NULL DEFAULT 0` and 0 on every row, of which 2,459 are a record stating false and 579 have no
record at all, so looked-and-false and never-looked are one value. `work_presentation.label` holds
the string `none` on 2,127 rows, which makes `label IS NOT NULL` lie about what is known.
STANDING-INSTRUCTIONS §5 is the rule both break: absence is a state and gets its own value.

**DONE 2026-08-13.** `volume_claim` is keyed on the record that makes the claim and `source` says
where that record got it, so two records of one catalogue disagreeing about a run are two rows.
`edition` splits into `source` and `cite`, and the constraint asks the half every row can satisfy:
a date names its source, always. `dates cited to something that is not a page` counts the 906 that
name one and locate nothing. `explicit_content` is nullable, so the 579 works with no record read as
unknown rather than as false, and `label` holds NULL where the publisher applied none.

## 5j. A vocabulary with one home, and a key into it

**NINE COLUMNS HOLD A CLOSED SET AS FREE TEXT**, and the schema is not what blocks them. A CHECK here
would be a second home for each vocabulary, which is the fault every ruling table in this file exists
to prevent and the one `check.STATES_A_READING` demonstrated by drifting from
`curate.READING_ATTRIBUTION` before this store existed. So the section's work is a home in `facts/`
first, and the key follows it.

  `credit_part.role`, 39 values. The gloss table exists and an invariant proves every role has one,
  and it lives in `kari/app.js`, so the home has to move into Python before a key can point at it.

  `release.kind` at 5, `identity_ruling.shape` at 4, `state_claim.says` at 2 and `work_anchor.scheme`
  at 2 are stated in `build.py` and in this loader. `edition.dated_basis` is stated inline in this
  file as a CHECK where `basis` gets a table with columns, and `facts/dating` is NOT its home: that
  module's `BASES` is a different vocabulary, about why a work has no date, overlapping on one word.

One needs no new home and is the first work. `imprint.parent` is an imprint written as a name, 23
of them with one that resolves to nothing, and it should be a foreign key into the table it is
already sitting in. Done: 41 of the 42 lines carrying a parent now resolve to one, and the
forty-second is `集英社ホームコミックス`, which matches no imprint at all and the key refuses to
invent.

**AND ONE IS A NORMALISATION, WHICH THE VOCABULARY WAS HIDING.** `admission.comparator` and `admission.shelf`
are the same fact twice: `facts/inclusion.SHELVES` states
`{cmoa.jp: genre 37 (百合・GL), bookwalker.jp: tag 14 (百合)}`, the 1,867 rows match it exactly, and
the shelf is functionally dependent on the comparator rather than on the row. A `comparator` table
filled from the fact makes the column a foreign key and takes `shelf` off `admission` altogether.

**DONE 2026-08-13, AND THE HOME CAME FIRST IN EVERY CASE.** `facts/serialisation` is a new module
owning the state a work is in, the reading we take from a platform, and the kind of event a release
records; `facts/identity` gained the anchor schemes and the ruling shapes; `facts/dating` gained what
a single volume's date rests on, which its existing `BASES` is not. `build.py` READS the serialisation
constants rather than restating them, which is what makes it a home and not a second copy, and the
store's foreign keys are where the two are made to agree.

  `hiatus` WAS FOUND BY READING THE PRODUCERS RATHER THAN THE ROWS. `build.py` writes it where a run
  has skipped two consecutive slots and no work meets that today, so a vocabulary assembled from the
  corpus would have refused the first work that went on one. A constraint refusing correct data is
  the failure this whole section is against.

  A ROLE PHRASE IS SEVERAL JOBS AND WAS ONE COLUMN. 11 of the 39 strings join atoms the splitter
  knows, `企画・監修`, so `credit_part.role` keeps what the field wrote and `credit_part_role` holds
  1,038 atoms as rows. A multi-valued column is the one shape a relational store may not keep.

  AND THE FACT'S ENTRY POINT IS THE ONLY WAY IN. Reading `facts/credit/splitter.ROLES` from the
  loader was refused by `a fact is reached through its entry point`, correctly, so `facts/credit`
  gained a `roles()` accessor and the invariant is what found it.

## 5k. A date says it is a date

**THIRTEEN COLUMNS OF UNCONSTRAINED TEXT**, across `edition`, `claim`, `work`, `offer`, `release`,
`admission`, `state_claim`, `volume_claim`, `work_presentation` and `quarantine`. `'yesterday
afternoon'` inserts into any of them.

Every value is well formed today, including the partial `YYYY-MM` that `edition.dated` and
`work.first_publication` carry beside whole dates, so the format is free to adopt, which is the only
time a constraint is. It is the cheapest item in the plan and it is a section of its own only
because it touches ten tables.

**DONE 2026-08-13**, and the partial form is admitted alongside the whole one, which is what the
corpus holds. `'yesterday afternoon'` is refused.

## What this plan does not adopt from the review

Recorded because a rejected finding that leaves no trace is indistinguishable from one nobody read.

**`work.volume_count` IS NOT A SECOND COPY OF `count(edition)`.** The review reads it as
denormalisation and would drop it. It is the count a source STATES, and the editions held are what
we have found; `works holding fewer volumes than the shop states` is 70 and `works holding more` is
25, and both budgets exist because the two numbers differ and the difference is the finding. It
should be filled and named for what it is rather than removed.

**`edition.kind = 'serialisation'` HAVING NO ROWS IS NOT A DEFECT.** An enum member nothing has
produced yet refuses nothing and asserts nothing false, which is a different thing from §13's
control that nobody consumes. `claim.predicate = 'romanisation'` is adopted in §5a for the opposite
reason: there the value is declared legal and made unstateable by another constraint, and a schema
contradicting itself is a fault whatever the row count.

**`claim.value` STAYS UNNORMALISED.** The review is right that 84 of the 998 disagreements the
standing question reports are one answer written two ways, `BUNBUN` against `ＢＵＮＢＵＮ`. The
value a source gave is what a claim is FOR, and folding it on the way in would lose the thing being
recorded. The question is what should compare folds, and the fix belongs in the query.

**THE `surface` CASE CHECK IS RIGHT AND STAYS.** The review counts the byline and the imprint among
what the check forbids from reaching a subject. Forbidding it is correct: one credit line appears on
many works and one imprint spelling reaches many houses, so a column could only ever hold the first.
§5e carries the edge that is actually missing.

**AND FROM THE SECOND REVIEW, 2026-08-13.** The same schema was reviewed again once §5a to §5e had
landed, under a prompt identical to the first, so a finding appearing in both is one I failed to fix
and a finding appearing only in the second is either something those sections introduced or
something the first missed. Every figure it reported was re-measured and every one held.

**`credit.kind = 'unknown'` HAVING NO ROWS IS NOT A DEFECT**, on the same reasoning that kept
`edition.kind = 'serialisation'`: an enum member nothing has produced yet refuses nothing and
asserts nothing false. `work_presentation.visibility` looked like a third of these and is not, which
is why it is in §5h instead: the corpus HOLDS 6 of them and the loader reads the wrong file.

**A TABLE DOES NOT OWE A DERIVATION.** The review counts sixteen tables no standing question reads
and calls the platform side unquestioned. A derivation exists to gate a cascade and to answer
something somebody asked; requiring one per table would mean inventing questions to satisfy a rule,
which is how a control nobody consumes gets written in the first place. What §7 actually needs is
that every `reads` declaration covers what an update touches, and that is §7's to establish against
a running updater. Imposing a shape now would settle it in advance of the evidence.

**`state_claim.says` AND `release.kind` STAY FREE TEXT**, for the reason §5a already gave for
`release.kind`: their vocabularies are written in `build.py` and nowhere else, so a CHECK here would
be a second home for them. The fix is a `facts/` module that owns each, and that is pipeline work
under §9's boundary rather than a schema change.

**THE DUPLICATED `kind` COLUMNS STAY, BECAUSE THE DUPLICATE IS THE CONSTRAINT.** `claim.kind`,
`name_record.kind`, `names.kind`, `work_byline.kind` and `credit_division.kind` repeat
`surface.kind` across some 18,000 rows, and `FOREIGN KEY (surface, kind) REFERENCES surface (id,
kind)` is what stops a title naming a person. 0 rows disagree and none can. Removing the redundancy
would remove the thing §5f was written to add.

**`quarantine.row` STAYS A JSON LIST IN A TEXT COLUMN**, which is the carrier this schema's header
says it exists to stop being, and is right in exactly one place. The column holds a row the model
could not admit, so by construction it cannot be modelled, and a typed shape would have to
anticipate every way a future row fails. If it ever fills, what that means is a §9 question about
the model, and not about a column type.

**`work_publisher` KEEPS ITS TRANSITIVE DEPENDENCY.** It carries a publisher and an imprint, and an
imprint determines its publisher, so the first depends on the second. 833 of 2,659 rows name a house
with no line known, so dropping the column would lose them, and 0 of the 1,827 rows carrying both
disagree.

**THE FILING VALUES ARE DEFERRED AND THIS IS THE LEAST COMFORTABLE OF THESE.** `credit.surface`
repeats a row of `credit_spelling`, `identity_ruling.about` repeats a row of
`identity_ruling_surface`, and `keeps` sits beside `keeps_credit`. That is real redundancy held
together by one loader function rather than by the schema, which is weaker than the case above it.
0 rows disagree, and the fix is a partial unique index over a `filed` flag on each set, which is a
restructure of three tables to enforce something nothing has broken. Worth revisiting the moment one
drifts.

**AND THE SHARED PEN NAME IS LEFT UNSTATEABLE ON PURPOSE.** `credit.surface UNIQUE` and
`credit_spelling.spelling` as a primary key both forbid two artists sharing one name, which the
schema header gives as a reason for opaque ids. There are no collisions today and the seven
homophone rulings are a different case. When one arrives the rebuild FAILS rather than losing data,
which is the right failure, and the model changes then with a real row to design against.

## 6. The compiler writes the store; the JSON is emitted from it

**PER DOMAIN, AS EACH LANDS, and never as a cutover.** When a domain is modelled, `build.py` writes
it to the store, the JSON for it is emitted FROM the store, and the direct path is deleted. Then
§1's budget falls by that domain and cannot rise again without something failing.

The site's format is not this plan's question. The emitter may write the same JSON the browser
fetches today, or something narrower, or the site may one day query the store directly. What this
plan fixes is that the data reaches the site THROUGH the store. Everything about presentation stays
free to evolve behind that line, which is the whole reason the line is worth drawing.

**IT CANNOT START ON A DOMAIN NOTHING HAS MODELLED.** An emitter cannot write a field the store has
no table for. A work's state, its admission evidence and its byline were all in that position when
§5e was written and none of them is now. §1's budget standing at 369 is what is left, and it is the
same list because the budget asks what the site is served rather than what the store holds.

**THE MECHANISM, DONE 2026-08-13, AND THE FIRST DOMAIN THROUGH IT.** `relational.build` takes the
compiler's own rows through a `source` argument, so `build.py` hands its structures in and the store
stops being downstream of the files it is meant to replace. `adapters/relational/emit.py` reads a
file back out of the tables. `credits.json` is the first domain: `credit_page_data` is deleted and
the file is what the store says.

**BYTE EQUALITY IS THE PROOF AND IT IS ONLY AVAILABLE WHILE BOTH EXIST**, which is the whole reason
this plan refuses a cutover. `test_emit.py` compares the emitted text against what the compiler
wrote, and the first comparison found two faults the store had taken on in §5h. 130 credits had
their RAW title filed as a spelling where the registry answers for the FOLD of it, so `二三　夏一`
shipped beside `二三夏一`; and `アンソロジー`, whose spelling was withdrawn and whose folded title
the registry still answers for, was being dropped. Neither is visible from either side alone.

**A DOMAIN CANNOT BE ITS OWN INPUT, AND CI FOUND THAT WITHIN THE HOUR.** The store's `credit` and
`work_credit` tables were loaded from `credits.json`, which is the file this domain now emits, so on
a clean checkout the store built empty and emitted empty. The local tree still had yesterday's file
to read, which is exactly the shape of blindness §14b is about. Both tables come from
`data/identity/` now, where `credit_spelling`, `superseded` and `identity_ruling` have been read
from since §5d, and deleting `data/build/credits.json` and rebuilding produces the file in full.

**AND THE MOVE FILLED A COLUMN §5b HAD GIVEN UP ON.** `work_credit.role` was 4,165 NULLs and §5b
concluded the roles were not on that route, on the strength of one letter: `credits.json` writes
`roles`, plural, and the loader asked for `role`. 568 edges state one, an edge naming two jobs is
two rows, and that is what `(work, credit, coalesce(role, ''))` was keyed for all along.

**WHAT EACH REMAINING DOMAIN NEEDS**, which is the queue and is 357 paths.

  `publishers.json` MOVED 2026-08-13 and the print half of `series.json` is answered from the same
  tables. `print_row` holds all 2,512 rows: a work, a house, the imprint spelling as
  catalogued, the label, the span, the volume count, and every catalogue record folded into the row.
  The 10 print paths on a series row are answered from it.

  AND `print_party` HOLDS THE JUDGEMENT'S ANSWER, which is what let the file move.
  `publisher_identity.anchor` decides which house a catalogued spelling names and
  `facts/imprint.resolve` which line, both at load time, so the emitter counts rows and spans years
  and decides nothing. An emitter resolving a spelling for itself would be the second
  implementation §3 refuses, and it would be the one that disagrees.

  WHAT BYTE EQUALITY CAUGHT THAT NOTHING ELSE WOULD HAVE. The parties were built from an
  unordered `SELECT id, record`, which SQLite served from the unique index on `record` rather than
  from the table, so every works list came out in a sequence with nothing to do with the compiler's:
  an unordered SELECT is not insertion order the moment a covering index exists. A line's years were
  measured from the BLOCK's dates where `facts/printblock.parties` says each folded record states
  its own. And §5j's foreign key on `imprint.parent` had dropped the one parent that resolves to no
  line, which a publisher page shows, so the registry's stated name is kept beside the key.

  IT ALSO CORRECTED `work_publisher`. §2 read that edge off `publishers.json`'s `works` list, which
  counts a house named in ANY seat, so 193 distributor edges sat there as though the house had
  published the book. It comes from `print_party` now and the seat comes with it, because dropping
  those edges would have lost a fact to make a column tidier.

  `feed/current.json` AND THE ARCHIVED MONTHS MOVED 2026-08-13, both from one emitter: a row is the
  same row wherever it is filed and what differs is the date filter over it, which stays in the
  build because it is a fact about the file's structure. All 373 rows of the window and all 601 of
  July, every field, parsed.

  WHAT IT TOOK WAS THE ROW'S OWN REASONING, which is most of a release: on what basis we hold the
  date, how confident that is, what kind of instalment it is and what made us say so. A release is a
  claim that something happened, and a reader is owed the reasoning with the claim.

  AND THE THREE ANSWERS `absence` HIDES, which the file spells apart and a column would not. 11 rows
  state an EMPTY set of access modes, meaning the capture looked and the chapter offers none; 19
  state a channel of `null`, meaning the platform has channels and this row is in none; and a row
  that was never asked states neither. `access_stated` and `channel_stated` are the difference.

  `series.json` MOVED 2026-08-13, ON PARSED EQUALITY: all 3,038 rows, every field, including the
  keys that are always there and sometimes null, which is a distinction the two row paths make and
  an emitter can get wrong in both directions. A work with a serialisation is ASKED whether its
  ending has a reason in Japanese and answers no; a print-only row is never asked.

  IT CHANGED ONE THING AND THAT IS A CORRECTION. The merge map named `w01220` as what `w01234`
  became, and `w01220` was itself retired, so a reader following that forwarder landed on an
  identifier the corpus no longer holds. `superseded` resolves the chain before it stores it, which
  is what §5d had to do by hand before a foreign key would accept the row.

  THE ROW'S RENDERINGS COST TWO MODULES AND BOTH WERE ONE FACT WITH TWO PRODUCERS WAITING TO HAPPEN.
  `names/attach` is the join: a row's `work_en` is not a lookup, since two candidate records are
  weighed, an edition takes the plain title's English, and a byline naming several people is
  composed from them. `names/ruby` is the furigana, which is a function of the reading AND of the
  spelling it sits over, so `仲谷 鳰` parts the name where `仲谷鳰` reads it as one word. Both are
  asked by `build.py` and by the emitter now.

  AND A RENDERING BELONGS TO A RECORD, not to the fold. `ruby` and `romanisation` were keyed by
  surface, so 78 rows showed the winning record's spans and spellings over a different record's
  name: 春結千晶 is held twice, once with an analyser's ハル ケツ チアキ and once with ハルユウチアキ
  off the shop that sells the artist's books, and the row showing the second spelled the first.

  `series.json`'s WEB HALF WAS MODELLED FIRST, which leaves the print half it already had.
  `serialisation` is one row per work over the offers below it: the counts and the address a row
  SHOWS are the chosen offer's and are read through `offer`, and what is here is what the compiler
  decided, which platform speaks for the work and how long the run demonstrably is. All 3,038 rows,
  1,390 of them naming an offer, with 71 skipped slots and 151 announcements of what comes next.

  `evidence` HOLDS ALL 2,366 ROWS AND `provenance` ALL 7,476, and they are two tables because a
  volume count says nothing about whether a work is yuri: running them together would make a
  classification look better supported by padding it with rows that answer a different question. How
  much a piece of evidence is worth belongs to its KIND, so the rank, the party type and the clause
  each was read out of are `credence_kind` and not 2,366 copies.

  `feed/meta.json` MOVED 2026-08-13 AND CLOSED THE SECTION. The scoping question it carried is
  answered by the shape rather than by an argument: what the emitter is HANDED is the run's report
  on ITSELF, how wide the window is, which months are archived and how many promotional samples were
  set aside, which is the same reasoning that keeps `run.json` and `checks.json` out of this
  measure. Everything the census LEARNED is in the store: the platforms, how far each listing has
  fallen behind, and the two queues of what has been noticed and not confirmed.

  A CENSUS KEEPS ITS OWN ORDER, which two platforms sharing a rank make underivable from the numbers
  in it, so `census_seq` and `meta_seq` are columns. A table this store fills from several
  directions has no insertion order to fall back on.

  `feed/names.json` IS THE KEYSTONE AND WAS NOT ON THE QUEUE, which measuring the rest found. It
  carries 2 unanswered paths of the 278, so the budget calls it modelled and says nothing about the
  order the files can move in: `series.json` and both feed files carry a RENDERING per row,
  `work_en` and `author_en`, and each of those is an entry from this map. Nothing else can move
  until it does, and `feed/meta.json` is the one file that carries no name at all.

  THE SEAM IT NEEDED IS BUILT, 2026-08-13, and it corrected a fault of the kind §6 keeps finding.
  The store loaded the renderings by READING `feed/names.json` off the disk, which on any run is the
  LAST run's and on a fresh checkout is nothing. It could not simply be handed the compiler's rows
  like `series` and `works`, because the map is downstream of two files the store emits: `floor` is
  every string the interface will render and it is assembled by walking the credit pages and the
  publisher pages. So `relational.renderings` is a load of its own. The compiler builds the store,
  emits those two files, assembles the map, and hands it back.

  AND A CLAIM NOW SAYS WHICH RECORD MADE IT. Claims hung off the FOLD alone, so the 112 author
  spellings that fold onto another's key put their answers in one heap. An entry is one record's
  account of a name, its reading, its English, its marks and its citation together, and one
  assembled from whichever record held each field would ship a name nobody ever wrote down.
  `names/fold` holds the rule that picks the record, so the compiler and the emitter ask one function
  rather than ranking the records twice.

  STORING THAT ANSWER WAS TRIED AND IS WRONG, which is worth the sentence. `name_record.renders` was
  a column saying which record the shipped entry is rendered from, filled by asking `fold_map` at
  load time, and it disagreed with the file on a handful of folds: the rule ranks the RENDERED
  entries and the loader has only the records, so a record whose rendering is withheld, or whose
  ruby its reading contradicts, scores for fields no reader ever sees. One function, asked about two
  different things, is two answers. The emitter renders first and folds after, which is the order
  `build.py` has always used.

  WHERE THE EMITTER STANDS, measured against the shipped file rather than described. `_entry` builds
  one record's rendering out of `claim`, `name_record`, `ruby` and `romanisation`, and the author
  map comes back with the right 2,575 keys and 9 rows differing. Every one of those is the same
  fault: two records folding onto one surface state the same claim, the loader deduped it as one
  row because the claim identity is `(surface, predicate, value, basis, source)`, and the row now
  belongs to whichever record was read first. 邪武丸 is the winner of its fold and its reading sits
  on the other record, so the entry came out with no reading at all. A claim is made BY a record and
  a duplicate is two records making one claim, so `claim_record` is an edge and the column is gone.

  THE AUTHOR MAP IS NOW 2,575 KEYS WITH 6 FIELDS DIFFERING, and the titles 7. Five of the six are a
  `reading_cite` whose `reviewed` date is a day earlier than the file's, which is the same dedupe
  seen from the other side: two records state one reading on different days, the claim identity does
  not include the date, and the surviving row keeps the first record's. That is a question about what
  identifies a claim rather than a fault in the emitter, and it is worth asking before it is fixed.

  AND THE TITLE MAP OWES TWO MORE THINGS. 13 keys it emits are titles of WITHHELD works, which the
  build filters against a register the store does not hold; 18 it does not emit are the catalogued
  spellings `build.py` keys onto the record of the work they name, which is `surface.alias_of` and
  is in the store already. Neither is a modelling gap in what a name IS.

  AND `basis` IS A PROPERTY OF THE RECORD RATHER THAN OF ITS ENGLISH NAME, which the store had wrong.
  2,571 of the 2,575 author records state one and 689 hold an English name, so on most of them the
  field says only that the Latin a reader gets is our romanisation; filed as part of the english
  CLAIM it existed on the 689 and vanished on the rest. It is a column on `name_record` now, and
  fixing it took the two maps from 24 differing fields to 13.

  `floor`, `phrases` AND `credit_parts` COME OUT EXACT, at 9,743, 7,479 and 3,399 keys. Two things
  the round trip found: a romanisation is ONE string where the three styles agree, which is what the
  file holds and is not a shortcut, since a name with no long vowel and no doubled consonant is
  spelled one way whichever style a reader chose; and a byline can say `and others`, which
  `[他著]雪子` does, and the loader was dropping the parts with no name.

  THE TITLE AND AUTHOR MAPS COME BACK WITH THE FILE'S OWN KEYS, 3,301 and 2,575, with 3 and 6
  entries differing. The last thing between them and the file was the register of works this
  database does not publish: a withheld work has no row in the store, which is why the ruling is a
  table of its own, and without it the emitter puts the title and its English rendering on the
  public site with only the work's rows removed.

  EVERY SECTION NOW COMES BACK WITH THE FILE'S OWN KEYS, and 11 entries of about 27,000 differ.
  `imprints` reads the resolution off the print parties, where `facts/imprint.resolve` made it at
  load time, so the emitter matches no spelling itself. `publishers` needed the imprints first: a
  LINE'S OWN NAME is a name, and `MFC キューンシリーズ` was once in the map under a key nothing asks
  for, so 35 rows showed the line in Japanese in English-only mode.

  AND A SEAT IS NOT A SEAT'S NAME. The census was being handed every print party as though it were a
  publisher, so seven houses that only ever DISTRIBUTE were counted as publishing.

  IT MOVED 2026-08-13, ON PARSED EQUALITY, and the two faults that stood in the way were both about
  what identifies a thing. THE DOCUMENT IS PART OF A CLAIM: two name records state one reading and
  are not always reading the same page on the same day, so keyed without the citation they were one
  row, the row kept whichever record was read first, and the entry the site shows cited a page that
  record never named. 23 rows the store had been collapsing are two claims apiece.

  AND AN ANCHOR IS NOT A SPELLING. A credit answers for the fold of its own title as well as for its
  anchors, and only an anchor is a page a reader can be sent to. `アンソロジー` is a credit whose
  spelling was withdrawn and whose folded title the registry still answers for, so the map offered a
  link to an address nothing mints. `credit_spelling.anchor` is the difference.

  PARSED AND NOT BYTES, because a fact object in this file is SHARED between the two keys that reach
  it, the catalogued spelling and the shown one, so what is written is one object under two keys and
  the order inside it follows whichever slot was filled first.

  `index.json` MOVED 2026-08-13, along with `feed/credit-keys.json`, which is `credit_spelling`
  written down. The index took four corrections that byte equality found and nothing else would
  have: `ci` follows the byline's order rather than the registry's, the marketing label varies
  between the records of one work, a record stating no date ships `null` where one with no
  first-publication block ships `""`, and the creator field has TWO divisions in this project.

  `works.json` MOVED 2026-08-13, ON PARSED EQUALITY AND NOT ON BYTES, which is a weaker standard and
  is stated rather than assumed. The file has 11 distinct key orders on its records and 38 on its
  volumes, each an artefact of the order the compiler merged its sources rather than a fact about a
  book, so asserting them would assert the merge order. Every key's PRESENCE and every value is
  asserted instead, which is the whole of what a reader is served.

  IT CORRECTED FOUR THINGS EARLIER SECTIONS HAD PUT IN THE STORE. §5f folded two volume rows onto
  one where a record lists the same book twice, which is the right reading of an ISBN and the wrong
  reading of a RECORD, so the store held 6,104 rows where the corpus states 6,105; both rows are
  kept now and the ISBN is attached once. §5c filled `volume_claim` from `volume_count`, so 2,574
  rows said what 330 of them meant. §5c keyed `admission` on the work, putting one record's grounds
  on another's row. And §5e synthesised a designation from a number, which `number_raw` made
  unnecessary and which was putting something into a field the record states.

  AND ITS ISBNs ARE NORMALISED NOW, which is the project owner's ruling reaching the file. Every
  difference from what the compiler wrote is provably the same ISBN respelled, 926 of them, or an
  `editions` list that held one ISBN written twice, 26 more. No ISBN changes identity, which is what
  made shipping the change safe to decide.

**WHAT MUST NOT HAPPEN.** A domain half-migrated, where the store holds it and the JSON is still
written directly. That is two producers of one fact, which is the fault this project names most
often. The budget in §1 does not catch it, which is why the direct path is deleted in the same
change that adds the emission.

**THE SECTION IS DONE, 2026-08-13, AND THE BUDGET IS 0.** Every one of the ten corpus files the site
fetches is written out of the tables, and `data reaching the site around the store` fell 707 to 0
over the section. The number is what makes the claim checkable: it counts the paths a READER is
served rather than the tables the store holds, so it cannot be satisfied by modelling something and
leaving the file to be written beside it.

AND THE LAST ONE WAS FOUND BY A DEPLOY, which is worth its own line. `data/build/series.json` was
still where the store read the WORK merge map from, and §6 had just made that file something the
store writes: a clean checkout built an empty map, emitted an empty map, and `pages.forwarders`
deleted the stub at all 153 retired work addresses. Fourth time this project has been bitten by a
domain being its own input, and the first time nothing upstream of the site caught it. The registry
states the merge, exactly as the credit half has since §5d, and `test_emit.py` now asserts that a
retired work address still resolves.

The move itself is the argument for having done it this way. Ten faults that
neither side could see alone: a credit registry that emptied on a clean checkout, an unordered
SELECT served from an index, 130 credits filed under a spelling the registry does not answer for,
two volume rows folded into one, a claim heap shared between the records that made it, furigana over
the wrong spelling of a name, a byline that said `and others` and lost it, a forwarder pointing at a
retired identifier, seven houses that only ever distribute counted as publishing, and 153 work
forwarders about to be deleted from the live site. Byte or parsed
equality against what the compiler wrote is what caught every one, and it is available only while
both producers exist, which is the whole reason this section refused a cutover.

## 7. Incremental on every update, reconciled weekly

**THE HARD PART IS ALREADY ARGUED.** `delta.py`'s design is one sentence: the cascade is gated on
OUTPUT change and never on input change, so a write producing the value already there cascades
nothing. Its correctness is by construction, since a pure derivation plus an idempotent write means
the fixed point a delta converges to is the fixed point a rebuild produces.

Nothing outside its own tests has ever applied a delta, so it has no production caller. This
section is not about writing the updater; it is about an update run applying what it captured
through `delta.write` rather than recompiling, and about the failure modes that only appear when
real captures drive it.

**AND IT CANNOT BEGIN UNTIL §5b.** `delta.write` addresses a row by a key and `claim` has none, so
the table holding most of the corpus can be inserted into and never updated or retracted. §5a is
the other precondition and is easy to miss for the same reason it went unnoticed for a month: the
incremental path opens the database with a bare connect, foreign keys are off on that connection,
and an updater writing a dangling reference would be told nothing.

Reconciliation is the point and it already exists. `equivalence.yml` rebuilds from source and
sets the result beside a store that has only ever been updated, because every focused test of the
updater is written against the same `reads` declarations the updater uses, so a wrong declaration
satisfies both. That is §14b and it survives this plan unchanged: a full rebuild from
`data/source` is still independent of the incremental path, so the second opinion does not go away
when the JSON does.

**WHAT GETS HARDER.** Today reconciliation compares two stores. When the store is the only compiled
form, a divergence has no JSON to arbitrate between them, so the report has to be good enough to
act on by itself. It already refuses to overwrite the incremental store with the rebuilt one, and
that decision becomes more important rather than less.

**DONE 2026-08-14, AND THE FAILURE MODES ARRIVED EXACTLY WHERE THIS SECTION SAID THEY WOULD.**
`relational.apply` reconciles the store against the rows the run compiled, and `build.py` calls it
instead of replacing the file. A second consecutive build now writes NOTHING: 262,495 rows
unchanged, nothing dropped, no derivation moved. That is the idempotence the design has always
claimed, demonstrated against the corpus rather than against a fixture.

**A SURROGATE ID IS NOT A FACT, WHICH COST FOUR ATTEMPTS TO STATE PROPERLY.** `surface.id` is handed
out by the insert that made the row, so the same name is 23581 in one compile and 23585 in the next.
Keyed on it, every row looked new; dropped from the comparison, an EDGE compared equal to an edge
pointing somewhere else. What works is translating a number into what it MEANS, following the chain
as far as it goes: `credit_part_role.surface` addresses `credit_part`, which addresses
`credit_division`, which is a surface, and only the last of the four is a rowid. Keys are checked at
COMMIT rather than per statement, because no ordering of forty tables is right in both directions at
once.

**AND A STALE DIGEST NEVER HEALS, which the weekly reconciliation found on its first real run.**
Convergence recomputes what a write TOUCHED, so an answer recorded before a change that has since
stopped moving its tables stays wrong for ever: `names nothing in the corpus is identified by` was
recorded at 593 where the store said 637. Re-asking all fifteen base questions costs 0.02 s, which
is less than the argument for not doing it, and `converge` still gates the cascade, which is where
the cost would be if there were one. An updated store and one rebuilt from nothing now agree on
every derivation and every table.

## What this plan does not decide

**Whether the site reads SQLite.** Out of scope by the owner's framing and genuinely separable once
§6 holds.

**Whether `data/build` disappears.** It may survive as an emitted artefact for as long as anything
finds it useful, including the checks. What matters is that nothing produces it except the store.

## 8. Turn the schedule on

**WHAT RUNS TODAY.** `equivalence.yml` is scheduled, `cron: "17 4 * * 1"`, Monday and away from
everything else. `gate.yml` and `leak-guard.yml` run on push and on pull request. `update.yml` has
its `schedule:` block **commented out**, with three crons written and disabled:

    # - cron: "37 15 * * *"   00:37 JST, after the midnight batch. The most valuable single run.
    # - cron: "07 3 * * *"    12:07 JST, catching the 11:00 and 12:00 clusters together.
    # - cron: "17 10 * * *"   19:17 JST, the small evening tail plus a retry margin.

The times are already reasoned: measured from 10,216 dated feed entries, 98% of releases land in
three hours JST, and each cron sits 30 minutes behind a cluster and off the hour because everything
at :00 queues behind the rest of GitHub. None of that needs revisiting.

**THE CONDITIONS ARE DECIDED AND THREE OF THEM ARE MET.** `TODO-github-setup.md` §C lists what must
hold before the schedule goes on, and this plan does not get to relax them.

| condition | state |
|---|---|
| per-host parallelism in Stage A | met: `run_stage.py` drives `stage-a.yaml` concurrently |
| a clean run with the browser stage | not confirmed |
| `SITE_DEPLOY_KEY` set, so publishing works | not confirmed; the step warns and exits 0 without it |
| a re-measured cost | not done since the concurrency change |

**THE COST WAS THE ONE THAT DECIDED IT, AND §11 REMOVES IT.** The reasoning below held while this
repository was private, where Actions bills against 2,000 free minutes a month and GitHub rounds
every run up to a whole minute. A public repository is not billed for standard runners, so the
condition that decided whether the schedule is three crons or one dissolves on the day §11 publishes
the repository. The measurement is still worth having, for knowing what the pipeline costs in time;
it stops being what gates the decision. The rest of §C's conditions are untouched, including
`SITE_DEPLOY_KEY`, which is still how anything reaches the site.

The argument as it stood: `yurison` is private, so Actions bills against 2,000 free
minutes a month, GitHub rounds every run up to a whole minute, and run COUNT matters as much as run
length. Stage A took 2,285s when it ran serially, which was roughly 1,800 minutes a month before the
browser stage. Concurrency should have changed that substantially and nobody has measured it. Three
crons a day is 90 runs a month before anything else, so the measurement decides whether it is three
crons, one, or the most valuable one alone.

This section sits late rather than first for one reason. A nightly job that half-succeeds trains you to
ignore its failures, which `TODO-github-setup.md` says in those words. Under this plan the store is
the compiled form, so an unattended failure is a day with no compile at all rather than a day with
stale JSON. §1a's quarantine is what makes an unattended run survivable, and §7's reconciliation is
what proves the incremental path has not drifted. Turning the schedule on before both hold would be
automating something that cannot yet fail safely.

**WHAT TO CHANGE, when the conditions hold.** Uncomment the block, keeping whichever crons the
re-measured cost supports. `equivalence.yml` needs nothing: it is already scheduled and already
runs the cache-free cycle, which is the reconciliation this plan depends on.

## 9. The maintenance pass, and what it works from

**WHAT THIS SECTION IS.** The unattended run populates what it can and sets aside what it cannot.
This is the process that deals with the residue afterwards. It says what the pass reads, what it
does with each class of thing, and what it may not touch. It deliberately says nothing about when
it runs.

**THE PASS IS EXPECTED TO RUN UNATTENDED TOO, which is what bounds its authority.** It changes DATA
and RULINGS: a curated name, an identity join, a scope refusal, a decision recorded in a queue file.
It does not change the code that collects, ingests or compiles. An unattended pass editing an
adapter would be altering what the next capture MEANS, unreviewed, on the strength of one row it
could not admit. That is the one thing a maintenance run must not be able to do.

It reads these in order, because each earlier one can create work for the later ones.

  §1a's quarantine, which holds rows the compiler could not admit. Newest first.

  The budgets that moved since the last pass, from `docs/budgets.json` and the gate's report.

  `data/queue`, 35 files today, each a decision somebody has to make: `identity-review.yaml`,
  `macron-boundaries.yaml`, `shop-query-title-only.yaml`, `bw-review.yaml` and the rest.

  `docs/GAPS.md`, for the classes nobody has closed.

**A QUARANTINED ROW HAS EXACTLY FOUR OUTCOMES, and naming them is the point of writing this down.**

  ADMIT IT. The data is right and the corpus was missing something it needed, usually a work the
  capture reached before anything admitted it. Add what is missing and the row inserts.

  JOIN IT. The data describes something already held under another identifier, which is what most
  of `updates naming a work we do not hold` turns out to be. `identity --attach` where the address
  is unclaimed, `--merge` where it already carries an id of its own, and the registry refuses the
  wrong one of those, which is how the operation is chosen rather than guessed.

  RULE ON IT, WHERE THE RULING IS DATA. Out of scope is `data/scope.yaml`, a doubtful designation is
  a rebuttal, a name is `curated.yaml`. Each carries its reasoning where the next pass finds it
  rather than in a commit message.

  DEFER IT, WHERE THE ANSWER IS A CHANGE TO THE PIPELINE. A requirement nobody wrote down, a source
  that changed shape, a bug in an adapter, a model asserting something the data does not support.
  This is a legitimate finding and the commonest one worth having, and it is not the maintenance
  pass's to act on. Document it and stop.

Every quarantined row leaves by one of those four doors. An empty quarantine emptied by deletion
looks exactly like one emptied by work, which is the whole reason to write the doors down.

**AN EARLIER DRAFT OF THIS SECTION GOT THE THIRD DOOR WRONG, and the mistake is worth keeping.** It
said the answer to a wrong model was "a schema change or a ruling in `facts/`", which is code, so a
pass forbidden to touch the pipeline was being told to change it. Splitting the door in two is what
the boundary above actually requires: a ruling that is data the pass makes, and a ruling that is
code it defers.

**WHAT A DEFERRAL HAS TO CONTAIN to be worth more than a note saying something is wrong.** The
quarantined row itself and the constraint that refused it, the capture or adapter it came from, how
many rows share the shape, and what the pass believes is happening. Enough that a later session,
directed at it, can reproduce the case without rediscovering it.

It goes to `docs/GAPS.md` for a class, which is what that file is for and what it already
holds for six findings from 2026-08-13. A queue file where the deferral is a list of rows rather
than an argument. Neither is the build, so writing to them stays inside the boundary.

A deferral leaves the row in quarantine, so §1a's budget keeps
counting it, which is correct: nothing has been resolved. What that means in practice is that a
pipeline fault shows up as a number that stops falling, and a pass that deferred everything looks
exactly like a pass that did nothing. So the deferral is recorded where a person reads it, and the
budget is what makes the silence visible.

**BUDGETS THAT MOVED.** A rise is accepted with a recorded reason and never edited away, and the
reason has to be established rather than assumed. The method that works is to put the new inputs
aside and rebuild: if the number returns to what it was, the rise is the new rows and not a defect.
A rise nobody can explain is a fault until somebody explains it.

**THE NAMING WORK, which is the largest recurring item.** New works arrive with no English, and
Stage E's passes reach only what a machine can settle: a title already in Latin, a reading the kana
state outright, an analyser's guess marked as one. What is left needs a person, and the precedence
is the project's own: an official English title the work carries outranks a licensor's, which
outranks a translation of ours, which outranks a romanisation. A romanisation is the finished
answer for a coinage and a poor one for a phrase.

The entries go in `data/names/curated.yaml`, which is the source, with the argument in the note,
and reach the store through `curate.py --apply`. `works without English` is 0 and can only rise;
`works showing a romanisation` never reaches zero and falls by deciding titles one at a time.

**THE OTHER RECURRING ITEMS.** Readings nobody has settled, interpunct credits nobody has ruled on,
macron boundaries, shop leads that reached no bibliography record, and translated editions whose
base work the corpus does not hold. Each has a queue file, and the discipline is the same: decide
it, record why, and let the number fall because the work was done.

**HOW A PASS ENDS.** Rebuild, gate, tests, deploy, push both repositories in that order, and read
what the site actually serves. Where `kari/app.js` has changed, the site repository goes
first, because `gate.yml` clones the site at its default branch and would otherwise test today's
Python against yesterday's JavaScript.

## 10. An invariant is a query on the store

**WHY THIS COMES BEFORE THE SPLIT.** §6's proof was byte or parsed equality against what the
compiler wrote, and it is available only while both producers exist. §11 moves the emitters out of
this repository, and on that day the comparison becomes the store against itself. What replaces it
has to exist first, and the honest replacement is that the store answers for itself: a constraint
the data cannot violate, or a query whose answer is checkable by anyone holding the file.

It is also what §7 needs. A check written in Python over `data/build/*.json` can only ever
describe a full rebuild. A query holds equally over a store that was rebuilt and one that was
updated in place, which is the whole difficulty of an incremental path: the reconciliation compares
two stores, and until the invariants are statements about a store there is nothing to compare them
with.

**THREE TIERS, AND THE FIRST ONE DELETES THE CHECK.**

  A CONSTRAINT, so the violation is unstateable. §5 did this for the alias cycle, for ISBN
  spelling and for the vocabularies, and each time the check that had been counting violations
  stopped existing rather than moving. Anything that is really a uniqueness, a foreign key or a
  domain belongs here.

  A QUERY WITH A NAME, a `SELECT`, and the number it should return. This is most of the middle
  ground, and it is where a budget belongs: a budget is a count already, so `docs/budgets.json`
  becomes a name, a query, a number and the reason, which finally puts the definition beside the
  figure it produces.

  PYTHON, because the subject is prose, the source tree, or two runs compared. `tics.py`,
  `modules without a test` and `adapters fetching without net.py` are about this repository rather
  than about the corpus, and the weekly equivalence run compares two stores and cannot be one query.

The shape of the move is measured rather than guessed. `check.py` holds 145 invariant and budget
functions. 43 of them read the built collections directly and are the obvious candidates; 26 name
the site and leave under §11; my estimate is that 60 to 70 end as constraints or queries and that
about 50 are properly Python. The number that matters is not how many move but that the ones that
stay are the ones with a stated reason to stay.

**THE CANARY SURVIVES AND GETS CHEAPER.** `--self-test` plants a violation and fails if the check
does not catch it, which is what stops a check that matches nothing from reporting clean. In SQL
that is a violating row inserted into a throwaway copy, which is simpler than the context patching
it takes today. Two things must not be lost in the translation: a query that ERRORS must read as
unmeasured rather than as zero, which is the trap `UNMEASURED` already exists for, and a budget
still ratchets down only.

**WHAT THIS IS NOT.** It is not a rewrite of the gate. The checks that stay in Python stay exactly
as they are, and a check moves only when somebody can say in a sentence what the query means.

**DONE 2026-08-14. `relational/asks.py` HOLDS THEM**, each with a name, a query, the tables it reads,
what it asserts and SQL that plants a violation. Eight invariants and six budgets answer from the
store, and the ten Python functions they replace are gone. Every migrated budget reproduces the
number its Python gave, which is the standard for calling it the same check: 37 incomplete attested
rows, 2,436 volumes with no printing date, 0 for the rest.

**THREE COULD NOT FIRE AND THE CANARIES ARE WHAT SAID SO.** A release id naming one release is
unstateable once the id is a primary key, so that check is gone rather than moved. A print run's
dates being ordered was planted with an UPDATE against a predicate no row satisfies, because `last`
is empty on all 2,512 print rows. A refutation of a print serial was planted the same way, and 1,407
of the 1,648 print works have no presentation row to update. Each is §4 caught one level down: a
canary that matches nothing runs perfectly and proves nothing.

**AND ONE NEW BUDGET CAME OUT OF THE MOVE**, which is the argument for writing the questions down.
A record's stored furigana should spell the record's own name and eleven sets do not: nine drop a
bracketed reading, so `恋する小惑星 (アステロイド)` gets spans covering the first six characters and
nothing over the gloss, and two are a name stored with a COMBINING dakuten where the aligner emits
the composed character, so `お嬢さま` and `お嬢さま` differ by a code point nobody can see.

**WHAT IS LEFT, MEASURED.** 32 of the remaining checks read the built collections and are the queue;
the site took 16 with it under §11; the rest are about this repository rather than the corpus, which
is prose, the source tree, and two runs compared, and they stay in Python where they can be.

## 11. The store is the artefact; the site builds from it

**THE BOUNDARY BECOMES A FILE WITH A VERSION ON IT.** Today it is a shell script that reaches into
a sibling checkout, writes HTML into it, and rewrites its `index.html` to bust a cache. What crosses
after this is `corpus.sqlite`: 30.7 MB, 42 tables, 17.5 seconds to build, stamped with a schema
version and the commit that produced it. The site pulls that and builds what it needs.

**THE VERSION IS A DETECTOR AND NOT A PROMISE**, ruled by the project owner: no guarantee of format
or schema is offered to anyone. So the stamp exists for the consumer to REFUSE on. A site build that
meets a store it does not recognise stops rather than reading a column that has moved, and the
schema stays as free to change as every other compiled thing in this repository.

The site goes on being served JSON, ruled by the project owner. The emitters move unchanged and
produce the same ten files on the other side of the line. Whether the site later queries the store
directly is a question about the site, which is exactly the freedom this boundary is for.

**WHAT LEAVES THIS REPOSITORY.** `adapters/relational/emit.py`, `adapters/stubs.py` and
`adapters/pages.py`, which are 1,754 lines of rendering; `deploy.sh` entire; and the 26 checks that
read `kari/app.js`, `app-status.js`, `index.html` and the deployed data tree. What is left has no
path that names the other repository, and `SITE_ROOT` and `YURARIUM_SITE` stop existing here.

**THE STORE CARRIES THE WITHHELD WORKS, ruled by the project owner.** The store is the archive and
the emission is the publication, which is a cleaner division than filtering both. What that means
concretely: 13 works refused under DEFINITIONS §6, 11 of them prose from one publisher's comics
label and 2 first published outside Japan, have no `work` row, and all 13 keep a title surface
carrying 26 claims between them. The `withheld` table holds each title with the reasoning that
refused it.

**SO THE WITHHOLDING MUST BECOME STRUCTURAL, which it is not today.** It is applied at emission, by
a filter in one function, and §11 moves that function into the repository that consumes the store.
A rule enforced by the consumer is a rule the producer cannot check. The answer is a VIEW: the
schema offers `published_work` and the emitters read views rather than tables, so shipping a
withheld work takes a deliberate act rather than an omission. Deciding that now costs nothing,
because nothing is withheld on content grounds today; the day something is, the store will carry
the flag, the reason and the renderings while the site shows nothing.

**HOW IT TRAVELS, AND WHY THAT STOPPED BEING A PROBLEM.** The store may be public and so may this
repository, both ruled by the project owner. That dissolves the only hard question the transfer had.
A private producer feeding a public consumer inverts the credential this project already has:
`SITE_DEPLOY_KEY` lives in the PRIVATE repository and grants write to the public one, which is the
safe direction, and making the site pull would have put a read credential for a private repository
into a public repository's secrets, one workflow edit from exposure. With both public, a read needs
no credential in either direction. The artefact is a release asset rather than a committed file, so
30.7 MB per build never enters anyone's git history.

**WHAT PUBLISHING THE REPOSITORY NEEDS FIRST, and it was measured rather than assumed on
2026-08-14.** Three axes, and this repository was built for two of them from the start.

  IDENTITY. `.githooks/leak-guard.sh` has enforced one pseudonymous author on every commit since the
  beginning and scans content against a structural denylist and an out-of-band list of real names,
  self-testing against a planted canary and failing closed. Run over all 1,020 commits from the root
  to HEAD it reports clean, and every commit in the history carries the one permitted author.

  THIRD-PARTY CONTENT. 3,980 tracked files under `data/source` and every one is YAML records rather
  than copies of pages. No synopsis and no image URL is stored anywhere, which REQUIREMENTS §2 says
  and `comicfuz/works.yaml` repeats in its own header. The page caches are gitignored, so what would
  be published is this project's account of what a source said.

  WHAT ASSUMED PRIVACY. §8's cost argument, which is the next paragraph, and
  `TODO-github-setup.md`'s wording. Both are documentation rather than mechanism.

Publishing is one-way in practice, since forks and archives outlive a setting, so the audit above is
the thing to repeat rather than trust once.

**THE RISK THAT REMAINS.** A check that changes repository is a check that can quietly not be
adopted, and those 26 include the ones that caught `????·Bun?Bun` and Japanese leaking into English
mode, which are the most reader-visible failures this project has had. They move as a unit with
their canaries, and the site's CI gates on them BEFORE this repository stops running them.

**DONE 2026-08-14.** `corpus.sqlite` is what crosses, stamped with the digest of `schema.sql` and
the date the run compiled it. `--publish` vacuums and copies it; `update.yml` attaches it to a
release, which needs no cross-repository credential because it is a release on this repository, and
30 MB of binary per run never enters anyone's git history. The site pulls the latest release on its
own schedule.

**THE STAMP EARNED ITSELF WITHIN THE HOUR.** Adding `run_report` moved the schema digest, and the
site's build refused the store rather than reading it: `is stamped 'd07040c9…' and this build knows
('fe21da7d…',)`. That is the whole of what no-guarantee-of-format buys, working the first time it
could.

**WHAT MOVED, AND THE PROOF IT WAS THE SAME THING.** `build/from_store.py` writes the ten files, the
entry pages and the cache-busting version; `build/reader_checks.py` holds sixteen checks about what
a reader is shown, each at the number this repository recorded, each with its canary. Before
anything was deleted, the site's build was set beside this one's output and all ten files were
BYTE-IDENTICAL. `deploy.sh`, `stubs.py`, `pages.py`, `test_display.py` and `lint/entrypoints.py` are
gone from here, and so is every path naming the other repository: `SITE_ROOT`, the site clone in two
workflows, and the `site` digest the incremental gate hashed.

**THE EMITTERS ARE IMPORTED RATHER THAN FORKED, and that is the line the split actually draws.** How
a name folds, where a personal name parts and what a citation may show a reader are facts about the
CORPUS, with one home here. What the site decides is which files it wants and what a reader needs
beside them. Its build puts this repository's `adapters/` on the path, cloned at the commit that
made the store; the dependency runs one way and needs no credential because both are public.

**WHAT THIS REPOSITORY STILL READS OUT OF `data/build`, WHICH IS THE RESIDUE.** `build.py` goes on
writing the ten files because 51 modules here read them: the capture passes that ask what the
published database lacks, and the checks §10 has not moved. That is not wrong, since the files are
emitted from the store and cannot disagree with it, but it means a question about the COMPILED form
goes out through a file and comes back in, and it hides an ordering: a pass reading
`data/build/series.json` needs a compile in front of it and says so nowhere. `shopquery` and
`editions/capture` ask the store now, through one query both share, and each of their docstrings had
claimed to be its one producer while both held a copy of the loop. The rest are the queue.

**AND TWO QUESTIONS STOPPED EXISTING RATHER THAN MOVING.** `deployed data matches built` compared
this repository's output against a copy of it in another, and there is no copy step left. `the
archive does not lose a published row` was that same comparison at one remove, and it is a GUARD in
the site's build now: the build that would drop the row is the build that stops.

## 12. A test the length of what it tests

**THE LENGTH IS A SYMPTOM AND THE MODULE IS THE CAUSE.** `test_build.py` is 913 lines and 211
assertions in a single function, and it is that long because `build.py` is 7,467 lines. Splitting
the file gives four integration tests where there was one, and none of them is a unit test either.

**THE CURE IS EXTRACTION, AND §6 IS THE EVIDENCE.** `names/fold`, `names/attach` and `names/ruby`
came out of `build.py` because a second caller needed them, and each shipped with a unit test of
nine to thirteen assertions over pure functions with no build in sight. Each also removed a section
from `test_build.py`. That is the whole method: when a rule is asked twice it becomes a module, and
the integration test gets shorter as a side effect rather than as a project.

**§10 SHRINKS THE OTHER LONG ONE.** `test_relational.py` is 790 lines and most of what it asserts is
that the schema refuses a bad row. As those become constraints, each test is an insert and an
expected refusal, which is three lines and reads as one.

**WHAT SHOULD REMAIN WHEN THIS IS DONE.** An integration test that says the whole thing runs and its
outputs join up, named as an integration test so nobody mistakes its length for a fault. Everything
else is a module with a test the size of its subject.

**FIRST TWO OUT, 2026-08-14, AND THE METHOD IS THE POINT RATHER THAN THE COUNT.** A volume's number
went to `facts/volumenumber`, whose own docstring had named `build.volume_number` as its counterpart
while the counterpart sat where it could only be reached by importing a 7,400-line compiler. Merging
them collided on `FIRST_ISSUE`, one a pattern and one the word, which is what two spellings of one
fact in one module does the moment they meet. `norm_work` went to `facts/worktitle`: three adapters
did `from build import norm_work` and executed the whole compiler for nineteen lines of regex.

**A DELEGATE IS NOT A MODULE, and `test_build.py` says so where one is left.** Where a rule moves,
what stays behind is an assertion that the build still ASKS, which is what a delegate can get wrong;
the twenty spellings of `volume 1` are asserted where the rule is, and cost no compiler to run.

**THE SURVEY IS RECORDED SO THE NEXT PASS DOES NOT REPEAT IT.** The strongest remaining candidates,
in order: the print-run cluster, `_shop_address` through `merge_volumes`, 410 lines carrying 46
assertions across four sections of `test_build.py`; the credit recomposition, 180 lines and 14
assertions, whose second implementation already exists in `check.py`; the shelf citation rule, 16
assertions, which splits into a pure parser and a file read; the chapter-title classifiers, 140
lines gathered from five places and 35 assertions, the largest single block in the test. And
`undated_publication`, `state_claim_rows`, `work_level_addresses` and the length cluster after
those. What LOOKS extractable and is not is worth as much: `work_alias` reads a file into a module
global AND writes a second one that a later pass reads back, `set_aside` globs the source tree, and
`main()`'s inner functions close over its locals and are asserted nowhere.

## 13. Nothing here reads the JSON

**WHAT §6 LEFT HALF-DONE, SEEN FROM THE OTHER END.** §6 reversed the direction: the compiler writes
the store and the JSON is emitted from it. §11 moved the emission of what a READER is served into
the repository that serves it. What neither touched is that this repository still writes the same
ten files into `data/build` and then reads them back: 51 modules here do, and `build.py` writes them
for no other reason. The compiled form is the store, and a pass asking the compiled form a question
should ask the store.

**IT IS NOT WRONG TODAY AND THAT IS WHAT MAKES IT WORTH DOING.** The files are emitted from the
store, so they cannot disagree with it; nothing is broken. What it costs is an ordering nobody
states. A pass reading `data/build/series.json` needs a compile in front of it, says so nowhere, and
on a machine that has built before it reads whatever the last build left. `shopquery` died on that
every CI run for two days, and on a developer's machine it looked like it worked.

What reads what, measured 2026-08-14:

| file | readers here | what they are asking |
|---|---|---|
| `series.json` | 22 modules | populations: what the corpus holds, and what it lacks |
| `feed.json` | 11 | every release, which the store now holds in full |
| `works.json`, `index.json` | 16 between them | the record layer and the collapsed index |
| `titles.json` | 4 | is this a work we hold |
| `credits.json`, `publishers.json` | 7 | the record pages |
| `run.json`, `checks.json`, `status.json` | 10 | the run's report on itself |

And 43 of `check.py`'s 112 checks read a built collection. §10 moved 14 and this is the rest of that
queue.

**THE WORK, IN THE ORDER ITS DEPENDENCIES ALLOW.**

  A POPULATION IS A NAMED QUERY AND TWO PASSES ALREADY SHARE ONE. `asks.POPULATIONS` holds the
  first, `works with a serialisation and no print edition`, asked by `shopquery` and
  `editions/capture`, each of whose docstrings had claimed to be its one producer. Every other
  question a capture pass asks of `series.json` is the same shape: which works a shelf has not been
  read for, which have no cover, which have gone quiet, whether we hold this title at all. About
  twenty of them, each a query and a call site.

  THE 43 CHECKS ARE §10 CONTINUED, on §10's terms: a constraint where the violation can be made
  unstateable, a query with its number where it cannot, Python where the subject is prose or the
  source tree. Each reproduces its number or the difference is explained.

  THEN `build.py` STOPS WRITING THEM, which is the observable end and is one line per file. The
  emitters stay, because the site calls them, and this repository stops calling them at all.

One thing has to be decided before the last step. `run.json`, `checks.json` and `status.json` are the
run's report on itself rather than compiled data, and `served.CORPUS` has always excluded them. They
are also what the site's status page is built from. Under §11 that page is the site's to build, so
either the store carries the report and the site renders it, or this repository goes on publishing
three small files that are not the corpus. That is a question about what a report IS, and it is the
only part of this section that is not mechanical.

**AND WHAT IS LOST, SAID PLAINLY.** `data/build` is a debugging affordance: a person can open
`series.json` and read it. A store is not readable that way, and `--ask` answers questions somebody
already thought to write down. Whatever replaces the affordance should exist before the files go,
or the first hard bug after this section will be argued in the dark.
