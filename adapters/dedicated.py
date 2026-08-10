#!/usr/bin/env python3
"""Which hosts are read by an adapter written for them, in one place (REQUIREMENTS §5).

WHY THIS IS A MODULE AND NOT A LINE IN EACH ADAPTER. A dedicated parser reads the platform's own
stated fields: COMIC FUZ's per-chapter access, カドコミ's `__NEXT_DATA__`, ニコニコ's
`div.meta_info`. A generic pattern matched against the same page returns something plausible
instead, and the build then holds two answers to one question with nothing to prefer either by
(STANDING-INSTRUCTIONS §3).

`adapters/generic/` learned that and wrote the list down. `adapters/remaining/`, which tries every
route against a single work, kept a shorter copy of its own naming comic.pixiv.net alone, so it
re-read comic-fuz.com, comic-walker.com and manga.nicovideo.jp and published eight works the
dedicated adapters already held in full. The clearest of the eight:

    お姉さんは女子小学生に興味があります。 came back with two chapters, `第１話から読む` and
    `3話 無料`. The first is the read-from-the-start button. The second is a fragment of ニコニコ's
    own meta line, `[ 3話 無料 ]`, which states how many episodes are free. 竹コミ's adapter holds
    64 chapters for the same work and `adapters/nicovideo/` reads its update date off that very
    line, correctly.

Two files named `releases.py` cannot import a constant from each other, which is the practical
reason this is a module of its own rather than a name exported from the adapter that needed it
first.

WHAT IS DELIBERATELY ABSENT. GigaViewer hosts. `adapters/remaining/` exists precisely because the
platform passes skip individual works: 散らないで菊 sits on コミックゼノン, its episode page exposes
the series feed, and the GigaViewer adapter ran over that platform without ever asking for it.
Naming those hosts here would remove the residue that adapter was built to reach.
"""

#: Hosts an adapter of this project's own reads. A generic or per-work route must leave them alone.
HOSTS = ("comic-walker.com", "comic-fuz.com", "manga.nicovideo.jp",
         "www.yomonga.com", "yomonga.com", "comic.pixiv.net")


def covers(url):
    """The dedicated host in `url`, or None.

    SUBSTRING, matched against the whole address, because that is how the callers phrase the
    question and a work reaches us as a URL rather than as a parsed host. `comic-fuz.com/manga/441`
    and `https://comic-fuz.com/series/2389` are the same platform under two spellings of one
    address, and both must be recognised.
    """
    return next((h for h in HOSTS if h in (url or "")), None)


if __name__ == "__main__":
    print("\n".join(HOSTS))
