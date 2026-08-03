#!/usr/bin/env python3
"""claims/trace.py: which pages it will read, and what it refuses to guess at."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from claims import trace  # noqa: E402

COVERS = ["adapters/claims/trace.py"]

GIGA = '<html><a href="/atom/series/12207421984005617278">feed</a></html>'
# The real marker, taken from adapters/comici.py rather than invented: an earlier fixture here
# used a plausible-looking class that no comici page emits, so the test failed against correct code.
COMICI = ('<li data-e2e="eli"><span data-e2e="eliTitle">\u7b2c1\u8a71</span>'
          '<span class="series-eplist-item-meta-date">2026/07/01</span></li>')


def run(dispositions):
    return {"claims": {"trace": dispositions}}


def main(s):
    # ENGINE DETECTION. Getting this wrong in the permissive direction is the one mistake that
    # would put a wrong statement on the site: a partial history read as a whole one lets build.py
    # refute a claim that is true.
    s.eq(trace.engine_of(GIGA), "gigaviewer", "an Atom link identifies GigaViewer")
    s.eq(trace.engine_of(COMICI), "comici", "the viewer element identifies comici")
    s.eq(trace.engine_of("<html><body>a page</body></html>"), None,
         "an unknown layout is not guessed at")
    s.eq(trace.engine_of(""), None, "nor is an empty body")
    s.eq(trace.engine_of(None), None, "nor a missing one")

    s.eq(trace.series_feed_url(GIGA, "https://pocket.shonenmagazine.com/title/03282"),
         "https://pocket.shonenmagazine.com/atom/series/12207421984005617278",
         "the feed URL is absolute and on the page's own host")
    s.eq(trace.series_feed_url("<html></html>", "https://x.jp/title/1"), None,
         "and absent where the page carries no feed")

    # TARGETS. Only open claims, only those with a page, each page once.
    rows = [
        {"work": "A", "url": "https://x.jp/1", "disposition": "open", "platform": "P"},
        {"work": "A", "url": "https://x.jp/1", "disposition": "open", "platform": "P"},
        {"work": "B", "url": "https://x.jp/2", "disposition": "absorbed", "platform": "P"},
        {"work": "C", "url": "", "disposition": "open", "platform": "P"},
        {"work": "D", "url": "https://x.jp/4", "disposition": "open", "platform": "Q"},
    ]
    got = trace.targets(run(rows))
    s.eq([t["url"] for t in got], ["https://x.jp/1", "https://x.jp/4"],
         "one row per open claim with a page, deduplicated")
    s.eq(trace.targets(run([])), [], "and nothing at all when nothing is open")

    # MERGE. A refetch replaces a work's entry rather than adding a second one: two entries for one
    # work would leave the loader picking between them, which is the collision this project keeps
    # meeting.
    doc = {"works": [{"work_title": "A", "url": "https://x.jp/1", "chapter_count": 2,
                      "platform_name": "P"}]}
    fresh = [{"work_title": "A", "url": "https://x.jp/1", "chapter_count": 9, "platform_name": "P"}]
    out = trace.merge(doc, fresh)
    s.eq(len(out["works"]), 1, "a refetched work replaces its entry")
    s.eq(out["works"][0]["chapter_count"], 9, "and it is the fresh copy that survives")
    s.eq(out["platform_name"], "", "the file names no platform: it spans them")
    s.check(out["works"][0].get("platform_name"), "so each work carries its own")

    out2 = trace.merge(out, [{"work_title": "B", "url": "https://x.jp/2", "platform_name": "P"}])
    s.eq(len(out2["works"]), 2, "a work not seen before is added")
    s.eq(trace.merge({}, [])["works"], [], "an empty run writes an empty list, not a crash")

    # READ_PAGE refuses what it cannot read, rather than returning an empty history that would
    # look like a platform listing nothing.
    eng, chs = trace.read_page("https://x.jp/1", "<html>nothing familiar</html>", "/tmp")
    s.eq(eng, None, "an unreadable page reports no engine")
    s.eq(chs, [], "and no chapters")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
