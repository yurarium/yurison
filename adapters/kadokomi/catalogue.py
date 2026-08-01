#!/usr/bin/env python3
"""Enumerate カドコミ's own 百合 catalogue (REQUIREMENTS §1, §5).

Better than antenna-seeded discovery in two ways: it is complete rather than whatever a third party
happened to list, and it is **the publisher's own labelling**, so it establishes `marketing_label`
under DEFINITIONS §4 instead of merely naming candidates.

Access: `/search/tag/<uuid>` is a permitted path — robots.txt disallows `/?` (the root with a query)
and `/api/`, neither of which this is. The page embeds its own results in `__NEXT_DATA__`, so this
reads the rendered page rather than calling the disallowed API. Paginated with `?p=N`, 20 per page.

Recorded 2026-08-01: 348 works, against 243 the antenna listed for this platform.

Usage:  catalogue.py --out data/source/kadokomi --cache ~/workspace/kadokomi-cache \
                     --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys, time, urllib.request

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
TAG_UUID = "018b8a02-f3d9-7a59-969d-288cb905f0fc"   # 百合
BASE = "https://comic-walker.com/search/tag/{uuid}"
PAUSE = 1.5
MIN_WORKS = 50


def page(n, cache, uuid):
    f = cache / f"tag-{uuid[:8]}-p{n}.html"
    if f.exists():
        return f.read_text()
    url = BASE.format(uuid=uuid) + (f"?p={n}" if n > 1 else "")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t


def results(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return None, []
    d = json.loads(m.group(1))
    for q in d.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", []):
        data = (q.get("state") or {}).get("data")
        if isinstance(data, dict) and "result" in data:
            return data.get("total"), data["result"]
    return None, []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--uuid", default=TAG_UUID)
    ap.add_argument("--max-pages", type=int, default=30)
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)

    total, works, seen = None, [], set()
    for n in range(1, a.max_pages + 1):
        t, rows = results(page(n, cache, a.uuid))
        if total is None:
            total = t
        if not rows:
            break
        new = 0
        for r in rows:
            code = r.get("code")
            if not code or code in seen:
                continue
            seen.add(code)
            works.append({"code": code, "title": (r.get("title") or "").strip(),
                          "status": r.get("serializationStatus")})
            new += 1
        if new == 0:
            break            # pagination exhausted or looping
        if total and len(works) >= total:
            break

    if len(works) < MIN_WORKS:
        sys.exit(f"HEALTH: enumerated {len(works)} works (< {MIN_WORKS}); the tag page markup or "
                 "pagination may have changed. Refusing to write.")

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = ["# カドコミ's own 百合 tag catalogue — the publisher's labelling, not a third party's.",
         "# Establishes marketing_label under DEFINITIONS §4 for every work listed.",
         "#",
         "# Read from /search/tag/<uuid>, a permitted path: robots.txt disallows /? and /api/, and",
         "# this is neither. Results are embedded in the page, so the disallowed API is not called.",
         "source: kadokomi", "role: attesting", f"retrieved: {a.retrieved}",
         "record_type: platform_yuri_catalogue", f"tag_uuid: {a.uuid}",
         f"total_reported: {total}", f"works_enumerated: {len(works)}", "works:"]
    for w in sorted(works, key=lambda w: w["code"]):
        L.append(f"  - code: {json.dumps(w['code'], ensure_ascii=False)}")
        L.append(f"    title: {json.dumps(w['title'], ensure_ascii=False)}")
        if w.get("status"):
            L.append(f"    status: {json.dumps(w['status'], ensure_ascii=False)}")
        L.append("    marketing_label: yuri")
    L.append("")
    (out / "catalogue.yaml").write_text("\n".join(L))

    print(f"total reported by カドコミ : {total}")
    print(f"works enumerated          : {len(works)}")
    print(f"written                   : {out}/catalogue.yaml")


if __name__ == "__main__":
    main()
