#!/usr/bin/env python3
"""Combine the coverage yardsticks into one ranked gap (REQUIREMENTS §5).

The acceptance criterion is the **union** of Web漫画アンテナ and 百合ナビ, and the two differ in
kind rather than degree:

  Web漫画アンテナ   broad, crowd-tagged, ~1,500 works over ~96 platforms.
  百合ナビ WEB連載   hand-maintained, ~130 works over ~19 platforms.

**Neither is a precision filter.** The antenna is crowd-tagged. 百合ナビ's list is human-maintained
but its inclusion standards are traditionally loose — it dates from a period with far less yuri
being published, when posting about a work was cheap. So being listed by either is evidence that a
work EXISTS and where, and is not evidence about its content. Both stay strictly Tier C discovery,
and neither listing may be cited toward `content_tier` (DEFINITIONS §5).

Neither alone is the target either: the criterion is their union. This merges them by platform and
ranks the gap by listed works, which is the order worth working in.

Usage:  coverage_union.py --out data/coverage
"""
import argparse, json, pathlib, re
from collections import defaultdict

import yaml


def norm(s):
    # Strip zero-width and bidi control characters: the antenna emits platform names carrying
    # U+200E/U+200F (竹コミ‎‏‎), which are invisible and silently break every comparison.
    s = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", s or "")
    return re.sub(r"[\s\-.=、。･・！!？?　]", "", s.strip().lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/coverage")
    a = ap.parse_args()
    out = pathlib.Path(a.out)

    plats = defaultdict(lambda: {"antenna": 0, "curated": 0, "watched": False, "names": set()})

    f = out / "webcomics-gap.yaml"
    if f.exists():
        d = yaml.safe_load(f.read_text()) or {}
        # webcomics-gap lists only UNWATCHED platforms, so anything here is by definition a gap.
        for p in d.get("platforms_missing") or []:
            k = norm(p["platform"])
            plats[k]["antenna"] += p["works"]
            plats[k]["names"].add(p["platform"])

    f = out / "yurinavi-webyuri.yaml"
    if f.exists():
        d = yaml.safe_load(f.read_text()) or {}
        for p in d.get("platforms") or []:
            k = norm(p["platform"])
            plats[k]["curated"] += p["works"]
            plats[k]["watched"] = plats[k]["watched"] or bool(p.get("watched"))
            plats[k]["names"].add(p["platform"])

    gaps = {k: v for k, v in plats.items() if not v["watched"]}
    # Ranked on listed works, unweighted. An earlier version weighted the curated list 4x on the
    # assumption that hand-curation meant higher precision; it does not here, so the weighting was
    # removed rather than retuned. Appearing on both lists is still a mild signal that a platform
    # genuinely carries yuri, so it breaks ties.
    ranked = sorted(gaps.items(),
                    key=lambda kv: (-(kv[1]["antenna"] + kv[1]["curated"]),
                                    -min(kv[1]["antenna"], kv[1]["curated"])))

    L = ["# COMBINED COVERAGE GAP — union of both yardsticks, ranked by listed works.",
         "#",
         "# NEITHER list is a precision filter. The antenna is crowd-tagged; 百合ナビ's is",
         "# hand-maintained but traditionally loose about inclusion, dating from a time when far",
         "# less yuri was published. Being listed says a work exists and where — nothing about its",
         "# content. Tier C discovery only; not citable toward content_tier.",
         "record_type: coverage_union", "platforms:"]
    for k, v in ranked:
        name = sorted(v["names"], key=len)[0]
        L.append(f"  - platform: {json.dumps(name, ensure_ascii=False)}")
        L.append(f"    antenna_works: {v['antenna']}")
        L.append(f"    curated_works: {v['curated']}")
    L.append("")
    (out / "union-gap.yaml").write_text("\n".join(L))

    print(f"{len(gaps)} unwatched platforms across both yardsticks\n")
    print(f"  {'platform':22} {'antenna':>8} {'curated':>8}")
    for k, v in ranked[:14]:
        name = sorted(v["names"], key=len)[0]
        print(f"  {name:22} {v['antenna']:>8} {v['curated']:>8}")


if __name__ == "__main__":
    main()
