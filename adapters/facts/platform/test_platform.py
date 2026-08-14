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

REGISTER = [{"name": "COMIC FUZ", "host": "comic-fuz.com"},
            {"name": "カドコミ", "host": "comic-walker.com"},
            {"name": "ComicWalker", "host": "comic-walker.com"},
            {"name": "マイナビニュース", "host": "news.mynavi.jp"},
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

    # THE REGISTER IS READ FROM DISK WHERE THE CALLER NAMES NONE, which is what every caller does.
    s.check(isinstance(platform.owners(), dict), "the corpus's own register loads")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
