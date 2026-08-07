#!/usr/bin/env python3
"""Works a retailer capture identified by ISBN, taken from the national bibliography.

WHY THIS EXISTS. `extract.py` selects 単行本 by imprint, which finds the 百合姫 line and nothing
else. コミックシーモア's 百合・GL shelf runs far wider than one imprint: 1,833 works, of which 615
state an ISBN and 526 of those are in MADB. Those works exist, they are dated by the national
bibliography, and the only reason they were not records is that nobody had asked MADB about them.

WHY THE SHOP IS NOT THE SOURCE. A retailer is Tier C, discovery only, and data/queue/ sits outside
the source tree so nothing can promote a candidate into a record by accident. So the shop is not
promoted here. It supplies an ISBN, an ISBN identifies an edition, and the edition's record comes
from MADB exactly as every other record in this directory does. What enters the source layer is
the bibliography's answer, not the shop's listing.

WHAT LABEL THESE WORKS CARRY, AND WHY IT IS USUALLY `none`. DEFINITIONS §4 takes only
publisher-side labelling, and names a shop's genre shelf as never counting toward it: a licensed
retailer sells the publisher's edition, but what it shelves that edition under is its own decision.
So a work admitted this way carries `marketing_label: none` unless the MADB record's own
schema:brand is a yuri imprint, which IS publisher-side and counts on its own merits. `none` means
what §4 says it means, which is nothing about content.

WHAT THIS DOES NOT DO. It does not match titles. An ISBN identifies an edition and a title does
not: `ndl.py` records `citrus+` returning an unrelated book from 2007. A work stating no ISBN gets
no answer here, and that is silence about the sources rather than about the work.
"""
import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import extract                                                                 # noqa: E402
import isbn as _isbn                                                           # noqa: E402

ROUTE = "isbn-from-capture"

# A work reached by ISBN off a shop's shelf. The shelf is why we looked and is not the label.
LABEL_SHELF = ("none",
               "Admitted under DEFINITIONS §2 on a licensed retailer's yuri shelf and identified\n"
               "    by ISBN. A shop's genre shelf is never publisher-side labelling (§4), so this\n"
               "    axis stays `none`, which says nothing about content.")

# How many of the ISBNs asked for must come back before the answer is worth writing. The index held
# 526 of コミックシーモア's 615 at release 1.2.18. A run answering a handful has read a truncated
# dataset rather than met a smaller catalogue.
MIN_SHARE = 0.5


# THE FORM AN ISBN IS COMPARED IN, from `adapters/isbn.py`. This was a digit-stripper of the same
# name, so `select` compared a thirteen-digit want against whatever MADB printed, and MADB prints
# 126,318 of its 355,323 ISBNs in ten digits. Every one of those records was invisible to it.
isbn13 = _isbn.isbn13


def wanted(paths):
    """Every ISBN stated by a queue capture, as digits.

    Reads the capture's own shape and not a normalised copy of it: `volumes[].isbn` is where both
    retailer captures put the number, and a second transformation between here and there would be
    a second place for the format to drift.
    """
    import yaml

    out = set()
    for p in paths:
        doc = yaml.safe_load(pathlib.Path(p).read_text()) or {}
        for w in (doc.get("works") or []):
            for v in (w.get("volumes") or []):
                got = isbn13(v.get("isbn"))
                if got:
                    out.add(got)
    return out


def select(books, isbns):
    """The MADB volume records whose ISBN was asked for."""
    return [r for r in books if isbn13(extract.flat(r.get("schema:isbn", ""))) in isbns]


def expand(books, seeds, series):
    """Every volume of every work a seed volume identified.

    WHY A SEED IS NOT ENOUGH. A shop states an ISBN for the volumes it sells, which is often volume
    one and rarely all of them: コミックシーモア states one ISBN for a three-volume work and none
    for the other two. A record built from the seeds alone would say `volume_count: 1` about a work
    with three, and `last_published` would be volume one's date. The shop identifies the work; the
    bibliography says how long it is.
    """
    titles = extract.title_index(series)
    keys = {extract.key_of(r, series, titles)[0] for r in seeds}
    return [r for r in books if extract.key_of(r, series, titles)[0] in keys]


def label_for(vs):
    """`extract.LABEL_IMPRINT` where the publisher's own imprint carries it, else `LABEL_SHELF`."""
    pats = [extract.norm(p) for p in extract.IMPRINTS]
    for r in vs:
        brand = extract.norm(extract.flat(r.get("schema:brand", "")))
        if any(p in brand for p in pats):
            return extract.LABEL_IMPRINT
    return LABEL_SHELF


# The shelves in use, from DEFINITIONS §2 and measured in data/coverage/retailer-recon.md.
SHELVES = {"cmoa.jp": "genre 37 (百合・GL)", "bookwalker.jp": "tag 14 (百合)"}


