#!/usr/bin/env python3
"""カドコミ release tracking (REQUIREMENTS §5).

カドコミ is the largest single source of active yuri web serialisation — 53 of the 250 works that
updated in a recent 3.5-week window, more than twice any other platform — but it publishes no feed
and its tag search loads from a robots-disallowed `/api/`.

Its per-work `/detail/<code>` pages are permitted and server-rendered though, embedding
`latestEpisodes` and `firstEpisodes` in `__NEXT_DATA__`. So works named by the Tier C yardsticks
are polled individually. No crawling, no API.

Unlike the other no-feed platforms, カドコミ *does* apply a 百合 tag, so this establishes
marketing_label under DEFINITIONS §4 where the tag is present.

Never stored: `summary` (publisher synopsis, §2) or thumbnail URLs.

Usage:  releases.py --works data/coverage/webcomics-works.yaml --out data/source/kadokomi \
                    --cache ~/workspace/kadokomi-cache --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys, time, urllib.error, urllib.request
from collections import Counter

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
DETAIL = "https://comic-walker.com/detail/{code}"
PAUSE = 1.5
YURI_TAGS = {"百合", "GL", "ガールズラブ"}
MIN_WORKS = 5


def fetch(code, cache, max_age_days=1):
    f = cache / f"{code}.html"
    if f.exists():
        age = (time.time() - f.stat().st_mtime) / 86400
        if age < max_age_days:
            return f.read_text()
    req = urllib.request.Request(DETAIL.format(code=code), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t


def work_data(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return None
    d = json.loads(m.group(1))
    for q in d.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", []):
        data = (q.get("state") or {}).get("data")
        if isinstance(data, dict) and "work" in data:
            return data
    return None


def ep_rows(data):
    """Episodes carry an id, code, title, update timestamp — and, it turns out, their access.

    This used to say free/paid was "not stated in a form we have established", which was true when
    written and stopped being true without anyone noticing. It is stated, in two fields:

        isActive        readable right now, without paying
        deliveryPeriod  when that ends; 9999-12-31 means it does not

    On 私を喰べたい、ひとでなし, 48 of 410 episodes are active and the rest are not — カドコミ's usual
    "newest few stay open" shape.

    Only the POSITIVE statement is recorded. isActive true means the platform says you can read it,
    so that is `free`. isActive false means it is not open, and カドコミ does not say whether that is
    because it must be bought or because it is simply gone — so nothing is recorded, and the row
    reads as unknown rather than as paid. Asserting 有料 from a missing field is what put
    オタクサキュバスの才能がありすぎる！ — a free one-shot — in the interface as paid."""
    out = {}
    for key in ("latestEpisodes", "firstEpisodes"):
        block = data.get(key) or {}
        lst = block.get("result") if isinstance(block, dict) else block
        for e in lst or []:
            if not isinstance(e, dict):
                continue
            code = e.get("code") or e.get("id")
            if not code:
                continue
            when = str(e.get("updateDate") or e.get("startDate") or e.get("deliveryStartAt") or "")
            row = {"code": code, "title": (e.get("title") or "").strip(),
                   "subtitle": (e.get("subTitle") or "").strip(),
                   "updated": when[:10] if when else ""}
            if e.get("isActive") is True:
                row["access_modes"] = ["free"]
                dp = str(e.get("deliveryPeriod") or "")[:10]
                # 9999-12-31 is the platform's way of saying "no end", not a date.
                if dp and not dp.startswith("9999"):
                    row["free_until"] = dp
            out[code] = row
    return list(out.values())


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", required=True, help="Tier C candidate list naming カドコミ works")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit", type=int, default=400)
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    codes = {}
    # カドコミ's own 百合 catalogue is authoritative and complete; prefer it over antenna seeding.
    cat = pathlib.Path("data/source/kadokomi/catalogue.yaml")
    if cat.exists():
        for w in (yaml.safe_load(cat.read_text()) or {}).get("works") or []:
            if w.get("code"):
                codes[w["code"]] = w.get("title")

    # Works the publisher does not tag 百合 are absent from the catalogue, so a comparator naming
    # one had nothing to resolve against. Codes found by external search live here.
    res = pathlib.Path("data/source/kadokomi/resolved.yaml")
    if res.exists():
        for w in (yaml.safe_load(res.read_text()) or {}).get("works") or []:
            if w.get("code"):
                codes[w["code"]] = w.get("title")

    # Works confirmed from the discovery queue. Confirmation established what they ARE and then
    # nothing fetched their episodes, so a one-shot found through 百合ナビ produced a work record
    # and no release — which is why the feed showed one one-shot in thirteen hundred entries.
    conf = pathlib.Path("data/source/kadokomi/confirmed.yaml")
    if conf.exists():
        for w in (yaml.safe_load(conf.read_text()) or {}).get("works") or []:
            if w.get("platform_code"):
                codes.setdefault(w["platform_code"], w.get("work_title"))

    src = yaml.safe_load(open(a.works)) or {}
    for c in src.get("candidates") or []:
        if "カドコミ" not in (c.get("platforms") or []):
            continue
        for u in [c.get("url", "")] + (c.get("urls") or []):
            m = re.search(r"comic-walker\.com/detail/([A-Za-z0-9_]+)", u or "")
            if m:
                codes[m.group(1)] = c.get("title")
    # The candidate list carries platform names but not always URLs; fall back to the gap report,
    # which does.
    gapf = pathlib.Path(a.works).parent / "webcomics-gap.yaml"
    if gapf.exists():
        for w in (yaml.safe_load(gapf.read_text()) or {}).get("works_missing") or []:
            m = re.search(r"comic-walker\.com/detail/([A-Za-z0-9_]+)", w.get("url") or "")
            if m:
                codes.setdefault(m.group(1), w.get("title"))
    codes = dict(list(codes.items())[:a.limit])
    if not codes:
        sys.exit("no カドコミ work codes found")

    works, failed, tagged = [], [], 0
    for code, title in codes.items():
        try:
            d = work_data(fetch(code, cache))
        except urllib.error.HTTPError as e:
            failed.append((title, f"HTTP {e.code}"))
            continue
        if not d:
            failed.append((title, "no payload"))
            continue
        w = d["work"]
        tags = [t["name"] for t in w.get("tags") or []]
        hits = [t for t in tags if t in YURI_TAGS]
        if hits:
            tagged += 1
        works.append({
            "work_title": w.get("title", title), "platform_code": code,
            "url": DETAIL.format(code=code), "tags": tags,
            "status": w.get("serializationStatus"),
            "authors": [x.get("name") for x in w.get("authors") or []],
            "marketing_label": "yuri" if hits else "none",
            "yuri_tags": hits,
            "episodes": ep_rows(d),
        })

    if len(works) < MIN_WORKS:
        sys.exit(f"HEALTH: resolved {len(works)} works (< {MIN_WORKS}). Refusing to write.")

    L = ["# カドコミ per-work episode lists. Works named by a Tier C yardstick; カドコミ attests them.",
         "# カドコミ DOES apply a 百合 tag, so marketing_label is established where present (§4).",
         "# No synopsis and no image URLs are stored (REQUIREMENTS §2).",
         "source: kadokomi", f"retrieved: {a.retrieved}", "record_type: web_work_chapters",
         "identification_mode: discovery-candidate", "works:"]
    for w in works:
        L.append(f"  - work_title: {js(w['work_title'])}")
        for k in ("platform_code", "url", "status", "marketing_label"):
            if w.get(k):
                L.append(f"    {k}: {js(w[k])}")
        L.append(f"    tags: {js(w['tags'])}")
        L.append(f"    authors: {js([x for x in w['authors'] if x])}")
        if w["yuri_tags"]:
            L.append("    marketing_label_basis:")
            L.append("      source: kadokomi")
            L.append(f"      url: {js(w['url'])}")
            L.append(f"      retrieved: {a.retrieved}")
            L.append(f"      note: {js('Publisher applies the tag ' + '/'.join(w['yuri_tags']) + ' on カドコミ.')}")
        L.append(f"    chapter_count: {len(w['episodes'])}")
        L.append("    chapters:")
        for e in w["episodes"]:
            L.append(f"      - code: {js(e['code'])}")
            L.append(f"        title: {js(e['title'])}")
            if e.get("subtitle"):
                L.append(f"        subtitle: {js(e['subtitle'])}")
            if e.get("updated"):
                L.append(f"        updated: {js(e['updated'])}")
            if e.get("access_modes"):
                L.append(f"        access_modes: {js(e['access_modes'])}")
            if e.get("free_until"):
                L.append(f"        free_until: {js(e['free_until'])}")
    L.append("")
    (out / "chapters.yaml").write_text("\n".join(L))

    eps = sum(len(w["episodes"]) for w in works)
    dated = sum(1 for w in works for e in w["episodes"] if e.get("updated"))
    print(f"works targeted : {len(codes)}")
    print(f"works resolved : {len(works)}  ({tagged} carry a publisher yuri tag)")
    print(f"episodes       : {eps}  ({dated} dated)")
    if failed:
        print(f"failed         : {len(failed)}")


if __name__ == "__main__":
    main()
