#!/usr/bin/env python3
"""百合ナビ's WEB連載中の百合漫画 list — the curated coverage yardstick (REQUIREMENTS §5).

A hand-maintained, daily-updated table of yuri works currently serialising on the web, organised by
update date, with the platform named in parentheses. Unlike Web漫画アンテナ this is already
yuri-curated, so it needs no filtering and carries no false positives — which makes it the sharper
measure of the acceptance criterion.

Its URL carries a stale 2017 date; the page itself is current. WordPress permalinks are not dates.

Tier C, discovery only (REQUIREMENTS §1). It says a work exists, where, and roughly when it
updated. It attests nothing. Output is a candidate list plus a coverage gap — the work queue.

Usage:  webyuri.py --out data/coverage --cache $YURI_CACHE/yurinavi-cache \
                   --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys, time, urllib.request
import unicodedata
from collections import Counter

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
URL = "https://yurinavi.com/2017/02/28/web_yuri/"
MIN_ROWS = 30


def fetch(cache, force=False):
    f = cache / "web_yuri.html"
    if f.exists() and not force:
        return f.read_text()
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(1.2)
    f.write_text(t)
    return t


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def parse(html):
    """Rows are `<day> <weekday> | <title> <author>(<platform>)`, grouped under ▼<n>月更新 headers."""
    out, month, day = [], None, None
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
        if not cells:
            continue
        joined = " ".join(cells)
        m = re.search(r"▼\s*(\d{1,2})\s*月更新", joined)
        if m:
            month, day = int(m.group(1)), None
            continue
        d = re.match(r"^(\d{1,2})\s", cells[0]) if cells[0] else None
        if d:
            day = int(d.group(1))
        for c in cells[1:]:
            # A work cell ends with the platform in parentheses; anything else is layout.
            w = re.match(r"^(.*?)\s*[（(]([^（()]+)[）)]\s*$", c)
            if not w or len(c) < 4:
                continue
            head, platform = w.group(1).strip(), w.group(2).strip()
            out.append({"raw": head, "platform": platform, "month": month, "day": day})
    return out


def norm(s):
    # Strip zero-width and bidi control characters: the antenna emits platform names carrying
    # U+200E/U+200F (竹コミ‎‏‎), which are invisible and silently break every comparison.
    s = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", s or "")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"""[\s\-.=、。･・!?,:;'"“”‘’()\[\]{}「」『』【】〈〉《》〔〕~〜_/\\|+*&#@]""",
                  "", s.strip().lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    rows = parse(fetch(cache, a.force))
    if len(rows) < MIN_ROWS:
        sys.exit(f"HEALTH: parsed {len(rows)} rows (< {MIN_ROWS}). Markup has probably changed; "
                 "refusing to write.")

    # Dedupe on raw text + platform; a work recurs on every date it updated.
    works, seen = [], set()
    for r in rows:
        k = (norm(r["raw"]), norm(r["platform"]))
        if k in seen:
            continue
        seen.add(k)
        works.append(r)

    covered = set()
    for f in pathlib.Path("data/source/gigaviewer").glob("*.yaml"):
        d = yaml.safe_load(f.read_text()) or {}
        for rel in d.get("releases") or []:
            covered.add(norm(rel.get("work_title")))
    kc = pathlib.Path("data/source/kadokomi/confirmed.yaml")
    if kc.exists():
        for w in (yaml.safe_load(kc.read_text()) or {}).get("works") or []:
            covered.add(norm(w.get("work_title")))

    # data/platforms.yaml is the registry of what is watched, across all adapters.
    watched = set()
    reg = pathlib.Path("data/platforms.yaml")
    if reg.exists():
        for pl in (yaml.safe_load(reg.read_text()) or {}).get("platforms") or []:
            if pl.get("watched"):
                watched.add(norm(pl.get("name")))
                for al in pl.get("aliases") or []:
                    watched.add(norm(al))

    per_plat = Counter(w["platform"] for w in works)
    on_watched = sum(n for p, n in per_plat.items() if norm(p) in watched)
    # The title and author run together in one cell; splitting them reliably needs the platform's
    # own page, so the raw string is kept verbatim rather than guessed apart (§6).
    hit = sum(1 for w in works if any(norm(w["raw"]).startswith(c) or c in norm(w["raw"])
                                      for c in covered if len(c) > 3))

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = ["# COVERAGE against 百合ナビ WEB連載中の百合漫画 — curated, so no filtering needed.",
         "# Tier C, discovery only: names a work, its platform, and roughly when it updated.",
         "# Attests nothing (REQUIREMENTS §1). This is the work queue for the §5 acceptance",
         "# criterion. `raw` holds title+author unsplit; separating them needs the platform page.",
         "source: yurinavi-webyuri", "role: coverage-yardstick", f"retrieved: {a.retrieved}",
         "record_type: coverage_gap", f"works_listed: {len(works)}",
         f"platforms_total: {len(per_plat)}",
         f"platforms_watched: {len([p for p in per_plat if norm(p) in watched])}",
         f"works_on_watched_platforms: {on_watched}",
         "platforms:"]
    for p, n in per_plat.most_common():
        L.append(f"  - platform: {json.dumps(p, ensure_ascii=False)}")
        L.append(f"    works: {n}")
        L.append(f"    watched: {str(norm(p) in watched).lower()}")
    L.append("works:")
    for w in sorted(works, key=lambda w: (w["platform"], w["raw"])):
        L.append(f"  - raw: {json.dumps(w['raw'], ensure_ascii=False)}")
        L.append(f"    platform: {json.dumps(w['platform'], ensure_ascii=False)}")
        if w["month"]:
            L.append(f"    last_update_seen: {w['month']:02d}-{(w['day'] or 0):02d}")
        L.append(f"    watched_platform: {str(norm(w['platform']) in watched).lower()}")
    L.append("")
    (out / "yurinavi-webyuri.yaml").write_text("\n".join(L))

    print(f"works listed      : {len(works)} on {len(per_plat)} platforms")
    print(f"PLATFORM COVERAGE : {len([p for p in per_plat if norm(p) in watched])}/{len(per_plat)}")
    print(f"                    {on_watched}/{len(works)} works "
          f"({100*on_watched/max(len(works),1):.1f}%) on a watched platform")
    print()
    print("largest unwatched platforms:")
    for p, n in per_plat.most_common():
        if norm(p) not in watched and n >= 3:
            print(f"  {n:4}  {p}")


if __name__ == "__main__":
    main()
