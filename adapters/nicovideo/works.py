#!/usr/bin/env python3
"""ニコニコ漫画 per-work episode lists, for works whose serialisation this database had not found.

WHY THIS SITS BESIDE releases.py. `releases.py` writes `work_update_dates`: the platform said this
work updated on this day, which is what a release feed needs. That record type produces no row in
the works list, so a serialisation reachable only here was invisible as a work however often it
updated. This writes `web_work_chapters`, which is the record type build.py turns into a row.

Both read the same page through the same parser. Nothing here re-derives a date or an episode list.

PARTIAL IS ASKED OF EACH PAGE, NOT ASSERTED OF THE PLATFORM. ニコニコ renders the episodes a
signed-out reader may open. For オレは男装女子じゃない！ that is all 37 of them; for 運命のヤマダ
ダダダダダダダダダ it is five, numbered 1, 2, 3, 13 and 17, with the newest called 第16話. Each
item carries the platform's own position number, so a highest position above the number of items
rendered is the page saying it left some out, and that is what `partial` records. Calling the whole
platform partial would report a complete 37-chapter run as a fraction of something longer.

NO EPISODE CARRIES A DATE, which this platform's own reader cannot see either. The work-level 更新
and 開始 dates are recorded on the work instead, so a row here states when the serialisation began
and when it last moved, and states nothing about individual chapters.

Usage:  works.py --ids data/queue/serialisation-joins.yaml --out data/source/nicovideo
"""
import argparse
import datetime
import json
import pathlib
import re
import sys

import yaml

#: The address of a work on nicovideo. Three files matched it; this is the one that owns the
#: platform.
COMIC_URL = re.compile(r"manga\.nicovideo\.jp/comic/(\d+)")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import net                                                                     # noqa: E402
import releases as nv                                                          # noqa: E402

WORK = "https://manga.nicovideo.jp/comic/{cid}"
COMIC_ID = COMIC_URL


def record(cid, html):
    """One `web_work_chapters` work record, or None where the page states no title.

    A page that parses to nothing is not an empty serialisation. It is a page we could not read,
    and returning a work with no chapters would publish that confusion as a fact about the manga.
    """
    d = nv.parse(html) or {}
    if not d.get("title"):
        return None
    eps = nv.episodes(html)
    # WHETHER THE LIST IS THE WHOLE RUN, ASKED OF THE PAGE RATHER THAN ASSUMED OF THE PLATFORM.
    # ニコニコ renders the episodes a signed-out reader may open, which for many works is all of
    # them and for others is a handful. Each item carries the platform's own position number, so
    # a highest position above the number of items rendered is the page saying it left some out:
    # 運命のヤマダダダダダダダダダダ renders five, numbered up to 17. Naming the platform partial
    # outright would report オレは男装女子じゃない！'s complete 37 chapters as a fraction of
    # something longer, which is the opposite mistake and just as wrong.
    numbered = [e["number"] for e in eps if e.get("number")]
    return {
        "work_title": d["title"],
        "author": d.get("author") or "",
        "url": WORK.format(cid=cid),
        "platform_code": str(cid),
        "started": d.get("started"),
        "updated": d.get("updated"),
        "episode_count_stated": d.get("episode_count"),
        "partial": bool(numbered) and max(numbered) > len(eps),
        "rights": nv.rights(html),
        # `[ N話 無料 ]` states how many episodes are free, and the rendered list is exactly those
        # episodes, so every chapter here is one a reader can open. Claiming `free` per chapter on
        # any weaker evidence would put paywalled chapters in the free view.
        # NO PER-CHAPTER ADDRESS, DELIBERATELY. build.py gives a row the address of its newest
        # chapter where the chapters have one, and `identity.py` anchors the work on the row's
        # address. A ニコニコ episode address changes with every instalment, so anchoring there
        # would mint a new identifier each time the work updated, which is the one thing an
        # identifier promises not to do. Without them the row keeps the work page, which is a
        # readable page and does not move. Nothing is lost: these chapters carry no date, so they
        # never enter the release feed, and `releases.py` already links the newest episode there.
        "chapters": [{"title": e["title"],
                      "access_modes": ["free"] if d.get("free_episodes") else []}
                     for e in eps],
    }


def targets(doc):
    """`{comic_id: title}` for every ニコニコ address in a joins document."""
    out = {}
    for j in (doc or {}).get("joins") or []:
        m = COMIC_ID.search(j.get("url") or "")
        if m:
            out.setdefault(m.group(1), j.get("platform_title") or j.get("title"))
    return out


def js(v):
    return json.dumps(v, ensure_ascii=False)


def write(path, works, retrieved):
    L = ["# ニコニコ漫画 per-work episode lists, for printed works whose serialisation was found",
         "# here by `adapters/serialisation/`. The platform attests these; the search that found",
         "# them attests nothing (REQUIREMENTS §1).",
         "#",
         "# PARTIAL. The page renders the episodes a signed-out reader may open and no others, so",
         "# the count is our reach rather than the length of the work.",
         "#",
         "# `rights` is the page's own copyright line. It is kept because it names the publisher,",
         "# which is the field that joined most of these to a printed book (RUNBOOK §11).",
         "source: nicovideo",
         "platform: nicovideo",
         "platform_name: ニコニコ漫画",
         f"retrieved: {retrieved}",
         "record_type: web_work_chapters",
         "identification_mode: known-works",
         f"works_resolved: {len(works)}",
         "works:"]
    for w in sorted(works, key=lambda x: x["platform_code"]):
        L.append(f"  - work_title: {js(w['work_title'])}")
        L.append(f"    author: {js(w['author'])}")
        L.append(f"    url: {js(w['url'])}")
        L.append(f"    platform_code: {js(w['platform_code'])}")
        for k in ("started", "updated", "episode_count_stated", "partial"):
            if w.get(k):
                L.append(f"    {k}: {js(w[k])}")
        if w.get("rights"):
            L.append(f"    rights: {js(w['rights'])}")
        L.append(f"    chapter_count: {len(w['chapters'])}")
        L.append("    chapters:")
        for c in w["chapters"]:
            L.append(f"      - title: {js(c['title'])}")
            if c["access_modes"]:
                L.append(f"        access_modes: {js(c['access_modes'])}")
        if not w["chapters"]:
            L[-1] = "    chapters: []"
    L.append("")
    pathlib.Path(path).write_text("\n".join(L))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ids", default="data/queue/serialisation-joins.yaml")
    ap.add_argument("--out", default="data/source/nicovideo")
    ap.add_argument("--cache", default="/tmp/yuri-serialisation-pages")
    ap.add_argument("--age", type=int, default=net.AGE_LISTING)
    a = ap.parse_args(argv)

    want = targets(yaml.safe_load(pathlib.Path(a.ids).read_text()))
    print(f"{len(want)} ニコニコ work(s) named by the joins file")
    pages = net.fetch_many([WORK.format(cid=c) for c in want], a.cache, a.age, workers=4)

    works, failed = [], []
    for cid in want:
        r = pages.get(WORK.format(cid=cid))
        rec = record(cid, r.text) if r and r.text else None
        if rec:
            works.append(rec)
        else:
            failed.append((cid, (r.error if r else "not fetched") or "no title on the page"))

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    write(out / "works.yaml", works, datetime.date.today().isoformat())
    chapters = sum(len(w["chapters"]) for w in works)
    print(f"{len(works)} work(s), {chapters} rendered episode(s) -> {out}/works.yaml")
    for cid, why in failed:
        print(f"  unread {cid}: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
