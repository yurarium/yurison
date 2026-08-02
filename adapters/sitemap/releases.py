#!/usr/bin/env python3
"""Release dates from a platform's own sitemap (REQUIREMENTS §5).

A sitemap is published for crawlers to read. Where its entries are per-episode and carry
`<lastmod>`, that is the platform stating when a page last changed — which for an episode page is
the episode. No rendering, no headers, nothing negotiated: the file exists to be fetched.

Found while looking for a way into マガポケ that did not need a browser. Its sitemap.xml is an index
pointing at sitemap_viewer_1.xml, which holds 5,354 episode URLs and 3,113 lastmod dates. Every one
of our 37 マガポケ works appears in it.

What this is and is not:

- `lastmod` describes the URL, not the chapter, so it is corroboration rather than a publication
  statement. Recorded with `date_basis: sitemap` and never merged into a stronger claim.
- Coverage is broad and shallow: the sitemap reaches every work, usually with one dated episode
  each. Rendering reaches fewer works with their whole chapter list. They complement rather than
  replace — this one answers "has this work updated recently at all" for the works rendering
  misses.
- Nothing here establishes a genre label (DEFINITIONS §4).

Usage:  releases.py --sites adapters/sitemap/sites.yaml --works data/coverage/claim-targets.yaml \
                    --out data/source/webpages --retrieved 2026-08-01
"""
import argparse, html as _html, json, pathlib, re, sys, time, urllib.error, urllib.request
from collections import defaultdict

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.0


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.read(8_000_000).decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return ""
    finally:
        time.sleep(PAUSE)


TITLE_LOOKUPS = 3


def chapter_title(url):
    """The chapter名 from an episode page's own <title>.

    マガポケ writes "作品 | 【第N話】章題 / マガポケ | …", so the middle segment is the chapter.
    Returns None rather than a guess when the shape does not hold.

    Entities are decoded FIRST. マガポケ writes that separating slash as &#x2F;, so splitting the
    raw title on "/" matched nothing and the platform's own name stayed welded to the chapter:
    【第1話】ぐっすん！ドキドキ！別れは出会いのシグナル &#x2F; マガポケ. It survived every field check —
    the row had a chapter, an author and a date — and was visible the moment the list was read
    instead of counted.
    """
    page = get(url)
    m = re.search(r"<title>([^<]*)</title>", page or "")
    if not m:
        return None
    parts = [s.strip() for s in _html.unescape(m.group(1)).split("|")]
    if len(parts) < 2:
        return None
    ch = parts[1].split("/")[0].strip()
    return ch or None


def entries(xml):
    """(url, lastmod) for every <url> that has both."""
    out = []
    for m in re.finditer(r"<url>(.*?)</url>", xml, re.S):
        b = m.group(1)
        u = re.search(r"<loc>([^<]+)</loc>", b)
        d = re.search(r"<lastmod>(\d{4}-\d{2}-\d{2})", b)
        if u and d:
            out.append((u.group(1), d.group(1)))
    return out


def expand(url, depth=0):
    """A sitemap index points at sitemaps. One level of indirection is enough for every case seen."""
    xml = get(url)
    if not xml:
        return []
    if "<sitemapindex" in xml[:600] and depth == 0:
        out = []
        for loc in re.findall(r"<loc>([^<]+)</loc>", xml):
            out += expand(loc, depth + 1)
        return out
    return entries(xml)


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", required=True)
    ap.add_argument("--works", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    a = ap.parse_args()

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    src = yaml.safe_load(open(a.works)) or {}
    sites = (yaml.safe_load(open(a.sites)) or {}).get("sites") or []

    for s in sites:
        rows = expand(s["sitemap"])
        if not rows:
            print(f"{s['name'][:20]:22} sitemap returned nothing")
            continue
        # Two patterns, because the sitemap and the candidate list identify a work differently:
        # the sitemap lists /title/<id>/episode/<id>, our candidates carry /title/<id>. Using one
        # pattern for both matched five works of thirty-seven.
        key = re.compile(s["work_key"])
        ckey = re.compile(s.get("candidate_key") or s["work_key"])
        by_work = defaultdict(list)
        for u, d in rows:
            m = key.search(u)
            if m:
                by_work[m.group(1).lstrip("0")].append((d, u))

        host = re.match(r"https?://([^/]+)", s["sitemap"]).group(1)
        works = []
        for w in src.get("candidates") or []:
            for u in w.get("urls") or []:
                # The host must match. Work ids are per-platform and collide across them:
                # /title/2268 is イタズラっ子世に憚らず!! on ガンガンONLINE and 僕の奥さんはちょっと怖い
                # on マガポケ, and matching on the bare number filed one under the other's name.
                if host not in (u or ""):
                    continue
                m = ckey.search(u or "")
                if not m:
                    continue
                eps = sorted(by_work.get(m.group(1).lstrip("0")) or [], reverse=True)
                if eps:
                    rows_ep = [{"updated": d, "url": eu} for d, eu in eps[:40]]
                    # A sitemap gives a URL and a date. The page behind it states the chapter, and
                    # a row with a date and no chapter is the one thing a reader can see is empty —
                    # so the newest few are fetched to name them. Only the newest: older entries
                    # will not appear in any feed window worth showing.
                    for e in rows_ep[:TITLE_LOOKUPS]:
                        ti = chapter_title(e["url"])
                        if ti:
                            e["title"] = ti
                    works.append({"work_title": w.get("title"), "url": u, "episodes": rows_ep})
                break
        if not works:
            print(f"{s['name'][:20]:22} no candidate work matched the sitemap")
            continue

        L = [f"# {s['name']} — dates from the platform's own sitemap.",
             "#",
             "# <lastmod> describes when a URL last changed, which for an episode page is the",
             "# episode. It is the platform's statement, published for crawlers to read, but it",
             "# describes the URL rather than the chapter — corroboration, not a publication record.",
             "#",
             "# Broad and shallow by nature: it reaches every work, usually with one dated episode",
             "# each. It answers 'has this updated recently at all' for works no other route covers.",
             "source: webpages", f"platform: {s['id']}", f"platform_name: {js(s['name'])}",
             f"publisher: {js(s.get('publisher', ''))}", f"retrieved: {a.retrieved}",
             "record_type: web_work_chapters", "identification_mode: discovery-candidate",
             "date_basis: sitemap", "date_confidence: low", "works:"]
        for w in works:
            L.append(f"  - work_title: {js(w['work_title'])}")
            L.append(f"    url: {js(w['url'])}")
            L.append(f"    chapter_count: {len(w['episodes'])}")
            L.append("    chapters:")
            for e in w["episodes"]:
                L.append(f"      - title: {js(e.get('title') or '')}")
                L.append(f"        updated: {e['updated']}")
                L.append(f"        url: {js(e['url'])}")
                L.append("        date_basis: sitemap")
        L.append("")
        (out / f"sitemap-{s['id']}.yaml").write_text("\n".join(L))
        n = sum(len(w["episodes"]) for w in works)
        print(f"{s['name'][:20]:22} works={len(works):3} dated episodes={n:5} "
              f"(sitemap held {len(rows)} dated URLs)")


if __name__ == "__main__":
    main()
