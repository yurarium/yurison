#!/usr/bin/env python3
"""The capture steps' candidate list: Web漫画アンテナ's, plus what 百合ナビ lists and nothing reaches.

WHY THERE ARE TWO LISTS AND ONE OF THEM IS MERGED. Every capture step read only
`data/coverage/webcomics-works.yaml`, the antenna's 百合 tag. 百合ナビ's WEB連載 list was read as an
acceptance yardstick and never as a source of addresses, so a work it lists and the antenna does
not was never fetched: on 2026-10-09 舞ちゃんのお姉さん飼育ごはん。 on 竹コミ！ and
彗星、ロック・ユー on カドコミ were counted as missed by the very list that links their pages.

THE ANTENNA'S FILE IS NOT TOUCHED. Every work in it is cited as admitted by the antenna's tag
(`inclusion.admitted_by_tag`), and the build's scope list and the acceptance measure read it as the
antenna. This writes a separate file for the capture steps, which need only an address.

A 百合ナビ WORK IS ADDED ONLY WHERE NOTHING ALREADY REACHES IT: no candidate of that title, and no
capture holding it. A work both lists name under slightly different titles, or reached by another
route at another address, would otherwise be fetched twice and held as two rows.
"""
import argparse
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from facts.worktitle import norm_work                                    # noqa: E402


def held(sources, skip=()):
    """Folded titles every capture under `sources` holds, leaving out files whose names start with
    any prefix in `skip`; the rendered route passes its own, `rendered-`, so a work it alone holds
    is not counted as reached some other way."""
    out = set()
    for f in sorted(pathlib.Path(sources).rglob("*.yaml")):
        if any(f.name.startswith(s) for s in skip):
            continue
        try:
            d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, OSError, UnicodeDecodeError):
            continue
        if isinstance(d, dict):
            for w in d.get("works") or []:
                if isinstance(w, dict) and (w.get("work_title") or w.get("title")):
                    out.add(norm_work(str(w.get("work_title") or w.get("title"))))
    return out


def merge(base, extra, already_held):
    """`base` unchanged, then each `extra` candidate nothing named or held already reaches."""
    out = list(base)
    seen = {norm_work(c.get("title") or "") for c in base}
    added = []
    for c in extra:
        k = norm_work(c.get("title") or "")
        if not k or k in seen or k in already_held:
            continue
        seen.add(k)
        out.append(c)
        added.append(c)
    return out, added


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--antenna", default="data/coverage/webcomics-works.yaml")
    ap.add_argument("--yurinavi", default="data/coverage/yurinavi-works.yaml")
    ap.add_argument("--sources", default="data/source")
    ap.add_argument("--out", default="data/coverage/candidates.yaml")
    a = ap.parse_args(argv)

    base = (yaml.safe_load(open(a.antenna, encoding="utf-8")) or {}).get("candidates") or []
    yp = pathlib.Path(a.yurinavi)
    extra = ((yaml.safe_load(yp.read_text(encoding="utf-8")) or {}).get("candidates") or []) \
        if yp.exists() else []
    merged, added = merge(base, extra, held(a.sources))
    head = ["# What the capture steps target: webcomics-works.yaml, plus the 百合ナビ WEB連載 works",
            "# no candidate names and no capture holds. Written by adapters/candidates.py every run;",
            "# see its docstring for why the antenna's own file is left as it is.",
            ]
    body = yaml.safe_dump({"source": "adapters/candidates.py", "role": "capture-targets",
                           "candidates": merged}, sort_keys=False, allow_unicode=True, width=1000)
    pathlib.Path(a.out).write_text("\n".join(head) + "\n" + body, encoding="utf-8")
    print(f"candidates: {len(base)} from the antenna, {len(added)} added from 百合ナビ"
          + "".join(f"\n  + {c.get('title')} ({', '.join(c.get('platforms') or [])})" for c in added))
    return 0


if __name__ == "__main__":
    sys.exit(main())
