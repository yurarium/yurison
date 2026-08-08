# Running the steady state on GitHub Actions

The pipeline is a scheduled job that fetches public bibliographic metadata, compiles it, and pushes
the compiled artefacts to the site repo. Nothing it does needs credentials to the sources, and
nothing it stores is page content.

## 0. Position

This is a bibliographic index: titles, authors, chapter names, dates, access states and links. No
page images, no synopsis text beyond what identifies a work, and a cover-host allowlist that fails
the build if anything else appears. That is the basis on which this runs at all, and it is why the
answer to "is this fair" does not depend on any particular platform's posture. Keep it true: the
moment the build starts holding content rather than references to content, the position changes.

Requests are paced 1.0–1.5 s per adapter and every adapter sends a User-Agent naming the project
and its URL. Routes were chosen at survey time to use paths the sites publish for reading —
adapters/kadokomi/ specifically routes around a `/api/` its robots disallows, in favour of the
per-work pages. There is deliberately **no** per-run re-scan of access rules.

## 1. Which repo runs it

`yurison` — the private pipeline repo. Not the Pages repo.

This matters beyond tidiness. GitHub's Additional Product Terms restrict Actions to "the
production, testing, deployment, or publication of the software project associated with the
repository where GitHub Actions are used". In `yurison` the pipeline *is* the project and the build
is its output, which is the ordinary case. Running the same job out of `yurarium.github.io`, where
the project is a static site, would be using Actions as unrelated compute.

So: build in `yurison`, push artefacts to `yurarium.github.io`.

## 2. What the runner needs

| need | how |
|---|---|
| Python 3 + PyYAML | `actions/setup-python`, `pip install pyyaml` |
| Chromium | preinstalled on `ubuntu-latest` as Google Chrome — **verify on first run** |
| Source credentials | none. Every adapter fetches public pages unauthenticated |
| Write access to the site repo | a deploy key or fine-grained PAT, repo secret |
| `LEAK_DENY` | already required by the existing leak-guard workflow |

Verify the browser before relying on it:

```bash
which google-chrome chromium chromium-browser || echo "none found"
```

If absent, add `browser-actions/setup-chrome` and append the resolved path to the `CHROME` probe
list at the top of `adapters/render/releases.py`, which already tries four locations.

## 2a. Letting CI commit

Two different problems, because they need different credentials.

**`yurison` committing to itself.** `permissions: contents: write` in the workflow. `actions/checkout`
persists the auto-provisioned `GITHUB_TOKEN` and `git push` just works — nothing to create, rotate
or leak.

**`yurison` pushing to `yurarium.github.io`.** `GITHUB_TOKEN` is scoped to the repository running
the workflow, so it cannot reach another repo at all. Three ways across:

| | scope | attached to | expires |
|---|---|---|---|
| **deploy key** (used here) | exactly one repo | nothing | never |
| fine-grained PAT | selected repos | a user account | ≤1 year |
| GitHub App token | installed repos | an app | auto-rotates |

A deploy key is the right one here, and not only because it is narrowest: it attaches **no user
identity**. A PAT would tie every automated commit on a pseudonymous project back to an account,
which is the thing this repo's whole guard apparatus exists to prevent.

```
ssh-keygen -t ed25519 -N "" -C "yurarium-ci" -f /tmp/ci_key
```

Public half → `yurarium.github.io` → Settings → Deploy keys → Add, **tick "Allow write access"**.
Private half → `yurison` → Settings → Secrets → Actions → `SITE_DEPLOY_KEY`. Then delete both
local copies; the private half exists only in the secret from then on.

### What the guard does and does not need to cover here

**A push authenticated with `GITHUB_TOKEN` does not trigger `on: push` workflows** — GitHub
suppresses it so workflows cannot recurse — and `core.hooksPath` is per-clone local config, see
`.githooks/install.sh`, so a fresh CI checkout has no local hook either. Neither half of the guard
runs automatically on an automated commit.

For the **content** half that does not matter, and it is worth being precise about why rather than
adding a scan out of caution. The guard's content half looks for real-name strings. Nothing the
pipeline generates can contain one: `data/source`, `data/build`, `data/coverage` and `data/ledger`
hold titles, authors, chapter names, dates and URLs read off public sites. Measured, not assumed —
zero files under any of the four contain the local username or a home path, and the only matches
anywhere in the tree are the canaries planted inside the guard scripts themselves. The public repo
receives only the three `data/build` JSON files, so a slip would have to survive into those
specifically. The content guard stays where the risk actually is: human-authored commits, via the
existing `leak-guard.yml`.

The **identity** half is worth asserting, because it guards something the data cannot: who the
commit is authored by. `update.yml` sets the bot identity and runs `identity-config` before
committing. That is one cheap check against a future edit that made the run commit as
`github.actor`.

One useful consequence of the deploy key: because the site push is *not* `GITHUB_TOKEN`, it does
trigger the site repo's own `leak-guard.yml`, so the public repo keeps its server-side backstop
without this workflow doing anything.

