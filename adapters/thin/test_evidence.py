#!/usr/bin/env python3
"""thin/evidence.py: the imprint-concentration query, and what each structural signal will and
will not fire on.

The counter-cases are the point. Every regex here was wrong in a first draft and each wrong version
is pinned below, because a rule that only demonstrates its own hits proves nothing about the ones
it should decline.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from thin import evidence as e  # noqa: E402

COVERS = ["adapters/thin/evidence.py"]


def work(wid, title, imprint=None, shelves=1, kind="shelf", volumes=1, chapters=0,
         author="", sources=(), rank=4):
    """One series.json row, trimmed to the fields this module reads."""
    return {
        "id": wid,
        "work": title,
        "author": author,
        "chapters": chapters,
        "sources": list(sources),
        "evidence": [{"kind": kind, "rank": rank, "source": "BOOK☆WALKER", "term": "百合"}
                     for _ in range(shelves)],
        "print": [{"imprint": imprint, "volumes": volumes}] if imprint is not None
                 else [{"volumes": volumes}],
    }


def split(row):
    """The credit splitter's contract, stubbed: one name per comma."""
    return [n for n in (row.get("author") or "").split(",") if n]


def test_query(s):
    # A yuri line contributes dozens of rows, so its works are not thin. A line with one row is.
    common = [work(f"c{i}", f"作品{i}", "百合姫コミックス") for i in range(4)]
    rare = work("r1", "ある本", "めずらしい叢書")
    rows = common + [rare]
    got = [r["id"] for r in e.candidates(rows)]
    s.eq(got, ["r1"], "an imprint with one shelf row is thin; a line with four is not")

    # THE THRESHOLD IS TWO, and it is the operator's. Three rows on one imprint is not thin.
    three = [work(f"t{i}", f"三{i}", "みっつの叢書") for i in range(3)]
    s.eq([r["id"] for r in e.candidates(three)], [],
         "an imprint contributing three works is above the threshold")
    s.eq(len(e.candidates(three, threshold=3)), 3, "the threshold is a parameter, not a constant")

    # A ROW NAMING NO IMPRINT IS IN. 68 of the operator's 296 are this case: a shop that printed no
    # label has said less about the work, which is the thinness the query is looking for.
    s.eq([r["id"] for r in e.candidates([work("n1", "無銘")])], ["n1"],
         "a work with no imprint at all is a candidate")

    # A SECOND PIECE OF EVIDENCE TAKES A WORK OUT, whatever its imprint. That is what makes this a
    # thin-evidence query rather than a rare-imprint query.
    two = work("x1", "ふたつ", "めずらしい叢書", shelves=2)
    s.eq(e.candidates([two]), [], "two evidence rows is not one evidence row")
    lab = work("x2", "ラベル", "めずらしい叢書")
    lab["evidence"].append({"kind": "imprint", "rank": 1, "source": "一迅社", "term": "百合姫"})
    s.eq(e.candidates([lab]), [], "a publisher-side row alongside the shelf is not thin evidence")
    s.eq(e.candidates([work("x3", "空", "めずらしい叢書", shelves=0)]), [],
         "a work with no evidence at all is not a shelf admission and is out of scope here")


def test_title_term(s):
    yes = ["百合な片想いちゃん", "ゆりにん～レズビアンカップル妊活奮闘記～", "リリィ･マーブル",
           "女の子同士で付き合ってます。", "LatteComi コミックアンソロジー【百合】"]
    for t in yes:
        s.check(e.TERM.search(t), f"the publisher's own title names the genre: {t}")

    # THE COUNTER-CASES, every one of which the first draft got wrong.
    s.check(not e.TERM.search("小百合さんの妹は天使"),
            "小百合 is a woman's name, not the genre")
    s.check(not e.TERM.search("百合子の一日"), "百合子 is a name too")
    s.check(not e.TERM.search("ゆりかごのうた"), "ゆりかご is a cradle")
    s.check(not e.TERM.search("ユリウス帝国戦記"), "ユリウス is Julius")
    s.check(not e.TERM.search("和太鼓†ガールズ～改訂版～"),
            "ガールズ alone is not ガールズラブ, and this one is about drumming")
    s.check(not e.TERM.search("GLASS HEART"), "GL inside a Latin word is not the label")
    s.check(e.TERM.search("GL短編集"), "GL as its own token is")


def test_other_category(s):
    # \b DOES NOT WORK HERE. Python treats コ as a word character, so \bBL\b never matches inside
    # `Kobunsha BLコミックシリーズ`, which is the actual row that made this signal worth having.
    s.check(e.OTHER_CATEGORY.search("Kobunsha BLコミックシリーズ"),
            "a BL imprint is the publisher naming a different category")
    s.check(e.OTHER_CATEGORY.search("BLIC-ERO"), "an ero imprint likewise")
    s.check(e.OTHER_CATEGORY.search("TSコミックス"), "and a TS line")
    s.check(not e.OTHER_CATEGORY.search("BLADE COMICS"),
            "BL inside BLADE is not a BL imprint")
    s.check(not e.OTHER_CATEGORY.search("百合姫コミックス"), "a yuri line is not another category")


