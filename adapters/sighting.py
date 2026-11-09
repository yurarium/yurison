#!/usr/bin/env python3
"""How the first-seen ledger identifies a release, REQUIREMENTS §5.

WHAT THE LEDGER IS FOR. A publication date is locked at first sighting and never revised, and a
release published before we heard of it is news on the day it is found rather than on a date months
back where nobody would look. Both need somewhere to remember the sighting, because source files
are snapshots that every adapter overwrites on every run.

WHAT A SIGHTING IS KEYED ON, AND WHY IT STOPPED BEING THE PLATFORM'S NAME. The key was
`work|episode|platform`, on the reasoning that a release whose key changes is a release we have not
seen. That holds for the work and for the chapter. It does not hold for the platform: correcting
WHERE we say a chapter is does not make it a chapter nobody saw. 公爵令嬢の籠絡ミッション was filed
under チャンピオンクロス and read from ヤングチャンピオン, the corrected attribution re-keyed all
four of its chapters, and three June and July rows became sightings of 2026-08-15. They left the
published July archive and arrived in the current window as news, so a reader saw a re-attribution
as a publication.

A CHAPTER'S ADDRESS SURVIVES BOTH. It is the same page whoever read it and whatever we later decide
to call the platform, so the key is the URL and the episode together: some routes give a chapter its
own address and some give the series page, and the address alone collapsed every chapter of a work
into one sighting.

THE MIGRATION IS THE CAREFUL PART, and `carried` is all of it. Every row in the ledger today is
under the old key, so a straight switch would make every release a sighting of the day it ran and
surface the whole corpus as news at once.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "names"))

from facts.worktitle import norm_work                                   # noqa: E402


def legacy_key(row):
    """`work|episode|platform`, the form the ledger was written in until 2026-08-15."""
    return (f"{norm_work(row.get('work') or '')}|{norm_work(row.get('ep') or '')}|"
            f"{row.get('plat_name') or row.get('plat')}")


def key(row):
    """What this release is remembered as: its own address and chapter, or the old form."""
    if row.get("url"):
        return f"url|{row['url']}|{norm_work(row.get('ep') or '')}"
    return legacy_key(row)


def by_episode(ledger):
    """`{episode: [(work, date)]}` over the ledger's old-form keys, for `carried` to search."""
    out = {}
    for k, v in ledger.items():
        if k.startswith("url|") or k.count("|") < 2:
            continue
        work, ep, _plat = k.split("|", 2)
        out.setdefault(ep, []).append((work, v))
    return out


def carried(ledger, row, index=None):
    """The earliest date this chapter was seen under any spelling of its work, or nothing.

    THE PLATFORM IS DROPPED FROM THE MATCH because the platform is what changed. What remains is
    the episode, which must be equal, and the work, which must be one string or a prefix of the
    other: a capture that later gave the full title lengthened it, so the same chapter sits under
    two work spellings with two dates. 公爵令嬢の籠絡ミッション's 第9話① is there truncated and
    seeded on 2026-08-02 and again in full on 2026-08-04, and taking the later one turns a seeded
    row, which the caller treats as unknown, into a sighting that makes a July chapter August news.

    THE EARLIEST OF THEM WINS, for the same reason. The exact old key is one spelling among several
    and it is the one most recently written.

    WHAT IT COSTS, SAID PLAINLY. Where two platforms genuinely carry one chapter, this hands the
    second row the date we first saw the first. That is the right answer to "when did we first see
    this chapter" and it is not the answer to "when did this platform first show it"; the second
    question is what a per-address key answers from now on, and this runs once per row, only while
    the ledger has no address for it.
    """
    work, ep, _plat = legacy_key(row).split("|", 2)
    seen = (index if index is not None else by_episode(ledger)).get(ep, ())
    got = [v for w, v in seen if w and (w.startswith(work) or work.startswith(w))]
    return min(got) if got else None


def by_address(ledger):
    """`{address: [(episode, date)]}` over the ledger's address keys, for `renamed` to search."""
    out = {}
    for k, v in ledger.items():
        if not k.startswith("url|"):
            continue
        url, _, ep = k[4:].rpartition("|")
        out.setdefault(url, []).append((ep, v))
    return out


def finale_seen(index, is_final):
    """`{address: date}`: the earliest day a chapter `is_final` names the last was seen there.

    A RENDERED PAGE SHOWS A WINDOW, and a finale leaves it while the work goes on posting extras.
    付き合ってあげてもいいかな's 第133話(最終話) was seen on マンガワン on 2026-09-06 and was gone from
    the page by November; the ledger is the record that keeps it.
    """
    out = {}
    for url, eps in (index or {}).items():
        days = [str(d)[:10] for ep, d in eps if is_final(ep)]
        if days:
            out[url] = min(days)
    return out


def _subtitled(a, b):
    """Whether `b` is `a` with something added after it that does not extend a number."""
    return bool(a and b and a != b and b.startswith(a) and not b[len(a)].isdigit())


def renamed(ledger, row, index=None):
    """The earliest date this chapter was seen at its own address under a shorter or longer name.

    A PLATFORM THAT ADDS A SUBTITLE HAS NOT PUBLISHED A CHAPTER. カドコミ listed 死神さんと昇天ごはん's
    chapters as 第1話 and 第2話 in October and as 第1話 ソラとナデシコ and 第2話 日が暮れて途方に暮れて on
    9 November. The key holds the name, so the renamed chapters were sightings of the 9th, and the
    late-find rule put a work we had followed for a month at the top of Updates as new.

    ONLY A NAME THE OTHER CONTINUES, and not into a number. Some routes give every chapter the
    series page as its address, where 第1話 and 第1話② are two chapters and 25 and 256 are not one;
    an empty name, which a work-level row carries, matches nothing.
    """
    if not row.get("url"):
        return None
    ep = norm_work(row.get("ep") or "")
    held = (index if index is not None else by_address(ledger)).get(row["url"], ())
    got = [v for e, v in held if _subtitled(e, ep) or _subtitled(ep, e)]
    return min(got) if got else None
