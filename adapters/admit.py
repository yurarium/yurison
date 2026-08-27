#!/usr/bin/env python3
"""Works a comparator announced that the corpus takes without asking a person first.

THE POLICY, decided by the project owner on 2026-08-15. A new work served by a known commercial
platform that is not age-gated is ingested and presented automatically. Discovery says a work
exists and where; the platform's own page is what attests it; and between those two there is
nothing for a human to add that waiting supplies.

WHAT STOOD IN THE WAY WAS NOT A RULE. `data/queue/yurinavi.yaml` said in its own header that each
entry "needs confirming against the publisher or platform", nothing promoted a candidate into the
target list the platform adapters read, and the discovery pass ran in no workflow at all: the queue
was last written on 2026-08-01. 贋作の第十番 was announced on チャンピオンクロス on 7 June and was
absent from the corpus ten weeks later, as were クレアちゃん飼育日記 on カドコミ and one other.

WHAT IS STILL A HUMAN'S. Whether a work belongs is DEFINITIONS §2 and does not move: a comparator's
listing is a presumption, rebuttable by §3 and overridden by §7. The two content axes are still
somebody's call and a work reaches a reader without them, as thousands already do. What stops
being a human's is the WAIT: a work presumed in scope, served openly, and addressable is no longer
held back until somebody types its title into a list.

AND WHAT IS STILL REFUSED. A platform the register does not know, one it marks `age_gated`, and one
that serves no works: `facts/platform.serves_openly` is the whole of that test and the register is
where it is stated.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from facts import platform as _platform                            # noqa: E402

#: What a candidate must carry before an adapter can be pointed at it. A work with no address is a
#: work nothing can fetch, and promoting it would put a title in the target list that every pass
#: looks for and none finds.
NEEDS = ("work_title", "platform")


def addressable(candidate):
    """The work's own URL on the platform, where the candidate carries one."""
    url = candidate.get("work_url") or ""
    if url.startswith("http") and _platform.of(url) is not None:
        return url
    return None


def admits(candidate, known=None):
    """Whether this candidate is taken automatically, and why not where it is not.

    Returns `(True, None)` or `(False, reason)`. The reason is the point: a candidate refused for
    want of an address is a discovery pass to improve, and one refused for its platform is the
    register answering as it should.
    """
    # AN ADAPTATION ANNOUNCEMENT NAMES NO PLACE TO READ THE MANGA, and saying anything else about
    # it invites the wrong edit. ムルシエラゴ was announced as a TV anime on
    # `magazine.jp.square-enix.com`, which is where 集英社 posted the NEWS, and the refusal read
    # "a platform the register does not hold", which invites somebody to register a magazine's
    # press page as somewhere works are served. The signal is in the candidate and says so already.
    if candidate.get("signal") == "adaptation":
        return False, "an adaptation was announced, which names nowhere to read the work"
    if not all(candidate.get(k) for k in NEEDS):
        # A PLATFORM NOBODY HAS REGISTERED IS NOT NO PLATFORM, and the difference is what somebody
        # acts on. 最恐呪物令嬢's article links straight to `younganimal.com`, which 白泉社 runs and
        # the register does not hold: the queue said it named no platform, so the reason given for
        # it sitting there was wrong. Registering a platform is one edit in one file.
        host = candidate.get("platform_host")
        return False, (f"{host} is a platform the register does not hold" if host
                       else "names no platform")
    if not _platform.serves_openly(candidate.get("platform"), known):
        return False, f"{candidate['platform']} is not a platform this reads openly"
    if not addressable(candidate):
        return False, "carries no address on that platform"
    return True, None


def targets(queues, known=None):
    """`[{title, platform, url}]` for every candidate the policy admits, deduplicated by title.

    `queues` is the parsed discovery files, each `{"candidates": [...]}`. The caller merges these
    into the list the platform adapters read, which has one writer.
    """
    seen, out = set(), []
    for doc in queues:
        for c in (doc or {}).get("candidates") or []:
            ok, _why = admits(c, known)
            title = (c.get("work_title") or "").strip()
            if not ok or not title or title in seen:
                continue
            seen.add(title)
            out.append({"title": title,
                        "platform": _platform.canonical(c["platform"], known)
                        or c["platform"],
                        "url": addressable(c)})
    return out


def refused(queues, known=None):
    """`[(title, reason)]` for every candidate the policy does not admit, so nothing is silent."""
    out = []
    for doc in queues:
        for c in (doc or {}).get("candidates") or []:
            ok, why = admits(c, known)
            if not ok and (c.get("work_title") or "").strip():
                out.append((c["work_title"].strip(), why))
    return sorted(set(out))
