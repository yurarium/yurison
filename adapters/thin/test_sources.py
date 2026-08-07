#!/usr/bin/env python3
"""thin/sources.py: what each page reader takes off a page, and what it declines to conclude.

The fixtures are cut down to the elements each reader looks at, which is what makes them readable
enough to tell that they are right (STANDING-INSTRUCTIONS §12).
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from thin import sources as S  # noqa: E402

COVERS = ["adapters/thin/sources.py"]


def bw_page(tags):
    return "".join(f'<a href="/tag/{i}/" class="tag">{n}</a>' for i, n in tags)


def cmoa_page(genre, brand, crumbs, yuri=True, blurb="ある紹介文", authors=("ある人",), product=True):
    prod = {"@context": "https://schema.org", "@type": "Product", "name": "ある本: 1",
            "brand": brand, "category": genre, "description": blurb}
    book = {"@context": "https://schema.org", "@type": "Book", "name": "ある本: 1",
            "author": [{"@type": "Person", "name": n} for n in authors]}
    crumb = {"@context": "https://schema.org", "@graph": [
        {"@type": "BreadcrumbList",
         "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n}
                             for i, n in enumerate(crumbs)]}]}
    shelf = '<a href="/search/genre/37/">百合・GL</a>' if yuri else ""
    blocks = ([prod] if product else []) + [book, crumb]
    return "".join('<script type="application/ld+json">'
                   + json.dumps(b, ensure_ascii=False) + "</script>"
                   for b in blocks) + shelf


def kado_page(genre, sub, tags):
    payload = {"props": {"pageProps": {"dehydratedState": {"queries": [
        {"state": {"data": {"work": {"title": "ある本", "genre": {"name": genre},
                                     "subGenre": {"name": sub},
                                     "tags": [{"name": t} for t in tags]}}}}]}}}}
    return ('<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(payload, ensure_ascii=False) + "</script>")


def test_bookwalker(s):
    shelved = S.bookwalker_filing(bw_page([("1491", "青年マンガ"), ("14", "百合"), ("2", "男性向け")]))
    s.eq(shelved["shelved"], True, "tag 14 on the work page is the shop repeating its shelf")
    s.eq(shelved["tags"]["1491"], "青年マンガ", "the rest of the shop's filing rides along")

    # THE CASE THE PASS EXISTS FOR. `w01734` carries these five tags and not tag 14, while the
    # capture of 2026-08-04 listed it under tag 14.
    gone = S.bookwalker_filing(bw_page([("1493", "女性マンガ"), ("3", "女性向け"),
                                        ("146", "ファンタジー"), ("1995", "異世界系作品"),
                                        ("733", "角川ビーンズ文庫")]))
    s.eq(gone["shelved"], False, "a tagged page without tag 14 says the shop no longer shelves it")

    # ABSENCE IS A STATE. A page we could not read must not look like a work the shop unshelved.
    s.eq(S.bookwalker_filing("<html>nothing</html>")["shelved"], None,
         "a page with no tags at all is unread, not unshelved")
    s.eq(S.bookwalker_filing("")["shelved"], None, "and so is an empty body")


def test_volume_pages(s):
    # THE TAG IS A VOLUME'S, NOT A WORK'S. A series page that lacks it settles nothing until its
    # volumes have been read, so the links off the series page are the second round's plan.
    page = ('<a href="https://bookwalker.jp/de1954424b-5b3a-4c0c-8f96-6b0a0511e598/">表紙</a>'
            '<a href="https://bookwalker.jp/de1954424b-5b3a-4c0c-8f96-6b0a0511e598/">1巻</a>'
            '<a href="https://bookwalker.jp/de39097d03-d9e0-412b-841d-9df406381746/">2巻</a>')
    got = S.volume_pages(page)
    s.eq(len(got), 2, "a volume linked twice is one page to read")
    s.check(got[0].endswith("de1954424b-5b3a-4c0c-8f96-6b0a0511e598/"),
            "and they keep the order the shop listed them in")

    # robots.txt disallows /de*/?sample=*, and a sample link is not this shape.
    s.eq(S.volume_pages('<a href="https://bookwalker.jp/de1954424b-5b3a-4c0c-8f96-'
                        '0a6b0511e598/?sample=1">試し読み</a>'), [],
         "a sample link is not a volume page and is never planned")
    s.eq(S.volume_pages("<html>a series with nothing listed</html>"), [],
         "a series page listing no volumes plans nothing rather than raising")


def test_cmoa(s):
    got = S.cmoa_filing(cmoa_page("女性マンガ", "一迅社",
                                  ["トップ", "女性マンガ", "一迅社", "百合姫コミックス", "ある本"]))
    s.eq(got["genre"], "女性マンガ", "the shop states its own top-level genre")
    s.eq(got["publisher"], "一迅社", "and the publisher")
    s.check("百合姫コミックス" in got["crumbs"], "the imprint is in the breadcrumb, publisher-side")
    s.eq(got["shelved"], True, "genre 37 present is the shop repeating its shelf")
    s.eq(S.cmoa_filing(cmoa_page("少年マンガ", "秋田書店", ["トップ"], yuri=False))["shelved"], False,
         "and absent is the shop no longer filing it there")
    s.eq(S.cmoa_filing("")["shelved"], None, "an unread page states nothing")

    # THE BLURB IS READ AND NEVER STORED. It is returned so a person can read it during the pass;
    # REQUIREMENTS §2 keeps it out of the repository, and review.py writes our own words instead.
    s.eq(got["blurb"], "ある紹介文", "the synopsis is available to the pass")

    s.eq(S.cmoa_filing("<script type=\"application/ld+json\">{bad json</script>")["genre"], None,
         "a malformed payload yields nothing rather than raising")

    # WHO THE SHOP SAYS WROTE IT answers a scope question nothing else in this pass can reach.
    # サンストーン is credited to a foreign author and a Japanese translator, and DEFINITIONS §6 puts
    # a Japanese edition that is a translation out of scope whatever shelf it sits on.
    foreign = S.cmoa_filing(cmoa_page(None, None,
                                      ["トップ", "青年マンガ", "誠文堂新光社", "G-NOVELS", "サンストーン"],
                                      authors=("ステファン・セジク", "上田香子"), product=False))
    s.eq(foreign["authors"], ["ステファン・セジク", "上田香子"], "the shop's own credit line is kept")
    s.check("G-NOVELS" in foreign["crumbs"],
            "a page with no Product block still answers from its breadcrumb")
    s.eq(foreign["shelved"], True, "and the shelf question is answered without a Product block")


def test_kadokomi(s):
    got = S.kadokomi_filing(kado_page("女性", "ファンタジー",
                                      ["コミカライズ", "異世界", "ラブコメ", "転生", "悪役令嬢"]))
    s.eq(got["genre"], "女性", "the publisher's platform states its own genre")
    s.eq(got["sub_genre"], "ファンタジー", "and its sub-genre")
    s.eq(got["yuri_tagged"], False, "and it did not apply 百合 or GL here")
    s.check("悪役令嬢" in got["tags"], "what it applied instead is the substance")

    s.eq(S.kadokomi_filing(kado_page("女性", "恋愛", ["百合", "現代"]))["yuri_tagged"], True,
         "the platform's own 百合 tag is publisher-side labelling under DEFINITIONS §4")
    s.eq(S.kadokomi_filing(kado_page("少年", "恋愛", ["GL"]))["yuri_tagged"], True,
         "GL counts, and enumerating 百合 alone once missed a work carrying only GL")
    s.eq(S.kadokomi_filing("<html>no payload</html>"), None,
         "a page with no payload is unread, and says None rather than an empty filing")


def test_dispatch(s):
    s.eq(S.read("bookwalker", bw_page([("14", "百合")]))["shelved"], True,
         "read dispatches on the kind of page")
    s.raises(ValueError, lambda: S.read("someshop", "<html/>"),
             "a kind with no reader raises rather than returning a silent nothing")


def main(s):
    test_bookwalker(s)
    test_volume_pages(s)
    test_cmoa(s)
    test_kadokomi(s)
    test_dispatch(s)


if __name__ == "__main__":
    sys.exit(testkit.run(main, "thin/sources"))
