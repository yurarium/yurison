#!/usr/bin/env python3
"""publishers.py: an English name for a publisher and an imprint, out of data.

COVERS = ['adapters/names/publishers.py']

The cataloguing around a publisher name is what makes this hard, and it is the same notation the
interface strips for display. Getting the two out of step is invisible: a key that does not match
what the interface asks for renders as Japanese, which is also what an unnamed publisher does.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit
from adapters.names import publishers as P


def main(s):
    # ── the cataloguing comes off, and only the cataloguing ────────────────────────────────────
    s.eq(P.publisher_of("[頒布]講談社"), "講談社", "a distributor marker is not part of the name")
    s.eq(P.publisher_of("講談社 (発売)"), "講談社", "and neither is a release note")
    s.eq(P.publisher_of("[頒布]KADOKAWA (発売)"), "KADOKAWA", "both at once")
    s.eq(P.publisher_of("一迅社"), "一迅社", "a plain name is left alone")

    # ── one imprint, however the record spells it ──────────────────────────────────────────────
    #
    # MADB catalogues 百合姫 at least six ways. Six spellings in one list read as six imprints,
    # which is the opposite of what an imprint is for.
    for spelling in ("コミック百合姫", "百合姫コミックス", "IDコミックス. Yurihime comics = コミック百合姫",
                     "IDコミックス／Yuri-hime comics", "IDコミックス　／　Yurihime comics"):
        s.eq(P.imprint_of(spelling), "コミック百合姫", f"one imprint under {spelling[:24]}")
    s.eq(P.imprint_of("IDコミックス"), "IDコミックス",
         "the umbrella line stands alone when it is all the record says")
    s.eq(P.imprint_of("まんがタイムKRコミックス"), "まんがタイムKRコミックス",
         "an imprint with no alias is itself")

    # THE RULE THAT WAS TRIED AND REJECTED, pinned so nobody re-derives it. `IDコミックス／Yuri-hime
    # comics` is one imprint written twice, once in each script, so reading the Latin half off the
    # record would name a third of the imprint rows for free. `GP-KIDS/高菜しんの` has the same
    # shape and is an imprint beside a person, so the rule publishes one party's name as another's.
    s.eq(P.imprint_of("GP-KIDS/高菜しんの"), "高菜しんの",
         "a record naming an imprint and a person is not a name written twice")

    # ── what reaches the interface ─────────────────────────────────────────────────────────────
    names = {"[発売]講談社": {"kind": "publisher", "shown": "講談社", "volumes": 102},
             "IDコミックス　／　Yuri-hime comics": {"kind": "imprint", "shown": "コミック百合姫",
                                                    "volumes": 120},
             "芳文社": {"kind": "publisher", "shown": "芳文社", "volumes": 187}}
    store = {"講談社": {"en": "Kodansha", "basis": "official-jp", "source": "kodansha.co.jp"},
             "コミック百合姫": {"en": "Comic Yuri Hime", "basis": "official-jp",
                                "source": "ichijinsha.co.jp"}}
    got = P.render(store, names)

    # KEYED BOTH WAYS ON PURPOSE. The interface normalises in the browser and this normalises in
    # Python, so the two implementations can drift; a raw key means a drift costs a lookup that the
    # other key still answers rather than a publisher silently rendering as Japanese.
    s.eq(got["講談社"]["en"], "Kodansha", "a curated name reaches the normalised key")
    s.eq(got["[発売]講談社"]["en"], "Kodansha", "and the raw catalogued string")
    s.eq(got["講談社"]["basis"], "official-jp", "with the basis it was recorded under")
    s.eq(got["コミック百合姫"]["en"], "Comic Yuri Hime",
         "an imprint is found under the name its eight spellings collapse to")
    s.eq(got["IDコミックス　／　Yuri-hime comics"]["en"], "Comic Yuri Hime",
         "and under the spelling the record actually used")
    s.check("芳文社" not in got, "a name with no English is absent rather than romanised")

    # KATAKANA IS NOT ROMANISED HERE, and that is the point. ナンバーナイン is a company called
    # No9; syllable-by-syllable it comes out Nanbānain, which transliterates a transliteration.
    kana = {"ナンバーナイン": {"kind": "publisher", "shown": "ナンバーナイン", "volumes": 540}}
    s.check("ナンバーナイン" not in P.render({}, kana),
            "a katakana name with no source stays Japanese rather than being romanised")

    # ── the queue ──────────────────────────────────────────────────────────────────────────────
    todo = P.unnamed(got, names)
    s.eq([n for _v, n, _k in todo], ["芳文社"], "only the unnamed are queued")
    s.eq(todo[0][0], 187, "counted by volumes, so the queue opens on what a reader sees most")

    three = {"講談社": {"kind": "publisher", "shown": "講談社", "volumes": 20},
             "[発売]講談社": {"kind": "publisher", "shown": "講談社", "volumes": 102},
             "[頒布]講談社": {"kind": "publisher", "shown": "講談社", "volumes": 80}}
    s.eq(P.unnamed({}, three), [(202, "講談社", "publisher")],
         "one publisher spelled three ways is one entry in the queue, not three")

    # ── WHICH FIELDS HOLD A NAME A READER SEES ─────────────────────────────────────────────────
    #
    # The queue here and `publishers with no English` in check.py both walk a print row, and both
    # walked their own list of fields until one of them gained `distributor` and the other did not.
    # One list now, and this pins what it holds so a field added to the row reaches both or
    # neither (STANDING-INSTRUCTIONS §3).
    s.eq([f for f, _n in P.NAME_FIELDS], ["publisher", "distributor", "imprint"],
         "the publisher, the distributor and the imprint are all shown, so all are queued")
    s.check(all(n is P.publisher_of for f, n in P.NAME_FIELDS if f != "imprint"),
            "a distributor is a publisher's name in another seat and normalises the same way")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.publishers"))
