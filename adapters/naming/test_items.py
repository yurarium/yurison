#!/usr/bin/env python3
"""naming/items.py: what the naming job is told about each title, and nothing more.

COVERS = ['adapters/naming/items.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import items as ni                                                      # noqa: E402


def main(s):
    series = [{"work": "鈴木りつ短編集", "work_en": {"basis": "romaji"}, "latest": "2026-10-01",
               "author": "鈴木りつ", "url": "https://shop/1",
               "sources": [{"platform": "BOOK☆WALKER", "url": "https://shop/1"}]},
              {"work": "決まった", "work_en": {"basis": "romaji"}, "latest": "2026-10-09"},
              {"work": "名前あり", "work_en": {"basis": "translated"}, "latest": "2026-10-10"}]
    named = {"決まった": {"en": "Decided"},
             "鈴木りつ短編集　考幻学入門": {"en": "Suzuki Ritsu Short Stories: An Introduction to Phantasmology"}}
    rows = ni.untitled(series, set(named))
    s.eq([r["work"] for r in rows], ["鈴木りつ短編集"],
         "a romanised title nobody decided is asked; a decided or named one is not")
    it = ni.item(rows[0], named)
    s.eq((it["key"], it["author"], it["platforms"], it["pages"]),
         ("鈴木りつ短編集", "鈴木りつ", ["BOOK☆WALKER"], ["https://shop/1"]),
         "an item holds the key, the creator, the platform and the page to read, once each")
    s.eq([r["ja"] for r in it["related"]], ["鈴木りつ短編集　考幻学入門"],
         "and the titles already named that share its start, so a series is named one way")
    s.eq(ni.related("短い", named), [], "a title too short to share a start has no relatives")
    s.eq(ni.related("決まったのゆるい本", named, kin=["決まった", "名前なし"]),
         [{"ja": "決まった", "en": "Decided"}],
         "a named title by the same creator is a relative though it starts otherwise")
    book = {"work": "本", "print": [{"shop_url": "https://www.cmoa.jp/title/1/"}]}
    s.eq(ni.item(book, {})["pages"], ["https://www.cmoa.jp/title/1/"],
         "a book's page is its shop's, since it has no web source")
    volumes(s)


def volumes(s):
    """A volume's own title is asked about with the work it belongs to beside it."""
    series = [{"work": "鈴木りつ短編集", "author": "鈴木りつ",
               "work_en": {"basis": "translated", "en": "Suzuki Ritsu Short Stories"},
               "print": [{"work_ids": ["bw-541043"], "shop_url": "https://bookwalker.jp/series/541043/"}]}]
    records = [{"work_id": "bw-541043", "volumes": [
                   {"designation": "考幻学入門", "subtitle": "考幻学入門", "published": "2025-08-20"},
                   {"designation": "鈴木りつ第二短編集 垂直・宇宙・無限",
                    "subtitle": "鈴木りつ第二短編集 垂直・宇宙・無限", "published": "2026-09-20"},
                   {"number": "3", "published": "2027-01-01"}]},
               {"work_id": "bw-elsewhere", "volumes": [{"subtitle": "考幻学入門"}]},
               {"work_id": "nobody", "volumes": [{"subtitle": "どこにもない"}]}]
    got = ni.volume_items(series, records, {}, 10)
    s.eq([i["key"] for i in got], ["鈴木りつ第二短編集 垂直・宇宙・無限", "考幻学入門"],
         "each subtitle once, newest book first; a book called by its number and one no work "
         "holds are not asked about")
    s.eq((got[1]["volume_of"], got[1]["pages"], got[1]["author"]),
         ({"ja": "鈴木りつ短編集", "en": "Suzuki Ritsu Short Stories"},
          ["https://bookwalker.jp/series/541043/"], "鈴木りつ"),
         "with the work's title and English beside it, and the page that lists the book")
    s.eq([i["key"] for i in ni.volume_items(series, records, {"考幻学入門": {"en": "x"}}, 10)],
         ["鈴木りつ第二短編集 垂直・宇宙・無限"], "a subtitle already named is not asked again")
    s.eq(len(ni.volume_items(series, records, {}, 1)), 1, "and the limit holds")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "naming.items"))
