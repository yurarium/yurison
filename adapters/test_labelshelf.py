#!/usr/bin/env python3
"""labelshelf: a publisher's 百合 label on カドコミ, matched to the shop series that sells it.

COVERS = ['adapters/labelshelf.py']
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import labelshelf as ls                                                 # noqa: E402

TAIL = " - マンガ（漫画） 電子書籍無料試し読み・まとめ買いならBOOK☆WALKER"


def listing(stem, credit):
    return f"<title>{stem}{TAIL}</title><a>{credit}</a>"


def main(s):
    doc = {"works": [
        {"work_title": "水野と茶山", "marketing_label": "yuri", "chapters": None,
         "authors": ["西UKO"], "url": "https://comic-walker.com/detail/KC_002610_S"},
        {"work_title": "served", "marketing_label": "yuri", "chapters": [{"title": "第1話"}]},
        {"work_title": "unlabelled", "marketing_label": "none", "chapters": None}]}
    s.eq([w["work_title"] for w in ls.unserved(doc)], ["水野と茶山"],
         "a labelled listing serving no episode is a candidate; a served or unlabelled one is not")

    s.check(ls.held_by(ls._fold("民宿かがや"), {ls._fold("ゆりなつ -民宿かがや-")}),
            "a title held inside a longer one counts as held")
    s.check(not ls.held_by(ls._fold("きのこ"), {ls._fold("きのこいぬ")}),
            "while a short fold is not matched inside another title")

    # THE SERIES HAS TO BE THIS WORK, by its own title and by a person it credits.
    s.check(ls.matches(listing("水野と茶山", "西UKO"), "水野と茶山", ["西UKO"]),
            "a listing naming the work and crediting its author is the work")
    s.check(not ls.matches(listing("水野と茶山", "別人"), "水野と茶山", ["西UKO"]),
            "a listing that credits nobody カドコミ credits is not")
    s.check(not ls.matches(listing("別の作品", "西UKO"), "水野と茶山", ["西UKO"]),
            "and neither is the same author's other series")

    pages = {"https://bookwalker.jp/series/1/list/": listing("別の作品", "西UKO"),
             "https://bookwalker.jp/series/2/list/": listing("水野と茶山", "西UKO")}

    def get(url):
        if "/search/" in url:
            return 'href="https://bookwalker.jp/series/1/" href="https://bookwalker.jp/series/2/"'
        return pages[url]

    s.eq(ls.find(get, doc["works"][0]), ("2", "https://bookwalker.jp/series/2/", "水野と茶山"),
         "the first search result that is the work is taken, past a neighbour")

    # A SINGLE-VOLUME WORK IS A PRODUCT, and the search's series links are its sidebar.
    product = "https://bookwalker.jp/de7a3d9f2f-6ae1-441e-ba20-7d53012148dd/"
    lone = {"work_title": "わたしの友達が世界一かわいい", "authors": ["三月"]}

    def get2(url):
        if "/search/" in url:
            return f'href="https://bookwalker.jp/series/9/" href="{product}"'
        return (listing("わたしの友達が世界一かわいい", "三月") if url == product
                else listing("ランキングの何か", "誰か"))

    s.eq(ls.find(get2, lone), ("7a3d9f2f-6ae1-441e-ba20-7d53012148dd", product,
                               "わたしの友達が世界一かわいい"),
         "a work the shop sells as one volume is found at its product page")
    s.eq(ls.queries("＜harmony/＞ ハーモニー"), ["＜harmony/＞ ハーモニー", "ハーモニー"],
         "and a decorated title is searched again without its decoration")
    s.eq(ls.listing_title("水野と茶山（ビームコミックス）(マンガ（漫画）)の電子書籍無料試し読みならBOOK☆WALKER"),
         "水野と茶山", "the shop's suffix and the imprint come off the listing's title")
    r = ls.row(doc["works"][0], "2", "https://bookwalker.jp/series/2/", "水野と茶山", "2026-10-31")
    s.eq((r["url"], r["id"], r["publisher_label"]["source"], r["publisher_label"]["url"]),
         ("https://bookwalker.jp/series/2/", "2", "kadokomi",
          "https://comic-walker.com/detail/KC_002610_S"),
         "the row names the shop series and the publisher's page that states the label")
    s.check("label" not in r, "and keeps clear of `label`, which shelfingest reads as an imprint")

    adm = pathlib.Path(tempfile.mkdtemp()) / "admitted.yaml"
    adm.write_text('works:\n  - title: "オルターエゴ"\n  - title: "水野と茶山"\n'
                   '    publisher_label: {source: kadokomi}\n', encoding="utf-8")
    s.eq(ls.shelved(adm), {ls._fold("オルターエゴ")},
         "a work a shelf admitted is left to the shelf; one this intake admitted is not counted")

    s.check(ls.due(None, "2026-10-31"), "a work never asked is due")
    s.check(not ls.due("2026-10-01", "2026-10-31"), "one asked last month is not")
    s.check(ls.due("2026-07-01", "2026-10-31"), "and one asked a season ago is again")

    out = pathlib.Path(tempfile.mkdtemp()) / "k.yaml"
    ls.write(out, [r], {"どこにもない": "2026-10-31"}, "2026-10-31")
    import yaml
    back = yaml.safe_load(out.read_text())
    s.eq((back["items"][0]["id"], back["items"][0]["publisher_label"]["label"],
          back["checked"]), ("2", "百合", {"どこにもない": "2026-10-31"}),
         "what is written reads back as the rows and the works the shop did not answer for")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "labelshelf"))
