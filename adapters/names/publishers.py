#!/usr/bin/env python3
"""English for a publisher and an imprint, rendered from data instead of from a literal in app.js.

WHY THIS EXISTS. `kari/app.js` carried `PUB_EN`, seven names typed by hand, with a comment saying
the corpus holds four publishers and a handful of imprints. It holds 139 publisher names and 250
imprint names that are written in Japanese, so 301 of them fell through the map and rendered as
Japanese beside an English title. A longer literal makes the same mistake at a larger size, and it
puts a name where no basis and no source can travel with it.

A PUBLISHER NAME IS A NAME. `data/names/` already holds titles and authors with the basis for each
rendering and the page it was read from, so publisher names go there too, and this module is the
join: the store on one side, every publisher and imprint string the corpus actually carries on the
other, and one file for the interface to read.

WHERE AN ENGLISH NAME COMES FROM: THE COMPANY. 講談社 signs itself KODANSHA LTD. and 芳文社 signs
itself HOUBUNSHA CO., LTD, each on its own site, and that is `official-jp`: the name they publish
under, carrying the page it was read from. Curated by hand through `data/names/curated.yaml`,
because a source is not something a script can invent.

ONE ENTRY COVERS EVERY SPELLING, which is what makes hand-curation affordable here. MADB writes
百合姫 at least eight ways and `imprint_of` already collapses them onto コミック百合姫, so the
389 strings in the corpus are far fewer names than they look, and the queue below is ordered by
volumes so the first entry written is the one most readers meet.

TWO RULES TRIED AND REJECTED, because both are the obvious shortcuts and both are wrong.

  ROMANISING KATAKANA. 150 of the 301 hold no kanji and no hiragana, so a kana-to-Hepburn pass
  would "solve" them in one line. It would also be wrong in the way the operator has just had to
  report about titles: katakana marks a FOREIGN word, and ナンバーナイン is a company that signs
  itself No9. Syllable by syllable it comes out Nanbānain, which transliterates a transliteration.

  TAKING MADB'S PARALLEL TITLE. MADB files an imprint as `IDコミックス／Yuri-hime comics`, one name
  written twice, once in each script, and reading the Latin half off the record costs no request at
  all. `GP-KIDS/高菜しんの` has exactly the same shape and is an imprint beside a person, so the
  rule publishes one party's name as another's. The corpus holds three volumes whose record uses
  the unambiguous `A = B` form, which is not worth a mechanism.

A name nobody has sourced stays Japanese, which is NAMES-PLAN §6 and costs a reader nothing.

Usage:  publishers.py                 write the interface's file and print what is still unnamed
        publishers.py --todo 40       print the queue, most-published first, and stop
"""
import argparse
import json
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

OUT = pathlib.Path("data/build/feed/publishers.json")

# THE CATALOGUER'S NOTATION, PORTED FROM app.js's `publisherOf` AND `imprintOf`.
#
# Two copies of one rule is what §3 is about, and there is no way to have one: the interface
# normalises in the browser and this has to produce keys that match what the interface asks for.
# What removes the risk is that the shipped file is keyed BOTH ways, by the raw catalogued string
# and by the normalised form, so a drift between the two implementations costs a lookup that the
# other key still answers, rather than a name that silently renders as Japanese.
CATALOGUE_PREFIX = re.compile(r"^\s*\[[^\]]*\]\s*")
TRAILING_NOTE = re.compile(r"\s*[（(][^）)]*[）)]\s*$")

# One imprint spelled six ways. MADB writes 百合姫 as `IDコミックス`, `コミック百合姫`,
# `IDコミックス. Yurihime comics = コミック百合姫`, `IDコミックス／Yuri-hime comics` and more.
IMPRINT_ALIAS = {"yurihimecomics": "コミック百合姫", "yurihimecomic": "コミック百合姫",
                 "コミック百合姫": "コミック百合姫", "百合姫コミックス": "コミック百合姫"}
UMBRELLA = "IDコミックス"

LATIN = re.compile(r"^[\x20-\x7eÀ-ɏ]+$")
JAPANESE = re.compile(r"[぀-ヿ一-鿿々]")


