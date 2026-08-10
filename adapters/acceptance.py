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
import datetime

FEED_DAYS = 60

import json
import unicodedata
import pathlib
import re
import sys
from datetime import date

import yaml

sys.path.insert(0, "adapters/webcomics")
from coverage import parse  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paths

THIS_YEAR = 2026


def norm(s):
    s = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", s or "")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"""[\s\-.=、。･・!?,:;'"“”‘’()\[\]{}「」『』【】〈〉《》〔〕~〜_/\\|+*&#@]""",
                  "", s.strip().lower())


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
    # Collected as we go and returned, so the floors below compare against what was actually
    # measured rather than re-deriving it and risking the two disagreeing.
    measured = {}
    feed = json.loads(pathlib.Path("data/build/feed.json").read_text())
    rel = [r for r in feed["releases"] if r.get("web") != "promotional-sample-only"]
    # The window the feed TARGETS, not the extent of what happens to be in it. Late-discovered
    # works carry their true publication date — one from 2026-05-14 — and deriving the period from
    # the minimum turned that single row into a 20-day extension of the measurement, against which
    # nothing else was covered. Acceptance fell from 100% to 94% without any coverage changing.
    hi = max(r["pub"] for r in rel)
    lo = max(min(r["pub"] for r in rel),
             str(datetime.date.fromisoformat(hi) - datetime.timedelta(days=FEED_DAYS)))
    d_lo = date(*(int(x) for x in lo.split("-")))
    d_hi = date(*(int(x) for x in hi.split("-")))
    ours = {norm(r["work"]) for r in rel}

    reg = yaml.safe_load(pathlib.Path("data/platforms.yaml").read_text())["platforms"]
    watched = set()
    for p_ in reg:
        if p_.get("watched"):
            watched.add(norm(p_["name"]))
            watched.update(norm(a) for a in p_.get("aliases") or [])

    # Works we hold but deliberately keep out of the feed. A yardstick counting these as updates is
    # a definitional disagreement, not a coverage gap, and conflating the two would misstate both.
    excluded = {norm(r["work"]) for r in feed["releases"]
                if r.get("web") == "promotional-sample-only"}
    # Works held back pending the adult-content review are excluded ON PURPOSE, so a yardstick
    # listing one is a definitional disagreement rather than coverage we lack. Counting them as
    # misses dropped 百合ナビ from 97.4% to 93.5% and read as a regression, which is exactly the
    # conflation the comment above warns against.
    for wf in sorted(pathlib.Path("data/source").rglob("withheld.yaml")):
        for w in (yaml.safe_load(wf.read_text()) or {}).get("works") or []:
            if w.get("work_title"):
                excluded.add(norm(w["work_title"]))
    for pc in feed.get("print_candidates") or []:
        excluded.add(norm(pc.get("work_title")))
    # Works the platform's own full chapter history contradicts. A yardstick reporting an update
    # the publisher's own feed does not show is not coverage we lack — we fetched the history and
    # it disagrees. Counted apart from both hits and misses, and named, so the disagreement is
    # visible rather than absorbed into a percentage.
    contradicted = {norm(c["work"]): c for c in feed.get("contradicted") or []}

    print(f"Feed period: {lo} → {hi}   ({(d_hi - d_lo).days + 1} days)")
    print(f"Feed holds : {len(rel)} releases across {len(ours)} distinct works\n")

    # ── Web漫画アンテナ ────────────────────────────────────────────────
    cache = paths.cache("webcomics-cache")
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
    contra = [r for r in miss if norm(r["title"]) in contradicted
              and norm(r["title"]) not in excluded]
    real = [r for r in miss if norm(r["title"]) not in excluded
            and norm(r["title"]) not in contradicted]
    if excl:
        print(f"  of which DELIBERATELY EXCLUDED ({len(excl)}): 試し読み-only series, not web"
              " publication (DEFINITIONS §6)")
        for r in excl[:5]:
            print(f"    - {r['title'][:38]:40} {r['platform']}")
    if contra:
        print(f"  of which CONTRADICTED ({len(contra)}): the platform's own chapter history shows "
              "no such update")
        for r in contra[:5]:
            c = contradicted[norm(r["title"])]
            print(f"    - {r['title'][:34]:36} claimed {c['claimed']}, platform's latest "
                  f"{c['platform_latest']} ({c['chapters_held']} chapters held)")
    if real:
        print(f"  genuinely missed ({len(real)}):")
        for r in real[:12]:
            print(f"    - {r['title'][:38]:40} {r['platform']}")
    adj_w = len(a_w) - len(excl) - len(contra)
    # A RATE OVER AN EMPTY DENOMINATOR IS NOT 0%, IT IS NO MEASUREMENT. `max(adj_w, 1)` turned
    # 0/0 into 0.0%, which is below every floor, so a run that read no listing at all failed in
    # the same words as a run whose coverage had collapsed. CI has never read this listing: the
    # cache holds pages the runner could not fetch, and the pass that fills it reported a clean
    # zero because its health check sat below an `if not rows: break`.
    if not rows:
        measured["webcomics adjusted"] = None
        print(f"  ADJUSTED : not measured. {cache} holds no page this pass could read, so there "
              f"is no listing to compare the feed against. This is not 0% coverage.")
    else:
        measured["webcomics adjusted"] = 100 * len(a_w_hit) / max(adj_w, 1)
        print(f"  ADJUSTED (excluding deliberate exclusions and contradictions) : "
              f"{len(a_w_hit)}/{adj_w} = {measured['webcomics adjusted']:.1f}%")

    # ── 百合ナビ WEB連載 ──────────────────────────────────────────────
    yf = pathlib.Path("data/coverage/yurinavi-webyuri.yaml")
    print("\n百合ナビ WEB連載中の百合漫画")
    if not yf.exists():
        print("  (not measured — run adapters/yurinavi/webyuri.py first)")
        return measured
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
        """百合ナビ runs title and author together, so match on our title being a PREFIX of the
        cell. The previous version also required len(title) > 3, which silently excluded short
        Japanese titles — 創る庭 normalises to three characters and was reported as a miss while
        sitting in the feed."""
        n = norm(raw)
        return any(o and n.startswith(o) for o in ours if len(o) >= 2)

    y_hit = [w for w in y_in if y_match(w["raw"])]
    # Deliberately excluded works are not a coverage gap here either. The webcomics measure
    # already subtracts them; this one counted them as misses, so withholding five works read as
    # 百合ナビ falling from 97.4% to 93.5%.
    y_in = [w for w in y_in if not any(e and e in norm(w["raw"]) for e in excluded)]
    y_hit = [w for w in y_in if y_match(w["raw"])]
    y_w = [w for w in y_in if norm(w["platform"]) in watched]
    y_w_hit = [w for w in y_w if y_match(w["raw"])]

    print(f"  works it lists as updating in the period : {len(y_in)}")
    print(f"  ...on a platform we watch                : {len(y_w)}")
    measured["yurinavi watched"] = 100 * len(y_w_hit) / max(len(y_w), 1)
    print(f"  ACCEPTANCE, watched platforms only       : "
          f"{len(y_w_hit)}/{len(y_w)} = {measured['yurinavi watched']:.1f}%")
    print(f"  ACCEPTANCE, all platforms                : "
          f"{len(y_hit)}/{len(y_in)} = {100*len(y_hit)/max(len(y_in),1):.1f}%")
    ymiss = [w for w in y_w if not y_match(w["raw"])]
    if ymiss:
        print(f"  missed on watched platforms ({len(ymiss)}):")
        for w in ymiss[:12]:
            print(f"    - {w['raw'][:38]:40} {w['platform']}")
    return measured


