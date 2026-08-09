#!/usr/bin/env python3
"""Apply hand-reviewed English names to the store, refusing any that cannot be attributed.

WHY THIS EXISTS. Every pass so far produces names mechanically, and none of them can produce the
two kinds that matter most: a licensed title, which lives in a licensor's catalogue and nowhere a
scraper here goes, and a translation, which is a judgement. Both were being held in a person's head
with nothing between the decision and the file.

WHY THE DECISIONS LIVE IN A FILE. The store is journal-backed and durable, so recording straight
into it would not lose anything. What it would lose is the REASON: which page was read, on what
day, and by what argument a title was translated rather than romanised. data/names/curated.yaml is
the source and titles.yaml the derived state, the same relation data/source and data/build already
have, which also makes re-applying after a rebuild a replay rather than a re-decision.

WHAT IT REFUSES, AND WHY THAT IS THE POINT.

  A COMMUNITY DATABASE MAY NOT SUPPLY A NAME. Wikipedia, Wikidata, AniList and MangaUpdates are
  leads. A lead tells you where to look; it is not an attribution, and the string it carries may be
  a licensed title, a Japanese publisher's own, or a scanlation title, with nothing in the record to
  say which. `community-db` therefore appears in no row of ATTRIBUTION below, so an entry sourced
  to one is rejected outright unless it is filed as a candidate. This is the project owner's rule
  and it was previously enforced by remembering it.

  A BASIS MUST MATCH ITS EVIDENCE. `licensed` means a licensor publishes it under that name, so it
  requires a licensor page. `official-jp` means the work's own English name, so it requires the
  Japanese publisher or the platform. `translated` and `romaji` are ours, and claiming a source for
  them would be dressing up a judgement as a finding.

  AN UNKNOWN KEY IS AN ERROR. A hand-edited file that reads `bais: licensed` would apply nothing
  and report success, which is this project's characteristic bug written in YAML.

Usage:  curate.py --check              validate the file and stop
        curate.py --apply              validate, then record into data/names
"""
import argparse
import pathlib
from facts import division as _division  # noqa: E402
import re
import unicodedata
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names import key  # noqa: E402
from names.store import NameStore  # noqa: E402

FILE = pathlib.Path(__file__).resolve().parents[2] / "data" / "names" / "curated.yaml"

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

# A PUBLISHER'S NAME IS SOURCED DIFFERENTLY FROM A WORK'S, so it gets its own row rather than
# bending the table above. `official-jp` for a work means the English title the work carries; for a
# company it means the Latin name the company signs itself with, which is on its own site and
# nowhere else. `licensed` has no meaning here at all: nobody licenses a publisher's name.
PUBLISHER_ATTRIBUTION = {
    "official-jp": ("publisher-jp", "platform"),
    "romaji": ("derived",),
    "translated": ("derived",),
}
KIND_ATTRIBUTION = {"titles": ATTRIBUTION, "authors": ATTRIBUTION,
                    "publishers": PUBLISHER_ATTRIBUTION}
CURATED_KINDS = ("titles", "authors", "publishers")

# A source_kind may be named here without being usable as evidence: a candidate records where a
# string was seen, and seeing it in a community database is the ordinary case.
SOURCE_KINDS = ("platform", "publisher-jp", "licensor", "community-db", "derived",
                # A national cataloguing authority, and the person themselves. Both state readings
                # and neither is a publisher or a platform, so neither fitted the list before.
                "national-library", "author",
                # The manga bibliography. It transcribes what a book prints, which is why it may
                # carry `official-jp` for a parallel title and nothing else.
                "bibliography")

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

