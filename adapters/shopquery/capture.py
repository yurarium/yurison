#!/usr/bin/env python3
"""Ask BOOK☆WALKER about every web work this database holds no print edition for.

WHY THIS EXISTS. `adapters/editions/capture.py` follows each work's own platform page to the shops
selling its volumes, and 534 of the 645 works with no print edition came back from it with "the
platform lists no collected volume". That is an answer about the PLATFORM. It was read as an answer
about the work, and the two are different: COMIC FUZ's page model for a series has no book field at
all, so its silence is structural and says nothing about whether 芳文社 printed the volumes. The
shop knows. `w00537` コンカフェ嬢は恋を着る is stocked on BOOK☆WALKER under ＦＵＺコミックス, marked
完結, with three volumes, and its FUZ page links to no shop at all.

WHAT THIS WRITES, AND WHERE. `data/queue/shop-query.yaml`, outside the source tree, so no row here
can become a record by accident. A retailer is Tier C (REQUIREMENTS §1). The record comes from the
national bibliography, through `adapters/madb/by_shop_query.py`, exactly as `by_isbn.py` builds one
from a shelf row's number.

WHAT IT ADMITS, WHICH IS NOTHING. Every work asked about is already in the database on its own
evidence, and stock is not a designation: DEFINITIONS §4 refuses a shop's own genre shelf as
`marketing_label`, and this is weaker than a shelf. The shop is asked what it sells and nothing
else.

THE QUERY ORDER. The author first, because an author search returning an agreeing title has agreed
on two fields at once, and then the title for the works that answered nothing. Both are recorded so
a reader can tell which question produced a row.

WHAT THE ACCESS RULES ALLOW. https://bookwalker.jp/robots.txt disallows /ex/problem/, /entry-list/,
/member/, /history/delete/, /history/parts/, /prx/ma/ and sample links under `User-agent: *`, and
/search/ is not among them. `bookwalker.py` already reads the same endpoint for completion markers.
Requests go out as the project's own identity through `adapters/net.py`, at least 1.5 s apart.

Usage:  capture.py                    every work still outstanding, resuming from the output
        capture.py --limit 40         the first 40 outstanding
        capture.py --report           read the output and say what it holds
"""
import argparse
import collections
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import net                                                                     # noqa: E402
import paths                                                                   # noqa: E402
import shop                                                                    # noqa: E402
import yaml                                                                    # noqa: E402

OUT = "data/queue/shop-query.yaml"
SERIES = "data/build/series.json"

# A shop's catalogue changes a few times a year for a given work and nothing here is a release
# feed, so a fortnight-old answer is as good as a fresh one.
AGE = net.AGE_LISTING

# POLITENESS, RAISED FOR THIS RUN. `net.PAUSE` is 1.2 s and the brief for this route asks for at
# least 1.5. Raised at import so every request this process makes to any host obeys it, which is
# safe because this module is a script and owns its own process.
net.PAUSE = max(net.PAUSE, 1.6)

# THE FLOOR, AS A SHARE OF THE WORKS ASKED ABOUT. A loop that dies halfway comes back with a
# handful of rows, writes them, and reads as a shop with thin stock. Every work asked produces a
# row, with or without a hit, so anything under this is a run that stopped.
#
# THE COUNTER-CASE, so this is not lowered later to make a run pass: a shop that changed its result
# markup would fail this legitimately, and the answer is to read the markup again.
FLOOR = 0.9


def gap_works(path=SERIES):
    """Every work with a web serialisation and no print edition, as the build states it.

    ONE PRODUCER OF THIS POPULATION. `editions/capture.py` asks the same question of the same file
    and this is the same rule, deliberately identical so that the before-and-after count for this
    route is comparable with that one's. Read from `data/build/series.json` because the question is
    what the PUBLISHED database is missing, which is the build's answer and not a source's.
    """
    doc = json.loads(pathlib.Path(path).read_text())
    out = []
    for w in doc.get("series") or []:
        if not w.get("sources") or w.get("print"):
            continue
        out.append({"id": w.get("id"), "work": w.get("work"), "author": w.get("author"),
                    "url": w.get("url"),
                    "platform": (w["sources"][0] or {}).get("platform")})
    return out


