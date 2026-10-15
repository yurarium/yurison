#!/usr/bin/env python3
"""Every episode a GigaViewer series has published, read from the platform's own episode list.

WHY THIS EXISTS. A GigaViewer series feed carries what a reader can open now, and on most of these
platforms that is a window: the latest few chapters and the free opening ones. Everything that has
expired drops out of the feed, so a work that ran for three years and ended reached us as its first
two chapters, dated the year it started. 女だから、とパーティを追放されたので伝説の魔女と最強タッグを
組みました read `dormant since 2021-04-12` from サンデーうぇぶり's feed; its own episode list holds
75 parts to 2024-07-07, 73 of them past their reading window. ハナちゃん匂いかがせて read dormant
since 2022 against a list ending 最終話 on 2025-12-15. Found by the owner on 2026-10-15.

The series page draws that list from `/api/viewer/pagination_readable_products`, fifty entries a
page, newest first, every entry carrying its title, the day it opened and its status. Nothing here
is guessed: an expired entry is marked `withdrawn`, with no access mode, because the platform says
it can no longer be read, and it still counts as an instalment published on its day.

WHAT IT DOES NOT CLAIM. A withdrawn chapter is not offered to a reader as readable, free or
priced. It is evidence of length, of when the run last moved, and of how it ended.

Usage:  episode_lists.py --out data/source/gigaviewer --cache .cache/giga-lists --retrieved DATE
"""
import argparse
import glob
import json
import pathlib
import re
import sys
import urllib.error

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import series_feeds as _sf                                                # noqa: E402

PAGE = 50
LIST = "https://{host}/api/viewer/pagination_readable_products?type=episode&aggregate_id={sid}" \
       "&sort_order=desc&offset={offset}"
SERIES_ANCHOR = re.compile(r"^web:https://([^/]+)/atom/series/(\d+)$")
#: Most of a platform's series answering nothing is a refusal, not a catalogue with no episodes.
HEALTH = 0.5


def access(entry):
    """`(access_modes, withdrawn)` for one entry, from the status the platform states."""
    label = ((entry or {}).get("status") or {}).get("label")
    if label == "unpublished":
        return [], True
    if label == "is_free":
        return ["free"], False
    return (["purchase"], False) if label else ([], False)


def chapters(entries):
    """The episode list as chapter records, oldest first, which is how the other captures order."""
    out = []
    for e in reversed(entries or []):
        if not isinstance(e, dict) or not e.get("title"):
            continue
        modes, gone = access(e)
        c = {"title": str(e["title"]).strip(),
             "updated": _sf.jst_date(e.get("display_open_at") or ""),
             "url": e.get("viewer_uri")}
        if modes:
            c["access_modes"] = modes
        if gone:
            c["withdrawn"] = True
        out.append(c)
    return out


def targets(feeds, registry, hosts):
    """`{(platform id, series id): title}` from the series feeds held and the registry's anchors."""
    out = {}
    by_host = {h: pid for pid, h in hosts.items()}
    for pid, doc in feeds.items():
        for w in (doc or {}).get("works") or []:
            if w.get("series_id") and w.get("work_title"):
                out.setdefault((pid, str(w["series_id"])), w["work_title"])
    for e in registry or []:
        if e.get("merged_into"):
            continue
        for a in e.get("anchors") or []:
            m = SERIES_ANCHOR.match(str(a))
            if m and m.group(1) in by_host and e.get("title"):
                out.setdefault((by_host[m.group(1)], m.group(2)), e["title"])
    return out


def read_list(host, sid, cache):
    """Every entry of one series' list, following the pages until one comes back short."""
    entries, offset = [], 0
    while True:
        page = json.loads(_sf.fetch(LIST.format(host=host, sid=sid, offset=offset), cache))
        if not isinstance(page, list):
            break
        entries += page
        if len(page) < PAGE:
            break
        offset += PAGE
    return entries


