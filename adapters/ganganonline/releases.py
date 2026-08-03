#!/usr/bin/env python3
"""ガンガンONLINE — chapters from the page's own embedded state (REQUIREMENTS §5).

I had this platform recorded as one that "publishes 次回更新 and no per-chapter date, author or
access — a reader on the site cannot see them either". That was wrong, and wrong in the way worth
naming: I judged the platform by what the rendered DOM gave me rather than by what the page
carries. The rendered route read the visible chapter strip, where the newest entry really does say
次回更新：8月9日, and I generalised from the hardest chapter to the whole site.

The page is Next.js and ships its state inline in <script id="__NEXT_DATA__">. In it:

    author            "原作／宮澤伊織(早川書房刊)　作画／水野英多　キャラクター原案／shirakaba"
    chapters[].mainText / .subText        "第89話-3" / "八尺様リバイバルIV"
    chapters[].publishingPeriod           "2026.07.19〜2026.08.01"
    chapters[].status                     2 = period ended, 3 = not yet a chapter

So the platform states a publication date, an author and an access state for every chapter. All of
it was sitting in the HTML of a plain GET the whole time.

This also fixes two things the rendered route got wrong rather than merely missed: it recorded
裏世界ピクニック's author as 女子ふたり怪異探検サバイバル!! — the tagline, which sits where an author
would visually — and it swept the neighbouring 作品インフォメーション block into chapter titles.

Access, from the same fields:

  status 3          not a chapter yet (次回更新). Dropped, not recorded as a release.
  status 2          the free window closed. purchase.
  period covers today   free — 期間限定 but unconditionally readable now.
  period has passed     purchase.
  no period, no status  free. The permanently-open opening chapters.

Usage:  releases.py --targets data/coverage/render-targets.yaml --out data/source/webpages \
                    --retrieved 2026-08-02
"""
import argparse, datetime as dt, html as html_mod, json, pathlib, re, sys, time
import urllib.error, urllib.request

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "render"))
import schedule_text  # noqa: E402

UA = "Mozilla/5.0 (compatible; yurarium/0.1; +https://yurarium.github.io/)"
PAUSE = 1.0
PLATFORM = "ganganonline"
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
PERIOD = re.compile(r"(\d{4})[./](\d{1,2})[./](\d{1,2})\s*[〜~-]\s*(?:(\d{4})[./](\d{1,2})[./](\d{1,2}))?")
MIN_WORKS = 3


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.read(4_000_000).decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return ""
    finally:
        time.sleep(PAUSE)


def _plain(html):
    """The page as a reader sees it. The announcement is prose, not part of the embedded state."""
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", html or "", flags=re.S | re.I)
    return re.sub(r"\s+", " ", html_mod.unescape(re.sub(r"<[^>]+>", " ", t)))


def state(html):
    m = NEXT_DATA.search(html or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(1))
    except ValueError:
        return None
    return (((d.get("props") or {}).get("pageProps") or {}).get("data") or {}).get("default")


def period(text):
    """(start, end) as dates. end is None for an open-ended window."""
    m = PERIOD.search(text or "")
    if not m:
        return None, None
    g = m.groups()
    start = dt.date(int(g[0]), int(g[1]), int(g[2]))
    end = dt.date(int(g[3]), int(g[4]), int(g[5])) if g[3] else None
    return start, end