## 3. Order of the run

Adapters write only into `data/source/` and `build.py` reads all of it, so they are mostly
independent — but not entirely, and the exception is easy to get backwards.

**Stage 0 — the work queue. Runs first; five adapters take its output as input.**

```
adapters/webcomics/coverage.py --out data/coverage --pages 8
    writes data/coverage/webcomics-works.yaml and webcomics-gap.yaml
```

Web漫画アンテナ is Tier C and stays that way: it may say a work exists and where, and nothing it
says becomes a record. What it produces here is the queue — which works to go and ask the platforms
about. `comicfuz`, `kadokomi`, `nicovideo`, `webpages` and `generic` all read one of those two files
and do nothing without it. Putting this in a later "reports" stage, which is where it looks like it
belongs, would leave those five adapters running against a queue up to a day stale — or on the
first run, against nothing at all.

**Stage A — feeds, APIs and server-rendered markup (no browser, most of the feed)**

```
adapters/gigaviewer/releases.py     --platforms …/platforms.yaml     platform-wide Atom
adapters/gigaviewer/series_feeds.py --platform <id>                  per-series Atom + free_only
                                                                     — per platform, 27 of them
adapters/comicfuz/releases.py       --gap   webcomics-gap.yaml
adapters/kadokomi/releases.py       --works webcomics-works.yaml
adapters/nicovideo/releases.py      --works webcomics-works.yaml
adapters/webpages/releases.py       --gap   webcomics-gap.yaml
adapters/generic/releases.py        --works webcomics-works.yaml --extract extract.yaml
adapters/ganganonline/releases.py   --targets render-targets.yaml   __NEXT_DATA__
adapters/yomonga/releases.py        --works adapters/yomonga/works.yaml
adapters/shogakukan/releases.py     --sites adapters/shogakukan/sites.yaml
adapters/sitemap/releases.py        --sites …/sites.yaml --works claim-targets.yaml
```

`series_feeds.py` takes `--platform`, singular, and must be looped over the 27 ids in
`platforms.yaml`. The per-series feed is a different endpoint from the platform-wide one and only
it carries `?free_only=1`, which is where per-chapter access comes from on every GigaViewer host.

**Stage B — comparators and enrichment (independent of A; order does not matter)**

```
adapters/comparators/claims.py    百合ナビ — the acceptance yardstick, never a record
adapters/yurinavi/*.py
adapters/openbd/enrich.py         volume-level dates, from openBD and MADB
adapters/madb/extract.py
```

`enrich.py` wants `--madb-cache <pinned MADB release>`. openBD is a publisher's own registration and
is thin for older books; the MADB index answers an ISBN openBD does not hold, at no request. The
pass prints how many dates each catalogue supplied, and it is correct for the MADB figure to read
nought while every ISBN-bearing record in the corpus is MADB's own, because the pass refuses to
write MADB's answer back over a record that came from MADB.

It wants no cache path. `names/openbd_reading.py` owns the location, at
`$YURI_CACHE/openbd-cache/openbd.json`, and the enrichment pass and the retailer captures all read
it through that module. Passing one used to be how the two halves diverged: the name pass filled
`names-cache/openbd.json`, this pass read `openbd-cache/openbd.json`, and on 2026-08-08 that cost
978 volumes their date for no reason except which file was opened. Pass `--fetch` and the run fills
the shared file itself, asking only about ISBNs it has no answer for.

That file holds openBD's silences as well as its records, each with the date it was established. An
ISBN nobody registered costs one request to discover and the answer is worth keeping, so it is
kept, and re-asked after ninety days because a publisher files a book eventually.

**Stage C — browser (slow, ~30 min, allowed to fail)**

```
adapters/render/releases.py --limit-per-host 140
adapters/remaining/releases.py
adapters/backfill/fields.py
```

**Stage D — compile and publish**

```
python3 build.py
./deploy.sh $SITE
```

## 4. Failure policy

`build.py` fails the run on a validation breach — a cover host outside the allowlist, or
pixivコミック present from two sources at once. Those must stay hard failures.

Everything else should degrade rather than abort. An adapter that returns nothing leaves the
previous run's `data/source/` file in place, and the build proceeds on it. This is the correct
behaviour for a source that is briefly down — マンガよもんが spent a stretch in maintenance and the
right response was to keep its last known rows, not to drop the platform.

Give Stage C `continue-on-error: true`. A browser flake should not cost the day's feed.

## 5. What to commit back

`data/source/` and `data/build/` in `yurison`, and the three JSON artefacts in the site repo. Commit
the sources, not just the build: they are the record, and the diff is how a bad run is spotted.

Use a bot identity and a message naming the run, so a scheduled commit is distinguishable from a
hand edit at a glance.

## 6. Schedule

Daily is right. The feed window is 60 days and most platforms update weekly, so hourly would be
pure load on the sources for no new rows. Effective dates are locked at first sighting (§5), so a
missed day is recovered by the next run rather than lost.

