#!/usr/bin/env python3
"""Reach the series nothing else reached, one at a time (REQUIREMENTS §5).

The platform adapters work by platform, which is the right shape for the bulk and leaves a residue:
a work whose URL sits in the candidate list on a host with a working adapter, and which the adapter
never fetched anyway. 散らないで菊 is on コミックゼノン, its episode page exposes the series feed,
and the GigaViewer adapter ran over that platform without ever asking for it.

Rather than keep debugging why each platform pass skipped each work, this takes the list of works
we hold nothing for and tries every route we have against each, in order of cost:

  1. GigaViewer  — the episode page links to /atom/series/<id>, which is a dated feed.
  2. comici      — the series page carries series-eplist-item markup with dates.
  3. markup      — a plain fetch, parsed by the proven strategies.
  4. render      — headless chromium, for pages that build their list in JavaScript.

A work is reported unreached only after all four fail, which is a much stronger statement than any
one adapter declining to pick it up.

A HOST WITH AN ADAPTER OF ITS OWN IS LEFT ALONE, from `adapters/dedicated.py`. Those four routes
are heuristics and the dedicated parsers read the platform's own stated fields, so running these
over comic-fuz.com, comic-walker.com or manga.nicovideo.jp put a second, worse answer beside a
good one: お姉さんは女子小学生に興味があります。 was published here with two chapters called
`第１話から読む` and `3話 無料`, the read-from-the-start button and a fragment of ニコニコ's own
`[ 3話 無料 ]` meta line, while 竹コミ's adapter held 64 chapters for it. Those works are reported
as covered elsewhere rather than as unreached, because they are.

Usage:  releases.py --works data/coverage/remaining.yaml --out data/source/webpages \
                    --cache $YURI_CACHE/remaining-cache --retrieved 2026-08-01
"""
import argparse, html as _html, json, pathlib, re, subprocess, sys, time
import urllib.error, urllib.request
from collections import Counter

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import comici  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "recon"))
from extract import CHAPTERISH, norm_date, try_jsonld, try_markup, try_next, try_pairs  # noqa: E402
from names import credits as _credits  # noqa: E402
import dedicated  # noqa: E402

UA = "Mozilla/5.0 (compatible; yurarium/0.1; +https://yurarium.github.io/)"
CHROME = next((c for c in ("/snap/bin/chromium", "/usr/bin/chromium",
                           "/usr/bin/chromium-browser", "/usr/bin/google-chrome")
               if pathlib.Path(c).exists()), None)
PAUSE = 1.0
MIN_EPISODES = 1

#: A CREDIT THE PAGE LABELS AS ONE. `著者：` and `作者：` name the field they hold, which is better
#: evidence than the middle position of a `<title>` and is what a platform writes when its title
#: has no room. Stops at the first tag or line break, so an anchor around the name is fine and a
#: run-on paragraph cannot be swallowed.
#:
#: THE LABEL IS PART OF THE MATCH AND NOT PART OF THE NAME, which is why the group starts after it.
#: `著者：深水たろー` inside an anchor yields 深水たろー, and everything the capture returns still
#: goes through `credits.people_only`, so a label sitting beside something that cannot be a person
#: is refused the same way a title's middle field is.
LABELLED_CREDIT = re.compile(r"(?:著者|作者|漫画|著)\s*[：:]\s*([^<>\n\r]{1,40})")
TODAY = __import__("datetime").date.today().isoformat()

COMICI_BLOCK = re.compile(r'data-e2e="eli"')
COMICI_ROW = re.compile(
    r'data-e2e="eliTitle">([^<]+)<.*?series-eplist-item-meta-date">(\d{4})/(\d{1,2})/(\d{1,2})<',
    re.S)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.read(3_000_000).decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return ""
    finally:
        time.sleep(PAUSE)


#: The same window `render/releases.py` uses, and for the same reason: a run that happens every few
#: days re-rendered everything at two days, and this is the more expensive of the two adapters.
RENDER_AGE_DAYS = 7


