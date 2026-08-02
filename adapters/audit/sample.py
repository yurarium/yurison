#!/usr/bin/env python3
"""Pick a stratified audit sample, and state what the interface CLAIMS about each row.

Why stratified. The obvious sample — the first ten of each tab — is the newest, best-covered rows
on the most-watched platforms. Taken today it would have been five カドコミ updates out of ten, and
five of the ten works were ones already debugged the same afternoon. It would have scored well and
taught nothing. Every fault found so far has been in the tail: one-shots older than the feed window,
platforms whose coverage is partial by construction, withdrawn works, works on more than one source.

So the sample deliberately reaches into the places doubt lives, and says which stratum each row came
from so the results can be read per stratum rather than as one number.

The claims are written out BEFORE anything is fetched. That is the point of this file existing at
all: auditing my own work, the temptation is to read the platform first and then decide what the
interface "really meant". A claim recorded in advance cannot be quietly reinterpreted to match what
turns up.

Usage:  sample.py --series data/build/series.json --feed data/build/feed.json --out /tmp/audit.json
"""
import argparse, json, random


def claims_for_update(r):
    """What a reader would take from one row of the 更新 tab."""
    out = [("work", f"a work called {r['work']} exists"),
           ("date", f"it published something on {r.get('feed_date') or r['pub']}"),
           ("platform", f"that happened on {r.get('plat_name') or r.get('plat')}")]
    if (r.get("ep") or "").strip():
        out.append(("chapter", f"the instalment is called {r['ep']}"))
    if r.get("author"):
        out.append(("author", f"it is by {r['author']}"))
    m = r.get("access_modes") or []
    if r.get("free"):
        out.append(("access", "that chapter is free to read"))
    elif "free-timed" in m:
        out.append(("access", "readable now at no cost, on a ticket or a timer"))
    elif "purchase" in m:
        out.append(("access", "that chapter costs money"))
    k = r.get("kind")
    if k == "oneshot":
        out.append(("kind", "it is complete in one instalment"))
    elif k == "new-series":
        out.append(("kind", "this is the start of a new serialisation"))
    elif k == "final":
        out.append(("kind", "the series ends here"))
    if r.get("provenance") != "attested":
        out.append(("provenance", "unconfirmed — a listing site reported this, no platform did"))
    if r.get("also_on"):
        out.append(("also_on", f"also carried on {'、'.join(r['also_on'])}"))
    return out


def claims_for_work(r):
    """What a reader would take from one row of the 作品 tab."""
    out = [("work", f"a work called {r['work']} exists")]
    if r.get("author"):
        out.append(("author", f"it is by {r['author']}"))
    out.append(("length", f"it has {r['chapters']}{'+' if r.get('partial') else ''} chapters"
                          f"{' (at least)' if r.get('partial') else ''}"))
    if r.get("latest"):
        out.append(("latest", f"its most recent chapter is {r.get('latest_ep') or '?'} "
                              f"on {r['latest']}"))
    st = {"active": "it is updating — a chapter within the last 45 days",
          "slow": "it is slow — last chapter within a year",
          "dormant": "it is dormant — nothing for over a year",
          "oneshot": "it is a one-shot, complete in one instalment",
          "unknown": "no date could be read for it"}
    out.append(("state", st.get(r.get("state"), r.get("state") or "?")))
    f = r.get("free", 0) + r.get("free_timed", 0)
    if f >= r["chapters"] and r["chapters"]:
        out.append(("access", "every chapter is readable at no cost"))
    elif f:
        out.append(("access", f"{f} of its {r['chapters']} chapters are readable at no cost"))
    elif r.get("priced"):
        out.append(("access", "all of it costs money"))
    for s in r.get("sources", []):
        out.append(("source", f"readable on {s['platform']}, which holds "
                              f"{s['chapters']}{'+' if s.get('partial') else ''} chapters"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", required=True)
    ap.add_argument("--feed", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20260802)
    a = ap.parse_args()
    rnd = random.Random(a.seed)

    feed = json.load(open(a.feed))["releases"]
    series = json.load(open(a.series))["series"]
    newest = sorted(feed, key=lambda r: r.get("feed_date") or r["pub"], reverse=True)

    SUSPECT = {"少年ジャンプ+", "サンデーうぇぶり", "webアクション", "一迅プラス", "竹コミ"}
    picked, seen = [], set()

    def take(stratum, rows, n, kind):
        got = 0
        for r in rows:
            key = (kind, r["work"], r.get("plat_name") or r.get("platform"))
            if key in seen:
                continue
            seen.add(key)
            picked.append({"stratum": stratum, "kind": kind, "row": r,
                           "claims": (claims_for_update if kind == "update" else claims_for_work)(r)})
            got += 1
            if got >= n:
                return

    # Updates: the head of the feed is what most readers see, so it is not skipped — only capped.
    take("update / newest", newest, 3, "update")
    take("update / access-suspect platform",
         [r for r in newest if (r.get("plat_name") or "") in SUSPECT], 2, "update")
    take("update / unconfirmed claim",
         [r for r in feed if r.get("provenance") != "attested"], 2, "update")
    # Works: reach past the default filter, which hides exactly the states that are hardest to get
    # right — a one-shot, a dormant series, a work on several platforms with different coverage.
    take("work / newest", sorted(series, key=lambda r: r.get("latest") or "", reverse=True), 2, "work")
    take("work / multi-source", [r for r in series if len(r.get("sources") or []) > 1], 2, "work")
    take("work / one-shot", rnd.sample([r for r in series if r.get("state") == "oneshot"], 12), 2, "work")
    take("work / dormant", rnd.sample([r for r in series if r.get("state") == "dormant"], 12), 2, "work")
    take("work / partial coverage", [r for r in series if r.get("partial")], 1, "work")

    json.dump({"sample": picked}, open(a.out, "w"), ensure_ascii=False, indent=1, default=str)
    print(f"{len(picked)} rows, {sum(len(p['claims']) for p in picked)} claims")
    for p in picked:
        r = p["row"]
        print(f"\n── {p['stratum']}  [{p['kind']}]")
        print(f"   {r['work']}  ·  {r.get('plat_name') or (r.get('sources') or [{}])[0].get('platform','?')}")
        for c, txt in p["claims"]:
            print(f"     {c:11} {txt}")


if __name__ == "__main__":
    main()
