#!/usr/bin/env python3
"""Discovery queue from 百合ナビ's news feed (REQUIREMENTS §1).

Publisher labelling only finds works a publisher chose to label. A large share of yuri one-shots
and web serials carry no 百合 label at all and run on platforms that never apply one — 少年ジャンプ+
among them. Nothing in Tier A or B announces those. Editorial coverage does.

百合ナビ is Tier C: **discovery only, never attesting**. Nothing here becomes a record. Entries land
in a queue for a human to confirm against the platform, which is what supplies the actual fields.
The queue is the point — it is what stops the database silently consisting only of works someone
else already tagged.

Usage:  discover.py --out data/queue --cache ~/workspace/yurinavi-cache --retrieved 2026-08-01
"""
import argparse, datetime, json, pathlib, re, time, urllib.request
import xml.etree.ElementTree as ET
from collections import Counter

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"

# Headline shapes worth queueing, vs. commerce noise that is not a publication event.
SIGNALS = [
    ("new-serial", r"連載(開始|スタート)|WEBで(スタート|連載)|新連載"),
    ("oneshot", r"読み切り|読切"),
    ("new-volume", r"(単行本|コミックス)[^。]{0,8}(発売|刊行)|新刊"),
    ("adaptation", r"アニメ化|ドラマ化|映像化"),
    ("roundup", r"まとめ|注目百合ニュース"),
]
IGNORE = r"セール|OFF|ポイント還元|還元|無料公開中止|キャンペーン|抽選|プレゼント"

MIN_ITEMS = 3

# Discovery resolves WHERE a work lives; confirmation then resolves what it is. Articles link out
# to the platform, so the platform and its work code are extracted here and carried on the
# candidate. Recognising a host is not attesting anything — it only says where to look.
PLATFORMS = [
    ("kadokomi", r"https?://comic-walker\.com/detail/([A-Za-z0-9_]+)"),
    ("comic-days", r"https?://comic-days\.com/(?:episode|series)/(\d+)"),
    ("kuragebunch", r"https?://kuragebunch\.com/(?:episode|series)/(\d+)"),
    ("ichicomi", r"https?://ichicomi\.com/(?:episode|series)/(\d+)"),
]


def fetch_article(url, cache):
    """Articles are fetched only to find the outbound platform link."""
    key = re.sub(r"[^a-z0-9]+", "_", url)[-70:]
    f = cache / "articles" / f"{key}.html"
    f.parent.mkdir(parents=True, exist_ok=True)
    if f.exists():
        return f.read_text()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    except Exception:
        return ""
    finally:
        time.sleep(1.2)
    f.write_text(t)
    return t


def resolve_platform(html):
    for name, pat in PLATFORMS:
        m = re.search(pat, html)
        if m:
            return name, m.group(1)
    return None, None


def fetch(url, cache, name="feed.xml"):
    p = cache / name
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        t = r.read().decode("utf-8", "replace")
    p.write_text(t)
    time.sleep(1.0)
    return t


def sitemap_posts(cache, days, today):
    """Every post URL in the window, from WordPress's own sitemap.

    The RSS feed returns thirteen items and honours no pagination — ?paged=, ?posts_per_page= and
    /page/N/feed/ all redirect back to the same thirteen. So discovery only ever saw the last
    fortnight or so of coverage, and one-shots are exactly what that misses: they are announced
    once and never mentioned again. One one-shot had reached the feed; the sitemap lists 202
    one-shot articles, 5 of them inside the current window.

    Post URLs carry their date, so the window is applied before anything is fetched.
    """
    idx = fetch("https://yurinavi.com/wp-sitemap.xml", cache, "sitemap.xml")
    subs = [u for u in re.findall(r"<loc>([^<]+)</loc>", idx) if "posts-post" in u]
    urls = []
    for i, s in enumerate(subs):
        urls += re.findall(r"<loc>([^<]+)</loc>", fetch(s, cache, f"sitemap-{i}.xml"))
    cutoff = today - datetime.timedelta(days=days)
    out = []
    for u in urls:
        m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", u)
        if not m:
            continue
        d = datetime.date(*map(int, m.groups()))
        if cutoff <= d <= today:
            out.append((u, d))
    return sorted(out, key=lambda x: x[1], reverse=True)


