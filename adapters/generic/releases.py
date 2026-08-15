#!/usr/bin/env python3
"""Generic chapter extraction for platforms with no shared engine (REQUIREMENTS §5, §6).

The long tail's 21 markup-only hosts have no engine in common, which was the argument for leaving
them alone. But they do not need one: what they have in common is the *shape* of a chapter list —
repeated blocks, each carrying a date and a chapter-like label. That is enough to parse without
knowing anything about a particular site's markup.

So this reuses the strategies proven per host in `data/coverage/extract.yaml` rather than carrying
a selector registry. A host is only processed if the second reconnaissance pass demonstrated that
a strategy returns dated chapters from it, so nothing here is speculative parsing.

The cost of generality is confidence, and it is paid explicitly:

- Every release is written with `date_basis: heuristic` and `date_confidence: low`. These are not
  a publisher's stated field, they are a pattern matched in a page.
- A block is only a chapter if it carries a chapter-like label (第N話, #N, episode N, 最終話…).
  A bare date is skipped, because a bare date on a manga page is usually the 単行本 release —
  the trap the first reconnaissance pass fell into on ガンガンONLINE.
- Blocks reading as volume announcements (発売, 刊行, 単行本, 巻) are dropped unless they also
  carry a chapter label.
- Anything that yields fewer than `MIN_EPISODES` is discarded rather than written thin.

Usage:  releases.py --works data/coverage/webcomics-works.yaml \
                    --extract data/coverage/extract.yaml --out data/source/webpages \
                    --cache $YURI_CACHE/generic-cache --retrieved 2026-08-01
"""
import html as _html
import argparse, json, pathlib, re, sys, time, unicodedata, urllib.error, urllib.request
from collections import Counter

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import dedicated  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "recon"))
from extract import (CHAPTERISH, norm_date, try_jsonld, try_labels,  # noqa: E402
                     try_markup, try_next, try_nuxt, try_pairs)

# The compatible-token form. Several hosts (firecross.jp, www.yomonga.com) reject a bare product
# token outright but serve this, and it is the long-standing convention — "Mozilla/5.0 (compatible;
# Googlebot/2.1; +http://...)" has the same shape. It still names us and still links to the project,
# so it is not the thing refused for pixivコミック: that would have meant claiming to be a browser
# in order to pass an access control. This claims to be us, in the format the web expects.
UA = ("Mozilla/5.0 (compatible; yurarium/0.1; bibliographic database; "
      "+https://yurarium.github.io/)")
PAUSE = 1.5
MIN_EPISODES = 2
#: `pairs` IS THE LAST OF THEM AND IT WAS NOT REACHABLE FROM HERE. `try_markup` reads a page that
#: names the element holding a chapter's title; `try_pairs` reads one that puts a label and a date
#: near each other and names neither. 裏サンデー and 少年ジャンプルーキー are both the second kind,
#: so this pass wrote nothing for them while `remaining/from_generic`, which tries every extractor
#: in turn, read 7 and 2 chapters. A strategy table missing one strategy is a platform this cannot
#: read for a reason that is about the table.
STRATEGIES = {"jsonld": try_jsonld, "next": try_next, "nuxt": try_nuxt, "pairs": try_pairs,
              "labels": try_labels}

#: THE STRATEGY THAT COMES BACK WITHOUT DATES, because its platforms print none. See
#: `extract.try_labels`: the day the page was read is what there is, and `build.py` locks a
#: heuristic date at first sighting so it cannot walk forward with the calendar.
DATELESS = "labels"


def clean(s):
    s = re.sub(r"[​-‏‪-‮﻿]", "", s or "")
    return unicodedata.normalize("NFKC", s).strip()


def fetch(url, cache, max_age_days=1):
    key = re.sub(r"[^A-Za-z0-9]", "_", url)[-120:]
    f = cache / f"{key}.html"
    if f.exists() and (time.time() - f.stat().st_mtime) / 86400 < max_age_days:
        return f.read_text()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read(1_500_000).decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t


#: A PAGE THAT ONLY EXISTS ONCE A BROWSER HAS RUN IT. 裏サンデー and アルファポリス serve a shell
#: and build the chapter list in the client, so a plain fetch reads 200 and parses nothing: seven
#: works between them looked like platforms with no chapter list rather than platforms this cannot
#: read without a browser. `adapters/remaining` already drives headless Chrome and this borrows it
#: rather than starting a second one.
RENDERED = "rendered"


def render_page(url, cache):
    """The DOM a browser produces for `url`, through the one renderer this project has."""
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "remaining"))
    import releases as _remaining
    return _remaining.render(url, pathlib.Path(cache))


