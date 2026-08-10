#!/usr/bin/env python3
"""sevenseas.py: a licence read from the licensor, and the imprint that decides scope."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import sevenseas as ss  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/sevenseas.py"]

# Quoted from the served pages. The first is on the adult imprint, which is why it is the fixture.
GHOST = ('<div class="publisher"><a href="https://ghostshipmanga.com/">Ghost Ship</a></div>'
         '<div id="SSGL-block" class="age-rating">girls\' love</div>'
         '<div class="age-rating" id="olderteen17"></div>'
         '<div id="originaltitle">姫と女勇者が結ばれるための12の聖行為 | '
         'Hime to Onna Yuusha ga Musubareru Tame no 12 no Hijiri Koui</div>')

LIST = ('<a href="https://sevenseasentertainment.com/series/a-white-rose-in-bloom/">'
        'A White Rose in Bloom</a>'
        '<a href="https://sevenseasentertainment.com/series/a-white-rose-in-bloom/">'
        '<img alt="cover"></a>'
        '<a href="https://sevenseasentertainment.com/series/bloom-into-you/">Bloom Into You</a>')


def main(s):
    got = ss.series_links(LIST)
    s.eq(len(got), 2, "each series once, however many times the page links to it")
    s.eq(got["https://sevenseasentertainment.com/series/bloom-into-you/"], "Bloom Into You",
         "with the title the catalogue prints")
    # A COVER LINK CARRIES NO TITLE. Taking the last link per url would file a series under the
    # empty string, and taking the first keeps the one a reader was shown.
    s.eq(got["https://sevenseasentertainment.com/series/a-white-rose-in-bloom/"],
         "A White Rose in Bloom", "and an image link does not overwrite it")
    s.eq(ss.series_links(""), {}, "no page, no series")

    ja, ro = ss.original_title(GHOST)
    s.eq(ja, "姫と女勇者が結ばれるための12の聖行為", "the Japanese title is what joins to our corpus")
    s.eq(ro, "Hime to Onna Yuusha ga Musubareru Tame no 12 no Hijiri Koui",
         "and the licensor's own romaji is attested, so it is kept rather than re-derived")
    s.eq(ss.original_title("<div>nothing</div>"), (None, None), "no block, no claim")
    s.eq(ss.original_title('<div id="originaltitle">日本語だけ</div>'), ("日本語だけ", None),
         "and a block with no romaji still yields the title")

    # THE IMPRINT DECIDES WHETHER §7 EXCLUDES THE WORK. Ghost Ship is the adult line, and an adult
    # imprint is one of the four exclusion signals, so it must survive the read rather than being
    # collapsed into "Seven Seas licensed it".
    s.eq(ss.imprint(GHOST), "Ghost Ship", "the adult imprint is named")
    s.eq(ss.imprint('<div><a href="https://sevenseasentertainment.com/">Seven Seas</a></div>'),
         "Seven Seas", "and so is the general one")
    s.eq(ss.imprint("<div>no publisher here</div>"), None, "silence is not an imprint")

    s.eq(ss.match_key("姫と女勇者が結ばれるための１２の聖行為"), ss.match_key("姫と女勇者が結ばれるための12の聖行為"),
         "full-width digits are the same title")
    s.eq(ss.match_key("私に天使が舞い降りた！"), ss.match_key("私に天使が舞い降りた!"),
         "and so is a title whose exclamation mark differs in width")
    s.check(ss.match_key("citrus") != ss.match_key("citrus+"),
            "while a sequel marker is not decoration and must survive the fold")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
