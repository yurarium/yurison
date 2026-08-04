#!/usr/bin/env python3
"""Which works the antenna has ever marked 完結, gathered from every snapshot we hold.

WHY THIS EXISTS. `state: dormant` was asserted on silence and nothing else: 150 works carried it
and not one carried a basis, with a median of 846 days since the last chapter and a longest of
eight and a half years. Completion, meanwhile, was only ever recorded when a chapter title said
最終話 outright, so a series that ended without us seeing its final instalment fell into dormant
and stayed there.

Most platforms state nothing. Probing one dormant work on each of ten platforms found completion
marked on two. What does carry it is Web漫画アンテナ, which tags a finished serialisation 完結
alongside its genre tags, and adapters/webcomics/coverage.py has been parsing those tags and
discarding them at write time.

WHY THE WHOLE CACHE AND NOT THE CURRENT PAGE. The antenna lists what updated recently, so a work
that finished two years ago has long since fallen off it: reading only today's fetch finds ten
works where the accumulated snapshots hold a hundred and twenty-nine. A tag seen in an older
snapshot has not expired, because a serialisation does not un-finish. The date the snapshot was
taken is recorded with the claim so a reader can see how old the observation is.

WHAT THIS IS NOT. An attestation. The antenna is an aggregator, and DEFINITIONS §5 makes a
community source a lead rather than a basis. What it produces here is a claim, to be weighed
against what the platform itself shows, and that weighing belongs to build.py rather than here.
"""
import argparse
import datetime
import glob
import html as _html
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import textnorm  # noqa: E402

ENTRY = re.compile(r'(?=<div class="entry">)')
TITLE = re.compile(r'class="entry-title[^"]*">\s*<a href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>')
SITE = re.compile(r'class="entry-site">\s*<a href="[^"]*">\s*([^<]+?)\s*</a>')
TAGS = re.compile(r'class="hover-tip-popup-block">\s*([^<]+?)\s*</span>')

FINISHED = "完結"


def entries(page):
    """Title, platform and tags for each listing row. The same split coverage.py uses."""
    out = []
    for b in ENTRY.split(page)[1:]:
        t = TITLE.search(b)
        if not t:
            continue
        site, tags = SITE.search(b), TAGS.search(b)
        out.append({
            "title": _html.unescape(t.group(2)),
            "url": t.group(1),
            "platform": _html.unescape(site.group(1)) if site else "",
            "tags": [_html.unescape(x.strip()) for x in tags.group(1).split(",")] if tags else [],
        })
    return out


def finished(pages):
    """{normalised title: claim} for every work any snapshot tags 完結.

    Keyed on the comparison form so the same work seen under two spellings is one claim, and the
    first spelling seen is kept for display. `seen` is the day the snapshot was taken, which is
    what makes the age of the observation visible rather than implied.
    """
    out = {}
    for path, taken in pages:
        for e in entries(path):
            if FINISHED not in e["tags"]:
                continue
            k = textnorm.norm(e["title"])
            if k in out:
                out[k]["seen"] = max(out[k]["seen"], taken)
                continue
            out[k] = {"work": e["title"], "platform": e["platform"], "url": e["url"],
                      "seen": taken}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", default="data/source/comparators/completion.yaml")
    a = ap.parse_args(argv)

    pages = []
    for f in sorted(glob.glob(str(pathlib.Path(a.cache) / "*.html"))):
        p = pathlib.Path(f)
        try:
            pages.append((p.read_text(encoding="utf-8", errors="replace"),
                          datetime.date.fromtimestamp(p.stat().st_mtime).isoformat()))
        except OSError:
            continue
    claims = finished(pages)

    L = ["# Works Web漫画アンテナ has tagged 完結, gathered from every snapshot in the fetch cache.",
         "#",
         "# A CLAIM, not an attestation: the antenna is an aggregator, so this is a lead under",
         "# DEFINITIONS §5 and what to do about it is build.py's to decide. `seen` is the day the",
         "# snapshot carrying the tag was taken, so the age of the observation is visible.",
         "source: webcomics.jp", "role: completion-claims",
         f"retrieved: {datetime.date.today().isoformat()}",
         f"pages_read: {len(pages)}", "claims:"]
    for k in sorted(claims):
        c = claims[k]
        L.append(f"  - work: {json.dumps(c['work'], ensure_ascii=False)}")
        L.append(f"    platform: {json.dumps(c['platform'], ensure_ascii=False)}")
        L.append(f"    url: {json.dumps(c['url'], ensure_ascii=False)}")
        L.append(f"    seen: {c['seen']}")
    L.append("")
    pathlib.Path(a.out).write_text("\n".join(L))
    print(f"{len(claims)} work(s) tagged {FINISHED} across {len(pages)} snapshot(s) -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
