#!/usr/bin/env python3
"""What this fact is checked on. Lives beside the fact so a check cannot drift from it.

These four ask about a division's STANDING, which is what this module owns. The two that
stayed in check.py ask about producers: `kana names with no stated division` is about kana
surfaces and `author names romanised as one word` is about a rendering. They move when the
producers do.

`check.py` imports these through the entry point and registers them under their published
names, which is what status.html shows.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))

import re                                                               # noqa: E402

import kana                                                             # noqa: E402
from facts import division as _division                                 # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]

# ASKED OF THE TABLE, so these cannot drift from the module they live in.
DIVIDED_BY_ITS_SOURCE = tuple(sorted(_division.bases_where("cited")))
UNCITED_DIVISIONS_COUNTED = tuple(sorted(_division.bases_where("counted")))


def _states_a_reading():
    """The source kinds that mean somebody stated a reading, from the one table that holds them."""
    try:
        import curate
        return tuple(sorted(curate.READING_ATTRIBUTION.get("stated", ())))
    except Exception:                                                   # noqa: BLE001
        return ()


STATES_A_READING = _states_a_reading()

def divisions(reading):
    """How many pieces a reading is written in. One means it states no division.

    `boundary.divisions` IS THE ANSWER AND THIS IS THE FALLBACK. The count decides whether a record
    owes a citation for its division, and `adapters/names/curate.py` refuses a curated entry on the
    same count, so two copies of it would be §3 with the check holding one of them.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        from names import boundary
    except Exception:                                                       # noqa: BLE001
        return len([p for p in re.split(r"[\s　]+", str(reading or "").strip()) if p])
    return boundary.divisions(reading)



