#!/usr/bin/env python3
"""webpages/releases.py: one engine, one parser.

COVERS = ['adapters/webpages/releases.py']

Comici is read by the shared module rather than by this file's selectors. Before that, every comici
platform read here (キミコミ, 竹コミ, ビッコミ, ライコミ, Gコミ, HERO'S Web, チャンピオンクロス,
花とゆめ+) carried a two-state access reading and only the first ten chapters, because the
three-state model and the range navigation had been worked out once and left in another file.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as wp

ENG = {"block": r'(?=<li class="ep">)',
       "title": r'<span class="t">([^<]+)<',
       "date": r'<time>(\d{4})/(\d{1,2})/(\d{1,2})</time>',
       "url": r'href="([^"]+)"'}


def li(title, y, m, d, href="/e/1"):
    return (f'<li class="ep"><a href="{href}"><span class="t">{title}</span></a>'
            f'<time>{y}/{m}/{d}</time></li>')


def main(s):
    rows = wp.episodes(li("第1話", 2026, 8, 3) + li("第2話", 2026, 8, 10, "/e/2"),
                       ENG, "https://x.jp")
    s.eq(len(rows), 2, "both blocks are read")
    s.eq(rows[0]["title"], "第1話", "the title comes from the engine's own selector")
    s.eq(rows[0]["updated"], "2026-08-03", "single-digit months and days are padded")

    # A block with no title is not an episode, and recording it would put a nameless row in the
    # feed with a real date attached.
    s.eq(wp.episodes('<li class="ep"><time>2026/8/3</time></li>', ENG, "https://x.jp"), [],
         "a block with no title is skipped")

    s.eq(wp.episodes("", ENG, "https://x.jp"), [], "an empty page yields nothing")

    # A comici page is routed to the shared parser, not to these selectors. The engine name alone
    # is not enough: the page must actually look like comici, or a misconfigured registry entry
    # would send an ordinary page down the wrong path.
    comici_eng = dict(ENG, engine_name="comici")
    s.eq(wp.episodes("<html>not comici at all</html>", comici_eng, "https://x.jp",
                     "https://x.jp/s/1", lambda u: ""), [],
         "an engine named comici on a page that is not comici falls through rather than misreading")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "webpages.releases"))
