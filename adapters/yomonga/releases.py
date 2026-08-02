#!/usr/bin/env python3
"""マンガよもんが — chapters, author and access from the work page (REQUIREMENTS §5).

Recorded until now as "in maintenance, unverifiable". The maintenance was real and it is over, but
that reason had also been standing in for a second one: the generic adapter reached this host and
took only dates from it, so the rows arrived with neither an author nor an access state.

The work page is server-rendered and states all three plainly:

    <div class="episode-list" data-episode_no="15">
      <div class="update-date">2026/07/07</div>
      <div class="episode-name">Chapter.15 第14話</div>
      <div class="publish-end-date">2026/08/18に公開終了</div>

and, next to the synopsis, 漫画：栗崎きんぐ.

Access comes from publish-end-date, which is the platform saying how long the chapter stays up. An
episode still inside its window is free; one whose window has closed is gone rather than
purchasable, and is recorded as such by simply not being listed any more — so what this reads is
always the live set.

Do not take 無料 from this site's branding. It calls itself ぶんか社の無料マンガサイト and the word
appears only in the meta description; there is no per-chapter 無料 badge anywhere in the markup. The
window is the platform's actual statement about access, and the branding is not evidence.

Usage:  releases.py --works data/source/webpages/generic-www-yomonga-com.yaml \
                    --out data/source/webpages --retrieved 2026-08-02
"""
import argparse, datetime as dt, html as _html, json, pathlib, re, sys, time
import urllib.error, urllib.request

import yaml

UA = "Mozilla/5.0 (compatible; yurarium/0.1; +https://yurarium.github.io/)"
PAUSE = 1.0
PLATFORM = "yomonga"
MIN_WORKS = 3

EPISODE = re.compile(
    r'class="episode-list"[^>]*>(.*?)(?=<div class="episode-list"|<footer|\Z)', re.S)
UPDATED = re.compile(r'class="update-date">\s*(\d{4})/(\d{1,2})/(\d{1,2})')
NAME = re.compile(r'class="episode-name">\s*([^<]+?)\s*<')
ENDS = re.compile(r'class="publish-end-date">\s*(\d{4})/(\d{1,2})/(\d{1,2})')
# 漫画：<name>, allowing markup between the label and the name. The name must be plain text with no
# quote or dot in it: the same pattern matches 漫画家募集_520x80-1.png in a banner's filename, and a
# file name is not an author.
AUTHOR = re.compile(r'(?:漫画|作画|著者|原作)\s*[：:]\s*(?:</?[^>]+>\s*)*([^<>"\'./\s][^<>"\'.]{0,17})')


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.read(3_000_000).decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return ""
    finally:
        time.sleep(PAUSE)


def author(html):
    for m in AUTHOR.finditer(html):
        name = _html.unescape(m.group(1)).strip()
        if name and not re.search(r"募集|バナー|banner", name):
            return name
    return None


def episodes(html, today):
    out = []
    for block in EPISODE.findall(html):
        d, n = UPDATED.search(block), NAME.search(block)
        if not (d and n):
            continue
        e = ENDS.search(block)
        row = {"title": _html.unescape(n.group(1)).strip(),
               "updated": f"{int(d.group(1)):04d}-{int(d.group(2)):02d}-{int(d.group(3)):02d}"}
        if e:
            end = dt.date(int(e.group(1)), int(e.group(2)), int(e.group(3)))
            row["access_modes"] = ["free"] if end >= today else ["purchase"]
            row["free_until"] = end.isoformat()
        else:
            row["access_modes"] = ["free"]      # listed with a 読む button and no stated end
        out.append(row)
    return out


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    a = ap.parse_args()

    today = dt.date.fromisoformat(a.retrieved)
    src = yaml.safe_load(open(a.works)) or {}
    works, failed = [], []
    for w in src.get("works") or []:
        html = get(w.get("url"))
        if not html or "メンテナンス" in html[:4000]:
            failed.append((w.get("work_title"), "page unavailable" if not html else "maintenance"))
            continue
        eps = episodes(html, today)
        if not eps:
            failed.append((w.get("work_title"), "no episode-list blocks on the page"))
            continue
        works.append({"work_title": w.get("work_title"), "author": author(html),
                      "url": w.get("url"), "episodes": eps})

    if len(works) < MIN_WORKS:
        sys.exit(f"only {len(works)} works resolved (minimum {MIN_WORKS}); not writing")

    L = ["# マンガよもんが — chapters, author and access from the work page's own markup.",
         "#",
         "# The page is server-rendered: each episode is an episode-list block carrying update-date,",
         "# episode-name and, where the chapter is time-limited, publish-end-date. The author sits",
         "# beside the synopsis as 漫画：<name>.",
         "#",
         "# Access is the window, not the branding. The site calls itself ぶんか社の無料マンガサイト and",
         "# the word 無料 appears nowhere except its meta description — there is no per-chapter badge,",
         "# so the stated end date is the only thing the platform actually says about access.",
         "#",
         "# No genre label is established here (DEFINITIONS §4).",
         "source: webpages", f"platform: {PLATFORM}", "platform_name: \"マンガよもんが\"",
         "publisher: \"ぶんか社\"", f"retrieved: {a.retrieved}",
         "record_type: web_work_chapters", "identification_mode: discovery-candidate",
         "date_basis: platform-stated", "date_confidence: reported", "works:"]
    for w in works:
        L.append(f"  - work_title: {js(w['work_title'])}")
        if w["author"]:
            L.append(f"    author: {js(w['author'])}")
        L.append(f"    url: {js(w['url'])}")
        L.append(f"    chapter_count: {len(w['episodes'])}")
        L.append("    chapters:")
        for e in w["episodes"]:
            L.append(f"      - title: {js(e['title'])}")
            L.append(f"        updated: {e['updated']}")
            L.append(f"        access_modes: {js(e['access_modes'])}")
            if e.get("free_until"):
                L.append(f"        free_until: {e['free_until']}")
    L.append("")
    pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(a.out) / f"{PLATFORM}.yaml").write_text("\n".join(L))

    n = sum(len(w["episodes"]) for w in works)
    print(f"works resolved : {len(works)}")
    print(f"chapters       : {n}")
    print(f"with author    : {sum(1 for w in works if w['author'])} of {len(works)}")
    if failed:
        print(f"unresolved     : {len(failed)}")
        for t, r in failed:
            print(f"    - {str(t)[:30]:32} {r}")


if __name__ == "__main__":
    main()
