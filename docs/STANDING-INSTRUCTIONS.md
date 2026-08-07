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

Find the **class** first: how many other rows have the same shape? Report that number, then fix the
class rather than the instance.

**Test the counter-case before believing the rule.** Every over-general rule in this project's
history was caught by a single example: `名` in 君の名は, `V` in Vチューバー, kun-yomi for names.
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
- a check whose pattern never matched anything reports clean, which is indistinguishable from a
  check that ran and found nothing. `git grep` with a stray `--` and a lint parsing output on a
  separator that had changed both did this in one session

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
prefabricated constructions. Those constructions are bad writing on their own merits: a sentence
spent saying nothing, an abstraction where a fact belongs, rhythm in place of content. Identifying
their author is beside the point. Enough together and the text lands in the uncanny valley, where a reader feels
the wrongness before naming it and stops trusting the page.

The goal is prose worth reading. That the project is AI-driven is a plain fact of the repository,
neither hidden nor advertised, and attribution stays. Where a published list of AI tells and the
reader's experience disagree, follow the reader.

**Scope.** Anything a reader sees. The whole of any repository that goes public, existing text
included. Code comments and docstrings. Commit messages written from now on; those already written
are history, and the public development history is to be squashed before 1.0 in any case.

**What enforces it.** `check.py` holds the invariant for public prose, plus budgets for the backlog
in internal documents, which ship at 1.0 and need the same pass. The `commit-msg` hook applies the
same list to each new message and blocks, because a person is present who can reword a line. Where
the rules came from is recorded in `adapters/lint/tics.py`.

**The documentation is part of the deliverable.** The informational foundation and the architecture
ship in the repository so that a third party can pick the project up and run with it or change it.
Write for that person: someone competent who has never seen this before, is trying to do something
specific, and will not read the whole thing. It has to be worth a stranger's time.

**State what is, not what isn't.** "A catalogue rather than a reader" spends a sentence on what the
thing is not and leaves the reader still waiting. Say what it is; add the contrast later only where
it earns its place.

**Three is a figure, not a number.** Avoid it as an organising principle: three bullets, three
bold-led paragraphs, three parallel clauses, a sentence announcing that there are three of
something. When there really are three things, say them in prose or find the fourth that was being
left out to make the shape work.

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

## 12. Every module has a test that runs offline and can be shown to fail

`./test.py` is the whole of it. It discovers suites rather than being told about them, blocks the
network in every child, and `--canary` inverts every assertion to prove each suite is capable of
failing. It runs at pre-push and in both workflows.

**A new module ships with its test in the same commit.** `modules without a test` is a budget at
zero, so a module arriving without one blocks the push. That is the intended friction: a test
written a week later is written against the code rather than against the requirement.

**Offline is what enforces the factoring.** A module that cannot be tested without a network has
not separated its logic from its I/O, so the guard turns "well factored" from a judgement somebody
makes into a condition the machine checks. When a test wants the network, the answer is to split
the fetch from the logic and test the logic, or to add a fixture. It is never to relax the guard.

**A suite that passes while inverted is asserting nothing.** This is the failure this project meets
more than any other, and the tooling built to catch it had the bug itself: the first `--canary` run
reported nine suites healthy when one had been inverted. A suite must emit `CANARY-PROVEN`, and the
runner treats its absence as unproven rather than as success.

**Test what a bug did, not what the function does.** §8 already requires a check with every fix.
Prefer the counter-case: five of the nine お休み matches in the corpus are story titles, and pinning
those is worth more than pinning the four that are notices, because the rule was wrong in that
direction and will be again.

**A report is not a test.** `acceptance.py` printed coverage percentages and always exited zero, so
it counted as a suite while coverage could have fallen to zero unnoticed. If a file is collected as
a test it must assert something; if it cannot, it belongs somewhere the runner does not look.

**Fixtures live in the repository** and are small enough to read. A fixture nobody can read is a
fixture nobody can tell is wrong.

## 13. A register nothing reads is worse than no register

`adapters/kadokomi/confirm.py` wrote a list of works flagged on content grounds from the project's
first run, headed "Not published". Nothing read the file. Every work in it was live on the public
site, and no number anywhere said otherwise. The failure was not the policy, which was sound; it
was that a control existed on paper and could not be observed to be doing anything.

**A produced file must have a named consumer, in the same commit.** Writing a register and wiring
it up later is the same as not writing it, with the added cost that it reads as done.

