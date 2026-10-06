#!/usr/bin/env python3
"""Chapter lists from server-rendered work pages, for platforms with no feed (REQUIREMENTS §5).

Several platforms publish no Atom feed but render their episode lists server-side, so a named work
can be followed by polling its own page. Works are named by the Tier C yardsticks; the platform
attests the chapters.

Selectors live in `sites.yaml` as declarative data (§6): adding a platform is a row, and repairing
one after a redesign is a bounded edit rather than a code change. Sites sharing an engine share a
spec — ビッコミ and 竹コミ both run comici with identical markup.

None of these platforms applies a 百合 tag, so nothing here establishes marketing_label.

Never stored: synopsis text or image URLs (§2).

Usage:  releases.py --gap data/coverage/webcomics-gap.yaml --out data/source/webpages \
                    --cache $YURI_CACHE/webpages-cache --retrieved 2026-08-01
"""
import html as _html
import argparse, json, pathlib, re, sys, time, urllib.error, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import comici  # noqa: E402
import textnorm  # noqa: E402
from collections import Counter

import yaml
import pathlib as _pl, sys as _sy                                         # noqa: E401,E402
_sy.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))    # noqa: E402
import htmlbits as _htmlbits                                            # noqa: E402
from facts import identity as _identity                                  # noqa: E402
from facts.worktitle import norm_work as _norm_work                      # noqa: E402

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.5
MIN_WORKS = 3


def fetch(url, cache, max_age_days=1):
    """The page, from the cache while it is younger than `max_age_days`, else from the host.

    THE AGE TEST IS THE WHOLE POINT AND IT WAS MISSING. This read `if f.exists()` and returned
    whatever was there, so a page fetched once was the page every later run read. The workflow
    carries `.cache` between runs, which made that for ever: on 2026-09-21 ビッコミ was serving a
    chapter dated 2026-08-27 while this pass held nothing after 2026-07-27, and four more platforms
    were frozen the same way, each at the day its own pages were first fetched.

    NOTHING THE RUN PRINTED SAID SO. The rows are complete, so the step reported
    `takecomic works= 22/ 22 chapters= 506` and a full access breakdown, and only the three seconds
    it took across 107 works gave it away. `kadokomi/releases.py` and `generic/releases.py` both
    take this argument; this is the one fetcher in the family that did not.
    """
    f = cache / (re.sub(r"[^a-zA-Z0-9]+", "_", url)[-80:] + ".html")
    if f.exists() and (time.time() - f.stat().st_mtime) / 86400 < max_age_days:
        return f.read_text()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t


TRUNCATED = re.compile(r"(?:\.{2,}|\u2026)\s*$")
OG_TITLE = _htmlbits.OG_TITLE


def carry_over(path, urls):
    """Works already in the file that this run did not reach, so a partial run keeps them.

    The writer replaced each site's file with whatever the run happened to fetch, and the targets
    come from the gap report, which shrinks as coverage improves. Re-running to collect one new
    field therefore deleted works: a pass that reached 65 dropped 49 from the catalogue, and their
    curated names became strays pointing at nothing. The same fault was fixed in the render adapter
    for the same reason.

    A work reached this time is replaced, because a fresh reading beats an old one. A work not
    reached is kept, because not looking at a page is not a finding about it.
    """
    p = pathlib.Path(path)
    if not p.exists():
        return []
    old = yaml.safe_load(p.read_text()) or {}
    keep = []
    for w in (old.get("works") or []):
        if w.get("url") in set(urls):
            continue
        # The file names the list `chapters` and the run names it `episodes`. The writer takes the
        # run's shape, so a carried work is handed back in it.
        w = dict(w, episodes=w.get("chapters") or [])
        w.pop("chapters", None)
        w.pop("chapter_count", None)
        keep.append(w)
    return keep


#: The work a page names in its own title, before the byline and the platform.
PAGE_WORK = re.compile(r"<title>\s*([^<|]+?)(?:\s+-\s+[^<|]*)?\s*\|")


