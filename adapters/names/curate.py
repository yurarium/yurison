#!/usr/bin/env python3
"""Apply hand-reviewed English names to the store, refusing any that cannot be attributed.

WHY THIS EXISTS. Every pass so far produces names mechanically, and none of them can produce the
two kinds that matter most: a licensed title, which lives in a licensor's catalogue and nowhere a
scraper here goes, and a translation, which is a judgement. Both were being held in a person's head
with nothing between the decision and the file.

WHY THE DECISIONS LIVE IN A FILE. The store is journal-backed and durable, so recording straight
into it would not lose anything. What it would lose is the REASON: which page was read, on what
day, and by what argument a title was translated rather than romanised. data/names/curated.yaml is
the source and titles.yaml the derived state, the same relation data/source and data/build already
have, which also makes re-applying after a rebuild a replay rather than a re-decision.

WHAT IT REFUSES, AND WHY THAT IS THE POINT.

  A COMMUNITY DATABASE MAY NOT SUPPLY A NAME. Wikipedia, Wikidata, AniList and MangaUpdates are
  leads. A lead tells you where to look; it is not an attribution, and the string it carries may be
  a licensed title, a Japanese publisher's own, or a scanlation title, with nothing in the record to
  say which. `community-db` therefore appears in no row of ATTRIBUTION below, so an entry sourced
  to one is rejected outright unless it is filed as a candidate. This is the project owner's rule
  and it was previously enforced by remembering it.

  A BASIS MUST MATCH ITS EVIDENCE. `licensed` means a licensor publishes it under that name, so it
  requires a licensor page. `official-jp` means the work's own English name, so it requires the
  Japanese publisher or the platform. `translated` and `romaji` are ours, and claiming a source for
  them would be dressing up a judgement as a finding.

  AN UNKNOWN KEY IS AN ERROR. A hand-edited file that reads `bais: licensed` would apply nothing
  and report success, which is this project's characteristic bug written in YAML.

Usage:  curate.py --check              validate the file and stop
        curate.py --apply              validate, then record into data/names
"""
import argparse
import pathlib
import re
import unicodedata
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names.store import NameStore  # noqa: E402

FILE = pathlib.Path(__file__).resolve().parents[2] / "data" / "names" / "curated.yaml"

# Which evidence each basis demands. `community-db` is deliberately absent from every row.
ATTRIBUTION = {
    "stated": ("platform", "publisher-jp"),      # the person's own rendering, where they wrote it
    "official-jp": ("publisher-jp", "platform"),  # the work's own English name
    "licensed": ("licensor",),                    # an English-language licensor's catalogue
    "translated": ("derived",),                   # ours
    "romaji": ("derived",),                       # ours
}

# A source_kind may be named here without being usable as evidence: a candidate records where a
# string was seen, and seeing it in a community database is the ordinary case.
SOURCE_KINDS = ("platform", "publisher-jp", "licensor", "community-db", "derived",
                # A national cataloguing authority, and the person themselves. Both state readings
                # and neither is a publisher or a platform, so neither fitted the list before.
                "national-library", "author")

# A curated READING is a different claim from a curated name, and only two bases can be curated.
# `aligned` and `back-converted` describe how a machine derived one, which is not something a
# person does by hand, and `guessed` is what curation exists to replace.
READING_ATTRIBUTION = {
    "surface": ("derived",),                    # the title is already kana; the reading is the name
    # A SOURCE PRINTS THE KANA: a yomi field, furigana in a byline, a cataloguer's transcription.
    #
    # `national-library` is the National Diet Library, which records dcndl:creatorTranscription
    # beside dc:creator for every book it holds. That is a national cataloguing authority stating
    # how a name is read, and it is the only route that reaches most pen names at all: 79 of 82
    # author readings settled this way came from it. `author` is the artist's own page, which is
    # better still and is rarer, because most of them never write their name in kana.
    "stated": ("platform", "publisher-jp", "national-library", "author", "licensor"),
    # SETTLED BY A REVIEWER where nothing states it. A community wiki, a bookshop listing or the
    # way readers write about a work are all evidence about how a title is said, and none of them
    # is an attribution. This basis says a person weighed that evidence, so it demands a note
    # saying what was weighed: a reading with no reasoning behind it is a guess wearing a label.
    "researched": ("community-db", "derived"),
}

# `reading_note` is separate from `note` because one entry can carry two decisions. A work whose
# English was chosen for one reason and whose reading was corrected for another had to put both
# arguments in one field, or lose one: 55 of the 60 reading corrections landed on titles that
# already had a curated translation with its own note. Two decisions, two reasons.
KEYS = {"en", "candidate", "basis", "source", "source_kind", "source_url", "reviewed", "note",
        "candidate_note", "reading", "reading_basis", "reading_note", "reading_source_kind",
        "reading_refuted", "en_refuted"}

