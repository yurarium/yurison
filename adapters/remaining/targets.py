#!/usr/bin/env python3
"""Write `data/coverage/remaining.yaml`: the listed works no capture holds, for the remaining route.

WHY THIS EXISTS. `remaining/releases.py` tries every route it has against the works nothing else
reached, and read them from a list derived by hand on 2026-08-02 and never again. By 2026-10-15
sixty-three of its seventy works were held by a platform capture, and ninety-three works listed
since were held by nothing and asked by nothing.

THE RULE. A candidate belongs here when it has an address on a host no dedicated adapter covers
(`dedicated.covers`, which `remaining/releases.py` honours too) and no capture holds it at that
address. One reading of the captures, `candidates.held_at`, so this list and the candidate list
cannot disagree about what is already reached.

IT DOES NOT READ ITS OWN ROUTE'S OUTPUT. `webpages/remaining.yaml` is what this list drives, so a
work it reached would drop out of the list the next run and its chapters would stop being
refreshed, and the run after that it would be back (memory: a filter must not read its own
output). That capture is skipped when reading what is held.

    targets.py [--candidates data/coverage/candidates.yaml] [--out data/coverage/remaining.yaml]
"""
import argparse
import datetime
import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import candidates as _candidates                                         # noqa: E402
from facts import sources as _sources                                    # noqa: E402
import dedicated                                                         # noqa: E402
from facts.worktitle import norm_work                                    # noqa: E402

#: The capture this list drives, left out of what counts as held.
OWN = ("remaining",)


def platform_of(cand, url):
    """The platform name the candidate gives beside this address, or its first one."""
    urls, plats = cand.get("urls") or [], cand.get("platforms") or []
    if len(urls) == len(plats) and url in urls:
        return plats[urls.index(url)]
    return plats[0] if plats else ""


def targets(cands, held, covered=dedicated.covers):
    """`[{title, platform, url}]` for each candidate no capture holds on a host nothing else reads.

    `held` is `{folded title: {address}}`. A work held at an address that is a different work's page
    on the same site is still unheld here, which is the same test the candidate list applies.
    """
    out = []
    for c in cands:
        # NOT A SOURCE IS NOT A TARGET. ダ・ヴィンチニュース runs 試し読み of finished books and was
        # ruled out on 2026-08-10, and this pass read its page for 君のためのカーテンコール all the
        # same, since the candidate list carries whatever the antenna links.
        urls = [u for u in c.get("urls") or [] if u and not covered(u) and not _sources.not_a_source(u)]
        if not urls or not c.get("title"):
            continue
        own = {_candidates.address(u) for u in urls}
        # REACHED unless every address holding the title is provably another work's page. An
        # address with no work id, another site, or none at all cannot be told apart, so it reaches.
        at = held.get(norm_work(c["title"])) or set()
        if any(not all(_candidates.another_page(a, o) for o in own) for a in at):
            continue
        out.append({"title": c["title"], "platform": platform_of(c, urls[0]), "url": urls[0]})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--candidates", default="data/coverage/candidates.yaml")
    ap.add_argument("--sources", default="data/source")
    ap.add_argument("--out", default="data/coverage/remaining.yaml")
    a = ap.parse_args(argv)

    cands = (yaml.safe_load(pathlib.Path(a.candidates).read_text(encoding="utf-8")) or {}).get(
        "candidates") or []
    rows = targets(cands, _candidates.held_at(a.sources, skip=OWN))
    js = lambda v: json.dumps(v, ensure_ascii=False)                        # noqa: E731
    L = ["# The listed works no capture holds, on hosts no dedicated adapter reads. Rewritten each",
         "# run by adapters/remaining/targets.py from the candidate list; see its docstring.",
         "source: derived", "role: remaining-works",
         f"retrieved: {datetime.date.today().isoformat()}", "works:"]
    for r in rows:
        L += [f"- title: {js(r['title'])}", f"  platform: {js(r['platform'])}", f"  url: {js(r['url'])}"]
    L.append("")
    pathlib.Path(a.out).write_text("\n".join(L), encoding="utf-8")
    print(f"{len(rows)} remaining work(s) of {len(cands)} candidates -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