def test_container(s):
    s.check(e.CONTAINER.search("アーシェラ将軍シリーズ"), "a 〜シリーズ row is a bundle")
    s.check(e.CONTAINER.search("【合本版】純蒸パイルバンカー"), "so is a 合本版")
    s.check(e.CONTAINER.search("百合姫表紙集 2011-2025"), "and a cover collection")
    # シリーズ IS ORDINARY INSIDE AN IMPRINT NAME, so the anchor matters: MFコミックス ジーンシリーズ
    # is where these works are published, not what the row is.
    s.check(not e.CONTAINER.search("ピエタとトランジ"), "an ordinary work title is not a container")
    s.check(not e.CONTAINER.search("シリーズもののお話"),
            "シリーズ inside a title is not a bundle; only a title that ends in it")


def test_signals_and_verdict(s):
    idx = e.author_index([dict(work("o1", "別の本", "叢書", rank=1), author="Ａ"),
                          dict(work("o2", "無関係", "叢書"), author="Ｂ")], split)

    row = dict(work("w1", "ある本", "叢書", author="Ａ"), )
    sig = e.signals(row, key="あるほん", antenna={"あるほん"}, index=idx, split=split)
    s.check(sig["antenna"], "the antenna's own 百合 tag naming the work is a second comparator")
    s.check(sig["author_in_field"],
            "a credited person with another publisher-side work works in the field")
    s.eq(e.verdict(sig), "corroborated", "a second source naming the work corroborates it")

    bare = e.signals(work("w2", "ある本", "叢書"), key="あるほん")
    s.eq(e.verdict(bare), "unsupported", "no second source is unsupported, which is not a fault")
    s.eq(e.verdict(bare, contradicted=True), "contradicted",
         "contradicted comes from a page somebody read, never from a signal")

    # A WORK CANNOT VOUCH FOR ITSELF. `w1` is in the index under Ａ in the real assembly, so the
    # exclusion of the row's own id is what keeps `author_in_field` from being always true.
    self_only = e.author_index([dict(work("s1", "自分", "叢書", rank=1), author="Ｃ")], split)
    s.check(not e.in_field(dict(work("s1", "自分", "叢書", rank=1), author="Ｃ"),
                           self_only, split),
            "a work's own publisher-side evidence is not its author's other credit")


def test_platform_declined(s):
    on = work("p1", "載っている", "叢書",
              sources=[{"platform": "カドコミ", "url": "https://comic-walker.com/detail/KC_1_S"}])
    s.check(not e.signals(on, tagged={"KC_1_S"})["platform_declined"],
            "a work the platform did tag has not been declined")
    s.check(e.signals(on, tagged={"KC_2_S"})["platform_declined"],
            "a work the platform hosts and did not tag has")
    off = work("p2", "どこにもない", "叢書")
    s.check(not e.signals(off, tagged={"KC_1_S"})["platform_declined"],
            "a work the platform does not host cannot have declined it; the signal abstains")


def test_ranking(s):
    dec = {k: False for k in ("title_term", "imprint_term", "antenna", "platform_declined",
                              "other_category", "container", "prominent", "author_in_field",
                              "male_directed")}
    s.eq(e.suspicion(dec), 0, "a candidate with nothing either way sits at zero")
    s.check(e.suspicion({**dec, "platform_declined": True}) >
            e.suspicion({**dec, "prominent": True}),
            "a publisher-side witness that declined outranks mere size")
    s.check(e.suspicion({**dec, "prominent": True, "author_in_field": True}) <
            e.suspicion({**dec, "prominent": True}),
            "an author who works in the field lowers suspicion")

    # 男性向け IS RECORDED AND SCORED AT ZERO. It is on 46% of the shelf and FALSE on `w01734`, the
    # one work we know does not belong, so weighting it would rank by a coin flip that also gets
    # the known case backwards.
    s.eq(e.suspicion({**dec, "male_directed": True}), 0,
         "the shop's 男性向け facet moves nothing")
    s.check("male_directed" not in e.WEIGHTS, "and carries no weight to be changed by accident")


def main(s):
    test_query(s)
    test_title_term(s)
    test_other_category(s)
    test_container(s)
    test_signals_and_verdict(s)
    test_platform_declined(s)
    test_ranking(s)


if __name__ == "__main__":
    sys.exit(testkit.run(main, "thin/evidence"))