def _related(a, b):
    """Whether two titles are one work, one of them perhaps the short form of the other."""
    x, y = _norm_work(a or ""), _norm_work(b or "")
    return bool(x) and bool(y) and (x.startswith(y) or y.startswith(x))


def misdirected(title, url, html, owner_of, title_of, addresses=()):
    """`(work id, title)` of the held work an address belongs to, where the candidate is another work.

    THE CASE. Web漫画アンテナ lists 超かぐや姫! at two addresses: its own カドコミ page, held as
    w00320, and `bibibi-comic.com/series/41de76fc8df5f`, which is the page of its spin-off
    超かぐやメシ！, held as w03278. Reading the second under the candidate's title wrote the
    spin-off's chapters and byline as an entry named 超かぐや姫!, and that entry offered one address
    twice, which has sat in quarantine since 2026-09-27, and on 2026-10-06 won the title-keyed author
    lookup and put テルヤ / 山下清悟 / フジヤマルリ on 超かぐや姫！'s own page.

    THE REGISTRY DECIDES THAT TWO WORKS ARE TWO, NOT THE TITLES. A first version compared the
    candidate's title with the held one, and over the 1,612 aggregator candidates it refused
    噓つき花嫁と同性結婚論, the held 嘘つき花嫁と同性結婚論 written with the other form of 噓, while
    友達/友だち and ―/- escaped only because the page happened to use the candidate's spelling. So a
    refusal needs all three of: this address is held work A; ANOTHER of the candidate's own addresses
    is held work B, a different work, whose title is the candidate's; and this page does not title
    itself as the candidate. Every test that fails to fire errs toward reading the row as before.
    """
    here = owner_of.get(_identity.web_anchor(url))
    if not here:
        return None
    elsewhere = {owner_of.get(_identity.web_anchor(u)) for u in addresses if u != url}
    own = [w for w in elsewhere - {None, here} if _related(title, title_of.get(w))]
    if not own:
        return None
    page = PAGE_WORK.search(html or "")
    if not page or _related(page.group(1), title):
        return None
    return here, title_of.get(here) or ""


def floor_for(site, targets, refused):
    """The fewest works a healthy parse of this site yields, counted over the candidates it read.

    REFUSED CANDIDATES ARE NOT COUNTED, because the floor asks whether the parser emptied and a
    refusal is a decision made before parsing. ビビビコミック has three candidates and MIN_WORKS is
    three, so counting the refused one would have put the site under its floor and written nothing
    for it at all.
    """
    read = max(1, len(targets) - len(refused))
    return site.get("min_works", min(MIN_WORKS, read))


#: comici states the author in the page title as "作品 - 作者 | プラットフォーム".
TITLE_AUTHOR = re.compile(r"<title>[^<|]*?\s+-\s+([^<|]+?)\s*\|")


def author_of(html, site, page):
    """The byline a work page states in its title, or None.

    AN EPISODE PAGE NAMES NOBODY. comici titles a series page `作品 - 作者 | キミコミ` and an
    episode page `作品・第1話 | キミコミ`, so a work whose target address is a chapter came back
    with no author while its own series page credited three people: 午後4時。透明、ときどき声優,
    the one キミコミ work of sixteen captured from `/episodes/`, reached readers with no credits on
    2026-10-02. The episode page links its series, which is how its work-level anchor was found,
    and that page is asked for the byline when the first page states none.

    ONLY THE BYLINE, AND THE TARGET ADDRESS IS LEFT ALONE. Reading the whole row from the series
    page instead would change the address the row is filed under, and release identifiers are
    built from it, so every chapter already published would be minted again beside itself.

    `page` is the caller's guarded fetch, which answers "" on a refusal, so a series page that
    will not load costs this work its byline and nothing else. §5: no author is stated where no
    page states one.
    """
    au = TITLE_AUTHOR.search(html or "")
    if not au and site.get("engine") == "comici":
        h = comici.series_link(html)
        if h:
            au = TITLE_AUTHOR.search(page(comici.series_address(site["host"], h)) or "")
    return _html.unescape(au.group(1).strip()) if au else None


