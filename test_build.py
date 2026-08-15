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
    # A §2 REBUTTAL KEEPS THE WORK AND TAKES IT OUT OF THE LISTING. `out` is a source disagreeing
    # with a source; `marginal` is the operator declining to decide. Neither is deletion, and the
    # two are kept apart because they mean different things.
    _reb = b.rebuttals()
    s.check(isinstance(_reb, dict), "rebuttals() reads the file into a map")
    if _reb:
        s.check(set(_reb.values()) <= {"rebutted", "marginal"},
                "a disposition is one of the two the interface knows")
        s.check(all(k.startswith("w") for k in _reb),
                "every entry names a work identifier, so nothing is matched on a title")

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


    # ── THE RESOLVER'S ROWS, DROPPED PER CHAPTER RATHER THAN PER WORK ────────────────────────────
    #
    # WHAT A READER SAW. 運命は役に立たない showed "a chapter arrived today" in the works list and
    # nothing at all in the updates feed on 2026-08-16. 花とゆめ+'s own pass read the work's page
    # and returned fourteen chapters ending at 12話; the catch-all resolver read the same page and
    # returned fifteen, ending at 13話 published that morning. Keyed on the WORK, this rule took the
    # dedicated pass covering the work as licence to drop every resolver row for it, including the
    # one chapter that pass had missed. Four chapters were being deleted this way, on four
    # platforms, and nothing counted them because the drop is what the rule is for.
    ADAPTER = {"work": "運命は役に立たない", "plat": "hanayume", "ep": "12話",
               "url": "https://hanayume.com/series/ca4ef0eb47ea3",
               "access_modes": ["purchase"]}
    RESOLVER = {"work": "運命は役に立たない", "plat": "remaining", "ep": "13話",
                "url": "https://hanayume.com/series/ca4ef0eb47ea3", "access_modes": []}
    kept = b.resolver_superseded([ADAPTER, RESOLVER, dict(RESOLVER, ep="12話")])
    s.eq([r["ep"] for r in kept if r["plat"] == "remaining"], ["13話"],
         "a chapter only the resolver saw survives, and its copy of a read chapter does not")
    s.eq(len([r for r in kept if r["plat"] != "remaining"]), 1,
         "and the adapter's own row is never what gets dropped")

    # THE REASON THE RULE EXISTS, UNCHANGED. コミックFUZ's adapter holds every chapter with a price
    # and a free_from date; the resolver held the same chapters dateless-in-substance and labelled
    # with whichever list named the work. Those are the same chapters, so they still go.
    FUZ = [{"work": "一畳間まんきつ暮らし！", "plat": "comicfuz", "ep": f"第{i}話",
            "url": "https://comic-fuz.com/manga/1", "access_modes": ["purchase"]}
           for i in range(1, 5)]
    THIN = [{"work": "一畳間まんきつ暮らし！", "plat": "remaining", "ep": f"第{i}話",
             "url": "https://comic-fuz.com/manga/1", "access_modes": []} for i in range(1, 5)]
    s.eq(len(b.resolver_superseded(FUZ + THIN)), 4,
         "every resolver row for a chapter the adapter read is dropped, as before")

    # AND COVERAGE IS PER HOST. The same work on another platform is another reading, so a resolver
    # row there is not superseded by an adapter that never saw that page.
    ELSEWHERE = dict(RESOLVER, ep="12話", url="https://manga-park.com/title/101442")
    s.eq(len(b.resolver_superseded([ADAPTER, ELSEWHERE])), 2,
         "an adapter on one host does not answer for a chapter on another")

    # A ROW THE ADAPTER READ WITHOUT AN ACCESS STATE STATES NOTHING ABOUT COVERAGE, which is the
    # existing condition and is kept: a sitemap-thin row must not silence the resolver.
    s.eq(len(b.resolver_superseded([dict(ADAPTER, ep="13話", access_modes=[]), RESOLVER])), 2,
         "an adapter row with no access state does not supersede anything")

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
    # WHICH RECORD ANSWERS IS `names/fold`'s AND IS TESTED THERE, since STORE-PLAN §6 needed the
    # store to reach the same answer and a rule with two implementations has none. What is asserted
    # here is that the build still asks it, which is what the collision above is about.
    s.eq(b.fold_map({"球詠": bare}, fold)[2], {"球詠": "球詠"},
         "and the fold says whose record the entry it keeps was rendered from")

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

    # SILENCE IS NOT TESTIMONY. Import stamps are found per file by spotting a run of instalments
    # sharing a timestamp, so a file holding one chapter of a work cannot see one and never reports
    # one. Reading that inability as an observation let sitemap-magapoke.yaml, holding a single
    # chapter of ハロー、メランコリック！ at 2021-11-11, overturn the stamp two files holding all 40
    # chapters agreed on. The work read `dormant` off the day the publisher loaded it, and showed
    # 【track1】, its first chapter, as its newest.
    # HOW LONG A WORK IS AND WHEN IT LAST PUBLISHED ARE TWO QUESTIONS. The row chosen to answer the
    # second is chosen for its dates, and the source with the best dates is routinely not the one
    # holding the most chapters. ナメられたくないナメカワさん published as 29 chapters because
    # コミックDAYS watched its run end, while 一迅プラス holds all 77.
    s.eq(b.best_known_length([{"chapters": 29}, {"chapters": 77}]), 77,
         "the work is as long as the best-informed source says")
    s.eq(b.best_known_length([{"chapters": 121}, {"chapters": 14}]), 121,
         "and sources are never summed, because they describe one story")
    s.eq(b.best_known_length([]), 0, "no rows, no length")
    s.eq(b.best_known_length([{}]), 0, "and a row with no count contributes none")

    s.check(not b.can_testify([{"title": "第1話", "updated": "2021-11-11"}]),
            "one chapter cannot tell an import from a publication")
    s.check(not b.can_testify([{"updated": "2021-11-11"}] * 40),
            "and neither can forty that all share one date, which is the signature itself")
    s.check(b.can_testify([{"updated": "2021-11-11"}, {"updated": "2021-11-18"}]),
            "two distinct dates is a source that watched something happen")
    s.check(not b.can_testify([]), "no chapters, nothing to say")
    s.check(not b.can_testify([{"title": "第1話"}, {"title": "第2話"}]),
            "and chapters carrying no date at all say nothing either")

    # Aliases resolve one work written two ways, and leave everything else alone.
    s.eq(b.work_alias("念願の悪役令嬢(ラスボス)の身体を手に入れたぞ!"),
         "念願の悪役令嬢の身体を手に入れたぞ!",
         "マガポケ's ruby gloss in the title names the work コミックDAYS carries without it")
    s.eq(b.work_alias("超深宇宙より愛をこめて【読み切り版】"), "超深宇宙より愛をこめて【読み切り版】",
         "a one-shot beside its serialisation is NOT the same work and is not aliased")
    s.eq(b.work_alias("citrus+"), "citrus+", "and a sequel keeps its own title")

    # AN UNDATED WORK STILL SAYS WHERE, which is what DEFINITIONS §6's scope test actually asks.
    # This returned `venue: None` on 1,209 records whose sources all named a publisher.
    fp = b.undated_publication({"venue": "ナンバーナイン", "date_basis": "no-print-edition"})
    s.eq(fp["venue"], "ナンバーナイン", "the venue the source stated survives having no date")
    # AND THE COUNTRY IS EMPTY UNLESS SOMETHING ATTESTS IT. This asserted "JP", against a line that
    # read `base.get("first_publication_country") or "JP"`, so the test could only ever agree with
    # the constant. §6 makes this field the inclusion test and the sources here catalogue the
    # Japanese EDITION, which is the one thing that cannot tell a translation from an original.
    s.eq(fp["country"], None, "the country is empty where the caller establishes none")
    s.eq(fp["country_basis"], "japanese-edition-catalogued",
         "and the record says the scope test has not run rather than pretending it passed")
    s.eq(fp["date"], None, "the date stays null rather than being filled from anything nearby")
    s.eq(fp["date_basis"], "no-print-edition", "and the record says which silence it is in")
    s.eq(fp["venue_type"], "digital-imprint", "typed from the basis, not guessed from the venue")
    s.eq("Digital-only" in fp["note"], True, "with the sentence that explains the term")

    # THE FOUR SILENCES ARE FOUR ANSWERS. Flattening them to one is what this replaced: a work on a
    # print imprint that dates its other books is unresolved, and a digital-only label is finished
    # work. Only the second is complete as it stands, and the field is how anyone tells them apart.
    # It can still gain a print date, by a capture finding a printing that did not exist when the
    # row was written, which is a different event from resolving a gap.
    s.ne(b.undated_publication({"date_basis": "no-print-date-stated"})["note"], fp["note"],
         "an unexplained silence does not read as an explained one")
    s.eq(b.undated_publication({"date_basis": "no-print-date-stated"})["venue_type"], "imprint",
         "and it claims no format it has not established")

    # A source that said nothing about why still has to say that much.
    bare = b.undated_publication({"publisher": "某社"})
    s.eq(bare["date_basis"], "no-date-attested", "no stated reason is itself the stated reason")
    s.eq(bare["venue"], "某社", "and the publisher answers for the venue where nothing else does")
    s.eq(bare["venue_type"], None, "with no venue type, because nothing established one")
    s.eq(b.undated_publication({})["venue"], None,
         "a record naming nobody gets null rather than an empty string pretending to be a venue")

    # A MULTI-CREDIT AUTHOR LINE IS COMPOSED FROM THE PARTS, and the composition decides whether
    # 41 works showed their author in Japanese on an English page. 彼女のカノジョと不純な初恋 is the
    # reported one: Akeo is in the name store as an already-Latin name with no reading and no
    # romanisation, correctly, and being found there skipped the fallback that handles exactly
    # that. The romanisation styles were then intersected across the credits, came out empty, and
    # the whole field shipped with no `romaji` at all.
    _fold = lambda x: x                                                          # noqa: E731
    LATIN_STORE = {"basis": "stated", "en": "Akeo", "script": "latin", "verified": True}
    HANAMIYA = {"reading": "ハナミヤ ミィ", "en": "Mee Hanamiya", "reading_basis": "stated",
                "romaji": {"macron": "Mii Hanamiya", "double": "Mii Hanamiya",
                           "plain": "Mii Hanamiya"}}
    SHIOKOJI = {"reading": "シオコウジ", "reading_basis": "stated",
                "romaji": {"macron": "Shiokōji", "double": "Shiokouji", "plain": "Shiokoji"}}
    store = {"Akeo": LATIN_STORE, "花宮みぃ": HANAMIYA, "塩こうじ": SHIOKOJI}
    got = b.credits_en("Akeo / 花宮みぃ / 塩こうじ", store, {}, _fold)
    s.check(got is not None, "the reported field composes rather than returning nothing")
    s.eq(sorted(got.get("romaji") or {}), ["double", "macron", "plain"],
         "with all three romanisation styles, which is what the page reads")
    s.eq(got["romaji"]["macron"], "Akeo / Mii Hanamiya / Shiokōji",
         "the Latin credit stands as its own romanisation beside two romanised ones")
    s.eq(got["reading"], "Akeo / ハナミヤ ミィ / シオコウジ",
         "and the reading no longer opens with an empty part where Akeo belongs")

    # The counter-case that decided which field the Latin form comes from. 花宮みぃ has an English
    # name and no romanisation would be a different fact: `en` is a TRANSLATION, and putting it
    # where the sound of the name goes would print a licensor's wording as a romanisation.
    s.check(b.credits_en("花宮みぃ / 塩こうじ",
                         {"花宮みぃ": {"en": "Mee Hanamiya", "basis": "romaji"},
                          "塩こうじ": SHIOKOJI}, {}, _fold) is None,
            "a Japanese credit with an English name and no reading composes nothing")

    # ALL OF THEM OR NONE, which is the rule that already existed and now actually holds. A
    # partial rendering is worse than none: the interface prefers author_en where it exists, so
    # emitting one without a romanisation suppresses the fallback to the Japanese.
    s.check(b.credits_en("花宮みぃ / 未知の人", {"花宮みぃ": HANAMIYA}, {}, _fold) is None,
            "one unresolvable credit stops the whole field")

    # The fallback that always worked, pinned so the fix cannot be read as replacing it.
    s.eq(b.credits_en("Ｍａｇｐｉｅ / 塩こうじ", {"塩こうじ": SHIOKOJI}, {},
                      _fold)["romaji"]["plain"],
         "Magpie / Shiokoji", "a full-width Latin credit absent from the store still folds")
    s.check(b.credits_en("塩こうじ", {"塩こうじ": SHIOKOJI}, {}, _fold) is None,
            "and a field naming one person is not a composition at all")

    shelf_citations(s)
    state_claims(s)
    series_addresses(s)


