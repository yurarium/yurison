#!/usr/bin/env python3
"""kana.py: reading to romanisation, title casing, and furigana alignment.

Every case below is one this project got wrong and shipped. They are kept as tests so the fix
cannot be undone by a later tidy-up, which is what STANDING-INSTRUCTIONS §2 asks for.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import kana


def main(s):
    # Three styles, all derived from the kana and none from each other (NAMES-PLAN §8.1). That is
    # what makes the reader's choice of style possible at render time.
    # romanise() returns lower case; title_case() decides capitalisation. Keeping them separate is
    # what lets a title and a personal name be cased by different rules from the same reading.
    s.eq(kana.romanise("ユウリ", "macron"), "yūri", "macron style")
    s.eq(kana.romanise("ユウリ", "double"), "yuuri", "double-vowel style")
    s.eq(kana.romanise("ユウリ", "plain"), "yuri", "plain style")
    s.eq(kana.title_case(kana.romanise("ユウリ", "macron")), "Yūri", "cased for display")

    # Script tests, which the English-only invariant leans on.
    s.check(kana.has_kanji("君の名は"), "kanji detected")
    s.check(not kana.has_kanji("ユウリ"), "katakana is not kanji")
    s.check(kana.has_kana("ゆり"), "kana detected")
    s.check(kana.has_latin("Vチューバー"), "latin detected inside a mixed string")

    # Case conversion both ways, since readings are stored as kana and rendered from them.
    s.eq(kana.to_hiragana("ユウリ"), "ゆうり", "katakana to hiragana")
    s.eq(kana.to_katakana("ゆうり"), "ユウリ", "hiragana to katakana")

    # TITLE CASE. Particles stay lower case, but the rule was once greedy enough to lower-case 名
    # in 君の名は, and punctuation broke it so that (watakushi Ni) came out instead of (Watakushi ni).
    s.eq(kana.title_case("kimi no na wa"), "Kimi no Na wa", "particles stay down, words go up")
    s.eq(kana.title_case("(watakushi ni)"), "(Watakushi ni)",
         "a word after an opening bracket is still the start of a word")
    s.eq(kana.title_case("yuri", particles=False), "Yuri", "particles=False still capitalises")

    # PUNCTUATION INSIDE A PERSONAL NAME STARTS A NEW ELEMENT. R-指定 was rendered `R - Shitei` off
    # a reading an analyser had divided at the hyphen, and once that division was retired the same
    # name read `R-shitei`. A name has no sentence structure, so each segment takes a capital.
    s.eq(kana.title_case("r-shitei", particles=False), "R-Shitei", "a hyphen begins an element")
    s.eq(kana.title_case("anjinneko@sōsaku", particles=False), "Anjinneko@Sōsaku",
         "and so does an @ between a handle and the tag after it")
    s.eq(kana.title_case("2c=garoa", particles=False), "2C=Garoa",
         "a digit is not a letter and does not take the capital away from what follows")
    s.eq(kana.title_case("shin'ichi", particles=False), "Shin'ichi",
         "an apostrophe is a syllable break inside one element, which Shin'Ichi is not")
    s.eq(kana.title_case("RDーsounds", particles=False), "RDーsounds",
         "a prolongation mark carries no sound and opens nothing")
    s.eq(kana.title_case("kimi no na-wa"), "Kimi no Na-wa",
         "a title keeps the old rule, where a hyphen is punctuation and not a new element")

    # A PERSON'S NAME IS ROMANISED FROM THEIR READING, SO THE DIVISION LIVES IN THE READING. Both
    # of these were reported by the project owner, months apart, as the same complaint: the name is
    # rendered as one English word and is not one. Nothing here can divide them. What these pin is
    # that once a source states the division the romanisation follows for free, so the whole job is
    # sourcing the space and never spelling it.
    def person(reading):
        return kana.title_case(kana.romanise(reading, "macron"), particles=False)

    s.eq(person("タイヨウマリイ"), "Taiyōmarii",
         "the media-arts catalogue files this artist closed up, and this is what that produces")
    s.eq(person("タイヨウ マリイ"), "Taiyō Marii",
         "and the National Diet Library's heading divides them, which is 太陽 まりい")
    s.eq(person("イガラシユミコ"), "Igarashiyumiko",
         "a kana surface folded to katakana states no division either")
    s.eq(person("イガラシ ユミコ"), "Igarashi Yumiko",
         "the same heading answers the first thing anybody asked of this project")

    # THE COUNTER-CASE, kept from the round that tried to derive a division instead of sourcing it.
    # 冬木先輩 is one unbroken kanji run and `フユキ センパイ` divides it correctly; a rule that put
    # the division back by counting morae cut it 冬木先 | 輩. The alignment below is pinned again
    # further down; what is pinned here is that a divided reading of a name still romanises as two
    # words and nothing in this round changed that.
    s.eq(person("フユキ センパイ"), "Fuyuki Senpai",
         "a division a source states romanises as two words, whatever the surface looks like")

    # ALIGNMENT. Furigana are placed per token with backtracking; a whole-string fallback used to
    # destroy good parses when one character could not be read.
    spans = kana.align("君の名は", "きみのなは")
    s.check(spans is not None, "alignment returns spans for a readable title")
    if spans:
        flat = "".join(t for t, _ in spans)
        s.eq(flat, "君の名は", "the spans reassemble the exact surface")
        rd = "".join(r or kana.to_hiragana(t) for t, r in spans)
        s.eq(rd, "きみのなは", "the spans reassemble the exact reading")
        s.check(all(r is None or kana.has_kana(r) for _, r in spans),
                "a ruby reading is kana or absent, never romaji")

    # A reading that cannot be aligned must fail cleanly rather than inventing a pairing.
    # A SPACED SURFACE AGAINST A SPACED READING. The solver takes the first split that fits and
    # tries the shortest first, so with the spaces stripped 狗之餌 took one kana and 廃狼 took the
    # other eight. The boundary is written on both sides and is used.
    s.eq(kana.align("狗之餌 廃狼", "イヌノエサ ハイロウ"),
         [("狗之餌", "イヌノエサ"), (" ", None), ("廃狼", "ハイロウ")],
         "a boundary written on both sides places the split")
    s.eq(kana.align("宮原 都", "ミヤハラ ミヤコ"),
         [("宮原", "ミヤハラ"), (" ", None), ("都", "ミヤコ")],
         "and does so where a naive split would still have fitted")
    # COUNTS MUST MATCH. A reading is word-separated and a surface is not, so spaces that do not
    # correspond say nothing and the whole-string search has to run as before.
    s.check(kana.align("ゆりでなるえすぽわーる", "ユリ デ ナル エスポワール"),
            "a reading spaced where the surface is not still aligns")
    # PUNCTUATION THE READING KEEPS IS ANCHORED ON. Letting a mark consume nothing let the kanji
    # run beside it swallow the mark: 翡翠 read ひ while 北 read すい、きた.
    s.eq(kana.align("翡翠、北", "ヒスイ、キタ"),
         [("翡翠", "ヒスイ"), ("、", None), ("北", "キタ")],
         "a mark the reading states pins the runs either side of it")
    # AND A READING THAT DROPS IT STILL ALIGNS, which is why the strict pass is a preference and
    # not a rule. 「」 appear in the surface and in neither reading.
    s.check(kana.align("「触れたい」は恋の始まり", "フレタイワコイノハジマリ"),
            "a reading that drops the surface's marks still aligns")
    # A SURFACE SPACED BEFORE A MARK. The reading's spaces come out, so a run of ` ～` has one
    # character the reading can spell and one it cannot. Requiring the whole run made the strict
    # pass fail and the kanji run beside it swallow the mark.
    s.eq(kana.align("百合探偵少女 ～朱理推～", "ユリ タンテイ ショウジョ   ～ アカリ スイ ～"),
         [("百合探偵少女", "ユリタンテイショウジョ"), (" ～", None),
          ("朱理推", "アカリスイ"), ("～", None)],
         "a run spaced before a mark still anchors on the mark")
    bad = kana.align("君の名は", "ぜんぜんちがう")
    s.check(bad is None or "".join(t for t, _ in bad) == "君の名は",
            "a mismatched reading does not corrupt the surface")

    # A READING THAT REPEATS ITS OWN TEXT ANNOTATES NOTHING. Latin is a READ run here on purpose,
    # so `紗痲 Fallin' Jail` reading `シャマ Fallin' Jail` paired Fallin with Fallin and shipped
    # `紗痲しゃま FallinFallin' JailJail` on the page. A reader reported it.
    s.eq(kana.align("紗痲 Fallin' Jail", "シャマ Fallin' Jail"),
         [("紗痲", "シャマ"), (" ", None), ("Fallin", None), ("'", None), (" ", None),
          ("Jail", None)],
         "a Latin run whose reading is itself takes no ruby")

    # FURIGANA OVER A LATIN WORD IS NOT FURIGANA. Queentopia came back under キュー, which is a
    # kanji run's reading spent on the run beside it. pass4_analyser has applied this rule to its
    # own spans throughout; align is the second producer of the same fact and did not.
    s.check(kana.align("Queentopia", "キュー") is None,
            "a Latin word takes no ruby, whatever the solver found to put over it")
    s.eq(kana.align("Queentopia学園", "クイーントピアガクエン"),
         [("Queentopia学園", "クイーントピアガクエン")],
         "and Latin abutting a kanji is ONE run, which is a different question and keeps its ruby")

    # A SET THAT NO LONGER SPELLS THE READING IS DROPPED WHOLE, which is the stated fallback for
    # `ruby spells the reading` applied by the producer, because build.py can only apply it to
    # spans it loaded from the store. `BOMBSHELLS 天野…` reads ボムシェルズアマノ…, the solver gave
    # BOMBSHELLS one kana and 天野 the other seven, and 天野 carried むしぇるずあまの on the page.
    s.check(kana.align("BOMBSHELLS 天野", "ボムシェルズアマノ") is None,
            "ruby that cannot spell its own reading is not published at all")

    # ── AN ANCHOR MUST NOT MATCH INSIDE THE WORD BEFORE IT ──────────────────────────────────
    # Both of these spell their reading and both shipped nothing, because `implausible ruby spans`
    # is what caught them and the gate stopped the readings being stored at all. が matched the ガ
    # inside メガミ, so 女神 kept メ and 今日 swallowed ミガキョウ; を matched the オ inside マオウ.
    s.eq(kana.align("私の女神が今日も推せる", "ワタシ ノ メガミ ガ キョウ モ オセル"),
         [("私", "ワタシ"), ("の", None), ("女神", "メガミ"), ("が", None), ("今日", "キョウ"),
          ("も", None), ("推", "オ"), ("せる", None)],
         "an anchor takes the ガ that is its own word and not the one inside メガミ")
    s.eq(kana.align("私が魔王を倒す", "ワタシ ガ マオウ ヲ タオス"),
         [("私", "ワタシ"), ("が", None), ("魔王", "マオウ"), ("を", None), ("倒", "タオ"),
          ("す", None)],
         "and を takes the ヲ, leaving 魔王 the マオウ it needs")
    # OKURIGANA IS THE COUNTER-CASE AND IT IS IN THE SAME TITLE. 推 under オ followed by せる taking
    # セル puts the anchor inside 推せる, which is allowed because it reaches the end of that word.
    # A rule demanding an anchor be a whole word refuses this one and every title in 【 】.
    s.eq(kana.align("推せる", "オセル"), [("推", "オ"), ("せる", None)],
         "kana trailing a stem inside one word are okurigana and still anchor there")
    s.eq(kana.align("【完結】冬木先輩と夏井", "【カンケツ】 フユキ センパイ ト ナツイ"),
         [("【", None), ("完結", "カンケツ"), ("】", None), ("冬木先輩", "フユキセンパイ"),
          ("と", None), ("夏井", "ナツイ")],
         "and a bracket the analyser folded into the word beside it still anchors")
    # THE PINNED SEARCH NEVER TURNS A REFUSAL INTO A RENDER. It finds a placement here, and the
    # placement puts `girl` over `girl`, which is the fault a reader reported on 紗痲 Fallin' Jail.
    s.check(kana.align("能面 battle girl納言", "ノウメン battle girl ナゴン") is None,
            "a title the loose search cannot place is still not placed")

    # THE COUNTER-CASES, and they are why Latin and digits are READ runs rather than anchors: a run
    # nothing can place makes the whole title unalignable.
    s.eq(kana.align("100日後に", "ヒャクニチゴニ"), [("100日後", "ヒャクニチゴ"), ("に", None)],
         "digits inside a kanji run keep the reading that spells them out")
    s.eq(kana.align("Vチューバー", "ブイチューバー"), [("V", "ブイ"), ("チューバー", None)],
         "and a single letter keeps the reading that is its own name")
    s.eq(kana.LETTER_NAME["V"], "ブイ", "which is the closed set of 26 that decides it")

    # JUKUGO-RUBY. Splitting a compound's reading across its characters, so じょう sits over 情
    # rather than over 純情. Accepted only when it is certain, because a reading placed over the
    # wrong character is worse than one placed over the whole word: the reader cannot tell.
    s.eq(kana.jukugo_split("純情", "ジュンジョウ"), [("純", "ジュン"), ("情", "ジョウ")],
         "a compound splits where each part is a reading of its character")
    s.eq(kana.jukugo_split("学校", "ガッコウ"), [("学", "ガッ"), ("校", "コウ")],
         "and 促音便 is a sound change, not a different word")
    s.eq(kana.jukugo_split("雨夜", "アマヨ"), None,
         "a split the table cannot support is declined rather than guessed")
    s.eq(kana.jukugo_split("純", "ジュン"), None, "one character is already its own ruby")
    s.eq(kana.jukugo_split("純情", ""), None, "and no reading splits into nothing")
    # THE PROPERTY THAT MATTERS. Whatever comes back must still spell the reading, or the ruby
    # contradicts the romanisation built from the same string.
    for word, rd in (("純情", "ジュンジョウ"), ("悪役", "アクヤク"), ("令嬢", "レイジョウ")):
        got = kana.jukugo_split(word, rd)
        s.eq("".join(x[1] for x in got), rd, f"the split of {word} still spells its reading")
        s.eq("".join(x[0] for x in got), word, f"and still spells {word}")

    # A TITLE THAT FAILS TO ALIGN GETS NO FURIGANA AT ALL, so one unmatched character costs the
    # whole line. 169 of 842 kanji titles were in that state, and between them two causes account
    # for it: a particle spelled as it sounds, and punctuation the reading drops.
    s.eq(kana.align("あの子は優しすぎる。", "アノコワヤサシスギル。"),
         [("あの", None), ("子", "コ"), ("は", None), ("優", "ヤサ"), ("しすぎる。", None)],
         "the topic は reads ワ, and still anchors")
    s.check(kana.align("うさぎはかく語りき", "ウサギワカクカタリキ"),
            "including where it sits inside a longer run of kana")
    s.check(kana.align("この恋を星には願わない", "コノコイオホシニワネガワナイ"),
            "and を reading オ does the same")
    s.check(kana.align("「触れたい」は恋の始まり", "フレタイワコイノハジマリ"),
            "a reading that drops the surface's brackets still anchors")
    s.check(kana.align("「触れたい」は恋の始まり", "「フレタイ」ワコイノハジマリ"),
            "and one that keeps them is matched as written")

    # THREE MORE WAYS THE SAME CHARACTER IS WRITTEN ONE WAY AND READ ANOTHER, each of which cost
    # a whole title its furigana.
    s.check(kana.align("ゆりづくしの教室で", "ユリズクシノキョウシツデ"),
            "四つ仮名: づ and ず are one sound, and a reading records the sound")
    s.check(kana.align("アラサー美女は地味女に餌付けされる", "アラサアビジョワジミオンナニエズケサレル"),
            "a long vowel written ー and spelled out as a vowel are the same reading")
    s.check(kana.align("阿佐ヶ谷サキュバス同人物語", "アサガヤサキュバスドウニンモノガタリ"),
            "ヶ in a place name is read が, not as a small ケ")
    s.check(kana.align("竹ヶ原", "タケガハラ") and kana.align("竹ヶ原", "タケカハラ"),
            "and it takes either voicing, because both occur in real names")

    # A CHARACTER NOBODY CAN SEE. Three titles are stored with げ written as け followed by
    # U+3099 COMBINING VOICED SOUND MARK. The mark is not kana, so it fell out of every comparison
    # and left the surface one character longer than its reading, and the title lost its furigana.
    s.check(kana.align("銀玉の価値を上\u3051\u3099る方法", "ギンダマノカチヲアゲルホウホウ"),
            "a decomposed kana aligns the same as the composed one it renders as")

    # THE COMPARISON IS ASYMMETRIC AND ITS CALLERS MUST KNOW IT. A surface は may sound like わ;
    # a surface わ is never written は. Passing reading and surface the wrong way round rejected
    # correct ruby on three titles while the alignment that produced it was right.
    spans = kana.align("あの子は優しすぎる。", "アノコワヤサシスギル。")
    s.check(kana.ruby_spells(spans, "アノコワヤサシスギル。"),
            "ruby carrying the surface's は spells a reading that records ワ")
    s.check(kana.ruby_spells(kana.align("阿佐ヶ谷サキュバス同人物語", "アサガヤサキュバスドウニンモノガタリ"),
                             "アサガヤサキュバスドウニンモノガタリ"),
            "and ruby over ヶ spells a reading that records ガ")

    # WHICH TWO VOWELS MAKE THE LONG ONE. 女王 is ジョ オ ウ. Taking the オ into ジョ leaves the ウ
    # as a syllable of its own and gives jōu, which romanises nothing: the long vowel is オウ.
    s.eq(kana.romanise("ジョオウ", "macron"), "joō", "the long vowel is the pair that ends the run")
    s.eq(kana.romanise("ジョオウサマ", "macron"), "joōsama", "and the rest of the word follows it")
    s.eq(kana.romanise("ジョオウ", "double"), "joou", "the doubled style is unaffected either way")

    # A VOWEL KANA ONLY DEFERS TO WHAT FOLLOWS IT. Where nothing follows that would lengthen it,
    # the ordinary merge stands, which is most of the language.
    s.eq(kana.romanise("コオリ", "macron"), "kōri", "こおり is kōri; the オ has nothing to defer to")
    s.eq(kana.romanise("オオキイ", "macron"), "ōkii", "and おおきい keeps its long ō")
    s.eq(kana.romanise("トオル", "macron"), "tōru", "as does とおる")
    s.eq(kana.romanise("ジョウ", "macron"), "jō", "a plain じょう is one long vowel, not two")

    # ー IS NOT A VOWEL and cannot begin a long vowel of its own, so it never defers.
    s.eq(kana.romanise("オーウチ", "macron"), "ōuchi", "オー holds its lengthening across a following ウ")

    # THE COUNTER-CASE. The substitution must not invent an alignment: a reading that genuinely
    # does not spell the surface still fails, because ruby over the wrong character is the thing
    # this whole function is careful about.
    s.eq(kana.align("雨夜の月", "ゼンゼンチガウヨミ"), None,
         "a reading that does not spell the surface is still refused")
    s.eq(kana.align("あの子は優しすぎる。", "アノコワゼンゼンチガウ"), None,
         "and a partial match past the anchor does not carry it")
    s.eq(kana.align("ゆりづくしの教室で", "ユリズクシノキョウシツ"), None,
         "a reading missing the end of the title is still refused")
    s.eq(kana.align("アラサー美女", "アラサイビジョ"), None,
         "and ー stands for the vowel it lengthens, not for any vowel")

    # THE PLAIN STYLE REMOVES A DIACRITIC, AND いい HAS NONE. Hepburn spells a long i written いい
    # as `ii`, so there was nothing for this style to strip and it ate a letter of the word:
    # 怪異部, whose reading is カイイ ブ, rendered as `Kai Bu`. The counter-case is the point of the
    # rule: ビール is lengthened by ー, which the macron style writes as ī, and a reader choosing
    # this style is asking for exactly that to go.
    s.eq(kana.romanise("カイイ", "plain"), "kaii", "いい keeps both letters with no macron to drop")
    s.eq(kana.romanise("カワイイ", "plain"), "kawaii", "and so does かわいい")
    s.eq(kana.romanise("セカイイチ", "plain"), "sekaiichi", "including across a morpheme join")
    s.eq(kana.romanise("ビール", "plain"), "biru", "while a prolongation mark is still dropped")
    s.eq(kana.romanise("カイイ", "macron"), "kaii", "the macron style already spelled it this way")

    # ── THE THREE STYLES, RULE BY RULE ─────────────────────────────────────────────────────────
    #
    # Modified (revised) Hepburn is the library standard and is what NAMES-PLAN §8.1 names. Where a
    # rule below is disputed between traditions, the reading in force is the one the National Diet
    # Library states in `読みの基準（2021年1月）別紙３．ローマ字読み形記録要領`, because NDL is where
    # most of our stated readings come from and its rules are written down in one place.
    #
    # THE THREE MAY DIFFER ONLY ABOUT VOWEL LENGTH. That is the whole reason there are three, and
    # every case in this section either pins a length difference as deliberate or pins an agreement.

    # ん IS ALWAYS `n`, INCLUDING BEFORE b, m AND p. Modified Hepburn, and NDL says it in one line:
    # 撥音「ン」は、すべて「n」を使用する. Traditional Hepburn writes Nambu and Gumma.
    for st in ("macron", "double", "plain"):
        s.eq(kana.romanise("ナンブ", st), "nanbu", f"ん before b is n, not m ({st})")
        s.eq(kana.romanise("グンマ", st), "gunma", f"and before m ({st})")
        s.eq(kana.romanise("ポンプ", st), "ponpu", f"and before p ({st})")
        # THE APOSTROPHE IS NOT A DIACRITIC, so the plain style keeps it. Without it しんいち reads
        # as し-に-ち, which is a different name and not a plainer spelling of the same one.
        s.eq(kana.romanise("キンイン", st), "kin'in", f"ん before a vowel takes an apostrophe ({st})")
        s.eq(kana.romanise("パンヤ", st), "pan'ya", f"and before y ({st})")
        s.eq(kana.romanise("アンナイ", st), "annai", f"and before anything else takes none ({st})")

    # LONG O: おう AND おお ARE THE SAME SOUND AND TWO SPELLINGS. The macron and plain styles answer
    # about the sound; the doubled style answers about the spelling, which is the information it
    # exists to keep.
    s.eq([kana.romanise("トウキョウ", st) for st in ("macron", "double", "plain")],
         ["tōkyō", "toukyou", "tokyo"], "おう written three ways")
    s.eq([kana.romanise("オオサカ", st) for st in ("macron", "double", "plain")],
         ["ōsaka", "oosaka", "osaka"], "おお differs from おう in the doubled style alone")

    # LENGTH FROM ー AGAINST LENGTH FROM A VOWEL KANA. ー names no letter of its own, so the doubled
    # style repeats the vowel and the two sources come out alike. The macron style separates them
    # for i and only for i, because Hepburn spells a long i written いい as `ii`.
    s.eq([kana.romanise("ビール", st) for st in ("macron", "double", "plain")],
         ["bīru", "biiru", "biru"], "ー after i")
    s.eq([kana.romanise("ミイラ", st) for st in ("macron", "double", "plain")],
         ["miira", "miira", "miira"], "and い after い, which Hepburn writes out in every style")
    s.eq([kana.romanise("アラサー", st) for st in ("macron", "double", "plain")],
         ["arasā", "arasaa", "arasa"], "ー after a")
    s.eq([kana.romanise("カアサン", st) for st in ("macron", "double", "plain")],
         ["kāsan", "kaasan", "kasan"], "and あ after あ, which agrees, there being no ii rule for a")
    # えい IS NOT A LONG VOWEL IN ANY STYLE. Hepburn writes Keiko, not Kēko.
    for st in ("macron", "double", "plain"):
        s.eq(kana.romanise("ケイコ", st), "keiko", f"えい is ei ({st})")

    # っ DOUBLES THE FOLLOWING CONSONANT, AND BEFORE ch HEPBURN WRITES tch. Nothing about length, so
    # all three agree.
    for st in ("macron", "double", "plain"):
        s.eq(kana.romanise("マッチャ", st), "matcha", f"っ before ch is tch ({st})")
        s.eq(kana.romanise("コッチ", st), "kotchi", f"and before chi ({st})")
        s.eq(kana.romanise("ザッシ", st), "zasshi", f"while sh doubles its first letter ({st})")
        s.eq(kana.romanise("キッテ", st), "kitte", f"and an ordinary consonant doubles ({st})")

    # A SOKUON SEPARATED FROM ITS CONSONANT BY A WORD BREAK WAS EATEN. A stored reading is
    # word-divided and the divider falls where the analyser put it: ひよ&びびっと! is filed
    # `ヒヨ & ビビッ ト !` and shipped as `bibi to`, a mora short. 10 stored names were like this.
    s.eq(kana.romanise("ヒヨ & ビビッ ト !", "macron"), "hiyo & bibi tto !",
         "a sokuon carries across a word break to the consonant it doubles")
    s.eq(kana.romanise("ハヅ ッ チ ワ", "macron"), "hazu  tchi wa",
         "including where the break leaves it standing alone, and tch still applies")
    # AND THE COUNTER-CASE. A mark between the two is the string saying they are not one word.
    s.eq(kana.romanise("ヤッ！タ", "macron"), "ya!ta",
         "a mark between the sokuon and the next mora does cancel it")
    # A SOKUON WITH NOTHING LEFT TO DOUBLE IS DROPPED, deliberately. Hepburn has no letter for a
    # glottal stop closing nothing, and NDL's sort-key rule would spell 保健室の鍵閉めてっ `shimetetsu`.
    for st in ("macron", "double", "plain"):
        s.eq(kana.romanise("トモダチダ ヨ ネッ", st), "tomodachida yo ne",
             f"a final sokuon is dropped rather than spelled ({st})")

    # PARTICLES ARE NOT CONVERTED HERE, AND THE COUNTER-CASE IS ONE MORA LONG. A reading records
    # the sound, which is NDL's rule too, so コンニチワ arrives spelled as it is said. Converting ハ
    # here would rename 母 and 部屋, and nothing in a reading says which ハ is a particle.
    for st in ("macron", "double", "plain"):
        s.eq(kana.romanise("ハハ", st), "haha", f"母 is haha, not wawa ({st})")
        s.eq(kana.romanise("ヘヤ", st), "heya", f"部屋 is heya, not eya ({st})")
        s.eq(kana.romanise("アノコワヤサシイ", st), "anokowayasashii",
             f"a reading that records the particle's sound needs no rule ({st})")
        # を IS THE ONE THAT CAN BE SETTLED, because modern Japanese writes it for nothing else.
        s.eq(kana.romanise("ジヲカク", st), "jiokaku", f"を is o wherever it stands ({st})")
    s.eq(kana.PARTICLE_SOUND["は"], "わ",
         "the surface-side rule stays where the surface is, which is alignment")

    # ヴ IS v, which is modified Hepburn and NDL's table. The four single characters ワ゛ヰ゛ヱ゛ヲ゛
    # sit above the range to_hiragana folds and had no entry at all, so they printed themselves.
    for st in ("macron", "double", "plain"):
        s.eq(kana.romanise("ヴァンパイア", st), "vanpaia", f"ヴァ is va ({st})")
        s.eq(kana.romanise("ヷ", st), "va", f"and so is ワ゛, which NDL records as ヴァ ({st})")
    s.eq(kana.romanise("ヺ", "macron"), "vo", "as ヲ゛ is ヴォ")

    # SMALL KANA. Standing alone they are their own sound, which is NDL's 2音 rule: ペルシァ is
    # perushia. ヵ and ヶ are kana and were in no table, so 竹ヶ原 romanised as `takeヶhara`.
    for st in ("macron", "double", "plain"):
        s.eq(kana.romanise("ペルシァ", st), "perushia", f"a small vowel standing alone is a vowel ({st})")
        s.eq(kana.romanise("タケヶハラ", st), "takekehara", f"and small ヶ is ke, not a character ({st})")
        s.eq(kana.romanise("ヵ", st), "ka", f"as small ヵ is ka ({st})")
    # THE READING SHOULD NOT GET HERE, and that is why the table above is a fallback and not the
    # rule: ヶ in a place name is read が, which is where alignment reads it.
    s.eq(kana.KE_SMALL["ヶ"], ("か", "が"), "a reading of ヶ is か or が, and this is not that")

    # A WORD ALREADY IN LATIN IS NOT ROMANISED, which is NDL's rule as well: ラテン文字は、そのまま
    # ラテン文字で記録する. Romanising it would read the letters as their Japanese names, which is
    # right for a single letter standing for itself and wrong for a word.
    for st in ("macron", "double", "plain"):
        s.eq(kana.romanise("Killer Twinkle", st), "Killer Twinkle", f"Latin passes through ({st})")
        s.eq(kana.romanise("20ネン", st), "20nen", f"and so do digits ({st})")

    # A ー WITH NO VOWEL BEFORE IT IS A DASH, and it was printing itself. ＲＤーＳｏｕｎｄｓ shipped as
    # `RDー Sounds` and ラブライブ!flowers*ー蓮ノ空… opened a phrase with one.
    s.eq(kana.romanise("RDー Sounds", "macron"), "RD- Sounds",
         "a prolongation mark lengthening nothing is the dash it was drawn as")
    s.eq(kana.romanise("ンー", "macron"), "n-", "including after ん, which carries no vowel")

    # ITERATION MARKS ARE EXACTLY DETERMINED, so they are written out rather than printed. is_kana
    # admits them, so a string holding one passes kana_only and reached romanise with no entry.
    s.eq(kana.romanise("ミヽ", "macron"), "mimi", "ヽ repeats the kana before it")
    s.eq(kana.romanise("トキヾ", "macron"), "tokigi", "and ヾ repeats it voiced")
    s.eq(kana.romanise("ハヾ", "macron"), "haba", "ハ takes the dakuten and not the handakuten")
    s.eq(kana.romanise("ヽ", "macron"), "ヽ", "a mark with nothing before it has nothing to repeat")

    # 四つ仮名 AND THE OBSOLETE KANA, all of them NDL's table and modified Hepburn alike.
    for st in ("macron", "double", "plain"):
        s.eq(kana.romanise("チカヂカ", st), "chikajika", f"ヂ is ji ({st})")
        s.eq(kana.romanise("イソヅリ", st), "isozuri", f"ヅ is zu ({st})")
        s.eq(kana.romanise("ヰタ", st), "ita", f"ヰ is i ({st})")
        s.eq(kana.romanise("ヱニス", st), "enisu", f"and ヱ is e ({st})")

    # THE PROPERTY BEHIND THE WHOLE SECTION. Where a reading holds no long vowel there is nothing
    # for the three styles to disagree about, so they must agree exactly. A difference here is a
    # rule that reached one style and not the others, which is the fault this audit was for.
    for probe in ("ナンブ", "キンイン", "パンヤ", "マッチャ", "コッチ", "ハハ", "ヘヤ", "ジヲカク",
                  "ヴァンパイア", "ヷ", "ペルシァ", "タケヶハラ", "チカヂカ", "ヰタ", "ケイコ",
                  "Killer Twinkle", "20ネン", "ミヽ", "ヒヨ & ビビッ ト !", "トモダチダ ヨ ネッ"):
        got = {kana.romanise(probe, st) for st in ("macron", "double", "plain")}
        s.eq(len(got), 1, f"the three styles agree on {probe}, which carries no length")

    # AND ITS COUNTER-CASE: where there IS a long vowel they must differ, or a style is not doing
    # the one job it has.
    for probe in ("ユウリ", "トウキョウ", "オオサカ", "アラサー", "カアサン", "ネエサン"):
        got = [kana.romanise(probe, st) for st in ("macron", "double", "plain")]
        s.eq(len(set(got)), 3, f"the three styles differ on {probe}, which is long")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "kana"))
