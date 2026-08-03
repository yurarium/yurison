# Standing instructions

How to work on this project. Loaded every session via `CLAUDE.md`.

**Authority order.** A lower layer may not contradict a higher one; where they conflict the higher
wins and the lower is wrong and should be fixed.

1. **These standing instructions**
2. **[Definitions](DEFINITIONS.md) and [Requirements](REQUIREMENTS.md)** — what a work is, what may
   be sourced, what must never be published
3. **Feature definitions** — [Interface](FEATURES-INTERFACE.md), [Names](../NAMES-PLAN.md)
4. **Invariants and budgets** — `check.py`, enforced at check-in
5. **Implementation**

---

## 1. Verify; do not assert

The characteristic failure here is not being wrong, it is **being confident without having
looked**. Specifically:

- **Never report a result you have not observed.** Not "this should now work" — run it and read the
  output. A build's exit code, a served file's contents, a rendered page.
- **Never pipe build output through `grep`.** It has swallowed a traceback three times and each
  time produced several turns of confidently wrong reporting. Read the output; filter afterwards.
- **"Pushed" is not "live".** A green *pages build and deployment* has been green for a build of the
  *previous* commit. The reliable check is grepping a marker out of the **served** file.
- **Do not take an agent's report at face value.** Verify its central claim independently. Sub-agent
  reports have been accurate here, but the one time a claim was load-bearing (AniList returning 403)
  it was worth the thirty seconds to reproduce.

## 2. Fix by rule, not by case

A fix that handles only the reported instance is half a fix. When something is reported:

1. Find the **class** — how many other rows have the same shape? Report that number.
2. Fix the class.
3. **Test the counter-case before believing the rule.** Every over-general rule in this project's
   history was caught by one example: `名` in 君の名は, `V` in Vチューバー, kun-yomi for names.
   Look for the case the rule would break *before* shipping it.

## 3. The dominant bug: two paths, one fact

Seven shipped bugs came from the same shape — the same fact derived independently in two places,
with nothing forcing agreement. `analyse()` vs `furigana_spans()`. The reading vs the ruby. `en` vs
the romanisations. A badge computed outside the loop that re-renders it.

**Before adding a second producer of an existing fact, ask whether it can consume the first
instead.** Where it genuinely cannot, add an invariant to `check.py` asserting they agree. Care does
not scale; the invariant does.

## 4. Silence is the failure mode to design against

Things here fail by returning something plausible, not by raising:

- SudachiPy returns the **surface** when it has no reading, and キゴウ — the word "symbol" — for
  punctuation
- a moved CSS selector returns rows with a field missing, and the build accepts them
- an empty result set looks exactly like "nothing matched" and like "the fetch failed"

So: **test for the specific bad value, not for an exception.** And every checking mechanism must be
able to prove it ran — `check.py --self-test` and `.githooks/leak-guard.sh` both canary themselves
for this reason. A clean report must mean "the check ran and caught its canary", never "the check
did nothing".

## 5. Absence is a state, not a missing value

Written in REQUIREMENTS and violated at least five times since, so it is repeated here. カドコミ's
silence is not "paid". An unbadged chapter is not "unknown". A work with no chapters is a *lead*,
not a work. A claim we have checked is *refuted*, not pending.

## 6. Nothing unactionable in front of a reader

The interface states facts about **manga**. Facts about **us** — coverage, confidence, what we have
not got to yet — belong on `status.html`.

The one deliberate exception is an unverified **name reading**, which is marked, because it is a
fact about the content, a Japanese-literate reader can judge it on sight, and it protects a real
person from being authoritatively misnamed. See `NAMES-PLAN.md` §5d. **Do not "tidy" it away by
applying the general rule mechanically** — that is exactly the mistake it is written down to
prevent.

## 7. It must run unattended

Anything that requires someone to remember to run it is not finished. The naming passes fill
themselves on every build for this reason.

**Backend: correct by construction, with stated fallbacks.** The site must keep updating. A
violated invariant degrades to the fallback named in `check.py`, is counted, and is surfaced on
`status.html`. The build does not abort.

**Check-in: all right or no go.** The same invariants block, because a person is present who can
fix them.

## 8. Bug protocol

