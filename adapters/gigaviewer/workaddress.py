#!/usr/bin/env python3
"""The work-level address behind a GigaViewer chapter address.

WHY THIS EXISTS. `build.py` gives a series row the address of its newest chapter, and
`identity.py` anchors the work on the row's address, so on a GigaViewer platform a work that
publishes looks like a work the database has never seen. `identity.stable_url` closes the rows
whose chapter address carries the work's own address in front of it, `/title/03056/episode/441581`.
It cannot close `comic-days.com/episode/12207421983997344603`: the chapter id is the whole path and
the series id is nowhere in the string. 506 rows have that shape, across 18 hosts.

WHERE THE ANSWER IS. On the chapter page itself. Every GigaViewer instance emits

    <link rel="alternate" type="application/atom+xml" href="https://HOST/atom/series/SERIES_ID">

so the chapter states which series it belongs to, in the platform's own numbering. That link is the
evidence tying a work-level address to the work, and it needs no title comparison to establish.

TWO ADDRESSES, BECAUSE THE PLATFORMS DIFFER.

`https://HOST/atom/series/SERIES_ID` is the work's feed. Every instance serves it, which makes it
the one shape that reaches all 506 rows, and `data/source/gigaviewer/*-series-feeds.yaml` already
records it per work.

`https://HOST/series/SERIES_ID/first_episode` is the work's reader address, and it is the link the
platform itself puts behind a series on its own listings. It does NOT exist everywhere.
一迅プラス, コミックガルド, MAGCOMI and webアクション have no route for it, and the first two answer
200 with their front page carrying ページが見つかりません, so a status code is not enough to tell
whether the address is real. `states_series` is the test that decides: the reader address is
accepted only when the page it returns names the same series id the chapter named. That check
rejects all four, which is how the soft 404 was found.

A TITLE IS A GUARD HERE AND NOT EVIDENCE. The series link already establishes the address, so
`names_work` exists to catch the other failure: a row whose `url` belongs to some other work,
which would attach one work's identity to another work's address. It compares the row's title
against the chapter page's own og:title, which carries the work title in an order that varies by
platform, so containment on the folded strings is the test rather than equality. A row that fails
it is reported and left alone.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from identity import fold  # noqa: E402

# The chapter page's link to its own series feed. Anchored on the href so that the `?free_only=1`
# variant beside it yields the same id rather than a second one.
SERIES_LINK = re.compile(r'href="https?://([^/"]+)/(?:atom|rss)/series/(\d+)')
OG_TITLE = re.compile(r'<meta property="og:title" content="([^"]*)"')


def series_id(html):
    """`(host, series_id)` the chapter page states for itself, or `(None, None)`.

    Every link on the page must agree. A page carrying two different series ids is not evidence
    about one work, and returning the first would pick by document order.
    """
    found = {m.groups() for m in SERIES_LINK.finditer(html or "")}
    return found.pop() if len(found) == 1 else (None, None)


def og_title(html):
    """The page's og:title, or None."""
    m = OG_TITLE.search(html or "")
    return m.group(1) if m else None


def names_work(og, work):
    """Whether an og:title names this work.

    Containment rather than equality, because the order differs by platform: コミックDAYS writes
    `WORK - AUTHOR / CHAPTER | SITE`, FEEL web writes `CHAPTER / WORK - AUTHOR | SITE`, and
    少年ジャンプ+ writes `[CHAPTER]WORK - AUTHOR | SITE`. An empty work title matches nothing,
    since `""` is contained in every string.
    """
    w, o = fold(work), fold(og)
    return bool(w) and bool(o) and w in o


def feed_address(host, sid):
    """The work's feed address. Served by every GigaViewer instance."""
    return f"https://{host}/atom/series/{sid}"


def reader_address(host, sid):
    """The work's reader address, which four of the eighteen hosts do not serve."""
    return f"https://{host}/series/{sid}/first_episode"


def states_series(html, sid):
    """Whether a page names this series id.

    The guard against a soft 404. 一迅プラス answers `/series/<id>/first_episode` with HTTP 200 and
    its front page, so `status == 200` says nothing; the series id appearing in the returned page
    says the address resolved to the work.
    """
    return bool(sid) and bool(re.search(rf"/(?:atom|rss)/series/{re.escape(str(sid))}\b", html or ""))


def resolve(url, work, get):
    """What a chapter address says about its work's address.

    `get(url)` returns the page text or None, and is injected so that the parsing above is testable
    without a network. Returns a dict with `state` in:

      resolved       the chapter page named its series and the title agrees
      unread         the chapter page could not be fetched
      no-series      the page carries no series link, so this is not a GigaViewer chapter
      title-differs  the page names a work this row is not about

    `reader` is filled only when a second fetch confirms the address resolves to the same series.
    """
    html = get(url)
    if html is None:
        return {"state": "unread", "url": url, "work": work}
    host, sid = series_id(html)
    if not sid:
        return {"state": "no-series", "url": url, "work": work}
    og = og_title(html)
    if not names_work(og, work):
        return {"state": "title-differs", "url": url, "work": work, "og": og,
                "host": host, "series_id": sid}
    out = {"state": "resolved", "url": url, "work": work, "host": host, "series_id": sid,
           "og": og, "feed": feed_address(host, sid), "reader": None}
    reader = reader_address(host, sid)
    page = get(reader)
    if page is not None and states_series(page, sid):
        out["reader"] = reader
    return out


def exposed(rows, chapter_under_title):
    """The series rows anchored on a chapter address the string cannot be reduced to a work.

    Measured here rather than described, so the before and after counts come from one definition.
    """
    return [r for r in rows
            if "/episode" in (r.get("url") or "")
            and not chapter_under_title.match(r.get("url") or "")]


