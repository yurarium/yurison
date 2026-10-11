#!/usr/bin/env python3
"""importdates.py: telling a back-catalogue import from a day's publishing."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import importdates as im  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/importdates.py"]


def work(title, *pairs):
    return {"work_title": title,
            "chapters": [{"title": t, "updated": d} for t, d in pairs]}


def main(s):
    # ONE SERIES IMPORTED ON ITS OWN. §4's shape: one work contributing several entries at one
    # instant, while everything around it publishes normally.
    one = [work("imported", *[(str(k), "2025-08-08") for k in range(6)]),
           work("normal", ("1", "2025-08-01"), ("2", "2025-08-08"))]
    got = im.stamps(one)
    s.check(("imported", "2025-08-08") in got,
            "a back catalogue arriving from one work on one date is a stamp")
    s.check(("normal", "2025-08-08") not in got,
            "and a work publishing one chapter that day is not caught by its neighbour")

    # A WHOLE PLATFORM MIGRATING. Most works arrive with a back catalogue, and the point of the
    # platform-wide rule is the straggler: a work that put only one chapter on the migration date
    # is still an import, and the per-work rule alone would let it through.
    wide = [work(f"w{i}", *[("c%d" % k, "2025-08-08") for k in range(6)],
                 *[("new", "2026-01-%02d" % (i + 1))]) for i in range(7)]
    wide.append(work("straggler", ("only", "2025-08-08"), ("new", "2026-02-02")))
    got = im.stamps(wide)
    s.eq(len([g for g in got if g[1] == "2025-08-08"]), 8,
         "every work on a migration date is stamped, however little it contributed")
    s.check(("straggler", "2025-08-08") in got,
            "including the one the per-work rule could never have caught")
    s.check(("w0", "2026-01-01") not in got, "and its own real date is left alone")

    # THE COUNTER-CASE, tested before believing the rule. A platform where many works publish on
    # the same day every week is a schedule, and no amount of works sharing it makes it an import,
    # so long as no single date swallows the source.
    weekly = []
    for i in range(8):
        weekly.append(work(f"w{i}", *[("c%d" % k, "2026-0%d-06" % (k + 1)) for k in range(4)]))
    s.eq(im.platform_wide(weekly), set(),
         "a shared weekly slot is a schedule: nobody puts two instalments on it")

    # THE STRAGGLER IS THE POINT, and a median missed it. Half of 一迅プラス's works contributed one
    # or two chapters to its migration, so a threshold on the middle work excluded the whole event.
    # ハロー、メランコリック! ended in 2021 and has a single chapter on that date, and that one
    # chapter was setting the work's latest to 2025.
    migration = [work(f"w{i}", *[("c%d" % k, "2025-08-08") for k in range(4)]) for i in range(5)]
    migration += [work(f"s{i}", ("only", "2025-08-08")) for i in range(4)]
    got = im.stamps(migration)
    s.check(("s0", "2025-08-08") in got,
            "a work contributing one chapter to a migration is stamped with the rest")

    # A BUSY DAY THAT CONTINUES ITS RUNS IS A PUBLICATION. マガポケ's 2026-10-08: four works, two of
    # them posting two chapters, so the day has an import's shape; but アイ・ヘイ・チュー's 【第6話】
    # follows the 第1話 to 第5話 already dated, which no import does.
    busy = [work("aihei", *[("【第%d話】" % k, "2026-0%d-09" % (k + 5)) for k in range(1, 5)],
                 ("【第6話】今に木阿弥", "2026-10-08")),
            work("kaiju", ("【第3話】", "2026-09-09"), ("【第4話(1)】", "2026-10-08"),
                 ("【第4話(2)】 前編", "2026-10-08")),
            work("launch", ("【第1話】", "2026-10-08"), ("【第2話】", "2026-10-08")),
            work("one", ("【一膳目】", "2026-10-08"))]
    s.check("2026-10-08" in im.platform_wide(busy), "the busy day still has an import's shape")
    busy_got = im.stamps(busy)
    s.check(("aihei", "2026-10-08") not in busy_got, "a chapter continuing its run is a publication")
    s.check(("kaiju", "2026-10-08") not in busy_got, "and so is a two-part instalment that continues it")
    s.check(("launch", "2026-10-08") in busy_got,
            "a work with nothing earlier is left to the day's shape, as before")
    s.check(("one", "2026-10-08") in busy_got, "and so is one whose title states no number")

    # THE COUNTER-CASES CONTINUITY MUST NOT EXCUSE. A back catalogue filled in behind chapters
    # already held is numbered BEFORE them; and a late load of the rest of a run continues the
    # numbering, which is what the per-work test is for and why it is not excused.
    filled = [work("behind", ("第10話", "2025-01-01"), *[("第%d話" % k, "2025-08-08") for k in (1, 2)])]
    filled += [work(f"w{i}", *[("c%d" % k, "2025-08-08") for k in range(3)]) for i in range(4)]
    s.check(("behind", "2025-08-08") in im.stamps(filled),
            "chapters numbered before the ones already held are an import")
    late = [work("rest", ("第1話", "2024-01-01"), *[("第%d話" % k, "2025-08-08") for k in range(2, 9)])]
    s.check(("rest", "2025-08-08") in im.stamps(late),
            "and seven chapters continuing a run on one day are still caught by the per-work test")
    s.eq(im._number("【ｔｒａｃｋ１４】"), None, "full-width letters are not read as a marker")
    s.eq(im._number("第１２話"), 12, "full-width digits are")
    s.eq(im._number("コミックス第2巻発売記念イラスト"), None, "and a volume is not an instalment")
    catchup = [work("caught", ("第59話", "2025-11-18"), *[("第%d話" % k, "2026-04-09") for k in (60, 61, 62)])]
    catchup += [work(f"w{i}", *[("c%d" % k, "2026-04-09") for k in range(2)]) for i in range(4)]
    s.check(("caught", "2026-04-09") in im.stamps(catchup),
            "three instalments at once after months of nothing is a platform catching up")
    s.eq(len([g for g in got if g[1] == "2025-08-08"]), 9, "all nine of them")

    # An ordinary busy day is not a migration: a few works, mostly one instalment each. Measured on
    # コミックDAYS 2026-05-17, which is 6 works and 17% multiple.
    busy = [work(f"b{i}", ("one", "2026-05-17")) for i in range(5)]
    busy.append(work("b5", ("a", "2026-05-17"), ("b", "2026-05-17")))
    s.eq(im.platform_wide(busy), set(), "one work publishing twice does not make a migration")

    # THE COUNTER-CASE THAT SHIPPED BROKEN. GigaViewer splits one instalment across entries
    # published together, so a monthly series puts three rows on its release day. Counting rows
    # made every ordinary update look like an import and filed きみが死ぬまで恋をしたい, which
    # updates monthly, as dormant. Quoted from that work's コミックDAYS feed.
    split = [work("きみが死ぬまで恋をしたい",
                  ("第23話 わたしのままで(3)", "2022-03-17"),
                  ("第23話 わたしのままで(2)", "2022-03-17"),
                  ("第23話 わたしのままで(1)", "2022-03-17"),
                  ("第24話 ここにいるよ(2)", "2022-04-17"),
                  ("第24話 ここにいるよ(1)", "2022-04-17"))]
    s.eq(im.stamps(split), set(),
         "an instalment split across entries is one release, not a run of three")
    # And the same work's real import is still caught, because those are distinct instalments.
    dump = [work("きみが死ぬまで恋をしたい",
                 *[(f"第{k}話 なにか({p})", "2021-06-09") for k in range(1, 7) for p in (1, 2)])]
    s.check(("きみが死ぬまで恋をしたい", "2021-06-09") in im.stamps(dump),
            "while six instalments arriving at once still reads as a back catalogue")

    # A source with nothing in it decides nothing.
    s.eq(im.stamps([]), set(), "no works, no stamps")
    s.eq(im.platform_wide([work("empty")]), set(), "and no dated chapters, no stamps")
    s.eq(im.stamps([work("solo", ("1", "2026-01-01"), ("2", "2026-02-01"))]), set(),
         "a work publishing on its own dates is never a stamp")

    # THE REAL CASE, from the file this was written for. Shortened, keeping the proportions:
    # 2025-08-08 carries most of the source across many series, and recent chapters are genuine.
    ichi = [work("ゆるゆり", *[("%d" % k, "2025-08-08") for k in range(8)]),
            work("大室家", *[("%d" % k, "2025-08-08") for k in range(7)]),
            work("彩純ちゃん", ("1", "2025-08-08"), ("2", "2025-08-08"),
                 ("33", "2026-04-17"), ("34", "2026-06-17"))]
    got = im.stamps(ichi)
    s.check(("ゆるゆり", "2025-08-08") in got, "the migration date is a stamp")
    s.check(("彩純ちゃん", "2026-06-17") not in got,
            "and a chapter published after the migration keeps its date")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
