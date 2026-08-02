#!/usr/bin/env python3
"""Reach the series nothing else reached, one at a time (REQUIREMENTS §5).

The platform adapters work by platform, which is the right shape for the bulk and leaves a residue:
a work whose URL sits in the candidate list on a host with a working adapter, and which the adapter
never fetched anyway. 散らないで菊 is on コミックゼノン, its episode page exposes the series feed,
and the GigaViewer adapter ran over that platform without ever asking for it.

Rather than keep debugging why each platform pass skipped each work, this takes the list of works
we hold nothing for and tries every route we have against each, in order of cost:

  1. GigaViewer  — the episode page links to /atom/series/<id>, which is a dated feed.
  2. comici      — the series page carries series-eplist-item markup with dates.
  3. markup      — a plain fetch, parsed by the proven strategies.
  4. render      — headless chromium, for pages that build their list in JavaScript.

A work is reported unreached only after all four fail, which is a much stronger statement than any
one adapter declining to pick it up.

Usage:  releases.py --works data/coverage/remaining.yaml --out data/source/webpages \
                    --cache ~/workspace/remaining-cache --retrieved 2026-08-01
"""
import argparse, html as _html, json, pathlib, re, subprocess, sys, time
import urllib.error, urllib.request
from collections import Counter

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "recon"))
from extract import CHAPTERISH, try_jsonld, try_markup, try_next, try_pairs  # noqa: E402

UA = "Mozilla/5.0 (compatible; yurarium/0.1; +https://yurarium.github.io/)"
CHROME = next((c for c in ("/snap/bin/chromium", "/usr/bin/chromium",
                           "/usr/bin/chromium-browser", "/usr/bin/google-chrome")
               if pathlib.Path(c).exists()), None)
PAUSE = 1.0
MIN_EPISODES = 1

COMICI_BLOCK = re.compile(r'data-e2e="eli"')
COMICI_ROW = re.compile(
    r'data-e2e="eliTitle">([^<]+)<.*?series-eplist-item-meta-date">(\d{4})/(\d{1,2})/(\d{1,2})<',
    re.S)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.read(3_000_000).decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return ""
    finally:
        time.sleep(PAUSE)


def render(url, cache):
    key = re.sub(r"[^A-Za-z0-9]", "_", url)[-110:]
    f = cache / f"{key}.html"
    if f.exists() and (time.time() - f.stat().st_mtime) / 86400 < 2:
        return f.read_text()
    if not CHROME:
        return ""
    try:
        out = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=9000", f"--user-agent={UA}", "--dump-dom", url],
            capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return ""
    time.sleep(PAUSE)
    h = out.stdout or ""
    if len(h) > 2000:
        f.write_text(h)
    return h


DIAG = {}


def from_giga(html, page_url):
    """The host comes from the page we fetched, not from the link. Some installs write the feed
    link relative (/atom/series/<id>), and requiring the absolute form meant the route silently
    declined on コミックゼノン and 一迅プラス — pages whose feed link I had checked by hand."""
    m = re.search(r"/atom/series/(\d+)", html)
    if not m:
        return []
    base = re.match(r"https?://([^/]+)", page_url)
    if not base:
        return []
    base = base.group(1)
    xml = get(f"https://{base}/atom/series/{m.group(1)}")
    if xml and "<entry>" not in xml:
        # The feed exists and lists nothing. 散らないで菊 is a コミックゼノン漫画大賞 entry whose
        # series feed carries a title and no episodes. Not our failure to reach it — the platform
        # publishes no episode list for it.
        ti = re.search(r"<title>([^<]*)</title>", xml)
        DIAG[page_url] = f"platform's series feed is empty ({ti.group(1) if ti else 'no title'})"
    # The free-only variant of the same feed gives per-chapter access, and every entry carries its
    # author — both were being discarded, which is why works rescued by this adapter arrived with a
    # date and nothing else.
    try:
        free_ids = set(re.findall(r'<link href="([^"]+)"/>',
                                  get(f"https://{base}/atom/series/{m.group(1)}?free_only=1")))
    except Exception:                                              # noqa: BLE001
        free_ids = set()
    out = []
    for b in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        t = re.search(r"<title>([^<]*)</title>", b)
        u = re.search(r"<updated>([^<]*)</updated>", b)
        l = re.search(r'<link href="([^"]+)"', b)
        au = re.search(r"<author>\s*<name>([^<]*)</name>", b, re.S)
        if t and u:
            row = {"title": _html.unescape(t.group(1).strip()), "updated": u.group(1)[:10]}
            if au:
                row["author"] = _html.unescape(au.group(1).strip())
            if free_ids and l:
                row["access_modes"] = ["free"] if l.group(1) in free_ids else ["purchase"]
            out.append(row)
    return out