# WHICH BASES ARRIVE WITH THEIR SOURCE'S OWN DIVISION ALREADY IN THE READING. An openBD collation
# key writes a comma between the halves, an NDL heading divides the reading beside the name, a
# Wikidata item states P734 and P735 separately, and a kana surface is its own reading and divides
# where it is written. `analyser` is absent because an analyser divides every name it is handed,
# and `back-converted` because a romanisation read backwards has already lost the length of every
# vowel and is in no position to be believed about a word break.
#
# `community-printed` WAS HERE FOR ONE DAY AND THE OWNER'S CORRECTION TOOK IT OUT, 2026-08-09.
# The ruling was implemented on a mistyped word: "with overcoming their fallback basis" should have
# read "without". This list is the answer to "did the division arrive cited", and a division typed
# by an anonymous editor is not cited whatever else is true of it, so the basis fails the question
# the list asks.
#
# THE SPACE ITSELF STAYS IN THE STORE AND ON THE PAGE. Nothing about the correction sends 88 people
# back to `Yabuuchiyuu`; what changes is what the record is entitled to claim about the space.
# `check.inv_a_division_cites_its_source` lets the basis past by name, the way it already let
# `back-converted` past, and `divisions resting on a community database` is the number that makes
# the admission visible.
#
# `check.DIVIDED_BY_ITS_SOURCE` asks this, and `boundary.SETTLED_BASES` deliberately answers a
# DIFFERENT question: whether a record may lend its division to some other record. It still carries
# `community-printed`, because a division a reader can be told the origin of is worth more than a
# glued romanisation, and `boundary.donor_basis` is what carries the origin across. The two lists
# and the reason they differ are asserted by `test_curate.test_dividing_bases_and_donors`.
# ASKED OF THE TABLE, not written down beside it. The comment above describes four lists that
# had to be kept consistent by an assertion; `facts/division` states each basis once and every
# question is a column, so there is nothing left to keep consistent.
DIVIDING_BASES = tuple(sorted(_division.bases_where("cited")))

# `reading_note` is separate from `note` because one entry can carry two decisions. A work whose
# English was chosen for one reason and whose reading was corrected for another had to put both
# arguments in one field, or lose one: 55 of the 60 reading corrections landed on titles that
# already had a curated translation with its own note. Two decisions, two reasons.
#
# `reading_source` and `reading_url` join `reading_source_kind` for the same reason it exists: one
# entry can hold two claims sourced from two places. A title translated here and read off a shop
# page had only the entry's `source` to describe both, so 11 readings claiming `stated` named
# `yurarium` as the source and carried no page, while the reading_note beside them named
# BOOK☆WALKER. The note was right and nothing could act on it.
# `translation` IS OUR RENDERING BESIDE A NAME THE WORK ALREADY HAS, and it exists because the
# file could not express the two together. An entry carries one `en`, so a title whose English is
# the publisher's or the licensor's had nowhere to put a translation of the meaning: writing one
# into `en` replaces the attributed name and demotes it, which §5's precedence forbids, and leaving
# it out is what put 225 titles in `titles with no translation of our own`. A reader who moves
# official-jp and licensed down EN_ORDER is asking for exactly the form those entries could not
# hold, and the control was doing nothing for them.
#
# 61 titles already hold both, and every one of them got there by accident: a translation recorded
# in an earlier round was displaced into `en_conflicts` when the licensor page was found later. The
# store keeps a displaced claim, so the shape works; nothing could produce it on purpose.
#
# It carries `translation_note` for the reason `reading_note` is separate from `note`. One entry
# holds two decisions, the argument for each is its own, and a translation with no argument behind
# it is the machine translation §5a rules out.
KEYS = {"en", "candidate", "basis", "source", "source_kind", "source_url", "reviewed", "note",
        "candidate_note", "reading", "reading_basis", "reading_note", "reading_source_kind",
        "reading_source", "reading_url", "reading_boundary", "reading_refuted", "en_refuted",
        "translation", "translation_note"}

# What we call ourselves in the store when a claim is our own judgement rather than a finding.
OURS = "yurarium"

