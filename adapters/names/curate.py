#!/usr/bin/env python3
"""Apply hand-reviewed English names to the store, refusing any that cannot be attributed.

WHY THIS EXISTS. Every pass so far produces names mechanically, and none of them can produce the
two kinds that matter most: a licensed title, which lives in a licensor's catalogue and nowhere a
scraper here goes, and a translation, which is a judgement. Both were being held in a person's head
with nothing between the decision and the file.

WHY THE DECISIONS LIVE IN A FILE. The store is journal-backed and durable, so recording straight
into it would not lose anything. What it would lose is the REASON: which page was read, on what
day, and by what argument a title was translated rather than romanised. data/names/curated.yaml is
the source and titles.yaml the derived state, the same relation data/source and data/build already
have, which also makes re-applying after a rebuild a replay rather than a re-decision.

WHAT IT REFUSES, AND WHY THAT IS THE POINT.

  A COMMUNITY DATABASE MAY NOT SUPPLY A NAME. Wikipedia, Wikidata, AniList and MangaUpdates are
  leads. A lead tells you where to look; it is not an attribution, and the string it carries may be
  a licensed title, a Japanese publisher's own, or a scanlation title, with nothing in the record to
  say which. `community-db` therefore appears in no row of ATTRIBUTION below, so an entry sourced
  to one is rejected outright unless it is filed as a candidate. This is the project owner's rule
  and it was previously enforced by remembering it.

  A BASIS MUST MATCH ITS EVIDENCE. `licensed` means a licensor publishes it under that name, so it
  requires a licensor page. `official-jp` means the work's own English name, so it requires the
  Japanese publisher or the platform. `translated` and `romaji` are ours, and claiming a source for
  them would be dressing up a judgement as a finding.

  AN UNKNOWN KEY IS AN ERROR. A hand-edited file that reads `bais: licensed` would apply nothing
  and report success, which is this project's characteristic bug written in YAML.

Usage:  curate.py --check              validate the file and stop
        curate.py --apply              validate, then record into data/names
"""
import argparse
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names.store import NameStore  # noqa: E402

FILE = pathlib.Path(__file__).resolve().parents[2] / "data" / "names" / "curated.yaml"

# Which evidence each basis demands. `community-db` is deliberately absent from every row.
ATTRIBUTION = {
    "stated": ("platform", "publisher-jp"),      # the person's own rendering, where they wrote it
    "official-jp": ("publisher-jp", "platform"),  # the work's own English name
    "licensed": ("licensor",),                    # an English-language licensor's catalogue
    "translated": ("derived",),                   # ours
    "romaji": ("derived",),                       # ours
}

# A source_kind may be named here without being usable as evidence: a candidate records where a
# string was seen, and seeing it in a community database is the ordinary case.
SOURCE_KINDS = ("platform", "publisher-jp", "licensor", "community-db", "derived")

KEYS = {"en", "candidate", "basis", "source", "source_kind", "source_url", "reviewed", "note",
        "candidate_note"}


def problems(kind, ja, e):
    """Everything wrong with one entry. Empty means it may be applied."""
    out = []
    if not isinstance(e, dict):
        return [f"{kind}/{ja}: expected a mapping, got {type(e).__name__}"]
    where = f"{kind}/{ja}"

    unknown = set(e) - KEYS
    if unknown:
        out.append(f"{where}: unknown key(s) {sorted(unknown)}")

    if bool(e.get("en")) == bool(e.get("candidate")):
        out.append(f"{where}: give exactly one of `en` (attributed) or `candidate` (seen, unproven)")
    if not e.get("source"):
        out.append(f"{where}: no source")
    if e.get("source_kind") not in SOURCE_KINDS:
        out.append(f"{where}: source_kind {e.get('source_kind')!r} is not one of {SOURCE_KINDS}")
    if not e.get("reviewed"):
        out.append(f"{where}: no reviewed date; a curated entry is a decision somebody made")

    if e.get("en"):
        basis = e.get("basis")
        if basis not in ATTRIBUTION:
            out.append(f"{where}: basis {basis!r} is not one of {sorted(ATTRIBUTION)}")
        elif e.get("source_kind") not in ATTRIBUTION[basis]:
            out.append(f"{where}: basis {basis!r} needs evidence from "
                       f"{' or '.join(ATTRIBUTION[basis])}, not {e.get('source_kind')!r}")
        if e.get("source_kind") != "derived" and not e.get("source_url"):
            out.append(f"{where}: an attributed name needs the page it was read from")
    elif e.get("basis"):
        out.append(f"{where}: a candidate carries no basis; it is not yet a claim about the work")
    return out


def check(doc):
    """Validate a whole file. Returns the list of problems across every entry."""
    out = []
    for kind in ("titles", "authors"):
        for ja, e in (doc.get(kind) or {}).items():
            out += problems(kind, ja, e)
    for key in set(doc) - {"titles", "authors"}:
        out.append(f"unknown top-level key {key!r}")
    return out


def apply(store, doc):
    """Record every entry. Returns (applied, candidates)."""
    applied = candidates = 0
    for kind in ("titles", "authors"):
        for ja, e in (doc.get(kind) or {}).items():
            fact = {k: e.get(k) for k in
                    ("en", "candidate", "basis", "source", "source_kind", "source_url", "note",
                     "candidate_note")}
            # `at` is the day the decision was reviewed, not the day this ran. Re-applying the file
            # after a rebuild must not restamp a name as freshly decided.
            fact["at"] = str(e.get("reviewed"))
            store.record(kind, ja, **fact)
            if e.get("en"):
                applied += 1
            else:
                candidates += 1
    return applied, candidates


def load(path=FILE):
    return yaml.safe_load(pathlib.Path(path).read_text()) or {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", default=str(FILE))
    ap.add_argument("--out", default="data/names")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)

    doc = load(a.file)
    bad = check(doc)
    for b in bad:
        print(f"  REJECT {b}")
    counts = {k: len(doc.get(k) or {}) for k in ("titles", "authors")}
    print(f"{counts['titles']} title(s), {counts['authors']} author(s); {len(bad)} rejected")
    if bad:
        return 1
    if a.apply:
        store = NameStore(a.out)
        applied, cands = apply(store, doc)
        store.compact()
        store.close()
        print(f"applied {applied} attributed name(s) and {cands} candidate(s) to {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