def shelf_citations(s):
    """WHERE A SHELF CLAIM CAN BE CHECKED, which for 1,900 rows was nowhere.

    A comparator entry named the shop and stated no address, so the only BOOK☆WALKER link near the
    evidence table pointed at the shop's page for the book. That page carries no 百合 filing, an
    operator followed it and concluded the entry was wrong, and they were reading our citation
    correctly. These pin that the address emitted is the SHELF's.
    """
    # THE PAGE GOES BACK INTO THE LISTING ADDRESS. The captures state the listing with page=1 and
    # record which page each work was read from, so the citation is built by substitution.
    s.eq(b.shelf_page_url("https://bookwalker.jp/tag/14/?qcat=2&order=title&page=1", 27),
         "https://bookwalker.jp/tag/14/?qcat=2&order=title&page=27",
         "the page the work was read on replaces the one the capture wrote")
    s.eq(b.shelf_page_url("https://bookwalker.jp/tag/14/?wa=1&page=1", 3),
         "https://bookwalker.jp/tag/14/?wa=1&page=3",
         "and the second listing keeps its own filter")
    s.eq(b.shelf_page_url("https://www.cmoa.jp/search/genre/37/", 4),
         "https://www.cmoa.jp/search/genre/37/?page=4",
         "a listing with no query gains one")
    # THE COUNTER-CASE THAT DECIDES THE RULE. Page 1 of a shelf a work is not on is the same fault
    # as the book's own page: a citation that invites a check and then fails it.
    s.eq(b.shelf_page_url("https://bookwalker.jp/tag/14/?page=1", None),
         "https://bookwalker.jp/tag/14/?page=1",
         "no page number stated leaves the address exactly as captured")
    s.eq(b.shelf_page_url("", 3), None, "and no listing address is no address")

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        cap = pathlib.Path(tmp) / "shelf.yaml"
        cap.write_text(
            "source_url: https://bookwalker.jp/tag/14/\n"
            "shop_tag: 百合\n"
            "listings:\n"
            "  manga:\n"
            "    url: \"https://bookwalker.jp/tag/14/?qcat=2&order=title&page=1\"\n"
            "items:\n"
            "  - listing: manga\n"
            "    id: \"abc\"\n"
            "    page: 27\n"
            "  - listing: manga\n"
            "    id: \"nopage\"\n")
        cites = b.shelf_citations({"bookwalker.jp": str(cap),
                                   "gone.example": str(pathlib.Path(tmp) / "absent.yaml")})
        s.eq(sorted(cites), ["bookwalker.jp"], "a capture that is not on disk contributes nothing")
        s.eq(cites["bookwalker.jp"]["url"], "https://bookwalker.jp/tag/14/",
             "the shelf address is the capture's own source_url")
        s.eq(cites["bookwalker.jp"]["pages"]["abc"][0], 27, "and each item carries its page")
        s.check("nopage" not in cites["bookwalker.jp"]["pages"],
                "an item the capture stated no page for gets none invented")

        entry = {"comparator": "bookwalker.jp", "shelf": "tag 14 (百合)", "retrieved": "2026-08-05"}
        cited = b.cite_shelf(entry, cites, "abc")
        s.eq(cited["url"], "https://bookwalker.jp/tag/14/?qcat=2&order=title&page=27",
             "a work the capture placed on a page cites that page of the shelf")
        s.eq(cited["page"], 27, "and the number is on the entry, not only inside the URL")
        s.check("bookwalker.jp/de" not in cited["url"] and "/series/" not in cited["url"],
                "never the shop's page for the book, which is what the operator was sent to")
        s.check(entry.get("url") is None, "the stored entry is not mutated")

        # THE COUNTER-CASES. Both are addresses nobody read, and inventing either is the fault.
        s.eq(b.cite_shelf(entry, cites, "unknown-id")["url"], "https://bookwalker.jp/tag/14/",
             "a work the capture does not list cites the shelf without a page")
        s.check("page" not in b.cite_shelf(entry, cites, "unknown-id"),
                "and states no page it cannot support")
        other = {"comparator": "yurinavi.com", "shelf": "百合", "retrieved": "2026-08-05"}
        s.check("url" not in b.cite_shelf(other, cites),
                "a comparator with no capture gains no url")


