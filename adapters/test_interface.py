#!/usr/bin/env python3
"""interface.py: loading the real kari/app.js and asking it what a reader would see.

COVERS = ['adapters/interface.py', 'adapters/interface.js']

WHAT THIS HAS TO PROVE, beyond that node starts. The whole value of this seam is that it is not a
model of the interface, so the assertions below are about the difference between running app.js and
describing it. Each pins a rendering the transcription in check.py got wrong:

  a title with a subtitle after an ISBD colon is NOT joined to the base title, which is the
  fallback the transcription invented and the reason a work reached a reader in Japanese;

  a title with a closed-set edition marker IS glossed beside its base title, which is a fallback
  app.js really has and which a rule guessed from the first case would have missed;

  `foldKey` is the browser's own, and its answer comes back whole rather than with the harness's
  tag stripper having read the ＜完＞ in a chapter name as an element and thrown it away.

OFFLINE. Nothing here reaches a network: node is handed a request on stdin and a path to a file.
Where node is not installed the suite says so and asserts nothing that depends on it, which the
runner reports as vacuous rather than as a pass.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import interface
import testkit

# A name map the size of a fixture: three records, each one a shape the renderer treats
# differently. Written out here rather than cut from feed/names.json because it is not a page and
# has no provenance to keep; what makes it honest is that each record is the shape a real one has.
# KEYED AS THE BUILD KEYS IT, folded: NFKC and every space removed. Written folded here rather
# than folded by a helper, because a helper would be this file's copy of `foldKey` and the point of
# the suite is that there is no copy.
NAMES = {
    "titles": {
        # A curated translation, under the platform's spelling with the subtitle in 〜 〜.
        "怪異部~M県Y市の怪現象について~": {
            "en": "The Uncanny Club", "basis": "translated",
            "en_forms": {"translated": "The Uncanny Club"}},
        # The base of an edition marker, which app.js glosses beside.
        "恋愛遺伝子XX": {
            "en": "The Romance Gene XX", "basis": "translated",
            "en_forms": {"translated": "The Romance Gene XX"}},
        # A romanisation and nothing else, which follows the style control.
        "雨夜の月": {"reading": "アマヨノツキ", "basis": "romaji",
                 "romaji": {"macron": "Amayo no Tsuki", "double": "Amayo no Tsuki",
                            "plain": "Amayo no Tsuki"}},
    },
    "authors": {},
    "phrases": {"第1話": "Ch. 1"},
    "credit_parts": {},
    "publishers": {"一迅社": {"en": "Ichijinsha", "basis": "official-jp"}},
    "imprints": {"Yurihime comics": {"id": "yurihime", "name": "コミック百合姫"}},
}


def main(s):
    # ── the ruling table, which the lint beside this reads as well ────────────────────────────
    #
    # Two sets and a relation between them, so both halves have to be checkable without node.
    paths = {p for surface in interface.SURFACES for p in surface.ruled_paths}
    s.check("works[].title.ja" in paths,
            "the bibliographic record's title is a ruled surface; it is the field the 発売 tab "
            "labelled a volume from while every check was green")
    s.check("series[].print[].imprint" in paths,
            "a nested path is ruled at the depth the data holds it")
    s.eq(sorted(interface.unruled({"series": [{"work": "雨夜の月"}]})), [],
         "a collection holding only ruled fields leaves nothing unruled")
    s.eq(interface.unruled({"series": [{"an_invented_field": "日本語"}]}),
         ["series[].an_invented_field"],
         "a field carrying Japanese that nothing has ruled on is reported, which is what stops the "
         "list of name fields going stale as passes add to the data")
    s.eq(interface.unruled({"series": [{"an_invented_field": "plain english"}]}), [],
         "and a field with no Japanese in it raises no question")

    calls, about = interface.calls_for({"works": [{"title": {"ja": "怪異部 : M県Y市の怪現象について"},
                                                  "creator": "[著]やまじえびね"}]})
    s.check(("workLabel", {"title": {"ja": "怪異部 : M県Y市の怪現象について"},
                           "creator": "[著]やまじえびね",
                           "work": "怪異部 : M県Y市の怪現象について"}) in calls,
            "a title living somewhere else on the row is handed to workLabel as `work`, which is "
            "what renderReleases does")
    s.check(any(c[0] == "creditNames" for c in calls),
            "and the credit field goes to the function the 発売 tab renders it with")
    s.eq(len(calls), len(about), "every call is accounted for by something saying what it was")

    if not interface.available():
        print("  note: node or kari/app.js is not here, so nothing was rendered")
        return

    # ── the interface itself, running ─────────────────────────────────────────────────────────
    iface = interface.Interface(names=NAMES, prefs={"LANG": "en"})
    got = iface.labels([
        ("workLabel", {"work": "怪異部～M県Y市の怪現象について～"}),
        ("workLabel", {"work": "怪異部 : M県Y市の怪現象について"}),
        ("workLabel", {"work": "恋愛遺伝子XX : 完全版"}),
        ("workLabel", {"work": "雨夜の月"}),
        ("phraseOf", "第１話"),
        ("imprintOf", "Yurihime comics"),
        ("pubBoth", "一迅社"),
    ])
    s.eq(got[0], "The Uncanny Club",
         "a title the store holds under its own spelling renders in English")
    s.eq(got[1], "怪異部 : M県Y市の怪現象について",
         "THE CATALOGUED SPELLING DOES NOT. app.js does not strip a subtitle to find the base "
         "title, and check.py's transcription claimed it did, which is why eight works reached a "
         "reader in Japanese with the invariant green. The fix is a key in the shipped map, and "
         "this is the assertion that the interface has not silently grown the fallback instead")
    s.eq(got[2], "The Romance Gene XX (Complete Edition)",
         "an edition marker from the closed set IS glossed beside its base title, so a rule "
         "generalised from the line above would be wrong in the other direction")
    s.eq(got[3], "Amayo no Tsuki", "a record with only a reading renders as a romanisation")
    s.eq(got[4], "Ch. 1", "a chapter name comes from the phrase map")
    s.eq(got[5], "コミック百合姫", "an imprint string resolves to the line the registry names")
    s.eq(got[6], "Ichijinsha", "a publisher renders through the shipped map")

    japanese = iface.with_prefs(LANG="ja").labels([("workLabel", {"work": "雨夜の月"})])
    s.eq(japanese[0], "雨夜の月",
         "and in Japanese the same row renders as itself, so the preference is really being set "
         "rather than being ignored on a name app.js does not hold")

    s.eq(iface.values([("foldKey", "4話②＜完＞")])[0], "4話2<完>",
         "the browser's own fold, returned whole. `labels` strips tags and read <完> as an "
         "element, which reported a disagreement with the Python fold that only the harness had")

    s.raises(interface.Unavailable,
             lambda: interface.render([["noSuchFunction", 1]], names=NAMES),
             "asking for a function kari/app.js does not have raises rather than answering empty, "
             "because a renderer that returned nothing would look exactly like a clean page")
    s.raises(interface.Unavailable,
             lambda: interface.render([["workLabel", {}]], names=NAMES, prefs={"NOT_A_PREF": 1}),
             "and so does a preference app.js does not hold, which would otherwise make every "
             "check above vacuous by never selecting English at all")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "interface"))