# What a reading may contain. Katakana and the marks that ride along with it: a title's own
# punctuation stays in its reading, and 100日後 keeps its digits, so a rule allowing katakana alone
# rejects readings the store already holds. What it still refuses is kanji and hiragana, which is
# the whole point of the check.
# A reading keeps the title's own bracketed labels and censoring marks verbatim, because they are
# part of the string rather than something to pronounce: 【タテスク】 and the 〇 of 〇〇する話 both
# appear in readings the store already holds.
KATAKANA = re.compile(r"^[ァ-ヺー・\s0-9０-９A-Za-zＡ-Ｚａ-ｚ"
                      r"!-/:-@\[-`{-~！-／：-＠［-｀｛-～、。〜…【】〇○◯"
                      r"─━♪♭♯★☆♡♥◎△▽※＆]+$")


def problems(kind, ja, e):
    """Everything wrong with one entry. Empty means it may be applied."""
    out = []
    if not isinstance(e, dict):
        return [f"{kind}/{ja}: expected a mapping, got {type(e).__name__}"]
    where = f"{kind}/{ja}"

    # REFUTED WITHOUT A REPLACEMENT, checked first because every other rule here assumes the entry
    # is proposing something. Research sometimes shows a reading is wrong and cannot say what is
    # right: カドコミ files 妻木都 under つ, which disproves the stored ムキ and leaves 都 unresolved.
    # There was no way to record that, so a reading known to be wrong stayed and was rendered.
    # 古川楊也 was published as "HOSHINO Katsura", which is a different person.
    if isinstance(e, dict) and (e.get("reading_refuted") or e.get("en_refuted")):
        bad = list(set(e) - KEYS)
        if bad:
            out.append(f"{where}: unknown key(s) {sorted(bad)}")
        if e.get("reading") or e.get("en"):
            out.append(f"{where}: a refutation cannot also propose a value")
        if not (e.get("reading_note") or e.get("note") or "").strip():
            out.append(f"{where}: a refutation has to say what disproved the reading")
        if not e.get("reviewed"):
            out.append(f"{where}: no reviewed date; this is a decision somebody made")
        return out

    unknown = set(e) - KEYS
    if unknown:
        out.append(f"{where}: unknown key(s) {sorted(unknown)}")

    if not (e.get("en") or e.get("candidate") or e.get("reading")):
        out.append(f"{where}: says nothing; give an `en`, a `candidate` or a `reading`")
    if e.get("en") and e.get("candidate"):
        out.append(f"{where}: an entry is either attributed (`en`) or seen (`candidate`), not both")
    if not e.get("source"):
        out.append(f"{where}: no source")
    if e.get("source_kind") not in SOURCE_KINDS:
        out.append(f"{where}: source_kind {e.get('source_kind')!r} is not one of {SOURCE_KINDS}")
    if not e.get("reviewed"):
        out.append(f"{where}: no reviewed date; a curated entry is a decision somebody made")

    if e.get("en"):
        basis = e.get("basis")
        if basis not in ATTRIBUTION:
            out.append(f"{where}: basis {basis!r} is not one of {sorted(ATTRIBUTION)}")
        elif e.get("source_kind") not in ATTRIBUTION[basis]:
            out.append(f"{where}: basis {basis!r} needs evidence from "
                       f"{' or '.join(ATTRIBUTION[basis])}, not {e.get('source_kind')!r}")
        if e.get("source_kind") != "derived" and not e.get("source_url"):
            out.append(f"{where}: an attributed name needs the page it was read from")
    elif e.get("basis"):
        out.append(f"{where}: a candidate carries no basis; it is not yet a claim about the work")

    if e.get("reading"):
        rb = e.get("reading_basis")
        # The reading's own attribution where it is given, and the entry's otherwise. An entry
        # whose translation came from a licensor may still have worked its reading out here, and a
        # licensor does not state Japanese readings, so that entry has to say so rather than
        # inherit a field offered for something else. Falling back to `derived` automatically was
        # tried and is wrong: it would let a licensor stand as evidence for a reading by silence.
        rsk = e.get("reading_source_kind") or e.get("source_kind")
        if rb not in READING_ATTRIBUTION:
            out.append(f"{where}: reading_basis {rb!r} is not one of {sorted(READING_ATTRIBUTION)}")
        elif rsk not in READING_ATTRIBUTION[rb]:
            out.append(f"{where}: reading_basis {rb!r} needs evidence from "
                       f"{' or '.join(READING_ATTRIBUTION[rb])}, not {e.get('source_kind')!r}")
        # Readings are stored as katakana throughout, and an invariant checks it at build time.
        # Catching a hiragana yomi here says which line to fix instead of failing the whole build.
        if not KATAKANA.match(e["reading"]):
            out.append(f"{where}: a reading is stored as katakana; got {e['reading']!r}")
        if rb == "researched" and not ((e.get("reading_note") or e.get("note") or "").strip()):
            out.append(f"{where}: a researched reading needs a note saying what it rests on")
    elif e.get("reading_basis"):
        out.append(f"{where}: reading_basis with no reading")
    return out


