#!/usr/bin/env python3
"""Works a capture pass was told to read and wrote no row for.

WHAT WENT WRONG. `data/source/comicfuz/resolved.yaml` named ぬるめた at
`https://comic-fuz.com/series/2389`, the only address in that file spelled `/series/` and not
`/manga/`. `adapters/comicfuz/releases.py` computes the `/manga/` spelling to decide whether a row
is a FUZ target and to key the duplicate set, then appends the ORIGINAL row to `targets`, so the
fetch asked for `/series/2389`. That address answers 404 while `/manga/2389` answers 200 with 75
chapters under こかむも. The 404 became one line in `failed`, `failed` was printed at the end of the
run and then discarded, and `works.yaml` was written with 46 of its 47 confirmed works and reported
success. Nothing in the repository recorded that a work had been asked for and not got.

WHY A PRINTED LIST IS NOT A RECORD (STANDING-INSTRUCTIONS §4, §13). Every capture pass here keeps a
`failed` list, prints it, and exits zero. The printed line is gone when the terminal scrolls, so an
absence in `data/source` reads exactly like a work that was never named. That is the same shape as
`adapters/kadokomi/confirm.py` writing a register nothing read: a control that exists and cannot be
observed to be doing anything.

WHAT THIS READS. The target lists a pass is given, and the captures a pass writes. Both are
committed files. A target is missed when no capture of the same platform states its identifier and
no register accounts for it.

WHY IT DOES NOT READ `failed` OR ANY COUNTER THE PASS PRINTS. §14b: a measure taken from the list
the capture writes agrees with the capture by construction. `works_resolved` in the capture header
counts the rows below it, so it is 46 whenever 46 rows were written, whatever was asked for. The
join is against the INPUT, which the pass consumes and never rewrites, so a target cannot be made
to disappear by the failure being measured.

WHY IT DOES NOT REUSE THE ADAPTER'S URL HANDLING, WHICH §3 WOULD ORDINARILY ASK FOR. The adapter's
normalisation is the thing under test. `ADDRESS` below accepts both spellings of a FUZ address
directly, so it never needs the rewrite that failed; consuming the adapter's version would have
made this blind in precisely the place the adapter was blind. The cost is a second reader of "which
work is this address", and it is paid deliberately. `adapters/test_capturegap.py` pins both
spellings against each other, which is the agreement §3 asks for where two producers are
unavoidable.

WHAT IT THEREFORE CANNOT SEE. A target list that never named the work at all. ニコニコ's chapter
pass takes its targets from `data/queue/serialisation-joins.yaml`, so a serialisation nobody joined
to a printed book is not counted here and is not a capture fault. `adapters/feedgap.py` is the
measure for that class, and it counts feed rows, so the two do not overlap.

A REGISTER MAY ACCOUNT FOR A TARGET, AND MAY NOT SILENCE ONE. `data/source/kadokomi/withheld.yaml`
holds five works the pass fetched, read and refused on content grounds. The pass looked, so those
are not missing, and they are dropped from the count. `data/queue/unheld-works.yaml` is the other
kind: it records what was decided about a work, not that a capture read its page, so it leaves the
count where it was (§13).

THAT SUBTRACTION REMOVES NOTHING TODAY, AND IT IS SAID HERE BECAUSE A FILTER THAT NEVER FIRES LOOKS
IDENTICAL TO ONE THAT IS BROKEN (§4). All five withheld works also have rows in
`data/source/kadokomi/chapters.yaml`, since the withholding happens downstream of the capture and
not in it, so they are already accounted for as captured. `adapters/test_capturegap.py` exercises
the subtraction directly, which is the only reason it can be trusted to work the day
`chapters.yaml` stops carrying them.

Usage:  capturegap.py
        capturegap.py --root .
"""
import argparse
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _yaml(path):
    """The parsed document, or an empty one where the file is not there."""
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}


