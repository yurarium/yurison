#!/usr/bin/env python3
"""Whether a reading can show where it came from, and the address it shows.

WHY THIS EXISTS. The store has recorded a reading's source since the first pass: 2,273 author
records name one. What nothing did was decide what a READER gets to see of it, so `names.json`
shipped the basis and dropped the source, the address and the date. 771 author readings held a
page anyone could open and no page was ever offered.

WHAT WAS ACTUALLY MISSING, measured before any of this was written, because the brief said the
count was zero and it was not:

    reading_source     2,273        reading_url        771 of the 2,262 with a reading
    reading_reviewed   0            reading_note       0 in the store, 814 in curated.yaml

Every source with a web address already carried one, at 100% for openBD, MADB, the National Diet
Library, Wikidata and each platform. The two large blocks holding none are the two that have none
to hold: a name written in kana is its own reading, and a morphological analyser is not a document.
Neither is a gap and neither gets an invented address.

THE ONE PRODUCER (§3). `store._stamp` writes a claim's citation and `store._stamped` names its
parts. `cite` below reads them back for display and is the only thing build.py asks. Nothing
recomputes an address from an ISBN or a record id a second time, because the pass that fetched the
page is the only thing that knows which page it read.

WHAT `faults` DELIBERATELY DOES NOT SHARE (§14b). The check must not verify with the producer's own
logic, so `faults` does not call `cite` and does not look at `reading_url` to decide whether one is
owed. It asks the BASIS, which is the claim's own statement about itself, and which `_stamp` has
never consulted: `_stamp` copies whatever address a pass hands it and would copy one just as
happily onto an analyser guess. So "the basis says a document states this" and "an address is
held" are produced by different things, and the check is the assertion that they agree.

That is what caught the fault this module was written for. 11 curated titles said
`reading_basis: stated` while carrying `source: yurarium` and no page, because one curated entry
holds two claims and had one citation between them: the entry's own `source` described the
TRANSLATION, and the reading was stamped with it. The reading_note beside each named BOOK☆WALKER,
which is where the reading really came from, and prose is not something a check can act on.
"""

# Bases that assert somebody else's document. Only these owe an address, and the debt is what
# `faults` collects.
#
#   stated             a source prints the kana: a yomi field, a collationkey, furigana in a byline
#   back-converted     a romanised string recovered from a database entry, which is that entry's page
#   community-printed  a community database prints the kana, which is an item page anybody can read
#
# `community-printed` OWES ONE FOR THE SAME REASON THE OTHERS DO, and rather more urgently. The
# project owner ruled Wikidata noncanonical on 2026-08-09, so the reading carries a mark saying the
# pronunciation is unconfirmed, and the citation is what lets a Japanese-literate reader go and
# settle it. Withholding the address while marking the reading would tell a reader there is a doubt
# and then decline to say where the doubt came from. All 73 hold a `wikidata.org/entity/` URI.
#
# THE OWNER'S CORRECTION LATER THAT DAY LEAVES IT HERE, and reviewing it is how that was settled
# rather than assumed. The corrected ruling is that Wikidata does not overcome the record's fallback
# basis, so the basis lost its place in `curate.DIVIDING_BASES`, where membership means a claim
# arrived cited. This list asks something else: whether there is a document behind the string, and
# an item page anybody can open is a document whatever standing its editor had. The address is not
# an argument that the reading is right. It is the route to the page that would show a reader it is
# wrong (§14c), and a marked fallback needs that more than a stated reading does.
#
# Everything else is the record accounting for itself and owes nothing. `surface` means the name is
# already kana, so there was no lookup and there is no page to cite. `analyser`, `aligned` and
# `guessed` are machine work, labelled `verified: false` and marked in the interface under
# NAMES-PLAN §5d. `researched` is a reviewer weighing evidence that no single page states, which is
# why curate.py demands a note from it instead of a URL.
SOURCED = ("stated", "back-converted", "community-printed")

