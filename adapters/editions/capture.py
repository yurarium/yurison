#!/usr/bin/env python3
"""Follow each web work's own platform page to the shops selling its volumes, and keep the ISBNs.

WHY THIS EXISTS. 862 of the 3,083 works this database holds have a web serialisation and no print
edition attached: no tankōbon, no volume count, no ISBN. Many of them plainly have collected
volumes. The reason we had none is that the print catalogue is reached by imprint and by a
retailer's yuri shelf, and a work serialised on a general platform is on neither.

The platform knows. Every engine surveyed on 2026-08-07 links from a series to the shops selling
that series' volumes, and those links carry identifiers. `adapters/editions/platforms.py` reads
each engine's page and `stores.py` reads each link.

WHAT THIS FILE IS NOT. It is not a record and it cannot become one. Everything it writes goes to
`data/queue/`, which sits outside the source tree so nothing can promote a candidate by accident.
A shop is Tier C, discovery only (REQUIREMENTS §1). What the ISBNs are for is
`adapters/madb/by_platform_isbn.py`, which asks the national bibliography and writes the answer.

THE JOIN IS THE ADDRESS, NEVER THE TITLE. Each row is keyed on the platform URL this database
already holds for the serialisation, and the ISBN was read off that URL's own page. So the volume
belongs to the work because of where it was found and not because two strings agreed. `トワ・エ・モア`
is a 1996 コンパス anthology and a 2024 講談社 series at once, and `citrus+` returned an unrelated
2007 book on a title match, which is why this is stated rather than assumed.

WHAT A PLATFORM'S SILENCE MEANS. Most of the 862 have no volumes because they are 読み切り or a
serialisation too young for one. A work whose page carries no shop link is recorded with
`books: none-listed` rather than skipped, because "the platform lists nothing" and "we never
asked" are different states and only one of them is worth asking again.

Usage:  capture.py                     every gap work, resuming from the output
        capture.py --engine comici     one engine
        capture.py --limit 50          the first 50 still outstanding
        capture.py --report            read the output and say what it holds
"""
import argparse
import collections
import datetime
import json
import pathlib
import re
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cmoa                                                                    # noqa: E402
import engines                                                                 # noqa: E402
import net                                                                     # noqa: E402
import paths                                                                   # noqa: E402
import platforms as P                                                          # noqa: E402
import stores as S                                                             # noqa: E402
import yaml                                                                    # noqa: E402

OUT = "data/queue/platform-editions.yaml"
SERIES = "data/build/series.json"

# A series page and a book page both change a few times a year, and a publication does not change
# at all. Nothing here is a release feed, so the cache is allowed to answer for a fortnight.
AGE = net.AGE_LISTING

# pixivコミック's API answers only to the client marker its own site sends. `pixivcomic/releases.py`
# established this route and the marker is its, not a browser's.
PIXIV_HEADERS = {"X-Requested-With": "pixivcomic", "Referer": "https://comic.pixiv.net/",
                 "Origin": "https://comic.pixiv.net", "Accept": "application/json"}

# THE FLOOR, AS A SHARE OF WHAT WAS ASKED. A loop that dies halfway comes back with a handful of
# rows, writes them, and reads as a quiet day rather than as a run that stopped. The counter-case,
# so this is not lowered later to make a run pass: a platform whose markup changed would fail this
# legitimately, and the answer is to look at the markup rather than to move the floor.
FLOOR = 0.5


def gap_works(path=SERIES):
    """Every work with a web serialisation and no print edition, as the build states it.

    Read from `data/build/series.json` rather than from the source layer, because the question is
    what the PUBLISHED database is missing and that is the build's answer, not a source's.
    """
    doc = json.loads(pathlib.Path(path).read_text())
    out = []
    for w in doc.get("series") or []:
        if not w.get("sources") or w.get("print"):
            continue
        for s in w["sources"]:
            out.append({"id": w.get("id"), "work": w.get("work"), "author": w.get("author"),
                        "platform": s.get("platform"), "url": s.get("url")})
    return out


def fetch(url, cache, headers=None):
    """One page, from the shared fetcher. Returns the body or None, never raising."""
    if headers:
        return _fetch_with(url, cache, headers)
    return net.fetch(url, cache, AGE).text