def state_claims(s):
    """WHAT THE PLATFORM SAYS, as a row instead of half a sentence.

    `state_basis` welded a source's claim to our own coverage, as in "no chapter for 2 days in what
    we hold, but the platform still marks the serialisation as running", so the page could render
    it only as a loose paragraph. Our half is `age_days`; this is the source's half.
    """
    rows = [{"platform": "カドコミ", "url": "https://comic-walker.com/detail/A",
             "retrieved": "2026-08-06", "state_claim": {"says": "running", "term": "ongoing"}},
            {"platform": "comici", "url": "https://comici.jp/b",
             "retrieved": "2026-08-05", "state_claim": {"says": "completed", "term": "完結"}},
            {"platform": "ニコニコ漫画", "url": "https://x.jp/c", "retrieved": "2026-08-05"}]
    got = b.state_claim_rows(rows)
    s.eq(len(got), 2, "a platform that states nothing produces no row")
    s.eq(got[0]["source"], "comici", "the stronger claim leads, whatever order the rows arrived in")
    s.eq(got[0]["term"], "完結", "the platform's own word is quoted rather than translated")
    s.eq(got[0]["says"], "completed", "beside our reading of it, which is the thing the page sorts")
    s.eq(got[1]["term"], "ongoing",
         "and カドコミ's English value stays English, because it is what the field said")
    s.eq(sorted(got[0]), ["read", "says", "source", "term", "url"],
         "the shape an evidence row has: who said it, what they said, and when it was read")
    s.eq(got[0]["read"], "2026-08-05", "the day that platform was read, not the day of the build")

    # THE COUNTER-CASE. A row with no address must not gain an empty one, which would render as a
    # link to nowhere in the same cell the evidence table links its read date from.
    bare = b.state_claim_rows([{"platform": "comici", "retrieved": "2026-08-05",
                                "state_claim": {"says": "completed", "term": "完結"}}])
    s.check("url" not in bare[0], "no address means no address field")
    s.eq(b.state_claim_rows([]), [], "no rows, no claims")