1. **Reproduce** and say how many rows share the shape.
2. **Add the check first** — an invariant in `check.py` if the statement is absolute, a tightened
   budget if it is a count. Watch it fail.
3. **Fix.**
4. **Watch the check pass**, and re-run the full gate.
5. **Record the shape in the commit message**, including any rule you tried and rejected. The
   rejected ones are the expensive knowledge — `NAMES-PLAN.md` records two, so they are not
   re-derived.

**Every shipped bug adds an invariant or tightens a budget, in the same commit as the fix.** That
is what converts a history of corrections into a floor that cannot be lost.

## 9. Licences are checked, not assumed

Read the project's own declaration before depending on it. Copyleft **data** is avoided where
avoidable: KANJIDIC2 and JMdict are CC BY-SA and deliberately unused; SudachiDict is Apache-2.0 and
Unihan is the Unicode licence. Data files derived from a source carry their attribution in the file.

## 10. Writing it down

- **Commit messages carry the reasoning**, including what was rejected and why. They are the
  project's decision record and are read back.
- **Comments explain why, especially why the obvious alternative was not taken.** A comment
  restating the code is noise; a comment naming the bug the code prevents is load-bearing.
- **Put the lesson next to the code it governs.** A rule in a module docstring survived and got
  cited; the same rule in a central document did not prevent five repeats.
- **A document that describes a state goes stale; one that records a decision does not.** Prefer
  the latter, and generate the former.

## 11. Write so a stranger can use it

Almost every word here was drafted by an assistant, and assistants reach for a small set of
prefabricated constructions. The problem is not that they identify their author. It is that they
are bad writing: a sentence spent saying nothing, an abstraction where a fact belongs, rhythm in
place of content. Enough together and the text lands in the uncanny valley, where a reader feels
the wrongness before naming it and stops trusting the page.

**This is not a disguise.** That the project is AI-driven is neither hidden nor advertised.
Attribution stays. Nothing here exists to defeat a detector, and where a detector and the reader
disagree, follow the reader.

**The documentation is part of the deliverable.** The informational foundation and the architecture
ship in the repository so that a third party can pick the project up and run with it or change it.
Write for that person: someone competent who has never seen this before, is trying to do something
specific, and will not read the whole thing. It has to be worth a stranger's time.

**The test:** would this annoy someone trying to use the project? Does the sentence say a thing, or
perform saying a thing?

`adapters/lint/tics.py` mechanises the part that can be mechanised, in three tiers:

| | |
|---|---|
| **HARD** | Constructions with no legitimate use. Invariant, zero in public text. |
| **SOFT** | Ordinary words that are filler in bulk. Budget, ratchets down. |
| **DENSITY** | Correct in ones and tiresome in threes. Measured per thousand words. |

Every entry names what to write instead, because a rule that only says "don't" is satisfied by
deleting the sentence. **If a rule makes a passage worse, the rule is wrong.** Change it rather
than working around it.

**Kept, though published lists of tells name them:** bold-lead bullets, numbered rules and tables,
because a rule here has to be findable and citable by someone who has never read the document.
Legibility beats camouflage. Curly quotes, which are correct typography for web text.

**Avoided:** em dashes, zero in public text and a budget internally. The reason is rhythm rather
than signature. A page of them reads as one long breath, and cutting them makes the sentence
structure carry the meaning.

**What no lint will catch, and you must:**

- **The escalating triple.** Three parallel clauses where two would do, the third adding rhythm
  rather than content.
- **The emphatic fragment.** A one-clause sentence dropped after a long one for weight.
- **Restatement as structure.** A paragraph whose last line says what its first line said.
- **Elegant variation.** Reaching for a synonym to avoid repeating a word. Repeat the word.
- **Hedging that carries no information.** "Generally", "typically", "often" attached to a claim
  that is either true or is not.
- **Symmetry that was not in the facts.** Two options given equal weight because two reads well,
  when one is obviously right. Give the recommendation.

**A rule this file got wrong, kept as a warning.** The first version exempted em dashes, reasoning
that the user writes them and these documents are full of them. That conflated how the user writes
in conversation with what the project publishes, and it survived exactly as long as it took someone
to read the README. When a style rule is being justified by *our* habits rather than by the
reader's experience, the rule is about to be wrong.
