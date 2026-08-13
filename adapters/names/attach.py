#!/usr/bin/env python3
"""Which rendering a row shows for its title and for its byline.

WHY THIS IS A MODULE. `feed/names.json` is keyed by name and a row is keyed by work, so something
has to join the two, and STORE-PLAN §6 needs the store to reach the SAME answer: `series.json` and
both feed files carry `work_en` and `author_en` on every row. A second implementation of the join
is the shape §3 counts seven shipped bugs from, and it would be the one that disagrees.

THE JOIN WEIGHS TWO CANDIDATES AND OFTEN COMPOSES A THIRD, which is the whole reason it is hard.
The same work reaches us spelled
勝たん！～ and 勝たん!～ and the store holds a record for each, one curated and one carrying only an
automatic reading, so an exact hit is not automatically the better one. An edition marker makes a
different key and the English attached to the plain title never reaches the row. And a byline naming
four people has no record of its own at all: it is composed from the people in it.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "names"))
import credits as _credits                                             # noqa: E402
from facts import cataloguing as _cat                                  # noqa: E402
from names import fold as _foldmod                                     # noqa: E402


def title(work, by_key, by_fold, fold):
    """The rendering a row shows for its title, or None.

    AN EXACT MATCH IS NOT AUTOMATICALLY THE BETTER ONE, which is why both candidates are weighed:
    whichever spelling the interface happened to display decided whether the work had an English
    name at all.
    """
    cands = [x for x in (by_key.get(work), by_fold.get(fold(work or ""))) if x]
    got = max(cands, key=_foldmod.fullness) if cands else None
    return inherit_edition_name(work, got, by_key, by_fold, fold)


def author(raw, by_key, by_fold, fold):
    """The rendering a row shows for its byline, or None."""
    raw = (raw or "").strip()
    return by_key.get(raw) or by_fold.get(fold(raw)) or composed(raw, by_key, by_fold, fold)


def composed(raw, exact, folded, fold):
    """One rendering for an author field naming several people, or None.

    THE COMPOSITION ITSELF IS IN adapters/names/credits.py, because two views need it and each
    solving it separately is how the works list and the updates feed came to disagree: the series
    rows composed on ` / ` and the release rows never composed at all, so the same four people
    rendered in English in one tab and in Japanese in the next. This is the store lookup and
    nothing else.

    THE FULLER RECORD WINS, which is the same rule the title join a few hundred lines below
    applies. The same person reaches us spelled two ways and the store holds a record for each,
    one curated and one carrying only an automatic reading.
    """
    def lookup(part):
        cands = [x for x in (exact.get(part), folded.get(fold(part))) if x]
        return max(cands, key=_foldmod.fullness) if cands else None

    return _credits.compose(raw, lookup)


def inherit_edition_name(work, rec, by_key, by_fold, fold):
    """`rec` with the plain title's English grafted on, where `work` is that title under a marker.

    Returns `rec` unchanged where it already has an English name, where the title carries no edition
    marker, or where the plain title has no name either. §3: the English has one producer, which is
    whatever named the plain title; this copies it onto an edition of the same work and says so.
    """
    if not work or (rec or {}).get("en"):
        return rec
    bare = _cat.without_edition_apparatus(work)
    base = by_key.get(bare) or by_fold.get(fold(bare)) if fold(bare) != fold(work) else None
    # BOTH SIDES STRIPPED THE SAME WAY, or a base carrying a tag its edition also carries is never
    # met. `without_edition_apparatus` takes the genre tag off as well as the marker, so
    # `LatteComi コミックアンソロジー【百合】（単話版）` reduced to `LatteComi コミックアンソロジー`
    # and went looking for it, while the record holding the English is written 【百合】 and all.
    # Looking the raw form up against raw keys can only work where the base has no apparatus at all.
    if (not base or not base.get("en")) and fold(bare) != fold(work):
        want = fold(bare)
        base = next((v for k, v in by_key.items()
                     if v.get("en") and fold(_cat.without_edition_apparatus(k)) == want
                     and fold(k) != fold(work)), base)
    if not base or not base.get("en"):
        # AND THE OTHER DIRECTION, because a name belongs to the WORK and not to whichever record
        # happens to hold it. Three rows were plain titles whose only named record was an edition:
        # `心の声が漏れやすいメイドさん` showed a romanisation while its 【単話版】 said The Maid
        # Whose Thoughts Slip Out. An edition's own marker is stripped on the way across, since it
        # describes that edition and not this row.
        here = fold(work)
        base = next((v for k, v in by_key.items()
                     if v.get("en") and fold(_cat.without_edition_apparatus(k)) == here
                     and fold(k) != here), None)
        if not base:
            return rec
        got = dict(rec or {})
        en = base["en"]
        for _ja, _en in _cat.EDITION_EN.items():
            en = en.replace(f" ({_en})", "")
        got["en"] = en
        got["basis"] = base.get("basis")
        got["en_forms"] = base.get("en_forms")
        got["en_of_edition_from"] = "an edition of this work"
        return got
    got = dict(rec or {})
    marker = _cat.edition_marker(work)
    got["en"] = f"{base['en']} ({marker})" if marker else base["en"]
    got["basis"] = base.get("basis")
    got["en_forms"] = base.get("en_forms")
    # SAID OUT LOUD, so a count over the shipped file can tell a name somebody wrote for this
    # edition from one carried across, and so a reader of the data is not misled about provenance.
    got["en_of_edition_from"] = bare
    return got


