#!/usr/bin/env python3
"""ndl_reading.py: taking a stated reading off a catalogue record, and refusing the wrong one."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import ndl_reading as nr  # noqa: E402

COVERS = ["adapters/names/ndl_reading.py"]

# Quoted from https://ndlsearch.ndl.go.jp/api/opensearch?creator=竹嶋えく as served 2026-08-04,
# cut to the fields this reads. The reading it states is the one round 3 accepted by hand.
ONE = """<rss><channel>
<item>
<title>君に好きっていわせたい</title>
<dc:creator>竹嶋, えく</dc:creator>
<dcndl:creatorTranscription>タケシマ, エク</dcndl:creatorTranscription>
<dc:publisher>一迅社</dc:publisher>
</item>
</channel></rss>"""

# A birth year rides along on both fields and belongs to neither the name nor its reading.
# 柊ゆたか came back this way in round 3 and had to be stripped on both sides to match at all.
YEARED = """<item>
<title>新米姉妹のふたりごはん</title>
<dc:creator>柊, ゆたか, 1981-</dc:creator>
<dcndl:creatorTranscription>ヒイラギ, ユタカ, 1981-</dcndl:creatorTranscription>
<dc:publisher>KADOKAWA</dc:publisher>
</item>"""

# An anthology record, where the pairing is positional and nothing in the XML joins a name to its
# own reading. Round 3 found three of four stored readings wrong on exactly this record.
FOUR = """<item>
<title>念願の悪役令嬢の身体を手に入れたぞ！</title>
<dc:creator>羽田, 遼亮</dc:creator>
<dc:creator>中島, 零</dc:creator>
<dc:creator>潮, 一葉</dc:creator>
<dc:creator>赤衣丸, 歩郎</dc:creator>
<dcndl:creatorTranscription>ハタ, リョウスケ</dcndl:creatorTranscription>
<dcndl:creatorTranscription>ナカジマ, レイ</dcndl:creatorTranscription>
<dcndl:creatorTranscription>ウシオ, ヒトハ</dcndl:creatorTranscription>
<dcndl:creatorTranscription>アカイ, マルボロウ</dcndl:creatorTranscription>
<dc:publisher>講談社</dc:publisher>
</item>"""

# The same record with one transcription missing, which is how a positional read attaches one
# person's reading to another person's name. This must yield nothing.
RAGGED = FOUR.replace("<dcndl:creatorTranscription>アカイ, マルボロウ"
                      "</dcndl:creatorTranscription>\n", "")

# Two records disagreeing about one written name. Neither is a majority and one may be somebody
# else, so the answer is that it is unresolved and worth a person's attention.
CONFLICT = """<item><title>A</title><dc:creator>灯</dc:creator>
<dcndl:creatorTranscription>アカシ</dcndl:creatorTranscription></item>
<item><title>B</title><dc:creator>灯</dc:creator>
<dcndl:creatorTranscription>アカリ</dcndl:creatorTranscription></item>"""


# The same name from a book record and from a magazine's table of contents. One reading, two
# renderings, quoted from the 東雲水生 response of 2026-08-04.
SPLIT_AND_UNSPLIT = """<item><title>あの日のきみを追いかけて</title>
<dc:creator>東雲, 水生</dc:creator>
<dcndl:creatorTranscription>シノノメ, ミズオ</dcndl:creatorTranscription></item>
<item><title>コミック百合姫 2025年5月号</title>
<dc:creator>東雲水生</dc:creator>
<dcndl:creatorTranscription>シノノメミズオ</dcndl:creatorTranscription></item>"""


def main(s):
    reading, ev = nr.resolve(ONE, "竹嶋えく")
    s.eq(reading, "タケシマ エク", "NDL's comma becomes the single space this project stores")
    s.eq(ev["status"], "stated", "and it is a statement by a cataloguing authority")
    s.eq(ev["records"], 1, "resting on the record it was read from")
    s.eq(ev["examples"], [("君に好きっていわせたい", "一迅社")],
         "which is named so a reviewer can check it")

    s.eq(nr.resolve(YEARED, "柊ゆたか")[0], "ヒイラギ ユタカ",
         "a birth year is cataloguing apparatus, on the name and on the reading alike")

    # THE SEPARATOR BEFORE THE YEAR IS NOT ALWAYS A COMMA. MADB writes `シノハラケンタ 1974-` with
    # a space, and madb_reading.py shares this rule rather than carrying a second copy of it.
    s.eq(nr.spaced("シノハラケンタ 1974-"), "シノハラケンタ",
         "a space before the year is the same cataloguing apparatus as a comma")
    # The counter-cases that keep the widened rule off a real name: both end in a number and
    # neither ends in the hyphen an open birth year carries.
    s.eq(nr.spaced("マポロ 3ゴウ"), "マポロ 3ゴウ", "a number inside a pen name survives it")
    s.eq(nr.spaced("ヒロpub. 2023"), "ヒロpub. 2023",
         "and so does a trailing year with no hyphen after it")

    s.eq(nr.resolve(FOUR, "潮一葉")[0], "ウシオ ヒトハ",
         "the third creator gets the third transcription, not the first")
    s.eq(nr.resolve(FOUR, "赤衣丸歩郎")[0], "アカイ マルボロウ", "and the fourth the fourth")

    # THE FAILURE WORTH REFUSING, which is publishing one artist's reading beside another's name.
    s.eq(nr.resolve(RAGGED, "潮一葉")[0], None,
         "lists of different lengths cannot be paired, so nothing is taken from the record")
    s.eq(nr.resolve(RAGGED, "潮一葉")[1]["status"], "no-record",
         "and the answer is that nothing was found, which is a state")

    # A PARTIAL MATCH IS NOT A MATCH. NDL holds many people under a short string, and three names
    # in round 3 were blocked because every record under them was somebody else.
    s.eq(nr.resolve(ONE, "竹嶋")[0], None, "a surname does not answer for a full name")
    s.eq(nr.resolve(ONE, "竹嶋えくお")[0], None, "and a longer name is a different person")
    s.eq(nr.resolve(ONE, "")[0], None, "no name, no lookup")
    s.eq(nr.resolve("", "竹嶋えく")[0], None, "no records, no reading")
    s.eq(nr.resolve("", "竹嶋えく")[1]["records"], 0, "counted as none rather than reported as one")

    # ONE READING WRITTEN TWO WAYS IS NOT TWO READINGS. NDL takes an electronic magazine's table
    # of contents as the publisher supplies it, unsplit, and a book record as 姓, 名. Treating that
    # as a conflict reported two of the first six names as unresolved when NDL had answered both.
    split, ev = nr.resolve(SPLIT_AND_UNSPLIT, "東雲水生")
    s.eq(split, "シノノメ ミズオ", "the split form is the answer, since it keeps the boundary")
    s.eq(ev["status"], "stated", "and the pair agrees rather than disagreeing")
    s.eq(ev["unsplit_also_seen"], True, "with the fact that a record supplied it unsplit kept")

    r, ev = nr.resolve(CONFLICT, "灯")
    s.eq(r, None, "two readings for one name settle nothing")
    s.eq(ev["status"], "conflicting", "and say so, because one of them may belong to someone else")
    s.eq(ev["readings"], ["アカシ", "アカリ"], "keeping both for the person who looks")

    s.eq(nr.key("竹嶋, えく"), nr.key("竹嶋えく"), "the separators are cataloguing, not the name")
    s.eq(nr.key("柊, ゆたか, 1981-"), nr.key("柊ゆたか"), "and so is the year")
    s.ne(nr.key("竹嶋えく"), nr.key("竹嶋えくお"), "while the characters themselves are the name")

    s.eq(nr.is_kana("タケシマ エク"), True, "katakana is what this project stores")
    s.eq(nr.is_kana("たけしま えく"), False, "hiragana is not, and must not pass as it")
    s.eq(nr.is_kana("竹嶋 えく"), False, "nor is the surface it was supposed to replace")
    s.eq(nr.is_kana(""), False, "and nothing is not a reading")
    # A DIGIT IS PART OF A NAME. NDL gives 西沢5ミリ as ニシザワ 5ミリ, and a rule allowing katakana
    # alone throws it away; the store already holds readings with digits and brackets in them. This
    # asks curate.py rather than restating its pattern, and the check is that the two agree.
    s.eq(nr.is_kana("ニシザワ 5ミリ"), True, "a digit the artist put in their name stays in it")

    s.eq(nr.query("竹嶋えく"),
         "https://ndlsearch.ndl.go.jp/api/opensearch?cnt=20&creator="
         "%E7%AB%B9%E5%B6%8B%E3%81%88%E3%81%8F", "the query the last three rounds used")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
