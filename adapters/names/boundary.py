#!/usr/bin/env python3
"""Where a name written in one unbroken run divides, and what licenses saying so.

WHY THIS EXISTS. A romanisation is generated from the reading, so the reading is where a word
boundary lives: 五十嵐純 is filed イガラシ ジュン and comes out `Igarashi Jun` for free. A name
written entirely in kana has no boundary in its surface, `pass1_kana` folds that surface to katakana
and calls it the reading, and いがらしゆみこ therefore romanises as `Igarashiyumiko`. 337 author
names were in that state.

TWO THINGS KEPT IT THERE, and both are worth naming because neither looks like a bug on its own.
`openbd_reading.unsettled` counts a kana surface as settled, which is right about the READING and
wrong about the boundary, so a kana name was never asked about. And `store.same_reading` counts
アオタユキコ and アオタ ユキコ as one reading, which is right when deciding whether two sources
disagree and wrong when the boundary is the whole of what one of them adds, so a boundary that did
arrive lost the rank merge to the surface. The ten kana names that carry a boundary today all came
through `curated.yaml`, which supersedes instead of merging.

WHAT THIS MODULE WILL AND WILL NOT DO. It carries a boundary that some record STATES onto our own
kana. It never proposes one. Splitting わらびもちきなこ in the wrong place is worse than leaving it
whole, because the wrong place is published under the artist's own work and reads as a fact.

  OUR KANA, THEIR BOUNDARY. A collation key is a filing key before it is a reading and JPRO folds
  the kana that sort together: とりいしづく is filed トリイ シズク. Taking the key whole republishes
  the artist's name with a different kana in it, which `openbd_reading.normalised` refuses outright.
  What the key may still add is the division, so the division is what is taken and the kana stay the
  surface's own.

  A DONOR THAT DOES NOT CORRESPOND IS NOT A DONOR. The flattened forms must be the same length and
  must agree once the filing fold is undone, or nothing is carried. A boundary applied at an offset
  in a string it does not correspond to would land inside a mora.

  DISAGREEMENT REFUSES. Two donors dividing the name differently leave the name whole, and counted.
  That is the whole of what can honestly be said about it.

RULES TRIED AND REJECTED, so they are not re-derived.

  A SURNAME LEXICON built the way `lexicon.py` builds its katakana one, out of the boundaries the
  corpus's own spaced readings attest. 480 surname elements and 452 given elements come out of it,
  and requiring both halves to be attested settles three names of 337. One of the three is
  ふみつき, which is one pen name and would have been cut into フミ ツキ on the strength of a single
  attestation of each half. Loosening it to the surname alone is worse in the same direction. The
  evidence is one attestation deep and the failure is silent.

  `reading_family` AND `reading_given`, which 154 author records already carry and which nothing
  reads. Thirteen of them would settle a name here, and every one of those thirteen came from
  MangaUpdates by back-converting a romanisation: `WARABIMOCHI Kinako` to ワラビモチ + キナコ. A
  back-conversion has already lost the length of every vowel and is in no position to be believed
  about a word break, which is why `SETTLED_BASES` below refuses that basis outright. The register
  being unread is a real finding (STANDING-INSTRUCTIONS §13) and reading it here would have been
  reading it as something it is not.

  62 OF THAT REGISTER ARE WIKIDATA'S AND ARE A DIFFERENT CASE, ruled 2026-08-09. P734 and P735 give
  the family and given kana as kana, so nothing was read backwards. They stay unread here all the
  same, because the reading Wikidata supplies already carries the space between the two halves and
  arrives divided: there is nothing in the register this module would learn. The refusal above is
  about the back-conversion and not about the source.

WIKIDATA IS A DONOR AND ITS DIVISIONS CARRY A MARK WITH THEM. The project owner ruled on
2026-08-09 that Wikidata is noncanonical and is used to raise the floor, so its readings hold
`reading_basis: community-printed` and the interface draws the `[?]` on them. A division LENT to
another record is the case that ruling does not cover by itself: アカイマルボロウ is a kana surface
whose sounds are certain, and it took its space from 赤衣丸歩郎, whose reading is an anonymous edit.
The receiving record renders with no doubt on it at all, so the mark that justified the division
stayed behind on the donor. `fill` therefore writes `reading_boundary_basis` beside
`reading_boundary`, build.py ships it, and the interface says where the space came from. 8 records
were in that state when this was written.
"""
import pathlib
import re
import unicodedata

