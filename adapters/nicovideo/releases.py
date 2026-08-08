#!/usr/bin/env python3
"""ニコニコ漫画 — work-level update dates (REQUIREMENTS §5).

This platform was recorded as structurally unusable. That was wrong, and the error is worth
stating plainly: the blocker said "work pages carry no per-episode date, so a release cannot be
placed on a timeline", and concluded that reaching it would need one fetch per episode. Both the
observation and the conclusion were wrong in the way that matters.

The observation: `episode_item` markup really does carry no date — only `data-number`, a page
count and view counters. But the date is on the page, in `div.meta_info`, at WORK level:

    2026年07月23日更新   2024年10月24日開始   [ 4話 無料 ]   [4コママンガ]

The conclusion: the feed's unit for an unattested update is "this work updated, on this date" —
that is what the comparators state and what the feed shows. Work level is therefore sufficient,
and it costs one fetch per work like カドコミ and FUZ, not one per episode.

Checked against the comparator before building: 百合ナビ claimed 魔女まじょS-WITCH updated
2026-07-23, and the page says 2026年07月23日更新. It is server-rendered, so no browser is needed.

What this establishes and what it does not:

- `updated` is the platform's own statement about the work, so a release built from it is
  **attested** rather than claimed. It is not per-chapter: we learn that the work updated, never
  which chapter, so `ep` is empty and the update kind stays `unknown` unless something else fills
  it in.
- `開始` gives a genuine serialisation start date — the first positive evidence of `new-series`
  this project has had from a platform.
- `[ N話 無料 ]` states how many episodes are free.
- the breadcrumb names the CHANNEL the work sits in, きららベース and 43 others across the works we
  hold. Its consumer is `check.py`'s `nicovideo channels agree with our own records`, which sets it
  against the channels `data/source/nicovideo/resolved.yaml` recorded by hand. Nothing in
  `build.py` reads it: a channel is a section of a platform and not a platform, and what the
  interface should do with one is `build.py`'s question rather than this adapter's.
- ニコニコ remains a poor `preferred` source: image quality is worse than the origin platforms and
  it syndicates heavily (overlap 0.71). This makes it a fallback for works reachable nowhere else,
  which is exactly what its 65 exclusive works are.

Never stored: episode thumbnails, synopsis text, or page images (§2).

Usage:  releases.py --works data/coverage/webcomics-works.yaml --out data/source/nicovideo \
                    --cache $YURI_CACHE/nico-cache --retrieved 2026-08-01
"""
import argparse, json, pathlib, re, sys, time, urllib.error, urllib.request
import html as htmlmod
from collections import Counter

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
WORK = "https://manga.nicovideo.jp/comic/{cid}"
PAUSE = 1.5
MIN_WORKS = 20


