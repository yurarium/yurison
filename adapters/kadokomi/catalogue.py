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
# カドコミ labels yuri under more than one tag, and enumerating only 百合 missed the others
# outright: 作りたい女と食べたい女 carries GL and nothing else, so no amount of paging the 百合 tag
# would ever have reached it. Each tag is its own catalogue and they are unioned.
TAGS = [
    ("百合", "018b8a02-f3d9-7a59-969d-288cb905f0fc"),
    ("GL",   "018b8a02-f448-7b77-b194-cafcc706ed85"),
]
TAG_UUID = TAGS[0][1]
BASE = "https://comic-walker.com/search/tag/{uuid}"
PAUSE = 1.5
MIN_WORKS = 50


def page(n, cache, uuid):
    # The full uuid, not a prefix. カドコミ's tag uuids share their first block — 百合 and GL are
    # both 018b8a02-… — so an 8-character key made GL read 百合's cached pages and report an
    # identical, and identically wrong, 348.
    f = cache / f"tag-{uuid}-p{n}.html"
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

    tags = TAGS if a.uuid == TAG_UUID else [("(given)", a.uuid)]
    works, seen, per_tag, totals = [], set(), {}, {}
    for name, uuid in tags:
        total, got = None, 0
        for n in range(1, a.max_pages + 1):
            t, rows = results(page(n, cache, uuid))
            if total is None:
                total = t
            if not rows:
                break
            new = 0
            for r in rows:
                code = r.get("code")
                got += 1
                if not code or code in seen:
                    continue
                seen.add(code)
                works.append({"code": code, "title": (r.get("title") or "").strip(),
                              "status": r.get("serializationStatus"), "tag": name})
                new += 1
            if new == 0 and got >= (total or 0):
                break            # pagination exhausted or looping
            if total and got >= total:
                break
        per_tag[name] = got
        totals[name] = total
    total = sum(v for v in totals.values() if v)

    if len(works) < MIN_WORKS:
        sys.exit(f"HEALTH: enumerated {len(works)} works (< {MIN_WORKS}); the tag page markup or "
                 "pagination may have changed. Refusing to write.")

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = ["# カドコミ's own yuri tag catalogues — the publisher's labelling, not a third party's.",
         "# Union of every tag in TAGS. 百合 alone was not enough: works tagged only GL are",
         "# invisible to it, which is how 作りたい女と食べたい女 stayed unreachable.",
         "# Establishes marketing_label under DEFINITIONS §4 for every work listed.",
         "#",
         "# Read from /search/tag/<uuid>, a permitted path: robots.txt disallows /? and /api/, and",
         "# this is neither. Results are embedded in the page, so the disallowed API is not called.",
         "source: kadokomi", "role: attesting", f"retrieved: {a.retrieved}",
         "record_type: platform_yuri_catalogue",
         "tags_enumerated:"] + [f"  - {{ name: {n}, uuid: {u}, listed: {totals.get(n)} }}"
                                for n, u in tags] + [
         f"total_reported: {total}", f"works_enumerated: {len(works)}", "works:"]
    for w in sorted(works, key=lambda w: w["code"]):
        L.append(f"  - code: {json.dumps(w['code'], ensure_ascii=False)}")
        L.append(f"    title: {json.dumps(w['title'], ensure_ascii=False)}")
        if w.get("status"):
            L.append(f"    status: {json.dumps(w['status'], ensure_ascii=False)}")
        L.append(f"    tag: {json.dumps(w.get('tag') or '', ensure_ascii=False)}")
        L.append("    marketing_label: yuri")
    L.append("")
    (out / "catalogue.yaml").write_text("\n".join(L))

    for n, _ in tags:
        print(f"  tag {n:6} listed {totals.get(n)}")
    print(f"total reported by カドコミ : {total}")
    print(f"works enumerated          : {len(works)}")
    print(f"written                   : {out}/catalogue.yaml")


if __name__ == "__main__":
    main()
