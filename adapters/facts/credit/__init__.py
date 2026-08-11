#!/usr/bin/env python3
"""How a credit field becomes people, and how many. One entry point, and the ruling is not optional.

WHY THIS IS ONE FACT. A credit field is a string a platform wrote, and turning it into people takes
a decision at every separator. A slash is unambiguous. A ・ is not: it separates names in a list
AND parts inside one person's name, so `矢立肇・富野由悠季` is two people and `くろば・Ｕ` is one.
The corpus can settle most of them, and `interpunct.settled` does.

THE FAULT THIS ENDS. The ruling existed and was OPT IN. `split_authors` and `split_credits_detail`
take a `ruled` argument, and of 31 calls across the project, 5 passed it. So a string the corpus had
settled as one person was split in the other 26 places, and `くろば・Ｕ` was in the store cut in half
with an identifier on each half. `build._recompose_credit` was one of the 26 and produced
`Sarii, B` while the store held `Sarii B`, which the invariant `a person is spelled one way` caught
only on a merge result.

SO THE DEFAULT IS INVERTED. The build calls `use_rulings` once, and every split after that uses it.
A caller that genuinely wants the unruled split asks for it by name, which is the direction round
that makes forgetting visible rather than silent.

WHAT THIS DOES NOT OWN. Whether a name is a person at all, which is `entities`; how that person's
name is read, which is `reading`; and how it is spelled in Latin, which is `romanisation`.
"""
import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))

_SUBMODULES = ("interpunct", "splitter", "checks", "nobody")

#: The corpus's answers about a ・, held here so every splitter sees the same ones. `None` means
#: nobody has computed them yet, which is different from "computed and empty".
_RULED = None


def use_rulings(ruled):
    """Install the corpus's interpunct answers for the rest of this run.

    Called once by the build, after `interpunct.settled` has read the credit fields. Everything that
    splits a credit afterwards gets them without asking, which is the point.
    """
    global _RULED
    _RULED = dict(ruled or {})
    return _RULED


def rulings():
    """What is installed, or `{}`. Never None, so a caller cannot tell "unset" from "empty"."""
    return dict(_RULED or {})


def _sp():
    return importlib.import_module(".splitter", __name__)


def split(credit, ruled=None, interpunct=True):
    """A credit field to `[(name, stated_reading)]`, using the installed ruling by default."""
    return _sp().split_authors(credit, interpunct=interpunct,
                                   ruled=_RULED if ruled is None else ruled)


def split_detail(credit, ruled=None, interpunct=True):
    """As `split`, and with the role the field wrote beside each name."""
    return _sp().split_credits_detail(credit, interpunct=interpunct,
                                          ruled=_RULED if ruled is None else ruled)


def split_unruled(credit):
    """Split on a ・ with the ruling deliberately ignored.

    EXISTS SO IGNORING IT IS AN ACT. Anything asking for this should be able to say why.
    """
    return _sp().split_authors(credit, interpunct=True, ruled={})


def split_whole(credit):
    """Split on every separator EXCEPT a ・, so a name containing one comes back whole.

    A DIFFERENT THING FROM `split_unruled`, and I conflated them once. `interpunct.settled` works
    out what the corpus can settle by asking which pieces are credited on their own elsewhere, and
    the evidence for that has to come from fields where no ・ was split, or it agrees with the split
    that produced it. That is the reasoning `interpunct` already records, and this is the call it
    needs.
    """
    return _sp().split_authors(credit, interpunct=False)


def __getattr__(name):
    """Anything `interpunct` publishes, reached through the entry point."""
    if name in _SUBMODULES or name.startswith("__"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    # `nobody` LAST, because it answers a question the other two do not ask: whether a creator
    # field names anybody at all, before the splitter is asked how many.
    for mod in (importlib.import_module(".interpunct", __name__), _sp(),
                importlib.import_module(".nobody", __name__)):
        if hasattr(mod, name):
            return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")



def _checks():
    return importlib.import_module(".checks", __name__)


#: WHAT THIS FACT CAN BE CHECKED ON, keyed by the name check.py registers.
CHECKS = {
    "interpunct_credits_nobody_has_ruled_on": lambda ctx, _n="interpunct_credits_nobody_has_ruled_on": getattr(_checks(), _n)(ctx),
    "credit_fields_the_division_does_not_account_for": lambda ctx, _n="credit_fields_the_division_does_not_account_for": getattr(_checks(), _n)(ctx),
    "credits_carrying_their_own_cataloguing": lambda ctx, _n="credits_carrying_their_own_cataloguing": getattr(_checks(), _n)(ctx),
    "credits_matching_a_chapter": lambda ctx, _n="credits_matching_a_chapter": getattr(_checks(), _n)(ctx),
    "credits_that_restate_a_name": lambda ctx, _n="credits_that_restate_a_name": getattr(_checks(), _n)(ctx),
}
