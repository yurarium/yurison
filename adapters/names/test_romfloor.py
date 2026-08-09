#!/usr/bin/env python3
"""romfloor.py: the Latin an English page falls back to, and what it must never return.

The reading function is a table written here, so this suite needs no analyser and no network. Every
case below is one the interface met on a live page with the budget counting it.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import entities
import romfloor

# What an analyser would answer, written out. Keyed by the whole run where a run has a reading and
# by the single character where the fallback has to read one alone.
READINGS = {
    "百合姫": "ユリ ヒメ",
    "育田花": "イクタ ハナ",
    "河上大志郎": "カワカミ タイシロウ",
    "沢田": "サワダ",
    "蒼井": "アオイ",
    "檜": "ヒノキ", "乃": "ノ", "坂": "サカ", "耀": "ヨウ", "季": "キ",
    "株": "カブ", "式": "シキ", "会": "カイ", "社": "シャ",
    "蒼": "アオ", "井": "イ",
}


def read(s):
    return READINGS.get(s)


def main(s):
    # KANA NEEDS NO SOURCE AND NO LOOKUP. This is the class that had no excuse: a kana surface is a
    # reading already, the project ships three romanisation styles computed from readings, and
    # seven credits reached an English page as kana anyway.
    s.eq(romfloor.floor("よつばますみ", read)["macron"], "Yotsubamasumi",
         "a kana pen name romanises with no reading in the table at all")
    s.eq(romfloor.floor("ホークアイ", read)["plain"], "Hokuai", "and it follows the style control")
    s.eq(romfloor.floor("ホークアイ", read)["double"], "Hookuai", "in every style")

    # THE STYLES MUST DISAGREE WHERE THERE IS LENGTH TO DISAGREE ABOUT, which is the property that
    # says the floor really is computed per style rather than spelled once and copied.
    got = {st: romfloor.floor("ホークアイ", read)[st] for st in romfloor.STYLES}
    s.eq(len(set(got.values())), 3, "three styles, three spellings of a long vowel")

    # THE MIDDLE DOT SITS IN THE KANA BLOCK AND IS NOT READ ALOUD. Left inside the run it vanished,
    # and くろば・Ｕ came back as one word nobody is called.
    s.eq(romfloor.floor("くろば・Ｕ", read)["macron"], "Kuroba · U",
         "the interpunct survives as an interpunct")
    s.eq(romfloor.floor("アナ・Ｃ・サンチェス", read)["macron"],
         "Ana · C · Sanchesu", "and it does so twice in one name")

    # A SPACE BETWEEN TWO RUNS IS PART OF THE NAME. `latinise` strips what it is given, so folding
    # each fragment as it was taken ran two names together.
    s.eq(romfloor.floor("サリイ ビー", read)["double"], "Sarii Bii",
         "two kana runs keep the space the source wrote between them")
    s.eq(romfloor.floor("沢田　かに", read)["macron"], "Sawada Kani",
         "an ideographic space between a kanji run and a kana one is a space")

    # THE DESK, WHICH THE OWNER RULED ON. A magazine plus a department is not a person's name: the
    # first half is discoverable and the second is a common noun with an English answer.
    s.eq(romfloor.floor("百合姫編集部", read)["macron"],
         "Yuri Hime Editorial Department", "the stem is read and the suffix is glossed")
    s.eq(romfloor.floor("Be編集部", read)["macron"], "Be Editorial Department",
         "a Latin magazine name keeps its own spelling")
    s.eq(romfloor.floor("ＮＯＡＨ編集部", read)["macron"],
         "NOAH Editorial Department", "and a full-width one is folded to the width it is read at")
    s.eq(romfloor.floor("編集部", read)["macron"], "Editorial Department",
         "the word standing alone is the gloss and nothing else")

    # AND THE COUNTER-CASE, which is what stops the rule from translating a word out of the middle
    # of a name: the suffix has to close the string.
    s.eq(romfloor.desk_parts("百合姫編集部"), ("百合姫", "Editorial Department"),
         "the stem is everything before the suffix")
    s.eq(romfloor.desk_parts("編集部の人"), None,
         "a desk word the credit does not end on is somebody's field and not the credit")
    s.eq(romfloor.desk_parts("育田花"), None, "and a person is not a desk")

    # PER CHARACTER IS THE WEAKEST ANSWER AND THE ONE ALWAYS AVAILABLE. Nothing in the table reads
    # 檜乃坂耀季 whole, so each character is read alone, which is a guess and is marked as one by
    # the interface.
    s.eq(romfloor.floor("檜乃坂耀季", read)["macron"], "Hinokinosakayōki",
         "a name nothing can read whole is assembled character by character")

    # A WHOLE-RUN READING BEATS THE CHARACTERS. Both are in the table, and taking the characters
    # where a run reads would publish the worse of two answers we hold.
    s.eq(romfloor.floor("育田花", read)["macron"], "Ikuta Hana",
         "the run's own reading is preferred to reading its characters")

    # NOTHING CAN READ THIS, AND THAT IS A STATE. Refused rather than half answered, so the build
    # can count it instead of shipping a string with a character still in it.
    s.eq(romfloor.floor("龜龜龜", read), None,
         "a run no reading reaches is refused whole")
    s.eq(romfloor.floor("Yuri Hime", read), None,
         "a string already in Latin has no floor to compute")
    s.eq(romfloor.floor("   ", read), None, "and neither has an empty one")

    # THE PROPERTY THE WHOLE MODULE EXISTS FOR. Whatever it returns holds no kana and no kanji.
    for probe in ["よつばますみ", "百合姫編集部",
                  "檜乃坂耀季", "くろば・Ｕ",
                  "沢田　かに", "BPS株式会社"]:
        got = romfloor.floor(probe, read)
        for st in romfloor.STYLES:
            s.check(got is None or not romfloor.JAPANESE.search(got[st]),
                    f"{probe} floors to Latin in {st}: {got and got[st]!r}")

    # THE RUNS INSIDE A STRING, because the interface renders a credit field in place and hands
    # over the run between two brackets as well as the whole field.
    s.eq(romfloor.runs_within("[著]時一二 / BPS株式会社"),
         ["株式会社", "時一二", "著"],
         "every maximal Japanese run, longest first")

    # THE REPEAT MARK IS RESOLVED BEFORE ANYTHING IS ASKED TO READ IT. Asked for 々 alone the
    # analyser answers with its word for the CATEGORY, so a run holding one could not be read and
    # 依々恋々 had no floor at all.
    s.eq(romfloor.floor("蒼井々", read)["macron"], "Aoii",
         "the repeat mark is the character before it")

    # THE MAP THE BROWSER LOOKS UP, keyed exactly as `foldKey` keys it: NFKC, spaces removed.
    got, unread = romfloor.build(["沢田　かに", "ＮＯＡＨ編集部"], read)
    s.check("沢田かに" in got, "the key has its space taken out")
    s.check("NOAH編集部" in got, "and its full width folded")
    s.eq(unread, [], "and nothing here was unreadable")
    s.eq(got["沢田かに"], "Sawada Kani",
         "a name the three styles spell alike is one string and not three")
    s.eq(romfloor.build(["ホークアイ"], read)[0]["ホークアイ"]["plain"], "Hokuai",
         "and one they spell differently keeps all three")

    # THE RUNS ARE ASKED FOR AND NOT ASSUMED. Only a credit field is composed in place, so only a
    # credit field needs its runs as keys; expanding every title the same way added four thousand
    # keys nothing looks up to a file that loads on every visit.
    plain, _ = romfloor.build(["[著]育田花"], read)
    s.check("育田花" not in plain, "a run is not a key unless the string was named as a field")
    withruns, _ = romfloor.build(["[著]育田花"], read, runs_of=["[著]育田花"])
    s.check("育田花" in withruns, "and it is one when the string was")

    # A WORD ADDED TO THE CLASSIFIER WITHOUT AN ENGLISH ANSWER WOULD ROMANISE SILENTLY. The
    # vocabulary lives in entities.py, which is what files a credit as a desk; this file only says
    # what the word means in English, and the two have to cover the same words or one of them is
    # deciding something the other has not been told.
    s.eq(set(romfloor.DESK_EN), set(dict(entities.KINDS)["desk"]),
         "every desk word entities.py knows has an English gloss here")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "romfloor"))
