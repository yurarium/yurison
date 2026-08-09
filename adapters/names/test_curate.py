#!/usr/bin/env python3
"""What curate.py must refuse, and what must survive being applied twice."""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import curate  # noqa: E402
from names.store import NameStore  # noqa: E402

COVERS = ["adapters/names/curate.py"]

LICENSED = {"en": "Otherside Picnic", "basis": "licensed", "source": "Square Enix Manga & Books",
            "source_kind": "licensor", "source_url": "https://example.invalid/otherside",
            "reviewed": "2026-08-03"}
OURS = {"en": "Wine Girls", "basis": "translated", "source": "yurarium",
        "source_kind": "derived", "reviewed": "2026-08-03"}


def with_(**kw):
    e = dict(LICENSED)
    e.update(kw)
    return {k: v for k, v in e.items() if v is not None}


def main(s):
    s.eq(curate.problems("titles", "x", LICENSED), [], "a licensed title with a licensor page")
    s.eq(curate.problems("titles", "x", OURS), [], "our own translation, no source page owed")

    # The project owner's rule, now enforced rather than remembered.
    s.check(curate.problems("titles", "x", with_(source_kind="community-db",
                                                 source="Wikipedia",
                                                 source_url="https://example.invalid/w")),
            "a community database may not supply an attributed name")
    s.check(curate.problems("titles", "x", with_(basis="official-jp")),
            "a licensor page cannot establish the work's OWN English name")
    s.check(curate.problems("titles", "x", with_(source_url=None)),
            "an attributed name needs the page it was read from")
    s.check(curate.problems("titles", "x", with_(basis="translated", source_kind="derived",
                                                 source_url=None, en="Otherside Picnic")) == [],
            "a translation needs no page, because it is not a finding")
    s.check(curate.problems("titles", "x", with_(reviewed=None)),
            "an entry with no review date")
    s.check(curate.problems("titles", "x", with_(bais="licensed")),
            "a misspelt key is an error rather than a silent no-op")
    s.check(curate.problems("titles", "x", with_(candidate="Otherside Picnic")),
            "an entry cannot be both attributed and a candidate")
    s.check(curate.problems("titles", "x", {"candidate": "Stardust Telepath",
                                            "source": "Wikipedia",
                                            "source_kind": "community-db",
                                            "reviewed": "2026-08-03"}) == [],
            "a community database is a fine source for a CANDIDATE")
    s.check(curate.problems("titles", "x", {"candidate": "Stardust Telepath", "basis": "licensed",
                                            "source": "Wikipedia", "source_kind": "community-db",
                                            "reviewed": "2026-08-03"}),
            "a candidate carrying a basis is a claim in disguise")
    s.check(curate.check({"titels": {}}), "an unknown top-level key")

    # A NAME THE PERSON WRITES THEMSELVES IS `stated`, AND THE PERSON IS THE EVIDENCE FOR IT.
    # `author` reached SOURCE_KINDS and READING_ATTRIBUTION in a round that was about readings, and
    # ATTRIBUTION kept the row whose comment says "the person's own rendering" without the person in
    # it. GAPS §9 is what that cost: 616 author names are romanisations of ours because the entry
    # recording a Latin byline could not be written down.
    OWN = {"en": "Sal Jiang", "basis": "stated", "source": "the artist's own X profile",
           "source_kind": "author", "source_url": "https://example.invalid/jiangsal",
           "reviewed": "2026-08-06"}
    s.eq(curate.problems("authors", "サル・ジャン", OWN), [],
         "a Latin byline on the artist's own page is theirs, and outranks anything we compute")
    s.check(curate.problems("authors", "サル・ジャン", dict(OWN, source_url=None)),
         "and it still needs the page it was read on, because a claim about a person is checkable")
    s.check(curate.problems("authors", "サル・ジャン", dict(OWN, source_kind="community-db")),
         "a fan database writing a romanisation is not the person stating a preference")
    s.check(curate.problems("authors", "サル・ジャン", dict(OWN, basis="licensed")),
         "and the artist is not a licensor, so the person cannot stand in for a catalogue")

    with tempfile.TemporaryDirectory() as d:
        doc = {"titles": {"裏世界ピクニック": LICENSED, "ワインガールズ": OURS,
                          "星屑テレパス": {"candidate": "Stardust Telepath", "source": "Wikipedia",
                                      "source_kind": "community-db", "reviewed": "2026-08-03"}}}
        st = NameStore(d)
        # A romanised string already in place, which is what the passes leave behind.
        st.record("titles", "ワインガールズ", en="Wain Gāruzu", basis="romaji", source="derived")
        applied, cands = curate.apply(st, doc)
        s.eq((applied, cands), (2, 1), "two attributed, one candidate")
        rec = st.records["titles"]
        s.eq(rec["裏世界ピクニック"]["en"], "Otherside Picnic", "the licensed title lands")
        s.eq(rec["ワインガールズ"]["en"], "Wine Girls", "a translation outranks a romanisation")
        s.check("Wain Gāruzu" in str(rec["ワインガールズ"].get("en_conflicts")),
                "the displaced romanisation is kept rather than discarded")
        s.check(not rec["星屑テレパス"].get("en"), "a candidate never becomes the name")
        s.eq(rec["星屑テレパス"]["en_candidates"][0]["value"], "Stardust Telepath",
             "the candidate is recorded where a later fetch can settle it")
        s.eq(rec["裏世界ピクニック"]["en_at"], "2026-08-03",
             "the stamp is the review date, not the day this ran")

        curate.apply(st, doc)
        s.eq(len(rec["星屑テレパス"]["en_candidates"]), 1, "re-applying the file changes nothing")
        s.eq(rec["ワインガールズ"]["en"], "Wine Girls", "and does not disturb an applied name")
        st.close()

    # OUR RENDERING BESIDE THE NAME THE WORK ALREADY HAS. The entry holds one `en`, so a title
    # carrying a licensor's English had nowhere to put a translation of the meaning, and 225 titles
    # offered a reader who moves `licensed` down EN_ORDER nothing to fall through to.
    BOTH = dict(LICENSED, translation="Backworld Picnic",
                translation_note="裏世界 is the world behind this one; the licensor's Otherside "
                                 "reads as a place name and loses the sense of a reverse side.")
    s.eq(curate.problems("titles", "裏世界ピクニック", BOTH), [],
         "an attributed name and our own translation, each with its own argument")
    s.check(curate.problems("titles", "裏世界ピクニック",
                            {k: v for k, v in BOTH.items() if k != "translation_note"}),
            "a translation with no argument behind it is the machine translation §5a rules out")
    s.check(curate.problems("titles", "ワインガールズ", dict(OURS, translation="Wine Girls")),
            "and a translation needs a name to sit beside; on its own it is just the `en`")
    s.check(curate.problems("titles", "裏世界ピクニック",
                            dict(BOTH, translation="Otherside Picnic")),
            "a translation repeating the attributed name adds no second form")

    with tempfile.TemporaryDirectory() as d:
        st = NameStore(d)
        curate.apply(st, {"titles": {"裏世界ピクニック": BOTH}})
        rec = st.records["titles"]["裏世界ピクニック"]
        # THE ATTRIBUTION KEEPS THE DISPLAY. §5's precedence is explicit that a licensor's title
        # outranks ours, so recording the translation must not take the slot: it is a second form
        # to offer, not a better answer.
        s.eq(rec["en"], "Otherside Picnic", "the licensed name still displays")
        s.eq(rec["basis"], "licensed", "on the basis that says whose name it is")
        s.eq(rec["en_source"], "Square Enix Manga & Books", "citing the page it was read from")
        s.eq([c["value"] for c in rec["en_conflicts"]], ["Backworld Picnic"],
             "with ours kept beside it, which is what build.py assembles en_forms from")
        s.check("reverse side" in rec["translation_note"], "and the argument for ours survives")

        # RE-WORDING A TRANSLATION REPLACES IT. The old wording standing beside the new one is a
        # conflict list disagreeing with itself, which is what `_supersede` exists to prevent for
        # the winning claim and could not reach here, because this claim deliberately does not
        # supersede: superseding would clear the licensor's name out of the slot.
        curate.apply(st, {"titles": {"裏世界ピクニック": dict(BOTH, translation="Reverse-Side Picnic")}})
        s.eq([c["value"] for c in rec["en_conflicts"]], ["Reverse-Side Picnic"],
             "the revised wording replaces the one it revises")
        curate.apply(st, {"titles": {"裏世界ピクニック": dict(BOTH, translation="Reverse-Side Picnic")}})
        s.eq(len(rec["en_conflicts"]), 1, "and re-applying the same file changes nothing")
    # A REFUTATION THE FILE HAS WITHDRAWN LEAVES THE RECORD. A refutation says nothing can be put
    # in this slot, and research eventually putting something there is the outcome it was written
    # to wait for. 生肉's セイニク was dropped in August with nothing to replace it; まんが王国 files
    # the artist ナマニク and the X handle the refutation recorded, @namanoniku0005, spells the same
    # thing. Applying the replacement left the record holding a reading AND the refutation of one,
    # so the file could record that decision and could not reverse it, and `pass4_analyser` reads
    # that field to decide whether a name may be filled at all.
    with tempfile.TemporaryDirectory() as d:
        st = NameStore(d)
        gone = {"reading_refuted": True, "reviewed": "2026-08-05", "source": "yurarium",
                "source_kind": "derived",
                "reading_note": "セイニク is a machine guess with nothing behind it."}
        curate.apply(st, {"authors": {"生肉": gone}})
        rec = st.records["authors"]["生肉"]
        s.check(rec.get("reading_refuted"), "the refutation is recorded")
        s.check(not rec.get("reading"), "and the reading it disowns is gone")

        found = {"reading": "ナマニク", "reading_basis": "researched",
                 "reading_source_kind": "derived", "reading_note": "まんが王国 files them so.",
                 "source": "まんが王国", "source_kind": "derived", "reviewed": "2026-08-08"}
        curate.apply(st, {"authors": {"生肉": found}})
        rec = st.records["authors"]["生肉"]
        s.eq(rec["reading"], "ナマニク", "the answer the refutation was waiting for lands")
        s.check(not rec.get("reading_refuted"),
                "and the refutation goes, so the record does not hold a reading and its denial")
        st.close()

    # A curated READING. The interface renders basis-romaji titles from the kana, so a wrong
    # reading cannot be fixed by writing the romanisation into `en`: the string is ignored.
    R = {"reading": "タマヨミ", "reading_basis": "stated", "source": "comic-fuz",
         "source_kind": "platform", "source_url": "https://example.invalid/441",
         "reviewed": "2026-08-03"}
    s.eq(curate.problems("titles", "球詠", R), [], "a reading stated by the platform")
    s.check(curate.problems("titles", "球詠", dict(R, reading="たまよみ")),
            "a hiragana reading is caught here rather than by a build invariant")
    s.check(curate.problems("titles", "球詠", dict(R, reading_basis="guessed")),
            "guessed is what curation replaces, so it cannot be curated")
    # A COMMUNITY DATABASE RAISES THE FLOOR AND STATES NOTHING, RULED BY THE PROJECT OWNER
    # 2026-08-09: "treat wikidata as noncanonical. use it to raise the floor on romaji". A pass on
    # the same day had put `community-db` in the `stated` row on the argument that P1814 prints kana,
    # and the ruling overturned it. The kana are still worth having, which is what `community-printed`
    # is, and they satisfy no test asking whether a source stated the reading.
    s.check(curate.problems("titles", "球詠", dict(R, source_kind="community-db")),
            "a community database does not state a reading")
    s.eq(curate.problems("titles", "球詠", dict(R, source_kind="community-db",
                                               reading_basis="community-printed")), [],
         "and the kana it prints are admissible as a floor under their own basis")
    s.check("community-printed" not in curate.STATED_BASES,
            "which no check asking whether a source stated a reading may accept")
    s.check(curate.problems("titles", "球詠", dict(R, source_kind="community-db",
                                                  en="Tamayomi", basis="official-jp")),
            "and the same source still cannot supply the work's own English name")
    s.check(curate.problems("titles", "球詠", dict(R, source_kind="platform",
                                                  reading_basis="community-printed")),
            "nor may a platform's own page be filed as something a community database printed")
    # THE LINE THE ROW TURNS ON. A romanisation read backwards has lost the length of every vowel,
    # so it is not a stated reading whoever holds it, and this table carries no row for it at all.
    s.check(curate.problems("titles", "球詠", dict(R, reading_basis="back-converted")),
            "a reading recovered from a romanisation cannot be curated as stated")
    s.check(curate.problems("titles", "球詠", {"source": "x", "source_kind": "derived",
                                              "reviewed": "2026-08-03"}),
            "an entry that says nothing at all")
    s.check(curate.problems("titles", "球詠", dict(R, reading=None, reading_basis="stated")),
            "a reading_basis with no reading")
    # A READING CARRIES THE TITLE'S OWN MARKS, and these two arrived with titles settled by hand.
    # 鮮血王女 quotes 『死神』 inside its subtitle and 天華百剣 ‐瞬‐ brackets its subtitle in HYPHEN
    # and not in the ASCII one, so a pattern without them rejects a reading that is entirely kana.
    s.eq(curate.problems("titles", "球詠", dict(R, reading="『タマヨミ』")), [],
         "a reading keeps the corner brackets the title puts round a word")
    s.eq(curate.problems("titles", "球詠", dict(R, reading="タマ ‐ ヨミ ‐")), [],
         "and the HYPHEN a subtitle is bracketed in")
    s.check(curate.problems("titles", "球詠", dict(R, reading="『球詠』")),
            "which does not let a kanji through, since that is what the rule is for")

    # ── Where a name divides, in a field rather than in a sentence ────────────────────────────
    # `ndl_heading.entry` stated the division in `reading_note` and `boundary.fill` states it in
    # `reading_boundary`. 293 author records filled only the prose, so no count could tell them
    # from records with no source at all. A reading whose kind is `derived` carries nobody's
    # spacing, so a division in one has to name its donor.
    D = {"reading": "ワラビモチ キナコ", "reading_basis": "surface", "reading_source_kind": "derived",
         "source": "ndlsearch.ndl.go.jp", "source_kind": "national-library",
         "source_url": "https://ndlsearch.ndl.go.jp/books/R1", "reviewed": "2026-08-09"}
    s.check(curate.problems("authors", "わらびもちきなこ", D),
            "a division out of our own kana with no field naming its donor")
    s.eq(curate.problems("authors", "わらびもちきなこ",
                         dict(D, reading_boundary="the NDL author heading")), [],
         "and the same entry once it says where the division came from")
    # THE PROSE IS NOT THE ANSWER, which is the whole of this round. An entry explaining the
    # division at length and leaving the field empty is exactly the state 293 records were in.
    s.check(curate.problems("authors", "わらびもちきなこ",
                            dict(D, reading_note="NDL's heading divides this person as "
                                                 "'ワラビモチ キナコ'.")),
            "a division explained in a note and nowhere else is still unaccounted for")
    # WHERE THE SOURCE SUPPLIED THE KANA IT SUPPLIED THE SPACES IN THEM, so `reading_source` is
    # already the citation and nothing more is owed.
    s.eq(curate.problems("authors", "わらびもちきなこ",
                         dict(D, reading_basis="stated", reading_source_kind="national-library",
                              reading_url="https://ndlsearch.ndl.go.jp/books/R1")), [],
         "a reading that arrived divided from a cataloguing authority cites itself")
    s.check(curate.problems("authors", "缶乃", dict(D, reading="カンノ",
                                                   reading_boundary="the NDL author heading")),
            "and a boundary on a reading with no division in it names spaces that do not exist")
    # A TITLE IS A SENTENCE AND A PUBLISHER IS A COMPANY (NAMES-PLAN §5f). 2,532 title readings
    # hold an analyser's division and all of them stay, because their spacing is what places ruby.
    s.eq(curate.problems("titles", "空色の音", {"reading": "ソライロ ノ オト",
                                                "reading_basis": "surface", "source": "yurarium",
                                                "source_kind": "derived",
                                                "reviewed": "2026-08-09"}), [],
         "a divided title reading is the analyser doing the job it is good at")

    # A READING SETTLED BY A REVIEWER, where nothing states one. Ranked below a printed kana and
    # above what an analyser aligned, and it has to say what it rests on: a reading with no
    # reasoning behind it is a guess wearing a better label.
    R2 = {"reading": "タマヨミ", "reading_basis": "researched", "source": "pixiv dictionary",
          "source_kind": "community-db", "reviewed": "2026-08-03",
          "note": "readers write the title たまよみ, and 詠 takes よみ in the lead's name 詠深"}
    s.eq(curate.problems("titles", "球詠", R2), [], "a researched reading with its reasoning")
    s.check(curate.problems("titles", "球詠", {k: v for k, v in R2.items() if k != "note"}),
            "and the same reading with none is refused")
    s.check(not curate.problems("titles", "球詠", dict(R2, source_kind="derived")),
            "a reviewer's own reasoning is a source it may rest on")
    s.check(curate.problems("titles", "球詠", dict(R2, source_kind="licensor")),
            "a licensor does not state Japanese readings, so it is not evidence here")

    # A key off by one character applies cleanly and names nothing, so the join is checked.
    doc = {"titles": {"球詠": {}, "球詠 ": {}}, "authors": {"まめ魚": {}}}
    s.eq(curate.unmatched(doc, {"球詠"}), [], "a key that applies is not reported as naming nothing")
    s.eq(curate.unmatched({"titles": {"球詠X": {}}}, {"球詠"}), ["球詠X"],
         "a key differing in a character names no work we hold")
    s.eq(curate.unmatched(doc, {"球詠", "球詠 "}), [], "and one that matches is not")
    # THIS ASSERTION USED TO GO THE OTHER WAY, and the reason it changed is the point. `unmatched`
    # folded with NFKC alone while the build and the interface also strip spaces, so `球詠 ` was
    # reported as naming no work we hold while applying perfectly. Two definitions of one key, and
    # a measure built on the stricter one reported a number the page contradicted (§3). The stray
    # space is still worth telling whoever typed it, as its own finding.
    s.eq(curate.spaced_keys(doc, {"球詠"}), ["球詠 "],
         "a key that reaches a held title only through the space-stripping is reported as that")
    s.eq(curate.spaced_keys({"titles": {"球詠（1）": {}}}, {"球詠(1)"}), [],
         "and a width difference is one spelling of one work, not a spacing question")
    s.eq(curate.unmatched({"authors": {"だれか": {}}}, set()), [],
         "an author may be curated before any of their work is")

    # A DECISION IS NOT WORK OUTSTANDING, whichever way it went. §5a keeps some titles romanised
    # on purpose, and reporting those as pending asks somebody to redo a thing that is finished.
    # The queue reported 27 when 6 were real: 21 were settled romanisations.
    import json as _json
    with tempfile.TemporaryDirectory() as d:
        b = pathlib.Path(d); (b / "feed").mkdir()
        (b / "feed" / "names.json").write_text(_json.dumps({"titles": {
            "decided": {"basis": "romaji", "romaji": {"macron": "Decided"}},
            "translated": {"basis": "translated", "en": "Translated"},
            "untouched": {"basis": "romaji", "romaji": {"macron": "Untouched"}}}}))
        (b / "feed" / "current.json").write_text(_json.dumps({"releases": [
            {"work": "decided", "pub": "2026-08-01"}, {"work": "translated", "pub": "2026-08-01"},
            {"work": "untouched", "pub": "2026-08-01"}]}))
        (b / "series.json").write_text(_json.dumps({"series": []}))
        cf = b / "curated.yaml"
        cf.write_text('titles:\n  decided:\n    basis: romaji\n')
        rows = curate.todo(str(b), curated=str(cf))
        works = [w for _, w, _ in rows]
        s.check("untouched" in works, "a romanisation nobody has looked at is still work to do")
        s.check("decided" not in works,
                "one a reviewer settled as romaji is finished, and drops out")
        s.check("translated" not in works, "as does a translated title, as before")

    # The shipped file must itself pass, or the check is a thing that only tests fixtures.
    s.eq(curate.check(curate.load()), [], "the file in the repository validates")
    s.eq(curate.unmatched(curate.load(), curate.known_titles()), [],
         "and every title in it names a work we hold")


    # THE CORPUS IS STATED, NOT REASSEMBLED. known_titles used to union the feed's rolling window
    # with the series list: three curated titles stopped naming works we hold overnight because the
    # window moved past them, and nothing about the corpus had changed.
    with tempfile.TemporaryDirectory() as d:
        b = pathlib.Path(d)
        s.eq(curate.known_titles(str(b)), None,
             "no titles.json is no answer, which is not the same as no titles")
        # And a caller must not read that silence as agreement.
        raised = False
        try:
            curate.unmatched({"titles": {"anything": {}}}, None)
        except SystemExit:
            raised = True
        s.check(raised, "so checking against no answer refuses rather than passing")

        (b / "titles.json").write_text(_json.dumps({"titles": ["ある作品", "私の百合はお仕事です！"]}))
        known = curate.known_titles(str(b))
        s.eq(known, {"ある作品", "私の百合はお仕事です！"}, "and a stated set is read as it stands")
        s.eq(curate.unmatched({"titles": {"私の百合はお仕事です!": {}}}, known), [],
             "a half-width variant of a title we hold is that title")
        s.eq(curate.unmatched({"titles": {"知らない作品": {}}}, known), ["知らない作品"],
             "and one nobody holds is reported")

    # A KEY WRITTEN TWICE VALIDATES AND DISAPPEARS. yaml.safe_load keeps the later mapping and drops
    # the earlier without a word, so the file parses cleanly and holds one of the two decisions. 12
    # titles were in that state, one pair 8,500 lines apart, because appending is easier than
    # merging. Read as text, since by the time a dict exists the evidence is gone.
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "curated.yaml"
        f.write_text("titles:\n  ある話:\n    en: One\n  べつの話:\n    en: Two\n"
                     "  ある話:\n    en: Three\nauthors:\n  だれか:\n    reading: ダレカ\n")
        dups = curate.duplicate_keys(f)
        s.eq([(x[0], x[1]) for x in dups], [("titles", "ある話")], "a key written twice is found")
        s.eq(dups[0][2], [2, 6], "with both lines, so a reviewer can merge them")
        s.check(not any(x[1] == "べつの話" for x in dups), "and a key written once is not")
        # The parser cannot see it, which is the whole reason this reads text.
        import yaml as _y
        s.eq(len((_y.safe_load(f.read_text()) or {}).get("titles") or {}), 2,
             "the loaded file holds two titles where three were written")

        f.write_text("titles:\n  ある話:\n    en: One\n")
        s.eq(curate.duplicate_keys(f), [], "a clean file reports nothing")

    dividing_bases_and_donors(s)


