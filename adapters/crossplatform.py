#!/usr/bin/env python3
"""Merge the same chapter across platforms, and point readers at the best one (REQUIREMENTS §5).

Three facts about multi-platform serialisation drive this, and each breaks a naive approach:

1. **A series is often on several platforms.** 19.6% of works on Web漫画アンテナ's 百合 tag, up to
   six each. Treating each platform's feed independently produces duplicate entries for one
   chapter.

2. **Releases are not simultaneous.** The same chapter can land a day or two apart. Matching on an
   exact timestamp therefore fails, and matching without a window produces duplicates separated by
   a couple of days — worse than either, because they look like two chapters.

3. **A platform can silently stop carrying a series.** No notice, no end marker; new chapters
   simply stop appearing there while continuing elsewhere. So the preferred source must be chosen
   **per release, from the platforms that actually carry that release** — not per work. A platform
   being better in general is no use if it does not have chapter 13.

The reading-quality ranking lives in `data/platforms.yaml` and is editorial curation, not a fact
from any source. It affects only where a reader is pointed, never inclusion or classification.
"""
import re
import unicodedata
from datetime import date, timedelta

# Releases of the same chapter this far apart are still one release.
MERGE_WINDOW_DAYS = 3

# A platform this many chapters behind the leader is treated as having lapsed, not as evidence
# that the series ended.
LAPSE_CHAPTERS = 2


def norm(s):
    return re.sub(r"[\s\-.=、。･・！!？?　]", "", unicodedata.normalize("NFKC", s or "").lower())


def episode_key(title):
    """Platforms number chapters differently — 第7話 / 7話 / #7 / その7. Reduce to the number when
    one is present, so the same chapter matches across platforms. Titled episodes fall back to the
    normalised title, which only matches within a platform's own naming."""
    t = unicodedata.normalize("NFKC", title or "")
    m = re.search(r"(?:第|#|その)?\s*(\d+)\s*(?:話|回|章)?", t)
    return f"n{int(m.group(1))}" if m else f"t{norm(t)}"


def _d(v):
    if isinstance(v, date):
        return v
    s = str(v)[:10]
    try:
        return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except (ValueError, IndexError):
        return None


def merge_releases(rows, ranks):
    """rows: dicts with work, episode, platform, date, url. ranks: {platform: reading_rank or None}.

    Returns one entry per chapter, carrying every source it was seen on, with `preferred` set to the
    best-ranked platform that actually carries it.
    """
    buckets = []
    for r in sorted(rows, key=lambda r: (norm(r["work"]), episode_key(r["episode"]),
                                         str(r.get("date") or ""))):
        k = (norm(r["work"]), episode_key(r["episode"]))
        d = _d(r.get("date"))
        for b in buckets:
            if b["key"] != k:
                continue
            bd = _d(b["date"])
            # Same chapter, close in time: one release seen in two places (fact 2).
            if d and bd and abs((d - bd).days) > MERGE_WINDOW_DAYS:
                continue
            b["sources"].append(r)
            if d and bd and d < bd:
                b["date"] = r["date"]        # earliest sighting wins and is then locked (§5)
            break
        else:
            buckets.append({"key": k, "work": r["work"], "episode": r["episode"],
                            "date": r.get("date"), "sources": [r]})

    UNRANKED = 99
    out = []
    for b in buckets:
        # Best-ranked platform AMONG THE SOURCES CARRYING THIS RELEASE (fact 3).
        best = min(b["sources"], key=lambda s: (ranks.get(s["platform"]) or UNRANKED,
                                                s["platform"]))
        out.append({
            "work": b["work"], "episode": b["episode"], "date": b["date"],
            "preferred": best["platform"], "preferred_url": best.get("url"),
            "also_on": sorted({s["platform"] for s in b["sources"]} - {best["platform"]}),
            "source_count": len(b["sources"]),
            # The rows that went into this bucket. Callers need them to map a release back to its
            # merged entry — grouping is on a normalised key, so only one row per bucket has the
            # raw strings the entry carries, and everything else failed a lookup keyed on those.
            "sources": b["sources"],
        })
    return sorted(out, key=lambda e: (str(e["date"] or ""), e["work"]), reverse=True)


def carriage(rows):
    """Detect platforms that have quietly stopped carrying a series.

    A platform whose latest numbered chapter for a work trails the leader by LAPSE_CHAPTERS or more
    is marked `lapsed`. This is a caution, not a conclusion: it must never be read as the series
    ending, only as that platform no longer being a reliable place to follow it.
    """
    latest = {}
    for r in rows:
        k = episode_key(r["episode"])
        if not k.startswith("n"):
            continue
        n = int(k[1:])
        key = (norm(r["work"]), r["platform"])
        if n > latest.get(key, -1):
            latest[key] = n

    by_work = {}
    for (w, p), n in latest.items():
        by_work.setdefault(w, {})[p] = n

    out = []
    for w, plats in by_work.items():
        lead = max(plats.values())
        for p, n in sorted(plats.items()):
            out.append({"work": w, "platform": p, "latest_chapter": n,
                        "behind_by": lead - n,
                        "status": "lapsed" if lead - n >= LAPSE_CHAPTERS else "active"})
    return out
