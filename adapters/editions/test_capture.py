#!/usr/bin/env python3
"""capture.py: the parts of the run that decide what the queue file ends up saying.

The fetching stays out of this suite because it has to: `test.py` blocks the network, which is what
forces the page reading into `platforms.py` where it is tested against fixtures. What is left is
the bookkeeping, and the bookkeeping is where this project's silent failures have lived.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import capture                                                                 # noqa: E402
import engines                                                                 # noqa: E402
import testkit                                                                 # noqa: E402
import yaml                                                                    # noqa: E402

# The engine table is exercised here rather than in a file of its own: it is a table plus two
# lookups, and the questions worth asking about it are the ones this suite already asks.
COVERS = ["adapters/editions/capture.py", "adapters/editions/engines.py"]


def main(s):
    # ── which works the run is for ───────────────────────────────────────────────────────────
    doc = {"series": [
        {"id": "w1", "work": "held in print", "author": "A",
         "sources": [{"platform": "P", "url": "https://comic-walker.com/detail/X"}],
         "print": [{"work_id": "C1"}]},
        {"id": "w2", "work": "web only", "author": "B",
         "sources": [{"platform": "P", "url": "https://comic-walker.com/detail/Y"}]},
        {"id": "w3", "work": "print only", "author": "C", "sources": []},
        {"id": "w4", "work": "two platforms", "author": "D",
         "sources": [{"platform": "P", "url": "https://ichicomi.com/episode/1"},
                     {"platform": "Q", "url": "https://comic.pixiv.net/works/2"}]},
    ]}
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "series.json"
        f.write_text(json.dumps(doc))
        got = capture.gap_works(f)
    s.eq([w["work"] for w in got], ["web only", "two platforms", "two platforms"],
         "a work already holding a print edition is not asked for, and a print-only work has no "
         "platform to ask")
    s.eq(len(got), 3, "a work on two platforms is two rows, because each address is its own lead")

    # ── the engine table ─────────────────────────────────────────────────────────────────────
    s.eq(engines.engine_of("https://comic-walker.com/detail/KC_006662_S")[0], "kadokomi",
         "a host names its engine")
    s.eq(engines.engine_of("https://bigcomics.jp/series/abc")[0], "comici",
         "and eleven platforms share one")
    s.eq(engines.engine_of("https://comic-fuz.com/manga/2062"), None,
         "a platform with no route is absent from the table rather than guessed at")
    s.check("comic-fuz.com" in engines.NO_ROUTE,
            "and is recorded as checked, so that no route and not checked stay different answers")
    s.check(all(e in engines.STEPS for e, _ in engines.ENGINES.values()),
            "every engine in the table states what asking it costs")

    # ── the carry-over rule ──────────────────────────────────────────────────────────────────
    # A pass must not delete what it is not looking at. This file is rebuilt whole on every run, so
    # a merge that dropped the works this run did not visit would lose them silently: the file
    # stays well-formed, gets smaller, and says nothing about what went missing.
    held = {"works": [
        {"platform_url": "https://a/1", "work": "kept", "volumes": [{"isbn": "9784000000001"}]},
        {"platform_url": "https://a/2", "work": "replaced", "volumes": []},
    ]}
    merged, added = capture.merge(held, [
        {"platform_url": "https://a/2", "work": "replaced", "volumes": [{"isbn": "9784000000002"}]},
        {"platform_url": "https://a/3", "work": "new", "volumes": []},
    ])
    urls = [w["platform_url"] for w in merged["works"]]
    s.eq(sorted(urls), ["https://a/1", "https://a/2", "https://a/3"],
         "the work this run did not visit is still there")
    s.eq(added, 1, "and only the genuinely new row is counted as new")
    by = {w["platform_url"]: w for w in merged["works"]}
    s.eq(by["https://a/2"]["volumes"], [{"isbn": "9784000000002"}],
         "a revisited work takes this run's answer")
    s.eq(by["https://a/1"]["volumes"], [{"isbn": "9784000000001"}],
         "and an untouched one keeps its own")

    # ── what the file says, read back ────────────────────────────────────────────────────────
    out = capture.render({
        "source": "platform-retail-links", "role": "print-edition-discovery",
        "record_type": "platform_retail_capture", "retrieved": "2026-08-07",
        "counts": {"works": 2}, "works": [
            {"platform_url": "https://comic-walker.com/detail/X", "id": "w1", "work": "ある作品",
             "platform": "カドコミ", "engine": "kadokomi", "steps": "page -> shop title page",
             "retrieved": "2026-08-07",
             "volumes": [capture.book("9784253013925", "ある作品 1", "https://www.cmoa.jp/title/1/", 1)],
             "notes": []},
            {"platform_url": "https://ichicomi.com/episode/1", "work": "no volumes",
             "engine": "giga", "volumes": [], "notes": ["the platform lists no volume"]},
        ]})
    back = yaml.safe_load(out)
    s.eq(len(back["works"]), 2, "the rendered file parses back to what went in")
    s.eq(back["works"][0]["volumes"][0]["isbn"], "9784253013925", "with the ISBN intact")
    s.eq(back["works"][0]["volumes"][0]["via"], "https://www.cmoa.jp/title/1/",
         "and the page it was read off, so a reader can check it")
    s.eq(back["works"][1]["volumes"], [], "a work with none renders an empty list")
    s.eq(back["works"][1]["notes"], ["the platform lists no volume"],
         "and the reason it is empty, which is the difference between silence and a gap")

    # A note is rendered as a LIST. It used to be repeated `note:` keys, which YAML collapses to
    # the last one, so every reason but one disappeared on the way back in.
    s.check(isinstance(back["works"][1]["notes"], list), "notes survive as a list, not a last-wins key")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
