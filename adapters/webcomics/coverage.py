#!/usr/bin/env python3
"""Measure release coverage against Web漫画アンテナ's 百合 tag (REQUIREMENTS §5).

Acceptance criterion: **every update listed on Web漫画アンテナ or 百合ナビ should eventually appear
in our feed**, with the attesting source recorded. Historical completeness is not required — what
ran before we started watching is imperfectly knowable and that is accepted. Forward coverage is
the target.

That makes the antenna a *yardstick*, not a data source. It is Tier C: it may say a work exists and
where, and nothing more (REQUIREMENTS §1). Nothing here becomes a record. The output is a gap
report — the list of platforms and works we do not yet cover, which is the work queue.

Fetches are paginated and polite: identified UA, one request per 1.5s, page count capped.

Usage:  coverage.py --out data/coverage --cache ~/workspace/webcomics-cache \
                    --pages 8 --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys, time, urllib.request
from collections import Counter, defaultdict

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
TAG_URL = "https://webcomics.jp/tag/%E7%99%BE%E5%90%88?p={n}"
PAUSE = 1.5
MIN_PER_PAGE = 10  # health: a page yielding almost nothing means the markup moved


def fetch(n, cache, force=False):
    f = cache / f"page{n}.html"
    if f.exists() and not force:
        return f.read_text()
    req = urllib.request.Request(TAG_URL.format(n=n), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t


def parse(html):
    """One dict per entry. Blocks are split on class="entry" so nothing leaks across boundaries."""
    out = []
    for b in re.split(r'(?=<div class="entry">)', html)[1:]:
        title = re.search(r'class="entry-title[^"]*">\s*<a href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>', b)
        if not title:
            continue
        site = re.search(r'class="entry-site">\s*<a href="[^"]*">\s*([^<]+?)\s*</a>', b)
        date = re.search(r'class="entry-date">\s*([^<]+?)\s*</div>', b)
        tags = re.search(r'class="hover-tip-popup-block">\s*([^<]+?)\s*</span>', b)
        cno = re.search(r'data-comic-no="(\d+)"', b)
        out.append({
            "title": title.group(2),
            "work_url": title.group(1),
            "platform": site.group(1) if site else "",
            "updated_text": date.group(1) if date else "",
            "tags": [x.strip() for x in tags.group(1).split(",")] if tags else [],
            "antenna_id": cno.group(1) if cno else "",
        })
    return out


def norm(s):
    # Strip zero-width and bidi control characters: the antenna emits platform names carrying
    # U+200E/U+200F (竹コミ‎‏‎), which are invisible and silently break every comparison.
    s = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", s or "")
    return re.sub(r"[\s\-.=、。･・！!？?　]", "", s.strip().lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--pages", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)

    entries, seen = [], set()
    for n in range(1, a.pages + 1):
        rows = parse(fetch(n, cache, a.force))
        if not rows:
            break
        if len(rows) < MIN_PER_PAGE and n == 1:
            sys.exit(f"HEALTH: page 1 yielded {len(rows)} entries (< {MIN_PER_PAGE}). "
                     "Markup has probably changed; refusing to write.")
        for r in rows:
            k = r["antenna_id"] or norm(r["title"])
            if k not in seen:
                seen.add(k)
                entries.append(r)

    # What we currently cover: works appearing in our own release feed, plus confirmed web works.
    covered = set()
    for f in pathlib.Path("data/source/gigaviewer").glob("*.yaml"):
        d = yaml.safe_load(f.read_text()) or {}
        for r in d.get("releases") or []:
            covered.add(norm(r.get("work_title")))
    kc = pathlib.Path("data/source/kadokomi/confirmed.yaml")
    if kc.exists():
        for w in (yaml.safe_load(kc.read_text()) or {}).get("works") or []:
            covered.add(norm(w.get("work_title")))

    # Platform coverage is the metric that actually predicts the acceptance criterion. The Atom
    # feeds are a rolling window of recent entries, so no snapshot can match a full catalogue —
    # but every update on a WATCHED platform passes through its window eventually. Whether we watch
    # the platform at all is therefore the gate; per-work overlap today is not.
    watched_names = set()
    pf = pathlib.Path("adapters/gigaviewer/platforms.yaml")
    if pf.exists():
        for pl in (yaml.safe_load(pf.read_text()) or {}).get("platforms") or []:
            if pl.get("enabled") is not False:
                watched_names.add(norm(pl.get("name")))
    # data/platforms.yaml is the registry of what is watched, including platforms served by
    # adapters other than the GigaViewer one (カドコミ, COMIC FUZ).
    reg = pathlib.Path("data/platforms.yaml")
    if reg.exists():
        for pl in (yaml.safe_load(reg.read_text()) or {}).get("platforms") or []:
            if pl.get("watched"):
                watched_names.add(norm(pl.get("name")))

    # A series is often on several platforms (19.6% of these are, up to six each), so a work is a
    # gap only when it is on NO watched platform. Counting presences overstates the gap and
    # mis-ranks the platforms: ニコニコ漫画 leads on presences, but about half of those works are
    # reachable somewhere already watched.
    platforms_of = defaultdict(set)
    for e in entries:
        platforms_of[norm(e["title"])].add(e["platform"])
    works_covered = {t for t, ps in platforms_of.items()
                     if any(norm(p_) in watched_names for p_ in ps)}

    # Rank unwatched platforms by works reachable nowhere already watched — the actual gain.
    exclusive = Counter()
    for t, ps in platforms_of.items():
        if t in works_covered:
            continue
        for p_ in ps:
            exclusive[p_] += 1

    per_platform = Counter(e["platform"] for e in entries)
    watched_works = len(works_covered)

    hits = [e for e in entries if norm(e["title"]) in covered]
    gaps = [e for e in entries if norm(e["title"]) not in covered]

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = ["# COVERAGE GAP against Web漫画アンテナ's 百合 tag.",
         "#",
         "# Tier C, discovery only: this says a work exists and where. It attests nothing and",
         "# nothing here is a record (REQUIREMENTS §1). This is the work queue for reaching the",
         "# acceptance criterion in §5 — every listed update eventually appearing in our feed.",
         "source: webcomics.jp", "role: coverage-yardstick", f"retrieved: {a.retrieved}",
         f"pages_sampled: {a.pages}", "record_type: coverage_gap",
         f"listings: {len(entries)}", f"distinct_works: {len(platforms_of)}",
         f"works_on_watched_platform: {watched_works}",
         f"platforms_total: {len(per_platform)}",
         f"platforms_watched: {len([p_ for p_ in per_platform if norm(p_) in watched_names])}",
         "# ranked by works reachable on NO watched platform",
         "platforms_missing:"]
    for p, n in exclusive.most_common():
        L.append(f"  - platform: {json.dumps(p, ensure_ascii=False)}")
        L.append(f"    works: {n}")
    L.append("works_missing:")
    for e in sorted(gaps, key=lambda e: e["platform"]):
        L.append(f"  - title: {json.dumps(e['title'], ensure_ascii=False)}")
        L.append(f"    platform: {json.dumps(e['platform'], ensure_ascii=False)}")
        L.append(f"    url: {json.dumps(e['work_url'], ensure_ascii=False)}")
        L.append(f"    antenna_id: {json.dumps(e['antenna_id'], ensure_ascii=False)}")
        L.append(f"    tags: {json.dumps(e['tags'], ensure_ascii=False)}")
    L.append("")
    (out / "webcomics-gap.yaml").write_text("\n".join(L))

    nworks = len(platforms_of)
    print(f"listings          : {len(entries)} over {a.pages} page(s), {len(per_platform)} platforms")
    print(f"distinct works    : {nworks}  ({len(entries)-nworks} multi-platform listings)")
    print()
    print(f"WORK COVERAGE     : {watched_works}/{nworks} "
          f"({100*watched_works/max(nworks,1):.1f}%) reachable on a watched platform")
    print(f"platforms watched : {len([p_ for p_ in per_platform if norm(p_) in watched_names])}"
          f"/{len(per_platform)}")
    print()
    print("unwatched platforms, by works reachable NOWHERE watched:")
    for p_, n in exclusive.most_common(12):
        print(f"  {n:4} exclusive (of {per_platform[p_]:4} listed)  {p_}")


if __name__ == "__main__":
    main()
