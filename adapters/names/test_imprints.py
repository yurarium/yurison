#!/usr/bin/env python3
"""imprints.py: which imprint line a catalogued imprint string names.

COVERS = ['adapters/names/imprints.py']

MOST OF WHAT IS PINNED HERE IS A COUNTER-CASE, because the fault this module can commit is folding
two lines into one and no count can see it. 一迅社 runs 10 lines under one umbrella and a substring
rule for the yuri line eats four of them; a pattern written for this investigation reached KADOKAWA's
BRIDGE COMICS the same way. Each of those is asserted to land somewhere else, and the assertions run
against the shipped registry rather than a fixture so a curating round that breaks one of them fails
here rather than on a page.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit
from adapters.names import imprints as I

REGISTRY = pathlib.Path(__file__).resolve().parents[2] / "data" / "names" / "imprints.yaml"


def name_of(publisher, raw, idx):
    line = I.resolve(publisher, raw, idx)
    return (line or {}).get("name")


def main(s):
    # ── the fold, which is what lets one entry cover many spellings ─────────────────────────────
    s.eq(I.fold("ＦＵＺコミックス"), I.fold("FUZコミックス"),
         "full-width Latin in a Japanese name is the source's typesetting, and NFKC settles it")
    s.eq(I.fold("MFC　キューンシリーズ"), I.fold("MFCキューンシリーズ"),
         "an ideographic space a transcriber inserted is not part of the name")
    s.eq(I.fold("Yuri-hime comics"), I.fold("YURIHIME COMICS"),
         "the hyphen the logotype lost in 2015, and case, fold onto one key")

    # AND WHAT THE FOLD MUST NOT REACH. Dropping the hyphen is safe only if it does not collapse a
    # suffix that distinguishes a line, and クロスフォリオ出版 is the house where it would: the
    # difference between its yuri line and its adult line is three letters after a hyphen.
    s.ne(I.fold("BLIC-GL"), I.fold("BLIC"), "a suffix that makes a line its own line survives")
    s.ne(I.fold("BLIC-GL"), I.fold("BLIC-ERO"),
         "and the two genre suffixes stay apart, which is the whole point of naming them")
    s.ne(I.fold("AOKISHI COMICS"), I.fold("AOKISHI COMIX"),
         "COMICS and COMIX are two transcriptions and need two entries, not a cleverer fold")

    lines = I.load(REGISTRY)
    s.check(lines, "the registry loads")
    idx = I.index(lines)

    # ── ONE LINE, HOWEVER THE RECORD SPELLS IT ─────────────────────────────────────────────────
    #
    # Every string below is in the corpus today. The compound forms cost no registry entry: they are
    # split on the cataloguer's separators and matched on the most specific segment, so ／ then ". "
    # then the ISBD "=" all arrive at the same line.
    for spelling in ("百合姫コミックス", "Yuri-hime comics", "Yurihime comics", "YURIHIME COMICS",
                     "Yuri-Hime COMICS", "YH comics", "yh COMICS", "コミック百合姫",
                     "IDコミックス　／　Yuri-hime comics", "IDコミックス. Yurihime comics",
                     "IDコミックス. コミック百合姫", "IDコミックス. YH comics",
                     "IDコミックス. Yurihime comics = コミック百合姫",
                     "IDコミックス　／　Yuri-hime comics anthology series"):
        s.eq(name_of("一迅社", spelling, idx), "百合姫コミックス",
             f"one line under {spelling}")

    # THE NAME IS THE BOOK LINE'S AND NOT THE MAGAZINE'S. コミック百合姫 is the magazine; the
    # publisher's own page for it calls the collected volumes 百合姫コミックス, and MADB writes the
    # magazine's name into the series field from 2023. The interface used to show the magazine.
    s.ne(name_of("一迅社", "コミック百合姫", idx), "コミック百合姫",
         "the magazine's name is a recorded spelling of the line and is not what the line is called")

    # ── THE COUNTER-CASES. A loose match eats a real imprint ────────────────────────────────────
    #
    # These are 一迅社's other lines and none of them is a yuri line. ZERO-SUMコミックス holds 10
    # works of this corpus, admitted on a retailer's shelf.
    for spelling, want in (("ZERO-SUMコミックス", "ZERO-SUMコミックス"),
                           ("Zero-sum comics", "ZERO-SUMコミックス"),
                           ("Howl comics", "HOWLコミックス"),
                           ("IDコミックス　／　DNAメディアコミックス", "DNAメディアコミックス"),
                           ("4コマkingsぱれっとcomics", "4コマKINGSぱれっとコミックス"),
                           ("IDコミックス　／　4コマkingsぱれっとcomics", "4コマKINGSぱれっとコミックス"),
                           ("LAKE", "comic LAKE"),
                           ("百合姫books", "百合姫books")):
        s.eq(name_of("一迅社", spelling, idx), want, f"{spelling} is its own line")

    # THE UMBRELLA IS NOT THE YURI LINE UNDER ANOTHER NAME, which is the merge that looks obviously
    # right and is not. Every one of the 47 rows carrying IDコミックス alone entered on a retailer's
    # shelf and carries marketing_label none, so folding it in would attach a publisher-side yuri
    # line to works the publisher labelled nothing.
    s.eq(name_of("一迅社", "IDコミックス", idx), "IDコミックス",
         "the umbrella stands alone where it is all the record says")

    # AND THE PARENT IS RECORDED BESIDE THE LINE INSTEAD OF BEING THROWN AWAY, because ISBD's ". "
    # states something true: this line sits inside that one.
    s.eq((I.resolve("一迅社", "IDコミックス. Yurihime comics", idx) or {}).get("parent"),
         "IDコミックス", "a sub-line names the umbrella it sits in")

    # ── THE SAME QUESTION GOING THE OTHER WAY, and only the publisher can settle it ─────────────
    #
    # KIRARA MENU is まんがタイムKRコミックス's own running number in the 奥付 and 芳文社's label
    # index gives it no page, so `Manga time KR comics. Kirara menu` is the parent line and not a
    # sub-line. つぼみシリーズ has its own label page, so it is its own line. Two ISBD sub-series in
    # one house, resolved in opposite directions on the publisher's own evidence.
    for spelling in ("まんがタイムKRコミックス", "Manga time KR comics", "Kirara menu",
                     "Manga time KR comics. Kirara menu", "Manga time KR comics　／　Kirara menu"):
        s.eq(name_of("芳文社", spelling, idx), "まんがタイムKRコミックス",
             f"きららMENU is this line's numbering: {spelling}")
    for spelling in ("Manga time KR comics　／　Tsubomi series", "まんがタイムＫＲコミックスつぼみシリーズ"):
        s.eq(name_of("芳文社", spelling, idx), "まんがタイムKRコミックスつぼみシリーズ",
             f"つぼみシリーズ is a line of its own: {spelling}")
    s.eq(name_of("芳文社", "Manga time comis", idx), "まんがタイムコミックス",
         "a cataloguer's typo on one record still reaches the line")

    # ── A LINE MAY NOT BE REACHED FROM ANOTHER HOUSE ────────────────────────────────────────────
    #
    # The false positive that opened this work. BRIDGE COMICS is KADOKAWA's and has nothing to do
    # with 百合姫; a pattern looking for the one found the other.
    s.eq(name_of("KADOKAWA", "ＢＲＩＤＧＥ　ＣＯＭＩＣＳ", idx), "BRIDGE COMICS",
         "the full-width spelling is the same KADOKAWA line")
    s.eq(name_of("一迅社", "BRIDGE COMICS", idx), None,
         "and 一迅社 does not run it, so 一迅社 cannot reach it")
    s.eq(name_of("KADOKAWA", "百合姫コミックス", idx), None,
         "matching is scoped by publisher in both directions")
    s.eq(name_of("KADOKAWA", "MFコミックス. フラッパーシリーズ", idx),
         "MFコミックス フラッパーシリーズ", "KADOKAWA's own sub-series fold the same way")
    s.eq(name_of("KADOKAWA", "角川コミックス・エース", idx), "角川コミックス・エース",
         "a line under the current company name")
    s.eq(name_of("角川書店", "角川コミックス・エース", idx), "角川コミックス・エース",
         "and under the name the house had when the older records were written")

    # A LINE KADOKAWA ITSELF LISTS TWICE IS TWO LINES. Its label index carries アライブ＋ and
    # MFコミックス アライブシリーズ as separate entries, so the ＋ is not a restyling.
    s.eq(name_of("KADOKAWA", "アライブ＋", idx), "アライブ＋", "the ＋ line is its own")
    s.ne(name_of("KADOKAWA", "MFコミックス　アライブシリーズ", idx), "アライブ＋",
         "and the series without it is not folded into it")

    # ── ABSENCE IS A STATE ─────────────────────────────────────────────────────────────────────
    #
    # A string the registry does not answer for gets no line. That is what makes `imprint strings
    # that reach no line` able to count anything at all: a matcher inventing a line per string would
    # reach every string and the count would read zero for ever (STANDING-INSTRUCTIONS §14b).
    s.eq(name_of("クロスフォリオ出版", "ガレットワークス", idx), None,
         "a company sitting in the imprint field is left alone and counted")
    s.eq(name_of("芳文社", "まんがタイムきらら", idx), None,
         "and so is a magazine name")
    s.eq(name_of("一迅社", "", idx), None, "an empty field names no line")
    s.eq(name_of("", "百合姫コミックス", idx), None,
         "and a row naming no publisher cannot be scoped, so it resolves to nothing")

    # ── THE CENSUS AND THE SHIPPED MAP ─────────────────────────────────────────────────────────
    rows = [
        {"print": [{"work_id": "a", "publisher": "一迅社", "imprint": "IDコミックス　／　Yuri-hime comics",
                    "first": "2006-02", "last": "2009-01"},
                   {"work_id": "b", "publisher": "一迅社", "imprint": "IDコミックス. コミック百合姫",
                    "first": "2023-05", "last": "2026-03"},
                   {"work_id": "c", "publisher": "一迅社", "imprint": "ZERO-SUMコミックス",
                    "first": "2018-04", "last": None},
                   {"work_id": "d", "publisher": "[頒布]講談社", "imprint": "Yurihime comics",
                    "first": "2019-01", "last": None}]},
    ]
    by_line, unresolved = I.census(rows, lines)
    s.eq(sorted(by_line), ["yurihime-comics", "zero-sum-comics"],
         "two lines out of three resolved spellings")
    s.eq(by_line["yurihime-comics"]["rows"], 2, "both 百合姫 spellings count to the one line")

    # THE SPELLINGS CARRY THEIR OWN YEARS, which is what a reader looking at a 2008 volume needs:
    # the line is 百合姫コミックス and that volume says Yuri-hime comics.
    spellings = by_line["yurihime-comics"]["spellings"]
    s.eq(spellings["IDコミックス　／　Yuri-hime comics"]["years"], ["2006", "2009"],
         "a spelling's span is measured off the rows carrying it")
    s.eq(spellings["IDコミックス. コミック百合姫"]["years"], ["2023", "2026"],
         "and the later spelling covers later books")

    # A DISTRIBUTOR IS NOT THE PUBLISHER, and the row above is catalogued the way MADB writes one.
    # `publisher_of` takes the bracket off, so this row is scoped to 講談社, which runs no line here.
    s.eq(sorted(u[1] for u in unresolved), ["Yurihime comics"],
         "a 百合姫 spelling under another house resolves to nothing instead of to the line")

    shipped = I.shipped(rows, lines)
    s.eq(shipped["ZERO-SUMコミックス"]["name"], "ZERO-SUMコミックス", "the map answers by raw string")
    s.eq(shipped[I.fold("IDコミックス. コミック百合姫")]["name"], "百合姫コミックス",
         "and by the fold, so a drift in the browser's stripping costs a lookup the other key holds")
    s.check("Yurihime comics" not in shipped,
            "a string that reached no line is absent from the map, which is what the budget counts")
    s.check(all("HOWLコミックス" != v["name"] for v in shipped.values()),
            "and a line no row carries is not shipped, so the map states only what the corpus holds")

    # ── THE FOUR HOUSES ARE COMPLETE, measured against the corpus rather than asserted ──────────
    #
    # A curating round that drops a spelling would leave these houses partly unplaced, and the
    # budget in check.py counts the whole corpus so a handful going missing hides inside it.
    build = pathlib.Path(__file__).resolve().parents[2] / "data" / "build" / "series.json"
    if build.exists():
        corpus = I.series_rows(build.parent)
        _held, left = I.census(corpus, lines)
        for house, want in (("一迅社", 1), ("芳文社", 1), ("クロスフォリオ出版", 1), ("KADOKAWA", 6)):
            got = sorted(u["raw"] for u in left.values() if u["publisher"] == house)
            s.eq(len(got), want, f"{house} has {want} imprint string(s) left to place: {got}")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.imprints"))
