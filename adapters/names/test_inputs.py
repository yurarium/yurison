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


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.inputs"))
