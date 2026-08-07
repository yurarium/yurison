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

AND WHERE NOBODY HAS SOURCED ONE, A ROMANISATION, MARKED AS ONE. That is the project owner's
ruling, and it is the treatment author names already get: §5d says an acknowledged guess is a
different speech act from an assertion, so a Latin form may be published provided a reader can tell
it from a name the company signs itself with. `basis` carries that distinction into the data and
`romaji` is the value that says the Latin is ours. The two rules tried and rejected above still
stand: what is rejected is inventing a name, not spelling out a reading.

The romanisation comes from the reading, through the same pass and the same romaniser as every
other name, so nothing here spells a name a second way. What that leaves is the join, and `english`
below is where it lives: 32 names had no English and 13 of them were people the name store already
held, because a work self-published through a shop names its own author as its publisher.

WHERE THE MAP IS WRITTEN NOW. build.py, inside feed/names.json, under a `publishers` key. This
module used to emit feed/publishers.json from deploy.sh, which made the interface fetch a second
file and made the build finish before its own output existed. `publisher_map()` in build.py does
the join and imports `publisher_of` and `imprint_of` from here, so the rule still has one copy.

What is left here is the REPORT: which names the corpus carries, which of them the store can
render, and the queue of the rest ordered by volumes. check.py's `publishers with no English`
budget reads the same three functions.

Usage:  publishers.py                 print what the store covers and what is still Japanese
        publishers.py --todo 40       print the queue, most-published first, and stop
        publishers.py --out PATH      also write the old standalone map, for a one-off comparison
"""
import argparse
import json
import pathlib
import re
import sys
import unicodedata

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


def corpus_names_from_rows(rows):
    """Every publisher and imprint string these series rows carry, and how many carry it.

    KEYED BY THE FIELD AS WELL AS THE STRING, which it was not, and the difference was a name
    missing from the shipped map. `GP-KIDS/高菜しんの` is catalogued in BOTH fields and the two
    normalise differently: as a publisher it is itself, and as an imprint it is 高菜しんの, because
    the slash separates an imprint from a person. Keyed on the string alone, whichever field was
    read first decided what the shown name was and the other one was merged into it, so the map
    held no 高菜しんの and the interface asked for a key nothing answered.

    Found by normalising the corpus the way app.js does and asking the shipped map for what came
    back, which is §14b: every measure in the pipeline shared this census, so none of them could
    see it. `publisher keys the interface misses` is that measure, kept.
    """
    out = {}
    for r in rows:
        for pr in (r.get("print") or []):
            for field, norm in (("publisher", publisher_of), ("imprint", imprint_of)):
                raw = str(pr.get(field) or "").strip()
                if not raw:
                    continue
                slot = out.setdefault((field, raw), {"kind": field, "raw": raw,
                                                     "shown": norm(raw), "volumes": 0})
                slot["volumes"] += 1
    return out


def corpus_names(build="data/build"):
    """Every publisher and imprint string the corpus carries, and how many volumes carry it.

    Read off the SERIES rows, which is where the interface reads them, so the queue is ordered by
    what a reader is most likely to be looking at.
    """
    rows = json.loads((pathlib.Path(build) / "series.json").read_text())["series"]
    return corpus_names_from_rows(rows)


def fold(s):
    """The interface's key: NFKC, spaces removed. `foldKey` in app.js and `_fold` in build.py."""
    return unicodedata.normalize("NFKC", s or "").replace(" ", "")


def english(raw, shown, store, people):
    """The English rendering for one publisher string, or None where nothing can render it.

    ONE PRODUCER FOR ONE FACT, which is §3 and which this file had already lost. 25 of the print
    rows name their own author as the publisher, because a work self-published through a shop's
    individual-publishing service has nobody else to name, and the same string was therefore being
    rendered twice: once from data/names/publishers.yaml and once from authors.yaml, by different
    code, with nothing forcing agreement. Two of them had already drifted on the live site.
    ガレットワークス was `Galette Works` beside its books and `Garettowākusu` beside its name, and
    ネジ式１３番地 was `Nejishiki 13-banchi` and `Neji Shiki Ichisan Banchi`. So a publisher string
    that a person's record already answers CONSUMES that answer rather than deriving a second one.

    THE ORDER, and why it is this way round:

      the publisher store, whatever its basis. A publisher-side source is about the company, and a
      reviewed romanisation with a note beats a machine's segmentation of the same characters.

      the person's record, where the string is one the name store already holds. This is the
      self-publishing case. It also means the reading pass never has to read these names, so the
      known word-boundary defect in kana names is inherited rather than re-derived, and it heals
      here the moment it heals there.

    A ROMANISATION IS OUR SPELLING OF THE JAPANESE AND MUST SAY SO. The record carries `basis`,
    which is `official-jp` where a company signs itself in Latin and `romaji` where the Latin is
    ours, and the romanisation is shipped in all three styles beside it so the reader's style
    control reaches a publisher name as it reaches every other name.
    """
    # THE NAME BEING SHOWN IS ASKED ABOUT FIRST, and the catalogued string only afterwards. Both
    # asked the raw string first, which is a record about a catalogue entry rather than about a
    # name, and one entry answers for two: `GP-KIDS/高菜しんの` is filed in both fields, so the
    # imprint — which is 高菜しんの alone — was answered by the record for the whole string and the
    # person's own name lost to it. A record about the name outranks a record about the line it was
    # catalogued on, whichever store holds it.
    rec = (store.get(shown) or people.get(fold(shown))
           or store.get(raw) or people.get(fold(raw)))
    if not rec:
        return None
    romaji = rec.get("romaji") or {}
    en = rec.get("en") or romaji.get("macron")
    if not en:
        return None
    # A romanisation stays `romaji` even when the record forgot to say so: `en` with no basis is a
    # record from before the field existed, and calling that official would assert a source.
    fact = {"en": en, "basis": (rec.get("basis") if rec.get("en") else "romaji") or "romaji"}
    # THE STYLE CONTROL MAY ONLY RESTYLE A STRING THE READING PRODUCED. 青騎士コミックス is written
    # `Aokishi Comics`, because コミックス is the English word it stands for and a romaniser cannot
    # know that; spelling the reading out gives `Aokishi Komikkusu`. Shipping both would let the
    # macron toggle replace a reviewed name with a transliteration of it, silently, and only for
    # readers who had touched the control. So the three styles travel only where they agree with
    # the name being shown, which is exactly the case where they are the same claim.
    if romaji and en == romaji.get("macron"):
        fact["romaji"] = romaji
    for flag in ("unverified", "uncertain"):
        if rec.get(flag):
            fact[flag] = True
    return fact