**Prefer reporting to filtering.** A filter that silently drops rows is unobservable when it stops
working. A count in `run.json`, surfaced on `status.html` and asserted by `check.py`, fails loudly
when the number and the register disagree. `content flags are accounted for` is that check, and it
deliberately does NOT require flagged works to be withheld: it requires the register and the
published report to agree, because agreement is what failed.

**When you fix an exposure, check every surface separately.** Those five titles reached the public
site through six paths: the release feed, the works list, an archived month, `names.json`'s phrases
section, `run.json`'s claim trace and `meta.json`'s coverage list. Each was found only by looking
at the next one after the previous fix appeared to have worked. Check the DEPLOYED bytes by
substring; a field-shaped check missed five of the six.

**Write-once yields to content.** REQUIREMENTS §5 protects a published month from having its DATES
quietly revised. It is not a licence to keep serving a work that has been withheld. Where the two
conflict, content wins and the removal is printed rather than made silently.

## 14. What the platform guarantees, and what it does not

Every platform in this database is a commercial publisher's own web arm. A reader following a link
to a serialisation on one is not going to meet unwanted pornographic content, certainly not up
front, which is why a source's own content rating does not withhold anything by itself.

That guarantee is structural and it is worth stating because it can lapse. It rests on WHERE the
work is published rather than on any judgement about the work, so it holds only while every source
is a commercial publisher. **A new source that is not one changes the position**, and the flag
register plus its check is what makes that visible rather than assumed.

**ニコニコ漫画 is admitted, decided 2026-08-07.** It is the first source that is not purely one
publisher's web arm: it carries publisher channels and a section anybody can post to, and the
serialisation pass added 337 works from it. The reading above was that this changes the position,
so it was put to the operator and the answer was to admit them.

What that costs is precision in the sentence at the top of this section. The structural guarantee
now holds for every source except this one, and for this one it rests on what the pass actually
found: no adult imprint and no adult marking on any of the 362 works joined, so nothing reached
`data/source/editions/withheld.yaml`. That is a measurement and not a guarantee, and it has to be
taken again when the population grows.

A second source of mixed character would make this a rule with two exceptions, which is the point
at which the sentence at the top should be rewritten instead of qualified.
## 14a. An agent works in its own tree, on its own branch

Two sessions editing one working tree cost us most of a day. A commit staged by explicit path still
swept another session's half-finished line into it. A push was blocked for hours by a module the
other session had not finished testing. A gate read NO GO for reasons neither session had caused,
so neither could tell whether its own work was sound. A `git checkout` to undo a mistake was refused
by policy, correctly, because it would have destroyed work that was not the author's.

§16 exists because of those, and it is a rule about care. This is the rule that removes the need for
care: **give every agent its own worktree and its own branch, and integrate serially afterwards.**

```
git worktree add ../wt-<name> -b agent/<name>
```

**Place worktrees as SIBLINGS of the repositories**, at `Development/yuri/wt-<name>`, so that
`../yurarium.github.io` still resolves and `check.py`, `deploy.sh` and the tests all work with no
environment override. A worktree nested inside a repository breaks that path and is worth nothing.

The Agent tool's own `isolation: "worktree"` does not work here, because the directory the agents are
launched from is not itself a repository; the two repositories are its children. Create the worktree
by hand and name it in the agent's first line.

Two agents in two worktrees still land on one branch eventually, so a file both of them edit is a
conflict deferred and not avoided. Say in each brief which paths that agent owns and which are
read-only to it.

**Nobody pushes but the integrator.** An agent commits to its branch and stops. Merging one branch
at a time is what makes a red gate attributable: it belongs to the branch being merged. Delete the
worktree once its branch is in, so a stale checkout cannot be worked in by mistake.

**A budget measured on a branch is true of that branch alone.** Budgets ratchet down on a green
run, so an isolated branch records what its own copy of the tree measures. `work/independent-checks`
ratcheted `stock phrasing in comments` to 891 against its own `check.py`; main measured 896 and had
before the branch existed. Taking the branch's figure across would have written a tightening nobody
achieved, and the next green run on main would have failed against it.

So a merge conflict in `docs/budgets.json` is not resolved by choosing a side. Take the union of the
keys, then RE-MEASURE by running the gate on the merge result, and record what it reports. The
smaller of two numbers is not the right answer either: each was measured against a different tree.

Two things follow. A budget whose name disappeared with the function behind it is dropped rather
than merged, or the file grows entries nothing computes. And a branch that renames a budget should
say so in its report, because the integrator is the only one who can see both names at once.

## 14b. A check must not share its subject's blind spot