# Each pass names the platform it captures, how that platform's identifier appears in an address,
# which fields state one, where its targets come from and where its rows land.
#
# `address` accepts every spelling of a work address the sources use, INCLUDING the ones an adapter
# rewrites before fetching. That is the point of the file: the FUZ pattern carries `series` because
# a confirmed identity was recorded that way and the pass lost it.
PASSES = [
    {
        "platform": "COMIC FUZ",
        "address": re.compile(r"comic-fuz\.com/(?:manga|series)/(\d+)"),
        "codes": (),
        "targets": [("data/source/comicfuz/resolved.yaml", ("works",)),
                    ("data/coverage/webcomics-gap.yaml", ("candidates", "works_missing"))],
        "captures": [("data/source/comicfuz/works.yaml", ("works",))],
        "accounted": [],
    },
    {
        "platform": "カドコミ",
        "address": re.compile(r"comic-walker\.com/detail/([A-Za-z0-9_]+)"),
        "codes": ("code", "platform_code"),
        "targets": [("data/source/kadokomi/catalogue.yaml", ("works",)),
                    ("data/source/kadokomi/resolved.yaml", ("works",)),
                    ("data/source/kadokomi/confirmed.yaml", ("works",)),
                    ("data/coverage/webcomics-gap.yaml", ("candidates", "works_missing"))],
        "captures": [("data/source/kadokomi/chapters.yaml", ("works",))],
        # Fetched, read, and refused on content grounds. The pass looked, so nothing is missing.
        "accounted": [("data/source/kadokomi/withheld.yaml", ("works",))],
    },
    {
        "platform": "ニコニコ漫画",
        "address": re.compile(r"manga\.nicovideo\.jp/comic/(\d+)"),
        "codes": ("comic_id", "platform_code"),
        "targets": [("data/source/nicovideo/resolved.yaml", ("works",)),
                    ("data/coverage/webcomics-works.yaml", ("candidates",))],
        # BOTH captures of the platform, because the question is whether anything went and looked.
        # releases.py writes work_update_dates and works.py writes web_work_chapters, and a work
        # held by either has been read.
        "captures": [("data/source/nicovideo/nicovideo.yaml", ("works",)),
                     ("data/source/nicovideo/works.yaml", ("works",))],
        "accounted": [],
    },
]

TITLE_FIELDS = ("title", "work_title")


def rows(doc, keys):
    """Every row under the named lists of one document, in the order the file gives them."""
    out = []
    for k in keys:
        v = (doc or {}).get(k)
        if isinstance(v, dict):
            v = list(v.values())
        for r in v or []:
            if isinstance(r, dict):
                out.append(r)
    return out


def ident(row, address, codes=()):
    """The platform identifier this row states, or None where it states none.

    An address is read first, because it says which platform the row is about. A bare code is
    trusted only for a pass whose fields carry one, so a `code` belonging to some other host is
    never mistaken for this platform's.
    """
    for field in ("url", "urls"):
        v = row.get(field)
        for one in (v if isinstance(v, list) else [v]):
            m = address.search(str(one or ""))
            if m:
                return m.group(1)
    for field in codes:
        v = row.get(field)
        if v not in (None, ""):
            return str(v)
    return None


def idents(doc_rows, address, codes=()):
    """`{identifier: title}` for the rows stating one, first title wins."""
    out = {}
    for r in doc_rows:
        i = ident(r, address, codes)
        if i is None:
            continue
        title = next((r[f] for f in TITLE_FIELDS if r.get(f)), None)
        if i not in out or (out[i] is None and title):
            out[i] = title
    return out


def load(root=None, read=_yaml):
    """One entry per pass, holding what it was told to read and what it wrote.

    Kept as three plain collections so a check can plant a canary in any of them. A function that
    goes to disk when it is called cannot be shown one, and a self-test then reports it healthy
    having exercised nothing.
    """
    base = pathlib.Path(root or ROOT)
    out = []
    for p in PASSES:
        got = {which: gather(base, p, p[which], read)
               for which in ("targets", "captures", "accounted")}
        out.append({
            "platform": p["platform"],
            "targets": got["targets"],
            "captured": set(got["captures"]),
            "accounted": set(got["accounted"]),
        })
    return out


def gather(base, p, spec, read=_yaml):
    """`{identifier: title}` across every file of one spec, read through the same pass rules."""
    got = {}
    for rel, keys in spec:
        got.update(idents(rows(read(base / rel), keys), p["address"], p["codes"]))
    return got


def missing(passes):
    """Every target no capture of its platform holds and no register accounts for.

    Returns `[{platform, ident, title}]`, ordered by platform and then by identifier, so the same
    tree gives the same answer whenever the question is asked.
    """
    out = []
    for p in passes or []:
        gone = set(p.get("targets") or {}) - set(p.get("captured") or ()) \
            - set(p.get("accounted") or ())
        for i in sorted(gone):
            out.append({"platform": p["platform"], "ident": i,
                        "title": (p.get("targets") or {}).get(i)})
    return sorted(out, key=lambda r: (r["platform"], r["ident"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    a = ap.parse_args(argv)

    passes = load(a.root)
    gone = missing(passes)
    for p in passes:
        n = sum(1 for r in gone if r["platform"] == p["platform"])
        print(f"{p['platform']:14}  {len(p['targets']):5} named  {len(p['captured']):5} captured  "
              f"{len(p['accounted']):3} accounted  {n:4} with no row")
    print()
    for r in gone:
        print(f"  {r['platform']:14}  {r['ident']:14}  {r['title'] or '(no title stated)'}")
    print(f"\n{len(gone)} target(s) named and never written. Each was fetched and failed, or was "
          f"never fetched; the pass printed the reason and kept none of it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
