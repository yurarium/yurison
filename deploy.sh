#!/usr/bin/env bash
# Copy compiled data into the site repo. Build first; this does not build for you.
# The site repo holds artefacts only — records and adapters stay here.
set -euo pipefail
SITE="${1:-$HOME/workspace/yurarium.github.io}"
[ -f data/build/index.json ] || { echo "no build output — run ./build.py first" >&2; exit 1; }
[ -d "$SITE/kari" ] || { echo "site repo not found at $SITE" >&2; exit 1; }
# feed.json is deliberately NOT copied. It is the internal whole — the acceptance tests and the
# audit sampler read it — and at 1.3 MB it was downloaded in full by every visitor to render the
# first screen. What ships is data/build/feed/: a 14-day current.json, one file per archived month,
# and meta.json. Nothing on the site fetches feed.json any more.
cp data/build/index.json data/build/works.json data/build/series.json data/build/run.json "$SITE/kari/data/"
mkdir -p "$SITE/kari/data/feed"
cp data/build/feed/*.json "$SITE/kari/data/feed/"
# Copy, then reconcile. `cp` adds and overwrites but never removes, so a file the build has stopped
# emitting would sit in the site repo for ever, served and stale. Anything in kari/data that the
# build no longer produces is deleted here rather than left to rot.
rm -f "$SITE/kari/data/feed.json"
for f in "$SITE/kari/data"/*.json "$SITE/kari/data/feed"/*.json; do
  [ -e "$f" ] || continue
  src="data/build/${f#"$SITE/kari/data/"}"
  [ -f "$src" ] || { echo "removing stale $f"; rm -f "$f"; }
done
echo "copied $(python3 -c 'import json;print(len(json.load(open("data/build/index.json"))))') works -> $SITE/kari/data/"
echo "feed: $(python3 -c 'import json;print(len(json.load(open("data/build/feed/current.json"))["releases"]))') current rows, archives: $(ls data/build/feed/ | grep -c '^[0-9]')"
echo "now commit and push in $SITE"
