#!/usr/bin/env python3
"""nicovideo/releases.py: dates from meta_info, or none at all.

COVERS = ['adapters/nicovideo/releases.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as nv


def main(s):
    s.eq(nv.iso(2026, 8, 3), "2026-08-03", "single digits are padded, so dates sort as strings")
    s.eq(nv.iso("2026", "12", "31"), "2026-12-31", "strings are accepted")

    page = '<div class="meta_info">2026年8月3日更新 / 2025年1月5日開始</div>'
    got = nv.parse(page)
    s.eq(got.get("updated"), "2026-08-03", "the update date is read")
    s.eq(got.get("started"), "2025-01-05", "the start date is read")

    # A missing block means NO date. §6: a guessed date is worse than none, because it silently
    # reorders the feed and nothing downstream can tell it was invented.
    s.check(nv.parse("<html>no meta_info here</html>") is None,
            "an absent block yields None rather than a guess")

    partial = nv.parse('<div class="meta_info">2026年8月3日更新</div>')
    s.eq(partial.get("updated"), "2026-08-03", "an update date alone is read")
    s.check("started" not in partial, "and no start date is invented")

    unparsable = nv.parse('<div class="meta_info">近日公開</div>')
    s.check(not (unparsable or {}).get("updated"), "text without a date yields no date")

    # Tags inside the block must not break the date, since the markup carries links and spans.
    tagged = nv.parse('<div class="meta_info"><span>2026年8月3日更新</span></div>')
    s.eq((tagged or {}).get("updated"), "2026-08-03", "markup inside the block is stripped first")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "nicovideo.releases"))