# What a reading may contain. Katakana and the marks that ride along with it: a title's own
# punctuation stays in its reading, and 100日後 keeps its digits, so a rule allowing katakana alone
# rejects readings the store already holds. What it still refuses is kanji and hiragana, which is
# the whole point of the check.
# A reading keeps the title's own bracketed labels and censoring marks verbatim, because they are
# part of the string rather than something to pronounce: 【タテスク】 and the 〇 of 〇〇する話 both
# appear in readings the store already holds.
# WIDER THAN IT WAS, BECAUSE THE PASSES WERE ALREADY WRITING THESE. This validator refused
# characters the store holds in readings the build ships, so a reviewer could not record by hand a
# reading a machine had written: 『死神』 in 鮮血王女 and the U+2010 hyphen in 天華百剣 ‐瞬‐ were both
# rejected while sitting in the store. Two definitions of a valid reading is the §3 fault, and the
# passes' one is the one the data obeys.
#
# HANGUL IS DELIBERATELY STILL REFUSED. It appears in stored readings too, and unlike a bracket it
# is not title punctuation: a reading in Korean is a fact about a record nobody has looked at, and
# admitting it here would stop anybody noticing.
KATAKANA = re.compile(r"^[ァ-ヺー・\s0-9０-９A-Za-zＡ-Ｚａ-ｚ"
                      r"!-/:-@\[-`{-~！-／：-＠［-｀｛-～、。〜…【】〇○◯"
                      r"─━♪♭♯★☆♡♥◎△▽※＆"
                      r"「」『』〈〉《》‐―†→⇔●♀➝×､･àáâäèéêëìíîïñòóôöùúûü]+$")


def _boundary_problems(kind, where, ja, e, rsk):
    """Whether this entry can say where the spaces in its reading came from.

    WHERE A NAME DIVIDES IS A SECOND FACT ABOUT IT (NAMES-PLAN §5e), AND IT NEEDS ITS OWN SLOT.
    `boundary.fill` writes `reading_boundary` and `ndl_heading.entry` wrote the identical fact into
    `reading_note` instead, so 212 records stated their division in a sentence. A sentence cannot be
    queried, counted, or checked, and every check that reads the field therefore believed those
    records had no source for the division at all.

    TWO WAYS TO ANSWER, AND `reading_source_kind` DECIDES WHICH. Where a source supplied the kana it
    supplied the spaces in them, so an NDL transcription or an openBD collationkey cites itself. A
    reading whose kind is `derived` is OURS: nothing came with it, so a division in one was carried
    from a donor and the donor has to be named here.

    THE PROSE MAY STILL SAY MORE. This asks for a field beside the sentence, never instead of it:
    what the note explains is why the division is believable, which no field holds.
    """
    from facts import division as boundary
    # A PERSON ONLY, AND NAMES-PLAN §5f IS THE REASON. A title is a sentence and a publisher is a
    # company, both made of ordinary words, which is what a morphological analyser is built for:
    # 2,532 title readings and 9 publisher readings hold an analyser's division and all of them
    # stay, because their spacing is also what `kana.align` reads to place ruby. A person's name is
    # the case the analyser is worst at and the case where being wrong misnames somebody.
    if kind != "authors":
        return []
    out = []
    divided = boundary.divisions(e.get("reading")) > boundary.divisions(ja)
    if e.get("reading_boundary") and not divided:
        out.append(f"{where}: a reading_boundary on a reading that states no division. The field "
                   f"names where the spaces came from and there are none.")
    if divided and rsk == "derived" and not e.get("reading_boundary"):
        out.append(f"{where}: the kana are ours and the reading divides, so nothing that came with "
                   f"it states where. Name the donor in `reading_boundary`; a division explained "
                   f"only in `reading_note` is a fact no check can read.")
    return out


