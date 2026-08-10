#!/usr/bin/env python3
"""by_isbn.py: a shop says which ISBN to ask about, and the bibliography answers."""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from madb import by_isbn, extract  # noqa: E402

COVERS = ["adapters/madb/by_isbn.py"]

# MADB volume records cut to the fields these passes read. The first two are one series; the third
# is on the 百合姫 imprint, which is the case where the publisher's own label reaches us.
VOL1 = {"schema:identifier": "M100", "schema:isbn": "9784063807028",
        "schema:name": "ひなちゃんが生きてるなら 1", "schema:isPartOf": ".../C900",
        "schema:volumeNumber": "1", "schema:datePublished": "2024-03-08",
        "schema:brand": "アフタヌーンKC"}
VOL2 = {"schema:identifier": "M101", "schema:isbn": "978-4-06-380703-5",
        "schema:name": "ひなちゃんが生きてるなら 2", "schema:isPartOf": ".../C900",
        "schema:volumeNumber": "2", "schema:datePublished": "2024-09-06",
        "schema:brand": "アフタヌーンKC"}
VOL3 = {"schema:identifier": "M200", "schema:isbn": "9784758070027",
        "schema:name": "初恋姉妹 1", "schema:isPartOf": ".../C901",
        "schema:volumeNumber": "1", "schema:datePublished": "2014-02-14",
        "schema:brand": "百合姫コミックス"}
SERIES = {"C900": {"schema:identifier": "C900", "schema:name": "ひなちゃんが生きてるなら",
                   "schema:creator": "松崎夏未", "schema:publisher": "講談社　∥　コウダンシャ",
                   "schema:brand": "アフタヌーンKC"},
          "C901": {"schema:identifier": "C901", "schema:name": "初恋姉妹",
                   "schema:creator": "袴田めら", "schema:publisher": "一迅社",
                   "schema:brand": "百合姫コミックス"}}

CAPTURE = """source: cmoa.jp
works:
  - shop_id: "1"
    url: "https://www.cmoa.jp/title/1/"
    volumes:
      - volume: 1
        isbn: "978-4-06-380702-8"
      - volume: 2
        delivered: "2024-09-10"
  - shop_id: "2"
    url: "https://www.cmoa.jp/title/2/"
    volumes:
      - volume: 1
        isbn: "9784758070027"
"""

# THE SAME SHELF LISTING ONE WORK UNDER TWO TITLES, which is the case `address_of` refuses. Five of
# コミックシーモア's works answer this way: the shop splits a series the bibliography holds whole,
# so each of its pages is right about part of the work and wrong about the rest.
SPLIT = """source: cmoa.jp
works:
  - shop_id: "3"
    url: "https://www.cmoa.jp/title/3/"
    volumes:
      - volume: 1
        isbn: "9784063807028"
  - shop_id: "4"
    url: "https://www.cmoa.jp/title/4/"
    volumes:
      - volume: 1
        isbn: "978-4-06-380703-5"
"""


