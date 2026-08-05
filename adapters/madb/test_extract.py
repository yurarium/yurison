#!/usr/bin/env python3
"""madb/extract.py: flattening MADB's polymorphic fields without losing the reading.

COVERS = ['adapters/madb/extract.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import extract as m


def main(s):
    # MADB hands the same logical field back as a string, a dict or a list depending on the record,
    # so every consumer would otherwise have to know all three shapes.
    s.eq(m.flat("plain"), "plain", "a string passes through")
    s.eq(m.flat({"@value": "v"}), "v", "a dict yields its value")
    s.eq(m.flat({"@id": "http://x/1"}), "http://x/1", "a dict without @value falls back to @id")
    s.eq(m.flat(["a", "b"]), "a / b", "a list is joined")
    s.eq(m.flat(None), "", "None flattens to empty rather than the string 'None'")

    # The reading is the point: it is what NAMES-PLAN needs and what a naive flatten would bury.
    v = [{"@value": "青田", "@language": "ja"}, {"@value": "アオタ", "@language": "ja-hrkt"}]
    s.eq(m.reading(v), "アオタ", "the ja-hrkt half is the reading")
    s.eq(m.primary(v), "青田 / アオタ", "primary keeps the non-reading form")
    s.eq(m.reading("no reading here"), "", "a bare string has no reading")
    s.eq(m.reading([{"@value": "x", "@language": "ja"}]), "",
         "a list without a ja-hrkt entry has no reading")

    # Publisher strings embed the reading behind a separator instead of in a field.
    s.eq(m.split_reading("一迅社　∥　イチジンシャ"), "一迅社", "the name half is taken")
    s.eq(m.split_reading("一迅社"), "一迅社", "a string without the separator is unchanged")

    s.eq(m.local_id({"@id": "http://mediaarts-db.jp/mg/12345"}), "12345", "the id tail is taken")

    # These are Japanese strings that routinely contain YAML metacharacters, so quoting is not
    # optional: an unescaped quote would break the file the whole pipeline reads next.
    s.eq(m.yaml_str('say "hi"'), '"say \\"hi\\""', "embedded quotes are escaped")
    s.eq(m.yaml_str("back\\slash"), '"back\\\\slash"', "backslashes are escaped first")

    s.eq(m.norm("ＹＵＲＩ・花"), m.norm("yuri花"), "width, case and separators fold")


    # A TITLE IS NOT AN IDENTIFIER. `トワ・エ・モア` is a コンパス anthology from 1996 with no
    # creator, and a 講談社 KCデラックス series by 仲藤ぬい from 2024. Matched on the title alone,
    # the second was filed inside the first and one work held volumes 28 years apart.
    OLD = {"schema:identifier": "C1", "schema:name": "トワ・エ・モア", "schema:publisher": "コンパス",
           "schema:brand": "コンパスアンソロジーコミックシリーズ"}
    NEW = {"schema:identifier": "M2", "schema:name": "トワ・エ・モア", "schema:publisher": "講談社",
           "schema:brand": "KCデラックス", "schema:creator": "[著]仲藤ぬい"}
    s.check(not m.agrees(NEW, OLD), "a shared title with nothing else agreeing is not one work")
    ser = {"C1": OLD}
    s.eq(m.key_of(NEW, ser, m.title_index(ser))[1], "title-only",
         "so the volume becomes its own work rather than somebody else's")

    # AND THE CASE THAT MUST SURVIVE IT. 一迅社's yuri line passed to 講談社, so volumes of one
    # work disagree about the publisher. The creator is what says they are one work.
    ICH = {"schema:identifier": "C2", "schema:name": "ゆるゆり", "schema:publisher": "一迅社",
           "schema:creator": "なもり"}
    KOD = {"schema:identifier": "M3", "schema:name": "ゆるゆり", "schema:publisher": "[発売]講談社",
           "schema:creator": "[著]なもり / ナモリ"}
    s.check(m.agrees(KOD, ICH), "a house changing hands does not split a work whose creator agrees")
    ser2 = {"C2": ICH}
    s.eq(m.key_of(KOD, ser2, m.title_index(ser2))[1], "title-match", "and the volume still joins")
    s.eq(m.people(KOD), {"なもり"}, "a role and a trailing reading are not people")
    s.eq(m.bare_publisher({"schema:publisher": "小学館クリエイティブ(発売)"}),
         m.bare_publisher({"schema:publisher": "小学館クリエイティブ"}),
         "a distributor role in a trailing bracket is not a second publisher")

if __name__ == "__main__":
    sys.exit(testkit.run(main, "madb.extract"))