def render(url, cache):
    key = re.sub(r"[^A-Za-z0-9]", "_", url)[-110:]
    f = cache / f"{key}.html"
    if f.exists() and (time.time() - f.stat().st_mtime) / 86400 < RENDER_AGE_DAYS:
        return f.read_text()
    if not CHROME:
        return ""
    try:
        out = subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
             "--virtual-time-budget=9000", f"--user-agent={UA}", "--dump-dom", url],
            capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return ""
    time.sleep(PAUSE)
    h = out.stdout or ""
    if len(h) > 2000:
        f.write_text(h)
    return h


DIAG = {}


def from_giga(html, page_url):
    """The host comes from the page we fetched, not from the link. Some installs write the feed
    link relative (/atom/series/<id>), and requiring the absolute form meant the route silently
    declined on コミックゼノン and 一迅プラス — pages whose feed link I had checked by hand."""
    m = re.search(r"/atom/series/(\d+)", html)
    if not m:
        return []
    base = re.match(r"https?://([^/]+)", page_url)
    if not base:
        return []
    base = base.group(1)
    xml = get(f"https://{base}/atom/series/{m.group(1)}")
    if xml and "<entry>" not in xml:
        # The feed exists and lists nothing. 散らないで菊 is a コミックゼノン漫画大賞 entry whose
        # series feed carries a title and no episodes. Not our failure to reach it — the platform
        # publishes no episode list for it.
        ti = re.search(r"<title>([^<]*)</title>", xml)
        DIAG[page_url] = f"platform's series feed is empty ({ti.group(1) if ti else 'no title'})"
    # The free-only variant of the same feed gives per-chapter access, and every entry carries its
    # author — both were being discarded, which is why works rescued by this adapter arrived with a
    # date and nothing else.
    try:
        free_ids = set(re.findall(r'<link href="([^"]+)"/>',
                                  get(f"https://{base}/atom/series/{m.group(1)}?free_only=1")))
    except Exception:                                              # noqa: BLE001
        free_ids = set()
    out = []
    for b in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        t = re.search(r"<title>([^<]*)</title>", b)
        u = re.search(r"<updated>([^<]*)</updated>", b)
        l = re.search(r'<link href="([^"]+)"', b)
        au = re.search(r"<author>\s*<name>([^<]*)</name>", b, re.S)
        if t and u:
            row = {"title": _html.unescape(t.group(1).strip()), "updated": u.group(1)[:10]}
            if au:
                _a = _html.unescape(au.group(1).strip())
                if _credits.is_a_person(_a):
                    row["author"] = _a
            if free_ids and l:
                row["access_modes"] = ["free"] if l.group(1) in free_ids else ["purchase"]
            out.append(row)
    return out


def from_comici(html, page_url=""):
    """Delegated to adapters/comici.py — one engine, one parser. This adapter used to hold
    the only correct reading of comici's three access states and its range navigation,
    which is precisely why the fix never reached the eight platforms read elsewhere."""
    return comici.chapters(html, page_url, get)



def from_generic(html):
    got = try_jsonld(html) or try_next(html)
    if len(got) < 2:
        got, _ = try_markup(html)
    if len(got) < 2:
        got = try_pairs(html)
    out, seen = [], set()
    for g in got:
        t = re.sub(r"\s+", " ", g.get("title") or "").strip()
        d = g.get("date")
        if not d or not CHAPTERISH.search(t):
            continue
        if g.get("exact"):
            # try_markup read this off the element the page names as the chapter's title, so it is
            # the label rather than a run of text to be cut down. Trimming it would take a real
            # subtitle with the furniture.
            lab = t
        else:
            m = CHAPTERISH.search(t)
            lab = re.split(r"\s\d{4}[-/.年]|\s+\d{2,}(?:\s|$)",
                           t[m.start(): m.end() + 40])[0].strip()
            # Rendered pages put the date's own label next to the chapter, and the generic
            # extractor swept it into the title: "第1話 ぐっすん！…別れは出会いのシグナル 更新日:".
            # Strip that and the other furniture words that sit in the same position.
            lab = re.sub(r"\s*(更新日|公開日|配信日|更新)\s*[:：]?\s*$", "", lab).strip()
        # A date in the future is 公開予定 — announced, not published. コミックFUZ carries these months
        # ahead, and one arrived here as しゅがー・みーつ・がーる! "updating" on 2026-08-25.
        if d > TODAY:
            continue
        if lab and (lab, d) not in seen:
            seen.add((lab, d))
            out.append({"title": lab, "updated": d})
    return out or from_oneshot(html)