def main(argv=None):
    """Read a work-level address for every exposed row and write it as an attachments file."""
    import argparse, collections, datetime, json                             # noqa: E401

    import identity
    import net

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--series", default="data/build/series.json")
    ap.add_argument("--registry", default="data/identity/works.yaml")
    ap.add_argument("--out", default="data/queue/address-work-level-gigaviewer.yaml")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--limit", type=int, help="stop after this many rows, for a trial run")
    a = ap.parse_args(argv)

    import yaml
    rows = json.loads(pathlib.Path(a.series).read_text())["series"]
    entries = (yaml.safe_load(pathlib.Path(a.registry).read_text()) or {}).get("works") or []
    owner = identity.index(entries)
    seen = collections.Counter(r.get("url") for r in rows if r.get("url"))

    targets = exposed(rows, identity.CHAPTER_UNDER_TITLE)[:a.limit]
    print(f"{len(targets)} exposed row(s)")

    # FETCHED IN TWO SWEEPS, RESOLVED WITHOUT A NETWORK. `resolve` asks for two pages, and asking
    # for them one row at a time is 1,000 requests strictly in series over 18 hosts. `fetch_many`
    # keeps each host at PAUSE while the others are busy, so the run costs what its largest host
    # costs. A listing age, because a series id changes when the platform reorganises and not
    # when the work publishes.
    def sweep(urls):
        got = net.fetch_many(sorted(set(urls)), a.cache, max_age_days=net.AGE_LISTING)
        return {u: r.text for u, r in got.items()}

    pages = sweep([r["url"] for r in targets])
    reads = {}
    for r in targets:
        host, sid = series_id(pages.get(r["url"]) or "")
        if sid:
            reads[reader_address(host, sid)] = None
    print(f"  {sum(1 for v in pages.values() if v)}/{len(pages)} chapter page(s) read; "
          f"{len(reads)} reader address(es) to test")
    pages.update(sweep(reads))

    joins, unresolved = [], []
    counts = collections.Counter()
    for r in targets:
        anchor = identity.web_anchor(r.get("url"), r.get("work"), seen[r.get("url")] > 1)
        wid = owner.get(anchor)
        got = resolve(r["url"], r.get("work"), pages.get)
        counts[got["state"]] += 1
        if got["state"] != "resolved" or not wid:
            if not wid:
                counts["no-identifier"] += 1
            unresolved.append(dict(got, id=wid))
        else:
            base = (f"the chapter page at {r['url']} links its own series feed at {got['feed']}, "
                    f"so the platform places this chapter in series {got['series_id']}, and the "
                    f"og:title there names the work: {got['og']}")
            joins.append({"id": wid, "title": r.get("work"), "url": r["url"],
                          "anchor": f"web:{got['feed']}", "basis": base})
            if got["reader"]:
                joins.append({"id": wid, "title": r.get("work"), "url": r["url"],
                              "anchor": f"web:{got['reader']}",
                              "basis": (f"{base}. {got['reader']} returns a page naming the same "
                                        f"series, which is the platform's own reader address for "
                                        f"the work")})
            counts["reader"] += 1 if got["reader"] else 0

    print(f"{dict(counts)}")
    js = lambda v: json.dumps(v, ensure_ascii=False)                         # noqa: E731
    L = ["# Work-level addresses for GigaViewer rows anchored on a chapter.",
         "#",
         "# WHY. build.py gives a row the address of its newest chapter, and identity.py anchors",
         "# the work on it, so a work that publishes looks like a work never seen before. The",
         "# chapter address here carries nothing of the work, so identity.stable_url cannot reduce",
         "# it and the address had to be fetched.",
         "#",
         "# WHAT THE EVIDENCE IS. Every GigaViewer chapter page links its own series feed. That",
         "# link is the platform placing the chapter in a series, and the og:title beside it names",
         "# the work, which is the guard against a row whose url belongs to somebody else.",
         "#",
         "# Two addresses where the platform serves two. The feed exists on every instance; the",
         "# reader address does not, and 一迅プラス answers it with a 200 carrying its front page,",
         "# so it is kept only where the page returned names the same series.",
         "#",
         "# Written by adapters/gigaviewer/workaddress.py. READ BY: identity.py --attachments.",
         "source: data/build/series.json",
         "role: address-stabilise",
         f"retrieved: {datetime.date.today().isoformat()}",
         "record_type: stable_address",
         "joins:"]
    for j in joins:
        L.append(f"  - id: {j['id']}")
        L.append(f"    title: {js(j['title'])}")
        L.append(f"    url: {js(j['url'])}")
        L.append(f"    anchor: {js(j['anchor'])}")
        L.append(f"    basis: {js(j['basis'])}")
    L.append("")
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L))
    print(f"{len(joins)} attachment(s) -> {out}")

    if unresolved:
        rp = out.with_name(out.stem + "-unresolved.yaml")
        U = ["# Exposed rows whose work-level address could NOT be established, and why.",
             "#",
             "# Left alone deliberately. An unclosed row risks a second identifier later; a wrong",
             "# anchor ties one work's identity to another work's address and is harder to see.",
             f"retrieved: {datetime.date.today().isoformat()}",
             f"count: {len(unresolved)}", "rows:"]
        for u in unresolved:
            U.append(f"  - url: {js(u.get('url'))}")
            U.append(f"    work: {js(u.get('work'))}")
            U.append(f"    id: {js(u.get('id'))}")
            U.append(f"    state: {js(u.get('state'))}")
            if u.get("og"):
                U.append(f"    og_title: {js(u['og'])}")
        U.append("")
        rp.write_text("\n".join(U))
        print(f"{len(unresolved)} unresolved -> {rp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
