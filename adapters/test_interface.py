#!/usr/bin/env python3
"""interface.py: loading the real kari/app.js and asking it what a reader would see.

COVERS = ['adapters/interface.py', 'adapters/interface.js']

WHAT THIS HAS TO PROVE, beyond that node starts. The whole value of this seam is that it is not a
model of the interface, so the assertions below are about the difference between running app.js and
describing it. Each pins a rendering the transcription in check.py got wrong:

  a title with a subtitle after an ISBD colon is NOT joined to the base title, which is the
  fallback the transcription invented and the reason a work reached a reader in Japanese;

  a title with a closed-set edition marker IS glossed beside its base title, which is a fallback
  app.js really has and which a rule guessed from the first case would have missed;

  `foldKey` is the browser's own, and its answer comes back whole rather than with the harness's
  tag stripper having read the ＜完＞ in a chapter name as an element and thrown it away.

OFFLINE. Nothing here reaches a network: node is handed a request on stdin and a path to a file.
Where node is not installed the suite says so and asserts nothing that depends on it, which the
runner reports as vacuous rather than as a pass.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import interface
import testkit

# A name map the size of a fixture: three records, each one a shape the renderer treats
# differently. Written out here rather than cut from feed/names.json because it is not a page and
# has no provenance to keep; what makes it honest is that each record is the shape a real one has.
# KEYED AS THE BUILD KEYS IT, folded: NFKC and every space removed. Written folded here rather
# than folded by a helper, because a helper would be this file's copy of `foldKey` and the point of
# the suite is that there is no copy.
# THE FLOOR, which is where a name with no rendering lands. Keyed folded like everything else, and
# holding a string where the three styles agree and an object where they differ, which is the shape
# `adapters/names/romfloor.py` ships.
FLOOR = {
    "怪異部:M県Y市の怪現象について": "Kaiibu : M Ken Y Shi no Kaigenshou ni Tsuite",
    "やまじえびね": {"macron": "Yamajiebine", "double": "Yamajiebine", "plain": "Yamajiebine"},
}

# The opening of the floor's own tooltip. Asserted present on a name the store holds nothing for and
# absent on one whose reading a community database printed, so it is written here once: the two
# assertions are a pair and a typo in either would look like the other case passing.
FLOOR_SENTENCE = "No source states how this name is read"

NAMES = {
    "floor": FLOOR,
    "titles": {
        # A curated translation, under the platform's spelling with the subtitle in 〜 〜.
        "怪異部~M県Y市の怪現象について~": {
            "en": "The Uncanny Club", "basis": "translated",
            "en_forms": {"translated": "The Uncanny Club"}},
        # The base of an edition marker, which app.js glosses beside.
        "恋愛遺伝子XX": {
            "en": "The Romance Gene XX", "basis": "translated",
            "en_forms": {"translated": "The Romance Gene XX"}},
        # A romanisation and nothing else, which follows the style control.
        "雨夜の月": {"reading": "アマヨノツキ", "basis": "romaji",
                 "romaji": {"macron": "Amayo no Tsuki", "double": "Amayo no Tsuki",
                            "plain": "Amayo no Tsuki"}},
    },
    "authors": {
        # A credit with an identifier, which is what makes it a link. Keyed folded, as the build
        # keys it, and carrying the id the registry minted rather than a shape invented here.
        "仲谷鳰": {"reading": "ナカタニ ニオ", "basis": "romaji", "id": "c00173",
                "romaji": {"macron": "Nakatani Nio", "double": "Nakatani Nio",
                           "plain": "Nakatani Nio"}},
        "水野英多": {"reading": "ミズノ ヒデタ", "basis": "romaji", "id": "c00500",
                 "romaji": {"macron": "Mizuno Hideta", "double": "Mizuno Hideta",
                            "plain": "Mizuno Hideta"}},
        # A credit the registry does not answer for, which is a state and not a gap: the store
        # holds records nothing in the works list credits.
        "宮澤伊織": {"reading": "ミヤザワ イオリ", "basis": "romaji",
                 "romaji": {"macron": "Miyazawa Iori", "double": "Miyazawa Iori",
                            "plain": "Miyazawa Iori"}},
        # A creator MADB writes as the name beside its own reading, which is the shape the 発売
        # tab used to publish as two artists.
        "紬めめ": {"reading": "ツムギ メメ", "basis": "romaji",
                "romaji": {"macron": "Tsumugi Meme", "double": "Tsumugi Meme",
                           "plain": "Tsumugi Meme"}},
        # A NAME WHOSE READING IS SOURCED AND STATES NO DIVISION. The media-arts catalogue files
        # this artist タイヨウマリイ, correctly and closed up, so the romanisation runs together
        # where the person is 太陽 まりい. Nothing in the characters says where a Japanese name
        # divides, so the run-on form is the honest fallback and the note is what stops it reading
        # as settled.
        "太陽まりい": {"reading": "タイヨウマリイ", "basis": "romaji", "undivided": True,
                  "romaji": {"macron": "Taiyōmarii", "double": "Taiyoumarii",
                             "plain": "Taiyomarii"}},
        # A NAME WHOSE READING A COMMUNITY DATABASE PRINTED, verbatim from data/names/authors.yaml.
        # Wikidata's P1814 gives ヤブウチ ユウ and P734/P735 divide it, so the spelling beats
        # anything derived from the characters and nobody who answers for the name has spoken. The
        # project owner's correction of 2026-08-09 is about exactly this record: the string a reader
        # sees improves and the record goes on resting on a fallback.
        "やぶうち優": {"reading": "ヤブウチ ユウ", "basis": "romaji", "unverified": True,
                  "reading_basis": "community-printed",
                  "romaji": {"macron": "Yabūchi Yū", "double": "Yabuuchi Yuu",
                             "plain": "Yabuchi Yu"}},
        # THE FOUR PEOPLE A LONG BYLINE SHOWS BEFORE IT COUNTS THE REST, two of them either side
        # of a ・ the corpus settled as a separator. `安田剛助・文尾文` is in no map, on purpose:
        # the build floors the two of them apart because it divided them apart, so a renderer that
        # loses the division has nothing to look the joined string up under and spells it a
        # character at a time.
        "安田剛助": {"reading": "ヤスダ コウスケ", "basis": "romaji", "reading_basis": "stated",
                 "id": "c01450",
                 "romaji": {"macron": "Yasuda Kōsuke", "double": "Yasuda Kousuke",
                            "plain": "Yasuda Kosuke"}},
        "文尾文": {"reading": "フミオ アヤ", "basis": "romaji", "reading_basis": "stated",
                "romaji": {"macron": "Fumio Aya", "double": "Fumio Aya", "plain": "Fumio Aya"}},
        "たいぼく": {"reading": "タイボク", "basis": "romaji",
                 "romaji": {"macron": "Taiboku", "double": "Taiboku", "plain": "Taiboku"}},
        "未来電機": {"reading": "ミライデンキ", "basis": "romaji",
                 "romaji": {"macron": "Miraidenki", "double": "Miraidenki",
                            "plain": "Miraidenki"}},
        # A ・ INSIDE ONE PERSON'S NAME, which is the counter-case. Nothing in the corpus credits
        # くろば or Ｕ on their own, so `interpunct.py` settles this string as one person and the
        # store is keyed on the whole of it.
        "くろば・U": {"reading": "クロバユー", "basis": "romaji", "id": "c00909",
                  "romaji": {"macron": "Kuroba U", "double": "Kuroba U", "plain": "Kuroba U"}},
    },
    "phrases": {"第1話": "Ch. 1"},
    # THE DIVISION AS `adapters/names/creditline.py` SHIPS IT. `p` is the people in order with the
    # job on each; the browser divides nothing itself, which is what stopped `credit()` and
    # `creditNames()` being two readers of one notation.
    "credit_parts": {
        "宮澤伊織/水野英多": {"p": [{"n": "宮澤伊織"}, {"n": "水野英多"}]},
        "[著]仲谷鳰ほか": {"p": [{"n": "仲谷鳰", "r": "著"}, {"etc": 1}]},
        "紬めめ/ツムギメメ": {"p": [{"n": "紬めめ"}], "drop": [" / ツムギメメ"]},
        # A BYLINE LONGER THAN A LINE HOLDS, with a ・ the corpus settled as a separator inside it.
        # Six people, and the work page draws four and counts the rest.
        "安田剛助・文尾文/たいぼく/未来電機/郷本/紀ノ上晟一": {
            "p": [{"n": "安田剛助"}, {"n": "文尾文"}, {"n": "たいぼく"}, {"n": "未来電機"},
                  {"n": "郷本"}, {"n": "紀ノ上晟一"}]},
        # And the same character inside ONE person's name, which the division keeps whole.
        "くろば・U/仲谷鳰": {"p": [{"n": "くろば・Ｕ"}, {"n": "仲谷鳰"}]},
    },
    "publishers": {"一迅社": {"en": "Ichijinsha", "basis": "official-jp"}},
    "imprints": {"Yurihime comics": {"id": "yurihime", "name": "コミック百合姫"}},
}


def main(s):
    # ── the ruling table, which the lint beside this reads as well ────────────────────────────
    #
    # Two sets and a relation between them, so both halves have to be checkable without node.
    paths = {p for surface in interface.SURFACES for p in surface.ruled_paths}
    s.check("works[].title.ja" in paths,
            "the bibliographic record's title is a ruled surface; it is the field the 発売 tab "
            "labelled a volume from while every check was green")
    s.check("series[].print[].imprint" in paths,
            "a nested path is ruled at the depth the data holds it")
    s.eq(sorted(interface.unruled({"series": [{"work": "雨夜の月"}]})), [],
         "a collection holding only ruled fields leaves nothing unruled")
    s.eq(interface.unruled({"series": [{"an_invented_field": "日本語"}]}),
         ["series[].an_invented_field"],
         "a field carrying Japanese that nothing has ruled on is reported, which is what stops the "
         "list of name fields going stale as passes add to the data")
    s.eq(interface.unruled({"series": [{"an_invented_field": "plain english"}]}), [],
         "and a field with no Japanese in it raises no question")

    # ── the character class, which was wrong and said nothing about it ────────────────────────
    #
    # `豈` has two code points, and the literal in this file held U+8C48 where the compatibility
    # range meant U+F900. The class therefore ran from U+8C48 to U+FAFF and swallowed Hangul, so
    # six credit rows naming Korean artists were counted as Japanese left on an English page. Both
    # ends of every range are pinned here because the fault was invisible by eye.
    for ch, want, why in ((chr(0x3040), True, "the kana block opens"),
                          (chr(0x30ff), True, "and closes"),
                          (chr(0x3400), True, "extension A opens"),
                          (chr(0x9fff), True, "the unified ideographs close"),
                          (chr(0xf900), True, "the compatibility ideographs open"),
                          (chr(0xfaff), True, "and close"),
                          ("싱", False, "Hangul is a script this project makes no claim about"),
                          ("한국어", False, "and a whole Korean word is not Japanese"),
                          (chr(0xa000), False, "nor is Yi, which sits in the gap the range spanned"),
                          ("A", False, "and Latin is not")):
        s.eq(bool(interface.KANA_KANJI.search(ch)), want,
             f"{why}: KANA_KANJI on {ch!r}")
    s.check(interface.JAPANESE_ANY.search("　") and not interface.JAPANESE_ANY.search("싱"),
            "the wider class takes the ideographic space and still leaves Hangul out")

    # ── a trailing [] means each item of that list, and used to mean the list ─────────────────
    #
    # `series[].print[]` was read as `series[].print`, so the walk handed the record branch a
    # SERIES row with the whole print list beside it. A series row carries no publisher, so every
    # one of 2,520 volume blocks was skipped and the surface reported clean having rendered
    # nothing.
    rows = {"series": [{"work": "カナリア",
                        "print": [{"publisher": "一迅社", "imprint": "Yurihime comics"}]}]}
    s.eq([v for _row, v in interface._values_at(rows, "series[].print[]")],
         [{"publisher": "一迅社", "imprint": "Yurihime comics"}],
         "the walk reaches each print block, not the list holding them")
    _calls, _about = interface.calls_for(rows)
    s.check(any(s_.path == "series[].print[]" for s_, _v in _about),
            "so the publisher names on a volume row are rendered rather than silently skipped")

    calls, about = interface.calls_for({"works": [{"title": {"ja": "怪異部 : M県Y市の怪現象について"},
                                                  "creator": "[著]やまじえびね"}]})
    s.check(("workLabel", {"title": {"ja": "怪異部 : M県Y市の怪現象について"},
                           "creator": "[著]やまじえびね",
                           "work": "怪異部 : M県Y市の怪現象について"}) in calls,
            "a title living somewhere else on the row is handed to workLabel as `work`, which is "
            "what renderReleases does")
    s.check(any(c[0] == "creditNames" for c in calls),
            "and the credit field goes to the function the 発売 tab renders it with")
    s.eq(len(calls), len(about), "every call is accounted for by something saying what it was")

    if not interface.available():
        print("  note: node or kari/app.js is not here, so nothing was rendered")
        return

    # ── the interface itself, running ─────────────────────────────────────────────────────────
    iface = interface.Interface(names=NAMES, prefs={"LANG": "en"})
    got = iface.labels([
        ("workLabel", {"work": "怪異部～M県Y市の怪現象について～"}),
        ("workLabel", {"work": "怪異部 : M県Y市の怪現象について"}),
        ("workLabel", {"work": "恋愛遺伝子XX : 完全版"}),
        ("workLabel", {"work": "雨夜の月"}),
        ("phraseOf", "第１話"),
        ("imprintOf", "Yurihime comics"),
        ("pubBoth", "一迅社"),
    ])
    s.eq(got[0], "The Uncanny Club",
         "a title the store holds under its own spelling renders in English")
    s.eq(got[1], "Kaiibu : M Ken Y Shi no Kaigenshou ni Tsuite[?]",
         "THE CATALOGUED SPELLING DOES NOT REACH THE CURATED TITLE. app.js does not strip a "
         "subtitle to find the base title, and check.py's transcription claimed it did, which is "
         "why eight works reached a reader in Japanese with the invariant green. The fix is a key "
         "in the shipped map, and this is the assertion that the interface has not silently grown "
         "the fallback instead. What it falls to now is the floor, marked")
    s.check("怪異部" not in got[1], "and what it must never fall to is the Japanese")
    s.eq(got[2], "The Romance Gene XX (Complete Edition)",
         "an edition marker from the closed set IS glossed beside its base title, so a rule "
         "generalised from the line above would be wrong in the other direction")
    s.eq(got[3], "Amayo no Tsuki", "a record with only a reading renders as a romanisation")
    s.eq(got[4], "Ch. 1", "a chapter name comes from the phrase map")
    s.eq(got[5], "コミック百合姫", "an imprint string resolves to the line the registry names")
    s.eq(got[6], "Ichijinsha", "a publisher renders through the shipped map")

    # ── THE FLOOR, WHICH IS THE THING AN ENGLISH PAGE MAY NOT FALL BELOW ─────────────────────
    #
    # The owner's ruling: an unclear romanisation with an explanatory tooltip is REQUIRED wherever
    # the alternative is Japanese under an English heading. So these ask the real renderer for the
    # cases that used to fall through, and the last of them asks what happens when even the floor
    # has nothing, because that answer must also not be Japanese.
    floored = iface.values([("authorLabel", {"author": "やまじえびね"}),
                            ("credit", "[著]やまじえびね")])
    s.check("Yamajiebine" in floored[0],
            "a name the store has no record for is spelled from the floor")
    s.check("class=\"unc floor\"" in floored[0],
            "and it is marked, so a reader can see the spelling is ours")
    s.check(FLOOR_SENTENCE in floored[0],
            "with a tooltip saying why, which is what the ruling asks for")
    s.check("class=\"unc floor\"" in floored[1],
            "and a credit line composed in place marks the name inside it the same way")
    s.check("やまじえびね" not in iface.labels([("credit", "[著]やまじえびね")])[0],
            "no part of a compound line stays Japanese while its neighbours romanise")

    # ── A READING NOBODY WITH STANDING TYPED IS ON THE FLOOR AS WELL ─────────────────────────
    #
    # THE OWNER'S CORRECTION OF 2026-08-09, WHICH IS WHAT THIS PINS. The Wikidata ruling was
    # implemented on a mistyped word and read as lifting these names out of the fallback population,
    # so 73 people stopped being counted as names nobody had settled while still being romanised off
    # kana an anonymous editor typed. The corrected ruling gives them the better string and leaves
    # them where they were, and `renderings resting on a mechanical romanisation` is what counts
    # them: 44 before, 628 after.
    wd = iface.values([("authorLabel", {"author": "やぶうち優"})])
    s.check("Yabūchi Yū" in wd[0],
            "the community database's kana are what the name is spelled from, which is the whole "
            "of what the ruling buys: without them this is Yabuuchiyuu or an analyser's guess")
    s.check('class="unc floor"' in wd[0],
            "and the rendering carries the floor's own class, because a Wikidata string does not "
            "close the gap and the count of the gap is taken off this markup")
    s.check("community-edited database" in wd[0],
            "with the tooltip naming the database, which is where a reader goes to settle it")
    s.check(FLOOR_SENTENCE not in wd[0],
            "and not the generic floor sentence, which would drop the one thing a reader can act "
            "on to buy a wording the class already carries")
    s.check('class="unc floor"' not in iface.values(
                [("authorLabel", {"author": "仲谷鳰"})])[0],
            "while a reading no community database is behind takes no floor mark at all, so the "
            "class still separates the two populations it is counted on")

    # NOTHING IN THE MAP AT ALL, which is the state the build makes unreachable and this file has
    # to pin anyway: a hole in the floor comes out as something a reader can see, never as kana.
    bare = interface.Interface(names={"titles": {}, "authors": {}, "phrases": {}},
                               prefs={"LANG": "en"})
    s.check(not interface.KANA_KANJI.search(bare.labels([("authorLabel", {"author": "雨夜"})])[0]),
            "a renderer handed no floor at all still returns no kana and no kanji")

    japanese = iface.with_prefs(LANG="ja").labels([("workLabel", {"work": "雨夜の月"})])
    s.eq(japanese[0], "雨夜の月",
         "and in Japanese the same row renders as itself, so the preference is really being set "
         "rather than being ignored on a name app.js does not hold")

    s.eq(iface.values([("foldKey", "4話②＜完＞")])[0], "4話2<完>",
         "the browser's own fold, returned whole. `labels` strips tags and read <完> as an "
         "element, which reported a disagreement with the Python fold that only the harness had")

    # ── a name romanised as one word says so, and only to the reader who needs telling ───────
    #
    # THE ASYMMETRY IS THE RULE, not an oversight. A reader in Japanese has the name itself and can
    # see 太陽まりい; a reader in English has `Taiyōmarii` and nothing to fall back on. So the note
    # is attached in English and the Japanese line is left alone, which is the same reasoning §5d
    # gives for the unverified-reading mark and the same reasoning `uncertainMark` gives for
    # narrowing its own trigger in Japanese.
    undiv = iface.values([("authorLabel", {"author": "太陽まりい"}),
                          ("authorLabel", {"author": "仲谷鳰"})])
    s.eq(iface.labels([("authorLabel", {"author": "太陽まりい"})])[0], "Taiyōmarii",
         "the run-on romanisation is what is shown, because a division nobody states is a guess")
    s.check("No source states where this name divides" in undiv[0],
            "and it carries a note saying why it runs together")
    s.check("title=" not in undiv[1],
            "a name whose reading divides carries no note, so the note stays worth reading")
    s.check("title=" not in iface.with_prefs(LANG="ja").values(
                [("authorLabel", {"author": "太陽まりい"})])[0],
            "and in Japanese nothing is said, because the reader has the name")

    # ── a credit is a link, and every name in it still goes through authorLabel ──────────────
    #
    # RUN AGAINST THE REAL FILE rather than described. A credit page is the first thing on this
    # site whose whole content is a list of other records, so a link that renders and opens
    # nothing is the failure it makes newly possible, and the address is built from the `id` the
    # build now ships on each name.
    linked = iface.labels([("linkedCredits", {"author": "仲谷鳰"}),
                           ("linkedCredits", {"author": "宮澤伊織 / 水野英多"}),
                           ("linkedCredits", {"author": "宮澤伊織"})])
    html = iface.values([("linkedCredits", {"author": "仲谷鳰"}),
                         ("linkedCredits", {"author": "宮澤伊織 / 水野英多"}),
                         ("linkedCredits", {"author": "宮澤伊織"})])
    s.eq(linked[0], "Nakatani Nio",
         "a single credit is still rendered by authorLabel, so the reader's language reaches it")
    s.check('href="/kari/credit/c00173/"' in html[0],
            "and it is a link to the record the registry minted for it")
    s.eq(linked[1], "Miyazawa Iori / Mizuno Hideta",
         "a credit line naming two people renders both, separated as the field separated them")
    s.check('href="/kari/credit/c00500/"' in html[1],
            "and the one the registry answers for is a link")
    s.check("credit/" not in html[2],
            "a credit with no identifier renders as before and is not a link, which is a state "
            "rather than a gap: the registry is minted from the works list and the store holds "
            "records nothing credits")
    ja_linked = iface.with_prefs(LANG="ja").values([("linkedCredits", {"author": "仲谷鳰"})])
    s.check("仲谷鳰" in ja_linked[0] and 'href="/kari/credit/c00173/"' in ja_linked[0],
            "and in Japanese it is the same address under the name as written")

    # ── a credit line, divided by the build and rendered in place ────────────────────────────
    #
    # RUN AGAINST THE REAL FILE. Each of these is a shape one of the two renderers this replaced
    # could not read: a role in a bracket with no gloss in the six-word table, the word that closes
    # an anthology credit, and a reading printed beside the name it reads.
    credits = iface.labels([("credit", "[著]仲谷鳰 ほか"),
                            ("creditNames", "[著]仲谷鳰 ほか"),
                            ("credit", "紬めめ / ツムギメメ"),
                            ("roleWord", "キャラクター原案・漫画"),
                            ("roleWord", "校正")])
    s.eq(credits[0], "[author]Nakatani Nio and others",
         "the catalogue tab glosses the role, renders the name through the store and says in "
         "English that the field names some of its contributors")
    s.eq(credits[1], "Nakatani Nio / and others",
         "and the 発売 tab lists the people the build divided out, which is what that tab shows")
    s.eq(credits[2], "Tsumugi Meme",
         "a reading printed beside its own name is taken off an English page, because kana beside "
         "a romanisation is the same name twice in a script the page is not written in")
    s.eq(credits[3], "character design and art",
         "A COMPOUND ROLE IS COMPOSED FROM ITS ATOMS. Listing every combination is what the old "
         "table did at a smaller size, and it is why it held キャラクターデザイン原案 and neither "
         "of its halves")
    s.eq(credits[4], "proofreading", "and an atom the corpus states once is still glossed")
    ja_credit = iface.with_prefs(LANG="ja").labels([("credit", "[著]仲谷鳰 ほか")])
    s.eq(ja_credit[0], "[著]仲谷鳰 ほか",
         "in Japanese the field is the field, notation and all")

    # ── the work page's byline, which is the route the `????` fault reached a reader by ────────
    #
    # `creditLine` shortens a byline naming more people than a line holds. It used to shorten by
    # cutting the FIELD on the slash and passing the pieces on as a field of their own, and that
    # string is in no map: the shipped division went missing, the whole line dropped to the floor,
    # and `安田剛助・文尾文` came out `???? · Bun?Bun` on w01700 for two artists whose readings
    # openBD and the publisher both state. It counts off the division now.
    long_field = "安田剛助・文尾文 / たいぼく / 未来電機 / 郷本 / 紀ノ上晟一"
    line = iface.labels([("creditLine", {"author": long_field}),
                         ("creditLine", {"author": "くろば・Ｕ / 仲谷鳰"}),
                         ("creditLine", {"author": "宮澤伊織 / 水野英多"})])
    s.check(line[0].startswith("Yasuda Kōsuke / Fumio Aya / Taiboku / Miraidenki"),
            "the work page draws the first four people the BUILD divided out, so a ・ the corpus "
            "settled as a separator puts two of them either side of it")
    s.check("?" not in line[0].replace("[?]", ""),
            "and nothing in the line is spelled a character at a time, which is what a lost "
            "division looks like on the page")
    s.check(line[0].endswith("and 2 others"),
            "the rest are counted, and counted off the division rather than off the separators: "
            "this field writes six people and holds only five slashes")
    s.eq(line[1], "Kuroba U / Nakatani Nio",
         "A ・ INSIDE A NAME IS NOT A SEPARATOR. Nothing credits くろば or Ｕ alone, so the corpus "
         "settles that string as one person and the line keeps it whole")
    s.eq(line[2], "Miyazawa Iori / Mizuno Hideta",
         "a byline shorter than the limit is drawn whole, by the same walk")

    s.raises(interface.Unavailable,
             lambda: interface.render([["noSuchFunction", 1]], names=NAMES),
             "asking for a function kari/app.js does not have raises rather than answering empty, "
             "because a renderer that returned nothing would look exactly like a clean page")
    s.raises(interface.Unavailable,
             lambda: interface.render([["workLabel", {}]], names=NAMES, prefs={"NOT_A_PREF": 1}),
             "and so does a preference app.js does not hold, which would otherwise make every "
             "check above vacuous by never selecting English at all")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "interface"))
