#!/usr/bin/env python3
"""Ask the interface what it would show, instead of asserting what it should.

WHAT THIS REPLACES. `check.py` held hand transcriptions of `kari/app.js`: a `fold`, a `render`
reimplementing the name lookup, a `joins` guessing at the order app.js falls back in, and copies of
`publisherOf` and `imprintOf`. STANDING-INSTRUCTIONS §3 says the same fact derived in two places
drifts with nothing forcing agreement, and each of those was a second derivation.

It drifted where it costs the most. `English mode has no Japanese` was extended to walk the volume
rows, went green, and a reader could still see
`シャドウ・アサシンズ・ワールド : 影は薄いけど、最強忍者やってます` on the 発売 tab. The
transcription tried the title with its subtitle stripped and with the separator turned into a
space; app.js tries neither. The check passed because its model of the renderer was kinder than the
renderer.

So this runs the renderer. `interface.js` evaluates `kari/app.js` as GitHub Pages serves it, in a
node vm with a stubbed browser around it, and calls the file's own functions. Nothing here spells a
rule that app.js already spells.

WHAT IT COSTS. One node process, which loads app.js in about 90 ms and renders the whole corpus of
2,558 work titles in about 30 ms. A gate run pays roughly 0.6 s in total, most of it parsing
`feed/names.json`, which node reads by path rather than being handed on stdin for that reason.
Nothing browser-shaped runs: no jsdom, no headless Chrome, no page.

WHAT IT CANNOT SEE, and this is the reason `adapters/lint/entrypoints.py` exists beside it. Running
the renderer proves that what reaches the renderer is rendered correctly. It says nothing about a
call site that never calls it, and every leak this project has had was one of those: the works list
wrote `esc(w.t)` from index.json and shipped 2,430 rows of Japanese, and the 発売 tab labelled a
volume from a catalogued record title. `entrypoints.py` is the static half, and it is the half that
can fail on a path no run exercises.

Offline: node is given a request on stdin and reads two files by path. Its own fetch entries are
removed before app.js is evaluated, because ./test.py installs its guard in Python and a node
grandchild is outside it.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
# `adapters/` ON THE PATH BEFORE THE FACT IS IMPORTED. Nothing here set it, so this module could
# only be imported from a shell that already had PYTHONPATH, which every shell in this project does.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from facts import script as _script                                     # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS = pathlib.Path(__file__).resolve().parent / "interface.js"
# WHERE THE RENDERER IS, IF THERE IS ONE HERE AT ALL. §11 moved the interface and everything that
# checks what a reader is shown into the repository that renders it, so this repository no longer
# assumes a sibling checkout: `YURARIUM_SITE` points at one where somebody wants these suites run
# against a real `app.js`, and without it they say they had nothing to run rather than passing.
SITE_ROOT = pathlib.Path(os.environ.get("YURARIUM_SITE") or ROOT.parent / "no-site-configured")
APP_JS = SITE_ROOT / "kari" / "app.js"


# ── which field goes through which function ───────────────────────────────────────────────────
#
# THE ONE TABLE, READ TWICE. `check.py` renders each field here through the function named beside
# it and asks what a reader would see. `adapters/lint/entrypoints.py` reads the same table and
# proves that kari/app.js never puts one of these fields on a page any other way. Neither half is
# worth much alone: rendering proves that what reaches the renderer is right, and the lint proves
# that everything reaches it.
#
# `arg` says how a caller builds the argument, because an entry point takes either a ROW or a
# STRING. `workLabel` reads `r.work` and `r.work_en` off a row, so a surface whose title lives
# somewhere else on the row hands the row over with `work` set to that field, which is what
# renderReleases does with `workLabel({ work: w.title.ja })`. That much is a model of the caller,
# and it is the part the lint checks rather than assumes.

# WRITTEN AS CODE POINTS, because the literal form of this class was wrong and nothing said so.
# The compatibility-ideograph range was typed with the character 豈, which has two code points:
# U+F900, the compatibility ideograph the range meant, and U+8C48, the ordinary character an editor
# inserts. The file held U+8C48, so the class ran from U+8C48 to U+FAFF and swallowed everything
# between, Hangul syllables among it. Six credit rows naming Korean artists counted as "still
# Japanese in English mode" on the strength of a name in a script this project makes no claim about.
#
# kari/app.js spells the same class \u3040-\u30ff\u3400-\u9fff\uf900-\ufaff and has always been
# right, which is STANDING-INSTRUCTIONS §3 once more: one fact, two spellings, and the copy nobody
# could read by eye is the one that drifted. `test_interface.py` pins both ends of each range and
# pins that Hangul falls outside.
# ASKED OF `facts/script`, which owns which writing system a string is in.
KANA_KANJI = _script._SCRIPT
# The same scripts plus the CJK punctuation and the full-width and half-width forms, for asking
# whether a FIELD carries anything Japanese at all. Wider on purpose: a field holding only an
# ideographic space is still a field somebody has to rule on.
JAPANESE_ANY = re.compile("[\u3000-\u303f\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff"
                          "\uff00-\uffef]")


class Surface:
    """One field of one built collection, and the interface function that renders it.

    `arg` is how the caller builds the argument, because the entry points take three shapes.
    `value` hands over the string. `row:<field>` hands over the row with `<field>` set to this
    value, which is what `workLabel({ work: w.title.ja })` does on the 発売 tab. `record` hands
    over the whole record, which is what the publisher parts take, and `fields` then says which of
    its fields this surface accounts for.

    `holds_at_zero` IS GONE, AND ITS REMOVAL IS THE RULING. It said whether Japanese here was a
    fault or a deficit: a work title blocked, an unromanised publishing line was counted and
    tolerated. The owner overruled that. An unclear romanisation with an explanatory tooltip is
    required wherever the alternative is Japanese under an English heading, so there is no surface
    left where Japanese is a finished state and nothing for the flag to distinguish.

    `reads` names what the JAVASCRIPT reads, where that is not the tail of the data path. The two
    agree for `works[].title.ja`, which app.js reads as `title.ja`, and they cannot agree for
    `credits[].works[].roles[]`: the browser holds the role list in a variable and reads `w.roles`.
    Left to the default, that surface contributes an accessor no file will ever contain, and the
    lint then guards a field nothing reads, which is the silence §4 is about.
    """

    def __init__(self, path, entry, arg, category, why, fields=(), reads=()):
        # `entry` may name more than one function where the interface legitimately has more than
        # one: the publisher parts exist as a plain-string form and an escaped form carrying each
        # name's mark, and both are entry points for the same three fields. The first is the one
        # this renders through; the lint accepts any of them.
        self.path, self.entry = path, (entry,) if isinstance(entry, str) else tuple(entry)
        self.arg = arg
        self.category, self.why = category, why
        self.fields = tuple(fields)
        self.reads = (reads,) if isinstance(reads, str) else tuple(reads)

    @property
    def renders_with(self):
        return self.entry[0]

    @property
    def accessor(self):
        """What the JavaScript reads: `works[].title.ja` is `title.ja` to app.js."""
        return self.path.split("[].", 1)[1] if "[]." in self.path else self.path

    @property
    def ruled_paths(self):
        """Every derived path this surface accounts for."""
        if not self.fields:
            return (self.path,)
        stem = self.path[:-2] if self.path.endswith("[]") else self.path
        return tuple(f"{stem}[].{f}" if self.path.endswith("[]") else f"{stem}.{f}"
                     for f in self.fields)

    @property
    def accessors(self):
        """What app.js reads for this surface, one accessor per field it accounts for."""
        if self.reads:
            return self.reads
        return tuple(p.split("[].", 1)[1] if "[]." in p else p for p in self.ruled_paths)


SURFACES = [
    Surface("index[].t", ("workLabel", "workTextOf"), "row:work", "title",
            "the catalogue tab's title, drawn from the compact index"),
    Surface("index[].c", "credit", "value", "person",
            "the catalogue tab's credit line, roles and people in one string"),
    Surface("works[].title.ja", ("workLabel", "workTextOf"), "row:work", "title",
            "the 発売 tab labels a volume row from the bibliographic record's title"),
    # WHAT A VOLUME ROW CALLS ITSELF, WHICH NOTHING ASKED THE RENDERER ABOUT. `volLabel` renders
    # this on the work page and on the 発売 tab, and it had no surface, so `English mode has no
    # Japanese` never ran over it. ガレット's `創刊号` reached an English page as itself, above
    # `vol. 2`, and the ruling in NOT_A_NAME below was carrying the field on the strength of 上 and
    # 下 being rendered, which they are and it was not. Asked of the RECORD, because the label is
    # made from the designation and the position the build placed it at together.
    Surface("works[].volumes[]", "volLabel", "record", "value",
            "the label on a volume row: its number, or what the record calls it instead",
            fields=("number", "designation")),
    Surface("works[].creator", "creditNames", "value", "person",
            "the 発売 tab's byline, the credit field split into the people in it"),
    # `publisherChip` IS THE ENTRY POINT FOR ONE HOUSE'S NAME, added when the houses got addresses
    # of their own. It renders through `pubBoth` and `pubMark` exactly as this row always did and
    # wraps the result in the record's link, so a caller handing it a publisher field has handed
    # the field to the renderer. `publisherPartsHtml` calls it, which is why the work page has no
    # copy of these three names any more.
    Surface("works[]", ("publisherParts", "publisherPartsHtml", "pubBoth", "publisherChip"),
            "record", "publisher",
            "who made the book, on a volume row: the house, the distributor and the line",
            fields=("publisher", "distributor", "imprint")),
    Surface("series[].work", ("workLabel", "workTextOf"), "row:work", "title",
            "the works tab's title, from the row that joined the platforms"),
    Surface("series[].author", "authorLabel", "row:author", "person",
            "the works tab's byline"),
    # THE SAME FIELD, THROUGH THE OTHER FUNCTION THAT RENDERS IT. The list rows call `authorLabel`
    # and the work page calls `creditLine`, which calls `linkedCredits`, which composes the field
    # out of the shipped division and wraps each person in their address. Measuring only the first
    # left the second unmeasured, and they answer differently: `linkedCredits` places the names
    # inside the field as written and `authorLabel` composes a new line from them.
    Surface("series[].author", "linkedCredits", "row:author", "person",
            "the same byline on a work page, where each person is a link to their record"),
    # THE FUNCTION THE WORK PAGE ACTUALLY CALLS, and the one this table was missing. The 作者 fact
    # calls `creditLine`, which shortens a long byline and calls `linkedCredits` for the rest, so
    # every check here was measuring the callee and not the caller. `creditLine` cut the field on
    # the slash and passed the pieces on as a field of their own, which threw the shipped division
    # away; the byline `安田剛助・文尾文` reached a reader as `???? · Bun?Bun` while `linkedCredits`
    # rendered the same field correctly, and a probe over this table reported zero
    # (STANDING-INSTRUCTIONS §14b).
    Surface("series[].author", "creditLine", "row:author", "person",
            "the byline as the work page draws it, shortened where it names more people than a "
            "line holds"),
    Surface("series[].latest_ep", "phraseOf", "value", "phrase",
            "the newest chapter's name, shown beside the row"),
    Surface("series[].collection", ("workTextOf", "workLabel"), "value", "title",
            "the collection a work belongs to, named on its own page"),
    Surface("series[].print[]",
            ("publisherParts", "publisherPartsHtml", "pubBoth", "publisherChip"), "record",
            "publisher",
            "the same three names on a work page's volume list, and on a credit's page, where the "
            "houses behind that person's works are listed",
            fields=("publisher", "distributor", "imprint")),
    Surface("releases[].work", ("workLabel", "workTextOf"), "row:work", "title",
            "the updates tab's title"),
    Surface("releases[].author", "authorLabel", "row:author", "person",
            "the updates tab's byline"),
    # THE SAME FIELD, THROUGH THE RENDERER THE DETAILED VIEW USES, and the reason it uses a second
    # one is §14b in the layout rather than in a check. The detailed row was a single anchor to the
    # chapter, so nothing inside it could be a link, so the byline had to be drawn by the one
    # renderer that returns no anchors. The row is not an anchor any more (owner's ruling,
    # 2026-08-10) and the byline goes through `creditLine` like the work page's, which places each
    # name inside the field as written instead of composing a new line from the parts. The two
    # answer differently on 24 of the fields in the current window, so measuring only the first
    # would leave what a reader now reads unmeasured, which is what `creditLine` missing from this
    # table already cost once.
    Surface("releases[].author", "creditLine", "row:author", "person",
            "the same byline on the detailed updates row, where each person is a link"),
    Surface("releases[].ep", ("phraseOf", "epText", "epLine"), "value", "phrase",
            "the chapter name on an update row"),
    Surface("releases[].collection", ("workTextOf", "workLabel"), "value", "title",
            "the collection an instalment belongs to, which is a work and gets a work's rendering"),

    # ── the two record pages, 2,241 credits and 164 houses ────────────────────────────────────
    #
    # WALKED BECAUSE THEY ARE PAGES A READER OPENS. `credits.json` and `publishers.json` are
    # fetched only when one of those addresses is visited, which is why they are separate files and
    # is also why nothing here read them: the surfaces above are the four collections the tabs
    # load. A page nobody walks is a page nobody measures, and adding these found a credit's
    # homophone list writing `esc(o.credit)` straight into the markup.
    Surface("credits[].credit", ("authorLabel", "creditChip"), "row:author", "person",
            "the name a credit page is headed with, and the same name in a work list"),
    Surface("credits[].homophones[].credit", ("authorLabel", "creditChip"), "row:author", "person",
            "a credit held apart from this one because they share a reading; the pair is "
            "information hung beside a record and never a merge"),
    # THE JOB ON THE EDGE FROM A WORK TO A PERSON. `roleWord` glosses it, and unlike a name a role
    # is a closed vocabulary somebody wrote down, so this holds at zero: a role with no gloss is a
    # missing table entry rather than a name nobody has researched.
    Surface("credits[].works[].roles[]", ("roleWord", "roleWords"), "value", "role",
            "the job a credit did on one work, shown under the work's title on a credit page",
            reads="roles"),
    Surface("publishers[].name", ("pubBoth", "publisherChip", "pubEn"), "value", "publisher",
            "the house a publisher page is headed with"),
    # `imprintOf` IS AN ENTRY POINT AND NOT AN EXCEPTION. It maps a catalogued spelling onto the
    # line's own name and hands that to `pubBoth`; the read of `name` inside it is the registry
    # answering, which is the same act as `pubEn` reading a record. Listing it here says so, rather
    # than parking it in the exception table where a reader would have to take a sentence's word
    # for it.
    Surface("publishers[].lines[].name", ("pubBoth", "publisherChip", "imprintOf"), "value",
            "publisher", "a yuri line on the house that runs it, which is the one thing a "
            "publisher page shows that no other page can", reads="name"),
    Surface("publishers[].lines[].parent", ("pubBoth", "publisherChip", "imprintOf"), "value",
            "publisher", "the umbrella a sub-line sits under, named beside it because both are "
            "real", reads="parent"),
]

# Fields whose values hold Japanese and are NOT a name. Each is ruled here so that a field arriving
# with no ruling fails `every Japanese field has a ruling` rather than passing unnoticed, which is
# what a hand-written list of name fields does after six months.
#
# A `ja` field beside an `en` one is the commonest shape here: the row carries both languages and
# the interface picks one, so the Japanese side is Japanese on purpose.
#: What makes a function a name renderer, and the reason this is derived. `SURFACES` above is a
#: hand-written table, and `creditLine` was missing from it: the work page called it, it cut the
#: byline on a slash and handed the pieces on as a field the build had never seen, and
#: `安田剛助・文尾文` reached a reader as `???? · Bun?Bun` while every probe over the table reported
#: zero. A table of what reaches a reader cannot be the thing that decides what reaches a reader.
FLOOR_PRIMITIVES = ("floorText", "enFallback", "phraseOf", "workLabel", "workTextOf")

#: A function the derivation finds and that is NOT a surface, each with the reason. An orchestrator
#: paints a region and calls renderers to fill it; it has no data path of its own, so there is
#: nothing for a surface row to be about. Anything here that starts RETURNING name text is a
#: surface, and moving it is the fix rather than editing this line.
NOT_A_SURFACE = {
    "renderCat": "paints the catalogue tab and calls the renderers for each field",
    "renderSeries": "paints the works tab the same way",
    "renderFeed": "paints the 発売 tab the same way",
    "renderWorkPage": "paints a work page and calls a renderer per field it shows",
    "renderPublisherPage": "paints a publisher page the same way",
    "compactList": "lays out a list of rows, each rendered by the surface for its field",
    "detailList": "the same for the expanded rows",
    "recWorkRows": "the rows of works on a record page, each field through its own renderer",
    "creditText": "the plain-text form of a credit line, used for searching and sorting rather "
                  "than shown; it goes through the same renderers and adds no name of its own",
    "creditGapText": "says how many people a shortened byline did not list, which is a count",
    "personShown": "decides WHETHER a person is listed, and renders nothing itself",
    "sourceBoth": "a source's name in both languages, which is a citation and not a name in the "
                  "corpus: the string is the site or shop as it calls itself",
    "stateLabel": "the words active, finished or paused, which are the interface's own English",
    "bylineRole": "the same role `roleWord` glosses, in the form a byline states it; it decides "
                  "which atoms of a compound survive the owner's elision of the default author "
                  "role and asks `roleWord` for every word it keeps",
    "andOthers": "the words a field uses to say the people it names are some of them, read off the "
                 "one role table so the byline and the credit page cannot disagree about them",
    "creditJoiner": "what the field put between two people, shipped beside the division; it "
                    "chooses punctuation and renders no name",
    "composedCredit": "a byline composed from the shipped division, every name through "
                      "`personShown` and every role through `bylineRole`",
}


def renderers(js=None):
    """Every function that returns text a naming primitive touched, derived from the source.

    THE SEEDS ARE THE PRIMITIVES AND WHATEVER `SURFACES` ALREADY NAMES, so the derived set is a
    superset of the table by construction and the interesting answer is what it holds that the table
    does not. A function counts when it calls a primitive anywhere, or when it RETURNS a call to
    something that does: an orchestrator calls a renderer and writes the result to the page, and a
    renderer hands its caller a string.

    §14b, WHAT IT CANNOT SEE: a renderer reached through a variable, a method on an object, or an
    arrow function assigned to a name. The site writes plain `function` declarations throughout, and
    a renderer written another way would be invisible here and is why `NOT_A_SURFACE` states its
    reasons rather than being a list of names.
    """
    import re
    src = js if js is not None else APP_JS.read_text(encoding="utf-8")
    named = set()
    for s in SURFACES:
        e = s.entry
        named |= set(e) if isinstance(e, (tuple, list)) else {e}
    seeds = set(FLOOR_PRIMITIVES) | named

    found = [(m.start(), m.group(1)) for m in re.finditer(r"^function ([A-Za-z_$][\w$]*)", src, re.M)]
    spans = {}
    for (a, name), (b, _n) in zip(found, found[1:] + [(len(src), None)]):
        spans[name] = src[a:b]

    def returned(body):
        return " ".join(body[m.end():m.end() + 500].split(";")[0]
                        for m in re.finditer(r"\breturn\b", body))

    got = {n for n in spans if n in seeds}
    for n, b in spans.items():
        if any(re.search(rf"\b{p}\s*\(", b) for p in FLOOR_PRIMITIVES):
            got.add(n)
    changed = True
    while changed:
        changed = False
        for n, b in spans.items():
            if n in got:
                continue
            if any(re.search(rf"\b{re.escape(t)}\s*\(", returned(b)) for t in got):
                got.add(n)
                changed = True
    return got - set(FLOOR_PRIMITIVES)


def unruled_renderers(js=None):
    """`[(name, )]` for every derived renderer neither in `SURFACES` nor argued in `NOT_A_SURFACE`."""
    named = set()
    for s in SURFACES:
        e = s.entry
        named |= set(e) if isinstance(e, (tuple, list)) else {e}
    return sorted(renderers(js) - named - set(NOT_A_SURFACE))


#: A field the interface DRAWS verbatim, and why that is right. Kept apart from `NOT_DRAWN` below
#: because the two are different rulings and only one of them can be checked by looking at the
#: source: "nothing puts this on a page" is a statement about `kari/app.js`, and
#: `adapters/lint/entrypoints.py` now holds it. "This is drawn as the source wrote it" is a
#: judgement about the value, and nothing but a person can make it.
#:
#: THE SPLIT EXISTS BECAUSE ONE LIST CARRIED BOTH AND NOTHING TOLD THEM APART. On 2026-08-12 a
#: volume's `designation` was ruled here on the reasoning that nothing drew it, and the same change
#: drew it, with `esc`, on 383 works in English mode. Neither guard could see it: both read
#: `SURFACES`, and this list was never compared against the source at all. Every entry below was
#: asserted and none was verified.
QUOTED = {
    "index[].y": "the yomi, a reading aid, drawn only where `LANG !== 'en'`",
    "works[].first_publication.venue": "the magazine a work first ran in, drawn as the record "
                                       "writes it because it is a quotation",
    "works[].first_publication.note": "where the date came from, quoted from the record",
    "works[].marketing_label_basis.note": "the publisher's own words, quoted as evidence",
    "series[].evidence[].source": "the source that holds the evidence, named",
    "series[].state_claims[].source": "the source making the claim, named",
    "series[].sourced_from[].source": "the source a field came from, named",
    "series[].completed_basis": "why a run is called finished, composed in English",
    "series[].stated_next.cadence": "the cadence a platform states, quoted in a tooltip",
    "releases[].id": "a chapter identifier a platform assigned, drawn as an identifier",
    "releases[].channel_name": "a channel's own name, drawn in a tooltip",
    "releases[].origin_note": "where an imported date came from, drawn in a tooltip",
    "releases[].ahead_next_ep": "the next chapter held ahead of the free window, in a tooltip",
    "credits[].homophones[].reading": "a reading, which is the fact the row is about",
}

#: A field NOTHING DRAWS. Enforced: `entrypoints.undrawn_findings` reports any read of one of these
#: whose value is escaped into markup or interpolated into a template, which are the two ways a
#: string becomes part of a page. An entry here is now a claim the source is asked about rather than
#: a claim about what its author believed.
NOT_DRAWN = {
    # A GATE FINDING IS DIAGNOSTIC OUTPUT, NOT A NAME. check.py reports an example beside a failing
    # invariant so a person can act on it, and an example naming a Japanese work carries that title
    # verbatim. It is never rendered to a reader as a name and must not be romanised: the point of
    # quoting it is that it matches what the data holds.
    "status[].gate.invariants[].examples[]":
        "a gate finding, quoted so a person can act on it. It names the work that failed and must "
        "stay verbatim, because the point of quoting it is that it matches what the data holds.",
    # THE SPELLINGS A CREDIT ANSWERS FOR, which is a lookup key and not a rendering. `credit` is
    # what heads the page and goes through `authorLabel`; this list is every other string the same
    # person is written as, folded the way `feed/names.json` is keyed, so a search can resolve a
    # raw field to the credit that owns it. Romanising it would defeat what it is for: the whole
    # value of `アオトヒビキ` sitting here is that it matches the characters a source wrote.
    "credits[].spellings[]":
        "every spelling one credit answers for, folded as a lookup key. Search resolves a raw "
        "credit field through it; nothing renders it, and matching the source's characters is the "
        "whole of its use.",
    "series[].completed_basis_ja": "the same sentence in Japanese, shown in Japanese mode",
    "series[].state_basis": "why a row is called active, in English",
    "series[].state_basis_ja": "the same sentence in Japanese, shown in Japanese mode",
    "series[].evidence[].term": "the term a source used, quoted rather than translated",
    "series[].state_claims[].term": "the term a source used",
    "series[].sources[].platform": "a platform's own name; platName renders it",
    "series[].stated_next.platform": "a platform's own name",
    "series[].skipped[][]": "chapter identifiers a capture could not read; nothing renders them",
    # THE JOB EACH CREDIT DID, AND THE NAME IT BELONGS TO, carried on the row so the credit
    # registry can hang a role on the edge from a work to a person. The interface never reads
    # either: it renders the credit field itself through `authorLabel`, and a credit page reads its
    # works and their roles out of `credits.json`, which the registry produces from this. A field
    # the build writes for a pass rather than for a page is a legitimate state, and saying so here
    # is what stops it being a silence.
    "series[].credits[].name": "the same person the credit field names, split out for the "
                               "registry; the field itself is what a page draws",
    "series[].credits[].role": "the job that credit did, for the edge from the work to the "
                               "person; a page reads it back from credits.json",
    # WHAT A PRINT BLOCK STANDS FOR, BESIDE WHAT IT SHOWS. A block is one print RUN and build.py
    # folds the catalogue records MADB filed that run under separately, so a run can be published
    # under a line the block does not show. These are the names of those folded records, carried so
    # that the passes counting publisher and imprint strings go on seeing every one of them; the
    # page draws its publisher from the block above, and the volume rows draw theirs from their own
    # works.json records, which `works[]` rules. Nothing renders this.
    "series[].print[].folded_names[].publisher": "the house a folded catalogue record names, for "
                                                 "the census; the block itself is what a page draws",
    "series[].print[].folded_names[].distributor": "the distributor a folded record names, for the "
                                                   "census",
    "series[].print[].folded_names[].imprint": "the line a folded record names, for the census and "
                                               "for the years that spelling covers",
    "works[].title.yomi": "the reading, a Japanese-side aid",
    "works[].admitted_by[].shelf": "the shop shelf that admitted the work, quoted",

    "releases[].plat_name": "a platform's own name",
    "releases[].preferred": "a platform's own name",
    "releases[].also_on[]": "a platform's own name",
    "releases[].channel.name": "a channel's own name",
    "releases[].channel.host": "a channel's host, its own name",
    "releases[].channel.origin": "where a channel came from",
    "releases[].access_basis": "why a chapter is free or paid, quoted from the platform",
    "releases[].ahead_ep": "a chapter name held ahead of the free window",
    "releases[].same_title_elsewhere": "a title held by a different work, named for the reader",
    "releases[].kind_basis": "why a row was called a chapter, quoted from what it was read off",

    # ── the record pages ──────────────────────────────────────────────────────────────────────
    "credits[].homophones[].basis": "how that reading was arrived at, kept for the ruling file "
                                    "and not drawn",
    # A SPELLING IS A HISTORICAL VARIANT AND IS QUOTED ON PURPOSE. `Yuri-hime comics` is what a
    # 2008 volume says, and the line's own name heads the row above it. The page shows the count
    # and puts the spellings in a tooltip, which is prose in its own right rather than the label.
    "publishers[].lines[].spellings[].raw": "a catalogued spelling of one line, quoted as the "
                                            "volume that carried it prints it",

    # ── status.html, which is the page for facts about us ─────────────────────────────────────
    #
    # §1 puts coverage, confidence and backlog here rather than in front of a reader, so a
    # Japanese title in this file is the SUBJECT of a sentence about our own work and not a label
    # the page failed to render. That is the one place on this site where the rule points the
    # other way, and it is worth saying so beside the fields rather than in a document.
    "status[].outstanding[].rows[]": "the works a queue still holds, listed by the name they are "
                                     "filed under; the English-name queue is a list of titles "
                                     "with no English name, so naming them in English is not "
                                     "available and would defeat the point of the list",
    "status[].gate.budgets[].means": "what one budget counts, in a sentence that quotes the "
                                     "source or the shop it is about",
}

#: Both rulings, for the readers that only need to know a path is accounted for.
NOT_A_NAME = {**NOT_DRAWN, **QUOTED}


RENDERING_RECORDS = ("work_en.", "author_en.", "title.en")


class Unavailable(Exception):
    """node is not installed, or kari/app.js is not beside this repository.

    Raised rather than returning nothing, per §4: a renderer that answered "no Japanese anywhere"
    because it never ran is indistinguishable from a clean page. Callers decide whether that is
    fatal; `check.py` reports it as a violation, because a check that cannot run has not passed.
    """


def available():
    return bool(shutil.which("node")) and APP_JS.exists() and HARNESS.exists()


def render(calls, names=None, names_path=None, prefs=None, app_js=None, timeout=120):
    """Run `calls` through kari/app.js and return `[{"html": …, "text": …}]`.

    `calls` is a list of `(function name, argument)`, both of them app.js's own: `("workLabel",
    {"work": "雨夜の月"})` is the interface being asked what it would put on a row. The argument is
    whatever the function takes, which for the label functions is a row.

    `names` is `feed/names.json` as a dict, or `names_path` is where to read it from. The path form
    exists because that file is 3.8 MB and serialising it into node's stdin costs more than
    rendering does. Passing the dict is what lets `check.py` plant a canary in it (§14b).

    `prefs` sets app.js's own preference variables by name, so `{"LANG": "en"}` is English-only
    mode as a reader selects it. A name app.js does not hold raises rather than being ignored,
    because a preference that silently did nothing would make every check below vacuous.
    """
    app = pathlib.Path(app_js or APP_JS)
    if not shutil.which("node"):
        raise Unavailable("node is not on PATH, so kari/app.js cannot be run")
    if not app.exists():
        raise Unavailable(f"{app} does not exist, so there is no interface to ask")
    req = {"names": names, "names_path": str(names_path) if names_path else None,
           "prefs": prefs or {}, "calls": [list(c) for c in calls]}
    out = subprocess.run([shutil.which("node"), str(HARNESS), str(app)],
                         input=json.dumps(req, ensure_ascii=False), capture_output=True,
                         text=True, timeout=timeout)
    if out.returncode != 0 and not out.stdout.strip():
        raise Unavailable(f"node exited {out.returncode}: {(out.stderr or '').strip()[:400]}")
    try:
        reply = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise Unavailable(f"the harness wrote no reply: {(out.stdout + out.stderr)[:400]}")
    if not reply.get("ok"):
        raise Unavailable(reply.get("error") or "the harness refused")
    return reply["results"]


class Interface:
    """One loaded copy of the interface, holding the name map the browser would have fetched.

    Batched deliberately. Every call spawns node, so asking row by row would spawn once per row;
    the callers below hand over every row of a surface at once and read the answers back in order.
    """

    def __init__(self, names=None, names_path=None, prefs=None, app_js=None):
        self.names, self.names_path = names, names_path
        self.prefs = dict(prefs or {})
        self.app_js = app_js

    def with_prefs(self, **prefs):
        p = dict(self.prefs)
        p.update(prefs)
        return Interface(self.names, self.names_path, p, self.app_js)

    def labels(self, calls):
        """The rendered text of each call, tags and entities removed.

        What a reader reads. A label is HTML, so a check asking whether Japanese survived has to
        look inside the markup and not at it.
        """
        return [r["text"] for r in self.rendered(calls)]

    def values(self, calls):
        """What each call returned, untouched.

        For a function that answers with a string rather than with markup. `foldKey` is the case
        that made this necessary: it folds `4話②＜完＞` to `4話2<完>`, and the tag stripper above
        read `<完>` as an element and threw it away, so a comparison against the Python fold
        reported a disagreement that only the harness had.
        """
        return [r["html"] for r in self.rendered(calls)]

    def rendered(self, calls):
        return render(calls, names=self.names, names_path=self.names_path,
                      prefs=self.prefs, app_js=self.app_js)


# ── what the data carries, derived rather than listed ─────────────────────────────────────────

def derive_fields(collections, depth=7):
    """Every path in the built data holding Japanese, as `{path: values seen}`.

    DERIVED, BECAUSE A LIST GOES STALE WITHOUT SAYING SO. The set of fields carrying a name is not
    a thing to write down once: a pass adds a field, nothing renders it through the store, and a
    reader meets Japanese under an English heading. So the fields are read off the data on every
    run and each one has to be ruled, either by `SURFACES` or by `NOT_A_NAME`.

    EVERY ROW, NOT A SAMPLE. The first version read 800 rows per collection on the argument that
    this is a census of shapes rather than of values, and check.py's own canary went straight
    through it: a probe appends its row to the end of 3,200, and a field nobody has ruled on is
    exactly the kind that appears on one row. Reading the lot costs a quarter of a second.
    """
    out = {}

    def walk(node, path, d=0):
        if d > depth:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k, d + 1)
        elif isinstance(node, list):
            for v in node:
                walk(v, f"{path}[]", d + 1)
        elif isinstance(node, str) and JAPANESE_ANY.search(node):
            out[path] = out.get(path, 0) + 1

    for name, rows in collections.items():
        walk(list(rows or []), name)
    return out


def unruled(collections):
    """Paths the data carries in Japanese that nothing here has ruled on.

    A path is ruled by being rendered through a named function (`SURFACES`), by being declared a
    Japanese string rather than a name (`NOT_A_NAME`), or by belonging to a rendering record.
    Anything else is a field somebody added and nobody decided about, which is the state this
    whole arrangement exists to make impossible.
    """
    ruled = {p for s in SURFACES for p in s.ruled_paths} | set(NOT_A_NAME)
    bad = []
    for path in sorted(derive_fields(collections)):
        if path in ruled or any(part in path for part in RENDERING_RECORDS):
            continue
        bad.append(path)
    return bad


def calls_for(collections):
    """`([(fn, arg), …], [(surface, value), …])` for every value of every ruled surface.

    Returned as two lists in step rather than one list of pairs, because the first goes to node as
    the request and the second stays here to say what each answer was about.
    """
    calls, about = [], []
    for s in SURFACES:
        if s.arg == "record":
            # One call per record, and the values it accounts for travel beside it: the parts are
            # rendered together, so asking three times would render the same row three times and
            # still not say which field a Japanese name came out of.
            for row, _ in _values_at(collections, s.path):
                held = [row.get(f) for f in s.fields if isinstance(row.get(f), str)]
                if not any(v.strip() for v in held):
                    continue
                calls.append((s.renders_with, row))
                about.append((s, " ".join(held)))
            continue
        for row, value in _values_at(collections, s.path):
            if not isinstance(value, str) or not value.strip():
                continue
            if s.arg.startswith("row:"):
                field = s.arg.split(":", 1)[1]
                arg = dict(row) if isinstance(row, dict) else {}
                arg[field] = value
            else:
                arg = value
            calls.append((s.renders_with, arg))
            about.append((s, value))
    return calls, about


def _values_at(collections, path):
    """`(row, value)` for each value at a dotted path, the row being the record it sits on.

    The row travels with the value because the row-taking entry points read a second field off it:
    `workLabel` wants `work_en` beside `work`, and handing it the string alone would ask the
    interface a question no caller asks.
    """
    # A TRAILING `[]` MEANS "EACH ITEM OF THAT LIST", AND IT USED TO MEAN "THE LIST".
    # `series[].print[]` was read as `series[].print`, so the walk handed `calls_for` the SERIES row
    # with the whole print list beside it. The record branch then asked that row for `publisher`,
    # `distributor` and `imprint`, which a series row does not carry, so every one of 2,520 volume
    # blocks was skipped and the surface rendered nothing at all while reporting clean. That is the
    # §4 silence exactly: a check that walks no rows is indistinguishable from a check that walks
    # rows and finds nothing.
    #
    # `works[]` is different only in that the list is the collection itself, which is why the
    # marker comes off the HEAD and not off the tail.
    head, _, rest = path.partition("[].")
    if not rest and head.endswith("[]"):
        head = head[:-2]
    rows = collections.get(head) or []
    out = []
    for row in rows:
        for value in _dig(row, rest, row):
            out.append(value)
    return out


def _dig(node, path, row):
    if not path:
        return [(row, node)]
    key, _, rest = path.partition(".")
    if key.endswith("[]"):
        key = key[:-2]
        got = (node or {}).get(key) if isinstance(node, dict) else None
        return [v for item in (got or []) for v in _dig(item, rest, item)]
    if not isinstance(node, dict) or key not in node:
        return []
    return _dig(node[key], rest, row)


def _self_check():
    """Prove the harness loads the real file and answers from it, not from anything here."""
    if not available():
        print("SKIP: node or kari/app.js is not available")
        return 0
    got = render([["workLabel", {"work": "雨夜の月"}], ["foldKey", "ＡＢ　Ｃ"]],
                 names={"titles": {}, "authors": {}, "phrases": {}}, prefs={"LANG": "en"})
    print(json.dumps(got, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(_self_check())