def render(store, people, names):
    """`{key: {en, basis, ...}}` for every name that has an English form, keyed both ways.

    Keyed by the string the catalogue holds AND by the string the interface shows, because the
    cataloguing is stripped in two places and §3 says two implementations of one rule will drift.
    A raw key means a drift costs a lookup the other key still answers.

    SHOWN NAMES FIRST, THEN THE RAW ALIASES, in two passes and not one. A raw string can be the
    shown name of one field and the alias of another: `GP-KIDS/高菜しんの` is the publisher's name
    entire and the imprint's catalogue line, so writing each slot's two keys as it went let the
    imprint's rendering claim the publisher's own name, and the publisher rendered as the person
    inside it. An alias may fill a gap; it may never displace a name.
    """
    out = {}
    facts = []
    for _slot, info in sorted(names.items()):
        fact = english(info["raw"], info["shown"], store, people)
        if fact:
            facts.append((info["raw"], info["shown"], fact))
    for _raw, shown, fact in facts:
        if shown:
            out.setdefault(shown, fact)
    for raw, _shown, fact in facts:
        if raw:
            out.setdefault(raw, fact)
    return out


def unreadable(names, store, people):
    """Publisher strings nothing can render yet, as the shown name. The reading pass queues on this.

    ASKED BEFORE ANYTHING IS RENDERED, so it reads the stores as they sit on disk rather than the
    map the build has not written yet. A record holding a reading can be romanised, so it counts as
    answered here even though it carries no `en`: what is outstanding is a name with neither.

    Only what nothing can reach. Reading every publisher name would put an analyser's guess and its
    note on top of 290 curated records, which is churn at best and, where a curated note is
    overwritten, the loss of the reason somebody recorded.
    """
    out = {}
    for _slot, info in names.items():
        raw, shown = info["raw"], info["shown"]
        if not JAPANESE.search(shown):
            continue
        rec = (store.get(raw) or store.get(shown)
               or people.get(fold(raw)) or people.get(fold(shown)) or {})
        if rec.get("en") or rec.get("reading"):
            continue
        out[shown] = info["volumes"]
    return sorted(out, key=lambda s: (-out[s], s))


def unnamed(rendered, names):
    """(volumes, name, kind) for every Japanese name the map cannot render, most-published first.

    COUNTED ON THE NAME THE READER SEES, not on the string a cataloguer typed. 講談社 reaches the
    corpus as itself, as `[発売]講談社` and as `[頒布]講談社`, and counting those separately reports
    one publisher three times and puts each of them lower down the queue than it belongs.
    """
    agg = {}
    for _slot, info in names.items():
        raw, shown = info["raw"], info["shown"]
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


def shipped_maps(build="data/build"):
    """`(publishers, authors)` out of the map the build wrote, in the shape a reader gets it.

    THE REPORT READS THE OUTPUT. It used to render the store again with its own copy of the rule,
    which meant it could not see a publisher the build had failed to write and could not see the
    romanisation the build renders from a reading. §14b: a report sharing its subject's derivation
    reports its subject's assumptions back.
    """
    p = pathlib.Path(build) / "feed" / "names.json"
    if not p.exists():
        return {}, {}
    doc = json.loads(p.read_text())
    return doc.get("publishers") or {}, doc.get("authors") or {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--store", default="data/names/publishers.yaml")
    ap.add_argument("--out", default=None)
    ap.add_argument("--todo", type=int, nargs="?", const=40, metavar="N",
                    help="print the names with no English, most-published first, and stop")
    a = ap.parse_args(argv)

    names = corpus_names(a.build)
    rendered, _people = shipped_maps(a.build)
    if not rendered:
        rendered = render(load_store(a.store), {}, names)
    todo = unnamed(rendered, names)

    if a.todo:
        for vols, name, kind in todo[:a.todo]:
            print(f"  {vols:5}  {kind:9}  {name}")
        print(f"\n{len(todo)} name(s) with no English; {min(a.todo, len(todo))} listed")
        return 0

    # Only on request. The interface reads feed/names.json, which build.py writes; a file emitted
    # here would be a second copy of the same fact with nothing forcing the two to agree.
    if a.out:
        out = pathlib.Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(
            {"note": "English for a publisher or an imprint, keyed by the string the catalogue "
                     "holds and by the string the interface shows. Written on request only; the "
                     "interface reads the same map out of feed/names.json.",
             "count": len(rendered), "names": rendered}, ensure_ascii=False, indent=1))
        print(f"wrote {out}")
    print(f"publishers: {len(names)} name(s) in the corpus, {len(rendered)} key(s) with English, "
          f"{len(todo)} still Japanese")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