# The kana a JPRO collation key folds together, each attested in this corpus: とりいしづく is filed
# トリイ シズク, アシダカヲズ is filed アシダカ オズ, いづみやおとは is filed イズミヤ オトハ.
# One-to-one, which is what lets an offset in the folded form name an offset in ours.
FILING_FOLD = str.maketrans({"ヂ": "ジ", "ヅ": "ズ", "ヲ": "オ", "ヰ": "イ", "ヱ": "エ"})

SPACE = re.compile(r"[\s　]+")


def kata(s):
    """Hiragana to katakana, so a surface and a reading can be compared in one script."""
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in str(s or ""))


def flat(s):
    """The comparison form: one script, composed, with the boundaries taken out.

    The interpunct goes with the spaces. A source writes トリイ・シヅク where another writes
    トリイ シヅク, and both are stating the same division of the same name.
    """
    return re.sub(r"[\s　・･]", "", unicodedata.normalize("NFC", kata(s)))


def filing(s):
    """`flat`, folded the way a collation key folds. The form two spellings must agree in."""
    return flat(s).translate(FILING_FOLD)


def divisions(s):
    """How many pieces a string is written in. One means it states no division.

    THE COUNT THE CHECK AND THE VALIDATOR SHARE, and it is deliberately not `cuts`. `cuts` answers
    where a DONOR divides and so treats an interpunct as a separator, because a source writing
    トリイ・シヅク is stating the same division as one writing トリイ シヅク. This answers whether
    OUR OWN string is divided, where an interpunct is a character somebody's name contains:
    さりい・Ｂ is one credit. Two questions, two functions, and each named after the one it answers.
    """
    return len([p for p in SPACE.split(str(s or "").strip()) if p])


def cuts(reading):
    """Offsets into the flattened reading where it divides. `()` where it states no division.

    Offsets, because the parts belong to the donor and the offsets are all that is carried. A boundary at either end states nothing and is dropped: a stray leading
    space is punctuation, not a claim about the name.
    """
    at, seen = [], 0
    for tok in [t for t in re.split(r"[\s　・･]", str(reading or ""))]:
        piece = flat(tok)
        if not piece:
            continue
        if seen:
            at.append(seen)
        seen += len(piece)
    return tuple(a for a in at if 0 < a < seen)


def respace(run, at):
    """The run with a space at each offset."""
    out, last = [], 0
    for a in at:
        out.append(run[last:a])
        last = a
    out.append(run[last:])
    return " ".join(p for p in out if p)


def carry(surface, donor):
    """Our own kana, divided where `donor` divides it. None where nothing can be carried.

    `surface` is the name as it is written and `donor` is a reading somebody states FOR THAT NAME.
    The caller establishes that the donor is about this person; this establishes only that the two
    strings correspond well enough for an offset in one to name an offset in the other.
    """
    ours = flat(surface)
    at = cuts(donor)
    if not ours or not at:
        return None
    theirs = flat(donor)
    if len(theirs) != len(ours) or filing(theirs) != filing(ours):
        return None
    return respace(ours, at)


# Why a name was left whole, as a value a caller can count. Silence about which of these applied is
# how a pass that stopped finding anything reads exactly like a pass with nothing left to find.
NO_DONOR = "no source states a boundary"
NO_CORRESPONDENCE = "the stated boundary does not correspond to this spelling"
DISAGREEMENT = "sources disagree about where the name divides"


def settle(surface, donors):
    """`(reading, [donor labels])` for a name whose division is settled, or `(None, why)`.

    `donors` is `[(reading, label)]`. The label is carried through so the record can say where the
    boundary came from; a boundary that cannot name its source is a guess wearing a citation.
    """
    carried = {}
    for reading, label in donors or []:
        got = carry(surface, reading)
        if got:
            carried.setdefault(got, []).append(label)
    if not carried:
        return None, (NO_CORRESPONDENCE if donors else NO_DONOR)
    if len(carried) > 1:
        return None, DISAGREEMENT
    got, labels = next(iter(carried.items()))
    return got, labels


