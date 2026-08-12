#!/usr/bin/env python3
"""Which work we hold a shop's capture row is about.

WHY THIS EXISTS. コミックシーモア states how many volumes a series has, correctly, for 1,831 works,
and none of it reaches a work we hold: the capture feeds the admitted queue and the queue is about
works we do NOT hold yet. So the shop said MURCIÉLAGO had 29 volumes while the interface said 32,
and nothing in the pipeline was in a position to notice, because nothing joined the two.

A TITLE IDENTIFIES NOTHING, and `shopfinal.py` records the case that settles it: `トワ・エ・モア` is
a 1996 コンパス anthology and a 2024 講談社 series at once. So the join is asked in two ways and
neither of them is a bare title.

  AN ISBN IDENTIFIES AN EDITION. Where a volume of ours and a volume of theirs carry the same ISBN
  it is the same book, and there is nothing further to argue about. 543 of the 1,831 rows join this
  way and not one of them reaches two works.

  A TITLE AND A HOUSE TOGETHER IDENTIFY A WORK. The title says which work and the house says whose,
  which is the part `トワ・エ・モア` was missing. 751 more join this way, again with no row reaching
  two works. Either seat answers, because MADB files a distributor where a shop files a publisher
  and the question here is whether the same company is behind both records.

WHAT IS DECLINED, AND WHAT IT COSTS. A title that agrees where the house does not would add 35
rows. They are almost all クロスフォリオ出版 and ナンバーナイン, digital distributors, against works
whose own records name somebody else, and the titles are `放課後`, `先生`, `少女レター`: exactly the
shape the ISBN rule exists to refuse. 35 rows is not worth the first wrong join, so they are left
unjoined and counted as unjoined.

502 rows join by neither route. Most are works we do not hold, which is what the admitted queue is
for, and this module says so by returning nothing rather than by guessing.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import isbn as _isbn                                                    # noqa: E402
from facts import namekey                                              # noqa: E402

#: Which seats on a print block name a company. A distributor is a publisher in another seat.
HOUSE_SEATS = ("publisher", "distributor")

#: A shop row selling something other than the work's volumes. See `counts_volumes`.
_EDITION = re.compile(r"お試し版|試し読み|分冊版|単話")


def _fold(s):
    return namekey.fold(str(s or ""))


def index(series, works):
    """`{isbn: …, house: …}`, the two ways a shop row can reach a series row.

    Built from the shipped collections rather than from the source records, because what a reader
    is shown is what a shop's count should be compared against. A row with no print block has no
    volumes to compare and is not indexed.
    """
    by_work = {w.get("work_id"): w for w in works or () if w.get("work_id")}
    out = {"isbn": {}, "house": {}}
    for r in series or ():
        rid = r.get("id")
        blocks = r.get("print") or []
        if not rid or not blocks:
            continue
        for wid in (i for b in blocks for i in (b.get("work_ids") or [b.get("work_id")]) if i):
            for v in (by_work.get(wid) or {}).get("volumes") or ():
                key = _isbn.isbn13(v.get("isbn") or "")
                if key:
                    out["isbn"].setdefault(key, set()).add(rid)
        title = _fold(r.get("work"))
        if not title:
            continue
        for b in blocks:
            for seat in HOUSE_SEATS:
                house = _fold(b.get(seat))
                if house:
                    out["house"].setdefault((title, house), set()).add(rid)
    return out


def match(row, idx):
    """`(series_row_id, route)` for one shop capture row, or `(None, reason)`.

    `route` is `isbn` or `house`; a row that reaches no work answers `unjoined` and a row that
    reaches two answers `ambiguous`. AMBIGUITY IS NOT RESOLVED HERE and is not silently taken: two
    works answering to one shop row is a question about our own records, and picking one of them
    would bury it. Neither route reaches two works on the capture this was written against, so a
    row that starts doing so is news.
    """
    hits = set()
    for v in row.get("volumes") or ():
        key = _isbn.isbn13(v.get("isbn") or "")
        if key:
            hits |= idx["isbn"].get(key, set())
    if hits:
        return (next(iter(hits)), "isbn") if len(hits) == 1 else (None, "ambiguous")
    title, house = _fold(row.get("shelf_title") or row.get("title")), _fold(row.get("publisher"))
    # THE SHOP'S PUBLISHER ONLY, against either of our seats. A shop's `imprint` is the line the
    # book is in rather than the company behind it, and asking with it would join 百合姫コミックス
    # to whatever 一迅社 publishes.
    if title and house:
        seen = idx["house"].get((title, house), set())
        if seen:
            return (next(iter(seen)), "house") if len(seen) == 1 else (None, "ambiguous")
    return None, "unjoined"


def counts_volumes(row):
    """Whether this shop row is a claim about how long a work is.

    A SHOP SELLS EDITIONS AND THIS COMPARES WORKS. コミックシーモア files
    `まんがの作り方【お試し版】` as a series of its own beside `まんがの作り方`, and it holds one
    volume where the work has eight. Both carry the work's ISBN, so both join, and reading the
    sample's count as the work's turned an agreement into a disagreement of 8 against 1. 単話 and
    分冊版 are the same thing at the other end: chapters sold singly, which `bwingest.CHAPTERWISE`
    already refuses to count as 巻 for exactly this reason.
    """
    return not _EDITION.search(str(row.get("shelf_title") or row.get("title") or ""))


def joined(rows, idx):
    """`{series_row_id: shop_row}` for the works exactly one shop row speaks about.

    ONE ROW PER WORK OR NONE. Six works are reached by two rows each after the samples are out:
    `春夏秋冬` and `春夏秋冬 完全版`, `Qualia -Envy-` and `Qualia -Jealousy-`, two 編 of
    `ネイルちゃんと深爪さん。`. Those are different products under one identity, so the shop is not
    stating how long the WORK is, and taking either count would be picking one at random. They are
    declined for the same reason `match` declines an ambiguous ISBN.
    """
    hits = {}
    for row in rows or ():
        if not counts_volumes(row):
            continue
        rid, _route = match(row, idx)
        if rid:
            hits.setdefault(rid, []).append(row)
    return {rid: rs[0] for rid, rs in hits.items() if len(rs) == 1}
