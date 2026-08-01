#!/usr/bin/env python3
"""Build the classification review queue (DEFINITIONS §3).

`content_tier` is the one field in this project that cannot be derived. It is an interpretive
judgment about what a work contains, and every automatic route to it is a category error: a
publisher's 百合 tag is `marketing_label` by definition, an aggregator's tag is somebody's opinion,
and "it was in 百合姫" is the venue's identity, not the work's.

So the queue does not guess. What it does is make the human judgment cheap by putting everything
bearing on it in one place, and by ordering the works so the ones worth doing first come first.

Ordering. Two things make a work worth classifying early:

  - **Reach** — a long-running series is more of the database than a single volume, and its tier
    decides more of what a reader sees.
  - **Doubt** — a work whose only qualification is its imprint has never been examined. One that
    several independent sources tag 百合 is likely to be a quick confirmation.

So the queue sorts by volume count within evidence bands, weakest evidence first: the works where
the answer is least obvious are the ones where a human adds most.

Each row carries `content_tier: ""` and a `basis` skeleton. A filled row is moved into
data/overlay/<work_id>.yaml, which build.py already prefers over every source. Nothing here is
read by the build — data/queue/ sits outside the source tree precisely so that a candidate cannot
become a record by accident (REQUIREMENTS §1).

Usage:  queue.py --out data/queue --retrieved 2026-08-01
"""
import argparse, glob, json, pathlib, re, sys, unicodedata
from collections import Counter

import yaml

TIERS = ["canonical-romance", "strongly-implied", "class-s", "incidental"]


def norm(s):
    s = re.sub(r"[​-‏‪-‮﻿]", "", s or "")
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"""[\s\-.=、。･・!?,:;'"“”‘’()\[\]{}「」『』【】〈〉《》〔〕~〜_/\\|+*&#@]""",
                  "", s.strip().lower())


def js(v):
    return json.dumps(v, ensure_ascii=False)