def series_addresses(s):
    """A ROW'S ADDRESS IS ITS NEWEST CHAPTER'S, so on GigaViewer it moves when the work publishes.

    The work-level addresses were captured and attached to the identifiers the works already answer
    to; what was left was for build.py to put one on the row. See docs/GAPS.md §21.
    """
    doc = {"record_type": "stable_address", "joins": [
        {"url": "https://comic-days.com/episode/1",
         "anchor": "web:https://comic-days.com/atom/series/9"},
        {"url": "https://comic-days.com/episode/1",
         "anchor": "web:https://comic-days.com/series/9/first_episode"},
        {"url": "https://ichijin-plus.com/episode/2",
         "anchor": "web:https://ichijin-plus.com/atom/series/7"},
    ]}
    got = b.work_level_addresses([doc])
    s.eq(got["https://comic-days.com/episode/1"],
         "https://comic-days.com/series/9/first_episode",
         "the reader address wins where the capture established one")
    # 一迅プラス, コミックガルド, MAGCOMI and webアクション serve no reader route, and two of them
    # answer it with a 200 carrying their front page. The feed is the shape every host has.
    s.eq(got["https://ichijin-plus.com/episode/2"],
         "https://ichijin-plus.com/atom/series/7",
         "and the feed address stands where the host serves no reader address")
    s.eq(len(got), 2, "one address per row, not one per anchor")
    s.eq(b.work_level_addresses([]), {}, "an absent capture is an empty answer, not a crash")

    # THE COUNTER-CASE THAT DECIDED THE GLOB. `data/queue/address-moved.yaml` sits under the same
    # filename prefix and attaches ANOTHER CHAPTER address, which is exactly what this field must
    # never hold: it would replace an address that moves with a second address that also moves.
    s.eq(b.work_level_addresses([{"record_type": "print_web_join", "joins": [
             {"url": "https://comic-days.com/episode/1",
              "anchor": "web:https://ichijin-plus.com/episode/5"}]}]),
         {}, "a repair capture is not a work-level address capture and is not read as one")

    # THE COUNTER-CASE. Falling back to the row's own address would put a chapter address in a
    # field whose whole purpose is to hold one that does not move.
    s.eq(b.series_address({"url": "https://comic-days.com/episode/3"}, got), None,
         "a row nothing has read an address for gets none")
    s.eq(b.series_address({"url": "https://comic-days.com/episode/3",
                           "feed_url": "https://comic-days.com/atom/series/4"}, got),
         "https://comic-days.com/atom/series/4",
         "the feed the row already holds answers where the capture has not reached it")
    s.eq(b.series_address({"url": "https://comic-fuz.com/manga/2474"}, got), None,
         "a row whose own address is already the work's needs no second copy of it")

    # THE PUBLISHER MAP THE INTERFACE READS. It ships inside feed/names.json now, and app.js looks
    # a name up by the string it has after stripping the cataloguing. The map is keyed BOTH ways
    # so a disagreement between the two normalisers costs a lookup the other key still answers.
    _pub_store = {"講談社": {"en": "Kodansha", "basis": "official-jp"},
                  "コミック百合姫": {"en": "Comic Yuri Hime", "basis": "official-jp"},
                  "百合コレ": {}}
    _rows = [{"print": [{"publisher": "[頒布]講談社", "imprint": "IDコミックス／Yuri-hime comics"},
                        {"publisher": "講談社 (発売)", "imprint": "百合コレ"},
                        {"publisher": "", "imprint": ""}]}]
    _map = b.publisher_map(_pub_store, {}, _rows)
    s.eq(_map.get("講談社", {}).get("en"), "Kodansha",
         "the name the interface asks with is a key")
    s.eq(_map.get("[頒布]講談社", {}).get("en"), "Kodansha",
         "and so is the catalogued string the cataloguing was stripped from")
    s.eq(_map.get("講談社 (発売)", {}).get("en"), "Kodansha",
         "a trailing distributor note is stripped to the same name")
    s.eq(_map.get("コミック百合姫", {}).get("en"), "Comic Yuri Hime",
         "an imprint spelled another way reaches its own entry")
    # THE COUNTER-CASES. A store record with no `en` is a name nobody has sourced, and §6 says it
    # renders as the Japanese it is; putting a key in the map with nothing behind it would make
    # the interface print an empty publisher instead.
    s.check("百合コレ" not in _map, "a store record with no English name ships no key")
    s.check("" not in _map, "an empty publisher field contributes no key")
    # A HOUSE WITH NO ENGLISH NAME IS STILL A HOUSE WITH AN ADDRESS, and this used to assert the
    # opposite. The map holds what could be RENDERED, which is the right rule for a rendering and
    # the wrong one for a link: 27 of the 164 houses have no English at all, so keying the
    # identifier off a rendering would have made exactly the smaller publishers unreachable, and
    # those are the ones a publisher page says most about. An entry carrying an id and no `en`
    # renders as the Japanese it always did.
    _bare = b.publisher_map({}, {}, _rows)
    s.check(all(not v.get("en") for v in _bare.values()),
            "an empty store renders no English for anybody")
    s.check(all(v.get("id") for v in _bare.values()),
            "and every key it does hold is there to carry an address")
    s.eq(b.publisher_map(_pub_store, {}, []), {}, "no rows map nothing")
    s.eq(_map.get("講談社", {}).get("basis"), "official-jp",
         "the basis travels with the name, so the interface can say whose name it is")

    # THE AUTHOR MAP ANSWERS WHERE THE PUBLISHER STORE CANNOT, because a work self-published
    # through a shop names its own author as its publisher and that name is already spelt once.
    # The map is keyed folded, which is how build.py holds it.
    _selfpub = b.publisher_map({}, {"嵩乃朔": {"romaji": {"macron": "Takano Saku"},
                                               "basis": "romaji"}},
                               [{"print": [{"publisher": "嵩乃朔", "imprint": "嵩乃朔"}]}])
    s.eq(_selfpub.get("嵩乃朔", {}).get("en"), "Takano Saku",
         "a self-publishing author is spelt once, by the store that already spells them")
    # ── THE PRINT BLOCK CARRIES BOTH PARTIES ───────────────────────────────────────────────────
    #
    # MADB writes `["[発売]講談社", "一迅社"]` and the source layer separates them. The block below
    # is what the interface reads, so the separation only holds if it survives this far: while it
    # did not, the volumes section and the evidence table each named 講談社 as the publisher of 132
    # works 一迅社 published, and agreed with each other while doing it.
    _rec = {"work_id": "C1", "publisher": "一迅社", "distributor": "講談社",
            "imprint": "Yurihime comics", "volume_count": 7, "last_published": "2024-06",
            "marketing_label": "yuri", "first_publication": {"date": "2022-01"}}
    _blk = b._print_block(_rec)
    s.eq(_blk["publisher"], "一迅社", "the publisher reaches the interface as the publisher")
    s.eq(_blk["distributor"], "講談社", "and the distributor as the distributor")
    s.eq(_blk["first"], "2022-01", "with the date the work was first published")
    # NEITHER FIELD IS WRITTEN EMPTY. A key present and blank is a fact stated about nobody, and
    # the interface would have to tell that apart from a field it has never been given.
    _plain = b._print_block({"work_id": "C2", "publisher": "太田出版", "imprint": "F×COMICS"})
    s.check("distributor" not in _plain, "a work nobody distributed carries no distributor key")
    s.check("publisher_basis" not in _plain, "and a named publisher needs no reason for a gap")
    # AND WHERE MADB NAMED ONLY A DISTRIBUTOR, the reason travels with the empty name.
    _gap = b._print_block({"work_id": "C3", "publisher": "", "publisher_basis": "not-stated",
                            "distributor": "講談社", "imprint": ""})
    s.eq(_gap["publisher_basis"], "not-stated", "an unnamed publisher says which kind of unnamed")
    s.eq(_gap["distributor"], "講談社", "beside the party MADB did name")

    # ── AND THE SHOP THAT ADMITTED THE WORK CAN BE REACHED FROM IT ─────────────────────────────
    #
    # `_shop_address` read a shop address out of `marketing_label_basis`, guarded on the one shop
    # whose records store the label's page and the shop's page at one URL. コミックシーモア
    # admitted 256 works, holds a page for every one of them, and 230 shipped rows could not reach
    # it. The guard was right about the fault it was written for and wrong about where the address
    # lives, so both halves are pinned here.
    s.eq(b._shop_address({"shop_url": "https://bookwalker.jp/de1/"}),
         "https://bookwalker.jp/de1/", "a record the shop supplied states its own address")
    s.eq(b._shop_address({"admitted_by": [{"comparator": "cmoa.jp",
                                           "shop_url": "https://www.cmoa.jp/title/1132/"}]}),
         "https://www.cmoa.jp/title/1132/",
         "and a bibliographic record admitted on a shelf carries the shop's page on the admission")
    # THE COUNTER-CASE THE OLD GUARD EXISTED FOR, and it has to keep passing: a record from the
    # national bibliography states its label's basis and no retailer sells anything here. Reading
    # that field put mediaarts-db.artmuseums.go.jp under a heading reading "Sold at" on 824 works.
    s.eq(b._shop_address({"marketing_label_basis": {
             "source": "madb", "url": "https://mediaarts-db.artmuseums.go.jp/id/C1"}}), None,
         "a catalogue's own page is not a shop, however much it looks like an address")
    s.eq(b._shop_address({"admitted_by": [{"comparator": "cmoa.jp"}]}), None,
         "and an admission that names no page produces no link rather than a guessed one")
    s.eq(b._print_block({"work_id": "C4", "admitted_by": [
             {"comparator": "cmoa.jp", "shop_url": "https://www.cmoa.jp/title/1132/"}]})["shop_url"],
         "https://www.cmoa.jp/title/1132/", "and the block a reader is given carries it")

    # ── A CREDIT LINE COMPOSED FROM THE STORE, AND THE ROLE BRACKET THAT USED TO FREEZE ONE ────
    #
    # `[著]安田剛助` was left as the analyser first wrote it, because the splitter peels the 著 off
    # and rebuilding from the parts alone would have dropped it. So the job survived and the name
    # did not: openBD stated ヤスダ コウスケ and the field went on reading `Cho Yasuda Takesuke`
    # while 安田剛助 on its own read `Yasuda Kōsuke`.
    _store = {"安田剛助": {"romaji": {"macron": "Yasuda Kōsuke"}, "en": "Kōsuke Yasuda"},
              "文尾文": {"romaji": {"macron": "Fumio Aya"}}}
    # The floor as feed/names.json ships it: keyed by the fold, spelling the runs the store does
    # not answer for. 著 is one of those. It names the job somebody did, so no name store holds it.
    _floor = {"著": "Cho", "編": "Hen", "安田剛助": "Yasuda Takesuke", "文尾文": "Bunbi Bun"}
    s.eq(b._recompose_credit("安田剛助", "Yasuda Takesuke", _store, {}, _floor), "Yasuda Kōsuke",
         "a bare name is composed from the store and not from the analyser's phrase")
    s.eq(b._recompose_credit("[著]安田剛助", "[ Cho ] Yasuda Takesuke", _store, {}, _floor),
         "[Cho]Yasuda Kōsuke",
         "and the same name inside a role bracket keeps the job and gets the current spelling")
    s.eq(b._recompose_credit("安田剛助 / 文尾文", "Yasuda Takesuke, Bunbi Bun", _store, {}, _floor),
         "Yasuda Kōsuke, Fumio Aya", "a line of two is composed from both records")
    # THE PHRASE MAP HOLDS TITLES AND CHAPTER NAMES TOO, and the splitter finds a name-shaped run
    # in plenty of them. Rewriting one would put a romanisation of part of a title in a map the
    # interface reads as a rendering of the whole of it, so the division has to account for the
    # whole field before anything is recomposed.
    s.eq(b._recompose_credit("100日後に咲く安田剛助（MFC）", "100 Nichigo ni Saku (MFC)",
                             _store, {}, _floor),
         "100 Nichigo ni Saku (MFC)",
         "a title the division cannot account for is left as the analyser wrote it")
    # AND WHERE THE STORE HAS NOTHING, THE PHRASE STANDS. Half a line composed and half romanised
    # whole reads as neither.
    s.eq(b._recompose_credit("[著]未知の人", "[ Cho ] Michi no Hito", _store, {}, _floor),
         "[ Cho ] Michi no Hito", "a person with no rendering leaves the phrase alone")
    # A ROLE THE FLOOR CANNOT SPELL IS NOT GUESSED AT EITHER. `_floored` answers None and the
    # phrase stands, rather than a hole appearing where the bracket was.
    s.eq(b._recompose_credit("[監修]安田剛助", "[ Kanshū ] Yasuda Takesuke", _store, {}, _floor),
         "[ Kanshū ] Yasuda Takesuke", "a job the floor does not spell leaves the phrase alone")
    s.eq(b._floored("[著]", _floor), "[Cho]", "the floor spells the notation around a name")
    s.eq(b._floored("[監修]", _floor), None, "and answers nothing for a run it does not hold")

    # ── THE BAR THE FLOOR RAISED, AND THE COUNTER-CASE THAT DECIDES WHERE IT APPLIES ───────────
    #
    # A line used to be left alone where any one person in it had no store record, and 60 of the
    # 70 fields in that state were held back by somebody ALREADY IN LATIN. `Magpie` has no record
    # because a Latin pen name is not a transliteration of anything, so no reading was ever going
    # to arrive and the residue was not going to fall. `divided` says the build has already ruled
    # this string a credit field, and there each person is spelt by the store, by their own Latin,
    # or by the floor, which is the order kari/app.js reads them in.
    _div = {"あとき": {"romaji": {"macron": "Atoki"}}}
    _dfloor = {"あとき": "Atoki", "水之江めがね": "Mizunoe Megane"}
    s.eq(b._recompose_credit("あとき / Magpie", "A Toki, Magpie", _div, {}, _dfloor, True),
         "Atoki, Magpie",
         "a person already in Latin no longer holds back the store's spelling of the rest")
    s.eq(b._recompose_credit("あとき / Ｍａｇｐｉｅ", "A Toki, Magpie", _div, {}, _dfloor, True),
         "Atoki, Magpie", "and a cataloguer's full-width typing of that name is folded, not read")
    s.eq(b._recompose_credit("あとき / 水之江めがね", "A Toki, Mizunoe Megane", _div, {}, _dfloor,
                             True),
         "Atoki, Mizunoe Megane", "a person the store has nothing for is spelt from the floor")
    # THE COUNTER-CASE, AND IT IS WHY `divided` EXISTS. This map holds chapter names and collection
    # titles beside credit lines, and the splitter finds name-shaped runs in plenty of them. With
    # the floor answering for anything, `月はタピオカみたいに` came back `Tsuki Wa Tapioka Mitaini`
    # with the particle capitalised and `特別編4` lost its translation. 1,573 of them changed.
    s.eq(b._recompose_credit("あとき / 水之江めがね", "A Toki, Mizunoe Megane", _div, {}, _dfloor),
         "A Toki, Mizunoe Megane",
         "and a string the build did not rule a credit field keeps the analyser's phrase")
    # AND A NAME NOTHING CAN SPELL STILL STOPS THE LINE, so a hole never reaches the map.
    s.eq(b._recompose_credit("あとき / 未知の人", "A Toki, Michi no Hito", _div, {}, _dfloor, True),
         "A Toki, Michi no Hito", "a name the floor has never spelled leaves the phrase alone")
    # THE KEY IS THE FOLD, WHICH IS HOW `credit_parts` IS RESOLVED. This function was handed the
    # raw-keyed store while the division beside it was resolved against the folded one, so a person
    # the splitter names 王月 よう and the store files 王月よう missed here and hit there.
    s.eq(b._person_shown("王月 よう", {"王月よう": {"romaji": {"macron": "Ōzuki Yō"}}}, {}),
         "Ōzuki Yō", "the store is asked with the key credit_parts is keyed on")

    edition_names(s)
    print_runs(s)
    volume_designations(s)
    volume_merge(s)