def _fetch_with(url, cache, headers):
    """A fetch carrying one adapter's own client marker, cached in the same place.

    `net.fetch` sends the project's identity and nothing else, which is right for a page. pixiv's
    API refuses that and answers its own site's marker, so this adds the header and keeps
    everything else as net.py has it: the pause, the cache and the outcome handling.
    """
    import urllib.error
    import urllib.request
    cache = pathlib.Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / net.cache_key(url)
    import time
    if f.exists() and (time.time() - f.stat().st_mtime) / 86400 < AGE:
        return f.read_text(encoding="utf-8", errors="replace")
    net._wait(urllib.parse.urlparse(url).netloc)                               # noqa: SLF001
    req = urllib.request.Request(url, headers={"User-Agent": net.UA, **headers})
    try:
        with urllib.request.urlopen(req, timeout=net.TIMEOUT) as r:
            text = r.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError):
        return None
    f.write_text(text)
    return text


def resolve_short(url, cache):
    """The ISBN behind a shortened Amazon link, or None.

    Costs one request and is only spent where a block offers nothing else. 集英社 pairs an
    `amzn.asia` link with a page that states the number, so following it there would buy nothing;
    文春 and OUR FEEL offer the short link alone, and following it is the only way through.
    """
    # The answer is the URL redirected to, and `net.fetch` reports that only on the request that
    # made it: a cache hit returns the address asked for, because a cached body has no redirect to
    # report. So the resolved address is kept beside the cached body, which is the one fact the
    # cache cannot reconstruct.
    side = pathlib.Path(cache) / (net.cache_key(url) + ".resolved")
    if side.exists():
        return S.isbn_of(side.read_text())
    r = net.fetch(url, cache, AGE)
    final = r.final_url or ""
    if r.status == 200:
        side.parent.mkdir(parents=True, exist_ok=True)
        side.write_text(final)
    return S.isbn_of(final)


def from_publisher(urls, cache):
    """`(isbn, page)` where a link identifies a book in a publisher's own catalogue, else `(None, None)`.

    Costs one request. Two shapes reach it: a link straight to the publisher's book page, and a
    shop id that the publisher's catalogue addresses under its own code. ビッコミ is the second.
    Every one of its shop links is a keyword search except 小学館's comic database, which carries
    the code that names the book page.
    """
    for u in urls or []:
        got = S.shop_id_of(u)
        if not got:
            continue
        page = P.publisher_page(got[0], got[1])
        if not page:
            continue
        isbn = P.publisher_isbn(fetch(page, cache) or "", engines.host_of(page))
        if P.states_id(isbn, got[0], got[1]):
            return isbn, page
    return None, None


def book(isbn, title=None, via=None, volume=None):
    """One printed volume as the capture stores it."""
    row = {"isbn": isbn}
    if volume is not None:
        row["volume"] = volume
    if title:
        row["stated_title"] = title
    if via:
        row["via"] = via
    return row


# ── one function per engine, each returning (books, notes) ────────────────────────────────────
# Each takes the work's own platform URL and a cache, and answers with the printed volumes that
# page leads to. `notes` is what the page said that the books do not carry: a shop id that needed
# following, a block that stated no number, a page that was not there.

def from_giga(url, cache):
    """GigaViewer: the series sidebar, one block per collected volume."""
    body = fetch(url, cache)
    if body is None:
        return [], ["page not fetched"]
    blocks = P.gigaviewer_books(body)
    if not blocks:
        return [], ["no series-book-details block; the platform lists no volume for this series"]
    out, notes = [], []
    for b in blocks:
        got = S.one_isbn(b["urls"])
        if got:
            out.append(book(got, b["title"], via=url))
            continue
        got, page = from_publisher(b["urls"], cache)
        if got:
            out.append(book(got, b["title"], via=page))
            continue
        short = [u for u in b["urls"] if S.is_short(u)]
        if short:
            got = resolve_short(short[0], cache)
            if got:
                out.append(book(got, b["title"], via=short[0]))
                continue
        notes.append(f"block {b['title'][:30]!r} states no number")
    return out, notes


