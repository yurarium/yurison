#!/usr/bin/env python3
"""Pass 2 — the bulk databases (NAMES-PLAN §3.2-§3.4, §7).

THE PLAN'S ORDER IS AniList → MangaUpdates → Wikidata. This runs Wikidata FIRST, and the reason is
§8.1 rather than coverage. Wikidata is the only one of the three that returns a KANA READING:
P1814 (name in kana) gives 宮澤伊織 → みやざわ いおり, with P734/P735 splitting family from given so
both name orders stay available (§8.2). AniList and MangaUpdates return ROMANISED strings — "Iori
Miyazawa", "MIYAZAWA Iori" — and a romanised string is the one form §8.1 refuses to treat as the
stored answer, because Yuri cannot tell you whether it was ゆり or ゆうり.

So Wikidata's hits are `community-printed` readings and the other two produce `back-converted` ones
that a later kana source is allowed to overwrite. None of the three STATES a reading: the project
owner ruled on 2026-08-09 that Wikidata is noncanonical and is used to raise the floor on romaji,
which is a rank above the analyser and below everything a publisher or the national library prints.
Running the source that gives real readings first means
the ranks resolve the right way round without depending on the order at all — but it also means the
best data arrives first, which matters for a job that may be stopped at any point.

ANILIST IS SWITCHED OFF, TODAY. Every request returns HTTP 403 with:

    "The AniList API has been temporarily disabled due to severe stability issues."

That is the plan's single best-ranked external source (§3.2) and the whole basis for "1055 titles is
~40 requests, not 1055". It is implemented here in full, batched by alias exactly as §3.2 and §7
describe, and it detects the shutdown and reports the source as unavailable — which, per the rule
in resolver.py, records NO attempts against any name. Getting that wrong would be expensive in a
way that is invisible until much later: 1055 titles marked "asked AniList, nothing found" during an
outage would never be asked again, and the plan's best source would be permanently written off on
the strength of somebody else's bad week.

WHAT EACH SOURCE IS ACTUALLY FOR

  wikidata      authors AND titles. Batched with a VALUES list, so a few requests cover everything.
                Authors: kana readings, family/given split, an English label. Titles: an English
                label — recorded as a CANDIDATE, see below. Thin on web-only serials, authoritative
                where it hits, CC0 so the licence question does not arise (§3.4).

  anilist       titles, and the staff on them. Batched by GraphQL alias. Currently unavailable.

  mangaupdates  titles, one request each — its API has no batch form, which is why it runs after
                the two that do. Better tail coverage of web and indie series (§3.3). Used for
                romanisation and for matching; its English titles are candidates only.

NONE OF THESE CAN SAY A TITLE IS OFFICIAL, and that is the project owner's correction to §5 rather
than caution on our part. The precedence for an English title is:

    official-jp   what the author, magazine or Japanese publisher calls it in English
    licensed      what an English-language licensor publishes it as
    ours          our translation or romanisation, marked as ours

and FAN OR SCANLATION TITLES ARE EXCLUDED ENTIRELY — not ranked last, not a fallback, not recorded
as a lead, because they are not a name the work has. All three sources here are community-editable
and MangaUpdates is largely a scanlation-community database, so an English title from any of them
may be any of the three, with nothing in the record to say which. They therefore produce
`en_candidates` entries: recorded, attributed, and never promoted to `en` without confirmation from
a Japanese publisher page or a licensor catalogue.

Romanisations are exempt from all of that. A transliteration is mechanical rather than chosen, so
there is no community judgement in it to be wrong about, and §8.1 wants the reading it back-
converts to. That is why these sources still resolve a useful number of titles despite the rule.

The only `official-jp` these passes legitimately produce is pass 0's: a title already printed in
Latin on the Japanese platform's own page IS the work's English name.

MATCHING IS THE PLACE THIS GOES WRONG QUIETLY. A search endpoint always returns its best guess, and
its best guess for a title we hold is frequently a different work with a similar name. Assigning
that work's English title to ours would produce a confident, plausible, wrong answer — the exact
failure §1 is built around, one step removed. So every source here verifies that what came back
actually IS the thing asked for: Wikidata by matching an exact label or alias, AniList by comparing
`title.native` to the query, MangaUpdates by requiring `hit_title` to equal the query. Anything
less exact is a miss, and a miss is cheap.

Usage:  pass2_bulk.py --source wikidata --kind authors
        pass2_bulk.py --source mangaupdates --kind titles --limit 50
        pass2_bulk.py --source all --offline        # replay every stored response, send nothing
"""
import argparse
import json
import pathlib
import re
import unicodedata
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names import inputs, kana  # noqa: E402
from names.resolver import Fact, HttpCache, Resolver, SourceUnavailable, drive  # noqa: E402
from names.store import NameStore  # noqa: E402
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import paths


