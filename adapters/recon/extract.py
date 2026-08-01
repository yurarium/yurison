#!/usr/bin/env python3
"""Second-pass reconnaissance: try to actually extract dated chapters (REQUIREMENTS §6).

The first pass asked "is a date on this page". That question has a false-positive answer —
ガンガンONLINE is server-rendered and shows 2024.05.24発売！, which is a 単行本 release date while
its chapter list loads client-side. Sniffing for date-shaped strings cannot tell the two apart.

So this pass tries the extraction instead, and reports what came back. A strategy counts as working
only if it yields at least two entries that each have a date AND a chapter-like label, because one
dated thing on a page is usually the volume.

Strategies, cheapest first:

  jsonld  — schema.org objects carrying datePublished/dateModified alongside a name.
  next    — __NEXT_DATA__, walked for arrays of objects with both a date-ish and a title-ish key.
  nuxt    — window.__NUXT__, same walk over whatever JSON can be recovered from the assignment.
  markup  — repeated sibling blocks each containing a date and an anchor. The fallback, and the
            one that needs a per-host selector, so it reports the tag/class it keyed on.

Output feeds data/coverage/extract.yaml, which is the registry a generic adapter reads.

Usage:  extract.py --targets data/coverage/recon-targets.yaml --out data/coverage --retrieved DATE
"""
import argparse, json, pathlib, re, socket, sys, time, urllib.error, urllib.request
from collections import Counter

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.0
TIMEOUT = 25

DATE_KEY = re.compile(r"(date|updated|published|created|delivery|release|start|open)", re.I)
TITLE_KEY = re.compile(r"(title|name|subtitle|label|heading)", re.I)
# A chapter says so: 第N話, N話, #N, episode N, or a plain number in a numbering context.
CHAPTERISH = re.compile(
    r"第?\s*[0-9０-９]+\s*(話|回|章|品|皿|杯)|#\s*\d+|"
    r"(?:episode|ep|file|case|act|vol|chapter)\s*\.?\s*\d+|最終(話|回)", re.I)
ISO = re.compile(r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})")
# 単行本 release dates are the trap this pass exists to avoid.
VOLUMEISH = re.compile(r"発売|刊行|単行本|巻")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read(1_500_000).decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout,
            ConnectionError, OSError):
        return ""
    finally:
        time.sleep(PAUSE)


