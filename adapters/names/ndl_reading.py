#!/usr/bin/env python3
"""How a name is read, taken from the National Diet Library's own transcription of it.

WHY THIS EXISTS. Three rounds of author readings were settled by reading NDL OpenSearch responses
by hand (`data/coverage/author-readings-*.md`), and 79 of the 82 readings that stuck came from this
one field. The reasoning was in a person's head and the extraction was done by eye, so the next
round could not reuse either. The judgement stays with the person; the extraction is here.

WHAT IT READS. `?creator=<name>` returns records carrying `dc:creator` and, beside it,
`dcndl:creatorTranscription`, a national cataloguing authority stating how the name is said. Under
`adapters/names/curate.py` that is `reading_basis: stated` with `reading_source_kind:
national-library`, and it is the only route that reaches most pen names at all.

  THE HTML RECORD PAGES ARE NOT AN ALTERNATIVE. ndlsearch.ndl.go.jp returns 503 for them while the
  API answers normally, so anything wanting a second look at a record has to want it from the API.

WHY THE TWO FIELDS ARE ZIPPED BY POSITION, AND WHERE THAT IS REFUSED. An anthology record lists
every contributor in `dc:creator` and every transcription in `dcndl:creatorTranscription`, in the
same order and nowhere joined. 念願の悪役令嬢 gave four names on one record and three of the four
stored readings were wrong, so reading the pairing off the position is worth doing. It is also the
way to attach one person's reading to another person's name, which is the worst outcome available
here: 古川楊也 was once published under a different artist's name and it took a refutation to undo.
So a record whose two lists are different lengths yields NOTHING rather than a best guess.

WHAT A MATCH REQUIRES. NDL writes a name as `姓, 名`, sometimes with a birth year as a third
element, and our catalogue writes it closed up. The comparison drops the separators and the year
from both sides. It does not drop anything else: a partial match would let 山田 answer for
山田恭平, and three names in the last round were blocked precisely because NDL holds many people
under one string.

WHAT SILENCE MEANS. Nothing at all. Most of these artists publish on the web, their work has no
ISBN, and NDL therefore holds nothing about them. An empty result is `unresolved`, which is a
finding, and it is never an invitation to derive a reading from the characters instead.
"""
import re
import unicodedata

# The XML tags this reads. Kept as a name each so a changed feed fails visibly rather than by
# returning an empty list, which is indistinguishable from an artist NDL has never heard of.
CREATOR = "dc:creator"
TRANSCRIPTION = "dcndl:creatorTranscription"

_ITEM = re.compile(r"<item>(.*?)</item>", re.S)
_YEAR = re.compile(r",\s*\d{4}-\d{0,4}\s*$")
_SEPARATORS = re.compile(r"[,、\s　・]+")


def _tags(xml, tag):
    return re.findall(rf"<{tag}>(.*?)</{tag}>", xml or "", re.S)


def _unescape(s):
    import html
    return html.unescape(s or "").strip()


def key(name):
    """A name with its cataloguing separators and birth year removed, for comparing two of them."""
    s = _YEAR.sub("", unicodedata.normalize("NFKC", _unescape(name)))
    return _SEPARATORS.sub("", s).lower()


def spaced(transcription):
    """NDL's `タケシマ, エク` as the single space this project stores between name elements."""
    s = _YEAR.sub("", unicodedata.normalize("NFKC", _unescape(transcription)))
    return " ".join(p for p in _SEPARATORS.split(s) if p)


def records(xml, name):
    """Every record whose creator IS this person, as {reading, title, publisher, creator}.

    A record contributes at most one reading, and only where the two creator lists line up. See the
    module docstring for why a mismatch yields nothing.
    """
    want = key(name)
    if not want:
        return []
    out = []
    for item in _ITEM.findall(xml or ""):
        creators = _tags(item, CREATOR)
        trans = _tags(item, TRANSCRIPTION)
        if not creators or len(creators) != len(trans):
            continue
        for c, t in zip(creators, trans):
            if key(c) != want:
                continue
            reading = spaced(t)
            if not reading:
                continue
            out.append({
                "reading": reading,
                "title": _unescape((_tags(item, "title") or [""])[0]),
                "publisher": _unescape((_tags(item, "dc:publisher") or [""])[0]),
                "creator": _unescape(c),
            })
            break
    return out


def resolve(xml, name):
    """The reading NDL states for this name, with what it rests on, or an unresolved answer.

    Returns (reading, evidence). `reading` is None where NDL states nothing, and also where its
    records genuinely disagree: two transcriptions for one written name is a finding to look at
    rather than a majority to take, since one of them may belong to somebody else entirely.

    WHERE THE BOUNDARY IS NOT A DISAGREEMENT, which cost the first pass two names in six. A book
    record gives `シノノメ, ミズオ` and an electronic-magazine table of contents gives
    `シノノメミズオ`, because the publisher supplies that field unsplit. Those are one reading
    written two ways, and calling them a conflict reports a resolved name as unresolved, which
    sends somebody to research a question that is already answered. So the comparison is made on
    the kana, and the split form is preferred as the answer because it carries the boundary the
    other one lost. 灯 is the counter-case and stays conflicting: アカシ and アカリ are different
    kana, and one of them was a different artist.
    """
    recs = records(xml, name)
    if not recs:
        return None, {"status": "no-record", "records": 0}
    ev = {
        "records": len(recs),
        "examples": [(r["title"], r["publisher"]) for r in recs[:3]],
        "creator_form": recs[0]["creator"],
    }
    by_kana = {}
    for r in recs:
        by_kana.setdefault(r["reading"].replace(" ", ""), set()).add(r["reading"])
    if len(by_kana) > 1:
        return None, {**ev, "status": "conflicting",
                      "readings": sorted({r["reading"] for r in recs})}
    forms = next(iter(by_kana.values()))
    # The split form, where both were supplied. Longest wins: it is the one with the space in it.
    best = max(sorted(forms), key=len)
    out = {**ev, "status": "stated"}
    if len(forms) > 1:
        out["unsplit_also_seen"] = True
    return best, out


def is_kana(reading):
    """Whether a reading is the katakana this project stores, rather than something else.

    THE PATTERN IS curate.py's, NOT A SECOND ONE. A stricter rule written here rejected NDL's
    ニシザワ 5ミリ for 西沢5ミリ, because it refused digits that a stored reading is allowed to keep:
    100日後 is in the store with its digits and 【タテスク】 with its brackets. Two rules for one
    fact is this project's most repeated bug (STANDING-INSTRUCTIONS §3), and here the second one
    was wrong within an hour of being written. The import is inside the function so that reading a
    catalogue record does not drag in the name store.
    """
    if not (reading or "").strip():
        return False
    from names.curate import KATAKANA
    return bool(KATAKANA.match(unicodedata.normalize("NFKC", reading)))


def query(name):
    """The OpenSearch URL for one creator. `cnt` is small because the first records settle it."""
    import urllib.parse
    return ("https://ndlsearch.ndl.go.jp/api/opensearch?cnt=20&creator="
            + urllib.parse.quote(name))
