# Refactor plan

Agreed with the project owner on 2026-08-09, after a decision-by-decision discussion. Nothing here
is executed until a stage is explicitly started. Progress is tracked in a published web artefact
whose unit is the extracted library.

## Why

Two independent causes, both measured.

**The loop is slow.** `./build.py` takes 93.9 s and `./test.py` takes 62.3 s, about 50 s of which is
`check.py --self-test`. An edit-to-verify cycle is therefore 3 to 4 minutes before a deploy. That
cost makes an agent batch changes, batched changes entangle failures, and entangled failures are
where "green on the branch, red on the merge" comes from.

**One fact keeps having two producers.** Twelve faults in a single working session shared one shape:

| fault | the two producers |
|---|---|
| an edition kept its catalogued title | `work_alias` reached from the web path and not the print path |
| organisation names unswept | `entities.RULED` written, `entities.py --apply` never run |
| a credit split against its ruling | `_recompose_credit` called `split_authors` without `ruled` |
| an interpunct divided twice | `enFallback` split a ・ the store had already ruled on |
| a reading's standing drifted | `check.STATES_A_READING` copied `curate.READING_ATTRIBUTION` |
| a division's standing drifted | `check.DIVIDED_BY_ITS_SOURCE` held a hand-written tuple |
| a note drifted from its twin | `SHAPE_NOTE` in `app.js` and in `pages.py` |
| a division lived in prose | `reading_note` said it, `reading_boundary` was empty on 293 records |
| a person had two romanisations | `phrases` and `authors[].romaji` |
| a whole route went unchecked | `creditLine` absent from the surface table |
| a byline lost its links | `linkedCredits` used `indexOf`, `creditText` used `foldSpans` |
| a spelling froze | a role bracket made `_recompose_credit` return the old phrase |

STANDING-INSTRUCTIONS §3 states the rule these break. Twelve breaches say the rule needs structure
behind it.

## The ten decisions

1. **Stage one is storage-independent.** Parallelise the 140 suites, split the gate so editing runs
   a cheap subset while commit and push keep the full one, canary-prove only the checks that
   changed, and reuse one Node process. Measure two things: what fraction of `build.py` is YAML
   parsing, and the stage dependency graph. Hold the hash-keyed incremental build until after the
   storage decision, because if parsing dominates then storage is the speed lever and an
   incremental layer over YAML solves around a problem we are about to delete.

2. **The store splits by who writes it.** Roughly 5 M is machine state (`titles.yaml` 2.4 M,
   `authors.yaml` 1.6 M, `phrases.yaml` 640 K, `attempts.yaml` 416 K, `publishers.yaml` 160 K).
   Roughly 180 K is hand-authored rulings (`credit-rulings`, `imprints`, `publishers`,
   `work-aliases`, `interpunct-rulings`, `distinct-titles`). `curated.yaml` at 2.1 M is mixed and is
   split so the human decision and its reasoning stay reviewable while the applied result becomes
   derived. The rulings stay YAML in git. They are what a reviewer reads and what the history is for.

3. **SQLite is a derived cache and never a source of truth.** It is rebuilt from committed inputs,
   and deleting it costs nothing but time.

4. **Reproducibility is bought by archiving matched constructions.** A reading's evidence is its URL,
   its retrieval date and the field as printed, which for NDL is the heading string. The whole page
   is not stored. This follows the ruling already in force for a shop's あらすじ: record the date and
   the matched construction. It keeps copyrighted expression out of a public repository and costs a
   few hundred kilobytes. The trade is stated openly: the INFERENCE becomes replayable and the
   EXTRACTION does not, so a parsing fault still requires a fetch.

   This is a prerequisite for decision 3. Today `data/names/` is both derived and authoritative:
   67 Wikidata readings and 256 NDL headings exist only as conclusions, and a rebuild from
   `data/source` would lose them.

5. **`data/build` stops being committed.** Measured: `deploy.sh` copies everything except
   `feed.json` (2.4 M), `titles.json` (128 K) and `ledger.json` (4 K), and all three are derived. The
   site repository's `kari/data` history already is the published snapshot, holding the exact bytes
   readers were served. One consequence to write down: `titles.json` is read by adapters, so a fresh
   clone must build once before it can fetch.

6. **Facts inside, stages outside.** Pipeline stages stay as orchestration. Every fact gets one
   owning module with a single public entry point, extracted serially so the pipeline keeps running
   throughout. A fact is anything two places can disagree about. Where a fact has a fuzzy edge, it
   belongs to whoever can DECIDE it, and everyone else consumes the decision: the interpunct rule
   decides whether a credit field names one person, so it belongs to `credit` and supplies evidence
   to `division`. Checks about a fact live in that fact's module and are discovered, the way
   `test.py` already discovers suites. An import lint proves nothing outside a module names its
   internals, using the technique `adapters/lint/entrypoints.py` already demonstrates.

