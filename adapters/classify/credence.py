#!/usr/bin/env python3
"""How much each piece of evidence for a yuri classification is worth, and in what order.

The work page lists every source that speaks to whether a work is yuri, strongest first. The order
is decided here and the page only sorts by the number this module states. Deciding it in the
renderer would put a judgement the documents already settle into the one place with no access to
the source records, and it would make the same fact have two producers, which is the shape behind
seven shipped bugs in this project (STANDING-INSTRUCTIONS §3).

THE ORDER, AND THE CLAUSE EACH RANK WAS READ OUT OF.

  1 imprint       The publisher's own imprint, printed on the book. DEFINITIONS §4 names the
                  imprint among the things that establish `marketing_label: yuri`, and the source
                  that records it is the national bibliography, Tier A in REQUIREMENTS §1. Nothing
                  else here is both the publisher's own act and catalogued by an authority.
  2 platform-tag  The same publisher's web arm applying a tag to its own title. §4 counts
                  platform-side labelling, so this is a label and not a comparator. It ranks below
                  the imprint because it is a field on a page the platform rewrites at will and
                  because REQUIREMENTS §1 puts platforms in Tier B.
  3 magazine      `marketing_label: magazine`, which §4 calls deliberately weaker than `yuri` and
                  `gl` for attributing the venue's identity to the work.
  4 shelf         A licensed retailer's yuri shelf. DEFINITIONS §2 admits it as a comparator,
                  presumptive and rebuttable; §4 says twice that it is never a `marketing_label`;
                  REQUIREMENTS §1 puts a reference site in Tier C.
  5 listing       Any other comparator. §2 has a retailer standing above an aggregator without
                  becoming publisher-side, so a site that neither publishes the work nor sells it
                  sits at the bottom of the same branch.

RANKS 3 AND 5 MATCH NOTHING IN THE CORPUS TODAY. They are here because §4 defines four label
values and §2 defines two kinds of comparator, and a value the ranking cannot place would reach
the page in whatever order the loop happened to build it. `rank()` raises on an unknown kind for
the same reason: a missing rank must stop the build rather than sort silently to the top.

THE TERM IS A QUOTATION. `百合・GL` and `百合` and an imprint name are visibly different claims and
a reader weighs them without help, so the page prints the source's own word and translates none of
it. That also means a row with nothing quotable is not emitted: a label with no imprint behind it
and a shelf whose notation carries no term would both put the reader in front of a claim they
cannot read, and the build counts them instead.

WHOSE NAME GOES ON THE ROW. The claim belongs to whoever made it, which is not always whoever we
read it from. An imprint is the publisher's act recorded by the bibliography, so the row names the
publisher and the address points at the bibliography page it was read from. Taking the address for
the claimant is how 824 works came to sit under a heading reading "Sold at" with the national
database as the shop; see `_shop_address` in build.py.

Offline and pure. Every function takes a record and returns rows.
"""
import re

# Rank 1 is the strongest. The reasoning for each is in the docstring above; the string here is
# what the emitted row carries so a reader of the data can find the clause without this file.
RANK = {"imprint": 1, "platform-tag": 2, "magazine": 3, "shelf": 4, "listing": 5}

RULE = {
    "imprint": "DEFINITIONS §4 imprint; REQUIREMENTS §1 tier A",
    "platform-tag": "DEFINITIONS §4 platform-side; REQUIREMENTS §1 tier B",
    "magazine": "DEFINITIONS §4 magazine, weaker than yuri and gl",
    "shelf": "DEFINITIONS §2 comparator, never §4; REQUIREMENTS §1 tier C",
    "listing": "DEFINITIONS §2 comparator below a retailer",
}

# What kind of party is speaking. The page translates these five words and nothing else in the
# table, because everything else is a proper noun or a quotation.
TYPE = {"imprint": "publisher", "platform-tag": "platform", "magazine": "magazine",
        "shelf": "retailer", "listing": "listing"}

# Where a label read from this source came from. A bibliography records the publisher's imprint;
# a platform states its own tag. Both are §4 labelling and they are not the same claim.
BIBLIOGRAPHIC = {"madb", "madb-title", "openbd", "openbd-jpro", "ndl"}
PUBLISHER_SIDE = {"publisher", "ichijinsha"}
PLATFORM_SIDE = {"kadokomi", "gigaviewer", "comicfuz", "nicovideo", "pixivcomic", "comici",
                 "ganganonline", "webpages"}

# A comparator that sells the licensed edition, which DEFINITIONS §2 puts above an aggregator.
RETAILERS = {"bookwalker.jp", "cmoa.jp"}

# What a source is called where its own name is not what the record writes. A host is a workable
# name for a site nobody has given one to, so anything absent here falls through to the raw value.
SOURCE_NAME = {
    "bookwalker.jp": "BOOK☆WALKER",
    "cmoa.jp": "コミックシーモア",
    "bookwalker": "BOOK☆WALKER",
    "madb": "メディア芸術データベース",
    "madb-title": "メディア芸術データベース",
    "openbd": "openBD",
    "ndl": "国立国会図書館サーチ",
}

# 百合 and GL are the words a Japanese source uses for this. GL is anchored because it is two
# letters and would otherwise match inside an unrelated tag.
YURI_TERM = re.compile(r"百合|ガールズ・?ラブ|^(?:GL|ＧＬ)$", re.I)