# THE ENGLISH CLAIM IS THE SAME QUESTION WITH A DIFFERENT VOCABULARY, and it was reachable here all
# along: `cite` took a `claim` argument from the day it was written and nothing ever passed one, so
# 286 official and licensed titles reached a reader with no way to say where the English came from
# while `data/names/curated.yaml` held the licensor's address for each. 転生王女と天才令嬢の魔法革命
# carries a Yen Press page and ぬるめた a COMIC FUZ one.
#
# WHICH BASES OWE AN ADDRESS, AND WHY IT IS NOT ALL FOUR. NAMES-PLAN §5 splits the English forms
# into somebody else's name for the work and ours. `official-jp` is the name the author, magazine
# or Japanese publisher uses and `licensed` is what an English-language licensor publishes it as,
# so both assert a document and both are shown unmarked, which is exactly the state §1 warns about:
# an assertion with the evidence withheld. `translated` and `romaji` are ours, they are already
# marked in the interface as ours, and there is no page anywhere to point at.
#
# THE BASIS FIELD IS NOT SPELT THE SAME WAY EITHER. A reading's basis is `reading_basis` and the
# English claim's is bare `basis`, because it came first and was the only one. Named here rather
# than assumed, since assuming it gave `en_basis`, which no record has ever held, so a citation for
# the English name could never have been produced whatever was passed in.
BASIS_FIELD = {"reading": "reading_basis", "en": "basis"}
SOURCED_BASES = {"reading": SOURCED, "en": ("official-jp", "licensed")}

# A SOURCE THAT IS THE NAME ITSELF OWES NO DOCUMENT. `surface` on the reading side means the name
# is already kana and nothing was looked up, and it is a basis there. On the English side it
# arrives as a SOURCE under an `official-jp` basis, which is the same statement about a different
# claim: CONTINUE?, DOUBLE HELIX BLOSSOM and 19 others are titles the work publishes in Latin
# already, so the work's own name is the English name and there is no page anywhere that could be
# cited for it. Naming it here rather than treating an absent address as the fault is what keeps
# the fault population real: the one record left is 新・魔法科高校の劣等生 キグナスの乙女たち,
# whose own note says the rendering is ours and whose basis says a licensor's.
# `title-furigana` is the same statement about a title. A work whose own title prints how a word in
# it is read (`恋する小惑星（アステロイド）`) states the reading in the string, so there is no page
# behind it beyond the source record already carrying that string. `names/gloss.py` records it.
SELF_SOURCED = ("surface", "title-furigana")

# The parts of a citation a reader is offered, and the store field each is read from. `{v}` is the
# claim: `reading` or `en`. Kept in step with `store._stamped`, which writes them.
#
# `note` IS NOT ONE OF THEM, decided by the project owner 2026-08-08. The store holds 1,247 author
# reading notes and 3,044 title notes, and they are our reasoning for our own decisions: why a
# reviewer settled one reading over another, what was weighed. That is a fact about us and
# STANDING-INSTRUCTIONS §6 keeps those off a reader's page. The citation says which document, where
# and when, which is what a reader can act on; 704 notes shipped in feed/names.json before this and
# nothing rendered one.
import re

PARTS = (("source", "{v}_source"), ("url", "{v}_url"), ("kind", "{v}_source_kind"),
         ("reviewed", "{v}_reviewed"))

# AN ISBN IS A CITATION EVEN WHERE A URL IS NOT. openBD answers by ISBN and its only address is a
# query against its API, which is not a page a reader can open, so 227 readings it genuinely stated
# were shown nothing at all. That is our filing showing through: the fact is the publisher's own
# registration for a book, and the book has an identifier a reader can act on. The identifier is
# lifted out of the query rather than stored twice, because the query already carries it and a
# second copy is a second producer of one fact.
ISBN_IN_QUERY = re.compile(r"[?&]isbn=(\d{10,13})")

# The same list plus the note, for `faults`, which asks whether a citation was left behind by a
# claim that went away. A note is part of the debris in that case even though it is not shown.
PARTS_HELD = PARTS + (("note", "{v}_note"),)


def basis_of(record, claim="reading"):
    return (record or {}).get(BASIS_FIELD.get(claim, f"{claim}_basis"))


def owes_a_document(record, claim="reading"):
    """Whether this claim asserts somebody else's document and therefore owes an address."""
    return (basis_of(record, claim) in SOURCED_BASES.get(claim, ())
            and (record or {}).get(f"{claim}_source") not in SELF_SOURCED)


