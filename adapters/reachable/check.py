#!/usr/bin/env python3
"""Is it still there? (REQUIREMENTS §5)

A 読切 is published once and often taken down. An archive sweep therefore recovers two kinds of
work at the same time — ones still readable and ones that only ever existed — and they must not
look alike in the interface. "Complete in one instalment, free" is a lie about a page that 404s.

This asks the platform, and records what it said and when. Nothing is inferred from age: a 2019
one-shot may still be up and a 2026 one may already be gone, so the only way to know is to ask.

A 404 is the EASY case and mostly not what happens. 散らないで菊 on コミックゼノン answers 200 with
32 KB of page, its title, its author — and 公開終了 in the body and an Atom series feed carrying no
entries at all. Judging by status code, or by page size, calls that readable. It is not.

Four answers, kept distinct because they mean different things:

  present    the page loads and the platform still lists episodes
  gone       404 or 410 — the platform says it is not there
  withdrawn  the page loads and says 公開終了, or its series feed is served empty. The work existed
             and no longer can be read. This is the common shape for an expired 読切.
  blocked    403, a timeout, or a network refusal. NOT a withdrawal. Says nothing about the work,
             only about our access, and geoblocked hosts land here.

A `gone` result does not delete anything. The work was published, on that date, by that author, and
that stays true — the record simply stops claiming you can read it.

Usage:  check.py --series data/build/series.json --out data/source/reachable \
                 --retrieved 2026-08-02 [--state oneshot] [--limit 400]
"""
import argparse, json, pathlib, re, sys, time
import urllib.error, urllib.request

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.0
ENDED = re.compile(r"公開終了|掲載終了|配信終了|販売終了")
ATOM = re.compile(r"/atom/series/(\d+)")


def fetch(url, limit=200_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read(limit).decode("utf-8", "replace"), r.status
    except urllib.error.HTTPError as e:
        return "", e.code
    except (urllib.error.URLError, OSError, ValueError):
        return "", 0
    finally:
        time.sleep(PAUSE)


def probe(url):
    body, code = fetch(url)
    if code in (404, 410):
        return "gone", code, "status"
    if not body:
        return "blocked", code, "no response"
    if len(body) < 2000:
        return "gone", code, "stub page"
    if ENDED.search(body):
        return "withdrawn", code, "page says 公開終了"
    # GigaViewer keeps serving a withdrawn work's page and its series feed; the feed is simply
    # empty. That emptiness is the platform stating there is nothing to read, and it is the only
    # signal on installs that show no 公開終了 text.
    m = ATOM.search(body)
    if m:
        host = re.match(r"https?://([^/]+)", url)
        if host:
            feed, _ = fetch(f"https://{host.group(1)}/atom/series/{m.group(1)}", 400_000)
            if feed and "<entry>" not in feed:
                return "withdrawn", code, "series feed served empty"
    return "present", code, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--state", help="only rows in this state (e.g. oneshot)")
    ap.add_argument("--limit", type=int, default=500)
    a = ap.parse_args()

    rows = json.load(open(a.series))["series"]
    if a.state:
        rows = [r for r in rows if r.get("state") == a.state]
    rows = [r for r in rows if r.get("url")][: a.limit]
    if not rows:
        sys.exit("nothing to check")

    out, tally = [], {}
    for r in rows:
        status, code, why = probe(r["url"])
        tally[status] = tally.get(status, 0) + 1
        out.append({"work": r["work"], "platform": r["platform"], "url": r["url"],
                    "status": status, "code": code, "why": why})
        if status != "present":
            print(f"  {status:10} {code or '-':>4}  {r['work'][:26]:28} {r['platform'][:12]:14} {why}")

    d = pathlib.Path(a.out)
    d.mkdir(parents=True, exist_ok=True)
    L = ["# Whether each work's page is still served, and what the platform answered.",
         "#",
         "# A 読切 is published once and often taken down, so an archive sweep recovers works that",
         "# are still readable and works that only ever existed — and they must not look alike.",
         "# Nothing here is inferred from age: a 2019 one-shot may still be up and a 2026 one gone.",
         "#",
         "# `gone` (404/410) is the platform's own answer. `blocked` (403, timeout, refusal) says",
         "# nothing about the work and only about our access; geoblocked hosts land there and are",
         "# NOT withdrawals. A `gone` result deletes nothing — the work was published, on that date,",
         "# by that author, and that stays true. The record just stops claiming it can be read.",
         "source: reachable", "role: availability", f"retrieved: {a.retrieved}",
         "record_type: availability_check", f"checked: {len(out)}", "works:"]
    for o in out:
        L.append(f"  - work: {json.dumps(o['work'], ensure_ascii=False)}")
        L.append(f"    platform: {json.dumps(o['platform'], ensure_ascii=False)}")
        L.append(f"    url: {json.dumps(o['url'], ensure_ascii=False)}")
        L.append(f"    status: {o['status']}")
        if o.get("why"):
            L.append(f"    why: {json.dumps(o['why'], ensure_ascii=False)}")
        L.append(f"    code: {o['code']}")
        L.append(f"    checked: {a.retrieved}")
    L.append("")
    (d / "availability.yaml").write_text("\n".join(L))
    print(f"\nchecked {len(out)}: {tally}")


if __name__ == "__main__":
    main()
