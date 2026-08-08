#!/usr/bin/env python3
"""comicfuz/releases.py: four access states, not two.

COVERS = ['adapters/comicfuz/releases.py']

This adapter once collapsed FUZ's four states into two and reported the platform at 14% free when
most of it can be read for nothing by anyone taking a chapter a day. The mistake was reading an
unlabelled chapter as paid; unlabelled is in fact the free-over-time state, and it is the majority.
Each state is pinned here so the collapse cannot recur.

THE STATES ARE PINNED TWICE, and the second time is the one that counts. The dicts written out
below state the rule and are worth reading side by side. The chapters read out of
`data/fixtures/comicfuz/` are four real records off 球詠's page, one per state, and they carry two
fields the written-out versions got wrong.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fixtures
import testkit
import releases as fz


def chapters_of(fixture):
    """Every chapter on a captured work page, by id."""
    pp = fz.page_props(fixtures.load(fixture))
    return {c["chapterId"]: c for g in pp["chapters"] for c in g["chapters"]}


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

    # ── the same four states, read off a real page ────────────────────────────────────────────
    #
    # 球詠 carries 228 chapters in 19 volume groups. The fixture keeps one chapter of each state,
    # named by its own chapterId rather than by position: the 先行 chapters are the newest and the
    # free ones the oldest, so any sampling by position keeps one state and loses the rest.
    ch = chapters_of("comicfuz/work-with-four-access-states")
    s.eq(len(ch), 4, "four chapters, one per access state")

    # THE PAYLOAD IS FOUND IN THE PAGE, not handed to the parser. FUZ embeds the whole chapter
    # list in `<script id="__NEXT_DATA__" type="application/json">`, and nothing above this line
    # exercises the extraction that has to find it.
    s.check(fz.page_props("<html>no next data here</html>") is None,
            "a page with no payload yields None rather than raising")

    modes, note, adv = fz.access_of(ch[2933])
    s.eq(modes, ["free"], "2933 states an empty pointConsumption and is free")

    # THE ONE THAT WAS WRONG, as the platform really writes it. The dict written out above gave
    # this state a `type`. The real record has NO type key at all: `{"amount": 30}` and nothing
    # else, with no badge. So the state is recognised by what is ABSENT, twice over, which is why
    # it read as paid to somebody looking at the page for a label.
    real_charge = ch[47947]
    s.eq(real_charge["pointConsumption"], {"amount": 30},
         "a charge chapter states an amount and no type")
    s.check("badge" not in real_charge, "and carries no badge key")
    modes, note, adv = fz.access_of(real_charge)
    s.eq(modes, ["free-timed"], "which is the チャージ state, readable free")
    s.check(not adv, "and is not paid-early")

    modes, note, adv = fz.access_of(ch[53783])
    s.eq(modes, ["purchase"], "53783 is badged, so it costs money today")
    s.check(adv, "and its type 1 says 先行")
    s.eq(fz.iso(ch[53783]["updatedDate"]), "2027-01-01",
         "the date on a 先行 chapter is when it stops costing points, and it is in the future")

    # A PURCHASE MAY STATE NO DATE AT ALL, which nothing written by hand had shown. 76444 is a
    # badged type 2 coin chapter and carries no `updatedDate` key, so the row built from it has an
    # empty `when` and is not a chapter with a date of 1970 or of today.
    s.check("updatedDate" not in ch[76444], "76444 states no date")
    s.eq(fz.iso(ch[76444].get("updatedDate")), "", "and iso answers with nothing rather than a guess")
    modes, note, adv = fz.access_of(ch[76444])
    s.eq(modes, ["purchase"], "it is still a purchase")
    s.check(not adv, "with no free-from date, so it is not paid-early")

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

    # A TARGET MUST CARRY THE ADDRESS THAT WILL BE FETCHED. FUZ serves one page under two
    # spellings and resolved.yaml records ぬるめた at /series/2389, which is the address the search
    # confirmed. The rewrite used to decide whether a row was a target and then the untouched row
    # was fetched, so /series/2389 was requested, answered 404, and the work was dropped from the
    # capture with nothing recorded. /manga/2389 answers 200 with 75 chapters.
    got = fz.fuz_targets([{"title": "ぬるめた", "url": "https://comic-fuz.com/series/2389"}])
    s.eq([w["url"] for w in got], ["https://comic-fuz.com/manga/2389"],
         "a /series/ target is fetched as /manga/, not merely recognised as one")
    s.eq([w["title"] for w in got], ["ぬるめた"], "and the rest of the row is carried through")

    # The counter-cases. One work named both ways is one target, and a row for another platform is
    # none at all.
    both = fz.fuz_targets([{"title": "x", "url": "https://comic-fuz.com/series/2389"},
                           {"title": "x", "url": "https://comic-fuz.com/manga/2389"}])
    s.eq(len(both), 1, "the two spellings of one work are one target, not two fetches")
    s.eq(fz.fuz_targets([{"title": "y", "url": "https://manga.nicovideo.jp/comic/54233"}]), [],
         "a row naming another platform is not a FUZ target")
    s.eq(fz.fuz_targets([{"title": "z"}]), [],
         "a row stating no address at all is skipped and does not raise")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "comicfuz.releases"))
