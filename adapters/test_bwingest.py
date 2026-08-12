#!/usr/bin/env python3
"""bwingest.py: a shop that states no ISBN, joined on a title and reviewed after."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bwingest as bw  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/bwingest.py"]


def work(**kw):
    base = {"shop_id": "u1", "url": "https://bookwalker.jp/de-u1/", "publisher": "一迅社",
            "imprint": "百合姫コミックス", "authors": ["袴田めら"], "completed": True,
            "first_publication": {"venue": "一迅社", "date_basis": "no-print-edition"},
            "volumes": [
                {"title": "初恋姉妹 1", "series_title": "初恋姉妹", "printed": "2014-02-14",
                 "delivered": "2016-08-01"},
                {"title": "初恋姉妹 2", "series_title": "初恋姉妹", "delivered": "2016-08-01"}]}
    base.update(kw)
    return base


def main(s):
    r = bw.record(work(), "2026-08-06")
    s.eq(r["title"], "初恋姉妹", "the series name is the work's title where the shop groups it")
    s.eq(r["volume_count"], 2, "with as many volumes as the shop showed")
    s.eq([v["number"] for v in r["volumes"]], ["1", "2"],
         "numbered as the shop's own product titles number them")
    s.eq(r["first_published"], "2014-02-14",
         "dated by the print edition the file was made from, which is a publication of the work")

    # THE DELIVERY DATE IS NEVER THE PUBLICATION DATE. It is the day the shop began selling a file
    # and runs years late on a back catalogue: 2016 for a 2014 book, above.
    s.eq(r["volumes"][0]["delivered"], "2016-08-01", "recorded, because it is a fact about the shop")
    s.eq(r["volumes"][1].get("published"), None, "and never promoted where no print date is stated")

    undated = bw.record(work(volumes=[{"title": "x", "series_title": "x", "delivered": "2020-01-01"}]),
                        "2026-08-06")
    s.eq(undated["first_published"], None, "a work the shop never dates is undated")
    s.eq(undated["date_basis"], "no-print-edition", "and says why, rather than borrowing a date")

    # A SINGLE VOLUME IS ITS OWN TITLE. 528 rows have no series grouping because the work is one
    # book, and its volume title is the work's name.
    one = bw.record(work(volumes=[{"title": "結婚するってよ", "series_title": None}]), "2026-08-06")
    s.eq(one["title"], "結婚するってよ", "a lone volume's title is the work's title")
    s.eq(one["volumes"][0]["number"], None, "and it carries no volume number, having no siblings")

    # A multi-volume work with no series name loses the number from the title, not from the words.
    two = bw.record(work(volumes=[{"title": "ふたりの話 1", "series_title": None},
                                  {"title": "ふたりの話 2", "series_title": None}]), "2026-08-06")
    s.eq(two["title"], "ふたりの話", "a volume number is stripped from a borrowed title")

    # A SHOP HOLDING ONE VOLUME STILL NUMBERS IT, and stripping only where there were siblings sent
    # `うどみょん１` to the works list with the number in its name. The shop stocks one volume of a
    # doujin, so the sibling test could never fire on exactly the works that needed it.
    lone = bw.record(work(volumes=[{"title": "うどみょん１", "series_title": None}]), "2026-08-06")
    s.eq(lone["title"], "うどみょん", "a lone volume's number is not part of the work's name either")

    # AND WHAT SITS BEFORE THE NUMBER IS WHAT SAYS WHETHER IT IS ONE. Seven of the nine single
    # volumes ending in a digit are ギロチン銀座's 再録集, where the number counts re-collections and
    # belongs to that word. Stripping by shape alone renames every one of them.
    kept = bw.record(work(volumes=[{"title": "乙女ホリック 再録集4", "series_title": None}]), "2026-08-06")
    s.eq(kept["title"], "乙女ホリック 再録集4", "a number a counter word governs stays in the title")
    s.eq(bw.without_volume_number("ガチ恋カウント2.9"), "ガチ恋カウント2.9",
         "and a digit inside a number is not a volume")
    s.eq(bw.without_volume_number("百合姫 第3巻"), "百合姫", "第 and 巻 around it are still a volume")
    s.eq(bw.without_volume_number("2"), "2", "a title that is only a number keeps it, having no other")

    # A HALF-WIDTH DIGIT GLUED TO A NAME IS THE NAME. These are the counter-cases that stop the rule
    # from being "ends in a digit", and every one of them is a shipped row.
    for name in ("魔法少女201", "あやめ14", "Smile0", "P-0004", "ラブフェロモンNo.5",
                 "百合姫表紙集 2011-2025", "小学生百合2019", "百合癖シチュ100"):
        s.eq(bw.without_volume_number(name), name, f"{name} keeps the number that is its name")

    # AND A SENTENCE-FINAL MARK MARKS ONE OFF, which is what tells `ふぉーおぶあかいんど！2` from
    # `あやめ14`: both are one volume with a half-width digit and only one has a boundary.
    s.eq(bw.without_volume_number("ふぉーおぶあかいんど！2"), "ふぉーおぶあかいんど！",
         "a number after ！ is a volume, and the mark stays with the name")

    # NOTHING CAPTURED IS NOT A WORK WITHOUT A NAME. 284 rows read no volumes at all.
    s.eq(bw.record(work(volumes=[]), "2026-08-06"), None,
         "a work the capture could not open is skipped rather than invented")

    # THE EDITION LABEL IS NOT PART OF THE NAME. BOOK☆WALKER writes it into the volume title on
    # 771 of 2,093 works, and leaving it there put a Latin imprint inside a Japanese reading:
    # ヒメチャン ワ オモイ オンナ （fuz コミックス）.
    s.eq(bw.strip_imprint("雪解けとアガパンサス（電撃コミックスNEXT）"),
         ("雪解けとアガパンサス", "電撃コミックスNEXT"), "the label comes off and is kept as the imprint")
    s.eq(bw.strip_imprint("ふつうの話")[0], "ふつうの話", "a title without one is untouched")
    # THE RECORD ANSWERS THE QUESTION ABOUT ITSELF. A word list caught 電撃コミックスNEXT and missed
    # ナンバーナイン, 百合コレ and orSiS, which are publishers and imprints carrying no such word.
    s.eq(bw.strip_imprint("黒の世界は白墨に染まる（orSiS）", "ぶんか社", "orSiS"),
         ("黒の世界は白墨に染まる", "orSiS"), "a bracket holding this record's own imprint is a label")
    s.eq(bw.strip_imprint("私が殺しました（ナンバーナイン）", "ナンバーナイン", None),
         ("私が殺しました", "ナンバーナイン"), "and so is one holding its own publisher")
    s.eq(bw.strip_imprint("白き乙女の人狼（ウェアウルフ）", "竹書房", "バンブーコミックス")[0],
         "白き乙女の人狼（ウェアウルフ）", "a reading gloss belongs to the title and stays")
    s.eq(bw.strip_imprint("彼氏の女友達がぐいぐい来る（私に）", "一迅社", "百合姫")[0],
         "彼氏の女友達がぐいぐい来る（私に）", "and so does a bracket the author wrote")
    s.eq(bw.strip_imprint("わたしが恋人になれるわけないじゃん（※ムリじゃなかった!?）")[0],
         "わたしが恋人になれるわけないじゃん（※ムリじゃなかった!?）",
         "and a bracket that is part of the title is not an edition label")
    lab = bw.record(work(imprint=None, volumes=[{"title": "作品名（百合姫コミックス）",
                                                 "series_title": "作品名（百合姫コミックス）"}]),
                    "2026-08-06")
    s.eq((lab["title"], lab["imprint"]), ("作品名", "百合姫コミックス"),
         "so a record takes the imprint from the title where the shop states none")

    # WHAT A SHOP SELLS ONE CHAPTER AT A TIME IS NOT A SET OF VOLUMES.
    # ── A POSITION IN A LISTING IS NOT A VOLUME NUMBER ────────────────────────────────────────
    #
    # THE FAULT THIS REPLACED, in the record it was found on. BOOK☆WALKER sells 32 products under
    # MURCIÉLAGO: 29 volumes and 3 free samples of volumes already in the list. The number was the
    # item's index, so the corpus published a 29 volume series as 32 volumes, invented volumes 30,
    # 31 and 32, and put every date after the second sample beside the wrong number.
    mur = bw.record(work(
        title="MURCIÉLAGO -ムルシエラゴ-",
        volumes=[{"title": "MURCIELAGO -ムルシエラゴ- 1巻", "series_title": "MURCIÉLAGO -ムルシエラゴ-",
                  "printed": "2014-04-25"},
                 {"title": "MURCIÉLAGO -ムルシエラゴ- 1巻【無料お試し版】",
                  "series_title": "MURCIÉLAGO -ムルシエラゴ-", "delivered": "2026-07-22"},
                 {"title": "MURCIELAGO -ムルシエラゴ- 2巻", "series_title": "MURCIÉLAGO -ムルシエラゴ-",
                  "printed": "2014-04-25"},
                 {"title": "【最新刊】MURCIÉLAGO -ムルシエラゴ- 29巻",
                  "series_title": "MURCIÉLAGO -ムルシエラゴ-", "delivered": "2026-07-24"}]),
        "2026-08-06")
    s.eq([v["number"] for v in mur["volumes"]], ["1", "2", "29"],
         "the shop's own numbers, and the free sample is not among them")
    s.eq(mur["volume_count"], 3,
         "SO THE COUNT IS OF VOLUMES AND NOT OF PRODUCTS; counting items gave 32 for a work with 29")
    s.check(all("お試し版" not in v["title"] for v in mur["volumes"]),
            "a free sample is dropped the way 単話 is, because the question is how long the work is")

    # AND THE LISTING IS NOT IN VOLUME ORDER, which is the half of the fault the samples hide.
    # パロスの剣 lists its newest volume first, so volume 3 went out as volume 1.
    par = bw.record(work(title="パロスの剣", volumes=[
        {"title": "【最新刊】パロスの剣　3巻", "series_title": "パロスの剣", "printed": "2016-01-01"},
        {"title": "パロスの剣　1巻", "series_title": "パロスの剣", "printed": "2014-01-01"},
        {"title": "パロスの剣　2巻", "series_title": "パロスの剣", "printed": "2015-01-01"}]),
        "2026-08-06")
    s.eq([v["number"] for v in par["volumes"]], ["3", "1", "2"],
         "each volume keeps the number its own title states, whatever order the shop listed it in")
    s.eq([v["published"] for v in par["volumes"]], ["2016-01-01", "2014-01-01", "2015-01-01"],
         "so a date stays beside the volume it belongs to")

    # A SERIES FILED UNDER ITS IMPRINT still names its volumes without it, and the two have to meet:
    # 3,634 of 4,792 rows miss where the imprint is left on the series title.
    imp = bw.record(work(title="さかさまロリポップ", imprint="まんがタイムKRコミックス", volumes=[
        {"title": "さかさまロリポップ　１巻",
         "series_title": "さかさまロリポップ（まんがタイムKRコミックス）", "printed": "2015-01-01"},
        {"title": "さかさまロリポップ　２巻",
         "series_title": "さかさまロリポップ（まんがタイムKRコミックス）", "printed": "2016-01-01"}]),
        "2026-08-06")
    s.eq([v["number"] for v in imp["volumes"]], ["1", "2"],
         "the imprint comes off the series name before the volume titles are read against it")

    # AND WHAT THE SHOP DOES NOT NUMBER IS NOT NUMBERED. `百合シリーズ` is a shop umbrella over
    # differently named books, and giving them 1, 2, 3 would assert a run that does not exist.
    umb = bw.record(work(title="百合シリーズ", volumes=[
        {"title": "ドSさんはヤキモチちゃんが大好き", "series_title": "百合シリーズ"},
        {"title": "ヤキモチちゃんとドSさんのラブらいふ", "series_title": "百合シリーズ"}]),
        "2026-08-06")
    s.eq([v["number"] for v in umb["volumes"]], [None, None],
         "a work the shop numbers nowhere carries no numbers")
    s.eq(umb["volume_count"], 2,
         "and the count falls back on how many items there are, which is all that can be said")

    # 付き合ってあげてもいいかな【単話】 lists 133 items, numbered （１） to （133） by the shop
    # itself, and calling them 第1巻 to 第133巻 says the work is 133 volumes long.
    s.check(bw.chapterwise("付き合ってあげてもいいかな【単話】"), "単話 is sold one chapter at a time")
    s.check(bw.chapterwise("女子校だからセーフ【単話版】"), "and so is 単話版")
    s.check(bw.chapterwise("ある話【分冊版】"), "and 分冊版, a volume split into parts sold apart")
    s.check(not bw.chapterwise("ふつうの単行本"), "an ordinary volume release is not")
    ch = bw.record(work(volumes=[{"title": "話【単話】（1）", "series_title": "話【単話】"},
                                 {"title": "話【単話】（2）", "series_title": "話【単話】"}]),
                   "2026-08-06")
    s.eq(ch["volume_count"], 0, "so it counts no volumes")
    s.eq(ch["volumes"], [], "and lists none, because it has none")
    s.eq(ch["chapter_count"], 2, "the items are counted as what they are")
    s.eq(len(ch["chapters"]), 2, "and kept, so their dates are not lost")

    # A MATCHING TITLE DECIDES WHICH PILE, NEVER A MERGE. トワ・エ・モア is one title over two
    # unrelated works, which is why this cannot be allowed to join anything by itself.
    recs = [{"_key": "a", "title": "A"}, {"_key": "b", "title": "B"}]
    new, review = bw.split(recs, {"b"})
    s.eq([x["title"] for x in new], ["A"], "a title we do not hold is a new work")
    s.eq([x["title"] for x in review], ["B"], "and one we do hold waits for a person")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
