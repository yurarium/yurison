#!/usr/bin/env python3
"""Which volume ended a series, where a shop says the series ended and says how long it is.

WHY A SHOP CAN ANSWER THIS. The updates tab marks a chapter 最終回 because the platform said so on
the chapter. A volume carries no such marking: of 7,262 volume titles read off コミックシーモア, 18
mention 最終 or 完結. What the shop does state is the series' own status and the number of volumes
it has, and where it says 完結 and states N volumes and N volumes were read, the Nth is the last
one. That is the shop's statement rather than our arithmetic over what we happen to hold.

WHY NOT "THE LAST VOLUME WE HAVE". A capture that stopped early would nominate the wrong volume and
say so confidently. The count is the guard: it has to agree before anything is claimed, and on the
capture this reads it disagrees on one work of 1,024.

WHY THE ISBN AND NOT THE TITLE. An ISBN identifies an edition; a title identifies nothing, as
`トワ・エ・モア` demonstrates by being a 1996 コンパス anthology and a 2024 講談社 series at once.
So the claim is keyed by the ISBN printed on the volume, and a work whose last volume states no
ISBN gets no claim rather than a claim about the wrong volume.

WHAT THIS IS. A claim under DEFINITIONS §5. A retailer is Tier C (REQUIREMENTS §1), so this is a
lead, and what to do about it is build.py's to decide, as with the antenna's completion claims
beside it.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import isbn as _isbn                                                           # noqa: E402

SHELVES = {"cmoa.jp": "genre 37 (百合・GL)", "bookwalker.jp": "tag 14 (百合)"}

# This was a digit-stripper called `isbn13` that did not convert, so a claim keyed on a
# ten-digit ISBN was keyed on a number no other reader in this repository would produce.
isbn13 = _isbn.isbn13


def final_volume(work):
    """The volume that ended this series, or None where the shop does not settle it.

    The shop has to mark the series complete, state how many volumes it has, and that many have to
    have been read. A work missing any of those is one this cannot speak about.
    """
    if not work.get("completed"):
        return None
    stated, found = work.get("volumes_stated"), work.get("volumes_found")
    if not stated or stated != found:
        return None
    numbered = [v for v in (work.get("volumes") or []) if v.get("volume")]
    if not numbered:
        return None
    last = max(numbered, key=lambda v: v["volume"])
    if last.get("volume") != stated or not isbn13(last.get("isbn")):
        return None
    return last


def claims(doc):
    """`[{isbn, volume, volumes, shop_id}]` for every work in a capture the shop settles."""
    out = []
    for w in (doc.get("works") or []):
        last = final_volume(w)
        if not last:
            continue
        out.append({"isbn": isbn13(last.get("isbn")), "volume": last["volume"],
                    "volumes": w.get("volumes_stated"), "shop_id": str(w.get("shop_id") or "")})
    return out


def finished(doc):
    """`[{shop_id, volumes, isbns}]` for every work the shop marks 完結.

    THE SAME JOIN, ASKED THE WHOLE QUESTION. `final_volume` above needs the stated count to agree
    with what was read, because it nominates one volume out of several and a short capture would
    nominate the wrong one. Whether the series is FINISHED is not that kind of claim: it is one
    fact about the series, the shop states it outright, and how much of the shelf we managed to
    read has no bearing on whether it is true. Having already accepted the shop's identification of
    which editions these are, declining its statement about them would be straining.

    Keyed by every ISBN on the work rather than the last, so a work joins on whichever of its
    volumes we happen to hold.
    """
    out = []
    for w in (doc.get("works") or []):
        if not w.get("completed"):
            continue
        isbns = sorted({isbn13(v.get("isbn")) for v in (w.get("volumes") or []) if v.get("isbn")})
        if isbns:
            out.append({"shop_id": str(w.get("shop_id") or ""),
                        "volumes": w.get("volumes_stated"), "isbns": isbns})
    return out


def main(argv=None):
    import argparse
    import json

    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", default="data/queue/cmoa-volumes.yaml")
    ap.add_argument("--out", default="data/source/comparators/shop-final-volumes.yaml")
    a = ap.parse_args(argv)

    doc = yaml.safe_load(pathlib.Path(a.capture).read_text()) or {}
    shop = str(doc.get("source") or "")
    rows, done = claims(doc), finished(doc)
    js = lambda v: json.dumps(v, ensure_ascii=False)                          # noqa: E731
    L = ["# Which volume ended a series, where the shop says the series ended and how long it is.",
         "#",
         "# A CLAIM under DEFINITIONS §5, not an attestation: a retailer is Tier C and this is a",
         "# lead. Keyed by ISBN, because an ISBN identifies an edition and a title identifies",
         "# nothing. See adapters/shopfinal.py for what has to hold before a work appears here.",
         f"source: {js(shop)}",
         f"shelf: {js(SHELVES.get(shop, 'yuri shelf'))}",
         "role: final-volume-claims",
         f"retrieved: {doc.get('retrieved')}",
         f"claims: {len(rows)}",
         f"finished_works: {len(done)}",
         "# Series the shop marks 完結, by every ISBN on them. A work joins on whichever volume we",
         "# hold. Whether the series ended is one fact the shop states; how much of its shelf we",
         "# read has no bearing on it, so no count has to agree before it is recorded.",
         "finished:"]
    for c in sorted(done, key=lambda x: x["isbns"][0]):
        L.append(f"  - shop_id: {js(c['shop_id'])}")
        L.append(f"    volumes: {js(c['volumes'])}")
        L.append(f"    isbns: {js(c['isbns'])}")
    L += ["# Which volume ENDED each series, where the stated count agrees with what was read.",
          "finals:"]
    for r in sorted(rows, key=lambda x: x["isbn"]):
        L.append(f"  - isbn: {js(r['isbn'])}")
        for k in ("volume", "volumes", "shop_id"):
            L.append(f"    {k}: {js(r[k])}")
    L.append("")
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L))
    total = len(doc.get("works") or [])
    marked = sum(1 for w in (doc.get("works") or []) if w.get("completed"))
    # HOW MANY OF THOSE MEAN ANYTHING. A one-volume work has no final volume, so a claim about one
    # is true and useless. Counted rather than assumed: on this capture every single claim is of
    # that kind, because the shop states ISBNs on first volumes and rarely on last ones.
    useful = sum(1 for r in rows if (r.get("volumes") or 0) >= 2)
    print(f"{shop}: {marked} of {total} works marked complete; {len(done)} join by ISBN and "
          f"{len(rows)} of those also name their final volume -> {a.out}")
    print(f"  of those final-volume claims, {useful} are of a work with more than one volume; "
          f"{len(rows) - useful} name the only volume a work has and say nothing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
