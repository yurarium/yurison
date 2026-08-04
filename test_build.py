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
    # And where both carry one, the BASIS decides, not the field count. 見えてますよ！愛沢さん is
    # held twice, and a curated translation lost to a community database's string because the
    # loser also happened to carry a reading, a ruby split and furigana spans.
    curated = {"en": "I Can See Them, Aizawa!", "basis": "translated"}
    scraped = {"en": "I See You, Aizawa-san!", "basis": "romaji", "reading": "x",
               "ruby": [["a", "b"]], "furigana_spans": [["a", "b"]], "note": "n"}
    s.check(b._fullness(curated) > b._fullness(scraped),
            "a translation beats a romanisation carrying more fields")
    s.eq(b.fold_map({"見えてますよ! 愛沢さん": scraped, "見えてますよ！愛沢さん": curated}, fold)[0]
         ["見えてますよ!愛沢さん"]["en"], curated["en"],
         "and the fold keeps the translated one whichever order they arrive in")
    s.eq(b.fold_map({"見えてますよ！愛沢さん": curated, "見えてますよ! 愛沢さん": scraped}, fold)[0]
         ["見えてますよ!愛沢さん"]["en"], curated["en"], "in the other order too")

    # PLATFORM HISTORY. Two file shapes, and the second was silently dropped: a file assembled
    # across platforms leaves the top-level platform_name empty and names it on each work instead,
    # so every work in it keyed on the empty string and matched no claim. 28 claims read as
    # untraced while their evidence sat on disk, one of them in a file called claim-resolved.yaml.
    import tempfile, yaml as _yaml
    with tempfile.TemporaryDirectory() as d:
        one = pathlib.Path(d) / "filewide.yaml"
        one.write_text(_yaml.safe_dump({"platform_name": "COMIC FUZ", "works": [
            {"work_title": "\u7403\u8a60", "chapters": [{"updated": "2026-07-10"},
                                                          {"updated": "2026-07-17"}]}]},
            allow_unicode=True))
        two = pathlib.Path(d) / "mixed.yaml"
        two.write_text(_yaml.safe_dump({"platform_name": "", "works": [
            {"work_title": "A", "platform_name": "\u7af9\u30b3\u30df",
             "chapters": [{"updated": "2026-07-01"}]}]}, allow_unicode=True))
        h = b.load_platform_history([str(one), str(two)])
        s.eq(sorted(h[(b.norm_work("\u7403\u8a60"), b.norm_work("COMIC FUZ"))]),
             ["2026-07-10", "2026-07-17"], "a file naming its platform once is read")
        s.check((b.norm_work("A"), b.norm_work("\u7af9\u30b3\u30df")) in h,
                "and so is a file that names the platform on each work")
        s.eq(b.load_platform_history([]), {}, "no files is an empty history, not a crash")

        # A work in two files keeps the fuller history: the denial branch asks how much we hold,
        # and a thin copy displacing a full one turns a refutable claim back into an open one.
        thin = pathlib.Path(d) / "thin.yaml"
        thin.write_text(_yaml.safe_dump({"platform_name": "COMIC FUZ", "works": [
            {"work_title": "\u7403\u8a60", "chapters": [{"updated": "2026-07-10"}]}]},
            allow_unicode=True))
        for order in ([str(one), str(thin)], [str(thin), str(one)]):
            got = b.load_platform_history(order)[(b.norm_work("\u7403\u8a60"),
                                                  b.norm_work("COMIC FUZ"))]
            s.eq(len(got), 2, "the fuller history survives whichever file is read first")

    # WHAT REACHES THE READER AS NOTHING, AND WHY. A row with no chapters is not always a gap in
    # our fetching: 44 of them were finished states wearing the same face, sitting in the web list
    # as work somebody might go and do. Each kind is decided by data rather than by a title.
    import tempfile, yaml as _yaml
    with tempfile.TemporaryDirectory() as d:
        kf = pathlib.Path(d) / "chapters.yaml"
        kf.write_text(_yaml.safe_dump({"works": [
            {"work_title": "shelf", "status": "unknown", "chapters": []},
            {"work_title": "running", "status": "ongoing", "chapters": []},
        ]}, allow_unicode=True))
        src = pathlib.Path(d) / "src"; src.mkdir()
        (src / "a.yaml").write_text(_yaml.safe_dump({"works": [
            {"work_title": "taster", "chapters": [
                {"title": "\u3010\u8a66\u3057\u8aad\u307f\u3011\u767d\u7389\u3082\u3061"
                          "\uff3b\u8c9d\u5408\u308f\u305b\uff3d"}]},
            {"work_title": "collection", "chapters": [
                {"title": "\u6f2b\u753b\uff1a\u72ac\u4e95\u3042\u3086 \u541b\u306f\u5149(\u524d\u7de8)"}]},
            {"work_title": "ordinary", "chapters": [{"title": "\u7b2c1\u8a71"}]},
        ]}, allow_unicode=True))
        K = {"platform": "\u30ab\u30c9\u30b3\u30df"}
        rows = [{"work": "shelf", "chapters": 0, "sources": [K]},
                {"work": "running", "chapters": 0, "sources": [K]},
                {"work": "elsewhere", "chapters": 0, "sources": [K, {"platform": "\u7af9\u30b3\u30df"}]},
                {"work": "taster", "chapters": 0, "sources": [{"platform": "P"}]},
                {"work": "collection", "chapters": 0, "sources": [{"platform": "P"}]},
                {"work": "ordinary", "chapters": 0, "sources": [{"platform": "P"}]},
                {"work": "shelf", "chapters": 9, "sources": [K]}]
        got = b.set_aside(rows, str(kf), str(src))
        s.check("shop listing" in (got.get("shelf") or ""),
                "a カドコミ listing with no episodes and no status is set aside, and says why")
        s.check("running" not in got, "a work the platform says it is serialising is not")
        s.check("elsewhere" not in got,
                "nor one we hold anywhere else: the claim is about what WE hold")
        s.check("\u8a66\u3057\u8aad\u307f" in (got.get("taster") or ""),
                "an anthology that is samples throughout is set aside as one")
        s.check("own authors" in (got.get("collection") or ""),
                "and one whose stories are filed under their own authors, separately")
        s.check("ordinary" not in got,
                "a work with ordinary chapters we simply failed to attach is left alone, "
                "because that IS a gap in our fetching")
        s.eq(b.set_aside([], str(kf), str(src)), {}, "no works is an empty answer, not a crash")

    # A BASIS MUST EXPLAIN THE STATE BEING PUBLISHED. `state` is read off the best row and these
    # used to take the first basis any row carried, so はなにあらし published `active`, its last
    # chapter a month old, above a sentence saying no chapter had appeared for 2946 days: one
    # platform holds 169 chapters ending last month, another holds 3 ending in 2018.
    best = {"state": "active", "state_basis": None}
    rows = [best, {"state": "dormant", "state_basis": "silent for 2946 days"}]
    s.eq(b._basis_of(best, rows, "state_basis"), None,
         "a basis from a row that disagrees about the state is not borrowed")
    agrees = [best, {"state": "active", "state_basis": "a chapter last month"}]
    s.eq(b._basis_of(best, agrees, "state_basis"), "a chapter last month",
         "one from a row that agrees is")
    own = {"state": "active", "state_basis": "its own reason"}
    s.eq(b._basis_of(own, [own] + rows, "state_basis"), "its own reason",
         "and the row's own basis wins over any other")
    s.eq(b._basis_of({"state": "slow"}, [], "completed_basis"), None,
         "no rows is no basis, not a crash")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "build"))
