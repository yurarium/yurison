#!/usr/bin/env python3
"""Fill the fields a row is missing, from the page a reader would open (REQUIREMENTS §5).

The platform adapters run per platform and each does one job well. What they leave behind is not a
platform gap but a row gap: a single 読切 reached through a 百合ナビ link on a host whose adapter
only ever walked that host's serialised titles, and which therefore arrived with a date, a chapter
name and nothing else. 吸血少女とウンディーネ on コミック アース・スター is one row. So is 夕子先輩は育て
られない on 一迅プラス. Neither is worth a platform pass; both are worth one fetch.

This takes the rows the build says are incomplete and goes to their page, by the routes that are
already proven:

  gigaviewer-feed  The episode page links /atom/series/<id> even for a one-shot, which is a
                   one-entry series. Fetching that feed and its ?free_only=1 variant gives the
                   access state, and every entry carries its author.
  title-tail       フラコミlike! writes <title> as 作品 | いつでも無料 | フラコミlike! | 空木帆子 —
                   the author is the last segment and the access is stated in the second. Read
                   both only when the platform's own name is in the expected position, so a
                   differently-shaped title yields nothing rather than a wrong name.

Nothing is guessed. A route that does not fire leaves the field empty, which is the honest state.

Usage:  fields.py --out data/source/webpages --retrieved 2026-10-15
        (the incomplete rows come from the store; `--gaps FILE` reads a file instead)
"""
import argparse, html as _html, json, pathlib, re, subprocess, sys, time
import urllib.error, urllib.request
from collections import Counter, defaultdict

import yaml
import pathlib as _pl, sys as _sy                                         # noqa: E401,E402
_sy.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))    # noqa: E402
import htmlbits as _htmlbits                                            # noqa: E402
_sy.path.insert(0, str(_pl.Path(__file__).resolve().parents[1] / "gigaviewer"))
import series_feeds as _sf                                              # noqa: E402

UA = "Mozilla/5.0 (compatible; yurarium/0.1; +https://yurarium.github.io/)"
PAUSE = 1.0

ATOM_SERIES = re.compile(r"/atom/series/(\d+)")
ENTRY = _htmlbits.ATOM_ENTRY
E_TITLE = _htmlbits.TITLE
E_UPDATED = re.compile(r"<updated>([^<]*)</updated>")
E_LINK = re.compile(r'<link href="([^"]+)"')
E_AUTHOR = re.compile(r"<author>\s*<name>([^<]*)</name>", re.S)
TITLE = _htmlbits.TITLE

# 作品 | いつでも無料 | フラコミlike! | 空木帆子 — four segments, the platform third and the author
# last. Requiring the platform name in place is what keeps this from reading any old title tail.
# Deliberately empty. It held flowercomics.jp, reading "いつでも無料" out of the page title as an
# access state for the whole work — and the platform's own per-chapter badges say Episode.2 -2 is
# チケット and Episode.4 -1 is paid. The banner was marketing, not a statement about a chapter, and a
# work-level reading of it was wrong on most of the work's chapters. adapters/shogakukan/ reads the
# badges instead. Kept as a named, empty route so the lesson stays with the mechanism.
TITLE_TAIL = {}

# Hosts that name their authors with a link to the author's own page. That link is the platform
# saying "this is a person, and here is their page" — the one form of author statement that cannot
# be confused with a tagline, a subtitle or a chapter name, which is what every looser reading of
# "the text next to the title" has turned out to be. コロコロオンライン writes the work title into a
# single h1 and its authors into three such links; its <title> runs them all together as
# "DOUBLE HELIX BLOSSOM SWAV アサウラ 西馬ごめゆき" with no separator, so the link is the only place
# the boundary between title and author is stated rather than guessed.
AUTHOR_LINK = {"www.corocoro.jp": r'href="/author/\d+"[^>]*>(?:\s*<[^>]*>)*\s*([^<]{1,24})'}
CHROME = next((c for c in ("/snap/bin/chromium", "/usr/bin/chromium",
                           "/usr/bin/chromium-browser", "/usr/bin/google-chrome")
               if pathlib.Path(c).exists()), None)