def norm_date(v):
    m = ISO.search(str(v))
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    if not (1990 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


def entries_from_obj(root):
    """Objects carrying both a date-ish and a title-ish field, at any depth."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            dk = [k for k in o if DATE_KEY.search(k) and norm_date(o[k])]
            tk = [k for k in o if TITLE_KEY.search(k) and isinstance(o[k], str) and o[k].strip()]
            if dk and tk:
                out.append({"title": o[tk[0]].strip()[:80], "date": norm_date(o[dk[0]]),
                            "date_key": dk[0]})
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(root)
    return out


def try_jsonld(html):
    out = []
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            out += entries_from_obj(json.loads(m.group(1)))
        except Exception:                                          # noqa: BLE001
            continue
    return out


def try_next(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return []
    try:
        return entries_from_obj(json.loads(m.group(1)))
    except Exception:                                              # noqa: BLE001
        return []


def try_nuxt(html):
    """__NUXT__ is an assignment, often an IIFE. Only the plain-object form is recoverable here;
    anything else is left to the markup strategy rather than evaluated."""
    m = re.search(r"window\.__NUXT__\s*=\s*(\{.*?\});?\s*</script>", html, re.S)
    if not m:
        return []
    try:
        return entries_from_obj(json.loads(m.group(1)))
    except Exception:                                              # noqa: BLE001
        return []


def try_pairs(html):
    """Pair each date with the nearest chapter label before it.

    try_markup splits at every occurrence of a tag, which yields the fragment between one opening
    tag and the next rather than a nested container. On a flat <li> list that is the same thing; on
    a nested div tree it is not, and title and date land in different fragments. マンガワン renders
    its chapter list as nested divs — 第8話(後編) in one <p>, 2026/07/19 in another two levels down
    — so nothing was extracted from a page that plainly had it.

    Pairing by position needs no assumption about structure at all.
    """
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    flat = re.sub(r"<[^>]+>", "\x00", body)
    out, seen = [], set()
    for m in re.finditer(r"\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}", flat):
        d = norm_date(m.group(0))
        if not d:
            continue
        back = flat[max(0, m.start() - 900): m.start()]
        labels = list(CHAPTERISH.finditer(back))
        if not labels:
            continue
        lm = labels[-1]
        # If another date sits between the label and this one, the label belongs to that date and
        # not to this — 第8話(後編) was being paired with 第8話(前編)'s date as well as its own.
        if re.search(r"\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}", back[lm.end():]):
            continue
        label = re.sub(r"[\x00]+", " ", back[lm.start(): lm.end() + 40]).strip()
        label = re.split(r"\s{2,}", label)[0].strip()
        if not label or (label, d) in seen:
            continue
        seen.add((label, d))
        out.append({"title": label, "date": d})
    return out


def try_markup(html):
    """Repeated blocks holding a date and an anchor. Reports the container it keyed on so the
    result is reproducible as a selector rather than a one-off parse."""
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    best = []
    for tag in ("li", "article", "div", "tr", "a"):
        blocks = re.split(rf"(?=<{tag}\b)", body)
        found, cls = [], Counter()
        for b in blocks:
            b = b[:4000]
            d = norm_date(re.sub(r"<[^>]+>", " ", b))
            if not d:
                continue
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", b)).strip()
            if VOLUMEISH.search(text[:160]) and not CHAPTERISH.search(text[:160]):
                continue
            t = CHAPTERISH.search(text)
            if not t:
                continue
            c = re.search(rf'<{tag}[^>]*class="([^"]{{0,60}})"', b)
            if c:
                cls[c.group(1).split()[0]] += 1
            found.append({"title": text[:80], "date": d})
        if len(found) > len(best):
            best = found
            best_tag, best_cls = tag, (cls.most_common(1)[0][0] if cls else "")
    if not best:
        return [], None
    return best, {"tag": best_tag, "class": best_cls}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    rows = (yaml.safe_load(open(a.targets)) or {}).get("targets") or []
    if a.limit:
        rows = rows[: a.limit]

    results = []
    for i, t in enumerate(rows, 1):
        url = t.get("work_url")
        r = {"platform": t["platform"], "host": t["host"], "work_url": url,
             "exclusive_works": t.get("exclusive_works", 0)}
        html = get(url) if url else ""
        if not html:
            r["strategy"] = "no-response"
            results.append(r)
            print(f"[{i}/{len(rows)}] {t['platform'][:20]:22} no-response", flush=True)
            continue
        sel = None
        for name, fn in (("jsonld", try_jsonld), ("next", try_next), ("nuxt", try_nuxt)):
            got = fn(html)
            got = [g for g in got if CHAPTERISH.search(g["title"])] or got
            if len(got) >= 2:
                r["strategy"], r["sample"] = name, got[:3]
                break
        else:
            got, sel = try_markup(html)
            if len(got) >= 2:
                r["strategy"], r["sample"], r["selector"] = "markup", got[:3], sel
            else:
                r["strategy"] = "none"
        results.append(r)
        print(f"[{i}/{len(rows)}] {t['platform'][:20]:22} {r['strategy']}"
              f"{' ' + str(sel) if sel and r['strategy'] == 'markup' else ''}", flush=True)

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "extract.yaml").write_text(
        "# Second-pass reconnaissance: which extraction strategy actually returns dated chapters.\n"
        "# A strategy counts only if it yielded >= 2 entries with both a date and a chapter-like\n"
        "# label — one dated thing on a page is usually the 単行本 release, which is the trap the\n"
        "# first pass fell into on ガンガンONLINE.\n"
        f"source: derived\nrole: reconnaissance\nretrieved: {a.retrieved}\n"
        + yaml.safe_dump({"platforms": results}, allow_unicode=True, sort_keys=False))
    c = Counter(r["strategy"] for r in results)
    print("\n" + ", ".join(f"{k}: {v}" for k, v in c.most_common()))
    print("written:", out / "extract.yaml")


if __name__ == "__main__":
    main()
