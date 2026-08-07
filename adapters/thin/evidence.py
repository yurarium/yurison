#!/usr/bin/env python3
"""Which shelf-admitted works have nothing but the shelf behind them, and what else we already hold.

WHY THIS EXISTS. DEFINITIONS §2 admits a work on a licensed retailer's yuri shelf, "presumptive and
rebuttable". 1,837 of 3,076 works in the corpus rest on a shelf and nothing else, so the
presumption is now most of the database and the word *rebuttable* has had no mechanism behind it.
The operator found one entry that does not belong (`w01734`) and one query that narrows without
knowing the answer first: imprint concentration. A yuri line contributes dozens of works, so an
imprint contributing one or two, on a single shelf row, has nothing supporting it. That returns
296, which is too many to read.

`candidates` reproduces that query and `signals` says what else the corpus already holds about each
one. Nothing here decides that a work is not yuri. DEFINITIONS §7 governs: this asks whether any
source DESIGNATES the work, and whether anything a source says contradicts the one shelf that does.

WHAT EACH SIGNAL IS FOR, AND WHAT IT IS WORTH. Measured on the 296, with the three works the
operator has judged as the calibration set: `w01734` is not yuri, `w00106` and `w00117` are.

  title_term        The publisher's own title carries 百合, ゆり, リリィ, レズ or GL. §4 counts the
                    publisher applying the word, and a title is the most public place it can apply
                    it. 43 of 296. Silent on all three calibration works, so it neither fires nor
                    over-fires there; it is the cheapest corroboration in the set.
  imprint_term      The imprint carries the word. §4 names the imprint outright, and DEFINITIONS §2
                    adds that an imprint reaching us through a shop still counts on its own merits.
                    3 of 296, all of them 宙出版's 百合コミックス line or コミック百合姫 itself.
  antenna           Web漫画アンテナ's own 百合 tag names the work. A second comparator under §2,
                    independent of both shops. 30 of 296, and it is what separates the calibration
                    set: it names `w00106` and `w00117` and does not name `w01734`.
  platform_declined The work sits on a platform whose 百合 tag we hold ENUMERATED, and the tag does
                    not name it. カドコミ is the only such platform: 350 works tagged, against 372
                    of our works hosted there. Read the caveat below before weighing it.
  other_category    The imprint names a category that is not yuri: BL, TL, ero, TS, horror. 5 of
                    296, and publisher-side, so the publisher stated it and nobody inferred it.
  container         The row may be a bundle or a periodical rather than a work: 〜シリーズ, 合本版,
                    総集編, 表紙集, ファンブック. 13 of 296. This is a finding about the record and
                    not about the manga, and it is kept apart from the designation question.
  prominent         Four volumes or forty chapters. Absence of any other yuri designation is worth
                    more for a work many people have seen than for a single-volume one nobody has.
                    It is a weak ordering term and it over-fires: オクターヴ, 桜Trick and
                    霧尾ファンクラブ are all prominent and all plainly yuri.
  author_in_field   Some credited person has ANOTHER corpus work carrying publisher- or
                    platform-side yuri evidence. It says the author works in the field rather than
                    anything about this book, so it lowers suspicion and never settles it.

SIGNALS TESTED AND DROPPED, so nobody re-derives them.

  BOOK☆WALKER's 男性向け facet. The capture stores it per row and nothing had read it, and a 男性向け
  flag on a yuri-shelved work looked like a discriminator we already owned. It is not: the facet is
  on 1,120 of the 2,443 rows on the shelf, 46%, and on 82 of the 221 candidates that came from that
  shelf, 37%. It is close to a coin flip in both populations and it is FALSE on `w01734`, so it
  fails the one case we know the answer to. Recorded on each row and scored at zero.

  Which listing a row came from. The capture keeps `manga` and `warensai` apart and records the
  page. All 221 BOOK☆WALKER candidates came from `manga`; no 話・連載 row reached the corpus as a
  work at all, so the field cannot separate anything here.

  Cross-retailer agreement, measured by the operator before this ran: 20 works appear on both
  shops' shelves, so absence from the other shop carries no information.

WHERE THIS CHECK IS BLIND, per STANDING-INSTRUCTIONS §14b. `platform_declined` cannot discover
anything within the 296, because the query already selected works with exactly ONE evidence row and
カドコミ's 百合 tag would have produced a second. Every カドコミ-hosted candidate is absent from that
tag BY CONSTRUCTION. What the signal adds is an ordering: it marks the works where a publisher-side
witness existed, had the opportunity, and filed the work under something else. The substance is in
what the platform filed it under instead, which `sources.py` reads off the platform's own page, and
that is a fact the selection never consulted. The tag is also not exhaustive: 115 of our 372
カドコミ works are outside it, so its silence alone rebuts nothing.

Offline and pure. Every function takes rows and returns rows.
"""
import collections
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from classify import credence  # noqa: E402

