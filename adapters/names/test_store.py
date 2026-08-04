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


if __name__ == "__main__":
    sys.exit(testkit.run(main, "store"))
