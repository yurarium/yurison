#!/usr/bin/env python3
"""Record which analyser-read titles the analyser was not guessing at.

WHY THIS IS A PASS AND NOT A TEST INSIDE build.py. The question needs the analyser, and build.py's
`render` runs over every name in the store with no tokeniser in scope and no way to get one where
SudachiPy is absent. So the answer is worked out once, beside the reading, and stored: `render`
reads `reading_ordinary` and draws the `[?]` on everything without it.

`facts/reading/vocabulary` holds the rule and the reasoning. This is the part that has to touch
SudachiPy, and it is separated for the reason every other pass here is: the rule is testable
offline and the tokeniser is not.

TITLES ONLY, which is a ruling and not a limit of the code. `apply` will mark whatever it is given.
NAMES-PLAN §1 and §5c keep a different standard for a person's name, and the note this mark carries
was written about pen names, so an author record is left alone and keeps its mark.

    ./adapters/names/analyser_vocabulary.py            report what would stop being doubted
    ./adapters/names/analyser_vocabulary.py --apply    write it into data/names/titles.yaml
"""
import argparse
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from facts import reading as _vocab                                     # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "names" / "titles.yaml"

#: The basis this pass answers about. A reading a source stated or a reviewer settled is not marked
#: in the first place, so saying anything about its vocabulary would be answering a question nobody
#: asked. `back-converted` is deliberately absent: that reading was recovered by reading a
#: romanisation backwards, which has already lost the length of every vowel, and no fact about the
#: WORDS repairs that.
BASIS = "analyser"

#: What the record says once this has run. Written only where it holds, and removed where it stops
#: holding, so a record whose reading changed under it cannot keep a mark it no longer earns.
FIELD = "reading_ordinary"


def _tokeniser():
    """Sudachi, or None where it is not installed. A pass that cannot run says so and writes none."""
    try:
        from sudachipy import Dictionary, SplitMode
    except ImportError:
        return None, None
    import pass4_analyser as _p4
    tok = Dictionary().create()
    modes = [SplitMode.C, SplitMode.A]
    return (lambda s: tok.tokenize(s, SplitMode.C),
            lambda s: _p4.analyse_best(tok, s, modes)[0])


def apply(records, tokenise, read=None):
    """Mark every title whose every word is ordinary vocabulary. `(marked, refusals)`.

    ADDITIVE, IDEMPOTENT AND OFFLINE ONCE `tokenise` IS SUPPLIED, so `build.py` calls it on every
    build and a title arriving overnight is judged by morning.

    `marked` holds only the records this run changed, so a second run reports nothing and a pass
    that stopped working cannot look like a pass with nothing left to do.

    THE SPLIT MODE IS C, WHICH IS THE MODE THE READING WAS PRODUCED IN. `pass4_analyser.analyse_best`
    tries C and falls back to A, and asking about a different segmentation than the one that
    produced the reading would answer about a string nobody stored. Where the two disagree the
    morphemes do not spell the surface the reading was cut from and `vocabulary.doubt` says so.

    `read` GIVES THE READING THE CURRENT CODE PRODUCES, and a record whose stored reading is not
    that one is left doubted. SudachiDict ships dated releases and this store holds readings from
    several of them: 163 of 2,663 no longer re-derive identically, four of those beyond where the
    spaces fall. ケイオン！ シャッフル is now read `Shuffle`, and a claim about the words in a
    reading has to be a claim about the reading the record actually holds. Spacing alone is not a
    different reading, which is `store.same_reading`, so a dictionary release that moved a token
    boundary does not put 159 marks back.
    """
    from store import same_reading                                       # noqa: PLC0415
    marked, refusals = {}, collections.Counter()
    for ja, rec in (records or {}).items():
        if not isinstance(rec, dict):
            continue
        if rec.get("reading_basis") != BASIS:
            # A RECORD THAT LEFT THIS BASIS TAKES THE FIELD WITH IT. A title read by the analyser
            # and later stated by a source keeps whatever this pass wrote unless somebody removes
            # it, and a stale field says something about a record that stopped being true.
            if rec.pop(FIELD, None) is not None:
                marked[ja] = False
            continue
        try:
            morphemes = [(m.surface(), tuple(m.part_of_speech()), m.is_oov())
                         for m in tokenise(ja)]
        except Exception:                                                   # noqa: BLE001
            # A TOKENISER THAT THREW IS NOT A TITLE WITHOUT DOUBT. Sudachi raises on an input
            # longer than its buffer, and the fallback that matters is the one that keeps the mark.
            morphemes = []
        why = _vocab.doubt(ja, morphemes)
        if not why and read is not None:
            got = read(ja)
            if not got or not same_reading(got, rec.get("reading")):
                why = _vocab.READING_HAS_MOVED
        if why:
            refusals[why] += 1
            if rec.pop(FIELD, None) is not None:
                marked[ja] = False
            continue
        if not rec.get(FIELD):
            rec[FIELD] = True
            marked[ja] = True
    return marked, refusals


def apply_store(path=None):
    """`apply`, against the store on disk. `(marked, refusals)`, and the file is written.

    A missing store, or a missing SudachiPy, leaves everything as it was. That is the documented
    fallback: nothing is unmarked, so every analyser reading keeps the `[?]` it had.
    """
    import yaml
    tokenise, read = _tokeniser()
    path = pathlib.Path(path or STORE)
    if tokenise is None or not path.exists():
        return {}, collections.Counter()
    doc = yaml.safe_load(path.read_text()) or {}
    names = doc.get("names") or {}
    marked, refusals = apply(names, tokenise, read)
    if marked:
        path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
    return marked, refusals


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--store", default=str(STORE))
    a = ap.parse_args(argv)

    import yaml
    tokenise, read = _tokeniser()
    if tokenise is None:
        print("SudachiPy is not installed; every analyser reading keeps its mark")
        return 0
    path = pathlib.Path(a.store)
    doc = yaml.safe_load(path.read_text()) or {}
    names = doc.get("names") or {}
    marked, refusals = apply(names, tokenise, read)
    added = sorted(k for k, v in marked.items() if v)
    for k in added[:40]:
        print(f"  {k[:48]:48} {names[k].get('reading')}")
    print(f"{len(added)} title(s) read entirely in ordinary vocabulary; "
          f"{sum(1 for v in marked.values() if not v)} lost a mark they no longer earn")
    for why, n in refusals.most_common():
        print(f"  {n:5} keep the doubt: {why}")
    if a.apply and marked:
        path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))
        print(f"written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