def volume_merge(s):
    """One volume list per print run, however many catalogues describe it.

    TWO CATALOGUES DESCRIBING ONE BOOK WERE TWO ROWS. MADB holds MURCIÉLAGO's volume 1 as `2014-04`
    with an ISBN and BOOK☆WALKER holds it as `2014-04-25` without one, and the page drew both under
    two headings. 20 works were in that state over 73 volume numbers.
    """
    _rec = lambda wid, vols, **kw: dict(                                           # noqa: E731
        {"work_id": wid, "title": {"ja": "作品"}, "sources": ["madb"],
         "volume_count": len(vols), "volumes": vols}, **kw)

    # ── ONE FACT AT TWO PRECISIONS IS ONE VOLUME ──────────────────────────────────────────────
    mad = _rec("C1", [{"number": "1", "isbn": "9784757542907", "published": "2014-04"},
                      {"number": "2", "isbn": "9784757542914", "published": "2014-04"}])
    bw = _rec("bw1", [{"number": "1", "published": "2014-04-25"},
                      {"number": "2", "published": "2014-04-25"},
                      {"number": "3", "published": "2014-09-25"}], sources=["bookwalker"])
    s.eq(b.merge_volumes([mad, bw]), 1, "one further record folded into the run")
    s.eq(len(mad["volumes"]), 3, "and the run is three volumes, not five")
    s.eq(bw["volumes"], [], "the record that did not lead carries none, so the gather returns one "
                            "list without the interface having to know a merge happened")
    s.eq(bw["volume_count"], 0, "and counts none, so the block above cannot take the larger of two "
                                "numbers describing one run")
    s.eq(mad["volumes"][0]["published"], "2014-04-25",
         "THE FINER DATE IS TAKEN, which is `isbndate.resolve` and is not decided again here")
    s.eq(mad["volumes"][0]["isbn"], "9784757542907", "with the ISBN only one catalogue states")
    s.eq(mad["volume_count"], 3, "and the count follows the numbering, every row of it numbered")

    # ── A DATE THAT DISAGREES IS A DIFFERENT BOOK ─────────────────────────────────────────────
    #
    # 君と綴るうたかた numbers a volume 6 in 2024-03 and another in 2025-01-13, with its own ISBN.
    # A second printing, which a string comparison cannot choose between, so both rows stand.
    one = _rec("C1", [{"number": "6", "isbn": "9784758026604", "published": "2024-03"},
                      {"number": "6", "isbn": "9784758028301", "published": "2025-01-13"}])
    b.merge_volumes([one])
    s.eq(len(one["volumes"]), 2, "a second printing years later is not folded into the first")

    # ── AND THE SAME NUMBER ON THE SAME DAY IS ONE VOLUME IN TWO EDITIONS ─────────────────────
    #
    # ささやくように恋を唄う holds volumes 9 to 12 twice with different ISBNs and the same date: a
    # standard and a special edition MADB gives no way to tell apart. `kari/app.js` folded these
    # and no longer does, because this is the same question asked of one record instead of two.
    two = _rec("C1", [{"number": "9", "isbn": "AAA", "published": "2021-06"},
                      {"number": "9", "isbn": "BBB", "published": "2021-06"}])
    b.merge_volumes([two])
    s.eq(len(two["volumes"]), 1, "two editions of one volume are one row")
    s.eq(two["volumes"][0]["editions"], ["AAA", "BBB"], "carrying both ISBNs, which is what the "
                                                        "reader is owed and what MADB cannot rank")

    # ── WHERE THE NUMBERING IS INCOMPLETE, A ROW COUNT IS NOT A LENGTH ────────────────────────
    #
    # 白き乙女の人狼 is five BOOK☆WALKER products with one number among them beside three numbered
    # MADB volumes. Nothing can say whether an unnumbered row IS one of the numbered ones, so
    # counting rows made the work eight volumes long where both catalogues say five.
    part = _rec("C1", [{"number": "1", "published": "2022-11"}], volume_count=3)
    loose = _rec("bw1", [{"published": "2022-11-30"}, {"published": "2023-05-31"}],
                 sources=["bookwalker"], volume_count=5)
    b.merge_volumes([part, loose])
    s.eq(part["volume_count"], 5,
         "the largest count a record states about itself stands where the numbering is incomplete")

    # ── AND A RECORD THAT NUMBERS NOTHING AND HOLDS SEVERAL IS ITS OWN RUN ────────────────────
    issues = _rec("bw1", [{"designation": "2017年1月号"}, {"designation": "2017年2月号"}],
                  sources=["bookwalker"])
    numbered = _rec("C1", [{"number": "1"}, {"number": "2"}])
    s.eq([[r["work_id"] for r in g] for g in b.print_runs([numbered, issues])],
         [["C1"], ["bw1"]],
         "so コミック百合姫's issues are never folded into a numbered run they cannot reconcile with")