def fetch(cid, cache, max_age_days=1):
    f = cache / f"{cid}.html"
    if f.exists() and (time.time() - f.stat().st_mtime) / 86400 < max_age_days:
        return f.read_text()
    req = urllib.request.Request(WORK.format(cid=cid), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t


def iso(y, m, d):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


# THE ELEMENT CARRIES MARKUP, so this reads to `</small>` and strips tags rather than stopping at
# the first `<`. Three of the 157 cached pages end the line with `<br />`, which made an
# `[^<]*</small>` pattern fail to match at all and report no rights on a page that states them.
COPYRIGHT = re.compile(r'<small class="copyright">(.*?)</small>', re.S)
# THE MARK IS NOT WRITTEN ONE WAY, and this pattern used to accept only `(C)`. Of the 154 cached
# work pages carrying a copyright line, 98 open with something else: © on its own, © followed by
# the emoji variation selector, Ⓒ in a circle, （C）and (ｃ) in fullwidth, &copy with no semicolon,
# and one page using @. The old pattern read nothing on all 98 and returned [] , which looks
# exactly like a page that states no rights (§5). It is the only field on this platform that names
# a PUBLISHER, so 98 publishers went unread.
#
# Found by capturing four real pages as fixtures. The invented markup the test had been written
# against said `(C)おにぎりパクパク/芳文社`, which is a real spelling and the minority one.
COPYRIGHT_MARK = re.compile(r'^\s*(?:[(（]\s*[cCｃＣ]\s*[)）]|[©Ⓒⓒ]️?|&copy;?|@)\s*')
EPISODE = re.compile(r'<li class="episode_item">(.*?)</li>', re.S)
EP_LINK = re.compile(r'<div class="title"><a href="(/watch/mg\d+)">([^<]*)</a>')
EP_NUMBER = re.compile(r'data-number="(\d+)"')
# The breadcrumb, which is the only element on the page that names the channel THIS work is in.
# Everything else carrying an /official/ address is navigation to somebody else's.
PANKUZU = re.compile(r'<ul class="sg_pankuzu">(.*?)</ul>', re.S)
# A slug may hold a hyphen (nico-yurihime, comic-valkyrie), and a pattern of [a-z0-9_]+ cuts it at
# the first one, so ニコニコ百合姫's 28 works would have read as a channel called `nico`.
CHANNEL = re.compile(r'<a href="/official/([a-z0-9_-]+)"[^>]*>\s*<span[^>]*>\s*'
                     r'(?:\[公式\]\s*)?([^<]*?)\s*</span>')


def rights(html):
    """The names in a work page's copyright line, `(C)おにぎりパクパク/芳文社`.

    A platform states an author on every work and a publisher on almost none. ニコニコ prints both,
    which is what lets a serialisation found here be joined to a printed book on the publisher when
    the two sides write the author differently. RUNBOOK §11 asks for the creator, the publisher or
    the imprint, and this is the only field on this platform that answers the second.

    THE ELEMENT IS THE EVIDENCE, NOT THE MARK. Eight of the 154 cached pages open the line with no
    copyright mark at all, `Mori/MAG Garden` and `Kawakami Shiwon/Hitoma Iruma/Nekoyashiki Pushio`
    among them. The element says `class="copyright"`, so its contents are the rights line whether
    or not it is punctuated as one, and refusing those would repeat in miniature the fault above.
    """
    m = COPYRIGHT.search(html or "")
    if not m:
        return []
    line = COPYRIGHT_MARK.sub("", _text(re.sub(r"<[^>]+>", " ", m.group(1))))
    return [x.strip() for x in re.split(r"[/／・,、]", line) if x.strip()]


def episodes(html):
    """[{title, url, number}] for the episodes the work page renders, in document order.

    PARTIAL BY CONSTRUCTION, and the page says so itself. 運命のヤマダダダダダダダダダダ renders
    five items numbered 1, 2, 3, 13 and 17 while its newest is 第16話, and its meta line reads
    `[ 5話 無料 ]`. What is rendered is what a signed-out reader may open, the same way
    pixivコミック's rendered list is, so the count is our reach and never the length of the work.

    No episode carries a date. That is the platform's limit rather than this parser's, which is why
    `parse` reads the work-level 更新 and 開始 dates from `div.meta_info` instead.
    """
    out = []
    for m in EPISODE.finditer(html or ""):
        b = m.group(1)
        link = EP_LINK.search(b)
        if not link:
            continue
        n = EP_NUMBER.search(b)
        out.append({"title": _text(link.group(2)),
                    "url": "https://manga.nicovideo.jp" + link.group(1),
                    "number": int(n.group(1)) if n else None})
    return out


def channel(html):
    """`{"channel": "きららベース", "channel_slug": "kirara"}`, from the breadcrumb, or `{}`.

    WHICH ELEMENT NAMES THE CHANNEL, because the page holds two kinds of /official/ address and
    only one of them is about this work. The breadcrumb states where the work sits:

        <ul class="sg_pankuzu"> ... <li ...><a href="/official/kirara" itemprop="url">
        <span itemprop="title">[公式] きららベース</span></a></li> ...

    The sidebar renders a banner for every official channel on the site, 157 of them, opening with
    ニコニコ漫画（公式） at /official/nicomanga. An unscoped search finds that banner first and
    returns it for every work on the platform, which is what this did: all 180 works we hold were
    filed under `nicomanga`, and the value passed inspection because one slug looks like another.
    The scope to `sg_pankuzu` is the whole of the fix, and it is why the pattern is anchored on the
    breadcrumb list instead of on the link.

    An empty dict where the breadcrumb names no channel, which is a state and not a gap (§5).
    ニコニコ漫画 carries a section anybody may post to, and those works read マンガ > その他マンガ
    with no /official/ crumb at all: 19 of the 180.

    The NAME is the joinable value. `data/platforms.yaml` records きららベース by name, under
    `channel_of: ニコニコ漫画`, and its own `id` is `kirarabase`, which is not the slug. A consumer
    handed the slug alone would have to invent that mapping, and a channel presented as a platform
    is the category error `build.py` already fixed once.
    """
    bc = PANKUZU.search(html or "")
    m = CHANNEL.search(bc.group(1)) if bc else None
    return {"channel": m.group(2), "channel_slug": m.group(1)} if m else {}


# A PAGE IS HTML AND ITS TEXT IS ESCAPED, so a title carrying an ampersand arrives as `&amp;` and
# every pass downstream treats those five characters as part of the name. ひよ&びびっと! was stored
# as `ひよ&amp;びびっと!`, the analyser read `amp` as a word, and the romanisation shipped as
# `Hiyo & Amp ; Bibi to !`. The other files that hold this title have it right, so the fault is
# here and not in what was captured. Applied to every string read out of the markup, because the
# next one to carry an entity will be a different field.
def _text(s):
    return htmlmod.unescape(str(s or "")).strip()


def parse(html):
    """Read div.meta_info. Absent or unparsable means no date — never a guessed one (§6)."""
    m = re.search(r'class="meta_info"(.*?)</div>', html, re.S)
    if not m:
        return None
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
    out = {}
    u = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日更新", txt)
    s = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日開始", txt)
    if u:
        out["updated"] = iso(*u.groups())
    if s:
        out["started"] = iso(*s.groups())
    n = re.search(r"\[\s*(\d+)話\s*(無料)?\s*\]", txt)
    if n:
        out["episode_count"] = int(n.group(1))
        if n.group(2):
            out["free_episodes"] = int(n.group(1))
    fm = re.search(r"\[([^\]]*マンガ)\]", txt)
    if fm:
        out["format"] = fm.group(1).strip()
    t = re.search(r"<title>([^<]*)</title>", html)
    if t:
        # ニコニコ states its works as "タイトル / 作者", which is a cleaner identity than the
        # comparator cell that named the work for us.
        head = _text(t.group(1).split(" - ")[0])
        # The title element is "タイトル / 作者 おすすめ無料漫画 - ニコニコ漫画". The trailing
        # editorial phrase varies (おすすめ漫画 / おすすめ無料漫画) and was landing in the author
        # field — "むちゃ おすすめ漫画".
        head = re.sub(r"\s*おすすめ(無料)?漫画\s*$", "", head).strip()
        if "/" in head:
            out["title"], _, out["author"] = (_text(x) for x in head.partition("/"))
        else:
            out["title"] = _text(head)
    # The work page renders the first few episodes AND the latest one, each with its title and a
    # /watch/ link. The 更新 date in meta_info is the date THAT episode appeared, so naming it costs
    # nothing and turns a work-level row into one that says which chapter — which is what a reader
    # looking at the page sees. Only the newest is emitted: the others carry no date of their own.
    #
    # `episodes` is the one reader of this markup. A second copy here drifted the moment the
    # discovery pass needed the whole list rather than the last item, which is the two-paths-one-
    # fact shape (STANDING-INSTRUCTIONS §3).
    eps = [e for e in episodes(html[html.find('id="episode_list"'):]) if e.get("number") is not None]
    if eps:
        best = max(eps, key=lambda e: e["number"])
        out["latest_episode"] = best["title"]
        out["latest_episode_url"] = best["url"]
        out["rendered_episodes"] = len(eps)

    out.update(channel(html))
    return out or None


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit", type=int, default=2000)
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    src = yaml.safe_load(open(a.works)) or {}
    targets = {}
    for w in src.get("candidates") or []:
        for u in [w.get("url", "")] + (w.get("urls") or []):
            m = re.search(r"manga\.nicovideo\.jp/comic/(\d+)", u or "")
            if m:
                targets.setdefault(m.group(1), w.get("title"))
    # Works that reach us only through 百合ナビ have no URL and so no id. Ids found by external
    # search live here; without them a work on a platform we watch stays an unclassified claim.
    res = pathlib.Path("data/source/nicovideo/resolved.yaml")
    if res.exists():
        for w in (yaml.safe_load(res.read_text()) or {}).get("works") or []:
            if w.get("comic_id"):
                targets.setdefault(str(w["comic_id"]), w.get("title"))

    # A LIMIT THAT BITES IN SILENCE IS A LOST WORK. The default was set when the seed list
    # was smaller, and a discovery pass that adds two hundred targets pushes the tail off
    # the end with nothing said. The default is now above the population and the cut is
    # reported when it happens, so a list outgrowing it is a number somebody sees.
    if len(targets) > a.limit:
        print(f"LIMIT: {len(targets)} work(s) named, {a.limit} asked for; "
              f"{len(targets) - a.limit} will not be read this run")
    targets = dict(list(targets.items())[: a.limit])
    if not targets:
        sys.exit("no ニコニコ漫画 work ids found")

    works, failed = [], []
    for cid, title in targets.items():
        try:
            d = parse(fetch(cid, cache))
        except urllib.error.HTTPError as e:
            failed.append((title, f"HTTP {e.code}"))
            continue
        except Exception as e:                                  # noqa: BLE001
            failed.append((title, type(e).__name__))
            continue
        if not d or not d.get("updated"):
            failed.append((title, "no meta_info date"))
            continue
        d["comic_id"] = cid
        d["url"] = WORK.format(cid=cid)
        d.setdefault("title", title)
        works.append(d)

    if len(works) < MIN_WORKS:
        sys.exit(f"HEALTH: resolved {len(works)} works (< {MIN_WORKS}). The meta_info markup may "
                 "have changed. Refusing to write.")

    L = ["# ニコニコ漫画 work-level update dates, read from div.meta_info on each work page.",
         "#",
         "# WORK level, not chapter level: the platform states that the work updated on a date, and",
         "# never which chapter. So these attest an update and nothing about its contents — no",
         "# chapter title, no number. Recorded as attested because the platform itself says it.",
         "#",
         "# `started` is a real serialisation start date, the first positive new-series evidence",
         "# any platform here has given us.",
         "source: webpages", "platform: nicovideo", "platform_name: ニコニコ漫画",
         f"retrieved: {a.retrieved}", "record_type: work_update_dates",
         "identification_mode: discovery-candidate",
         "granularity: work",
         f"works_resolved: {len(works)}", "works:"]
    for w in sorted(works, key=lambda w: w["updated"], reverse=True):
        L.append(f"  - work_title: {js(w['title'])}")
        for k in ("author", "url", "comic_id", "updated", "started", "episode_count",
                  "free_episodes", "format", "channel", "channel_slug", "latest_episode",
                  "latest_episode_url"):
            if w.get(k) not in (None, ""):
                L.append(f"    {k}: {js(w[k])}")
    L.append("")
    (out / "nicovideo.yaml").write_text("\n".join(L))

    dated = sum(1 for w in works if w.get("updated"))
    started = sum(1 for w in works if w.get("started"))
    freed = sum(1 for w in works if w.get("free_episodes"))
    print(f"works targeted : {len(targets)}")
    print(f"works resolved : {len(works)}  ({dated} dated, {started} with a start date)")
    print(f"free-episode counts stated : {freed}")
    if failed:
        print(f"failed         : {len(failed)}  {Counter(r for _, r in failed).most_common(3)}")
    print(f"written        : {out}/nicovideo.yaml")


if __name__ == "__main__":
    main()