def problems(kind, ja, e):
    """Everything wrong with one entry. Empty means it may be applied."""
    out = []
    if not isinstance(e, dict):
        return [f"{kind}/{ja}: expected a mapping, got {type(e).__name__}"]
    where = f"{kind}/{ja}"

    # REFUTED WITHOUT A REPLACEMENT, checked first because every other rule here assumes the entry
    # is proposing something. Research sometimes shows a reading is wrong and cannot say what is
    # right: カドコミ files 妻木都 under つ, which disproves the stored ムキ and leaves 都 unresolved.
    # There was no way to record that, so a reading known to be wrong stayed and was rendered.
    # 古川楊也 was published as "HOSHINO Katsura", which is a different person.
    if isinstance(e, dict) and (e.get("reading_refuted") or e.get("en_refuted")):
        bad = list(set(e) - KEYS)
        if bad:
            out.append(f"{where}: unknown key(s) {sorted(bad)}")
        if e.get("reading") or e.get("en"):
            out.append(f"{where}: a refutation cannot also propose a value")
        if not (e.get("reading_note") or e.get("note") or "").strip():
            out.append(f"{where}: a refutation has to say what disproved the reading")
        if not e.get("reviewed"):
            out.append(f"{where}: no reviewed date; this is a decision somebody made")
        return out

    unknown = set(e) - KEYS
    if unknown:
        out.append(f"{where}: unknown key(s) {sorted(unknown)}")

    if not (e.get("en") or e.get("candidate") or e.get("reading")):
        out.append(f"{where}: says nothing; give an `en`, a `candidate` or a `reading`")
    if e.get("en") and e.get("candidate"):
        out.append(f"{where}: an entry is either attributed (`en`) or seen (`candidate`), not both")
    if not e.get("source"):
        out.append(f"{where}: no source")
    if e.get("source_kind") not in SOURCE_KINDS:
        out.append(f"{where}: source_kind {e.get('source_kind')!r} is not one of {SOURCE_KINDS}")
    if not e.get("reviewed"):
        out.append(f"{where}: no reviewed date; a curated entry is a decision somebody made")

    if e.get("en"):
        basis = e.get("basis")
        table = KIND_ATTRIBUTION.get(kind, ATTRIBUTION)
        if basis not in table:
            out.append(f"{where}: basis {basis!r} is not one of {sorted(table)}")
        elif e.get("source_kind") not in table[basis]:
            out.append(f"{where}: basis {basis!r} needs evidence from "
                       f"{' or '.join(table[basis])}, not {e.get('source_kind')!r}")
        if e.get("source_kind") != "derived" and not e.get("source_url"):
            out.append(f"{where}: an attributed name needs the page it was read from")
    elif e.get("basis"):
        out.append(f"{where}: a candidate carries no basis; it is not yet a claim about the work")

    if e.get("translation"):
        # A SECOND FORM, NOT A SECOND OPINION ABOUT WHO NAMED THE WORK. `translation` is only ever
        # ours, so it takes no source and no basis; what it needs is an attributed name to sit
        # beside and an argument of its own.
        if e.get("basis") not in ("official-jp", "licensed"):
            out.append(f"{where}: `translation` is our rendering beside the name the work already "
                       f"has, so the entry needs an `en` on basis official-jp or licensed; with "
                       f"nothing to sit beside, write the translation as `en` on basis translated")
        if e.get("translation") == e.get("en"):
            out.append(f"{where}: the translation repeats the attributed name and adds no form")
        if not (e.get("translation_note") or "").strip():
            out.append(f"{where}: a translation needs a note saying what it rests on")
    elif e.get("translation_note"):
        out.append(f"{where}: translation_note with no translation")

    if e.get("reading"):
        rb = e.get("reading_basis")
        # The reading's own attribution where it is given, and the entry's otherwise. An entry
        # whose translation came from a licensor may still have worked its reading out here, and a
        # licensor does not state Japanese readings, so that entry has to say so rather than
        # inherit a field offered for something else. Falling back to `derived` automatically was
        # tried and is wrong: it would let a licensor stand as evidence for a reading by silence.
        rsk = e.get("reading_source_kind") or e.get("source_kind")
        if rb not in READING_ATTRIBUTION:
            out.append(f"{where}: reading_basis {rb!r} is not one of {sorted(READING_ATTRIBUTION)}")
        elif rsk not in READING_ATTRIBUTION[rb]:
            out.append(f"{where}: reading_basis {rb!r} needs evidence from "
                       f"{' or '.join(READING_ATTRIBUTION[rb])}, not {e.get('source_kind')!r}")
        # Readings are stored as katakana throughout, and an invariant checks it at build time.
        # Catching a hiragana yomi here says which line to fix instead of failing the whole build.
        if not KATAKANA.match(e["reading"]):
            out.append(f"{where}: a reading is stored as katakana; got {e['reading']!r}")
        if rb == "researched" and not ((e.get("reading_note") or e.get("note") or "").strip()):
            out.append(f"{where}: a researched reading needs a note saying what it rests on")
        # THE SAME DEBT THE `en` RULE ABOVE COLLECTS, and it went uncollected for readings. `stated`
        # asserts that a source printed the kana, so there is a page, and a reading published as
        # sourced with nothing behind it is the one thing NAMES-PLAN §1 says must never happen: a
        # plausible reading presented as if it had a source. `derived` is exempt because it is not
        # claiming one.
        if rb == "stated" and rsk != "derived" and not (e.get("reading_url")
                                                        or e.get("source_url")):
            out.append(f"{where}: a stated reading needs the page that states it")
        out += _boundary_problems(kind, where, ja, e, rsk)
    elif e.get("reading_basis"):
        out.append(f"{where}: reading_basis with no reading")
    return out