Pin `schedule:` off the hour — every scheduled workflow on GitHub fires at :00 and is queued.

## 7. Caching

`actions/cache` on the render cache directory, keyed by date. The render adapter reuses a cached
DOM for 2 days, so a cache hit turns Stage C from ~30 minutes into ~1. Cache is ~34 MB.

Do not cache `data/source/` — it is committed, and a stale cache silently shadowing a commit is a
class of bug with no symptom.

## 8. The thing that will break first

`adapters/render/` is the fragile part and it is fragile in a specific way: it reads class names and
DOM shapes that the platforms change without notice. When マガポケ renames `c-episode-item__ico--`,
this adapter does not fail — it returns rows with no access, and the build accepts them.

The guard is the field audit, which is in the build already. If attested rows missing a field goes
from 0 to some number, a selector has moved. Worth failing the run on: it is a two-line check and
it is the only thing standing between a silent selector change and a month of half-empty rows.

## 9. pixivコミック is on the browser route

The API adapter is retired. `data/source/pixivcomic/` is gone and `comic.pixiv.net` is back in
`render-targets.yaml`; `build.py` still refuses to run with both present, which is what keeps this
from drifting back by accident. The adapter code was moved to `../pixiv-api-adapter-retired/`
rather than deleted.

What the browser route gives, and what it does not:

- The episode list renders as `<a href="/viewer/stories/<id>">` blocks holding a label, a subtitle
  and `更新日: 2026年5月8日`. `episodes_pixiv()` in `adapters/render/` reads those. The generic
  strategies could not, because pixiv numbers chapters `1`, `2`, `3` and `CHAPTERISH` does not
  match a bare number — which is why this platform used to come back with a fraction of itself.
- **The rendered list contains exactly the episodes a signed-out reader can open.** Checked against
  four works whose per-episode access was independently known: 3 free of 18, 7 of 7, 1 of 42, 5 of
  10 — the anchor count matched the free count every time. So membership of that list is the access
  statement, the same way GigaViewer's `?free_only=1` feed is.
- It therefore **cannot see paid chapters at all**. The API returned 582 chapters across 123 works;
  the browser returns the free subset. For a feed that shows a 60-day window this costs less than
  it sounds, because a chapter that is paid today was usually free when it was new and was caught
  then — but it does mean pixiv's *history* is now the survival set, not the record. That
  distinction is already live for every GigaViewer platform.

Cost in runtime: 131 works at roughly 10 s each, so pixiv alone is most of Stage C. The render
cache is what makes this tolerable on repeat runs.

## 10. Known gap

`data/source/webpages/magapoke-deep.yaml` was collected by pressing もっと見る in a browser, which
`--headless --dump-dom` cannot do. It is a static snapshot of nine chapters' access states and
nothing in the pipeline refreshes it. Either drive that pass with Playwright or accept that only
each work's newest ~20 chapters get an access state automatically, and mark those rows stale-able
so they cannot rot unnoticed.

## 11. Merging two records that turn out to be one work

An address published once has to keep resolving. That is why a work's identifier is opaque and
minted in `adapters/identity.py` rather than derived from its title: a title changes and an address
must not. Merging is the one operation that retires an identifier, so it is also the one that can
break an address, and the procedure exists so that it does not.

**Establish that they are one work, on a field that is not the title.** `adapters/madb/extract.agrees`
is the test: the creator, the publisher or the imprint has to agree. A matching title is the
strongest lead available and no kind of evidence on its own, which `トワ・エ・モア` demonstrates by
being a 1996 コンパス anthology and a 2024 講談社 series at once. Where nothing but the title agrees,
leave the pair undecided. An undecided join costs a duplicate row; a wrong merge is hard to see once
made.

**Retire the newer identifier into the older**, so the address that has been published longest is
the one that survives:

```
python3 adapters/identity.py --merge RETIRED SURVIVING --basis "creator agrees: ..."
./build.py && ./deploy.sh
```

**What happens to the retired address.** `identity.py` writes `merged_into` into
`data/identity/works.yaml`; `build.py` ships the map as `merged` in `series.json`; `adapters/stubs.py`
writes a page at the retired address that forwards to the survivor, by meta refresh for a reader
with no JavaScript and by `location.replace` for everyone else; and `app.js` follows the same map
in `liveId()` for a link followed inside the interface. A chain of merges is followed to whatever is
live, so A into B into C lands on C.

**Check it after deploying**, because this was recorded in the registry and acted on nowhere for
some time, and 20 retired identifiers became blank pages in one afternoon:

```
curl -s https://yurarium.github.io/kari/work/RETIRED/ | grep -c "This record is now"
```

`adapters/test_stubs.py` covers the forwarder, the chain, and the two guards: a live identifier is
never turned into a forwarder, and one that is not a well-formed id writes nothing, because a path
is built from it.
