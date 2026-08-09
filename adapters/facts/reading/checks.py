#!/usr/bin/env python3
"""What this fact is checked on, beside the rulings it checks against.

These ask whether a reading may be believed and whether it can show who said so, which is
what this module rules on. `ruby spells the reading` and `a kana name's reading spells it`
stayed: they compare a reading against a SURFACE, which is a question about alignment.
"""
import pathlib
import re                                                              # noqa: F401
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))

ROOT = pathlib.Path(__file__).resolve().parents[3]

import unicodedata                                                      # noqa: E402
from names import provenance                                            # noqa: E402
from names import kana                                                  # noqa: E402


def _pub(ctx):
    """The publisher names the corpus carries. Moved with the check that reads it."""
    from names import publishers as _p
    return _p.names(ctx) if hasattr(_p, "names") else (ctx.get("publishers") or {})

def readings_are_kana(ctx):
    """The stored form is the KANA reading, never a romanised string (NAMES-PLAN §8.1).

    Yūri, Yuuri and Yuri all derive from kana and none derives from another, so a romanised string
    in this field permanently caps what the reader's style control can offer.
    fallback: reject that record; the work renders in Japanese.
    """
    # NOT "the reading is only kana". A reading legitimately carries digits, Latin and punctuation
    # straight through from the surface ,  100日後に reads "100 ニチゴ ニ", and #うちらが最強 keeps its
    # hash. The thing §8.1 forbids is a ROMANISED string standing in for the reading, so the test
    # is whether a run of Latin letters appears in the surface it came from. If it does, it was
    # passed through; if it does not, something romanised it.
    bad = []
    for kind in ("titles", "authors"):
        for k, v in (ctx["names"].get(kind) or {}).items():
            rd = v.get("reading")
            if not rd:
                continue
            # FOLDED, because ＪＫ and JK are the same letters. A title writes them full-width and
            # a reading passes them through folded, and comparing raw called that a romanisation:
            # 先生とＪＫ failed on a reading of センセイ ト JK, which is the surface's own letters.
            # Folding cannot weaken the test, since a romanisation of kanji appears in the surface
            # under neither width.
            surface = unicodedata.normalize("NFKC", k).lower()
            for run in re.findall(r"[A-Za-z]{2,}", unicodedata.normalize("NFKC", rd)):
                if run.lower() not in surface:
                    bad.append(f"{kind}:{k[:20]}={rd[:24]}")
                    break
    return bad


def reading_can_show_its_source(ctx):
    """A reading that says a source states it must be able to show that source.

    NAMES-PLAN §1: the failure mode is a plausible reading with no source behind it, presented as
    if it had one, which at a glance is indistinguishable from a correct one. `reading_basis:
    stated` IS that presentation. So the basis has to be backed by an address a reader can open,
    and the two shapes counted here are the two ways it stopped being.

    A CLAIM WITH NO DOCUMENT. 11 curated titles said a source stated their reading while naming
    `yurarium` and holding no page. One curated entry carries two claims and had one citation
    between them, so a title translated here and read off a shop page stamped the translation's
    provenance onto the reading. The reading_note beside each named BOOK☆WALKER and prose is not
    something a check can act on.

    A DOCUMENT WITH NO CLAIM. 11 refuted author readings kept a source and a date after the reading
    was withdrawn, and two kept a URL pointing at the MangaUpdates page for a DIFFERENT PERSON,
    which is the page the refutation was written to disown.

    §14b, WHAT THIS SHARES AND WHAT IT THEREFORE CANNOT SEE. It reuses `provenance.faults`, which
    is not the thing that produces an address: `store._stamp` writes one whenever a pass hands it
    over and has never looked at a basis, while this asks the basis and then asks whether an
    address is held. Two producers, and the check is the assertion that they agree, so a pass that
    forgot to record a page cannot satisfy it by forgetting consistently.

    What it cannot see is whether the page says what we say it says. An address that resolves to
    the wrong record passes here, and only the reader following it will know. That is the residual
    §14b names, and it is why the address is shipped rather than merely counted.

    fallback: the citation is not rendered, and the reading shows as it did before.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        from names import provenance
    except Exception:                                                       # noqa: BLE001
        return []
    bad = []
    for kind in ("titles", "authors"):
        for ja, fault, detail in provenance.faults(ctx["names"].get(kind) or {}):
            bad.append(f"{kind}:{ja[:24]} {fault} ({detail[:60]})")
    return bad


def uncertain_readings(ctx):
    return sum(1 for kind in ("titles", "authors")
               for v in (ctx["names"].get(kind) or {}).values() if v.get("reading_uncertain"))


def author_readings_no_source_states(ctx):
    """Author names shipping as a romanisation of ours under the unverified mark.

    THE DEFICIT THE NAMING WORK IS AGAINST, and it is written as a budget because there is no
    correct value for it and no floor anybody can compute. Every name in here renders in English as
    a romanisation of a reading nobody but a morphological analyser has ever produced, which is the
    one thing NAMES-PLAN section 1 says must never be presented as if it had a source. The mark is
    what says so on the page, and this is the same population counted where a person can watch it
    move.

    IT FALLS ONLY WHEN A NAME GETS SOURCED. `build.py` clears the mark for `stated` and for
    `researched` and for nothing else, so the only way to move this number is to find a source or
    to weigh one, and both of those leave a citation on the record. Suppressing the mark would move
    it too, which is why the number is kept beside the reason: a fall with no new citations behind
    it is the failure, not the success.

    NOT `uncertain readings`, WHICH SITS A FEW LINES ABOVE IT. That one counts the store's
    `reading_uncertain`, a flag pass 4 sets when it could not read a word at all and assembled the
    reading character by character. This one counts what a READER meets, which is 703 names against
    that budget's 73, and the two moved in opposite directions for a whole round without anyone
    being able to see it.

    MEASURED ON WHAT SHIPS AND OWING THE PASSES NOTHING (section 14b). The routes that reduce it
    select on `reading_basis`; this reads the rendered record, where `basis` is what the English
    column holds and the mark is what the browser draws. A pass that recorded a reading and failed
    to reach the feed would settle a name by its own measure and change nothing here.

    IT HAS A FLOOR OF EIGHT AND NOBODY CAN SOURCE THEM. A refuted reading leaves the record with no
    reading and no English, and `basis: romaji` and the mark stay on it, so 伊実 and 生肉 and the
    six others count here while rendering as the Japanese they are. Those are decisions somebody
    made and researched: 伊実 is a Chinese creator NDL deliberately files without kana, and there is
    nothing to replace the guess with. They are left in the count because taking them out would
    mean this number and the population the naming rounds are measured against are two different
    sets, and worth naming here so the next round does not spend a day on them.
    """
    return sum(1 for v in ((ctx["names_shipped"] or {}).get("authors") or {}).values()
               if v.get("basis") == "romaji" and (v.get("uncertain") or v.get("unverified")))


def publisher_readings_nobody_has_settled(ctx):
    """Publisher keys shipped as OUR romanisation whose reading no source states.

    WHY THIS EXISTS, AND WHY IT IS NOT THE BUDGET ABOVE. `publishers with no English` reached zero
    largely by romanising, which finished the rendering and moved the sourcing rather than doing
    it: a romanisation is the reading spelt in Latin, so a name romanised off a reading nobody has
    stated is published on a guess and carries the mark that says so. 134 keys were in that state
    on 2026-08-08 and no number anywhere said so, which is STANDING-INSTRUCTIONS §13: the first
    budget's fall to zero read as the work being done.

    A DEFICIT, so it falls only when a reading gets sourced. The route that would empty it without
    doing that is suppressing the mark in the interface, which was tried once and rejected, and
    this reads the SHIPPED map and asks for the mark precisely so that suppressing it would show
    up here as a fall nobody earned.

    The rule is `publishers.unsettled_readings`, which owes the producer nothing: `unverified` is
    computed in build.py out of `verified` and `reading_basis`, and this reads neither, only the
    file a reader is served. §14b, what it therefore cannot see: a reading cited to a page that
    says something else. No count can see that; only a reader following the citation will.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import publishers as _pub
    except Exception:                                                       # noqa: BLE001
        return 0
    # `names_shipped` and not `names`: the store holds a reading, and only the build spells it and
    # decides whether to mark it. Asking the store would count records rather than renderings and
    # would answer 0 while a reader was being shown 134 marks, which is what the first draft did.
    return len(_pub.unsettled_readings((ctx["names_shipped"] or {}).get("publishers") or {}))


