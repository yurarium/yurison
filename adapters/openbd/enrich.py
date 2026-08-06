#!/usr/bin/env python3
"""Enrich the corpus from openBD, storing only licence-safe derived fields.

openBD's terms permit use for 本の紹介 purposes but forbid transferring use rights to third
parties, and REQUIREMENTS §3 therefore rules out republishing bulk openBD payloads. So this adapter
diverges from the usual source-layer rule: **raw payloads stay in a local cache outside the repo,
and only a derived projection is committed** — existence, confirmed publication date, and a cover
URL where openBD supplies one.

No synopsis (内容紹介) or review text is ever stored; that is copyrightable and forbidden by §2.

TWO CATALOGUES, AND THE ONE RULE THAT DECIDES WHICH ANSWERS. openBD is a publisher's own JPRO
registration and it is thin for older books: it held a date for 483 of the 1,310 ISBNs in the
corpus on 2026-08-06, and for 10 of 23 ISBNs read off コミックシーモア. `madb/isbn_dates.py` reads
the national bibliography's answer for an ISBN out of the pinned bulk release at no cost and no
request, and it held 22 of those same 23. So this pass asks both.

**MADB's answer is never written back over a record that came from MADB.** That is the whole of
the rule and it is not fussiness. `madb/extract.py` reads `schema:datePublished` off the very
records `isbn_dates.py` indexes, so for a work in `data/source/madb/` the two are one fact with two
producers, and an enrichment layer restating it would look like a second catalogue agreeing when
it is the same file read twice (STANDING-INSTRUCTIONS §3). MADB is consulted for a volume whose
primary record states no date, where its answer fills a hole, and for a work whose primary record
came from somewhere else.

WHAT THAT IS WORTH TODAY, STATED SO IT IS NOT MISTAKEN FOR A RESULT. Every ISBN-bearing record in
the corpus is MADB's own, and MADB holds no date for any of the 19 volumes its own extraction left
undated, so the MADB half of this pass supplies nothing at present. The run prints the number, and
a pass that supplied nothing says so rather than reading as a pass that worked. It supplies
something the moment a work source that is not the bibliography states an ISBN.

Usage:  enrich.py --cache $YURI_CACHE/openbd-cache/openbd.json \
                  --works data/source/madb --out data/source/openbd --retrieved 2026-08-01 \
                  --madb-cache $YURI_CACHE/madb-cache/1.2.18
"""
import argparse, glob, json, pathlib, sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from madb import isbn_dates                                                    # noqa: E402

# Health assertion: openBD resolved ~77% of this corpus on 2026-08-01. A large drop means the API
# changed or the fetch failed, and the adapter must not write a thinned record set (§6).
MIN_HIT_RATE = 0.50

# Which catalogue a stored date came from, in the vocabulary `cmoa_volumes.PREFERENCE` already
# uses for the same two answers. One set of names, so whatever reads these records does not have
# to learn a second.
OPENBD, MADB = "openbd-registration", "madb-tankobon"


def yaml_str(t):
    return '"' + str(t).replace("\\", "\\\\").replace('"', '\\"') + '"'


def pubdate(raw):
    """openBD gives YYYYMMDD or YYYYMM. Normalise to ISO; never invent precision we lack."""
    d = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if len(d) >= 8:
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    if len(d) >= 6:
        return f"{d[:4]}-{d[4:6]}"
    return d[:4] if len(d) == 4 else ""