def write(path, pid, name, works, retrieved):
    js = _sf.js
    L = ["# Every episode each series has published, from the platform's own episode list. Written by",
         "# adapters/gigaviewer/episode_lists.py; an entry the platform says can no longer be read is",
         "# `withdrawn` and carries no access mode, since it counts toward length and dates only.",
         f"source: gigaviewer", f"platform: {pid}", f"platform_name: {js(name)}",
         f"retrieved: {js(retrieved)}", "record_type: web_work_chapters",
         "identification_mode: known-works", "date_basis: stated", "date_confidence: reported",
         "works:"]
    for w in sorted(works, key=lambda x: x["series_id"]):
        L.append(f"  - work_title: {js(w['work_title'])}")
        L.append(f"    series_id: {js(w['series_id'])}")
        L.append(f"    url: {js(w['url'])}")
        L.append(f"    chapter_count: {len(w['chapters'])}")
        L.append("    chapters:" if w["chapters"] else "    chapters: []")
        for c in w["chapters"]:
            L.append(f"      - title: {js(c['title'])}")
            L.append(f"        updated: {js(str(c['updated']))}")
            if c.get("url"):
                L.append(f"        url: {js(c['url'])}")
            if c.get("access_modes"):
                L.append(f"        access_modes: {js(c['access_modes'])}")
            if c.get("withdrawn"):
                L.append("        withdrawn: true")
    L.append("")
    pathlib.Path(path).write_text("\n".join(L), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="data/source/gigaviewer")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--registry", default="data/identity/works.yaml")
    a = ap.parse_args(argv)

    plats = {p["id"]: p for p in yaml.safe_load(open("adapters/gigaviewer/platforms.yaml"))["platforms"]}
    hosts = {pid: p["host"] for pid, p in plats.items() if p.get("host")}
    feeds = {}
    for f in sorted(glob.glob(str(pathlib.Path(a.out) / "*-series-feeds.yaml"))):
        pid = pathlib.Path(f).name[: -len("-series-feeds.yaml")]
        if pid in hosts:
            feeds[pid] = yaml.safe_load(open(f, encoding="utf-8")) or {}
    reg = (yaml.safe_load(open(a.registry, encoding="utf-8")) or {}).get("works") or []
    want = targets(feeds, reg, hosts)
    print(f"{len(want)} series across {len({p for p, _ in want})} platform(s)")

    cache = pathlib.Path(a.cache).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    by_plat, failed = {}, 0
    for (pid, sid), title in sorted(want.items()):
        try:
            entries = read_list(hosts[pid], sid, cache)
        except (urllib.error.URLError, OSError, ValueError) as e:
            failed += 1
            print(f"  unread {pid} {sid} ({title}): {type(e).__name__}")
            continue
        by_plat.setdefault(pid, []).append({
            "work_title": title, "series_id": sid,
            "url": f"https://{hosts[pid]}/atom/series/{sid}", "chapters": chapters(entries)})
    if want and failed / len(want) > HEALTH:
        raise SystemExit(f"HEALTH: {failed} of {len(want)} series answered nothing. Refusing to write.")
    out = pathlib.Path(a.out)
    for pid, works in sorted(by_plat.items()):
        path = out / f"{pid}-episode-lists.yaml"
        reached = {w["series_id"] for w in works}
        # `carry_over` hands a kept work's chapters back as `episodes`, the key its own writer reads.
        kept = [dict(w, chapters=w.pop("episodes", None) or []) for w in _sf.carry_over(path, reached)]
        write(path, pid, plats[pid].get("name") or pid, works + kept, a.retrieved)
        n = sum(len(w["chapters"]) for w in works)
        gone = sum(1 for w in works for c in w["chapters"] if c.get("withdrawn"))
        print(f"  {pid:22} {len(works):4} series, {n:6} episodes, {gone:6} withdrawn")
    return 0


if __name__ == "__main__":
    sys.exit(main())
