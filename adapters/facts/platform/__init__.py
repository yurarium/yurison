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
REGISTERS = (ROOT / "data" / "platforms.yaml",
             ROOT / "adapters" / "gigaviewer" / "platforms.yaml")
REGISTER = REGISTERS[0]


def registered():
    """Every platform either register holds, as `{name, id, publisher, host}` rows.

    A NAME IN BOTH FILES IS ONE PLATFORM, and the project's own register wins on the fields they
    both carry: it is where a person writes a ruling and the adapter's list is what a pass drives
    itself from.
    """
    out = {}
    for f in reversed(REGISTERS):
        if not f.exists():
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for p in (doc.get("platforms") or []):
            if not p.get("name"):
                continue
            hosts = ([p["host"]] if p.get("host") else []) + list(p.get("hosts") or [])
            # THE ENGLISH NAME LIVES WITH THE PLATFORM, READER-PLAN item 5. The interface held its
            # own table of these, which is a second register: it drifted, and three names reached
            # an English page in Japanese while a fourth was in the table and rendered through a
            # path that never asked it.
            out[p["name"]] = {"name": p["name"], "id": p.get("id"),
                              "publisher": p.get("publisher") or None, "en": p.get("en") or None,
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
