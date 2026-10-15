#!/usr/bin/env python3
"""Keep `data/queue/cmoa-yuri.yaml` current: コミックシーモア's 百合・GL shelf, read again each week.

WHY THIS EXISTS. The shelf was captured on 2026-08-04 by a script that was never committed, and
nothing read the shop again: every work it filed under genre 37 after that day was invisible to the
print side. `adapters/cmoa.py` held every piece the capture needs, the row parser, the facet
reader, the URL builders and a tested `merge`, and only the loop around them was missing. This is
the loop.

THE SAME TWO PASSES AS THE FIRST CAPTURE. The genre listing gives every title but no publisher, and
the shop's own publisher facet partitions the same shelf so that one re-read per publisher fills
the field, about a hundred requests instead of one per work. The partition is checked against the
shelf total and the run says where they disagree.

NOTHING HELD IS DROPPED. `cmoa.merge` keeps every entry the new rows do not mention, so a work the
shop stops shelving keeps its record and its `seen` date stops moving. Titles carrying a censorship
marker are counted and never written, exactly as the first capture did.

    cmoa_shelf.py [--out data/queue/cmoa-yuri.yaml] [--cache DIR]
"""
import argparse
import datetime
import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cmoa                                                             # noqa: E402
import net                                                              # noqa: E402
import paths                                                            # noqa: E402

PAUSE = 1.6
#: Said once above the first capture's own notes, which describe 2026-08-04 and stay as its record.
HEADER = "# Refreshed weekly by adapters/cmoa_shelf.py; the notes below describe the first capture.\n"
PER_PAGE = 100
MAX_PAGES = 60


def entry(row, today, publisher=None):
    """A listing row in the document's own shape, or None where its title marks a censored edition."""
    if cmoa.censored_marker(row["title"]):
        return None
    out = {"cmoa_title_id": row["title_id"], "title": row["title"], "authors": row["authors"],
           "cmoa_author_ids": row["author_ids"], "genre": row.get("genre"),
           "label": row.get("labels") or [], "completed": bool(row.get("completed")),
           "url": row["url"], "seen": today}
    if publisher:
        out["publisher"] = publisher
        out["doujin"] = cmoa.is_doujin(publisher, row.get("labels") or ())
    return out


def pages(get, url_for, limit=MAX_PAGES):
    """`(stated total, every row)` for one listing, walked until a page comes back empty or the
    shop's own count is reached."""
    rows, stated = [], None
    for n in range(1, limit + 1):
        html = get(url_for(n)) or ""
        if stated is None:
            stated = cmoa.total(html)
        got = cmoa.rows(html)
        if not got:
            break
        rows += got
        if stated is not None and len(rows) >= stated:
            break
    return stated, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="data/queue/cmoa-yuri.yaml")
    ap.add_argument("--cache", default=str(paths.cache("cmoa-shelf")))
    a = ap.parse_args(argv)

    net.set_pause("www.cmoa.jp", PAUSE)
    get = lambda u: net.body(net.fetch(u, a.cache, max_age_days=net.AGE_FEED))  # noqa: E731
    today = datetime.date.today().isoformat()
    out = pathlib.Path(a.out)
    text = out.read_text(encoding="utf-8") if out.exists() else ""
    doc = yaml.safe_load(text) or {}
    header = HEADER + "".join(l + "\n" for l in text.splitlines()
                              if l.startswith("#") and not l.startswith(HEADER.strip()))

    stated, listed = pages(get, lambda n: cmoa.shelf_url(page=n))
    if not listed:
        sys.exit("HEALTH: the genre listing returned no rows; the markup may have moved. Not writing.")
    excluded = {}
    new = []
    for r in listed:
        e = entry(r, today)
        if e is None:
            m = cmoa.censored_marker(r["title"])
            excluded[m] = excluded.get(m, 0) + 1
            continue
        new.append(e)
    doc, added = cmoa.merge(doc, new)

    parts = cmoa.facet(get(cmoa.facet_url("publisher")) or "", "publisher")
    partitioned = 0
    for pid, name, count in parts:
        _, got = pages(get, lambda n, p=pid: cmoa.shelf_url(page=n, publisher_id=p))
        partitioned += len(got)
        doc, _ = cmoa.merge(doc, [e for e in (entry(r, today, name) for r in got) if e])
    doc["retrieved"] = today
    doc["shelf_total_reported"] = stated
    doc["excluded_by_marker"] = excluded
    doc["excluded_total"] = sum(excluded.values())
    doc["captured_total"] = len(doc.get("titles") or [])
    doc.pop("pages_captured", None)
    doc.pop("publishers_captured", None)

    body = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100)
    out.write_text(header + body, encoding="utf-8")
    gap = (stated or 0) - partitioned
    print(f"shelf states {stated}; listed {len(listed)}, {added} new; {len(parts)} publishers "
          f"partition {partitioned}" + (f" ({gap:+d} against the shelf)" if gap else "")
          + f"; {doc['captured_total']} held -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