def gather_tags():
    """Third-party and platform tags, by normalised title.

    These are evidence TOWARD a tier and never a tier themselves — a reader deciding whether
    「秘密の関係」 means a romance still has to read the work. They are here to tell a classifier
    where to look first, not what to conclude.
    """
    tags = {}

    def add(title, source, vals):
        if not title or not vals:
            return
        tags.setdefault(norm(title), {}).setdefault(source, set()).update(
            v for v in vals if v)

    kf = pathlib.Path("data/source/kadokomi/chapters.yaml")
    if kf.exists():
        for w in (yaml.safe_load(kf.read_text()) or {}).get("works") or []:
            add(w.get("work_title"), "kadokomi", w.get("tags") or [])
    for f in glob.glob("data/source/gigaviewer/*-series.yaml"):
        for w in (yaml.safe_load(open(f)) or {}).get("series") or []:
            add(w.get("title"), "gigaviewer", w.get("genres") or [])
    cf = pathlib.Path("data/source/comparators/claims.yaml")
    if cf.exists():
        for c in (yaml.safe_load(cf.read_text()) or {}).get("updates") or []:
            add(c.get("work"), "webcomics.jp", c.get("listing_tags") or [])
    return tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    a = ap.parse_args()

    wf = pathlib.Path("data/build/works.json")
    if not wf.exists():
        sys.exit("data/build/works.json not found — run build.py first")
    doc = json.loads(wf.read_text())
    works = doc["works"] if isinstance(doc, dict) else doc

    done = set()
    ov = pathlib.Path("data/overlay")
    if ov.exists():
        for f in ov.glob("*.yaml"):
            d = yaml.safe_load(f.read_text()) or {}
            if d.get("content_tier"):
                done.add(d.get("work_id"))

    tags = gather_tags()
    rows = []
    for w in works:
        if w.get("content_tier") or w["work_id"] in done:
            continue
        t = w.get("title") or {}
        title = t.get("ja") if isinstance(t, dict) else t
        ev = tags.get(norm(title or ""), {})
        # How much independent corroboration exists that this is yuri at all. The imprint is not
        # counted: it qualifies every work in this catalogue and so distinguishes none of them.
        corroboration = sum(1 for src, vs in ev.items()
                            if {"百合", "GL", "ガールズラブ"} & vs)
        rows.append({
            "work_id": w["work_id"],
            "title": title,
            "yomi": t.get("yomi") if isinstance(t, dict) else "",
            "creator": w.get("creator", ""),
            "publisher": w.get("publisher", ""),
            "imprint": w.get("imprint", ""),
            "volumes": w.get("volume_count", 0),
            "first_published": (w.get("first_publication") or {}).get("date", ""),
            "marketing_label": w.get("marketing_label", ""),
            "tags": {src: sorted(vs) for src, vs in sorted(ev.items())},
            "corroboration": corroboration,
        })

    # Weakest evidence first, then longest series first inside each band.
    rows.sort(key=lambda r: (r["corroboration"], -r["volumes"], r["title"] or ""))
    if a.limit:
        rows = rows[: a.limit]

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = ["# CLASSIFICATION REVIEW QUEUE — content_tier (DEFINITIONS §3).",
         "#",
         "# NOT A RECORD, and not read by the build. data/queue/ sits outside the source tree so",
         "# that nothing here can become a record by accident (REQUIREMENTS §1).",
         "#",
         "# content_tier cannot be derived. A publisher's 百合 tag is marketing_label by",
         "# definition; an aggregator's tag is an opinion; 'serialised in 百合姫' is the venue's",
         "# identity, not the work's. Everything below is evidence pointing at where to look —",
         "# never at what to conclude.",
         "#",
         "# To classify: fill content_tier with one of",
         f"#   {' | '.join(TIERS)}",
         "# and complete the basis, then move the entry to data/overlay/<work_id>.yaml, which the",
         "# build prefers over every source. class-s on a post-2000 work needs justifying in the",
         "# basis note (DEFINITIONS §3).",
         "#",
         "# Ordered weakest-evidence-first, longest series first within each band: the works with",
         "# no corroboration beyond their imprint are the ones a human adds most to.",
         "source: derived", "role: review-queue", f"retrieved: {a.retrieved}",
         "record_type: classification_queue",
         f"unclassified_total: {len(rows)}", "works:"]
    for r in rows:
        L.append(f"  - work_id: {js(r['work_id'])}")
        L.append(f"    title: {js(r['title'])}")
        if r["yomi"]:
            L.append(f"    yomi: {js(r['yomi'])}")
        L.append(f"    creator: {js(r['creator'])}")
        L.append(f"    imprint: {js(r['imprint'])}")
        L.append(f"    volumes: {r['volumes']}")
        L.append(f"    first_published: {js(r['first_published'])}")
        L.append(f"    marketing_label: {js(r['marketing_label'])}")
        if r["tags"]:
            L.append("    evidence_tags:   # toward a tier, never a tier")
            for src, vs in r["tags"].items():
                L.append(f"      {src}: {js(vs)}")
        else:
            L.append("    evidence_tags: {}   # nothing beyond the imprint")
        L.append('    content_tier: ""   # ' + " | ".join(TIERS))
        L.append("    content_tier_basis:")
        L.append('      source: ""       # who says so — a Japanese source (REQUIREMENTS §1)')
        L.append('      url: ""')
        L.append(f'      retrieved: ""')
        L.append('      note: ""         # what in the work supports this')
    L.append("")
    (out / "classification.yaml").write_text("\n".join(L))

    bands = Counter(r["corroboration"] for r in rows)
    print(f"unclassified works      : {len(rows)}")
    print(f"already classified      : {len(done)}")
    print(f"corroboration bands     : "
          + ", ".join(f"{k} source(s): {v}" for k, v in sorted(bands.items())))
    print(f"with any evidence tags  : {sum(1 for r in rows if r['tags'])}")
    print(f"written                 : {out}/classification.yaml")


if __name__ == "__main__":
    main()