# A reading this project is willing to take a boundary from. An analyser's boundary is the thing
# `madb_reading.py` refuses at length to publish under a catalogue's name, so it is refused here
# too, and `back-converted` is a romanisation read backwards, which has already lost the length of
# every vowel and is in no position to be believed about a word break.
#
# NOT THE SAME LIST AS `curate.DIVIDING_BASES`, AND THE DIFFERENCE IS THE QUESTION. That one asks
# whether a record's own division arrived with its own reading; this asks whether a record may lend
# its division to a DIFFERENT record. `community-printed` is in both, and it is the one entry where
# the two questions could have been answered differently: a lent division leaves the mark behind on
# the donor. `donor_basis` is what carries the mark across, which is what makes admitting it here
# honest rather than convenient. `test_boundary` asserts the relationship so the two cannot drift.
SETTLED_BASES = ("stated", "surface", "researched", "community-printed")

# A basis whose division is a claim somebody typed under nobody's name, so a record receiving one
# has to say so. Everything else here is a publisher, a cataloguing authority, a reviewer with a
# note, or the name's own kana, and none of those owes a reader an explanation of the space.
MARKED_DONOR_BASES = ("community-printed",)


def donor_basis(names, labels):
    """The basis a set of division donors rests on, where every one of them wants a mark.

    None where any donor is stronger, which includes the artist's own byline: a label that names no
    record in the store is the surface's own division, and that is the best donor there is.

    THE WEAKEST DONOR DOES NOT DECIDE. Two records dividing a name the same way are two statements
    of one division, and where one of them is a publisher's the space is the publisher's whatever
    else agrees with it. So this answers only when there is nothing better behind the division.
    """
    got = set()
    for label in labels or ():
        rec = (names or {}).get(label)
        if rec is None:
            return None
        got.add(rec.get("reading_basis"))
    if got and got <= set(MARKED_DONOR_BASES):
        return sorted(got)[0]
    return None


def store_donors(names, key):
    """Every other record in the store that states a division of this same reading.

    THE JOIN IS THE READING, AND THAT IS DELIBERATELY NOT AN IDENTITY CLAIM. 五十嵐純 filed
    イガラシ ジュン and a kana name flattening to イガラシジュン are the same person almost always
    and need not be for this to be right, because what is taken is the DIVISION and two names that
    are said the same divide the same way. Where they genuinely do not, the two donors disagree and
    `settle` refuses.

    Exact agreement on the flattened reading, not the filing fold, because here both strings are
    ours and a difference between them is a difference between two artists' names.
    """
    want = flat((names.get(key) or {}).get("reading") or key)
    out = []
    for other, rec in names.items():
        if other == key:
            continue
        reading = rec.get("reading")
        if not reading or rec.get("reading_basis") not in SETTLED_BASES:
            continue
        if cuts(reading) and flat(reading) == want:
            out.append((reading, other))
    return out


def wants_division(name, record):
    """Whether this record's READING leaves the name's division unanswered.

    ANY SURFACE, WHICH IS WHERE THIS WAS WRONG. `wants_boundary` below asks only about kana names,
    on the reasoning that a name holding a kanji gets its division from the reading a source stated
    for it. That is the ordinary path and it is not the only one: 太陽まりい has a reading a national
    catalogue states, タイヨウマリイ, and the catalogue states it closed up, so the ordinary path
    delivered a correct reading and no division at all. 459 records were in that state and the
    module that exists to divide names was not looking at any of them.

    A DIVIDED SURFACE IS A QUESTION AND NOT AN ANSWER, which is the other half of the same mistake.
    佐倉 おりこ writes its own division and the reading サクラオリコ does not carry it, so the name
    romanises `Sakuraoriko` under a byline with a space in it. The surface is the best donor there
    is and `from_surface` is what reads it; excluding those records meant the one name whose
    division nobody had to look up was the one nothing looked at.
    """
    reading = (record or {}).get("reading")
    if not reading or cuts(reading):
        return False
    # Kana and nothing else, IN THE READING. A digit or a Latin letter has to be read before it can
    # be divided, and タイザン5 is somebody's whole name. The surface may hold anything, since the
    # division is carried onto the reading rather than onto the characters.
    return len(flat(reading)) >= 4 and bool(re.fullmatch(r"[ァ-ヺーゝゞ]+", flat(reading)))


KANA_RUN = re.compile(r"^[ぁ-ゖァ-ヺーゝゞ]+$")


