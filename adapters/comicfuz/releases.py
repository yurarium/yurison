#!/usr/bin/env python3
"""COMIC FUZ (芳文社) — per-work chapter lists and the first real access data (REQUIREMENTS §5).

FUZ is not GigaViewer and publishes no feed, so it cannot be watched the way the others are. Its
per-work pages are server-rendered though, embedding the full chapter list in `__NEXT_DATA__`, so
named works can be followed by polling their own pages. Works are named by the Tier C yardsticks;
FUZ itself attests the chapters.

Two things make it worth the extra work despite the cost:

- **Reading quality.** Ranked joint-best in `data/platforms.yaml`, and all 34 of its listed works
  are reachable on no other watched platform.
- **`pointConsumption`.** FUZ states per chapter whether it is free (`{}`) or costs points
  (`{type, amount}`). This is the first source to give real `access_modes` data — everything else
  so far reports at best a free-window start date.

FUZ applies **no 百合 tag**, so nothing here establishes `marketing_label` (DEFINITIONS §4). Its tag
vocabulary is update-day, audience (男性向け), imprint and magazine.

Never stored: `shortDescription` / `longDescription` (publisher synopsis, §2) or thumbnail URLs.

Usage:  releases.py --gap data/coverage/webcomics-gap.yaml --out data/source/comicfuz \
                    --cache ~/workspace/fuz-cache --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys, time, urllib.error, urllib.request
from collections import Counter

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.5
MIN_WORKS = 5


def fetch(url, cache):
    key = re.sub(r"[^0-9]", "", url.rsplit("/", 1)[-1]) or "x"
    f = cache / f"{key}.html"
    if f.exists():
        return f.read_text()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t


def page_props(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return None
    return json.loads(m.group(1)).get("props", {}).get("pageProps")


def access_of(chapter):
    """FUZ states the access model per chapter. `pointConsumption` empty means free to read;
    populated means it costs points. Anything else is quarantined rather than guessed (§6)."""
    pc = chapter.get("pointConsumption")
    if pc == {} or pc is None:
        return ["free"], None
    if isinstance(pc, dict) and pc.get("amount"):
        return ["purchase"], f"pointConsumption type={pc.get('type')} amount={pc.get('amount')}"
    return ["unknown"], f"unrecognised pointConsumption: {json.dumps(pc, ensure_ascii=False)}"


def iso(d):
    """FUZ dates are YYYY/MM/DD.

    Note these are NOT always publication dates. 40 of 1,880 dated chapters were in the future when
    first read, all of them `purchase` — they are scheduled availability dates for chapters that
    have not been released yet. Callers must check (see `scheduled`).
    """
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", str(d or ""))
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", required=True, help="Tier C yardstick naming FUZ works")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    gap = yaml.safe_load(open(a.gap)) or {}
    # Accepts the full candidate list (candidates/urls) or the gap report (works_missing/url).
    rows = []
    for w in gap.get("candidates") or []:
        for u in w.get("urls") or []:
            rows.append({"title": w.get("title"), "url": u})
    for w in gap.get("works_missing") or []:
        rows.append({"title": w.get("title"), "url": w.get("url")})
    seen_u, targets = set(), []
    for w in rows:
        u = w.get("url") or ""
        if "comic-fuz.com/manga/" in u and u not in seen_u:
            seen_u.add(u)
            targets.append(w)
    targets = targets[:a.limit]
    if not targets:
        sys.exit("no COMIC FUZ works found in the gap file")

    works, failed, acc = [], [], Counter()
    for tgt in targets:
        try:
            pp = page_props(fetch(tgt["url"], cache))
        except urllib.error.HTTPError as e:
            failed.append((tgt["title"], f"HTTP {e.code}"))
            continue
        if not pp or "manga" not in pp:
            failed.append((tgt["title"], "no pageProps payload"))
            continue
        mg = pp["manga"]
        chapters = []
        for group in pp.get("chapters") or []:
            for c in group.get("chapters") or []:
                modes, note = access_of(c)
                acc[modes[0]] += 1
                when = iso(c.get("updatedDate"))
                row = {
                    "chapter_id": c.get("chapterId"),
                    "title": c.get("chapterMainName", ""),
                    "updated": when,
                    "access_modes": modes,
                }
                # A date in the future is a schedule, not an observation (REQUIREMENTS §5). These
                # chapters have not been released; they must never enter a release feed.
                if when and when > a.retrieved:
                    row["scheduled"] = True
                if note:
                    row["access_note"] = note
                chapters.append(row)
        works.append({
            "work_title": mg.get("mangaName", tgt["title"]),
            "yomi": mg.get("mangaNameKana", ""),
            "url": tgt["url"],
            "authors": [x.get("author", {}).get("authorName")
                        for x in pp.get("authorships") or []],
            "tags": [x["name"] for x in pp.get("tags") or []],
            "latest_updated": iso(mg.get("latestUpdatedDate")),
            "is_original": mg.get("isOriginal"),
            "chapters": chapters,
            "discovered_via": {"source": gap.get("source"), "role": "discovery-only"},
        })

    # ── access flips ───────────────────────────────────────────────────────────────────────────
    # A chapter moving from paid to free is itself an update for a reader who wants free content,
    # and FUZ applies different rules per series — some free throughout, some free after the latest
    # couple, some paywalling recent volumes. Detected by comparing against the previous run and
    # recorded on the chapter; it can only be observed across runs, never from one snapshot.
    prior = {}
    pf = out / "works.yaml"
    if pf.exists():
        old = yaml.safe_load(pf.read_text()) or {}
        for w in old.get("works") or []:
            for c in w.get("chapters") or []:
                if c.get("chapter_id") is not None:
                    prior[c["chapter_id"]] = (c.get("access_modes") or [None])[0]
    flips = 0
    for w in works:
        for c in w["chapters"]:
            was = prior.get(c["chapter_id"])
            now = (c["access_modes"] or [None])[0]
            if was and now and was != now:
                c["access_changed"] = f"{was} -> {now}"
                c["access_changed_on"] = a.retrieved
                if now in ("free", "free-timed"):
                    c["became_free"] = True
                flips += 1

    if len(works) < MIN_WORKS:
        sys.exit(f"HEALTH: resolved {len(works)} works (< {MIN_WORKS}). Refusing to write.")

    L = ["# COMIC FUZ per-work chapter lists. Works named by a Tier C yardstick; FUZ attests them.",
         "# FUZ applies NO 百合 tag, so nothing here establishes marketing_label (DEFINITIONS §4).",
         "# No synopsis and no image URLs are stored (REQUIREMENTS §2).",
         "source: comicfuz", f"retrieved: {a.retrieved}", "record_type: web_work_chapters",
         "identification_mode: discovery-candidate", "works:"]
    for w in works:
        L.append(f"  - work_title: {js(w['work_title'])}")
        for k in ("yomi", "url", "latest_updated", "is_original"):
            if w.get(k) not in (None, ""):
                L.append(f"    {k}: {js(w[k])}")
        L.append(f"    authors: {js([x for x in w['authors'] if x])}")
        L.append(f"    tags: {js(w['tags'])}")
        L.append(f"    chapter_count: {len(w['chapters'])}")
        L.append("    chapters:")
        for c in w["chapters"]:
            L.append(f"      - chapter_id: {c['chapter_id']}")
            L.append(f"        title: {js(c['title'])}")
            if c["updated"]:
                L.append(f"        updated: {c['updated']}")
            if c.get("scheduled"):
                L.append("        scheduled: true   # future date — not yet released")
            L.append(f"        access_modes: {js(c['access_modes'])}")
            for k in ("access_changed", "access_changed_on"):
                if c.get(k):
                    L.append(f"        {k}: {js(c[k])}")
            if c.get("became_free"):
                L.append("        became_free: true")
            if c.get("access_note"):
                L.append(f"        access_note: {js(c['access_note'])}")
    L.append("")
    (out / "works.yaml").write_text("\n".join(L))

    print(f"works targeted : {len(targets)}")
    print(f"works resolved : {len(works)}")
    print(f"chapters       : {sum(len(w['chapters']) for w in works)}")
    print(f"access modes   : {dict(acc)}")
    print(f"access flips   : {flips} (only observable across runs)")
    for t, why in failed:
        print(f"  FAILED {t}: {why}")


if __name__ == "__main__":
    main()