def cite(record, claim="reading"):
    """What this claim can show for itself, or None where it has nothing to show.

    NONE IS AN ANSWER AND NOT A GAP (§5 of the standing instructions). A kana name and an analyser
    guess both return None, because there is no document behind either, and offering the reader an
    empty citation would state that one is missing. The analyser's readings are already marked
    unverified, which is the honest thing to say about them and the thing a reader can act on.

    A CITATION IS OFFERED ONLY FOR A CLAIM THAT EXISTS. A refuted reading used to leave its source
    and its URL standing, so the record cited a page for a reading it no longer made; two of them
    cited the MangaUpdates page for a different person, which is the page the refutation was
    written to disown. `store.clear_claim` removes them now, and this refuses to render one
    regardless, because a display path that trusts the data to be clean is how the first one shipped.
    """
    if not record.get(claim):
        return None
    if not owes_a_document(record, claim):
        return None
    # AN ADDRESS IS WHAT MAKES IT A CITATION, and it has to be one we may send a reader to. A
    # source named with no page behind it is the state the invariant exists to drive to zero, and
    # rendering it would put "openBD" in front of a reader with nothing to open, which is a fact
    # about our filing and not about the name. A closed route is worse: it would publish an
    # invitation to a path the host asked us not to take.
    url = record.get(f"{claim}_url")
    isbn = None
    if not citable(url):
        # A QUERY THAT NAMES A BOOK STILL NAMES THE BOOK. The address is refused, and what it
        # identified is kept, so the citation says which registration was read without inviting a
        # reader down a route we do not send them. Anything else with no citable address still
        # returns None, which is the honest answer where nothing identifies the source.
        m = ISBN_IN_QUERY.search(str(url or ""))
        if not m:
            return None
        isbn = m.group(1)
    out = {}
    for key, field in PARTS:
        if key == "url" and isbn:
            continue
        value = record.get(field.format(v=claim))
        if value:
            out[key] = value
    if isbn:
        out["isbn"] = isbn
    return out or None


def is_address(value):
    """Whether a string is an address at all.

    Deliberately crude, and crude in the safe direction. It is asserting that the field holds a
    location and not a description of one: `openBD` and `the artist's own site` are both true
    statements about where a reading came from and neither is something to click.
    """
    return isinstance(value, str) and value.startswith(("http://", "https://"))


# Routes this project has ruled closed, as (host, path prefix). An address here is fine to have
# recorded and must not be put in front of a reader.
#
# ndlsearch.ndl.go.jp/api is disallowed in the host's own robots.txt (REQUIREMENTS §1), so linking
# it would advertise a route we have agreed not to take and would send every reader who follows the
# citation down it. 35 author readings hold one. They are also the wrong SHAPE for a citation
# whatever the rule said: the recorded address is the creator SEARCH the pass ran, and a search is
# not the record that states the reading.
CLOSED_ROUTES = (("ndlsearch.ndl.go.jp", "/api"),)

# Addresses that resolve to DATA rather than to a document, as (host, path prefix). A different
# reason from the one above and the same treatment, so they are held in a separate table and the
# reason is not lost.
#
# `api.openbd.jp/v1/get?isbn=…` states the reading: the collationkey in that JSON is where 196
# author readings came from, and it is the record and not a search, which is what separates it from
# the NDL case. What it is not is a page. A reader following the citation gets a wall of JSON,
# which is our filing shown to somebody who asked about a name, so the citation is withheld and
# counted like any other. openBD publishes no per-book reader page to point at instead, so this one
# falls only if the reading is re-sourced somewhere a person can read it.
DATA_ENDPOINTS = (("api.openbd.jp", "/"),)


def citable(value):
    """Whether an address may be shown to a reader, which is a stricter question than `is_address`.

    Held separately on purpose. The invariant asks whether an address was recorded at all, and
    these records did record one, so folding the two together would report a pass that did its job
    as a pass that did not. What this catches is counted instead, and it falls when the record page
    is recorded in place of the query.
    """
    if not is_address(value):
        return False
    rest = value.split("//", 1)[1]
    host, _, path = rest.partition("/")
    return not any(host == h and ("/" + path).startswith(p)
                   for h, p in CLOSED_ROUTES + DATA_ENDPOINTS)