def headline_of(html):
    m = re.search(r"<title>([^<]*)</title>", html)
    if not m:
        return ""
    # WordPress renders "<headline> | 百合ナビ"; the site name is not part of the headline.
    return re.sub(r"\s*[|｜]\s*百合ナビ.*$", "", m.group(1)).strip()


def titles_in(headline):
    """Japanese headlines quote work titles in 「」 or 『』. Take those, not the whole headline."""
    return [m.strip() for m in re.findall(r"[「『]([^」』]{2,60})[」』]", headline)]


def signal_of(headline):
    if re.search(IGNORE, headline):
        return None
    for name, pat in SIGNALS:
        if re.search(pat, headline):
            return name
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--feed", default="https://yurinavi.com/feed")
    ap.add_argument("--days", type=int, default=60,
                    help="also read the sitemap back this far; 0 for RSS only")
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    root = ET.fromstring(fetch(a.feed, cache))
    items = root.findall(".//item")
    if len(items) < MIN_ITEMS:
        raise SystemExit(f"HEALTH: feed returned {len(items)} items (< {MIN_ITEMS}). Refusing to write.")

    # The RSS items, plus every post in the window that the RSS cannot reach.
    seen_urls = {(it.findtext("link") or "").strip() for it in items}
    extra = []
    if a.days:
        today = datetime.date(*(int(x) for x in a.retrieved.split("-")))
        for u, d in sitemap_posts(cache, a.days, today):
            if u in seen_urls:
                continue
            html = fetch_article(u, cache)
            extra.append((headline_of(html), u, str(d)))

    rows, counts = [], Counter()
    for head, art, when in ([((it.findtext("title") or "").strip(),
                              (it.findtext("link") or "").strip(),
                              (it.findtext("pubDate") or "").strip()) for it in items] + extra):
        sig = signal_of(head)
        counts[sig or "ignored"] += 1
        if not sig or sig == "roundup":
            continue
        plat, code = resolve_platform(fetch_article(art, cache)) if art else (None, None)
        for t in titles_in(head):
            rows.append({"work_title": t, "signal": sig, "headline": head,
                         "url": art, "platform": plat, "platform_code": code,
                         "source": "yurinavi", "announced": when})

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = [
        "# DISCOVERY QUEUE — candidates only. Not records, not evidence of anything.",
        "#",
        "# 百合ナビ is Tier C: it may say a work exists, and nothing else (REQUIREMENTS §1).",
        "# Each entry needs confirming against the publisher or platform, which is what supplies",
        "# the fields. Works reaching the database this way will often have marketing_label: none",
        "# and require a human content_tier call — that is the whole reason the queue exists.",
        "source: yurinavi",
        "role: discovery-only",
        f"retrieved: {a.retrieved}",
        "record_type: discovery_queue",
        "candidates:",
    ]
    for r in sorted(rows, key=lambda r: r["announced"], reverse=True):
        L.append(f"  - work_title: {json.dumps(r['work_title'], ensure_ascii=False)}")
        for k in ("signal", "announced", "url", "platform", "platform_code"):
            if r.get(k):
                L.append(f"    {k}: {json.dumps(r[k], ensure_ascii=False)}")
        L.append(f"    headline: {json.dumps(r['headline'], ensure_ascii=False)}")
        L.append("    status: unconfirmed")
    L.append("")
    (out / "yurinavi.yaml").write_text("\n".join(L))

    print(f"feed items     : {len(items)}")
    from collections import Counter as _C
    print(f"candidates     : {len(rows)}")
    plats = _C(r.get("platform") or "unresolved" for r in rows)
    print(f"  platforms    : {dict(plats)}")
    for k, v in counts.most_common():
        print(f"  {str(k):12}: {v}")
    print(f"written        : {out}/yurinavi.yaml")


if __name__ == "__main__":
    main()
