#!/usr/bin/env python3
"""Fill the fields a row is missing, from the page a reader would open (REQUIREMENTS §5).

The platform adapters run per platform and each does one job well. What they leave behind is not a
platform gap but a row gap: a single 読切 reached through a 百合ナビ link on a host whose adapter
only ever walked that host's serialised titles, and which therefore arrived with a date, a chapter
name and nothing else. 吸血少女とウンディーネ on コミック アース・スター is one row. So is 夕子先輩は育て
られない on 一迅プラス. Neither is worth a platform pass; both are worth one fetch.

This takes the rows the build says are incomplete and goes to their page, by the routes that are
already proven:

  gigaviewer-feed  The episode page links /atom/series/<id> even for a one-shot, which is a
                   one-entry series. Fetching that feed and its ?free_only=1 variant gives the
                   access state, and every entry carries its author.
  title-tail       フラコミlike! writes <title> as 作品 | いつでも無料 | フラコミlike! | 空木帆子 —
                   the author is the last segment and the access is stated in the second. Read
                   both only when the platform's own name is in the expected position, so a
                   differently-shaped title yields nothing rather than a wrong name.

Nothing is guessed. A route that does not fire leaves the field empty, which is the honest state.

Usage:  fields.py --gaps data/coverage/field-gap-rows.yaml --out data/source/webpages \
                  --retrieved 2026-08-02
"""
import argparse, html as _html, json, pathlib, re, sys, time
import urllib.error, urllib.request
from collections import Counter, defaultdict

import yaml

UA = "Mozilla/5.0 (compatible; yurarium/0.1; +https://yurarium.github.io/)"
PAUSE = 1.0

ATOM_SERIES = re.compile(r"/atom/series/(\d+)")
ENTRY = re.compile(r"<entry>(.*?)</entry>", re.S)
E_TITLE = re.compile(r"<title>([^<]*)</title>")
E_UPDATED = re.compile(r"<updated>([^<]*)</updated>")
E_LINK = re.compile(r'<link href="([^"]+)"')
E_AUTHOR = re.compile(r"<author>\s*<name>([^<]*)</name>", re.S)
TITLE = re.compile(r"<title>([^<]*)</title>", re.S)

# 作品 | いつでも無料 | フラコミlike! | 空木帆子 — four segments, the platform third and the author
# last. Requiring the platform name in place is what keeps this from reading any old title tail.
TITLE_TAIL = {
    "flowercomics.jp": ("フラコミlike!", {"いつでも無料": ["free"]}),
}


