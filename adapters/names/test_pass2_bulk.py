#!/usr/bin/env python3
"""pass2_bulk.py: telling a romanisation from a chosen English name.

COVERS = ['adapters/names/pass2_bulk.py']

This decides whether a community database's English field is usable at all. "Bloom Into You" and
"Kimi to Shiranai Natsu ni Naru" arrive through the SAME field: one is a licensed name and the
other is mechanical transliteration, and §5 marks the two differently to the reader. Getting it
wrong in either direction mislabels every title that source supplies.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit
from adapters.names import pass2_bulk as p2


def main(s):
    r = p2.looks_romanised

    # A macron settles it alone: only romanised Japanese carries one.
    s.check(r("Yagate Kimi ni Naru", "やがて君になる"), "particles mark a romanisation")
    s.check(r("Yūri", "百合"), "a macron settles it by itself")

    # An English NAME must not be taken for a romanisation, or a licensed title gets marked as our
    # own mechanical guess.
    s.check(not r("Bloom Into You", "やがて君になる"), "a licensed English title is not romanised")
    s.check(not r("This Monster Wants to Eat Me", "私を喰べたい、ひとでなし"),
            "one Japanese-looking function word is not enough; English has 'to' as well")

    # An honorific alone is not enough either: English titles keep them routinely.
    s.check(not r("JK-chan and Her Male Classmate's Mom", "x"),
            "an honorific by itself does not make an English title a romanisation")

    # Convertibility alone is not enough: Wataten! converts perfectly and is the official name.
    s.check(not r("Wataten!", "私に天使が舞い降りた！"),
            "a string that converts cleanly is still not necessarily a romanisation")

    s.check(not r("", "百合"), "an empty string is not a romanisation")
    s.check(not r(None, "百合"), "None does not raise")

    # The comparison form is loose about presentation and strict about content.
    # Width folding is what the docstring promises, and it was missing: けいおん！Ｓｈｕｆｆｌｅ,
    # ７日間限定彼女 and ルミナス＝ブルー never matched their own half-width forms in a source
    # database. 15 of 1,055 titles were affected and folding introduced no new collisions.
    s.eq(p2.norm("ＹＵＲＩ！"), p2.norm("yuri!"), "full-width latin folds")
    s.eq(p2.norm("７日間限定彼女"), p2.norm("7日間限定彼女"), "full-width digits fold")
    s.eq(p2.norm("ルミナス＝ブルー"), p2.norm("ルミナス=ブルー"), "full-width punctuation folds")
    s.eq(p2.norm("けいおん！Ｓｈｕｆｆｌｅ"), p2.norm("けいおん!Shuffle"), "a real affected title")
    s.ne(p2.norm("百合"), p2.norm("薔薇"), "different titles stay different")

    # A ROMANISATION OF THE WRONG WORK. MangaUpdates confirms identity on any of a record's
    # associated titles and then returns the primary title's romanisation, so a series catalogued
    # twice hands back a name belonging to its other title. Nothing else catches it: the only
    # other test compares Latin against Japanese and passes anything.
    s.check(not p2.romanises_this("お姉さまと巨人 ～お嬢さまが異世界転生～", "Onee-sama to Kyojin"),
            "a romanisation covering the first seven characters is not this title's")
    s.check(p2.romanises_this("お姉さまと巨人 ～お嬢さまが異世界転生～",
                              "Onee-sama to Kyojin ~Ojou-sama ga Isekai Tensei~"),
            "and the whole title's romanisation is")
    s.check(not p2.romanises_this("スケバンと転校生",
                                  "Sukeban to Tenkousei wa Koi wo Shita no Darou ka"),
            "a romanisation of a longer title is not this one's either")
    s.check(p2.romanises_this("スケバンと転校生", "Sukeban to Tenkousei"),
            "while the title's own romanisation passes")

    # DELIBERATELY LOOSE. It is here to catch a name belonging to another work, not to adjudicate a
    # reading, so ordinary variation must not trip it.
    s.check(p2.romanises_this("今日はカノジョがいないから", "Kyou wa Kanojo ga Inai kara"),
            "an ordinary romanisation is not second-guessed")
    s.check(p2.romanises_this("球詠", "Tamayomi"), "nor a short title with a long reading")
    s.check(p2.romanises_this("citrus", "citrus"), "nor one with no Japanese in it at all")
    s.check(p2.romanises_this("何か", "!!!"), "and an unreadable romanisation is not judged here")

    # AN ALIAS MATCH NAMES THE ITEM, NOT THE TITLE ASKED ABOUT. Wikidata binds a work catalogued
    # under two Japanese names to one item, and its English label belongs to the one it is filed
    # under. The author path has guarded this since 古川楊也 took ホシノ カツラ's reading; the title
    # path could not, because the query never asked which was the label.
    def row(ja, jalabel, en, item="Q1"):
        b = {"ja": {"value": ja}, "en": {"value": en},
             "type": {"value": "http://www.wikidata.org/entity/Q8261"},
             "item": {"value": item}}
        if jalabel is not None:
            b["jalabel"] = {"value": jalabel}
        return b

    W = p2.Wikidata
    s.check(W._title_fact("彩香ちゃんは弘子先輩を落としたい",
                          [row("彩香ちゃんは弘子先輩を落としたい", "彩香ちゃんは弘子先輩を落としたい",
                               "Ayaka Wants to Win Over Hiroko")]),
            "a match on the item's own label is this title's English name")
    s.eq(W._title_fact("彩香ちゃんは弘子先輩を落としたい",
                       [row("彩香ちゃんは弘子先輩を落としたい", "彩香ちゃんは弘子先輩に恋してる",
                            "Ayaka Is in Love with Hiroko")]),
         None, "and a match on one of its aliases is not")

    # Rows captured before the query asked for the label carry none. Absent is not the same as
    # different, so they are left alone rather than thrown away.
    s.check(W._title_fact("彩香ちゃんは弘子先輩を落としたい",
                          [row("彩香ちゃんは弘子先輩を落としたい", None,
                               "Ayaka Wants to Win Over Hiroko")]),
            "a row from before the label was selected is still usable")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.pass2_bulk"))
