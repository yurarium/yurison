#!/usr/bin/env python3
"""Pass 1 — the names whose reading is not a question (NAMES-PLAN §4).

A name written in kana IS its own reading. なもり is read Namori because that is what the kana say;
there is no lookup, no source to cite, and no way for it to be wrong. So this pass costs nothing,
resolves exactly, and — the part worth being precise about — what it records is the READING, not a
romanisation.

That distinction is §8.1 and it is why this pass is three lines of logic rather than a call to a
romaniser. The temptation is to write `namori` into the data and call the name done. Doing so would
permanently decide, for every reader forever, that ゆうり is spelled Yuri rather than Yūri or Yuuri,
because a romanised string cannot be un-romanised. Storing ユウリ decides nothing and offers all
three. The romanisation is generated at display time from the kana, by kana.romanise().

READING_BASIS IS `surface`, WHICH OUTRANKS EVERYTHING. A later database claiming なもり is read some
other way is not a correction, it is an error, and the store's rank table makes sure the databases
cannot overwrite this. It is the one basis a machine can assert with total confidence.

BASIS FOR THE ENGLISH RENDERING IS SET FOR AUTHORS AND LEFT OPEN FOR TITLES, and the asymmetry is
§1's: an author's English form is a romanisation, full stop, so `romaji` is settled the moment the
reading is known. A title's English form is a separate and unanswered question — ゆるゆり might end
up `official` (the publisher uses "YuruYuri"), `translated`, or `romaji` under §5a, and pass 1 has
no standing to choose. So a kana title gets its reading and no `basis`, and it stays in the queue
for pass 2 as a TITLE while being finished as a READING. The store tracks those separately for
exactly this reason.

WHAT COUNTS AS KANA-ONLY is slightly wider here than §2's script census, which put 219 authors and
164 titles in this bucket. Punctuation and decorative symbols do not have readings and so do not
stop a string being mechanically determined: ガールズ×ヴァンパイア is as exactly resolved as
ガールズヴァンパイア, and いちこえ、にふり、タチアオイ likewise. Digits are excluded, because 1話 needs
a decision (ichi? hito?) that no rule supplies. The wider test finds ~231 authors and ~192 titles.
"""
import argparse
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names import inputs, kana  # noqa: E402
from names.store import NameStore  # noqa: E402


def surface_fields(ja, kind):
    """What this pass records for one kana name, or None where the name is not kana.

    IT IS A FUNCTION SO THAT THE AUTOPILOT CAN CALL IT. `pass4_analyser.fill_missing` runs on every
    build and this pass runs when somebody remembers, so 181 kana-only author names picked up an
    analyser reading for a question the analyser was never needed for. Three of them came out
    wrong: はうあゆ was read ワ ウ アユ, because an analyser reading running text takes は as the
    particle, and はとぼし went the same way; あーねすと gained a sokuon nobody wrote. Those went to
    the site as Wa u Ayu and Wa Toboshi under the artists' own work.

    A second copy of the rule inside the autopilot would be this project's most repeated bug
    (STANDING-INSTRUCTIONS §3), so the autopilot consumes this one.
    """
    if not kana.kana_only(ja):
        return None
    fields = {
        "reading": kana.to_katakana(ja),
        "reading_basis": "surface",
        "source": "surface",
        "pass": 1,
    }
    if kind == "authors":
        # §5: an author's rendering is a romanisation of the reading and carries no visible
        # mark. `en` stays absent — the string is generated per reader style, never stored.
        fields.update(basis="romaji")
    return fields


def run(store, authors, titles):
    stats = collections.Counter()

    for kind, names in (("authors", authors), ("titles", titles)):
        for ja in names:
            fields = surface_fields(ja, kind)
            if fields is None:
                continue
            if store.records[kind].get(ja, {}).get("reading_basis") == "surface":
                stats[f"{kind}-already"] += 1
                continue
            store.record(kind, ja, **fields)
            stats[f"{kind}-resolved"] += 1
            store.maybe_compact()

    store.compact()
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--out", default="data/names")
    ap.add_argument("--sample", type=int, default=0,
                    help="print N resolved names in all three styles, to eyeball the renderer")
    args = ap.parse_args(argv)

    authors, titles, _, _by_title = inputs.load(args.build)
    store = NameStore(args.out)
    stats = run(store, authors, titles)
    for k, v in sorted(stats.items()):
        print(f"{k:24} {v}")
    if args.sample:
        print()
        for ja in sorted(a for a in authors if kana.kana_only(a))[:args.sample]:
            r = store.records["authors"][ja]["reading"]
            print(f"  {ja:20} {r:20} "
                  f"{kana.romanise(r, 'macron')} / {kana.romanise(r, 'double')} / "
                  f"{kana.romanise(r, 'plain')}")
    print()
    print("authors", store.status("authors", authors))
    print("titles ", store.status("titles", titles))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
