#!/usr/bin/env python3
"""Which imprint line a catalogued imprint string names. One producer, read by build.py and check.py.

WHY THIS EXISTS. An imprint is one object with many recorded spellings, and until this module it was
many objects. 一迅社 runs a single yuri line and the corpus held 27 strings for it, so a publisher
page built over the field would have given that line twenty entries. The strings differ because
MADB, openBD and a retailer each transcribe one printed logotype their own way, and because our own
extractor stores whichever of those a record happened to state.

WHAT THE VARIATION ACTUALLY IS, measured against MADB release 1.2.18 and openBD rather than assumed:

  THE CATALOGUER'S. MADB writes one brand as the list ["IDコミックス", "Yurihime comics"] on 87
  一迅社 records and as the single string `IDコミックス　／　Yurihime comics` on 14, so its separator
  is the join between two list values and carries no hierarchy of its own. The same pair occurs the
  other way round (`Zero-sum comics　／　IDコミックス`, `REXコミックス　／　IDコミックス`), and one
  record reads `4コマkingsぱれっとcomics　／　4コマKINGSぱれっとCOMICS`, which is one name joined to
  its own case variant. The separator changes with the notation of the day: ／ then ". " then " : ",
  and `Action comics : comic high's brand` against `Action comics　／　comic high's brand` is the
  same imprint under two of them. Case and spacing belong here too.

  THE PUBLISHER'S. The 百合姫 line's Latin logotype loses its hyphen at books published in 2015, and
  both catalogues turn over in the same year: MADB's last hyphenated volume is 2016 and openBD's is
  2015. MADB modified every pre-2025 record of the line in one 2024 sweep which emitted the
  hyphenated form 193 times and the bare form 378 times, so the form came off the book and not out
  of a convention the cataloguer held that week. A restyled logotype is the same line, which is why
  it is a spelling here and not a second entry.

WHAT ISBD'S ". " STATES, AND WHY THE PARENT IS KEPT. It states a series inside a series, and the
outer element is a fact. Two houses settle it in opposite directions and only the publisher can say
which: `IDコミックス. Yurihime comics` is the yuri line, and bare `IDコミックス` is not, because all
47 rows holding it alone entered on a retailer's shelf with marketing_label none. Against that,
`Manga time KR comics. Kirara menu` IS まんがタイムKRコミックス, because KIRARA MENU is that line's
own running number in the 奥付 and 芳文社's label index gives it no page, while つぼみシリーズ has one
and is therefore its own line. So the sub-line is the identity, the parent is recorded beside it,
and neither is folded into the other.

EXACT ON A SEGMENT, NEVER A SUBSTRING. A substring match is the failure this is written to prevent.
一迅社 has 10 lines under one umbrella and `百合姫コミックス` as a substring rule eats
ZERO-SUMコミックス, HOWLコミックス and DNAメディアコミックス, none of which is a yuri line; the
pattern that opened this investigation reached KADOKAWA's BRIDGE COMICS the same way. Folding
punctuation and case alone is not the answer either, and that was measured before it was rejected:
38 publishers carried more than one imprint before the fold and 38 after, because the variants
differ in content and not only in notation.

WHERE THE SPELLINGS LIVE. `data/names/imprints.yaml`, curated, one entry per line. A string that
matches nothing gets no object and is counted, which is the whole reason the registry is curated
rather than derived: a matcher that invents an object for every unrecognised string reaches every
string by construction, and the count of what it missed is then zero for the rest of its life
(STANDING-INSTRUCTIONS §14b). `imprint strings that reach no imprint object` is that count, and it
is measured in check.py off the shipped map, consulting nothing in this file.

THE UNIT OF CURATION IS A HOUSE, and the residue per house is asserted in test_imprints.py. Curating
by string would place whatever happened to be looked at and leave a count nobody can read; curating a
house means reading what it publishes, deciding every string it carries, and recording the ones the
file refuses. Two shapes are refused wherever they appear, and both are pinned as counter-cases: a
COMPANY name in the imprint field, which is what a distributor writes when it did not make the book,
and a MAGAZINE name with nothing saying it stands for the book line. コミック百合姫 is folded into
百合姫コミックス only because MADB's own `IDコミックス. Yurihime comics = コミック百合姫` states the
equation; コミックハイ!, 楽園, ヤングキング and まんがタイムきらら have no such statement and stay
out.

WHAT NO COUNT HERE CAN SEE: a string folded into the wrong line under the same publisher. Matching
is scoped by publisher so a line cannot be reached from another house, and `an imprint spelling
belongs to its own publisher` holds that. Within one house the guard is the counter-case, pinned in
test_imprints.py: ZERO-SUM, HOWL, DNAメディア, 4コマKINGS, 百合姫books and bare IDコミックス must
each resolve somewhere other than the yuri line, and BRIDGE COMICS must resolve to KADOKAWA.

Usage:  imprints.py                  every line, its spellings and the years each spelling covers
        imprints.py --unresolved     imprint strings no line answers for, most-recorded first
        imprints.py --publisher 一迅社   one house
"""
import argparse
import collections
import json
import pathlib
import re
import sys
import unicodedata

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