# Japanese function words, as they appear in a romanisation. A Latin string carrying several of
# these is a transliteration of the Japanese rather than an English title.
JA_PARTICLES = {
    "wa", "ga", "no", "ni", "to", "wo", "de", "dewa", "kara", "made", "yo", "ne", "na", "mo",
    "ka", "nite", "toshite", "desu", "masu", "masen", "suru", "shita", "naru", "nai", "tai",
    "dake", "koto", "mono", "sono", "kono", "ano", "watashi", "boku", "kimi", "anata", "ore",
}
JA_SUFFIX = re.compile(r"-(chan|san|kun|sama|senpai|sensei|tachi)\b", re.I)
MACRON = re.compile(r"[āīūēōâîûêô]", re.I)
TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)


def romanises_this(ja, romaji):
    """True where a romanisation is long enough, and short enough, to be THIS title's.

    MangaUpdates confirms identity on `hit_title`, which may be any of a record's associated
    titles, and then hands back `record.title`, which romanises the PRIMARY one. Where a series is
    catalogued under two Japanese names those are different strings, and nothing downstream can
    tell: the only other test compares Latin against Japanese and passes whatever it is given. So
    お姉さまと巨人 ～お嬢さまが異世界転生～ took a romanisation covering its first seven characters.

    Length is the one thing the two strings can be compared on without reading either. A kana reads
    as one mora, a kanji as one to four, and Latin and digits as up to three each; two morae of
    slack at each end covers elision and the ー. This is deliberately loose. It is here to catch a
    romanisation belonging to a different work, which is off by a factor, and not to adjudicate a
    reading, which is somebody else's job.
    """
    back = kana.romaji_to_kana(romaji or "")
    if not back:
        return True                       # nothing to measure; the other tests still apply
    lo = hi = 0
    for c in ja or "":
        if kana.is_kana(c):
            lo += 1
            hi += 1
        elif "一" <= c <= "鿿" or c == "々":
            lo += 1
            hi += 4
        elif c.isascii() and c.isalnum():
            hi += 3
    small = "ャュョぁぃぅぇぉァィゥェォ"
    morae = sum(1 for c in back if kana.is_kana(c) and c not in small)
    return max(1, lo - 2) <= morae <= hi + 2


def looks_romanised(en, ja):
    """True when a Latin string is a transliteration of the Japanese, not an English name.

    This decides whether a community database's English field is usable at all. A romanisation is
    mechanical and can be taken at face value; an English NAME from the same field may be a
    licensed title, a Japanese publisher's own, or a scanlation title, and becomes a candidate
    instead. "Bloom Into You" and "Kimi to Shiranai Natsu ni Naru" arrive through the same field, so
    without this test either every romanisation is treated as a chosen name or every chosen name is
    treated as a romanisation — and §5 marks the two differently in the interface.

    Four signals, combined so that no single weak one can decide:

      - a macron. Only romanised Japanese has one, so this settles it alone.
      - two or more Japanese function words as standalone tokens. TWO, not one: "This Monster Wants
        to Eat Me" contains `to`, and English is entitled to its own prepositions.
      - an attached honorific — but NOT on its own. English titles keep honorifics routinely
        ("JK-chan and Her Male Classmate's Mom" is an official English title), so -chan only counts
        alongside something else.
      - the whole string converting cleanly back to kana. kana.romaji_to_kana returns None on any
        syllable that is not Japanese, so a clean conversion means every token was a Japanese
        syllable — strong, but not sufficient by itself, because "Wataten!" converts perfectly and
        is the work's official English title.
    """
    if not en:
        return False
    if MACRON.search(en):
        return True
    tokens = [t.lower() for t in TOKEN.findall(en)]
    particles = sum(1 for t in tokens if t in JA_PARTICLES)
    if particles >= 2:
        return True
    honorific = bool(JA_SUFFIX.search(en))
    convertible = bool(tokens) and kana.romaji_to_kana(" ".join(tokens)) is not None
    return honorific and (particles >= 1 or convertible)


def norm(s):
    """Comparison form for "is this the same title". Deliberately loose about presentation and
    strict about content: case, width, spacing and decorative brackets vary between databases and
    never mean a different work, but a different word does."""
    # NFKC first, or the width the docstring promises to ignore is not ignored. Without it
    # けいおん！Ｓｈｕｆｆｌｅ never matched its own half-width form in a source database, and neither
    # did ７日間限定彼女 or ルミナス＝ブルー: 15 of 1,055 titles here. Folding introduces no new
    # collisions, which was measured across the whole catalogue before the line was added.
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = kana.to_katakana(s).lower()
    s = "".join(c for c in s if not c.isspace())
    return re.sub(r"[~〜～・･\-‐−–—’'\"“”「」『』()（）\[\]【】!！?？.,、。:：;；/／＆&]", "", s)


