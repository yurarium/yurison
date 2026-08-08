#!/usr/bin/env python3
"""credits.py: a name and its own reading are one person."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import credits  # noqa: E402

COVERS = ["adapters/names/credits.py"]

STORE = {
    "蓬餅": {"reading": "ヨモギモチ"},
    "矢坂しゅう": {"reading": "ヤサカシュウ"},
    "焼肉定食": {"reading": "ヤキニク テイショク"},
    "一迅社": {"reading": "イチジンシャ"},
    "田口囁一": {"reading": "タグチショウイチ"},
    "原田重光": {"reading": "ハラダシゲミツ"},
}


def main(s):
    # HTML ENTITIES AND PAGE FURNITURE. A rendered-page capture handed over a Follow button as a
    # credit, and an ampersand hidden behind an escape split one credit into what looked like junk.
    s.eq(credits.split_credits("&nbsp;フォローする")[0], [],
         "a control's own label is not a credit")
    s.eq(credits.split_credits("大島永遠&amp;大島智")[0], ["大島永遠&大島智"],
         "an escaped ampersand is unescaped and the credit survives whole")
    s.eq(credits.split_credits("フォローする / 山田太郎")[0], ["山田太郎"],
         "furniture beside a real credit drops and the person stays")
    # AND A NAME CONTAINING THE WORD IS A NAME. The reject list is exact matches only.
    s.eq(credits.split_credits("フォロワーの話")[0], ["フォロワーの話"],
         "a name containing a control's word is still a name")

    # THE CASE THIS WAS WRITTEN FOR. One string in two scripts, with the reading spaced.
    s.eq(credits.dedupe("おにぎりパクパク / オニギリ パクパク"), "おにぎりパクパク",
         "a kana fold of the name beside it is the same person")

    # The kanji case, which no fold can see and only the store's reading settles.
    s.eq(credits.dedupe("蓬餅 / ヨモギモチ", STORE), "蓬餅",
         "a stored reading of the name beside it is the same person")
    s.eq(credits.dedupe("矢坂しゅう / ヤサカシュウ", STORE), "矢坂しゅう",
         "and so is one whose name is partly kana")

    # A reading is word-separated and a name is not, so the space cannot be the difference.
    s.eq(credits.dedupe("焼肉定食 / ヤキニク テイショク", STORE), "焼肉定食",
         "a spaced reading still matches the name it reads")

    # Two credits written four times: the readings go and the people stay, in order.
    s.eq(credits.dedupe("一迅社 / 田口囁一 / イチジンシャ / タグチショウイチ", STORE),
         "一迅社 / 田口囁一", "every restatement goes and the order of the people is kept")

    # THE COUNTER-CASE, AND THE REASON THE SCRIPT IS NOT THE TEST. extract.people drops any
    # all-katakana part, which would delete each of these, and every one of them is a person.
    for name in ("サブロウタ", "コダマナオコ", "アキリ", "ヨルモ"):
        s.eq(credits.dedupe(name), name, f"a katakana pen name is a person: {name}")
    s.eq(credits.dedupe("コダマナオコ / サブロウタ"), "コダマナオコ / サブロウタ",
         "two katakana pen names are two people")

    # A second person is not dropped merely for following a name.
    s.eq(credits.dedupe("原田重光 / 蘇募ロウ", STORE), "原田重光 / 蘇募ロウ",
         "a name that does not read the one before it survives")

    # Degenerate input comes back unchanged rather than raising.
    s.eq(credits.dedupe(""), "", "an empty field is empty")
    s.eq(credits.dedupe(None), "", "a missing field is empty")
    s.eq(credits.dedupe("梵辛"), "梵辛", "one credit is returned as it was given")

    # An exact repeat is not a reading, and is still one person.
    s.eq(credits.dedupe("梵辛 / 梵辛"), "梵辛", "the same name twice is one credit")

    s.eq(credits.doubled("蓬餅 / ヨモギモチ", STORE), 1, "the measure counts what it drops")
    s.eq(credits.doubled("原田重光 / 蘇募ロウ", STORE), 0, "and counts nothing where nothing goes")

    # A CAPTURED CREDIT THAT CANNOT BE A NAME. Each of these reached an author field from a page
    # title whose middle field was not the author.
    for junk in ("#1(1)", "７", "第3話", "12", "(2)", "--"):
        s.check(not credits.is_a_person(junk), f"not a person: {junk}")
    # And the counter-case, because a rule keyed on "contains a digit" deletes real people.
    for real in ("タイザン5", "梵辛", "おにぎりパクパク", "Ｍａｇｐｉｅ", "帯屋ミドリ2"):
        s.check(credits.is_a_person(real), f"a person: {real}")

    # ── the pair the store could not see ─────────────────────────────────────────────────────
    # w01478 shipped `田口ケンジ / タグチケンジ` to a reader. The fold cannot see it because the
    # name holds a kanji, and the store cannot either because a credit line is never fed to the
    # naming pass, so neither half is in it. A reader of names settles it.
    ANALYSED = {"田口ケンジ": "タグチケンジ", "原田重光": "ハラダシゲミツ",
                "コダマナオコ": "コダマナオコ", "蘇募ロウ": "ソボロウ"}
    read = ANALYSED.get
    s.eq(credits.dedupe("田口ケンジ / タグチケンジ", {}, read), "田口ケンジ",
         "an analysed reading collapses the pair the store knows nothing about")
    s.eq(credits.dedupe("田口ケンジ / タグチケンジ", {}), "田口ケンジ / タグチケンジ",
         "and without a reader it survives, which is what shipped")

    # The counter-cases that decide whether the reader may be trusted at all. It can only ever
    # collapse a pair it read EXACTLY onto its neighbour, so a wrong reading keeps both credits.
    s.eq(credits.dedupe("コダマナオコ / サブロウタ", {}, read), "コダマナオコ / サブロウタ",
         "two katakana pen names stay two people with a reader in play")
    s.eq(credits.dedupe("原田重光 / 蘇募ロウ", {}, read), "原田重光 / 蘇募ロウ",
         "and so do a kanji name and the katakana name of somebody else")
    s.eq(credits.dedupe("田口ケンジ / タグチケンジ", {}, lambda n: "マチガイ"),
         "田口ケンジ / タグチケンジ", "a reader that gets it wrong changes nothing")

    # THE MEASURE MUST NOT SHARE THE FIX'S BLIND SPOT. `doubled` reads zero for the case above
    # when the store is empty, which is exactly why the budget was green while it was live.
    s.eq(credits.doubled("田口ケンジ / タグチケンジ", {}), 0,
         "the store-based measure is blind to the case the store cannot see")
    s.eq(credits.candidate_doubles("田口ケンジ / タグチケンジ"), 1,
         "the store-free measure sees the shape: katakana beside kanji")
    s.eq(credits.candidate_doubles("原田重光 / アサウラ"), 1,
         "it is a candidate and not a verdict, so two real people of that shape count too")
    s.eq(credits.candidate_doubles("原田重光 / 蘇募ロウ"), 0,
         "and a part holding a kanji cannot be the katakana reading of anything")
    s.eq(credits.candidate_doubles("コダマナオコ / サブロウタ"), 0,
         "two katakana names have no kanji half to be the reading of")
    s.eq(credits.candidate_doubles("原田重光"), 0, "and one credit is no pair at all")

    # ── composing a field from the people in it ──────────────────────────────────────────────
    LATIN = {"basis": "stated", "en": "Akeo", "script": "latin", "verified": True}
    MIKAWA = {"reading": "ミカワ ゴースト", "reading_basis": "stated",
              "romaji": {"macron": "Mikawa Gōsuto", "double": "Mikawa Goosuto",
                         "plain": "Mikawa Gosuto"}}
    MORI = {"reading": "モリ ユウ", "reading_basis": "stated",
            "romaji": {"macron": "Mori Yū", "double": "Mori Yuu", "plain": "Mori Yu"}}
    look = {"Akeo": LATIN, "三河ごーすと": MIKAWA, "森夕": MORI}.get

    # A releases row separates its people with a comma and a series row with a slash. A composer
    # that knew one of them left 49 of 191 release rows rendering their authors in Japanese.
    s.eq(credits.split_credits("おだまさる, 佐島勤, 森夕")[0], ["おだまさる", "佐島勤", "森夕"],
         "a comma-separated credit line names three people")
    s.eq(credits.split_credits("おだまさる, 森夕")[1], ", ",
         "and the separator comes back so the rendering reads like the row it replaces")
    s.eq(credits.split_credits("三河ごーすと / 森夕")[1], " / ", "a slashed field keeps its slash")
    s.eq(credits.split_credits("さりい・Ｂ")[0], ["さりい・Ｂ"],
         "an interpunct is left alone, because it sits inside this name and between other people")

    got = credits.compose("三河ごーすと, 森夕", look)
    s.eq(got["romaji"]["macron"], "Mikawa Gōsuto, Mori Yū",
         "the comma survives into every romanisation")
    s.eq(got["reading"], "ミカワ ゴースト, モリ ユウ", "and into the reading")

    # The Akeo case: in the store, no reading, no romanisation, and correctly so.
    mixed = credits.compose("Akeo / 三河ごーすと", look)
    s.eq(sorted(mixed.get("romaji") or {}), ["double", "macron", "plain"],
         "a Latin credit contributes all three styles rather than emptying the intersection")
    s.eq(mixed["romaji"]["plain"], "Akeo / Mikawa Gosuto", "standing as its own romanisation")
    s.eq(mixed["reading"], "Akeo / ミカワ ゴースト",
         "and the reading no longer opens with an empty part")

    # FURIGANA NOBODY COULD READ IS NOT PUBLISHED. Composing a field prints spans the store has
    # held all along and nothing ever rendered: 電撃G'sマガジン carries で over 電撃G and
    # んげきじーず over s. The part keeps its reading and its romanisation and loses its ruby.
    s.check(credits.readable_ruby([["電撃G", "で"], ["'", None], ["s", "んげきじーず"]]) is None,
            "one kana over a run holding a kanji cannot be read aloud")
    s.eq(credits.readable_ruby([["花", "はな"], ["宮", "みや"]]),
         [["花", "はな"], ["宮", "みや"]], "a run with kana enough is kept as it stands")
    s.check(credits.readable_ruby([["承", "うけたまわ"], ["る", None]]) is not None,
         "and a surprising reading is not an impossible one: 承る is one kanji under five kana")
    s.check(credits.readable_ruby([]) is None, "no spans is nothing to keep")

    BADRUBY = {"reading": "デンゲキジーズマガジン", "reading_basis": "stated",
               "ruby": [["電撃G", "で"], ["'", None], ["s", "んげきじーず"], ["マガジン", None]],
               "romaji": {"macron": "Dengeki G's Magazine", "double": "Dengeki G's Magazine",
                          "plain": "Dengeki G's Magazine"}}
    withbad = credits.compose("電撃G'sマガジン／森夕", {"電撃G'sマガジン": BADRUBY,
                                                        "森夕": MORI}.get)
    s.eq(withbad["ruby"][0], ["電撃G'sマガジン", None],
         "the part with unreadable furigana falls back to its bare surface")
    s.eq(withbad["romaji"]["macron"], "Dengeki G's Magazine / Mori Yū",
         "while its romanisation, which was never in doubt, survives")

    s.check(credits.compose("三河ごーすと / 知らない人", look) is None,
            "one unresolvable credit composes nothing, so the Japanese fallback survives")
    s.check(credits.compose("三河ごーすと", look) is None, "one person is not a composition")
    s.check(credits.compose("", look) is None, "and neither is nothing")

    # ── THE THREE FAULTS BEHIND 192 SERIES ROWS RENDERING JAPANESE IN ENGLISH MODE ─────────────
    #
    # Measured 2026-08-07. Each one is a shape the field splitter could not see, and all three
    # were already handled by inputs.split_authors, which this now asks instead of splitting on a
    # separator list of its own.

    # 126 of the 192 named ONE person with a role after the name, 96 of them 著者. The caller
    # looks the whole field up, `森夕(著者)` matches nothing, and the composer used to decline
    # any field holding a single credit, so the notation had nowhere to come off.
    s.eq((credits.compose("森夕(著者)", look) or {})["romaji"]["macron"], "Mori Yū",
         "a lone credit with a role welded to it resolves to the person")
    s.eq((credits.compose("【漫画】森夕", look) or {})["romaji"]["macron"], "Mori Yū",
         "and so does one with the role in front of it")
    s.check(credits.compose("森夕", look) is None,
            "while a field the notation did not change is still nothing to compose")

    # `原作/大鷹シン 漫画/ホマレ`: the slash separates a ROLE from a NAME here, so splitting on it
    # made 原作 a person.
    s.eq(credits.split_credits("原作/三河ごーすと 漫画/森夕")[0], ["三河ごーすと", "森夕"],
         "a slash between a role and a name is not a slash between two people")
    s.eq(credits.split_credits("原作／三河ごーすと　作画／森夕")[0], ["三河ごーすと", "森夕"],
         "the same field written full-width")

    # `冬眠結(漫画) 橙々(原作)`: two credits with nothing but a space between them.
    s.eq(credits.split_credits("三河ごーすと(漫画) 森夕(原作)")[0], ["三河ごーすと", "森夕"],
         "a role bracket ends a credit, so the space after it separates two people")

    # THE COUNTER-CASES, all four of which the fix has to leave alone.
    s.eq(credits.split_credits("sono.N（SHUEISHA）")[0], ["sono.N"],
         "a bracket that is not a role is dropped, and does not make the credit a role")
    s.eq(credits.split_credits("コダマナオコ(コダマ)")[0], ["コダマナオコ"],
         "a katakana gloss is not a role either")
    s.eq(credits.split_credits("LYCORIS(企画)")[0], ["LYCORIS"], "and 企画 is")
    s.eq(credits.split_credits("原田重光 / 蘇募ロウ")[0], ["原田重光", "蘇募ロウ"],
         "a slash between two names still separates two people")

    # A LONE LATIN CREDIT UNDER NOTATION NEEDS NO STORE RECORD. `murata(著者)` holds a kanji, so
    # it counts as a Japanese surface and was counted as a row with nothing to show; the person is
    # `murata` and that is already its own romanisation.
    s.eq((credits.compose("murata(著者)", look) or {})["romaji"]["plain"], "murata",
         "a Latin name under a role is its own romanisation")
    s.check(credits.already_latin("森夕") is None, "while a Japanese one is not")

    # ── ANNOTATING IS NOT REWRITING ────────────────────────────────────────────────────────────
    #
    # Furigana rides on the field AS WRITTEN. Composing the spans by joining the people with a
    # separator covered `三河ごーすと / 森夕` for a field reading `原作/三河ごーすと 漫画/森夕`, so
    # the Japanese page would have printed the credit with its roles deleted. 95 rows.
    def bases(rec):
        return "".join(str((sp or [""])[0] or "") for sp in (rec or {}).get("ruby") or [])

    for field in ("原作/三河ごーすと 漫画/森夕", "三河ごーすと(漫画) 森夕(原作)", "森夕(著者)",
                  "三河ごーすと, 森夕"):
        s.eq(bases(credits.compose(field, look)), field,
             f"the ruby covers the field as written: {field}")

    # AND WHERE IT CANNOT, IT ANNOTATES NOTHING. A span set that does not cover its surface is
    # furigana over the wrong characters, which is worse than none.
    s.eq(credits.spliced_ruby("森夕 / 知らない人", ["三河ごーすと"], [MIKAWA]),
         [["森夕 / 知らない人", None]],
         "a name the field does not hold collapses the whole set to a bare span")

    # A COMPOSED NAME'S STYLES COME OUT IN A FIXED ORDER. The styles every part can offer were
    # collected in a set, which answers "which" and says nothing about sequence, so the three keys
    # landed in whatever order the interpreter hashed them that run. Two builds of one tree then
    # produced byte-different files holding identical data, which left `deployed data matches
    # built` unable to settle and put about 1,500 meaningless lines in every build diff.
    _two = {"A": {"reading": "エー", "romaji": {"plain": "A", "macron": "Ā", "double": "Aa"}},
            "B": {"reading": "ビー", "romaji": {"macron": "B̄", "plain": "B", "double": "Bb"}}}
    _c = credits.compose("A / B", _two.get)
    s.eq(list(_c["romaji"]), ["macron", "double", "plain"],
         "the styles of a composed name are ordered, not hashed")
    # A part offering fewer styles narrows the set without disturbing the order of what is left.
    _thin = {"A": _two["A"], "B": {"reading": "ビー", "romaji": {"plain": "B", "macron": "B̄"}}}
    s.eq(list(credits.compose("A / B", _thin.get)["romaji"]), ["macron", "plain"],
         "and a style no part can offer is simply absent")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
