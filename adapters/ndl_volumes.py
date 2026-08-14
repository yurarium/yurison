#!/usr/bin/env python3
"""ISBNs and dates for the volumes no ISBN-keyed catalogue can reach, from the National Diet Library.

WHY THIS EXISTS. Every volume row in the corpus that holds an ISBN holds a date, and every row that
holds a date holds an ISBN: the same 2,305 rows of 6,038. Dating is ISBN-keyed, openBD and the MADB
単行本 dataset and `isbndate.resolve` are all keyed on one, and BOOK☆WALKER states no ISBN on any of
5,968 volumes read. So 3,733 rows can reach none of them, and the wall is the key rather than the
catalogue.

NDL IS THE ONE PUBLIC DATABASE WITH A DIFFERENT KEY. It searches by TITLE, it is a national library,
it is free, and it holds every book published in Japan. `adapters/ndl.py` already reads its
opensearch replies for the dormancy question; this asks the same API a different question and keeps
what it says about each volume.

THE ANSWER IS AN ISBN AND THAT IS WORTH MORE THAN A DATE. A row that gains an ISBN gains openBD, the
bulk dataset and every future enrichment with it, which is why the population here is the rows
holding no ISBN rather than the rows holding no date.

WHAT IT REACHES, MEASURED ON 2026-08-12: 3,710 rows across 1,541 works whose work no bibliographic
record covers at all, and 23 rows across 8 works whose record stops short. The second is the case
the project owner found: MADB holds MURCIÉLAGO to volume 20 and NDL holds it to 28, ISBN and date
on every one.

WHAT IT CANNOT REACH is a book that was never printed. コミックシーモア states no ISBN for 1,215 of
its 1,833 works, led by ナンバーナイン and クロスフォリオ出版, digital distributors; a national
library catalogues books and there is no book. That is the floor and no pass moves it.

AND IT LAGS THE NEWEST VOLUME. MURCIÉLAGO's 29th was delivered by the shop on 2026-07-24 and the
catalogue holds to the 28th, 2026-01. A monthly run picks each up a few months late, which is what a
national library is.

  ./ndl_volumes.py                  ask about the works whose rows hold no ISBN
  ./ndl_volumes.py --limit 40       ask about the first 40 of them
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import population  # noqa: E402

import ndl                                                              # noqa: E402
import paths as _paths                                                  # noqa: E402

#: Where the answers are kept. A capture rather than a source record: what NDL states about a volume
#: is applied to a row another catalogue already holds, the way openBD's answer is, so it is
#: enrichment and not a record of its own.
OUT = "data/queue/ndl-volumes.yaml"


def wanted(series, works):
    """`[{work, author, id, missing}]` for the works whose reachable volume rows hold no ISBN.

    ORDERED BY HOW MUCH IS MISSING, so a run stopped early has answered the most it could. A work
    with no author is skipped and counted: the author agreement is the only thing standing between
    a title search and every book in Japan, and `ndl.volumes` refuses without one.
    """
    by_id = {w.get("work_id"): w for w in works or () if w.get("work_id")}
    out = []
    for row in series or ():
        ids = [i for block in (row.get("print") or ()) for i in (block.get("work_ids") or [])]
        missing = sum(1 for i in ids for v in (by_id.get(i) or {}).get("volumes") or ()
                      if not (v.get("isbn") or v.get("editions")))
        if missing and (row.get("author") or "").strip() and (row.get("work") or "").strip():
            out.append({"work": row["work"], "author": row["author"].strip(),
                        "id": row.get("id"), "missing": missing})
    return sorted(out, key=lambda x: (-x["missing"], x["work"]))


def record(xml, author):
    """`[{volume, isbn, published}]` from one reply, dated in the corpus's form."""
    out = []
    for vol in ndl.volumes(xml, author):
        date = ndl.issued_date(vol.get("issued"))
        out.append({"volume": vol.get("volume") or None, "isbn": vol.get("isbn"),
                    "published": date or None, "publisher": vol.get("publisher") or None,
                    "title": vol.get("title") or None})
    return out


