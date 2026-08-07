#!/usr/bin/env python3
"""by_platform_isbn.py: a platform says which edition its series has, and the bibliography answers."""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit                                                                 # noqa: E402
from madb import by_platform_isbn as bp, extract                               # noqa: E402

COVERS = ["adapters/madb/by_platform_isbn.py"]

VOL1 = {"schema:identifier": "M100", "schema:isbn": "9784065250891",
        "schema:name": "雨夜の月 1", "schema:isPartOf": ".../C900",
        "schema:volumeNumber": "1", "schema:datePublished": "2021-08-06",
        "schema:brand": "ヤンマガKCスペシャル"}
VOL2 = {"schema:identifier": "M101", "schema:isbn": "4065310776",
        "schema:name": "雨夜の月 4", "schema:isPartOf": ".../C900",
        "schema:volumeNumber": "4", "schema:datePublished": "2023-04-06",
        "schema:brand": "ヤンマガKCスペシャル"}
VOL3 = {"schema:identifier": "M200", "schema:isbn": "9784087927498",
        "schema:name": "博イラスト集 明日ちゃんまでの足跡", "schema:isPartOf": ".../C901",
        "schema:volumeNumber": "1", "schema:datePublished": "2022-03-18",
        "schema:brand": "愛蔵版コミックス"}
SERIES = {"C900": {"schema:identifier": "C900", "schema:name": "雨夜の月",
                   "schema:creator": "くずしろ", "schema:publisher": "講談社",
                   "schema:brand": "ヤンマガKCスペシャル"},
          "C901": {"schema:identifier": "C901", "schema:name": "博イラスト集 明日ちゃんまでの足跡",
                   "schema:creator": "博", "schema:publisher": "集英社",
                   "schema:brand": "愛蔵版コミックス"}}

CAPTURE = """source: platform-retail-links
works:
  - platform_url: "https://comic-days.com/episode/12207421983645810020"
    id: "w00100"
    work: "雨夜の月"
    platform: "コミックDAYS"
    engine: "giga"
    volumes:
      - isbn: "9784065250891"
        via: "https://comic-days.com/episode/12207421983645810020"
  - platform_url: "https://tonarinoyj.jp/episode/1"
    id: "w00200"
    work: "明日ちゃんのセーラー服"
    platform: "となりのヤングジャンプ"
    engine: "giga"
    volumes:
      - isbn: "9784087927498"
  - platform_url: "https://kuragebunch.com/episode/2"
    work: "no volumes"
    volumes: []
"""


