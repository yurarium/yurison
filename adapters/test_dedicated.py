#!/usr/bin/env python3
"""dedicated.py: which hosts an adapter of this project's own already reads.

COVERS = ['adapters/dedicated.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dedicated
import testkit


def main(s):
    # THE THREE HOSTS THE PER-WORK ROUTE WAS RE-READING, each with a dedicated adapter that holds
    # more chapters than the heuristic ever recovered: comicfuz 228 against 0 for 球詠, kadokomi 75
    # for 世界で一番おっぱいが好き！, nicovideo the work-level date the heuristic turned into a
    # chapter called `3話 無料`.
    s.eq(dedicated.covers("https://comic-fuz.com/manga/441"), "comic-fuz.com",
         "a COMIC FUZ work address is recognised")
    s.eq(dedicated.covers("https://comic-walker.com/detail/KC_000034_S"), "comic-walker.com",
         "a カドコミ work address is recognised")
    s.eq(dedicated.covers("https://manga.nicovideo.jp/comic/31194"), "manga.nicovideo.jp",
         "a ニコニコ漫画 work address is recognised")
    s.eq(dedicated.covers("https://comic.pixiv.net/works/9913"), "comic.pixiv.net",
         "and pixivコミック, which was the only host the per-work route knew to leave alone")

    # ONE PLATFORM UNDER TWO SPELLINGS OF ITS ADDRESS. FUZ serves the same page at /manga/<id> and
    # /series/<id>, and `data/coverage/remaining.yaml` carries ぬるめた as /series/2389, which 404s.
    # The run reported it as `page did not load`, which is a statement about the address rather
    # than about the work: adapters/comicfuz holds all 75 of its chapters.
    s.eq(dedicated.covers("https://comic-fuz.com/series/2389"), "comic-fuz.com",
         "the other spelling of a FUZ address is the same platform")

    # THE COUNTER-CASE, and it is the one that matters. adapters/remaining/ exists because the
    # platform passes skip individual works: 散らないで菊 is on コミックゼノン, its episode page
    # exposes the series feed, and the GigaViewer pass ran over that platform without asking for
    # it. A GigaViewer host named here would remove the residue this whole adapter reaches.
    for url in ("https://comic-zenon.com/episode/12207421983944323839",
                "https://ichicomi.com/episode/2551460910021695025",
                "https://tonarinoyj.jp/episode/2551460910044575820",
                "https://comic-days.com/episode/3269632237276869027"):
        s.check(dedicated.covers(url) is None,
                f"a GigaViewer address is still the per-work route's to try: {url}")

    # And an address on no listed host is nobody's.
    s.eq(dedicated.covers("https://www.corocoro.jp/title/773"), None,
         "a host with no adapter of its own is left to the generic routes")
    s.eq(dedicated.covers(None), None, "a missing address answers nothing rather than raising")

    # THE TWO READERS AGREE, because they read the same tuple. generic/releases.py held this list
    # first and adapters/remaining/ held a shorter copy, which is how the copies came to disagree.
    s.check(len(set(dedicated.HOSTS)) == len(dedicated.HOSTS),
            "the list names each host once")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "dedicated"))
