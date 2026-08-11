#!/usr/bin/env python3
"""Where a work was first published, and what says so. One producer of `first_publication.country`.

WHY THIS IS A FACT. DEFINITIONS §6 makes first publication the inclusion test: a work is in scope if
its first publication venue was in Japan, and author nationality is irrelevant. The field carrying
the answer was a literal in three places, `build.py` twice and `adapters/cmoa_volumes.py` once, so
2,564 works asserted `JP` and not one of them had been asked. A constant is not a producer of a
fact, it is the answer written down before the question, and it cannot fail the test it stands for.

WHY THE SOURCES CANNOT ANSWER IT BY THEMSELVES. Works enter here through MADB, openBD and two
Japanese shops, and every one of those catalogues the JAPANESE EDITION. A Japanese edition of a
comic first published in Zagreb and a Japanese edition of a comic first published in Tokyo are the
same shape of record, so reading the country off the edition we hold gives `JP` for both. That is
the §14b failure in its purest form: the value was derived from the one thing that cannot tell the
two cases apart, and the check on it asked whether the field was non-empty.

WHAT THIS DECIDES. Which term `country_basis` takes, and therefore whether a country is attested at
all. Where nothing attests one the country is None and the term says why, because `unknown` is a
state (STANDING-INSTRUCTIONS §5) and `JP` on no evidence is an assertion of the answer.

WHAT THIS DOES NOT DECIDE, and the distinction is the whole design. A publisher's line saying "we
bring foreign comics to Japan" is EVIDENCE about a work on it and not a proof: a house may put a
Japanese work on such a line, and 誠文堂新光社 could do so tomorrow without telling anybody. A
translator credit is evidence too, and it has a live counter-case in 現代語訳, a Japanese classic
rendered into modern Japanese, which is translated and was first published in Japan. So neither
signal retracts a work. Each produces `review`, meaning somebody should read the publisher's page
for THIS work, and a ruling recorded in `data/scope.yaml` with that page cited is what refuses it.

WHAT ELSE THIS DOES NOT OWN. Which line an imprint string names, which is `facts/imprint` and its
registry `data/names/imprints.yaml`; how a credit field becomes people and roles, which is
`facts/credit`; and why a row carries the DATE it carries, which is `facts/dating`. The country and
the date are different questions about one block and §6 says so outright: the test turns on WHERE.
"""
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from facts import credit as _credit                                          # noqa: E402
from facts import imprint as _imprint                                        # noqa: E402

#: The operator's rulings on scope, curated with a citation each. Read here rather than in build.py
#: so that the rulings and the signals that produce candidates for them answer as one thing.
RULINGS = "data/scope.yaml"

#: Roles a Japanese catalogue writes for the person who put the text into Japanese. A record
#: carrying one states that its text is a translation of something written elsewhere first.
#: 訳 alone is enough and is what MADB writes; 翻訳 is what a publisher's own page writes.
TRANSLATION_ROLES = ("訳", "翻訳", "翻訳者", "監訳", "共訳")

#: Every term `country_basis` can hold, what it means, and what it settles about scope.
#:
#: `scope` is one of:
#:   `in`            first publication in Japan is attested. DEFINITIONS §6 admits the work.
#:   `out`           first publication elsewhere is attested. §6 excludes it.
#:   `review`        something says the Japanese edition may be a translation. A person reads the
#:                   publisher's page for this work and records a ruling either way.
#:   `unestablished` nobody has asked. Not a synonym for `review`: there is no signal to follow up,
#:                   only the absence of one.
BASES = {
    "japanese-serialisation-attested": {
        "country": "JP",
        "scope": "in",
        "note":
        "A source names the Japanese magazine or platform the work first ran in, so the first "
        "publication venue was in Japan and DEFINITIONS §6 admits it. This is the only term that "
        "puts JP in the field, and it is the one no bulk catalogue can supply.",
    },
    "publisher-states-origin": {
        "country": None,          # the ruling states it; the term does not presume one
        "scope": "out",
        "note":
        "The Japanese publisher's own page for this work says where the work comes from, and it "
        "is not Japan. The Japanese edition is a translation, so DEFINITIONS §6 excludes the work "
        "whatever the author's nationality and whoever sells it here.",
    },
    "translator-credited": {
        "country": None,
        "scope": "review",
        "note":
        "The record credits somebody with putting the text into Japanese, so the Japanese text is "
        "a translation of a text that existed before it. Which country that text was published in "
        "is a separate question, and 現代語訳 of a Japanese classic is translated and Japanese, so "
        "this asks for the publisher's page rather than settling anything.",
    },
    "foreign-comics-line": {
        "country": None,
        "scope": "review",
        "note":
        "The book is on a line whose business is bringing comics published abroad to Japan. Where "
        "`data/names/imprints.yaml` carries the flag, the publisher's own page for the line is "
        "what put it there. It is evidence about a book on the line and not a proof about any "
        "particular book, because nothing stops a house putting a Japanese work on it.",
    },
    "japanese-edition-catalogued": {
        "country": None,
        "scope": "unestablished",
        "note":
        "Every source consulted catalogues the Japanese edition. That places the EDITION in Japan "
        "and says nothing about where the work first appeared, so the scope test has not run. The "
        "route that closes it is a serialisation venue, which the bulk catalogues do not carry.",
    },
}