# THE SEGMENTER IS THE PUBLISHER MODULE'S, not a second copy of it. `publishers.segments` already
# splits a catalogued imprint on the cataloguer's separators for `imprint_of`, and §3 says the day
# there are two of them they disagree. What follows from consuming it: a separator it does not know
# is not a separator here either, so `Action comics : comic high's brand` stays one segment, matches
# nothing, and shows up in the unresolved count. That is the observable path and not a silent one.
from publishers import publisher_of, segments                                   # noqa: E402

REGISTRY = pathlib.Path("data/names/imprints.yaml")

# WHAT ONE ENTRY COVERS. NFKC first, because full-width Latin is the source's typesetting: ＦＵＺ and
# FUZ are one word and ＢＲＩＤＧＥ　ＣＯＭＩＣＳ is one line's name twice. Then case, then the
# characters a transcriber inserts or drops without meaning anything by it: the space in
# `MFC　キューンシリーズ`, the 中黒 in 角川コミックス・エース, and the hyphen that left the 百合姫
# logotype in 2015.
#
# THE HYPHEN IS SAFE TO DROP HERE AND WAS CHECKED AGAINST THE HOUSE THAT WOULD BREAK IT.
# ZERO-SUMコミックス folds to zerosumコミックス and Zero-sum comics to zerosumcomics, which are still
# two spellings of one line and neither is any nearer 百合姫. BLIC, BLIC-GL and BLIC-ERO fold to
# three distinct keys, so the suffix that makes one of them a yuri line survives.
_FOLD_OUT = re.compile(r"[\s　・\-‐‑–]")


def fold(s):
    """The form two spellings are compared in. One entry covers every spelling that folds to it."""
    return _FOLD_OUT.sub("", unicodedata.normalize("NFKC", str(s or "")).lower())


def load(path=REGISTRY):
    """The registry as `[line, ...]`, each line a dict, in file order."""
    p = pathlib.Path(path)
    if not p.exists():
        return []
    return (yaml.safe_load(p.read_text()) or {}).get("lines") or []


def index(lines):
    """`{(publisher_fold, spelling_fold): line}`, which is the only lookup this module performs.

    KEYED ON THE PUBLISHER AS WELL AS THE SPELLING, so a line can be reached only from the house
    that runs it. `角川コミックス・エース` is catalogued under KADOKAWA and under 角川書店 and both
    are listed on the entry, and `ブシロードコミックス` is the same shape reached differently: two
    arms of one group are both catalogued as the publisher of one line, which the dates show is
    neither a rename nor a transfer.
    """
    out = {}
    for line in lines:
        for pub in (line.get("publishers") or []):
            for spelling in (line.get("spellings") or []):
                out.setdefault((fold(pub), fold(spelling)), line)
    return out


def resolve(publisher, raw, idx):
    """The line a catalogued imprint string names, or None where the registry holds no answer.

    MOST SPECIFIC SEGMENT FIRST, which is what makes the compound forms cost no entries.
    `IDコミックス. Yurihime comics = コミック百合姫` segments into three, and the last of them that
    the registry knows decides. The whole string is tried first so that a line whose own name holds
    one of the separators is not taken apart before it is looked up.

    A SEGMENT IS MATCHED WHOLE. `Yuri-hime comics anthology series` and `Yuri-hime comics` fold to
    different keys and are two entries, so the shorter one cannot reach the longer one's rows.
    """
    p = fold(publisher_of(publisher))
    if not p:
        return None
    whole = idx.get((p, fold(raw)))
    if whole:
        return whole
    for seg in reversed(segments(raw)):
        line = idx.get((p, fold(seg)))
        if line:
            return line
    return None


def _span(seen, first, last):
    for v in (first, last):
        if not v:
            continue
        v = str(v)[:4]
        seen[0] = v if seen[0] is None or v < seen[0] else seen[0]
        seen[1] = v if seen[1] is None or v > seen[1] else seen[1]


