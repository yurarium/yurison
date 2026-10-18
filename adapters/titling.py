#!/usr/bin/env python3
"""How a platform titles a one-shot's only instalment, measured from its own captures.

WHY THIS EXISTS. サンデーうぇぶり marks no one-shot as one: つるこさん's page carries no 読切 badge
and its feed no status. What it does do is title things consistently. Across its captures 59 of
the 60 works holding one instalment title that instalment exactly as the work, and none of its 9
serials ever titles a chapter so; a serial's chapters are numbered (第3話, 1. 1回表), even the first.
少年ジャンプ+ is 43 of 43 the same way, webアクション 5 of 5 and ヤンマガWeb 13 of 13. The
convention is a fact about the platform, and a single instalment named after its work on a platform
that keeps it is a one-shot on better grounds than the shape alone.

MEASURED, NOT LISTED. いちコミ titles three serials' chapters after the work and となりのヤングジャンプ
self-names 28 of 81 single instalments, so a rule that trusted the shape everywhere would be wrong
there, and a list of the platforms where it holds would go stale as captures grow. The counts are
taken from the captures each build and carried into the basis a reader is shown.

A PLATFORM KEEPS THE CONVENTION where it holds at least MIN_SERIALS serials and none of them
self-names a chapter, and at least MIN_SINGLES single instalments of which SHARE or more are
self-named.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import textnorm                                                         # noqa: E402

MIN_SERIALS = 5
MIN_SINGLES = 5
SHARE = 0.9


def fold(s):
    return textnorm.norm(s or "").replace(" ", "")


def self_named(work, chapter):
    """Whether `chapter` is titled exactly as `work`, folded."""
    return bool(fold(work)) and fold(chapter) == fold(work)


def measure(works):
    """`{named, singles, serials, serials_named}` over one platform's works."""
    out = {"named": 0, "singles": 0, "serials": 0, "serials_named": 0}
    for w in works:
        chs = w.get("chapters") or []
        title = w.get("work_title")
        if len(chs) == 1:
            out["singles"] += 1
            out["named"] += self_named(title, chs[0].get("title"))
        elif len(chs) > 1:
            out["serials"] += 1
            out["serials_named"] += any(self_named(title, c.get("title")) for c in chs)
    return out


def keeps(m):
    """Whether a platform's counts show the convention."""
    return (m["serials"] >= MIN_SERIALS and not m["serials_named"]
            and m["singles"] >= MIN_SINGLES and m["named"] >= SHARE * m["singles"])


def conventions(docs, canonical=lambda s: s):
    """`{platform name: counts}` for the platforms keeping the convention, from capture documents
    each stating `platform_name` and `works`."""
    by = {}
    for d in docs:
        name = canonical((d or {}).get("platform_name"))
        if name:
            by.setdefault(name, []).extend((d or {}).get("works") or [])
    return {n: m for n, m in ((n, measure(ws)) for n, ws in by.items()) if keeps(m)}
