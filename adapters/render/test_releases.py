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

    # CARRY-OVER. --limit-per-host bounds a run; it must not bound the FILE. pixivコミック has 131
    # targets and a limit of 40, so overwriting cost 68 works and 291 chapters in one run, and 13
    # claims that had been attested went back to untraced.
    import tempfile, yaml as _yaml
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "rendered-x.yaml"
        f.write_text(_yaml.safe_dump({"works": [
            {"work_title": "A", "url": "u/1", "chapters": [{"title": "1", "updated": "2026-01-01"}]},
            {"work_title": "B", "url": "u/2", "chapters": [{"title": "1", "updated": "2026-01-02"}]},
        ]}, allow_unicode=True))
        kept = rd.carry_over(f, [{"url": "u/1"}])
        s.eq([w["url"] for w in kept], ["u/2"],
             "a work this run did not reach is kept")
        s.check(all(w["url"] != "u/1" for w in kept),
                "and a work it did reach is not carried over, so the fresh reading wins")
        s.eq(rd.carry_over(f, [{"url": "u/1"}, {"url": "u/2"}]), [],
             "a run that reached everything carries nothing over")
        s.eq(rd.carry_over(pathlib.Path(d) / "absent.yaml", [{"url": "u/1"}]), [],
             "a first run has nothing to carry over and does not fail")


    a_clean_read_is_recorded(s)


def a_clean_read_is_recorded(s):
    """Only failures reached the ledger, so success looked like never having looked.

    `checkstate.record` was called on `blocked` and on `empty` and nowhere else. `schedule.py` sorts
    by `overdue_days`, which returns None for a work with no row, and None sorts first as most
    overdue. So a work read cleanly every run was permanently the most overdue thing in the list:
    アイ・ヘイ・チュー published on 2026-08-07, was read without trouble, and was listed overdue on
    the 8th.
    """
    import sys as _s
    _s.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    import checkstate

    checks = {}
    checkstate.record(checks, "P", "read cleanly", "ok", when="2026-08-07")
    checkstate.record(checks, "P", "came back empty", "empty", when="2026-08-01")
    s.eq(checkstate.overdue_days(checks, "P", "read cleanly", __import__("datetime").date(2026, 8, 8)), 1,
         "a work read cleanly yesterday is one day since we looked")
    s.eq(checkstate.overdue_days(checks, "P", "came back empty", __import__("datetime").date(2026, 8, 8)), 7,
         "and one that failed a week ago is seven")
    s.eq(checkstate.overdue_days(checks, "P", "never seen", __import__("datetime").date(2026, 8, 8)), None,
         "a work with no row is None, which is what sorts first")
    s.check(checkstate.overdue_days(checks, "P", "read cleanly", __import__("datetime").date(2026, 8, 8))
            < checkstate.overdue_days(checks, "P", "came back empty", __import__("datetime").date(2026, 8, 8)),
            "so recording the clean read is what stops it outranking a real failure")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "render.releases"))