# A work the platform marks as a one-shot. 読み切り is the word and 読切 is the same word written
# short. It reaches us as the label on the button that opens the thing, きら星ポータル's page
# offering 読み切りを読む and nothing else, so the match is anywhere on the page.
ONESHOT = re.compile(r"読\s*み?\s*切り?")


def from_oneshot(html):
    """The single release of a work whose page states one date and marks itself a one-shot.

    THE EXTRACTORS WANT A CHAPTER-SHAPED LABEL before they will keep a date, and a 読み切り offers
    none: きら星ポータル's page for ツイてるギャルとミエてる陰キャ offers a 読み切りを読む button
    beside 2026年6月17日
    and no 第N話 anywhere, so a date the platform states plainly was thrown away and the work read
    as having no dated chapter list.

    A ONE-SHOT IS ONE CHAPTER, so the work-level date is that chapter's, and the platform's 更新 is
    its release. The project owner ruled this on 2026-08-10 for exactly this shape.

    NARROW ON PURPOSE. It runs only where the ordinary extractors found nothing, the page says it is
    a one-shot, and the page states exactly one date. Two dates mean the page is telling us
    something this cannot read, and a page with a chapter list never reaches here.
    """
    if not ONESHOT.search(html):
        return []
    found = {norm_date(m) for m in re.findall(r"\d{4}[-/.年]\s*\d{1,2}[-/.月]\s*\d{1,2}", html)}
    dates = sorted(d for d in found if d and d <= TODAY)
    if len(dates) != 1:
        return []
    return [{"title": "読み切り", "updated": dates[0], "oneshot": True}]


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--name", default="remaining",
                    help="output basename; the claim-resolution queue writes a separate file so it "
                         "does not overwrite the works this adapter was originally built for")
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    rows, how, failed = [], Counter(), []
    for w in (yaml.safe_load(open(a.works)) or {}).get("works") or []:
        url = w.get("url")
        if not url:
            failed.append((w.get("title"), "no URL"))
            continue
        host = dedicated.covers(url)
        if host:
            failed.append((w.get("title"),
                           f"{host} is covered by a dedicated adapter, so it is not re-read here"))
            continue
        html = get(url)
        eps, route, page_author = [], None, None
        if html:
            # comici states the author in the page title as "作品 - 作者 | プラットフォーム", the same
            # place the webpages adapter reads it. This route was ignoring it, so works rescued here
            # arrived without one while the same platform's other works had theirs.
            # THE MIDDLE FIELD IS NOT ALWAYS THE AUTHOR. Where a platform puts its newest chapter
            # there instead, this read it as a credit: 平良深姉妹はどっちもヤんでる was published
            # crediting `金子ある / #1(1)`, and #1(1) sits in that platform's own feed as a chapter.
            # A capture that cannot be somebody's name is dropped and the work keeps the credit it
            # already had.
            # ASKED OF EACH CREDIT IN THE FIELD, NOT OF THE FIELD. ゼノンプラス writes
            # `作品 - 作者 / 読切 作品 | プラットフォーム`, so the middle holds the artist and the
            # work's own episode label. `is_a_person` refuses `読切 画家の肖像` and accepts the pair,
            # because every refusal it makes anchors at the start of the string and the string
            # opens with a real name. Two rows shipped with the work's title inside the byline.
            _au = re.search(r"<title>[^<|]*?\s+-\s+([^<|]+?)\s*\|", html)
            if _au:
                _cand = _html.unescape(_au.group(1).strip())
                page_author = _credits.people_only(_cand)
            if not page_author:
                # A CREDIT THE PAGE LABELS, where the title states none. The rule above needs a
                # `|` to anchor on and きら星ポータル writes `作品 / 誌名 - サイト`, so
                # ツイてるギャルとミエてる陰キャ arrived with an empty author while its page says
                # `著者：深水たろー` twice over, once in an anchor to the site's own author page and
                # once in the copyright line. A label is better evidence than a position in a title
                # anyway: it says which field this is rather than leaving it to be inferred.
                _lab = LABELLED_CREDIT.search(html)
                if _lab:
                    page_author = _credits.people_only(_html.unescape(_lab.group(1).strip()))
            for name, fn in (("gigaviewer", lambda h: from_giga(h, url)),
                             ("comici", lambda h: from_comici(h, url)),
                             ("markup", from_generic)):
                eps = fn(html)
                if len(eps) >= MIN_EPISODES:
                    route = name
                    break
        if not eps:
            rh = render(url, cache)
            if rh:
                eps = from_generic(rh)
                route = "rendered" if eps else None
        if not eps:
            failed.append((w.get("title"),
                           DIAG.get(url) or ("page did not load" if not html else
                                             "no route yielded a dated chapter list")))
            continue
        how[route] += 1
        if page_author:
            for e in eps:
                e.setdefault("author", page_author)
        rows.append({"work_title": w.get("title"), "url": url, "platform": w.get("platform"),
                     "route": route, "author": page_author, "episodes": eps})

    if rows:
        L = ["# Series reached individually after every platform pass had left them out.",
             "#",
             "# Four routes tried per work, cheapest first: the GigaViewer per-series feed linked",
             "# from an episode page, comici's series-eplist markup, a plain fetch parsed by the",
             "# usual strategies, and finally a rendered DOM. The route used is recorded per work.",
             "#",
             "# No genre label is established here (DEFINITIONS §4).",
             "source: webpages", f"platform: {a.name}", "platform_name: \"\"",
             f"retrieved: {a.retrieved}", "record_type: web_work_chapters",
             "identification_mode: discovery-candidate", "works:"]
        for r in rows:
            L.append(f"  - work_title: {js(r['work_title'])}")
            if r.get("author"):
                L.append(f"    author: {js(r['author'])}")
            L.append(f"    url: {js(r['url'])}")
            if r.get("platform"):
                L.append(f"    platform_name: {js(r['platform'])}")
            L.append(f"    route: {js(r['route'])}")
            L.append(f"    chapter_count: {len(r['episodes'])}")
            L.append("    chapters:")
            for e in r["episodes"]:
                L.append(f"      - title: {js(e['title'])}")
                L.append(f"        updated: {e['updated']}")
                if e.get("author"):
                    L.append(f"        author: {js(e['author'])}")
                if e.get("access_modes"):
                    L.append(f"        access_modes: {js(e['access_modes'])}")
                if e.get("access_note"):
                    L.append(f"        access_note: {js(e['access_note'])}")
                if r["route"] in ("markup", "rendered"):
                    L.append(f"        date_basis: {'rendered' if r['route']=='rendered' else 'heuristic'}")
        L.append("")
        (out / f"{a.name}.yaml").write_text("\n".join(L))

    print(f"works attempted : {len(rows) + len(failed)}")
    print(f"reached         : {len(rows)}  {dict(how)}")
    if failed:
        print(f"unreached       : {len(failed)}")
        for t, r in failed:
            print(f"    - {str(t)[:34]:36} {r}")


if __name__ == "__main__":
    main()