def dividing_bases_and_donors(s):
    """The three lists that used to be one list copied out by hand, and what separates them.

    STANDING-INSTRUCTIONS §3. `curate.STATED_BASES` says which bases mean a source stated the
    reading, `curate.DIVIDING_BASES` says which arrive with their source's own division in them, and
    `boundary.SETTLED_BASES` says which may lend a division to a DIFFERENT record. `check.py` held
    hand-written copies of the first two and one of them had already drifted. Where a second producer
    genuinely cannot consume the first, §3 asks for an assertion that they agree, and this is it.
    """
    from names import boundary
    s.eq(set(curate.STATED_BASES), {"stated"},
         "one basis means a source stated the reading, and it is the one named after it")
    s.check(set(curate.STATED_BASES) <= set(curate.DIVIDING_BASES),
            "a stated reading arrives divided the way its source divided it")
    s.check(set(curate.STATED_BASES) <= set(curate.READING_ATTRIBUTION),
            "and every basis named there is a row of the table it selects from")
    # THE ONE ENTRY THAT COULD HAVE GONE EITHER WAY, and the reason it went this way is that the
    # mark travels. A lent division leaves its doubt behind on the donor's record, so
    # `boundary.donor_basis` carries the basis across and build.py ships it. Admitting the basis as a
    # donor without that would put an anonymous edit's word about where somebody's name breaks in
    # front of a reader with no mark on it at all: 8 records were in that state on 2026-08-09.
    s.check("community-printed" in curate.DIVIDING_BASES,
            "a community database's division stands where its own reading landed")
    s.check("community-printed" in boundary.SETTLED_BASES,
            "and may be lent, because donor_basis is what carries the mark with it")
    s.check("community-printed" in boundary.MARKED_DONOR_BASES,
            "which is the list that says a borrower owes the reader an explanation")
    s.check("analyser" not in curate.DIVIDING_BASES
            and "analyser" not in boundary.SETTLED_BASES,
            "an analyser divides every name it is handed, so its answer cites nothing")
    s.check("back-converted" not in curate.DIVIDING_BASES
            and "back-converted" not in boundary.SETTLED_BASES,
            "and a romanisation read backwards has lost the length of every vowel")
    s.eq(sorted(set(boundary.SETTLED_BASES) - set(curate.DIVIDING_BASES)), [],
         "nothing may lend a division that does not carry one of its own")

if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