def admitted_by(captures, retrieved):
    """The comparator lines for a record, naming the shop and the shelf that admitted the work.

    §2 admits a work a comparator lists and then requires knowing WHICH comparator, so a reader
    can tell whether a work is here because a publisher called it yuri or because a shop shelved
    it there. Written from the capture's own `source` rather than from an argument, so the shop
    named in the record is the shop the ISBNs came from.
    """
    import yaml

    shops = []
    for p in captures:
        doc = yaml.safe_load(pathlib.Path(p).read_text()) or {}
        shop = str(doc.get("source") or "")
        if shop and shop not in shops:
            shops.append(shop)
    L = ["admitted_by:"]
    for shop in shops:
        L += [f"  - comparator: {shop}",
              f"    shelf: {extract.yaml_str(SHELVES.get(shop, 'yuri shelf'))}",
              f"    retrieved: {retrieved}",
              "    note: >-",
              "      A licensed retailer's yuri shelf is a comparator (DEFINITIONS §2). Presumptive",
              "      and rebuttable, and never a marketing_label (§4)."]
    return L


def owned_elsewhere(out, route=ROUTE):
    """work_ids another route already wrote, which `route` must leave alone.

    A 百合姫 work that also sits on the shop's shelf is ONE work with one id, and the imprint route
    reached it with better evidence. Overwriting it here would replace `marketing_label: yuri` with
    `none` on a work whose publisher applied the label.

    `route` is a parameter because there is now more than one caller: the platform route
    (`by_platform_isbn.py`) has to ask the same question about its own name, and a second copy of
    this function would have been a second definition of what "already held" means.
    """
    out = pathlib.Path(out)
    held = set()
    if not out.exists():
        return held
    for f in out.glob("*.yaml"):
        text = f.read_text()
        if f"route: {route}" not in text:
            held.add(f.stem)
    return held


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", required=True, help="a pinned MADB release directory")
    ap.add_argument("--tag", required=True, help="MADB release tag, recorded in every record")
    ap.add_argument("--retrieved", required=True, help="ISO date the cache was downloaded")
    ap.add_argument("--capture", nargs="+", required=True, help="queue captures stating ISBNs")
    ap.add_argument("--out", default="data/source/madb")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    isbns = wanted(a.capture)
    if not isbns:
        sys.exit("no ISBNs stated by the capture(s) given; nothing to ask")

    books = extract.load(a.cache, "metadata101.json")
    series = {r["schema:identifier"]: r for r in extract.load(a.cache, "metadata104.json")}
    vols = select(books, isbns)

    answered = {isbn13(extract.flat(r.get("schema:isbn", ""))) for r in vols}
    share = len(answered) / len(isbns)
    if share < MIN_SHARE:
        sys.exit(f"HEALTH: {len(answered)} of {len(isbns)} ISBNs answered ({share:.0%}), under the "
                 f"{MIN_SHARE:.0%} floor. That is a truncated dataset rather than a thin shelf. "
                 "Refusing to write.")

    whole = expand(books, vols, series)
    by_series, grouping = extract.group(whole, series)
    by_series = extract.dedupe(by_series)

    # A work whose volumes came back under an id another route owns is that route's work.
    held = owned_elsewhere(a.out)
    skipped = [k for k in by_series if extract.work_id(k) in held]
    for k in skipped:
        del by_series[k]

    labels = {k: label_for(vs) for k, vs in by_series.items()}
    print(f"ISBNs asked      : {len(isbns)}")
    print(f"volumes answered : {len(vols)}  ({len(answered)} distinct ISBNs, {share:.0%})")
    print(f"volumes in those works: {len(whole)}  (the rest of each work, which no shop stated)")
    print(f"works            : {len(by_series)} new, {len(skipped)} already held by another route")
    print(f"  labelled yuri  : {sum(1 for v in labels.values() if v[0] == 'yuri')} "
          "(the publisher's own imprint)")
    print(f"  labelled none  : {sum(1 for v in labels.values() if v[0] == 'none')}")
    if a.dry_run:
        print("dry run; nothing written")
        return 0

    # Written one at a time rather than through extract.write, because the label is decided per
    # work here and that function takes one label for the whole pass.
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.yaml"):
        if f"route: {ROUTE}" in f.read_text():
            f.unlink()
    # Once, not once per record. Read inside the loop it re-parsed a 1,833-work capture 296 times
    # and turned a 17-second pass into one that had to be killed.
    admission = admitted_by(a.capture, a.retrieved)
    for sid, vs in sorted(by_series.items()):
        (out / f"{extract.work_id(sid)}.yaml").write_text(
            extract.render(sid, vs, series, grouping[sid], a.tag, a.retrieved, ROUTE, labels[sid],
                           admission))
    print(f"written          : {len(by_series)} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
