#!/usr/bin/env python3
"""Generic chapter extraction for platforms with no shared engine (REQUIREMENTS §5, §6).

The long tail's 21 markup-only hosts have no engine in common, which was the argument for leaving
them alone. But they do not need one: what they have in common is the *shape* of a chapter list —
repeated blocks, each carrying a date and a chapter-like label. That is enough to parse without
knowing anything about a particular site's markup.

So this reuses the strategies proven per host in `data/coverage/extract.yaml` rather than carrying
a selector registry. A host is only processed if the second reconnaissance pass demonstrated that
a strategy returns dated chapters from it, so nothing here is speculative parsing.

The cost of generality is confidence, and it is paid explicitly:

- Every release is written with `date_basis: heuristic` and `date_confidence: low`. These are not
  a publisher's stated field, they are a pattern matched in a page.
- A block is only a chapter if it carries a chapter-like label (第N話, #N, episode N, 最終話…).
  A bare date is skipped, because a bare date on a manga page is usually the 単行本 release —
  the trap the first reconnaissance pass fell into on ガンガンONLINE.
- Blocks reading as volume announcements (発売, 刊行, 単行本, 巻) are dropped unless they also
  carry a chapter label.
- Anything that yields fewer than `MIN_EPISODES` is discarded rather than written thin.

Usage:  releases.py --works data/coverage/webcomics-works.yaml \
                    --extract data/coverage/extract.yaml --out data/source/webpages \
                    --cache $YURI_CACHE/generic-cache --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys, time, unicodedata, urllib.error, urllib.request
from collections import Counter

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "recon"))
from extract import CHAPTERISH, norm_date, try_jsonld, try_markup, try_next, try_nuxt  # noqa: E402

# The compatible-token form. Several hosts (firecross.jp, www.yomonga.com) reject a bare product
# token outright but serve this, and it is the long-standing convention — "Mozilla/5.0 (compatible;
# Googlebot/2.1; +http://...)" has the same shape. It still names us and still links to the project,
# so it is not the thing refused for pixivコミック: that would have meant claiming to be a browser
# in order to pass an access control. This claims to be us, in the format the web expects.
UA = ("Mozilla/5.0 (compatible; yurarium/0.1; bibliographic database; "
      "+https://yurarium.github.io/)")
PAUSE = 1.5
MIN_EPISODES = 2
STRATEGIES = {"jsonld": try_jsonld, "next": try_next, "nuxt": try_nuxt}


def clean(s):
    s = re.sub(r"[​-‏‪-‮﻿]", "", s or "")
    return unicodedata.normalize("NFKC", s).strip()


def fetch(url, cache, max_age_days=1):
    key = re.sub(r"[^A-Za-z0-9]", "_", url)[-120:]
    f = cache / f"{key}.html"
    if f.exists() and (time.time() - f.stat().st_mtime) / 86400 < max_age_days:
        return f.read_text()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read(1_500_000).decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t


def episodes(html, strategy):
    if strategy in STRATEGIES:
        got = STRATEGIES[strategy](html)
    else:
        got, _ = try_markup(html)
    out, seen = [], set()
    for g in got:
        title = re.sub(r"\s+", " ", g.get("title") or "").strip()
        date = g.get("date")
        if not date or not CHAPTERISH.search(title):
            continue
        # The label is buried in a run of scraped text that also carries the date and whatever
        # counters the site prints next to it — マンガPark yields "第1話① 6178 67 2023/1/24".
        # Keep the chapter part and cut at the first thing that is plainly not part of a title:
        # a date, or a bare run of three or more digits, which is a view or comment count.
        m = CHAPTERISH.search(title)
        label = title[max(0, m.start() - 4): m.end() + 40]
        label = re.split(r"\s\d{4}[-/.年]\d{1,2}|\s\d{3,}\b", label)[0]
        # Markup in the window means we ran off the end of the episode list. The +40 is speculative
        # — it exists to catch a subtitle — and every episode but the LAST is bounded by the next
        # one, so the last is the only one that can over-run. GANMA! prints its author block
        # straight after the list, and 飛野さんのバカ's fifth episode came out as
        # '配信 第5話 作家 <img alt="author avatar" loading="la', stopping only at the character cap
        # while its four siblings were a clean '配信 第N話'.
        # A tag is never part of a chapter title, so its presence is proof the tail is not a
        # subtitle. Drop the speculative part rather than trying to clean it: what follows an
        # over-run is another section of the page, not a damaged version of what we wanted.
        if "<" in label:
            label = title[max(0, m.start() - 4): m.end()]
        label = label.strip(" 　·・|/-")
        k = (label, date)
        if k in seen:
            continue
        seen.add(k)
        out.append({"title": label, "updated": date})
    return out


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", required=True)
    ap.add_argument("--extract", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit-per-host", type=int, default=40)
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    # Hosts already served by a real engine are skipped — a proven adapter beats a heuristic.
    giga = {p["host"] for p in yaml.safe_load(
        open("adapters/gigaviewer/platforms.yaml"))["platforms"]}
    web = {s["host"] for s in yaml.safe_load(
        open("adapters/webpages/sites.yaml"))["sites"]}
    # Hosts with a dedicated adapter of their own. A heuristic must never shadow a parser that
    # reads the platform's own stated fields — comic-walker.com reached here as
    # "電撃ツイッターマガジン" and was re-scraping カドコミ, whose adapter already does it properly.
    web |= {"comic-walker.com", "comic-fuz.com", "manga.nicovideo.jp"}

    plans = {}
    for p in yaml.safe_load(open(a.extract))["platforms"]:
        if p["host"] in giga or p["host"] in web:
            continue
        if p.get("strategy") in ("markup", "jsonld", "next", "nuxt"):
            plans[p["host"]] = {"platform": p["platform"], "strategy": p["strategy"]}
    if not plans:
        sys.exit("no hosts with a proven extraction strategy")

    src = yaml.safe_load(open(a.works)) or {}
    targets = {h: [] for h in plans}
    for w in src.get("candidates") or []:
        for u in [w.get("url", "")] + (w.get("urls") or []):
            m = re.match(r"https?://([^/]+)", u or "")
            if m and m.group(1) in targets and len(targets[m.group(1)]) < a.limit_per_host:
                targets[m.group(1)].append({"title": w.get("title"), "url": u})
                break

    written = []
    for host, plan in plans.items():
        rows, failed = [], 0
        for t in targets.get(host, []):
            try:
                eps = episodes(fetch(t["url"], cache), plan["strategy"])
            except (urllib.error.HTTPError, urllib.error.URLError, OSError):
                failed += 1
                continue
            if len(eps) >= MIN_EPISODES:
                rows.append({"work_title": t["title"], "url": t["url"], "episodes": eps})
        if not rows:
            print(f"{plan['platform'][:20]:22} nothing parsed ({failed} failed) — writing nothing")
            continue
        pid = re.sub(r"[^a-z0-9]+", "-", host.lower()).strip("-")
        L = [f"# {plan['platform']} — chapters extracted heuristically from work pages.",
             "#",
             "# NOT a publisher-stated field. Blocks carrying a date and a chapter-like label were",
             "# matched in the page; the strategy was proven for this host in",
             "# data/coverage/extract.yaml before being run. Every release carries",
             "# date_basis: heuristic and date_confidence: low so it is never mistaken for the",
             "# kind of statement GigaViewer or FUZ make.",
             "#",
             "# No 百合 label is established here (DEFINITIONS §4); works are named by the Tier C",
             "# yardsticks and this attests only their chapters.",
             "source: webpages", f"platform: {pid}", f"platform_name: {js(plan['platform'])}",
             "publisher: \"\"", f"retrieved: {a.retrieved}", "record_type: web_work_chapters",
             "identification_mode: discovery-candidate",
             f"extraction: {plan['strategy']}", "date_basis: heuristic",
             "date_confidence: low", "works:"]
        for w in rows:
            L.append(f"  - work_title: {js(w['work_title'])}")
            L.append(f"    url: {js(w['url'])}")
            L.append(f"    chapter_count: {len(w['episodes'])}")
            L.append("    chapters:")
            for e in w["episodes"]:
                L.append(f"      - title: {js(e['title'])}")
                L.append(f"        updated: {e['updated']}")
                L.append("        date_basis: heuristic")
        L.append("")
        (out / f"generic-{pid}.yaml").write_text("\n".join(L))
        n = sum(len(w["episodes"]) for w in rows)
        written.append((plan["platform"], len(rows), n))
        print(f"{plan['platform'][:20]:22} works={len(rows):3} chapters={n:4}"
              f"{f'  failed={failed}' if failed else ''}")

    print(f"\n{len(written)} platform(s), {sum(w for _, w, _ in written)} works, "
          f"{sum(c for _, _, c in written)} chapters -> {out}")


if __name__ == "__main__":
    main()
