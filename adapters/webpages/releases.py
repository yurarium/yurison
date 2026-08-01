#!/usr/bin/env python3
"""Chapter lists from server-rendered work pages, for platforms with no feed (REQUIREMENTS §5).

Several platforms publish no Atom feed but render their episode lists server-side, so a named work
can be followed by polling its own page. Works are named by the Tier C yardsticks; the platform
attests the chapters.

Selectors live in `sites.yaml` as declarative data (§6): adding a platform is a row, and repairing
one after a redesign is a bounded edit rather than a code change. Sites sharing an engine share a
spec — ビッコミ and 竹コミ both run comici with identical markup.

None of these platforms applies a 百合 tag, so nothing here establishes marketing_label.

Never stored: synopsis text or image URLs (§2).

Usage:  releases.py --gap data/coverage/webcomics-gap.yaml --out data/source/webpages \
                    --cache ~/workspace/webpages-cache --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys, time, urllib.error, urllib.request
from collections import Counter

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.5
MIN_WORKS = 3


def fetch(url, cache):
    f = cache / (re.sub(r"[^a-zA-Z0-9]+", "_", url)[-80:] + ".html")
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


def episodes(html, eng, base):
    out = []
    for b in re.split(eng["block"], html)[1:]:
        tm = re.search(eng["title"], b)
        if not tm:
            continue
        dm = re.search(eng["date"], b) if eng.get("date") else None
        um = re.search(eng["url"], b) if eng.get("url") else None
        row = {"title": tm.group(1).strip()}
        if dm:
            row["updated"] = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
        if um:
            u = um.group(1)
            row["url"] = u if u.startswith("http") else base.rstrip("/") + u
        if eng.get("free"):
            fm = re.search(eng["free"], b)
            if fm:
                # Only a stated value is recorded; absence is left unset rather than assumed (§6).
                row["access_modes"] = ["free"] if fm.group(1) == "true" else ["purchase"]
        out.append(row)
    return out


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--sites", default="adapters/webpages/sites.yaml")
    ap.add_argument("--limit", type=int, default=60)
    a = ap.parse_args()

    spec = yaml.safe_load(open(a.sites))
    engines = spec["engines"]
    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    gap = yaml.safe_load(open(a.gap)) or {}
    missing = gap.get("works_missing") or []

    grand = Counter()
    for site in spec["sites"]:
        eng = engines[site["engine"]]
        targets = [w for w in missing
                   if site["host"] in (w.get("url") or "")][:a.limit]
        if not targets:
            print(f"{site['id']:12} no works in the gap file")
            continue

        works, failed = [], []
        for tgt in targets:
            try:
                html = fetch(tgt["url"], cache)
            except urllib.error.HTTPError as e:
                failed.append((tgt["title"], f"HTTP {e.code}"))
                continue
            eps = episodes(html, eng, f"https://{site['host']}")
            if len(eps) < site.get("min_episodes", 1):
                failed.append((tgt["title"], f"{len(eps)} episodes parsed"))
                continue
            works.append({"work_title": tgt["title"], "url": tgt["url"], "episodes": eps})

        if len(works) < MIN_WORKS:
            print(f"HEALTH: {site['id']} — {len(works)} works parsed (< {MIN_WORKS}); "
                  "markup may have changed. Writing nothing for this site.", file=sys.stderr)
            continue

        L = [f"# {site['name']} ({site['publisher']}) — chapters from server-rendered work pages.",
             "# Works named by a Tier C yardstick; the platform attests the chapters.",
             "# This platform applies no 百合 tag, so nothing here establishes marketing_label.",
             "source: webpages", f"platform: {site['id']}",
             f"platform_name: {js(site['name'])}", f"publisher: {js(site['publisher'])}",
             f"engine: {site['engine']}", f"retrieved: {a.retrieved}",
             "record_type: web_work_chapters", "identification_mode: discovery-candidate",
             "works:"]
        for w in works:
            L.append(f"  - work_title: {js(w['work_title'])}")
            L.append(f"    url: {js(w['url'])}")
            L.append(f"    chapter_count: {len(w['episodes'])}")
            L.append("    chapters:")
            for e in w["episodes"]:
                L.append(f"      - title: {js(e['title'])}")
                for k in ("updated", "url"):
                    if e.get(k):
                        L.append(f"        {k}: {js(e[k])}")
                if e.get("access_modes"):
                    L.append(f"        access_modes: {js(e['access_modes'])}")
        L.append("")
        (out / f"{site['id']}.yaml").write_text("\n".join(L))

        ne = sum(len(w["episodes"]) for w in works)
        acc = Counter(m for w in works for e in w["episodes"]
                      for m in (e.get("access_modes") or []))
        grand["works"] += len(works)
        grand["chapters"] += ne
        print(f"{site['id']:12} works={len(works):3}/{len(targets):3} chapters={ne:5}"
              + (f"  access={dict(acc)}" if acc else "")
              + (f"  failed={len(failed)}" if failed else ""))

    print()
    print(f"total: {grand['works']} works, {grand['chapters']} chapters -> {out}")


if __name__ == "__main__":
    main()
