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
| §3 | Volumes, editions and the print run | §2 |
| §4 | Releases and the per-platform offer | §3 |
| §5 | Renderings, which are derived from a source that stays where it is | §4 |
| §6 | The compiler writes the store; the JSON is emitted from it | per domain, as each lands |
| §7 | Incremental on every update, reconciled weekly | §6 |
| §8 | Turn the schedule on | §7, and TODO-github-setup §C's conditions |
| §9 | The maintenance pass, and what it works from | §1a |

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

## 4. Releases and the per-platform offer

974 releases in the window and a per-platform `sources` array on every series row: what a platform
holds, what it charges for, and when it last updated. `schema.sql`'s own comment says these are
properties of the platform's offer and not of the work, which is a relational statement already.

**WHAT BECOMES EXPRESSIBLE.** A release belongs to a work and to a platform, both by foreign key, so
a release naming a work we do not hold is refused rather than counted. `updates naming a work we do
not hold` is 18 today, and those 18 are the reason §1a comes first: this is the commonest way a
capture arrives faster than the corpus can admit it, so it is the case the quarantine will carry
most often and the one that must never cost an unattended run its other work.

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

## 6. The compiler writes the store; the JSON is emitted from it

**PER DOMAIN, AS EACH LANDS, and never as a cutover.** When a domain is modelled, `build.py` writes
it to the store, the JSON for it is emitted FROM the store, and the direct path is deleted. Then
§1's budget falls by that domain and cannot rise again without something failing.

The site's format is not this plan's question. The emitter may write the same JSON the browser
fetches today, or something narrower, or the site may one day query the store directly. What this
plan fixes is that the data reaches the site THROUGH the store. Everything about presentation stays
free to evolve behind that line, which is the whole reason the line is worth drawing.

**WHAT MUST NOT HAPPEN.** A domain half-migrated, where the store holds it and the JSON is still
written directly. That is two producers of one fact, which is the fault this project names most
often. The budget in §1 does not catch it, which is why the direct path is deleted in the same
change that adds the emission.

## 7. Incremental on every update, reconciled weekly

**THE HARD PART IS ALREADY ARGUED.** `delta.py`'s design is one sentence: the cascade is gated on
OUTPUT change and never on input change, so a write producing the value already there cascades
nothing. Its correctness is by construction, since a pure derivation plus an idempotent write means
the fixed point a delta converges to is the fixed point a rebuild produces.

**IT HAS NO PRODUCTION CALLER.** Nothing outside its own tests has ever applied a delta. So this
section is not about writing the updater; it is about an update run applying what it captured
through `delta.write` rather than recompiling, and about the failure modes that only appear when
real captures drive it.

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