7. **`romanisation` first, `division` second.** `romanisation` is close to a pure function,
   exhaustively testable offline, and carries real known faults, so it proves the machinery where
   failure is cheap to diagnose. `division` holds the most value and the most entanglement, and it
   goes second with tooling that already works.

8. **Description and justification are separated in comments.** A comment saying what code does is
   free. A comment saying why it is correct is a claim: it carries its evidence and is falsifiable.
   Where a comment asserts never, always or unreachable, it names the test that proves it or it is
   deleted. Three comments in one session confidently justified behaviour that was wrong, including
   `enFallback`'s "should be unreachable" while readers were shown `????`. A confident wrong comment
   calcifies harder than a test, because a test says this happens and a comment says this is right,
   which stops the next reader looking.

9. **The tracker's unit is the library**, with the seven extraction steps as sub-tasks, a standing
   inventory of every fact marked owned or unowned, and per-stage budget movements in both
   directions.

10. **The interface splits into modules and the checks evaluate the modules.** The bundle is verified
    by derivation, with an invariant that it hashes to a build of the checked sources, which is the
    shape `deployed data matches built` already has. Tree-shaking is off: `app.js` dispatches through
    string-keyed maps (`EV_HOLDS`, `SSTATE`, `VIS_LABEL`, `PLAT_EN`) and a renderer reached only by
    key is invisible to static analysis, which is the same class as `creditLine` missing from the
    surface table. Two harnesses that can disagree is a new fact with two producers, so there is one.

## The extraction protocol

Seven steps, applied to one library at a time. A library is done when the import lint passes and
nothing outside it names the fact.

1. **Enumerate every site holding a piece of the fact**, by search and not by memory.
2. **Read them critically.** Assertions in comments are promoted to tests or deleted. An assertion
   that survives becomes a test with its evidence attached.
3. **Write the public surface and its tests first**, including counter-cases already pinned.
4. **Move implementations in, one call site at a time**, keeping the pipeline green.
5. **Move the checks in and delete the copies.** Prove each canary still fires.
6. **Add the import lint in the same commit as the last call-site move**, so the window in which two
   producers exist is one commit.
7. **Write `BLINDSPOT.md`**, stating what the module cannot see. A module that cannot say what it
   does not see is unfinished. Two unstated blind spots hid real faults this session: `creditLine`
   was not a surface, and `a division cites its source` tested only kana surfaces.

Extraction is expected to surface disagreements that nothing currently compares. Those get a budget,
counted and named, so an extraction stays bounded instead of becoming open-ended debugging.

## Fact inventory

The tracker carries this and keeps it current. Initial reading:

| fact | owner today | state |
|---|---|---|
| romanisation | `kana.py`, plus the floor in `romfloor.py` and `app.js` | unowned, first to extract |
| division | `boundary`, `ndl_heading`, `openbd_reading`, `analyser_division`, `curate`, `check`, `store`, `build`, `app.js` | unowned, three basis vocabularies |
| credit | `inputs.split_credits_detail`, `credits`, `creditline`, `interpunct`, `app.js` | unowned |
| reading | `provenance`, `curate.READING_ATTRIBUTION`, six naming passes | unowned |
| title cataloguing | `isbd.py` | close to owned, one reader already |
| imprint | `imprints.py` | close to owned |
| work identity | `identity.py`, `credit_identity.py` | partly owned |
| dates | `build.py`, several adapters | unowned |
| inclusion | DEFINITIONS plus `classify/` | unowned |
| rendering surfaces | `interface.py` hand-kept table | unowned, and known to lag |

## Other angles folded in

- **Surfaces are derived, not listed.** A hand-maintained table of what to check will always lag what
  the renderer does. `creditLine` was missing and a reader saw `????`.
- **A budget must not depend on which tree you stand in.** `stock phrasing in comments` counted a
  gitignored file and read 903 in one tree and 898 in another, so a branch ratcheted honestly and
  the merge undid it. Every measure reading the filesystem needs the same audit.
- **Ratcheting becomes an explicit act.** `build.py` runs `check.py --runtime`, which ratchets
  budgets down, and twice in one session that banked a number measured over a half-migrated store.
- **Merge-result measurement is automated.** §14a is currently a person remembering.
- **`deploy.sh` uses `cp`**, which adds and overwrites and never removes, so a file the build stops
  producing lingers in the deployed tree. It also copies `checks.json` twice.

## What done looks like

The inner loop runs in single-digit seconds. Every fact has one owner and an import lint proving it.
Every module states its blind spot. A rebuild from a fresh clone reproduces the database from
committed inputs. The published snapshot is the site repository's history and nothing else claims to
be one.