def _key(number):
    """A volume number as it compares: `01` and `1` are one volume, `上` is itself."""
    n = str(number or "").strip()
    if not n:
        return None
    return str(int(n)) if n.isdigit() else n


def apply(rows, volumes):
    """Fill the ISBN and the date on the volume rows NDL answers for. Returns how many it filled.

    KEYED ON THE VOLUME NUMBER, because that is what both sides state and neither side states an
    ISBN we could key on: this exists precisely because our rows have none. A row NDL does not
    number, or numbers in a form ours does not, is left alone.

    IT FILLS AND NEVER OVERWRITES. A row that already holds an ISBN was answered by a catalogue
    that keyed on one, and a second opinion about a book is `isbndate.resolve`'s question rather
    than this pass's. The same for a date: what is filled here is a silence.
    """
    held = {}
    for row in rows or ():
        key = _key(row.get("volume"))
        if key and row.get("isbn"):
            held.setdefault(key, row)
    filled = 0
    for vol in volumes or ():
        got = held.get(_key(vol.get("number")))
        if not got or vol.get("isbn") or vol.get("editions"):
            continue
        vol["isbn"] = got["isbn"]
        vol["isbn_source"] = "ndl"
        if got.get("published") and not vol.get("published"):
            vol["published"] = got["published"]
            vol["published_basis"] = "national-library"
            vol["published_source"] = "ndl"
        filled += 1
    return filled


def main(argv=None):
    import argparse
    import json
    import urllib.parse

    import net as _net

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # THE STORE BY DEFAULT AND A FILE ONLY WHEN ASKED, §13.
    ap.add_argument("--series", default=None,
                    help="read the work rows from this series.json instead of from the store")
    ap.add_argument("--works", default="data/build/works.json")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--cache", default=str(_paths.cache("ndl-cache")))
    ap.add_argument("--max-age", type=int, default=90, dest="max_age")
    a = ap.parse_args(argv)

    import yaml
    series = population.series(a.series)
    works = json.loads(pathlib.Path(a.works).read_text()).get("works") or []
    todo = wanted(series, works)
    if a.limit:
        todo = todo[:a.limit]
    doc = yaml.safe_load(pathlib.Path(a.out).read_text()) if pathlib.Path(a.out).exists() else {}
    held = (doc or {}).get("works") or {}

    def _save():
        pathlib.Path(a.out).write_text(yaml.safe_dump(
            {"source": "ndlsearch.ndl.go.jp", "role": "volume-record",
             "source_kind": "national-library",
             "note": "Volume records for works whose rows hold no ISBN. A record counts only where "
                     "NDL's creator agrees with the author we hold, because a title search matches "
                     "every book in Japan. Dates are NDL's own, read into the corpus's form.",
             "works": held}, allow_unicode=True, sort_keys=True, width=100))

    # THROUGH `net.py`, which owns the pause a host is asked at, the cache key, the redirect and
    # the backoff on a 503. A module with its own urlopen has none of them, and this one is over a
    # thousand requests to one host.
    asked = answered = 0
    for job in todo:
        if job["work"] in held:
            continue
        url = ("https://ndlsearch.ndl.go.jp/api/opensearch?cnt=100&title="
               + urllib.parse.quote(job["work"]))
        got = _net.fetch(url, a.cache, max_age_days=a.max_age)
        xml = got.text
        if not xml:
            print(f"  skip {job['work'][:26]}: {got.outcome if hasattr(got, 'outcome') else 'no body'}")
            continue
        asked += 1
        got = record(xml, job["author"])
        held[job["work"]] = {"author": job["author"], "id": job.get("id"),
                             "missing": job["missing"], "volumes": got}
        if got:
            answered += 1
        # WRITTEN AS IT GOES. A full run is over a thousand requests and the better part of an
        # hour; a pass that only writes at the end throws all of it away when anything interrupts,
        # and every entry already held is skipped above, so a re-run resumes rather than repeats.
        if asked % 25 == 0:
            _save()

    _save()
    print(f"NDL volumes: {len(todo)} work(s) wanted, {asked} asked, {answered} answered")
    print(f"  held: {len(held)} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