def render(url):
    """These pages build their content in JavaScript; there is nothing in the served HTML to read."""
    if not CHROME:
        return ""
    try:
        out = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--virtual-time-budget=11000",
             f"--user-agent={UA}", "--dump-dom", url], capture_output=True, text=True, timeout=140)
    except (subprocess.TimeoutExpired, OSError):
        return ""
    time.sleep(PAUSE)
    return out.stdout or ""


def author_links(url):
    pat = AUTHOR_LINK.get(host_of(url))
    if not pat:
        return None
    names = [_html.unescape(x).strip() for x in re.findall(pat, render(url))]
    names = [n for n in dict.fromkeys(names) if n]
    return " / ".join(names) or None


def get(url, limit=3_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.read(limit).decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return ""
    finally:
        time.sleep(PAUSE)


def host_of(u):
    m = re.match(r"https?://([^/]+)", u or "")
    return m.group(1).lower() if m else ""


def gigaviewer_feed(url, html):
    """Chapters with author and access, from the series feed the page links."""
    m = ATOM_SERIES.search(html or "")
    if not m:
        return None, []
    host = host_of(url)
    xml = get(f"https://{host}/atom/series/{m.group(1)}")
    if not xml:
        return None, []
    free = set(E_LINK.findall(get(f"https://{host}/atom/series/{m.group(1)}?free_only=1") or ""))
    author, out = None, []
    for b in ENTRY.findall(xml):
        t, u = E_TITLE.search(b), E_UPDATED.search(b)
        if not (t and u):
            continue
        au, ln = E_AUTHOR.search(b), E_LINK.search(b)
        if au and not author:
            author = _html.unescape(au.group(1)).strip()
        # THE DATE IN JAPAN, which slicing the UTC stamp is not: a chapter out at 15:00Z is the
        # next day there, and the platform's own list says so.
        row = {"title": _html.unescape(t.group(1)).strip(), "updated": _sf.jst_date(u.group(1))}
        if free and ln:
            row["access_modes"] = ["free"] if ln.group(1) in free else ["purchase"]
        out.append(row)
    return author, out


MAGAPOKE = re.compile(r"^https?://pocket\.shonenmagazine\.com/title/\d+/episode/\d+")
NUXT = re.compile(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', re.S)


def magapoke_episode(html):
    """`(author, chapter)` from a マガポケ episode page, or `(None, None)`.

    THE FEED THAT LISTS EVERY CHAPTER STATES NO ACCESS, and the work page that does draws ten. The
    episode page states its own in the data it is rendered from, a Nuxt payload in which every
    value is an index into one array: `point` is the price, `ticket_rental_enabled` says a 作品
    チケット opens it, and `is_page_visible` says it can be read now without either. Checked
    against the badges the rendered capture reads on 将来的に死んでくれ, one of each kind, and all
    three agreed: 第3話 free, 第5話 a ticket, 第42話 sixty points.
    """
    m = NUXT.search(html or "")
    if not m:
        return None, None
    try:
        arr = json.loads(m.group(1))
    except ValueError:
        return None, None

    def at(v):
        return arr[v] if isinstance(v, int) and not isinstance(v, bool) and 0 <= v < len(arr) else v

    ep = next((x for x in arr if isinstance(x, dict) and "episode_id" in x and "point" in x), None)
    if not ep:
        return None, None
    title = at(ep.get("episode_name"))
    opened = str(at(ep.get("start_time")) or "")[:10]
    if not title or not opened:
        return None, None
    if at(ep.get("is_page_visible")) == 1 and not at(ep.get("point")):
        modes = ["free"]
    elif at(ep.get("ticket_rental_enabled")) == 1:
        modes = ["free-timed"]
    elif at(ep.get("point")) and at(ep.get("single_sale_enabled")) == 1:
        modes = ["purchase"]
    else:
        modes = []
    work = next((x for x in arr if isinstance(x, dict) and "author_text" in x), None)
    author = str(at(work.get("author_text")) or "").strip() or None if work else None
    chapter = {"title": str(title).strip(), "updated": opened}
    if modes:
        chapter["access_modes"] = modes
    return author, chapter


def title_tail(url, html):
    """Author and access from a <title> whose shape the platform keeps."""
    spec = TITLE_TAIL.get(host_of(url))
    if not spec:
        return None, None
    plat, access_words = spec
    m = TITLE.search(html or "")
    if not m:
        return None, None
    parts = [s.strip() for s in _html.unescape(m.group(1)).split("|")]
    if len(parts) < 4 or parts[-2] != plat:
        return None, None
    author = parts[-1] or None
    access = next((v for k, v in access_words.items() if k in parts), None)
    return author, access


def js(v):
    return json.dumps(v, ensure_ascii=False)


def asked(gaps, prior):
    """The store's incomplete rows, then each work an earlier run filled that they no longer name.

    A FILLED ROW STOPS BEING A GAP, which is the point, and that is also how this pass would forget
    it: the next compile reads the row complete, the gap list drops it, and a rewrite from the gap
    list alone takes the fill away again (a filter reading its own output). So what this file
    already holds is asked again every run, which also follows a page that changes.
    """
    # A WORK ON TWO PLATFORMS IS TWO FILLS. ドリーム☆ジャンボ☆ガール is read from コミックDAYS's
    # series feed and from マガポケ's episode pages, and keyed by title alone the second replaced the
    # first and took 46 chapters with it.
    named = [(g.get("work"), g.get("platform")) for g in gaps]
    out = list(gaps)
    for w in prior:
        if not (w.get("work_title") and w.get("url")):
            continue
        # EVERY ADDRESS THE FILL WAS MADE FROM, not only the one it is filed under, and even where
        # the work is a gap again. マガポケ's are one per episode: re-asking the first alone rewrote
        # アイドラトリィ's fill with #51 and dropped #52, and skipping a work the gaps named dropped
        # #51 the run after. A work the gaps name keeps its earlier addresses beside theirs.
        urls = [c["url"] for c in w.get("chapters") or [] if c.get("url")]
        if not _same_fill((w["work_title"], w.get("platform_name")), named):
            urls = [w["url"]] + urls
        elif w.get("route") == "magapoke-episode":
            urls = [w["url"]] + urls
        for u in dict.fromkeys(urls):
            out.append({"work": w["work_title"], "url": u, "platform": w.get("platform_name")})
    return out


def _same_fill(key, keys):
    """Whether `(work, platform)` is one of `keys`: the same title, and the same platform wherever
    both name one, so a gap that names none still finds the fill it is about."""
    return any(key[0] == k[0] and (not key[1] or not k[1] or key[1] == k[1]) for k in keys)


def kept(works, prior):
    """Each earlier fill this run could not refresh, in the shape `works` holds, so a page that
    did not load costs nothing it had already given."""
    have = [(w["work_title"], w.get("platform")) for w in works]
    return works + [{"work_title": w["work_title"], "author": w.get("author"), "url": w["url"],
                     "platform": w.get("platform_name"), "route": w.get("route"),
                     "work_access": w.get("access_modes"), "episodes": w.get("chapters") or []}
                    for w in prior if w.get("work_title")
                    and not _same_fill((w["work_title"], w.get("platform_name")), have)]


def main():
    ap = argparse.ArgumentParser()
    # THE STORE BY DEFAULT. The gap list was a file derived by hand on 2026-08-02 and never again,
    # so the pass had nothing new to fill from then on while `incomplete attested rows` rose.
    ap.add_argument("--gaps", default=None, help="a gap file to read instead of the store")
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    a = ap.parse_args()

    if a.gaps:
        gaps = (yaml.safe_load(open(a.gaps)) or {}).get("rows") or []
    else:
        import population
        gaps = population.incomplete_rows()
    outf = pathlib.Path(a.out) / "backfill.yaml"
    prior = ((yaml.safe_load(outf.read_text(encoding="utf-8")) or {}).get("works") or []
             if outf.exists() else [])
    gaps = asked(gaps, prior)
    # KEYED BY WORK AND PLATFORM, since access is a fact about a chapter ON A PLATFORM and the build
    # only carries it between rows that agree on the platform. This adapter spans hosts and would
    # otherwise declare none, which is why its first run filled in five authors and no access at all.
    by_work = defaultdict(set)
    order = []
    for g in gaps:
        w, u = g.get("work"), g.get("url")
        if not (w and u):
            continue
        key = (w, g.get("platform"))
        if key not in by_work:
            order.append(key)
        by_work[key].add(u)

    works, how, missed = [], Counter(), []
    for key in order:
        w, plat = key
        url = sorted(by_work[key])[0]
        html = get(url)
        if not html:
            missed.append((w, "page did not load"))
            continue
        author, eps = gigaviewer_feed(url, html)
        route = "gigaviewer-feed" if eps else None
        # マガポケ STATES ACCESS PER EPISODE, so each episode the store holds without it is read.
        if not eps and MAGAPOKE.match(url):
            for i, u in enumerate(sorted(by_work[key])):
                au, ch = magapoke_episode(html if i == 0 else get(u))
                if ch and ch["title"] not in {e["title"] for e in eps}:
                    author = author or au
                    eps.append(dict(ch, url=u))
            route = "magapoke-episode" if eps else None
        if not eps:
            au, access = title_tail(url, html)
            if au or access:
                author, route = au, "title-tail"
                # No chapter list from this route; the fields are stated for the work, so they are
                # recorded at work level and the build carries them onto its rows.
                works.append({"work_title": w, "author": author, "url": url,
                              "platform": plat, "route": route,
                              "work_access": access, "episodes": []})
                how[route] += 1
                continue
        if not eps and not author:
            au = author_links(url)
            if au:
                works.append({"work_title": w, "author": au, "url": url,
                              "platform": plat, "route": "author-link",
                              "work_access": None, "episodes": []})
                how["author-link"] += 1
                continue
            missed.append((w, "no route yielded the missing fields"))
            continue
        how[route] += 1
        works.append({"work_title": w, "author": author, "url": url,
                      "platform": plat, "route": route,
                      "work_access": None, "episodes": eps})

    resolved = len(works)
    works = kept(works, prior)
    if not works:
        print("no gap row resolved and nothing held from before; not writing")
        return 0

    L = ["# Fields filled in one row at a time, from the page a reader would open.",
         "#",
         "# These are rows the platform passes left incomplete — usually a single 読切 on a host",
         "# whose adapter walks serialised titles only. The routes are the proven ones: the",
         "# per-series Atom feed an episode page links even when the series is one entry long, and",
         "# a <title> whose shape the platform keeps, read only when the platform's own name is in",
         "# the position that shape requires.",
         "#",
         "# A route that does not fire leaves the field empty. Nothing here is inferred.",
         "#",
         "# No genre label is established here (DEFINITIONS §4).",
         "source: webpages", "platform: backfill", "platform_name: \"\"",
         f"retrieved: {a.retrieved}", "record_type: web_work_chapters",
         "identification_mode: discovery-candidate", "works:"]
    for w in works:
        L.append(f"  - work_title: {js(w['work_title'])}")
        if w["author"]:
            L.append(f"    author: {js(w['author'])}")
        L.append(f"    url: {js(w['url'])}")
        if w.get("platform"):
            L.append(f"    platform_name: {js(w['platform'])}")
        L.append(f"    route: {js(w['route'])}")
        if w["work_access"]:
            L.append(f"    access_modes: {js(w['work_access'])}")
        if w["episodes"]:
            L.append(f"    chapter_count: {len(w['episodes'])}")
            L.append("    chapters:")
            for e in w["episodes"]:
                L.append(f"      - title: {js(e['title'])}")
                L.append(f"        updated: {e['updated']}")
                if e.get("access_modes"):
                    L.append(f"        access_modes: {js(e['access_modes'])}")
                if e.get("url"):
                    L.append(f"        url: {js(e['url'])}")
    L.append("")
    pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(a.out) / "backfill.yaml").write_text("\n".join(L))

    print(f"gap works       : {len(order)}")
    print(f"resolved        : {resolved}  {dict(how)}; {len(works) - resolved} kept from before")
    if missed:
        print(f"still missing   : {len(missed)}")
        for t, r in missed:
            print(f"    - {str(t)[:34]:36} {r}")


if __name__ == "__main__":
    sys.exit(main())