def cites_its_source(ctx):
    """A division a name does not itself write has to say where it came from.

    THIS IS WHAT STOPS THE BOUNDARY PASS BECOMING A GUESSER. `adapters/names/boundary.py` will only
    carry a division some record states, and the way to be sure it stays that way is not to read the
    module: it is to require every division in the store to name its origin. A record that acquired
    one from an analyser, a surname lexicon or somebody's intuition has nothing to put here and
    fails the gate.

    AN ANALYSER DIVIDES EVERY NAME IT IS GIVEN, so its answer is a citation of nothing. It is also
    at its weakest on exactly these: 331 kana names carried its answer, and
    よつば◎ますみ。 came back ヨツバ ◎ マスミ。 with the kana untouched and a division nobody stated.
    `madb_reading.py` refuses to publish an analyser's boundary under a catalogue's name for the
    same reason, at length. So the source has to be one that states readings.

    くわばら たもつ writes its own division and needs no citation, which is why the surface is
    counted rather than assumed to have none.

    A NAME HOLDING A KANJI IS ASKED THE SAME QUESTION, and for two years it was not. The clause
    above tests kana surfaces only, on the reasoning that a name with a kanji in it takes its
    division from the reading a source stated for it, and 1,016 records showed that is the ordinary
    path and not the only one: のぴやか梢 was divided ノ ピ ヤ カ コズエ by an analyser and read
    `No Pi Ya Ka Kozue` on the site. So the second clause covers every other surface, and it admits
    one thing the first does not, because the population it meets is different. Where a reading came
    from a source at all, the division came with it: an openBD collation key writes a comma between
    the halves, an NDL heading divides both the name and its reading, and a Wikidata item states
    P734 and P735 separately. That is what `reading_basis` records, and `curate.DIVIDING_BASES` is
    the list of the bases that carry their own citation. `analyser` carries none.

    WHAT IT LETS PAST, DELIBERATELY AND COUNTED, and it is two classes rather than one.
    `UNCITED_DIVISIONS_COUNTED` names them beside the budget each is counted by. `back-converted` is
    a reading recovered from somebody's romanisation, so its spacing is that romaniser's;
    `community-printed` is Wikidata's P734 and P735, typed by an editor who signed nothing. Both are
    weak claims and both ARE claims, which is the whole of the difference between them and an
    analyser's answer. An `entity` is not a person: 「真夜中ぱんチ」製作委員会 is made of ordinary
    words and dividing it misnames nobody.

    `community-printed` REACHED THAT LIST BY THE OWNER'S CORRECTION OF 2026-08-09. The ruling had
    been implemented on a mistyped word and read as lifting these records out of the fallback
    population, which put the basis in `curate.DIVIDING_BASES` and had this invariant treating an
    anonymous edit as a citation. The restored word is "without": Wikidata does not overcome the
    fallback basis. So the division stands, because refusing the space alone would take the harder
    half of a single editor's claim and return 88 people to a glued romanisation, and it stands as
    something counted instead of as something cited.

    A BORROWED DIVISION IS CITED BY WHATEVER THE DONOR CITED, which is the same correction one
    record further on. `reading_boundary` names the record a space was carried from and says nothing
    about what stood behind it, so 20 kana credits whose space came from Wikidata were passing on
    the strength of the field being filled. `reading_boundary_basis` is the field that says, `boundary.donor_basis`
    writes it, and the same budget counts those 20.

    §14b, what it cannot see: whether a division is in the right PLACE. It reads the store's own
    account of where each one came from, so a record that cites a source no human checked passes.
    `adapters/names/analyser_division.py` is what made the analyser's records able to answer, and
    the answers it writes are the surface's arithmetic and not a person's judgement.

    fallback: none. A guessed division reads as a fact about a real person's name.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import kana
    except Exception:
        return []
    bad = []
    for k, v in (ctx["names"].get("authors") or {}).items():
        rd = v.get("reading")
        if not rd or divisions(rd) <= divisions(k):
            continue
        # Ahead of everything else, because both of these are answers about the whole record and
        # the clauses below would otherwise reach them through a citation that is not one.
        if (v.get("reading_basis") in UNCITED_DIVISIONS_COUNTED
                or v.get("reading_boundary_basis") in UNCITED_DIVISIONS_COUNTED):
            continue
        cited = bool(v.get("reading_boundary")) or v.get("reading_source_kind") in STATES_A_READING
        if kana.kana_only(k):
            if not cited:
                bad.append(f"{k}: divided as {rd!r} with nothing saying who divided it")
            continue
        if cited or v.get("entity") or v.get("reading_basis") in DIVIDED_BY_ITS_SOURCE:
            continue
        bad.append(f"{k}: divided as {rd!r} with nothing saying who divided it")
    return bad


def names_its_donor_in_a_field(ctx):
    """Where a person's name divides has to be recorded in a field, never only in prose.

    THE FAULT THIS IS FOR. Two producers wrote one fact into two slots. `boundary.fill` and
    `analyser_division` record where a division came from in `reading_boundary`, which is a FIELD;
    `ndl_heading.entry` and `openbd_reading.boundary_entries` wrote the same fact into
    `reading_note`, which is PROSE. 293 author records cited their division in a sentence and
    nowhere else, so every count that reads the field read them as having no source at all, and no
    number anywhere could tell 293 from 0. STANDING-INSTRUCTIONS §3 is one producer of a fact, and
    a fact held in prose cannot be queried, checked or counted.

    THE TWO HONEST ANSWERS, AND WHY THERE ARE EXACTLY TWO. A reading whose kana came from a source
    arrived with that source's spaces already in it: NDL writes a heading word-divided, an openBD
    collationkey puts a comma between the halves, a Wikidata item states the family and given kana
    separately. There the citation is `reading_source` and `reading_source_kind`, which are fields.
    A reading whose kind is `derived` is OURS, so nothing came with it, and a division in one was
    carried from a donor that has to be named in `reading_boundary`.

    NOT THE SAME QUESTION AS `a division cites its source`, which asks whether anything at all
    stands behind a division and admits a basis as the answer. This asks whether the answer is
    somewhere a machine can read, which is what was false while every gate was green.

    §14b, and it is why this does not simply ask `boundary.fill` whether it would have found a
    donor. That would be the fix's own question, so it could only ever report what the fix already
    handles. What it asks instead is arithmetic on two strings the store holds, the reading and the
    surface, against one provenance field that the boundary passes do not write. A record can only
    satisfy it by saying something, and `--self-test` plants a divided reading with our own kana and
    no donor, which is the state 293 records were in.

    What it cannot see: whether a donor named here is the right one, or whether the division landed
    in the right place. `reading_boundary` is a label and no check can read a catalogue for it.

    fallback: none. A division nobody can trace is a claim about a real person's name with nothing
    behind it, which is the case NAMES-PLAN §5f says is worse than no division.
    """
    bad = []
    for k, v in (ctx["names"].get("authors") or {}).items():
        rd = v.get("reading")
        if not rd or divisions(rd) <= divisions(k):
            continue
        if v.get("reading_boundary") or v.get("reading_source_kind") != "derived":
            continue
        bad.append(f"{k}: divided as {rd!r} out of kana of our own, and no field says by whom. "
                   f"A `reading_note` explaining it is prose and nothing can read it.")
    return bad


def divisions_read_back_from_a_romanisation(ctx):
    """People divided on the strength of a space in somebody's romanisation of them.

    THE RESIDUE `a division cites its source` LETS PAST, and the only one. MangaUpdates gives
    `KASHI Michiyo` for 一世蕨 and `pass2_bulk` recovers カシ ミチヨ from it, so both the reading and
    the place it breaks come from a community editor writing the name in Latin. That is a claim
    somebody made, which is why it is not corrected the way an analyser's division is
    (`adapters/names/analyser_division.py`), and it is the weakest form the claim takes: a
    back-conversion has already lost the length of every vowel, and `boundary.py` refuses to take a
    division from one as a donor for any other name.

    A count on the store, because the fault is in what the record claims and not in how it renders.
    It falls when a source states one of these, and the three it holds today are all one shape:
    MangaUpdates was the only place these three names were found at all.
    """
    return sum(1 for k, v in (ctx["names"].get("authors") or {}).items()
               if v.get("reading_basis") == "back-converted"
               and divisions(v.get("reading")) > divisions(k))


def divisions_resting_on_a_community_database(ctx):
    """People whose name divides where an anonymous edit says it divides, and nowhere else.

    THE COST OF THE RULING, WRITTEN AS A NUMBER. The project owner ruled on 2026-08-09 that
    Wikidata is noncanonical and is used to raise the floor, so its readings hold
    `community-printed` and its divisions stand. A division is a claim about where a real person's
    name breaks, and NAMES-PLAN is emphatic that a wrong one is published under the artist's own
    work and reads as a fact. Keeping them and saying nothing would be the register nobody reads
    (§13), so this is what a person watches.

    AND THE CORRECTION LATER THAT DAY IS WHAT MAKES IT THE ONLY THING WATCHING THEM. The ruling had
    been read as lifting these records out of the fallback population; the owner restored the word
    "without", so Wikidata raises the floor on the string and leaves the record resting where it
    was. `a division cites its source` therefore stops treating the basis as a citation and admits
    it by name instead, and this count is the whole of what stands between 88 divisions and nobody
    knowing they are there.

    TWO POPULATIONS AND ONE QUESTION. A record can hold such a division because its own reading is
    Wikidata's and arrived divided, or because `boundary.fill` carried the space onto a reading that
    came from somewhere else. The second is the one that surprised: アカイマルボロウ is a kana
    surface whose sounds are certain, and it took its space from 赤衣丸歩郎.

    IT FALLS WHEN A SOURCE STATES A DIVISION, and it cannot fall any other way. Dropping the space
    would not move it either, since a record with no division is not counted here and 62 people
    would go back to a glued romanisation to buy it.

    §14b, what it cannot see: whether a division is in the right PLACE. Nothing mechanical can. What
    it does not share with its subject is the producer: `boundary.fill` decides using `cuts` and
    `SETTLED_BASES`, and this counts spaces in the stored string against the surface's own, which is
    arithmetic on two strings and consults neither.
    """
    return sum(1 for k, v in (ctx["names"].get("authors") or {}).items()
               if divisions(v.get("reading")) > divisions(k)
               and (v.get("reading_basis") == "community-printed"
                    or v.get("reading_boundary_basis") == "community-printed"))

