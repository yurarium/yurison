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
import argparse, datetime, json, pathlib, re, sys, time, urllib.error, urllib.request

JST = datetime.timezone(datetime.timedelta(hours=9))


def jst_date(stamp):
    """The date a Japanese platform considers a UTC timestamp to fall on."""
    s = str(stamp or "").strip()
    if len(s) <= 10 or "T" not in s:
        return s[:10]
    try:
        d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return s[:10]
    return d.astimezone(JST).date().isoformat() if d.tzinfo else s[:10]
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

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

# An EMPTY feed means broken, not "nothing published". A small feed does not: some publishers
# genuinely run only a few series, so a threshold above 1 rejects legitimate small platforms
# (comic-trail returned 3 real entries and was wrongly failed at 5).
MIN_ENTRIES = 1

# Platform timestamps are unreliable. GigaViewer emits Atom <updated> and no <published>, so the
# value is by definition "last modified", not "first published". Sites mass-update it during
# metadata refreshes and when importing an existing series, which back-dates a whole run to one
# instant. Observed 2026-08-01: 37 entries across 4 timestamps, one of them carrying 25 entries
# from only 3 works.
#
# A shared timestamp is normal when it is a scheduled daily batch — many works, about one entry
# each. It is suspect when one work contributes several entries at the identical instant.
BULK_PER_WORK = 3

# Some platform "series" are only 試し読み — sample chapters promoting a printed volume. They are
# not web manga: under DEFINITIONS §6 the work's first publication is the tankōbon, and the web
# posting is advertising. Their samples are not publication events and do not belong in a release
# feed. The series is still worth keeping: it names a print work, often one the catalogue lacks.
PROMO_ONLY_TYPES = {"trial"}

# GigaViewer ships in two generations. The newer Next.js build (ichicomi) renders genre chips on
# its series listing; the classic server-rendered build (comic-days, zenon, tonarinoyj, …) carries
# title, author and tagline and NO genre data at all. Verified 2026-08-01: none of the classic
# hosts exposes a working /tag/ or /genre/ page either.
#
# So most platforms cannot tell us which of their series are yuri, which is DEFINITIONS §4's bias
# in concrete form — general platforms label nothing. They onboard in `known-works` mode instead:
# the feed attests releases for works identified as yuri somewhere else (the print catalogue, a
# labelling platform, or a confirmed discovery candidate).
#
# A known-works match is IDENTIFICATION, not classification. The work's marketing_label comes from
# wherever it was established; the platform is only telling us a release happened.
MODE_GENRE = "genre"
MODE_KNOWN = "known-works"


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


def known_titles(paths):
    """Normalised titles of works already ESTABLISHED as yuri — the built catalogue, and platforms
    that label their own series. A match here is identification against settled evidence."""
    out = {}
    for p_ in paths:
        f = pathlib.Path(p_)
        if not f.exists():
            continue
        if f.suffix == ".json":
            for w in json.loads(f.read_text()):
                out[norm_title(w.get("t", ""))] = w.get("t", "")
        else:
            d = yaml.safe_load(f.read_text()) or {}
            for s in d.get("series") or []:
                out[norm_title(s.get("title", ""))] = s.get("title", "")
    out.pop("", None)
    return out


def candidate_titles(path):
    """Titles a Tier C yardstick says are yuri and names a platform for.

    This is DISCOVERY, not evidence (REQUIREMENTS §1): the antenna says which titles to look for,
    and the platform's own feed is what attests the release. Releases matched this way are marked
    `discovery-candidate` and the work carries no marketing_label from it — a Tier C listing is a
    bare assertion of membership and establishes nothing about content.
    """
    f = pathlib.Path(path)
    if not f.exists():
        return {}
    d = yaml.safe_load(f.read_text()) or {}
    out = {}
    # Accept either the full candidate list or the gap report; the full list is what should be
    # used, since the gap deliberately excludes everything already reachable.
    for w in (d.get("candidates") or []) + (d.get("works_missing") or []):
        out[norm_title(w.get("title", ""))] = w.get("title", "")
    out.pop("", None)
    return out


