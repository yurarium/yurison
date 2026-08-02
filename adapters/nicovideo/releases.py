#!/usr/bin/env python3
"""ニコニコ漫画 — work-level update dates (REQUIREMENTS §5).

This platform was recorded as structurally unusable. That was wrong, and the error is worth
stating plainly: the blocker said "work pages carry no per-episode date, so a release cannot be
placed on a timeline", and concluded that reaching it would need one fetch per episode. Both the
observation and the conclusion were wrong in the way that matters.

The observation: `episode_item` markup really does carry no date — only `data-number`, a page
count and view counters. But the date is on the page, in `div.meta_info`, at WORK level:

    2026年07月23日更新   2024年10月24日開始   [ 4話 無料 ]   [4コママンガ]

The conclusion: the feed's unit for an unattested update is "this work updated, on this date" —
that is what the comparators state and what the feed shows. Work level is therefore sufficient,
and it costs one fetch per work like カドコミ and FUZ, not one per episode.

Checked against the comparator before building: 百合ナビ claimed 魔女まじょS-WITCH updated
2026-07-23, and the page says 2026年07月23日更新. It is server-rendered, so no browser is needed.

What this establishes and what it does not:

- `updated` is the platform's own statement about the work, so a release built from it is
  **attested** rather than claimed. It is not per-chapter: we learn that the work updated, never
  which chapter, so `ep` is empty and the update kind stays `unknown` unless something else fills
  it in.
- `開始` gives a genuine serialisation start date — the first positive evidence of `new-series`
  this project has had from a platform.
- `[ N話 無料 ]` states how many episodes are free.
- ニコニコ remains a poor `preferred` source: image quality is worse than the origin platforms and
  it syndicates heavily (overlap 0.71). This makes it a fallback for works reachable nowhere else,
  which is exactly what its 65 exclusive works are.

Never stored: episode thumbnails, synopsis text, or page images (§2).

Usage:  releases.py --works data/coverage/webcomics-works.yaml --out data/source/nicovideo \
                    --cache ~/workspace/nico-cache --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys, time, urllib.error, urllib.request
from collections import Counter

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
WORK = "https://manga.nicovideo.jp/comic/{cid}"
PAUSE = 1.5
MIN_WORKS = 20


def fetch(cid, cache, max_age_days=1):
    f = cache / f"{cid}.html"
    if f.exists() and (time.time() - f.stat().st_mtime) / 86400 < max_age_days:
        return f.read_text()
    req = urllib.request.Request(WORK.format(cid=cid), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t


def iso(y, m, d):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def parse(html):
    """Read div.meta_info. Absent or unparsable means no date — never a guessed one (§6)."""
    m = re.search(r'class="meta_info"(.*?)</div>', html, re.S)
    if not m:
        return None
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
    out = {}
    u = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日更新", txt)
    s = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日開始", txt)
    if u:
        out["updated"] = iso(*u.groups())
    if s:
        out["started"] = iso(*s.groups())
    n = re.search(r"\[\s*(\d+)話\s*(無料)?\s*\]", txt)
    if n:
        out["episode_count"] = int(n.group(1))
        if n.group(2):
            out["free_episodes"] = int(n.group(1))
    fm = re.search(r"\[([^\]]*マンガ)\]", txt)
    if fm:
        out["format"] = fm.group(1).strip()
    t = re.search(r"<title>([^<]*)</title>", html)
    if t:
        # ニコニコ states its works as "タイトル / 作者", which is a cleaner identity than the
        # comparator cell that named the work for us.
        head = t.group(1).split(" - ")[0].strip()
        # The title element is "タイトル / 作者 おすすめ無料漫画 - ニコニコ漫画". The trailing
        # editorial phrase varies (おすすめ漫画 / おすすめ無料漫画) and was landing in the author
        # field — "むちゃ おすすめ漫画".
        head = re.sub(r"\s*おすすめ(無料)?漫画\s*$", "", head).strip()
        if "/" in head:
            out["title"], _, out["author"] = (x.strip() for x in head.partition("/"))
        else:
            out["title"] = head
    # The work page renders the first few episodes AND the latest one, each with its title and a
    # /watch/ link. The 更新 date in meta_info is the date THAT episode appeared, so naming it costs
    # nothing and turns a work-level row into one that says which chapter — which is what a reader
    # looking at the page sees. Only the newest is emitted: the others carry no date of their own.
    sec = html[html.find('id="episode_list"'):]
    best = None
    for b in re.split(r'<li class="episode_item">', sec)[1:]:
        n = re.search(r'data-number="(\d+)"', b)
        ti = re.search(r'<div class="title"><a href="(/watch/mg\d+)">([^<]*)</a>', b)
        if n and ti and (best is None or int(n.group(1)) > best[0]):
            best = (int(n.group(1)), ti.group(2).strip(), ti.group(1))
    if best:
        out["latest_episode"] = best[1]
        out["latest_episode_url"] = "https://manga.nicovideo.jp" + best[2]

    ch = re.search(r'/official/([a-z0-9_]+)/"[^>]*>\s*<div class="mg_banner">', html)
    if ch:
        out["channel_slug"] = ch.group(1)
    return out or None


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit", type=int, default=200)
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    src = yaml.safe_load(open(a.works)) or {}
    targets = {}
    for w in src.get("candidates") or []:
        for u in [w.get("url", "")] + (w.get("urls") or []):
            m = re.search(r"manga\.nicovideo\.jp/comic/(\d+)", u or "")
            if m:
                targets.setdefault(m.group(1), w.get("title"))
    # Works that reach us only through 百合ナビ have no URL and so no id. Ids found by external
    # search live here; without them a work on a platform we watch stays an unclassified claim.
    res = pathlib.Path("data/source/nicovideo/resolved.yaml")
    if res.exists():
        for w in (yaml.safe_load(res.read_text()) or {}).get("works") or []:
            if w.get("comic_id"):
                targets.setdefault(str(w["comic_id"]), w.get("title"))

    targets = dict(list(targets.items())[: a.limit])
    if not targets:
        sys.exit("no ニコニコ漫画 work ids found")

    works, failed = [], []
    for cid, title in targets.items():
        try:
            d = parse(fetch(cid, cache))
        except urllib.error.HTTPError as e:
            failed.append((title, f"HTTP {e.code}"))
            continue
        except Exception as e:                                  # noqa: BLE001
            failed.append((title, type(e).__name__))
            continue
        if not d or not d.get("updated"):
            failed.append((title, "no meta_info date"))
            continue
        d["comic_id"] = cid
        d["url"] = WORK.format(cid=cid)
        d.setdefault("title", title)
        works.append(d)

    if len(works) < MIN_WORKS:
        sys.exit(f"HEALTH: resolved {len(works)} works (< {MIN_WORKS}). The meta_info markup may "
                 "have changed. Refusing to write.")

    L = ["# ニコニコ漫画 work-level update dates, read from div.meta_info on each work page.",
         "#",
         "# WORK level, not chapter level: the platform states that the work updated on a date, and",
         "# never which chapter. So these attest an update and nothing about its contents — no",
         "# chapter title, no number. Recorded as attested because the platform itself says it.",
         "#",
         "# `started` is a real serialisation start date, the first positive new-series evidence",
         "# any platform here has given us.",
         "source: webpages", "platform: nicovideo", "platform_name: ニコニコ漫画",
         f"retrieved: {a.retrieved}", "record_type: work_update_dates",
         "identification_mode: discovery-candidate",
         "granularity: work",
         f"works_resolved: {len(works)}", "works:"]
    for w in sorted(works, key=lambda w: w["updated"], reverse=True):
        L.append(f"  - work_title: {js(w['title'])}")
        for k in ("author", "url", "comic_id", "updated", "started", "episode_count",
                  "free_episodes", "format", "channel_slug", "latest_episode",
                  "latest_episode_url"):
            if w.get(k) not in (None, ""):
                L.append(f"    {k}: {js(w[k])}")
    L.append("")
    (out / "nicovideo.yaml").write_text("\n".join(L))

    dated = sum(1 for w in works if w.get("updated"))
    started = sum(1 for w in works if w.get("started"))
    freed = sum(1 for w in works if w.get("free_episodes"))
    print(f"works targeted : {len(targets)}")
    print(f"works resolved : {len(works)}  ({dated} dated, {started} with a start date)")
    print(f"free-episode counts stated : {freed}")
    if failed:
        print(f"failed         : {len(failed)}  {Counter(r for _, r in failed).most_common(3)}")
    print(f"written        : {out}/nicovideo.yaml")


if __name__ == "__main__":
    main()