def volume_designations(s):
    """The build still asks `facts/volumenumber/number` for it. §12.

    THE RULE MOVED AND ITS TEST WENT WITH IT. Twenty spellings of `volume 1` are asserted in
    `facts/volumenumber/test_number.py`, where exercising them costs no compiler at all. What is
    left here is that this module still asks, which is what a delegate can get wrong.
    """
    s.eq(b.volume_number({"number": "創刊号"}), 1,
         "the inaugural issue is the first one, so it sorts and counts as 1")
    s.eq(b.volume_number({"number": "上"}), None, "and 上 designates a half rather than numbering it")


def print_runs(s):
    """One book run drawn as one run, and a reissue still drawn as two.

    THIS IS THE CASE THAT WAS WRONG. MADB files a run under a second heading whenever the spine
    changes, so 捏造トラップ holds volumes 1, 2, 3 and 5 and 捏造トラップ : NTR holds 4 and 6.
    Identity joined them and the index counted six, and the work page still drew `4 volumes from
    2015` above `2 volumes from 2017`: a work split at a volume the catalogue merely filed
    elsewhere. Every case below is a real pair of records.

    AND THE COUNTER-CASE FIRST, because the split display is right for the case it was written for.
    """
    # ── THE COUNTER-CASE: A REISSUE STAYS TWO RUNS ────────────────────────────────────────────
    #
    # citrus is a ten volume run and a four volume 2015 reissue. Their numbering OVERLAPS, which is
    # what a reissue looks like from the catalogue, and folding them gave `vol. 1, vol. 1, vol. 2,
    # vol. 2` in one list. Tested before the merge, so a rule that merged everything fails here.
    _run = lambda wid, ja, nums, src="madb", **kw: dict(                           # noqa: E731
        {"work_id": wid, "title": {"ja": ja}, "volume_count": len(nums), "sources": [src],
         "volumes": [{"number": n} for n in nums]}, **kw)
    _citrus = [_run("C1", "citrus", ["1", "2", "3", "4"], first_publication={"date": "2013-03"}),
               _run("C2", "citrus", ["1", "2", "3", "4"], first_publication={"date": "2015-08"})]
    s.eq([[r["work_id"] for r in g] for g in b.print_runs(_citrus)], [["C1"], ["C2"]],
         "a reissue numbering the same volumes again is a run of its own")

    # AND THE SAME OVERLAP ACROSS TWO CATALOGUES MEANS THE OPPOSITE THING. MADB and BOOK☆WALKER
    # both hold MURCIÉLAGO volume 1 from スクウェア・エニックス in April 2014: one run described
    # twice. Merging it was tried on 2026-08-12 and withdrawn, because the two catalogues date one
    # book at two precisions and the fold drew a 52 row list, `vol. 1 April 2014` beside
    # `vol. 1 25 Apr 2014`. `merge_volumes` reconciles the volumes before this runs, so the reason
    # for the withdrawal is gone: the catalogue contradicting ITSELF is what means a second edition.
    _mur = [_run("C338361", "MURCIELAGO", ["1", "2", "3"]),
            _run("bw-15279", "MURCIÉLAGO -ムルシエラゴ-", ["1", "2", "3", "4"], src="bookwalker")]
    s.eq(len(b.print_runs(_mur)), 1,
         "two catalogues numbering the same volumes are one run, reconciled volume by volume")

    # ── AND THE CASE UNDER TEST: COMPLEMENTARY NUMBERING IS ONE RUN ───────────────────────────
    _ntr = [_run("C360665", "捏造トラップ", ["1", "2", "3", "5"],
                 first_publication={"date": "2015-07"}, publisher="一迅社",
                 imprint="百合姫コミックス", marketing_label="yuri"),
            _run("madb-t-de1410efb48e", "捏造トラップ : NTR", ["4", "6"],
                 first_publication={"date": "2017-05"}, publisher="一迅社",
                 distributor="講談社", imprint="")]
    _groups = b.print_runs(_ntr)
    s.eq(len(_groups), 1, "two headings holding volumes 1,2,3,5 and 4,6 are ONE run of one book")
    _blk = b.merged_print_block(_groups[0])
    s.eq(_blk["volumes"], 6, "six volumes, which is the count of DISTINCT numbers and not the sum")
    s.eq(_blk["first"], "2015-07", "dated from the earliest printing in the run")
    s.eq(_blk["work_id"], "C360665", "named for the record that speaks for the work")
    s.eq(_blk["work_ids"], ["C360665", "madb-t-de1410efb48e"],
         "AND CARRYING BOTH IDENTIFIERS; the volume list is drawn by matching works.json on these, "
         "so an id dropped here drops volumes 4 and 6 off the page")
    s.eq(_blk["distributor"], "講談社",
         "a field the primary record does not state is taken from the record that does")
    s.eq(_blk["imprint"], "百合姫コミックス", "and one the primary DOES state is its own")

    # THE SUM WOULD HAVE BEEN 5 HERE TOO. スクールゾーン runs 1 to 3 under one heading and 4 to 5
    # under `School zone = スクールゾーン`, where the sum and the union agree.
    _sz = [_run("C1", "スクールゾーン", ["1", "2", "3"]),
           _run("C2", "School zone = スクールゾーン", ["4", "5"])]
    s.eq(b.merged_print_block(b.print_runs(_sz)[0])["volumes"], 5,
         "1 to 3 and 4 to 5 is a run of five")

    # A NUMBER IS A NUMBER WHATEVER THE PADDING. 紅殻のパンドラ is numbered `01` to `21` and its
    # GHOST URN continuation `22` to `25`, so a text comparison would call a reissue numbered `04`
    # a continuation of a run holding `4` and fold a second printing into the first.
    _pad = [_run("C1", "紅殻のパンドラ", ["01", "02", "03"]),
            _run("C2", "紅殻のパンドラ", ["04", "05"])]
    s.eq(b.merged_print_block(b.print_runs(_pad)[0])["volumes"], 5,
         "padded and plain numbering continue one another")
    _reissue = [_run("C1", "作品", ["1", "2", "3"]), _run("C2", "作品", ["01", "02", "03"])]
    s.eq(len(b.print_runs(_reissue)), 2, "and a padded REPRINT of the same volumes is a run apart")

    # WHICH RECORD SPEAKS FOR THE RUN IS `print_precedence`, THE ORDER THE ROW'S TITLE COMES FROM.
    # An English edition sorting first would otherwise name a run of a Japanese work, which is the
    # fault that put `Day In, Day Out` on 明けても暮れても.
    _en = [_run("bw-1", "Day In, Day Out【English Ver.】", ["1"]),
           _run("bw-2", "明けても暮れても", ["2"])]
    s.eq(b.merged_print_block(b.print_runs(_en)[0])["work_id"], "bw-2",
         "the work's own language names the run, whatever the identifiers sort like")

    # A RECORD THAT NUMBERS NOTHING MAKES NO CLAIM THAT CAN CONFLICT, so it joins rather than
    # standing alone as an unnumbered heading beside a numbered one.
    _bare = [_run("C1", "作品", ["1", "2"]), dict(_run("C2", "作品", []), volume_count=1)]
    s.eq(len(b.print_runs(_bare)), 1, "an unnumbered record joins the run it was filed under")
    s.eq(b.merged_print_block(b.print_runs(_bare)[0])["volumes"], 2,
         "and cannot be counted into it, so the largest stated count stands")

    # ONE RECORD IS UNCHANGED APART FROM THE LIST OF IDENTIFIERS, which every reader now goes
    # through. This is the 470 print rows that were never in question.
    _one = b.merged_print_block([_ntr[0]])
    s.eq(_one["volumes"], 4, "a lone record still states its own count")
    s.eq(_one["work_ids"], ["C360665"], "and answers the id question with a list of one")


