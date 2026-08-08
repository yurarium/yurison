#!/usr/bin/env python3
"""cmoa_volumes.py: resuming a capture, and refusing to file a shop's silence as a date."""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cmoa_volumes as cv  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/cmoa_volumes.py"]

# A parsed work page as cmoa.work() returns one. The fields are those of
# https://www.cmoa.jp/title/167439/ as served on 2026-08-05; test_cmoa.py pins the parse itself,
# so what is exercised here is what happens to the parse afterwards.
PARSED = {
    "cmoa_title_id": "167439", "publisher": "小学館", "imprint": "裏サンデー女子部",
    "genres": ["少女マンガ", "恋愛", "百合・GL"], "completed": True, "volumes_stated": 14,
    "detail_volume": 1, "isbn": "9784091287557", "published": "2019-01",
    "distribution_started": "2019-01-11",
    "volumes": [{"volume": 1, "name": "付き合ってあげてもいいかな 1",
                 "url": "https://www.cmoa.jp/title/167439/"},
                {"volume": 2, "name": "付き合ってあげてもいいかな 2",
                 "url": "https://www.cmoa.jp/title/167439/vol/2/"}],
}

# The same page for a work the shop files under its adult genre. Nothing on the shelf row said so,
# which is the whole reason the designation test runs a second time here.
DESIGNATED = dict(PARSED, cmoa_title_id="9", genres=["アダルトマンガ", "百合・GL"])


def parsed(**over):
    d = dict(PARSED)
    d["volumes"] = [dict(v) for v in PARSED["volumes"]]
    d.update(over)
    return d