def get(url, limit=3_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.read(limit).decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return ""
    finally:
        time.sleep(PAUSE)


def host_of(u):
    m = re.match(r"https?://([^/]+)", u or "")
    return m.group(1).lower() if m else ""


def gigaviewer_feed(url, html):
    """Chapters with author and access, from the series feed the page links."""
    m = ATOM_SERIES.search(html or "")
    if not m:
        return None, []
    host = host_of(url)
    xml = get(f"https://{host}/atom/series/{m.group(1)}")
    if not xml:
        return None, []
    free = set(E_LINK.findall(get(f"https://{host}/atom/series/{m.group(1)}?free_only=1") or ""))
    author, out = None, []
    for b in ENTRY.findall(xml):
        t, u = E_TITLE.search(b), E_UPDATED.search(b)
        if not (t and u):
            continue
        au, ln = E_AUTHOR.search(b), E_LINK.search(b)
        if au and not author:
            author = _html.unescape(au.group(1)).strip()
        row = {"title": _html.unescape(t.group(1)).strip(), "updated": u.group(1)[:10]}
        if free and ln:
            row["access_modes"] = ["free"] if ln.group(1) in free else ["purchase"]
        out.append(row)
    return author, out


def title_tail(url, html):
    """Author and access from a <title> whose shape the platform keeps."""
    spec = TITLE_TAIL.get(host_of(url))
    if not spec:
        return None, None
    plat, access_words = spec
    m = TITLE.search(html or "")
    if not m:
        return None, None
    parts = [s.strip() for s in _html.unescape(m.group(1)).split("|")]
    if len(parts) < 4 or parts[-2] != plat:
        return None, None
    author = parts[-1] or None
    access = next((v for k, v in access_words.items() if k in parts), None)
    return author, access


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gaps", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    a = ap.parse_args()

    gaps = (yaml.safe_load(open(a.gaps)) or {}).get("rows") or []
    by_work = defaultdict(set)
    plat_of, order = {}, []
    for g in gaps:
        w, u = g.get("work"), g.get("url")
        if not (w and u):
            continue
        if w not in by_work:
            order.append(w)
        by_work[w].add(u)
        # Access is a fact about a chapter ON A PLATFORM, so the build only carries it between rows
        # that agree on the platform. This adapter spans hosts and would otherwise declare none,
        # which is why its first run filled in five authors and no access at all.
        if g.get("platform"):
            plat_of.setdefault(w, g["platform"])

    works, how, missed = [], Counter(), []
    for w in order:
        url = sorted(by_work[w])[0]
        html = get(url)
        if not html:
            missed.append((w, "page did not load"))
            continue
        author, eps = gigaviewer_feed(url, html)
        route = "gigaviewer-feed" if eps else None
        if not eps:
            au, access = title_tail(url, html)
            if au or access:
                author, route = au, "title-tail"
                # No chapter list from this route; the fields are stated for the work, so they are
                # recorded at work level and the build carries them onto its rows.
                works.append({"work_title": w, "author": author, "url": url,
                              "platform": plat_of.get(w), "route": route,
                              "work_access": access, "episodes": []})
                how[route] += 1
                continue
        if not eps and not author:
            missed.append((w, "no route yielded the missing fields"))
            continue
        how[route] += 1
        works.append({"work_title": w, "author": author, "url": url,
                      "platform": plat_of.get(w), "route": route,
                      "work_access": None, "episodes": eps})

    if not works:
        sys.exit("no gap row resolved; not writing")

    L = ["# Fields filled in one row at a time, from the page a reader would open.",
         "#",
         "# These are rows the platform passes left incomplete — usually a single 読切 on a host",
         "# whose adapter walks serialised titles only. The routes are the proven ones: the",
         "# per-series Atom feed an episode page links even when the series is one entry long, and",
         "# a <title> whose shape the platform keeps, read only when the platform's own name is in",
         "# the position that shape requires.",
         "#",
         "# A route that does not fire leaves the field empty. Nothing here is inferred.",
         "#",
         "# No genre label is established here (DEFINITIONS §4).",
         "source: webpages", "platform: backfill", "platform_name: \"\"",
         f"retrieved: {a.retrieved}", "record_type: web_work_chapters",
         "identification_mode: discovery-candidate", "works:"]
    for w in works:
        L.append(f"  - work_title: {js(w['work_title'])}")
        if w["author"]:
            L.append(f"    author: {js(w['author'])}")
        L.append(f"    url: {js(w['url'])}")
        if w.get("platform"):
            L.append(f"    platform_name: {js(w['platform'])}")
        L.append(f"    route: {js(w['route'])}")
        if w["work_access"]:
            L.append(f"    access_modes: {js(w['work_access'])}")
        if w["episodes"]:
            L.append(f"    chapter_count: {len(w['episodes'])}")
            L.append("    chapters:")
            for e in w["episodes"]:
                L.append(f"      - title: {js(e['title'])}")
                L.append(f"        updated: {e['updated']}")
                if e.get("access_modes"):
                    L.append(f"        access_modes: {js(e['access_modes'])}")
    L.append("")
    pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(a.out) / "backfill.yaml").write_text("\n".join(L))

    print(f"gap works       : {len(order)}")
    print(f"resolved        : {len(works)}  {dict(how)}")
    if missed:
        print(f"still missing   : {len(missed)}")
        for t, r in missed:
            print(f"    - {str(t)[:34]:36} {r}")


if __name__ == "__main__":
    main()
