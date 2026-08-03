#!/usr/bin/env bash
# Copy compiled data into the site repo. Build first; this does not build for you.
# The site repo holds artefacts only — records and adapters stay here.
set -euo pipefail
# Derived from this script's own location, not from one machine's home directory.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE="${1:-${YURARIUM_SITE:-$(dirname "$REPO")/yurarium.github.io}}"
[ -f data/build/index.json ] || { echo "no build output — run ./build.py first" >&2; exit 1; }
[ -d "$SITE/kari" ] || { echo "site repo not found at $SITE" >&2; exit 1; }
# feed.json is deliberately NOT copied. It is the internal whole — the acceptance tests and the
# audit sampler read it — and at 1.3 MB it was downloaded in full by every visitor to render the
# first screen. What ships is data/build/feed/: a 14-day current.json, one file per archived month,
# and meta.json. Nothing on the site fetches feed.json any more.
cp data/build/index.json data/build/works.json data/build/series.json data/build/run.json data/build/checks.json "$SITE/kari/data/"
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
# Re-run the checks AFTER copying, and ship the report last.
#
# Two of the invariants compare the site against the build, and build.py runs the checks at the end
# of the BUILD — when data/build has just been rewritten and the site still holds the previous
# deploy. At that instant the comparison legitimately fails, so the report published alongside the
# data always claimed five violations that copying had already fixed. A report that is wrong by
# construction is worse than none: it trains the reader to ignore it.
python3 check.py --runtime >/dev/null 2>&1 || true
cp data/build/checks.json "$SITE/kari/data/" 2>/dev/null || true

echo "copied $(python3 -c 'import json;print(len(json.load(open("data/build/index.json"))))') works -> $SITE/kari/data/"
echo "feed: $(python3 -c 'import json;print(len(json.load(open("data/build/feed/current.json"))["releases"]))') current rows, archives: $(ls data/build/feed/ | grep -c '^[0-9]')"
echo "now commit and push in $SITE"
