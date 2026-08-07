#!/usr/bin/env python3
"""comicfuz/releases.py: four access states, not two.

COVERS = ['adapters/comicfuz/releases.py']

This adapter once collapsed FUZ's four states into two and reported the platform at 14% free when
most of it can be read for nothing by anyone taking a chapter a day. The mistake was reading an
unlabelled chapter as paid; unlabelled is in fact the free-over-time state, and it is the majority.
Each state is pinned here so the collapse cannot recur.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as fz


def main(s):
    # Free: the platform says so with an empty pointConsumption.
    modes, note, adv = fz.access_of({"pointConsumption": {}})
    s.eq(modes, ["free"], "an empty pointConsumption is free")
    s.check(not adv, "and is not running ahead of the free line")

    modes, _, _ = fz.access_of({})
    s.eq(modes, ["free"], "a missing pointConsumption is free too")

    # THE ONE THAT WAS WRONG. An amount with no badge is a チャージ chapter: one per series per day,
    # costing nothing. 2,067 of 2,421 chapters held here are this state.
    modes, note, adv = fz.access_of({"pointConsumption": {"amount": 30, "type": 2}})
    s.eq(modes, ["free-timed"], "an amount with NO badge is a charge chapter, readable free")
    s.check("チャージ" in (note or ""), "and the note names the mechanism")
    s.check(not adv, "a charge chapter is not paid-early")

    # Badged means it costs money today. Two kinds, distinguished by whether it has an end.
    modes, note, adv = fz.access_of(
        {"pointConsumption": {"amount": 30, "type": 1}, "badge": {"x": 1}})
    s.eq(modes, ["purchase"], "a badged chapter is a purchase")
    s.check(adv, "type 1 is 先行, paid now and free from its stated date")
    s.check("先行" in (note or ""), "and the note says so")

    modes, note, adv = fz.access_of(
        {"pointConsumption": {"amount": 50, "type": 2}, "badge": {"x": 1}})
    s.eq(modes, ["purchase"], "a badged coin chapter is a purchase")
    s.check(not adv, "type 2 has no free-from date, so it is not paid-early")

    # Anything unrecognised must say so rather than being folded into a neighbour.
    modes, note, _ = fz.access_of({"pointConsumption": {"something": "new"}})
    s.eq(modes, ["unknown"], "an unrecognised shape is unknown, not guessed")
    s.check("unrecognised" in (note or ""), "and carries the shape it could not read")

    s.eq(fz.iso("2026/8/3"), "2026-08-03", "a slashed date is normalised and padded")

    # A REFRESH MAY NOT REMOVE A WORK (REQUIREMENTS §4). THE BUG THIS PINS: targets come from the
    # gap report, which lists only works reachable nowhere else watched, so a work that becomes
    # reachable elsewhere leaves the gap file and then leaves data/source. A run meant to add 42
    # discovered works removed 24 held ones, 恋する小惑星 and アネモネは熱を帯びる among them.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "works.yaml"
        f.write_text('works:\n'
                     '  - work_title: "held"\n    url: "https://comic-fuz.com/manga/1"\n'
                     '  - work_title: "refetched"\n    url: "https://comic-fuz.com/manga/2"\n')
        kept = fz.carry_over(f, {"https://comic-fuz.com/manga/2"})
        s.eq([w["work_title"] for w in kept], ["held"],
             "a work this run did not target is kept")
        s.eq(fz.carry_over(f, {"https://comic-fuz.com/manga/1",
                               "https://comic-fuz.com/manga/2"}), [],
             "and a work it did resolve is replaced rather than duplicated")
    s.eq(fz.carry_over(pathlib.Path(d) / "gone.yaml", set()), [],
         "a first run with no file to carry from keeps nothing and does not raise")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "comicfuz.releases"))