# THE PUBLISHER'S OWN WORD, in the title or the imprint. Written narrowly, because the counter-cases
# are common enough to have been in the first draft's output:
#   小百合 and 百合子 are personal names. 小百合さんの妹は天使 is a work about a woman called Sayuri.
#   ゆりかご is a cradle, and ユリウス is Julius.
#   ガールズ on its own is not ガールズラブ. 和太鼓†ガールズ matched the first draft and is a drumming
#   comedy; the word has to be the compound.
# A hit here is the publisher naming the genre, which is what §4 asks for. It is not proof about
# content, and this module never claims it is.
TERM = re.compile(r"(?<!小)百合(?!子)|(?<![ゆか])ゆり(?!かご)|ユリ(?!ウス)|リリィ|リリー|レズ"
                  r"|ガールズ・?ラブ|女の?子同士|(?<![A-Za-z])GL(?![A-Za-z])")

# A category the publisher named that is not this one. `BL` needs its own boundary because Python's
# \b treats カ as a word character, so \bBL\b never matches inside `Kobunsha BLコミックシリーズ`.
OTHER_CATEGORY = re.compile(r"(?<![A-Za-z])BL(?![A-Za-z])|ボーイズラブ|ERO|ティーンズラブ"
                            r"|(?<![A-Za-z])TL(?![A-Za-z])|ホラー|TSコミックス|アダルト|官能")

# A row that may not be one work. Kept apart from the designation question deliberately: a magazine
# or a shop's bundle filed as a work is a fault in the record, and DEFINITIONS §2 has nothing to say
# about it. `シリーズ` is anchored to the end because it is ordinary inside an imprint name
# (MFコミックス　ジーンシリーズ) and only means a bundle when it is what the row is called.
CONTAINER = re.compile(r"シリーズ$|合本版|総集編|表紙集|ファンブック")

# Publisher- and platform-side evidence, which is what `author_in_field` looks for on a person's
# other work. Derived from adapters/classify/credence.py rather than written out, because a check
# and its subject each holding a private copy of one table is the drift §14b describes, and that
# module is where DEFINITIONS §2 and §4 were read into numbers.
PUBLISHER_SIDE_RANK = credence.rank("magazine")


def evidence(row):
    return row.get("evidence") or []


def imprints(row):
    """Every distinct imprint the row's print editions name."""
    return sorted({p["imprint"] for p in (row.get("print") or []) if p.get("imprint")})


def shelf_only(rows):
    """Works carrying evidence, all of which is a retailer's shelf."""
    return [r for r in rows if evidence(r)
            and all(e.get("kind") == "shelf" for e in evidence(r))]


def imprint_frequency(rows):
    """How many of `rows` each imprint appears on, counted once per work.

    Counted over the shelf-only population rather than the whole corpus, because the question is
    whether the imprint has a yuri line ON THE SHELVES. 一迅社's 百合姫コミックス is dozens of rows
    either way; an imprint with one row here and forty elsewhere is not contributing to this shelf.
    """
    return collections.Counter(i for r in rows for i in imprints(r))