# AN IMPRINT NAME THAT CARRIES THE CLAIM. Matched loosely because MADB spells 百合姫 in Latin as
# often as in kana: Yurihime comics, Yuri-hime comics, YURIHIME COMICS.
#
# WHY THE TEST EXISTS AT ALL, which took reading the extractor to find. `adapters/madb/extract.py`
# selects VOLUMES whose schema:brand is one of the 百合姫 imprints and then writes the SERIES
# record, whose own brand may be the umbrella line: 117 works are stored with `imprint:
# IDコミックス` and carry `marketing_label: yuri` on the strength of a volume brand the record does
# not hold. Quoting IDコミックス as the reason a work is filed as yuri would show a reader a term
# that makes no such claim, and it is 一迅社's general comics line rather than its yuri one. So
# those rows are not emitted, and build.py counts them: the fix is for the extractor to store the
# brand it selected on, and until it does the honest answer is to say nothing here.
YURI_IMPRINT = re.compile(r"百合|ガールズ・?ラブ|yuri|\bGL\b", re.I)

# `tag 14 (百合)` and `genre 37 (百合・GL)`: the shop's internal identifier, then its own word for
# the shelf. Only the second is worth showing, and it is shown unaltered.
_SHELF_ID = re.compile(r"^\s*(?:tag|genre|category|shelf|list)\s*[0-9０-９]+\s*", re.I)
_WRAPPED = re.compile(r"^[（(](.+)[）)]$")


def rank(kind):
    """The credence rank of an evidence kind, 1 being the strongest.

    Raises on a kind with no rank. A caller that met one has added a kind here without deciding
    where it sits, and sorting it silently to the front of the strongest-first table would state
    something nobody decided.
    """
    if kind not in RANK:
        raise ValueError(f"no credence rank for evidence kind {kind!r}; see RANK in this module")
    return RANK[kind]


def shelf_term(shelf):
    """The shop's own word for a shelf, out of the record's `tag 14 (百合)` notation, or None."""
    s = str(shelf or "").strip()
    if not s:
        return None
    s = _SHELF_ID.sub("", s).strip()
    m = _WRAPPED.match(s)
    return (m.group(1).strip() if m else s) or None


def stated_terms(tags):
    """Which of a platform's own tags are the yuri claim, in the order the record wrote them."""
    return [str(t).strip() for t in (tags or []) if YURI_TERM.search(str(t).strip())]


def named(value):
    """The display name for a source key or comparator host."""
    key = str(value or "").strip()
    return SOURCE_NAME.get(key.lower(), key)


def _row(kind, source, term, retrieved, url):
    # `rule` is NOT on the row. It is a property of the kind and identical across every row of
    # that kind, so it is written once per file instead of 2,492 times, which is 146 KB of
    # series.json for a string no reader sees. RULE above is what a build writes out.
    return {"kind": kind, "rank": rank(kind), "type": TYPE[kind],
            "source": source, "term": term,
            "read": str(retrieved or "")[:10] or None,
            **({"url": url} if url else {})}


def label_row(rec, platform=None):
    """The categorisation row a record's own `marketing_label` supports, or None.

    `platform` is the display name of the site the record was read from, needed only when the
    label is the platform's own tag. A print record names its publisher and needs nothing.
    """
    label = rec.get("marketing_label")
    if not label or label == "none":
        return None
    basis = rec.get("marketing_label_basis") or {}
    src = str(basis.get("source") or "").strip()
    if label == "magazine":
        kind, term = "magazine", str(rec.get("venue") or rec.get("magazine") or "").strip()
        source = str(rec.get("publisher") or "").strip()
    elif src in PLATFORM_SIDE:
        kind = "platform-tag"
        term = "・".join(stated_terms(rec.get("tags")))
        source = str(platform or named(src)).strip()
    elif src in BIBLIOGRAPHIC or src in PUBLISHER_SIDE:
        kind = "imprint"
        term = str(rec.get("imprint") or "").strip()
        if not YURI_IMPRINT.search(term):
            return None
        source = str(rec.get("publisher") or "").strip()
    else:
        return None
    if not term or not source:
        return None
    return _row(kind, source, term, basis.get("retrieved"), basis.get("url"))


def shelf_rows(rec):
    """One row per comparator that admitted this work under DEFINITIONS §2."""
    out = []
    for entry in rec.get("admitted_by") or []:
        host = str(entry.get("comparator") or "").strip().lower()
        term = shelf_term(entry.get("shelf"))
        if not host or not term:
            continue
        kind = "shelf" if host in RETAILERS else "listing"
        out.append(_row(kind, named(host), term, entry.get("retrieved"), entry.get("url")))
    return out


def rows(rec, platform=None):
    """Every categorisation row a single source record supports, strongest first."""
    got = shelf_rows(rec)
    one = label_row(rec, platform)
    if one:
        got.append(one)
    return order(got)


def order(got):
    """Strongest first, then by the source's name so a redraw cannot reorder equal rows."""
    seen, out = set(), []
    for r in sorted(got, key=lambda x: (x["rank"], x["source"], x["term"])):
        key = (r["kind"], r["source"], r["term"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
