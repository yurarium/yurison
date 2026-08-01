#!/usr/bin/env python3
"""Acceptance measurement against the two yardstick sites (REQUIREMENTS §5).

The criterion: **every update listed on Web漫画アンテナ or 百合ナビ should appear in this feed over
time.** This measures it over the period the feed actually covers, rather than against each site's
whole catalogue — most of which is dormant work that is not updating at all.

Method:
  1. Take the window our feed covers (earliest to latest release we hold).
  2. From each yardstick, take the works it says updated inside that window.
  3. Check how many of those appear in our feed.

Matching is by normalised work title. 百合ナビ runs title and author together in one cell, so its
side is matched by prefix containment and is necessarily looser.

Usage:  acceptance.py
"""
import json
import pathlib
import re
import sys
from datetime import date

import yaml

sys.path.insert(0, "adapters/webcomics")
from coverage import parse  # noqa: E402

THIS_YEAR = 2026


def norm(s):
    s = re.sub(r"[​-‏‪-‮﻿]", "", s or "")
    return re.sub(r"[\s\-.=、。･・！!？?　　]", "", s.strip().lower())


def antenna_date(txt, today):
    """The antenna shows '4時間前', '7月28日' (this year) or '2025年5月23日'."""
    t = (txt or "").strip()
    if "分前" in t or "時間前" in t:
        return today
    m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", t)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{1,2})月(\d{1,2})日", t)
    if m:
        return date(THIS_YEAR, int(m.group(1)), int(m.group(2)))
    return None


def main():
    feed = json.loads(pathlib.Path("data/build/feed.json").read_text())
    rel = [r for r in feed["releases"] if r.get("web") != "promotional-sample-only"]
    lo = min(r["pub"] for r in rel)
    hi = max(r["pub"] for r in rel)
    d_lo = date(*(int(x) for x in lo.split("-")))
    d_hi = date(*(int(x) for x in hi.split("-")))
    ours = {norm(r["work"]) for r in rel}

    reg = yaml.safe_load(pathlib.Path("data/platforms.yaml").read_text())["platforms"]
    watched = {norm(p["name"]) for p in reg if p.get("watched")}

    # Works we hold but deliberately keep out of the feed. A yardstick counting these as updates is
    # a definitional disagreement, not a coverage gap, and conflating the two would misstate both.
    excluded = {norm(r["work"]) for r in feed["releases"]
                if r.get("web") == "promotional-sample-only"}
    for pc in feed.get("print_candidates") or []:
        excluded.add(norm(pc.get("work_title")))

    print(f"Feed period: {lo} → {hi}   ({(d_hi - d_lo).days + 1} days)")
    print(f"Feed holds : {len(rel)} releases across {len(ours)} distinct works\n")

    # ── Web漫画アンテナ ────────────────────────────────────────────────
    cache = pathlib.Path.home() / "workspace/webcomics-cache"
    rows = []
    for f in sorted(cache.glob("page*.html"),
                    key=lambda p: int(re.search(r"\d+", p.name).group())):
        rows += parse(f.read_text())
    in_window, seen = [], set()
    for r in rows:
        d = antenna_date(r["updated_text"], d_hi)
        if d and d_lo <= d <= d_hi and norm(r["title"]) not in seen:
            seen.add(norm(r["title"]))
            in_window.append(r)

    a_hit = [r for r in in_window if norm(r["title"]) in ours]
    a_w = [r for r in in_window if norm(r["platform"]) in watched]
    a_w_hit = [r for r in a_w if norm(r["title"]) in ours]

    print("Web漫画アンテナ 百合 tag")
    print(f"  works it lists as updating in the period : {len(in_window)}")
    print(f"  ...on a platform we watch                : {len(a_w)}")
    print(f"  ...present in our feed                   : {len(a_hit)}")
    print(f"  ACCEPTANCE, watched platforms only       : "
          f"{len(a_w_hit)}/{len(a_w)} = {100*len(a_w_hit)/max(len(a_w),1):.1f}%")
    print(f"  ACCEPTANCE, all platforms                : "
          f"{len(a_hit)}/{len(in_window)} = {100*len(a_hit)/max(len(in_window),1):.1f}%")
    miss = [r for r in a_w if norm(r["title"]) not in ours]
    excl = [r for r in miss if norm(r["title"]) in excluded]
    real = [r for r in miss if norm(r["title"]) not in excluded]
    if excl:
        print(f"  of which DELIBERATELY EXCLUDED ({len(excl)}): 試し読み-only series, not web"
              " publication (DEFINITIONS §6)")
        for r in excl[:5]:
            print(f"    - {r['title'][:38]:40} {r['platform']}")
    if real:
        print(f"  genuinely missed ({len(real)}):")
        for r in real[:12]:
            print(f"    - {r['title'][:38]:40} {r['platform']}")
    adj_w = len(a_w) - len(excl)
    print(f"  ADJUSTED (excluding deliberate exclusions)  : "
          f"{len(a_w_hit)}/{adj_w} = {100*len(a_w_hit)/max(adj_w,1):.1f}%")

    # ── 百合ナビ WEB連載 ──────────────────────────────────────────────
    yf = pathlib.Path("data/coverage/yurinavi-webyuri.yaml")
    print("\n百合ナビ WEB連載中の百合漫画")
    if not yf.exists():
        print("  (not measured — run adapters/yurinavi/webyuri.py first)")
        return
    yd = yaml.safe_load(yf.read_text()) or {}
    y_in = []
    for w in yd.get("works") or []:
        lu = str(w.get("last_update_seen") or "")
        m = re.match(r"(\d{2})-(\d{2})", lu)
        if not m:
            continue
        try:
            d = date(THIS_YEAR, int(m.group(1)), int(m.group(2)))
        except ValueError:
            continue
        if d_lo <= d <= d_hi:
            y_in.append(w)

    def y_match(raw):
        n = norm(raw)
        return any(o and (n.startswith(o) or o in n) for o in ours if len(o) > 3)

    y_hit = [w for w in y_in if y_match(w["raw"])]
    y_w = [w for w in y_in if norm(w["platform"]) in watched]
    y_w_hit = [w for w in y_w if y_match(w["raw"])]

    print(f"  works it lists as updating in the period : {len(y_in)}")
    print(f"  ...on a platform we watch                : {len(y_w)}")
    print(f"  ACCEPTANCE, watched platforms only       : "
          f"{len(y_w_hit)}/{len(y_w)} = {100*len(y_w_hit)/max(len(y_w),1):.1f}%")
    print(f"  ACCEPTANCE, all platforms                : "
          f"{len(y_hit)}/{len(y_in)} = {100*len(y_hit)/max(len(y_in),1):.1f}%")
    ymiss = [w for w in y_w if not y_match(w["raw"])]
    if ymiss:
        print(f"  missed on watched platforms ({len(ymiss)}):")
        for w in ymiss[:12]:
            print(f"    - {w['raw'][:38]:40} {w['platform']}")


if __name__ == "__main__":
    main()
