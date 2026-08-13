#!/usr/bin/env python3
"""What a serialisation can be doing, what a platform can say about it, and what a release is.

WHY THIS IS ONE FACT. Three closed vocabularies describe the same thing at three removes: the state
a work is in, the word we take from a platform that spoke about it, and the kind of event a release
row records. Each was written as a string literal in `build.py`, 44 of them, and nothing anywhere
said what the whole set was.

`build.py` READS THESE RATHER THAN RESTATING THEM, which is what makes this a home and not a second
copy. Every site that PRODUCES one of these values names the constant; the comparisons against them
are left as words, because a comparison states nothing about what the vocabulary is.

AND THE STORE IS WHERE THE TWO ARE MADE TO AGREE. `adapters/relational/schema.sql` keys the columns
on tables filled from here, so a value that arrives from anywhere else is refused by a rebuild
rather than stored. That is the arrangement `facts/division` already has with `basis`.

WHAT THIS DOES NOT OWN. When a work enters each state, which is `build.py`'s thresholds over the
release feed and is judgement rather than vocabulary.
"""

#: WHAT A WORK'S SERIALISATION IS DOING. `PRINT` and `ONESHOT` describe a work with no serialisation
#: to be running at all; `ACTIVE`, `SLOW` and `DORMANT` are thresholds over how recently a chapter
#: arrived; `COMPLETED` is a source saying so; `UNKNOWN` is the admitted silence.
#:
#: `HIATUS` HAS NO ROWS AND BELONGS HERE ANYWAY. `build.py` writes it where a run has skipped two
#: consecutive slots and the newest is recent, and no work meets that today. A vocabulary assembled
#: from what the corpus happens to hold would refuse the first work that went on one, which is a
#: constraint refusing correct data. Reading the PRODUCERS rather than the rows is what found it.
PRINT, ONESHOT, UNKNOWN = "print", "oneshot", "unknown"
COMPLETED, ACTIVE, DORMANT, SLOW, HIATUS = "completed", "active", "dormant", "slow", "hiatus"
STATES = (PRINT, ONESHOT, UNKNOWN, COMPLETED, ACTIVE, DORMANT, SLOW, HIATUS)

#: WHAT WE TAKE A PLATFORM TO HAVE SAID. Two answers, and the platform's own word is kept beside
#: this one in `state_claim.term`, because カドコミ answers `finished` in English where comici
#: answers 完結 and flattening them would hide that they are separate sources agreeing.
RUNNING = "running"
SAYS = (RUNNING, COMPLETED)

#: WHAT KIND OF EVENT A RELEASE ROW RECORDS. `chapter` is an instalment, `oneshot` a work complete
#: in one, `extra` something beside the run, `access-change` a chapter that became free or stopped
#: being, and `unclassified` a row nothing has decided about.
CHAPTER, EXTRA, ACCESS_CHANGE, UNCLASSIFIED = "chapter", "extra", "access-change", "unclassified"
RELEASE_KINDS = (CHAPTER, ONESHOT, EXTRA, ACCESS_CHANGE, UNCLASSIFIED)


def states():
    """Every state a work's serialisation can be in."""
    return STATES


def says():
    """Every reading we take from a platform's own statement about a serialisation."""
    return SAYS


def release_kinds():
    """Every kind of event a release row records."""
    return RELEASE_KINDS


#: WHEN A WORK'S SERIALISATION IS SAID TO HAVE GONE QUIET, in the words the file publishes beside
#: the states. `build.py` applies these numbers over the release feed and this is where they are
#: stated, because a threshold written in two places is two thresholds the day either moves.
ACTIVE_DAYS, SLOW_DAYS = 45, 365
THRESHOLDS = {"active": f"latest chapter within {ACTIVE_DAYS} days",
              "slow": "within a year", "dormant": "older than a year"}
