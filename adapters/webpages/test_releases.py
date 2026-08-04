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

    # A TRUNCATED TITLE, REPAIRED FROM THE PAGE'S OWN. youngchampion.jp cuts a listing at a fixed
    # length and appends an ellipsis, so 公爵令嬢の籠絡ミッション arrived with its second half gone
    # and no full-length copy anywhere in the catalogue to recover it from. The page states the
    # whole thing in og:title.
    FULL = ("\u516c\u7235\u4ee4\u5b22\u306e\u7c60\u7d61\u30df\u30c3\u30b7\u30e7\u30f3"
            "\uff5e\u9b54\u738b\u3068\u306e\u653f\u7565\u7d50\u5a5a\u304c\u3001"
            "\u4eba\u985e\u6700\u5f8c\u306e\u5207\u308a\u672d\u3067\u3059\uff01\u2026"
            "\u3063\u3066\u3001\u9b54\u738b\u304c\u5973\u306e\u5b50\u306e\u5834\u5408"
            "\u306f\u3069\u3046\u3059\u308c\u3070\u3044\u3044\u306e\u3067\u3059\u304b"
            "\uff01\uff1f\uff5e")
    CUT = FULL[:34].replace("\uff01", "!") + "..."
    page = f'<meta property="og:title" content="{FULL}">'
    s.eq(wp.untruncated(CUT, page), FULL, "the page's own title replaces a truncated one")
    # The prefix is tested on the comparison form: the listing wrote a half-width mark where the
    # page writes a full-width one, which is the single case this exists for.
    s.check("!" in CUT and "\uff01" in FULL, "the fixture really does mix the two marks")

    # A title that was not cut is left alone, whatever og:title says. マガポケ puts the episode and
    # the platform in its og:title, so firing on every difference would swap a correct title for a
    # decorated one.
    s.eq(wp.untruncated("\u79c1\u306b\u5929\u4f7f",
                         '<meta property="og:title" content="\u79c1\u306b\u5929\u4f7f | 1 / X">'),
         "\u79c1\u306b\u5929\u4f7f", "an untruncated title is never replaced")
    s.eq(wp.untruncated("\u5207\u308c\u305f...", "<html></html>"), "\u5207\u308c\u305f...",
         "and a page with no og:title leaves the truncation as it found it")
    s.eq(wp.untruncated("", page), "", "an empty title asks for nothing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "webpages.releases"))
