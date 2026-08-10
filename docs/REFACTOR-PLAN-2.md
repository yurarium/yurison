# Refactor plan, second round

Agreed 2026-08-10, after measuring the working cycle that the first round was supposed to shorten.
The tracker for this plan is GENERATED from the repository, not hand-written, for reasons the first
round demonstrated.

## Why there is a second round

The first plan named `build.py` and `test.py`, so those are what got measured and improved: 95 to 52
seconds and 62 to 26. A full cycle still takes about six minutes, because the two largest terms in
it were never timed.

| step | seconds |
|---|---:|
| `build.py` (full) | 79 |
| `deploy.sh` | 39 |
| `check.py --gate` | 97 |
| `test.py` | 30 |
| *subtotal, run by hand* | *245* |
| push runs `--gate` again | 97 |
| push runs `test.py` again | 30 |
| **total** | **372** |

**The checks answer the same question four times in one cycle.** `build.py` shells out to
`check.py --runtime`; `deploy.sh` runs it again at the end; a person runs `--gate`; the pre-push
hook runs `--gate --no-tighten` and `test.py`. Roughly 170 of the 372 seconds are re-answering.

`deploy.sh` is not a copy either. It regenerates 5,378 pre-rendered pages through `pages.py`,
`stubs.py` and `status.py` every time, almost all of them unchanged.

**And the meta-fault, which matters more than the seconds.** Decision 1 of the first plan said to
measure the parse fraction and the dependency graph, and that is exactly what was measured. Nobody
asked whether the list was the right list. A plan that says what to measure is a fact with one
producer, and it went unchecked, which is the failure the whole first round was about.

## What this round fixes, and in what order

Ordered by payoff against risk, with the cheapest guarantees first.

### Stage A. The cycle stops re-answering itself

1. **A green-tree token.** After `check.py --gate` passes, record a hash of everything the checks
   read. The pre-push hook skips the gate when the hash is unchanged. The hook remains the
   mandatory boundary; it stops re-proving a tree proved a minute ago.

   **The hazard, stated up front:** a token is a claim that nothing changed, and it must hash the
   INPUTS TO THE CHECKS, not just tracked source. A token over the wrong set vouches for a stale
   answer, which is worse than the 127 seconds it saves. It records what it hashed, and a token
   that cannot say what it covered is not honoured.

2. **`deploy.sh` stops running the checks.** The fourth run buys nothing the gate has not said.

3. **`build.py --no-checks` becomes the default for a build, with `--checks` to opt in.** The
   flag exists and I did not use it consistently, which is a sign the default is wrong.

### Stage B. The expensive checks stop rescanning what has not changed

4. **`stock phrasing in comments` caches per file.** 12.8 seconds of a 97-second gate, spent
   re-reading about 280 files that mostly did not change. Key on content hash, not mtime.

5. **`deploy.sh` regenerates only pages whose content changed.** 39 seconds for 5,378 pages that
   are nearly all identical to the ones already there.

6. **Audit every remaining check for the same shape.** The two above were found by timing; nothing
   says they are the only two. A per-check timing report, printed by `--gate --timings`, makes the
   next one visible without another round of this conversation.

### Stage C. The store becomes load-bearing

Ruled by the project owner on 2026-08-10: retiring it is off the table. The store carries the build
and the site. It is still not a unique source of truth, and data is compiled into it from
git-diffable sources.

What it buys is the thing the current pipeline cannot do: **partial ingestion**, so new source
information updates the store without recompiling it, and a **differential site build**, so only
the artefacts that changed data requires are written. There are 5,542 pre-rendered pages today and
a deploy regenerates all of them.

**THE CONSTRAINT ON HOW THIS IS PROVED, and it shapes the design.** Equivalence with a from-scratch
rebuild is established constructively and by focused offline tests. It is NOT established by
building the whole database twice and comparing, which is the verification a slow pipeline reaches
for and the reason it stays slow.

7. **Nothing writes to the store except the compiler.** The property that keeps it derived. A check
   proves the only writer is `adapters/store`, the way the fact lint proves an entry point.

8. **The cascade is gated on OUTPUT change, and never on input change.** This is the whole design
   and it replaces a more elaborate one. Every derivation is a pure function of the store,
   recomputed as freely as SQL allows; a write that produces the value already there is a no-op and
   cascades nothing. Downstream work is triggered by a digest that moved, so a recomputation that
   confirms what was already known costs a comparison.

   **Measured, because the first version of this plan guessed the other way.** Scanning every credit
   surface is 1.2 ms. Grouping every credit by its works is 4.1 ms. Grouping all 4,989 claims is
   2.4 ms. The expensive thing was never the reduction; it is rewriting a class of rows, and that
   only happens when the answers actually move, which in the common case is few of them or none.