def episodes(html, strategy, today=None, page_url=""):
    if strategy == DATELESS:
        got = try_labels(html, page_url)
    elif strategy in STRATEGIES:
        got = STRATEGIES[strategy](html)
    else:
        got, _ = try_markup(html)
    if strategy == DATELESS:
        # THE DAY THIS READ THE PAGE, for a platform that states no date anywhere. Not a guess
        # about publication: `date_basis: heuristic` says what it is and the first-seen ledger
        # holds it still from the next run onward.
        got = [dict(g, date=today) for g in got]
    out, seen = [], set()
    for g in got:
        title = re.sub(r"\s+", " ", g.get("title") or "").strip()
        date = g.get("date")
        if not date or not CHAPTERISH.search(title):
            continue
        if g.get("exact"):
            # The page named the element holding the chapter's own title, so this IS the label and
            # is taken whole. What follows reconstructs a label from a run of scraped text, and
            # applied to a real title it cuts a subtitle off. マンガPark, ファイアCROSS and
            # マンガよもんが all arrive here.
            label = title
        else:
            # The label is buried in a run of scraped text that also carries the date and whatever
            # counters the site prints next to it — マンガPark yields "第1話① 6178 67 2023/1/24".
            # Keep the chapter part and cut at the first thing that is plainly not part of a title:
            # a date, or a bare run of three or more digits, which is a view or comment count.
            m = CHAPTERISH.search(title)
            label = title[max(0, m.start() - 4): m.end() + 40]
            label = re.split(r"\s\d{4}[-/.年]\d{1,2}|\s\d{3,}\b", label)[0]
            # Markup in the window means we ran off the end of the episode list. The +40 is
            # speculative, existing to catch a subtitle, and every episode but the LAST is bounded
            # by the next one, so the last is the only one that can over-run. GANMA! prints its
            # author block straight after the list, and 飛野さんのバカ's fifth episode came out as
            # '配信 第5話 作家 <img alt="author avatar" loading="la', stopping only at the character
            # cap while its four siblings were a clean '配信 第N話'.
            # A tag is never part of a chapter title, so its presence is proof the tail is not a
            # subtitle. Drop the speculative part rather than trying to clean it: what follows an
            # over-run is another section of the page, not a damaged version of what we wanted.
            if "<" in label:
                label = title[max(0, m.start() - 4): m.end()]
            label = label.strip(" 　·・|/-")
        k = (label, date)
        if k in seen:
            continue
        seen.add(k)
        out.append({"title": label, "updated": date})
    return out


#: WHERE A PLATFORM PUTS ITS CREDIT, declared per platform because guessing it was wrong. See
#: `page_author`: the two forms are `title` for `作品 - 作者 | サイト` and `labelled` for a
#: `著者：` field, and a platform that declares neither has no author read from it.
AUTHOR_FROM = "author_from"


