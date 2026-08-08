#!/usr/bin/env python3
"""store.py: what counts as the same reading, and what counts as a conflict."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import store


def main(s):
    # Word boundaries are a presentation choice, not a disagreement. A kana surface carries no
    # space; a source that separates family from given does. Treating that as a conflict filled the
    # review list with 23 non-conflicts, and a review list nobody trusts is a review list nobody
    # reads.
    s.check(store.same_reading("アオタユキコ", "アオタ ユキコ"), "spacing alone is not a conflict")
    s.check(store.same_reading("アオタ　ユキコ", "アオタユキコ"),
            "a full-width space is not a conflict either")
    s.check(store.same_reading("ユリ", "ユリ"), "identical readings agree")

    # A real disagreement must still register, or the check is worthless in the other direction.
    s.check(not store.same_reading("アオタユキコ", "アオタミチコ"),
            "different readings are a genuine conflict")
    s.check(not store.same_reading("ユリ", "サクラ"), "unrelated readings disagree")

    s.eq(len(store.today()), 10, "today() is an ISO date")
    s.check(store.today().count("-") == 2, "and is dashed, so it sorts as a string")

    # SUPERSEDING. Equal rank and a different value is a conflict between sources, and the same
    # producer revising itself is not: a reworded translation was filed as a conflict against
    # itself and the page kept showing the wording that had just been rejected.
    import tempfile
    tmp = tempfile.TemporaryDirectory()
    st = store.NameStore(tmp.name)
    st.record("titles", "私を喰べたい、ひとでなし", en="The Inhuman Girl Who Wants to Eat Me",
              basis="translated", source="yurarium")
    st.record("titles", "私を喰べたい、ひとでなし", en="This Monster Wants to Eat Me",
              basis="translated", source="yurarium", supersede=True)
    r = st.records["titles"]["私を喰べたい、ひとでなし"]
    s.eq(r["en"], "This Monster Wants to Eat Me", "the revision is adopted")
    s.check(any(c["value"] == "The Inhuman Girl Who Wants to Eat Me"
                for c in r.get("en_conflicts") or []), "the wording it replaced is kept")
    s.check(not any(c["value"] == "This Monster Wants to Eat Me"
                    for c in r.get("en_conflicts") or []),
            "and the adopted wording is not left disagreeing with itself")
    st.record("titles", "私を喰べたい、ひとでなし", en="This Monster Wants to Eat Me",
              basis="translated", source="yurarium", supersede=True)
    s.eq(len(r.get("en_conflicts") or []), 1, "re-applying the same file adds nothing")
    st.record("titles", "私を喰べたい、ひとでなし", en="A Scanlation Title",
              basis="translated", source="somewhere-else")
    s.eq(r["en"], "This Monster Wants to Eat Me",
         "and a caller that did not ask to supersede still cannot overwrite")

    # A DIVISION IS NOT A DISAGREEMENT, and superseding has to ask `same_reading` the same way the
    # rank merge does. It asked `==`, so the 37 kana names that took a division from openBD's
    # collationkey each filed their own undivided form as a conflict with itself.
    st.record("authors", "あおのなち", reading="アオノナチ", reading_basis="surface",
              source="surface")
    st.record("authors", "あおのなち", reading="アオノ ナチ", reading_basis="surface",
              source="openBD", supersede=True)
    a = st.records["authors"]["あおのなち"]
    s.eq(a["reading"], "アオノ ナチ", "the division is adopted")
    s.eq(a.get("reading_conflicts"), None,
         "and the undivided form is not filed as a source disagreeing with itself")
    st.record("authors", "あおのなち", reading="アオノ ミチコ", reading_basis="surface",
              source="elsewhere", supersede=True)
    s.check(any(c["value"] == "アオノ ナチ" for c in a.get("reading_conflicts") or []),
            "a real disagreement is still kept, which is what the list is for")
    st.close()
    tmp.cleanup()

    # SPANS BELONG TO THE READING THEY WERE CUT FROM. pass 4 writes them beside the reading it
    # derived them from, and a better reading arriving later left ruby spelling something the
    # record no longer said. 193 records were in that state.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        st = store.NameStore(d)
        st.records["titles"]["球詠"] = {
            "reading": "タマヨミ",
            "furigana_spans": [["球", "きゅう"], ["詠", "えい"]],
        }
        st.records["titles"]["雨夜の月"] = {
            "reading": "アマヨ ノ ツキ",
            "furigana_spans": [["雨夜", "あまよ"], ["の", None], ["月", "つき"]],
        }
        dropped = st.drop_stale_spans()
        s.eq(dropped, 1, "the spans that do not spell their reading are dropped")
        s.check("furigana_spans" not in st.records["titles"]["球詠"],
                "きゅうえい does not spell タマヨミ, so it goes")
        s.check("furigana_spans" in st.records["titles"]["雨夜の月"],
                "and spans that do spell their reading are kept, spacing and all")

    # THE DOUBT WAS ABOUT A READING THAT HAS BEEN REPLACED. The mark says a machine was unsure,
    # and pass 4 sets it on the record rather than through record(), so a better reading arriving
    # later left it in place: eight titles a person had settled stayed in the review queue, and a
    # budget that cannot fall is not a ratchet.
    with tempfile.TemporaryDirectory() as d:
        st = store.NameStore(d)
        st.records["titles"]["夢後のグレイ"] = {
            "reading": "ボウゴ ノ グレイ", "reading_basis": "researched",
            "reading_uncertain": True}
        st.records["titles"]["まだ機械のまま"] = {
            "reading": "キカイ", "reading_basis": "analyser", "reading_uncertain": True}
        s.eq(st.drop_settled_doubt(), 1, "the doubt does not outlive the reading it was about")
        s.check(not st.records["titles"]["夢後のグレイ"].get("reading_uncertain"),
                "a researched reading is somebody's answer, not a thing to keep asking about")
        s.check(st.records["titles"]["まだ機械のまま"].get("reading_uncertain"),
                "and a reading still the analyser's keeps its mark")

    # A CITATION THE FILE STOPPED CARRYING LEAVES THE RECORD. record() filters None out of the fact
    # before _apply sees it, so a key deleted from an entry was indistinguishable from one never
    # written: the store kept the old value and re-applying could not remove it. Found on
    # 真先輩の前ではかっこつけられない!, whose English is ours and cited the National Diet Library,
    # because the address had been written entry-wide before it moved to reading_url.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        st2 = store.NameStore(d)
        st2.record("titles", "X", en="An English Name", basis="translated", source="ndl",
                   source_url="https://example.invalid/rec", source_kind="national-library",
                   supersede=True)
        s.eq(st2.records["titles"]["X"].get("en_url"), "https://example.invalid/rec",
             "the citation lands on the claim")
        st2.record("titles", "X", en="An English Name", basis="translated",
                   source="yurarium", source_kind="derived", supersede=True)
        s.check("en_url" not in st2.records["titles"]["X"],
                "and a citation the file stopped carrying leaves the record")
        # A claim the file says nothing about keeps its own page.
        st2.record("titles", "X", reading="ヨミ", reading_basis="stated",
                   reading_source="national-library", reading_url="https://example.invalid/yomi",
                   supersede=True)
        st2.record("titles", "X", en="Another Name", basis="translated", supersede=True)
        s.eq(st2.records["titles"]["X"].get("reading_url"), "https://example.invalid/yomi",
             "an entry silent about the reading does not strip the reading's page")

    # AN ABSENCE EXPIRES, AND ONLY WHERE IT WAS ASKED TO. A work with no record at the National
    # Diet Library today has one when its next volume is deposited, so an attempt recorded for ever
    # turns a saving into a hole. The four numbered passes still get "for ever", because expiring
    # them would re-ask 2,002 names against Wikidata for a source whose answer does not change on a
    # schedule.
    with tempfile.TemporaryDirectory() as d:
        st3 = store.NameStore(d)
        st3.attempt("ある作品", "ndl-books", "ndl-books")
        s.check(st3.tried("ある作品", "ndl-books"), "an attempt is recorded")
        s.check(st3.tried("ある作品", "ndl-books", 180), "and is fresh on the day it was made")
        st3.attempts["ある作品"][0]["at"] = "2020-01-01"
        s.check(not st3.tried("ある作品", "ndl-books", 180),
                "an absence older than the expiry is worth asking about again")
        s.check(st3.tried("ある作品", "ndl-books"),
                "and with no expiry asked for, it still suppresses the question")
        s.check(not st3.tried("ある作品", "openbd", 180),
                "an attempt against one source says nothing about another")
        # A date nothing can read must not re-open a two hour sweep every run.
        st3.attempts["ある作品"][0]["at"] = "not a date"
        s.check(st3.tried("ある作品", "ndl-books", 180), "an unreadable date counts as recent")
        s.eq(st3.open_for("titles", ["ある作品"], "ndl-books", "reading"), [],
             "open_for skips what this source has already answered nothing for")
        st3.attempts["ある作品"][0]["at"] = "2020-01-01"
        s.eq(st3.open_for("titles", ["ある作品"], "ndl-books", "reading", 180), ["ある作品"],
             "and re-opens it once the absence has expired")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "store"))

