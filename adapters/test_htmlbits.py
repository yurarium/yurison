#!/usr/bin/env python3
"""adapters/htmlbits: the patterns every web source shares.

COVERS = ['adapters/htmlbits.py']

Each assertion is a page shape the corpus has actually met, including the two spellings that were
in use for one thing.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "names"))
import htmlbits as h                                                    # noqa: E402
import testkit                                                          # noqa: E402


def main(s):
    # TWO SPELLINGS WERE IN USE, `(.*?)` and `([^<]*)`, which differ only on a title holding a
    # newline. The lazy form with DOTALL handles both, so neither caller loses anything.
    s.eq(h.TITLE.search("<title>Yuri</title>").group(1), "Yuri", "a title is read")
    s.eq(h.TITLE.search("<title>two\nlines</title>").group(1), "two\nlines",
         "including one broken over a line, which one of the two spellings missed")

    # AND TWO FOR og:title, one of which required the attributes in a fixed order.
    s.eq(h.OG_TITLE.search('<meta property="og:title" content="A">').group(1), "A",
         "the plain order is read")
    s.eq(h.OG_TITLE.search('<meta charset="utf-8" property="og:title" data-x="1" content="B">')
         .group(1), "B", "and a reordered one, which a page may write and has not thereby changed")

    s.eq(h.RSS_ITEM.findall("<item>a</item><item>b</item>"), ["a", "b"], "RSS items")
    s.eq(h.ATOM_ENTRY.findall("<entry>x</entry>"), ["x"], "and Atom entries, a different wrapper")
    s.eq(h.ANCHOR.search('<a href="/x">t</a>').group(1), "t", "a link's text")
    s.eq(h.ALT.search('<img alt="c">').group(1), "c", "an image's alternative text")
    s.eq(h.DT_DD.search("<dt>k</dt>\n<dd>v</dd>").groups(), ("k", "v"),
         "and a definition pair, which two catalogues use for their fields")

    s.eq(h.canonical('<link rel="canonical" href="https://a/series/1"/>'), "https://a/series/1",
         "a page's canonical address is read")
    s.eq(h.canonical('<link href="https://a/2" rel="canonical">'), "https://a/2", "in either order")
    s.eq(h.canonical('<link rel="stylesheet" href="x.css">'), None, "and another link is not one")

    # WHAT IS DELIBERATELY ABSENT. A selector naming one shop's markup belongs to that shop's
    # adapter; four of them here would put four shops' HTML in a file none of them owns.
    for gone in ("ELI", "M_BOOK_ITEM", "ATOM_SERIES", "COMIC_WALKER"):
        s.check(not hasattr(h, gone), f"{gone} is one source's markup and is not here")


    # A PRIZE CITATION, opening the description or bracketed after the title's own sentence.
    page = '<meta property="og:description" content="{}">'
    s.eq(h.citation(page.format("第３回大波賞「佳作」受賞作品。会社勤めの主人公・先輩。")),
         "第３回大波賞「佳作」受賞作品。会社勤めの主人公・先輩。",
         "a description that opens on a prize and its rank is a citation")
    s.eq(h.citation(page.format("エンパシー。【ちばてつや賞ヤング部門第88回佳作】生活のため病院で…")),
         "【ちばてつや賞ヤング部門第88回佳作】", "and so is the bracket ヤンマガWeb writes after the title")
    s.eq(h.citation(page.format("TANGO。女子高生のサラとレイの2人は色んな秘密を共有してる。")), None,
         "a synopsis is not")
    s.eq(h.citation(page.format("佐藤糸はクラスの姫として女子校生活を満喫していた。漫画賞で大賞を狙う")), None,
         "nor one that mentions a prize after its first sentence")

if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
