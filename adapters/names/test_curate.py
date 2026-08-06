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
    s.check(curate.problems("titles", "球詠", dict(R, source_kind="community-db")),
            "and a community database cannot state a reading either")
    s.check(curate.problems("titles", "球詠", {"source": "x", "source_kind": "derived",
                                              "reviewed": "2026-08-03"}),
            "an entry that says nothing at all")
    s.check(curate.problems("titles", "球詠", dict(R, reading=None, reading_basis="stated")),
            "a reading_basis with no reading")

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
    s.eq(curate.unmatched(doc, {"球詠"}), ["球詠 "], "a title matching no work is reported")
    s.eq(curate.unmatched(doc, {"球詠", "球詠 "}), [], "and one that matches is not")
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

if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
