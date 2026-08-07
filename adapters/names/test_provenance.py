#!/usr/bin/env python3
"""provenance.py: what a reading must show before it may say a source stated it.

Every fixture here is a shape the pipeline really produced, which is the point of §14b. A check
proved against a shape somebody invented for the test is proved against nothing: the canary is
planted downstream of whatever filtered the data, so a check whose subject already removes every
failing case passes for the rest of its life. The three faults below were all live in
data/names when this was written, and each is named with the record it came from.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import provenance  # noqa: E402
from names.store import NameStore  # noqa: E402

COVERS = ["adapters/names/provenance.py"]

# openBD, which is the ordinary healthy case: the publisher's own collationkey, read off a URL
# built from the ISBN the corpus already held.
SOURCED = {"reading": "シノノメ ミズオ", "reading_basis": "stated", "reading_source": "openBD",
           "reading_source_kind": "publisher-jp",
           "reading_url": "https://api.openbd.jp/v1/get?isbn=9784758027335",
           "reading_reviewed": "2026-08-05"}

# あいかわももこ. Kana throughout, so the reading is the name and there is no page anywhere.
SURFACE = {"reading": "アイカワモモコ", "reading_basis": "surface", "reading_source": "surface"}

# 2C=がろあ, from pass 4. A morphological analyser is not a document and never gets an address.
ANALYSER = {"reading": "2 C =ガロ ア", "reading_basis": "analyser", "reading_source": "sudachi",
            "reading_source_kind": "analyser"}


def main(s):
    # ---- what a reader is offered -------------------------------------------------------------
    c = provenance.cite(SOURCED)
    s.eq(c["url"], "https://api.openbd.jp/v1/get?isbn=9784758027335",
         "a sourced reading shows the page it was read from")
    s.eq(c["reviewed"], "2026-08-05", "and the day a person last looked at it")
    s.eq(provenance.cite(SURFACE), None,
         "a kana name cites nothing: it is its own reading and no lookup happened")
    s.eq(provenance.cite(ANALYSER), None,
         "an analyser guess cites nothing; the unverified mark is what it has to say")

    # ---- the fault the module was written for -------------------------------------------------
    # 11 curated titles were in exactly this state. The entry's `source` described the TRANSLATION
    # and the reading was stamped with it, so a reading claiming a source named us and held no page.
    bw = {"reading": "フレナイ", "reading_basis": "stated", "reading_source": "yurarium",
          "reading_source_kind": "derived"}
    s.eq([f for _n, f, _d in provenance.faults({"#ふれない": bw})], ["cannot-show-its-source"],
         "a reading claiming a source with no address is a fault")
    s.eq(provenance.cite(bw), None, "and it is never rendered as a citation")
    s.eq(provenance.faults({"#ふれない": dict(bw, reading_source="BOOK☆WALKER",
                                            reading_url="https://bookwalker.jp/de89a94759/")}), [],
         "and it is clean once the page it names is recorded")

    # 古川楊也: refuted because the reading belonged to another person, and the record went on
    # citing the MangaUpdates page that said so. A citation for a claim that is not there.
    orphan = {"reading_source": "sudachi", "reading_at": "2026-08-06",
              "reading_url": "https://www.mangaupdates.com/author/0fnry5y/hoshino-katsura",
              "reading_refuted": "the reading of a different person's name"}
    s.eq([f for _n, f, _d in provenance.faults({"古川楊也": orphan})],
         ["citation-without-a-claim"], "a source left behind by a withdrawn reading is a fault")

    # ---- an address has to be one --------------------------------------------------------------
    # `the artist's own site` is a true statement about where a reading came from and is not a
    # place a reader can go, so a check counting non-empty fields would pass on it.
    s.check(provenance.faults({"x": dict(SOURCED, reading_url="the artist's own site")}),
            "a description of a source is not an address")
    s.check(not provenance.is_address("openBD"), "a source name is not an address")
    s.check(provenance.is_address("https://mediaarts-db.artmuseums.go.jp/id/C107809"),
            "a MADB record id resolves to a page")

    # ---- a route this project agreed not to take ------------------------------------------------
    # 35 author readings hold the creator search the pass ran against NDL's OpenSearch. Its
    # robots.txt disallows /api, so linking it would advertise a route we do not take, and a search
    # is not the record that states the reading either.
    ndl_api = dict(SOURCED, reading_source="national-library",
                   reading_url="https://ndlsearch.ndl.go.jp/api/opensearch?creator=%E5%AE%AE")
    s.check(provenance.is_address(ndl_api["reading_url"]), "it is a well-formed address")
    s.check(not provenance.citable(ndl_api["reading_url"]), "and it is not one to show a reader")
    s.eq(provenance.cite(ndl_api), None, "so no citation is rendered for it")
    s.eq(provenance.faults({"宮原都": ndl_api}), [],
         "and the invariant does not fire: an address WAS recorded, which is what it asks")
    s.eq(len(provenance.uncitable({"宮原都": ndl_api})), 1, "the withheld citation is counted")
    # The record page on the same host is open and is the shape a citation should have.
    s.check(provenance.citable("https://ndlsearch.ndl.go.jp/books/R100000137-I04000000A21870300000"),
            "the /books record page is not on the closed route")
    s.eq(provenance.uncitable({"x": SOURCED}), [], "an ordinary citation is not withheld")

    # ---- a page that belongs to the other claim -------------------------------------------------
    # 100日後に咲く百合 as the store held it: Yen Press publishes the English title and states no
    # Japanese reading anywhere, and the reading was stamped with its page because the entry
    # carried one page for both claims. `faults` is satisfied, since an address IS held.
    yen = {"reading": "ヒャクニチゴニサクユリ", "reading_basis": "stated",
           "reading_source_kind": "platform", "en": "Lilies Blooming in 100 Days",
           "en_source_kind": "licensor",
           "reading_url": "https://yenpress.com/series/lilies-blooming-in-100-days-manga",
           "en_url": "https://yenpress.com/series/lilies-blooming-in-100-days-manga"}
    s.eq(provenance.faults({"100日後に咲く百合": yen}), [],
         "an address is held, so the invariant has nothing to say")
    s.eq(len(provenance.borrowed({"100日後に咲く百合": yen})), 1,
         "and the count catches that it is the other claim's address")
    s.eq(provenance.borrowed({"x": dict(yen, reading_url="https://bookwalker.jp/de5f304615/")}), [],
         "clean once the reading names the page that states it")
    # Two claims read off the SAME page is ordinary and is not this fault.
    s.eq(provenance.borrowed({"x": dict(yen, en_source_kind="platform")}), [],
         "one page can state both where both came from the same kind of source")

    # ---- the store keeps the two claims apart --------------------------------------------------
    # The §3 half. One entry, two claims, and until now one citation between them.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        st = NameStore(d)
        st.record("titles", "#ふれない", en="#Not Touching", basis="translated",
                  source="yurarium", source_kind="derived",
                  reading="フレナイ", reading_basis="stated", reading_source="BOOK☆WALKER",
                  reading_source_kind="platform",
                  reading_url="https://bookwalker.jp/de89a94759/", reviewed="2026-08-06")
        rec = st.records["titles"]["#ふれない"]
        s.eq(rec["reading_source"], "BOOK☆WALKER",
             "the reading keeps its own source when the entry names another")
        s.eq(rec["en_source"], "yurarium", "and the translation keeps the entry's")
        s.eq(rec["reading_reviewed"], "2026-08-06", "the review date reaches the claim")
        s.eq(provenance.faults(st.records["titles"]), [], "so the record can show its source")

        # A refutation must take the citation with it, which is what left two records pointing at
        # the wrong person's page.
        dropped = st.clear_claim("titles", "#ふれない", "reading")
        s.check("reading_url" in dropped and "reading_source" in dropped,
                "clearing a reading drops the address and the source it was stamped with")
        s.eq(provenance.faults(st.records["titles"]), [],
             "and leaves no citation behind for a reading that is gone")
        s.eq(st.records["titles"]["#ふれない"]["en"], "#Not Touching",
             "while the other claim in the same record is untouched")
        st.close()


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