def norm_title(s):
    s = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", s or "")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"""[\s\-.=、。･・!?,:;'"“”‘’()\[\]{}「」『』【】〈〉《》〔〕~〜_/\\|+*&#@]""",
                  "", s.strip().lower())


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
    ap.add_argument("--known", nargs="*", default=["data/build/index.json",
                                                   "data/source/gigaviewer/ichicomi-series.yaml"],
                    help="sources of already-established yuri work titles")
    ap.add_argument("--candidates", default="data/coverage/webcomics-works.yaml",
                    help="Tier C yardstick naming candidate titles (discovery only)")
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    plats = yaml.safe_load(open(a.platforms))["platforms"]

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    known = known_titles(a.known)
    cands = candidate_titles(a.candidates) if a.candidates else {}
    # Established titles win where both contain a title, so provenance is never downgraded.
    cands = {k: v for k, v in cands.items() if k not in known}
    if known or cands:
        print(f"known yuri works: {len(known)} established, {len(cands)} discovery candidates\n")

    totals = Counter()
    for p in plats:
        if p.get("enabled") is False:
            totals["disabled"] += 1
            continue
        mode = p.get("mode", MODE_GENRE)

        series = {}
        if mode == MODE_GENRE:
            if not p.get("series_pages"):
                totals["skipped (no series pages)"] += 1
                continue
            for sp in p["series_pages"]:
                html, cached = get(sp["url"], cache, a.force)
                found = yuri_series(html, p["yuri_genre"], sp.get("label", ""))
                if not found:
                    print(f"HEALTH: {p['id']} — no yuri series found at {sp['url']}. "
                          "Markup may have changed; refusing to write for this platform.",
                          file=sys.stderr)
                    totals["degraded"] += 1
                    series = None
                    break
                series.update(found)
            if series is None:
                continue
        else:
            if not known:
                totals["skipped (no known-works list)"] += 1
                continue
            series = None  # resolved per-entry against `known` below

        try:
            feed, cached = get(p["atom"], cache, a.force)
            root = ET.fromstring(feed)
            # A 200 is not proof of a feed: mangacross.jp/atom serves its React app shell with a
            # 200 status. Require an actual Atom root before believing any of it.
            if not root.tag.endswith("}feed"):
                raise ET.ParseError(f"root element is <{root.tag}>, not an Atom <feed> — "
                                    "the endpoint is probably serving a web page")
        except (ET.ParseError, OSError) as e:
            # One broken source degrades that platform and nothing else (§6): a run must not die
            # because a publisher served malformed XML.
            print(f"HEALTH: {p['id']} — feed unusable ({type(e).__name__}: {e}). "
                  "Writing nothing for this platform.", file=sys.stderr)
            totals["degraded"] += 1
            continue
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
            if mode == MODE_GENRE:
                if work not in series:
                    continue
                ident = "platform-genre"
            else:
                nw = norm_title(work)
                if nw in known:
                    ident = "known-work-match"
                elif nw in cands:
                    ident = "discovery-candidate"
                else:
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
                # Atom <updated>: last modified, NOT first published. Named accordingly.
                "platform_updated": (e.findtext("a:updated", "", ATOM) or "").strip(),
                "url": link,
                "author": (e.findtext("a:author/a:name", "", ATOM) or "").strip(),
                # How this release was identified as belonging to a yuri work. A known-work match
                # is identification only — it carries no marketing_label of its own.
                "identified_via": ident,
            }
            if rt == "unclassified":
                r["raw_title"] = ep  # kept verbatim for the next maintenance pass (§6)
            if free_start:
                r["free_term_start"] = free_start
            rels.append(r)

        # Flag bulk-update signatures: several entries of ONE work sharing an identical timestamp.
        per = Counter((r["work_title"], r["platform_updated"]) for r in rels)
        for r in rels:
            n = per[(r["work_title"], r["platform_updated"])]
            if n >= BULK_PER_WORK:
                r["date_confidence"] = "low"
                r["date_note"] = (f"{n} releases of this work share this timestamp — consistent with "
                                  "a metadata refresh or a series import, not same-day publication")
            else:
                r["date_confidence"] = "reported"

        # Dates are LOCKED at first sight and never revised (REQUIREMENTS §4).
        #
        # The bulk-update problem is largely a first-import artefact: on the run that first sees a
        # platform, everything is inherited from timestamps we had no part in observing. From then
        # on we watch releases appear, and a later mass-update cannot move a date we already hold.
        # So the primary date is the earliest evidence available when the release was first seen,
        # and subsequent platform changes are recorded as divergence rather than followed.
        prior = {}
        prev_file = out / f"{p['id']}.yaml"
        first_run = not prev_file.exists()
        if not first_run:
            old = yaml.safe_load(prev_file.read_text()) or {}
            prior = {o.get("release_id"): o for o in (old.get("releases") or [])}

        # Releases that have scrolled out of the Atom window must be KEPT (REQUIREMENTS §4).
        # Rewriting the file from the current window each run silently discarded everything older,
        # so the feed could never accumulate — it only ever held one window's worth.
        seen_now = {r["release_id"] for r in rels}
        retained = 0
        for rid, old_rec in prior.items():
            if rid in seen_now:
                continue
            keep = dict(old_rec)
            keep["in_current_window"] = False
            rels.append(keep)
            retained += 1

        for r in rels:
            if r.get("in_current_window") is False:
                continue          # already locked on an earlier run; nothing to recompute
            was = prior.get(r["release_id"])
            if was:
                r["first_seen"] = str(was.get("first_seen") or a.retrieved)
                r["first_reported"] = str(was.get("first_reported") or r["platform_updated"])
                r["date_basis"] = was.get("date_basis") or "bootstrap"
                # Direct evidence of a platform rewriting its own timestamps. Kept, not followed.
                if r["platform_updated"] and r["platform_updated"] != r["first_reported"]:
                    r["platform_date_changed"] = (f"was {r['first_reported']}, "
                                                  f"now {r['platform_updated']}")
            else:
                r["first_seen"] = a.retrieved
                r["first_reported"] = r["platform_updated"]
                # bootstrap: present when we started watching, so the platform's date is inherited
                # with nothing behind it. observed: appeared between two runs, so first_seen is
                # real evidence and bounds the true date from above.
                r["date_basis"] = "bootstrap" if first_run else "observed"

            # The date the rest of the system uses: earliest evidence held, locked.
            # Named distinctly: `cands` is the module-level discovery-candidate map, and shadowing
            # it here silently broke title matching on every platform after the first.
            date_evidence = [d for d in (r["first_reported"], r["first_seen"]) if d]
            # JST, not UTC. Atom <updated> is UTC and 少年ジャンプ+ / サンデーうぇぶり publish at
            # 15:00Z — midnight JST the next day — so slicing ten characters dated every one of
            # their chapters a day early. 春雷卓球 shows 2026年07月31日 against a 2026-07-30T15:00:00Z
            # stamp, on a series that updates 毎週金曜: the Friday is the 31st.
            #
            # This is a PARSE correction, not a revision of a locked date (§5). The date was never
            # the platform's; it was our misreading of the platform's, and the locking rule exists
            # to stop us following a platform that moves its own dates, not to preserve our own
            # arithmetic errors.
            r["date"] = min(jst_date(c) for c in date_evidence) if date_evidence else ""

        # Classify each series by the shape of its release history.
        by_work = defaultdict(list)
        for r in rels:
            by_work[r["work_title"]].append(r)
        promo = {w for w, rs in by_work.items()
                 if {x["release_type"] for x in rs} <= PROMO_ONLY_TYPES}
        for r in rels:
            r["web_status"] = "promotional-sample-only" if r["work_title"] in promo else "serialised"

        doc = [
            "# Source-layer record: web releases from a GigaViewer platform (REQUIREMENTS §5).",
            f"# identification mode: {mode}",
            "# The Atom feed is the publisher's own update channel. Episode thumbnails offered as",
            "# enclosures are NOT referenced — they are not a reuse feed (§2).",
            "source: gigaviewer",
            f"platform: {p['id']}",
            f"platform_name: {json.dumps(p['name'], ensure_ascii=False)}",
            # Optional. A platform found by probing for /atom is identified by its host; the
            # publisher behind it is a separate fact. An empty value is honest — guessing one from
            # the domain would put invented attribution into the source layer.
            f"publisher: {json.dumps(p.get('publisher', ''), ensure_ascii=False)}",
            f"retrieved: {a.retrieved}",
            "record_type: web_releases",
            f"identification_mode: {mode}",
            f"yuri_series_count: {len(series) if series else 0}",
            "releases:",
        ]
        for r in sorted(rels, key=lambda r: r["platform_updated"], reverse=True):
            doc.append(f"  - release_id: {json.dumps(r['release_id'], ensure_ascii=False)}")
            if r.get("in_current_window") is False:
                doc.append("    in_current_window: false")
            for k in ("work_title", "web_status", "identified_via", "episode_title",
                      "release_type", "date", "date_basis",
                      "first_seen", "first_reported", "platform_updated", "platform_date_changed",
                      "date_confidence", "date_note", "url",
                      "author", "free_term_start", "raw_title"):
                if r.get(k):
                    doc.append(f"    {k}: {json.dumps(r[k], ensure_ascii=False)}")
            doc.append(f"    advances_narrative: {str(r['advances_narrative']).lower()}")
        doc.append("")
        (out / f"{p['id']}.yaml").write_text("\n".join(doc))

        # The yuri series list is itself evidence, and is what marketing_label rests on.
        if series is None:
            series = {}
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

        # Promotional-sample series are print works reached through a web sample. Emitted as
        # catalogue candidates rather than releases — kept, not discarded (§4).
        if promo:
            pdoc = ["# Print works surfaced by web 試し読み samples. NOT web manga (DEFINITIONS §6):",
                    "# the sample promotes a printed volume, so first publication is the tankōbon.",
                    "# These are catalogue candidates, not releases and not records.",
                    "source: gigaviewer", f"platform: {p['id']}", f"retrieved: {a.retrieved}",
                    "record_type: print_candidates", "candidates:"]
            for w in sorted(promo):
                rs = by_work[w]
                pdoc.append(f"  - work_title: {json.dumps(w, ensure_ascii=False)}")
                pdoc.append(f"    author: {json.dumps(series.get(w, {}).get('author', ''), ensure_ascii=False)}")
                pdoc.append(f"    sample_count: {len(rs)}")
                pdoc.append(f"    sample_url: {json.dumps(rs[0]['url'], ensure_ascii=False)}")
                pdoc.append(f"    label: {json.dumps(series.get(w, {}).get('label', ''), ensure_ascii=False)}")
                pdoc.append("    status: unconfirmed")
            pdoc.append("")
            (out / f"{p['id']}-print-candidates.yaml").write_text("\n".join(pdoc))

        totals["platforms"] += 1
        totals["series"] += len(series)
        totals["releases"] += len(rels)
        idents = Counter(r["identified_via"] for r in rels)
        types = Counter(r["release_type"] for r in rels)
        low = sum(1 for r in rels if r.get("date_confidence") == "low")
        boot = sum(1 for r in rels if r.get("date_basis") == "bootstrap")
        moved = sum(1 for r in rels if r.get("platform_date_changed"))
        totals["low-confidence dates"] += low
        print(f"{p['id']:14} series={len(series):3} releases={len(rels):3}"
              + (f" (+{retained} retained)" if retained else "")
              + f"  {dict(types)}  {dict(idents)}")
        if promo:
            n = sum(1 for r in rels if r["web_status"] == "promotional-sample-only")
            print(f"{'':14} {len(promo)} series are 試し読み samples only "
                  f"({n} releases) -> print candidates, excluded from the feed")
        print(f"{'':14} dates: {boot} bootstrap, {len(rels)-boot} observed"
              + (f", {low} bulk-signature" if low else "")
              + (f", {moved} CHANGED at source" if moved else ""))

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
