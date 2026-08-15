#!/usr/bin/env python3
"""facts/platform: which platform a page is on.

COVERS = ['adapters/facts/platform/__init__.py']

WHAT CAN BE WRONG HERE IS ANSWERING WHERE THE ADDRESS DOES NOT SAY. A host two platforms share
cannot name either, and a guess would reach a reader as a fact.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts import platform                                             # noqa: E402

#: A PLATFORM STATED TWICE, WHICH IS WHAT A MERGE ACROSS REGISTERS PRODUCES. `adapters/webpages/
#: sites.yaml` holds HERO'S Web with its viewer subdomain and the project's own register holds the
#: bare host, so the row this builds must carry both or seven works addressed at the viewer name no
#: platform at all.
TWICE = [{"name": "HERO'S Web", "id": "heros-web", "hosts": ["heros-web.com",
                                                             "viewer.heros-web.com"]},
         {"name": "HERO'S Web", "id": "heros", "host": "heros-web.com"}]

REGISTER = [{"name": "COMIC FUZ", "host": "comic-fuz.com", "id": "comic-fuz"},
            {"name": "カドコミ", "host": "comic-walker.com", "id": "kadokomi"},
            {"name": "ComicWalker", "host": "comic-walker.com", "id": "comicwalker"},
            {"name": "マイナビニュース", "host": "news.mynavi.jp", "id": "mynavi"},
            {"name": "ヤングチャンピオン", "host": "youngchampion.jp"},
            {"name": "ヤンマガWeb"}]


def main(s):
    known = platform.owners(REGISTER)
    s.eq(known.get("comic-fuz.com"), "COMIC FUZ", "a host one platform claims names it")
    s.check("comic-walker.com" not in known,
            "and a host two claim names neither, because the address cannot say which")
    s.check("ヤンマガWeb" not in known.values(),
            "a platform with no host of its own is not reachable this way")

    s.eq(platform.of("https://comic-fuz.com/manga/3612", known), "COMIC FUZ",
         "a URL answers with the platform that owns its host")
    s.eq(platform.of("https://news.mynavi.jp/article/1", known), "マイナビニュース",
         "which is how a byline read off a news site stops being called `bylines`")
    s.eq(platform.of("https://comic-walker.com/detail/KC_000188_S", known), None,
         "a shared host answers nothing rather than guessing")

    # ── AND WHAT IS NOT A URL ANSWERS NOTHING RATHER THAN RAISING ──────────────────────────────
    for got in (None, "", "not a url", "comic-fuz.com/manga/3612"):
        s.eq(platform.of(got, known), None, f"{got!r} names no platform")

    # ── THE SAME ANSWER IN THE OTHER CURRENCY ─────────────────────────────────────────────────
    #
    # A NAME IS WHAT A READER IS SHOWN AND AN ID IS WHAT AN ADDRESS IS BUILT FROM. A release id was
    # minted from the capture file's own `platform`, which is the name of the PASS: a work read by
    # the `remaining` browser route kept its id until the platform got an adapter of its own, and
    # then every chapter of it was re-minted for no reason a reader could see. Three chapters left
    # the published July archive that way on 2026-08-15.
    ids = platform.ids(REGISTER)
    s.eq(ids.get("comic-fuz.com"), "comic-fuz", "a host one platform claims names its id")
    s.check("comic-walker.com" not in ids,
            "and a shared host names no id, exactly as it names no platform")
    s.check("youngchampion.jp" not in ids,
            "nor does a platform the register gives no id, rather than inventing one")
    s.eq(platform.id_of("https://comic-fuz.com/manga/3612", ids), "comic-fuz",
         "so an address answers with the id of the platform whose host it is on")
    s.eq(platform.id_of("https://comic-walker.com/detail/KC_000188_S", ids), None,
         "and a shared host answers nothing here too")
    for got in (None, "", "not a url", "comic-fuz.com/manga/3612"):
        s.eq(platform.id_of(got, ids), None, f"{got!r} names no platform id")

    # THE REGISTER IS READ FROM DISK WHERE THE CALLER NAMES NONE, which is what every caller does.
    s.check(isinstance(platform.owners(), dict), "the corpus's own register loads")
    s.check(platform.ids(), "and it states an id for the hosts it claims")

    # ── ONE PLATFORM STATED IN TWO REGISTERS IS ONE PLATFORM WITH BOTH ITS HOSTS ──────────────
    #
    # The merge kept whichever file came last, so a host only the other one knew was dropped:
    # `viewer.heros-web.com` carries seven works and named no platform at all.
    o = platform.owners(TWICE)
    s.eq(o.get("viewer.heros-web.com"), "HERO'S Web",
         "a host stated in one register survives the other stating the platform too")
    s.eq(o.get("heros-web.com"), "HERO'S Web", "and so does the one they both state")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
