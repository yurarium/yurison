#!/usr/bin/env python3
"""artwork/covers.py: which image a page states, what it is, and what a rerun skips.

COVERS = ['adapters/artwork/covers.py']

OFFLINE BY CONSTRUCTION. Nothing here reaches a host: the page markup is passed in as a string and
the image bytes are made here, because what is under test is the reading of a page and the ordering
and resumption of the work, not the fetching, which is `net.py`'s and has its own suite.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import covers                                                          # noqa: E402
import testkit                                                         # noqa: E402


def _reading(s):
    OG = ('<html><head><meta property="og:image" content="/img/hero.jpg">'
          '<meta name="twitter:image" content="https://cdn.example.jp/t.png">')
    s.eq(covers.image_url(OG, "https://example.jp/works/12"),
         "https://example.jp/img/hero.jpg",
         "og:image is preferred and a relative address is made absolute")

    s.eq(covers.image_url('<meta content="https://cdn.jp/a.jpg" property="og:image">', "https://x.jp/"),
         "https://cdn.jp/a.jpg", "the attributes are read in either order, which platforms vary")

    s.eq(covers.image_url('<meta name="twitter:image" content="https://cdn.jp/t.png">', "https://x.jp/"),
         "https://cdn.jp/t.png", "twitter:image is the fallback where no og:image is stated")

    s.check(covers.image_url("<html><head><title>a page</title></head>", "https://x.jp/") is None,
            "a page stating no splash yields None rather than a guess")

    # A PLACEHOLDER IS NOT ARTWORK. Platforms serve one where a work has no cover, so accepting it
    # fills the store with the same grey rectangle under many names and wastes a person's time
    # looking at each of them.
    for u in ("/assets/no-image.png", "https://cdn.jp/img/noimg_640.jpg",
              "/static/placeholder.webp", "/i/default-cover.png"):
        s.check(covers.image_url(f'<meta property="og:image" content="{u}">', "https://x.jp/") is None,
                f"{u} is a placeholder and is refused")


def _extension(s):
    # THE BYTES DECIDE, NOT THE ADDRESS. A platform commonly serves `cover.jpg?w=640` that is really
    # a WebP, and storing that under .jpg makes a file nothing will open.
    s.eq(covers.extension("https://x.jp/a.jpg", b"RIFF\x00\x00\x00\x00WEBPVP8 "), ".webp",
         "a WebP served at a .jpg address is stored as what it is")
    s.eq(covers.extension("https://x.jp/nothing", b"\x89PNG\r\n\x1a\n"), ".png",
         "an address with no extension takes the magic number's answer")
    s.eq(covers.extension("https://x.jp/a.jpg", b"\xff\xd8\xff\xe0"), ".jpg", "a real JPEG")
    s.eq(covers.extension("https://x.jp/a.png?v=2", b"not an image at all"), ".png",
         "unrecognised bytes fall back to the address, which is better than nothing")
    s.eq(covers.extension("https://x.jp/thing", b"???"), ".bin",
         "and to .bin where the address says nothing either")


def _ordering(s):
    rows = [{"work": "old", "chapters": 3, "latest": "2024-01-01",
             "sources": [{"platform": "A", "url": "https://a.jp/1"}]},
            {"work": "new", "chapters": 3, "latest": "2026-08-01",
             "sources": [{"platform": "A", "url": "https://a.jp/2"}]},
            {"work": "print only", "chapters": 0, "sources": []},
            {"work": "no address", "chapters": 5, "sources": [{"platform": "A"}]}]
    got = covers.targets(rows)
    s.eq([t[0] for t in got], ["new", "old"],
         "recently updated first, and a work with no chapters or no address is not a target")

    # ONE ADDRESS PER WORK, and the row's own preferred source is the one taken. A work serialising
    # in three places carries the same artwork on each, so three fetches buy nothing.
    multi = [{"work": "w", "chapters": 2, "latest": "2026-01-01", "preferred": "B",
              "sources": [{"platform": "A", "url": "https://a.jp/x"},
                          {"platform": "B", "url": "https://b.jp/x"}]}]
    s.eq(covers.targets(multi)[0][1], "https://b.jp/x",
         "the preferred platform's address is the one fetched")


def _ledger(s):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "ledger.json"
        led = covers.Ledger(p)
        led.put("https://a.jp/1", work="w", state="stored", file="x.jpg")
        led.put("https://a.jp/2", work="v", state="no-image")
        led.put("https://a.jp/3", work="u", state="unreachable", why="HTTP 503")
        led.save()

        again = covers.Ledger(p)
        s.check(again.done("https://a.jp/1"), "a stored work is not looked at again")
        # A PAGE STATING NO SPLASH IS SETTLED. Without this every rerun fetches it for ever to
        # learn the same nothing.
        s.check(again.done("https://a.jp/2"), "and neither is one whose page states no splash")
        # A REFUSAL IS NOT SETTLED, because a 503 is the host asking to be tried later.
        s.check(not again.done("https://a.jp/3"), "a host that refused is tried again next time")
        s.check(not again.done("https://a.jp/9"), "a work never looked at is not done")
        s.eq(again.counts()["stored"], 1, "the ledger counts what it holds")

        # RESUMABLE MEANS THE SECOND RUN ASKS FOR LESS. This is the property the whole file is for.
        rows = [{"work": "w", "chapters": 1, "latest": "2026-01-01",
                 "sources": [{"platform": "A", "url": "https://a.jp/1"}]},
                {"work": "z", "chapters": 1, "latest": "2026-01-02",
                 "sources": [{"platform": "A", "url": "https://a.jp/9"}]}]
        left = [t for t in covers.targets(rows) if not again.done(t[1])]
        s.eq([t[0] for t in left], ["z"], "only the work the ledger has not settled is left to do")


def _ledger_survives_a_kill(s):
    """A half-written ledger must not cost a run its record."""
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "ledger.json"
        p.write_text("{ this is not json")
        led = covers.Ledger(p)
        s.eq(led.rows, {}, "a corrupt ledger reads as empty rather than raising")
        led.put("https://a.jp/1", work="w", state="stored")
        led.save()
        s.eq(len(covers.Ledger(p).rows), 1, "and the next save repairs it")
        s.check(not (p.with_suffix(".tmp")).exists(),
                "the write is atomic, so a kill mid-save leaves the old ledger and no debris")


def _rendered_key_matches_the_renderer(s):
    """The key this reads a rendered DOM under is the one `render/releases.py` wrote it under.

    §3, AND THE ONE LINE IT IS WORTH COPYING. Importing the render module would pull a headless
    browser's dependencies into a pass that only reads a file. So the key is duplicated, and the
    duplication is held together HERE by asking the real function what it produces: if that
    module's naming ever changes, this fails rather than the cover pass quietly re-fetching 52
    works from hosts that refuse it.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_render_rel", pathlib.Path(__file__).resolve().parents[1] / "render" / "releases.py")
    for url in ("https://comic.pixiv.net/works/10005",
                "https://comic-fuz.com/manga/3423",
                "https://x.jp/a?b=1&c=2"):
        import re as _re
        mine = _re.sub(r"[^A-Za-z0-9]", "_", url)[-120:]
        # The renderer builds the same string inline; this is that expression, read off its source
        # rather than reimplemented, so the test cannot agree with a copy of the bug.
        src = (pathlib.Path(__file__).resolve().parents[1] / "render" / "releases.py").read_text()
        line = next(l for l in src.splitlines() if 'key = re.sub' in l)
        theirs = eval(line.split("=", 1)[1].strip(), {"re": _re, "url": url})   # noqa: S307
        s.eq(mine, theirs, f"the cover pass and the renderer agree on the cache name for {url}")
    s.check(spec is not None, "and the renderer is where this expects it")


def main(s):
    _rendered_key_matches_the_renderer(s)

    _reading(s)
    _extension(s)
    _ordering(s)
    _ledger(s)
    _ledger_survives_a_kill(s)


if __name__ == "__main__":
    testkit.run(main, __file__)
