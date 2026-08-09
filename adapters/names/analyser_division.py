#!/usr/bin/env python3
"""Divisions a morphological analyser put into a person's name, and which of them may stand.

WHY THIS EXISTS. のぴやか梢 was shown to an English reader as `No Pi Ya Ka Kozue`. Behind it is the
reading ノ ピ ヤ カ コズエ, which is SudachiPy meeting a pen name it has never seen and handing back
one token per kana. `boundary.py` carries a division that some record STATES onto our own kana, and
this is the half nobody had written: 279 author records held a division an analyser had made up and
no source had stated, and the invariant that would have caught them tested kana surfaces only.

A WRONG DIVISION IS WORSE THAN NO DIVISION. The run-on form says nothing about where a name breaks
and carries the mark that says so (NAMES-PLAN §5d). `No Pi Ya Ka Kozue` is a claim about how a real
person's name divides, published under their own work, and nothing supports it.

WHAT SURVIVES, AND WHY IT IS NOT A GUESS. A kana run in the surface reads as itself, so its length
in the reading is arithmetic: のぴやか is four morae and ノピヤカコズエ opens with exactly those
four, so the offset after ノピヤカ is fixed by the writing and not by anybody's judgement. Where the
analyser divided at an offset like that the space stands and the record says the surface is where
it came from. Every other space comes out. のぴやか梢 keeps one of its four and reads ノピヤカ
コズエ; 上田香子 keeps none, because 上田香子 is one unbroken kanji run and nothing in it says where
ウエダキョウコ breaks.

THIS ESTABLISHES WHERE A DIVISION FALLS AND NEVER THAT ONE FALLS. That distinction is the whole
distance between this module and the two rules NAMES-PLAN records as tried and rejected. 九羊ボン is
filed クラムボン by the media-arts catalogue, one word and a pun on it, and the arithmetic here
would place an offset before ボン without hesitating. Nothing asks it to: the catalogue's reading
arrives with no space in it, this module only ever REMOVES spaces, and `boundary.fill` proposes a
division only from a donor that states one. So the pun survives, and the limit is worth naming
because it is real. Where an analyser has divided a compound that changes script in the middle, the
surface cannot tell that from a surname meeting a given name, and ぶり大根 keeps its space for that
reason.

A SYMBOL READS AS ITSELF AND DIVIDES NOTHING. Punctuation passes through a reading untouched, so
the arithmetic reaches it as readily as it reaches kana, and in this corpus every offset it reached
that way was wrong: R-指定 read `R - Shitei`, 2C=がろあ read `2 C =Garo A`, ○山浩平 read
`○ Yama Kōhei` and あんじんねこ@創作 read `Anjin Neko @ Sōsaku`. A symbol is not an element of a
name. So a surviving offset needs a word character on each side of it, which keeps コミック nishi
and cuts all four of those, and a part of a single mora is a prefix: お久しぶり read
`O Hisashiburi`.

A SURFACE THAT WRITES ITS OWN SPACES HAS ANSWERED THE QUESTION. 三松　真由美 and 中村 朱里 are
bylines with the division in them, and where the reading holds one part per surface part the
offsets between those parts are the author's own. Those are left as the analyser produced them,
which is the rule `a division cites its source` has always applied to a spaced surface.

PEOPLE ONLY. A company or a committee is made of ordinary words and an analyser is good at those.
That is the line `build.py` already draws with `is_person`, so a record carrying `entity` is not
asked about. Titles are left alone for a second reason as well: `kana.align` reads a title reading's
spacing to place ruby, and NAMES-PLAN §5c sets a lower bar for a work than for a person.

RULE TRIED AND REJECTED, recorded so it is not re-derived. Collapsing the whole reading whenever any
one of its spaces was unsupported, instead of taking out the unsupported spaces. It is one line
shorter and it throws away answers: むつをむつ 蒼井ゆん would go from ムツ ヲ ムツ　アオイ ユン to
ムツヲムツアオイユン when the surface establishes both of the offsets the correct reading needs, and
4ka エンピツ would lose the space its own byline writes.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names import boundary                                                    # noqa: E402

# A run of kana, which is the only kind of run whose length in the reading is known. ー and the
# iteration marks belong to it: they are morae in the reading exactly as they are characters in the
# surface, which is what the arithmetic needs of them.
KANA_RUN = re.compile(r"[ぁ-ゖァ-ヺーゝゞ]+")

# What separates one part of a byline from the next. The same class `boundary.flat` removes, so the
# two modules agree about what a space is.
SEPARATOR = re.compile(r"[\s　・･]+")

# What may END and what may BEGIN a part, on either side of a surviving offset. A word character
# covers kana, a Latin handle and a digit, and leaves out every symbol, which is where the
# arithmetic went wrong: R - Shitei, ○ Yama Kōhei, Anjin Neko @ Sōsaku and 2 C =Garo A all take
# their spaces from a symbol reading as itself. ー and the iteration marks may close a part and
# never open one, since neither carries a sound of its own.
PART_ENDS = re.compile(r"[^\W_]")
PART_OPENS = re.compile(r"(?![ーゝゞ])[^\W_]")

# The shortest part a kana run may cut off. One mora is a prefix or a particle and not an element of
# a name: the analyser divided お久しぶり into お and 久しぶり, and the surface agrees with the
# arithmetic and is still not describing two halves of a name.
FLOOR = 2

# Where a surviving offset came from, kept beside the offset so the floor and the both-sides-kana
# rule apply to the arithmetic and not to a space the author wrote.
FROM_KANA = "kana"
FROM_BYLINE = "byline"

# What the record records as the source of a division this module keeps. `boundary.fill` writes the
# key of the record a division was carried from, and this writes a phrase, because the donor here is
# the name's own surface and it has no key of its own.
SURFACE = "the kana in its own surface"


def runs(surface):
    """`(kind, text)` for each maximal run in a surface, left to right.

    Three kinds. A kana run has a known length in the reading, a separator has a length of zero, and
    everything else has a length nobody knows, which is what makes it the end of a walk.
    """
    out, i = [], 0
    while i < len(surface):
        for kind, pattern in ((FROM_KANA, KANA_RUN), (FROM_BYLINE, SEPARATOR)):
            m = pattern.match(surface, i)
            if m:
                out.append((kind, m.group(0)))
                i = m.end()
                break
        else:
            j = i
            while j < len(surface) and not (KANA_RUN.match(surface, j)
                                            or SEPARATOR.match(surface, j)):
                j += 1
            out.append((None, surface[i:j]))
            i = j
    return out


def _walk(surface, glued):
    """`{offset: origin}` for the offsets one surface establishes in one flattened reading.

    FROM BOTH ENDS, because a run of kanji has no known length and so ends the walk. Everything
    before the first kanji run is placed by counting forwards and everything after the last is
    placed by counting backwards, which is the shape `boundary.from_surface` already uses on a
    surface that writes its own spaces.

    AND IT CHECKS ITSELF. A kana run must actually be in the reading at the offset the arithmetic
    puts it. Where a source transcribes the kana differently, as a filing key folding づ to ず does,
    nothing matches and nothing is established.
    """
    at, n = {}, len(glued)
    pos = 0
    for kind, text in runs(surface):
        if kind == FROM_KANA:
            piece = boundary.flat(text)
            if glued[pos:pos + len(piece)] != piece:
                break
            pos += len(piece)
            if 0 < pos < n:
                at.setdefault(pos, FROM_KANA)
        elif kind == FROM_BYLINE:
            if 0 < pos < n:
                at[pos] = FROM_BYLINE
        else:
            break
    pos = n
    for kind, text in reversed(runs(surface)):
        if kind == FROM_KANA:
            piece = boundary.flat(text)
            if glued[pos - len(piece):pos] != piece:
                break
            pos -= len(piece)
            if 0 < pos < n:
                at.setdefault(pos, FROM_KANA)
        elif kind == FROM_BYLINE:
            if 0 < pos < n:
                at[pos] = FROM_BYLINE
        else:
            break
    return at


def established(surface, reading):
    """`{offset: origin}` for every offset in `reading` that `surface` accounts for.

    ONE SURFACE PART TO ONE READING PART, where the counts agree. 三松　真由美 divides itself and
    ミマツ 　 マユミ divides in the same place, so the offset between them is the byline's and the
    arithmetic never has to reach inside a kanji run to find it. Where the counts disagree the
    correspondence is unknown and the whole surface is walked instead, which is what leaves
    むつをむつ 蒼井ゆん with the two offsets its kana establish and none of the three the analyser
    invented between them.
    """
    glued = boundary.flat(reading)
    sparts = [p for p in SEPARATOR.split(str(surface or "")) if p]
    rparts = [p for p in SEPARATOR.split(str(reading or "")) if p]
    if len(sparts) > 1 and len(sparts) == len(rparts):
        at, pos = {}, 0
        for spart, rpart in zip(sparts, rparts):
            for offset, origin in _walk(spart, boundary.flat(rpart)).items():
                at.setdefault(pos + offset, origin)
            pos += len(boundary.flat(rpart))
            if 0 < pos < len(glued):
                at[pos] = FROM_BYLINE
        return at
    return _walk(surface, glued)


def retire(surface, reading):
    """`reading` with every space the surface does not account for taken out.

    Idempotent, because a reading this has already been through holds only offsets it keeps.
    """
    glued = boundary.flat(reading)
    at = established(surface, reading)
    wanted = [o for o in boundary.cuts(reading) if o in at]
    kept, edges = [], [0] + wanted + [len(glued)]
    for i, offset in enumerate(wanted):
        if at[offset] == FROM_KANA:
            if offset - edges[i] < FLOOR or edges[i + 2] - offset < FLOOR:
                continue
            if not (PART_ENDS.match(glued[offset - 1]) and PART_OPENS.match(glued[offset])):
                continue
        kept.append(offset)
    return boundary.respace(glued, tuple(kept))


def asks(record):
    """Whether this record holds a division that an analyser made and nothing has checked.

    `entity` is what `build.py` reads to decide a credit is not a person, and a company's name is
    made of ordinary words that an analyser divides correctly. `back-converted` is a romanisation
    read backwards and its spacing is the romaniser's, so it is somebody's claim and not an
    analyser's, and it is counted where it is not corrected.

    A DIVISION `boundary.fill` HAS CARRIED IS SOMEBODY ELSE'S AND STAYS. The reading of 赤川左岸 is
    still the analyser's, and its division came from 赤河左岸, the same person filed under another
    spelling with a stated reading. `fill` runs after this on every build, so without this line the
    two passes take it in turns: one carries the division on and the next takes it off, and the file
    moves on every build for the rest of its life.
    """
    record = record or {}
    return bool(record.get("reading")
                and record.get("reading_basis") == "analyser"
                and not record.get("entity")
                and record.get("reading_boundary", SURFACE) == SURFACE
                and boundary.cuts(record["reading"]))


def retire_all(names):
    """Take the unsupported spaces out of every analyser division in `names`. `(changed, kept)`.

    `changed` maps a name to `(before, after)` and `kept` lists the names whose whole division the
    surface accounts for.

    EVERY DIVISION THAT SURVIVES SAYS THE SURFACE IS WHERE IT CAME FROM, whether or not anything was
    taken out of it, because after this runs there is nothing else it could have come from. のぴやか梢
    keeps one of the four spaces the analyser gave it and cites the surface for that one exactly as
    三好ミオ cites it for its only one. `a division cites its source` reads the field, so a division
    that acquired itself somewhere else fails the gate.
    """
    changed, kept = {}, []
    for key, rec in names.items():
        if not asks(rec):
            continue
        before = rec["reading"]
        after = retire(key, before)
        if after != before:
            rec["reading"] = after
            changed[key] = (before, after)
        else:
            kept.append(key)
        if boundary.cuts(after):
            rec["reading_boundary"] = SURFACE
        else:
            rec.pop("reading_boundary", None)
    return changed, kept


STORE = pathlib.Path(__file__).resolve().parents[2] / "data" / "names" / "authors.yaml"


def retire_store(path=None):
    """`retire_all`, against the store on disk. `(changed, kept)`, and the file is written.

    THE AUTOPILOT CALLS THIS, before `boundary.fill_store`, so a name the analyser divided overnight
    is corrected the same morning and the glued form is then offered to a donor that states a real
    division. A missing store is the documented fallback and not an error, the same line
    `boundary.fill_store` takes.
    """
    import yaml
    path = pathlib.Path(path or STORE)
    if not path.exists():
        return {}, []
    text = path.read_text()
    doc = yaml.safe_load(text) or {}
    names = doc.get("names") or {}
    changed, kept = retire_all(names)
    written = yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100)
    # Compared rather than assumed, so a run with nothing left to correct leaves the file alone and
    # a second run is free. Every kept record is marked on every pass, so counting the corrections
    # would not have told us whether the file moved.
    if written != text:
        path.write_text(written)
    return changed, kept


def main(argv=None):
    import argparse

    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", default="data/names/authors.yaml")
    ap.add_argument("--apply", action="store_true", help="write the readings back to the store")
    a = ap.parse_args(argv)

    path = pathlib.Path(a.store)
    doc = yaml.safe_load(path.read_text()) or {}
    names = doc.get("names") or {}
    asked = [k for k, r in names.items() if asks(r)]
    changed, kept = retire_all(names)
    glued = sum(1 for _b, after in changed.values() if not boundary.cuts(after))
    print(f"{len(asked)} name(s) divided by an analyser; {len(changed)} corrected, "
          f"{glued} of them left whole; {len(kept)} accounted for by the surface")
    for k, (before, after) in sorted(changed.items()):
        print(f"  {k:24} {before}  ->  {after}")
    if a.apply and changed:
        path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
        print(f"written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
