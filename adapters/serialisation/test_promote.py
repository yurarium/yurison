#!/usr/bin/env python3
"""promote.py: which confirmations become joins, and which addresses a platform still needs."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import promote as P                                                            # noqa: E402
import testkit                                                                 # noqa: E402

DOC = {"confirmed": [
    {"id": "w01472", "verdict": "agreed", "title": "運命のヤマダダダダダダダダダダ",
     "author": "おにぎりパクパク", "url": "https://manga.nicovideo.jp/comic/72312",
     "evidence": "publisher 芳文社 is named on the platform page"},
    {"id": "w01472", "verdict": "agreed", "title": "運命のヤマダダダダダダダダダダ",
     "author": "おにぎりパクパク", "url": "https://comic-walker.com/detail/KC_000031_S",
     "evidence": "creator agrees"},
    {"id": "w01183", "verdict": "differs", "title": "サラダボウル", "author": "きぃやん",
     "url": "https://manga.nicovideo.jp/comic/51635", "evidence": "the page credits somebody else"},
    {"id": "w01190", "verdict": "undecided", "title": "ぼくは、百合な",
     "author": "だれか", "url": "https://comic.pixiv.net/works/1", "evidence": "no author"},
]}


def main(s):
    got = P.agreed(DOC)
    s.eq(sorted(got), ["w01472"], "only an agreed lead becomes a join")
    s.eq(len(got["w01472"]), 2,
         "and every agreeing address is kept, because the row's own URL is chosen downstream")
    s.check("w01183" not in got, "a refused lead is not a join")
    s.check("w01190" not in got, "and neither is an undecided one")
    s.eq(P.agreed({}), {}, "an empty confirmation file yields no joins")

    flat = [r for rs in got.values() for r in rs]
    s.eq(P.seed_rows(flat, P.NICO, set()), [("72312", "運命のヤマダダダダダダダダダダ", "おにぎりパクパク")],
         "the ニコニコ address becomes a seed with its work id")
    s.eq(P.seed_rows(flat, P.KADOKOMI, set())[0][0], "KC_000031_S",
         "and the カドコミ address becomes its code")

    # THE CARRY-OVER RULE. Both seed files hold rows put there by earlier work, and a pass that
    # re-offered them would append a duplicate on every run.
    s.eq(P.seed_rows(flat, P.NICO, {"72312"}), [],
         "an address the adapter already knows is not offered again")

    twice = flat + flat
    s.eq(len(P.seed_rows(twice, P.NICO, set())), 1,
         "and one address named twice is one seed")

    s.eq(P.seed_rows(flat, P.NICO, set())[0][2], "おにぎりパクパク",
         "the seed carries the author the platform stated, which is what a later run matches on")

    # FUZ's adapter reads a whole address rather than a bare id, so its pattern keeps one.
    fuzrow = [{"id": "w1", "verdict": "agreed", "title": "スローループ", "author": "うちのまいこ",
               "url": "https://comic-fuz.com/manga/1541", "evidence": "imprint agrees"}]
    s.eq(P.seed_rows(fuzrow, P.FUZ, set())[0][0], "comic-fuz.com/manga/1541",
         "a FUZ seed is its address")
    s.eq(P.seed_rows(fuzrow, P.NICO, set()), [], "and it is not offered to ニコニコ")


if __name__ == "__main__":
    sys.exit(testkit.run(main, pathlib.Path(__file__).name))