# --------------------------------------------------------------------------------------------
# Wikidata

WDQS = "https://query.wikidata.org/sparql"

# Work classes we will accept a title match from. Without this, a one-word title like 恋 matches an
# entity that is a concept, a song and a village, and the English label of a village is not a
# translation of the manga. Checked client-side because it keeps the SPARQL simple enough to stay
# inside the query timeout with a 120-item VALUES list.
WORK_TYPES = {
    "Q8274", "Q21198342", "Q747381", "Q1004", "Q1107", "Q562061",   # manga, manga series, light novel, comics, anime
    "Q7725634", "Q47461344", "Q571", "Q49084", "Q8261",             # literary work, written work, book, short story, novel
    "Q5398426", "Q11424", "Q1261214", "Q63952888",                  # tv series, film, tv special, animated series
    "Q104637332", "Q25379", "Q1760610", "Q20937557",                # webcomic-ish, play, comic book, series
}

# Occupations that make a matched human plausibly the person who drew or wrote a manga. This is not
# fussiness: matching a short kana pen name against Wikidata's aliases is a false-positive machine,
# because あまね, のん, みなみ and はづき are also singers, actors and AV idols with the same alias.
# Measured on the first 240 authors, unfiltered matching attributed のん to three different people
# and gave あまね the English name of an AV idol. Both would have been published as an author's name.
CREATOR_OCCUPATIONS = {
    "Q191633",    # mangaka
    "Q715301",    # comics artist
    "Q1114448",   # cartoonist
    "Q644687",    # illustrator
    "Q1062952",   # character designer
    "Q6625963",   # novelist
    "Q36180",     # writer
    "Q482980",    # author
    "Q12406482",  # comics creator
}

# ?how distinguishes a match on the item's MAIN label from a match on one of its aliases, and that
# distinction is load-bearing. P1814 is the kana for the item's own name, not for every alias it
# carries: 古川楊也 is an alias of the person whose P1814 reads ホシノ カツラ, and taking that at face
# value publishes 古川楊也 as "Hoshino Katsura" — a reading of a different name, presented as this
# one's. The English label has the same defect for the same reason. So an alias match is allowed to
# confirm that the person exists and is a creator, and nothing more.
# ?jalabel is the item's OWN Japanese label, fetched so it can be compared with the string we asked
# about — which is how an alias match is told from a main-label one, and that distinction is
# load-bearing. P1814 is the kana for the item's own name, not for every alias it carries: 古川楊也
# is an alias of the person whose P1814 reads ホシノ カツラ, and taking that at face value publishes
# 古川楊也 as "Hoshino Katsura" — a reading of a different name, presented as this one's. The
# English label has the same defect for the same reason. So an alias match confirms the person
# exists and is a creator, and nothing more.
#
# Done with one OPTIONAL rather than a UNION over the two match kinds, which reads more directly
# but times WDQS out at this VALUES size — measured, not assumed.
AUTHOR_SPARQL = """SELECT ?item ?ja ?jalabel ?en ?kana ?fkana ?gkana ?occ WHERE {
  VALUES ?ja { %s }
  ?item rdfs:label|skos:altLabel ?ja .
  ?item wdt:P31 wd:Q5 ; wdt:P106 ?occ .
  OPTIONAL { ?item rdfs:label ?jalabel FILTER(lang(?jalabel)="ja") }
  OPTIONAL { ?item rdfs:label ?en FILTER(lang(?en)="en") }
  OPTIONAL { ?item wdt:P1814 ?kana }
  OPTIONAL { ?item wdt:P734/wdt:P1814 ?fkana }
  OPTIONAL { ?item wdt:P735/wdt:P1814 ?gkana }
}"""

# ?jalabel carries the item's OWN Japanese label, so a match on one of its aliases can be told
# apart from a match on its name. AUTHOR_SPARQL has selected it since the 古川楊也 / ホシノ カツラ
# failure and this query never did, which left the title side with the same fault and no way to see
# it: 彩香ちゃんは弘子先輩を落としたい and its sibling 〜に恋してる are both bound to one item, and it
# handed the same English label to both.
TITLE_SPARQL = """SELECT ?item ?ja ?jalabel ?en ?type WHERE {
  VALUES ?ja { %s }
  ?item rdfs:label|skos:altLabel ?ja .
  OPTIONAL { ?item rdfs:label ?jalabel FILTER(lang(?jalabel)="ja") }
  ?item wdt:P31 ?type .
  ?item rdfs:label ?en FILTER(lang(?en)="en")
}"""


