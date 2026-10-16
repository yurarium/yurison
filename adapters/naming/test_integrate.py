#!/usr/bin/env python3
"""naming/integrate.py: the job's answers become curated entries only when a person's would.

COVERS = ['adapters/naming/integrate.py']
"""
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import integrate as ni                                                  # noqa: E402

TEXT = """titles:
  "既にある":
    en: "Already"
    basis: translated
    source: yurarium
    source_kind: derived
    reviewed: '2026-10-01'
    note: >-
      Named before.

authors:
  "誰か":
    en: "Someone"
"""
NOTE = "The platform page gives the English title on its logo, so it is the work's own name."


def main(s):
    official = {"key": "星の本", "en": "Star Book", "basis": "official-jp", "source_kind": "platform",
                "source_url": "https://comic-walker.com/detail/KC_1", "translation": "The Book of Stars",
                "translation_note": "星 is star and 本 a book, joined by の.", "note": NOTE}
    ours = {"key": "月の本", "en": "The Moon Book", "basis": "translated", "source_kind": "derived",
            "note": "月 is the moon and 本 a book; the page describes a diary kept by moonlight."}
    asked = {"星の本", "月の本", "既にある", "黙る"}
    text, written, refused = ni.integrate(TEXT, [official, ours, {**ours, "key": "既にある"}],
                                          asked, "2026-10-16")
    doc = yaml.safe_load(text)
    s.eq(written, ["星の本", "月の本"], "a sound answer to a title it was asked about is written")
    s.eq(doc["titles"]["星の本"]["source"], "comic-walker.com",
         "an official name cites the page it stands on, its host as the source")
    s.eq((doc["titles"]["月の本"]["source"], doc["titles"]["月の本"]["source_kind"]),
         ("yurarium", "derived"), "a translation of ours is attributed to us")
    s.eq(doc["titles"]["星の本"]["translation"], "The Book of Stars",
         "our own rendering stands beside the official name with its note")
    s.eq(list(doc["authors"]), ["誰か"], "and every entry lands in titles, before authors")
    same = ni.entry({**official, "translation": "STAR BOOK"}, "2026-10-16")[0]
    s.check("translation" not in same and same["en"] == "Star Book",
            "a rendering that is the official name in other letters is dropped, the name kept")
    s.eq(dict(refused), {"既にある": "already named", "黙る": "no answer"},
         "an existing key is never overwritten, and a title left unanswered is reported")

    bad = [{"key": "外の本", **{k: v for k, v in ours.items() if k != "key"}},
           {**official, "key": "星の本", "source_kind": "derived"},
           {**official, "source_url": ""},
           {**ours, "note": "Moon."},
           {"key": "月の本", "skip": "the page did not load"}]
    _, written, refused = ni.integrate(TEXT, bad, {"星の本", "月の本"}, "2026-10-16")
    s.eq(written, [], "and an unsound one is not")
    why = [w for _, w in refused]
    s.check(why[0] == "not a title it was asked about", "a key it was not asked about is refused")
    s.check("cannot rest on" in why[1], "an official name resting on our own judgement is refused")
    s.check("has to cite" in why[2], "an official name with no page is refused")
    s.check("does not say why" in why[3], "a note too thin to say why is refused")
    s.check(why[4].startswith("declined"), "a skip is reported as the job declining")

    dashed = ni.entry({**ours, "note": ours["note"] + " A moon — a book."}, "2026-10-16")[0]
    s.check("—" not in dashed["note"], "an em dash in a note does not reach the file")
    s.eq(ni.answers_of({"result": 'Here: {"names": [{"key": "x"}]}'}), [{"key": "x"}],
         "answers are read from the text when the structured output is absent")
    s.eq(ni.answers_of({"structured_output": {"names": [{"key": "y"}]}, "result": "{}"}),
         [{"key": "y"}], "and from the structured output when it is there")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "naming.integrate"))