def untruncated(target_title, html):
    """The page's own name for the work, where the one we were given is a truncation of it.

    The target list is built from listings, and a listing truncates. youngchampion.jp cuts at a
    fixed character count and appends an ellipsis, so 公爵令嬢の籠絡ミッション arrived with its
    second half missing and no full-length copy anywhere else in the catalogue to recover it from.
    The page states the whole thing in og:title.

    ONLY WHERE IT IS A TRUNCATION, tested by prefix. og:title is not reliably a bare work name:
    マガポケ puts the episode and the platform in it, so taking it wherever it differs would trade
    a truncated title for a decorated one. A page whose og:title begins with what we were given,
    minus a trailing ellipsis, is stating the same name at greater length and nothing else is.

    THE PREFIX IS TESTED ON THE COMPARISON FORM. The listing wrote 切り札です! with a half-width
    mark and the page writes 切り札です！ with a full-width one, so a literal prefix test fails on
    the one case it exists for. textnorm folds that difference and keeps the words.
    """
    # ONLY A VISIBLY TRUNCATED TITLE IS REPAIRED. Without this the rule fires on
    # 私に天使が舞い降りた！, whose og:title is the same name followed by the episode and the
    # platform, and swaps a correct title for a decorated one. A trailing ellipsis is the platform
    # saying it cut the string, and it is the only invitation to go looking for the rest.
    if not target_title or not TRUNCATED.search(target_title):
        return target_title
    m = OG_TITLE.search(html or "")
    if not m:
        return target_title
    og = _html.unescape(m.group(1)).strip()
    stem = TRUNCATED.sub("", target_title).strip()
    if not stem or not textnorm.norm(og).startswith(textnorm.norm(stem)):
        return target_title
    # THE TAIL IS CUT AT THE DECORATION, not taken whole. youngchampion.jp states the bare title in
    # og:title; comic-gardo states "<work> - <author> / <episode>". Taking the whole string put the
    # author into the work's name. The separator is only honoured PAST the stem, so a title
    # containing one of these marks keeps it.
    # The result is the platform's own string throughout, never ours spliced onto theirs: the
    # listing wrote 切り札です! and the page writes 切り札です！, and keeping our half of the join
    # would publish a title neither source states. The stem's length indexes into og safely,
    # because a half-width mark and a full-width one are each one character.
    tail = og[len(stem):]
    for sep in (" - ", " | ", "｜"):
        if sep in tail:
            og = og[:len(stem) + tail.index(sep)]
            break
    og = og.strip()
    return og if len(og) > len(stem) else target_title