class Wikidata(Resolver):
    """One SPARQL query per batch of names, matched on an exact label or alias (§3.4)."""

    name = "wikidata"
    kinds = ("authors", "titles")
    provides = "either"
    # Titles are long — several run past 40 characters — and 120 of them in a URL query string is
    # enough for WDQS to answer 503 rather than parse it. Names are short, so they keep the bigger
    # batch; the request count is small either way.
    batch = 120
    title_batch = 60

    def lookup(self, kind, names, cache):
        query = (AUTHOR_SPARQL if kind == "authors" else TITLE_SPARQL) % " ".join(
            '"%s"@ja' % n.replace("\\", "\\\\").replace('"', '\\"') for n in names)
        # POST rather than GET. A VALUES list of 120 titles makes a query string several kilobytes
        # long, which WDQS rejects outright — and a rejection looks exactly like "none of these
        # exist" to anything that is not paying attention.
        text = cache.get("wikidata", WDQS,
                         body=urllib.parse.urlencode({"query": query}),
                         headers={"Accept": "application/sparql-results+json",
                                  "Content-Type": "application/x-www-form-urlencoded"})
        try:
            doc = json.loads(text)
        except json.JSONDecodeError:
            # WDQS answers a timeout with an HTML error page. That is the service declining, not a
            # statement that none of 120 names exists.
            raise SourceUnavailable("wikidata returned a non-JSON body (query timeout?)")

        # Rows are grouped by name before anything is decided, because the decisions that matter —
        # is this one person or several, is any of them a creator — are properties of the whole
        # result set for a name, not of any single row.
        rows = {}
        for b in doc.get("results", {}).get("bindings", []):
            ja = b.get("ja", {}).get("value")
            if ja in names:
                rows.setdefault(ja, []).append(b)

        out = {}
        for ja, group in rows.items():
            fact = (self._author_fact(ja, group) if kind == "authors"
                    else self._title_fact(ja, group))
            if fact:
                out[ja] = [fact]
        return out

    @staticmethod
    def _author_fact(ja, group):
        """One fact, or nothing, from every Wikidata row matching this name.

        TWO GUARDS, both learned from the data rather than assumed:

        AMBIGUITY. If the name matches more than one human, we have not found the author — we have
        found that the pen name is shared. のん is an actress, a singer and a voice actor before it
        is our manga author, and picking whichever row came back first would attribute a stranger's
        name to somebody's work. Several matches is a miss, not a choice.

        OCCUPATION. A single match still has to be a plausible creator: あまね matched exactly one
        human, an AV idol, and would have been published as this author's English name.
        """
        items = {b["item"]["value"] for b in group}
        if len(items) != 1:
            return None
        occupations = {b.get("occ", {}).get("value", "").rsplit("/", 1)[-1] for b in group}
        if not (occupations & CREATOR_OCCUPATIONS):
            return None

        item = next(iter(items))
        # An alias match tells us the person exists and is a creator. It does NOT tell us how THIS
        # name is read or written in English — see the note on AUTHOR_SPARQL — so those fields are
        # only taken from rows where the string we asked about was the item's own label.
        own = [b for b in group if (b.get("jalabel") or {}).get("value") == ja]
        if not own:
            return None
        reading = fkana = gkana = en = None
        for b in own:
            reading = reading or (b.get("kana") or {}).get("value")
            fkana = fkana or (b.get("fkana") or {}).get("value")
            gkana = gkana or (b.get("gkana") or {}).get("value")
            en = en or (b.get("en") or {}).get("value")

        fact = Fact(source_url=item, **{"pass": 2})
        if reading:
            # `community-printed` IS WHAT WIKIDATA IS, AND THE READING SAYS SO. Ruled by the project
            # owner on 2026-08-09: "treat wikidata as noncanonical. use it to raise the floor on
            # romaji". P1814 prints KANA, so an editor typed the reading and nothing was recovered
            # from a romanisation, which is what puts it above the analyser; nobody with standing
            # over the person's name typed it, which is what keeps it below everything a publisher
            # or the national library prints. `curate.READING_ATTRIBUTION` carries the argument and
            # the two rows this one is NOT.
            #
            # THE MARK FOLLOWS THE BASIS AND IS NOT SET HERE. `store._verify` derives `verified`
            # from `reading_basis`, so moving off `stated` is the whole of what turns the `[?]` on
            # for these 67 records. Writing the flag beside the basis would be a second producer of
            # one fact, which is how the two came to disagree in the first place.
            fact.update(reading=kana.to_katakana(reading), reading_basis="community-printed",
                        reading_source_kind="community-db")
            # Wikidata writes a full reading as "family given". Where P734/P735 did not supply the
            # halves, that space carries the same information (§8.2), and both name orders stay
            # available only if we know which half is which.
            parts = reading.split()
            if not fkana and len(parts) == 2:
                fkana, gkana = parts
        if fkana:
            fact["reading_family"] = kana.to_katakana(fkana)
        if gkana:
            fact["reading_given"] = kana.to_katakana(gkana)
        if en and norm(en) != norm(ja):
            # `romaji`, NOT `stated`. §1 reserves `stated` for a preference the author has shown —
            # a handle, a signature, a Latin byline. A Wikidata English label is an editor's
            # romanisation, usually in Western order (あおのなち → "Nachi Aono"), and treating an
            # editor's choice as the author's own would let it outrank the real thing later.
            fact.update(en=en, basis="romaji",
                        note="Wikidata English label; word order is the source's, not the author's")
        return fact if (reading or en) else None

    @staticmethod
    def _title_fact(ja, group):
        """The English label, when every work matching this title agrees on what it is.

        A title routinely matches several items — the manga, the anime, the film — and that is not
        ambiguity, because they share a name. Disagreement is: two different works with the same
        Japanese title and different English ones, where picking either asserts something we did
        not check.
        """
        works = [b for b in group
                 if b.get("type", {}).get("value", "").rsplit("/", 1)[-1] in WORK_TYPES]
        # AN ALIAS MATCH NAMES THE ITEM, NOT THIS TITLE. A work catalogued under two Japanese names
        # binds both to one item, and the item's English label belongs to the name it is filed
        # under. Taking it for the alias publishes one work's English name on another's record.
        # Rows from before ?jalabel was selected carry none, and are left as they were rather than
        # discarded: absent is not the same as different, and re-querying settles them.
        labelled = [b for b in works if b.get("jalabel")]
        if labelled:
            works = [b for b in labelled if (b.get("jalabel") or {}).get("value") == ja]
            if not works:
                return None
        labels = {}
        for b in works:
            en = (b.get("en") or {}).get("value")
            # An English label identical to the Japanese is Wikidata having no English name for the
            # work, not an English name that happens to be Japanese.
            if en and norm(en) != norm(ja):
                labels.setdefault(norm(en), (en, b["item"]["value"]))
        if len(labels) != 1:
            return None
        en, item = next(iter(labels.values()))
        if looks_romanised(en, ja):
            # A romanisation is safe to take at face value from any of these sources: it is a
            # mechanical rendering of the Japanese, not a name anyone chose, so the scanlation
            # problem does not arise. It is also a reading spelled in the wrong alphabet —
            # recovering the kana gives the title a reading it would otherwise have had none of,
            # lossy in the long vowels (§8.1) and so recorded as back-converted.
            fact = Fact(en=en, basis="romaji", source_kind="community-db",
                        source_url=item, **{"pass": 2})
            back = kana.romaji_to_kana(en)
            if back:
                fact.update(reading=back, reading_basis="back-converted")
            return fact
        # An English NAME, on the other hand, is a candidate and not an attribution. Wikidata's
        # label usually reflects a licensed release, but it is community-editable and the project
        # owner's correction is explicit that "usually" is not the standard: until it can be traced
        # to a Japanese publisher or a licensor catalogue it is not `licensed` and certainly not
        # `official-jp`. Recorded so a later confirmation is one fetch away, not re-research.
        return Fact(candidate=en, source_kind="community-db", source_url=item,
                    candidate_note="Wikidata English label; usually a licensed title, but "
                                   "community-editable and unconfirmed",
                    **{"pass": 2})