def main(s):
    with tempfile.TemporaryDirectory() as d:
        cap = pathlib.Path(d) / "platform-editions.yaml"
        cap.write_text(CAPTURE)

        by_url = bp.wanted_by_work([cap])
        s.eq(sorted(by_url), ["https://comic-days.com/episode/12207421983645810020",
                              "https://tonarinoyj.jp/episode/1"],
             "a work the platform stated no volume for contributes no row")
        s.eq(by_url["https://tonarinoyj.jp/episode/1"]["work"], "明日ちゃんのセーラー服",
             "and each row keeps the platform's own title, for the agreement check")

        # THE KEY IS THE ADDRESS. A title would not do: the same string names more than one work in
        # this corpus, and the whole point of the route is that the ISBN was found on this page.
        s.check(all(u.startswith("http") for u in by_url), "rows are keyed on the platform URL")

        books = [VOL1, VOL2, VOL3]
        isbns = {i for v in by_url.values() for i in v["isbns"]}
        import by_isbn                                                         # noqa: PLC0415
        got = by_isbn.select(books, isbns)
        s.eq(sorted(r["schema:identifier"] for r in got), ["M100", "M200"],
             "the volumes whose ISBN the platform stated")
        whole = by_isbn.expand(books, got, SERIES)
        s.eq(sorted(r["schema:identifier"] for r in whole), ["M100", "M101", "M200"],
             "and the rest of each work, which the platform's block did not list")

        # A LINK TO A SHOP IS NOT A LABEL. The platform is publisher-side and a コミックス block
        # applies no genre to anything, so this axis stays `none` (DEFINITIONS §4).
        s.eq(bp.LABEL_PLATFORM[0], "none", "a work reached this way carries no marketing label")
        s.eq(bp.label_for([VOL1, VOL2]), bp.LABEL_PLATFORM,
             "and the imprint on it is not one the publisher runs as a yuri line")
        yurihime = dict(VOL1, **{"schema:brand": "百合姫コミックス"})
        s.eq(bp.label_for([yurihime]), extract.LABEL_IMPRINT,
             "unless it is, in which case the publisher's own imprint carries the label")

        # THE FALLBACK IS THIS ROUTE'S OWN. Taking the sibling's wrote "admitted on a licensed
        # retailer's yuri shelf" onto records of works that were already held and had never been
        # near a shelf.
        s.check("shelf" not in bp.LABEL_PLATFORM[1],
                "a record written here does not claim a shelf admitted the work")
        s.check("platform page" in bp.LABEL_PLATFORM[1],
                "it says where the edition was identified instead")

        # THE AGREEMENT CHECK, WHICH REPORTS AND DOES NOT FILTER. となりのヤングジャンプ lists an
        # illustration book in the same block as the volume, so an ISBN off that page can reach a
        # record that is not the serialisation. It is counted rather than dropped, because a filter
        # that silently discards rows is unobservable when it stops working.
        s.eq(bp.agreement([VOL1], SERIES, "C900", "雨夜の月"), "agreed",
             "the bibliography's title and the platform's name the same work")
        s.eq(bp.agreement([VOL3], SERIES, "C901", "明日ちゃんのセーラー服"), "differs",
             "and the illustration book beside it is visible as a disagreement")
        s.eq(bp.agreement([VOL1], SERIES, "C900", "雨夜の月(1)"), "agreed",
             "a volume number on the platform's title does not make it a different work")
        s.eq(bp.agreement([VOL1], SERIES, "C900", ""), "unknown",
             "and nothing to compare is its own answer, not a pass")

        # MADB WRITES A TITLE IN ISBD NOTATION and a platform writes one of its parts, in either
        # order. Rejecting these would refuse correct records for a cataloguing convention.
        isbd = {"C1": {"schema:identifier": "C1", "schema:name": "白と黒 = Black & White"},
                "C2": {"schema:identifier": "C2",
                       "schema:name": "キグナスの乙女たち : 新・魔法科高校の劣等生"},
                "C3": {"schema:identifier": "C3", "schema:name": "異種族女子に○○する話"}}
        s.eq(bp.agreement([], isbd, "C1", "白と黒～Black & White～"), "agreed",
             "a parallel title after = is the same work")
        s.eq(bp.agreement([], isbd, "C2", "新・魔法科高校の劣等生 キグナスの乙女たち"), "agreed",
             "and a series statement after : written the other way round")
        s.eq(bp.agreement([], isbd, "C3", "異種族女子に〇〇する話"), "agreed",
             "and 〇 against ○ in a censored word, which is the same character to a reader")
        s.eq(bp.agreement([], isbd, "C1", "けがわとなかみ"), "differs",
             "while a genuinely different title still differs, which is what the guard is for")

        # THE CARRY-OVER RULE, ASKED ABOUT THIS ROUTE'S OWN NAME. Three passes write into
        # data/source/madb/ now, and a clear scoped to the wrong name deletes another one's work.
        out = pathlib.Path(d) / "src"
        out.mkdir()
        (out / "C901.yaml").write_text(f"route: {extract.ROUTE_IMPRINT}\nwork_id: C901\n")
        (out / "C900.yaml").write_text(f"route: {bp.ROUTE}\nwork_id: C900\n")
        s.eq(by_isbn.owned_elsewhere(out, bp.ROUTE), {"C901"},
             "a record another route wrote is held against this one")
        s.eq(by_isbn.owned_elsewhere(out, extract.ROUTE_IMPRINT), {"C900"},
             "and the question is answered per route rather than for one of them")

        # WHAT THE RECORD SAYS ABOUT WHERE IT CAME FROM. Not `admitted_by`: the work was already in
        # the database and nothing here admits it. What it carries is where the edition was found.
        lines = bp.identified_by({"platform": "コミックDAYS",
                                  "url": "https://comic-days.com/episode/1"}, "2026-08-07")
        s.check(any("コミックDAYS" in x for x in lines), "the record names the platform")
        s.check(any("comic-days.com" in x for x in lines), "and the page the ISBN was read off")
        s.check(not any("admitted_by" in x for x in lines),
                "and does not claim to have admitted a work that was already held")

        text = extract.render("C900", [VOL1, VOL2], SERIES, "series-link", "1.2.18", "2026-08-07",
                              bp.ROUTE, bp.LABEL_PLATFORM,
                              bp.identified_by({"platform": "コミックDAYS",
                                                "url": "https://comic-days.com/episode/1"},
                                               "2026-08-07"))
        s.check(f"route: {bp.ROUTE}" in text, "the record says which pass wrote it")
        s.check("volume_count: 2" in text, "and is as long as the bibliography says")
        s.check("first_published: 2021-08-06" in text, "with the bibliography's date")
        s.check("marketing_label: none" in text, "and the label it is entitled to")

        # THE CONTENT-FLAG REGISTER. Attaching a book run to a serialisation puts the publisher's
        # imprint on a work for the first time, and four of the 226 turned out to be on an adult
        # imprint. §14's policy does not withhold them, so the register records and REPORTS, and
        # the file has a consumer in the same commit: build.py reads it and check.py asserts that
        # the register and the published report agree.
        import yaml                                                            # noqa: PLC0415
        adult = {"C1": {"schema:identifier": "C1", "schema:name": "悪魔のモカちゃん",
                        "schema:brand": "ヤングアンリアルコミックス", "schema:publisher": "三和出版"},
                 "C2": {"schema:identifier": "C2", "schema:name": "雨夜の月",
                        "schema:brand": "ヤンマガKCスペシャル", "schema:publisher": "講談社"}}
        rows = bp.designations({"C1": [VOL1], "C2": [VOL1]}, adult,
                               {"C1": ["https://comic.pixiv.net/works/6807"]},
                               {"https://comic.pixiv.net/works/6807": {"work": "悪魔のモカちゃん"}})
        s.eq([r["work_id"] for r in rows], ["C1"],
             "only the record on a designated imprint is flagged")
        s.eq(rows[0]["work_title"], "悪魔のモカちゃん",
             "under the title the reader sees, which is the platform's")
        reg = yaml.safe_load(bp.render_register(rows, "2026-08-07"))
        s.eq(reg["flagged_total"], 1, "the register states its own count")
        s.eq(reg["works"][0]["withhold"], False,
             "and withholds nothing, because every platform here is a publisher's own web arm")

        # THE JOIN FILE, which is what makes the identity claim an identifier rather than a title.
        doc = yaml.safe_load(bp.render_joins(
            [{"platform_url": "https://comic-days.com/episode/1", "work": "雨夜の月",
              "madb_work_id": "C900", "agreement": "agreed"}], "2026-08-07"))
        s.eq(len(doc["joins"]), 1, "the join file parses back")
        s.eq(doc["joins"][0]["madb_work_id"], "C900", "naming the print record")
        s.eq(doc["joins"][0]["platform_url"], "https://comic-days.com/episode/1",
             "and the address of the serialisation it belongs to")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
