# Launch plan

Written 2026-10-15 after a sweep of what runs and what does not, and an interview with the owner.
It replaces the ad hoc daily "trigger the update and perform routine maintenance" loop with a
system that keeps itself current, and ends with the site public.

## What the sweep found

The site has been kept current by hand. The update workflow has no schedule: it was commented out
in August pending one watched run and never switched on, so every run since was dispatched from an
interactive session. Beyond that:

- **The print side has no regular route at all.** BOOK☆WALKER, MADB and 一迅社 records, 2,951
  files, were all last read between 2026-08-05 and 2026-08-08. A new volume of a held work, or a new
  print work, can only enter by hand. The 一迅社 producer exists only on the unmerged branch
  `work/ichijinsha`, and the MADB routes read a release pinned at 1.2.18.
- **About fifteen producers whose output the build reads have run once and never again**, the same
  shape as comicブースト, the BOOK☆WALKER completion sweep and the render targets fixed this month:
  `comparators/claims.py`, `comparators/completion.py`, `shopfinal.py`, `magapoke.py` lengths,
  `kadokomi/catalogue.py`, `kadokomi/confirm.py`, `gigaviewer/confirm.py`, the serialisation
  sweep, confirm and promote chain, `ndl_volumes.py`, `bylines.py`, `backfill/fields.py`,
  `claims/trace.py`, and `madb/by_shop_query.py`, whose input queue CI refreshes daily and nothing
  drains. Four consumed files have no producer in the tree at all: `claim-targets.yaml`,
  `remaining.yaml`, `cmoa-completion.yaml` and `series-lengths.yaml`.
- **Eight GigaViewer platforms** in `adapters/gigaviewer/platforms.yaml` get no series-feeds run,
  and コミックリュウ's files have not changed since 2026-09-15 while the adapter exits 0.
- **CI writes `data/state/checks.yaml` and never commits it**, so the build reads the August copy.
- **Two frozen BOOK☆WALKER completion files are read after the fresh one** and can override it.
- **Stage C runs under `bash -e`**, so one failing render step silently skips the rest; Stage 0 and
  two post-compile steps report nothing when they fail alone.
- **Most hand work was budgets rising by design.** Of 21 acceptances since September, the most
  frequent were `incomplete attested rows` (11), `author readings no source states` (9),
  `author names romanised as one word` (8), `credit fields an identifier does not cover` (7),
  `updates naming a work we do not hold` (6) and `announced works the corpus does not hold` (4).
  Each moves with every new work or author, so each arrival produced a "failure" that a person
  then waved through.
- **Red runs and their emails** came from two causes: an adapter crash failing the whole update
  (2026-10-11), and site builds racing to push. The site race is fixed (one build at a time).

## Decisions taken

| Question | Decision |
|---|---|
| Print intake | Weekly, automated, bounded per run |
| Update cadence | Twice a day, 00:37 and 12:07 JST |
| Names and induction | A Claude Code job in GitHub Actions on the owner's Pro subscription token, after every update; names researched as now, unmarked as now |
| Usage audit | Every job run logs turns, tokens and duration; a running total on the status page |
| Persistent failures | An auto-managed GitHub issue per failing source, a status-page section and a weekly digest |
| Bad data | Quarantine the offending rows or source, publish the rest, raise an issue |
| Code fixes | The owner starts a session; the job does not change code |
| Going public | Serve at the site root without the 仮 label, and allow search indexing |
| Go-live bar | The owner decides after a week of autonomous running |

## The work, in order

### 1. Everything that should run, runs, by construction

#### A producer manifest

One file, `adapters/producers.yaml`, lists every producer: its command, its
cadence (every run, daily, weekly), the files it writes and how old each may get. The stage runner
reads it; `update.yml` stops listing commands inline. Two checks make a missed producer impossible
to merge rather than easy to find later:

- every `data/source`, `data/coverage` and `data/queue` path the build or an adapter reads is
  written by a producer in the manifest, or is marked hand-curated with a reason (a static scan of
  the paths and globs the code opens, so a new reader without a producer fails the test);
- every output's `retrieved:` date is within its cadence's limit, measured each run. A stale file is
  a finding that feeds the failure issues, so a producer that exits 0 and writes nothing, as
  コミックリュウ's does, is caught.

#### Wire or retire each frozen producer

Of the producers listed above, one whose output is still wanted
is put on a cadence with a bounded batch, as `bookwalker.py`'s `plan()` now does; a one-off whose
output is superseded (the slow and unknown BOOK☆WALKER files, `series-lengths.yaml` where episode
lists now answer) is retired along with its reader.

