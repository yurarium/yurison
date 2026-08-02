#!/usr/bin/env python3
"""Shogakukan's web reader — chapters, authors and access from the work page (REQUIREMENTS §5).

Two hosts run the same reader: コロコロオンライン and フラコミlike!. Same chapter rows, same access
badges, same author links. コロコロ builds its list in JavaScript; フラコミ serves the identical
markup already rendered, so it is fetched plainly and only コロコロ pays for a browser. They were
found separately — フラコミ because the catch-all resolver had turned its chapter Episode.4 -1 into
"Episode.4 -1 0 0" by sweeping up the like and comment counts beside it.

The catch-all resolver reached this platform and read its chapter strip positionally, which gave
titles like "第99話 4,825" — the chapter with its like count welded on — and no author or access at
all. I had then recorded the author as unreachable because the page <title> runs everything
together with no separator:

    DOUBLE HELIX BLOSSOM SWAV アサウラ 西馬ごめゆき | 週刊コロコロコミック

Splitting that is a guess at where the title ends, and this project has spent a session undoing
guesses of exactly that shape. The page does not require one. It states each author as a link to
that author's own page — <a href="/author/152">SWAV</a> — so the boundary is the platform's, not
mine. SWAV turns out to be a third author rather than a subtitle, which no split of that string
would have got right.

Every chapter row states the rest:

    <img alt="第99話 の話サムネイル">     the chapter, cleanly, with no like count
    <time>2026/07/18</time>            its date
    <img alt="無料">                    its access badge

Access badges, which are images with Japanese alt text:

    無料          free
    チケット       free-timed — readable with a 作品チケット rather than by paying
    黄色いCマーク   purchase — the coin badge

A row dated in the future is 次回更新予定, announced and not published, and is not a release.

The page builds itself in JavaScript, so this renders. There is no JSON in the served HTML and the
API host answers 405 to GET — it takes POST only, and reconstructing that call is a great deal of
work for one platform when the page itself says everything.

Usage:  releases.py --sites adapters/shogakukan/sites.yaml --out data/source/webpages \
                    --retrieved 2026-08-02
"""
import argparse, datetime as dt, html as _html, json, pathlib, re, subprocess, sys, time
import urllib.error, urllib.request

import yaml

UA = "Mozilla/5.0 (compatible; yurarium/0.1; +https://yurarium.github.io/)"
PAUSE = 1.0
CHROME = next((c for c in ("/snap/bin/chromium", "/usr/bin/chromium",
                           "/usr/bin/chromium-browser", "/usr/bin/google-chrome")
               if pathlib.Path(c).exists()), None)

ROW = re.compile(r'<li class="bg-white">(.*?)</li>', re.S)
ROW_TITLE = re.compile(r'alt="([^"]+?)\s*の話サムネイル"')
ROW_DATE = re.compile(r"<time[^>]*>\s*(\d{4})/(\d{1,2})/(\d{1,2})")
AUTHOR = re.compile(r'href="/author/\d+"[^>]*>(?:\s*<[^>]*>)*\s*([^<]{1,24})')
BADGE = {"無料": ["free"], "チケット": ["free-timed"], "黄色いCマーク": ["purchase"]}


def get(url):
    """Plain fetch first. フラコミlike! serves the whole chapter list this way and rendering it would
    be a browser spent on markup already in hand."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.read(4_000_000).decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return ""
    finally:
        time.sleep(PAUSE)


def render(url):
    if not CHROME:
        return ""
    try:
        out = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=12000",
             f"--user-agent={UA}", "--dump-dom", url], capture_output=True, text=True, timeout=150)
    except (subprocess.TimeoutExpired, OSError):
        return ""
    time.sleep(PAUSE)
    return out.stdout or ""


def authors(dom):
    names = [_html.unescape(x).strip() for x in AUTHOR.findall(dom)]
    return " / ".join(dict.fromkeys(n for n in names if n)) or None


def chapters(dom, today):
    out = []
    for block in ROW.findall(dom):
        t, d = ROW_TITLE.search(block), ROW_DATE.search(block)
        if not (t and d):
            continue
        when = dt.date(int(d.group(1)), int(d.group(2)), int(d.group(3)))
        if when > today:
            continue                       # 次回更新予定 — announced, not published
        row = {"title": _html.unescape(t.group(1)).strip(), "updated": when.isoformat()}
        for alt in re.findall(r'alt="([^"]{1,16})"', block):
            if alt in BADGE:
                row["access_modes"] = BADGE[alt]
                break
        out.append(row)
    return out


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    a = ap.parse_args()

    today = dt.date.fromisoformat(a.retrieved)
    pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
    for site in (yaml.safe_load(open(a.sites)) or {}).get("sites") or []:
        emit(site, today, a)


def emit(site, today, a):
    works, failed, rendered = [], [], 0
    for w in site.get("works") or []:
        dom = get(w.get("url"))
        eps = chapters(dom, today) if dom else []
        if not eps:
            dom = render(w.get("url"))
            eps = chapters(dom, today) if dom else []
            rendered += bool(eps)
        if not eps:
            failed.append((w.get("work_title"), "no chapter rows on the page"))
            continue
        works.append({"work_title": w.get("work_title"), "author": authors(dom),
                      "url": w.get("url"), "episodes": eps})

    if not works:
        print(f"{site['name'][:18]:20} no work resolved")
        return

    L = [f"# {site['name']} — chapters, authors and access from the work page.",
         "#",
         "# Each chapter row names itself in its thumbnail's alt text (\"第99話 の話サムネイル\"), dates",
         "# itself in a <time>, and states its access as an image badge: 無料, チケット, or the coin",
         "# mark. Authors are links to their own author pages, which is why they can be read at all —",
         "# the page <title> runs work and authors together with no separator.",
         "#",
         "# Rendered: the page builds in JavaScript and the API host answers 405 to GET.",
         "#",
         "# No genre label is established here (DEFINITIONS §4).",
         "source: webpages", f"platform: {site['id']}",
         f"platform_name: {js(site['name'])}", f"publisher: {js(site.get('publisher', ''))}",
         f"retrieved: {a.retrieved}",
         "record_type: web_work_chapters", "identification_mode: discovery-candidate",
         # Per site, not per adapter. Both read the platform's own markup, but コロコロ only draws
         # it in a browser and フラコミ serves it — and "how we came to hold this" is what this
         # field records. Writing platform-stated for both would have hidden the browser.
         f"date_basis: {'rendered' if rendered else 'platform-stated'}",
         "date_confidence: reported", "works:"]
    for w in works:
        L.append(f"  - work_title: {js(w['work_title'])}")
        if w["author"]:
            L.append(f"    author: {js(w['author'])}")
        L.append(f"    url: {js(w['url'])}")
        L.append(f"    chapter_count: {len(w['episodes'])}")
        L.append("    chapters:")
        for e in w["episodes"]:
            L.append(f"      - title: {js(e['title'])}")
            L.append(f"        updated: {e['updated']}")
            if e.get("access_modes"):
                L.append(f"        access_modes: {js(e['access_modes'])}")
    L.append("")
    (pathlib.Path(a.out) / f"{site['id']}.yaml").write_text("\n".join(L))

    n = sum(len(w["episodes"]) for w in works)
    acc = sum(1 for w in works for e in w["episodes"] if e.get("access_modes"))
    au = sum(1 for w in works if w["author"])
    print(f"{site['name'][:18]:20} works={len(works)} chapters={n} access={acc} author={au}"
          f"{'  (rendered)' if rendered else ''}")
    for t, r in failed:
        print(f"    - {str(t)[:30]:32} {r}")


if __name__ == "__main__":
    main()