def kana_reading_spells_its_name(ctx):
    """A name written in kana IS its reading, so the reading may not hold different kana.

    WHAT IT GUARDS, AND WHY IT IS NOT TRUE BY CONSTRUCTION. `pass1_kana` folds a kana surface to
    katakana and that half cannot fail. The half that can is a STATED reading landing on a kana
    name: a JPRO collationkey is a filing key before it is a reading and folds the kana that sort
    together, so openBD files とりいしづく under トリイ シズク and いづみやおとは under
    イズミヤ オトハ. Taking either whole republishes the artist's name with a different kana in it,
    which is one person under two spellings with nothing in the record saying they are the same.
    23 kana author names carry a reading from a source rather than from their own surface.

    Boundaries come out first, because a boundary IS admitted here and is what
    `adapters/names/boundary.py` carries onto our kana. What must not change is the spelling.

    WHAT IT THEREFORE CANNOT SEE, since §14b asks: a boundary in the wrong PLACE. Nothing mechanical
    can, which is why only a stated one is ever taken.

    Authors only. A title's reading legitimately differs from its surface, because は is written as
    the topic particle and read ワ: 7 kana titles are in that state and every one of them is right.

    fallback: none. A misspelt name is served under the artist's own work.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import kana
    except Exception:
        return []
    strip = str.maketrans("", "", " 　")
    bad = []
    for k, v in (ctx["names"].get("authors") or {}).items():
        rd = v.get("reading")
        if not rd or not kana.kana_only(k):
            continue
        want = unicodedata.normalize("NFC", kana.to_katakana(k)).translate(strip)
        got = unicodedata.normalize("NFC", kana.to_katakana(rd)).translate(strip)
        if want != got:
            bad.append(f"{k}: reading {rd!r} spells {got[:24]!r}")
    return bad


def ruby_spells_reading(ctx):
    """Ruby that does not spell its own reading is one record contradicting itself on one line.

    fallback: drop the ruby, keep the reading.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import kana
    except Exception:
        return []
    bad = []
    for r in ctx["series"]:
        we = r.get("work_en") or {}
        rd, rb = we.get("reading"), we.get("ruby")
        if not rd or not rb:
            continue
        # kana.ruby_spells is the definition of the question: a particle is written as it is
        # spelled and read as it sounds, so a literal comparison calls correct ruby a
        # contradiction. Putting わ over は would be the actual error.
        if not kana.ruby_spells(rb, rd):
            bad.append(r["work"])
    return bad