def check(doc):
    """Validate a whole file. Returns the list of problems across every entry."""
    out = []
    for kind in CURATED_KINDS:
        for ja, e in (doc.get(kind) or {}).items():
            out += problems(kind, ja, e)
    for key in set(doc) - set(CURATED_KINDS):
        out.append(f"unknown top-level key {key!r}")
    return out


# ONE PRODUCER OF THE KEY (§3). This module folded with NFKC alone while `build.py` and the
# interface folded with NFKC and then stripped spaces, so "names a work we hold" had two meanings
# and this one was the stricter: a curated key that differs from a held title by a space was
# reported as naming nothing while applying perfectly.
#
# THE REASONING FOR THE DIFFERENCE WAS SOUND AND IS KEPT, as its own question. A key that differs
# by a full-width bracket is one work under two spellings; a key that differs by a stray space is a
# typo that happens to work, and whoever typed it should hear about it. `spaced_keys` reports those,
# and `unmatched` no longer answers a question the renderer would answer differently.
_fold = key.fold


def unmatched(doc, known):
    """Curated keys that name no work we hold.

    A key is the Japanese title exactly as the catalogue stores it, and a hand-typed one that is
    off by a wave dash or a full-width bracket applies cleanly, changes nothing, and reports
    success. That is the failure this project keeps meeting, so the join is checked rather than
    assumed. Authors are not checked here: an author may legitimately be curated before any of
    their work is, and the same is not true of a title.
    """
    # Folded, because a work reaches us under more than one spelling and only one of them can be
    # on display. ギャルメイドと悪役令嬢 is stored 勝たん！～ by one platform and 勝たん!～ by another,
    # and the curated key stopped naming a work we hold the moment the interface picked the other
    # spelling. NFKC folds the pair without touching the words, which is how the name lookup in
    # build.py joins them too.
    # NO ANSWER IS NOT AN EMPTY ANSWER. `known_titles` returns None where the build has not stated
    # its titles, and folding None into an empty set would report every curated entry as naming
    # nothing, or, worse in the other direction, let a caller treat silence as agreement.
    if known is None:
        raise SystemExit("data/build/titles.json is missing: run build.py before checking the "
                         "curated names against the corpus")
    folded = {_fold(k) for k in known}
    return sorted(k for k in (doc.get("titles") or {}) if k not in known and _fold(k) not in folded)