def ask(work, cache):
    """`(rows, query_kind, notes)` for one work: what the shop stocks under this name.

    Two questions, in the order that makes the answer worth most. The author query is asked first
    and its hits have agreed on the author's name AND on the title before anything else is read.
    """
    notes = []
    for kind, word in (("author", work.get("author")), ("title", work.get("work"))):
        if not word:
            continue
        r = net.fetch(shop.query_url(word), cache, AGE)
        if r.text is None:
            # 404 is how this shop says a query matched nothing, which is an answer and not a
            # failure. Anything else is a request that did not happen and is worth naming.
            notes.append(f"{kind} query answered nothing"
                         if net.is_permanent(r) else f"{kind} query failed: {r.error}")
            continue
        found = shop.pick(shop.tiles(r.text), work.get("work"))
        if found:
            return found, kind, notes
        notes.append(f"{kind} query returned no title this database recognises")
    return [], None, notes


def confirm(row, cache):
    """The shop's own credit for a hit, from the first volume's page.

    A tile carries no author, which is the absence `bookwalker-yuri.yaml` records about the shelf
    listing too, so the credit costs one request and there is no cheaper route to it. Without it
    every hit would rest on the title alone, which is the join this route refuses to make.
    """
    if not row.get("volume_urls"):
        return {}, "the tile links no volume, so no credit could be read"
    r = net.fetch(row["volume_urls"][0], cache, AGE)
    if r.text is None:
        return {}, f"volume page not read: {r.error}"
    return shop.details(r.text), None


def merge(doc, rows):
    """Fold new rows in, keeping every work the rows do not mention.

    A pass keeps what it is not looking at (REQUIREMENTS §4). Rebuilding this file from what the
    current run fetched is the failure `extract.py` and `comicfuz/releases.py` have each met, and
    it is silent: the file stays well formed and says nothing about what left it.
    """
    held = {w["work_url"]: w for w in (doc.get("works") or [])}
    added = 0
    for r in rows:
        if r["work_url"] not in held:
            added += 1
        held[r["work_url"]] = r
    return dict(doc, works=sorted(held.values(), key=lambda w: w.get("work_url") or "")), added


HEADER = """\
# What BOOK☆WALKER stocks for works this database already holds and has no print edition for.
# NOT RECORDS, and nothing here admits anything. Every work asked about was admitted on its own
# evidence before the shop was asked, the shop was asked what it sells, and a shop is Tier C,
# discovery only (REQUIREMENTS §1). data/queue/ sits outside the source tree so no row can become a
# record. adapters/madb/by_shop_query.py takes these leads to the national bibliography, and the
# bibliography's answer is what gets stored.
#
# WHY THIS SHOP. コミックシーモア states an ISBN and would be the better one to ask. Its search is
# closed to us: https://www.cmoa.jp/robots.txt carries `Disallow: /search/result/` under
# `User-agent: *`, which is the endpoint adapters/cmoa.py builds. BOOK☆WALKER's robots.txt closes
# /ex/problem/, /entry-list/, /member/, /history/delete/, /history/parts/, /prx/ma/ and sample
# links, and /search/ is not among them.
#
# `agreement` IS THE WHOLE OF THE EVIDENCE, and a title alone is not enough to make a join.
#   creator     the shop's credit for the volume shares a person with the credit this database
#               holds for the serialisation. Both fields agree, and by_shop_query.py acts on this.
#   title-only  the titles agree and no person does. RECORDED AND JOINED TO NOTHING. `トワ・エ・モア`
#               is a 1996 コンパス anthology and a 2024 講談社 series at once, and a wrong join
#               attaches one work's volumes to another where nobody can see it afterwards.
#
# `query` is which question produced the hit. `author` is the stronger one and is asked first: a
# search for the author that comes back with an agreeing title has agreed twice over.
#
# NO ISBN. BOOK☆WALKER sells files and states no number on any of them, which is why this file
# carries an imprint and a publisher instead. That is not a shortcoming of the capture; it is why
# the bibliography has to be asked by title and by a person's name here, and by ISBN elsewhere.
#
# A WORK WITH NO HIT IS AN ANSWER. `hits: []` with a note means the shop was asked and stocks
# nothing under a name this database recognises. Absence is a state (STANDING-INSTRUCTIONS §5).
"""


