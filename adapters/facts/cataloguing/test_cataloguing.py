#!/usr/bin/env python3
"""facts/cataloguing: taking a catalogue's punctuation off a name without taking the book's subtitle with it.

COVERS = ['adapters/facts/cataloguing/__init__.py',
          'adapters/facts/cataloguing/checks.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
import cataloguing as m                                                 # noqa: E402
from cataloguing import checks as c                                     # noqa: E402


def main(s):
    # ── THE PARALLEL TITLE COMES OFF AND IS KEPT ──────────────────────────────────────────────
    #
    # ` = ` introduces a 並列タイトル transcribed from the book's own title page. Storing the whole
    # string made cataloguing punctuation part of the name, and two records of one work then
    # compared unequal: several pairs shipped as duplicates and were merged by hand.
    s.eq(m.title_proper("リリィシステム = LILY SYSTEM"), "リリィシステム",
         "the parallel title comes off the name")
    s.eq(m.parallel_title("リリィシステム = LILY SYSTEM"), "LILY SYSTEM",
         "and is kept, being the publisher's own English name")
    s.eq(m.parallel_title("ふつうの子"), "", "a title with no parallel title yields none")
    s.eq(m.title_proper(""), "", "and an empty name is empty")
    s.eq(m.title_proper(None), "", "as is no name at all")

    # ── THE SUBTITLE STAYS ON THE NAME ────────────────────────────────────────────────────────
    #
    # ` : ` introduces other title information, which is what the publisher printed about the book.
    # A rule that cut it would be deleting content, so the only thing this module does with a
    # colon is stop reading the parallel title at it.
    s.eq(m.title_proper("恋愛遺伝子XX : 完全版"), "恋愛遺伝子XX : 完全版",
         "a colon introduces other title information and the name keeps it")
    s.eq(m.other_title_information("ギャルメイドと悪役令嬢 : おじょーさま、お世話させていただきます"),
         "おじょーさま、お世話させていただきます", "and the subtitle is readable on its own")
    s.eq(m.title_proper("ギャルメイドと悪役令嬢 : おじょーさま、お世話させていただきます"),
         "ギャルメイドと悪役令嬢 : おじょーさま、お世話させていただきます",
         "while the stored name is still the whole of what the publisher printed")

    # BOTH MARKS AT ONCE, which is the shape the first version of this split could not read. The
    # parallel half was tested for Japanese text over everything after the equals sign, so the
    # subtitle behind the colon made `Cinnamon` look Japanese and six records kept their
    # punctuation. The parallel title ENDS at the colon.
    FULL = "シナモン = Cinnamon : 人外×人間百合アンソロジー"
    s.eq(m.title_proper(FULL), "シナモン : 人外×人間百合アンソロジー",
         "the parallel title comes off and the Japanese subtitle stays")
    s.eq(m.parallel_title(FULL), "Cinnamon", "with the English read only as far as the colon")
    s.eq(m.other_title_information(FULL), "人外×人間百合アンソロジー", "and the subtitle named")
    s.eq(m.areas(FULL), ("シナモン : 人外×人間百合アンソロジー", "Cinnamon", "人外×人間百合アンソロジー"),
         "which is the whole of what the string states")

    # AND WHOSE SUBTITLE IT IS DEPENDS ON THE LANGUAGE. A tagline in English follows an English
    # name and belongs to it. `リリウム・テラリウム` is what the work is called; attaching
    # `GIRL meets GIRL OMNIBUS STORY` to that would be a name nobody writes, and dropping it would
    # be discarding something the publisher printed. It goes with the English.
    ED = "リリウム・テラリウム = Lilium Terrarium : GIRL meets GIRL OMNIBUS STORY ＆ ILLUSTRATION by ED"
    s.eq(m.title_proper(ED), "リリウム・テラリウム", "a Latin subtitle does not join the Japanese name")
    s.eq(m.parallel_title(ED), "Lilium Terrarium : GIRL meets GIRL OMNIBUS STORY ＆ ILLUSTRATION by ED",
         "it stays with the English name it describes, so nothing is thrown away")
    s.eq(m.title_proper("ザ・ファブル = THE FABLE : The silent-killer is living in this town"),
         "ザ・ファブル", "which is how the work is actually named")

    # ── COUNTER-CASES: EVERY SHAPE THAT MUST NOT SPLIT ────────────────────────────────────────
    #
    # Each of these is a real record. The rule was wrong in this direction before and pinning the
    # refusals is worth more than pinning the splits.
    # THE REFUSAL IS SHOWN ON A BOOK NOBODY HAS LOOKED UP, because 一迅社 has since settled this one:
    # it prints ルミナス＝ブルー, one name with a fullwidth sign inside it, so the spaced ASCII form a
    # cataloguer wrote now resolves to the house's spelling.
    s.eq(m.title_proper("ひかり = やみ"), "ひかり = やみ",
         "a parallel half holding Japanese is not a translation")
    s.eq(m.title_proper("ルミナス = ブルー"), "ルミナス＝ブルー",
         "and a sign the publisher prints inside a name is restored to the form they print")
    s.eq(m.parallel_title("ルミナス = ブルー"), "", "so no English name is taken from it")
    # THE RULE IS UNCHANGED AND IS SHOWN ON A BOOK NOBODY HAS LOOKED UP. These two shapes used to be
    # pinned on School zone and ニニンがシノブ伝ぷらす, which a publisher has since settled, so the
    # rule needs its own examples or the ruling would read as the rule loosening.
    s.eq(m.title_proper("Moonlit garden = 月の庭"), "Moonlit garden = 月の庭",
         "the same shape the other way round is refused for the same reason")
    s.eq(m.title_proper("あいうえお = A=B+C"), "あいうえお = A=B+C",
         "a second equals sign leaves no way to say where the name ends")

    # WHERE A PUBLISHER HAS SETTLED WHAT THE STRING CANNOT. The refusals above stand because nothing
    # in the characters says which half is the name. MAG Garden prints スクールゾーン 1 and KADOKAWA
    # prints ニニンがシノブ伝ぷらす 1, so for these two books the answer is known and recorded.
    s.eq(m.title_proper("School zone = スクールゾーン"), "スクールゾーン",
         "a reversed pair the publisher has settled takes the name the book carries")
    s.eq(m.parallel_title("School zone = スクールゾーン"), "School zone",
         "and the Latin half is its parallel title")
    s.eq(m.title_proper("ニニンがシノブ伝ぷらす = 2×2=SHINOBUDEN+"), "ニニンがシノブ伝ぷらす",
         "and two signs are no obstacle once somebody has read the cover")
    s.eq(m.title_proper("X = Y = Z"), "X = Y = Z", "so nothing is guessed")
    s.eq(m.title_proper("ある話 : 副題 = SUBTITLE"), "ある話 : 副題 = SUBTITLE",
         "ISBD writes the parallel title before the other title information, never after it")
    s.eq(m.title_proper("2×2=SHINOBUDEN+"), "2×2=SHINOBUDEN+",
         "an equals sign with no spaces around it is inside a name, not marking one")
    # AND THE COST OF GETTING THAT WRONG, which the first version of this rule paid. It matched on
    # a bare `=`, so eight titles in release 1.2.18 were stored truncated at the sign: `X=love`
    # became `X` and `18=80` became `18`.
    s.eq(m.title_proper("X=love"), "X=love", "so a title built around the sign keeps all of itself")
    s.eq(m.title_proper("18=80"), "18=80", "and so does one that is arithmetic")
    s.eq(m.title_proper("A:B"), "A:B", "and a colon with no spaces is not ISBD punctuation either")
    s.eq(m.title_proper(" = LILY SYSTEM"), "= LILY SYSTEM",
         "a mark with nothing before it introduces nothing")
    s.eq(m.title_proper("灰色の季節、箱庭で = : Gray season,in the garden"),
         "灰色の季節、箱庭で = : Gray season,in the garden",
         "and an empty area between two marks is a transcription with a piece missing, not a name")

    # THE ORIGINAL SPACING SURVIVES. Everything but the parallel title is copied out of the string
    # as written, so a subtitle nobody asked about is not reformatted on its way past.
    s.eq(m.title_proper("ある作品  :  副題"), "ある作品  :  副題", "odd spacing is left as it was")
    s.eq(m.title_proper("ある作品 = A WORK  :  副題"), "ある作品  :  副題",
         "and is still left as it was when something else on the line was removed")

    # ── THE EDITION STATEMENT, AND WHY IT IS A LIST AND NOT A PATTERN ─────────────────────────
    #
    # 恋愛遺伝子XX is "The Romance Gene XX" and 恋愛遺伝子XX : 完全版 had no English at all, so a
    # translated title was stranded in Japanese by a two-character suffix. The reader interface
    # glosses the marker beside the base work's name, and this is the same closed set.
    s.eq(m.edition_statement("恋愛遺伝子XX : 完全版"), "完全版",
         "a reissue marker from the closed set is recognised")
    s.eq(m.edition_statement("総合タワーリシチ : 新装版"), "新装版", "as is another member of it")
    s.eq(m.edition_statement("シロップ = syrup : 社会人百合アンソロジー"), "",
         "and a subtitle is not one, however much it looks like apparatus")
    s.eq(m.edition_statement("恋愛遺伝子XX"), "", "a title with no colon states no edition")
    s.eq(m.title_proper("恋愛遺伝子XX : 完全版"), "恋愛遺伝子XX : 完全版",
         "recognising it changes nothing about the name, which is still what was catalogued")
    # THE VOCABULARY IS THE INTERFACE'S. A marker the backend recognised and `EDITION_EN` could not
    # name would be a row the reader is shown in Japanese with no explanation.
    s.check("完全版" in m.EDITIONS and "分冊版" in m.EDITIONS and "雑誌掲載版" in m.EDITIONS,
            "the set is the one kari/app.js glosses")
    s.check("短編集" not in m.EDITIONS,
            "and a collection is not a reissue, so it stays part of the name")

    # ── the count that lives beside the rule ────────────────────────────────────────────────────
    #
    # It was in check.py, which put the rule in one file and the measure of the rule in another.
    n = c.titles_carrying_cataloguing_punctuation
    s.eq(n(["\u604b\u611b\u907a\u4f1d\u5b50XX : \u5b8c\u5168\u7248"]), 1,
         "an edition statement is a catalogue's apparatus and counts")
    s.eq(n(["\u3042\u308b\u540d\u524d = Another Name"]), 1,
         "and so does an equals sign in a title nobody has ruled on yet")
    s.eq(n(["\u30ae\u30e3\u30eb\u30e1\u30a4\u30c9\u3068\u60aa\u5f79\u4ee4\u5b22 : "
            "\u304a\u3058\u3087\u30fc\u3055\u307e\u3001\u304a\u4e16\u8a71\u3055\u305b"
            "\u3066\u3044\u305f\u3060\u304d\u307e\u3059"]), 0,
         "a subtitle after the same colon is content, which is what the closed set buys")

    # A SIGN A PUBLISHER PRINTS IS NOT PUNCTUATION, and RULED is asked of the WHOLE title. Every
    # entry there was read off a house's own catalogue page, so the answer is a person's and the
    # pattern's job is the next one nobody has looked up.
    for ruled in m.RULED:
        s.eq(n([ruled]), 0, f"a ruled title is not counted: {ruled}")
    s.eq(n([next(iter(m.RULED)) + " = X"]), 1,
         "and a ruled title with something appended is a different string, so it is counted again")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "cataloguing"))
