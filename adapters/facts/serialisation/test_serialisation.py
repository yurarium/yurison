#!/usr/bin/env python3
"""facts/serialisation: the three vocabularies that describe a running work.

COVERS = ['adapters/facts/serialisation/__init__.py']

WHAT THIS IS ACTUALLY ASSERTING. Not that the lists have particular members, which would restate
them, but that they are what the CORPUS uses, which is the only thing that can be wrong. A
vocabulary a compiler has outgrown is a vocabulary that refuses correct rows, and STORE-PLAN §5j
adopted these while every value in the store was already a member.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import serialisation                                         # noqa: E402

BUILD = pathlib.Path(__file__).resolve().parents[3] / "data" / "build"


def _rows(name, key):
    f = BUILD / name
    return (json.loads(f.read_text(encoding="utf-8")).get(key) or []) if f.exists() else []


def main(s):
    # ── THE VOCABULARIES ARE CLOSED, AND CLOSED MEANS A MEMBER CAN BE REFUSED ─────────────────
    s.check(all(isinstance(x, str) and x for x in serialisation.states()),
            "every state is a word")
    s.eq(len(set(serialisation.states())), len(serialisation.states()),
         "and no state is listed twice, which a set literal would have hidden")
    s.check("running" in serialisation.says() and "completed" in serialisation.says(),
            "a platform is taken to have said one of two things")
    s.check("completed" in serialisation.states() and "completed" in serialisation.says(),
            "AND THE TWO OVERLAP ON ONE WORD, which is why they are separate vocabularies: a "
            "state is what we conclude and a saying is what a source said")

    # ── AND EACH IS WHAT THE CORPUS ACTUALLY USES ─────────────────────────────────────────────
    #
    # THE ONLY WAY THESE CAN BE WRONG. A list nothing produces is a list that refuses a correct row
    # the day the compiler learns a new word, so the assertion worth making is against the data.
    rows = _rows("series.json", "series")
    if rows:
        used = {r.get("state") for r in rows if r.get("state")}
        s.eq(sorted(used - set(serialisation.states())), [],
             "every state the build writes is one this fact states")
        said = {c.get("says") for r in rows for c in (r.get("state_claims") or []) if c.get("says")}
        s.eq(sorted(said - set(serialisation.says())), [],
             "and every reading it takes from a platform")
    feed = _rows("feed/current.json", "releases")
    if feed:
        kinds = {r.get("type") for r in feed if r.get("type")}
        s.eq(sorted(kinds - set(serialisation.release_kinds())), [],
             "and every kind of event a release records")
    s.check(rows or feed, "the build was present for at least one of those to be asked of")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
