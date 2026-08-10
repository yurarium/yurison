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

Usage:  coverage.py --out data/coverage --cache $YURI_CACHE/webcomics-cache \
                    --pages 8 --retrieved 2026-08-01
"""
import argparse, html as _html, json, pathlib, re, sys, time, urllib.request
import unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import textnorm

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
    # SPLIT ON THE TAG, NOT ON ONE SPELLING OF IT. This wanted `<div class="entry">` with the
    # bracket immediately after the class, and webcomics.jp now writes
    # `<div class="entry" data-comic-no="203870">`. One added attribute, and every page read as
    # nothing from 2026-08-04 until it was found on 2026-08-10: 50 entries are on the page, with
    # entry-title, entry-site, entry-date and the id all where they were.
    for b in re.split(r'(?=<div\b[^>]*\bclass="entry"[\s>])', html)[1:]:
        title = re.search(r'class="entry-title[^"]*">\s*<a href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>', b)
        if not title:
            continue
        site = re.search(r'class="entry-site">\s*<a href="[^"]*">\s*([^<]+?)\s*</a>', b)
        date = re.search(r'class="entry-date">\s*([^<]+?)\s*</div>', b)
        tags = re.search(r'class="hover-tip-popup-block">\s*([^<]+?)\s*</span>', b)
        cno = re.search(r'data-comic-no="(\d+)"', b)
        # The antenna emits HTML entities in its own text — HERO&#039;S Web, and apostrophes and
        # ampersands inside work titles. Left encoded they travel into titles, platform names and
        # every comparison built on them, so a platform never matches its registry entry.
        u = _html.unescape
        out.append({
            "title": u(title.group(2)),
            "work_url": title.group(1),
            "platform": u(site.group(1)) if site else "",
            "updated_text": u(date.group(1)) if date else "",
            "tags": [u(x.strip()) for x in tags.group(1).split(",")] if tags else [],
            "antenna_id": cno.group(1) if cno else "",
        })
    return out


# One producer of this fact, shared with adapters/coverage_union.py. See adapters/textnorm.py for
# why `+` is kept: it is the difference between 少年ジャンプ+ and the magazine.
norm = textnorm.norm


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
        # THE HEALTH CHECK GOES FIRST, because the case it exists for is the one `if not rows`
        # was swallowing. Zero entries on page 1 is the strongest evidence the markup moved or
        # the host answered with something else, and it was the only quantity that left here
        # quietly: 1 to 9 entries exited loudly, 0 broke out of the loop and reported success.
        # Every CI run of this pass has printed `listings: 0 over 8 page(s)` and exited 0.
        if n == 1 and len(rows) < MIN_PER_PAGE:
            # SAY WHAT WAS READ, because the refusal on its own does not distinguish a markup
            # change from a host answering something else, and the page is on a machine nobody
            # can look at. The size and the title are enough to tell an interstitial from a
            # listing whose classes were renamed, and neither reproduces the page.
            page = fetch(n, cache, a.force)
            m = re.search(r"<title[^>]*>([^<]{0,120})", page)
            title = m.group(1).strip() if m else "(none)"
            sys.exit(f"HEALTH: page 1 yielded {len(rows)} entries (< {MIN_PER_PAGE}). "
                     f"Refusing to write. What was read: {len(page)} characters, "
                     f"title {title!r}, "
                     f"{'has' if 'class=\"entry\"' in page else 'has no'} entry block. "
                     f"Cached at {cache}/page{n}.html; pass --force to re-fetch, since a cache "
                     f"that once held a refusal is read for ever otherwise.")
        # An empty page after the first is the end of the listing, which is ordinary.
        if not rows:
            break
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
                # The yardsticks label some sites differently from their own branding —
                # ゼノン編集部 for コミックゼノン, ヤンチャンWeb for チャンピオンクロス — so a site we
                # already watch was being counted as an unwatched gap under its other name.
                watched_names.add(norm(pl.get("name")))
                for al in pl.get("aliases") or []:
                    watched_names.add(norm(al))

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

    # The FULL candidate list — every work the antenna lists, with the platforms carrying it.
    #
    # The gap file above holds only works on NO watched platform, which makes it useless as a
    # matching list: onboarding a platform removes its works from the gap, so the adapters stop
    # recognising exactly the titles they just gained access to. Feed matching must use this file.
    W = ["# ALL works listed under Web漫画アンテナ's 百合 tag, with their platforms.",
         "#",
         "# Tier C, DISCOVERY ONLY (REQUIREMENTS §1): this says a work exists and where. It attests",
         "# nothing and establishes no marketing_label. Adapters use it to know which titles to look",
         "# for; the platform's own feed or page is what attests a release.",
         "#",
         "# Distinct from webcomics-gap.yaml, which lists only what is NOT yet reachable.",
         "source: webcomics.jp", "role: discovery-only", f"retrieved: {a.retrieved}",
         "record_type: candidate_works", f"works: {len(platforms_of)}", "candidates:"]
    # CUMULATIVE. The 百合 tag is a hint sheet for where to look for a new series, a one-shot or a
    # chapter, and not a statement of what exists. A work dropping off it says the aggregator has
    # stopped mentioning it and nothing else, so nothing here is ever removed: every previous
    # candidate is carried forward whole, or merged into the fresh row where the walk saw it again.
    # Removal, if it is ever right, is a decision about the work and belongs somewhere that records
    # a reason.
    #
    # THE 8-PAGE WALK IS A RECENCY WINDOW and not the end of the listing. Measured 2026-08-10:
    # page 8 and page 20 each returned 50 rows, page 60 returned 0 and page 150 answered 404, so
    # the tag runs to roughly 32 pages and the loop reaches its ceiling well before its end.
    #
    # Reading deeper cannot cost a work, because of the paragraph above, and the note that used to
    # sit here said it could. What deeper reading costs is requests. The shape wanted instead is a
    # walk that stops at the first page holding nothing new, and it is not written here because it
    # needs the target lists decoupled from the discovery window first: the gap report below is
    # built from this run's listings, so a short walk shrinks it from 376 rows to 47, and merging
    # the carry-forward into it instead takes it to 1,446 and sets every adapter re-reading works
    # already held. Recorded in docs/BUDGET-QUEUE.md.
    prev = {}
    _pf = out / "webcomics-works.yaml"
    if _pf.exists():
        for c in (yaml.safe_load(_pf.read_text()) or {}).get("candidates") or []:
            if c.get("title"):
                prev[norm(c["title"])] = c

    titles, urls, tags = {}, {}, {}
    for e in entries:
        titles.setdefault(norm(e["title"]), e["title"])
        # URLs must be carried here, not only in the gap report. The gap excludes anything already
        # reachable, so adapters that resolve work pages from it lose access to a work the moment
        # its platform is onboarded — which is the opposite of what should happen.
        urls.setdefault(norm(e["title"]), []).append(e["work_url"])
        # THE TAGS WERE PARSED AND THEN DROPPED. The antenna marks a finished serialisation 完結,
        # and that is the only completion signal available for most platforms: of the works it
        # tags, 48 disagreed with the state we had inferred from silence alone. Carried through so
        # something can read it. It is a claim by an aggregator and not an attestation, which is
        # for the consumer to weigh.
        tags.setdefault(norm(e["title"]), set()).update(e.get("tags") or [])
    carried = 0
    for k, c in prev.items():
        if k not in platforms_of:
            platforms_of[k] = set(c.get("platforms") or [])
            titles.setdefault(k, c.get("title"))
            urls.setdefault(k, list(c.get("urls") or []))
            tags.setdefault(k, set(c.get("tags") or []))
            carried += 1
        else:
            platforms_of[k] |= set(c.get("platforms") or [])
            urls.setdefault(k, []).extend(c.get("urls") or [])
            tags.setdefault(k, set()).update(c.get("tags") or [])
    for k, ps in sorted(platforms_of.items()):
        W.append(f"  - title: {json.dumps(titles.get(k, k), ensure_ascii=False)}")
        W.append(f"    platforms: {json.dumps(sorted(p for p in ps if p), ensure_ascii=False)}")
        W.append(f"    urls: {json.dumps(sorted(set(u for u in urls.get(k, []) if u)), ensure_ascii=False)}")
        if tags.get(k):
            W.append(f"    tags: {json.dumps(sorted(tags[k]), ensure_ascii=False)}")
    W.append("")
    (out / "webcomics-works.yaml").write_text("\n".join(W))

    print(f"carried forward   : {carried} works no longer listed but still tracked")
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