def candidates(rows, threshold=2):
    """The operator's imprint-concentration query: 296 works, reproduced exactly.

    A work qualifies when its evidence is exactly ONE shelf row and either it names no imprint at
    all or its rarest-but-one imprint appears on no more than `threshold` shelf-only works.

    An imprint-less row is IN, not out. 68 of the 296 name none, and a shop that printed no label
    has said less about the work rather than more, which is the same thinness the query is for.
    """
    freq = imprint_frequency(shelf_only(rows))
    out = []
    for r in rows:
        ev = evidence(r)
        if len(ev) != 1 or ev[0].get("kind") != "shelf":
            continue
        imp = imprints(r)
        if not imp or max(freq[i] for i in imp) <= threshold:
            out.append(r)
    return out


def author_index(rows, split):
    """{person: [works]} across the whole corpus, using `split` to break a credit line.

    `split` is adapters/names/inputs.split_authors, passed in so this module has no opinion about
    where a role label ends and a name begins. That question already has an owner and a second
    answer to it is the shape behind seven shipped bugs here (STANDING-INSTRUCTIONS §3).
    """
    idx = collections.defaultdict(list)
    for r in rows:
        for name in split(r):
            idx[name].append(r)
    return idx


def in_field(row, index, split):
    """Whether anyone credited here has ANOTHER work carrying publisher- or platform-side evidence.

    `row['id']` is excluded, so a work cannot vouch for itself.
    """
    for name in split(row):
        for other in index.get(name, ()):
            if other.get("id") == row.get("id"):
                continue
            if any(e.get("rank", 99) <= PUBLISHER_SIDE_RANK for e in evidence(other)):
                return True
    return False


def platform_codes(row, platform):
    """The work's own codes on one platform, taken off the last path segment of each source URL."""
    return [s["url"].rstrip("/").rsplit("/", 1)[-1]
            for s in (row.get("sources") or [])
            if s.get("platform") == platform and s.get("url")]


def prominent(row):
    """Four volumes or forty chapters: enough of a work that other sources had a chance at it."""
    vols = max([p.get("volumes") or 0 for p in (row.get("print") or [])] or [0])
    return vols >= 4 or (row.get("chapters") or 0) >= 40


def signals(row, key="", antenna=(), tagged=(), index=None, split=None, facets=None):
    """Every structural signal this module holds about one candidate.

    `key` is the row's title in the comparison form, so that matching against a list written by
    somebody else is done on the same footing spacing and width are already compared on elsewhere.
    `antenna` is the set of those keys on Web漫画アンテナ's 百合 tag; `tagged` the set of カドコミ codes
    on that platform's own 百合 and GL tags; `facets` the BOOK☆WALKER capture row for the work,
    and None for a work admitted at the other shop.
    """
    imp = imprints(row)
    codes = platform_codes(row, "カドコミ")
    facets = facets or {}
    return {
        "title_term": bool(TERM.search(row.get("work") or "")),
        "imprint_term": any(TERM.search(i) for i in imp),
        "antenna": bool(key) and key in set(antenna),
        "platform_declined": bool(codes) and not any(c in set(tagged) for c in codes),
        "other_category": any(OTHER_CATEGORY.search(i) for i in imp),
        "container": bool(CONTAINER.search(row.get("work") or "")),
        "prominent": prominent(row),
        "author_in_field": bool(index is not None and split is not None
                                and in_field(row, index, split)),
        # Recorded, scored at zero. See the dropped-signals note in the module docstring.
        "male_directed": bool(facets.get("male_directed")),
    }


def verdict(sig, contradicted=False):
    """`contradicted`, `corroborated` or `unsupported` for one candidate.

    `contradicted` is never derived from a signal. It is set only where a source READ for this pass
    says something against the shelf, which is a fact about a page somebody opened and not an
    inference from what the corpus happens to hold.
    """
    if contradicted:
        return "contradicted"
    if sig["title_term"] or sig["imprint_term"] or sig["antenna"]:
        return "corroborated"
    return "unsupported"


# What each signal moves the ordering by. Weights, not probabilities: they order a reading queue
# and nothing downstream treats them as a measurement. `male_directed` is absent deliberately.
WEIGHTS = {"platform_declined": 3, "container": 2, "other_category": 2,
           "prominent": 1, "author_in_field": -1}


def suspicion(sig):
    """How far up the reading queue a candidate goes. Higher is read sooner."""
    return sum(w for k, w in WEIGHTS.items() if sig.get(k))