def from_surface(name, reading):
    """`reading` divided where the SURFACE divides it, or None where the offset is not established.

    THE SPACE IN A BYLINE IS A STATED DIVISION, and it is stated by whoever wrote the name. 佐倉
    おりこ, 圷　見南子 and 出内　テツオ are how those artists are credited, and the readings
    サクラオリコ, アクツミナコ and イデウチテツオ threw the space away, so 20 people were romanised
    as one word under a byline that divides them.

    WHERE THE OFFSET COMES FROM, AND WHY THIS IS NOT SEGMENTATION. A surface part written entirely
    in kana IS its own reading, so its length in the reading is known by arithmetic and not by
    guessing: かしい in `かしい 葵` is カシイ, three morae, and the reading カシイアオイ begins with
    exactly those three. NAMES-PLAN records two rejected attempts at deriving a division, and both
    were rejected for proposing where a KANJI run ends. Nothing here proposes anything: the division
    is the author's, the anchor is exact, and a part whose length is not established yields nothing.

    So 圷　見南子 divides and 冬木先輩 does not, because the second has no space in it to read.

    AND IT CHECKS ITSELF. The anchored kana must actually be there. 三本 ひより gives ヒヨリ at the
    end of ミツモトヒヨリ and the offset stands; a reading that transcribes the kana differently, as
    a filing key folding づ to ず does, does not match and nothing is carried.
    """
    parts = [p for p in re.split(r"[\s　・･]+", str(name or "")) if p]
    ours = flat(reading)
    if len(parts) < 2 or not ours:
        return None
    at, seen = [], 0
    for p in parts[:-1]:                       # from the left, while each part reads itself
        if not KANA_RUN.fullmatch(p):
            break
        seen += len(flat(p))
        if seen >= len(ours) or flat(name).find(flat(p), 0) < 0:
            return None
        at.append(seen)
    if not at:                                 # nothing on the left, so try the right
        tail = 0
        for p in reversed(parts[1:]):
            if not KANA_RUN.fullmatch(p):
                break
            tail += len(flat(p))
            if tail >= len(ours):
                return None
            at.append(len(ours) - tail)
        at.sort()
    if not at:
        return None
    # THE ANCHOR HAS TO BE WHERE IT SAYS IT IS. Every kana part read off the surface must appear in
    # the reading at the offset the arithmetic put it, or the two strings are not each other's.
    if respace(ours, tuple(at)).replace(" ", "") != ours:
        return None
    pieces = respace(ours, tuple(at)).split(" ")
    for p, piece in zip(parts, pieces):
        if KANA_RUN.fullmatch(p) and flat(p) != piece:
            return None
    return respace(ours, tuple(at)) if len(pieces) == len(parts) else None


def wants_boundary(name, record):
    """Whether a KANA name's own kana can take a division from a donor that supplies no kana.

    THE NARROWER QUESTION, AND IT IS A DIFFERENT ONE. `openbd_reading.boundary_queue` asks this,
    because a collation key folds づ to ず and may not be published as anybody's reading: what it
    can supply is offsets, and an offset only names a place in OUR kana when the surface and the
    reading are the same string. That holds for a kana name and for nothing else.

    `wants_division` is the general question and `fill` asks that one, carrying onto the reading.
    """
    return (wants_division(name, record) and flat(record["reading"]) == flat(name)
            and bool(re.fullmatch(r"[ァ-ヺーゝゞ]+", flat(name))))


def fill(names):
    """Carry every boundary the store itself can settle. `(added, refusals)`.

    ADDITIVE, IDEMPOTENT AND OFFLINE, so `build.py` can call it on every build. A record whose
    reading already divides is not asked about, which is what makes a second run cost nothing.

    `reading_boundary` names the record the division came from. It is what the invariant
    `a boundary a name does not write names its source` reads, and it is why this pass cannot
    quietly become a guesser: a record with a boundary and no source fails the gate.
    """
    import collections
    added, refusals = {}, collections.Counter()
    for key, rec in names.items():
        if not wants_division(key, rec):
            continue
        # ONTO THE READING, NOT ONTO THE SURFACE. For a kana name the two are the same string and
        # this changes nothing; for 山本和音 the surface has no offsets to put a space at and the
        # reading ヤマモトカズネ does. The donor is another record of the same name spelt with a
        # space in it, which is this person's own record and not a guess about them.
        #
        # THE BYLINE IS THE FIRST DONOR ASKED, because it is the artist's own. Where it and a
        # second record disagree `settle` refuses, which is the right answer: two spellings of one
        # name dividing it in two places is a question nothing here can close.
        own = from_surface(key, rec["reading"])
        donors = store_donors(names, key) + ([(own, "its own byline")] if own else [])
        got, why = settle(rec["reading"], donors)
        if not got:
            refusals[why] += 1
            continue
        rec["reading"] = got
        rec["reading_boundary"] = ", ".join(sorted(why))
        # WHERE THE SPACE CAME FROM, AS A BASIS AND NOT ONLY AS A RECORD KEY. `reading_boundary`
        # names the donor and says nothing about what the donor is worth, so a division lent by an
        # anonymous edit and one lent by the national library were the same field. Written only
        # where the mark is owed, so a record that acquires a better donor later loses the field
        # rather than keeping a stale one.
        _basis = donor_basis(names, why)
        if _basis:
            rec["reading_boundary_basis"] = _basis
        else:
            rec.pop("reading_boundary_basis", None)
        # The spans were cut from the undivided reading. `store._apply` drops them for the same
        # reason whenever a reading changes, and this writes the file directly.
        rec.pop("furigana_spans", None)
        added[key] = got
    return added, refusals


