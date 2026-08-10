#!/usr/bin/env python3
"""Give a glued analyser reading the division the analyser already made.

WHY THIS EXISTS. The project owner raised `上田香子` rendering `Uedakyōko` on 2026-08-09: one token
no reader would take for a Japanese name. The record says why. `reading_basis: analyser`,
`reading_source: sudachi`, and no boundary, because the pass kept the whole reading as one opaque
run and threw the segmentation away. Sudachi had already tokenised the name as 上田/ウエダ and
香子/キョウコ at the moment the reading was produced.

WHAT IT DOES NOT DO, and this is the part the measurement decided. It does not divide on a morpheme
boundary. Taking every two-morpheme split gives クロ バ for くろば, ルイ ス for るいす and オ
ヒサシブリ for お久しぶり: 118 divisions across the author store, most of them inventing a person.
A morpheme boundary is not a name boundary. `facts/division.boundary.from_analyser` asks the
analyser what it thinks the halves ARE, and takes a division only where it says 固有名詞 人名 姓 and
then 名. That leaves 40, and every one is a surname beside a given name.

THE CLAIM STAYS WHAT IT WAS. `reading_boundary_basis` is `analyser`, which cites no source and is
marked wherever it reaches a reader, and `divisions resting on a community database` and its
siblings go on counting these. The string a reader sees gets better and nothing behind it moves,
which is the shape of the owner's Wikidata ruling of the same week.

    ./adapters/names/analyser_division.py            report what would be divided
    ./adapters/names/analyser_division.py --apply    write the divisions into data/names
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from facts import division as _division                                 # noqa: E402
import store as _store                                                  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: What the division is recorded as resting on. A person reading the record has to be able to tell
#: this from a division somebody printed.
BASIS = "analyser"
NOTE = "the analyser's own segmentation, where it names a surname and a given name"


def _tokeniser():
    """Sudachi, or None where it is not installed. A pass that cannot run says so and writes none."""
    try:
        from sudachipy import dictionary
    except ImportError:
        return None
    return dictionary.Dictionary().create()


def proposals(records, tokenise=None):
    """`{surface: divided reading}` for every glued analyser reading the analyser can divide."""
    tok = tokenise or _tokeniser()
    if tok is None:
        return {}
    out = {}
    for ja, r in (records or {}).items():
        if not isinstance(r, dict):
            continue
        reading = r.get("reading")
        if (not reading or r.get("reading_basis") != BASIS
                or _division.divisions(reading) != 1 or r.get("reading_boundary")):
            continue
        morphemes = [(m.surface(), m.reading_form(), tuple(m.part_of_speech()))
                     for m in tok.tokenize(ja)]
        divided = _division.from_analyser(reading, morphemes)
        if divided:
            out[ja] = divided
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--kind", default="authors")
    a = ap.parse_args(argv)

    st = _store.NameStore(ROOT / "data" / "names")
    records = st.records.get(a.kind) or {}
    got = proposals(records)
    for ja, divided in sorted(got.items()):
        print(f"  {ja:24} {records[ja]['reading']}  ->  {divided}")
    print(f"{len(got)} of {len(records)} {a.kind} take the analyser's own division")

    if a.apply:
        # THE CLAIM IS THE SAME CLAIM, SO ITS PROVENANCE TRAVELS WITH IT. Superseding clears what
        # the incoming fact does not restate, which is right for a reviewer replacing a reading and
        # wrong here: this is not a new reading, it is the reading that is already there with the
        # division the analyser made. Restating them dropped `reading_source_kind`, `reading_pass`
        # and the furigana spans on all 39 the first time this ran.
        for ja, divided in got.items():
            # A COPY, BECAUSE `record` MUTATES THE RECORD IN PLACE. Holding the live dict and
            # reading a field back after the write gave None, which is how the furigana spans
            # were restored from a record that no longer had them.
            was = dict(records[ja])
            st.record(a.kind, ja, reading=divided, reading_basis=BASIS,
                      reading_boundary=NOTE, reading_boundary_basis=BASIS,
                      reading_source=was.get("reading_source"),
                      reading_source_kind=was.get("reading_source_kind"),
                      reading_pass=was.get("reading_pass"),
                      reading_at=was.get("reading_at"),
                      source=was.get("reading_source") or "sudachi",
                      supersede=True)
            # SPANS ARE CUT FROM A READING AND THIS ONE IS THE SAME READING RESPACED, so they are
            # put back rather than left to be re-derived, which build.py would do on the next run
            # and which would make this pass look like it had changed the ruby.
            if was.get("furigana_spans") is not None:
                st.records[a.kind][ja]["furigana_spans"] = was["furigana_spans"]
        st.close()
        print(f"  wrote {len(got)} division(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
