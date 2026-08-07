#!/usr/bin/env python3
"""カドコミ release tracking (REQUIREMENTS §5).

カドコミ is the largest single source of active yuri web serialisation — 53 of the 250 works that
updated in a recent 3.5-week window, more than twice any other platform — but it publishes no feed
and its tag search loads from a robots-disallowed `/api/`.

Its per-work `/detail/<code>` pages are permitted and server-rendered though, embedding
`latestEpisodes` and `firstEpisodes` in `__NEXT_DATA__`. So works named by the Tier C yardsticks
are polled individually. No crawling, no API.

Unlike the other no-feed platforms, カドコミ *does* apply a 百合 tag, so this establishes
marketing_label under DEFINITIONS §4 where the tag is present.

Never stored: `summary` (publisher synopsis, §2) or thumbnail URLs.

Usage:  releases.py --works data/coverage/webcomics-works.yaml --out data/source/kadokomi \
                    --cache $YURI_CACHE/kadokomi-cache --retrieved 2026-08-01
"""
import argparse
import datetime, json, pathlib, re, sys, time, urllib.error, urllib.request
from collections import Counter

import yaml

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
DETAIL = "https://comic-walker.com/detail/{code}"
PAUSE = 1.5
YURI_TAGS = {"百合", "GL", "ガールズラブ"}
MIN_WORKS = 5


