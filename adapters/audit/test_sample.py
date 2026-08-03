#!/usr/bin/env python3
"""audit/sample.py: enumerating what a reader would take from a row.

COVERS = ['adapters/audit/sample.py']

The audit exists to be checked against the platform by hand, so a claim it fails to list is a claim
nobody verifies. Under-listing is the failure mode, and it is silent.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import sample


def kinds(row):
    return {k for k, _ in sample.claims_for_update(row)}


def main(s):
    base = {"work": "百合の花", "pub": "2026-08-03", "plat": "x", "plat_name": "プラットフォーム"}

    got = kinds(base)
    s.check("work" in got, "the work itself is a claim")
    s.check("date" in got, "the date is a claim")
    s.check("platform" in got, "the platform is a claim")

    # Absence must not become a claim. A row with no author must not assert an author.
    s.check("author" not in got, "a row without an author claims no author")
    s.check("chapter" not in got, "a row without a chapter name claims no chapter")
    s.check("access" not in got, "a row stating no access terms claims none")

    s.check("author" in kinds({**base, "author": "作者"}), "an author present is claimed")
    s.check("chapter" in kinds({**base, "ep": "第1話"}), "a chapter name present is claimed")
    s.check("chapter" not in kinds({**base, "ep": "   "}),
            "a blank chapter name is not a chapter name")

    # Access is three distinct claims, because they promise the reader different things.
    free = dict(sample.claims_for_update({**base, "free": True, "access_modes": ["free"]}))
    s.check("free" in free.get("access", ""), "free says free")
    timed = dict(sample.claims_for_update({**base, "access_modes": ["free-timed"]}))
    s.check("no cost" in timed.get("access", ""), "free-timed promises no cost, with a wait")
    paid = dict(sample.claims_for_update({**base, "access_modes": ["purchase"]}))
    s.check("costs money" in paid.get("access", ""), "purchase says it costs money")

    # Kind claims tell a reader whether to expect more, so a wrong one misleads directly.
    s.check("kind" in kinds({**base, "kind": "oneshot"}), "a one-shot states it is complete")
    s.check("kind" in kinds({**base, "kind": "new-series"}), "a new series states it is a start")
    s.check("kind" not in kinds({**base, "kind": "new-chapter"}),
            "an ordinary chapter makes no special claim")

    # Every claim is a pair of a tag and a sentence a person can check against the platform.
    for k, text in sample.claims_for_update({**base, "author": "a", "ep": "第1話"}):
        s.check(isinstance(k, str) and isinstance(text, str) and text.strip(),
                f"claim {k!r} carries a checkable sentence")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "audit.sample"))
