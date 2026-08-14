#!/usr/bin/env python3
"""What date the national bibliography holds against an ISBN, from the MADB bulk dataset.

WHY THIS EXISTS. A retailer states an ISBN and, sometimes, a publication month. openBD answers by
ISBN from the publisher's own JPRO registration and was the obvious second source, but it is thin
for this corpus: of 23 ISBNs read off コミックシーモア work pages, openBD held a date for 10.
`metadata101` holds a date for 22 of the same 23. It is 単行本 records sourced from NDLサーチ, so it
is the national bibliography rather than a registration one publisher may or may not have filed.

It also costs nothing. The release is already pinned in the cache for `extract.py`, the file is on
disk, and answering an ISBN is a dictionary lookup. There is no host to be polite to and no run to
resume, which is why the remainder of an ISBN-bearing shelf is a solved problem and the remainder
of a shelf with no ISBNs is not.

WHY IT STREAMS RATHER THAN LOADING THE GRAPH. `extract.py` does `json.loads` on the whole file,
which is right for a pass that needs the graph and wrong here: metadata101 is 665 MB on disk and
several times that once parsed, for two fields per record. Records are read one at a time and
parsed one at a time, so the memory cost is one record.

WHAT IT DOES NOT DO. It does not match titles. An ISBN identifies an edition and a title does not,
and `ndl.py` records what a title search costs: `citrus+` returns an unrelated book from 2007. A
work with no ISBN gets no answer here, which is silence about the sources and not about the work.

THE INDEX IS KEYED ON THE THIRTEEN-DIGIT FORM, AND WAS NOT UNTIL 2026-08-06. It stripped the
punctuation out of whatever the catalogue printed and stored that. MADB prints 126,318 of its
355,323 ISBNs in ten digits, 35.5% of the bibliography, because it imported those records from
NDLサーチ as they were catalogued. Every one of them was unreachable from a thirteen-digit
question, and every question this repository asks is thirteen-digit, so a third of the national
bibliography answered nothing and looked exactly like a catalogue that had no record.

What it cost is measurable: 51 コミックシーモア works were filed `isbn-stated-not-catalogued`,
meaning no catalogue asked held the number. Two of them, ハニー＆ハニー and フリー・ソウル, were in
this file the whole time. `adapters/isbn.py` is now the one converter and this module consumes it,
which is the same fix as the pager: one fact, one producer (STANDING-INSTRUCTIONS §3).
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import isbn as _isbn                                                           # noqa: E402
from madb import extract                                                       # noqa: E402

# The bulk dataset is pretty-printed and each 単行本 record sits at indent 4. Nested objects sit at
# 6 and 8, so the record boundary is unambiguous without parsing the file as a whole.
_START, _END = "    {", "    },"
VOLUMES = "metadata101.json"

# A health floor for the index. metadata101 held 346,826 dated ISBNs at release 1.2.18, and a run
# that builds an index far short of that has read a truncated download rather than a smaller
# catalogue. The bibliography does not shrink.
#
# WHY THE NUMBER MOVED WHEN THE KEY DID, so it is not read as the dataset having changed. Keying
# on the thirteen-digit form took the index from 347,875 entries to 346,826. It lost 1,049 rather
# than gaining 126,318, because the ten-digit records were always indexed, under a key nothing ever
# asked for. What changed is which questions reach them. The 1,049 are books the catalogue holds
# twice, once in each form, and they are now one entry.
MIN_DATED = 200_000

_ISO = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


def records(path):
    """Every record in a MADB bulk file, one parsed dict at a time."""
    buf, inside = [], False
    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if stripped == _START:
                buf, inside = [], True
                continue
            if inside and stripped in (_END, _END[:-1]):
                inside = False
                try:
                    yield json.loads("{" + "".join(buf) + "}")
                except ValueError:
                    pass
                continue
            if inside:
                buf.append(line)


def pair(record):
    """`(isbn, date)` for one record, or None where it states neither.

    `extract.flat` and not a second reader of the same field. MADB writes a value as a string, a
    dict or a list depending on whether a reading is attached, and which half is the value is one
    decision with one place to make it (STANDING-INSTRUCTIONS §3).

    `isbn.isbn13` and not a second normaliser either, which is the fix for the fault the module
    docstring records: the key is the thirteen-digit form whichever form the catalogue printed.
    """
    number = _isbn.isbn13(extract.flat(record.get("schema:isbn", "")))
    date = extract.flat(record.get("schema:datePublished", "")).strip()
    if not number or not _ISO.match(date):
        return None
    return number, date


def build(path):
    """`{isbn: date}` over a bulk file. The FIRST date for an ISBN wins.

    An ISBN identifies one edition, so a second record carrying it is a duplicate catalogue entry
    rather than a second publication, and the file is in identifier order rather than in any order
    that would make a later record better.
    """
    out = {}
    for rec in records(path):
        got = pair(rec)
        if got:
            out.setdefault(got[0], got[1])
    return out


def healthy(index):
    """Whether an index is worth using, as `(ok, dated)`."""
    return len(index) >= MIN_DATED, len(index)


def load(cache, rebuild=False):
    """The index for a pinned release, built once and kept beside the release it came from.

    The index lives in the cache and never in the repository: it is derived from a 665 MB dataset
    that is itself uncommitted, and a 12 MB derived file in the repository would be the dataset
    arriving through the back door.
    """
    cache = pathlib.Path(cache)
    # THE FILE NAME CARRIES THE KEY FORM, so that changing the key cannot be answered out of an
    # index built under the old one. `isbn-dates.json` is keyed on whatever the catalogue printed
    # and this is keyed on the thirteen-digit form; a rebuild flag would have had to be remembered
    # by whoever ran the next pass, and a stale index answers plausibly rather than failing.
    store = cache / "isbn13-dates.json"
    if store.exists() and not rebuild:
        return json.loads(store.read_text())
    # A CACHE THAT IS NOT THERE IS A STATE AND NOT A FAULT. This is a 665 MB dataset restored from a
    # runner's cache, and a cold or expired one made `openbd` die on a FileNotFoundError every time:
    # the enrichment it does with its OWN source is worth having without the national bibliography's
    # dates beside it. Said out loud, so a run where the cache never came back is visible rather
    # than looking like a quiet day.
    if not (cache / VOLUMES).exists():
        print(f"madb: no {VOLUMES} under {cache}; ISBN dates are not enriched from the national "
              f"bibliography this run")
        return {}
    index = build(cache / VOLUMES)
    ok, dated = healthy(index)
    if not ok:
        raise SystemExit(
            f"Refusing to write: {dated} dated ISBN(s) indexed, under the {MIN_DATED} a whole "
            f"metadata101 holds. That is a truncated download rather than a smaller catalogue, "
            f"and the national bibliography does not shrink.")
    store.write_text(json.dumps(index))
    return index


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", required=True, help="a pinned MADB release directory")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--isbn", nargs="*", default=[], help="look these up and print the answer")
    a = ap.parse_args(argv)

    index = load(a.cache, a.rebuild)
    print(f"{len(index)} ISBN(s) with a publication date in {a.cache}/{VOLUMES}")
    for isbn in a.isbn:
        print(f"  {isbn}: {index.get(isbn) or 'not held'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