def check(doc):
    """Validate a whole file. Returns the list of problems across every entry."""
    out = []
    for kind in ("titles", "authors"):
        for ja, e in (doc.get(kind) or {}).items():
            out += problems(kind, ja, e)
    for key in set(doc) - {"titles", "authors"}:
        out.append(f"unknown top-level key {key!r}")
    return out


def _fold(t):
    """Width-folded, for deciding whether a curated key names a work we hold.

    NFKC only. build.py's lookup also strips spaces, and this deliberately does not: a key that
    differs by a full-width bracket is one work under two spellings and applies correctly, while a
    key with a stray space is a typo that happens to apply. The first should pass silently and the
    second is worth a reader's attention, so they are not folded together here.
    """
    return unicodedata.normalize("NFKC", t or "")


def unmatched(doc, known):
    """Curated keys that name no work we hold.

    A key is the Japanese title exactly as the catalogue stores it, and a hand-typed one that is
    off by a wave dash or a full-width bracket applies cleanly, changes nothing, and reports
    success. That is the failure this project keeps meeting, so the join is checked rather than
    assumed. Authors are not checked here: an author may legitimately be curated before any of
    their work is, and the same is not true of a title.
    """
    # Folded, because a work reaches us under more than one spelling and only one of them can be
    # on display. ギャルメイドと悪役令嬢 is stored 勝たん！～ by one platform and 勝たん!～ by another,
    # and the curated key stopped naming a work we hold the moment the interface picked the other
    # spelling. NFKC folds the pair without touching the words, which is how the name lookup in
    # build.py joins them too.
    # NO ANSWER IS NOT AN EMPTY ANSWER. `known_titles` returns None where the build has not stated
    # its titles, and folding None into an empty set would report every curated entry as naming
    # nothing, or, worse in the other direction, let a caller treat silence as agreement.
    if known is None:
        raise SystemExit("data/build/titles.json is missing: run build.py before checking the "
                         "curated names against the corpus")
    folded = {_fold(k) for k in known}
    return sorted(k for k in (doc.get("titles") or {}) if k not in known and _fold(k) not in folded)


def known_titles(build="data/build"):
    """Every title the build says it knows, folded.

    ASKED, NOT REASSEMBLED. This used to union the feed's rolling window with the series list, and
    later the month archives too, none of which is the corpus: the window forgets a work after a
    fortnight, the archives hold events, and series.json drops rows the interface will not show.
    Three curated titles stopped naming works we hold overnight because the window moved, and the
    three files together still missed 18 works and disagreed with each other about punctuation.

    build.py states the set now, in titles.json, holding titles as it holds them so each consumer
    folds to its own rule. `None` where the file is absent, so a caller can tell "no answer" from
    "no titles". Given no answer the check stops and says so: an empty set would pass everything.
    """
    import json
    p = pathlib.Path(build) / "titles.json"
    if not p.exists():
        return None
    return set(json.loads(p.read_text()).get("titles") or [])