def spaced_keys(doc, known):
    """Curated keys that reach a held title only because the fold strips spaces.

    Not a fault: the key applies and the reading is shown. It is a hand-typed string that agrees
    with the catalogue about every character except the whitespace, which is worth telling whoever
    typed it so the file stays legible. See the note above `_fold`.
    """
    if known is None:
        return []
    return sorted(k for k in (doc.get("titles") or {})
                  if k not in known and any(key.spaced(k, t) for t in known))


def duplicate_keys(path=None):
    """Keys written twice in the curated file, which YAML resolves by silently keeping the last.

    A DECISION THAT VALIDATES AND DISAPPEARS. `yaml.safe_load` takes the later mapping and drops the
    earlier one without a word, so every check downstream reads a file that parses cleanly and holds
    one of the two entries. 12 titles were in that state, one pair 8,500 lines apart, and appending
    to this file rather than merging is how they got there.

    Read as TEXT, because the parser is what loses them: by the time a dict exists the evidence is
    gone. `(section, key, [line numbers])`.
    """
    import collections
    lines = pathlib.Path(path or FILE).read_text().split("\n")
    section, seen = None, collections.defaultdict(list)
    for n, line in enumerate(lines, 1):
        head = re.match(r"^(%s):" % "|".join(CURATED_KINDS), line)
        if head:
            section = head.group(1)
            continue
        key = re.match(r"^  (\S.*?):\s*$", line)
        if key and section:
            seen[(section, key.group(1))].append(n)
    return [(s, k, ns) for (s, k), ns in seen.items() if len(ns) > 1]


def known_titles(build="data/build"):
    """Every title the build says it knows, folded.

    ASKED, NOT REASSEMBLED. This used to union the feed's rolling window with the series list, and
    later the month archives too, none of which is the corpus: the window forgets a work after a
    fortnight, the archives hold events, and series.json drops rows the interface will not show.
    Three curated titles stopped naming works we hold overnight because the window moved, and the
    three files together still missed 18 works and disagreed with each other about punctuation.

    build.py states the set now, in titles.json, holding titles as it holds them so each consumer
    folds to its own rule. `None` where the file is absent, so a caller can tell "no answer" from
    "no titles". Given no answer the check stops and says so: an empty set would pass everything.
    """
    import json
    p = pathlib.Path(build) / "titles.json"
    if not p.exists():
        return None
    return set(json.loads(p.read_text()).get("titles") or [])


def todo(build="data/build", limit=None, curated=None):
    """Works still showing a romanisation, most recently updated first.

    WHY THIS IS A FUNCTION AND NOT A QUERY SOMEBODY TYPES. The queue for the first two rounds of
    curation was picked with the filter "has no `en`", which is wrong: a machine romanisation IS
    an `en`, so every work already carrying one was excluded from the very pass meant to replace
    it. あなたのとなり is four kana meaning next to you and was skipped as already named, because
    Anata no Tonari was sitting in the field. Choosing the queue by hand reintroduces that each
    time; generating it does not.

    A romanisation is the finished answer for some titles, so this is a queue to review rather
    than a list of faults, and it is ordered by what a reader is most likely to be looking at.
    """
    import json
    names = json.loads(pathlib.Path(f"{build}/feed/names.json").read_text())["titles"]
    feed = json.loads(pathlib.Path(f"{build}/feed/current.json").read_text())["releases"]

    import unicodedata
    fold = lambda t: unicodedata.normalize("NFKC", t or "").replace(" ", "")
    latest = {}
    for r in feed:
        latest[r["work"]] = max(latest.get(r["work"], ""), r.get("pub") or "")
    for w in {s["work"] for s in json.loads(pathlib.Path(f"{build}/series.json").read_text())["series"]}:
        latest.setdefault(w, "")

    # A DECISION ALREADY MADE IS NOT WORK OUTSTANDING, whichever way it went. §5a keeps a title
    # romanised where translating is the wrong answer, and 球詠 and ぬるめた are as settled as any
    # translation is. Leaving them in the queue would report a finished state as pending, which is
    # the same category error this project met in the claim dispositions: it asks somebody to go
    # and do a thing that has been done and cannot be improved by doing again.
    #
    # The test is whether the work appears in curated.yaml at all, rather than what its basis says,
    # because that is exactly the record of a person having decided.
    decided = set((load(curated) if curated else load()).get("titles") or {})
    out = []
    for work, when in latest.items():
        rec = names.get(fold(work)) or {}
        if rec.get("basis") in ("official-jp", "licensed", "translated") or work in decided:
            continue
        out.append((when, work, (rec.get("romaji") or {}).get("macron") or rec.get("en")))
    out.sort(key=lambda x: (x[0] or "", x[1]), reverse=True)
    return out[:limit] if limit else out