def main(s):
    # ── A DATE IS A DATE, AND 配信開始日 IS NOT ONE ───────────────────────────────────────────
    # This is the check the whole capture exists to get right. 双葉社 states 2007年12月 for a file
    # cmoa began selling on 2012-10-05, so a rule that fell back on the distribution date would put
    # five wrong years into the field that decides whether a work is in scope, on a row that would
    # then look answered.
    rec, why = cv.record(parsed(), {"title": "付き合ってあげてもいいかな"})
    s.eq(why, None, "an undesignated work is kept")
    s.eq(rec["shop_id"], "167439", "keyed by the id admitted.yaml already carries")
    s.eq(rec["first_publication_date"], "2019-01", "出版年月 settles the first volume")
    s.eq(rec["first_publication_basis"], "shop-publication-month",
         "and the basis says which route said so")
    s.eq(rec["first_publication_country"], "JP", "a print edition from a Japanese publisher")
    s.eq(rec["volumes"][0]["delivered"], "2019-01-11",
         "the distribution date is kept, under a name nothing can mistake for publication")
    s.eq(rec["volumes_found"], 2, "the volumes this page listed")
    s.eq(rec["volumes_stated"], 14, "against the fourteen the shop says exist")

    # THE WORST REAL CASE, quoted rather than invented: 一迅社 title 153015 is printed 2007-11-01
    # and delivered 2018-07-18, a hundred and twenty-eight months apart. Across the 353 volumes
    # stating both, 154 are delivered BEFORE the print date and 45 more than three years after, so
    # the delivery date is not a bound in either direction and cannot stand in for one.
    far = cv.record(parsed(published="2007-11", distribution_started="2018-07-18"), None)[0]
    s.eq(far["first_publication_date"], "2007-11",
         "the print date stands however long after it the shop began selling the file")
    s.eq(far["volumes"][0]["delivered"], "2018-07-18", "and the delivery date is kept beside it")

    # ── THE DIGITAL-ONLY ROW, WHOSE ANSWER THE OWNER REVERSED ON 2026-08-08 ───────────────────
    # This block asserted the opposite until that ruling: no date, and a basis saying so. What has
    # not changed is everything above, which is about a volume stating both dates.
    bare = cv.record(parsed(published=None, isbn=None), None)[0]
    s.eq(bare["first_publication_date"], "2019-01-11",
         "a page stating only 配信開始日 is dated by the day the shop began delivering the file")
    s.eq(bare["first_publication_basis"], "shop-delivery-date",
         "and the basis names the delivery, which is exactly what the date is true of")
    s.eq(bare["first_publication_event"], "shop-delivery",
         "the event travels with it, so nothing downstream reads it as a printing")
    s.eq(bare["first_publication_followup"], "unclassified",
         "and a row whose page has not been read for its edition sorts to neither pile")
    s.eq(bare["first_publication_country"], "JP", "a dated row answers where, which §6 asks")
    s.eq(bare["first_publication_source"], bare["volumes"][0]["url"],
         "cited to the volume page stating the date, which a catalogue route has none of")
    s.eq(bare["volumes"][0]["delivered"], "2019-01-11",
         "and the volume keeps the shop's own field under the shop's own name")

    # ONE PRINTED VOLUME ANSWERS FOR THE WORK, and volume 1 is not where this is decided. The
    # branch above reads volume 1 and `delivery.promote` reads all of them, so a work whose second
    # volume states a printing is refused rather than dated from its file.
    mixed = {"volumes": [{"volume": 1, "delivered": "2019-01-11"},
                         {"volume": 2, "printed": "2007-11"}]}
    s.eq(cv.first_publication(mixed), (None, "shop-delivery-date-refused"),
         "a printing anywhere on the work refuses the delivery date and says it did")

    # THE SILENCE THAT ANOTHER CATALOGUE COULD STILL ANSWER, kept apart from the one that nothing
    # can: an ISBN exists and openBD has no record of it, which is 13 of the 23 ISBNs sampled.
    unreg = cv.record(parsed(published=None), None)[0]
    s.eq(unreg["first_publication_basis"], "isbn-stated-not-catalogued",
         "an ISBN no catalogue holds is a different silence from having no ISBN")

    s.eq(cv.first_publication({"volumes": []}), (None, "no-volumes-found"),
         "a work with no volumes settles nothing, and says so")

    # A LATER VOLUME'S DATE IS NOT THE WORK'S FIRST. The detail block describes one volume, and
    # attaching volume 7's ISBN to a work's first publication would be silent and wrong.
    late = {"volumes": [{"volume": 7, "printed": "2024-01"}]}
    s.eq(cv.first_publication(late), (None, "no-first-volume-listed"),
         "volume 7's date answers nothing about volume 1")

    # ── THE DESIGNATION TEST RUNS AGAIN, BECAUSE THE PAGE SAYS MORE THAN THE ROW ──────────────
    out, why = cv.record(DESIGNATED, {"title": "something"})
    s.eq(out, None, "a work the page files under the adult genre does not enter the file")
    s.check(why and "アダルト" in why, f"and the reason names the designation: {why!r}")
    s.check(why and "something" not in why,
            "the reason is a reason and never the title (DEFINITIONS §7)")

    cut, why = cv.record(parsed(volumes=[{"volume": 1, "name": "ある百合の話【棒消し修正版】",
                                          "url": "u"}]), None)
    s.eq(cut, None, "nor does a volume titled as a censored edition of an adult work")
    s.check(why and "棒消し" in why, "counted under the marker that identified it")

    # The counter-case, so the rule is not a substring search for 修正版: an authorial revision.
    ok, why = cv.record(parsed(volumes=[{"volume": 1, "name": "ある百合の話【加筆修正版】",
                                         "url": "u"}]), None)
    s.eq(why, None, "a revised-and-expanded reissue is an ordinary commercial edition")
    s.check(ok is not None, "so it is captured")

    # ── THE FLOOR ────────────────────────────────────────────────────────────────────────────
    # A page that lists no volume is not a thin answer, it is a page that did not parse: cmoa lists
    # at least the volume it is showing. A moved selector returns 200, a body, and rows like this.
    s.eq(cv.usable(parsed()), True, "a page with a volume list is usable")
    s.eq(cv.usable(parsed(volumes=[])), False, "a page with none is a parse that failed")
    s.eq(cv.usable(None), False, "and no page at all is not a quiet day")

    s.eq(cv.healthy(40, 40)[0], True, "a run that answered everything passes")
    s.eq(cv.healthy(20, 40)[0], True, "and half is the floor itself, which clears")
    s.eq(cv.healthy(19, 40)[0], False, "a share below the floor refuses")
    # THE SHAPE THE FLOOR EXISTS FOR: a loop that died after a handful. "Did we get anything" says
    # yes here, which is why the measure is a share of what was asked.
    s.eq(cv.healthy(3, 40)[0], False, "three rows out of forty asked is a stopped fetch")
    s.eq(cv.healthy(0, 0)[0], True, "and asking nothing is not a failure")

    # ── RESUMING, WHICH IS THE HALF THAT ONLY RUNS ON THE SECOND DAY ──────────────────────────
    doc = {"works": {}, "retrieved": "2026-08-05", "asked": 2}
    doc, added = cv.fold(doc, [cv.record(parsed(), None)[0]])
    s.eq(added, 1, "the first work is added")
    doc, added = cv.fold(doc, [cv.record(parsed(cmoa_title_id="103366"), None)[0]])
    s.eq(sorted(doc["works"]), ["103366", "167439"], "and the second joins it")

    # A SECOND RUN MUST NOT REBUILD THE FILE FROM WHAT IT ALONE FETCHED. This is the failure that
    # has bitten this project three times and it is silent: well-formed, smaller, saying nothing.
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "out.yaml"
        p.write_text(cv.yaml_document(doc))
        back = cv.load(p)
        s.eq(sorted(back["works"]), ["103366", "167439"], "both survive a write and a read")
        s.eq(back["works"]["167439"]["shop_id"], "167439",
             "and each row still carries the id it is filed under")
        s.eq(back["works"]["167439"]["first_publication_date"], "2019-01",
             "with the date it was captured with")
        s.eq(len(back["works"]["167439"]["volumes"]), 2, "and its volumes")
        s.eq(back["works"]["167439"]["volumes"][0]["delivered"], "2019-01-11",
             "and each volume's fields, which is what a thinned file would have lost")

        # THE SHELF SIZE SURVIVES THE ROUND TRIP, AND FOR ONE RUN IT DID NOT. `asked` is written
        # out as `admitted_rows` and was never read back, so the first pass that loaded the file
        # and rewrote it reset 1,844 to 0 and the queue reported itself empty. One fact under two
        # names, which is this project's most repeated bug (STANDING-INSTRUCTIONS §3).
        s.eq(back["asked"], 2, "the number of rows the shelf asked about comes back")

        after, _ = cv.fold(back, [cv.record(parsed(cmoa_title_id="1132"), None)[0]])
        s.eq(sorted(after["works"]), ["103366", "1132", "167439"],
             "a third run adds one work and carries the two it never touched")

        s.eq(cv.outstanding(["103366", "1132", "167439", "999"], after), ["999"],
             "so only the work nobody has fetched is still outstanding")
        s.eq(cv.outstanding(["9", "8"], {"works": {}, "excluded_ids": ["9"]}), ["8"],
             "and a work excluded on a designation is answered, not retried every run")

    s.eq(cv.load(pathlib.Path(tempfile.gettempdir()) / "no-such-cmoa-file.yaml")["works"], {},
         "a first run reads an empty document rather than failing")

    # ── THE CATALOGUE JOINS ──────────────────────────────────────────────────────────────────
    s.eq(cv.openbd_dates({"9784091287557": {"summary": {"pubdate": "201901"}}}),
         {"9784091287557": "2019-01"}, "openBD's YYYYMM reads as a month")
    s.eq(cv.openbd_dates({"9784091287557": None}), {"9784091287557": ""},
         "and an ISBN it does not hold reads as nothing")

    doc, filled, dis = cv.apply_dates(doc, {"9784091287557": "2019-01"}, "openbd-registration")
    s.eq(filled, 2, "the ISBN is held by both works in this document, so both volumes are filled")
    s.eq(dis, 0, "and it agrees with the month the shop stated")
    s.eq(doc["works"]["167439"]["first_publication_basis"], "openbd-registration",
         "the work's basis is recomputed to say the registration answered it")

    doc, filled, _ = cv.apply_dates(doc, {"9784091287557": None}, "openbd-registration")
    s.eq(filled, 0, "an ISBN a catalogue does not hold fills nothing")
    s.eq(doc["works"]["167439"]["volumes"][0]["printed"], "2019-01",
         "and erases nothing it filled before, because a null is not a correction")

    # A BETTER SOURCE REPLACES A WORSE ONE AND NEVER THE OTHER WAY. Both catalogue passes may run
    # in either order, so the weaker one running second must not undo the stronger.
    doc, filled, dis = cv.apply_dates(doc, {"9784091287557": "2019-01-11"}, "madb-tankobon")
    s.eq(doc["works"]["167439"]["volumes"][0]["printed"], "2019-01-11",
         "the national bibliography's answer replaces the registration's")
    s.eq(dis, 2, "and the two dates differing is counted rather than quietly resolved")
    doc, filled, _ = cv.apply_dates(doc, {"9784091287557": "2019-01"}, "openbd-registration")
    s.eq(filled, 0, "a later run of the weaker source overwrites nothing")
    s.eq(doc["works"]["167439"]["volumes"][0]["printed"], "2019-01-11",
         "so the better answer survives whichever order the passes ran in")
    s.eq(doc["works"]["167439"]["first_publication_basis"], "madb-tankobon",
         "and the basis says which catalogue is in the field")

    # ── THE DESCRIPTION IS READ FROM ONE BOX, WHICH IS THE WHOLE OF THE RULE ─────────────────
    # A doujin word appears somewhere on 321 of the 1,971 cached pages and inside the description
    # box on 285. The other 36 are in reader reviews and in the covers of other people's books in
    # the sidebar, so a count over the whole page would have read as the shop stating something
    # about 36 works it says nothing about. This literal states that one rule and holds no あらすじ,
    # which REQUIREMENTS §2 forbids storing.
    page = ('<div class="title_intro_box"><p>※本作は個人誌作品の電子書籍版となります。</p>'
            '<div id="comic_description_hide"></div>'
            '<div class="review_txt">同人誌の再録だそうです</div>')
    s.eq(cv.description(page), "※本作は個人誌作品の電子書籍版となります。",
         "the shop's own box, with its markup stripped and the review outside it left alone")
    s.eq(cv.description('<div class="review_txt">同人誌の再録です</div>'), "",
         "a page with no description box yields nothing, and not the nearest other text")
    s.eq(cv.description(None), "", "and no page at all yields nothing rather than raising")
    # A TEMPLATE THAT MOVED ITS OWN MARKER IS READ IMPERFECTLY AND NOT REPORTED AS SILENT. The box
    # opens, so the shop did say something, and returning "" here would file the row `unclassified`
    # on the strength of one renamed element.
    s.check("個人誌" in cv.description(
        '<div class="title_intro_box"><p>※本作は個人誌作品の電子書籍版となります。</p></div>'),
        "an unterminated box still yields the text it opened on")

    # ── THE SYNOPSIS IS A NARROWER SPAN, AND THE DATE RULE READS THAT ONE ────────────────────
    # The box holds the shop's own metadata under the blurb and one of its lines is 配信開始日. A
    # date rule reading the box would find that line on all 1,971 cached pages and hand the
    # delivery date back as a printing, which is the answer this whole round exists to avoid.
    boxed = ('<div class="title_intro_box"><div id="comic_description"><p>2016年発行の同人誌です</p>'
             '<div class="related_box"><div>配信開始日 ： 2015年8月18日</div></div>'
             '<div id="comic_description_hide"></div>')
    s.eq(cv.synopsis(boxed), "2016年発行の同人誌です",
         "the shop's blurb without the table of its own metadata under it")
    s.check("配信開始日" in cv.description(boxed),
         "which the wider span does carry, and is why the two spans are not one function")
    s.eq(cv.synopsis('<div class="title_intro_box"><p>本作は同人誌です</p>'
                     '<div id="comic_description_hide"></div>'), "本作は同人誌です",
         "a page whose table element is absent is read imperfectly and not reported as silent")
    s.eq(cv.synopsis(None), "", "and no page at all yields nothing rather than raising")

    # ── A PRINTING THE SHOP STATED IN WORDS OUTRANKS THE DAY IT BEGAN DELIVERING ─────────────
    # 33 rows in the capture are in this state. `edition_date` is what `read_editions` puts on the
    # row from the description; everything below it follows from that one field.
    said = cv.settle({"url": "https://www.cmoa.jp/title/246840/", "edition_date": "2022-05",
                      "edition_date_event": "issue", "publisher": "ナンバーナイン",
                      "volumes": [{"volume": 1, "url": "https://www.cmoa.jp/title/246840/",
                                   "delivered": "2022-06-24"}]})
    s.eq(said["first_publication_date"], "2022-05", "the printing answers and the delivery does not")
    s.eq(said["first_publication_basis"], "shop-blurb-print-date", "and the basis says which it is")
    s.eq(said["first_publication_event"], "issue",
         "発行 and 初出 are two claims, so the row says which one the shop made")
    s.eq(said["first_publication_source"], "https://www.cmoa.jp/title/246840/",
         "citing the work page, which is where the sentence a reader would check is")
    s.check("first_publication_followup" not in said,
            "and the row leaves the delivery population instead of being a settled member of it")
    # A CATALOGUE STILL OUTRANKS A SENTENCE. The branch order is the whole of this rule.
    both = cv.settle({"url": "https://www.cmoa.jp/title/1/", "edition_date": "2016",
                      "edition_date_event": "issue",
                      "volumes": [{"volume": 1, "url": "https://www.cmoa.jp/title/1/",
                                   "printed": "2018-03", "printed_basis": "madb-tankobon"}]})
    s.eq(both["first_publication_basis"], "madb-tankobon",
         "a bibliography holds a record and a blurb holds a sentence, so the record answers")

    # ── A PER-BOOK ROUTE CITES THE PAGE, AND THE CITATION IS WRITTEN OUT ─────────────────────
    # `adapters/publisher_dates.py` reads one page per book, so unlike a bulk catalogue it has a
    # URL to name. `check.py`'s `per-book dates cite their page` is the consumer, and it can only
    # see a citation that survives being written to the file.
    cited = {"works": {"167439": cv.record(parsed(published=None), None)[0]}}
    s.eq(cited["works"]["167439"]["first_publication_basis"], "isbn-stated-not-catalogued",
         "a row no catalogue holds the ISBN of is what the publisher route is for")
    cited, filled, _ = cv.apply_dates(cited, {"9784091287557": "2019-01-16"},
                                      "publisher-own-page",
                                      {"9784091287557": "https://example.invalid/detail/1"})
    s.eq(filled, 1, "the publisher's own page answers where neither catalogue did")
    s.eq(cited["works"]["167439"]["volumes"][0]["printed_source"],
         "https://example.invalid/detail/1", "the page the date came off is stored on the volume")
    s.eq(cited["works"]["167439"]["first_publication_source"],
         "https://example.invalid/detail/1", "and volume 1's citation is the work's")
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "cited.yaml"
        p.write_text(cv.yaml_document(cited))
        v = cv.load(p)["works"]["167439"]["volumes"][0]
        s.eq(v["printed_source"], "https://example.invalid/detail/1",
             "and it is written out, because a citation the file drops cannot be checked")
        bare = cv.yaml_document({"works": {
            "1": {"shop_id": "1", "first_publication_date": None, "volumes": []}}})
        s.check(not any(ln.strip().startswith("first_publication_source:")
                        for ln in bare.splitlines()),
                "a row with no per-book page carries no empty citation field")

    # A bulk catalogue passes no URL, and it outranks the publisher's 発売日 because the two state
    # different conventions. So the page has to go with the date it belonged to; a citation left
    # standing beside somebody else's answer is worse than none.
    cited, _, _ = cv.apply_dates(cited, {"9784091287557": "2019-01"}, "madb-tankobon")
    s.eq(cited["works"]["167439"]["volumes"][0]["printed"], "2019-01",
         "the bibliography replaces the publisher's date")
    s.eq(cited["works"]["167439"]["volumes"][0]["printed_source"], None,
         "and carries no page, so the publisher's is cleared with it")

    s.eq(sorted(cv.isbns_held(doc)), ["9784091287557"], "the ISBNs to ask about are gathered once")
    s.eq(cv.isbns_held({"works": {}}), {}, "an empty capture asks about nothing")

    # ── WHICH VOLUME PAGES ARE WORTH OPENING ─────────────────────────────────────────────────
    # A volume page always states 配信開始日, so `delivered` is the mark of a page already read.
    printed = cv.record(parsed(), None)[0]
    s.eq(cv.volumes_outstanding({"works": {"167439": printed}}), [("167439", 2)],
         "volume 1 was read off the work page; volume 2 is what is left to ask about")

    # THE COST CONTROL, and it is where the remainder of the money goes. A work whose first volume
    # states no ISBN was never printed, so its later volumes will not state one either, and asking
    # buys a distribution date that answers nothing under §6.
    digital = cv.record(parsed(isbn=None, published=None), None)[0]
    s.eq(cv.volumes_outstanding({"works": {"167439": digital}}), [],
         "a digital-only work's later volumes are not worth a request")
    s.eq(cv.volumes_outstanding({"works": {"167439": digital}}, printed_only=False),
         [("167439", 2)], "unless the caller says to ask about them anyway")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