def fetch(code, cache, max_age_days=1):
    f = cache / f"{code}.html"
    if f.exists():
        age = (time.time() - f.stat().st_mtime) / 86400
        if age < max_age_days:
            return f.read_text()
    req = urllib.request.Request(DETAIL.format(code=code), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            t = r.read().decode("utf-8", "replace")
    finally:
        time.sleep(PAUSE)
    f.write_text(t)
    return t


def work_data(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return None
    d = json.loads(m.group(1))
    for q in d.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", []):
        data = (q.get("state") or {}).get("data")
        if isinstance(data, dict) and "work" in data:
            return data
    return None


def ep_rows(data):
    """Episodes carry an id, code, title, update timestamp — and, it turns out, their access.

    This used to say free/paid was "not stated in a form we have established", which was true when
    written and stopped being true without anyone noticing. It is stated, in two fields:

        isActive        readable right now, without paying
        deliveryPeriod  when that ends; 9999-12-31 means it does not

    On 私を喰べたい、ひとでなし, 48 of 410 episodes are active and the rest are not — カドコミ's usual
    "newest few stay open" shape.

    Only the POSITIVE statement is recorded. isActive true means the platform says you can read it,
    so that is `free`. isActive false means it is not open, and カドコミ does not say whether that is
    because it must be bought or because it is simply gone — so nothing is recorded, and the row
    reads as unknown rather than as paid. Asserting 有料 from a missing field is what put
    オタクサキュバスの才能がありすぎる！ — a free one-shot — in the interface as paid."""
    out = {}
    for key in ("latestEpisodes", "firstEpisodes"):
        block = data.get(key) or {}
        lst = block.get("result") if isinstance(block, dict) else block
        for e in lst or []:
            if not isinstance(e, dict):
                continue
            code = e.get("code") or e.get("id")
            if not code:
                continue
            # WHEN IT WAS PUBLISHED IS NOT WHEN IT OPENS. `updateDate` is the chapter's own
            # date. `startDate` and `deliveryStartAt` are when カドコミ starts delivering it, which
            # for a rotating free window is a date in the future and has nothing to do with when
            # the chapter came out: 悪いが私は百合じゃない carried 28 chapters of a 2020 serial
            # stamped three days ahead of the capture, and on that day they surfaced as 28 new
            # chapters of a work whose newest is from June, none of them readable.
            #
            # So a delivery date is recorded as what it is, and a date in the future is never
            # accepted as a publication date whichever field it came from.
            when = str(e.get("updateDate") or "")[:10]
            opens = str(e.get("startDate") or e.get("deliveryStartAt") or "")[:10]
            if when > _TODAY:
                opens, when = opens or when, ""
            row = {"code": code, "title": (e.get("title") or "").strip(),
                   "subtitle": (e.get("subTitle") or "").strip(),
                   "updated": when}
            if opens:
                row["opens_on"] = opens
                if opens > _TODAY:
                    # Not out yet. Recorded so a later run can tell a chapter that arrived from one
                    # that was always there, and so nothing downstream reads it as an update.
                    row["not_yet_delivered"] = True
            if e.get("isActive") is True:
                row["access_modes"] = ["free"]
                dp = str(e.get("deliveryPeriod") or "")[:10]
                # 9999-12-31 is the platform's way of saying "no end", not a date.
                if dp and not dp.startswith("9999"):
                    row["free_until"] = dp
            out[code] = row
    return drop_rotated(list(out.values()))


_TODAY = datetime.date.today().isoformat()

_NUM = re.compile(r"(?:Chapter|第|#)\s*(\d+)", re.I)


def chapter_no(row):
    """The chapter's own number, where its title states one."""
    m = _NUM.search(row.get("title") or "")
    return int(m.group(1)) if m else None


def drop_rotated(rows):
    """Dates that cannot be publication dates, refused.

    カドコミ's `updateDate` is when the ENTRY last changed, not when the chapter came out, and it
    moves when a chapter re-enters the free rotation. 悪いが私は百合じゃない reported chapters 1 to
    28 of a serial that began in 2020 as updated today while its chapter 55 sat at June, so 28
    chapters of a work whose newest is from June appeared in the feed as new, none of them readable
    and none carrying a URL.

    A serial's chapter 28 cannot be published after its chapter 55, and that contradiction sits
    inside the work's own data. So a date later than every higher-numbered chapter's is not a
    publication date: the chapter is recorded undated, and the timestamp is kept as `rotated_date`
    so a later pass can tell it from a chapter nobody ever dated. Only the date goes.

    A work whose chapters carry no numbers states no order, so nothing there contradicts anything.
    """
    numbered = [(r, chapter_no(r)) for r in rows]
    for row, num in numbered:
        if num is None or not row.get("updated"):
            continue
        later = [r.get("updated") for r, n in numbered
                 if n is not None and n > num and r.get("updated")]
        if later and row["updated"] > max(later):
            row["rotated_date"] = row.pop("updated")
    return rows


def carry_over(path, resolved_codes):
    """Works already in the file that this run did not resolve, so a failed fetch keeps them.

    A pass keeps what it did not look at. カドコミ answered 398 of 400 works and the two that
    returned an error were simply not written, which removed them from the corpus: a transient HTTP
    error is a fact about a request rather than about a manga. Two curated titles stopped
    naming works we hold that way, on a run whose only intent was to correct some dates.

    Keyed on `platform_code`, which is what a work is fetched by. A work this run resolved is
    replaced, because a fresh answer beats a stored one.
    """
    f = pathlib.Path(path)
    if not f.exists():
        return []
    old = yaml.safe_load(f.read_text()) or {}
    keep = []
    for w in (old.get("works") or []):
        if str(w.get("platform_code")) in {str(c) for c in resolved_codes}:
            continue
        w = dict(w, episodes=w.get("chapters") or [])
        w.pop("chapters", None)
        w.pop("chapter_count", None)
        keep.append(w)
    return keep


def js(v):
    return json.dumps(v, ensure_ascii=False)


def _next_update(work):
    """What カドコミ says about its next chapter for this work, if it says anything."""
    t = (work.get("nextUpdateDateText") or "").strip()
    if not t:
        return None
    if t == "未定":
        return {"next_update_undecided": True}
    m = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", t)
    if not m:
        return None
    try:
        return {"next_update": datetime.date(*(int(x) for x in m.groups())).isoformat()}
    except ValueError:
        return None            # a date the platform prints and the calendar does not have


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", required=True, help="Tier C candidate list naming カドコミ works")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit", type=int, default=2000)
    # How stale a cached page may be before it is fetched again. The default keeps a daily run
    # honest; raising it re-runs the PARSE over pages already held, which is what you want when
    # the parser has changed and the pages have not.
    ap.add_argument("--max-age", type=float, default=1)
    a = ap.parse_args()

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    codes = {}
    # カドコミ's own 百合 catalogue is authoritative and complete; prefer it over antenna seeding.
    cat = pathlib.Path("data/source/kadokomi/catalogue.yaml")
    if cat.exists():
        for w in (yaml.safe_load(cat.read_text()) or {}).get("works") or []:
            if w.get("code"):
                codes[w["code"]] = w.get("title")

    # Works the publisher does not tag 百合 are absent from the catalogue, so a comparator naming
    # one had nothing to resolve against. Codes found by external search live here.
    res = pathlib.Path("data/source/kadokomi/resolved.yaml")
    if res.exists():
        for w in (yaml.safe_load(res.read_text()) or {}).get("works") or []:
            if w.get("code"):
                codes[w["code"]] = w.get("title")

    # Works confirmed from the discovery queue. Confirmation established what they ARE and then
    # nothing fetched their episodes, so a one-shot found through 百合ナビ produced a work record
    # and no release — which is why the feed showed one one-shot in thirteen hundred entries.
    conf = pathlib.Path("data/source/kadokomi/confirmed.yaml")
    if conf.exists():
        for w in (yaml.safe_load(conf.read_text()) or {}).get("works") or []:
            if w.get("platform_code"):
                codes.setdefault(w["platform_code"], w.get("work_title"))

    src = yaml.safe_load(open(a.works)) or {}
    for c in src.get("candidates") or []:
        if "カドコミ" not in (c.get("platforms") or []):
            continue
        for u in [c.get("url", "")] + (c.get("urls") or []):
            m = re.search(r"comic-walker\.com/detail/([A-Za-z0-9_]+)", u or "")
            if m:
                codes[m.group(1)] = c.get("title")
    # The candidate list carries platform names but not always URLs; fall back to the gap report,
    # which does.
    gapf = pathlib.Path(a.works).parent / "webcomics-gap.yaml"
    if gapf.exists():
        for w in (yaml.safe_load(gapf.read_text()) or {}).get("works_missing") or []:
            m = re.search(r"comic-walker\.com/detail/([A-Za-z0-9_]+)", w.get("url") or "")
            if m:
                codes.setdefault(m.group(1), w.get("title"))
    # A LIMIT THAT BITES IN SILENCE IS A LOST WORK. The default was set when the seed list
    # was smaller, and a discovery pass that adds two hundred targets pushes the tail off
    # the end with nothing said. The default is now above the population and the cut is
    # reported when it happens, so a list outgrowing it is a number somebody sees.
    if len(codes) > a.limit:
        print(f"LIMIT: {len(codes)} work(s) named, {a.limit} asked for; "
              f"{len(codes) - a.limit} will not be read this run")
    codes = dict(list(codes.items())[:a.limit])
    if not codes:
        sys.exit("no カドコミ work codes found")

    works, failed, tagged = [], [], 0
    for code, title in codes.items():
        try:
            d = work_data(fetch(code, cache, a.max_age))
        except urllib.error.HTTPError as e:
            failed.append((title, f"HTTP {e.code}"))
            continue
        if not d:
            failed.append((title, "no payload"))
            continue
        w = d["work"]
        tags = [t["name"] for t in w.get("tags") or []]
        hits = [t for t in tags if t in YURI_TAGS]
        if hits:
            tagged += 1
        works.append({
            "work_title": w.get("title", title), "platform_code": code,
            "url": DETAIL.format(code=code), "tags": tags,
            "status": w.get("serializationStatus"),
            "authors": [x.get("name") for x in w.get("authors") or []],
            "marketing_label": "yuri" if hits else "none",
            "yuri_tags": hits,
            "episodes": ep_rows(d),
            # THE PLATFORM'S OWN ANNOUNCEMENT, out of the payload rather than the prose beside it.
            # カドコミ carries nextUpdateDateText, either a whole date or 未定 where it does not
            # know. 未定 is kept, because a platform saying it has not settled a date is a
            # different fact from a page that says nothing, and it is the honest answer to a
            # reader asking when the next chapter lands.
            "stated_schedule": _next_update(w),
        })

    if len(works) < MIN_WORKS:
        sys.exit(f"HEALTH: resolved {len(works)} works (< {MIN_WORKS}). Refusing to write.")

    # Everything this run did not resolve, written back unchanged. See carry_over.
    resolved_now = len(works)
    works += carry_over(out / "chapters.yaml", [w["platform_code"] for w in works])

    L = ["# カドコミ per-work episode lists. Works named by a Tier C yardstick; カドコミ attests them.",
         "# カドコミ DOES apply a 百合 tag, so marketing_label is established where present (§4).",
         "# No synopsis and no image URLs are stored (REQUIREMENTS §2).",
         "source: kadokomi", f"retrieved: {a.retrieved}", "record_type: web_work_chapters",
         "identification_mode: discovery-candidate", "works:"]
    for w in works:
        L.append(f"  - work_title: {js(w['work_title'])}")
        for k in ("platform_code", "url", "status", "marketing_label"):
            if w.get(k):
                L.append(f"    {k}: {js(w[k])}")
        # A CARRIED-OVER WORK IS WHATEVER THE LAST RUN WROTE, not what this one builds, so every
        # field here is optional. Reading w["yuri_tags"] directly killed the first run that carried
        # anything, which is a mechanism added without asking what consumes it.
        L.append(f"    tags: {js(w.get('tags') or [])}")
        L.append(f"    authors: {js([x for x in (w.get('authors') or []) if x])}")
        if w.get("yuri_tags"):
            L.append("    marketing_label_basis:")
            L.append("      source: kadokomi")
            L.append(f"      url: {js(w.get('url') or '')}")
            L.append(f"      retrieved: {a.retrieved}")
            L.append(f"      note: {js('Publisher applies the tag ' + '/'.join(w['yuri_tags']) + ' on カドコミ.')}")
        elif w.get("marketing_label_basis"):
            # Carried from a run that did establish it, kept verbatim including the day it was read.
            L.append("    marketing_label_basis:")
            for k2 in ("source", "url", "retrieved", "note"):
                if w["marketing_label_basis"].get(k2):
                    L.append(f"      {k2}: {js(w['marketing_label_basis'][k2])}")
        if w.get("stated_schedule"):
            L.append("    stated_schedule:")
            for k2, v2 in sorted(w["stated_schedule"].items()):
                L.append(f"      {k2}: {js(v2)}")
        L.append(f"    chapter_count: {len(w.get('episodes') or [])}")
        L.append("    chapters:")
        for e in (w.get("episodes") or []):
            L.append(f"      - code: {js(e.get('code') or '')}")
            L.append(f"        title: {js(e.get('title') or '')}")
            if e.get("subtitle"):
                L.append(f"        subtitle: {js(e['subtitle'])}")
            if e.get("updated"):
                L.append(f"        updated: {js(e['updated'])}")
            if e.get("access_modes"):
                L.append(f"        access_modes: {js(e['access_modes'])}")
            if e.get("free_until"):
                L.append(f"        free_until: {js(e['free_until'])}")
            # When the platform starts delivering it, which is not when it was published.
            if e.get("opens_on"):
                L.append(f"        opens_on: {js(e['opens_on'])}")
            if e.get("not_yet_delivered"):
                L.append("        not_yet_delivered: true")
            # The timestamp that was refused, kept rather than discarded: a later pass can tell a
            # chapter nobody ever dated from one whose date was a rotation stamp.
            if e.get("rotated_date"):
                L.append(f"        rotated_date: {js(e['rotated_date'])}")
    L.append("")
    (out / "chapters.yaml").write_text("\n".join(L))

    eps = sum(len(w["episodes"]) for w in works)
    dated = sum(1 for w in works for e in w["episodes"] if e.get("updated"))
    print(f"works targeted : {len(codes)}")
    print(f"works resolved : {resolved_now}  ({tagged} carry a publisher yuri tag)")
    if len(works) > resolved_now:
        print(f"carried over   : {len(works) - resolved_now} not reached this run, kept as they were")
    print(f"episodes       : {eps}  ({dated} dated)")
    if failed:
        print(f"failed         : {len(failed)}")


if __name__ == "__main__":
    main()