def apply(store, doc):
    """Record every entry. Returns (applied, candidates)."""
    applied = candidates = 0
    for kind in CURATED_KINDS:
        for ja, e in (doc.get(kind) or {}).items():
            # EVERY KEY THE FILE MAY CARRY, and it used to be a shorter list than KEYS. Three that
            # a reviewer writes were built into the fact by nobody and reached no store:
            # `reading_source_kind`, so a reading read off a platform was filed under the entry's
            # own `derived`; `reading_note`, which is 814 arguments for 814 hand-settled readings
            # and the very thing `researched` is required to supply; and `reviewed`, which was
            # flattened onto `at` and so could not be told from the day a pass happened to run.
            fact = {k: e.get(k) for k in
                    ("en", "candidate", "basis", "source", "source_kind", "source_url", "note",
                     "candidate_note", "reading", "reading_basis", "reading_note",
                     "reading_source_kind", "reading_source", "reading_url", "reading_boundary",
                     "reviewed")}
            # `at` is the day the decision was reviewed, not the day this ran. Re-applying the file
            # after a rebuild must not restamp a name as freshly decided.
            fact["at"] = str(e.get("reviewed"))
            # The file is the decision of record, so re-applying it after an edit must change the
            # answer rather than filing the new wording as a conflict against the old one.
            fact["supersede"] = True
            store.record(kind, ja, **fact)
            # A refutation removes what is there and puts nothing in its place, so the name renders
            # as the Japanese it is. record() has no way to express an absence, so it is done here.
            if e.get("reading_refuted") or e.get("en_refuted"):
                rec = store.records[kind].get(ja) or {}
                why = str(e.get("reading_note") or e.get("note") or "")[:300]
                if e.get("reading_refuted"):
                    # WHAT BELONGS TO A CLAIM IS THE STORE'S TO SAY, because the store is what
                    # stamps it on. The list here was hand-written and short by six fields, so 11
                    # refuted readings kept a source and a date for a reading that had been
                    # withdrawn, and two kept a URL pointing at the MangaUpdates page for a
                    # different person: the page the refutation was written to disown. 古川楊也 was
                    # published as HOSHINO Katsura and the record went on citing the page that
                    # said so.
                    store.clear_claim(kind, ja, "reading")
                    rec["reading_refuted"] = why
                # An English name can be somebody else's too, and by the same route: MangaUpdates
                # gave 古川楊也 the author page of hoshino-katsura, so the database published a
                # different person's name in English beside their work.
                if e.get("en_refuted"):
                    store.clear_claim(kind, ja, "en")
                    rec["en_refuted"] = why
            # OUR RENDERING BESIDE THE WORK'S OWN, recorded as a second claim because that is what
            # it is. `translated` ranks below `official-jp` and `licensed`, so the store files it
            # in `en_conflicts` and the attributed name goes on displaying; build.py assembles
            # `en_forms` from both, and the reader's EN_ORDER control finally has something to
            # reach for.
            #
            # NO `supersede` HERE, and the stale form is dropped by hand instead. Superseding
            # clears the slot, which for this claim is the licensor's name, so the translation
            # would take the display and the attribution would be pushed aside. Re-wording a
            # translation would otherwise leave the old wording standing beside the new one, which
            # is a conflict list disagreeing with itself: the exact fault `_supersede` was written
            # for, met by the other door.
            tr = e.get("translation")
            if tr:
                rec = store.records[kind].get(ja) or {}
                stale = [c for c in (rec.get("en_conflicts") or [])
                         if c.get("basis") == "translated" and c.get("source") == OURS
                         and c.get("value") != tr]
                if stale:
                    rec["en_conflicts"] = [c for c in rec["en_conflicts"] if c not in stale]
                store.record(kind, ja, en=tr, basis="translated", source=OURS,
                             source_kind="derived", translation_note=e.get("translation_note"),
                             at=str(e.get("reviewed")))
            # A REFUTATION THE FILE HAS WITHDRAWN LEAVES THE RECORD, which is the same rule the
            # store applies to a citation the file stops carrying and was missing here. A
            # refutation says nothing can be put in this slot, and research eventually putting
            # something there is the one outcome it was written to wait for. 生肉's セイニク was
            # dropped in August with the artist's X handle noted and nothing to do with it;
            # まんが王国 files them ナマニク and @namanoniku0005 spells the same thing. Replacing
            # the entry left the record holding a reading AND the refutation of one, so the file
            # could record the decision and could not reverse it, and `pass4_analyser` reads that
            # field to decide whether a name may be filled at all.
            for claim in ("reading", "en"):
                if e.get(claim) and not e.get(f"{claim}_refuted"):
                    (store.records[kind].get(ja) or {}).pop(f"{claim}_refuted", None)
            if e.get("en"):
                applied += 1
            else:
                candidates += 1
    return applied, candidates


