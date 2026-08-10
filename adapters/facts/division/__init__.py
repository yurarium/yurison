#!/usr/bin/env python3
"""Where a name divides, and what standing a division has. One table, everything else derived.

WHY THIS IS ONE FACT. A division carries a BASIS saying where the space came from, and four
questions get asked of that basis: may it be believed as cited, may it be lent to another record,
must a reader be told, and may it exist at all. Those four answers lived in four places:

    curate.DIVIDING_BASES              which arrive already cited
    boundary.SETTLED_BASES             which may lend a division to another record
    boundary.MARKED_DONOR_BASES        which must carry a mark when lent
    check.UNCITED_DIVISIONS_COUNTED    which may exist uncited, counted rather than blocked

They agree today. They agree because `check.py` held hand-written copies of two of them, one had
already drifted, and a repair replaced the copies with a test asserting the four stay consistent.
The comment on that test says it plainly: where a second producer cannot consume the first, section
3 settles for an assertion that they agree.

THIS IS THE CONSUMPTION THAT MAKES THE ASSERTION UNNECESSARY. One table states each basis once, and
every question is a column of it. Two lists cannot drift when there is one list.

WHAT THIS MODULE DOES NOT DECIDE. Whether a particular name divides, and where. That is arithmetic
off a surface, a heading a library printed, or a ruling somebody made, and those live with the
sources that supply them. This owns what a division MEANS once it exists. See BLINDSPOT.md.
"""

#: Each basis, once. The columns are the questions anybody asks about a division.
#:
#: cited     the source that gave the reading gave the division with it, so it needs no separate
#:           citation. A catalogue printing `美鈴, ちょこ` states both at once.
#: donates   may lend its division to a DIFFERENT record of the same person.
#: marked    a reader is told, because the division is weaker than the sounds around it.
#: counted   may exist without citing a source, counted by a budget instead of blocked.
_TABLE = {
    # a source printed the reading with its division in it
    "stated":            {"cited": True,  "donates": True,  "marked": False, "counted": False},
    # a reviewer weighed the evidence and wrote down what they concluded
    "researched":        {"cited": True,  "donates": True,  "marked": False, "counted": False},
    # the writing fixes the offset: a kana run in the surface reads as itself, so it is arithmetic
    "surface":           {"cited": True,  "donates": True,  "marked": False, "counted": False},
    # a community database printed it. The owner's ruling of 2026-08-09: it raises the floor on a
    # romanisation WITHOUT overcoming the fallback basis, so it may be shown and lent, and it never
    # counts as anybody having stated where a person's name divides.
    "community-printed": {"cited": False, "donates": True,  "marked": True,  "counted": True},
    # a romanisation read backwards into kana. The spaces are a reconstruction of a reconstruction,
    # so they are never lent, and the few that exist are counted.
    "back-converted":    {"cited": False, "donates": False, "marked": True,  "counted": True},
    # a morphological analyser guessed. A guessed division is a false claim about a person's name,
    # which is worse than no division, so these are retired rather than counted.
    "analyser":          {"cited": False, "donates": False, "marked": True,  "counted": False},
}

#: WHICH BASIS WINS when two records of one person hold different readings. A column and not a
#: second table, because it is another question about a basis and `build.py` held it as a dict
#: keyed on the same vocabulary, which the duplicates lint found.
#:
#: `analyser` and `back-converted` are a machine's answer and sit below everything that came from
#: somewhere. `community-printed` is Wikidata, ruled noncanonical on 2026-08-09 and kept as a floor:
#: an editor typed the kana, so it beats a machine reading the characters, and nobody answers for
#: it, so it loses to a kana surface and to anything a source states. The owner's correction later
#: that day left this alone, because it decides which of two records holds the better STRING and a
#: better string is exactly what Wikidata may give.
_RANK = {"stated": 5, "researched": 4, "surface": 3, "community-printed": 2,
         "back-converted": 1, "analyser": 1}

BASES = tuple(_TABLE)


def rank(basis):
    """How much a reading on this basis is worth against another. Unknown ranks below everything."""
    return _RANK.get(basis, 0)


def ranks():
    """The whole table, for a caller that wants the mapping."""
    return dict(_RANK)


def _ask(basis, column):
    return bool(_TABLE.get(basis, {}).get(column))


