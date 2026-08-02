#!/usr/bin/env python3
"""Best-guess readings for everything the sourced passes could not reach — labelled as guesses.

WHY THIS EXISTS. Passes 0-2 resolve a name only when a source states its reading. That is the right
bar for a claim, and it left 733 works and 461 authors with no English at all: a database where two
thirds of the rows are Japanese-only whatever the language toggle says.

NAMES-PLAN §5d is what makes this pass legitimate. An acknowledged guess is a different speech act
from an assertion — it does not misname anyone, it offers a reading and says it is a reading — so
the choice is no longer "publish a possible error or show nothing". Everything here is written
`verified: false` and the interface marks it.

WHAT IT IS NOT. A morphological analyser is not a source. UniDic and SudachiDict are trained on
running text and are weakest on exactly what this project is full of: pen names, coinages, and
titles that are wordplay. So an analyser reading is never `stated`, never overwrites a sourced
reading, and never clears the unverified flag. If pass 2 or a future pass 3 later finds a real
source, it wins and this record is replaced.

THE ASYMMETRY IS DELIBERATE (§1 vs §5c). A mis-read title is a small correctable error about a
book. A mis-read author name misnames a real person under their own work. Both are guessed here —
because the alternative is no English at all — but the author side is where the unverified mark is
doing the real work, and it must never be quietly dropped from the interface.

Licence: SudachiPy and SudachiDict-core are Apache-2.0 (§5c). KANJIDIC2 is deliberately not used.

Usage:  pass4_analyser.py [--limit N] [--dry-run]
"""
import argparse, datetime, pathlib, sys, unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import yaml  # noqa: E402

STORE = pathlib.Path(__file__).resolve().parents[2] / "data" / "names"
KATA = {chr(c) for c in range(0x30A0, 0x3100)}


def kata(s):
    """Readings are stored in katakana, matching every other pass."""
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)


def has_kanji(s):
    return any("\u4e00" <= c <= "\u9fff" for c in s)


def analyse(tokenizer, s, mode=None):
    """A reading for the whole string, or None if any part of it comes back unreadable.

    Partial is not useful here: a title half in kana and half in raw kanji reads worse than the
    Japanese did, so it is all or nothing. Sudachi returns the SURFACE when it has no reading for a
    token rather than a marker, so `田口囁一` came back as `タグチ 囁一` and passed a naive check —
    the test that matters is whether kanji survive into the output, not whether the field is empty.

    SplitMode.C keeps named entities and compounds whole. Mode A is morphemes, which split 食べたい
    into 食べ/たい and rendered "Tabe Tai"; the coarser mode is closer to words, which is what a
    romanised title needs.
    """
    out = []
    for m in tokenizer.tokenize(s, mode):
        surf = m.surface()
        r = m.reading_form()
        # SURFACE FIRST. Sudachi does not decline to read a symbol — it returns キゴウ, the reading
        # of 記号, the WORD "symbol". So a space, ～, ×, ♡ or ◎ each came back as a legitimate-looking
        # kana reading and sailed past a check for empty or unreadable output: 森島 明子 became
        # "Morishima Kigō Akiko" and 100日後に×××する女社長 grew three of them. Punctuation, symbols
        # and separators pass through as themselves whatever the analyser says about them.
        if surf and all(unicodedata.category(c)[0] in "PZS" or c.isascii() for c in surf):
            out.append(surf)
            continue
        if not r or r == "*" or has_kanji(r):
            return None            # a kanji we cannot read means we cannot read the string
        out.append(kata(r))
    # No space before closing punctuation, and none after an opening one — " , " is not spacing,
    # it is damage.
    got = ""
    for tokn in out:
        if not tokn:
            continue
        if got and not (tokn[0] in "、。，．！？」』）】〉》・…" or got[-1] in "「『（【〈《"):
            got += " "
        got += tokn
    got = got.strip()
    return got if got and not has_kanji(got) else None


