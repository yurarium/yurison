# The stage dependency graph

Written during stage one of the refactor, as the second of its two measurements. It exists so that
an incremental build has something to key on, and so stage four models the flow it finds instead of
the flow it assumes. Derived by reading path literals out of `build.py`, then checked against what
the scripts actually open.

## The shape

```
data/source/**        fetched records, immutable once written (REQUIREMENTS section 5)
        |
        |  adapters/*                       one adapter per platform or catalogue
        v
data/coverage/**      what each source was found to hold
data/ledger/**        when a thing was first seen
        |
        |  adapters/names/pass0..pass4      readings, divisions, English names
        v
data/names/**         the store: titles, authors, publishers, phrases, attempts, curated
data/identity/**      rulings and registries: works, credits, credit-works, publishers
        |
        |  build.py
        v
data/build/*.json     series, works, index, credits, publishers, titles, feed, run
        |
        |  check.py --runtime         writes checks.json and status.json
        |  deploy.sh                  copies a subset
        v
../yurarium.github.io/kari/data/**    the published snapshot
```

## What `build.py` reads

48 path literals across five directories. `data/source` and `data/coverage` are adapter output;
`data/names` and `data/identity` hold the store and the rulings; `data/ledger` holds first-seen
dates.

## What `build.py` writes

Eight files: `series.json`, `works.json`, `index.json`, `credits.json`, `publishers.json`,
`titles.json`, `feed.json`, `run.json`. `check.py --runtime` adds `checks.json` and `status.json`.
`deploy.sh` copies all except `feed.json`, `titles.json` and `ledger.json`.

## The loop that surprises people

`titles.json` is build output AND adapter input. `bwingest`, `gigaviewer/releases` and `curate` all
read it to decide what to fetch or what to reconcile, so the flow is not a straight line:

```
build.py  ->  data/build/titles.json  ->  adapters decide what to fetch
                                              |
                                              v
                                      data/source/**  ->  build.py
```

A fresh clone must therefore build once before it can fetch. The committed `data/build` hides this
today, and dropping it in stage three makes the ordering visible.

## What this means for an incremental build

The keys are clean at the top and muddy at the bottom.

**Clean.** `data/source` is immutable once fetched, so an adapter stage keyed on the hash of its
inputs need not re-run. The naming passes consume `data/source` plus `data/names` and produce
`data/names`, which is a fixed point rather than a pipeline: a pass can be skipped when neither its
inputs nor its own prior output changed.

**Muddy.** `build.py` reads all five directories and writes eight files in one pass, so it has no
internal stage boundaries to key on. Making it incremental means giving it some, and that is the
same work as deciding what the tables are. It belongs to stage four and not before.

## The measurement that goes with this

YAML parsing is 43 percent of `build.py` with libyaml already installed and in use. CSafeLoader is
6.3 times faster than the pure-Python loader on `titles.yaml`, 0.66 s against 4.14 s, and the 62 s
that remains is the cost of constructing 7.4 million Python objects from 22,780 files.

That is the number stage one was asked to produce, and it answers the question stage one was holding
open: **storage is the speed lever**, so the hash-keyed incremental build stays held and the effort
goes into stage four.

## A hotspot recorded and deliberately not fixed here

`boundary.fill_store` is 24 s of the build, of which `store_donors` is 23 s and `cuts` is called
1.76 million times. It is left alone because it belongs to the `division` fact, and optimising it
where it sits would mean touching nine files that stage two is about to collapse into one.