def cites_its_source(basis):
    """Whether a division on this basis arrived with its source and needs no separate citation."""
    return _ask(basis, "cited")


def may_donate(basis):
    """Whether a division on this basis may be lent to another record of the same person."""
    return _ask(basis, "donates")


def is_marked(basis):
    """Whether a reader is told about a division on this basis."""
    return _ask(basis, "marked")


def counted_uncited(basis):
    """Whether a division on this basis may exist without a citation, counted by a budget.

    Distinct from `may_donate`: `back-converted` is counted and never lent, and `analyser` is
    neither, because a guess about somebody's name is retired instead of tolerated.
    """
    return _ask(basis, "counted")


def bases_where(column):
    """Every basis answering yes to one question, for a caller that wants the set.

    Provided so a caller that genuinely needs a set gets it from the table instead of writing one
    down beside it, which is the fault this module was extracted to end.
    """
    return frozenset(b for b in _TABLE if _ask(b, column))


_SUBMODULES = ("boundary", "analyser_division", "checks")


def _boundary():
    import importlib
    return importlib.import_module(".boundary", __name__)


def _checks():
    import importlib
    return importlib.import_module(".checks", __name__)


#: WHAT THIS FACT CAN BE CHECKED ON, keyed by the name check.py registers. Exposed here because a
#: check is part of a fact's public surface, and because `adapters/lint/facts.py` refuses a caller
#: reaching for the submodule directly.
CHECKS = {
    "cites_its_source": lambda ctx: _checks().cites_its_source(ctx),
    "names_its_donor_in_a_field": lambda ctx: _checks().names_its_donor_in_a_field(ctx),
    "divisions_read_back_from_a_romanisation":
        lambda ctx: _checks().divisions_read_back_from_a_romanisation(ctx),
    "divisions_resting_on_a_community_database":
        lambda ctx: _checks().divisions_resting_on_a_community_database(ctx),
    "divisions": lambda reading: _checks().divisions(reading),
    "kana_names_with_no_stated_division": lambda ctx, _n="kana_names_with_no_stated_division": getattr(_checks(), _n)(ctx),
    "author_names_romanised_as_one_word": lambda ctx, _n="author_names_romanised_as_one_word": getattr(_checks(), _n)(ctx),
}


# ── the producers, re-exported ────────────────────────────────────────────────────────────────
# THE SURFACE ITS CALLERS ACTUALLY USE, measured rather than guessed. `boundary.py` and
# `analyser_division.py` moved in here because deciding where a name divides is this fact; the
# source adapters that HAPPEN to yield divisions (`ndl_heading`, `openbd_reading`) stayed with
# their sources, because parsing a library catalogue is not this fact.
def __getattr__(name):
    """Anything the boundary module publishes, reached through the entry point.

    Written as a module `__getattr__` so the re-export list cannot drift from what the submodule
    offers, which is the same failure this whole module was extracted to end. A name neither this
    module nor `boundary` defines still raises AttributeError.
    """
    # A SUBMODULE NAME IS NOT FORWARDED. `from . import boundary` reaches this hook before the
    # submodule is bound on the package, so forwarding it called the import that called the hook.
    # Importing the submodule is the import machinery's job and never this function's.
    if name in _SUBMODULES or name.startswith("__"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    for mod in (_boundary(), _checks()):
        if hasattr(mod, name):
            return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _ad():
    import importlib
    return importlib.import_module(".analyser_division", __name__)


def retire(*a, **k):
    """`analyser_division.retire`: strip a division no source states."""
    return _ad().retire(*a, **k)


def asks(*a, **k):
    """`analyser_division.asks`: whether a record's division is the analyser's to remove."""
    return _ad().asks(*a, **k)


def retire_store(*a, **k):
    """`analyser_division.retire_store`: strip every uncited division from the store on disk.

    NAMED HERE BECAUSE `__getattr__` DOES NOT REACH IT. The hook forwards to `boundary` and to
    `checks`, so the two functions above had to be written out and this third one was missed.
    build.py calls it on every build, inside the try that prints one line and continues, so the
    AttributeError read as `automatic reading pass skipped` and took the author readings, the
    divisions and the publisher names down with it. STANDING-INSTRUCTIONS §4.
    """
    return _ad().retire_store(*a, **k)