# A credit line is not a name. 原作／宮澤伊織(早川書房刊) 作画／水野英多 went through the analyser as
# one string and came back "Gensaku Kigō Miyazawa Iori Kigō …" — it romanised the ROLE LABELS and
# read ／ as 記号, the word "symbol". An analyser will always try; the guard has to be ours.
ROLE = ("原作", "作画", "漫画", "脚本", "構成", "企画", "監修", "協力", "編集", "案", "著")
SEP = "／/・、,＆&+"


def has_japanese(s):
    return any("\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff" for c in s)


def is_credit_line(s):
    if len(s) > 24:
        return True                       # a name that long is a sentence about several people
    if any(c in s for c in SEP):
        return True
    return any(r in s for r in ROLE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    try:
        from sudachipy import Dictionary
    except ImportError:
        sys.exit("SudachiPy not installed: pip install sudachipy sudachidict-core")
    from sudachipy import SplitMode
    tok = Dictionary().create()
    mode = SplitMode.C
    today = str(datetime.date.today())

    for kind in ("titles", "authors"):
        f = STORE / f"{kind}.yaml"
        doc = yaml.safe_load(f.read_text())
        names = doc["names"]

        # Everything the pipeline has seen, not just what already has a record.
        import json
        seen = set()
        series = json.load(open("data/build/series.json"))["series"]
        for r in series:
            if kind == "titles":
                seen.add(r["work"])
            elif r.get("author"):
                seen.add(r["author"].strip())

        todo = [s for s in sorted(seen)
                if s and not (names.get(s) or {}).get("reading")
                # A name already in Latin has nothing to read. Worse, the analyser does not
                # decline — it reads the SPACE between the words as 記号, so "Sal Jiang" came back
                # "サル キゴウ jiang". Asking a Japanese analyser to read English is our error, not
                # its failure.
                and has_japanese(s)
                and not (kind == "authors" and is_credit_line(s))]
        if a.limit:
            todo = todo[: a.limit]

        added = skipped = 0
        for s in todo:
            r = analyse(tok, s, mode)
            # A reading identical to the surface tells the reader nothing they cannot already see.
            if not r or r.replace(" ", "") == s.replace(" ", ""):
                skipped += 1
                continue
            rec = names.setdefault(s, {})
            spans = furigana_spans(tok, s, mode)
            if spans:
                rec["furigana_spans"] = spans
            rec.update({"reading": r, "reading_at": today, "reading_basis": "analyser",
                        "reading_pass": 4, "reading_source": "sudachi",
                        "reading_source_kind": "analyser",
                        # Never true. This is the labelled guess §5d permits, not a claim.
                        "verified": False})
            rec.setdefault("basis", "romaji")
            rec["note"] = ("reading guessed by a morphological analyser, not stated by any source; "
                           "analysers are weakest on pen names and coinages")
            added += 1

        print(f"{kind}: {len(todo)} without a reading -> {added} guessed, {skipped} left alone")
        if not a.dry_run:
            doc["names"] = names
            f.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=True, width=100))


if __name__ == "__main__":
    main()


def furigana_spans(tokenizer, s, mode=None):
    """[[text, reading-or-null], …] for a whole string, aligned per kanji run.

    Alignment is per TOKEN because that is where a reading is actually known — asking for the
    reading of a whole title and then trying to place it is the harder problem and the one that
    produces ruby over the wrong character. SudachiPy supplies the tokens and their readings; only
    the placement inside a token is ours (kana.align).

    Returns None if any token cannot be aligned, because a title with ruby over half its kanji
    looks like a bug rather than a partial answer.
    """
    import kana as _k
    out = []
    for m in tokenizer.tokenize(s, mode):
        surf = m.surface()
        r = m.reading_form()
        if not surf:
            continue
        if not r or r == "*" or has_kanji(r):
            if all(unicodedata.category(c)[0] in "PZS" or c.isascii() for c in surf):
                out.append([surf, None])
                continue
            return None
        got = _k.align(surf, kata(r))
        if got is None:
            return None
        for text, rd in got:
            out.append([text, _k.to_hiragana(rd) if rd else None])
    # Merge neighbouring unread runs so the markup does not fragment plain text pointlessly.
    merged = []
    for text, rd in out:
        if rd is None and merged and merged[-1][1] is None:
            merged[-1][0] += text
        else:
            merged.append([text, rd])
    return merged