def load(path=FILE):
    return yaml.safe_load(pathlib.Path(path).read_text()) or {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", default=str(FILE))
    ap.add_argument("--out", default="data/names")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--build", default="data/build", help="where to look up the titles we hold")
    ap.add_argument("--todo", type=int, nargs="?", const=40, metavar="N",
                    help="list works still showing a romanisation, newest first, and stop")
    a = ap.parse_args(argv)

    if a.todo:
        rows = todo(a.build)
        for when, work, shown in rows[:a.todo]:
            print(f"  {when or '        '}  {work[:44]:46} {shown}")
        print(f"\n{len(rows)} work(s) still show a romanisation; {min(a.todo, len(rows))} listed")
        return 0

    doc = load(a.file)
    # BEFORE ANYTHING PARSED, because the parser is what loses them. A key written twice validates,
    # applies cleanly and holds one of the two decisions.
    dups = duplicate_keys(a.file)
    for section, key, lines in dups:
        print(f"  DUPLICATE {section}/{key[:34]}: written at lines "
              f"{', '.join(str(n) for n in lines)}; YAML keeps the last and drops the rest")
    bad = check(doc)
    for b in bad:
        print(f"  REJECT {b}")
    stray = unmatched(doc, known_titles(a.build))
    for s in stray:
        print(f"  STRAY  titles/{s}: names no work in the catalogue")
    counts = {k: len(doc.get(k) or {}) for k in CURATED_KINDS}
    print(f"{counts['titles']} title(s), {counts['authors']} author(s), "
          f"{counts['publishers']} publisher(s); "
          f"{len(bad)} rejected, {len(stray)} matching nothing, {len(dups)} written twice")
    if bad or stray:
        return 1
    if a.apply:
        store = NameStore(a.out)
        applied, cands = apply(store, doc)
        store.compact()
        store.close()
        print(f"applied {applied} attributed name(s) and {cands} candidate(s) to {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
