#!/usr/bin/env python3
"""Hand-reviewed verdicts on whether a work has ended, and what refuses to be one.

WHY THIS EXISTS. 121 works carry `state: dormant`, which rests on silence and nothing else. Three
mechanical sources reach the rest: a platform's own status field, a chapter titled 最終話, and the
antenna's 完結 tag. None of them reaches these, and probing ten platforms found completion stated
on two, so no amount of further automation gets at them from where we stand.

What is left is looking, one work at a time, the way a person would: the final chapter's own page,
the author's posts, the publisher's series page, a volume that says 完結 on its obi. That produces
evidence a rule could not have found, and this is where the answer goes.

A BASIS CARRIES THE WEIGHT. A verdict with a citation can be checked by somebody
who disagrees; a verdict without one is an opinion with a schema. So a source is required for
anything except `unsettled`, which is the honest outcome when looking found nothing and needs no
citation because it claims nothing.

RANKED ABOVE THE COMPARATOR because a person read a page and wrote down which one. The antenna's
tag is a lead by DEFINITIONS §5; a cited publisher page is not. Where the two disagree the review
wins and says why.

WHAT `continuing` IS FOR. Looking sometimes shows the opposite: a work we call dormant is on
hiatus, or moved, or is still running somewhere we do not watch. That is worth recording for the
same reason a refuted claim is: it stops the next pass paying to discover it again.

WHY `oneshot` LIVES HERE AND NOT IN A FILE OF ITS OWN. A one-shot has ended, so a register of
endings that could not say so would be answering half a question, and a second register answering
the other half is the shape STANDING-INSTRUCTIONS §3 is written about: two files, one fact, nothing
forcing them to agree about a work that appears in both. `oneshot` is `completed` plus the reason,
and the reason is what the interface needs: a one-shot's length is stated without a hedge, so a
reader is owed the sentence saying why the work is one instalment rather than one instalment of a
serialisation we hold a slice of.

IT IS THE STRONGER CLAIM, so it is the harder one to record. `completed` says a work stopped;
`oneshot` says it was never going to continue, which asserts something about how it was published
and is wrong in the direction that misleads: it tells a reader a story is whole. So it requires a
basis in both languages, and `basis_en` exists for that. Every other verdict reaches the interface
in Japanese alone today, which is its own defect and a wider one than this register.
"""
import argparse
import datetime
import pathlib
import sys

import yaml

FILE = pathlib.Path(__file__).resolve().parents[1] / "data" / "completion-reviewed.yaml"

VERDICTS = ("completed", "oneshot", "continuing", "unsettled")

# Verdicts that say the work has stopped publishing. `oneshot` is one of them by construction: a
# work complete in one instalment has nothing further coming. Named as a set so a caller asking
# "has this ended" does not have to know which of the two it is looking at.
ENDED = ("completed", "oneshot")

# Which evidence may support a verdict. `community-db` is admissible here, unlike for a name,
# because how a work ended is a matter of record that a wiki can report correctly, and because the
# alternative is no answer at all. It is ranked below the rest by being named in the basis.
SOURCE_KINDS = ("platform", "publisher-jp", "licensor", "community-db", "author", "derived")

KEYS = {"verdict", "basis", "basis_en", "source", "source_kind", "source_url", "reviewed", "note",
        "ended_on"}


def problems(work, e):
    """Everything wrong with one verdict. Empty means it may be applied."""
    out = []
    if not isinstance(e, dict):
        return [f"{work}: expected a mapping, got {type(e).__name__}"]
    unknown = set(e) - KEYS
    if unknown:
        out.append(f"{work}: unknown key(s) {sorted(unknown)}")
    v = e.get("verdict")
    if v not in VERDICTS:
        out.append(f"{work}: verdict {v!r} is not one of {VERDICTS}")
    if not e.get("reviewed"):
        out.append(f"{work}: no reviewed date; this is a decision somebody made")
    if v == "unsettled":
        # Claims nothing, so it owes no citation. It still owes a sentence saying what was looked
        # at, or it is indistinguishable from not having looked.
        if not (e.get("basis") or "").strip():
            out.append(f"{work}: an unsettled verdict still has to say what was looked at")
        return out
    if not (e.get("basis") or "").strip():
        out.append(f"{work}: no basis; a verdict with no evidence is an opinion with a schema")
    if e.get("source_kind") not in SOURCE_KINDS:
        out.append(f"{work}: source_kind {e.get('source_kind')!r} is not one of {SOURCE_KINDS}")
    if e.get("source_kind") != "derived" and not e.get("source_url"):
        out.append(f"{work}: {e.get('source_kind')} evidence needs the page it was read from")
    # A ONE-SHOT'S REASON REACHES THE READER, so it has to exist in the reader's language. The
    # work page states the length of a one-shot without a hedge and prints this sentence beside
    # it, and a Japanese-only sentence there is the interface explaining itself to half its
    # audience. See the header.
    if v == "oneshot" and not (e.get("basis_en") or "").strip():
        out.append(f"{work}: a oneshot verdict is shown to a reader, so it needs basis_en too")
    if e.get("ended_on"):
        try:
            datetime.date.fromisoformat(str(e["ended_on"]))
        except ValueError:
            out.append(f"{work}: ended_on {e['ended_on']!r} is not a date")
    return out


def check(doc):
    out = []
    for work, e in (doc.get("works") or {}).items():
        out += problems(work, e)
    for key in set(doc) - {"works", "source", "role", "retrieved"}:
        out.append(f"unknown top-level key {key!r}")
    return out


def load(path=FILE):
    p = pathlib.Path(path)
    return yaml.safe_load(p.read_text()) if p.exists() else {}


def verdicts(path=FILE):
    """{work: entry} for entries that decide something. `unsettled` decides nothing and is
    deliberately absent, so a caller cannot accidentally treat looking as a finding."""
    return {w: e for w, e in (load(path).get("works") or {}).items()
            if isinstance(e, dict) and e.get("verdict") in ENDED + ("continuing",)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", default=str(FILE))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    doc = load(a.file)
    bad = check(doc)
    for b in bad:
        print(f"  REJECT {b}")
    works = doc.get("works") or {}
    from collections import Counter
    c = Counter(e.get("verdict") for e in works.values() if isinstance(e, dict))
    print(f"{len(works)} reviewed: {dict(c)}; {len(bad)} rejected")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
