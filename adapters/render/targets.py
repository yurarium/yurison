#!/usr/bin/env python3
"""Keep `data/coverage/render-targets.yaml` current: add the listed works only a browser can reach.

WHY THIS EXISTS. The rendered route reads its works from that file, and the file was written by
hand on 2026-08-02 and never again. A work that appeared on a client-rendered platform after that
day could not be rendered at all: on 2026-10-09 nineteen works on Web漫画アンテナ's 百合 tag were
held by no capture, among them ぎるてぃらいぶらり, announced by 百合ナビ and listed by the antenna
since 2026-10-07, whose マガポケ page renders two dated chapters. The candidate list it should
follow is rewritten every run; the target list was not.

THE RULE IS THE FILE'S OWN, stated in its header: rendering is the only route, so a work another
capture already holds does not belong here. A candidate is added to a platform when one of its
addresses is on that platform's host, no work of that title is already a target there, and no
capture outside the rendered route holds it.

IT ONLY ADDS. Platform ids name the `rendered-<id>.yaml` files, and `check.py` watches for an id
that changes, so platforms and existing works are left exactly as they are. Removing a target is
a decision, and nothing here makes it.

IT EDITS THE FILE IN PLACE. A full rewrite drops the comments, and one of them is the only record
of why the ガンガンONLINE section exists. New entries are inserted at the end of each platform's
list and every other byte is left alone.
"""
import argparse
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from facts.worktitle import norm_work                                    # noqa: E402
import candidates as _candidates                                         # noqa: E402

#: An address naming one chapter rather than the work, which moves as the work publishes.
EPISODE = re.compile(r"/episodes?/|/viewer/|[?&]s$|/chapter/")


def work_address(urls, host):
    """The candidate's address on this host, the work's own page before a chapter's."""
    on = [u for u in urls if host in (u or "")]
    whole = [u for u in on if not EPISODE.search(u)]
    return (whole or on or [None])[0]


def held_elsewhere(sources):
    """Folded titles every capture outside the rendered route holds. One reading of the captures,
    `candidates.held`, so the two lists cannot disagree about what is already reached."""
    return _candidates.held(sources, skip=("rendered-",))


def additions(spec, candidates, held):
    """`{platform id: [(title, url), ...]}` to append, in the candidates' order."""
    out = {}
    for p in spec.get("platforms") or []:
        host = p.get("host") or ""
        have = {norm_work(w.get("title") or "") for w in p.get("works") or []}
        for c in candidates:
            title = c.get("title")
            url = work_address(c.get("urls") or [], host)
            if not title or not url:
                continue
            k = norm_work(title)
            if k in have or k in held:
                continue
            have.add(k)
            out.setdefault(p["id"], []).append((title, url))
    return out


def _q(s):
    """A YAML scalar the file's own style would write, quoted only where it has to be."""
    return yaml.safe_dump(s, allow_unicode=True, width=10000).strip().removesuffix("\n...").strip()


def insert(text, adds):
    """The file's text with each platform's additions appended to the end of its list."""
    lines = text.splitlines(True)
    starts = {m.group(1): i for i, l in enumerate(lines)
              for m in [re.match(r"- id: (\S+)\s*$", l)] if m}
    for pid, items in sorted(adds.items(), key=lambda kv: -starts.get(kv[0], -1)):
        i = starts.get(pid)
        if i is None:
            continue
        j = i + 1
        while j < len(lines) and not re.match(r"(- id: |#|\S)", lines[j]):
            j += 1
        # Back over blank lines so the new entries sit with the list and not after a gap.
        while j > i + 1 and not lines[j - 1].strip():
            j -= 1
        block = "".join(f"  - title: {_q(t)}\n    url: {_q(u)}\n" for t, u in items)
        lines.insert(j, block)
    return "".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--targets", default="data/coverage/render-targets.yaml")
    ap.add_argument("--candidates", default="data/coverage/candidates.yaml")
    ap.add_argument("--queue", default="data/queue/yurinavi.yaml")
    ap.add_argument("--sources", default="data/source")
    a = ap.parse_args(argv)

    path = pathlib.Path(a.targets)
    text = path.read_text(encoding="utf-8")
    spec = yaml.safe_load(text) or {}
    cands = list((yaml.safe_load(open(a.candidates, encoding="utf-8")) or {}).get("candidates") or [])
    # 百合ナビ'S ANNOUNCEMENTS TOO, which name a work the day it starts, often before the antenna.
    q = pathlib.Path(a.queue)
    if q.exists():
        for w in (yaml.safe_load(q.read_text(encoding="utf-8")) or {}).get("candidates") or []:
            if w.get("work_title") and w.get("work_url"):
                cands.append({"title": w["work_title"], "urls": [w["work_url"]]})
    adds = additions(spec, cands, held_elsewhere(a.sources))
    n = sum(len(v) for v in adds.values())
    if n:
        new = insert(text, adds)
        after = yaml.safe_load(new) or {}
        if [p.get("id") for p in after.get("platforms") or []] != \
                [p.get("id") for p in spec.get("platforms") or []]:
            sys.exit("render targets: the edit changed the platform list; refusing to write")
        path.write_text(new, encoding="utf-8")
    print(f"render targets: {n} work(s) added"
          + "".join(f"\n  {pid}: " + ", ".join(t for t, _u in items) for pid, items in adds.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