def uncitable(names, claim="reading"):
    """Readings holding an address that may not be shown, as `(name, url)`.

    The gap between what the store legitimately records and what a page may link to. Everything
    here is a reading a reader would otherwise be offered a citation for, so the count is the
    number of citations silently withheld, and silence is the thing this project designs against.

    A RECORD THAT CITES BY ANOTHER ROUTE IS NOT SILENT. openBD answers by ISBN and its only address
    is a query against its API, which is not a page to send anybody to, so these were counted here
    and shown nothing. `cite` now keeps the identifier out of the refused query, so the reader is
    told which registration was read. The address is still not shown and never will be; what has
    changed is that the citation is no longer empty, which is what this counts. A record with no
    identifier of any kind stays here, because that one really does show nothing.
    """
    return [(ja, (r or {}).get(f"{claim}_url"))
            for ja, r in sorted((names or {}).items())
            if (r or {}).get(claim) and owes_a_document(r, claim)
            and is_address((r or {}).get(f"{claim}_url"))
            and not citable((r or {}).get(f"{claim}_url"))
            and not cite(r, claim)]


def borrowed(names):
    """Records citing ONE page for two claims that say they came from different kinds of source.

    THE HALF OF THE §3 FAULT AN ADDRESS DOES NOT FIX. A record holds a reading and an English
    rendering, and where only one page was ever stated the store stamps it onto both. If the two
    claims name different kinds of source then at most one of them can be right about where it came
    from, and the record cannot say which.

    IT RUNS BOTH WAYS, which is why this counts records and does not accuse a field. 100日後に咲く
    百合 cited Yen Press for a Japanese reading, and Yen Press publishes the English title and
    states no reading anywhere. Thirteen titles are the mirror: Wikidata really does state their
    reading in P1814, and our own translation borrowed the Wikidata address, so it is the English
    name citing a page that did not give it.

    Arithmetic on the finished record. It compares two addresses for equality and two source kinds
    for difference, consults no pass, no basis and no lookup table, and cannot be satisfied by a
    producer that is consistently wrong. That is what keeps it out of `faults`, whose question is
    whether an address is held at all: every record here holds one.

    BOTH KINDS HAVE TO BE KNOWN. An absent kind is silence about where a claim came from, and
    reading silence as disagreement made a fault of every record stating one kind and not the other.

    This is a count, because clearing one needs the page somebody actually read and some of those
    were never written down. 犬井あゆ and 野宮りおん carry readings the National Diet Library states,
    recorded without the record id, and nothing on disk recovers it.
    """
    out = []
    for ja, record in sorted((names or {}).items()):
        record = record or {}
        url = record.get("reading_url")
        if not url or url != record.get("en_url"):
            continue
        mine, theirs = record.get("reading_source_kind"), record.get("en_source_kind")
        if mine and theirs and mine != theirs:
            out.append((ja, mine, theirs, url))
    return out


def faults(names, claim="reading"):
    """Every record whose citation and whose claim disagree, as `(name, fault, detail)`.

    Two shapes, and they are opposite failures of the same rule.

    `cannot-show-its-source` is a claim that a document states this, with no document named. That
    is the reader being told a reading is sourced and given no way to check it, and it is the state
    11 curated titles and one author reading were in.

    `citation-without-a-claim` is the reverse: an address, a source or a date left behind by a
    reading that was withdrawn. Arithmetic on the record and nothing else, so it owes nothing to
    any pass and cannot be satisfied by one.

    A BASIS WITH NO STRING IS A CLAIM AND NOT DEBRIS, which is what the second test guards.
    `_merge_group` says so outright: an author marked `romaji` carries a basis and no `en`, because
    §8.1 generates the romanisation per reader from the kana rather than storing one. 196 author
    records are in that state with a source recorded beside them, and reading the missing string as
    a withdrawn claim would have made a fault of the commonest healthy shape on the English side.
    A withdrawn claim has no basis either: `clear_claim` takes the basis with the value.
    """
    out = []
    for ja, record in sorted((names or {}).items()):
        record = record or {}
        held = record.get(claim)
        cited = {field.format(v=claim): record.get(field.format(v=claim))
                 for _key, field in PARTS_HELD}
        cited = {k: v for k, v in cited.items() if v}
        if held:
            if owes_a_document(record, claim) and not is_address(
                    record.get(f"{claim}_url")):
                out.append((ja, "cannot-show-its-source",
                            f"basis {basis_of(record, claim)!r} from "
                            f"{record.get(f'{claim}_source')!r} with no address"))
        elif cited and not basis_of(record, claim):
            out.append((ja, "citation-without-a-claim",
                        ", ".join(f"{k}={v!r}" for k, v in sorted(cited.items()))[:160]))
    return out
