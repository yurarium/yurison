#!/usr/bin/env python3
"""Fetch the platform pages behind untraced claims, so each claim can reach a disposition.

WHY THIS EXISTS. A comparator reports that a work updated. build.py can absorb that claim when the
platform attests it too, and refute it when we hold the platform's own history and it lists nothing
there. Where we hold no history the claim stays `open`, which is honest and is also the whole
backlog: 30 of 33 open claims say some version of "we have not looked at that page".

Looking is the work. This reads the open claims out of the last run, fetches each one's page, and
writes what the platform lists into data/source/webpages/claim-resolved.yaml, which is where
build.py reads whole histories from. Nothing here decides anything: it gathers evidence, and the
disposition rules in build.py are left as the only place that judges it.

WHY IT TARGETS CLAIMS RATHER THAN PLATFORMS. The platform adapters walk a whole site and are the
right tool for keeping the catalogue current. A claim names one work on one platform, and there are
tens of them across two dozen hosts, most of which we have no reason to walk. Fetching two dozen
pages is proportionate where crawling two dozen sites is not.

ENGINES. Two cover most of it, and both are already in the repo:

  comici       an episode list rendered into the page. adapters/comici.py reads it, including the
               range navigation that splits long series across several requests.
  GigaViewer   the page carries a link to a per-series Atom feed, and the feed is the complete
               history. adapters/gigaviewer/series_feeds.py parses it.

A host running neither is reported and left alone. Guessing at an unknown layout would produce a
history that looks whole and is not, and a partial history used as a whole one turns a live claim
into a refutation. That is the one mistake here that would put a wrong statement on the site.

Usage:  trace.py --run data/build/run.json --out data/source/webpages/claim-resolved.yaml
        trace.py --dry-run          list what it would fetch, and stop
"""
import argparse
import collections
import datetime
import json
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import checkstate  # noqa: E402
import comici  # noqa: E402
import net  # noqa: E402
import paths  # noqa: E402
from gigaviewer import series_feeds  # noqa: E402

OUT = "data/source/webpages/claim-resolved.yaml"

# The link a GigaViewer work page carries to its own complete feed.
ATOM = re.compile(r"/atom/series/(\d+)")


def engine_of(html):
    """Which reader can take this page, or None if we have neither."""
    if not html:
        return None
    if comici.is_comici(html):
        return "comici"
    if ATOM.search(html):
        return "gigaviewer"
    return None


def series_feed_url(html, page_url):
    """The per-series Atom URL a GigaViewer page points at, absolute."""
    m = ATOM.search(html or "")
    host = re.match(r"(https?://[^/]+)", page_url or "")
    return f"{host.group(1)}/atom/series/{m.group(1)}" if m and host else None


def targets(run):
    """One row per open claim that names a URL, deduplicated by page.

    Deduplicated because two comparators reporting the same work on the same platform are one page
    to fetch, and because a work claimed on several dates is still one page.
    """
    seen, out = set(), []
    for t in (run.get("claims") or {}).get("trace") or []:
        if t.get("disposition") != "open" or not t.get("url"):
            continue
        key = t["url"]
        if key in seen:
            continue
        seen.add(key)
        out.append({"work_title": t["work"], "platform_name": t.get("platform") or "",
                    "url": t["url"]})
    return out


def merge(doc, rows):
    """Fold freshly read histories into the file, replacing a work's entry rather than appending.

    Replacing, because this file is refetched: appending would leave two entries for one work and
    the loader would have to pick, which is the collision this project keeps meeting. Keyed on the
    URL, since that is what was fetched and what identifies the page.
    """
    doc = dict(doc or {})
    works = list(doc.get("works") or [])
    by_url = {w.get("url"): i for i, w in enumerate(works) if w.get("url")}
    for r in rows:
        if r["url"] in by_url:
            works[by_url[r["url"]]] = r
        else:
            works.append(r)
    doc["works"] = sorted(works, key=lambda w: (w.get("platform_name") or "",
                                                w.get("work_title") or ""))
    doc.setdefault("source", "claim tracing")
    doc.setdefault("platform", "")
    doc.setdefault("platform_name", "")     # per-work; this file spans platforms
    doc.setdefault("record_type", "chapter-history")
    doc.setdefault("identification_mode", "claim-url")
    doc["retrieved"] = datetime.date.today().isoformat()
    return doc


