#!/usr/bin/env python3
"""Discovery queue from 百合ナビ's news feed (REQUIREMENTS §1).

Publisher labelling only finds works a publisher chose to label. A large share of yuri one-shots
and web serials carry no 百合 label at all and run on platforms that never apply one — 少年ジャンプ+
among them. Nothing in Tier A or B announces those. Editorial coverage does.

百合ナビ is Tier C: **discovery only, never attesting**. Nothing here becomes a record. Entries land
in a queue for a human to confirm against the platform, which is what supplies the actual fields.
The queue is the point — it is what stops the database silently consisting only of works someone
else already tagged.

Usage:  discover.py --out data/queue --cache $YURI_CACHE/yurinavi-cache --retrieved 2026-08-01
"""
import argparse, datetime, json, pathlib, re, sys, time, urllib.request

import yaml
import xml.etree.ElementTree as ET
from collections import Counter

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"

# Headline shapes worth queueing, vs. commerce noise that is not a publication event.
# Order matters: roundup is tested FIRST. A まとめ headline names the work it leads with, so it
# also matches 連載開始 or 読み切り — and it was being filed as that work's announcement. But the
# roundup's body links to 百合ナビ's own per-work articles, not to the platform, so the candidate
# could never resolve. Those per-work articles are in the sitemap and reach us on their own; the
# roundup is a duplicate of them with the link stripped out.
SIGNALS = [
    ("roundup", r"まとめ|注目百合ニュース"),
    ("new-serial", r"連載(開始|スタート)|WEBで(スタート|連載)|新連載"),
    ("oneshot", r"読み切り|読切"),
    ("new-volume", r"(単行本|コミックス)[^。]{0,8}(発売|刊行)|新刊"),
    ("adaptation", r"アニメ化|ドラマ化|映像化"),
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


def registry_hosts():
    """host -> platform id, from every register rather than a list kept by hand.

    The hand-kept list named four platforms. comic-earthstar.com has been in the GigaViewer
    registry throughout and was not in it, so articles linking straight to the work were filed as
    "no platform link" and the resolver was the thing at fault.

    AND IT READ TWO OF THE THREE REGISTERS. `data/platforms.yaml` is the project's own, where a
    ruling about a platform is written, and this asked the adapters' files instead: マンガワン is
    in it with `manga-one.com` and an article linking straight there resolved to nothing. Three
    hand-written entries papered over three of the gaps. `facts/platform` merges all three and is
    the one place that knows which host belongs to which platform.
    """
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from facts import platform as _platform
    return dict(_platform.ids())


def unshorten(url, cache):
    """t.co and friends hide the destination. Eight of the links in the unresolved articles were
    shortened, so the work they pointed at was invisible to any amount of pattern matching."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.url
    except Exception:                                              # noqa: BLE001
        return url
    finally:
        time.sleep(0.4)


SHORTENERS = ("t.co", "bit.ly", "ow.ly", "buff.ly", "urx.blue", "ux.nu")


def resolve_near(html, title, hosts):
    """`(platform, code, url)` for the platform link nearest a given work title in the body.

    THE URL IS CARRIED NOW AND WAS THROWN AWAY. Discovery found the work's own address, kept the
    platform and a code parsed out of it, and dropped the address itself; the queue then held
    candidates nothing could fetch, so a work announced on a platform this reads sat unheld for ten
    weeks. `adapters/admit.py` is what needed it.

    A まとめ article covers a dozen works and links to each. Taking the first platform link in the
    page attaches whichever work happens to appear first to every title in it, which is worse than
    leaving it unresolved. So the link is chosen by distance from where the title is mentioned.
    """
    i = html.find(title)
    if i < 0:
        return None, None, None
    best = None
    for m in re.finditer(r'href="(https?://([^/"]+)[^"]*)"', html):
        if m.group(2) not in hosts:
            continue
        d = abs(m.start() - i)
        if best is None or d < best[0]:
            best = (d, m.group(1), m.group(2))
    if not best or best[0] > 4000:      # further than that is a different section of the article
        return None, None, None
    code = re.search(r"/(?:episode|series|detail|manga|comic|title)/([A-Za-z0-9_]+)", best[1])
    return hosts[best[2]], (code.group(1) if code else None), best[1]


#: HOSTS AN ARTICLE LINKS TO THAT ARE NOT WHERE THE WORK IS. The site's own furniture, the share
#: buttons, and the microformat profile every WordPress theme points at.
#: MATCHED BY SUFFIX, because a share button is served from a subdomain: the host is
#: `social-plugins.line.me` and the list said `line.me`, so the first thing every article pointed
#: at was a LINE button. 百合ナビ's own fanbox is here for the same reason.
FURNITURE = ("yurinavi.com", "gmpg.org", "twitter.com", "x.com", "facebook.com",
             "hatena.ne.jp", "line.me", "instagram.com", "youtube.com", "youtu.be",
             "pinterest.com", "feedly.com", "fanbox.cc", "note.com", "pixiv.net")


def outbound_host(html, title=None):        # noqa: ARG001  (title kept for the caller's symmetry)
    """The host an article points at that is neither furniture nor a platform we know.

    A PLATFORM NOBODY HAS REGISTERED IS NOT NO PLATFORM. 最恐呪物令嬢 was announced on 2026-08-15
    and its article links straight to `younganimal.com`; the queue recorded it as naming no
    platform, so the reason a reader was given for it sitting there was wrong. The work is on a
    site 白泉社 runs and the register does not hold, which is one edit in one file and a decision
    for a person rather than something to be inferred from an article.

    NEVER RECORDED AS THE PLATFORM, only as the host. What `facts/platform.serves_openly` answers
    for is the register, and this is the question that comes before it.
    """
    # THE WHOLE ARTICLE, NOT A WINDOW ROUND THE TITLE. `find` returns the first occurrence, which
    # is the `<title>` tag 57,000 characters before the link 最恐呪物令嬢's article carries, so a
    # window round it saw nothing. Safe to widen because this reports a HOST and never a platform:
    # the furniture list is what keeps the answer meaningful, not the distance.
    hosts = registry_hosts()
    for m in re.finditer(r'href="https?://([^/"]+)', html):
        h = m.group(1)
        if (h in hosts or h in SHORTENERS
                or any(h == f or h.endswith("." + f) for f in FURNITURE)):
            continue
        return h
    return None


def resolve_platform(html, cache=None, title=None):
    """`(platform, code, url)`: where a work lives, and the address the article linked to."""
    hosts = registry_hosts()
    if title:
        p, c, u = resolve_near(html, title, hosts)
        if p:
            return p, c, u
    for name, pat in PLATFORMS:                 # explicit forms first: they carry a clean code
        m = re.search(pat, html)
        if m:
            return name, m.group(1), m.group(0)
    links = re.findall(r'href="(https?://[^"]+)"', html)
    for u in links:
        h = re.match(r"https?://([^/]+)", u).group(1)
        if h in hosts:
            code = re.search(r"/(?:episode|series|detail|manga|comic|title)/([A-Za-z0-9_]+)", u)
            return hosts[h], (code.group(1) if code else None), u
    for u in links:                             # only then pay for the redirects
        h = re.match(r"https?://([^/]+)", u).group(1)
        if h not in SHORTENERS:
            continue
        real = unshorten(u, cache)
        rh = re.match(r"https?://([^/]+)", real)
        if rh and rh.group(1) in hosts:
            code = re.search(r"/(?:episode|series|detail|manga|comic|title)/([A-Za-z0-9_]+)", real)
            return hosts[rh.group(1)], (code.group(1) if code else None), real
    return None, None, None


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
        art_html = fetch_article(art, cache) if art else ""
        for t in titles_in(head):
            # Resolved per title, not per article: a まとめ names several works and links to each.
            plat, code, wurl = (resolve_platform(art_html, cache, t) if art_html
                                else (None, None, None))
            # WHERE THE ARTICLE POINTS WHEN NO REGISTER KNOWS IT, so the queue can say "a platform
            # nobody has registered" rather than "no platform", which is what somebody acts on.
            host = None if plat else (outbound_host(art_html, t) if art_html else None)
            rows.append({"work_title": t, "signal": sig, "headline": head,
                         "url": art, "platform": plat, "platform_code": code,
                         "work_url": wurl, "platform_host": host,
                         "source": "yurinavi", "announced": when})

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    # ── CUMULATIVE, FOR THE REASON `webcomics/coverage.py` GIVES ABOUT ITS OWN FILE ──────────
    #
    # THIS REWROTE THE QUEUE FROM THE CURRENT FEED WINDOW, so a candidate older than the window
    # vanished on the next run whether or not anything had been done about it. 贋作の第十番 was
    # announced on チャンピオンクロス on 7 June, sat unadmitted while the queue said a human must
    # confirm it, and was dropped by a run in August without a word. An announcement is a thing
    # that happened, and a work leaving 百合ナビ's recent news says nothing about the work.
    #
    # A FRESH ROW WINS, because a later run resolves what an earlier one could not: the platform,
    # the code and the work's own address are exactly what a re-read of the article supplies.
    was = out / "yurinavi.yaml"
    if was.exists():
        held = {c.get("work_title"): c for c in
                ((yaml.safe_load(was.read_text()) or {}).get("candidates") or [])}
        fresh = {r["work_title"] for r in rows}
        carried = [c for t_, c in sorted(held.items()) if t_ and t_ not in fresh]
        # AND A CARRIED ROW IS RE-RESOLVED WHERE IT NEVER RESOLVED, because the resolver improves
        # and the row does not. 贋作の第十番 was carried with a platform and no address, which is
        # exactly the state that keeps a work out of the target list; the article is on disk from
        # the run that first read it, so asking again costs nothing.
        again = 0
        for c in carried:
            row = {k: c.get(k) for k in
                   ("work_title", "signal", "announced", "url", "headline",
                    "platform", "platform_code", "work_url", "platform_host")}
            if not row.get("work_url") and row.get("url"):
                html = fetch_article(row["url"], cache)
                if html:
                    plat, code, wurl = resolve_platform(html, cache, row["work_title"])
                    if wurl:
                        row.update(platform=plat or row.get("platform"),
                                   platform_code=code or row.get("platform_code"),
                                   work_url=wurl)
                        again += 1
            rows.append(row)
        if again:
            print(f"re-resolved    : {again} carried candidate(s) that had no address")
        print(f"carried forward: {len(carried)} candidate(s) older than the feed window")
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
        for k in ("signal", "announced", "url", "platform", "platform_code", "work_url",
                  "platform_host"):
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
