#!/usr/bin/env python3
"""by_publisher_text.py: a label the publisher's own text applies, on a record the bibliography gives."""
import pathlib
import sys
import tempfile

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from madb import by_publisher_text as bpt, extract  # noqa: E402
from classify import credence  # noqa: E402

COVERS = ["adapters/madb/by_publisher_text.py"]

VOL1 = {"schema:identifier": "M811779", "schema:isbn": "9784592711568",
        "schema:name": "メジロバナの咲く 1", "schema:isPartOf": ".../C434017",
        "schema:volumeNumber": "1", "schema:datePublished": "2019-10"}
VOL2 = {"schema:identifier": "M847311", "schema:isbn": "9784592711841",
        "schema:name": "メジロバナの咲く 2", "schema:isPartOf": ".../C434017",
        "schema:volumeNumber": "2", "schema:datePublished": "2021-05"}
SERIES = {"C434017": {"schema:identifier": "C434017", "schema:name": "メジロバナの咲く",
                      "schema:creator": "[著]中村明日美子", "schema:publisher": "白泉社　∥　ハクセンシャ"}}

TEXTS = """works:
  - isbn: "978-4-592-71184-1"
    title: "メジロバナの咲く"
    label: gl
    term: "ガールズラブ"
    quote: "著者初の長編ガールズラブ、待望の第2巻。"
    url: "https://example.org/9784592711841"
    retrieved: 2026-11-01
  - isbn: "9784000000000"
    title: "no label"
    label: none
    term: ""
    quote: ""
    url: "https://example.org/x"
    retrieved: 2026-11-01
"""


def main(s):
    with tempfile.TemporaryDirectory() as d:
        src = pathlib.Path(d) / "publisher-text.yaml"
        src.write_text(TEXTS)
        wanted = bpt.entries(src)
        s.eq(list(wanted), ["9784592711841"],
             "an entry is keyed on its ISBN in thirteen digits, and one stating no label is not read")

        # THE TEXT NAMES ONE VOLUME; THE BIBLIOGRAPHY SAYS HOW LONG THE WORK IS.
        whole = bpt.by_isbn.expand([VOL1, VOL2], bpt.by_isbn.select([VOL1, VOL2], set(wanted)),
                                   SERIES)
        s.eq(sorted(r["schema:identifier"] for r in whole), ["M811779", "M847311"],
             "volume 1 comes back with the work although the publisher's text was for volume 2")
        s.eq(bpt.which(whole, wanted)["title"], "メジロバナの咲く",
             "and the work knows which entry selected it")

        e = wanted["9784592711841"]
        text = extract.render("C434017", whole, SERIES, "series-link", "1.2.21", "2026-11-01",
                              bpt.ROUTE, (e["label"], bpt.NOTE), basis=bpt.basis(e))
        rec = yaml.safe_load(text)
        s.eq((rec["marketing_label"], rec["marketing_label_basis"]["source"],
              rec["marketing_label_basis"]["url"]),
             ("gl", "publisher", "https://example.org/9784592711841"),
             "the label cites the page the publisher's text was read on, not MADB")
        s.eq(rec["volume_count"], 2, "while the volumes are MADB's")

        # THE EVIDENCE ROW QUOTES THE PUBLISHER'S WORD AND NAMES THE PUBLISHER.
        row = credence.label_row(rec)
        s.eq((row["kind"], row["type"], row["source"], row["term"]),
             ("description", "publisher", "白泉社", "ガールズラブ"),
             "a reader is shown the publisher's own word, attributed to the publisher")
        rec["marketing_label_basis"]["term"] = "学園"
        s.eq(credence.label_row(rec), None, "and a term that makes no yuri claim is not shown")

        out = pathlib.Path(d) / "madb"
        out.mkdir()
        (out / "C434017.yaml").write_text(f"route: {extract.ROUTE_IMPRINT}\n")
        s.eq(bpt.by_isbn.owned_elsewhere(out, bpt.ROUTE), {"C434017"},
             "a work another route holds is that route's, and this one leaves it")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "madb.by_publisher_text"))