def read_page(url, html, cache):
    """Chapters for one work page, or None where no reader here can take it."""
    eng = engine_of(html)
    if eng == "comici":
        return eng, comici.chapters(html, url, lambda u: (net.fetch(u, cache, 1).text or ""))
    if eng == "gigaviewer":
        feed = series_feed_url(html, url)
        if not feed:
            return eng, []
        return eng, series_feeds.episodes(net.fetch(feed, cache, 1).text or "")
    return None, []


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", default="data/build/run.json")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--cache", default=str(paths.cache("claims-cache")))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)

    run = json.loads(pathlib.Path(a.run).read_text())
    todo = targets(run)
    print(f"{len(todo)} untraced claim(s) with a page to read")
    if a.dry_run:
        for t in todo:
            print(f"   {t['platform_name'][:16]:18} {t['work_title'][:26]:28} {t['url']}")
        return 0

    cache = pathlib.Path(a.cache)
    pages = net.fetch_many([t["url"] for t in todo], cache, max_age_days=1, workers=a.workers)

    # WHAT WE LOOKED AT, recorded whatever we found. A claim we cannot settle looks identical to
    # one we never opened, because both leave no history behind, and build.py was reporting the
    # first as the second: 18 claims read as untraced work when the truth was that the platform's
    # own listing has nothing in it to argue from. The ledger is the difference.
    checks = checkstate.load()

    rows, tally = [], collections.Counter()
    for t in todo:
        res = pages[t["url"]]
        plat = t["platform_name"] or (t["url"].split("/")[2])
        if not res.text:
            tally[f"unreachable ({res.status or res.error})"] += 1
            checkstate.record(checks, plat, t["work_title"],
                              "blocked" if res.status in (401, 403, 429) else
                              "missing" if res.status in (404, 410) else "error",
                              note=f"HTTP {res.status}" if res.status else res.error)
            continue
        eng, chs = read_page(t["url"], res.text, cache)
        if not eng:
            tally["no reader for this site"] += 1
            # Reached, and unreadable by anything here. That is an adapter owed, not a finding.
            checkstate.record(checks, plat, t["work_title"], "error",
                              note="fetched, but no reader here can parse this site")
            continue
        dated = [c for c in chs if c.get("updated")]
        if not dated:
            tally[f"{eng}: read, but the page dates nothing"] += 1
            # A FINDING, not a failure. The platform's own list, read successfully, carries nothing
            # dated for this work. It cannot confirm the claim and cannot refute it either.
            checkstate.record(checks, plat, t["work_title"], "empty",
                              note=f"{eng}: read; the platform lists nothing dated here")
            continue
        checkstate.record(checks, plat, t["work_title"], "ok",
                          note=f"{eng}: {len(dated)} dated chapter(s)")
        tally[f"{eng}: {len(dated)} chapter(s)"] += 0     # keep the key stable below
        tally[eng] += 1
        rows.append({"work_title": t["work_title"], "url": t["url"],
                     "platform_name": t["platform_name"], "route": eng,
                     "chapter_count": len(dated),
                     "chapters": [{"title": c.get("title") or "", "updated": c["updated"]}
                                  for c in dated]})

    checkstate.save(checks)
    out = pathlib.Path(a.out)
    doc = yaml.safe_load(out.read_text()) if out.exists() else {}
    out.write_text(yaml.safe_dump(merge(doc, rows), allow_unicode=True, sort_keys=False,
                                  width=100))
    for k, n in sorted(tally.items()):
        if n:
            print(f"   {n:3}  {k}")
    print(f"wrote {len(rows)} history/histories to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