def census(rows, lines):
    """`(by_line, unresolved)` over series rows: what each line is recorded as, and for how long.

    THE HISTORICAL VARIANTS ARE MEASURED AND NOT WRITTEN DOWN. The registry says which spellings are
    one line; the years each spelling covers are a property of the corpus and change with every
    capture, so recording them by hand would be a second copy of a fact the rows already hold. This
    is what a publisher page shows a reader who is looking at a 2008 volume and wants to know what
    that volume says.

    `unresolved` is keyed by (publisher, raw string) because the same string can be one house's line
    and another's unanswered field.
    """
    idx = index(lines)
    by_line = {}
    unresolved = {}
    for r in rows:
        for pr in (r.get("print") or []):
            raw = str(pr.get("imprint") or "").strip()
            if not raw:
                continue
            pub = publisher_of(pr.get("publisher") or "")
            line = resolve(pub, raw, idx)
            if line is None:
                slot = unresolved.setdefault((pub, raw), {"publisher": pub, "raw": raw, "rows": 0})
                slot["rows"] += 1
                continue
            held = by_line.setdefault(line["id"], {"line": line, "rows": 0, "spellings": {}})
            held["rows"] += 1
            spell = held["spellings"].setdefault(raw, {"raw": raw, "rows": 0, "years": [None, None]})
            spell["rows"] += 1
            _span(spell["years"], pr.get("first"), pr.get("last"))
    return by_line, unresolved


def shipped(rows, lines):
    """`{key: {id, name, ...}}` for the interface, keyed by the catalogued string AND by its fold.

    KEYED BOTH WAYS for the reason `publisher_map` is: the browser and this module each strip the
    cataloguing, §3 says two implementations of one rule drift, and one of them runs in a browser so
    they cannot be merged. A drift then costs a lookup the other key still answers.

    ONLY STRINGS THE CORPUS CARRIES. A map holding every spelling in the registry would answer for
    strings no row has, and `imprint spellings no row carries` would then have nothing to measure.
    """
    by_line, _unresolved = census(rows, lines)
    out = {}
    for held in by_line.values():
        line = held["line"]
        fact = {"id": line["id"], "name": line["name"]}
        if line.get("parent"):
            fact["parent"] = line["parent"]
        if line.get("publishers"):
            fact["publishers"] = list(line["publishers"])
        if line.get("adult"):
            fact["adult"] = True
        for raw in held["spellings"]:
            out.setdefault(raw, fact)
            out.setdefault(fold(raw), fact)
    return out


def dead_spellings(rows, lines):
    """Registry spellings no row carries, as `(publisher, spelling)`. A curated entry going stale.

    Written for the report and not for a gate. A spelling with no rows behind it is a name somebody
    put in from a publisher's label list, which is how the 一迅社 and KADOKAWA entries were built,
    so this counts intent as well as error and belongs in a report a person reads.
    """
    idx = index(lines)
    seen = set()
    for r in rows:
        for pr in (r.get("print") or []):
            raw = str(pr.get("imprint") or "").strip()
            if not raw:
                continue
            p = fold(publisher_of(pr.get("publisher") or ""))
            seen.add((p, fold(raw)))
            seen.update((p, fold(s)) for s in segments(raw))
    return sorted((pub, spelling) for line in lines
                  for pub in (line.get("publishers") or [])
                  for spelling in (line.get("spellings") or [])
                  if (fold(pub), fold(spelling)) not in seen and (fold(pub), fold(spelling)) in idx)


def series_rows(build="data/build"):
    return json.loads((pathlib.Path(build) / "series.json").read_text())["series"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--registry", default=str(REGISTRY))
    ap.add_argument("--publisher", default=None, help="one house only")
    ap.add_argument("--unresolved", action="store_true",
                    help="print the imprint strings no line answers for, and stop")
    a = ap.parse_args(argv)

    lines = load(a.registry)
    rows = series_rows(a.build)
    by_line, unresolved = census(rows, lines)

    if a.unresolved:
        want = [u for u in unresolved.values()
                if not a.publisher or u["publisher"] == a.publisher]
        for u in sorted(want, key=lambda u: (-u["rows"], u["publisher"], u["raw"])):
            print(f"  {u['rows']:5}  {u['publisher']:12}  {u['raw']}")
        print(f"\n{len(want)} imprint string(s) reach no line, on {sum(u['rows'] for u in want)} row(s)")
        return 0

    held = [h for h in by_line.values()
            if not a.publisher or a.publisher in (h["line"].get("publishers") or [])]
    for h in sorted(held, key=lambda h: -h["rows"]):
        line = h["line"]
        parent = f"  (in {line['parent']})" if line.get("parent") else ""
        print(f"{h['rows']:5}  {line['name']}{parent}")
        for s in sorted(h["spellings"].values(), key=lambda s: (s["years"][0] or "9999", s["raw"])):
            lo, hi = s["years"]
            print(f"       {s['rows']:4}  {lo or '????'}-{hi or '????'}  {s['raw']}")
    dead = dead_spellings(rows, lines)
    counts = collections.Counter(len(h["spellings"]) for h in held)
    print(f"\n{len(held)} line(s) over {sum(h['rows'] for h in held)} row(s); "
          f"{sum(len(h['spellings']) for h in held)} catalogued spelling(s); "
          f"{counts.get(1, 0)} line(s) recorded one way only")
    print(f"{len(unresolved)} string(s) reach no line; {len(dead)} registry spelling(s) no row carries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
