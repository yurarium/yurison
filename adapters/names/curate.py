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
import pathlib as _pl0
import sys as _sys0

_sys0.path.insert(0, str(_pl0.Path(__file__).resolve().parents[1]))

import population as _population  # noqa: E402

import argparse
import pathlib
import re
import unicodedata
import sys

import yaml

# BEFORE THE `facts` IMPORTS, WHICH IS THE WHOLE POINT OF THE LINE. It used to sit below them, so
# `from facts import reading` resolved only when `adapters` was already on the path and the usage
# this module's own docstring documents, `curate.py --check` from the repo root, died on
# ModuleNotFoundError. Found on 2026-08-13 wiring the pass into the daily update, which is the
# first thing that ever ran it the documented way.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from facts import reading as _reading  # noqa: E402
from facts import division as _division  # noqa: E402
from names import key  # noqa: E402
from names.store import NameStore  # noqa: E402

FILE = pathlib.Path(__file__).resolve().parents[2] / "data" / "names" / "curated.yaml"

ATTRIBUTION = _reading.ATTRIBUTION

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

SOURCE_KINDS = _reading.SOURCE_KINDS

# THE RULINGS MOVED TO `facts/reading`, which is where a standing decision about what may
# be believed belongs. This module applies them; it no longer also states them.
READING_ATTRIBUTION = _reading.READING_ATTRIBUTION

STATED_BASES = _reading.STATED_BASES

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
# `en_source`, `en_url` and `en_source_kind` MIRROR THE READING'S, and they were missing while
# the reading's existed. The store already lets a claim's own citation outrank the entry's, so the
# machinery was there and only this file could not reach it: an entry whose English came from a
# licensor and whose reading was read off the title had one `source_url` between them, and the
# reading was stamped with the licensor's page. お姉さまと巨人 cited Yen Press for a reading nobody
# there stated. What was asymmetric was the vocabulary and not the model.
KEYS = {"en", "candidate", "basis", "source", "source_kind", "source_url", "reviewed", "note",
        "en_source", "en_url", "en_source_kind",
        "candidate_note", "reading", "reading_basis", "reading_note", "reading_source_kind",
        "reading_source", "reading_url", "reading_boundary", "reading_refuted", "en_refuted",
        "translation", "translation_note",
        # THE KANA ARE THEMSELVES A TRANSLITERATION, which no rule can detect. ステファン・セジク
        # romanises to `Sutefan Sejiku`, a transliteration of a transliteration, and the person is
        # Stjepan Šejić; but るいす・まくられん is credited beside 楽時たらひ on Japanese anthologies
        # and is a pen name playing with a foreign sound. Katakana is not evidence of a foreign
        # name, so this is a ruling somebody records per name and never a detector.
        "transliterates",
        # AND A TITLE WHOSE ENGLISH OURS WOULD ONLY REPEAT, which no rule can detect
        # either. `スカーレット` is the English word Scarlet in kana and the publisher
        # printed `Scarlet`; `安達としまむら` is two surnames. `translation` is refused
        # when it repeats the `en`, so those titles could say nothing at all and sat in
        # `titles with no translation of our own` as work nobody could ever do.
        "translation_refused"}

# What we call ourselves in the store when a claim is our own judgement rather than a finding.
OURS = "yurarium"

# CATALOGUES THAT FLATTEN A TITLE ONTO ONE LINE. Both transcribe to ISBD, where the parallel title
# follows an equals sign and the volume follows a full stop, and both drop the space after a comma
# doing it. Three works checked against their own artwork all set the space, or set the comma at a
# line end where nothing could follow it: おやすみシェヘラザード breaks after `Nighty night,` on the
# cover of book one, 先輩、美味しいですか sets `Senpai, does it taste good?` on one line in its series
# art, and ヴァンピアーズ sets `VAMPEERZ, MY PEER VAMPIRES` under its logo. The catalogues recorded all
# three closed up.
#
# WHY THIS IS NOT A REWRITE RULE. A Japanese cover really does sometimes close the comma up, so a
# pass that silently inserted the space would be asserting a typography nobody looked at: 一億年ボタン
# prints `shita Oreha,Saikyo ni natteita` on its own cover, romanising a fullwidth 、 with no space.
# The catalogue cannot tell the two apart and neither can a regex, so this refuses the entry and
# sends somebody to the work.
FLATTENS_THE_COMMA = ("mediaarts-db", "openBD")

