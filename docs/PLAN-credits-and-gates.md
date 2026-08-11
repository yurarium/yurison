# Credit rendering, credit search, and where each gate runs

Agreed with the project owner 2026-08-11. Progress is marked here and nowhere else.

The three items left open when `agent/roles` merged, plus the gate split they depend on. Read
[STANDING-INSTRUCTIONS](STANDING-INSTRUCTIONS.md) first; §3 (one producer) and §14a (one worktree
per agent) are what most of this is about.

## What the measurement changed

The search move was blocked on "187 spellings have no identifier, and minting publishes addresses",
which is the owner's call. Measured on 2026-08-11 against the shipped files:

| | |
|---|---|
| Index-row credits unresolved against shipped `credits.json` | 257 |
| The registry ON DISK already knows, as anchors or retired spellings | 70 |
| Genuinely absent from the registry | 187 |
| Of the 257, refused by `is_a_person` and the rest | 0 |

So 70 are people already ruled on, invisible only because `credits.json` ships surviving spellings
and drops the anchors: `4ka エンピツ`, `お子様ランチ`, `さりいB`. Shipping the anchors resolves them
with no minting at all, and shrinks the decision before it has to be made. None of the 257 is a
label, a format or a company, so the refusals strengthened on 2026-08-10 and 2026-08-11 have
already taken the dangerous cases out.

---

## 1. `gate.yml` runs on push to `main`, blocking. DONE 2026-08-11

`gate.yml` runs `test.py`, `--canary`, `build.py` and `check.py --gate`. Its trigger was
`branches-ignore: [main]`, reasoned as "main is what the unattended update commits to". Sound about
the bot and blind to the difference between the bot and a person: six code pushes to `main` on
2026-08-11 ran no tests and no gate, only `leak-guard`.

**No actor condition is needed.** A push authenticated with `GITHUB_TOKEN` does not trigger `on:
push` workflows, which `update.yml` already documents and which was verified: the update run's own
commit `4415905` triggered nothing, while every other commit that day triggered `leak-guard`.

## 2. Roles into `credit_parts`. DONE 2026-08-11

366 fields were given the roles their work record states, and 90 shipped fields now show at least
one. 裏世界ピクニック reads `Miyazawa Iori (story) / Mizuno Eita (art) / shirakaba (character
design)`. Joined from `credits` by name, so the answer is carried across rather than derived twice;
position would agree until a source lists the same people in another order.

What it was: roles rendered where they sat in the field text and not where the build had them
structured, so 裏世界ピクニック read `Miyazawa Iori / Mizuno Eita / shirakaba` while its record held
原作 / 作画 / キャラクター原案. `credit_parts` shipped `{"p": [{"n": …}], "j": " / "}` and now carries
`r` per person. It needed no identifiers and no search change, which is why bundling it with the
search move was wrong.

## 3. The byline fallback. DONE 2026-08-11

`creditGapText` drops a bracket left empty by a role that elided, and spaces a rendered gap so two
names cannot run together. All 2,611 shipped fields re-rendered afterwards: none malformed, none
changed.

What it was: where a field has no division record the interface walks the raw string in place, and
that walk took the role text out and left its punctuation. `[著]アンソロジー` rendered `[]Ansorojī`
and `ぐう(作画)水無瀬(原作)riritto` glued each name to the role before it. Prophylactic: no shipped
field reaches the walk, and a field shape the divider does not cover would, which is the ordinary
way this corpus grows.

## 4. Ship the anchors in `credits.json`. NOT STARTED

Each credit gains the spellings it answers for. Re-measure the 257 afterwards; it should fall by
about 70. Search by any spelling the registry unifies is impossible until this lands.

## 5. Decide minting on the re-measured number. NOT STARTED, owner's call

Recommendation: mint for the remainder. They are people the corpus credits, and a registry
population narrower than the corpus is two answers to "who does this database know about". Two
conditions: mint only what passes the refusals as they stand, and count identifiers minted from
catalogue rows alone in a budget, so a population change is visible rather than silent.

**Do not mint before step 4.** It would create second identifiers for the 70 people who already
have one, which is the fault the merge and interpunct machinery exists to prevent, and a published
address is expensive to withdraw: `アンソロジー` cost a ruling, a vocabulary and a change to
`_withdraw` on 2026-08-11.

## 6. Move search onto the registry. NOT STARTED

`index[].c` becomes identifiers and a query resolves through the registry to `works[]`.

**The safety property that makes it non-regressive**: a row with an unresolved credit KEEPS its raw
string in the search index. Search then strictly gains, and step 6 stops depending on step 5
reaching zero.

---

## The tension steps 1 and 5 sit either side of

Nine of the twelve budgets re-measured on 2026-08-11 rose from data the update run fetched, not
from code. Under a blocking gate on `main`, a data drift can block a code push. The clean answer is
that `gate.yml` blocks on the code and reports the data budgets, which is the same separation §B3
argues for one level down. Recorded here because it is a design question and not a defect, and
because it will be met the first time a data budget moves under the new trigger.

---

## B2 and B3, the separation the tension above predicted. DONE 2026-08-11

**B3, which tier blocks.** `check.py --data-advisory` splits the verdict on `SOURCE_BUDGETS`, the
set that already declared which budgets count this repository's own Python and Markdown. Those
block; the ones counting the data report. Invariants are not in the split, because a violated
invariant is a broken statement whoever caused it, and neither is a budget that could not be
measured, which says a check failed to run rather than that a count moved. `gate.yml` passes the
flag; `./check.py --gate` by hand still blocks on everything, which is where accepting a rise
belongs.

The tension above is what this answers, and it was not theoretical: five budgets rose on 2026-08-11
from data the update run had fetched, and each stopped a commit that was about code.

**B3, the unit tests are out of the update run.** That job fetches data and does not change code.
`./test.py` and `--canary` prove the tree is sound, `gate.yml` already blocked on that tree at
check-in, and nothing between then and now can have altered it. Four minutes a night to re-answer a
settled question, in a job where a failure withholds the data. A flake in a test about credit
splitting could have cost a day of releases that were fetched perfectly well.

`check.py --self-test` STAYS, and the distinction is the point. Its canaries are planted in a
context built from today's corpus, so it asks whether the checks can still fail against the data
that has just arrived. A check goes vacuous when the data changes shape under it, and the check-in
gate cannot see that because it runs against yesterday's corpus.

**B2, one adapter must not cost the night.** All thirteen Stage A commands are required and
`run_stage.py` returns 1 if any fails, which stopped the job before the compile: one publisher
changing a feed's shape withheld the other twelve platforms' updates too.

Shaped by the owner's rule that partially processing new information is an acceptable failure and
publishing a site with existing information missing is not. An adapter that fails writes nothing, so
its source file keeps every row it had and the compile publishes that platform as it stood: nothing
is lost, only not gained. A partial WRITE is the other half and is already covered, by
`capturegap.py`, which joins the targets a pass was given against the rows it wrote and owes the
pass's own counters nothing.

It is not swallowed. The failing adapter and its stderr are named, the step goes red, the source's
`age_days` climbs on the status page, and a final step fails the job AFTER the publish rather than
instead of it. Publishing first is the rule; going red is how anybody learns a platform stopped
answering.
