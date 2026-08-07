#!/usr/bin/env python3
"""capturegap.py: works a capture was told to read and wrote no row for.

COVERS = ['adapters/capturegap.py']

EVERY ROW BELOW IS REAL. STANDING-INSTRUCTIONS §14b asks a measure to be shown failing on something
the pipeline actually produces, so the rows here are copied out of `data/source/comicfuz/`,
`data/source/nicovideo/` and `data/source/kadokomi/` as they stood on 2026-08-07, spelling
untouched. ぬるめた is carried in `resolved.yaml` at `/series/2389` because that is the address the
search confirmed, and `/manga/2389` is the address every other FUZ file uses. The two are the same
page, and the pass that lost the work is the one that treated them as different.

THE COUNTER-CASES ARE THE POINT (§2). A rule that counted an unfamiliar spelling as missing would
report ばっどがーる, whose target is `/manga/2461` and whose capture row is `/manga/2461`, and would
report every work whose target came in as a bare `comic_id` and whose capture states a `url`. Both
are pinned below, because the measure would look right on ぬるめた and be worthless.

WHAT IS DELIBERATELY NOT SILENCED. A withheld work is accounted for, since the pass fetched its
page and refused it. A ruling in `data/queue/unheld-works.yaml` is not, since it records a decision
about a work and no capture of one (§13).
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import capturegap
import testkit

FUZ = re.compile(r"comic-fuz\.com/(?:manga|series)/(\d+)")
NICO = re.compile(r"manga\.nicovideo\.jp/comic/(\d+)")
KADO = re.compile(r"comic-walker\.com/detail/([A-Za-z0-9_]+)")

# data/source/comicfuz/resolved.yaml, as the confirmation pass wrote it.
FUZ_TARGETS = [
    {"title": "ぬるめた", "url": "https://comic-fuz.com/series/2389"},
    {"title": "ばっどがーる", "url": "https://comic-fuz.com/manga/2461"},
    {"title": "球詠", "url": "https://comic-fuz.com/manga/214"},
]
# data/source/comicfuz/works.yaml, as the capture wrote it. ぬるめた is the one that is not here.
FUZ_CAPTURE = [
    {"work_title": "ばっどがーる", "url": "https://comic-fuz.com/manga/2461"},
    {"work_title": "球詠", "url": "https://comic-fuz.com/manga/214"},
]
# data/coverage/webcomics-works.yaml candidates, which state addresses in a list and sometimes
# several of them, only one being the platform this pass captures.
NICO_TARGETS = [
    {"title": "ミモザの柩", "platforms": ["ニコニコ漫画"],
     "urls": ["https://manga.nicovideo.jp/comic/54233"]},
    {"title": "打撃系鬼っ娘が征く配信道!@COMIC", "platforms": ["コロナEX", "ニコニコ漫画"],
     "urls": ["https://manga.nicovideo.jp/comic/49417",
              "https://to-corona-ex.com/comics/20000000049417"]},
    # data/source/nicovideo/resolved.yaml states an id and no address at all.
    {"title": "ひとりぼっちの○○生活", "comic_id": 13928},
    # A candidate on a platform this pass does not capture. It names no ニコニコ address, so it is
    # not this pass's target and must not be counted as one.
    {"title": "てぇてぇ二人", "platforms": ["となりのヤングジャンプ"],
     "urls": ["https://tonarinoyj.jp/episode/14079602755360143718"]},
]
# The two ニコニコ captures. A work read by either has been read.
NICO_UPDATES = [{"work_title": "打撃系鬼っ娘が征く配信道!@COMIC", "comic_id": "49417",
                 "url": "https://manga.nicovideo.jp/comic/49417"}]
NICO_CHAPTERS = [{"work_title": "ひとりぼっちの○○生活", "platform_code": "13928",
                  "url": "https://manga.nicovideo.jp/comic/13928"}]


def main(s):
    # ── the identifier, which is what the whole measure turns on ────────────────────────────────
    s.eq(capturegap.ident({"url": "https://comic-fuz.com/series/2389"}, FUZ), "2389",
         "the /series/ spelling states work 2389")
    s.eq(capturegap.ident({"url": "https://comic-fuz.com/manga/2389"}, FUZ), "2389",
         "and so does the /manga/ spelling, which is the agreement the adapter lost")
    s.eq(capturegap.ident({"url": "https://to-corona-ex.com/comics/20000000049417"}, NICO), None,
         "an address on another host states no identifier for this platform")
    s.eq(capturegap.ident({"comic_id": 13928}, NICO, ("comic_id",)), "13928",
         "a bare id is read as a string, so 13928 and '13928' are one work")
    s.eq(capturegap.ident({"code": "KC_000031_S"}, KADO, ("code", "platform_code")),
         "KC_000031_S", "a カドコミ code is the identifier where no address is stated")
    # A code field belonging to some other host must not be adopted by a pass that declares none.
    s.eq(capturegap.ident({"code": "KC_000031_S"}, FUZ), None,
         "a pass with no code fields reads addresses only")

    # ── the join ────────────────────────────────────────────────────────────────────────────────
    fuz = {"platform": "COMIC FUZ",
           "targets": capturegap.idents(FUZ_TARGETS, FUZ),
           "captured": set(capturegap.idents(FUZ_CAPTURE, FUZ)),
           "accounted": set()}
    gone = capturegap.missing([fuz])
    s.eq([r["ident"] for r in gone], ["2389"],
         "the confirmed work with no capture row is reported")
    s.eq([r["title"] for r in gone], ["ぬるめた"], "and it is named, not just counted")

    # THE COUNTER-CASE. Rewriting ぬるめた's address to the spelling the capture uses must change
    # nothing, because the identifier was never the difference.
    same = dict(fuz, targets=capturegap.idents(
        [dict(r, url=r["url"].replace("/series/", "/manga/")) for r in FUZ_TARGETS], FUZ))
    s.eq([r["ident"] for r in capturegap.missing([same])], ["2389"],
         "the same work is missing under either spelling of its address")
    # And a capture that holds the work under the OTHER spelling is a capture that holds it.
    held = dict(fuz, captured=set(capturegap.idents(
        [{"url": "https://comic-fuz.com/series/2389"}] + FUZ_CAPTURE, FUZ)))
    s.eq(capturegap.missing([held]), [],
         "a row spelled /series/ in the capture still answers for /manga/")

    nico = {"platform": "ニコニコ漫画",
            "targets": capturegap.idents(NICO_TARGETS, NICO, ("comic_id", "platform_code")),
            "captured": set(capturegap.idents(NICO_UPDATES, NICO, ("comic_id",))
                            | capturegap.idents(NICO_CHAPTERS, NICO, ("platform_code",))),
            "accounted": set()}
    s.eq(sorted(nico["targets"]), ["13928", "49417", "54233"],
         "a candidate naming no address on this platform is not one of its targets")
    s.eq([r["ident"] for r in capturegap.missing([nico])], ["54233"],
         "a work either capture holds is held; only ミモザの柩 has no row anywhere")

    # ── a register accounts for a target; it never silences one ─────────────────────────────────
    withheld = dict(fuz, accounted={"2389"})
    s.eq(capturegap.missing([withheld]), [],
         "a target the pass fetched and refused on content grounds is accounted for")
    s.eq(len(capturegap.missing([fuz, nico])), 2,
         "passes are counted together, one entry per missed target")

    # ── reading the files ───────────────────────────────────────────────────────────────────────
    s.eq(capturegap.rows({"candidates": [{"title": "a"}], "works_missing": [{"title": "b"}]},
                         ("candidates", "works_missing")),
         [{"title": "a"}, {"title": "b"}],
         "a coverage file states its rows under two different keys and both are read")
    s.eq(capturegap.rows({}, ("works",)), [],
         "a file that is not there contributes nothing and does not raise")
    s.eq(capturegap.rows({"works": {"k": {"title": "a"}}}, ("works",)), [{"title": "a"}],
         "a capture keyed by identifier is read as its values")

    # THE MEASURE MUST NOT BE SATISFIED BY THE CAPTURE ALONE (§14b). Every identifier here comes
    # from the target list, so a pass that wrote nothing at all reports every target missing rather
    # than reporting nothing to check.
    empty = dict(fuz, captured=set())
    s.eq(len(capturegap.missing([empty])), 3,
         "a capture that wrote no rows reports every target it was given")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "capturegap"))
