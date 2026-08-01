#!/usr/bin/env bash
# Copy compiled data into the site repo. Build first; this does not build for you.
# The site repo holds artefacts only — records and adapters stay here.
set -euo pipefail
SITE="${1:-$HOME/workspace/yurarium.github.io}"
[ -f data/build/index.json ] || { echo "no build output — run ./build.py first" >&2; exit 1; }
[ -d "$SITE/kari" ] || { echo "site repo not found at $SITE" >&2; exit 1; }
cp data/build/index.json data/build/works.json "$SITE/kari/data/"
echo "copied $(python3 -c 'import json;print(len(json.load(open("data/build/index.json"))))') works -> $SITE/kari/data/"
echo "now commit and push in $SITE"
