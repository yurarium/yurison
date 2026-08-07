#!/usr/bin/env python3
"""credits.py: a name and its own reading are one person."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import credits  # noqa: E402

COVERS = ["adapters/names/credits.py"]

STORE = {
    "蓬餅": {"reading": "ヨモギモチ"},
    "矢坂しゅう": {"reading": "ヤサカシュウ"},
    "焼肉定食": {"reading": "ヤキニク テイショク"},
    "一迅社": {"reading": "イチジンシャ"},
    "田口囁一": {"reading": "タグチショウイチ"},
    "原田重光": {"reading": "ハラダシゲミツ"},
}


def main(s):
    # THE CASE THIS WAS WRITTEN FOR. One string in two scripts, with the reading spaced.
    s.eq(credits.dedupe("おにぎりパクパク / オニギリ パクパク"), "おにぎりパクパク",
         "a kana fold of the name beside it is the same person")

    # The kanji case, which no fold can see and only the store's reading settles.
    s.eq(credits.dedupe("蓬餅 / ヨモギモチ", STORE), "蓬餅",
         "a stored reading of the name beside it is the same person")
    s.eq(credits.dedupe("矢坂しゅう / ヤサカシュウ", STORE), "矢坂しゅう",
         "and so is one whose name is partly kana")

    # A reading is word-separated and a name is not, so the space cannot be the difference.
    s.eq(credits.dedupe("焼肉定食 / ヤキニク テイショク", STORE), "焼肉定食",
         "a spaced reading still matches the name it reads")

    # Two credits written four times: the readings go and the people stay, in order.
    s.eq(credits.dedupe("一迅社 / 田口囁一 / イチジンシャ / タグチショウイチ", STORE),
         "一迅社 / 田口囁一", "every restatement goes and the order of the people is kept")

    # THE COUNTER-CASE, AND THE REASON THE SCRIPT IS NOT THE TEST. extract.people drops any
    # all-katakana part, which would delete each of these, and every one of them is a person.
    for name in ("サブロウタ", "コダマナオコ", "アキリ", "ヨルモ"):
        s.eq(credits.dedupe(name), name, f"a katakana pen name is a person: {name}")
    s.eq(credits.dedupe("コダマナオコ / サブロウタ"), "コダマナオコ / サブロウタ",
         "two katakana pen names are two people")

    # A second person is not dropped merely for following a name.
    s.eq(credits.dedupe("原田重光 / 蘇募ロウ", STORE), "原田重光 / 蘇募ロウ",
         "a name that does not read the one before it survives")

    # Degenerate input comes back unchanged rather than raising.
    s.eq(credits.dedupe(""), "", "an empty field is empty")
    s.eq(credits.dedupe(None), "", "a missing field is empty")
    s.eq(credits.dedupe("梵辛"), "梵辛", "one credit is returned as it was given")

    # An exact repeat is not a reading, and is still one person.
    s.eq(credits.dedupe("梵辛 / 梵辛"), "梵辛", "the same name twice is one credit")

    s.eq(credits.doubled("蓬餅 / ヨモギモチ", STORE), 1, "the measure counts what it drops")
    s.eq(credits.doubled("原田重光 / 蘇募ロウ", STORE), 0, "and counts nothing where nothing goes")

    # A CAPTURED CREDIT THAT CANNOT BE A NAME. Each of these reached an author field from a page
    # title whose middle field was not the author.
    for junk in ("#1(1)", "７", "第3話", "12", "(2)", "--"):
        s.check(not credits.is_a_person(junk), f"not a person: {junk}")
    # And the counter-case, because a rule keyed on "contains a digit" deletes real people.
    for real in ("タイザン5", "梵辛", "おにぎりパクパク", "Ｍａｇｐｉｅ", "帯屋ミドリ2"):
        s.check(credits.is_a_person(real), f"a person: {real}")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
