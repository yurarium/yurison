#!/usr/bin/env python3
"""Mint identifiers for print works a retailer shelf admitted, which need no judgement to mint.

WHY THIS EXISTS. The weekly print intake (adapters/stage-print.yaml) brings in works the build
cannot key until somebody mints them: 91 on the first refresh of BOOK☆WALKER's 百合 shelf. Each was
already admitted by `shelfingest.py` on the designation test, and `bwingest.py` has already sent
any title we hold to review instead of writing it, so what is left is a new work standing on one
shop record with a stable id of its own. Minting it is bookkeeping. Handing ninety of them to the
naming job would spend its allowance on nothing it can judge, a dozen at a time.

WHAT IT MINTS, and only this: a row awaiting an identifier that has no web address at all and stands
on print records, anchored on each record as `madb:<record id>`, which is how every print work in
the registry is anchored. A row with a web address is a serialisation somebody has to place, and
stays for the naming job. An anchor another entry already holds is a merge, and is refused.

    mint.py [--awaiting data/build/awaiting-identifier.json] [--registry data/identity/works.yaml]
"""
import argparse
import json
import pathlib
import re
import sys

ID = re.compile(r"^  - id: w(\d+)$", re.M)


def mintable(rows):
    """The awaiting rows this may mint: print records only, no web address."""
    return [r for r in rows or []
            if r.get("records") and not r.get("addresses") and not r.get("platforms")
            and r.get("work")]


def mint(text, rows):
    """`(new registry text, [(id, title)])`. Entries go at the end of `works:`, before `related:`."""
    taken = set(re.findall(r'"(madb:[^"]+)"', text))
    n = max((int(x) for x in ID.findall(text)), default=0)
    block, made = [], []
    for r in rows:
        anchors = [f"madb:{x}" for x in r["records"]]
        if any(a in taken for a in anchors):
            continue
        n += 1
        wid = f"w{n:05d}"
        # `title: null`, as every print work in the registry is: the record names it.
        block.append(f"  - id: {wid}\n    title: null\n"
                     f"    anchors:\n" + "".join(f'      - "{a}"\n' for a in anchors))
        taken.update(anchors)
        made.append((wid, r["work"]))
    if not block:
        return text, []
    at = text.find("\nrelated:\n")
    at = len(text) if at < 0 else at + 1
    return text[:at] + "".join(block) + text[at:], made


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--awaiting", default="data/build/awaiting-identifier.json")
    ap.add_argument("--registry", default="data/identity/works.yaml")
    a = ap.parse_args(argv)
    src = pathlib.Path(a.awaiting)
    rows = json.loads(src.read_text(encoding="utf-8")).get("works") or [] if src.exists() else []
    reg = pathlib.Path(a.registry)
    text, made = mint(reg.read_text(encoding="utf-8"), mintable(rows))
    if made:
        reg.write_text(text, encoding="utf-8")
    print(f"{len(made)} print work(s) minted of {len(rows)} awaiting"
          + (f": {made[0][0]} to {made[-1][0]}" if made else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
