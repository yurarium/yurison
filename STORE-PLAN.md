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
| §1a | Somewhere for what a constraint refuses | before anything refuses |
| §2 | Fill the two tables that were designed and never written | done 2026-08-13 |
| §3 | Volumes, editions and the print run | done 2026-08-13 |
| §4 | Releases and the per-platform offer | done 2026-08-13 |
| §5 | Renderings, which are derived from a source that stays where it is | done 2026-08-13 |
| §5a | The constraints that do not fire | done 2026-08-13 |
| §5b | A row nothing can address twice | done 2026-08-13 |
| §5d | A name is an identity here, and it must not be | done 2026-08-13 |
| §5c | What the store says it holds and does not | §5a |
| §5e | The domains still outside the store | §5c |
| §6 | The compiler writes the store; the JSON is emitted from it | §5e |
| §7 | Incremental on every update, reconciled weekly | §6, and §5b absolutely |
| §8 | Turn the schedule on | §7, and TODO-github-setup §C's conditions |
| §9 | The maintenance pass, and what it works from | §1a |

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
fold the table is keyed on resolves all 55 and is a change to one dictionary.

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

**A CITATION THAT CITES NOTHING SATISFIES `edition`'s CHECK.** 915 rows cite the literal string
`'ndl'`, and 2,818 cite a series-level page, one of them shared by 119 volumes. The check the
comment names, `per-book dates cite their page`, is about per-book pages specifically, and 3,733 of
the 6,108 dated rows carry a citation that does not witness the date. `cite = 'nonsense'` inserts.

**`imprint` IS KEYED ON A SPELLING AND A LINE IS IDENTIFIED BY ITS SLUG.** 906 of 2,661
`work_publisher` rows carry no imprint, because the print blocks spell one line as `Yuri-hime
comics`, `Yurihime comics` and `IDコミックス　／　Yurihime comics` and the loader matches by exact
name. 125 of 306 imprint rows have no slug. 47 work and publisher pairs have more than one print
block and 15 name different imprints, of which the loader keeps the first without counting the
rest. `parent` is free text and one value resolves to no imprint.

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

**PER DOMAIN, AS EACH LANDS, and never as a cutover.** When a domain is modelled, `build.py` writes
it to the store, the JSON for it is emitted FROM the store, and the direct path is deleted. Then
§1's budget falls by that domain and cannot rise again without something failing.

The site's format is not this plan's question. The emitter may write the same JSON the browser
fetches today, or something narrower, or the site may one day query the store directly. What this
plan fixes is that the data reaches the site THROUGH the store. Everything about presentation stays
free to evolve behind that line, which is the whole reason the line is worth drawing.

**IT CANNOT START ON A DOMAIN §5e HAS NOT MODELLED.** An emitter cannot write a field the store has
no table for, and a work's state, its admission evidence and its byline are all in that position.
§1's budget standing at 391 is the list, and it is the same list because the budget asks what the
site is served rather than what the store holds.

**WHAT MUST NOT HAPPEN.** A domain half-migrated, where the store holds it and the JSON is still
written directly. That is two producers of one fact, which is the fault this project names most
often. The budget in §1 does not catch it, which is why the direct path is deleted in the same
change that adds the emission.

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

**THE COST IS THE ONE THAT DECIDES IT.** `yurison` is private, so Actions bills against 2,000 free
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
