# A gate that is cheap by construction: a plan

Written 2026-08-13, after an iteration loop that felt slow was measured and was not. Everything
below rests on numbers taken on one machine on that day, and the first section exists because the
premise this plan was asked for turned out to be wrong.

| | |
|---|---|
| `./build.py` | 35.6s |
| `./test.py`, 180 suites | 39.8s |
| `./check.py --gate` | **79.6s** |
| `./check.py --gate --proved-by tests --incremental` | **2.6s** |
| `relational/__init__.py --build` | 6.9s |

The sections are in the order they are to be done, and each says what it needs from the one before.

| | stage | needs | worth |
|---|---|---|---|
| §1 | Make the cheap path the one you get by accident | done 2026-08-13 | 79.6s to 28.5s |
| §2 | Stop re-proving the checks against unchanged code | done 2026-08-13 | 28.5s to 2.4s |
| §3 | Render the interface once, ask it six questions | nothing | about 13s off `--full` |
| §4 | Let the schema refuse what the checks report | §1 | five fault classes, no seconds |
| §5 | Derive the content-flag report rather than reconcile it | §4 | 8.1s and two false alarms |

## 0. What is actually slow, and it is not the gate

A full build, test and gate cycle is under three minutes. With the fast gate it is about 78 seconds.
Nothing in the loop is slow in the sense the phrase usually means.

**WHAT MADE IT LOOK SLOW.** An operator polling background jobs on a cadence far longer than the
jobs take. A 36-second build watched on 90-second polls reads as six minutes, and the conclusion
drawn from it was that the gate needed optimising. The gate did not. This section is first because
a plan that begins by optimising the wrong thing is the expensive kind of mistake, and the evidence
that it nearly happened is worth keeping in the file.

**WHAT IS STILL TRUE.** `./check.py --gate` really does cost 79.6s, and that is the invocation a
person types. 2.6s is available and is reached only by remembering two flags. That gap is the real
finding and §1 closes it.

## 1. Make the cheap path the one you get by accident

**THE FAULT.** `--incremental`'s own help says "cycle.py's fast path passes it and `--full` never
does". So the design already names a `--full` and already treats incremental as the ordinary case,
and the default is the other way round. A person typing the documented command gets the slow answer
and no indication that a fast one exists.

`--proved-by` is the same shape: it exists so a gate running beside the tests need not re-prove the
checks itself, and only `cycle.py` passes it.

**WHAT TO DO.** `--gate` implies `--incremental`. `--full` turns it off and keeps every current
guarantee. `cycle.py` stops passing a flag it no longer needs to name.

The cache contract is already right and none of it moves: a pass is remembered against
a digest of what the check read, a failure never is, and `test_incremental.py` proves it by planting
a violation and asking whether the next run still measures that check. §1 changes which path is
default and nothing about what the path may remember.

**HOW IT IS PROVED.** `cycle.py --full` already refuses the green-tree token and every remembered
pass, and `equivalence.yml` runs it weekly. A default that is wrong shows up there rather than in a
reviewer's memory.

**DONE 2026-08-13, and inverting a default broke something it was easy to miss.** `cycle.py --full`
reached the full path by NOT passing `--incremental`, so it was the absence of a flag. With the
default inverted that absence became the FAST path, and `--full` would have quietly run the cached
checks, which is the one thing it exists to refuse. It now says `--full` to the gate outright.
`test_cycle` asserted the old spelling and would have passed throughout, so it is rewritten to ask
the property: the full plan says `--full`, the fast plan does not.

## 2. Stop re-proving the checks against unchanged code

**THE FAULT.** 24.7s of 79.6, a third of the gate, goes to proving the checks can fail. That
question is about `check.py` and the `facts` modules. It is re-answered on every run over data that
cannot affect it.

`--proved-by` addresses this only where a second process is running the tests. There is no answer
for a person running the gate alone, which is the case §1 makes common.

The fix is to digest the checking code, the same way `_input_keys` digests the three input
classes, and remember the self-test result against it. A run whose checking code is unchanged skips
the proof; any edit to `check.py` or a `facts` module re-runs it in full.

**THE COUNTER-CASE TO TEST.** A check whose behaviour depends on a file outside the digest, which
is the blind spot `_input_keys` already documents about itself: it takes three over-approximations
rather than 110 hand-kept declarations, and a check reading something in none of the classes is
invisible to it. The self-test digest must over-approximate in the same direction, covering every
tracked Python file rather than a list of the ones believed relevant.

**DONE 2026-08-13.** The proof is remembered under a reserved name that starts with a space, so no
invariant or budget can collide with it, and it is keyed by `_verify_key` on the code AND the build,
because the canaries are planted in the real context. It needed no key of its own design.

