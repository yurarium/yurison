#!/usr/bin/env python3
"""Reconnaissance across every unwatched platform (REQUIREMENTS §6).

The long tail was previously written off as offering no leverage, on the strength of six hosts
probed for two engines. That was a conclusion drawn from a sample chosen for convenience. This
probes all of them for everything, so the question "how would we reach this one" has an answer per
platform rather than a shrug.

For each host it records, from at most a handful of requests:

  - robots.txt, and specifically whether the paths we would use are permitted;
  - feed endpoints at the conventional locations, and whether they actually return a feed rather
    than a soft 404 HTML page (the trap comic-boost.com fell into on the first pass);
  - sitemaps, which are a permitted enumeration route and often the cheapest one;
  - on a representative work page: whether it is server-rendered, and which embedded payload it
    carries (__NEXT_DATA__, __NUXT__, JSON-LD, Apollo, or plain markup);
  - whether a date appears in that payload at all — the single thing that decides usability, since
    a release with no date cannot be placed on a timeline.

Nothing here fetches more than one work page per host, and nothing is stored but the shape of the
site. This is a survey, not a scrape.

Usage:  probe.py --targets data/coverage/recon-targets.yaml --out data/coverage --retrieved DATE
"""
import argparse, json, pathlib, re, socket, sys, time, urllib.error, urllib.parse, urllib.request

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.0
TIMEOUT = 20
FEEDS = ["/atom", "/rss", "/feed", "/rss.xml", "/feed.xml", "/atom.xml", "/index.xml"]
SITEMAPS = ["/sitemap.xml", "/sitemap_index.xml", "/sitemaps.xml"]

DATE_PAT = re.compile(
    r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}|"
    r'"(?:updated|published|created|release|delivery|start)[A-Za-z_]*"\s*:\s*"?\d|'
    r"更新日|公開日|配信日|掲載日")

PAYLOADS = [
    ("next", re.compile(r'<script id="__NEXT_DATA__"')),
    ("nuxt", re.compile(r"window\.__NUXT__")),
    ("jsonld", re.compile(r'type="application/ld\+json"')),
    ("apollo", re.compile(r"__APOLLO_STATE__")),
    ("initial", re.compile(r"window\.__(?:INITIAL|PRELOADED)_?[A-Z_]*__")),
]


def get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(400_000)
            return r.status, r.headers.get("Content-Type", ""), body.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "") if e.headers else "", ""
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
        return None, str(getattr(e, "reason", e))[:60], ""
    finally:
        time.sleep(PAUSE)


def is_feed(ct, body):
    """A 200 is not a feed. Several sites answer every unknown path with their homepage."""
    if "xml" in (ct or "").lower() or "rss" in (ct or "").lower():
        return True
    head = (body or "")[:400].lstrip()
    return head.startswith("<?xml") or "<rss" in head or "<feed" in head


def disallow_rules(body):
    """Every path `User-agent: *` is told to keep out of, in the order the file lists them.

    EVERY RULE IS KEPT, AND ONCE ONLY TWELVE WERE. This returned `dis[:12]`, which kept the recorded
    survey short and quietly shortened the rule set `allowed()` matches against. NDL Search
    publishes thirty rules and `Disallow: /api` is the twenty-ninth, so a robots check on that host
    reported `/api/opensearch` permitted while the file forbids it, and three rounds of author
    lookups went out on a route robots refuses. A gate that answers from a cut-down copy of the
    rules is worse than no gate, because it reads as having checked (STANDING-INSTRUCTIONS §4).

    Parsing is separate from fetching so a test can hold a real robots.txt and assert what it
    yields. That is also the only way this particular bug could have been caught offline.
    """
    dis, ua_all = [], False
    for line in (body or "").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            ua_all = v == "*"
        elif k == "disallow" and ua_all and v:
            dis.append(v)
    return dis


def robots_rules(host):
    st, _, body = get(f"https://{host}/robots.txt")
    if st != 200 or not body:
        return {"present": False, "disallow": []}
    return {"present": True, "disallow": disallow_rules(body)}


def allowed(path, dis):
    return not any(path.startswith(d.rstrip("*")) for d in dis if d and d != "/")


def probe(name, host, work_url):
    r = {"platform": name, "host": host}
    rb = robots_rules(host)
    r["robots"] = rb
    r["feeds"] = []
    for p in FEEDS:
        if not allowed(p, rb["disallow"]):
            continue
        st, ct, body = get(f"https://{host}{p}")
        if st == 200 and is_feed(ct, body):
            r["feeds"].append({"path": p, "content_type": ct.split(";")[0]})
            break
    for p in SITEMAPS:
        st, ct, body = get(f"https://{host}{p}")
        if st == 200 and is_feed(ct, body):
            n = len(re.findall(r"<loc>", body))
            r["sitemap"] = {"path": p, "urls_in_first_page": n,
                            "is_index": "<sitemapindex" in body[:400]}
            break
    if work_url:
        st, ct, body = get(work_url)
        r["work_page"] = {"url": work_url, "status": st}
        if body:
            r["work_page"]["bytes"] = len(body)
            r["work_page"]["payload"] = [n for n, pat in PAYLOADS if pat.search(body)] or ["markup"]
            r["work_page"]["has_date"] = bool(DATE_PAT.search(body))
            # Server-rendered content, as opposed to a shell that renders client-side.
            text = re.sub(r"<script.*?</script>", " ", body, flags=re.S)
            text = re.sub(r"<[^>]+>", " ", text)
            r["work_page"]["visible_text_chars"] = len(re.sub(r"\s+", " ", text).strip())
    return r


def verdict(r):
    """What route this platform has. Ordered by cost: a feed beats a page, a page beats a browser."""
    wp = r.get("work_page") or {}
    if r.get("feeds"):
        return "feed"
    if wp.get("status") == 200 and wp.get("has_date") and (wp.get("visible_text_chars") or 0) > 800:
        return "server-rendered-page"
    if wp.get("status") == 200 and wp.get("has_date"):
        return "page-with-date-thin"
    if r.get("sitemap"):
        return "sitemap-only"
    if wp.get("status") == 200:
        return "page-no-date"
    return "unreachable"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    tg = yaml.safe_load(open(a.targets)) or {}
    rows = tg.get("targets") or []
    if a.limit:
        rows = rows[: a.limit]

    out, results = pathlib.Path(a.out), []
    out.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(rows, 1):
        try:
            r = probe(t["platform"], t["host"], t.get("work_url"))
        except Exception as e:                                     # noqa: BLE001
            r = {"platform": t["platform"], "host": t["host"], "error": type(e).__name__}
        r["verdict"] = verdict(r)
        r["exclusive_works"] = t.get("exclusive_works", 0)
        results.append(r)
        print(f"[{i}/{len(rows)}] {t['platform'][:22]:24} {r['verdict']}", flush=True)

    (out / "recon.yaml").write_text(
        "# Reconnaissance across unwatched platforms. Survey only — one work page per host.\n"
        "# `verdict` is the cheapest route found, not a judgment about whether to take it.\n"
        f"source: derived\nrole: reconnaissance\nretrieved: {a.retrieved}\n"
        + yaml.safe_dump({"platforms": results}, allow_unicode=True, sort_keys=False))
    print("\nwritten:", out / "recon.yaml")


if __name__ == "__main__":
    main()
