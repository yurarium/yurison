#!/usr/bin/env python3
"""pass4_analyser.py: the fallback that reads a name when no dictionary can.

COVERS = ['adapters/names/pass4_analyser.py']

Almost every case here is a wrong reading this project shipped. They are kept because the analyser
fails SILENTLY when it fails: it returns something plausible, never an error.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import pass4_analyser as p4


def main(s):
    # Script tests the rest of the module leans on.
    s.check(p4.has_kanji("田口"), "kanji detected")
    s.check(not p4.has_kanji("タグチ"), "katakana is not kanji")
    s.check(p4.is_kana_ch("ア"), "katakana is kana")
    s.check(not p4.is_kana_ch("A"), "a latin letter is not kana")
    s.eq(p4.kata("ゆり"), "ユリ", "readings are normalised to katakana")

    # A LETTER READ AS A UNIT was a real defect: Sudachi reads M as メートル and L as リットル, so
    # furigana appeared over Latin. The letter's own NAME is the only legitimate reading.
    s.check("M" in p4.LETTER_NAME, "single letters have their own names")
    s.eq(p4.LETTER_NAME["V"], "ブイ", "V reads as its name, which is why Vチューバー is allowed")
    s.eq(len(p4.LETTER_NAME), 26, "all 26 letters are covered, not a handful")

    # PARTICLE SOUND. 114 readings carried ハ where the word is spoken ワ, because は as a particle
    # is not は as a syllable. The fix is part-of-speech, and the table records the two cases.
    s.eq(p4.PARTICLE_SOUND.get("は"), "ワ", "は as a particle sounds ワ")
    s.eq(p4.PARTICLE_SOUND.get("へ"), "エ", "へ as a particle sounds エ")

    # THE ANALYSER'S OWN VOCABULARY IS NOT A READING. Asked for 々 or 彡 alone it answers キゴウ,
    # its name for the category 補助記号. エストレーヤ★彡 shipped as `Esutorēya★Kigō` and 依々恋々
    # as `Ikigō Renren`, a person and a title wearing the word "symbol" as a sound. A symbol that
    # answers with ITSELF is a different thing and still passes, which is what keeps ー working.
    try:
        from sudachipy import Dictionary, SplitMode
        _tk, _md = Dictionary().create(), [SplitMode.C, SplitMode.A]
        s.check(p4.per_char(_tk, _md, "々") != "キゴウ", "々 is not read as the word for symbol")
        s.check(p4.per_char(_tk, _md, "彡") != "キゴウ", "彡 is not read as the word for symbol")
        s.eq(p4.per_char(_tk, _md, "ー"), "ー", "a symbol that reads as itself keeps its reading")
        s.eq(p4.per_char(_tk, _md, "〇"), "レイ", "〇 is a numeral and reads レイ")
        s.eq(p4.per_char(_tk, _md, "激"), "ゲキ", "an ordinary kanji is untouched")
    except ImportError:
        s.skip("sudachipy absent")

    # ── A WORD BREAK MAY NOT FALL ON A DOUBLING ──────────────────────────────────────────────
    #
    # っ doubles the consonant that FOLLOWS it, so a token ending in one cannot be the end of a
    # word: whatever it doubles is in the next token. Sudachi cuts まっぴるま into まっ and ぴるま,
    # and the romaniser wrote what it was handed. `Shiranaima Ppiruma` is a word beginning on a
    # doubled consonant, which no Japanese word does. 63 phrases were spelled that way, including a
    # person: はっとりみつる as `Ha Ttori Mitsuru`.
    try:
        from sudachipy import Dictionary, SplitMode
        _tk2, _md2 = Dictionary().create(), [SplitMode.C, SplitMode.A]
        for ja, want in (("知らないまっぴるま", "シラナイマッピルマ"),
                         ("ばっどがーる", "バッド ガール"),
                         ("はっとりみつる", "ハットリ ミツル"),
                         ("ぬっく", "ヌック")):
            got, _ = p4.analyse_best(_tk2, ja, _md2)
            s.eq(got, want, f"{ja} keeps its doubling and the sound it doubles in one word")

        # BOTH SIDES OF THE BOUNDARY, because Sudachi cuts either way. It ends a token on the っ in
        # まっ|ぴるま and it OPENS one with the っ of the quotative って, which came out `Suki Tte`.
        for ja, want in (("好きって気付いてほしい", "スキッテ キヅイテ ホシイ"),
                         ("あたし達って付き合ってるよね", "アタシタチッテ ツキアッテル ヨ ネ")):
            got, _ = p4.analyse_best(_tk2, ja, _md2)
            s.eq(got, want, f"{ja}: a token opening on って joins the word it doubles into")

        # AND THE COUNTER-CASE, because a rule that glued everything would read as a pass here. A
        # break that falls nowhere near a っ is left where the analyser put it, and a っ INSIDE a
        # token was never the problem.
        got, _ = p4.analyse_best(_tk2, "小春と湊", _md2)
        s.check(got and " " in got, "an ordinary two-word title still divides")
        got, _ = p4.analyse_best(_tk2, "ぎゅっとにぎって", _md2)
        s.eq(got, "ギュット ニギッテ",
             "and a word whose own っ is medial divides from the next word as before")
    except ImportError:
        s.skip("sudachipy absent")

    # An override table exists because some readings are simply known: 私 in a title is watashi,
    # and the analyser preferred ワタクシ until told otherwise.
    s.check(isinstance(p4.READING_OVERRIDE, dict), "an override table exists")
    s.check(len(p4.READING_OVERRIDE) > 0, "and it is populated")
    # 抱かれたい女 WAS READ イダカレタイ, reported 2026-08-10. だく is holding a person and いだく is
    # harbouring a feeling, and SudachiDict answers イダク for every inflection.
    s.eq(p4.READING_OVERRIDE.get("抱か"), "ダカ", "the passive stem of 抱く is だか")
    # AND THE COUNTER-CASE THAT KEPT THE RULE OFF THE LEMMA. 元カノに幻想を抱くな is in this corpus
    # three times and is げんそうをいだく, which is the sense the entry above is not about.
    for surface in ("抱く", "抱い", "抱き"):
        s.eq(p4.READING_OVERRIDE.get(surface), None,
             f"{surface} is not overridden: 幻想を抱く and 抱き枕 are the words it would break")
    try:
        from sudachipy import Dictionary, SplitMode
        _tk = Dictionary().create()
        s.eq(p4.analyse(_tk, "抱かれたい女", SplitMode.C), "ダカレタイ オンナ",
             "so the reported title reads だかれたい")
        s.eq(p4.analyse(_tk, "元カノに幻想を抱くなバーカ", SplitMode.C),
             "モトカノ ニ ゲンソウ ヲ イダクナ バーカ",
             "and the counter-case in the same corpus still reads いだく")
        # THE TABLE HAS TO REACH WHAT WAS ALREADY READ. It is applied while a reading is produced,
        # and `fill_missing` only produces one for a record that has none, so five records held
        # イダカレタイ after the entry existed.
        s.check(p4.overruled(_tk, "抱かれたい女", "イダカレタイ オンナ", SplitMode.C),
                "a stored reading holding the analyser's own answer is stale")
        s.check(not p4.overruled(_tk, "抱かれたい女", "ダカレタイ オンナ", SplitMode.C),
                "and one already carrying the table's answer is not")
        s.check(not p4.overruled(_tk, "元カノに幻想を抱くなバーカ",
                                 "モトカノ ニ ゲンソウ ヲ イダクナ バーカ", SplitMode.C),
                "a token the table says nothing about never makes a record stale")
    except ImportError:
        s.skip("sudachipy absent")

    # A SECOND TABLE FOR WORDS THE DICTIONARY DOES NOT HOLD, whose reading belongs to the whole word.
    # Reported 2026-08-12 as `Tsuiteru Gyaru to Mieteru Kage Kya`, from ツイてるギャルとミエてる陰キャ.
    s.check(isinstance(p4.COMPOUND_READING, dict), "a compound table exists")
    s.eq(p4.COMPOUND_READING.get("陰キャ"), "インキャ", "陰キャ is いんキャ, not かげキャ")
    # THE KEY THAT COULD NOT LIVE IN THE PER-MORPHEME TABLE, which is why there are two of them.
    s.eq(p4.READING_OVERRIDE.get("陰"), None,
         "陰 alone is not overridden: 陰で, 陰口 and 光と陰 are all かげ")
    # Longest first, so a longer word beats a shorter one that prefixes it.
    s.eq(p4.COMPOUND_KEYS, sorted(p4.COMPOUND_READING, key=len, reverse=True),
         "keys are tried longest first")

    # THE SPLIT IS DONE ON THE STRING, BEFORE THE ANALYSER, and this is the case that forced it.
    # Sudachi reads 陰キャギャル as 陰 + キャギャル, so no run of whole tokens joins to 陰キャ and a
    # lookahead over its output finds nothing. Cutting the string first also leaves ギャル a token.
    s.eq([seg for seg in p4._compound_segments("陰キャギャルでもイキがりたい！")],
         [("陰キャ", True), ("ギャルでもイキがりたい！", False)],
         "a compound is cut out of the string whatever the analyser would have done with it")
    s.eq(p4._compound_segments("光と陰"), [("光と陰", False)],
         "a string with no compound in it comes back whole")
    s.eq(p4._compound_segments("陰キャと陽キャ"),
         [("陰キャ", True), ("と", False), ("陽キャ", True)],
         "two compounds in one string are both cut out")

    try:
        from sudachipy import Dictionary, SplitMode
        _tk = Dictionary().create()
        s.eq(p4.analyse(_tk, "ツイてるギャルとミエてる陰キャ", SplitMode.C),
             "ツイテル ギャル ト ミエテル インキャ", "the reported title reads いんキャ")
        s.eq(p4.analyse(_tk, "陰キャギャルでもイキがりたい！", SplitMode.C),
             "インキャ ギャル デ モ イキガリタイ！",
             "and so does the one whose tokens straddle the word")
        # THE COUNTER-CASES, each an ordinary word this must not touch. A table that fixed one title
        # and broke three would be worse than the wrong reading it replaced.
        for src, want in (("陰で笑う", "カゲ デ ワラウ"),
                          ("陰口をたたく", "カゲグチ ヲ タタク"),
                          ("光と陰", "ヒカリ ト カゲ"),
                          ("陰陽師", "オンミョウジ")):
            s.eq(p4.analyse(_tk, src, SplitMode.C), want, f"{src} is untouched")
        # A STORED READING ASSEMBLED FROM THE CHARACTERS IS STALE, so the refresh reaches records
        # written before the table existed. This is the whole of how the fix reaches the corpus.
        s.check(p4.overruled(_tk, "ツイてるギャルとミエてる陰キャ",
                             "ツイテル ギャル ト ミエテル カゲ キャ", SplitMode.C),
                "a reading holding かげ キャ is stale")
        s.check(not p4.overruled(_tk, "ツイてるギャルとミエてる陰キャ",
                                 "ツイテル ギャル ト ミエテル インキャ", SplitMode.C),
                "and one already carrying いんキャ is not")
        s.check(not p4.overruled(_tk, "光と陰", "ヒカリ ト カゲ", SplitMode.C),
                "a title the table says nothing about is never stale")
    except ImportError:
        s.skip("sudachipy absent")

    # Credit lines are not titles. 原作／宮澤伊織 was once romanised wholesale, producing
    # "Gensaku Kigō Miyazawa Iori": the role is a label to translate, the name is a name.
    s.check(p4.is_credit_line("原作／宮澤伊織"), "a credit line is recognised by its role marker")
    s.check(not p4.is_credit_line("君の名は"), "an ordinary title is not a credit line")

    # ONE ROLE VOCABULARY. This file kept eleven words of its own while `inputs.ROLES` held forty,
    # so a role the splitter knew and this did not let the whole field into the store as a person:
    # はいむらきよたか(キャラクターデザイン) shipped in names.json with the role inside the name.
    for line in ("はいむらきよたか(キャラクターデザイン)", "石田可奈(キャラクターデザイン)",
                 "広輪凪(カバーイラスト)", "ｆｉｎｉｔｅ(校正)", "潮一葉 ネーム"):
        s.check(p4.is_credit_line(line), f"a role welded to a name is a credit line: {line}")
    # AND THE COUNTER-CASE THAT KEEPS THE SINGLE CHARACTERS OUT. 作, 画, 絵 and 著 are what pen
    # names are built from, so a substring test on them would take a person with it.
    for who in ("作田ハジメ", "はいむらきよたか", "絵日はな", "文月ナオ", "阿部潤"):
        s.check(not p4.is_credit_line(who), f"and a pen name is not one: {who}")
    # A SINGLE CHARACTER IN A BRACKET IS THE ROLE AND NOTHING ELSE. `index[].c` reached this pass
    # for the first time on 2026-08-09, and the bibliography writes a print credit as `[著]名前`.
    # None of the tests above catches it: the string is short, holds no separator and holds no
    # multi-character role, so three fields entered the store as people and the analyser read 著 as
    # チョ. `[チョ]KENTOOKAYAMA` was recorded as somebody's reading and `readings are stored as
    # kana` caught it. 378 records were in that shape once the collection was fed in.
    for line in ("[著]KENTO OKAYAMA", "[著]ねこうめ", "[作]いくたはな", "[編]乙女☆妄想族",
                 "コミックニュータイプ(編)",
                 # A DOUBLED DELIMITER IS STILL ONE DELIMITER, and the outer pair of `[[著]]` holds
                 # `[著`, which is not a role. `a person is spelled one way` caught this one: the
                 # phrase map said `[ [ Cho ] ] Tsubaki Tori Ka` and the store said
                 # `[[Cho]]Tsubaki Torika`, one credit spelled two ways on the same page.
                 "[[著]]椿木とりか"):
        s.check(p4.is_credit_line(line), f"a bracketed role is a credit line: {line}")
    # AND THE COUNTER-CASE THE BRACKET RULE COULD BREAK, which is the whole reason a bracket holding
    # kana is read as a furigana gloss elsewhere. 博（ひろ） is a name with its own reading printed
    # beside it and 壇九（TANJIU) is a name beside the Latin the artist also goes by.
    for who in ("博（ひろ）", "壇九（TANJIU)", "太陽まりい"):
        s.check(not p4.is_credit_line(who), f"and a bracket holding no role is not: {who}")

    # A ・ IS THE ONE PATH THAT LOADS THE INTERPUNCT MODULE, and nothing above takes it: every
    # string here either holds a role or holds no separator, so `_interpunct` was never called and
    # the import inside it went on naming `names.interpunct` for a week after 93469a1 moved that
    # file to `facts/credit`. The ImportError reached build.py's naming block, which catches
    # everything and prints one line, so every author reading, every division and every publisher
    # name stopped being filled while the build reported `automatic reading pass skipped`.
    s.check(p4.is_credit_line("くろば・Ｕ"),
            "an interpunct nobody has ruled on still reads as a credit line")
    _ip, _fold = p4._interpunct()
    s.check(not p4.is_credit_line("くろば・Ｕ", {_fold("くろば・Ｕ"): _ip.ONE}),
            "and the corpus ruling that it names one person is what makes it a name")

    s.check(p4.has_japanese("第1話"), "japanese detected")
    s.check(not p4.has_japanese("Chapter 1"), "plain english is not japanese")

    # Unihan gives on-yomi. It must return kana or nothing, never a romanised string, because
    # everything downstream derives romanisation FROM the kana (NAMES-PLAN §8.1).
    on = p4.unihan_on("山")
    s.check(on is None or all(p4.is_kana_ch(c) or c in "ー・" for c in on),
            f"a Unihan reading is kana or absent, got {on!r}")

    # THE FAILURE `fell_back` CANNOT SEE. Sudachi reports trouble only when it has no reading at
    # all. With no entry for a compound it reads each character as its own token, and each reading
    # is defensible alone: 葬焔 came back ソウ ホノオ, an on beside a kun, and nothing had failed so
    # nothing was flagged. Both halves of the test are needed, because adjacent single-character
    # tokens are ordinary: 100日後 is 日 + 後 reading ニチ ゴ, and there are 43 such pairs in the
    # catalogue against 4 that mix kinds.
    class FakeTok:
        def __init__(self, pairs):
            self.pairs = pairs

        def tokenize(self, s, mode=None):
            return [type("M", (), {"surface": (lambda self, v=a: v),
                                   "reading_form": (lambda self, v=b: v)})()
                    for a, b in self.pairs]

    s.check(p4.unrecognised_compound(FakeTok([("葬", "ソウ"), ("焔", "ホノオ")]), "葬焔"),
            "a compound split into an on reading and a kun reading is flagged")
    s.check(not p4.unrecognised_compound(FakeTok([("日", "ニチ"), ("後", "ゴ")]), "日後"),
            "two on readings side by side are how a compound normally reads")
    s.check(not p4.unrecognised_compound(FakeTok([("職場", "ショクバ")]), "職場"),
            "a 重箱 reading the analyser knows arrives whole and cannot be caught this way")
    s.check(not p4.unrecognised_compound(FakeTok([("私", "ワタシ"), ("の", "ノ"), ("本", "ホン")]),
                                         "私の本"),
            "characters separated by a particle are not a compound")

    # A VOLUME IS NOT A CHAPTER. 巻 was missing from the counter list, so ４巻 第３９話 matched the
    # bare-number branch as chapter four and the real chapter fell into the subtitle and was
    # romanised: "Ch. 4 Maki Dai 39Wa". 53 chapter names begin with a volume number.
    plain = lambda t: t                                                      # noqa: E731
    s.eq(p4.chapter_en("４巻 第３９話「瞑目アリア」", plain), 'Vol. 4, Ch. 39 “瞑目アリア”',
         "the volume is read off the front and the chapter inside is read as a chapter")
    s.eq(p4.chapter_en("2巻 第26話", plain), "Vol. 2, Ch. 26", "and full-width digits are the same")

    # THE SAME LABEL, WRAPPED. A bracket around a chapter label is punctuation, and CHAPTER_PAT
    # anchors at the start, so a wrapper made it miss and the whole thing was romanised. 186
    # phrases read "( Dai 18Wa ) Shippai no Tatsujin" and "[Dai 100Wa]shin Awasete".
    s.eq(p4.chapter_en("【第100話】心合わせて", plain), "Ch. 100 心合わせて",
         "a chapter in a lenticular bracket is a chapter")
    s.eq(p4.chapter_en("（第18話）失敗の達人", plain), "Ch. 18 失敗の達人",
         "and one in full-width parentheses is the same statement")
    s.eq(p4.chapter_en("[#49]Pair", plain), "Ch. 49 Pair",
         "a hash label in half-width brackets too")

    # A BRACKET INSIDE A BRACKET. One class of closing marks let the match end at the first bracket
    # of any kind, so 【第132話(1)】 stopped inside its own parenthesis and the label reached readers
    # as `Ch. 132 (1 ]`: an opening round bracket closed by a square one.
    s.eq(p4.chapter_en("【第132話(1)】", plain), "Ch. 132 (1)",
         "a part marker in parentheses survives the brackets around the whole label")
    s.eq(p4.chapter_en("【第100話】（前編）", plain), "Ch. 100 (前編)",
         "and what follows the wrapper is still what follows it, NFKC-folded like the rest")

    # A CHAPTER NUMBERED IN KANJI IS STILL A NUMBER. NFKC turns ７ into 7 and leaves 七 alone, so
    # 第七話 missed the structure branch and was romanised whole as `Dai Nana Hanashi`: the word
    # "chapter" spelled out in Latin as though it were the chapter's name.
    s.eq(p4.chapter_en("第七話", plain), "Ch. 7", "a chapter numbered in kanji is a chapter")
    s.eq(p4.chapter_en("第十二話 ためし", plain), "Ch. 12 ためし", "including the teens")
    s.eq(p4.chapter_en("第二十三話", plain), "Ch. 23", "and the twenties")
    # AND A WORD THAT HAPPENS TO HOLD THOSE CHARACTERS IS LEFT ALONE, which is what keeps the rule
    # from eating titles: 千歳 is a name and 十七歳 is an age, neither is a chapter number.
    s.eq(p4.digits_for_kanji("千歳の話"), "千歳の話",
         "kanji digits loose in a subtitle are words, not a number")
    s.eq(p4.digits_for_kanji("十七歳の夏"), "十七歳の夏", "and an age is not a chapter")
    s.eq(p4._serialisation().kanji_number("x"), None,
         "a string that is not a number reads as none, asked of the one producer")

    # AN ELLIPSIS IS ONE CHARACTER AND SUDACHI SPELLS IT OUT. `…` tokenises into three morphemes:
    # one carrying the character and two carrying an EMPTY surface and a full-width dot each. The
    # surface-first rule is written `if surf and …`, so the two empty ones fell through to the
    # reading branch and contributed a dot apiece: `そして…` read `ソシテ…．．` and romanised
    # `Soshite.....`. There is no text at a zero-width span.
    try:
        from sudachipy import Dictionary as _D, SplitMode as _S
    except ImportError:
        s.skip("sudachipy absent")
        return
    _tk2, _md2 = _D().create(), [_S.C, _S.A]
    plain2 = lambda x: p4.romanise_ja(_tk2, _md2, x)                        # noqa: E731
    s.eq(p4.romanise_ja(_tk2, _md2, "そして…"), "Soshite...",
         "an ellipsis romanises as one ellipsis")
    s.eq(p4.romanise_ja(_tk2, _md2, "転生してしまった…"), "Tenshō Shite Shimatta...",
         "and does at the end of a sentence")

    # NO SPACE BEFORE A CLOSING MARK, IN EITHER WIDTH. The spacing sets held the full-width marks
    # alone while `chapter_en` NFKC-folds its input before it reaches them, so by the time a
    # subtitle arrived every ！ was a `!` and matched nothing: 526 of 9,018 phrases shipped with a
    # space in front of a closing mark.
    s.eq(p4.chapter_en("第34話 我慢しなくて…いいですか!?", plain2), "Ch. 34 Gaman Shinakute... Iidesu Ka!?",
         "an ASCII closing mark takes no space before it either")
    s.eq(p4.chapter_en("第18話 シャネルが勝ったら…", plain2), "Ch. 18 Shaneru ga Kattara...",
         "and an ellipsis NFKC has folded to three dots is not spaced apart")

    # A WORD THE ANALYSER READS CONFIDENTLY AND WRONGLY, corrected before it is asked.
    s.eq(p4.romanise_ja(_tk2, _md2, "八尺様リバイバルV"), "Hasshakusama Ribaibaru V",
         "八尺様 is the yōkai はっしゃくさま, not the ヤサカ of 八尺瓊")

    # A PLATFORM'S ROW INDEX IS NOT THE WORK'S CHAPTER NUMBER. コミックDAYS prefixes its own row number: "100.第94話しんゆうのたのみ" is row 100 carrying chapter 94, and it rendered
    # "Ch. 100 . Dai 94 Hanashi ...", wrong in the number as well as the romanising.
    s.eq(p4.chapter_en("100.第94話しんゆうのたのみ", plain), "Ch. 94 しんゆうのたのみ",
         "the work's own label outranks the list position it sits at")
    s.eq(p4.chapter_en("1.第1話", plain), "Ch. 1", "even where the two agree")
    s.eq(p4.chapter_en("07Chapter.12第6話-2", plain), "Ch. 6-2",
         "a row index carrying its own word is still a row index")

    # THE PREFIX MUST BE INDEX MATERIAL AND NOTHING ELSE. That is what keeps a real title safe:
    # 恋する第3惑星 has 第3 in it and is not chapter three of anything.
    s.eq(p4.chapter_en("恋する第3惑星", plain), None,
         "a title that happens to contain 第N is not a chapter label")

    # THE FALLBACK AGAIN. Where what follows the prefix is not a chapter label, the prefix stays.
    s.eq(p4.chapter_en("12.普通の話", plain), "Ch. 12 普通の話",
         "a bare number keeps its place when nothing better is claimed")
    s.check("." not in (p4.chapter_en("12.普通の話", plain) or "").split(" ", 2)[-1][:1],
            "and the separator belongs to neither the number nor the subtitle")

    # THE FALLBACK, and it is the reason this is safe. A bracket whose contents are not a chapter
    # is left exactly as it was, so a wrapper nobody anticipated costs nothing.
    s.eq(p4.chapter_en("【お知らせ】更新", plain), None,
         "a notice in a bracket is not a chapter and is not made into one")
    s.eq(p4.chapter_en("（前編）はじまり", plain), "Part 1 はじまり",
         "and a bracketed part marker still reads as the part it is")
    s.eq(p4.chapter_en("3巻発売フェア", plain), "Vol. 3 発売フェア",
         "a volume followed by something that is not a chapter keeps the volume")
    s.eq(p4.chapter_en("第12話 テスト", plain), "Ch. 12 テスト",
         "a chapter with no volume is unchanged")

    # A CIRCLED DIGIT IS A PART MARKER. NFKC folds it into the number beside it, so Step.14① came
    # out "Step.141", which reads as chapter one hundred and forty-one.
    s.eq(p4.part_marks("Step.14①"), "Step.14 (1)", "the part is bracketed, not absorbed")
    s.eq(p4.part_marks("第90話②"), "第90話 (2)", "wherever it sits")
    s.eq(p4.part_marks("no marker here"), "no marker here", "and a name without one is untouched")
    s.eq(p4.chapter_en("第90話②", plain), "Ch. 90-2",
         "a chapter-shaped name still hyphenates its part, which is the form that sorts")

    # THE CACHE INVALIDATES ITSELF. Every entry in phrases.yaml is derived, and the file was
    # written once per string and never revisited, so a fix to the renderer never reached what it
    # had already rendered. Three faults in one day came from that, each correct and invisible
    # until the file was emptied by hand. The fingerprint has to move when the renderer moves, and
    # stay put when it does not; a version number somebody remembers to bump is the same bug.
    before = p4.renderer_fingerprint()
    s.eq(p4.renderer_fingerprint(), before, "the same renderer fingerprints the same")
    was = p4.EXTRA_EN["番外編"]
    try:
        p4.EXTRA_EN["番外編"] = "Side story"
        s.check(p4.renderer_fingerprint() != before,
                "changing what a chapter renders as changes the fingerprint")
    finally:
        p4.EXTRA_EN["番外編"] = was
    s.eq(p4.renderer_fingerprint(), before, "and putting it back puts the fingerprint back")


    # LATIN IS READ AS ITSELF. Sudachi lowercases it, returning `jk` for `ＪＫ`, so `ＪＫすぷらっしゅ！`
    # was stored with a reading of `jk ス プラッ シュ！`: a case the analyser invented.
    s.eq(p4.latin_reading("ＪＫ"), "JK", "full-width letters fold to the same letters, cased as written")
    s.eq(p4.latin_reading("S"), "S", "half-width Latin, which was always right, is unchanged")
    s.eq(p4.latin_reading("ＦＬＯＳ　ＣＯＭＩＣ"), "FLOS COMIC", "and a run of them, spaces folded too")
    s.eq(p4.latin_reading("すぷらっしゅ"), None, "kana is not Latin, so the analyser answers for it")
    s.eq(p4.latin_reading("×"), None, "nor is a symbol carrying no letters")
    s.eq(p4.latin_reading(""), None, "and an empty surface reads as nothing")

    # A KANA NAME IS PASS 1's, AND THE AUTOPILOT IS WHAT RUNS EVERY TIME. `fill_missing` only ever
    # queued a name with NO reading, so every kana name arriving after the last hand-run pass 1 got
    # an analyser reading for a question that has no lookup in it. 181 author names were in that
    # state and three came out wrong: an analyser reading running text takes は as the particle, so
    # はうあゆ went to the site as Wa u Ayu and はとぼし as Wa Toboshi, under the artists' own work,
    # and あーねすと gained a sokuon nobody wrote.
    s.eq(p4.wants_reading("はうあゆ", {"reading": "ワ ウ アユ", "reading_basis": "analyser"}), True,
         "a kana name carrying a guess is outstanding work, not a filled slot")
    s.eq(p4.wants_reading("東雲水生", {"reading": "シノノメ スイセイ", "reading_basis": "analyser"}),
         False, "while a name with kanji keeps its guess, because nothing here can better it")
    s.eq(p4.wants_reading("東雲水生", {"reading": "シノノメ スイセイ", "reading_basis": "analyser"},
                          refresh=True), True, "unless a refresh was asked for, which is the flag")
    # AND THE COUNTER-CASE, which is why the rule is scoped to authors. は is the topic particle in
    # a title and is said wa, so on six kana titles the analyser is right where the surface is not.
    # A title is a sentence; a pen name is not.
    s.eq(p4.wants_reading("きみはシュガー", {"reading": "キミ ワ シュガー",
                                             "reading_basis": "analyser"}, kind="titles"), False,
         "a kana title keeps the analyser's particle, because there は really is said wa")
    s.eq(p4.wants_reading("きみはシュガー", {"reading": "キミ ワ シュガー",
                                             "reading_basis": "analyser"}, kind="authors"), True,
         "and the same string as a pen name does not, which is the whole distinction")
    s.eq(p4.wants_reading("はうあゆ", {"reading": "ハウアユ", "reading_basis": "surface"}), False,
         "a name pass 1 has already answered is left alone, or every build would churn the file")
    s.eq(p4.wants_reading("林家志弦", {"reading": "ハヤシヤ シズル", "reading_basis": "stated"}),
         False, "and a reading a publisher stated is never replaced by a machine")
    s.eq(p4.wants_reading("あとき", {}), True, "a name with nothing recorded wants a reading")

    # A REFUTATION IS A DECISION, NOT AN EMPTY SLOT, and it looked like one from here. curate.py
    # removes the reading and records why, and the point of that record is that nothing can replace
    # it: 時一二 is not a Japanese name and the National Diet Library holds no kana for it on
    # purpose. The autopilot refilled ten of them on the next build, so 古川楊也 came back as
    # フルカワ ヨウナリ hours after a reviewer wrote down that it cannot be read.
    s.eq(p4.wants_reading("古川楊也", {"reading_refuted": "a different person's name"}), False,
         "a name a reviewer could not settle is finished, not waiting")
    s.eq(p4.wants_reading("古川楊也", {"reading_refuted": "a different person's name"},
                          refresh=True), False, "and a refresh does not reopen it either")

    # The rule it is corrected BY is pass 1's own, called rather than copied: two producers of one
    # fact is what STANDING-INSTRUCTIONS §3 is about, and this fact already had a home.
    import pass1_kana as p1
    s.eq(p1.surface_fields("はうあゆ", "authors")["reading"], "ハウアユ",
         "the name's own kana, which is the whole of the answer")
    s.eq(p1.surface_fields("はうあゆ", "authors")["reading_basis"], "surface",
         "recorded as the surface it is")
    s.eq(p1.surface_fields("東雲水生", "authors"), None,
         "and a name with kanji is not this rule's business")

    # ── THE CAVEAT GOES IN THE READING'S SLOT ─────────────────────────────────────────────────
    #
    # This pass says one thing about every name it touches, and it used to say it in `note`, which
    # is where the argument for an ENGLISH name lives. 196 titles held a curated translation with a
    # sentence about SudachiDict where its reasoning should have been, and 1,693 records carried it
    # in total. `reading_note` is the slot, and `curate.py` spells out why the two exist apart.
    #
    # ASKED OF THE SOURCE, because the two write sites sit deep inside functions that need a
    # tokenizer and a store to reach. What must never come back is an assignment putting this
    # sentence into `note`, and that is a statement about the text of the module.
    src = pathlib.Path(p4.__file__).read_text(encoding="utf-8")
    s.check("analysers are weakest on pen names and coinages" in p4.ANALYSER_CAVEAT,
            "the sentence is named once and not typed at each site")
    s.eq(src.count('rec["note"] = '), 0,
         "no site assigns the English's note, which is what put a reading's doubt in it")
    s.eq(src.count('rec.setdefault("reading_note", ANALYSER_CAVEAT)'), 2,
         "both write sites offer it to the reading's own slot")
    # AND IT DEFERS. A reading somebody has already reasoned about outranks a sentence about an
    # analyser, and NAMES-PLAN §5d admits this pass precisely because it labels itself a guess.
    s.check('rec["reading_note"] = ' not in src,
            "offered with setdefault, so an argument already written there survives")

if __name__ == "__main__":
    sys.exit(testkit.run(main, "pass4_analyser"))