def main(s):
    with tempfile.TemporaryDirectory() as d:
        cap = pathlib.Path(d) / "cmoa-volumes.yaml"
        cap.write_text(CAPTURE)

        # AN ISBN IS DIGITS. The shop writes it hyphenated and MADB writes it both ways; a run that
        # compared the two as typed would ask about a number nobody holds.
        want = by_isbn.wanted([cap])
        s.eq(want, {"9784063807028", "9784758070027"}, "hyphens are not part of an ISBN")
        s.check("" not in want, "and a volume stating no ISBN contributes nothing")

        books = [VOL1, VOL2, VOL3]
        got = by_isbn.select(books, want)
        s.eq([r["schema:identifier"] for r in got], ["M100", "M200"],
             "a volume is selected when the ISBN was asked for, however either side spells it")
        s.eq(by_isbn.select([VOL1], {"9780000000000"}), [],
             "and an ISBN nobody asked about is not selected")

        # THE SHOP IDENTIFIES THE WORK; THE BIBLIOGRAPHY SAYS HOW LONG IT IS. The capture states an
        # ISBN for volume 1 and none for volume 2, and a record built from the seeds alone would
        # say the work is one volume long and had its last volume in March.
        whole = by_isbn.expand(books, got, SERIES)
        s.eq(sorted(r["schema:identifier"] for r in whole), ["M100", "M101", "M200"],
             "the volumes nobody stated an ISBN for come back with the work")

        # THE SHELF IS WHY WE LOOKED AND IS NEVER THE LABEL (DEFINITIONS §4). A retailer's genre
        # shelf is its own decision; the imprint on the record is the publisher's.
        s.eq(by_isbn.label_for([VOL1, VOL2])[0], "none",
             "a work reached off a shop's shelf carries no marketing label")
        s.eq(by_isbn.label_for([VOL3]), extract.LABEL_IMPRINT,
             "unless the record's own imprint is one the publisher runs as a yuri line")

        by_series, grouping = extract.group([VOL1, VOL2, VOL3], SERIES)
        s.eq(len(by_series), 2, "volumes gather into works by their series link")

        out = pathlib.Path(d) / "src"
        out.mkdir()
        # A RECORD ANOTHER ROUTE OWNS IS LEFT ALONE. Both passes write here, and the imprint route
        # reached its works with the publisher's own evidence.
        (out / "C901.yaml").write_text(f"route: {extract.ROUTE_IMPRINT}\nwork_id: C901\n")
        s.eq(by_isbn.owned_elsewhere(out), {"C901"}, "a record without this route's marker is held")
        (out / "C900.yaml").write_text(f"route: {by_isbn.ROUTE}\nwork_id: C900\n")
        s.eq(by_isbn.owned_elsewhere(out), {"C901"}, "and this route's own records are not")

        # THE CARRY-OVER RULE. Each pass clears only what it wrote. A blanket wipe here deleted
        # every record the other route had just produced.
        extract.write(out, {"C900": [VOL1, VOL2]}, {"C900": "series-link"}, SERIES,
                      "1.2.18", "2026-08-05", by_isbn.ROUTE, by_isbn.LABEL_SHELF)
        s.check((out / "C901.yaml").exists(), "a pass does not delete what it is not looking at")

        # §2 ADMITS THE WORK AND WANTS TO KNOW WHICH COMPARATOR DID IT. Neither axis can carry
        # this: a shop's shelf is not publisher-side, so the label stays `none` and the admission
        # has to be recorded somewhere a reader can see it.
        shops, pages = by_isbn.read_captures([cap])
        adm = by_isbn.admitted_by(shops, "2026-08-05")
        s.check(any("cmoa.jp" in x for x in adm), "the record names the shop that admitted the work")
        s.check(any("37" in x for x in adm), "and the shelf it was standing on")

        # AND WHERE TO GO AND LOOK. The block used to be computed once for a whole pass, so it could
        # name the shop and never the title, and 230 shipped rows named コミックシーモア with no
        # way to reach it. The join is the ISBN, which is the number that selected the record.
        s.eq(by_isbn.address_of([VOL1, VOL2], pages), {"cmoa.jp": "https://www.cmoa.jp/title/1/"},
             "the work's own volumes say which of the shop's pages admitted it")
        s.eq(by_isbn.address_of([VOL3], pages), {"cmoa.jp": "https://www.cmoa.jp/title/2/"},
             "and a second work resolves to its own page and not to the first one's")
        s.eq(by_isbn.address_of([{"schema:isbn": "9780000000000"}], pages), {},
             "a volume the capture states no ISBN for reaches no page, and none is invented")
        s.check('shop_url: "https://www.cmoa.jp/title/1/"' in "\n".join(
            by_isbn.admitted_by(shops, "2026-08-05", by_isbn.address_of([VOL1, VOL2], pages))),
            "and the address reaches the record's own admitted_by entry")

        # ONE PAGE OR NONE. Two of the shop's titles carrying one work's volumes name no single
        # page for it, and picking either would send a reader to a title whose volumes are not the
        # ones listed beside the link. §5: the absence is the answer.
        split = pathlib.Path(d) / "split.yaml"
        split.write_text(SPLIT)
        _, two = by_isbn.read_captures([split])
        s.eq(by_isbn.address_of([VOL1, VOL2], two), {},
             "a shop listing one work under two titles states no address for it")
        s.eq(by_isbn.address_of([VOL1], two), {"cmoa.jp": "https://www.cmoa.jp/title/3/"},
             "though each of those titles is still an answer about the volume it states")

        # THE SHOPS COME FROM THE CAPTURE'S OWN `source`, so the record names the shop the ISBNs
        # came from rather than whichever one a caller passed.
        s.eq(shops, ["cmoa.jp"], "the capture says which shop it is")

        extract.write(out, {"C900": [VOL1, VOL2]}, {"C900": "series-link"}, SERIES,
                      "1.2.18", "2026-08-05", by_isbn.ROUTE, by_isbn.LABEL_SHELF)
        text = (out / "C900.yaml").read_text()
        s.check("marketing_label: none" in text, "the record states the label it is entitled to")
        s.check(f"route: {by_isbn.ROUTE}" in text, "and which pass wrote it")
        s.check("first_published: 2024-03-08" in text, "with the bibliography's date, not the shop's")
        s.check("1132" not in text and "cmoa.jp/title" not in text,
                "the shop's own listing is not copied into the record its ISBN led to")
        s.check("volume_count: 2" in text, "and the work is as long as the bibliography says")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