def chapters(D, today):
    out = []
    for c in D.get("chapters") or []:
        if c.get("status") == 3:
            continue                        # 次回更新 — announced, not published
        title = " ".join(x for x in (c.get("mainText"), c.get("subText")) if x).strip()
        if not title:
            continue
        start, end = period(c.get("publishingPeriod"))
        if not start:
            # A back-catalogue chapter with no window: open, but the platform states no date for
            # it, and a release row without a date is not a release. Skipped deliberately.
            continue
        if c.get("status") == 2 or (end and end < today):
            access = ["purchase"]
        else:
            access = ["free"]
        out.append({"title": title, "updated": start.isoformat(), "access_modes": access})
    return out


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    a = ap.parse_args()

    today = dt.date.fromisoformat(a.retrieved)
    spec = next((s for s in (yaml.safe_load(open(a.targets)) or {}).get("platforms") or []
                 if s.get("id") == PLATFORM), None)
    if not spec:
        sys.exit(f"no {PLATFORM} section in {a.targets}")

    works, no_state, empty = [], [], []
    for w in spec.get("works") or []:
        url = w.get("url")
        html = get(url)
        D = state(html)
        if not D:
            no_state.append(w.get("title") or url)
            continue
        eps = chapters(D, today)
        if not eps:
            empty.append(D.get("titleName") or w.get("title"))
            continue
        works.append({"work_title": D.get("titleName") or w.get("title"),
                      "author": (D.get("author") or "").strip() or None,
                      "url": url, "episodes": eps,
                      # 次回更新：8月6日 is printed beside the chapter list. The platform is
                      # announcing a date; the alternative is us averaging its past intervals.
                      "stated_schedule": schedule_text.read(_plain(html), a.retrieved)})

    if len(works) < MIN_WORKS:
        sys.exit(f"only {len(works)} works resolved (minimum {MIN_WORKS}); not writing")

    L = ["# ガンガンONLINE — chapters, dates, author and access from the page's own embedded state.",
         "#",
         "# The page ships its state inline in <script id=\"__NEXT_DATA__\">, so a plain GET carries",
         "# everything: a per-chapter publishingPeriod (\"2026.07.19〜2026.08.01\"), a status marking",
         "# ended and not-yet-published chapters, and the title-level author. No rendering needed.",
         "#",
         "# The window's start date is the publication date and is recorded as platform-stated. A",
         "# chapter whose window has closed, or which carries status 2, is purchase; one still open",
         "# is free. status 3 is 次回更新 — announced, not published — and is not a release.",
         "#",
         "# No genre label is established here (DEFINITIONS §4).",
         "source: webpages", f"platform: {PLATFORM}",
         f"platform_name: {js(spec.get('name') or 'ガンガンONLINE')}",
         f"publisher: {js(spec.get('publisher') or 'スクウェア・エニックス')}",
         f"retrieved: {a.retrieved}", "record_type: web_work_chapters",
         "identification_mode: discovery-candidate",
         "date_basis: platform-stated", "date_confidence: reported", "works:"]
    for w in works:
        L.append(f"  - work_title: {js(w['work_title'])}")
        if w["author"]:
            L.append(f"    author: {js(w['author'])}")
        L.append(f"    url: {js(w['url'])}")
        if w.get("stated_schedule"):
            L.append("    stated_schedule:")
            for k2, v2 in sorted(w["stated_schedule"].items()):
                L.append(f"      {k2}: {js(v2)}")
        L.append(f"    chapter_count: {len(w['episodes'])}")
        L.append("    chapters:")
        for e in w["episodes"]:
            L.append(f"      - title: {js(e['title'])}")
            L.append(f"        updated: {e['updated']}")
            L.append(f"        access_modes: {js(e['access_modes'])}")
    L.append("")
    pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(a.out) / f"{PLATFORM}.yaml").write_text("\n".join(L))

    n = sum(len(w["episodes"]) for w in works)
    free = sum(1 for w in works for e in w["episodes"] if e["access_modes"] == ["free"])
    print(f"works resolved  : {len(works)}")
    print(f"chapters        : {n}  ({free} free, {n - free} purchase)")
    print(f"with author     : {sum(1 for w in works if w['author'])}")
    if no_state:
        print(f"no page state   : {len(no_state)}  {no_state[:4]}")
    if empty:
        print(f"no dated chapter: {len(empty)}  {empty[:4]}")


if __name__ == "__main__":
    main()