def from_gangan(url, cache):
    """ガンガンONLINE: its own 単行本 section, one shop-banner row per volume."""
    body = fetch(url, cache)
    if body is None:
        return [], ["page not fetched"]
    out, notes = [], []
    for b in P.ganganonline_books(body):
        got = S.one_isbn(b["urls"])
        if got:
            out.append(book(got, b["title"], via=url))
        else:
            notes.append(f"volume {b['title'][:30]!r} states no number")
    if not out and not notes:
        notes.append("no 単行本 section on the page")
    return out, notes


def from_comici(url, cache, max_items=None):
    """Comici: the series page names a store item per volume; the item page carries the shops."""
    body = fetch(url, cache)
    if body is None:
        return [], ["page not fetched"]
    found = P.comici_store_items(body)
    if not found["items"] and found["all_url"]:
        body = fetch(urllib.parse.urljoin(url, found["all_url"]), cache) or ""
        found = P.comici_store_items(body)
    if not found["items"]:
        return [], ["no 単行本情報 block; the platform lists no volume for this series"]
    base = f"https://{engines.host_of(url)}"
    out, notes = [], []
    for item in found["items"][:max_items]:
        page = fetch(f"{base}/store_items/{item}", cache)
        if page is None:
            notes.append(f"store item {item} not fetched")
            continue
        links = P.comici_store_links(page)
        got = S.one_isbn(links)
        if got:
            out.append(book(got, via=f"{base}/store_items/{item}"))
            continue
        got, pub = from_publisher(links, cache)
        if got:
            out.append(book(got, via=pub))
        else:
            notes.append(f"store item {item} offers no printed edition")
    if found["stated"]:
        notes.append(f"the platform states {found['stated']} volume(s)")
    return out, notes


def from_kadokomi(url, cache):
    """カドコミ: the shop row names a コミックシーモア title, whose own page states the ISBNs.

    None of カドコミ's own shop links states a number: most are keyword searches, and the ones that
    are not identify a file on a digital store. コミックシーモア's title id is the exception, and it
    is the identifier this route rests on. cmoa is Tier C and supplies discovery only; what it
    supplies is which edition to ask the bibliography about.
    """
    body = fetch(url, cache)
    if body is None:
        return [], ["page not fetched"]
    doc = P.kadokomi_next_data(body)
    if not doc:
        return [], ["no __NEXT_DATA__; the page shape may have changed"]
    if not doc["comics"]:
        return [], ["カドコミ lists no collected volume for this work"]
    notes, ids = [], []
    for c in doc["comics"]:
        for st in c["stores"]:
            got = S.shop_id_of(st.get("url") or "")
            if got and got[0] == "cmoa_title" and got[1] not in ids:
                ids.append(got[1])
    if not ids:
        return [], [f"{len(doc['comics'])} volume(s) listed and no shop link identifies an edition"]
    out = []
    for tid in ids:
        page = fetch(cmoa.work_url(tid), cache)
        if page is None:
            notes.append(f"cmoa title {tid} not fetched")
            continue
        w = cmoa.work(page, tid)
        if w.get("isbn"):
            first = (w.get("volumes") or [{}])[0]
            out.append(book(w["isbn"], first.get("name"), via=cmoa.work_url(tid),
                            volume=w.get("detail_volume")))
        else:
            notes.append(f"cmoa title {tid} states no ISBN, so no printed edition is identified")
    return out, notes


def from_pixiv(url, cache):
    """pixivコミック: `ad_books` answers with the printed books, ASIN and cover URL both."""
    m = re.search(r"comic\.pixiv\.net/works/(\d+)", url)
    if not m:
        return [], ["not a pixivコミック work URL"]
    api = f"https://comic.pixiv.net/api/app/works/{m.group(1)}/ad_books"
    body = fetch(api, cache, PIXIV_HEADERS)
    if body is None:
        return [], ["ad_books not fetched"]
    out, notes = [], []
    for b in P.pixiv_ad_books(body):
        got = S.one_isbn([b.get("amazon_url") or "", b.get("image_url") or ""])
        if got:
            out.append(book(got, b.get("title"), via=api))
        else:
            notes.append(f"book {str(b.get('title'))[:30]!r} states no printed ASIN")
    if not out and not notes:
        notes.append("pixivコミック lists no printed book for this work")
    return out, notes


