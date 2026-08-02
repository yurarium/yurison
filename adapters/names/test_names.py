#!/usr/bin/env python3
"""Regression test for the three decisions that would be expensive to get wrong (NAMES-PLAN).

These are not unit tests for coverage's sake. Each block pins one rule that, if it silently
regressed, would put a wrong name in front of a reader — and would look right while doing it.

1. STORE THE READING, RENDER THE STYLE (§8.1). All three romanisation styles must come out of the
   same kana, and the doubled style must write back the kana that was actually there: おう → ou and
   おお → oo are different spellings and flattening them loses what we were handed. If this breaks,
   the reader-facing style toggle silently offers fewer real choices than it claims.

2. RANK, NOT RECENCY (§1, and the owner's precedence correction to §5). A stated preference must
   never be overwritten by a later mechanical pass; official-jp must beat licensed; an equal-ranked
   disagreement must be kept as a conflict rather than settled by whichever source ran last; and a
   losing claim must still be recorded. Every one of those failing looks like "the data changed a
   bit" rather than like a bug.

3. AN ENGLISH TITLE FROM A COMMUNITY DATABASE IS A CANDIDATE, NEVER `en`. This is the bright line:
   a scanlation title is not a name the work has, and community databases cannot tell us which of
   their English titles is one.

Run: python3 adapters/names/test_names.py
"""
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names import kana  # noqa: E402
from names.inputs import split_authors  # noqa: E402
from names.pass2_bulk import looks_romanised  # noqa: E402
from names.store import NameStore  # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {name}: {got!r}" + ("" if ok else f" (want {want!r})"))
    if not ok:
        FAILS.append(name)


print("§8.1 — all three styles derive from the kana, and none from each other")
for reading, macron, double, plain in [
    ("ゆうり", "yūri", "yuuri", "yuri"),
    ("ゆり", "yuri", "yuri", "yuri"),
    ("とうきょう", "tōkyō", "toukyou", "tokyo"),
    ("おおさか", "ōsaka", "oosaka", "osaka"),   # おお, not おう — the doubled style must show it
    ("ビール", "bīru", "biiru", "biru"),        # ー lengthens i to ī; いい would stay ii
    ("けいこ", "keiko", "keiko", "keiko"),      # えい is ei in Hepburn, not ē
    ("しんいち", "shin'ichi", "shin'ichi", "shin'ichi"),
    ("まっちゃ", "matcha", "matcha", "matcha"),  # っ + ch is tch
    ("がっこう", "gakkō", "gakkou", "gakko"),
]:
    check(f"{reading} macron", kana.romanise(reading, "macron"), macron)
    check(f"{reading} double", kana.romanise(reading, "double"), double)
    check(f"{reading} plain", kana.romanise(reading, "plain"), plain)

print("\nromaji back-conversion refuses rather than inventing")
check("English word does not transliterate", kana.romaji_to_kana("Otherside Picnic"), None)
check("macron carries its length back", kana.romaji_to_kana("Hakkō"), "ハッコウ")
check("clean romaji round-trips", kana.romanise(kana.romaji_to_kana("Tōkyō"), "macron"), "tōkyō")

print("\ncredit lines are people, not roles and imprints")
check("roles stripped from both ends",
      [n for n, _ in split_authors("原作／宮澤伊織(早川書房刊)　作画／水野英多　キャラクター原案／shirakaba")],
      ["宮澤伊織", "水野英多", "shirakaba"])
check("separator inside a bracket does not split it",
      [n for n, _ in split_authors("小林湖底(GA文庫・SBクリエイティブ刊)　キャラクター原案：りいちゅ")],
      ["小林湖底", "りいちゅ"])
check("a spaced name is one person", [n for n, _ in split_authors("森島 明子")], ["森島 明子"])
check("bracketed kana is a reading, not an affiliation", split_authors("博（ひろ）"), [("博", "ヒロ")])
check("a bracketed studio is neither", split_authors("ののかなこ（FiFS)"), [("ののかなこ", None)])

print("\nromanisation vs. a chosen English name")
for s, want in [("Bloom Into You", False), ("Kimi to Shiranai Natsu ni Naru", True),
                ("Kuchibeta Shokudō", True), ("Wataten!", False), ("Mayonaka Punch", False),
                ("This Monster Wants to Eat Me", False), ("Hogushite, Yui-san", True),
                ("JK-chan and Her Male Classmate's Mom", False)]:
    check(f"{s!r}", looks_romanised(s, ""), want)

