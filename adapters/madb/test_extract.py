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


if __name__ == "__main__":
    sys.exit(testkit.run(main, "madb.extract"))
