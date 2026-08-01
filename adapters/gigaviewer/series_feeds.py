#!/usr/bin/env python3
"""Per-series Atom feeds on GigaViewer platforms (REQUIREMENTS §5).

A platform's main `/atom` holds roughly the last twenty entries across everything it publishes. On
a large platform that is a window of days, and it competes with itself: 一迅プラス's yuri line has
165 series, so a work updating once a month is almost never in view. The result was 37 unresolved
claims against a platform whose entire yuri catalogue we already held — 大室家 and ゆるゆり among
them, sitting as "a listing site says this updated" for a publisher we watch.

GigaViewer also exposes a feed **per series**, at `/atom/series/<series_id>`, and that one is not
a rolling window: 大室家's returns all 136 episodes with dates. One request per series replaces
guessing from a platform-wide feed.

Finding the series id is the only awkward part. It is not an attribute anywhere on the listing —
it appears solely inside the percent-encoded thumbnail URL next to each entry
(`…series-sub-thumbnail-vertical-with-logo%2F<id>-<hash>`). Fragile, so a run that resolves fewer
ids than MIN_RESOLVED refuses to write rather than quietly returning less.

Dates come from the feed's own `<updated>`, so these are platform-attested, not heuristic. The
episode title is the feed `<title>`; the series title comes from the listing, not from parsing the
episode.

Usage:  series_feeds.py --platform ichicomi --out data/source/gigaviewer \
                        --cache ~/workspace/giga-series-cache --retrieved 2026-08-01
"""
import argparse, html as _html, json, pathlib, re, sys, time, urllib.error, urllib.request
from collections import Counter

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.2
MIN_RESOLVED = 20

SERIES_ID = re.compile(
    r'data-series-name="([^"]+)"(.{0,2000}?)series-sub-thumbnail[^"]*?(?:%2F|/)(\d+)-', re.S)
ENTRY = re.compile(r"<entry>(.*?)</entry>", re.S)


def fetch(url, cache, max_age_days=1):
    key = re.sub(r"[^A-Za-z0-9]", "_", url)[-120:]
    f = cache / f"{key}"
    if f.exists() and (time.time() - f.stat().st_mtime) / 86400 < max_age_days:
        return f.read_text()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t


def series_ids(html):
    """Series name -> id, read off the listing page. First occurrence wins; a listing repeats an
    entry across carousels and the later copies carry the same id."""
    out = {}
    for m in SERIES_ID.finditer(html):
        out.setdefault(m.group(1).strip(), m.group(3))
    return out


def episodes(xml):
    out = []
    for b in ENTRY.findall(xml):
        t = re.search(r"<title>([^<]*)</title>", b)
        u = re.search(r"<updated>([^<]*)</updated>", b)
        l = re.search(r'<link href="([^"]+)"', b)
        free = re.search(r"<giga:freeTermStartDate>([^<]*)<", b)
        if not (t and u):
            continue
        # Atom escapes the episode title, so 【試し読み】あんすこ［Are you &quot;mine&quot;？］ arrives
        # encoded. Decoded here, at parse, so the writer quotes it correctly — decoding it later,
        # in the written file, produces a bare " inside a quoted scalar and invalid YAML.
        out.append({"title": _html.unescape(t.group(1).strip()), "updated": u.group(1)[:10],
                    "url": l.group(1) if l else "",
                    "free_from": free.group(1)[:10] if free else None})
    return out


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit", type=int, default=400)
    a = ap.parse_args()

    reg = yaml.safe_load(open("adapters/gigaviewer/platforms.yaml"))["platforms"]
    p = next((x for x in reg if x["id"] == a.platform), None)
    if not p:
        sys.exit(f"platform '{a.platform}' not in the GigaViewer registry")
    pages = p.get("series_pages") or []
    if not pages:
        sys.exit(f"'{a.platform}' declares no series_pages; nothing to enumerate")

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    found = {}
    for page in pages:
        found.update(series_ids(fetch(page["url"], cache)))
    if len(found) < MIN_RESOLVED:
        sys.exit(f"HEALTH: resolved {len(found)} series ids (< {MIN_RESOLVED}). The listing markup "
                 "or the thumbnail URL shape may have changed. Refusing to write.")

    works, failed = [], []
    for name, sid in list(found.items())[: a.limit]:
        try:
            eps = episodes(fetch(f"https://{p['host']}/atom/series/{sid}", cache))
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            failed.append((name, type(e).__name__))
            continue
        if eps:
            works.append({"work_title": name, "series_id": sid, "episodes": eps})

    if not works:
        sys.exit("HEALTH: no series returned episodes. Refusing to write.")

    L = [f"# {p['name']} — per-series Atom feeds, one per work.",
         "#",
         "# The platform-wide /atom holds about twenty entries across everything it publishes,",
         "# which on a platform with 165 yuri series is a window of days. Per-series feeds are not",
         "# a rolling window — 大室家's returns all 136 of its episodes — so a work updating monthly",
         "# is caught rather than missed.",
         "#",
         "# Dates are the feed's own <updated>: platform-attested, not inferred.",
         "source: gigaviewer", f"platform: {p['id']}", f"platform_name: {js(p['name'])}",
         f"publisher: {js(p.get('publisher', ''))}", f"retrieved: {a.retrieved}",
         "record_type: web_work_chapters", "identification_mode: platform-genre",
         f"series_resolved: {len(works)}", "works:"]
    for w in works:
        L.append(f"  - work_title: {js(w['work_title'])}")
        L.append(f"    series_id: {js(w['series_id'])}")
        L.append(f"    url: {js('https://' + p['host'] + '/atom/series/' + w['series_id'])}")
        L.append(f"    chapter_count: {len(w['episodes'])}")
        L.append("    chapters:")
        for e in w["episodes"]:
            L.append(f"      - title: {js(e['title'])}")
            L.append(f"        updated: {e['updated']}")
            if e.get("url"):
                L.append(f"        url: {js(e['url'])}")
            if e.get("free_from"):
                L.append(f"        free_from: {e['free_from']}")
    L.append("")
    (out / f"{p['id']}-series-feeds.yaml").write_text("\n".join(L))

    eps = sum(len(w["episodes"]) for w in works)
    print(f"series ids resolved : {len(found)}")
    print(f"series with episodes: {len(works)}")
    print(f"episodes            : {eps}")
    if failed:
        print(f"failed              : {len(failed)}  {Counter(r for _, r in failed).most_common(3)}")
    print(f"written             : {out}/{p['id']}-series-feeds.yaml")


if __name__ == "__main__":
    main()