def edition_names(s):
    """An edition takes the English of the work it is an edition of, in both directions.

    THIS SHIPPED WITH NO TEST, which is how the asymmetry below survived: the graft stripped the
    edition and looked the bare form up against keys nobody had stripped.
    """
    import unicodedata

    def fold(x):
        return unicodedata.normalize("NFKC", str(x)).replace(" ", "").lower()

    def graft(work, store):
        by_fold = {fold(k): v for k, v in store.items()}
        return b._inherit_edition_name(work, {}, store, by_fold, fold)

    named = {"球詠": {"en": "Tamayomi", "basis": "romaji"}}
    s.eq(graft("球詠【単話版】", named)["en"], "Tamayomi (single chapters)",
         "an edition takes its work's English and says which edition it is")
    s.eq(graft("球詠【単話版】", named)["en_of_edition_from"], "球詠",
         "and records the title it took it from, so a count can tell the two apart")
    s.eq(graft("球詠", named), {}, "the plain title itself is left alone")

    # THE OTHER DIRECTION, because a name belongs to the work and not to whichever record holds it.
    only_edition = {"心の声が漏れやすいメイドさん【単話版】":
                    {"en": "The Maid Whose Thoughts Slip Out (single chapters)", "basis": "translated"}}
    got = graft("心の声が漏れやすいメイドさん", only_edition)
    s.eq(got["en"], "The Maid Whose Thoughts Slip Out",
         "a plain title takes an edition's name with that edition's own marker removed")

    # BOTH SIDES STRIPPED THE SAME WAY. `without_edition_apparatus` takes the genre tag off as well
    # as the marker, so an edition reduced to a form its own base never had and went looking for it.
    # The base is written 【百合】 and all, and the two could not meet.
    tagged = {"LatteComiコミックアンソロジー【百合】":
              {"en": "LatteComi Comic Anthology: Yuri", "basis": "translated"}}
    s.eq(graft("LatteComi コミックアンソロジー【百合】（単話版）", tagged)["en"],
         "LatteComi Comic Anthology: Yuri (single chapters)",
         "an edition meets a base that carries a tag the stripper also removes")

    # AND A WORK NOBODY HAS NAMED GRAFTS NOTHING, rather than an empty string a reader would meet.
    s.eq(graft("球詠【単話版】", {"球詠": {"basis": "romaji"}}), {},
         "a base with no English of its own hands none across")
    s.eq(graft("知らない作品【単話版】", named), {}, "and a work with no base at all is left alone")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "build"))
