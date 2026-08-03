#!/usr/bin/env python3
"""pass1_kana.py: the free pass, where the name is already its own reading.

COVERS = ['adapters/names/pass1_kana.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit
from adapters.names import pass1_kana as p1


class FakeStore:
    """Enough of the store to observe what pass 1 writes, and nothing more."""

    def __init__(self, existing=None):
        self.records = {"authors": dict(existing or {}), "titles": {}}
        self.written = []
        self.compacted = 0

    def record(self, kind, ja, **fields):
        self.written.append((kind, ja, fields))
        self.records[kind][ja] = fields

    def maybe_compact(self):
        pass

    def compact(self):
        self.compacted += 1


def main(s):
    st = FakeStore()
    stats = p1.run(st, ["ヤマダタロウ", "山田太郎", "さとうはなこ"], ["ユリ", "百合"])

    written = {(k, ja) for k, ja, _ in st.written}
    # A kana name is already its reading, so it needs no dictionary and no guess.
    s.check(("authors", "ヤマダタロウ") in written, "a katakana author is resolved for free")
    s.check(("authors", "さとうはなこ") in written, "a hiragana author is resolved too")
    s.check(("titles", "ユリ") in written, "a kana title is resolved")
    # A name with kanji is NOT this pass's business, and guessing here would be the expensive error.
    s.check(("authors", "山田太郎") not in written, "a name with kanji is left to a later pass")
    s.check(("titles", "百合") not in written, "and so is a title with kanji")

    fields = dict((ja, f) for k, ja, f in st.written)["さとうはなこ"]
    s.eq(fields["reading"], "サトウハナコ", "the reading is stored as katakana, never as romaji")
    s.eq(fields["reading_basis"], "surface", "the basis says the surface WAS the reading")
    s.eq(fields["pass"], 1, "the pass is recorded, so the provenance is traceable")
    # §5: an author's rendering is a romanisation generated per reader style, so no `en` is stored.
    s.eq(fields.get("basis"), "romaji", "an author is marked as rendered from the reading")
    s.check("en" not in fields, "and no English string is stored, since style is the reader's")

    s.check(stats["authors-resolved"] >= 2, "the count reflects what was written")
    s.eq(st.compacted, 1, "the store is compacted once at the end")

    # A name already resolved by this pass is not rewritten, or every run would churn the file.
    again = FakeStore({"ヤマダタロウ": {"reading_basis": "surface"}})
    p1.run(again, ["ヤマダタロウ"], [])
    s.eq(again.written, [], "an already-surfaced name is skipped rather than rewritten")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.pass1_kana"))
