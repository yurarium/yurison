#!/usr/bin/env python3
"""publishers.py: an English name for a publisher and an imprint, out of data.

COVERS = ['adapters/names/publishers.py']

The cataloguing around a publisher name is what makes this hard, and it is the same notation the
interface strips for display. Getting the two out of step is invisible: a key that does not match
what the interface asks for renders as Japanese, which is also what an unnamed publisher does.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit
from adapters.names import publishers as P


def main(s):
    # ── the cataloguing comes off, and only the cataloguing ────────────────────────────────────
    s.eq(P.publisher_of("[頒布]講談社"), "講談社", "a distributor marker is not part of the name")
    s.eq(P.publisher_of("講談社 (発売)"), "講談社", "and neither is a release note")
    s.eq(P.publisher_of("[頒布]KADOKAWA (発売)"), "KADOKAWA", "both at once")
    s.eq(P.publisher_of("一迅社"), "一迅社", "a plain name is left alone")

    # ── one imprint, however the record spells it ──────────────────────────────────────────────
    #
    # MADB catalogues 百合姫 at least six ways. Six spellings in one list read as six imprints,
    # which is the opposite of what an imprint is for.
    for spelling in ("コミック百合姫", "百合姫コミックス", "IDコミックス. Yurihime comics = コミック百合姫",
                     "IDコミックス／Yuri-hime comics", "IDコミックス　／　Yurihime comics"):
        s.eq(P.imprint_of(spelling), "コミック百合姫", f"one imprint under {spelling[:24]}")
    s.eq(P.imprint_of("IDコミックス"), "IDコミックス",
         "the umbrella line stands alone when it is all the record says")
    s.eq(P.imprint_of("まんがタイムKRコミックス"), "まんがタイムKRコミックス",
         "an imprint with no alias is itself")

    # THE RULE THAT WAS TRIED AND REJECTED, pinned so nobody re-derives it. `IDコミックス／Yuri-hime
    # comics` is one imprint written twice, once in each script, so reading the Latin half off the
    # record would name a third of the imprint rows for free. `GP-KIDS/高菜しんの` has the same
    # shape and is an imprint beside a person, so the rule publishes one party's name as another's.
    s.eq(P.imprint_of("GP-KIDS/高菜しんの"), "高菜しんの",
         "a record naming an imprint and a person is not a name written twice")

    # ── ONE CATALOGUED STRING IN TWO FIELDS IS TWO NAMES ───────────────────────────────────────
    #
    # The census keyed its slots on the catalogued string alone, so a string filed in both fields
    # got whichever normalisation was read first and the other was merged into it. `GP-KIDS/高菜
    # しんの` is exactly that: itself as a publisher, 高菜しんの as an imprint. The map therefore
    # held no 高菜しんの and app.js asked for a key nothing answered. Found by normalising the
    # corpus the way the browser does, because every measure inside the pipeline shared this
    # census and none of them could see it.
    census = P.corpus_names_from_rows(
        [{"print": [{"publisher": "GP-KIDS/高菜しんの", "imprint": "GP-KIDS/高菜しんの"}]}])
    s.eq(sorted(i["shown"] for i in census.values()), ["GP-KIDS/高菜しんの", "高菜しんの"],
         "both normalisations of one catalogued string survive the census")
    shown = P.render({}, {"高菜しんの": {"romaji": {"macron": "Takana Shinno"}}}, census)
    s.eq(shown.get("高菜しんの", {}).get("en"), "Takana Shinno",
         "so the interface finds the key its own imprint rule produces")

    # AND THE RECORD ABOUT THE NAME BEATS THE RECORD ABOUT THE CATALOGUE LINE. The whole string is
    # a publisher record in its own right, and asking with it first answered the imprint with the
    # publisher's rendering, so one person was spelt two ways on one row.
    lined = P.render({"GP-KIDS/高菜しんの": {"en": "GP - KIDS / Takana Shinno", "basis": "romaji"}},
                     {"高菜しんの": {"romaji": {"macron": "Takana Shinno"}}}, census)
    s.eq(lined.get("高菜しんの", {}).get("en"), "Takana Shinno",
         "the imprint is the person, not the line the cataloguer typed")
    s.eq(lined.get("GP-KIDS/高菜しんの", {}).get("en"), "GP - KIDS / Takana Shinno",
         "and the publisher field is still the whole catalogued string")

    # ── what reaches the interface ─────────────────────────────────────────────────────────────
    names = {("publisher", "[発売]講談社"):
                 {"kind": "publisher", "raw": "[発売]講談社", "shown": "講談社", "volumes": 102},
             ("imprint", "IDコミックス　／　Yuri-hime comics"):
                 {"kind": "imprint", "raw": "IDコミックス　／　Yuri-hime comics",
                  "shown": "コミック百合姫", "volumes": 120},
             ("publisher", "芳文社"):
                 {"kind": "publisher", "raw": "芳文社", "shown": "芳文社", "volumes": 187}}
    store = {"講談社": {"en": "Kodansha", "basis": "official-jp", "source": "kodansha.co.jp"},
             "コミック百合姫": {"en": "Comic Yuri Hime", "basis": "official-jp",
                                "source": "ichijinsha.co.jp"}}
    got = P.render(store, {}, names)

    # KEYED BOTH WAYS ON PURPOSE. The interface normalises in the browser and this normalises in
    # Python, so the two implementations can drift; a raw key means a drift costs a lookup that the
    # other key still answers rather than a publisher silently rendering as Japanese.
    s.eq(got["講談社"]["en"], "Kodansha", "a curated name reaches the normalised key")
    s.eq(got["[発売]講談社"]["en"], "Kodansha", "and the raw catalogued string")
    s.eq(got["講談社"]["basis"], "official-jp", "with the basis it was recorded under")
    s.eq(got["コミック百合姫"]["en"], "Comic Yuri Hime",
         "an imprint is found under the name its eight spellings collapse to")
    s.eq(got["IDコミックス　／　Yuri-hime comics"]["en"], "Comic Yuri Hime",
         "and under the spelling the record actually used")
    s.check("芳文社" not in got, "a name with no English is absent rather than romanised")

    # KATAKANA IS NOT ROMANISED HERE, and that is the point. ナンバーナイン is a company called
    # No9; syllable-by-syllable it comes out Nanbānain, which transliterates a transliteration.
    # A record with neither an English name nor a reading renders nothing at all, so this file
    # never invents a spelling: the romanisation comes from the reading, which comes from the pass.
    kana = {("publisher", "ナンバーナイン"): {"kind": "publisher", "raw": "ナンバーナイン",
                                              "shown": "ナンバーナイン", "volumes": 540}}
    s.check("ナンバーナイン" not in P.render({}, {}, kana),
            "a katakana name with no source stays Japanese rather than being romanised")

    # ── one producer for one fact ──────────────────────────────────────────────────────────────
    #
    # 25 print rows name their own author as the publisher, because a self-published work has
    # nobody else to name. The same string was being spelt by two maps with nothing forcing
    # agreement, and two of them had drifted on the live site: ガレットワークス was `Galette Works`
    # beside its books and `Garettowākusu` beside its name.
    selfpub = P.corpus_names_from_rows(
        [{"print": [{"publisher": "嵩乃朔"}, {"publisher": "ガレットワークス"}]}])
    people = {"嵩乃朔": {"romaji": {"macron": "Takano Saku", "plain": "Takano Saku"},
                          "basis": "romaji"},
              "ガレットワークス": {"romaji": {"macron": "Garettowākusu"}, "basis": "romaji"}}
    pub = {"ガレットワークス": {"en": "Galette Works", "basis": "official-jp"}}
    both = P.render(pub, people, selfpub)
    s.eq(both["嵩乃朔"]["en"], "Takano Saku",
         "a publisher who is a person we already spell is spelt that way and not a second way")
    s.eq(both["嵩乃朔"]["basis"], "romaji", "and it says the Latin is ours")
    s.eq(both["嵩乃朔"]["romaji"]["plain"], "Takano Saku",
         "with the styles carried through, so the reader's romanisation control reaches it")
    s.eq(both["ガレットワークス"]["en"], "Galette Works",
         "a publisher-side source outranks the person's romanisation of the same string")

    # A RECORD FROM BEFORE `basis` EXISTED IS NOT OFFICIAL. Calling an unlabelled name official
    # asserts a source that was never recorded, and the mark exists to keep those apart.
    s.eq(P.english("x", "x", {"x": {"en": "Ex"}}, {})["basis"], "romaji",
         "an English name with no recorded basis is treated as ours, not as the company's")
    s.eq(P.english("x", "x", {}, {}), None, "and a string nothing holds renders nothing")

    # THE COUNTER-CASE FOR THE STYLE CONTROL. 青騎士コミックス is written Aokishi Comics, because
    # コミックス is the English word it stands for; spelling the reading out gives Aokishi
    # Komikkusu. Shipping both would let the macron toggle replace a reviewed name with a
    # transliteration of it, for the readers who had touched the control and nobody else.
    _named = P.english("青騎士コミックス", "青騎士コミックス",
                       {"青騎士コミックス": {"en": "Aokishi Comics", "basis": "romaji",
                                              "romaji": {"macron": "Aokishi Komikkusu"}}}, {})
    s.eq(_named["en"], "Aokishi Comics", "a reviewed name is what is shown")
    s.check("romaji" not in _named,
            "and the styles do not travel where they would replace it with the reading spelt out")
    _spelt = P.english("百合コレ", "百合コレ",
                       {"百合コレ": {"en": "Yuri Kore", "basis": "romaji",
                                     "romaji": {"macron": "Yuri Kore", "plain": "Yuri Kore"}}}, {})
    s.eq(_spelt["romaji"]["plain"], "Yuri Kore",
         "they do travel where the name shown IS the romanisation")

    # ── THE SAME NAME UNDER TWO TYPESETTINGS ───────────────────────────────────────────────────
    #
    # The store is keyed by the strings the CORPUS carries and the imprint registry names each line
    # NFKC-normalised with ordinary spaces, so six lines carrying a reviewed English name and a
    # sourced reading rendered in Japanese: the exact lookup answered for `ＦＵＺコミックス` and not
    # for `FUZコミックス`, and for `MFC　キューンシリーズ` with an ideographic space and not for
    # `MFC キューンシリーズ` with a plain one.
    _typeset = {"ＦＵＺコミックス": {"en": "FUZ Comics", "basis": "official-jp"},
                "MFC　キューンシリーズ": {"en": "MFC Cune Series", "basis": "romaji"}}
    s.eq(P.english("FUZコミックス", "FUZコミックス", _typeset, {})["en"], "FUZ Comics",
         "full-width letters and ordinary ones are one name")
    s.eq(P.english("MFC キューンシリーズ", "MFC キューンシリーズ", _typeset, {})["en"],
         "MFC Cune Series", "and so are an ideographic space and a plain one")
    s.eq(P.unreadable(
        P.corpus_names_from_rows([{"print": [{"publisher": "KADOKAWA",
                                              "imprint": "MFC キューンシリーズ"}]}]),
        _typeset, {}), [],
        "and the reading pass does not queue a name the renderer can already answer")

    # AND THE FOLD DOES NOT REACH ACROSS A REAL DIFFERENCE. `4コマkingsぱれっとcomics` and
    # `4コマKINGSぱれっとコミックス` are two spellings of one line and differ in CONTENT, not in
    # typesetting, so each keeps its own entry and neither answers for the other.
    s.eq(P.english("4コマKINGSぱれっとコミックス", "4コマKINGSぱれっとコミックス",
                   {"4コマkingsぱれっとcomics": {"en": "4-koma kings palette comics",
                                                 "basis": "romaji"}}, {}), None,
         "comics against コミックス is a different string and not a different typesetting")
    # AN EXACT RECORD STILL WINS, because a fold names a family and a key names one member.
    s.eq(P.english("MFC キューンシリーズ", "MFC キューンシリーズ",
                   dict(_typeset, **{"MFC キューンシリーズ": {"en": "Exact", "basis": "romaji"}}),
                   {})["en"], "Exact", "the record written about this string outranks the fold")

    # ── what the reading pass is asked to read ─────────────────────────────────────────────────
    #
    # Only what nothing else can reach. Reading every publisher name would put an analyser's guess
    # and its note on top of every curated record, which loses the reason somebody wrote it down.
    queue = P.unreadable(
        P.corpus_names_from_rows([{"print": [{"publisher": "芳文社", "imprint": "百合コレ"},
                                             {"publisher": "嵩乃朔", "imprint": "KADOKAWA"}]}]),
        {"芳文社": {"en": "Houbunsha", "basis": "official-jp"}},
        {"嵩乃朔": {"reading": "タカノ サク"}})
    s.eq(queue, ["百合コレ"], "only a Japanese name that neither store can answer is queued")

    # ── the queue ──────────────────────────────────────────────────────────────────────────────
    todo = P.unnamed(got, names)
    s.eq([n for _v, n, _k in todo], ["芳文社"], "only the unnamed are queued")
    s.eq(todo[0][0], 187, "counted by volumes, so the queue opens on what a reader sees most")

    three = {("publisher", "講談社"):
                 {"kind": "publisher", "raw": "講談社", "shown": "講談社", "volumes": 20},
             ("publisher", "[発売]講談社"):
                 {"kind": "publisher", "raw": "[発売]講談社", "shown": "講談社", "volumes": 102},
             ("publisher", "[頒布]講談社"):
                 {"kind": "publisher", "raw": "[頒布]講談社", "shown": "講談社", "volumes": 80}}
    s.eq(P.unnamed({}, three), [(202, "講談社", "publisher")],
         "one publisher spelled three ways is one entry in the queue, not three")

    # ── THE READING BEHIND A ROMANISATION ──────────────────────────────────────────────────────
    #
    # `publishers with no English` fell to zero by romanising, and a romanisation is the reading
    # spelt in Latin, so the outstanding work moved from the rendering to the sourcing and nothing
    # counted it. This is what counts it, and the cases below are the four that decide the rule.
    shipped = {"まんがタイムKRコミックス": {"en": "Manga Time KR Comics", "basis": "romaji",
                                            "unverified": True},
               "踏月": {"en": "Tōtsuki", "basis": "romaji", "unverified": True,
                        "uncertain": True},
               "宙出版": {"en": "Ohzora Shuppan", "basis": "romaji"},
               "講談社": {"en": "Kodansha", "basis": "official-jp"},
               "青騎士コミックス": {"en": "Aokishi Comics", "basis": "romaji",
                                    "uncertain": True}}
    s.eq(P.unsettled_readings(shipped),
         ["まんがタイムKRコミックス", "踏月", "青騎士コミックス"],
         "a romanisation carrying either mark is counted, and a settled one is not")
    s.check("講談社" not in P.unsettled_readings(shipped),
            "a name the house signs itself with is not a romanisation and cannot be counted here")
    s.check("宙出版" not in P.unsettled_readings(shipped),
            "and neither is a romanisation whose reading a source states, which is the only way "
            "this number is allowed to fall")
    s.eq(P.unsettled_readings({}), [], "an empty map is no answer rather than a bad one")

    # ── WHICH FIELDS HOLD A NAME A READER SEES ─────────────────────────────────────────────────
    #
    # The queue here and `publishers with no English` in check.py both walk a print row, and both
    # walked their own list of fields until one of them gained `distributor` and the other did not.
    # One list now, and this pins what it holds so a field added to the row reaches both or
    # neither (STANDING-INSTRUCTIONS §3).
    s.eq([f for f, _n in P.NAME_FIELDS], ["publisher", "distributor", "imprint"],
         "the publisher, the distributor and the imprint are all shown, so all are queued")
    s.check(all(n is P.publisher_of for f, n in P.NAME_FIELDS if f != "imprint"),
            "a distributor is a publisher's name in another seat and normalises the same way")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.publishers"))
