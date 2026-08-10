#!/usr/bin/env python3
"""One reading of comici's chapter list, shared by every adapter that touches a comici host.

WHY THIS EXISTS. comici's three-state access badge was worked out and fixed in
adapters/remaining/ — and reached almost nothing, because most comici platforms are not read by
that adapter at all. adapters/webpages/ has its own two-state parser and produces キミコミ, 竹コミ,
ビッコミ, ライコミ, Gコミ, HERO'S Web, チャンピオンクロス and 花とゆめ+. An audit found ワインガールズ
badged 4 free / 10 ticket / 2 paid on the page and reported as 4 free / 6 paid, months after the
fix that should have covered it.

Two parsers for one engine means a fix lands in one of them. So there is now one.

THE BADGES. comici marks access three ways, and the middle one is the one a reader cares about:

    data-e2e="eliFreeBadge"      free — 今なら無料 counts, it is readable now
    data-e2e="eliIfIcon"         作品チケット: one free chapter per series per day, per account
    data-e2e="eliWfIcon"        共通チケット: one extra free chapter per day, any series
    data-e2e="eliCoinIcon"       coin. Actually paid.

The two ticket systems are different rules with the same outcome — every chapter marked with either
can be read for nothing, eventually — so both are `free-timed` and which one it was is kept in
access_note. The paid test runs FIRST, because a paid row can carry the word 無料 in surrounding
promotional text.

THE RANGES. comici renders ten episodes and hides the rest behind もっと見る. It also renders a range
navigation — /episodes/<hash>/1, /2, /3 labelled 1, 31, 61 — and those are ordinary URLs returning a
whole block rather than a page of ten. Following them takes お姉さんは女子小学生に興味があります。 from
22 chapters to 76, and the LAST range holds the newest, which is all an update feed needs. No
browser and no credential: the episode list is also served by plus-api.comici.jp, which answers 403
without a contentApiKey Bearer token from the site's own bundle, and this project does not replay
one.
"""
import html as _html
import re

#: Comici's episode marker, matched in two files. Its markup belongs to its adapter.
EPISODE_ITEM = re.compile(r'data-e2e="eli"')

BLOCK = EPISODE_ITEM
ROW = re.compile(
    r'data-e2e="eliTitle">([^<]+)<.*?series-eplist-item-meta-date">(\d{4})/(\d{1,2})/(\d{1,2})<',
    re.S)
SORT_LINK = re.compile(r'class="series-sort-link"[^>]*href="([^"]+)"')
PAID = re.compile(r'data-e2e="eliCoinIcon"|series-eplist-item-access-paid')
TICKET_WORK = re.compile(r'data-e2e="eliIfIcon"')
TICKET_ANY = re.compile(r'data-e2e="eliWfIcon"')
FREE = re.compile(r'data-e2e="eliFreeBadge"'
                  r'|series-eplist-item-access-text[^"]*mode-free'
                  r'|series-eplist-item-access[^>]*>\s*(?:<[^>]*>\s*)*無料')


def is_comici(html):
    return bool(BLOCK.search(html or ""))


def access_of(block):
    """(access_modes, note) for one episode block, or (None, None) when it states nothing."""
    if PAID.search(block):
        return ["purchase"], None
    if TICKET_WORK.search(block):
        return ["free-timed"], "作品チケット — one free chapter per series per day, per account"
    if TICKET_ANY.search(block):
        return ["free-timed"], "共通チケット — one extra free chapter per day, any series"
    if FREE.search(block):
        return ["free"], None
    return None, None


def rows(html):
    """Episodes on one page, in the order the platform lists them."""
    if not is_comici(html):
        return []
    out = []
    for b in re.split(r'(?=<div data-e2e="eli")', html)[1:]:
        m = ROW.search(b)
        if not m:
            continue
        row = {"title": _html.unescape(m.group(1).strip()),
               "updated": f"{int(m.group(2)):04d}-{int(m.group(3)):02d}-{int(m.group(4)):02d}"}
        modes, note = access_of(b)
        if modes:
            row["access_modes"] = modes
        if note:
            row["access_note"] = note
        out.append(row)
    return out


def chapters(html, page_url, fetch):
    """Every episode, following the range navigation when the page offers one.

    `fetch` is the caller's own fetcher, so caching and pacing stay where they belong.
    """
    if not is_comici(html):
        return []
    ranges = list(dict.fromkeys(SORT_LINK.findall(html)))
    if ranges and page_url:
        base = re.match(r"(https?://[^/]+)", page_url)
        if base:
            merged, seen = [], set()
            for rel in ranges:
                u = rel if rel.startswith("http") else base.group(1) + rel
                if u in seen:
                    continue
                seen.add(u)
                merged += rows(fetch(u) or "")
            if merged:
                ded = {}
                for r in merged:
                    ded.setdefault((r["title"], r["updated"]), r)
                return list(ded.values())
    return rows(html)

# The platform's own word for where a serialisation stands, carried in the page's data and not in
# anything a reader sees. Three values across 251 cached pages, and every one is an assertion:
# 連載中 120, 読み切り 66, 完結 65. There is no fourth meaning "we do not know", so a page that
# carries the field has answered.
#
# ESCAPED, which is why it went unread. comici serves its data inside a Next.js flight payload, so
# the JSON arrives with its quotes backslashed: \"status\":\"完結\". A pattern written for
# ordinary JSON matches nothing and reports the field absent, which is what happened when this was
# first checked by hand. Both forms are accepted, because the escaping is a property of the
# delivery rather than of the fact.
STATUS = re.compile(r'\\?"status\\?"\s*:\s*\\?"([^"\\]+)\\?"')

FINISHED = "完結"
ONESHOT = "読み切り"
RUNNING = "連載中"


def status(html):
    """What the platform says about the serialisation, or None where it says nothing."""
    m = STATUS.search(html or "")
    return m.group(1) if m else None


# The work's own page, as an episode page links it: /series/<hash>. The hash is hexadecimal, which
# is what separates it from the platform's own /series/list/up/1 paging and from
# /store_items/series/4333/1, both of which sit on the same page and neither of which is a work.
SERIES_LINK = re.compile(r'href="(?:https?://[^/"]+)?/series/([0-9a-f]{8,})(?:/[a-z]+)?"')


def series_link(html):
    """The work-level hash an episode page states for itself, or None.

    WHY IT IS READ FROM THE EPISODE PAGE. `build.py` gives a row the address of its newest chapter,
    so a row landing on /episodes/<hash> moves when the work publishes and `identity.py` mints a
    second identifier for a work it already holds. The episode page carries a link to its own
    series, and that link is what ties the work's address to the work.

    Every link must agree. A page naming two series is not evidence about one work, and taking the
    first would be picking by document order.
    """
    found = set(SERIES_LINK.findall(html or ""))
    return found.pop() if len(found) == 1 else None


def series_address(host, series_hash):
    """The work's address on a comici host."""
    return f"https://{host}/series/{series_hash}"
