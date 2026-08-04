#!/usr/bin/env python3
"""comparators/completion.py: which listing rows count as a completion claim, and which do not."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import testkit  # noqa: E402
import completion as c  # noqa: E402

COVERS = ["adapters/comparators/completion.py"]


def row(title, tags, site="P", url="https://x/1"):
    return ('<div class="entry">'
            f'<div class="entry-title ellipsis1"><a href="{url}" target="_blank">{title}</a></div>'
            f'<div class="entry-site"><a href="/p">{site}</a></div>'
            f'<span class="hover-tip-popup-block">{",".join(tags)}</span>')


def main(s):
    page = row("A", ["百合", "完結"]) + row("B", ["百合", "女子高生"])
    got = c.entries(page)
    s.eq(len(got), 2, "one row per entry, split on the same boundary coverage.py uses")
    s.eq(got[0]["tags"], ["百合", "完結"], "tags are split and unescaped")

    fin = c.finished([(page, "2026-08-01")])
    s.eq(sorted(v["work"] for v in fin.values()), ["A"], "only a row tagged 完結 is claimed")
    s.eq(fin[c.textnorm.norm("A")]["seen"], "2026-08-01", "the snapshot's date rides with it")

    # A WORK DOES NOT UN-FINISH, so an older snapshot still counts and the newest sighting wins.
    older = row("A", ["百合", "完結"])
    fin2 = c.finished([(older, "2025-01-01"), (page, "2026-08-01")])
    s.eq(len(fin2), 1, "the same work across two snapshots is one claim")
    s.eq(fin2[c.textnorm.norm("A")]["seen"], "2026-08-01", "and carries the most recent sighting")

    # Keyed on the comparison form, so two spellings of one title do not become two claims.
    two = row("あの子と ふたりで。", ["完結"]) + row("あの子とふたりで。", ["完結"])
    s.eq(len(c.finished([(two, "2026-08-01")])), 1,
         "spacing is presentation, so one work is one claim")

    s.eq(c.finished([]), {}, "no snapshots is no claims, not a crash")
    s.eq(c.finished([("<html>nothing</html>", "2026-08-01")]), {},
         "a page with no entries claims nothing")
    s.eq(c.entries(row("C", [])), [{"title": "C", "url": "https://x/1", "platform": "P",
                                    "tags": []}],
         "a row with no tags parses and claims nothing")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
