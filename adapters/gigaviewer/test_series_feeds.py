#!/usr/bin/env python3
"""series_feeds.py: reading a per-series Atom feed, and the id it is fetched by.

COVERS = ['adapters/gigaviewer/series_feeds.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fixtures
import testkit
import releases
import series_feeds as sf


def main(s):
    # ── two real feeds ────────────────────────────────────────────────────────────────────────
    #
    # Both come out of the series-feed cache with their addresses and retrieval dates recorded.
    # Their subtitles are cut, because a subtitle is the publisher's synopsis and REQUIREMENTS §2
    # forbids storing one; nothing here reads it.
    ordinary = fixtures.load("gigaviewer/series-feed-ordinary")
    bracketed = fixtures.load("gigaviewer/series-feed-platform-named-in-brackets")

    # The feed states its own series name, which is why a misattributed id can be caught. The id is
    # read positionally off a thumbnail URL, and that pairing has been wrong: 夕子先輩は育てられない
    # took on its neighbour's six chapters.
    # The real shape is 一迅プラス（大室家）: platform outside, series inside the brackets. Only the
    # inner part identifies the work, and a title without brackets identifies nothing, so it
    # returns None instead of handing back the platform name as though it were a series.
    s.eq(sf.feed_series_name(ordinary), "大室家",
         "the series name is taken from inside the brackets")
    s.check(sf.feed_series_name("<title>一迅プラス</title>") is None,
            "a title with no bracketed series yields None, not the platform name")
    s.check(sf.feed_series_name("<feed></feed>") is None,
            "a feed without a title yields None rather than raising")

    # THE PLATFORM WHOSE OWN NAME CONTAINS BRACKETS. A greedy match spanned from the first opener
    # to the last closer, so 23 COMIC OGYAAA!! series were named after the platform and its
    # tagline with the real title trapped at the end. Four of them reached the published database.
    #
    # The whole title is here rather than paraphrased, because the fault is in the punctuation:
    # COMIC OGYAAA!! (コミックオギャー)｜おもしろい、がうまれるところ（あの子は優しすぎる。）
    s.eq(sf.feed_series_name(bracketed), "あの子は優しすぎる。",
         "the series is the LAST bracket group, not everything between the first and the last")
    s.check("(コミックオギャー)" in bracketed,
            "the earlier bracket group the greedy match ran from is still in this fixture")

    # The counter-case that rules out the obvious fix. A non-greedy pattern solves the above and
    # breaks this instead, returning the inner group; counting depth from the end handles both.
    s.eq(sf.last_bracketed("X（あの子（仮））"), "あの子（仮）",
         "a series title containing brackets survives whole")
    s.eq(sf.last_bracketed("一迅プラス（大室家）"), "大室家", "the ordinary one-group case still works")
    s.check(sf.last_bracketed("一迅プラス") is None, "no brackets means no name")
    s.check(sf.last_bracketed("stray ) closer") is None,
            "a closer with no opener claims nothing rather than guessing")

    # ── entries, and the day they land on ─────────────────────────────────────────────────────
    #
    # The fixture holds the two newest of 大室家's 136 entries. Its stamps are why `jst_date`
    # exists: 一迅プラス publishes at 15:00:00Z, which is midnight in Tokyo on the following day,
    # so every chapter of this series is filed a day early by anything reading the UTC date. That
    # is a real publishing schedule and not a boundary chosen to make a test interesting.
    eps = sf.episodes(ordinary)
    s.eq(len(eps), 2, "both entries are read")
    if len(eps) == 2:
        s.eq(eps[0]["title"], "第136話", "titles come from the entry")
        s.check(all(e.get("url") for e in eps), "every entry carries its own URL")
        s.check("2026-07-15T15:00:00Z" in ordinary, "the feed really does stamp 15:00 UTC")
        # Dates are platform-attested here, not heuristic, so they must survive exactly.
        s.eq(eps[0]["updated"], "2026-07-16",
             "15:00 UTC is the next day in Tokyo, and the feed is dated in JST")
        s.eq(eps[1]["updated"], "2026-06-17", "and the entry before it lands a month earlier")

    # THE OTHER PLATFORM PUBLISHES AT 03:00Z, which is noon in Tokyo on the SAME day. Two feeds
    # rather than one, because a conversion that simply added a day would pass against 一迅プラス
    # alone.
    other = sf.episodes(bracketed)
    s.check("2024-08-23T03:00:00Z" in bracketed, "COMIC OGYAAA!! stamps 03:00 UTC")
    s.eq(other[0]["updated"], "2024-08-23", "which is the same day in Tokyo, not the next one")

    s.eq(sf.episodes("<feed></feed>"), [], "an empty feed yields no episodes")

    # JST conversion is the same fact as in releases.py, and both must agree.
    s.eq(sf.jst_date("2026-08-03T15:00:00Z"), "2026-08-04", "the boundary is 15:00 UTC")
    s.eq(sf.jst_date("2026-08-03T14:59:59Z"), "2026-08-03", "one second earlier is the day before")

    # Normalisation is used to compare the listing's name against the feed's.
    s.eq(sf.norm("ＹＵＲＩ"), sf.norm("yuri"), "width and case fold for the comparison")

    # ── the listing, and the pairing that was off by one ──────────────────────────────────────
    #
    # The series id is not an attribute anywhere on the listing. It appears once per series, inside
    # the percent-encoded thumbnail address, so the pairing is positional and this is where it went
    # wrong: 163 of 一迅プラス's 164 works took the NEXT series' id, because a block names itself
    # again on its 1話へ and 最新話へ buttons and those sit after the thumbnail.
    #
    # The three blocks are consecutive entries off the real page, kept whole so the buttons are
    # still in them. Cut to the thumbnail anchors alone the fixture would pass the broken reader.
    listing = fixtures.load("gigaviewer/series-listing")
    ids = sf.series_ids(listing)
    s.eq(ids, {"君のせいなんだから、責任とってよね。": "2551460909791966658",
               "たゆたう恋の散り際に": "2551460909671366556",
               "超深宇宙より愛をこめて": "2550912965923183753"},
         "each series takes the id out of its own block's thumbnail")

    # THE COUNTER-CASE, PINNED RATHER THAN DESCRIBED. If the buttons ever stop repeating the name,
    # the assertion above starts passing for a reader that scans across blocks, and this is what
    # says so.
    s.eq(listing.count('data-series-name="たゆたう恋の散り際に"'), 3,
         "a block names its series three times, twice after the thumbnail it belongs to")
    s.check(listing.index("2551460909791966658") < listing.index("series-series-first")
            < listing.index("2551460909671366556"),
            "the first block's thumbnail, then its buttons, then the next block's thumbnail: the "
            "order that let a scan pair a name with the following series")

    # 一迅プラス's SECOND ENTRY IS THE ONE THAT WENT MISSING. Under the old pairing there was no id
    # left for it: every name from the second on had taken its neighbour's, so たゆたう恋の散り際に
    # was never fetched and carry_over went on serving an older run's chapters for it. That is why
    # the fixture starts at the top of the listing.
    s.check("たゆたう恋の散り際に" in ids, "the second entry resolves, which it did not before")

    # THE OTHER READER OF THIS PAGE MUST FIND THE SAME SERIES. releases.yuri_series splits on
    # series_feeds.SERIES_BLOCK and reads title, author and genre out of each block; series_ids
    # reads the name and the id. Two readers of one page disagreeing by one entry is exactly the
    # fault above, so they are compared here rather than trusted to stay in step.
    s.eq(sorted(releases.yuri_series(listing, "百合", "コミック百合姫")), sorted(ids),
         "both readers of the listing name the same series")

    s.check(len(sf.series_ids("<html>nothing</html>")) == 0,
            "a page with no thumbnails yields no ids rather than raising")

    # A NARROWER RUN MUST NOT DELETE THE WIDER ONE'S WORK. Probing 26 dormant works rewrote
    # comic-days from 109 series to 13 and tonarinoyj from 84 to 2, because the writer replaced the
    # whole file with whatever that run resolved.
    import pathlib as _pl, tempfile
    with tempfile.TemporaryDirectory() as d:
        f = _pl.Path(d) / "p-series-feeds.yaml"
        f.write_text('works:\n'
                     '  - work_title: "kept"\n    series_id: "111"\n    chapters: []\n'
                     '  - work_title: "refetched"\n    series_id: "222"\n    chapters: []\n')
        got = sf.carry_over(f, ["222"])
        s.eq([w["work_title"] for w in got], ["kept"],
             "a series this run did not resolve is kept, because not fetching is not a finding")
        s.eq(got[0]["episodes"], [], "and comes back in the shape the writer takes")
        s.eq(sf.carry_over(f, [111, 222]), [],
             "the id is compared as text, so a number resolves the same series as a string")
        s.eq(sf.carry_over(_pl.Path(d) / "absent.yaml", []), [],
             "a platform with no file yet carries nothing over")


    # THE BANNER IS ABOUT THE SERIES; THE BUTTON IS ABOUT THE CHAPTER. 一迅プラス prints
    # 「作品チケット対象です」 on every chapter page of a series it runs tickets on, so matching that
    # answered "readable on a ticket" for chapters that cost points: 映しちゃダメな顔 reported 19 of
    # them where all 19 are point purchases and a reader can open two.
    s.check(sf.TICKET_RE.search("チケットで読む（無料）"),
            "the button on a chapter is what says that chapter is ticket-readable")
    s.check(not sf.TICKET_RE.search("この作品は作品チケット対象です"),
            "and a statement about the series is not evidence about any chapter of it")
    s.check(not sf.TICKET_RE.search("80ptで購入して読む"), "a price is not a ticket")

if __name__ == "__main__":
    sys.exit(testkit.run(main, "series_feeds"))
