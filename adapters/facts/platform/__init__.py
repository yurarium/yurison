#!/usr/bin/env python3
"""Which platform a page is on, and what that platform is called.

WHY THIS IS A MODULE, STORE-PLAN §12. `host_platforms` and `platform_of` were two functions in
`build.py` until `adapters/bylines.py` needed the same answer, and a rule asked twice becomes a
module rather than a second copy.

WHAT IT IS FOR. An adapter's module name is not a platform's name. `bylines.py` writes one file
holding a credit read off twelve different platforms' own pages, and it named the platform
`bylines` because the capture format wants one: seven work pages then showed `bylines` in the
Platform column beside COMIC FUZ and カドコミ, and it was an option in the reader's platform filter.
The address each row was read from says which platform it really is.

A HOST WITH TWO CLAIMANTS ANSWERS NOTHING. `comic-walker.com` carries カドコミ and other KADOKAWA
brands, so a URL on it cannot say which. Answering "probably カドコミ" would be a guess wearing a
fact's clothes, and an unnamed platform is a state the corpus already knows how to hold.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[3]

#: WHERE THE PROJECT WRITES A PLATFORM DOWN, AND THERE ARE TWO PLACES. `data/platforms.yaml` is the
#: project's own register and `adapters/gigaviewer/platforms.yaml` is the list one adapter drives
#: itself from, carrying two hundred more with their hosts. Two files, one answer: a reader asking
#: what platforms exist should not have to know which pass found one.
#: THE THIRD ONE WAS FOUND BY A DRIFT. `build.py` canonicalises a comparator's spelling through
#: all three and this module read two, so the two answers could differ about which name is the
#: platform's. `adapters/webpages/sites.yaml` keys its list under `sites` rather than `platforms`.
REGISTERS = ((ROOT / "data" / "platforms.yaml", "platforms"),
             (ROOT / "adapters" / "gigaviewer" / "platforms.yaml", "platforms"),
             (ROOT / "adapters" / "webpages" / "sites.yaml", "sites"))
REGISTER = REGISTERS[0][0]


#: A PLATFORM MARKED THIS IS ONE A READER MUST PROVE THEIR AGE TO OPEN, and no entry carries it
#: today. It is the one thing that stops a work being taken automatically from a platform the
#: register knows: DEFINITIONS §7 excludes pornography outright by designation, and a gate at the
#: door is such a designation made by the platform itself.
AGE_GATED = "age_gated"

#: AND A PLATFORM THAT SERVES NO WORKS AT ALL. マイナビニュース is read for the bylines it prints
#: in articles ABOUT works, so a work announced there is announced in a report rather than served.
#: Absent means it serves works, which is what every other entry in the register does.
SERVES_WORKS = "serves_works"


def registered():
    """Every platform either register holds, as `{name, id, publisher, host}` rows.

    A NAME IN BOTH FILES IS ONE PLATFORM, and the project's own register wins on the fields they
    both carry: it is where a person writes a ruling and the adapter's list is what a pass drives
    itself from.
    """
    out = {}
    for f, key in reversed(REGISTERS):
        if not f.exists():
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for p in (doc.get(key) or []):
            if not p.get("name"):
                continue
            hosts = ([p["host"]] if p.get("host") else []) + list(p.get("hosts") or [])
            # THE ENGLISH NAME LIVES WITH THE PLATFORM, READER-PLAN item 5. The interface held its
            # own table of these, which is a second register: it drifted, and three names reached
            # an English page in Japanese while a fourth was in the table and rendered through a
            # path that never asked it.
            # EVERY ID THE REGISTERS USE FOR IT, not only the winning file's. The project's own
            # register calls Seasons `seasons` and the adapter's calls it `comic-seasons`, and a
            # merge keyed on the name kept one: a caller holding the other spelling found no
            # platform at all, which is how a work announced there was refused as unknown. Same
            # shape as the two spellings of COMIC OGYAAA!! that reached a reader.
            was = out.get(p["name"], {})
            out[p["name"]] = {"name": p["name"], "id": p.get("id") or was.get("id"),
                              "ids": sorted({i for i in (p.get("id"), was.get("id"),
                                                         *(was.get("ids") or ())) if i}),
                              "aliases": [a for a in (p.get("aliases") or [])
                                          if a and a != p["name"]],
                              "publisher": p.get("publisher") or None, "en": p.get("en") or None,
                              # WHETHER THIS PIPELINE READS IT, AND WHETHER A READER MUST PROVE
                              # THEIR AGE TO. `serves_openly` is the one caller and both fields are
                              # the register's to state; dropping them here made a row that could
                              # not answer the question the register exists to answer.
                              "watched": bool(p.get("watched")),
                              AGE_GATED: bool(p.get(AGE_GATED)),
                              SERVES_WORKS: p.get(SERVES_WORKS) is not False,
                              "host": hosts[0] if hosts else None, "hosts": hosts}
    return list(out.values())


def owners(platforms=None):
    """`{host: platform name}` for every host exactly one platform claims."""
    if platforms is None:
        platforms = registered()
    seen = {}
    for p in platforms:
        # A PLATFORM MAY HOLD MORE THAN ONE HOST, because a site moves. 一迅プラス was
        # `ichicomi.com` and is `ichijin-plus.com`, and the register held only the old one, so a
        # page on the new domain named no platform at all. `hosts` lists them and `host` stays the
        # single form every other entry uses.
        for h in ([p["host"]] if p.get("host") else []) + list(p.get("hosts") or []):
            if h and p.get("name"):
                seen.setdefault(h, set()).add(p["name"])
    return {h: next(iter(n)) for h, n in seen.items() if len(n) == 1}


def of(url, known=None):
    """The platform a URL is on, where exactly one platform claims its host. None otherwise."""
    if not url or "://" not in str(url):
        return None
    return (owners() if known is None else known).get(str(url).split("/")[2])


def ids(platforms=None):
    """`{host: platform id}` for every host exactly one platform claims.

    THE SAME ANSWER AS `owners` IN THE OTHER CURRENCY. A name is what a reader is shown and an id
    is what an address is built from, and both are the register's to state.
    """
    if platforms is None:
        platforms = registered()
    by_name = {p["name"]: p.get("id") for p in platforms}
    return {h: by_name[n] for h, n in owners(platforms).items() if by_name.get(n)}


def id_of(url, known=None):
    """The id of the platform a URL is on, where exactly one platform claims its host.

    WHY AN ADDRESS MAY NOT BE BUILT FROM THE ROUTE THAT READ IT. A release id was minted from the
    capture file's own `platform` field, which is the name of the PASS: `remaining` for the browser
    route that reads whatever is left, `backfill` for the one that fills gaps. A work those routes
    covered kept its id only until a platform got an adapter of its own, and then every chapter of
    it was re-minted under a new address for no reason a reader could see. Three chapters of
    公爵令嬢の籠絡ミッション left the published July archive that way on 2026-08-15.

    THE PLATFORM IS A PROPERTY OF THE ADDRESS, not of the pass. `youngchampion.jp` is ヤングチャン
    ピオン whoever read it, so an id built from the host survives a routing change, and the register
    is the one place that maps the two.
    """
    if not url or "://" not in str(url):
        return None
    return (ids() if known is None else known).get(str(url).split("/")[2])




def serves_openly(pid, known=None):
    """Whether this platform is one the corpus takes a work from without asking a person first.

    THE POLICY THIS ANSWERS FOR, decided by the project owner on 2026-08-15: a new work served by a
    known commercial platform that is not age-gated is ingested and presented automatically. What
    stood in the way was not a rule but three gaps: 百合ナビ discovery ran in no workflow, its queue
    said a human must confirm each entry, and nothing promoted a confirmed one into the target list
    the platform adapters read. 贋作の第十番 was announced on チャンピオンクロス on 7 June and was
    still absent ten weeks later.

    WHAT QUALIFIES, AND IT IS THE REGISTER THAT SAYS SO. Being in the register is what "known"
    means: every entry is a publisher's or a distributor's site that somebody looked at and wrote
    down. `age_gated` and `serves_works` are the two exclusions, both stated there, so admitting a
    platform is one edit in one file rather than a rule spread across the passes that read it.

    `watched` IS NOT THE TEST, THOUGH IT LOOKS LIKE IT. It says this pipeline reads the platform,
    and it has gone stale in the direction that matters: サンデーうぇぶり is marked `false` and the
    corpus holds 130 of its chapters, as it does for マガポケ, ヤンジャン+ and きら星ポータル. A
    policy resting on it would refuse works from four platforms this reads every day. What the flag
    is for is reporting coverage, and it is wrong about that too.

    IT IS NOT AN INCLUSION TEST. Whether a work belongs is DEFINITIONS §2 and stays there: what this
    decides is whether a work already presumed in scope waits for a person before a reader sees it.
    """
    if not pid:
        return False
    for p in (registered() if known is None else known):
        if (pid in (p.get("ids") or (p.get("id"),)) or pid == p.get("name")
                or pid in (p.get("aliases") or [])):
            return not p.get(AGE_GATED) and p.get(SERVES_WORKS) is not False
    return False


def canonical(name, known=None):
    """The registered name for a platform, given any spelling the register lists for it.

    ONE PLATFORM UNDER TWO SPELLINGS IS STILL ONE PLATFORM, READER-PLAN item 9. The platform's own
    capture writes `COMIC OGYAAA!!` and a comparator claim writes `コミックオギャー!!`, and the
    register held both as entries in their own right, sharing an id and a host. Four feed rows read
    `COMIC OGYAAA!! · also on Comic Ogyaaa!!`, which tells a reader a work is somewhere else as
    well as where it is.

    AN ID IS A SPELLING THE REGISTER LISTS. `admit` hands this whatever a discovery pass recorded,
    which is the platform's id, and the target list every adapter reads is keyed on the display
    name: 贋作の第十番 was written into it as `championcross` where every other row says カドコミ or
    サンデーうぇぶり, so the adapters would have looked for a platform by that name and found none.

    AN UNKNOWN NAME COMES BACK UNCHANGED. A platform nobody has registered is a platform this
    cannot rename, and inventing a canonical form for it would be worse than leaving it alone.
    """
    if not name:
        return name
    for p in (registered() if known is None else known):
        if (name == p["name"] or name in (p.get("aliases") or [])
                or name in (p.get("ids") or ())):
            return p["name"]
    return name