def render(doc):
    js = lambda v: json.dumps(v, ensure_ascii=False)                           # noqa: E731
    L = [HEADER.rstrip(), "",
         f"source: {doc['source']}", f"role: {doc['role']}",
         f"record_type: {doc['record_type']}", f"retrieved: {doc['retrieved']}",
         "key: work_url", "counts:"]
    for k, v in sorted((doc.get("counts") or {}).items()):
        L.append(f"  {k}: {v}")
    L.append("works:")
    for w in doc.get("works") or []:
        L.append(f"  - work_url: {js(w['work_url'])}")
        for k in ("id", "work", "author", "platform", "query", "retrieved"):
            if w.get(k):
                L.append(f"    {k}: {js(w[k])}")
        if w.get("hits"):
            L.append("    hits:")
            for h in w["hits"]:
                L.append(f"      - series_url: {js(h.get('series_url'))}")
                for k in ("title_listed", "shop_author", "imprint", "publisher", "agreement"):
                    if h.get(k):
                        L.append(f"        {k}: {js(h[k])}")
                if h.get("volumes_stated") is not None:
                    L.append(f"        volumes_stated: {h['volumes_stated']}")
                L.append(f"        completed_marker: {json.dumps(bool(h.get('completed_marker')))}")
        else:
            L.append("    hits: []")
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
    ap.add_argument("--cache", default=str(paths.cache("shopquery-cache")))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--retrieved", default=datetime.date.today().isoformat())
    ap.add_argument("--report", action="store_true", help="read the output and say what it holds")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    out = pathlib.Path(a.out)
    doc = (yaml.safe_load(out.read_text()) if out.exists() else None) or {}

    if a.report:
        works = doc.get("works") or []
        by = collections.Counter(h.get("agreement") for w in works for h in (w.get("hits") or []))
        print(f"works asked      : {len(works)}")
        print(f"with a hit       : {sum(1 for w in works if w.get('hits'))}")
        for k, n in by.most_common():
            print(f"  agreement {k:12} {n}")
        return 0

    held = {w["work_url"] for w in (doc.get("works") or [])}
    todo = [w for w in gap_works(a.series) if w.get("url") and w["url"] not in held]
    if a.limit:
        todo = todo[:a.limit]
    print(f"outstanding: {len(todo)} work(s)")

    rows = []
    for w in todo:
        found, kind, notes = ask(w, a.cache)
        hits = []
        for t in found:
            got, why = confirm(t, a.cache)
            if why:
                notes.append(why)
            agreement = shop.classify(got.get("author"), w.get("author"))
            hits.append({"series_url": t["series_url"], "title_listed": t["title_listed"],
                         "shop_author": got.get("author"),
                         "imprint": got.get("imprint") or t.get("imprint"),
                         "publisher": got.get("publisher"),
                         "volumes_stated": t.get("volumes_stated"),
                         "completed_marker": t.get("completed_marker"),
                         "agreement": agreement})
        rows.append({"work_url": w["url"], "id": w.get("id"), "work": w.get("work"),
                     "author": w.get("author"), "platform": w.get("platform"),
                     "query": kind, "retrieved": a.retrieved, "hits": hits, "notes": notes})
        best = ", ".join(sorted({h["agreement"] for h in hits})) or "nothing stocked"
        print(f"  {str(w.get('work'))[:26]:28} {best}")

    answered = sum(1 for r in rows if r["hits"] or r["notes"])
    if todo and answered < len(todo) * FLOOR:
        sys.exit(f"HEALTH: {answered} of {len(todo)} works produced neither a hit nor a reason "
                 f"(under the {FLOOR:.0%} floor). That is a run that stopped and not a shop with "
                 "thin stock. Refusing to write.")

    doc.setdefault("source", "bookwalker.jp")
    doc.setdefault("role", "print-edition-discovery")
    doc.setdefault("record_type", "shop_work_query")
    doc["retrieved"] = a.retrieved
    doc, added = merge(doc, rows)
    hits = [h for w in doc["works"] for h in (w.get("hits") or [])]
    doc["counts"] = {
        "works_asked": len(doc["works"]),
        "works_with_a_hit": sum(1 for w in doc["works"] if w.get("hits")),
        "hits_agreeing_on_a_creator": sum(1 for h in hits if h.get("agreement") == "creator"),
        "hits_on_the_title_alone": sum(1 for h in hits if h.get("agreement") == "title-only"),
    }
    print(f"\nnew rows: {added}; file holds {doc['counts']['works_asked']} work(s), "
          f"{doc['counts']['hits_agreeing_on_a_creator']} hit(s) agreeing on a creator, "
          f"{doc['counts']['hits_on_the_title_alone']} on the title alone")
    if a.dry_run:
        print("dry run; nothing written")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(doc))
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