print("\n§1 + §5 precedence — rank decides, and the loser is kept")
tmp = tempfile.mkdtemp()
try:
    s = NameStore(tmp)
    s.record("titles", "X", en="Kimi no Nanika", basis="romaji", source="wikidata")
    s.record("titles", "X", en="Something Of Yours", basis="official-jp", source="publisher-jp")
    s.record("titles", "X", en="Your Thing", basis="licensed", source="yenpress")
    x = s.records["titles"]["X"]
    check("official-jp is what displays", (x["en"], x["basis"]), ("Something Of Yours", "official-jp"))
    check("both losers kept, none discarded",
          sorted(c["value"] for c in x["en_conflicts"]), ["Kimi no Nanika", "Your Thing"])

    s.record("titles", "Y", en="A", basis="romaji", source="mangaupdates")
    s.record("titles", "Y", en="B", basis="romaji", source="anilist")
    y = s.records["titles"]["Y"]
    check("equal rank, different value -> conflict not overwrite",
          (y["en"], [c["value"] for c in y["en_conflicts"]]), ("A", ["B"]))

    s.record("titles", "Z", en="Same", basis="romaji", source="mangaupdates")
    s.record("titles", "Z", en="Same", basis="romaji", source="wikidata")
    check("two sources agreeing is corroboration",
          s.records["titles"]["Z"]["en_corroborated"], ["wikidata"])

    s.record("authors", "なもり", reading="ナモリ", reading_basis="surface", source="surface")
    s.record("authors", "なもり", reading="ナモリコ", reading_basis="stated", source="wikidata")
    n = s.records["authors"]["なもり"]
    check("a kana surface cannot be corrected by a database", n["reading"], "ナモリ")
    check("but the disagreement is on the record",
          [c["value"] for c in n["reading_conflicts"]], ["ナモリコ"])

    s.record("authors", "P", reading="ヤマダ", reading_basis="back-converted", source="mangaupdates")
    check("a back-converted reading is not verified", s.records["authors"]["P"]["verified"], False)
    s.record("authors", "P", reading="ヤマダ タロウ", reading_basis="stated", source="wikidata")
    check("a stated reading displaces it and is verified",
          (s.records["authors"]["P"]["reading"], s.records["authors"]["P"]["verified"]),
          ("ヤマダ タロウ", True))

    print("\nthe bright line — a community English title never becomes `en`")
    s.record("titles", "C", candidate="Possibly A Scanlation Title",
             source="mangaupdates", source_kind="community-db")
    c = s.records["titles"]["C"]
    check("nothing displayable was created", c.get("en"), None)
    check("but it is recorded, with who said it",
          (c["en_candidates"][0]["value"], c["en_candidates"][0]["source_kind"]),
          ("Possibly A Scanlation Title", "community-db"))

    print("\nprovenance belongs to the claim, not the record")
    s.record("authors", "Sal Jiang", en="Sal Jiang", basis="stated",
             source="surface", source_kind="platform")
    s.record("authors", "Sal Jiang", en="Sal Jiang", basis="romaji",
             source="mangaupdates", source_kind="community-db")
    sj = s.records["authors"]["Sal Jiang"]
    check("a corroborating fan database cannot relabel a platform byline",
          sj["en_source_kind"], "platform")
    check("and the corroboration is still recorded", sj["en_corroborated"], ["mangaupdates"])

    print("\n§4 — the journal survives a process that never got to compact")
    s2 = NameStore(tmp)
    s2.record("authors", "Q", reading="キュー", reading_basis="surface", source="surface")
    s2.attempt("R", 2, "wikidata")
    del s2                                  # no close(), no compact — as if killed
    s3 = NameStore(tmp)
    check("a fact written but not compacted is replayed",
          s3.records["authors"].get("Q", {}).get("reading"), "キュー")
    check("so is an attempt", s3.tried("R", "wikidata"), True)
    check("and a resolved name is not offered to the same source again",
          s3.open_for("authors", ["Q", "R"], "wikidata", "reading"), [])
finally:
    shutil.rmtree(tmp)

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: {', '.join(FAILS)}")
    sys.exit(1)
print("all name invariants hold")
