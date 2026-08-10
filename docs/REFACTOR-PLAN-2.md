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

### Stage C. The schema earns its place or is retired

7. **Something consumes the store.** `adapters/store/` builds, answers five standing questions, and
   nothing in the pipeline reads it. A schema nothing consumes is a document, and this plan should
   not pretend otherwise. Either a check moves onto it or the claim that it replaces invariants
   stays theoretical.

8. **The eight refused claims are dealt with.** `researched` readings carrying no reasoning, which
   `curate.problems` is supposed to demand. The enforcement has a hole as well as the data.

9. **`analyser` gets a ruling or a reason.** It is the commonest source kind in the store and
   `READING_ATTRIBUTION` does not mention it. The loader admits the pair against the `analyser`
   basis alone, which is a decision made by a loader and belongs to the owner.

### Stage D. The facts the first round did not reach

10. **Six facts are still unowned:** dates, inclusion, work identity, title cataloguing, imprint,
    and rendering surfaces. Two of them, `title cataloguing` and `imprint`, are close: each already
    has a single reader. The first round took four and stopped where the plan's list stopped.

11. **Rendering surfaces are derived, not listed.** `interface.py` keeps a hand-written table, and
    `creditLine` missing from it let `???? · Bun?Bun` reach a reader. A hand-maintained list of what
    to check will always lag what the renderer does.

### Stage E. The residue the first round recorded and did not clear

12. **The eight unevidenced impossibilities**, found by the lint decision 8 called for.
13. **Two modules called `store`**, whichever is on the path first winning.
14. **The glued-romanisation shape** (`Uedakyōko`) and **the kana that spells a foreign name**
    (`Sutefan Sejiku`), both raised by the owner and both written up rather than done.
15. **Fifteen leftover worktrees**, thirteen unmerged, two holding uncommitted edits.

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

A full cycle runs in under two minutes with nothing verified less than it is today. Every fact the
inventory lists has one owner. The store is consumed or retired. Nothing in the residue list is
still a note.
