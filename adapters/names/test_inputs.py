#!/usr/bin/env python3
"""inputs.py: turning a credit line into the people in it.

COVERS = ['adapters/names/inputs.py']

Credit lines are the messiest strings in the database. Getting this wrong produces a person who
does not exist, and a fabricated name is worse than a missing one.
"""
import pathlib
import sys

# inputs.py does `from . import kana`, so it only loads as part of its package. Importing it by
# path gives "attempted relative import with no known parent package"; the repo root on sys.path
# and a dotted import is the form that works.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit
from adapters.names import inputs


def names(credit):
    return [n for n, _ in inputs.split_authors(credit)]


def main(s):
    s.eq(names("宮澤伊織"), ["宮澤伊織"], "a bare name is one person")

    # AN AMPERSAND JOINS TWO PEOPLE. All four credits in the corpus that carry one are a pair, and
    # no name anywhere spells itself with an &, which is what admitted it where the interpunct is
    # still argued about. Until this, two of these were one identifier holding two artists.
    s.eq(names("大島永遠&大島智"), ["大島永遠", "大島智"], "a half-width ampersand separates")
    s.eq(names("ひあるろん＆達磨"), ["ひあるろん", "達磨"], "and the full-width one does too")
    s.eq(names("iimAn&惟丞 / 年中麦茶太郎"), ["iimAn", "惟丞", "年中麦茶太郎"],
         "beside the separator the field already used")
    # THE SHAPE THAT MUST NOT REACH HERE. An unescaped entity splits into a person called
    # `amp;大島智`, which is why `credits.split_credits` unescapes before calling this and why the
    # unescaping is not done inside the splitter, where every caller would pay for it twice.
    s.eq(names("大島永遠&amp;大島智"), ["大島永遠", "amp;大島智"],
         "raw HTML is not this function's input, and it says so by producing nonsense")

    # Roles are labels, not people. 原作／宮澤伊織 was once romanised whole, giving a "person"
    # called Gensaku Kigō Miyazawa Iori.
    s.eq(names("原作／宮澤伊織"), ["宮澤伊織"], "a role marker is stripped")
    s.eq(names("[漫画]東雲水生 / [脚本]駒尾真子"), ["東雲水生", "駒尾真子"],
         "two bracketed roles yield two people")

    # An imprint in brackets belongs to nobody.
    s.eq(names("宮澤伊織(早川書房刊)"), ["宮澤伊織"], "a publisher note is not part of the name")

    # A bracketed KANA gloss after a non-kana head is furigana, so it is the reading rather than a
    # separate person. This is the only case where a reading is taken from the credit line at all.
    got = inputs.split_authors("博（ひろ）")
    s.eq([n for n, _ in got], ["博"], "a furigana gloss does not become a second person")
    s.eq([r for _, r in got], ["ヒロ"], "and is kept as the reading, in katakana")

    # A separator INSIDE brackets must not split the line, which is what the masking exists for.
    s.eq(names("宮澤伊織(早川・書房)"), ["宮澤伊織"], "a separator inside brackets does not split")

    s.eq(names(""), [], "an empty credit yields nobody")
    s.eq(names(None), [], "None yields nobody rather than raising")
    s.eq(names("／・"), [], "punctuation alone is not a person")

    # Duplicates collapse: the same person credited twice is one person.
    s.eq(names("宮澤伊織 / 宮澤伊織"), ["宮澤伊織"], "a repeated name appears once")

    # `ほか` CLOSES A CREDIT AND IS NOT A CONTRIBUTOR. The bibliography writes an anthology as
    # `浅見百合子 ほか`, and a space is not a separator here by design, so the whole string was one
    # person. THE BUG THIS PINS: 奏 : 青春バンド百合アンソロジー was refused a join to the ニコニコ
    # page that names 浅見百合子 first of nine, because the name we were matching with was
    # "浅見百合子 ほか" and nobody is called that.
    s.eq(names("浅見百合子 ほか"), ["浅見百合子"], "ほか after a name is not a second person")
    s.eq(names("昆布わかめ / 他"), ["昆布わかめ"], "and neither is 他 as a part of its own")
    s.eq(names("柚原もけ / 入間人間 / ほか"), ["柚原もけ", "入間人間"],
         "the named contributors survive it")

    # THE COUNTER-CASE. Those two characters occur inside real names, and the rule only fires
    # after whitespace or on a part of its own.
    s.eq(names("ほかり"), ["ほかり"], "a name beginning with them is untouched")
    s.eq(names("山田他郎"), ["山田他郎"], "and so is one containing 他")

    # ── A ROLE IN A BRACKET CLOSES A CREDIT ────────────────────────────────────────────────────
    #
    # `冬眠結(漫画) 橙々(原作)` is two people with nothing but a space between them, and a space is
    # not a separator here. The bracket is what licenses the split.
    s.eq(names("冬眠結(漫画) 橙々(原作)"), ["冬眠結", "橙々"],
         "a role bracket ends a credit, so the space after it separates two people")
    s.eq(names("羽流木はない（原作） 篠月しのぶ（漫画）"), ["羽流木はない", "篠月しのぶ"],
         "full-width brackets do the same")
    s.eq(names("介錯(漫画・原作) 姫神の巫女(原案)"), ["介錯", "姫神の巫女"],
         "and so does a bracket holding two roles at once")

    # THE COUNTER-CASE, and it is the reason a space is not a separator. Both of these are fields
    # of exactly the shape above, and both hold names with a space inside them.
    s.eq(names("三松　真由美(原作) 白井　くま(漫画)"), ["三松　真由美", "白井　くま"],
         "a space inside a name survives the split")
    s.eq(names("高坂 はしやん(著) 伊予嶺つく(著)"), ["高坂 はしやん", "伊予嶺つく"],
         "including a half-width one")
    s.eq(len(names("sono.N（SHUEISHA） 森夕")), 1,
         "a bracket that is not a role leaves the field as one credit")

    # ── THE ROLE VOCABULARY ────────────────────────────────────────────────────────────────────
    #
    # It was a list of compounds written out by hand, so widening it meant guessing which compound
    # to add next: キャラクターデザイン and 構成協力 were both missed by a round that added four.
    s.eq(names("石田可奈(キャラクターデザイン)"), ["石田可奈"], "キャラクターデザイン is a role")
    s.eq(names("森夕(構成協力)"), ["森夕"], "and so is 構成協力")
    s.eq(names("竹嶋えく(イラスト・漫画)"), ["竹嶋えく"], "and two roles joined by an interpunct")
    s.eq(names("南瓜かぷちー(表紙 / 漫画)"), ["南瓜かぷちー"], "and two joined by a slash")
    s.eq(names("潮一葉 ネーム"), ["潮一葉"], "a trailing ネーム is notation")

    # A ROLE IS NOT A READING. キャラクターデザイン is kana all the way through, so the furigana
    # rule above claimed it: 三廼 was filed reading ミツヤ ( キャラクター デザイン ) and printed
    # that way. Whatever the role vocabulary recognises is notation, in any script.
    s.eq([r for _, r in inputs.split_authors("石田可奈(キャラクターデザイン)")], [None],
         "a role in kana is not taken as the name's reading")

    # THE COUNTER-CASE for the vocabulary: these sit in brackets and are not roles.
    s.eq(names("sono.N（SHUEISHA）"), ["sono.N"], "a publisher in brackets is dropped, not a role")
    s.eq(names("コダマナオコ(コダマ)"), ["コダマナオコ"], "and a katakana gloss is still a gloss")
    s.eq(names("作田ハジメ"), ["作田ハジメ"],
         "a single-character role opening a name needs a delimiter to count as one")
    s.eq(names("画津まゆ"), ["画津まゆ"], "the same for 画")
    s.eq(names("著：山田"), ["山田"], "with the delimiter it is notation")

    # TWO BRACKETS ON ONE CREDIT. Peeling one left 壇九(著者), which is nobody.
    s.eq(names("壇九（TANJIU)(著者)"), ["壇九"], "a name can carry a Latin gloss and a role")

    # A ROLE WELDED TO A NAME WITH NO DELIMITER, which only multi-character roles may take.
    s.eq(names("原案協力舞方パーク"), ["舞方パーク"], "a two-part role prefix comes off in one go")
    s.eq(names("他著雪子"), ["雪子"], "and an anthology's `and others, written by` does too")

    # ── ・ IS A SEPARATOR FOR THE STORE AND NOT FOR THE PAGE ────────────────────────────────────
    #
    # It separates people in 矢立肇・富野由悠季 and sits inside a name in さりい・Ｂ, and nothing in
    # the string tells them apart. Feeding the store, a wrong split costs one entry nobody looks
    # up; printing a credit line, it prints half of somebody's name.
    s.eq(names("さりい・Ｂ"), ["さりい", "Ｂ"], "the store gets both halves")
    s.eq([n for n, _ in inputs.split_authors("さりい・Ｂ", interpunct=False)], ["さりい・Ｂ"],
         "and a caller that is going to print it gets the name whole")
    s.eq([n for n, _ in inputs.split_authors("矢立肇・富野由悠季", interpunct=False)],
         ["矢立肇・富野由悠季"], "which is the cost of it, paid in the safe direction")

    # ── THE ROLE THE SPLITTER TAKES OFF, REPORTED RATHER THAN ONLY DISCARDED ────────────────────
    #
    # A credit becomes a reference when a work links to the person it names, and one person is 原作
    # on one work and 作画 on another, so the role belongs on the edge between them. It comes out of
    # this traversal because a second pass over the same string is how two readers of one fact drift.
    roles = lambda c: [(n, r) for n, _rd, r in inputs.split_credits_detail(c)]     # noqa: E731
    s.eq(roles("原案：士郎正宗　漫画：六道神士"), [("士郎正宗", "原案"), ("六道神士", "漫画")],
         "a label at the head names the credit beside it")
    s.eq(roles("冬眠結(漫画) 橙々(原作)"), [("冬眠結", "漫画"), ("橙々", "原作")],
         "and so does one in a bracket")

    # A LABEL AT THE TAIL BELONGS TO THE CREDIT AFTER IT, which is the whole reason ROLE_TAIL
    # exists. `原作／宮澤伊織　作画／水野英多` splits on the slash into `原作`, `宮澤伊織　作画` and
    # `水野英多`, so 作画 arrives glued to the end of 宮澤伊織's chunk while labelling 水野英多.
    # Reading it as 宮澤伊織's put every person in the field under the next person's job.
    s.eq(roles("原作／宮澤伊織(早川書房刊)　作画／水野英多　キャラクター原案／shirakaba"),
         [("宮澤伊織", "原作"), ("水野英多", "作画"), ("shirakaba", "キャラクター原案")],
         "every credit takes the label written before it and not the one written after")
    s.eq(roles("原作/大鷹シン 漫画/ホマレ"), [("大鷹シン", "原作"), ("ホマレ", "漫画")],
         "the same where the credit separated its roles with a slash")

    # A LABEL IS SPENT ON ONE CREDIT. `原作／A／B` says what A did and says nothing about B, and
    # carrying it down the field would file everybody under the first job named.
    s.eq(roles("原作／宮澤伊織／水野英多"), [("宮澤伊織", "原作"), ("水野英多", None)],
         "a label reaches the credit after it and stops")
    s.eq(roles("秋山はる"), [("秋山はる", None)], "and a credit with no label carries none")
    s.eq(roles("[著]秋山はる"), [("秋山はる", "著")],
         "MADB's own notation is a label like any other")
    s.eq(roles("石田可奈(キャラクターデザイン)"), [("石田可奈", "キャラクターデザイン")],
         "including the one whose absence from a third role list filed it as a reading")
    s.eq(inputs.split_authors("原案：士郎正宗　漫画：六道神士"), [("士郎正宗", None),
                                                          ("六道神士", None)],
         "and the caller that wants names still gets pairs, from the one traversal")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.inputs"))
