#!/usr/bin/env python3
"""render/releases.py: badges, and the one that means "you can read this now".

COVERS = ['adapters/render/releases.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as rd


def main(s):
    # THREE BADGES, NOT TWO. マガポケ marks a chapter --free, --point, or --ticket-free, the last
    # meaning readable now by spending a ticket the platform hands out. It was invisible twice
    # over: the capture was (\w+) and '-' is not a word character, so --ticket-free captured as
    # "ticket"; and anything not exactly "free" was called purchase. The one state meaning "you
    # can read this right now" was recorded as the one meaning you cannot.
    s.check("ticket-free" in rd.ACCESS_BADGE or "ticket" in rd.ACCESS_BADGE,
            "the ticket badge is in the map at all")
    tick = rd.ACCESS_BADGE.get("ticket-free") or rd.ACCESS_BADGE.get("ticket")
    s.eq(tick, ["free-timed"], "a ticket chapter is free-timed, never purchase")
    s.eq(rd.ACCESS_BADGE.get("free"), ["free"], "a free badge is free")

    spec = {"item": r'(?=<li class="ep")',
            "date": r'data-date="(\d{4}-\d{2}-\d{2})"',
            "title": r'class="t">([^<]+)<',
            "free_marker": r"is-free"}
    page = ('<li class="ep" data-date="2026-08-03"><span class="t">第1話</span><i class="is-free">'
            '</i></li>'
            '<li class="ep" data-date="2026-08-10"><span class="t">第2話</span></li>')
    rows = rd.episodes_structured(page, spec)
    s.eq(len(rows), 2, "both items are read")
    if len(rows) == 2:
        s.eq(rows[0]["title"], "第1話", "the title is taken from the spec's group")
        s.eq(rows[0]["updated"], "2026-08-03", "the date is normalised")
        s.eq(rows[0]["access_modes"], ["free"], "the free marker is presence-based")
        s.eq(rows[1]["access_modes"], ["purchase"], "its absence is the other state")

    # An item missing either half is skipped rather than half-recorded, because a row with a title
    # and no date reorders the feed and a row with a date and no title says nothing.
    s.eq(rd.episodes_structured('<li class="ep" data-date="2026-08-03"></li>', spec), [],
         "an item with no title is skipped")
    s.eq(rd.episodes_structured('<li class="ep"><span class="t">第1話</span></li>', spec), [],
         "an item with no date is skipped")
    s.eq(rd.episodes_structured("", spec), [], "an empty page yields nothing")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "render.releases"))