def episodes(html, eng, base, page_url=None, fetch=None):
    # comici is read by the shared module, not by this file's selectors. Its access model has three
    # states and its chapter list is paginated behind a range navigation; both were worked out once
    # and both used to live only in adapters/remaining/, so every comici platform read HERE — キミコミ,
    # 竹コミ, ビッコミ, ライコミ, Gコミ, HERO'S Web, チャンピオンクロス, 花とゆめ+ — carried a two-state
    # reading and only the first ten chapters. One engine, one parser.
    if eng.get("engine_name") == "comici" and comici.is_comici(html):
        return comici.chapters(html, page_url, fetch or (lambda u: ""))
    # Commented-out markup is not content. コミックノヴァ keeps the previous state of its episode
    # list in a comment beside the live one, and the stale copy parses just as well: the 猫魔法
    # record carried a third chapter called 第第1話(1/2)話, which is the template's own placeholder
    # with the label substituted into it twice. adapters/recon/extract.py met the identical fault
    # on the identical pages and was fixed the same way; this is the second parser, so it needs
    # the same rule rather than the same bug.
    html = re.sub(r"<!--.*?-->", " ", html or "", flags=re.S)
    out = []
    for b in re.split(eng["block"], html)[1:]:
        tm = re.search(eng["title"], b)
        if not tm:
            continue
        dm = re.search(eng["date"], b) if eng.get("date") else None
        um = re.search(eng["url"], b) if eng.get("url") else None
        row = {"title": tm.group(1).strip()}
        if dm:
            row["updated"] = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
        if um:
            u = um.group(1)
            row["url"] = u if u.startswith("http") else base.rstrip("/") + u
        # Only a stated value is recorded; absence is left unset rather than assumed (§6).
        if eng.get("free") and re.search(eng["free"], b):
            row["access_modes"] = ["free"]
        elif eng.get("paid") and re.search(eng["paid"], b):
            row["access_modes"] = ["purchase"]
        elif eng.get("free_attr"):
            fm = re.search(eng["free_attr"], b)
            if fm:
                row["access_modes"] = ["free"] if fm.group(1) == "true" else ["purchase"]
        out.append(row)
    return out


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--sites", default="adapters/webpages/sites.yaml")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--registry", default="data/identity/works.yaml")
    a = ap.parse_args()

    # WHICH HELD WORK EACH ADDRESS BELONGS TO, so a candidate the aggregator filed at another work's
    # page can be refused instead of written under the wrong title. See `misdirected`.
    _reg = pathlib.Path(a.registry)
    _entries = ((yaml.safe_load(_reg.read_text(encoding="utf-8")) or {}).get("works") or []) \
        if _reg.exists() else []
    owner_of = _identity.index(_entries)
    title_of = {e["id"]: e.get("title") for e in _entries}

    spec = yaml.safe_load(open(a.sites))
    engines = spec["engines"]
    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    gap = yaml.safe_load(open(a.gap)) or {}
    # Accepts either the full candidate list (candidates/urls) or the gap report
    # (works_missing/url). The full list is what should be used — the gap deliberately excludes
    # everything already reachable, so an adapter reading it loses works the moment they are.
    missing = []
    # EVERY ADDRESS A CANDIDATE IS LISTED AT, which is how `misdirected` knows the candidate is
    # already held as some other work.
    addresses_of = {}
    for w in gap.get("candidates") or []:
        addresses_of.setdefault(w.get("title"), []).extend(w.get("urls") or [])
        for u in w.get("urls") or []:
            missing.append({"title": w.get("title"), "url": u})
    for w in gap.get("works_missing") or []:
        missing.append({"title": w.get("title"), "url": w.get("url")})

    grand = Counter()
    for site in spec["sites"]:
        eng = dict(engines[site["engine"]], engine_name=site["engine"])
        targets = [w for w in missing
                   if site["host"] in (w.get("url") or "")][:a.limit]
        if not targets:
            print(f"{site['id']:12} no works in the gap file")
            continue

        works, failed, refused = [], [], []
        for tgt in targets:
            try:
                html = fetch(tgt["url"], cache)
            except urllib.error.HTTPError as e:
                failed.append((tgt["title"], f"HTTP {e.code}"))
                continue
            # THE INNER FETCH IS GUARDED TOO. `episodes` is handed this to read the pages a
            # series is paginated over, and it was `lambda u: fetch(u, cache)` with nothing round
            # it, while the fetch of the series page above records an HTTP error against that one
            # title and carries on. So a single transient refusal on page 2 of one work raised out
            # of the loop and ended the adapter: run 31399575062 lost all 13 platforms and wrote 0
            # works to one 502 Bad Gateway, from a host that answers 200 either side of it.
            #
            # An empty page is the contract `episodes` already has, since its caller reads
            # `fetch(u) or ""`, so a refusal degrades that one work's pagination and nothing else.
            def _page(u, _c=cache, _f=failed, _t=tgt):
                try:
                    return fetch(u, _c)
                except urllib.error.HTTPError as e:
                    _f.append((_t["title"], f"HTTP {e.code} on a continuation page"))
                    return ""
                except (urllib.error.URLError, OSError) as e:
                    _f.append((_t["title"], f"{type(e).__name__} on a continuation page"))
                    return ""

            mis = misdirected(tgt["title"], tgt["url"], html, owner_of, title_of,
                              addresses_of.get(tgt["title"], ()))
            if mis:
                refused.append((tgt["title"], tgt["url"]) + mis)
                continue
            eps = episodes(html, eng, f"https://{site['host']}", tgt["url"], _page)
            if len(eps) < site.get("min_episodes", 1):
                failed.append((tgt["title"], f"{len(eps)} episodes parsed"))
                continue
            # The byline, which was never read, so every comici platform reported chapters with no
            # author; and from the series page where the target is a chapter. See `author_of`.
            au = author_of(html, site, _page)
            row = {"work_title": untruncated(tgt["title"], html), "url": tgt["url"],
                   "episodes": eps}
            # THE PLATFORM'S OWN WORD ON THE SERIALISATION, which nothing was reading. comici
            # states 完結, 読み切り or 連載中 in the page's data, and a hand review of 121 dormant
            # works found it settled every one of the fourteen on these platforms. It is an
            # attestation rather than a tag somebody applied, so it belongs in the source record.
            # `eng` is the engine's SPEC, not its name: comparing it to a string was quietly
            # false everywhere and the field was collected for nothing. site["engine"] is the name.
            st = comici.status(html) if site["engine"] == "comici" else None
            if st:
                row["status"] = st
            if au:
                row["author"] = au
            works.append(row)

        # The floor exists to catch a site redesign silently emptying a parser. It has to scale
        # with how many works the site actually has, or a platform carrying one yuri title is
        # permanently indistinguishable from a broken one — which is what happened to 花とゆめ+
        # (4 candidates) and COMICリュエル (1) the first time they ran.
        floor = floor_for(site, targets, refused)
        if len(works) < floor:
            print(f"HEALTH: {site['id']} — {len(works)} works parsed (< {floor}); "
                  "markup may have changed. Writing nothing for this site.", file=sys.stderr)
            continue

        L = [f"# {site['name']} ({site.get('publisher') or 'publisher not established'}) — chapters from "
         "server-rendered work pages.",
             "# Works named by a Tier C yardstick; the platform attests the chapters.",
             "# This platform applies no 百合 tag, so nothing here establishes marketing_label.",
             "source: webpages", f"platform: {site['id']}",
             f"platform_name: {js(site['name'])}", f"publisher: {js(site.get('publisher', ''))}",
             f"engine: {site['engine']}", f"retrieved: {a.retrieved}",
             "record_type: web_work_chapters", "identification_mode: discovery-candidate",
             "works:"]
        # Everything this run did not reach, written back unchanged. See carry_over.
        _path = out / f"{site['id']}.yaml"
        for w in works + carry_over(_path, [x["url"] for x in works]):
            L.append(f"  - work_title: {js(w['work_title'])}")
            if w.get("status"):
                L.append(f"    status: {js(w['status'])}")
            if w.get("author"):
                L.append(f"    author: {js(w['author'])}")
            L.append(f"    url: {js(w['url'])}")
            L.append(f"    chapter_count: {len(w['episodes'])}")
            L.append("    chapters:")
            for e in w["episodes"]:
                L.append(f"      - title: {js(e['title'])}")
                for k in ("updated", "url"):
                    if e.get(k):
                        L.append(f"        {k}: {js(e[k])}")
                if e.get("access_modes"):
                    L.append(f"        access_modes: {js(e['access_modes'])}")
        L.append("")
        (out / f"{site['id']}.yaml").write_text("\n".join(L))

        ne = sum(len(w["episodes"]) for w in works)
        acc = Counter(m for w in works for e in w["episodes"]
                      for m in (e.get("access_modes") or []))
        grand["works"] += len(works)
        grand["chapters"] += ne
        print(f"{site['id']:12} works={len(works):3}/{len(targets):3} chapters={ne:5}"
              + (f"  access={dict(acc)}" if acc else "")
              + (f"  failed={len(failed)}" if failed else "")
              + (f"  refused={len(refused)}" if refused else ""))
        for title, url, wid, held in refused:
            print(f"    refused {title!r}: {url} is {wid} {held!r}, so not written under that title")

    print()
    print(f"total: {grand['works']} works, {grand['chapters']} chapters -> {out}")


if __name__ == "__main__":
    main()