# THE SENTENCES THAT HELD THIS FACT BEFORE THE FIELD DID. Two producers wrote where a name divides
# into `reading_note`, which is prose: `ndl_heading.entry` and `openbd_reading.boundary_entries`.
# 212 records cited their division there and nowhere else, so a check reading `reading_boundary`
# believed every one of them had no source, and no count could tell 212 from 0.
#
# READ ONCE, BY THE MIGRATION BELOW. Both producers write the field now, so nothing after this
# round needs to parse a sentence; this exists to move what was already said rather than to lose
# it. A note whose wording does not match is left alone and is reported by the migration as
# unrecognised, because silently transcribing nothing is how a migration reports success on work it
# did not do.
#
# The apostrophes are doubled in some entries, which is a YAML round trip and not a second wording.
#
# BOUNDED TO ONE LINE AND NOT TO ONE SENTENCE. `[^.]*?` was the first attempt and it matched 37
# fewer records than it should have, because openBD's own sentence writes `e.g.` in the middle of
# itself. A full stop is not the end of a sentence in this note and a newline is the end of a
# paragraph, so the paragraph is what the pattern may not cross.
DIVISION_SENTENCES = (
    (re.compile(r"The National Diet Library'+s author heading(?:\s+on record\s+([\w.-]+?))?"
                r"\s+divides this person as"),
     "the National Diet Library's author heading"),
    (re.compile(r"openBD'+s collationkey[^\n]*?divides this name as"),
     "openBD's collationkey"),
)


def donors_named_in(note):
    """The division donors a producer's prose named, as the labels `reading_boundary` holds.

    Ordered as they appear, deduplicated, so a note naming one donor twice yields one label. `[]`
    where the note says nothing about a division, which includes every note that only argues about
    the SOUNDS: those records have no division to account for.
    """
    text = str(note or "")
    out = []
    for pattern, label in DIVISION_SENTENCES:
        m = pattern.search(text)
        if not m:
            continue
        got = f"{label} on record {m.group(1)}" if m.lastindex and m.group(1) else label
        if got not in out:
            out.append(got)
    return out


def from_notes(entries):
    """Move a division from the prose that stated it into the field. `(moved, unrecognised)`.

    ONE PRODUCER OF A FACT (STANDING-INSTRUCTIONS §3). A record whose reading divides more than its
    surface has a second fact attached to it, and it had two slots: `reading_boundary`, which
    `fill` writes and a check can read, and a sentence inside `reading_note`, which nothing can.
    This fills the field from the sentence, once, and leaves the sentence where it is, because what
    the prose adds is the argument and the field was never going to hold that.

    ADDITIVE AND IDEMPOTENT. A record already naming its donor is not touched, so a second run
    costs nothing and cannot overwrite a donor `fill` established.

    `unrecognised` is every record that still cannot say where its division came from once this has
    run. It is returned rather than logged because a migration that transcribes nothing must not
    look the same as one with nothing to transcribe.
    """
    moved, unrecognised = {}, {}
    for key, rec in (entries or {}).items():
        reading = rec.get("reading")
        if not reading or divisions(reading) <= divisions(key) or rec.get("reading_boundary"):
            continue
        got = donors_named_in(rec.get("reading_note"))
        if got:
            rec["reading_boundary"] = ", ".join(got)
            moved[key] = rec["reading_boundary"]
        elif rec.get("reading_source_kind") == "derived":
            # THE ONES THAT MATTER. A reading whose kana are ours carries nobody's spacing, so a
            # division in one is unaccounted for unless something names its donor. Where the kana
            # came from a source, the spaces came with them and `reading_source` is the citation.
            unrecognised[key] = reading
    return moved, unrecognised


