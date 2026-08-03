#!/usr/bin/env python3
"""build.py's pure predicates: the ones that decide what a row IS.

COVERS = ['build.py']

build.py is 2,700 lines and its main() resists decomposition for reasons recorded in
adapters/lint/shadowing.py. These functions are the parts that can be reached without it, and they
are the parts that classify: a wrong answer here mislabels a work in the reader's interface rather
than crashing anything, so nothing else would catch it.
"""
import importlib.util
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "adapters"))
import testkit

spec = importlib.util.spec_from_file_location(
    "buildmod", pathlib.Path(__file__).resolve().parent / "build.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def main(s):
    # SKIPPED SLOTS. 休載イラスト is a publisher posting art instead of a chapter. Counted as
    # chapters they inflated 19 works and let a notice become a work's `latest`.
    s.check(b.is_skipped_slot("休載イラスト"), "a hiatus illustration is a skipped slot")
    s.check(b.is_skipped_slot("[休載イラスト11]オトメの帝国"),
            "a numbered hiatus illustration is still a skipped slot")
    s.check(b.is_skipped_slot("休載のお知らせ"), "a hiatus announcement is a skipped slot")
    s.check(b.is_skipped_slot("今週はお休みです"), "a stated weekly break is a skipped slot")

    # The counter-cases that decided the rule. Five of nine お休み matches in the corpus are STORY
    # titles; keying on お休み alone would have filed them all as announcements.
    s.check(not b.is_skipped_slot("第８３話　エリザベートお休み中"),
            "a numbered chapter about a rest is a chapter")
    s.check(not b.is_skipped_slot("第20話 前編　ルイくんのお休み"),
            "a numbered chapter naming a day off is a chapter")
    s.check(not b.is_skipped_slot("#14 #お休みしゅる"), "a hash-numbered chapter is a chapter")
    s.check(not b.is_skipped_slot("第25話　ルイくんの友達がお休みの日"),
            "and again with the number later in the title")
    s.check(not b.is_skipped_slot("第1話"), "an ordinary chapter is not a skipped slot")
    s.check(not b.is_skipped_slot(""), "an empty title is not a skipped slot")
    s.check(not b.is_skipped_slot(None), "None does not raise")

    # EPISODE NUMBERING drives new-series against new-chapter, and a wrong answer tells a reader to
    # expect a second chapter that does not exist.
    s.eq(b.ep_number("第1話"), 1, "a numbered first chapter")
    s.eq(b.ep_number("第12話"), 12, "a later chapter")
    s.eq(b.ep_number("１２話"), 12, "full-width digits count the same")
    s.check(b.ep_number("読切") is None, "a one-shot has no episode number")
    s.check(b.ep_number("休載イラスト") is None, "a notice has no episode number")

    # WORK NORMALISATION decides identity across platforms. Getting it wrong either splits one work
    # into two rows or merges two works into one.
    s.eq(b.norm_work("ＹＵＲＩ"), b.norm_work("yuri"), "width and case fold together")
    s.eq(b.norm_work("百合 の 花"), b.norm_work("百合の花"), "internal spacing is not identity")
    s.ne(b.norm_work("百合"), b.norm_work("薔薇"), "different works stay distinct")
    s.eq(b.norm_work(None), "", "None normalises rather than raising")

    # EXTRAS ARE CONTENT. おまけ and 番外編 are instalments a reader follows the series for, so they
    # must not be swept in with notices. This is why a completed series can still publish.
    s.check(b.EXTRA_RE.search("おまけの１５話"), "おまけ is an extra")
    s.check(b.EXTRA_RE.search("番外編"), "番外編 is an extra")
    s.check(not b.NON_STORY_RE.search("おまけの１５話"), "an extra is not filed as a notice")

    # FINALES. A series is `completed` on the strength of this, so a false positive retires a
    # running work and a false negative leaves a finished one looking abandoned.
    s.check(b.FINAL_RE.search("最終話"), "最終話 is a finale")
    s.check(b.FINAL_RE.search("最終回"), "最終回 is a finale")
    s.check(not b.FINAL_RE.search("第2話"), "an ordinary chapter is not a finale")

    # PRIZE ENTRIES. 【第28回角川漫画新人大賞】佳作 is a citation where a chapter name goes, and the
    # 28 is the twenty-eighth CONTEST. ep_number read it as a chapter number, so four works were
    # filed as later chapters of series that do not exist.
    s.check(b.is_prize_entry("【第28回角川漫画新人大賞】佳作"), "a bracketed citation is an entry")
    s.check(b.is_prize_entry("カドマンGP受賞作"), "a title that is only an award is an entry")
    s.check(b.is_prize_entry("ライオンと不時着(第17回NC佳作)"),
            "the bracket may sit at the end")

    # The counter-cases, which a keyword list got wrong four times in ten across 11,201 names.
    s.check(not b.is_prize_entry("第11話 2021年12月29日 東京大賞典(GⅠ)"),
            "大賞 inside 大賞典 is a horse race, and the chapter is numbered")
    s.check(not b.is_prize_entry("第23話①：歌唱コンテスト"),
            "a chapter about a singing contest is a chapter")
    s.check(not b.is_prize_entry("第1回 強豪校から来た転校生。最後のコンクールで"),
            "a competition as the story's subject is not a citation")
    s.check(not b.is_prize_entry("第1話"), "an ordinary chapter is not an entry")
    s.check(not b.is_prize_entry(""), "an empty title is not an entry")

    # 回 numbers both contests and chapters, so it must not decide either way. This is why the
    # prize rule uses its own narrower counter rather than CHAPTER_NUM_RE.
    s.check(b.UNAMBIGUOUS_CHAPTER.search("第1話"), "話 counts chapters")
    s.check(not b.UNAMBIGUOUS_CHAPTER.search("第28回"), "回 alone does not")
    s.check(b.CHAPTER_NUM_RE.search("第28回"),
            "while the skipped-slot counter does accept 回, which is why they are separate")

    # TRIAL PREVIEWS. 【試し読み】あんすこ［Are you "mine"？］ is a preview of a printed anthology.
    # The bracketed part is a real work by a real author, so splitting it out is right; what is on
    # the web is a sample, not a serialisation. Keeping only the first half of that put 28 previews
    # in the works list and 13 in the feed.
    got = b.anth_parts('【試し読み】白玉もち［貝合わせ］')
    s.eq(got, ('白玉もち', '貝合わせ', True), "a preview yields author, title, and that it IS one")

    # A 読切 instalment is NOT a preview. Same shape, different marker, and it must keep its place
    # in the feed, or the fix would remove real one-shots along with the samples.
    s.eq(b.anth_parts('【読切】白玉もち［貝合わせ］'), ('白玉もち', '貝合わせ', False),
         "a 読切 instalment is an anthology entry that is not a preview")

    # The other shape a container uses, which carries no marker at all.
    got2 = b.anth_parts('漫画：東雲水生 ある日の話')
    s.check(got2 and got2[0] == '東雲水生', "the author-prefixed shape is read")
    s.check(got2 and got2[2] is False, "and is not a preview")

    s.check(b.anth_parts('第1話') is None, "an ordinary chapter is not an anthology entry")
    s.check(b.anth_parts('') is None, "an empty title is not one")
    s.check(b.anth_parts(None) is None, "None does not raise")

    # A two-part instalment stays one work, or a 読切 in two halves becomes two works.
    two = b.anth_parts('【読切】白玉もち［貝合わせ（前編）］')
    s.eq(two and two[1], '貝合わせ', "a 前編 marker is stripped from the title")

    # Hiatus freshness has to be a real window, or an attested pause either never applies or never
    # decays back to the observed ladder.
    s.check(0 < b.HIATUS_FRESH_DAYS <= 365, "the hiatus window is a sane number of days")

    # FOLDING TITLES TOGETHER. Two spellings of one title must not let iteration order decide
    # which name ships. 彼氏の女友達がぐいぐい来る(私に) is held with both bracket widths, and a
    # curated translation on one of them was dropped on the way to the page by a dict
    # comprehension, with nothing reporting a problem.
    import unicodedata
    fold = lambda t: unicodedata.normalize("NFKC", t or "").replace(" ", "")
    rich = {"en": "Keeps Coming On Strong (At Me)", "basis": "translated"}
    bare = {"basis": "romaji"}
    first = b.fold_map({"来る(私に)": rich, "来る（私に）": bare}, fold)
    second = b.fold_map({"来る（私に）": bare, "来る(私に)": rich}, fold)
    s.eq(first[0], second[0], "the surviving record does not depend on which spelling came first")
    s.eq(first[0]["来る(私に)"]["en"], rich["en"], "and it is the one carrying the English name")
    s.eq(first[1], [("来る(私に)", 1)], "the collision is reported rather than passed over")
    s.eq(b.fold_map({"球詠": bare}, fold)[1], [], "a title held once reports no collision")
    s.check(b._fullness({"en": "x"}) > b._fullness({"reading": "x", "basis": "y"}),
            "an English name outweighs a record that merely has more fields")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "build"))