`--self-test` proves a check CAN fail. It does not prove the check can fail on anything the pipeline
is able to produce, and those are different claims. A canary is planted directly into the context,
downstream of whatever filtered the data on its way there, so a check whose subject already removed
every failing case is canary-proven and reports nothing for the rest of its life.

Found by a reader, on a live page, with every gate green. `w01478` was credited
`田口ケンジ / タグチケンジ`, a name beside its own reading, which is the exact class
`credits.dedupe` collapses. It survived because neither name is in the name store, so there was
nothing to compare. The budget counting that class does the same store lookup, so it read 0. **The
measure was blind in precisely the places the fix was blind**, and a check that shares its subject's
assumption cannot report its subject's failures.

Three shapes, all present in this repository when this was written:

**The subject filters on the function the check verifies with.** `build.py` drops any furigana span
set that `kana.ruby_spells` rejects, and `ruby spells the reading` verifies with `kana.ruby_spells`.
Nothing that reaches the check can fail it. It guards that the filter still runs, which has value,
and it detects no wrong ruby ever.

**The subject enforces the exact condition the check tests.** `build.py` moves a row's first date
back to its earliest volume, and `first date precedes its editions` tests whether a row's first date
precedes its earliest volume. True by construction.

**The check and the subject share a table, a regex or a lookup.** `credits that are not people` and
`credits.is_a_person` each carry a copy of one regex. They had already drifted: the copy in the
check does not recognise `第3話` and the copy in the adapter does, so the check under-reports what
the adapter is catching, and neither number means what it says. §3 covers this, and the drift is the
smaller half of the problem.

**What to do instead.** Measure the OUTPUT against something the producer never consulted.
`implausible ruby spans` is the shape to copy: it counts runs holding fewer kana than they have
kanji, which is arithmetic on the rendered result, owes nothing to the aligner, and caught 30 real
faults the aligner was content with. Where a check must reuse the subject's code, say so in its
docstring and name what it therefore cannot see.

## 15. Layout changes ask what kind of control it is

Every control in the interface falls into one of the kinds below, and which one decides where it
sits, how it persists, and whether Back undoes it. Ask before moving anything.

**Selects a body of data.** The tab, the period, an individual record. This is navigation: it goes
near the top, it pushes a history entry, and it belongs in the URL so it can be linked to.

**Narrows the current body.** Platform, kind, access, the search box. A filter. It sits with the
other filters, and today it stays out of history because pushing on every adjustment makes leaving
the site take a dozen presses.

**Changes how the same data looks.** Language, theme, romanisation, furigana, compact against
detailed. A preference. It is persisted, it is never in history, and Back must never alter it.

**Leaves the site.** A link to a chapter on the publisher's platform. The browser already gives
this history for free, and it is worth naming because it is the one case needing no work: the
reader expects Back, and Back does the right thing without us.

This is the same split that fixed the control bar when the dropdowns read "content, content,
presentation, content", and the same one that decides what a reader can share a link to. `docs/FEATURES-INTERFACE.md` carries the detail, including why the URL must be read before
the saved view is restored.


## 16. The working tree may not be yours alone

Assume another session is editing this checkout. On 2026-08-06 five were, and two of them reached
for `git stash` to get a clean baseline and swept up twenty files of somebody else's uncommitted
work. Both restored it and verified it byte for byte, and both were right to report it, but neither
needed to take the risk.

**Never run a command that discards or moves work you did not write.** `git stash`, `git reset
--hard`, `git checkout -- <path>` and `git clean` all operate on the whole tree or on files by name,
and none of them can tell your changes from anyone else's. Reverting one file cost an hour of
uncommitted work in this repository the same day, so this is not only about agents.

**To read a baseline, read it. Do not create one by mutation.**

```
git show HEAD:build.py                  the committed version, without touching the tree
git show HEAD:build.py > /tmp/base.py   when a tool needs a path
git diff --stat -- adapters/            what changed, without changing anything
```

**Stage by path and commit only what you touched.** `git add -A` in a shared tree commits work you
have not read, which is how a half-finished change from another session reaches the history under
your message. Name your files:

```
git add adapters/thing.py adapters/test_thing.py docs/GAPS.md
```

**A gate that fails on somebody else's file is not your failure.** `./check.py --gate` and the prose
lint read the whole tree, so a parallel run's uncommitted edits will fail your gate. Establish that
by linting the specific files you touched, say so, and do not fix another session's work to make
your own commit pass. `--no-verify` is available for exactly this and the reason belongs in the
commit message.

**Do not push.** Pushing publishes whatever the tree holds and starts a build. That decision belongs
to whoever is coordinating the session.
