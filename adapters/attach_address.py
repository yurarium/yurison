#!/usr/bin/env python3
"""Give one work one more address, with the reason, and change nothing else in the registry.

WHY THIS EXISTS. `facts/identity --attach` records the join and then runs the whole identity pass,
which mints an identifier for every row and print record it sees: an attachment made that way on
2026-10-15 minted 134 works nobody had asked for, and had to be reverted. Every attachment since has
been typed into works.yaml by hand. This is the narrow form: `facts.identity.attach` and its
refusals, an anchor another work holds or one somebody detached, and the registry written back
through the same writer in the order it was in, so the diff is the attachment.

    attach_address.py w03441 web:https://manga.nicovideo.jp/comic/73501 \\
        --basis "the same title and credits, 佐藤36 and 煮豆シューター, on the platform's page"
    attach_address.py --detach web:https://example.com/x --basis "a different work by its credits"
"""
import argparse
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from facts import identity as ident                                     # noqa: E402

REGISTRY = pathlib.Path("data/identity/works.yaml")
KINDS = ("web:", "madb:")


def change(text, anchor, wid=None, basis=None, today=None):
    """`(new text, error)`: `anchor` attached to `wid`, or detached where `wid` is None."""
    if not (basis or "").strip():
        return text, "a basis is required: the join is a claim, and the next reader has to weigh it"
    if not anchor.startswith(KINDS):
        return text, f"{anchor} is not an anchor; it starts with one of {', '.join(KINDS)}"
    doc = yaml.safe_load(text) or {}
    entries = doc.get("works") or []
    if wid:
        entries, err = ident.attach(entries, anchor, wid, basis.strip(), retrieved=today)
    else:
        if not ident.index(entries).get(anchor):
            return text, f"{anchor} is held by no work; there is nothing to detach"
        entries, err = ident.detach(entries, anchor, basis.strip(), retrieved=today), None
    if err:
        return text, err
    return ident.render(entries, doc.get("related") or [], today=str(doc.get("generated") or ""),
                        keep_order=True), None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("work", nargs="?", help="the identifier gaining the address")
    ap.add_argument("anchor", nargs="?")
    ap.add_argument("--detach", metavar="ANCHOR", help="take this address off the work holding it")
    ap.add_argument("--basis", required=True)
    ap.add_argument("--registry", default=str(REGISTRY))
    a = ap.parse_args(argv)
    if bool(a.detach) == bool(a.work and a.anchor):
        ap.error("give either a work and an anchor, or --detach ANCHOR")
    reg = pathlib.Path(a.registry)
    text, err = change(reg.read_text(encoding="utf-8"), a.detach or a.anchor,
                       None if a.detach else a.work, a.basis)
    if err:
        print(f"refused: {err}", file=sys.stderr)
        return 1
    reg.write_text(text, encoding="utf-8")
    print(f"{a.detach} detached" if a.detach else f"{a.anchor} attached to {a.work}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