Done on 2026-10-15, taking the count from 21 to 10:

| producer | now | what running it found |
|---|---|---|
| comparator claims and 完結 tags | Stage 0, each run | dates read against the fetch, not the run; completion carries its claims forward |
| カドコミ catalogue | Stage 0, daily | 350 works became 365 |
| カドコミ and GigaViewer confirmation | Stage 0, each run | earlier confirmations kept and asked again; 8 GigaViewer works became 20 |
| マガポケ lengths | post, weekly | kept as the cross-check on the full series feeds |
| claim tracing | post, each run | the compile writes `claims-open.json` for it, since `run.json` is no longer written |
| bylines | post, weekly | a failed fetch no longer caches, nor drops a credit it read before |
| remaining works | Stage C, each run | derived from the candidates by `remaining/targets.py`; 70 hand-listed became 100 |
| field backfill | post, each run | reads the store's `incomplete attested rows` and keeps what it filled; 16 works on its first run |
| `claim-targets.yaml` | retired | the build's scope and the sitemap read the candidate list |
| BOOK☆WALKER slow and unknown | retired | their fourteen answers folded into the main file |

COMICリュウ was not a stuck producer: it left GigaViewer for comici as COMICリュウライブ around
2026-09-16, and is read through `webpages/sites.yaml` now. マガジンデビュー, パイコミックス and 栞 were never GigaViewer
installs at all (their `/atom` is a WordPress feed) and are disabled beside it. What remains frozen is the print side
(section 2), the serialisation sweep and its seeds, the shop-query joins, and `cmoa-completion.yaml`,
which belongs with the コミックシーモア shelf.

#### One capture scaffold

Fetching through `net.py` with a cache, carrying over what a run did not
reach, the health threshold, the YAML writer and the end-of-run report are each written five or
more times across the adapters, which is how fixes reach some sources and not others: the date
serialisation bug that crashed カドコミ existed in one copy. They become one module that adapters
call, migrated platform by platform with each adapter's tests kept green, and a lint budget counting
adapters not yet on it that only falls.

#### Smaller fixes

Commit `data/state`. Give all GigaViewer platforms series feeds and episode
lists. Run Stage C's commands through the stage runner so one failure does not skip the rest.

### 2. Print intake, weekly

Wire the chains that built the print side in August: BOOK☆WALKER's 百合 shelf through
`shelfingest.py`, `recon/bookwalker_volumes.py` and `bwingest.py`; コミックシーモア's shelf through its
volume capture; MADB by ISBN and by platform ISBN, with the pinned release re-pinned on a schedule;
openBD and NDL enrichment; and the 一迅社 adapter brought over from its branch. Each runs weekly in
a bounded batch with carry-over, so a shop that is down for a week costs a week, not the corpus.
New volumes then reach the 発売 tab within about a week, and `bookwalker.py`'s "ask again on a new
volume" trigger starts to fire.

Running weekly since 2026-10-16 as `adapters/stage-print.yaml`. The first refresh of BOOK☆WALKER's
shelf found 136 rows it had not listed in August and brought in 83 new print works, which
`adapters/naming/mint.py` mints on their shop records with no person needed. The volume capture now
lists each unfinished series again every four weeks, oldest first, so a new volume of a held work
arrives. What is not done:

- コミックシーモア refused every request from here on 2026-10-15 (HTTP 503, home page included). The
  shelf producer it never had, `adapters/cmoa_shelf.py`, is written and scheduled, and a run will
  say whether CI reaches the shop. Its volume capture does not yet list a held work again.
- Of the reference sources, MADB needs its pinned release re-pinned before the joins by ISBN can
  run, and the NDL passes use a path its robots.txt disallows, so they stay stopped for the owner.

### 3. A run succeeds unless something unexpected broke

#### Outcome policy

An update goes red only for an orchestration fault: the store will not build,
a schema mismatch, a leaked path or secret, or an unhandled exception outside an adapter. A source
that fails, returns nothing or trips its health threshold is recorded and the run goes on, keeping
that source's last good capture.

#### Quarantine and publish

A hard check that fails on rows sets those rows aside (the store's
quarantine already exists for this) and publishes the rest, with the reason recorded where the
status page and the issues can read it.

#### Surfacing

A source-health ledger counts consecutive failures per source. After three, one
GitHub issue per source opens, updates each run with the latest error, and closes itself when the
source recovers. The status page lists failing and stale sources and for how long. A weekly digest
issue sums up collection failures, budget movements, quarantined rows, queue depths and the
Claude job's usage. The site build is dispatched by the pipeline after it publishes, with a check
afterwards that the served data carries the new store's stamp.

