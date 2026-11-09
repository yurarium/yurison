#!/usr/bin/env python3
"""misread: words an analyser reads confidently and wrongly.

COVERS = ['adapters/facts/reading/misread.py']

THE FAULT THIS IS FOR. SudachiDict holds 八尺 as a 固有名詞 and reads it ヤサカ, which is right for
八尺瓊勾玉 and wrong for 八尺様, the yōkai, who is はっしゃくさま. `is_oov` is false and every signal
`facts/reading/vocabulary` reads says this is ordinary in-dictionary vocabulary, so nothing marked
the reading and 裏世界ピクニック's chapter names shipped as `Yasakasama Ribaibaru`.

WHY THE VALUE IS KANA AND NOT LATIN. The romanisation styles are the reader's choice and this is
applied at build time, so a Latin value would bake one style in. And the substitution is of the
WORD, not the run: replacing 八尺様リバイバル wholesale makes one out-of-vocabulary blob and loses the
word boundaries the analyser is good at finding.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import testkit                                                          # noqa: E402
from facts.reading import misread                                       # noqa: E402


def main(s):
    s.check(misread.MISREAD, "there is at least one correction to make")

    # ── the correction applies ─────────────────────────────────────────────────────────────────
    s.eq(misread.corrected("八尺様リバイバルV"), "ハッシャク様リバイバルV",
         "the misread word is replaced and its neighbours are left alone")
    s.eq(misread.corrected("第90話-2 八尺様リバイバルV"), "第90話-2 ハッシャク様リバイバルV",
         "and it is replaced wherever in the string it sits")

    s.eq(misread.corrected("おまけ③ 柚稀＆梓ができるまで"), "おまけ③ 柚稀＆アズサができるまで",
         "梓 standing as a person is the given name")

    # ── and only where it applies ──────────────────────────────────────────────────────────────
    s.eq(misread.corrected("梓月は天に咲う"), "梓月は天に咲う",
         "a compound the word sits inside is a different word and is left for its own record")
    s.eq(misread.corrected("上梓"), "上梓", "and so is the noun the analyser already reads")
    s.eq(misread.corrected("[特別読切] 燕のあやかし画帳"), "[特別読切] ツバメのあやかし画帳",
         "燕 standing alone is the bird")
    s.eq(misread.corrected("江畔ノ燕々"), "江畔ノ燕々", "and the doubled 燕々 of verse is left alone")
    s.eq(misread.corrected("燕尾服"), "燕尾服", "as is the on'yomi compound")
    s.eq(misread.corrected("裏世界ピクニック"), "裏世界ピクニック",
         "a string holding no misread word comes back as it went in")
    s.eq(misread.corrected(""), "", "and so does an empty one")
    s.eq(misread.corrected(None), "", "and so does nothing at all")

    # ── every row carries its reason ───────────────────────────────────────────────────────────
    # A table of corrections with no reasons is a list of somebody's preferences, and the next
    # reader cannot tell a researched reading from a guess.
    for surface, (kana, why) in misread.MISREAD.items():
        s.check(kana and kana != surface, f"{surface} is corrected to something, and to something else")
        s.check(len((why or "").strip()) > 40,
                f"{surface} says what states its reading and what the analyser said instead")
    s.eq(set(misread.reasons()), set(misread.MISREAD),
         "and every row's reason is reachable without reading the table")

    # ── THE VALUE IS KANA, which is what keeps the reader's romanisation choice alive ──────────
    for surface, (kana, _why) in misread.MISREAD.items():
        s.check(not any(c.isascii() and c.isalpha() for c in kana),
                f"{surface} is corrected to kana rather than to a romanisation")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "misread"))