# --------------------------------------------------------------------------------------------
# AniList

ANILIST = "https://graphql.anilist.co"
ANILIST_DISABLED = re.compile(r"temporarily disabled|has been disabled", re.I)

ALIAS = """  t%(i)d: Media(search: %(q)s, type: MANGA) {
    id siteUrl
    title { romaji english native }
    staff(perPage: 4) { edges { role node { id siteUrl name { full native last first } } } }
  }"""


class AniList(Resolver):
    """§3.2's batching: many lookups ride one request as GraphQL aliases.

    IMPLEMENTED AND CURRENTLY DEAD. See the module docstring — the API answers 403 "temporarily
    disabled" to everything. The shutdown is detected and reported as the source being unavailable,
    which records no attempts, so the day it comes back every name is still open.
    """

    name = "anilist"
    kinds = ("titles",)
    provides = "either"
    batch = 25

    def lookup(self, kind, names, cache):
        body = json.dumps({"query": "query {\n%s\n}" % "\n".join(
            ALIAS % {"i": i, "q": json.dumps(n, ensure_ascii=False)} for i, n in enumerate(names))})
        text = cache.get("anilist", ANILIST, body=body,
                         headers={"Content-Type": "application/json", "Accept": "application/json"})
        if ANILIST_DISABLED.search(text):
            raise SourceUnavailable("anilist: API disabled by the operator (HTTP 403)")
        try:
            doc = json.loads(text)
        except json.JSONDecodeError:
            raise SourceUnavailable("anilist returned a non-JSON body")
        data = doc.get("data") or {}
        if not data and doc.get("errors"):
            raise SourceUnavailable(f"anilist: {doc['errors'][0].get('message')}")

        out = {}
        for i, ja in enumerate(names):
            media = data.get(f"t{i}")
            if not media:
                continue
            # The search endpoint returns its best guess for anything. Only an exact native-title
            # match is this work; a near match is a different work with a similar name.
            if norm(media.get("title", {}).get("native")) != norm(ja):
                continue
            facts = []
            url = media.get("siteUrl")
            english = (media.get("title") or {}).get("english")
            romaji = (media.get("title") or {}).get("romaji")
            if english and norm(english) != norm(ja):
                if looks_romanised(english, ja):
                    facts.append(Fact(en=english, basis="romaji", source_kind="community-db",
                                      source_url=url, **{"pass": 2}))
                else:
                    # `title.english` is usually the licensed title and is community-editable, so
                    # it is a lead rather than proof. Candidate, per the correction to §5.
                    facts.append(Fact(candidate=english, source_kind="community-db", source_url=url,
                                      candidate_note="AniList title.english; usually the licensed "
                                                     "title but community-editable and unconfirmed",
                                      **{"pass": 2}))
            if romaji and norm(romaji) != norm(ja):
                # `title.romaji` is fine as romanisation — it is the mechanical rendering, not a
                # name anyone chose.
                facts.append(Fact(en=romaji, basis="romaji", source_kind="community-db",
                                  source_url=url, **{"pass": 2}))
                back = kana.romaji_to_kana(romaji)
                if back:
                    facts.append(Fact(reading=back, reading_basis="back-converted",
                                      source_url=url, **{"pass": 2}))
            if facts:
                out[ja] = facts
        return out


