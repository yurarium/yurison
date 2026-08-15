#!/usr/bin/env python3
"""analyser_division.py: a space an analyser invented comes out unless the surface accounts for it."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))

import testkit  # noqa: E402
from facts.division import analyser_division as d  # noqa: E402

COVERS = ["adapters/facts/division/analyser_division.py"]


def main(s):
    # THE SIX NAMES THIS WAS REPORTED ON, live on the site the day it was written. Every one of them
    # is a real person, and each shows a different way for the arithmetic to reach an offset that
    # is not a division of anybody's name.
    s.eq(d.retire("のぴやか梢", "ノ ピ ヤ カ コズエ"), "ノピヤカ コズエ",
         "one token per kana goes; the offset the kana run establishes stays")
    s.eq(d.retire("まゃ～吾郎", "マ ャ ～ ゴロウ"), "マャ～ゴロウ",
         "a wave dash is not an element of a name, so no space sits beside it")
    s.eq(d.retire("むつをむつ 蒼井ゆん", "ムツ ヲ ムツ　　アオイ ユン"), "ムツヲムツ アオイ ユン",
         "the byline's own space and the trailing kana run survive; the three inside do not")
    s.eq(d.retire("R-指定", "R - シテイ"), "R-シテイ",
         "a Latin letter reads as itself and still divides nothing")
    s.eq(d.retire("○山浩平", "○ ヤマ コウヘイ"), "○ヤマコウヘイ",
         "and neither does a symbol, whatever the analyser made of the kanji after it")
    s.eq(d.retire("あんじんねこ@創作", "アンジン ネコ @ ソウサク"), "アンジンネコ@ソウサク",
         "an @ between a handle and a tag is not a word break")

    # WHAT MUST SURVIVE. The common shape by a distance: a kanji surname meeting a given name
    # written in kana, where the kana run reads itself and the offset is arithmetic.
    s.eq(d.retire("三好ミオ", "ミヨシ ミオ"), "ミヨシ ミオ",
         "a kana given name establishes where the reading breaks")
    s.eq(d.retire("あおい華葉", "アオイ カバ"), "アオイ カバ",
         "and so does a kana element at the front")
    s.eq(d.retire("三松　真由美", "ミマツ 　 マユミ"), "ミマツ マユミ",
         "a byline that writes its own space keeps it, with no arithmetic needed")
    s.eq(d.retire("4ka エンピツ", "4 ka　エンピツ"), "4ka エンピツ",
         "the author's space stands even where the parts on either side of it do not")

    # THE COUNTER-CASE. 九羊ボン is filed クラムボン by the media-arts catalogue, one word and a pun
    # on it, and the arithmetic would happily cut it in half. It is never asked to: this module
    # removes spaces and adds none, so a reading that arrives whole leaves whole.
    s.eq(d.retire("九羊ボン", "クラムボン"), "クラムボン",
         "a name with no division in it comes back with none")
    s.eq(d.retire("冬木先輩", "フユキセンパイ"), "フユキセンパイ",
         "the name test_kana.py pins is not touched either")
    # AND THE GUARD THAT KEEPS IT OFF A SOURCED READING. `retire` knows nothing about where a
    # reading came from, so pointed at いがらしゆみこ it would take out the division NDL's author
    # heading states. `asks` is the whole of what stops that, which is why it is pinned here beside
    # the damage it prevents rather than only in the section on which records are asked about.
    s.eq(d.retire("いがらしゆみこ", "イガラシ ユミコ"), "イガラシユミコ",
         "the arithmetic cannot see a stated division and would take it out")
    s.check(not d.asks({"reading": "イガラシ ユミコ", "reading_basis": "surface"}),
            "so the record is never offered to it")

    # THE OFFSETS A SURFACE ACCOUNTS FOR, and the two rules that narrow them.
    s.eq(sorted(d.established("のぴやか梢", "ノピヤカコズエ")), [4],
         "a leading kana run establishes one offset and the kanji after it none")
    s.eq(sorted(d.established("三好ミオ", "ミヨシミオ")), [3],
         "and a trailing one is counted from the other end")
    s.eq(sorted(d.established("○山浩平", "○ヤマコウヘイ")), [],
         "a surface with no kana in it accounts for nothing")
    s.eq(d.retire("お久しぶり", "オ ヒサシブリ"), "オヒサシブリ",
         "one mora is a prefix, not half of a name")
    s.eq(d.retire("コミックnishi", "コミック nishi"), "コミック nishi",
         "a Latin handle after a kana run is an element and keeps its space")
    s.eq(d.retire("ＲＤーＳｏｕｎｄｓ", "RDー Sounds"), "RDーSounds",
         "and a prolongation mark opens no part, whatever follows it")

    # A READING THAT HAS BEEN THROUGH THIS ALREADY does not change again, which is what lets the
    # build run it on every pass.
    once = d.retire("のぴやか梢", "ノ ピ ヤ カ コズエ")
    s.eq(d.retire("のぴやか梢", once), once, "the correction is idempotent")

    # WHICH RECORDS ARE ASKED ABOUT.
    s.check(d.asks({"reading": "ノ ピ ヤ カ コズエ", "reading_basis": "analyser"}),
            "an analyser's division is the question")
    s.check(not d.asks({"reading": "ノピヤカコズエ", "reading_basis": "analyser"}),
            "a reading with no division in it is not")
    s.check(not d.asks({"reading": "タイヨウ マリイ", "reading_basis": "stated"}),
            "a division a source states is not this module's business")
    s.check(not d.asks({"reading": "カシ ミチヨ", "reading_basis": "back-converted"}),
            "and a romanisation read backwards is somebody's claim, counted and not corrected")
    s.check(not d.asks({"reading": "オトメ ☆ モウソウゾク", "reading_basis": "analyser",
                        "entity": "circle"}),
            "a credit that is not a person is made of ordinary words")
    # THE PASS THAT RUNS AFTER THIS ONE. `boundary.fill` carried 赤川左岸's division from 赤河左岸,
    # the same artist filed under another spelling with a stated reading, and left the analyser's
    # reading in place. Without this the two passes take turns on every build.
    s.check(not d.asks({"reading": "アカガワ サガン", "reading_basis": "analyser",
                        "reading_boundary": "赤河左岸"}),
            "a division another record states outranks the arithmetic and is left alone")
    s.check(d.asks({"reading": "ノ ピ ヤ カ コズエ", "reading_basis": "analyser",
                    "reading_boundary": d.SURFACE}),
            "and this module's own citation does not stop it looking again")

    # THE WHOLE STORE, which is what build.py calls.
    names = {
        "のぴやか梢": {"reading": "ノ ピ ヤ カ コズエ", "reading_basis": "analyser"},
        "三好ミオ": {"reading": "ミヨシ ミオ", "reading_basis": "analyser"},
        "太陽まりい": {"reading": "タイヨウ マリイ", "reading_basis": "stated"},
    }
    changed, kept = d.retire_all(names)
    s.eq(changed, {"のぴやか梢": ("ノ ピ ヤ カ コズエ", "ノピヤカ コズエ")},
         "the invented division is corrected and reported with what it was")
    s.eq(kept, ["三好ミオ"], "the arithmetic one is kept")
    s.eq(names["三好ミオ"]["reading_boundary"], d.SURFACE,
         "and says the surface is where it came from, so the gate can read it")
    s.eq(names["のぴやか梢"]["reading_boundary"], d.SURFACE,
         "the space that survived a correction cites the surface too, being all that is left")
    s.eq(names["太陽まりい"]["reading"], "タイヨウ マリイ", "a stated reading is untouched")
    s.eq(d.retire_all(names)[0], {}, "a second run finds nothing left to correct")

    # THE STORE ON DISK.
    import tempfile
    import yaml
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / "authors.yaml"
        p.write_text(yaml.safe_dump({"names": {
            "R-指定": {"reading": "R - シテイ", "reading_basis": "analyser"}}},
            allow_unicode=True))
        changed, _kept = d.retire_store(p)
        s.eq(changed, {"R-指定": ("R - シテイ", "R-シテイ")}, "the store on disk is corrected")
        back = yaml.safe_load(p.read_text())["names"]["R-指定"]
        s.eq(back["reading"], "R-シテイ", "and the file holds the corrected reading")
        s.check("reading_boundary" not in back,
                "a name left whole cites nothing, because it divides nowhere")
        stamp = p.stat().st_mtime_ns
        d.retire_store(p)
        s.eq(p.stat().st_mtime_ns, stamp, "a run with nothing to do leaves the file alone")
    s.eq(d.retire_store(pathlib.Path(tmp) / "gone.yaml"), ({}, []),
         "no store is the documented fallback, not an error")

    # THE DOOR build.py USES, WHICH IS NOT THE DOOR THIS FILE USES (§14b). Everything above reaches
    # `facts.division.analyser_division`; the build reaches `facts.division`, whose `__getattr__`
    # forwards to `boundary` and `checks` and to nothing else. `retire` and `asks` were written out
    # by hand there and `retire_store` was missed, so the build raised AttributeError inside the
    # naming block, printed `automatic reading pass skipped`, and every test here passed.
    from facts import division as entry
    for name in ("retire", "asks", "retire_store"):
        s.check(hasattr(entry, name), f"the entry point answers {name}, which build.py calls on it")


    a_run_that_corrected_nothing_still_writes(s)


def a_run_that_corrected_nothing_still_writes(s):
    """The CLI wrote only when it had shortened a reading, and threw its marks away otherwise.

    `retire_all` sets `reading_boundary` on every division the surface accounts for, whether or not
    it also took a space out. `main` asked for `changed` before writing, so a run reporting
    "136 accounted for by the surface, 0 corrected" saved none of them. 安藤いも arrived divided
    アンドウ イモ, was kept by this pass the same day, and failed `a division cites its source`.
    """
    import subprocess
    import sys as _sys
    import tempfile

    import yaml as _y

    root = pathlib.Path(__file__).resolve().parents[3]
    mod = root / "adapters" / "facts" / "division" / "analyser_division.py"
    rec = {"reading": "アンドウ イモ", "reading_basis": "analyser",
           "reading_source_kind": "analyser"}
    with tempfile.TemporaryDirectory() as d:
        store = pathlib.Path(d) / "authors.yaml"
        store.write_text(_y.safe_dump({"names": {"安藤いも": dict(rec)}}, allow_unicode=True))
        r = subprocess.run([_sys.executable, str(mod), "--store", str(store), "--apply"],
                           capture_output=True, text=True, cwd=str(root), timeout=120)
        s.eq(r.returncode, 0, "the pass runs against a store it is pointed at")
        s.check("0 corrected" in r.stdout, "and corrects nothing here, which is the case at issue")
        got = (_y.safe_load(store.read_text()) or {})["names"]["安藤いも"]
        s.eq(got.get("reading_boundary"), "the kana in its own surface",
             "a division the surface accounts for is marked even when nothing was shortened")

        # AND A SECOND RUN LEAVES THE FILE ALONE, which is what comparing the text buys.
        before = store.read_text()
        subprocess.run([_sys.executable, str(mod), "--store", str(store), "--apply"],
                       capture_output=True, text=True, cwd=str(root), timeout=120)
        s.eq(store.read_text(), before, "and a run with nothing left to say does not rewrite it")


    # ── AN INTERPUNCT SURVIVES `retire`, WHICH IS THE SECOND WRITER OF THAT RULE ──────────────
    #
    # `boundary.from_surface` was fixed for this and `retire` was not, so the reading that no
    # longer spelled its own name came back on the next run carrying `reading_boundary: the kana
    # in its own surface`, which is written here. Three removals and two guards elsewhere did not
    # stop it, because none of them was the producer.
    from facts.division import analyser_division as _ad
    s.eq(_ad.retire("スタジオクロマト・スタジオコロリド",
                                  "スタジオクロマト スタジオコロリド"),
         "スタジオクロマト・スタジオコロリド",
         "a division the surface writes with an interpunct keeps the interpunct")
    s.eq(_ad.retire("かしい葵", "カシイ アオイ"), "カシイ アオイ",
         "and one the surface does not write with one still gets a space")
    s.eq(_ad.separators("ア・イ", "アイ"), {1: "・"},
         "the separator is reported at the offset it establishes")
    s.eq(_ad.separators("ア イ", "アイ"), {},
         "and a plain space names no character to keep")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