#: A comma with a letter hard against it. Digits are left alone: `Vol.1,2` is a list and not a title
#: set across two lines.
CLOSED_COMMA = re.compile(r",[A-Za-z]")

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

    # A RULING THAT PROPOSES NO NAME, checked here for the same reason the refutation above is:
    # every rule below assumes the entry is claiming something. `transliterates` records that the
    # kana are themselves a transliteration and that a search did not find the Latin spelling. That
    # is a finding about the SURFACE and cites nothing, so `no source` and `source_kind` would both
    # be demanding a citation for a search that came back empty.
    #
    # IT STILL OWES A NOTE AND A DATE. An unsettled name is a decision somebody made to stop
    # looking, and a reader of the file has to be able to see which routes were tried.
    if (isinstance(e, dict) and e.get("transliterates")
            and not (e.get("en") or e.get("candidate") or e.get("reading"))):
        bad = list(set(e) - KEYS)
        if bad:
            out.append(f"{where}: unknown key(s) {sorted(bad)}")
        if not (e.get("note") or "").strip():
            out.append(f"{where}: a transliteration ruling has to say which routes were tried")
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
    # AND THE PER-CLAIM ONES ARE THE SAME VOCABULARY. Unchecked, a misspelt `en_source_kind` reads
    # as an entry saying nothing about where its English came from, which is the entry's own
    # `source_kind` answering for it. That is the silent fallback this pair of keys exists to end.
    for k in ("en_source_kind", "reading_source_kind"):
        if e.get(k) is not None and e.get(k) not in SOURCE_KINDS:
            out.append(f"{where}: {k} {e.get(k)!r} is not one of {SOURCE_KINDS}")
    if not e.get("reviewed"):
        out.append(f"{where}: no reviewed date; a curated entry is a decision somebody made")

    if e.get("en"):
        basis = e.get("basis")
        table = KIND_ATTRIBUTION.get(kind, ATTRIBUTION)
        # THE ENGLISH'S OWN SOURCE OUTRANKS THE ENTRY'S, exactly as `reading_source_kind` does
        # below. `en_source_kind` was added to KEYS and passed through to the store, and this test
        # went on reading the entry's `source_kind`, so the vocabulary existed and the check could
        # not see it. What it cost: 17 titles read off ndlsearch carry the catalogue as the entry's
        # source because that is where the KANA came from, and a translation of our own beside one
        # of them was rejected for resting on a national library that translated nothing.
        esk = e.get("en_source_kind") or e.get("source_kind")
        if basis not in table:
            out.append(f"{where}: basis {basis!r} is not one of {sorted(table)}")
        elif esk not in table[basis]:
            out.append(f"{where}: basis {basis!r} needs evidence from "
                       f"{' or '.join(table[basis])}, not {esk!r}")
        if esk != "derived" and not (e.get("source_url") or e.get("en_url")):
            out.append(f"{where}: an attributed name needs the page it was read from")
        if (e.get("en_source") or e.get("source")) in FLATTENS_THE_COMMA and CLOSED_COMMA.search(e["en"]):
            out.append(f"{where}: {e.get('en_source') or e.get('source')} transcribes a title onto "
                       f"one line, so a comma closed up in {e['en']!r} is the catalogue's and not "
                       f"the work's. Read the comma off the work and cite that page instead")
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

    if e.get("translation_refused"):
        # THE RULING SAYS THERE IS NOTHING TO WRITE, so it has to be about a title that already has
        # an English name and it has to carry the argument. Without the first it is a title nobody
        # translated; without the second it is a decision with no reasoning behind it, which is the
        # one thing this file exists to stop.
        if e.get("translation"):
            out.append(f"{where}: an entry either translates the title or records why it cannot, "
                       f"and this does both")
        if e.get("basis") not in ("official-jp", "licensed"):
            out.append(f"{where}: `translation_refused` says our rendering would only repeat the "
                       f"name the work already has, so the entry needs an `en` on basis "
                       f"official-jp or licensed for it to repeat")
        if len(str(e["translation_refused"]).split()) < 4:
            out.append(f"{where}: `translation_refused` carries the argument rather than a flag; "
                       f"say what our rendering would come out as and why that is the same name")

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
        # THE READING'S OWN NOTE, and not the record's. Accepting `note` as a fallback made this
        # report nothing while thirteen researched readings had no reasoning recorded: their notes
        # argued for the ENGLISH name, several of them saying only which licensor page states the
        # Japanese title, which is evidence about a translation and not about a reading. The store's
        # own CHECK reads `reading_note` alone, refused eight of the rows, and was right. A record
        # carries nine `reading_*` keys precisely so a claim about one predicate is not settled by
        # an argument about another.
        if rb == "researched" and not (e.get("reading_note") or "").strip():
            out.append(f"{where}: a researched reading needs a reading_note saying what it rests on")
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
        raise SystemExit("no titles to check against: run ./build.py before checking the "
                         "curated names against the corpus")
    folded = {_fold(k) for k in known}
    # A WORK RULED OUT OF SCOPE IS NOT A TYPO. `data/scope.yaml` carries the §6 rulings, and a work
    # ruled `out-of-scope` stops being published, so its curated entry stops naming a work we hold
    # while remaining a decision somebody made and recorded. Reporting those as strays would ask a
    # reviewer to delete the reasoning for a retraction, which is the one thing the file is for.
    out_of_scope = {_fold(k) for k in _ruled_out_of_scope()}
    return sorted(k for k in (doc.get("titles") or {})
                  if k not in known and _fold(k) not in folded and _fold(k) not in out_of_scope)


