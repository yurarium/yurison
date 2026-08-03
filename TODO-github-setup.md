# Finishing the GitHub setup — parked

The pipeline side is written and tested locally. What remains is the part that needs decisions in
the GitHub UI, plus one real piece of engineering. Parked deliberately: interface work is easier to
iterate on when nothing is pushing to the same repos underneath it.

**Status 2026-08-03.** The first real run happened: `workflow_dispatch` with `skip_browser`. Stage
0, Stage A, compile, the invariants, the self-test, the unit tests and the field audit all passed.
It failed closed at *Assert the commit identity* and committed nothing — the workflow set
`yurarium-bot <noreply@yurarium.github.io>` while `.githooks/leak-guard.sh` permits exactly one
author string. Fixed by making CI use the permitted identity rather than widening the allowlist.

`SITE_DEPLOY_KEY` is still absent, so section A below is still outstanding and the publish step
will skip. Until that exists, a scheduled run would update `yurison` and leave the site untouched.

**Nothing here fires on its own.** `.github/workflows/update.yml` is `workflow_dispatch` only — the
`schedule:` block is commented out. Until someone uncomments it or clicks Run workflow, no
automated run touches either repo. That is the state to leave it in while the interface is moving.

---

## A. Credentials — GitHub UI, ~10 minutes

1. Generate a keypair:
   `ssh-keygen -t ed25519 -N "" -C "yurarium-ci" -f /tmp/ci_key`
2. Public half (`/tmp/ci_key.pub`) → `yurarium.github.io` → Settings → Deploy keys → Add deploy key.
   **Tick "Allow write access".**
3. Private half (`/tmp/ci_key`) → `yurison` → Settings → Secrets and variables → Actions → new
   secret `SITE_DEPLOY_KEY`.
4. Delete both local copies.
5. Confirm `LEAK_DENY` is already set in `yurison` secrets — the existing `leak-guard.yml` requires
   it and fails closed without it.

Without `SITE_DEPLOY_KEY` the workflow still builds and commits to `yurison`; it warns and skips
publishing. That is a usable half-state for the first run.

## B. First run — one click, then read the diff

Actions → update → Run workflow, with **skip_browser ticked**. That exercises Stage 0, A and D in
about ten minutes without the 45-minute browser stage, and it is the run most likely to expose a
wrong flag or a missing input file.

Then read the commit it produced. Specifically:

- `data/ledger/first-seen.yaml` — should gain entries, not rewrite existing ones. If existing dates
  moved, the lock is broken again and everything downstream of §5 is wrong.
- `data/source/` diffs should be small. Large diffs on unchanged content mean an adapter lost its
  output ordering, which turns every future commit into a full-file rewrite.
- The field-audit step's printed count. It was 0 incomplete when this was written.

Then run it again **without** skip_browser and confirm Chrome is present on the runner.

## C. Turn on the schedule

Uncomment the `schedule:` block. Daily at 20:17 UTC — off the hour, because everything cron'd at
:00 queues behind everyone else's jobs.

Watch the first three scheduled runs before trusting it.

## D. The one real engineering task left

`data/source/webpages/magapoke-deep.yaml` holds nine chapters' access states collected by pressing
もっと見る in a browser. `--headless --dump-dom` cannot press anything, so nothing refreshes it. It
is a static snapshot that will quietly age.

Two honest options:

1. **Drive that pass with Playwright.** Real dependency (a package plus a browser download), but it
   makes the deep list refreshable and would also let コロコロ's list load properly. ~half a day.
2. **Accept the limit.** Only each work's newest ~20 chapters get an access state automatically.
   Defensible — access matters most for recent chapters — but then those nine rows need marking as
   a fixed snapshot so nobody reads them as live.

Option 2 costs nothing and needs doing either way, because right now the file implies it is
maintained and it is not.

## E. Smaller things worth doing at some point

- **Mirror the repo off GitHub.** `yurison`'s history is the sole copy of the record; the ledger and
  the withdrawn-at-source history exist nowhere else. A periodic clone somewhere is cheap insurance.
- **Cache eviction.** `actions/cache` evicts after 7 days unused and caps at 10 GB per repo. The
  render cache is ~34 MB, so this is not a problem now, only something that would silently make
  Stage C slow rather than fail.
- **`--limit-per-host 140`** is doing real work — the default 40 silently capped pixivコミック at 40
  of its 131 works for as long as that platform has been rendered. Worth a comment in
  `render-targets.yaml` so it is not "tidied" back to the default.

## F. Decisions still open

- Whether the `identity-config` assertion in `update.yml` earns its place, given the workflow sets
  the bot identity two lines above it. It is one line and guards a real (if unlikely) future edit;
  it is also arguably redundant.
- Whether to keep committing `data/build/` to `yurison`. It is regenerable from `data/source/` by
  definition, so it is ~1.7 MB of churn per run buying only the ability to see the compiled diff.
  Keeping it makes bad runs obvious; dropping it makes the repo smaller.
