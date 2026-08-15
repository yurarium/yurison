#!/usr/bin/env python3
"""admit: which announced works the corpus takes without asking a person first.

COVERS = ['adapters/admit.py']

WHAT CAN BE WRONG HERE IS ADMITTING TOO MUCH, and the two directions cost different things. Refusing
a work a platform serves openly leaves it out of the database until somebody notices, which is the
state this policy was written to end: 贋作の第十番 was announced on 7 June and was still absent ten
weeks later. Admitting one from a platform the register does not know, or one it marks age-gated,
puts a title into the list every adapter looks for and reaches past a ruling DEFINITIONS §7 makes
by designation. So the test is the register's and the refusals carry reasons.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import admit                                                            # noqa: E402
import testkit                                                          # noqa: E402

COVERS = ["adapters/admit.py"]

#: A register of the shape `facts/platform.registered` returns, holding the three cases.
KNOWN = [
    {"name": "カドコミ", "id": "kadokomi", "ids": ["kadokomi"], "aliases": [],
     "host": "comic-walker.com", "hosts": ["comic-walker.com"]},
    {"name": "チャンピオンクロス", "id": "championcross", "ids": ["championcross"], "aliases": [],
     "host": "championcross.jp", "hosts": ["championcross.jp"]},
    {"name": "オトナ書店", "id": "otona", "ids": ["otona"], "aliases": [], "age_gated": True,
     "host": "otona.example", "hosts": ["otona.example"]},
    {"name": "マイナビニュース", "id": "mynavi-news", "ids": ["mynavi-news"], "aliases": [],
     "serves_works": False, "host": "news.mynavi.jp", "hosts": ["news.mynavi.jp"]},
]

SERVED = {"work_title": "クレアちゃん飼育日記", "platform": "kadokomi",
          "work_url": "https://comic-walker.com/detail/KC_016896_S"}


def main(s):
    # ── WHAT THE POLICY TAKES ─────────────────────────────────────────────────────────────────
    s.eq(admit.admits(SERVED, KNOWN), (True, None),
         "a work served by a platform the register knows is taken without asking anybody")
    s.eq(admit.targets([{"candidates": [SERVED]}], KNOWN),
         [{"title": "クレアちゃん飼育日記", "platform": "カドコミ",
           "url": "https://comic-walker.com/detail/KC_016896_S"}],
         "and reaches the target list under the platform's own name, which is what adapters match")

    # THE NAME AND NOT THE ID, because the target list is keyed on what a reader is shown. 贋作の
    # 第十番 went in as `championcross` where every other row says カドコミ, and every adapter
    # looking for a platform by that name would have found none.
    s.eq(admit.targets([{"candidates": [dict(SERVED, platform="championcross",
                                             work_url="https://championcross.jp/episodes/b5")]}],
                       KNOWN)[0]["platform"], "チャンピオンクロス",
         "an id is a spelling the register lists, and the name is what comes out")

    # ── WHAT IT REFUSES, AND WHY EACH REFUSAL IS ITS OWN SENTENCE ─────────────────────────────
    #
    # A GATE AT THE DOOR IS A DESIGNATION. DEFINITIONS §7 excludes pornography by the signals a
    # publisher or a platform prints, and an age gate is the platform printing one.
    s.eq(admit.admits(dict(SERVED, platform="otona",
                           work_url="https://otona.example/x/1"), KNOWN)[0], False,
         "an age-gated platform is not taken automatically")
    s.check("not a platform this reads openly"
            in admit.admits(dict(SERVED, platform="otona",
                                 work_url="https://otona.example/x/1"), KNOWN)[1],
            "and the refusal says which test it failed")

    # A NEWS SITE REPORTS ON WORKS AND SERVES NONE, so taking one from there is taking it from an
    # article about it.
    s.eq(admit.admits(dict(SERVED, platform="mynavi-news",
                           work_url="https://news.mynavi.jp/article/1"), KNOWN)[0], False,
         "a platform serving no works is not one to take a work from")

    # A PLATFORM NOBODY HAS REGISTERED. The register is what "known" means, so an unknown host is
    # a decision somebody has to make rather than one this may take.
    s.eq(admit.admits(dict(SERVED, platform="nowhere"), KNOWN)[0], False,
         "an unregistered platform is refused")

    # AN ANNOUNCEMENT WITH NO PLATFORM IS NEWS ABOUT A WORK. `ムルシエラゴ` was an anime adaptation
    # notice: it names a work this may well hold and says nothing about where to read it.
    s.eq(admit.admits({"work_title": "ムルシエラゴ"}, KNOWN), (False, "names no platform"),
         "an announcement naming no platform names nowhere to look")

    # AND AN ADDRESS IS WHAT AN ADAPTER FETCHES. A title with no URL in the target list is a title
    # every pass looks for and none finds.
    s.eq(admit.admits({"work_title": "x", "platform": "kadokomi"}, KNOWN)[1],
         "carries no address on that platform",
         "a candidate with no address is refused, and says so")
    s.eq(admit.addressable({"work_url": "https://unknown.example/x"}), None,
         "an address on a host the register cannot name is no address for this")

    # ── NOTHING IS SILENT ─────────────────────────────────────────────────────────────────────
    #
    # A queue is read by a person deciding what to do next, so a refusal that printed nothing would
    # leave a work sitting there with no reason attached to it.
    q = [{"candidates": [SERVED, {"work_title": "ムルシエラゴ"},
                         dict(SERVED, work_title="x", platform="nowhere")]}]
    s.eq(len(admit.targets(q, KNOWN)), 1, "one of the three is taken")
    s.eq(sorted(t for t, _ in admit.refused(q, KNOWN)), ["x", "ムルシエラゴ"],
         "and the other two are named as refused")

    # ONE ROW PER WORK, however many queues announced it.
    s.eq(len(admit.targets([{"candidates": [SERVED]}, {"candidates": [SERVED]}], KNOWN)), 1,
         "a work announced twice is one target")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