def _ruled_out_of_scope(path=None):
    """Titles `data/scope.yaml` rules out under DEFINITIONS §6, or nothing where it has no rulings."""
    at = pathlib.Path(path or (pathlib.Path(__file__).resolve().parents[2] / "data" / "scope.yaml"))
    if not at.exists():
        return ()
    doc = yaml.safe_load(at.read_text(encoding="utf-8")) or {}
    got = []
    for x in (doc.get("rulings") or []):
        if str((x or {}).get("disposition") or "") != "out-of-scope":
            continue
        # A RULING MAY NAME A LINE AND NOT A BOOK. A prose imprint is ruled once and names its
        # eleven works in `works`; reading the top-level title alone saw none of them, and eleven
        # curated names went on looking like keys that match nothing in the catalogue.
        for m in (x.get("works") or [x]):
            got.append(str((m or {}).get("title") or ""))
    return tuple(x for x in got if x)


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

    A FIELD WRITTEN TWICE INSIDE ONE ENTRY GOES THE SAME WAY, and looking only at the top level is
    the check sharing its subject's blind spot. Merging an entry that already held a reading put a
    second `source` and `reviewed` under 11 titles at once: the file parsed, the top level was
    clean, and each entry quietly held one of its two dates.
    """
    import collections
    lines = pathlib.Path(path or FILE).read_text().split("\n")
    section, entry, seen, fields = None, None, collections.defaultdict(list), {}
    for n, line in enumerate(lines, 1):
        head = re.match(r"^(%s):" % "|".join(CURATED_KINDS), line)
        if head:
            section, entry = head.group(1), None
            continue
        key = re.match(r"^  (\S.*?):\s*$", line)
        if key and section:
            # QUOTED AND UNQUOTED ARE ONE KEY. YAML reads `"惚れた女の遺言.mp3":` and
            # `惚れた女の遺言.mp3:` as the same name and keeps the later; this compared the raw text
            # and saw two, so an entry written in one style beside an entry in the other passed the
            # check and then vanished into the other one. Found on 2026-08-10 when a curated English
            # name was applied, validated, reported clean, and did not reach the store.
            # KEYED ON THE BLOCK AND NOT ON ITS NAME, because two blocks sharing a name are two
            # blocks. Pooling their fields reports the second `en:` of a duplicated entry as a
            # duplicated field, which is one fault counted twice and named wrongly the second time.
            name = key.group(1).strip()
            if len(name) > 1 and name[0] == name[-1] and name[0] in "\"'":
                name = name[1:-1]
            entry = (section, name, n)
            seen[(section, name)].append(n)
            continue
        field = re.match(r"^    ([A-Za-z_]+):", line)
        if field and entry:
            fields.setdefault((entry, field.group(1)), []).append(n)
    out = [(s, k, ns) for (s, k), ns in seen.items() if len(ns) > 1]
    out += [(e[0], f"{e[1]}.{f}", ns) for (e, f), ns in fields.items() if len(ns) > 1]
    return out


def known_titles(build="data/build"):
    """Every title the build says it knows, folded.

    ASKED, NOT REASSEMBLED. This used to union the feed's rolling window with the series list, and
    later the month archives too, none of which is the corpus: the window forgets a work after a
    fortnight, the archives hold events, and series.json drops rows the interface will not show.
    Three curated titles stopped naming works we hold overnight because the window moved, and the
    three files together still missed 18 works and disagreed with each other about punctuation.

    `emit.titles` states the set now, from the store, holding titles as it holds them so each
    consumer folds to its own rule. A named build directory is still read where it holds the file,
    which is how a person checks against an older compile. With neither, `population` stops the run
    rather than answering nothing: an empty set would pass every curated title.
    """
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    import population
    return set(population.titles(pathlib.Path(build) / "titles.json" if build else None))


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
    _nf = pathlib.Path(f"{build}/feed/names.json")
    names = (_population.names(_nf if _nf.exists() else None).get("titles") or {})
    feed = json.loads(pathlib.Path(f"{build}/feed/current.json").read_text())["releases"]

    import unicodedata
    fold = lambda t: unicodedata.normalize("NFKC", t or "").replace(" ", "")
    latest = {}
    for r in feed:
        latest[r["work"]] = max(latest.get(r["work"], ""), r.get("pub") or "")
    _named = pathlib.Path(f"{build}/series.json")
    for w in {s["work"] for s in _population.series(_named if _named.exists() else None)}:
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
                     "en_source", "en_url", "en_source_kind",
                     "candidate_note", "reading", "reading_basis", "reading_note",
                     "reading_source_kind", "reading_source", "reading_url", "reading_boundary",
                     "transliterates", "translation_refused", "reviewed")}
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