`./check.py --gate` is 2.4s on a tree it has answered for, 78.9s on one it has not, and `--full`
refuses the remembered answer. Both halves of the counter-case were run by hand: touching
`facts/reading` re-proved in 25.5s rather than trusting the cache, and restoring the file re-proved
again rather than carrying a stale entry across the change.

## 3. Render the interface once, ask it six questions

**THE FAULT.** Six checks each build the interface and run the real `kari/app.js` in a Node vm:
`every name is defined where it is used` (5.3s), `no ruby over bare Latin` (5.2s), `no cataloguing
notation in an English rendering` (3.8s), `a byline never states the default role` (2.5s),
`renderings resting on a mechanical romanisation` (1.9s), `full-width forms in English renderings`
(1.8s). About 18s, and they agree on the collections they render.

One memoised render per gate run answers all six, each check keeping its own question and its own
name. This is memoisation and leaves every rule where it is.

**WHY IT IS NOT FIRST.** With §1 in place a data-only run skips most of these anyway. It earns its
place on `--full`, which is what `equivalence.yml` runs weekly and what a reviewer runs after
touching the interface.

## 4. Let the schema refuse what the checks report

**THE DESIGN IS DONE AND NOT ENACTED.** `adapters/relational/schema.sql` opens by naming five
invariants in `check.py` that are foreign keys written out as Python, "and they run after the damage
rather than refusing it":

    every credit identifier resolves            work_credit.credit -> credit.id
    a shipped identifier resolves               work_credit.work   -> work.id
    one row per identifier                      primary keys
    credit pages listing a work that does not name them    the edge is the only link
    publisher pages listing a work from another house      the edge is the only link

All five are still live in `check.py`. The last two are the ones worth having: the schema's own
claim is that they "stop being checkable at all, which is the point: there is no way to state the
wrong thing".

**THIS BUYS FAULT CLASSES AND NOT SECONDS, and the plan should be honest about that.** None of the
five appears in the gate's expensive list. What changes is that a dangling credit identifier becomes
unstateable rather than reported, which is worth doing on its own terms and will not move the clock.

It needs the store in the daily path. `--build` costs 6.9s, which is a fifth of the build
it follows, so the cost argument that kept it out does not survive measurement.

**WHAT KEPT IT OUT, AND WHAT THAT ARGUMENT ACTUALLY SAYS.** `equivalence.yml` explains that
`delta.py` updates the store without recompiling it and that its correctness argument is
convergence, tested against the same `reads` declarations the updater uses, so a wrong declaration
satisfies the updater and its tests together. A full rebuild shares nothing with those declarations
and is therefore the check that does not share its subject's blind spot, §14b's rule.

That argues for the REBUILD staying weekly and independent. It does not argue for the store being
absent from the daily path. The two were collapsed, and separating them is what unblocks this
section: build the store daily, keep the weekly rebuild-and-compare exactly as it is.

## 5. Derive the content-flag report rather than reconcile it

**THE FAULT.** `content flags are accounted for` costs 8.1s and gave two false failures in one day.
It reconciles a register against a report by computing the marketing signal a THIRD time: it
`exec_module`s `build.py` and applies its patterns to the DEPLOYED `series.json`. A fresh build
judged against a stale deployment fails it, both times today, neither time a fault.

**WHAT TO DO.** `run.json`'s rows already come from `content_flags()` and `marketing_flags()`. Make
that the single producer, so the report is derived from the register rather than compared with it,
and the disagreement the check looks for cannot arise. What remains worth asserting is that a
withheld work is absent from what is served, which is a byte test on the output and near-free.

**THE GENERAL FORM, and it is the reason this section is in the plan at all.** A check that
reconciles two producers of one fact is evidence there should be one producer. That is
STANDING-INSTRUCTIONS §3 turned on the checks themselves. `the interface folds a name key as the
build does` is the same shape: it exists because Python and JavaScript each implement the fold, and
a build that emitted the folded key to an interface that never folds would leave it nothing to
disagree about.

**WHAT MUST SURVIVE.** The reason the check exists. A register that nothing consumes reads as a
control that is working, which is how five works stayed live on the public site while a file said
they were withheld. Deriving the report keeps the consumer; it removes only the third computation.

## What is deliberately not here

**Porting budgets to SQL.** `delta.DERIVATIONS` expresses five, and most budgets are counts over
shipped rows, so the shape fits. It is left out because `--gate --incremental` already answers in
2.6s, so this would replace one fast answer with another, and because the delta updater's
correctness argument is the one the project itself treats as needing an independent weekly proof.
Widening its surface before that proof has run against a much larger set of derivations is betting
on the piece that is already known to need watching.

Reconsider it when §1 to §5 are done and the number that argues for it is a measurement rather than
an expectation.
