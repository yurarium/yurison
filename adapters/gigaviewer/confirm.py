#!/usr/bin/env python3
"""Confirm discovery candidates against GigaViewer platforms (REQUIREMENTS §1).

The second half of the discovery architecture, which until now existed only for カドコミ. 百合ナビ
names a work and links to it; this asks the platform what it actually is. A Tier C source may say
a work exists and nothing more — the fields come from the publisher.

Why it matters more than it sounds: one-shots are announced once and never mentioned again, and
they run on platforms that apply no genre label at all, so nothing in Tier A or B will ever
volunteer them. Editorial coverage is the only route in, and coverage without confirmation is a
name in a queue rather than a release in the feed.

Route, in two requests per candidate:

  /episode/<code>          the article's own link. Its <title> is "作品 - 作者 / 話 | プラット",
                           which gives work and author, and its markup carries the series id as a
                           link to that series' feed.
  /atom/series/<id>        every episode with a date.

`is_oneshot` is then read rather than guessed: a series whose feed holds exactly one episode is a
one-shot, which is what 読み切り means. A series with more is a serial the article happened to
describe, and saying so is the point of confirming.

Output is the same `web_work_chapters` shape the per-series fetcher writes, so the build reads it
without changes.

Usage:  confirm.py --queue data/queue/yurinavi.yaml --out data/source/gigaviewer \
                   --cache ~/workspace/giga-series-cache --retrieved 2026-08-01
"""
import argparse, html as _html, json, pathlib, re, sys, time, urllib.error, urllib.request
from collections import Counter, defaultdict

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.2


def fetch(url, cache, max_age_days=1):
    key = re.sub(r"[^A-Za-z0-9]", "_", url)[-120:]
    f = cache / key
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


def identity(html):
    """work, author from the episode page's own title element."""
    m = re.search(r"<title>([^<]*)</title>", html)
    if not m:
        return None, None
    head = _html.unescape(m.group(1)).split("|")[0].strip()
    head = head.split("/")[0].strip()          # drop the episode part
    if " - " in head:
        w, _, a = head.partition(" - ")
        return w.strip(), a.strip()
    return head, None


def episodes(xml):
    out = []
    for b in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        t = re.search(r"<title>([^<]*)</title>", b)
        u = re.search(r"<updated>([^<]*)</updated>", b)
        l = re.search(r'<link href="([^"]+)"', b)
        if t and u:
            out.append({"title": _html.unescape(t.group(1).strip()),
                        "updated": u.group(1)[:10],
                        "url": l.group(1) if l else ""})
    return out


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    a = ap.parse_args()

    reg = {p["id"]: p for p in yaml.safe_load(
        open("adapters/gigaviewer/platforms.yaml"))["platforms"]}
    cands = (yaml.safe_load(open(a.queue)) or {}).get("candidates") or []

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    by_platform, stats, failed = defaultdict(list), Counter(), []
    for c in cands:
        pid, code = c.get("platform"), c.get("platform_code")
        if not pid or not code or pid not in reg:
            stats["not on a GigaViewer platform"] += 1
            continue
        host = reg[pid]["host"]
        try:
            ep = fetch(f"https://{host}/episode/{code}", cache)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            failed.append((c.get("work_title"), type(e).__name__))
            continue
        work, author = identity(ep)
        sid = re.search(r"/atom/series/(\d+)", ep)
        if not sid:
            failed.append((c.get("work_title"), "no series feed on the episode page"))
            continue
        try:
            eps = episodes(fetch(f"https://{host}/atom/series/{sid.group(1)}", cache))
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            failed.append((c.get("work_title"), type(e).__name__))
            continue
        if not eps:
            failed.append((c.get("work_title"), "series feed empty"))
            continue
        is_oneshot = len(eps) == 1
        stats["confirmed"] += 1
        stats["one-shot" if is_oneshot else "serial"] += 1
        by_platform[pid].append({
            "work_title": work or c.get("work_title"), "author": author,
            "series_id": sid.group(1), "url": f"https://{host}/episode/{code}",
            "is_oneshot": is_oneshot, "episodes": eps,
            "discovered_via": {"source": c.get("source"), "signal": c.get("signal"),
                               "article": c.get("url"), "headline": c.get("headline")},
        })

    for pid, works in by_platform.items():
        p = reg[pid]
        L = [f"# {p['name']} — works confirmed from the discovery queue.",
             "#",
             "# 百合ナビ named these and linked to them; the platform supplies the fields. Tier C",
             "# names a work and establishes nothing about it (REQUIREMENTS §1).",
             "#",
             "# is_oneshot is read, not guessed: a series feed holding exactly one episode is a",
             "# one-shot. These platforms apply no genre label, so nothing here establishes",
             "# marketing_label (DEFINITIONS §4).",
             "source: gigaviewer", f"platform: {pid}", f"platform_name: {js(p['name'])}",
             f"publisher: {js(p.get('publisher', ''))}", f"retrieved: {a.retrieved}",
             "record_type: web_work_chapters", "identification_mode: discovery-candidate",
             f"works_confirmed: {len(works)}", "works:"]
        for w in works:
            L.append(f"  - work_title: {js(w['work_title'])}")
            if w.get("author"):
                L.append(f"    author: {js(w['author'])}")
            L.append(f"    url: {js(w['url'])}")
            L.append(f"    series_id: {js(w['series_id'])}")
            L.append(f"    is_oneshot: {'true' if w['is_oneshot'] else 'false'}")
            L.append("    discovered_via:")
            for k, v in (w["discovered_via"] or {}).items():
                if v:
                    L.append(f"      {k}: {js(v)}")
            L.append(f"    chapter_count: {len(w['episodes'])}")
            L.append("    chapters:")
            for e in w["episodes"]:
                L.append(f"      - title: {js(e['title'])}")
                L.append(f"        updated: {e['updated']}")
                if e.get("url"):
                    L.append(f"        url: {js(e['url'])}")
        L.append("")
        (out / f"{pid}-confirmed.yaml").write_text("\n".join(L))

    print(f"candidates              : {len(cands)}")
    for k, v in stats.most_common():
        print(f"  {k:22}: {v}")
    if failed:
        print(f"  failed                : {len(failed)}  {failed[:3]}")
    print(f"written                 : {len(by_platform)} file(s) -> {out}")


if __name__ == "__main__":
    main()