#: WHY A WORK IS NOT MANGA, for the OTHER question DEFINITIONS §6 asks. The clause is written out
#: plainly, "light novels and prose ... it is not manga. It will not be given work records", and
#: only the country half was ever tested: eleven prose works reached readers with work records and
#: credit pages. A ruling on medium rests on one of these the way a ruling on country rests on a
#: term above.
#:
#: KEPT SEPARATE FROM `BASES` BECAUSE THEY ANSWER DIFFERENT QUESTIONS. A term saying where a book
#: was published cannot say what kind of book it is, and a check that accepted either for either
#: would let a country term excuse a medium ruling.
MEDIUM_BASES = {
    "imprint-is-a-prose-line": {
        "medium": "prose",
        "note":
        "The line the work is published on is a prose line, so every work on it is prose. "
        "パルソラ's コミックノベル「yomuco」 is the case: one of its books says 初ノベライズ in its own "
        "listing, none of the eleven appears in the Media Arts Database or openBD, and six of them "
        "credit an author beside an 絵 illustrator, which is how an illustrated novel is billed.",
    },
    "listing-states-a-novelisation": {
        "medium": "prose",
        "note":
        "The shop's own copy for the book calls it a novelisation. That is the strongest medium "
        "evidence a retailer listing can carry, and it is stronger than the category the same shop "
        "files the book under: BOOK☆WALKER said 初ノベライズ and マンガ総合 on one page.",
    },
}


def medium_bases():
    """Every term a ruling on medium may rest on."""
    return tuple(MEDIUM_BASES)


def medium_note(basis):
    """The sentence explaining a medium term, or None where the term is not one."""
    return (MEDIUM_BASES.get(basis) or {}).get("note")


#: WHAT A RECORD WITH NO SIGNAL AT ALL TAKES. Named rather than left to a `.get` returning None,
#: because a missing term reads exactly like an answer (`facts/dating` was fixed for this).
FALLBACK = "japanese-edition-catalogued"


def bases():
    """Every term the field can hold."""
    return tuple(BASES)


def note(basis):
    """The sentence explaining a term, falling back to the one for a scope test nobody has run."""
    return BASES.get(basis, BASES[FALLBACK])["note"]


def scope(basis):
    """What the term settles about DEFINITIONS §6: `in`, `out`, `review` or `unestablished`."""
    return (BASES.get(basis) or BASES[FALLBACK])["scope"]


def attests(basis):
    """Whether the term names an answer to the scope test, rather than a lead or a silence."""
    return scope(basis) in ("in", "out")


def load(path=RULINGS):
    """The ruling file as a document. An absent file is no rulings, which is a legitimate state."""
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}


def members(r):
    """The works one ruling names, as `{work, title, records}` each.

    A RULING OVER A LINE RATHER THAN A BOOK. Every ruling here used to name one work, because the
    question was where one book was first published and each answer was its own reading of one
    publisher's page. The medium question is not like that: パルソラ's コミックノベル「yomuco」 is a
    prose line, and eleven works arrive on it. Eleven rulings would be one argument copied eleven
    times, and the twelfth work to appear on the line would silently not be covered by any of them.

    A ruling with no `works` is a ruling about itself, which is every ruling written before this and
    the shape a single-work answer should keep.
    """
    got = (r or {}).get("works")
    if not got:
        return [r] if r else []
    return [{"work": m.get("work"), "title": m.get("title"),
             "records": list(m.get("records") or [])} for m in got]