# --------------------------------------------------------------------------------------------
# MangaUpdates

MU_SEARCH = "https://api.mangaupdates.com/v1/series/search"
MU_SERIES = "https://api.mangaupdates.com/v1/series/%s"
# The description carries the licensor link for licensed works, and the slug in that URL is the
# official English title as the publisher writes it. Only accepted when an associated title agrees.
MU_OFFICIAL = re.compile(r"Official English Release:.{0,40}?\]\((https?://[^)]+)\)", re.S)


class MangaUpdates(Resolver):
    """§3.3, one request per title because the API offers no batch form.

    Two requests for a hit: the search establishes that MangaUpdates holds this exact Japanese
    title, and the series record then supplies the associated-title list and the romanised authors.
    The second request only ever happens for a confirmed match, so the cost tracks hits rather than
    the queue.
    """

    name = "mangaupdates"
    kinds = ("titles",)
    provides = "either"
    batch = 1

    def __init__(self, store=None, credits=None):
        # Authors come back on a title's record, so this source resolves names of a kind it was not
        # asked about. They are written straight through rather than returned, because drive() is
        # scoped to one kind at a time.
        #
        # `credits` maps our Japanese title to the authors WE hold for it, and without it the
        # author half of this source is dead: MangaUpdates gives "MIZUNO Eita" with no Japanese
        # beside it, and a romanised string cannot be matched to 水野英多 by string comparison.
        # The work is the join.
        self.store = store
        self.credits = credits or {}
        self.author_hits = 0

    def lookup(self, kind, names, cache):
        ja = names[0]
        body = json.dumps({"search": ja, "perpage": 5}, ensure_ascii=False)
        text = cache.get("mu-search", MU_SEARCH, body=body,
                         headers={"Content-Type": "application/json"})
        try:
            doc = json.loads(text)
        except json.JSONDecodeError:
            raise SourceUnavailable("mangaupdates returned a non-JSON body")

        for hit in doc.get("results") or []:
            if norm(hit.get("hit_title")) != norm(ja):
                continue
            rec = hit.get("record") or {}
            return {ja: self._facts(ja, rec, cache)}
        return {}

    def _facts(self, ja, rec, cache):
        """What MangaUpdates may and may not be believed about.

        The project owner's correction is specific about this source: MangaUpdates is largely a
        SCANLATION-community database, so its English titles are frequently fan names. A fan title
        is not ranked last — it is not a name the work has at all, and publishing one would attach
        a name to a book that nobody with any standing ever gave it.

        So the split here is by what kind of claim the field is, not by how confident it looks:

          romanisation      believed. A transliteration is mechanical; there is no community
                            judgement in it to be wrong, and §8.1 wants the reading it yields.
          English title     candidate only, whatever its apparent provenance — including the
                            licensor link, which is a community-entered URL rather than a licensor
                            catalogue we have read. Confirming one costs a single fetch of the page
                            it names, which is why the URL is kept.
          identity          used, never recorded. That MangaUpdates holds this exact Japanese title
                            is what makes the record the right record; it says nothing in English.
        """
        facts = []
        romaji = rec.get("title")
        url = rec.get("url")
        detail = self._detail(rec.get("series_id"), cache)
        associated = [a.get("title") for a in (detail.get("associated") or []) if a.get("title")]

        licensor = self._licensor_title(rec.get("description") or "", associated)
        if licensor:
            title, licensor_url = licensor
            facts.append(Fact(candidate=title, source_kind="community-db", source_url=licensor_url,
                              candidate_note="MangaUpdates names this licensor page as the "
                                             "official English release; the link is community-"
                                             "entered and has not been fetched, so unconfirmed",
                              **{"pass": 2}))

        if romaji and norm(romaji) != norm(ja):
            if looks_romanised(romaji, ja) and not romanises_this(ja, romaji):
                # The record is about a work whose name this is not. Identity was confirmed on an
                # associated title and the romanisation describes the primary one, so nothing here
                # can be attributed to the title we asked about.
                romaji = None
            if romaji and looks_romanised(romaji, ja):
                facts.append(Fact(en=romaji, basis="romaji", source_kind="community-db",
                                  source_url=url, **{"pass": 2}))
                back = kana.romaji_to_kana(romaji)
                if back:
                    # §8.1: lossy in exactly the long vowels the style toggle cares about, so it is
                    # recorded as back-converted and any kana source outranks it.
                    facts.append(Fact(reading=back, reading_basis="back-converted",
                                      source_url=url, **{"pass": 2}))
            else:
                # MangaUpdates' main title field holds an English name for some series rather than
                # a romanisation, and on this source an English name is exactly the thing that may
                # be a scanlation title. Candidate.
                facts.append(Fact(candidate=romaji, source_kind="community-db", source_url=url,
                                  candidate_note="MangaUpdates main title, not a romanisation; "
                                                 "may be a scanlation title",
                                  **{"pass": 2}))
        # Associated titles are NOT recorded, not even as leads. On a scanlation-community database
        # the associated list is where fan titles live, and the correction excludes them entirely.
        self._record_authors(ja, detail, cache)
        return facts

    def _detail(self, series_id, cache):
        if not series_id:
            return {}
        text = cache.get("mu-series", MU_SERIES % series_id)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _licensor_title(description, associated):
        """The English title a licensor's own URL implies, plus that URL. A CANDIDATE, not a fact.

        The description carries `**Official English Release:** [Publisher](url)`, and the slug in
        that URL is what the publisher calls the work. Requiring an associated title to match the
        slug keeps out URL conventions that are not titles — but two agreeing fields of the same
        community record are still one community record, so this cannot promote itself to
        `licensed`. What it can do is name the page that WOULD settle it, which is why the URL
        travels with the candidate.
        """
        m = MU_OFFICIAL.search(description)
        if not m:
            return None
        url = m.group(1)
        slug = urllib.parse.urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
        if not slug or not re.fullmatch(r"[a-z0-9-]+", slug):
            return None
        want = slug.replace("-", "")
        for title in associated:
            if re.sub(r"[^a-z0-9]", "", title.lower()) == want:
                return title, url
        return None

    def _record_authors(self, ja_title, detail, cache):
        """Join MangaUpdates' romanised credits to our Japanese ones, but only when it is certain.

        MangaUpdates writes a credit as `MIYAZAWA Iori` — family in caps, given in title case. That
        capitalisation is the only statement of name ORDER any source here makes, and §8.2 says to
        record which order a fetched name came in rather than assuming, so the halves are stored
        separately and both orders stay renderable. Where the convention is not followed, nothing
        is split rather than something guessed.

        THE JOIN IS ONE-TO-ONE OR NOTHING. Nothing in the record says which romanised credit
        corresponds to which of our authors, and a romanised string cannot be string-matched to
        水野英多 — so the WORK is the join. But matching by position would be a coin toss on any
        title with a writer and an artist, and getting it wrong assigns the artist's reading to the
        writer: §1's exact failure, with two people misnamed instead of one. So the association is
        taken only when our credit for this work names exactly one person and MangaUpdates lists
        exactly one. §2 notes 810 of 965 authors appear on a single work, so the strict rule still
        reaches most of them.

        This is also the only route in passes 0-2 by which a KANJI author name acquires a reading
        at all — back-converted and so unverified, but a starting point where there was none.
        """
        if not self.store:
            return
        ours = self.credits.get(ja_title) or []
        # One person credited as both Author and Artist is listed twice, with the same author_id.
        # Counting the rows rather than the people made the one-to-one rule reject essentially
        # every series — MangaUpdates duplicates far more often than it does not.
        theirs, seen = [], set()
        for a in detail.get("authors") or []:
            key = a.get("author_id") or a.get("name")
            if a.get("name") and key not in seen:
                seen.add(key)
                theirs.append(a)

        pair = self._pair(ours, theirs)
        if not pair:
            return
        ja, a = pair
        latin = a["name"]
        fam, giv = self._split_caps(latin)
        # `romaji`, never `stated`: a community-supplied romanisation is not a preference the
        # author has expressed, and letting it take the top rank would block the real thing.
        fact = {"en": latin, "basis": "romaji", "source": "mangaupdates",
                "source_kind": "community-db", "source_url": a.get("url"), "pass": 2}
        back = kana.romaji_to_kana(latin)
        if back:
            fact.update(reading=back, reading_basis="back-converted")
        if fam:
            fact.update(note=f"MangaUpdates name order: family={fam} given={giv}",
                        reading_family=kana.romaji_to_kana(fam),
                        reading_given=kana.romaji_to_kana(giv))
        self.store.record("authors", ja, **fact)
        self.author_hits += 1

    @staticmethod
    def _pair(ours, theirs):
        """Match one of our Japanese authors to one of MangaUpdates' romanised ones, or nothing.

        Two ways, and the first is not a heuristic at all: MangaUpdates sometimes writes the
        Japanese in the name itself — `Touma (当麻)` — which states the correspondence outright and
        is worth preferring over any amount of inference.

        Failing that, one-to-one or nothing. Position is not a match: on a work with a writer and an
        artist, guessing would assign one person's reading to the other, which is §1's failure with
        two people misnamed rather than one.
        """
        for a in theirs:
            m = re.search(r"[（(]([^）)]+)[）)]", a["name"])
            if m:
                inner = m.group(1).strip()
                for ja in ours:
                    if norm(ja) == norm(inner):
                        return ja, a
        if len(ours) == 1 and len(theirs) == 1:
            return ours[0], theirs[0]
        return None

    @staticmethod
    def _split_caps(latin):
        parts = latin.split()
        caps = [p for p in parts if len(p) > 1 and p.isupper()]
        if len(caps) == 1 and len(parts) == 2:
            fam = caps[0]
            giv = parts[0] if parts[1] == fam else parts[1]
            return fam, giv
        return None, None