def answer(volume, record, madb, primary_source):
    """What a catalogue holds for one volume, as `(date, basis)`, or `("", "")` for silence.

    `record` is openBD's answer and may be None, which is how openBD says it holds nothing.
    `madb` is `isbn_dates`' index, which may be empty when the pass runs without a release pinned.

    openBD is asked first because the registration is what this layer exists to carry, and MADB
    only where openBD is silent. The guard on MADB is the docstring's rule: a work whose primary
    record came from MADB gets MADB's answer only for a volume that record failed to date. Filling
    a hole is worth doing; restating the same file's own answer as though a second catalogue had
    confirmed it is the two-producers bug this project meets more than any other.
    """
    isbn = (volume.get("isbn") or "").strip()
    if not isbn:
        return "", ""
    date = pubdate(((record or {}).get("summary") or {}).get("pubdate"))
    if date:
        return date, OPENBD
    if primary_source == "madb" and volume.get("published"):
        return "", ""
    held = (madb or {}).get(isbn) or ""
    return (held, MADB) if held else ("", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--works", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--madb-cache", default=None,
                    help="a pinned MADB release directory, for ISBNs openBD does not hold")
    a = ap.parse_args()

    cache = json.loads(pathlib.Path(a.cache).read_text())
    madb = isbn_dates.load(a.madb_cache) if a.madb_cache else {}
    files = sorted(glob.glob(f"{a.works}/*.yaml"))
    if not files:
        sys.exit(f"no source records under {a.works}")

    all_isbns = []
    for f in files:
        all_isbns += [v["isbn"] for v in (yaml.safe_load(open(f)).get("volumes") or []) if v.get("isbn")]
    # HOW MANY OF THIS CORPUS'S ISBNs THE CACHE ANSWERS FOR, not how big the cache is. The measure
    # was `len(cache)` over the corpus, which is a ratio between two different populations: the
    # cache is shared with the name passes and the retailer captures, and once it grew past the
    # corpus the floor cleared itself whatever openBD had said. A floor that cannot fail is the
    # failure it was built to catch (STANDING-INSTRUCTIONS §4).
    wanted = set(all_isbns)
    resolved = sum(1 for i in wanted if cache.get(i))
    hit_rate = resolved / max(len(wanted), 1)
    if hit_rate < MIN_HIT_RATE:
        sys.exit(f"HEALTH: openBD resolved {hit_rate:.1%} of ISBNs (< {MIN_HIT_RATE:.0%}). Refusing to write.")

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.yaml"):
        f.unlink()

    written = covers = confirmed = 0
    by_basis = {OPENBD: 0, MADB: 0}
    for f in files:
        w = yaml.safe_load(open(f))
        primary = w.get("source") or "madb"
        rows = []
        for v in w.get("volumes") or []:
            rec = cache.get(v.get("isbn", ""))
            date, basis = answer(v, rec, madb, primary)
            # A row is kept where EITHER catalogue said something. Keying it on openBD alone lost
            # the volumes openBD has never carried, which are the ones a second catalogue is for.
            if not rec and not date:
                continue
            s = (rec or {}).get("summary", {}) or {}
            rows.append((v["isbn"], date, basis, (s.get("cover") or "").strip(), bool(rec)))
        if not rows:
            continue
        L = [
            "# Derived from openBD. Raw payloads are NOT committed — openBD forbids transferring",
            "# use rights to third parties (REQUIREMENTS §3). No synopsis text is stored (§2).",
            "source: openbd",
            f"retrieved: {a.retrieved}",
            f"work_id: {w['work_id']}",
            "record_type: volume_enrichment",
            "volumes:",
        ]
        for isbn, date, basis, cover, in_openbd in rows:
            L.append(f"  - isbn: {yaml_str(isbn)}")
            L.append(f"    openbd: {'present' if in_openbd else 'absent'}")
            if date:
                L.append(f"    published: {date}")
                # WHICH CATALOGUE SPOKE, on the row rather than inferred from the directory it is
                # in. A reader that took every date here for openBD's would have been right until
                # the day this pass gained a second source, and wrong silently afterwards.
                L.append(f"    published_basis: {basis}")
                confirmed += 1
                by_basis[basis] += 1
            if cover:
                # Referenced live from openBD's host, never cached or committed (§2, §4).
                L.append(f"    cover_url: {yaml_str(cover)}")
                covers += 1
        L.append("")
        (out / f"{w['work_id']}.yaml").write_text("\n".join(L))
        written += 1

    print(f"openBD hit rate : {hit_rate:.1%} ({resolved}/{len(wanted)} ISBNs)")
    print(f"works enriched  : {written}/{len(files)}  -> {out}")
    print(f"dates confirmed : {confirmed}")
    print(f"  from openBD   : {by_basis[OPENBD]}")
    # Printed even at nought, because a second source that answered nothing and a second source
    # nobody wired up look identical from the output otherwise (STANDING-INSTRUCTIONS §4).
    print(f"  from MADB     : {by_basis[MADB]}"
          + ("" if a.madb_cache else "   (no release pinned; --madb-cache was not given)"))
    print(f"cover URLs      : {covers}")
    if covers < written * 0.05:
        print("NOTE: openBD supplies almost no covers for this publisher. The site is effectively")
        print("      text-only for this corpus — see docs/MADB.md and REQUIREMENTS §2.")


if __name__ == "__main__":
    main()
