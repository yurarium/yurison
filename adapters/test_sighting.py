#!/usr/bin/env python3
"""sighting: what the first-seen ledger remembers a release as, and how the old form migrates.

COVERS = ['adapters/sighting.py']

WHY THE MIGRATION IS THE SUBJECT. Changing a ledger key is changing what the pipeline believes it
has already seen, and getting it wrong in either direction reaches a reader the next morning: too
strict and every release becomes a sighting of today, so the whole corpus surfaces as news at once;
too loose and a genuine late discovery is filed months back where nobody looks. The cases here are
the three the corpus actually holds, and each is named.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sighting                                                         # noqa: E402
import testkit                                                          # noqa: E402

COVERS = ["adapters/sighting.py"]

#: The work whose four chapters this was written for, as the ledger holds it: under a truncated
#: title seeded on 2026-08-02, under the full title on 2026-08-04, and under both spellings of the
#: platform, because the attribution was corrected from チャンピオンクロス to ヤングチャンピオン.
LEDGER = {
    "公爵令嬢の籠絡ミッション魔王との政略結婚が人類最後の切り札ですって魔王が女の子の場合はどう|第9話1|チャンピオンクロス": "2026-08-02",
    "公爵令嬢の籠絡ミッション魔王との政略結婚が人類最後の切り札ですって魔王が女の子の場合はどうすればいいのですか|第9話1|チャンピオンクロス": "2026-08-04",
    "公爵令嬢の籠絡ミッション魔王との政略結婚が人類最後の切り札ですって魔王が女の子の場合はどうすればいいのですか|第9話1|ヤングチャンピオン": "2026-08-04",
    "あの子とふたりで|第11話|COMIC OGYAAA!!": "2026-08-03",
    "あの子とふたりで|第11話|コミックオギャー!!": "2026-08-02",
    "べつの作品|第1話|どこか": "2026-07-20",
}

ROW = {"work": "公爵令嬢の籠絡ミッション～魔王との政略結婚が、人類最後の切り札です！…って、魔王が女の子の場合はどうすればいいのですか！？～",
       "ep": "第9話①", "plat_name": "ヤングチャンピオン",
       "url": "https://youngchampion.jp/series/86c1162f34a04"}


def main(s):
    # ── WHAT A RELEASE IS REMEMBERED AS ───────────────────────────────────────────────────────
    s.eq(sighting.key(ROW), "url|https://youngchampion.jp/series/86c1162f34a04|第9話1",
         "a release is remembered by its address and its chapter")

    # THE EPISODE IS PART OF IT WHATEVER THE ADDRESS IS. Some routes give a chapter its own URL and
    # some give the series page; keyed on the address alone, every chapter of a work collapsed into
    # one sighting and three of the four then had none.
    other = dict(ROW, ep="第9話②")
    s.ne(sighting.key(ROW), sighting.key(other),
         "two chapters sharing a series address are two sightings")

    # AND THE PLATFORM IS NOT IN IT, which is the whole change: the same page under a corrected
    # attribution is the same page.
    s.eq(sighting.key(dict(ROW, plat_name="チャンピオンクロス")), sighting.key(ROW),
         "correcting where we say a chapter is does not make it a chapter nobody saw")

    # A ROW WITH NO ADDRESS KEEPS THE OLD FORM, because there is nothing better to use.
    s.eq(sighting.key({"work": "あ", "ep": "第1話", "plat_name": "P"}), "あ|第1話|P",
         "a release with no address of its own is keyed as it always was")

    # ── THE CARRY ACROSS ──────────────────────────────────────────────────────────────────────
    #
    # THE EARLIEST UNDER ANY SPELLING. The exact old key holds 2026-08-04 and the same chapter sits
    # under a shorter title at 2026-08-02, which is the seed date the caller treats as unknown.
    # Taking the later one made a July chapter August news and moved it out of the July archive.
    s.eq(sighting.carried(LEDGER, ROW), "2026-08-02",
         "the earliest sighting of this chapter under any spelling of its work")
    s.eq(sighting.carried(LEDGER, dict(ROW, plat_name="チャンピオンクロス")), "2026-08-02",
         "and the platform is not part of the match, being the field that changed")

    # ONE PLATFORM UNDER TWO SPELLINGS is the same platform, and the ledger holds both.
    ogyaaa = {"work": "あの子とふたりで", "ep": "第11話", "plat_name": "COMIC OGYAAA!!",
              "url": "https://comic-ogyaaa.com/episode/12207421983966745358"}
    s.eq(sighting.carried(LEDGER, ogyaaa), "2026-08-02",
         "a chapter seen under both spellings of one platform was seen on the earlier day")

    # A CHAPTER NOBODY HAS SEEN CARRIES NOTHING, which is what makes it a new sighting rather than
    # a silently back-dated one.
    s.eq(sighting.carried(LEDGER, {"work": "知らない作品", "ep": "第1話", "plat_name": "P"}), None,
         "an unseen chapter carries no date")
    s.eq(sighting.carried(LEDGER, {"work": "あの子とふたりで", "ep": "第99話",
                                   "plat_name": "COMIC OGYAAA!!"}), None,
         "and a chapter of a known work that is itself new carries none either")

    # THE EPISODE MUST MATCH EXACTLY, or every chapter of a work would inherit the first one's date.
    s.eq(sighting.carried(LEDGER, {"work": "べつの作品", "ep": "第2話", "plat_name": "どこか"}), None,
         "a different chapter is a different sighting")

    # A WORK WHOSE TITLE IS A PREFIX OF ANOTHER'S IS NOT THAT WORK'S CHAPTER, and this is the cost
    # of matching on prefixes: the two are told apart by the episode alone, so the rule holds only
    # while a shared episode label means the same instalment. Named here rather than left implicit.
    s.eq(sighting.carried({"あ|第1話|P": "2026-01-01"},
                          {"work": "あるある", "ep": "第1話", "plat_name": "Q"}), "2026-01-01",
         "a title that extends another matches it, which is what a lengthened capture looks like")

    # ── THE INDEX IS THE SAME ANSWER, PRECOMPUTED ─────────────────────────────────────────────
    index = sighting.by_episode(LEDGER)
    s.eq(sighting.carried(LEDGER, ROW, index), sighting.carried(LEDGER, ROW),
         "an index handed in answers as the one built here would")
    s.check("第9話1" in index and "url|" not in "".join(index),
            "and it is built from the old-form keys alone, the new form needing no search")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
