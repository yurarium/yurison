#!/usr/bin/env python3
"""feedgap.py: which feed rows name a work the database does not hold.

COVERS = ['adapters/feedgap.py']

EVERY ROW BELOW IS REAL. STANDING-INSTRUCTIONS §14b asks a check to fail on something the pipeline
can produce rather than on a canary planted past the filter that would have removed it, so the
titles here are copied out of `data/build/feed/` and `data/build/series.json` as they stood on
2026-08-07, spelling and spacing untouched.

The counter-cases are the point. Three works in the archived month are spelled one way in the feed
and another in the series file, and none of the three carries a `wid`, so a count taken from that
field would have reported all three as works we do not hold. They are held. A measure that read the
join's own output would have been wrong about them and right about nothing extra.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import feedgap
import testkit

# As `data/build/series.json` spells them.
SERIES = [
    {"work": "見えてますよ! 愛沢さん", "id": "w00114"},
    {"work": "伽藍の姫 -がらんのひめ-", "id": "w00203"},
    {"work": "アイ・ヘイ・チュー", "id": "w00149"},
    {"work": "球詠", "id": "w00026"},
]

# As `data/build/feed/` spells them. `wid` is carried exactly as the built files carry it: the
# archived month has none on any row, and the live feed has one wherever build.py's title match
# succeeded.
FEED = [
    # The five live rows this module was written for. No record under any spelling.
    {"work": "おちこぼれフルーツタルト", "plat": "nicovideo"},
    {"work": "フルボイス！", "plat": "nicovideo"},
    {"work": "わたしが恋人になれるわけないじゃん、ムリムリ！（※ムリじゃなかった!?）", "plat": "nicovideo"},
    {"work": "タイムトラベル少女 ～ミライのサキ～", "plat": "nicovideo"},
    {"work": "ぬるめた", "plat": "nicovideo"},
    # Held, spelled differently, and carrying no identifier in the archived month.
    {"work": "見えてますよ！愛沢さん", "plat": "nicovideo"},
    {"work": "伽藍の姫-がらんのひめ-", "plat": "pixivcomic"},
    {"work": "アイ・ヘイ・チュー!", "plat": "magapoke"},
    # Held and matched, as the live feed carries it.
    {"work": "球詠", "plat": "comic-fuz", "wid": "w00026"},
]


def main(s):
    bad = feedgap.unheld(FEED, SERIES)
    titles = [r["work"] for r in bad]

    s.eq(len(bad), 5, "the five live rows are the whole of what is missing")
    for want in ("おちこぼれフルーツタルト", "フルボイス！", "タイムトラベル少女 ～ミライのサキ～",
                 "ぬるめた"):
        s.check(want in titles, f"{want} is counted as a work we do not hold")

    # THE COUNTER-CASES. Each of these is held and each would fail a `wid` test.
    s.check("見えてますよ！愛沢さん" not in titles, "a fullwidth ！ and a space are not a missing work")
    s.check("伽藍の姫-がらんのひめ-" not in titles, "a space around a subtitle is not a missing work")
    s.check("アイ・ヘイ・チュー!" not in titles, "a trailing ! is not a missing work")

    # A row carrying no `wid` for a work we hold must not count, and a row carrying one for a work
    # we do not hold must still count. Neither answer may come from the field.
    s.eq(feedgap.unheld([{"work": "球詠", "plat": "comic-fuz"}], SERIES), [],
         "a held work with no wid on the row is held")
    s.eq(len(feedgap.unheld([{"work": "ぬるめた", "wid": "w99999"}], SERIES)), 1,
         "a wid pointing at no series row does not make a work held")

    # A row that states no work states no missing work either.
    s.eq(feedgap.unheld([{"work": "", "plat": "nicovideo"}, {"plat": "nicovideo"}], SERIES), [],
         "a row with no title is not a missing record")

    # Nothing held at all means every row is missing, which is the shape a lost series.json takes.
    s.eq(len(feedgap.unheld(FEED, [])), len(FEED), "an empty corpus holds none of the rows")
    s.eq(feedgap.unheld([], SERIES), [], "no rows, nothing missing")

    # `held` keeps the first identifier for a title rather than the last, so a duplicate title
    # cannot quietly retire the row that was already answering for it.
    h = feedgap.held([{"work": "球詠", "id": "w00026"}, {"work": "球詠", "id": "w09999"}])
    s.eq(h[feedgap.textnorm.norm("球詠")], "w00026", "the first row keeps the title")

    # Grouping. Two rows for one work are one work, and the count of rows is kept.
    grouped = feedgap.works(bad)
    s.eq(len(grouped), 5, "five rows, five distinct works")
    two = feedgap.works(FEED[:1] + FEED[:1])
    s.eq(two[0]["rows"], 2, "two rows for one work are counted as two rows")
    s.eq(len(two), 1, "and as one work")

    # A ruling is reporting, never filtering: joining one does not change what is counted.
    ruled = {feedgap.textnorm.norm("ぬるめた"): {"disposition": "in"}}
    s.eq(len(feedgap.works(bad, ruled)), 5, "a ruling removes nothing from the count")
    s.eq([e["disposition"] for e in feedgap.works(bad, ruled) if e["work"] == "ぬるめた"], ["in"],
         "the ruling is carried onto the work it is about")

    # An absent register is a legitimate state and not a crash (STANDING-INSTRUCTIONS §5).
    s.eq(feedgap.rulings("data/queue/no-such-file.yaml"), {}, "no register, no rulings")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "feedgap"))
