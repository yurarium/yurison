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
                    --cache $YURI_CACHE/webpages-cache --retrieved 2026-08-01
"""
import html as _html
import argparse, json, pathlib, re, sys, time, urllib.error, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import comici  # noqa: E402
import textnorm  # noqa: E402
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


TRUNCATED = re.compile(r"(?:\.{2,}|\u2026)\s*$")
OG_TITLE = re.compile(r'<meta[^>]+property="og:title"[^>]+content="([^"]*)"')


def untruncated(target_title, html):
    """The page's own name for the work, where the one we were given is a truncation of it.

    The target list is built from listings, and a listing truncates. youngchampion.jp cuts at a
    fixed character count and appends an ellipsis, so 公爵令嬢の籠絡ミッション arrived with its
    second half missing and no full-length copy anywhere else in the catalogue to recover it from.
    The page states the whole thing in og:title.

    ONLY WHERE IT IS A TRUNCATION, tested by prefix. og:title is not reliably a bare work name:
    マガポケ puts the episode and the platform in it, so taking it wherever it differs would trade
    a truncated title for a decorated one. A page whose og:title begins with what we were given,
    minus a trailing ellipsis, is stating the same name at greater length and nothing else is.

    THE PREFIX IS TESTED ON THE COMPARISON FORM. The listing wrote 切り札です! with a half-width
    mark and the page writes 切り札です！ with a full-width one, so a literal prefix test fails on
    the one case it exists for. textnorm folds that difference and keeps the words.
    """
    # ONLY A VISIBLY TRUNCATED TITLE IS REPAIRED. Without this the rule fires on
    # 私に天使が舞い降りた！, whose og:title is the same name followed by the episode and the
    # platform, and swaps a correct title for a decorated one. A trailing ellipsis is the platform
    # saying it cut the string, and it is the only invitation to go looking for the rest.
    if not target_title or not TRUNCATED.search(target_title):
        return target_title
    m = OG_TITLE.search(html or "")
    if not m:
        return target_title
    og = _html.unescape(m.group(1)).strip()
    stem = TRUNCATED.sub("", target_title).strip()
    if not stem or not textnorm.norm(og).startswith(textnorm.norm(stem)):
        return target_title
    # THE TAIL IS CUT AT THE DECORATION, not taken whole. youngchampion.jp states the bare title in
    # og:title; comic-gardo states "<work> - <author> / <episode>". Taking the whole string put the
    # author into the work's name. The separator is only honoured PAST the stem, so a title
    # containing one of these marks keeps it.
    # The result is the platform's own string throughout, never ours spliced onto theirs: the
    # listing wrote 切り札です! and the page writes 切り札です！, and keeping our half of the join
    # would publish a title neither source states. The stem's length indexes into og safely,
    # because a half-width mark and a full-width one are each one character.
    tail = og[len(stem):]
    for sep in (" - ", " | ", "｜"):
        if sep in tail:
            og = og[:len(stem) + tail.index(sep)]
            break
    og = og.strip()
    return og if len(og) > len(stem) else target_title

def episodes(html, eng, base, page_url=None, fetch=None):
    # comici is read by the shared module, not by this file's selectors. Its access model has three
    # states and its chapter list is paginated behind a range navigation; both were worked out once
    # and both used to live only in adapters/remaining/, so every comici platform read HERE — キミコミ,
    # 竹コミ, ビッコミ, ライコミ, Gコミ, HERO'S Web, チャンピオンクロス, 花とゆめ+ — carried a two-state
    # reading and only the first ten chapters. One engine, one parser.
    if eng.get("engine_name") == "comici" and comici.is_comici(html):
        return comici.chapters(html, page_url, fetch or (lambda u: ""))
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
        # Only a stated value is recorded; absence is left unset rather than assumed (§6).
        if eng.get("free") and re.search(eng["free"], b):
            row["access_modes"] = ["free"]
        elif eng.get("paid") and re.search(eng["paid"], b):
            row["access_modes"] = ["purchase"]
        elif eng.get("free_attr"):
            fm = re.search(eng["free_attr"], b)
            if fm:
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
    # Accepts either the full candidate list (candidates/urls) or the gap report
    # (works_missing/url). The full list is what should be used — the gap deliberately excludes
    # everything already reachable, so an adapter reading it loses works the moment they are.
    missing = []
    for w in gap.get("candidates") or []:
        for u in w.get("urls") or []:
            missing.append({"title": w.get("title"), "url": u})
    for w in gap.get("works_missing") or []:
        missing.append({"title": w.get("title"), "url": w.get("url")})

    grand = Counter()
    for site in spec["sites"]:
        eng = dict(engines[site["engine"]], engine_name=site["engine"])
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
            eps = episodes(html, eng, f"https://{site['host']}", tgt["url"],
                           lambda u: fetch(u, cache))
            if len(eps) < site.get("min_episodes", 1):
                failed.append((tgt["title"], f"{len(eps)} episodes parsed"))
                continue
            # comici states the author in the page title as "作品 - 作者 | プラットフォーム".
            # It was never read, so every comici platform reported chapters with no author.
            au = re.search(r"<title>[^<|]*?\s+-\s+([^<|]+?)\s*\|", html)
            row = {"work_title": untruncated(tgt["title"], html), "url": tgt["url"],
                   "episodes": eps}
            if au:
                row["author"] = _html.unescape(au.group(1).strip())
            works.append(row)

        # The floor exists to catch a site redesign silently emptying a parser. It has to scale
        # with how many works the site actually has, or a platform carrying one yuri title is
        # permanently indistinguishable from a broken one — which is what happened to 花とゆめ+
        # (4 candidates) and COMICリュエル (1) the first time they ran.
        floor = site.get("min_works", min(MIN_WORKS, max(1, len(targets))))
        if len(works) < floor:
            print(f"HEALTH: {site['id']} — {len(works)} works parsed (< {floor}); "
                  "markup may have changed. Writing nothing for this site.", file=sys.stderr)
            continue

        L = [f"# {site['name']} ({site.get('publisher') or 'publisher not established'}) — chapters from "
         "server-rendered work pages.",
             "# Works named by a Tier C yardstick; the platform attests the chapters.",
             "# This platform applies no 百合 tag, so nothing here establishes marketing_label.",
             "source: webpages", f"platform: {site['id']}",
             f"platform_name: {js(site['name'])}", f"publisher: {js(site.get('publisher', ''))}",
             f"engine: {site['engine']}", f"retrieved: {a.retrieved}",
             "record_type: web_work_chapters", "identification_mode: discovery-candidate",
             "works:"]
        for w in works:
            L.append(f"  - work_title: {js(w['work_title'])}")
            if w.get("author"):
                L.append(f"    author: {js(w['author'])}")
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
