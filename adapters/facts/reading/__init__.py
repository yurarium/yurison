#!/usr/bin/env python3
"""What may be believed about how a name is read, and on whose word.

WHY THIS IS ONE FACT. A reading carries a BASIS saying how we came by it and a SOURCE KIND
saying who said so, and the pairs that are allowed are a standing ruling. That ruling lived in
`curate.py` beside the code that applies it, and `check.py` held a copy of its values written
out by hand. The copy drifted, was found, and was replaced by a derivation. This is where the
ruling lives now, so a copy has nowhere to be.

THE ROWS ARE RULINGS AND NOT PREFERENCES. Each one records who decided and when, and the
community-db row records a decision made and reversed inside one day. Read the comments
before changing a row.

WHAT THIS DOES NOT OWN. The readings themselves, which the naming passes produce and the
source adapters fetch; and where a name divides, which is `facts/division`. See BLINDSPOT.md.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))

# A source_kind may be named here without being usable as evidence: a candidate records where a
# string was seen, and seeing it in a community database is the ordinary case.
SOURCE_KINDS = ("platform", "publisher-jp", "licensor", "community-db", "derived",
                # A national cataloguing authority, and the person themselves. Both state readings
                # and neither is a publisher or a platform, so neither fitted the list before.
                "national-library", "author",
                # The manga bibliography. It transcribes what a book prints, which is why it may
                # carry `official-jp` for a parallel title and nothing else.
                "bibliography")


# Which evidence each basis demands. `community-db` is deliberately absent from every row.
ATTRIBUTION = {
    # THE PERSON'S OWN RENDERING, WHERE THEY WROTE IT, and `author` belongs here for the reason the
    # row is named after. It was left out when `author` joined SOURCE_KINDS, because that round was
    # about READINGS and READING_ATTRIBUTION got it: the two lists were edited apart and the one
    # covering the artist's own page kept the artist off it. GAPS §9 is the cost. Every one of the
    # 616 author names on the site is a romanisation of ours, nobody has looked for the Latin name
    # the artist writes themselves, and an entry recording one was rejected by this line.
    "stated": ("platform", "publisher-jp", "author"),
    # `bibliography` IS ADMITTED HERE AND NOWHERE ELSE, and the reason is what ISBD punctuation
    # means. A 並列タイトル after ` = ` is transcribed from the book's own title page: MADB is not
    # inventing an English name, it is recording the one the publisher printed. So the source of
    # the name is the publisher and the bibliography is the transcriber, which is a different
    # relation from a cataloguer's romanisation and is why this admits no other basis.
    "official-jp": ("publisher-jp", "platform", "bibliography"),  # the work's own English name
    "licensed": ("licensor",),                    # an English-language licensor's catalogue
    "translated": ("derived",),                   # ours
    "romaji": ("derived",),                       # ours
}


# A curated READING is a different claim from a curated name, and only two bases can be curated.
# `aligned` and `back-converted` describe how a machine derived one, which is not something a
# person does by hand, and `guessed` is what curation exists to replace.
READING_ATTRIBUTION = {
    "surface": ("derived",),                    # the title is already kana; the reading is the name
    # A SOURCE PRINTS THE KANA: a yomi field, furigana in a byline, a cataloguer's transcription.
    #
    # `national-library` is the National Diet Library, which records dcndl:creatorTranscription
    # beside dc:creator for every book it holds. That is a national cataloguing authority stating
    # how a name is read, and it is the only route that reaches most pen names at all: 79 of 82
    # author readings settled this way came from it. `author` is the artist's own page, which is
    # better still and is rarer, because most of them never write their name in kana.
    #
    # `community-db` WAS ADMITTED HERE FOR ONE DAY AND THE PROJECT OWNER OVERRULED IT, 2026-08-09.
    # The pass that put it here argued that a reading is a transcription and that a user-edited base
    # can print kana correctly without having standing over a person's name. The ruling is that
    # Wikidata is treated as noncanonical and used to raise the floor on romaji, which is the row
    # below rather than this one. See `community-printed`.
    "stated": ("platform", "publisher-jp", "national-library", "author", "licensor"),
    # SETTLED BY A REVIEWER where nothing states it. A community wiki, a bookshop listing or the
    # way readers write about a work are all evidence about how a title is said, and none of them
    # is an attribution. This basis says a person weighed that evidence, so it demands a note
    # saying what was weighed: a reading with no reasoning behind it is a guess wearing a label.
    "researched": ("community-db", "derived"),
    # A COMMUNITY DATABASE PRINTS THE KANA AND NOBODY WITH STANDING OVER THE NAME HAS SPOKEN.
    # Ruled by the project owner 2026-08-09: "treat wikidata as noncanonical. use it to raise the
    # floor on romaji, including additional required searches".
    #
    # WHAT THE BASIS IS. Wikidata's P1814 gives the kana of a name, typed by an editor who signed
    # nothing. That is better than a morphological analyser, which is at its worst on pen names and
    # never declines to answer, and it is worse than anything a publisher or the national library
    # prints. So it sits between them, and it satisfies no test asking whether a source STATED a
    # reading: `STATED_BASES` below carries `stated` alone.
    #
    # WHY IT IS NOT `researched`. That basis means a reviewer weighed evidence and wrote down what
    # they weighed, and `problems` demands the note. Nobody here weighed anything; a query returned
    # a field. Filing this as `researched` would put a machine's harvest under a person's judgement,
    # which is the shape NAMES-PLAN §1 names as the failure to design against.
    #
    # THE LINE IS BETWEEN KANA AND LATIN, AND IT IS WHY THIS ADMITS ONE COMMUNITY DATABASE AND NOT
    # THREE. AniList and MangaUpdates return romanised strings, so a reading from either is
    # recovered by reading a romanisation backwards, which has already lost the length of every
    # vowel: those take `back-converted`, which this table does not carry. A source that prints the
    # kana itself has lost nothing, and Wikidata is the only one of the three that does.
    #
    # IT IS MARKED WHEREVER IT REACHES A READER. `build.py` ships `unverified` for it and the
    # interface draws the `[?]` that says the pronunciation is unconfirmed, because that is what is
    # in question: the sounds, stated by nobody who answers for them.
    #
    # AND THE RECORD STILL RESTS ON A FALLBACK, corrected by the project owner 2026-08-09: "I
    # mistyped 'without overcoming their fallback basis'". The first reading of the ruling had this
    # basis lifting a name OUT of the fallback population, so 73 people stopped being counted as
    # names nobody had settled. The correction says Wikidata gives a better STRING and not a better
    # CLAIM: the romanisation a reader sees improves, the gap in the data does not close, and
    # `renderings resting on a mechanical romanisation` counts these along with everything else the
    # interface spelled for itself.
    "community-printed": ("community-db",),
}


# WHAT AN ANALYSER IS, WHICH IS NOT AN ATTRIBUTION. `analyser` is the commonest source kind in the
# corpus, 3,056 readings, and `READING_ATTRIBUTION` above has no row for it because that table
# answers who may be believed to have STATED a reading and a morphological analyser states nothing.
# It segments a string and offers a reading for every name it is handed, declining none.
#
# THE PAIR HAS TO EXIST SOMEWHERE, because a claim references a basis and a source kind and the
# store will not hold a row whose basis it has never heard of. It was written in the loader, where a
# comment recorded the reasoning and the vocabulary decision sat in the code that reads the data
# rather than in the fact that owns the vocabulary. It is here now, which is the same decision in
# the place a reader looks for it.
#
# THIS IS THE LOADER'S DECISION MADE VISIBLE AND NOT A RULING. What an analyser's output is worth
# beside a stated reading is the owner's to settle, the way `community-printed` was settled on
# 2026-08-09. Until then the position is the conservative one: the pair is admitted so the claim can
# be recorded and queried, `STATED_BASES` does not carry it, so nothing asks a reader to believe a
# source said it, and `renderings resting on a mechanical romanisation` is where the population is
# counted. Overturning it is one line here and the budget that moves says how much it touched.
ANALYSER = "analyser"

#: The basis a reading takes when a record carries none. A record with no stated basis was produced
#: by the analyser pass, which is the only thing in the pipeline that writes a reading without
#: saying where it came from.
DEFAULT_BASIS = ANALYSER


def analyser_pair():
    """`(basis, source_kind)` for a reading a machine segmented, which no attribution table admits."""
    return (ANALYSER, ANALYSER)


# WHICH BASES MEAN A SOURCE STATED THE READING, and it is one. Held here rather than in `check.py`
# because the table above is what decides it and a check that keeps its own copy has already
# drifted from this one once: it admitted `community-db` for a researched reading and the copy did
# not, so a record citing one read as citing nothing. `check.STATES_A_READING` asks this.
STATED_BASES = ("stated",)



def may_state(basis, source_kind):
    """Whether a source of this kind may be believed to have given a reading on this basis."""
    return source_kind in READING_ATTRIBUTION.get(basis, ())


def kinds_for(basis):
    """The source kinds a basis admits, or an empty tuple for a basis nobody has ruled on."""
    return tuple(READING_ATTRIBUTION.get(basis, ()))


def bases():
    """Every reading basis the project has ruled on."""
    return tuple(READING_ATTRIBUTION)


def states_a_reading():
    """Every source kind that means somebody STATED the reading, across the stated bases.

    `check.STATES_A_READING` was this, written out by hand, and it had drifted when somebody looked.
    """
    out = set()
    for b in STATED_BASES:
        out |= set(READING_ATTRIBUTION.get(b, ()))
    return tuple(sorted(out))


def _checks():
    import importlib
    return importlib.import_module(".checks", __name__)


#: The submodules, which `__getattr__` must never forward: `from . import vocabulary` reaches the
#: hook before the submodule is bound on the package, so forwarding it calls the import that called
#: the hook. `facts/division` records the same trap.
_SUBMODULES = ("checks", "vocabulary", "misread")


def __getattr__(name):
    """Anything `vocabulary` publishes, reached through the entry point.

    Written as a hook rather than a re-export list so the list cannot drift from what the submodule
    offers. `analyser_vocabulary` asks for `doubt` and for the reasons a doubt stands, and asking
    the package for them is what `a fact is reached through its entry point` requires.
    """
    if name in _SUBMODULES or name.startswith("__"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib
    # BOTH SUBMODULES, in the order they were added. `misread` answers what a word is read where an
    # analyser reads it wrongly, which is a different question from `vocabulary`'s and belongs to
    # the same fact: what may be believed about how a name is read.
    for sub in (".vocabulary", ".misread"):
        mod = importlib.import_module(sub, __name__)
        if hasattr(mod, name):
            return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


#: WHAT THIS FACT CAN BE CHECKED ON, keyed by the name check.py registers.
CHECKS = {
    "readings_are_kana": lambda ctx, _n="readings_are_kana": getattr(_checks(), _n)(ctx),
    "reading_can_show_its_source": lambda ctx, _n="reading_can_show_its_source": getattr(_checks(), _n)(ctx),
    "uncertain_readings": lambda ctx, _n="uncertain_readings": getattr(_checks(), _n)(ctx),
    "claims_whose_evidence_their_basis_does_not_admit":
        lambda ctx: _checks().claims_whose_evidence_their_basis_does_not_admit(ctx),
    "author_readings_no_source_states": lambda ctx, _n="author_readings_no_source_states": getattr(_checks(), _n)(ctx),
    "publisher_readings_nobody_has_settled": lambda ctx, _n="publisher_readings_nobody_has_settled": getattr(_checks(), _n)(ctx),
    "titles_read_by_a_machine_unmarked": lambda ctx, _n="titles_read_by_a_machine_unmarked": getattr(_checks(), _n)(ctx),
    "kana_reading_spells_its_name": lambda ctx, _n="kana_reading_spells_its_name": getattr(_checks(), _n)(ctx),
    "ruby_spells_reading": lambda ctx, _n="ruby_spells_reading": getattr(_checks(), _n)(ctx),
    "facts_fetched_with_no_citation":
        lambda ctx: _checks().facts_fetched_with_no_citation(ctx),
}


#: HOW AN ENGLISH NAME WAS ARRIVED AT, and which answer wins. A different vocabulary from the
#: reading bases above and a fact in its own right: `build.py` and `names/store.py` each held it as
#: a dict keyed the same way, which the duplicates lint found.
#:
#: Three levels, per the owner's correction to section 5. `official-jp` is the English title the
#: AUTHOR, MAGAZINE or JAPANESE PUBLISHER uses: the work's own name in English, and it outranks
#: everything. `licensed` is what an English-language licensor publishes it as, authoritative but a
#: second party's choice. `translated` and `romaji` are ours and are marked as ours.
_EN_RANK = {"official-jp": 50, "licensed": 40, "translated": 20, "stated": 20, "romaji": 10}


def en_bases():
    """Every basis an English name can have."""
    return tuple(_EN_RANK)


def en_rank(basis):
    """Which English name wins. Unknown ranks below everything."""
    return _EN_RANK.get(basis, 0)


def en_ranks():
    """The whole table, for a caller that wants the mapping."""
    return dict(_EN_RANK)


def en_kinds_for(basis):
    """The source kinds an ENGLISH basis admits, or an empty tuple for one nobody has ruled on.

    THE COMPANION TO `kinds_for`, WHICH ANSWERS FOR A READING. Both tables have been here since the
    English side was written and only the reading one had a way to ask, so `adapters/relational`
    filled its attribution table from readings alone and reported 4,749 claims resting on a pair it
    forbade. 2,767 of them were `('translated','derived')`, which `ATTRIBUTION` admits on its first
    reading. A table nobody can query is a table that gets restated.

    EVERY ENGLISH BASIS HAS A ROW HERE, which is what separates this table from the reading one:
    `back-converted` sits in `division.BASES` and `READING_ATTRIBUTION` has never ruled on it, so 22
    readings rest on a basis nothing can check. That gap is real and is recorded in docs/GAPS.md.
    This side has no such hole, and a caller inventing a row for either is what the accessor stops.
    """
    return tuple(ATTRIBUTION.get(basis, ()))
