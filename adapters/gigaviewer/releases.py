#!/usr/bin/env python3
"""Track web-manga releases from GigaViewer platforms (REQUIREMENTS §5).

GigaViewer is Hatena's manga engine, run by many Japanese publishers. Every instance serves an
Atom feed at /atom and renders series listings server-side, so one adapter covers all of them and
adding a publisher is a row in platforms.yaml.

Two steps, deliberately separate:

  series  — read each platform's yuri series listing, building the set of series whose OWN publisher
            labelling marks them yuri. Establishes marketing_label (DEFINITIONS §4).
  feed    — read /atom and keep entries belonging to those series. The feed is site-wide, so
            without the series step it would sweep in every unrelated title the publisher runs.

The feed is the publisher's own published update channel, so this needs no scraping for updates.
Series pages are fetched politely: identified UA, conditional requests, one request per second.

Images are never used. The feed offers episode thumbnails as enclosures; those are not a
publisher-supplied reuse feed and §2 forbids referencing them.

Usage:  releases.py --out data/source/gigaviewer --cache ~/workspace/giga-cache
"""
import argparse, json, pathlib, re, sys, time, urllib.error, urllib.request
import xml.etree.ElementTree as ET
from collections import Counter

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
ATOM = {"a": "http://www.w3.org/2005/Atom"}
GIGA = "{https://gigaviewer.com}"
PAUSE = 1.0

# Episode titles are typed by pattern. Anything unmatched is quarantined as `unclassified` with the
# raw string kept, never guessed into the nearest value (REQUIREMENTS §6).
RELEASE_TYPES = [
    ("chapter", r"^第?\s*[0-9０-９]+\s*(話|回|章)|^#\s*[0-9]+"),
    ("oneshot", r"読み切り|読切"),
    ("trial", r"試し読み|試読|お試し"),
    ("extra", r"番外編|特別編|外伝|おまけ|出張版|特別読切"),
    ("notice", r"休載|お知らせ|告知|重要"),
    ("apology-art", r"お詫び|おわび"),
    ("republication", r"再掲|再録"),
]

MIN_ENTRIES = 5  # health assertion: an empty or tiny feed means broken, not "nothing published"


def get(url, cache_dir, force=False):
    """Fetch with a cached copy and a conditional request. Returns (text, from_cache)."""
    key = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:120]
    body_p, meta_p = cache_dir / f"{key}.body", cache_dir / f"{key}.meta"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if body_p.exists() and not force:
        if meta.get("etag"):
            req.add_header("If-None-Match", meta["etag"])
        if meta.get("last_modified"):
            req.add_header("If-Modified-Since", meta["last_modified"])
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            text = r.read().decode("utf-8", "replace")
            meta_p.write_text(json.dumps({"etag": r.headers.get("ETag"),
                                          "last_modified": r.headers.get("Last-Modified")}))
            body_p.write_text(text)
            return text, False
    except urllib.error.HTTPError as e:
        if e.code == 304 and body_p.exists():
            return body_p.read_text(), True
        raise
    finally:
        time.sleep(PAUSE)


def yuri_series(html, genre, label):
    """Series whose own listing carries the publisher's yuri genre or label.

    GigaViewer renders each series as a block containing a title attribute, an optional label, and
    a genre list. Matching is done per block so a genre never leaks across series boundaries.
    """
    out = {}
    for block in re.split(r'(?=<div class="Series_series_)', html):
        m = re.search(r'class="Series_title[^"]*"[^>]*>([^<]+)<', block)
        if not m:
            continue
        title = m.group(1).strip()
        genres = re.findall(r'class="Series_genre[^"]*"[^>]*>([^<]+)<', block)
        lab = re.search(r'class="Series_label[^"]*"[^>]*>([^<]+)<', block)
        lab = lab.group(1).strip() if lab else ""
        if genre in genres or (label and label == lab):
            author = re.search(r'class="Series_author[^"]*"[^>]*>([^<]+)<', block)
            out[title] = {
                "title": title,
                "author": author.group(1).strip() if author else "",
                "genres": genres,
                "label": lab,
                "evidence": "genre" if genre in genres else "label",
            }
    return out