def restate_donor_bases(names):
    """Say what every division ALREADY in the store rests on. `{name: basis}` for the marked ones.

    `fill` writes `reading_boundary_basis` as it divides, and it only ever looks at a record whose
    reading is still whole, so the divisions it settled on earlier runs would never acquire the
    field. Eight records were in that state on 2026-08-09, each a kana surface holding a space lent
    by a Wikidata reading, and each rendering with no doubt on it anywhere.

    ADDITIVE, IDEMPOTENT AND OFFLINE, so `fill_store` runs it on every build. A record whose donor
    is no longer marked has the field REMOVED rather than left standing, which is the same rule
    `fill` applies: a stale mark says something about a record that stopped being true.

    The donor is read back out of `reading_boundary`, which `fill` writes as its labels joined with
    a comma and a space. A label naming no record in the store is a donor from outside it, and
    `donor_basis` answers None for those, which is the right answer: the artist's own byline and a
    catalogue's heading are both better than anything this marks.
    """
    marked = {}
    for key, rec in (names or {}).items():
        label = rec.get("reading_boundary")
        if not label:
            continue
        basis = donor_basis(names, [p for p in str(label).split(", ") if p])
        if basis:
            rec["reading_boundary_basis"] = basis
            marked[key] = basis
        else:
            rec.pop("reading_boundary_basis", None)
    return marked


STORE = pathlib.Path(__file__).resolve().parents[2] / "data" / "names" / "authors.yaml"


def fill_store(path=None):
    """`fill`, against the store on disk. `(divided, refusals)`, and the file is written.

    THE AUTOPILOT CALLS THIS, so a name arriving overnight beside a record that already states its
    division is divided by morning. It writes the YAML directly, the way `pass4_analyser.fill_missing`
    does, because both run inside a build that has not opened a NameStore.

    A missing store is not an error. `fill_missing` takes the same line: the names are not filled,
    the interface shows the Japanese, and that is §6's documented fallback.
    """
    import yaml
    path = pathlib.Path(path or STORE)
    if not path.exists():
        return {}, {}
    doc = yaml.safe_load(path.read_text()) or {}
    names = doc.get("names") or {}
    before = {k: (v or {}).get("reading_boundary_basis") for k, v in names.items()}
    added, refusals = fill(names)
    # EVERY DIVISION IN THE STORE, not only the ones this run settled. `fill` walks the whole store
    # anyway and the divisions it wrote on earlier days are the ones missing the field.
    restate_donor_bases(names)
    changed = any((v or {}).get("reading_boundary_basis") != before.get(k)
                  for k, v in names.items())
    if added or changed:
        path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
    return added, refusals


def main(argv=None):
    import argparse

    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", default="data/names/authors.yaml")
    ap.add_argument("--apply", action="store_true", help="write the boundaries back to the store")
    ap.add_argument("--from-notes", action="store_true",
                    help="move a division stated in `reading_note` into `reading_boundary`, and "
                         "report every record that still cannot say where its division came from")
    ap.add_argument("--section", default="names",
                    help="the top-level key the records sit under. `names` for a store, `authors` "
                         "for data/names/curated.yaml")
    a = ap.parse_args(argv)

    path = pathlib.Path(a.store)
    doc = yaml.safe_load(path.read_text()) or {}
    names = doc.get(a.section) or {}

    if a.from_notes:
        moved, left = from_notes(names)
        for k, v in sorted(moved.items()):
            print(f"  {k:24} {v}")
        for k, v in sorted(left.items()):
            print(f"  UNRECOGNISED {k:20} {v!r}: divided, kana ours, no donor named anywhere")
        print(f"{len(moved)} division(s) moved out of prose into the field; "
              f"{len(left)} still unaccounted for")
        if a.apply and moved:
            path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
            print(f"written to {path}")
        return 1 if left else 0

    names = doc.get("names") or {}
    wanted = [k for k, r in names.items() if wants_boundary(k, r)]
    added, refusals = fill(names)
    print(f"{len(wanted)} name(s) written in one run; {len(added)} settled")
    for k, v in sorted(added.items()):
        print(f"  {k:24} {v}")
    for why, n in refusals.most_common():
        print(f"  {n:4} left whole: {why}")
    if a.apply and added:
        path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
        print(f"written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
