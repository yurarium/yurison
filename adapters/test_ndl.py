#!/usr/bin/env python3
"""ndl.py: reading a series' volume record, and refusing to read someone else's."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ndl  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/ndl.py"]


def item(title, creator, issued, isbn, vol="", genre="漫画", publisher="芳文社"):
    return f"""<item><title>{title}</title>
  <dc:title>{title}</dc:title>
  <dc:creator>{creator}</dc:creator>
  <dcndl:volume>{vol}</dcndl:volume>
  <dc:publisher>{publisher}</dc:publisher>
  <dcterms:issued>{issued}</dcterms:issued>
  <dcndl:genre>{genre}</dcndl:genre>
  <dc:identifier xsi:type="dcndl:ISBN">{isbn}</dc:identifier></item>"""


# Quoted in shape from the served 恋する小惑星 response, shortened to three volumes.
KOISURU = "<channel>" + "".join([
    item("恋する小惑星 (アステロイド)", "Quro", "2018.4", "978-4-8322-4936-3", "1"),
    item("恋する小惑星 (アステロイド)", "Quro", "2020.3", "978-4-8322-7167-8", "3"),
    item("恋する小惑星", "Quro", "2024.9", "978-4-8322-9568-1", "6"),
    # The search also returns things that are not the manga, which is why genre is checked.
    item("歩いていこう! TVアニメ「恋する小惑星」オープニングテーマ", "東山奈央", "2020.2",
         "", genre="音楽"),
    item("インタビュー 恋する小惑星", "編集部", "2021.6", "978-0-0000-0000-0", genre="雑誌記事"),
])


def main(s):
    got = ndl.volumes(KOISURU, "Quro")
    s.eq([v["volume"] for v in got], ["1", "3", "6"], "the manga volumes, oldest first")
    s.eq(got[-1]["issued"], "2024.9", "and the date the last one was issued")

    r = ndl.run(KOISURU, "Quro")
    s.eq(r["last_issued"], "2024.9", "which is the fact the completion question turns on")
    s.eq(r["held"], 3, "counted as what NDL holds")
    s.eq(r["publisher"], "芳文社", "with the publisher, so the answer can be checked")

    # THE FAULT THIS IS BUILT AROUND. A title search is a string match against every book in Japan:
    # `citrus+` returns two volumes of an unrelated 2007 book. Agreement on the author is what
    # separates a record about this work from a record about a different one with a similar name.
    other = "<channel>" + item("citrus", "別の著者", "2007.10", "978-4-0000-0000-1", "1")
    s.eq(ndl.volumes(other, "サブロウタ"), [],
         "a book by somebody else is not this work's volume record")
    s.eq(ndl.run(other, "サブロウタ"), None, "so the series record says nothing rather than wrong")
    s.eq(len(ndl.volumes(other)), 1,
         "and without an author to check against, the same search matches it, "
         "which is why the caller has to supply one")

    # Neither an empty response nor a response with nothing catalogued as manga says anything.
    s.eq(ndl.run("", "Quro"), None, "no response, no answer")
    s.eq(ndl.run("<channel></channel>", "Quro"), None, "and no items, no answer")
    s.eq(ndl.volumes("<channel>" + item("x", "Quro", "2020.1", "", genre="漫画"), "Quro"), [],
         "a record with no ISBN is not a volume we can cite")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
