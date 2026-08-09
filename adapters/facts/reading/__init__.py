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