def from_comici(html):
    if not COMICI_BLOCK.search(html):
        return []
    out = []
    for b in re.split(r'(?=<div data-e2e="eli")', html)[1:]:
        m = COMICI_ROW.search(b)
        if m:
            row = {"title": _html.unescape(m.group(1).strip()),
                   "updated": f"{int(m.group(2)):04d}-{int(m.group(3)):02d}-{int(m.group(4)):02d}"}
            # Two badge forms across comici installs: 竹コミ classes it (…access-text … mode-free),
            # 花とゆめ+ puts the literal 無料 in the access element and an SVG lock on paid ones.
            if re.search(r'series-eplist-item-access-text[^"]*mode-free'
                         r'|series-eplist-item-access[^>]*>\s*(?:<[^>]*>\s*)*無料', b):
                row["access_modes"] = ["free"]
            elif re.search(r'series-eplist-item-access-paid|mode-paid'
                           r'|series-eplist-item-access[^>]*>\s*(?:<[^>]*>\s*)*<path', b):
                row["access_modes"] = ["purchase"]
            out.append(row)
    return out


def from_generic(html):
    got = try_jsonld(html) or try_next(html)
    if len(got) < 2:
        got, _ = try_markup(html)
    if len(got) < 2:
        got = try_pairs(html)
    out, seen = [], set()
    for g in got:
        t = re.sub(r"\s+", " ", g.get("title") or "").strip()
        d = g.get("date")
        if not d or not CHAPTERISH.search(t):
            continue
        m = CHAPTERISH.search(t)
        lab = re.split(r"\s\d{4}[-/.年]|\s+\d{2,}(?:\s|$)", t[m.start(): m.end() + 40])[0].strip()
        if lab and (lab, d) not in seen:
            seen.add((lab, d))
            out.append({"title": lab, "updated": d})
    return out


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    rows, how, failed = [], Counter(), []
    for w in (yaml.safe_load(open(a.works)) or {}).get("works") or []:
        url = w.get("url")
        if not url:
            failed.append((w.get("title"), "no URL"))
            continue
        html = get(url)
        eps, route, page_author = [], None, None
        if html:
            # comici states the author in the page title as "作品 - 作者 | プラットフォーム", the same
            # place the webpages adapter reads it. This route was ignoring it, so works rescued here
            # arrived without one while the same platform's other works had theirs.
            _au = re.search(r"<title>[^<|]*?\s+-\s+([^<|]+?)\s*\|", html)
            if _au:
                page_author = _html.unescape(_au.group(1).strip())
            for name, fn in (("gigaviewer", lambda h: from_giga(h, url)),
                             ("comici", from_comici), ("markup", from_generic)):
                eps = fn(html)
                if len(eps) >= MIN_EPISODES:
                    route = name
                    break
        if not eps:
            rh = render(url, cache)
            if rh:
                eps = from_generic(rh)
                route = "rendered" if eps else None
        if not eps:
            failed.append((w.get("title"),
                           DIAG.get(url) or ("page did not load" if not html else
                                             "no route yielded a dated chapter list")))
            continue
        how[route] += 1
        if page_author:
            for e in eps:
                e.setdefault("author", page_author)
        rows.append({"work_title": w.get("title"), "url": url, "platform": w.get("platform"),
                     "route": route, "author": page_author, "episodes": eps})

    if rows:
        L = ["# Series reached individually after every platform pass had left them out.",
             "#",
             "# Four routes tried per work, cheapest first: the GigaViewer per-series feed linked",
             "# from an episode page, comici's series-eplist markup, a plain fetch parsed by the",
             "# usual strategies, and finally a rendered DOM. The route used is recorded per work.",
             "#",
             "# No genre label is established here (DEFINITIONS §4).",
             "source: webpages", "platform: remaining", "platform_name: \"\"",
             f"retrieved: {a.retrieved}", "record_type: web_work_chapters",
             "identification_mode: discovery-candidate", "works:"]
        for r in rows:
            L.append(f"  - work_title: {js(r['work_title'])}")
            if r.get("author"):
                L.append(f"    author: {js(r['author'])}")
            L.append(f"    url: {js(r['url'])}")
            if r.get("platform"):
                L.append(f"    platform_name: {js(r['platform'])}")
            L.append(f"    route: {js(r['route'])}")
            L.append(f"    chapter_count: {len(r['episodes'])}")
            L.append("    chapters:")
            for e in r["episodes"]:
                L.append(f"      - title: {js(e['title'])}")
                L.append(f"        updated: {e['updated']}")
                if e.get("author"):
                    L.append(f"        author: {js(e['author'])}")
                if e.get("access_modes"):
                    L.append(f"        access_modes: {js(e['access_modes'])}")
                if r["route"] in ("markup", "rendered"):
                    L.append(f"        date_basis: {'rendered' if r['route']=='rendered' else 'heuristic'}")
        L.append("")
        (out / "remaining.yaml").write_text("\n".join(L))

    print(f"works attempted : {len(rows) + len(failed)}")
    print(f"reached         : {len(rows)}  {dict(how)}")
    if failed:
        print(f"unreached       : {len(failed)}")
        for t, r in failed:
            print(f"    - {str(t)[:34]:36} {r}")


if __name__ == "__main__":
    main()