def from_comicboost(url, cache):
    """comicブースト: the series page links 幻冬舎コミックス's own book page per volume."""
    body = fetch(url, cache)
    if body is None:
        return [], ["page not fetched"]
    links = P.comicboost_books(body)
    if not links:
        return [], ["no コミックス block; the platform lists no volume for this series"]
    out, notes = [], []
    for u in links:
        got = P.publisher_isbn(fetch(u, cache) or "", engines.host_of(u))
        if got:
            out.append(book(got, via=u))
        else:
            notes.append(f"publisher page {u} states no ISBN")
    return out, notes


def from_yanmaga(url, cache):
    """ヤンマガWeb: the series page links 講談社's product page, which states the ISBN."""
    series = P.yanmaga_series_url(url)
    body = fetch(series, cache)
    if body is None:
        return [], ["series page not fetched"]
    links = P.yanmaga_books(body)
    if not links:
        return [], ["no コミックス banner; the platform lists no volume for this series"]
    out, notes = [], []
    for u in links:
        got = P.publisher_isbn(fetch(u, cache) or "", engines.host_of(u))
        if got:
            out.append(book(got, via=u))
        else:
            notes.append(f"publisher page {u} states no ISBN")
    return out, notes


ROUTES = {"giga": from_giga, "comici": from_comici, "kadokomi": from_kadokomi,
          "pixiv": from_pixiv, "gangan": from_gangan, "comicboost": from_comicboost,
          "yanmaga": from_yanmaga}


def merge(doc, rows):
    """Fold new rows into the document, keeping every work the rows do not mention.

    A pass keeps what it is not looking at. Rebuilding this file from only what the
    current run fetched is the failure this project has met three times, and it is silent: the file
    is well-formed, smaller, and says nothing about what went missing.
    """
    held = {w["platform_url"]: w for w in (doc.get("works") or [])}
    added = 0
    for r in rows:
        if r["platform_url"] not in held:
            added += 1
        held[r["platform_url"]] = r
    out = dict(doc)
    out["works"] = sorted(held.values(), key=lambda w: (w.get("platform") or "",
                                                        w.get("platform_url") or ""))
    return out, added


HEADER = """\
# Printed volumes found by following each web work's own platform page to the shops selling them.
# NOT RECORDS. A shop is Tier C, discovery only (REQUIREMENTS §1), and data/queue/ sits outside the
# source tree so nothing here can become a record by accident. adapters/madb/by_platform_isbn.py
# takes the ISBNs to the national bibliography, and the bibliography's answer is what is stored.
#
# KEYED ON `platform_url`, the address this database already holds for the serialisation. The ISBN
# was read off that URL's own page, so a volume belongs to a work because of where it was found.
# Nothing here matched a title against a title, which is the failure `citrus+` and `トワ・エ・モア`
# are recorded against.
#
# WHAT THE FIELDS MEAN.
#   engine    which page shape was read. adapters/editions/engines.py names the chain of requests.
#   books     the printed volumes the platform led to, each with the page its ISBN was read off.
#             An empty list with a `note` is an answer: the platform lists no printed volume.
#   note      what the page said that the books do not carry. A block stating no number, a shop
#             that identifies only a file, a series the platform has not collected.
#
# A WORK WITH NO BOOKS IS NOT A FAILURE. Most of the works in this file are 読み切り or a
# serialisation too young for a tankōbon. Absence is a state (STANDING-INSTRUCTIONS §5).
"""