9. **Convergence is the correctness argument.** Recompute what a delta touches, follow the digests
   that moved, and stop when nothing moves. A pure derivation plus an idempotent write means the
   fixed point a delta converges to is the fixed point a rebuild produces, so equivalence is a
   property of the construction and not something a comparison has to discover. Most deltas settle
   in one pass.

10. **A reduction over everything is fine; assuming its output changed is not.**
    `interpunct.attested_apart` reads every credit field to decide one name, and adding a work that
    credits くろば on its own genuinely flips くろば・Ｕ from one person to two. That is a real
    dependency and the answer is to recompute the reduction, which is milliseconds, and then let
    the digest decide whether anything downstream cares. The failure to avoid is treating an input
    change as an output change and rewriting a class that did not need it.

11. **The delta kinds are enumerated and each gets its own focused test.** Insert, update, delete,
    merge, divide, retract. Deletion and retraction are where these systems fail, because an output
    whose input disappeared has nothing left to notice it, and a digest that is never recomputed
    never moves.

12. **A differential site build.** Each artefact declares the store rows it renders; an artefact is
    rewritten when the digest of those rows changes. 5,542 pages, nearly all identical between runs.

13. **A weekly full rebuild on the GitHub side, compared against the incremental store.** The
    owner's suggestion of 2026-08-10, and it puts the expensive proof where the time does not
    matter. The focused tests have to be provable able to fail, and the honest proof that they
    catch a real divergence is a whole rebuild set beside a store that has only ever been updated.
    Running it weekly in CI costs a couple of minutes of a 2,000-minute allowance and keeps it out
    of the working loop entirely.

    Section 14b: this is the check that does not share the incremental path's assumptions. Every
    focused test is written against the same dependency declarations the updater uses, so a wrong
    declaration satisfies both. A rebuild shares nothing with it.

    What it does on a difference is report, loudly, with the rows that differ. It does not
    silently overwrite the incremental store with the rebuilt one, because a divergence is a bug in
    the updater and quietly repairing the symptom would hide it until the next one.

14. **The eight refused claims are dealt with.** `researched` readings carrying no reasoning, which
    `curate.problems` is supposed to demand. The enforcement has a hole as well as the data, and the
    store already refuses the rows.

15. **`analyser` gets a ruling or a recorded reason.** It is the commonest source kind in the store
    and `READING_ATTRIBUTION` does not mention it. The loader currently admits the pair against the
    `analyser` basis alone, which is a decision a loader made and which belongs to the owner.

### Stage D. The facts the first round did not reach

16. **Six facts are still unowned:** dates, inclusion, work identity, title cataloguing, imprint,
    and rendering surfaces. Two of them, `title cataloguing` and `imprint`, are close: each already
    has a single reader. The first round took four and stopped where the plan's list stopped.

17. **Rendering surfaces are derived, not listed.** `interface.py` keeps a hand-written table, and
    `creditLine` missing from it let `???? · Bun?Bun` reach a reader. A hand-maintained list of what
    to check will always lag what the renderer does.

### Stage E. The residue the first round recorded and did not clear

18. **The eight unevidenced impossibilities**, found by the lint decision 8 called for.
19. **Two modules called `store`**, whichever is on the path first winning.
20. **The glued-romanisation shape** (`Uedakyōko`) and **the kana that spells a foreign name**
    (`Sutefan Sejiku`), both raised by the owner and both written up rather than done.
21. **Fifteen leftover worktrees**, thirteen unmerged, two holding uncommitted edits.

## The tracker updates itself

The first round's tracker was hand-edited, and it was wrong twice: a step was marked done that had
not been done, and a stage stayed "in progress" after its steps were complete. Both were caught by
the owner reading it, which is the wrong reader for that fault.

**So the tracker is GENERATED.** `adapters/tracker.py` measures the repository and emits the page.
What it reports is derived from the tree:

- **timings** by running each step, so the headline numbers cannot go stale
- **stage and item state** from `docs/plan-2-state.yaml`, which holds one line per item and is the
  only hand-written input
- **the fact inventory** from `adapters/facts/`, counting entry points, tests, checks and blind
  spots on disk
- **budget movements** from `docs/budgets.json` against what the tree measures
- **the open residue** by running the lints, so a number cannot be claimed lower than it is

The hand-written part is deliberately one line per item, because a status somebody types is the one
thing a machine cannot derive. Everything a machine CAN derive, it derives.

**And it runs without being remembered.** `check.py --gate` refreshes the state file's measured
half, and the plan's own item states are edited in the same commit as the work they describe, which
is where a reviewer sees them.

## What done looks like

A full cycle runs in under two minutes with nothing verified less than it is today. An ingestion of
new source data updates the store and the site without recompiling either, and the equivalence with
a from-scratch build rests on declared dependencies and focused tests. Every fact the inventory
lists has one owner. Nothing in the residue list is still a note.