def classify(title):
    for name, pat in RELEASE_TYPES:
        if re.search(pat, title):
            return name
    return "unclassified"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--platforms", default="adapters/gigaviewer/platforms.yaml")
    ap.add_argument("--force", action="store_true", help="ignore cache validators")
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    plats = yaml.safe_load(open(a.platforms))["platforms"]

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    totals = Counter()
    for p in plats:
        if not p.get("series_pages"):
            totals["skipped (no series pages)"] += 1
            continue

        series = {}
        for sp in p["series_pages"]:
            html, cached = get(sp["url"], cache, a.force)
            found = yuri_series(html, p["yuri_genre"], sp.get("label", ""))
            if not found:
                print(f"HEALTH: {p['id']} — no yuri series found at {sp['url']}. "
                      "Markup may have changed; refusing to write for this platform.", file=sys.stderr)
                totals["degraded"] += 1
                series = None
                break
            series.update(found)
        if series is None:
            continue

        feed, cached = get(p["atom"], cache, a.force)
        root = ET.fromstring(feed)
        entries = root.findall("a:entry", ATOM)
        if len(entries) < MIN_ENTRIES:
            print(f"HEALTH: {p['id']} — feed has {len(entries)} entries (< {MIN_ENTRIES}). "
                  "Refusing to write for this platform.", file=sys.stderr)
            totals["degraded"] += 1
            continue

        rels = []
        for e in entries:
            # GigaViewer puts the SERIES title in <content> and the EPISODE title in <title>.
            work = (e.findtext("a:content", "", ATOM) or "").strip()
            if work not in series:
                continue
            ep = (e.findtext("a:title", "", ATOM) or "").strip()
            link = next((l.get("href") for l in e.findall("a:link", ATOM)
                         if l.get("rel") is None), "")
            free_start = e.findtext(f"{GIGA}freeTermStartDate", "", {})
            rt = classify(ep)
            r = {
                "release_id": (e.findtext("a:id", "", ATOM) or "").strip(),
                "work_title": work,
                "episode_title": ep,
                "release_type": rt,
                "advances_narrative": rt in ("chapter", "oneshot", "extra"),
                "published": (e.findtext("a:updated", "", ATOM) or "").strip(),
                "url": link,
                "author": (e.findtext("a:author/a:name", "", ATOM) or "").strip(),
            }
            if rt == "unclassified":
                r["raw_title"] = ep  # kept verbatim for the next maintenance pass (§6)
            if free_start:
                r["free_term_start"] = free_start
            rels.append(r)

        doc = [
            "# Source-layer record: web releases from a GigaViewer platform (REQUIREMENTS §5).",
            "# The Atom feed is the publisher's own update channel. Episode thumbnails offered as",
            "# enclosures are NOT referenced — they are not a reuse feed (§2).",
            "source: gigaviewer",
            f"platform: {p['id']}",
            f"platform_name: {json.dumps(p['name'], ensure_ascii=False)}",
            f"publisher: {json.dumps(p['publisher'], ensure_ascii=False)}",
            f"retrieved: {a.retrieved}",
            "record_type: web_releases",
            f"yuri_series_count: {len(series)}",
            "releases:",
        ]
        for r in sorted(rels, key=lambda r: r["published"], reverse=True):
            doc.append(f"  - release_id: {json.dumps(r['release_id'], ensure_ascii=False)}")
            for k in ("work_title", "episode_title", "release_type", "published", "url",
                      "author", "free_term_start", "raw_title"):
                if r.get(k):
                    doc.append(f"    {k}: {json.dumps(r[k], ensure_ascii=False)}")
            doc.append(f"    advances_narrative: {str(r['advances_narrative']).lower()}")
        doc.append("")
        (out / f"{p['id']}.yaml").write_text("\n".join(doc))

        # The yuri series list is itself evidence, and is what marketing_label rests on.
        sdoc = ["# Series whose own publisher labelling marks them yuri (DEFINITIONS §4).",
                "source: gigaviewer", f"platform: {p['id']}", f"retrieved: {a.retrieved}",
                "record_type: web_series", "series:"]
        for s in sorted(series.values(), key=lambda s: s["title"]):
            sdoc.append(f"  - title: {json.dumps(s['title'], ensure_ascii=False)}")
            sdoc.append(f"    author: {json.dumps(s['author'], ensure_ascii=False)}")
            sdoc.append(f"    label: {json.dumps(s['label'], ensure_ascii=False)}")
            sdoc.append(f"    genres: {json.dumps(s['genres'], ensure_ascii=False)}")
            sdoc.append(f"    marketing_label: yuri")
            sdoc.append(f"    basis: publisher {s['evidence']} on {p['name']}")
        sdoc.append("")
        (out / f"{p['id']}-series.yaml").write_text("\n".join(sdoc))

        totals["platforms"] += 1
        totals["series"] += len(series)
        totals["releases"] += len(rels)
        types = Counter(r["release_type"] for r in rels)
        print(f"{p['id']:14} series={len(series):3} releases={len(rels):3}  {dict(types)}")

    print()
    print(f"platforms written : {totals['platforms']}")
    print(f"yuri series       : {totals['series']}")
    print(f"releases          : {totals['releases']}")
    if totals["degraded"]:
        print(f"degraded          : {totals['degraded']} (wrote nothing — see stderr)")
    if totals["skipped (no series pages)"]:
        print(f"awaiting survey   : {totals['skipped (no series pages)']} platforms have no series_pages yet")


if __name__ == "__main__":
    main()
