#!/usr/bin/env python3
"""Words a morphological analyser reads confidently and wrongly.

WHY THIS IS SEPARATE FROM `vocabulary`. That module answers whether the analyser was GUESSING, so
a reading can be marked as ours or left unmarked. It cannot help here, because the analyser is not
guessing: SudachiDict holds 八尺 as a 固有名詞 and reads it ヤサカ, `is_oov` is false, and every
signal `vocabulary` reads says this is ordinary in-dictionary vocabulary. It is, for 八尺瓊勾玉. It
is not for 八尺様, the yōkai, who is はっしゃくさま. A confident wrong answer is invisible to every
test of confidence.

WHAT A ROW IS. A surface that a source states the reading of, where the analyser states a different
one. Each carries the reading and the reason, because a table of corrections with no reasons is a
list of somebody's preferences and the next reader cannot tell a researched reading from a guess.

WHY IT SUBSTITUTES KANA RATHER THAN RETURNING A ROMANISATION. Two reasons, and the second is the
one that decides it. The romanisation styles are the reader's choice and this is applied at build
time, so producing Latin here would bake one style in. And substituting the WHOLE run breaks the
word boundaries: `八尺様リバイバルV` romanises `Yasakasama Ribaibaru V` with the spaces the analyser
found, and replacing the run with ハッシャクサマリバイバル makes one out-of-vocabulary blob that comes
back `Hasshakusamaribaibaru`. So the word alone is replaced, in place, and the analyser goes on
doing the segmenting it is good at.

THIS IS NOT A PLACE TO PUT A READING YOU PREFER. A row belongs here when a source states the
reading and the analyser contradicts it. Where no source states one, the answer is the mark that
says so, not an entry here.
"""

#: `surface: (kana, why)`. The kana is what the surface is read, in katakana as the store keeps
#: readings. The reason names what states it.
MISREAD = {
    "八尺様": ("ハッシャク様",
             "The yōkai of the 2ch story cycle, はっしゃくさま, whose name is the eight-shaku "
             "height she is described at. SudachiDict holds 八尺 as 固有名詞 read ヤサカ, which is "
             "the 八尺瓊 of the imperial regalia and a different word, so the analyser answers "
             "confidently and `is_oov` is false. Reached readers as `Yasakasama Ribaibaru` on the "
             "chapter names of 裏世界ピクニック, whose 八尺様 is the yōkai."),
}


def corrected(text):
    """`text` with every misread surface replaced by its stated reading.

    IN PLACE AND WORD BY WORD, so the analyser still finds the boundaries around it. The value is
    a kana spelling of that word and not of its neighbours.
    """
    out = str(text or "")
    for surface, (kana, _why) in MISREAD.items():
        if surface in out:
            out = out.replace(surface, kana)
    return out


def reasons():
    """`{surface: why}`, for a reader asking what a row rests on."""
    return {k: why for k, (_kana, why) in MISREAD.items()}


if __name__ == "__main__":
    for surface, (kana, why) in MISREAD.items():
        print(f"{surface}  ->  {kana}\n    {why}\n")