SOURCES = {"wikidata": Wikidata, "anilist": AniList, "mangaupdates": MangaUpdates}
# §3's order is AniList first; this runs Wikidata first because it is the only one returning kana.
# The plan's ranking was by names-per-request and Wikidata still wins on that too, being batched.
ORDER = ("wikidata", "anilist", "mangaupdates")


def build(source_name, store, by_title=None):
    cls = SOURCES[source_name]
    return cls(store, by_title) if source_name == "mangaupdates" else cls()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--out", default="data/names")
    ap.add_argument("--cache", default=str(paths.cache("names-cache")))
    ap.add_argument("--source", choices=list(SOURCES) + ["all"], default="all")
    ap.add_argument("--kind", choices=["authors", "titles", "both"], default="both")
    ap.add_argument("--limit", type=int, default=None, help="stop after N names per source/kind")
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between requests (§7)")
    ap.add_argument("--offline", action="store_true",
                    help="replay cached responses only, send nothing (§4: re-derivable offline)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    authors, titles, _, by_title = inputs.load(args.build)
    store = NameStore(args.out)
    cache = HttpCache(args.cache, pause=args.pause, offline=args.offline)
    sets = {"authors": sorted(authors), "titles": sorted(titles)}
    kinds = ["authors", "titles"] if args.kind == "both" else [args.kind]
    sources = list(ORDER) if args.source == "all" else [args.source]

    try:
        for sname in sources:
            resolver = build(sname, store, by_title)
            for kind in kinds:
                if kind not in resolver.kinds:
                    continue
                stats = drive(resolver, store, kind, sets[kind], cache,
                              limit=args.limit, verbose=args.verbose)
                print(f"{sname:14} {kind:8} {stats}")
                if getattr(resolver, "author_hits", 0):
                    print(f"{'':14} {'authors':8} {resolver.author_hits} recorded via title records")
    except KeyboardInterrupt:
        print("\ninterrupted — compacting what is already known", file=sys.stderr)
    finally:
        store.close()

    print(f"\nrequests made: {cache.requests}   served from cache: {cache.hits}"
          + (f"   not cached, skipped: {cache.declined}" if args.offline else ""))
    print("authors", store.status("authors", sets["authors"]))
    print("titles ", store.status("titles", sets["titles"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