def index(doc):
    """`{key: ruling}` over every identifier a ruling names.

    KEYED ON MORE THAN ONE IDENTIFIER BECAUSE THE BUILD HAS MORE THAN ONE. The works list is keyed
    on the source record's id, `C418518` or `bw-…`, and the series list is keyed on the identity id
    `w01338`, which is minted later in the same run. A ruling that named only one of them would
    reach one list and quietly leave the work in the other, which is the six-surfaces failure of
    STANDING-INSTRUCTIONS §13.
    """
    out = {}
    for r in (doc or {}).get("rulings") or []:
        for m in members(r):
            for key in [m.get("work")] + list(m.get("records") or []):
                if key:
                    out[str(key)] = r
    return out


def ruling_for(keys, idx):
    """The ruling for whichever of `keys` one names, or None."""
    for k in keys or ():
        if k and str(k) in (idx or {}):
            return idx[str(k)]
    return None


def refusals(doc):
    """Works a ruling refuses, as rows shaped like the content-flag register's.

    SHAPED LIKE THE OTHER REGISTER ON PURPOSE. `build.withheld_works` already carries a work out of
    every surface it reaches, six of them, and each was found only by looking after the previous fix
    appeared to have worked. A second mechanism would have to rediscover all six.
    """
    rows = []
    for r in (doc or {}).get("rulings") or []:
        if r.get("disposition") != "out-of-scope":
            continue
        for m in members(r):
            rows.append({"title": m.get("title"), "work": m.get("work"),
                         "reason": r.get("why"),
                         "source": r.get("country_source") or r.get("medium_source")
                                   or "scope ruling",
                         "withhold": True})
    return rows


def refused_keys(doc):
    """Every identifier a refusing ruling names, so a list keyed on any of them can drop the work.

    Keys and not titles, because the works list is built from source records and MADB, openBD and
    a shop each transcribe one title differently.
    """
    return {k for k, r in index(doc).items() if r.get("disposition") == "out-of-scope"}


def roles_of(creator):
    """The roles a catalogued credit field states, through the module that owns credit fields.

    Asked of `facts/credit` rather than matched here. `[上田香子][訳] / [作・画]ステファン・セジク`
    holds a role in brackets before one name and after the other, and a second reader of that
    notation is the shape §3 counts seven shipped bugs from.
    """
    return [role for _name, _reading, role in _credit.split_detail(creator or "") if role]


def foreign_line(publisher, imprint, lines=None, idx=None):
    """The registry line for this record that publishes Japanese editions of comics from abroad.

    THE PUBLISHER STRING IS TRIED AS A LINE NAME, WHICH IS NOT A GUESS. MADB records a book whose
    奥付 splits 発行 from 発売 by putting the LINE in the publisher field and the distributing house
    beside it: サンストーン is `G-NOVELS / [発売]誠文堂新光社` with the imprint field empty. So a
    record stating no imprint may still be naming its line, and asking only the imprint field would
    miss exactly the books this is for.

    IT CANNOT REACH A LINE BY ACCIDENT, because the registry is curated and answers a spelling only
    under the house that runs it (`facts/imprint`). A company name in the imprint field is a shape
    `data/names/imprints.yaml` refuses outright, and a line reached by this fallback still has to
    carry `foreign_edition` before anything here happens.
    """
    lines = _imprint.load() if lines is None else lines
    idx = _imprint.index(lines) if idx is None else idx
    for raw in (imprint, publisher):
        if not raw:
            continue
        line = _imprint.resolve(publisher, raw, idx)
        if line and line.get("foreign_edition"):
            return line
    return None


def country_of(keys=(), publisher=None, imprint=None, creator=None, roles=None,
               rulings=None, lines=None, imprint_index=None):
    """`(country, basis)` for one record. The only place `first_publication.country` is decided.

    ORDER OF PRECEDENCE, strongest first. A ruling is a person having read the publisher's page for
    this work, so it beats every signal. A translator credit is a statement in the record itself. A
    line flag is a statement about every book on the line. Where none of them speaks, the answer is
    that nobody has asked, and the country stays empty.
    """
    ruled = ruling_for(keys, rulings if rulings is not None else index(load()))
    if ruled:
        basis = ruled.get("country_basis") or FALLBACK
        return ruled.get("country"), basis
    if any(r in TRANSLATION_ROLES for r in (roles if roles is not None else roles_of(creator))):
        return None, "translator-credited"
    if foreign_line(publisher, imprint, lines=lines, idx=imprint_index):
        return None, "foreign-comics-line"
    return None, FALLBACK
