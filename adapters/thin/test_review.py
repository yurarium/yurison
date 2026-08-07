#!/usr/bin/env python3
"""thin/review.py: what a review row says, what sets a verdict, and what deliberately does not.

Everything here runs on a hand-built context, so no file and no network is involved. The point is
the rules, and the rule that matters most is the narrow one: only the admitting shop withdrawing
its own shelf sets `contradicted`.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from thin import review as R  # noqa: E402

COVERS = ["adapters/thin/review.py"]


def row(wid, title, imprint, shop="BOOK☆WALKER", shop_id="1", sources=()):
    return {"id": wid, "work": title, "author": "", "chapters": 0, "sources": list(sources),
            "evidence": [{"kind": "shelf", "rank": 4, "source": shop, "term": "百合",
                          "read": "2026-08-05"}],
            "print": [{"imprint": imprint, "volumes": 1, "work_id": f"bw-{shop_id}"}]}


def ctx_for(rows, facets=None, cmoa=None, antenna=(), tagged=()):
    return {"rows": rows, "antenna": set(antenna), "tagged": set(tagged),
            "facets": facets or {}, "cmoa_by_title": cmoa or {},
            "kadokomi_retrieved": "2026-08-01", "index": {}}


def said(kind, shelved=None, url="https://bookwalker.jp/series/1/", **extra):
    return {"kind": kind, "url": url, "status": 200,
            "said": {"shelved": shelved, "tags": {"14": "百合"} if shelved else {"1": "青年マンガ"},
                     **extra}}


def vol(shelved, n=1):
    return said("bookwalker", shelved=shelved, url=f"https://bookwalker.jp/de{n:036d}/")


def test_plan(s):
    rows = [row("w1", "ある本", "叢書")]
    ctx = ctx_for(rows, facets={"1": {"id": "1", "url": "https://bookwalker.jp/series/1/"}})
    got = R.plan(ctx)
    s.eq([p["kind"] for p in got], ["bookwalker"], "a shelf admission is re-asked at that shop")

    # EVERY candidate's shop page is planned, not a selected few. Reading only the suspicious rows
    # would make the answer depend on the ranking the reading is supposed to test.
    many = [row(f"w{i}", f"本{i}", f"叢書{i}", shop_id=str(i)) for i in range(5)]
    ctx2 = ctx_for(many, facets={str(i): {"id": str(i), "url": f"https://bookwalker.jp/series/{i}/"}
                                 for i in range(5)})
    s.eq(len(R.plan(ctx2)), 5, "one page per candidate, unranked")

    web = [row("w2", "連載本", "叢書", shop_id="9",
               sources=[{"platform": "カドコミ",
                         "url": "https://comic-walker.com/detail/KC_1_S"}])]
    ctx3 = ctx_for(web, facets={"9": {"id": "9", "url": "https://bookwalker.jp/series/9/"}})
    s.eq(sorted(p["kind"] for p in R.plan(ctx3)), ["bookwalker", "kadokomi"],
         "a work on the publisher's own platform gets that page too")

    # A work whose shop row was not re-identified is planned for nothing and says so later.
    s.eq(R.plan(ctx_for([row("w3", "行方不明", "叢書", shop_id="404")])), [],
         "no shop row means no page to read, which is a finding rather than a crash")

    # ROUND TWO. A series page without the tag is not an answer, so its volumes are planned.
    page = '<a href="https://bookwalker.jp/de%036d/">1</a>' % 7
    two = R.plan(ctx, read={"w1": [said("bookwalker", shelved=False)]},
                 pages={"https://bookwalker.jp/series/1/": page})
    s.eq([p["url"] for p in two], ["https://bookwalker.jp/de%036d/" % 7],
         "an untagged series page sends the pass to its volumes")
    s.eq(R.plan(ctx, read={"w1": [said("bookwalker", shelved=True)]},
                pages={"https://bookwalker.jp/series/1/": page}), [],
         "a series page that carries the tag needs no second round")
    s.eq(R.plan(ctx, read={"w1": [vol(False, 7)]}, pages={}), [],
         "a volume page without the tag is already the shop's answer about that volume")


def test_contradiction_is_narrow(s):
    s.check(R.contradicted([said("bookwalker", shelved=False)]),
            "the admitting shop no longer filing the work on that shelf is the rebuttal")
    s.check(not R.contradicted([said("bookwalker", shelved=True)]),
            "the shop repeating its own shelf is not")
    s.check(not R.contradicted([said("bookwalker", shelved=None)]),
            "a page nobody could read contradicts nothing; absence is a state")
    s.check(not R.contradicted([]), "and a work nothing was read for is not contradicted either")

    # 霧尾ファンクラブ IS THE COUNTER-CASE, and it broke the first version of this rule. The shop
    # tags volumes rather than works: its series page and volume 1 carry no 百合, volume 2 does, and
    # the work is plainly yuri. One page carrying the shelf clears it, whatever the others show.
    s.check(not R.contradicted([said("bookwalker", shelved=False), vol(False, 1), vol(True, 2)]),
            "a single volume still on the shelf answers for the work")
    s.check(R.contradicted([said("bookwalker", shelved=False), vol(False, 1), vol(False, 2)]),
            "only a run of noes across the volumes is an answer")

    # THE PLATFORM DOES NOT SET THE VERDICT. カドコミ applying neither 百合 nor GL is recorded and
    # ranked, and it is not a rebuttal: 115 of the 372 corpus works it hosts sit outside its yuri
    # tags, so its silence is far too common to settle anything by itself.
    s.check(not R.contradicted([said("kadokomi", yuri_tagged=False, genre="少女", tags=["ラブコメ"])]),
            "the publisher's platform declining the tag is evidence, not a verdict")


def test_rows(s):
    rows = [row("w1", "ある本", "叢書")]
    facets = {"1": {"id": "1", "url": "https://bookwalker.jp/series/1/", "male_directed": True}}
    ctx = ctx_for(rows, facets=facets)
    read = {"w1": [said("bookwalker", shelved=False)]}
    got = R.rows_for(ctx, read, "2026-08-07")[0]
    s.eq(got["verdict"], "contradicted", "the withdrawn shelf sets the verdict")
    s.check("not under tag 14" in got["read"][0]["said"],
            "and the row says what the page showed")
    s.eq(got["read"][0]["source"], "BOOK☆WALKER", "credited to whoever said it")
    s.eq(got["read"][0]["retrieved"], "2026-08-07", "with the date it was read")
    s.check(got["suspicion"] >= 5, "a contradiction goes to the top of the queue")

    still = R.rows_for(ctx, {"w1": [said("bookwalker", shelved=True)]}, "2026-08-07")[0]
    s.eq(still["verdict"], "unsupported",
         "the shop repeating itself is not a second source, so the work stays unsupported")
    s.check("male_directed" in still["signals"],
            "the 男性向け facet is recorded even though it moves no ranking")
    s.eq(still["suspicion"], 0, "and it moves no ranking")

    # A ROW EXAMINED AND FOUND SOUND IS KEPT. That is the record that stops the same work being
    # re-examined from nothing, which is the whole reason the file lists all 296.
    corr = R.rows_for(ctx_for([row("w2", "百合な話", "叢書")]), {}, "2026-08-07")[0]
    s.eq(corr["verdict"], "corroborated", "the publisher's own title names the genre")
    s.check(corr.get("unread"), "and an unread shop page is stated rather than left blank")


def test_ordering_and_summary(s):
    rows = [row("wa", "静かな本", "叢書", shop_id="1"),
            row("wb", "騒がしい本", "叢書", shop_id="2")]
    facets = {i: {"id": i, "url": f"https://bookwalker.jp/series/{i}/"} for i in ("1", "2")}
    read = {"wb": [said("bookwalker", shelved=False)], "wa": [said("bookwalker", shelved=True)]}
    got = R.rows_for(ctx_for(rows, facets=facets), read, "2026-08-07")
    s.eq([r["work"] for r in got], ["wb", "wa"], "strongest suspicion first")
    sm = R.summary(got)
    s.eq(sm["works"], 2, "the summary counts what the file holds")
    s.eq(sm["verdicts"]["contradicted"], 1, "and how the verdicts fell")


def test_title_matching(s):
    # コミックシーモア prints the short title; the bibliography holds the long one. `bare` is what
    # closed 11 of the 22 gaps, and it must not fold two different works together.
    s.eq(R.bare("抱かれたい女(ひと) = person who wants to be embraced : JDだけど…"),
         R.bare("抱かれたい女"), "a Latin gloss and a furigana bracket are not part of the title")
    s.ne(R.bare("最後の制服"), R.bare("最初の制服"), "and stripping does not merge distinct titles")


def main(s):
    test_plan(s)
    test_contradiction_is_narrow(s)
    test_rows(s)
    test_ordering_and_summary(s)
    test_title_matching(s)


if __name__ == "__main__":
    sys.exit(testkit.run(main, "thin/review"))