### 4. Checks that do not need a person to wave them through

Each budget is classified by what it measures. A regression measure, where a known good thing got
worse (an attested row losing its access state, a title losing its English), stays strict and
routes through quarantine and issues. An arrival queue, which rises with new works and authors by
design, counts arrivals apart from the backlog: arrivals are accepted automatically with a
generated reason in the run's record, and the finding is age, an item waiting longer than its limit
(an author unread for 30 days, a release-day row with no access state after 3 days). Anything that
is neither is published on the status page as a report, without a pass mark.

Where a rule can do the underlying work, it does: credit identifiers minted for new credits each
run, unheld-work rulings recorded automatically where an admission basis exists, and width variants
like ～ and 〜 folded where titles are compared, so they stop needing aliases. The gate then blocks a
commit only on regressions, so the Claude job's commits are not stopped by arrivals it cannot help.

### 5. The Claude job: names

A workflow runs after each update with Claude Code headless, authenticated by the owner's
subscription token (`CLAUDE_CODE_OAUTH_TOKEN`), so it draws on the Pro allowance and incurs no API
charges. Usage credits (overage) stay switched off.

- **Input.** `adapters/naming/items.py` writes up to a dozen titles still showing a romanisation
  nobody decided, each with its creator, platforms, the pages to read and up to three related
  titles already named.
- **Instructions.** `adapters/naming/PROMPT.md` is the system prompt: the four bases in order, the
  note, and when to decline. It carries nothing else about the project.
- **Bounds.** Claude runs in an empty directory with web search and fetch and no other tool, and
  answers in JSON against `adapters/naming/schema.json`. `adapters/naming/integrate.py` writes each
  answer into `data/names/curated.yaml` only if it passes the check a hand-written entry passes. The
  workflow applies the names, builds and runs the gate, and commits only a clean result, otherwise
  it leaves the batch in an issue.
- **Audit.** Each run appends its turns, fresh input, cache reads and writes, output tokens,
  duration, model and what it changed to `data/ledger/claude-usage.jsonl`, and the status page shows
  the running total.
- **Owner setup, once.** Run `claude setup-token`, add the token as a repository secret, and keep
  usage credits off on claude.ai.

Induction moved out of the job on 2026-10-16. The first run gave Claude the whole repository and
spent 2.5 million input tokens on thirteen names and one induction, nearly all of it the same
context re-read every turn. Minting is bookkeeping, so the update does it:
`adapters/naming/mint.py` for print works, `adapters/naming/induct.py` for web works, which holds
back any whose title matches a work we hold, or which starts like one by the same author. Inclusion
rulings for works the feed names without a record are not automated; they stay counted by
`updates naming a work we do not hold`.

### 6. The rest of what the daily loop did, and where it goes

| Done by hand until now | New home |
|---|---|
| Triggering the update | The schedule, twice a day |
| Checking the site deployed and serves the new data | The post-deploy stamp check, raising an issue on mismatch |
| Accepting budget rises | Section 4; arrivals accept themselves |
| Inducting works, writing English titles | The Claude job |
| Ruling on unheld works | Automatic where a basis exists, otherwise the Claude job |
| Re-running a site build after a race | Gone: builds queue and the pipeline dispatches |
| Writing BUDGET-QUEUE reasons | Generated into the run record and the weekly digest |
| Diagnosing a broken source | The failure issue; the owner starts a session to fix code |
| Recording design gaps in GAPS.md | Stays with sessions; the digest links new findings |

### 7. Going public

Move the site from `/kari/` to the root with redirects from every published `/kari/` address
(work, credit and publisher pages included), drop the 仮 label, and allow indexing: remove noindex,
add `robots.txt` and a sitemap. Rehearsed on a branch before the switch.

### 8. The burn-in week

Starts once sections 1 to 5 are merged and the first scheduled runs are green. For seven days nobody
commits to keep it running. The daily digest records each run, each failure issue, the Claude job's
output and usage, and data freshness. At the end the owner decides whether to go public.

## Order and size

1. Schedule and outcome policy (sections 3, outcome and surfacing), so the system can run unwatched.
2. Producer manifest and the frozen producers (section 1).
3. Budget reclassification (section 4).
4. The Claude job (section 5), once the owner's token is in place.
5. Print intake (section 2).
6. Capture scaffold migration (section 1), continuing during burn-in where it does not touch
   behaviour.
7. Burn-in (section 8), then going public (section 7).
