#!/usr/bin/env python3
"""acceptance: what a coverage floor does when there was no measurement to compare.

COVERS = ['adapters/acceptance.py']

THE FAULT THIS IS FOR. `max(adj_w, 1)` turned 0/0 into 0.0%, so a run that read no listing at all
reported the same number as a run whose coverage had collapsed, and failed the floor in the same
words. Every CI run has been in the first state: the runner never read Web漫画アンテナ, and the pass
that fills its cache reported a clean zero because its own health check sat below an early break.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import acceptance                                                       # noqa: E402


def main(s):
    floors = acceptance.FLOORS
    s.check(floors, "there are floors to compare against")
    name = next(iter(floors))
    floor = floors[name]

    s.eq(acceptance._assert_floors({**{k: 100.0 for k in floors}}), [],
         "every measure above its floor is a pass")

    below = {k: 100.0 for k in floors}
    below[name] = floor - 1
    got = acceptance._assert_floors(below)
    s.eq(len(got), 1, "a measure below its floor is a failure")
    s.check("below the floor" in got[0], "and says so in those words")

    # NOT MEASURED IS NOT A FAILURE. There is nothing to compare, and calling it 0% would say
    # coverage collapsed when the listing was never read. The pass prints why, loudly.
    unmeasured = {k: 100.0 for k in floors}
    unmeasured[name] = None
    s.eq(acceptance._assert_floors(unmeasured), [],
         "a measure that could not be taken does not fail a floor")

    # AND A MEASURE THE PASS NEVER RECORDED IS STILL A FAILURE, which is what tells the two apart:
    # `None` is a pass that looked and found no input, absence is a pass that did not look.
    missing = {k: 100.0 for k in floors}
    del missing[name]
    got2 = acceptance._assert_floors(missing)
    s.eq(len(got2), 1, "a measure the pass forgot entirely is a failure")
    s.check("no value at all" in got2[0], "and is not confused with one that reported nothing")

    # THE INVERTED RUN MUST STILL FAIL, or the floors are not being compared at all. With one
    # measure unmeasurable, the other is what carries the proof; with both unmeasurable there is
    # no proof and `--canary` reports VACUOUS rather than passing.
    raised = {k: 100.1 for k in floors}
    s.check(acceptance._assert_floors({**unmeasured, **{}}) == []
            and len(acceptance._assert_floors({k: 0.0 for k in raised})) == len(floors),
            "with every measure taken and every floor raised, every one of them fails")


    # A LISTING READ LONG BEFORE THE FEED'S LAST DAY IS NOT A MEASUREMENT, which is what a local
    # cache from 2026-08-10 produced on 2026-10-08: 75% over eight edge cases. Ages from real files.
    import datetime, os, tempfile, time
    d_hi = datetime.date(2026, 10, 9)
    with tempfile.TemporaryDirectory() as d:
        fresh, old = pathlib.Path(d) / "page1.html", pathlib.Path(d) / "page2.html"
        for f in (fresh, old):
            f.write_text("x", encoding="utf-8")
        day = lambda dt: time.mktime(datetime.datetime.combine(dt, datetime.time(12)).timetuple())
        os.utime(fresh, (day(d_hi), day(d_hi)))
        os.utime(old, (day(datetime.date(2026, 8, 10)),) * 2)
        s.eq(acceptance.listing_age([old], d_hi), 60, "a page read on 2026-08-10 is 60 days old")
        s.check(acceptance.listing_age([old], d_hi) > acceptance.LISTING_MAX_AGE_DAYS,
                "and too old to measure against")
        s.eq(acceptance.listing_age([old, fresh], d_hi), 0,
             "the newest page decides, since a run rewrites them together")
        s.eq(acceptance.listing_age([], d_hi), None, "no pages is no age, which is the other branch")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "acceptance-floors"))