def todo(build="data/build", limit=None, curated=None):
    """Works still showing a romanisation, most recently updated first.

    WHY THIS IS A FUNCTION AND NOT A QUERY SOMEBODY TYPES. The queue for the first two rounds of
    curation was picked with the filter "has no `en`", which is wrong: a machine romanisation IS
    an `en`, so every work already carrying one was excluded from the very pass meant to replace
    it. あなたのとなり is four kana meaning next to you and was skipped as already named, because
    Anata no Tonari was sitting in the field. Choosing the queue by hand reintroduces that each
    time; generating it does not.

    A romanisation is the finished answer for some titles, so this is a queue to review rather
    than a list of faults, and it is ordered by what a reader is most likely to be looking at.
    """
    import json
    names = json.loads(pathlib.Path(f"{build}/feed/names.json").read_text())["titles"]
    feed = json.loads(pathlib.Path(f"{build}/feed/current.json").read_text())["releases"]

    import unicodedata
    fold = lambda t: unicodedata.normalize("NFKC", t or "").replace(" ", "")
    latest = {}
    for r in feed:
        latest[r["work"]] = max(latest.get(r["work"], ""), r.get("pub") or "")
    for w in {s["work"] for s in json.loads(pathlib.Path(f"{build}/series.json").read_text())["series"]}:
        latest.setdefault(w, "")

    # A DECISION ALREADY MADE IS NOT WORK OUTSTANDING, whichever way it went. §5a keeps a title
    # romanised where translating is the wrong answer, and 球詠 and ぬるめた are as settled as any
    # translation is. Leaving them in the queue would report a finished state as pending, which is
    # the same category error this project met in the claim dispositions: it asks somebody to go
    # and do a thing that has been done and cannot be improved by doing again.
    #
    # The test is whether the work appears in curated.yaml at all, rather than what its basis says,
    # because that is exactly the record of a person having decided.
    decided = set((load(curated) if curated else load()).get("titles") or {})
    out = []
    for work, when in latest.items():
        rec = names.get(fold(work)) or {}
        if rec.get("basis") in ("official-jp", "licensed", "translated") or work in decided:
            continue
        out.append((when, work, (rec.get("romaji") or {}).get("macron") or rec.get("en")))
    out.sort(key=lambda x: (x[0] or "", x[1]), reverse=True)
    return out[:limit] if limit else out


def apply(store, doc):
    """Record every entry. Returns (applied, candidates)."""
    applied = candidates = 0
    for kind in ("titles", "authors"):
        for ja, e in (doc.get(kind) or {}).items():
            fact = {k: e.get(k) for k in
                    ("en", "candidate", "basis", "source", "source_kind", "source_url", "note",
                     "candidate_note", "reading", "reading_basis", "reading_note")}
            # `at` is the day the decision was reviewed, not the day this ran. Re-applying the file
            # after a rebuild must not restamp a name as freshly decided.
            fact["at"] = str(e.get("reviewed"))
            # The file is the decision of record, so re-applying it after an edit must change the
            # answer rather than filing the new wording as a conflict against the old one.
            fact["supersede"] = True
            store.record(kind, ja, **fact)
            # A refutation removes what is there and puts nothing in its place, so the name renders
            # as the Japanese it is. record() has no way to express an absence, so it is done here.
            if e.get("reading_refuted") or e.get("en_refuted"):
                rec = store.records[kind].get(ja) or {}
                why = str(e.get("reading_note") or e.get("note") or "")[:300]
                if e.get("reading_refuted"):
                    for f in ("reading", "reading_basis", "reading_source_kind", "furigana_spans",
                              "reading_uncertain"):
                        rec.pop(f, None)
                    rec["reading_refuted"] = why
                # An English name can be somebody else's too, and by the same route: MangaUpdates
                # gave 古川楊也 the author page of hoshino-katsura, so the database published a
                # different person's name in English beside their work.
                if e.get("en_refuted"):
                    for f in ("en", "basis", "en_source", "en_source_kind", "en_url", "en_at",
                              "en_pass", "en_conflicts"):
                        rec.pop(f, None)
                    rec["en_refuted"] = why
            if e.get("en"):
                applied += 1
            else:
                candidates += 1
    return applied, candidates


def load(path=FILE):
    return yaml.safe_load(pathlib.Path(path).read_text()) or {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", default=str(FILE))
    ap.add_argument("--out", default="data/names")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--build", default="data/build", help="where to look up the titles we hold")
    ap.add_argument("--todo", type=int, nargs="?", const=40, metavar="N",
                    help="list works still showing a romanisation, newest first, and stop")
    a = ap.parse_args(argv)

    if a.todo:
        rows = todo(a.build)
        for when, work, shown in rows[:a.todo]:
            print(f"  {when or '        '}  {work[:44]:46} {shown}")
        print(f"\n{len(rows)} work(s) still show a romanisation; {min(a.todo, len(rows))} listed")
        return 0

    doc = load(a.file)
    bad = check(doc)
    for b in bad:
        print(f"  REJECT {b}")
    stray = unmatched(doc, known_titles(a.build))
    for s in stray:
        print(f"  STRAY  titles/{s}: names no work in the catalogue")
    counts = {k: len(doc.get(k) or {}) for k in ("titles", "authors")}
    print(f"{counts['titles']} title(s), {counts['authors']} author(s); "
          f"{len(bad)} rejected, {len(stray)} matching nothing")
    if bad or stray:
        return 1
    if a.apply:
        store = NameStore(a.out)
        applied, cands = apply(store, doc)
        store.compact()
        store.close()
        print(f"applied {applied} attributed name(s) and {cands} candidate(s) to {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