def page_author(html, where=None):
    """The credit a work page states, read the way `adapters/remaining` reads one.

    DECLARED, NOT GUESSED, AND THE FIRST VERSION GUESSED. Reading both forms against every platform
    put `WEB読み`, a button, on every ファイアCROSS row and one author's name on every マンガPark
    row: both platforms had been read correctly without an author for months, and this took a
    working byline away from them. `credit pages listing a work that does not name them` went from
    8 to 22 and that is what the number is for.

    THE AUDIT IS WHAT ASKED FOR THIS. Rows from this pass carried no author at all, so a platform
    onboarded here had every one of its rows missing the field and `adapters/fieldaudit.py` called
    it a moved selector, which is exactly what a platform losing a field across its own rows looks
    like. The difference is that these never had it: the extractors read a chapter list and the
    credit sits elsewhere on the page.

    BORROWED RATHER THAN WRITTEN AGAIN. `remaining/releases.py` reads the title's `作品 - 作者 |
    プラットフォーム` shape and the labelled `著者：` form, and puts both through `people_only`, which
    refuses a chapter label sitting where a name belongs. Two copies of that would be two answers.
    """
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "remaining"))
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))
    import releases as _remaining
    from names import credits as _credits
    if where == "title":
        m = re.search(r"<title>[^<|]*?\s+-\s+([^<|]+?)\s*\|", html or "")
        return _credits.people_only(_html.unescape(m.group(1).strip())) if m else None
    if where == "labelled":
        lab = _remaining.LABELLED_CREDIT.search(html or "")
        return _credits.people_only(_html.unescape(lab.group(1).strip())) if lab else None
    return None


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", required=True)
    ap.add_argument("--extract", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit-per-host", type=int, default=40)
    # WHICH HALF OF THE PLATFORMS TO READ, because a browser belongs in one stage and a fetch in
    # another. `update.yml` runs stage A without a browser at all and stage C with one, under a
    # timeout and allowed to fail; a platform that needs Chrome read in stage A would either
    # silently write nothing on a runner without one or make the fetch-only stage as slow and as
    # flaky as the browser stage. `both` is what a person running this by hand wants.
    ap.add_argument("--rendered", choices=("both", "skip", "only"), default="both",
                    help="whether to read the platforms that need a browser")
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    # Hosts already served by a real engine are skipped — a proven adapter beats a heuristic.
    giga = {p["host"] for p in yaml.safe_load(
        open("adapters/gigaviewer/platforms.yaml"))["platforms"]}
    web = {s["host"] for s in yaml.safe_load(
        open("adapters/webpages/sites.yaml"))["sites"]}
    # Hosts with a dedicated adapter of their own, named once in adapters/dedicated.py because
    # adapters/remaining/ needs the same list. comic-walker.com reached here as
    # "電撃ツイッターマガジン" and was re-scraping カドコミ, whose adapter already does it properly.
    # www.yomonga.com has adapters/yomonga/releases.py, which runs from its own work list. The
    # generic pass kept writing a second file for the same five works, and the build read both, so
    # a first-pass parse sat beside the refined one as though a platform had published it:
    # "07Chapter.12第6話-2" against the adapter's "Chapter.16 第15話". See docs/GAPS.md §8.
    web |= set(dedicated.HOSTS)

    plans = {}
    for p in yaml.safe_load(open(a.extract))["platforms"]:
        if p["host"] in giga or p["host"] in web:
            continue
        wants_browser = p.get("strategy") == RENDERED
        if a.rendered == "skip" and wants_browser:
            continue
        if a.rendered == "only" and not wants_browser:
            continue
        if p.get("strategy") in ("markup", "jsonld", "next", "nuxt", "pairs", DATELESS,
                                 RENDERED):
            plans[p["host"]] = {"platform": p["platform"], "strategy": p["strategy"],
                                # WHICH EXTRACTOR READS THE RENDERED DOM, where it is not the
                                # default. A browser supplies markup and the markup still has to
                                # be read by whichever extractor suits the page.
                                "rendered_as": p.get("rendered_as", "pairs"),
                                AUTHOR_FROM: p.get(AUTHOR_FROM)}
    if not plans:
        sys.exit("no hosts with a proven extraction strategy")

    src = yaml.safe_load(open(a.works)) or {}
    targets = {h: [] for h in plans}
    for w in src.get("candidates") or []:
        for u in [w.get("url", "")] + (w.get("urls") or []):
            m = re.match(r"https?://([^/]+)", u or "")
            if m and m.group(1) in targets and len(targets[m.group(1)]) < a.limit_per_host:
                targets[m.group(1)].append({"title": w.get("title"), "url": u})
                break

    written = []
    for host, plan in plans.items():
        rows, failed = [], 0
        for t in targets.get(host, []):
            try:
                page = (render_page(t["url"], cache) if plan["strategy"] == RENDERED
                        else fetch(t["url"], cache))
                # A RENDERED PAGE IS READ BY THE ORDINARY EXTRACTORS. What the browser supplies is
                # the markup that was never in the response, and `try_markup` is what reads markup.
                eps = episodes(page, plan.get("rendered_as", "pairs")
                               if plan["strategy"] == RENDERED else plan["strategy"],
                               today=a.retrieved, page_url=t["url"])
            except (urllib.error.HTTPError, urllib.error.URLError, OSError):
                failed += 1
                continue
            if len(eps) >= MIN_EPISODES:
                who = page_author(page, plan.get(AUTHOR_FROM))
                if who:
                    for e in eps:
                        e.setdefault("author", who)
                rows.append({"work_title": t["title"], "url": t["url"], "episodes": eps,
                             "author": who})
        if not rows:
            print(f"{plan['platform'][:20]:22} nothing parsed ({failed} failed) — writing nothing")
            continue
        pid = re.sub(r"[^a-z0-9]+", "-", host.lower()).strip("-")
        L = [f"# {plan['platform']} — chapters extracted heuristically from work pages.",
             "#",
             "# NOT a publisher-stated field. Blocks carrying a date and a chapter-like label were",
             "# matched in the page; the strategy was proven for this host in",
             "# data/coverage/extract.yaml before being run. Every release carries",
             "# date_basis: heuristic and date_confidence: low so it is never mistaken for the",
             "# kind of statement GigaViewer or FUZ make.",
             "#",
             "# No 百合 label is established here (DEFINITIONS §4); works are named by the Tier C",
             "# yardsticks and this attests only their chapters.",
             "source: webpages", f"platform: {pid}", f"platform_name: {js(plan['platform'])}",
             "publisher: \"\"", f"retrieved: {a.retrieved}", "record_type: web_work_chapters",
             "identification_mode: discovery-candidate",
             f"extraction: {plan['strategy']}", "date_basis: heuristic",
             "date_confidence: low", "works:"]
        for w in rows:
            L.append(f"  - work_title: {js(w['work_title'])}")
            if w.get("author"):
                L.append(f"    author: {js(w['author'])}")
            L.append(f"    url: {js(w['url'])}")
            L.append(f"    chapter_count: {len(w['episodes'])}")
            L.append("    chapters:")
            for e in w["episodes"]:
                L.append(f"      - title: {js(e['title'])}")
                L.append(f"        updated: {e['updated']}")
                if e.get("author"):
                    L.append(f"        author: {js(e['author'])}")
                L.append("        date_basis: heuristic")
        L.append("")
        (out / f"generic-{pid}.yaml").write_text("\n".join(L))
        n = sum(len(w["episodes"]) for w in rows)
        written.append((plan["platform"], len(rows), n))
        print(f"{plan['platform'][:20]:22} works={len(rows):3} chapters={n:4}"
              f"{f'  failed={failed}' if failed else ''}")

    print(f"\n{len(written)} platform(s), {sum(w for _, w, _ in written)} works, "
          f"{sum(c for _, _, c in written)} chapters -> {out}")


if __name__ == "__main__":
    main()