# ── This is a TEST, not only a report ──────────────────────────────────────────────────────────
#
# It printed percentages and always exited 0, so ./test.py counted it as a suite while it asserted
# nothing: coverage could have fallen to zero and the run would still have been green. That is the
# vacuous-green shape this project keeps meeting, and the runner's --canary pass named it.
#
# The floors below are budgets, not targets. They record what was measured on a green run and
# ratchet the same way docs/budgets.json does: coverage falling means a source stopped being read,
# which is exactly the silent regression an acceptance measure exists to catch. Raising a floor is
# a decision to be argued in a commit message; lowering one by hand is the same.
FLOORS = {
    "webcomics adjusted": 90.0,      # measured 92.5
    "yurinavi watched": 94.0,        # measured 97.4
}


def _assert_floors(measured):
    """Compare each measured percentage against its floor. Returns the failures."""
    bad = []
    for name, floor in FLOORS.items():
        got = measured.get(name, KeyError)
        # NOT MEASURED IS NOT A FAILURE, AND NOT SILENT EITHER. A floor compares a measurement;
        # where none was taken there is nothing to compare, and reporting the worst possible value
        # would say coverage collapsed when the truth is that the listing was never read. It is
        # printed loudly by the pass above. A measure the pass forgot to record entirely is still
        # a failure, which is what tells the two apart.
        if got is KeyError:
            bad.append(f"{name}: the pass recorded no value at all, so the floor could not be "
                       f"checked and nothing said why")
        elif got is None:
            continue
        elif got < floor:
            bad.append(f"{name}: {got:.1f}% is below the floor of {floor:.1f}%")
    return bad


if __name__ == "__main__":
    import os
    measured = main() or {}
    failures = _assert_floors(measured)
    if os.environ.get("YURA_CANARY") == "1":
        # Inverted: the floors are raised past anything achievable, so a suite that really compares
        # them must fail. Passing here would mean the comparison is not happening.
        FLOORS = {k: 100.1 for k in FLOORS}
        if _assert_floors(measured):
            print("CANARY-PROVEN")
            sys.exit(0)
        print("VACUOUS: the coverage floors are not actually compared")
        sys.exit(2)
    if failures:
        print("\nACCEPTANCE FAILED:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    print("\nacceptance floors hold")