def render(doc):
    js = lambda v: json.dumps(v, ensure_ascii=False)                           # noqa: E731
    L = [HEADER.rstrip(), "",
         f"source: {doc['source']}", f"role: {doc['role']}",
         f"record_type: {doc['record_type']}", f"retrieved: {doc['retrieved']}",
         "key: platform_url", "counts:"]
    for k, v in sorted((doc.get("counts") or {}).items()):
        L.append(f"  {k}: {v}")
    L.append("works:")
    for w in doc.get("works") or []:
        L.append(f"  - platform_url: {js(w['platform_url'])}")
        for k in ("id", "work", "platform", "engine", "steps", "retrieved"):
            if w.get(k):
                L.append(f"    {k}: {js(w[k])}")
        if w.get("volumes"):
            L.append("    volumes:")
            for b in w["volumes"]:
                # One field per line. `- isbn: X, volume: 1` reads as a single scalar with a comma
                # in it, so the document stopped parsing at the first volume number written.
                L.append(f"      - isbn: {js(b['isbn'])}")
                if b.get("volume"):
                    L.append(f"        volume: {b['volume']}")
                if b.get("stated_title"):
                    L.append(f"        stated_title: {js(b['stated_title'])}")
                if b.get("via"):
                    L.append(f"        via: {js(b['via'])}")
        else:
            L.append("    volumes: []")
        if w.get("notes"):
            L.append("    notes:")
            for n in w["notes"]:
                L.append(f"      - {js(n)}")
    L.append("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--series", default=SERIES)
    ap.add_argument("--cache", default=str(paths.cache("editions-cache")))
    ap.add_argument("--engine", nargs="*", help="only these engines")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--retrieved", default=datetime.date.today().isoformat())
    ap.add_argument("--report", action="store_true", help="read the output and say what it holds")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    out = pathlib.Path(a.out)
    doc = (yaml.safe_load(out.read_text()) if out.exists() else None) or {}

    if a.report:
        works = doc.get("works") or []
        by = collections.Counter(w.get("platform") for w in works)
        with_books = collections.Counter(w.get("platform") for w in works if w.get("volumes"))
        print(f"works captured : {len(works)}")
        print(f"with a printed volume: {sum(1 for w in works if w.get('volumes'))}")
        print(f"ISBNs          : {len({v['isbn'] for w in works for v in (w.get('volumes') or [])})}")
        for p, n in by.most_common():
            print(f"  {p:24} {with_books[p]:4} of {n:4}")
        return 0

    wanted = gap_works(a.series)
    held = {w["platform_url"] for w in (doc.get("works") or [])}
    todo = []
    for w in wanted:
        eng = engines.engine_of(w["url"])
        if not eng or eng[0] not in ROUTES:
            continue
        if a.engine and eng[0] not in a.engine:
            continue
        if w["url"] in held:
            continue
        todo.append((w, eng[0]))
    if a.limit:
        todo = todo[:a.limit]
    print(f"outstanding: {len(todo)} work(s) across "
          f"{len({e for _, e in todo})} engine(s)")

    rows, counts = [], collections.Counter()
    for w, eng in todo:
        books, notes = ROUTES[eng](w["url"], a.cache)
        counts[eng] += 1
        counts[f"{eng}: with a volume"] += 1 if books else 0
        rows.append({"platform_url": w["url"], "id": w.get("id"), "work": w.get("work"),
                     "platform": w.get("platform"), "engine": eng,
                     "steps": engines.STEPS.get(eng, ""), "retrieved": a.retrieved,
                     "volumes": books, "notes": notes})
        print(f"  {eng:11} {str(w.get('work'))[:26]:28} {len(books)} volume(s)"
              + (f"  {notes[0][:60]}" if notes and not books else ""))

    asked = len(todo)
    got = sum(1 for r in rows if r["volumes"] or r["notes"])
    if asked and got < asked * FLOOR:
        sys.exit(f"HEALTH: {got} of {asked} works produced neither a volume nor a reason "
                 f"(under the {FLOOR:.0%} floor). That is a run that stopped rather than a "
                 "catalogue that is thin. Refusing to write.")

    doc.setdefault("source", "platform-retail-links")
    doc.setdefault("role", "print-edition-discovery")
    doc.setdefault("record_type", "platform_retail_capture")
    doc["retrieved"] = a.retrieved
    doc, added = merge(doc, rows)
    doc["counts"] = {
        "works": len(doc["works"]),
        "works_with_a_printed_volume": sum(1 for w in doc["works"] if w.get("volumes")),
        "isbns": len({v["isbn"] for w in doc["works"] for v in (w.get("volumes") or [])}),
    }
    print()
    for k, v in sorted(counts.items()):
        print(f"  {k:28} {v}")
    print(f"new rows: {added}; file holds {doc['counts']['works']} work(s), "
          f"{doc['counts']['works_with_a_printed_volume']} with a printed volume, "
          f"{doc['counts']['isbns']} ISBN(s)")
    if a.dry_run:
        print("dry run; nothing written")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(doc))
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
