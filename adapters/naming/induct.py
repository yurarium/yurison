#!/usr/bin/env python3
"""Mint identifiers for web serialisations awaiting one, and hold back any that may be a work we have.

WHY THIS EXISTS. The naming job used to induct these itself: it read the registry, searched it for
the title, fetched the chapter page for its series feed and wrote the entry. Each step is
bookkeeping with a fixed answer, and doing it inside the job meant handing Claude a YAML file of
twenty thousand lines to search. This does it the same way every time, and the job is left with the
one thing that needs reading and judgement, the English name.

WHAT IT MINTS. A row awaiting an identifier that has a web address, that nobody has ruled on in
`data/queue/unheld-works.yaml`, and that resembles no work the store holds. Its anchors are its
addresses as `web:` anchors. A GigaViewer chapter address (`/episode/<n>`) links its own series feed
on the page, and that feed is attached too, with the page cited, so later chapters arrive under the
work instead of awaiting another identifier.

WHAT IT HOLDS BACK, for a person, and says why: a row whose title folds to one the store holds, or
starts the way one does by the same author. Those are the cases where minting would make a second
record of a work that moved platform or was retitled, and a second record is harder to undo than a
work left waiting a day. An anchor another entry already holds is also refused, as mint.py refuses.

    induct.py [--awaiting data/build/awaiting-identifier.json] [--registry data/identity/works.yaml]
              [--offline]
"""
import argparse
import datetime
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import feedgap                                                          # noqa: E402
from mint import ID                                                     # noqa: E402

EPISODE = re.compile(r"^(https://[^/]+)/episode/\d+")
SERIES_FEED = re.compile(r'href="(https://[^"]+/atom/series/(\d+))"')
#: How much of a title two must share, by the same author, before one may be the other.
SHARED = 5


def fold(s):
    return feedgap.textnorm.norm(s or "")


def resembles(row, held):
    """`[(id, title, why)]` for the held works this row may be."""
    t, author = fold(row.get("work")), (row.get("author") or "").strip()
    out = []
    for h in held:
        ht = fold(h.get("work"))
        if not ht or not str(h.get("id") or "").startswith("w"):
            continue
        if ht == t:
            out.append((h["id"], h.get("work"), "the same title"))
        elif author and author == (h.get("author") or "").strip() and len(t) >= SHARED \
                and ht[:SHARED] == t[:SHARED]:
            out.append((h["id"], h.get("work"), f"the same author and a title starting {t[:SHARED]}"))
    return out


def inductable(rows, ruled):
    """The awaiting rows this may consider: a web address, a title, and no ruling."""
    return [r for r in rows or [] if r.get("addresses") and r.get("work")
            and fold(r.get("work")) not in ruled]


def series_feed(address, page):
    """`(feed url, series id)` the chapter page at `address` links, or None."""
    m = EPISODE.match(address or "")
    if not m or not page:
        return None
    for href, sid in SERIES_FEED.findall(page):
        if href.startswith(m.group(1) + "/"):
            return href, sid
    return None


def entry(wid, row, feeds, today):
    """One registry entry for `row`; `feeds` is `{chapter address: (feed url, series id)}`."""
    anchors = sorted(row["addresses"])
    lines = [f"  - id: {wid}", f"    title: {json.dumps(row['work'], ensure_ascii=False)}",
             "    anchors:"]
    extra = [(a, *feeds[a]) for a in anchors if a in feeds]
    lines += [f'      - "web:{a}"' for a in anchors]
    lines += [f'      - "web:{f}"' for _, f, _ in extra if f not in anchors]
    if extra:
        lines.append("    attached:")
        for a, f, sid in extra:
            basis = (f"the chapter page at {a} links its own series feed at {f}, so the platform "
                     f"places this chapter in series {sid}")
            lines += [f'      - anchor: "web:{f}"', f"        basis: {json.dumps(basis)}",
                      f"        retrieved: {today}"]
    return "\n".join(lines) + "\n"


def induct(text, rows, held, pages, today):
    """`(new registry text, [(id, title)], [(title, why)])`.

    `pages` is `{address: html or None}` for the chapter pages already fetched.
    """
    taken = set(re.findall(r'"(web:[^"]+)"', text))
    n = max((int(x) for x in ID.findall(text)), default=0)
    block, made, doubts = [], [], []
    for r in rows:
        like = resembles(r, held)
        if like:
            doubts.append((r["work"], "; ".join(f"{i} {t!r}, {why}" for i, t, why in like)))
            continue
        if any(f"web:{a}" in taken for a in r["addresses"]):
            doubts.append((r["work"], "an address is already another work's anchor"))
            continue
        feeds = {a: f for a in r["addresses"] if (f := series_feed(a, pages.get(a)))}
        if any(f"web:{f}" in taken for f, _ in feeds.values()):
            doubts.append((r["work"], "its series feed is already another work's anchor"))
            continue
        n += 1
        wid = f"w{n:05d}"
        block.append(entry(wid, r, feeds, today))
        taken.update(f"web:{a}" for a in r["addresses"])
        taken.update(f"web:{f}" for f, _ in feeds.values())
        made.append((wid, r["work"]))
    if not block:
        return text, [], doubts
    at = text.find("\nrelated:\n")
    at = len(text) if at < 0 else at + 1
    return text[:at] + "".join(block) + text[at:], made, doubts


def fetch_pages(rows, offline):
    """`{chapter address: html or None}` for every GigaViewer chapter address in `rows`."""
    import net
    import paths
    cache = paths.cache("naming-pages")
    out = {}
    for r in rows:
        for a in r["addresses"]:
            if EPISODE.match(a):
                res = net.cached(a, cache) if offline else net.fetch(a, cache, max_age_days=7)
                out[a] = res.text if res else None
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--awaiting", default="data/build/awaiting-identifier.json")
    ap.add_argument("--registry", default="data/identity/works.yaml")
    ap.add_argument("--offline", action="store_true", help="read chapter pages from the cache only")
    a = ap.parse_args(argv)

    import population
    src = pathlib.Path(a.awaiting)
    rows = (json.loads(src.read_text(encoding="utf-8")).get("works") or []) if src.exists() else []
    rows = inductable(rows, feedgap.rulings())
    held = population.series(None) if rows else []
    reg = pathlib.Path(a.registry)
    text, made, doubts = induct(reg.read_text(encoding="utf-8"), rows, held,
                                fetch_pages(rows, a.offline), datetime.date.today().isoformat())
    if made:
        reg.write_text(text, encoding="utf-8")
    print(f"{len(made)} web work(s) inducted, {len(doubts)} held for a person")
    for wid, title in made:
        print(f"  {wid} {title}")
    for title, why in doubts:
        print(f"  held: {title}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