def publisher_of(s):
    """A publisher without the cataloguing around it. `[頒布]講談社` and `講談社 (発売)` are both 講談社."""
    return TRAILING_NOTE.sub("", CATALOGUE_PREFIX.sub("", str(s or ""))).strip()


def segments(s):
    return [x.strip() for x in re.split(r"[=／/.．]", CATALOGUE_PREFIX.sub("", str(s or "")))
            if x.strip()]


def imprint_of(s):
    """One spelling of an imprint, whichever of the six a record used."""
    segs = segments(s)
    for seg in reversed(segs):
        k = re.sub(r"[\s・-]", "", seg.lower())
        if IMPRINT_ALIAS.get(k) or IMPRINT_ALIAS.get(seg):
            return IMPRINT_ALIAS.get(k) or IMPRINT_ALIAS.get(seg)
    named = [x for x in segs if x != UMBRELLA]
    return (named[-1] if named else (segs[0] if segs else "")) or ""


def corpus_names(build="data/build"):
    """Every publisher and imprint string the corpus carries, and how many volumes carry it.

    Read off the SERIES rows, which is where the interface reads them, so the queue is ordered by
    what a reader is most likely to be looking at.
    """
    rows = json.loads((pathlib.Path(build) / "series.json").read_text())["series"]
    out = {}
    for r in rows:
        for pr in (r.get("print") or []):
            for field, norm in (("publisher", publisher_of), ("imprint", imprint_of)):
                raw = str(pr.get(field) or "").strip()
                if not raw:
                    continue
                slot = out.setdefault(raw, {"kind": field, "shown": norm(raw), "volumes": 0})
                slot["volumes"] += 1
    return out


def render(store, names):
    """`{key: {en, basis, source}}` for every name that has an English form, keyed both ways."""
    out = {}
    for raw, info in sorted(names.items()):
        shown = info["shown"]
        rec = store.get(raw) or store.get(shown)
        if not (rec and rec.get("en")):
            continue
        fact = {"en": rec["en"], "basis": rec.get("basis") or "romaji",
                "source": rec.get("source") or ""}
        for key in {raw, shown}:
            if key:
                out.setdefault(key, fact)
    return out


def unnamed(rendered, names):
    """(volumes, name, kind) for every Japanese name the map cannot render, most-published first.

    COUNTED ON THE NAME THE READER SEES, not on the string a cataloguer typed. 講談社 reaches the
    corpus as itself, as `[発売]講談社` and as `[頒布]講談社`, and counting those separately reports
    one publisher three times and puts each of them lower down the queue than it belongs.
    """
    agg = {}
    for raw, info in names.items():
        shown = info["shown"]
        if not JAPANESE.search(shown) or shown in rendered or raw in rendered:
            continue
        slot = agg.setdefault(shown, [0, shown, info["kind"]])
        slot[0] += info["volumes"]
    return sorted((tuple(v) for v in agg.values()), reverse=True)


def load_store(path="data/names/publishers.yaml"):
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    return (yaml.safe_load(p.read_text()) or {}).get("names") or {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--store", default="data/names/publishers.yaml")
    ap.add_argument("--out", default=None)
    ap.add_argument("--todo", type=int, nargs="?", const=40, metavar="N",
                    help="print the names with no English, most-published first, and stop")
    a = ap.parse_args(argv)

    names = corpus_names(a.build)
    rendered = render(load_store(a.store), names)
    todo = unnamed(rendered, names)

    if a.todo:
        for vols, name, kind in todo[:a.todo]:
            print(f"  {vols:5}  {kind:9}  {name}")
        print(f"\n{len(todo)} name(s) with no English; {min(a.todo, len(todo))} listed")
        return 0

    out = pathlib.Path(a.out) if a.out else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"note": "English for a publisher or an imprint, keyed by the string the catalogue holds "
                 "and by the string the interface shows. `basis` says whose name it is: "
                 "official-jp is the company's own and is shown unmarked, romaji is a Latin form "
                 "of the Japanese and is ours.",
         "count": len(out_names := {k: v for k, v in rendered.items()}),
         "names": out_names}, ensure_ascii=False, indent=1))
    print(f"publishers: {len(names)} name(s) in the corpus, {len(rendered)} key(s) with English, "
          f"{len(todo)} still Japanese -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
