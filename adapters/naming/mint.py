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

JOINS FIRST. The MADB routes find print records for serialisations the registry already holds, and
write each finding to a joins file (data/queue/shop-query-joins.yaml and platform-print-joins.yaml)
naming the record and the work. A record a join claims is that work's book run, so it is attached to
the work before anything is minted, through `facts/identity.attach_all`, which takes only joins whose
anchor nobody holds. Minting first gave 33 of release 1.2.21's records an identifier of their own
beside the serialisation they print, and a reader saw each work twice.

AND A TITLE THE CORPUS ALREADY HOLDS IS NOT MINTED. A record no join claims can still be a book the
corpus holds: the 百合姫 imprint route met four 2026 books BOOK☆WALKER already listed, three of
them anthologies, and 骨に願いを、星に呪いを collected from 一迅社's own platform. MADB credits
nobody on an anthology, so no join and no duplicate check could see them. A row whose title folds
to a held work's stays unminted, which keeps it from every reader, and is reported for a person to
join with `identity --attach` or to mint as a different work.

    mint.py [--awaiting data/build/awaiting-identifier.json] [--registry data/identity/works.yaml]
            [--joins data/queue/shop-query-joins.yaml data/queue/platform-print-joins.yaml]
"""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

JOINS = ["data/queue/shop-query-joins.yaml", "data/queue/platform-print-joins.yaml"]
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
    # BEFORE THE RELATED SECTION'S OWN COMMENT, which `identity.render` writes above `related:`.
    # Entries inserted at `related:` itself landed under that comment, inside the prose about it.
    at = text.find("\n\n# Related works.")
    if at >= 0:
        at += 1
    else:
        at = text.find("\nrelated:\n")
        at = len(text) if at < 0 else at + 1
    return text[:at] + "".join(block) + text[at:], made


def as_attachments(doc, entries):
    """A joins document in the shape `identity.attach_all` takes: `anchor`, `id`, `basis`.

    THE SHOP QUERY WRITES THAT SHAPE ALREADY. The platform route writes what it found instead, the
    serialisation's address and the record, because `identity`'s full pass resolves the address
    against the web population. Here the registry resolves it: the work holding `web:<address>` is
    the serialisation. A lead the capture marked `differs` is not a join, as `identity.chain_joins`
    rules: the bibliography's title for the record names something other than the serialisation.
    """
    from facts import identity

    if (doc.get("joins") or [{}])[0].get("anchor") or not doc.get("joins"):
        return doc
    held = identity.index(entries)
    out = []
    for j in doc["joins"]:
        wid = held.get(identity.web_anchor(j.get("platform_url")))
        if j.get("agreement") == "differs" or not (wid and j.get("madb_work_id")):
            continue
        out.append({"anchor": identity.print_anchor(j["madb_work_id"]), "id": wid,
                    "retrieved": str(doc.get("retrieved") or ""),
                    "basis": f"the serialisation's own page at {j['platform_url']} links the shop "
                             f"selling its volumes, the shop states their ISBN, and the national "
                             f"bibliography's record holding that ISBN is this one"})
    return {"joins": out}


def titled_like_held(rows, held_titles):
    """`(rows to mint, [(row, held title)])`: a row whose title folds to a held work's is held back."""
    from facts import identity

    held = {}
    for t in held_titles or []:
        held.setdefault(identity.match_key(t), t)
    out, back = [], []
    for r in rows:
        k = identity.match_key(r.get("work"))
        if k and k in held:
            back.append((r, held[k]))
        else:
            out.append(r)
    return out, back


def attach(text, joins):
    """`(registry text, attached, refused)` once every join in `joins` has been applied.

    Written back through `identity.render` in the registry's own order and under its own
    `generated` date, so a run with nothing to attach gives the text back unchanged.
    """
    import yaml
    from facts import identity

    doc = yaml.safe_load(text) or {}
    entries, attached, refused = doc.get("works") or [], 0, []
    for j in joins:
        entries, n, r = identity.attach_all(entries, as_attachments(j, entries))
        attached, refused = attached + n, refused + r
    if not attached:
        return text, 0, refused
    return (identity.render(entries, doc.get("related") or [], today=str(doc.get("generated")),
                            keep_order=True), attached, refused)


def main(argv=None):
    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--awaiting", default="data/build/awaiting-identifier.json")
    ap.add_argument("--registry", default="data/identity/works.yaml")
    ap.add_argument("--joins", nargs="*", default=JOINS)
    a = ap.parse_args(argv)
    src = pathlib.Path(a.awaiting)
    rows = json.loads(src.read_text(encoding="utf-8")).get("works") or [] if src.exists() else []
    reg = pathlib.Path(a.registry)
    before = reg.read_text(encoding="utf-8")
    joins = [yaml.safe_load(pathlib.Path(f).read_text()) or {} for f in a.joins
             if pathlib.Path(f).exists()]
    text, attached, refused = attach(before, joins)
    print(f"{attached} print record(s) attached to a work already held, from {len(joins)} "
          f"joins file(s)")
    # A REFUSAL IS A JOIN WHOSE RECORD ANOTHER WORK HOLDS, which is a merge and a person's call.
    # Counted rather than listed: every one is refused again each week until it is decided.
    if refused:
        print(f"  {len(refused)} join(s) refused; `identity --attachments` lists them")
    import population
    try:
        held_titles = population.titles()
    except Exception as e:                                                  # noqa: BLE001
        # NO STORE, NO MINTING: without the held titles a duplicate cannot be told from a new work.
        print(f"no held titles to compare against ({type(e).__name__}); nothing minted")
        held_titles, rows = [], []
    rows, back = titled_like_held(mintable(rows), held_titles)
    for r, t in back:
        print(f"  HELD {r['work']}: the corpus holds 「{t}」; join it or mint it by hand")
    text, made = mint(text, rows)
    if text != before:
        reg.write_text(text, encoding="utf-8")
    print(f"{len(made)} print work(s) minted of {len(rows)} awaiting"
          + (f": {made[0][0]} to {made[-1][0]}" if made else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
