#!/usr/bin/env python3
"""madb/extract.py: flattening MADB's polymorphic fields without losing the reading.

COVERS = ['adapters/madb/extract.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import extract as m


def main(s):
    # ISBD's ` = ` introduces a 並列タイトル, transcribed from the book's own title page. Storing the
    # whole string made cataloguing punctuation part of the name, and two records of one work then
    # compared unequal: several pairs shipped as duplicates and were merged by hand.
    s.eq(m.title_proper("リリィシステム = LILY SYSTEM"), "リリィシステム",
         "the parallel title comes off the name")
    s.eq(m.parallel_title("リリィシステム = LILY SYSTEM"), "LILY SYSTEM",
         "and is kept, being the publisher's own English name")
    # COUNTER-CASES, each a shape that must NOT split.
    s.eq(m.title_proper("A = ビー"), "A = ビー",
         "a parallel half holding Japanese is not a translation")
    s.eq(m.title_proper("X = Y = Z"), "X = Y = Z",
         "two marks make the split ambiguous, so nothing is guessed")
    s.eq(m.title_proper("恋愛遺伝子XX : 完全版"), "恋愛遺伝子XX : 完全版",
         "a colon introduces other title information and is left alone")
    s.eq(m.parallel_title("ふつうの子"), "",
         "a title with no parallel title yields none")

    # ── THE CATALOGUED TITLE IS SPLIT ACROSS TWO FIELDS ────────────────────────────────────────
    #
    # MADB puts the title proper in schema:name and the other title information in
    # schema:alternativeHeadline, and writes the reading of BOTH into schema:name's ja-hrkt half
    # with ISBD's colon between them. Reading schema:name alone stored 怪異部 for a work whose own
    # reading says カイイブ : エムケン ワイシ ノ カイゲンショウ ニ ツイテ, and the works list showed
    # `Kaii Bu` for 怪異部～M県Y市の怪現象について～. 20 records of this corpus were in that state.
    KAII = {"schema:name": ["怪異部", {"@value": "カイイブ : エムケン ワイシ ノ カイゲンショウ ニ ツイテ",
                                       "@language": "ja-hrkt"}],
            "schema:alternativeHeadline": "M県Y市の怪現象について"}
    s.eq(m.catalogued_name(KAII), "怪異部 : M県Y市の怪現象について",
         "the two fields are one ISBD line")
    s.eq(m.title_proper(m.catalogued_name(KAII)), "怪異部 : M県Y市の怪現象について",
         "and isbd keeps the subtitle, which is why nothing there had to change")

    # MADB DOES NOT ALWAYS READ THE SUBTITLE ALOUD, and that is silence about the reading rather
    # than about the title. 3 of the 20 are here, and the corpus holds the full name for each of
    # them from a platform: ゆりゆりぱにっく～尊すぎる事案が発生しています！～.
    YURI = {"schema:name": ["ゆりゆりぱにっく", {"@value": "ユリユリ パニック", "@language": "ja-hrkt"}],
            "schema:alternativeHeadline": "尊すぎる事案が発生しています"}
    s.eq(m.catalogued_name(YURI), "ゆりゆりぱにっく : 尊すぎる事案が発生しています",
         "a subtitle the reading never states is still the subtitle")

    # A LATIN VALUE IS OFTEN A PREFIX OF THE REAL ONE, and the reading is what proves it. Grafting
    # `Fallin` on publishes a name no edition carries: the work is 紗痲 Fallin' Jail.
    SHAMA = {"schema:name": ["紗痲", {"@value": "シャマ : フォーリン ジェイル", "@language": "ja-hrkt"}],
             "schema:alternativeHeadline": "Fallin"}
    s.eq(m.subtitle(SHAMA), "", "a Latin value the reading does not repeat is cut short")
    s.eq(m.catalogued_name(SHAMA), "紗痲", "so the record keeps the name it can stand behind")
    TH = {"schema:name": ["王都で気ままに暮らしたい",
                          {"@value": "オウト デ キママ ニ クラシタイ : ザ コミック", "@language": "ja-hrkt"}],
          "schema:alternativeHeadline": "TH"}
    s.eq(m.subtitle(TH), "", "`TH` against ザ コミック is the same fault two letters in")
    # AND THE COUNTER-CASE, which is why the test is on the reading and not on the script. Where
    # MADB repeats the Latin unchanged, the field is whole and is taken.
    SQ = {"schema:name": ["嘘から始まる恋の夏",
                          {"@value": "ウソ カラ ハジマル コイ ノ ナツ : squall", "@language": "ja-hrkt"}],
          "schema:alternativeHeadline": "squall"}
    s.eq(m.catalogued_name(SQ), "嘘から始まる恋の夏 : squall",
         "a Latin value its own reading repeats is stated whole")

    # A LIST STATES SEVERAL PIECES IN NO STATED ORDER, so neither end can be picked. 172 records
    # hold one and the release puts the subtitle at both ends of it.
    s.eq(m.subtitle({"schema:alternativeHeadline": ["コミック", "平凡会社員の成り上がり迷宮録"]}), "",
         "several values with no order between them yield none")
    s.eq(m.subtitle({}), "", "a record stating no subtitle states none")
    s.eq(m.catalogued_name({"schema:name": "ふつうの子"}), "ふつうの子",
         "and a record with one field is that field")
    # A VALUE ALREADY INSIDE THE NAME IS NOT ADDED TWICE.
    s.eq(m.catalogued_name({"schema:name": "citrus : 完全版", "schema:alternativeHeadline": "完全版"}),
         "citrus : 完全版", "a subtitle the name already carries is not repeated")

    # MADB hands the same logical field back as a string, a dict or a list depending on the record,
    # so every consumer would otherwise have to know all three shapes.
    s.eq(m.flat("plain"), "plain", "a string passes through")
    s.eq(m.flat({"@value": "v"}), "v", "a dict yields its value")
    s.eq(m.flat({"@id": "http://x/1"}), "http://x/1", "a dict without @value falls back to @id")
    s.eq(m.flat(["a", "b"]), "a / b", "a list is joined")
    s.eq(m.flat(None), "", "None flattens to empty rather than the string 'None'")

    # The reading is the point: it is what NAMES-PLAN needs and what a naive flatten would bury.
    v = [{"@value": "青田", "@language": "ja"}, {"@value": "アオタ", "@language": "ja-hrkt"}]
    s.eq(m.reading(v), "アオタ", "the ja-hrkt half is the reading")
    s.eq(m.primary(v), "青田 / アオタ", "primary keeps the non-reading form")
    s.eq(m.reading("no reading here"), "", "a bare string has no reading")
    s.eq(m.reading([{"@value": "x", "@language": "ja"}]), "",
         "a list without a ja-hrkt entry has no reading")

    # Publisher strings embed the reading behind a separator instead of in a field.
    s.eq(m.split_reading("一迅社　∥　イチジンシャ"), "一迅社", "the name half is taken")
    s.eq(m.split_reading("一迅社"), "一迅社", "a string without the separator is unchanged")

    s.eq(m.local_id({"@id": "http://mediaarts-db.jp/mg/12345"}), "12345", "the id tail is taken")

    # These are Japanese strings that routinely contain YAML metacharacters, so quoting is not
    # optional: an unescaped quote would break the file the whole pipeline reads next.
    s.eq(m.yaml_str('say "hi"'), '"say \\"hi\\""', "embedded quotes are escaped")
    s.eq(m.yaml_str("back\\slash"), '"back\\\\slash"', "backslashes are escaped first")

    s.eq(m.norm("ＹＵＲＩ・花"), m.norm("yuri花"), "width, case and separators fold")


    # A TITLE IS NOT AN IDENTIFIER. `トワ・エ・モア` is a コンパス anthology from 1996 with no
    # creator, and a 講談社 KCデラックス series by 仲藤ぬい from 2024. Matched on the title alone,
    # the second was filed inside the first and one work held volumes 28 years apart.
    OLD = {"schema:identifier": "C1", "schema:name": "トワ・エ・モア", "schema:publisher": "コンパス",
           "schema:brand": "コンパスアンソロジーコミックシリーズ"}
    NEW = {"schema:identifier": "M2", "schema:name": "トワ・エ・モア", "schema:publisher": "講談社",
           "schema:brand": "KCデラックス", "schema:creator": "[著]仲藤ぬい"}
    s.check(not m.agrees(NEW, OLD), "a shared title with nothing else agreeing is not one work")
    ser = {"C1": OLD}
    s.eq(m.key_of(NEW, ser, m.title_index(ser))[1], "title-only",
         "so the volume becomes its own work rather than somebody else's")

    # AND THE CASE THAT MUST SURVIVE IT. 一迅社's yuri line passed to 講談社, so volumes of one
    # work disagree about the publisher. The creator is what says they are one work.
    ICH = {"schema:identifier": "C2", "schema:name": "ゆるゆり", "schema:publisher": "一迅社",
           "schema:creator": "なもり"}
    KOD = {"schema:identifier": "M3", "schema:name": "ゆるゆり", "schema:publisher": "[発売]講談社",
           "schema:creator": "[著]なもり / ナモリ"}
    s.check(m.agrees(KOD, ICH), "a house changing hands does not split a work whose creator agrees")
    ser2 = {"C2": ICH}
    s.eq(m.key_of(KOD, ser2, m.title_index(ser2))[1], "title-match", "and the volume still joins")
    s.eq(m.people(KOD), {"なもり"}, "a role and a trailing reading are not people")

    # AND THE CASE THE SAME HANDOVER TAKES WHEN NOBODY IS CREDITED. citrus is catalogued under
    # both houses with no creator on either record, which is said to leave the date as the only
    # field. It does not: the imprint is IDコミックス on both sides and joins them.
    CIT_I = {"schema:identifier": "C4", "schema:name": "citrus", "schema:publisher": "一迅社",
             "schema:brand": "IDコミックス", "schema:datePublished": "2015-08"}
    CIT_K = {"schema:identifier": "M5", "schema:name": "Citrus", "schema:publisher": "[発売]講談社",
             "schema:brand": "IDコミックス", "schema:datePublished": "2015-08"}
    s.check(m.agrees(CIT_K, CIT_I), "the imprint carries the handover where no creator is named")

    # THE RULE THAT WAS PROPOSED FOR THIS FUNCTION AND IS REFUSED. Where neither record names a
    # creator, an exactly agreeing publication month was proposed as the fourth test. The month is
    # weakest exactly where it would be used: a tie-in anthology is raced out by rival houses in
    # the month the game ships, so ペルソナ4コミックアンソロジー is two different books in 2009-01,
    # one 光文社 and one 一迅社, and To heart 2アンソロジーコミック is three in 2005-07 under three
    # publishers. An agreeing month is evidence about a release date, not about a work.
    KOU = {"schema:identifier": "C5", "schema:name": "ペルソナ4コミックアンソロジー",
           "schema:publisher": "光文社", "schema:brand": "火の玉ゲームコミックシリーズ",
           "schema:datePublished": "2009-01"}
    ICJ = {"schema:identifier": "M6", "schema:name": "ペルソナ4コミックアンソロジー",
           "schema:publisher": "一迅社", "schema:brand": "DNAメディアコミックス",
           "schema:datePublished": "2009-01"}
    s.check(not m.agrees(ICJ, KOU),
            "two anthologies sharing a title and a month are not one work")
    ser3 = {"C5": KOU}
    s.eq(m.key_of(ICJ, ser3, m.title_index(ser3))[1], "title-only",
         "so each stays its own work, which is what the month rule would have undone")
    # A VOLUME COUNT COUNTS VOLUMES. ささやくように恋を唄う holds four of its volumes twice, a
    # standard and a special edition differing in the ISBN and nothing else, so counting records
    # called a 12-volume work 16 volumes long above a list of 12.
    two_eds = [{"schema:volumeNumber": "9", "schema:datePublished": "2024-04", "schema:isbn": "a"},
               {"schema:volumeNumber": "9", "schema:datePublished": "2024-04", "schema:isbn": "b"}]
    s.eq(m.volume_count(two_eds), 1, "two editions of one volume are one volume")
    s.eq(m.volume_count(two_eds + [{"schema:volumeNumber": "10",
                                    "schema:datePublished": "2024-08"}]), 2, "and the next is another")
    s.eq(m.volume_count([{"schema:volumeNumber": "1", "schema:datePublished": "2019-07"},
                         {"schema:volumeNumber": "1", "schema:datePublished": "2024-11"}]), 2,
         "a reissue years later is its own volume, not an edition of the first")
    s.eq(m.volume_count([{"schema:datePublished": "2008-05"}, {"schema:datePublished": "2008-05"}]), 2,
         "and unnumbered volumes have nothing to match on, so each counts once")

    s.eq(m.publisher_names({"schema:publisher": "小学館クリエイティブ(発売)"}),
         m.publisher_names({"schema:publisher": "小学館クリエイティブ"}),
         "a distributor role in a trailing bracket is not a second publisher")

    # ── A MULTI-VALUED FIELD IS NOT ITS FIRST VALUE ────────────────────────────────────────────
    #
    # Both faults below are the same one. MADB states a set of values and `primary` took the first,
    # so the umbrella imprint stood for the yuri line and the distributor stood for the publisher.
    s.eq(m.values(["IDコミックス", "Yurihime comics",
                   {"@value": "ID コミックス", "@language": "ja-hrkt"}]),
         ["IDコミックス", "Yurihime comics"], "the names are kept and the readings are not")
    s.eq(m.values("YURIHIME COMICS"), ["YURIHIME COMICS"], "a bare string is one value")
    s.eq(m.values(None), [], "an absent field states nothing")
    s.eq(m.values([{"@value": "ID コミックス", "@language": "ja-hrkt"}]), [],
         "a field holding only a reading names nothing")

    # THE IMPRINT THAT EARNED THE LABEL. 117 works were stored as `imprint: IDコミックス` beside
    # `marketing_label: yuri`, because the 百合姫 line is MADB's SECOND value for the brand. The
    # evidence table withheld those rows rather than quote a term making no yuri claim.
    UMB = {"schema:brand": ["IDコミックス", "Yurihime comics",
                            {"@value": "ID コミックス", "@language": "ja-hrkt"}]}
    s.eq(m.imprint_of([UMB])[0], "Yurihime comics",
         "the brand that carries the label is the one stored, not the umbrella line above it")
    s.eq(m.as_stated(UMB["schema:brand"]), "IDコミックス / Yurihime comics",
         "and the field is kept as MADB stated it, so the reading can be checked")
    s.check(m.is_yuri_imprint("IDコミックス. Yurihime comics = コミック百合姫"),
            "a joined spelling still names the line")
    s.check(not m.is_yuri_imprint("IDコミックス"),
            "and the umbrella line on its own does not, which is why the row was withheld")

    # THE COUNTER-CASE TO THE OBVIOUS RULE. Taking the LAST value would be the most specific one in
    # every record stating several, and it is not always a brand at all.
    SUB = {"schema:brand": ["Emerald comics", "Romance comics = ロマンスコミックス", "プロポーズのゆくえ"]}
    s.eq(m.imprint_of([SUB])[0], "Emerald comics",
         "a record with nothing matched keeps its stated brand rather than a sub-series title")

    # A work whose own record names no 百合姫 brand: the volumes are what selection saw.
    BARE = {"schema:brand": "yh COMICS"}
    VOL = {"schema:brand": ["IDコミックス", "Yuri-hime comics anthology series"]}
    s.eq(m.imprint_of([BARE, VOL])[0], "Yuri-hime comics anthology series",
         "and where only a volume carries the line, that is the brand the record states")
    s.check(m.imprint_of([BARE, VOL])[1] is VOL, "and the record it was read from is reported")
    s.eq(m.imprint_of([{}, {"schema:brand": "アフタヌーンKC"}])[0], "アフタヌーンKC",
         "a series record stating no brand at all takes its volumes', matched or not")

    # ── A DISTRIBUTOR IS NOT A PUBLISHER ───────────────────────────────────────────────────────
    #
    # MADB writes `["[発売]講談社", "一迅社"]` for a 一迅社 book 講談社 put into shops. Reading the
    # first value made 132 works read 講談社, and a per-publisher count of 一迅社 came out short.
    ICH = {"schema:publisher": ["[発売]講談社　∥　コウダンシャ", "一迅社　∥　イチジンシャ"]}
    s.eq(m.publisher_of(ICH).name, "一迅社", "the party with no role marker is the publisher")
    s.eq([(p.name, p.role, p.stated) for p in m.publishers(ICH)],
         [("講談社", "distributor", "発売"), ("一迅社", "publisher", "")],
         "and both parties are on the record, each with the role MADB gave it")
    s.eq(m.party("[頒布]講談社 (発売)").name, "講談社",
         "a role at both ends of a name leaves the name")
    s.eq(m.party("[頒布]講談社 (発売)").stated, "頒布", "and the first role stated is the one read")

    # THE COUNTER-CASE. MADB brackets names in the same position, so a rule stripping every bracket
    # leaves a credit naming nobody. `[Shueisha]` and `[ヒゲの筆]` are publishers, not roles.
    s.eq(m.party("[ヒゲの筆]").name, "[ヒゲの筆]", "an unrecognised bracket is not a role marker")
    s.eq(m.party("[ヒゲの筆]").role, "publisher", "so the party keeps the default role")
    s.eq(m.party("ほぼ日 (発行所)").role, "publisher", "発行所 is the publishing role, not delivery")
    s.eq(m.party("エンターブレイン (東京)").name, "エンターブレイン (東京)",
         "and a place in a trailing bracket stays part of the name")

    # WHERE NOBODY HOLDS THE ROLE, the answer is nobody. Promoting the distributor into the empty
    # seat is the fault this function exists to stop.
    s.eq(m.publisher_of({"schema:publisher": "[頒布]大垣書店"}).name, "",
         "a record naming only a distributor names no publisher")

    # ── THE ROLE TABLE IS THE ONE THE RELEASE HOLDS ────────────────────────────────────────────
    #
    # A table built for 発売 and 頒布 leaves the rest of the bracket inside the name, so the party
    # holding the OTHER role becomes the publisher by default. 15 records of release 1.2.18 were in
    # that state and each shape is pinned below, because the fault reappears one word at a time.
    s.eq(m.publisher_of({"schema:publisher": ["[発売・共同刊行]コミックス", "講談社"]}).name, "講談社",
         "a co-publisher written first does not take the seat from the publisher")
    s.eq(m.publisher_of({"schema:publisher": ["[製作・発売]熊日情報文化センター",
                                              "熊本日日新聞社"]}).name, "熊本日日新聞社",
         "nor does a party that produced and delivered")
    s.eq(m.publisher_of({"schema:publisher": ["[特別編集] コミックメーカー",
                                              "ビクターエンタテインメント"]}).name,
         "ビクターエンタテインメント", "nor an editing credit MADB brackets in the same position")
    s.eq(m.publisher_of({"schema:publisher": ["[発売所]松島書店", "[発行人]松島広治"]}).name,
         "松島広治", "and 発行人 is the publishing role, so the person holding it answers")
    # AND WHERE A CO-PUBLISHER IS ALL THERE IS, it is the answer rather than nobody.
    s.eq(m.publisher_of({"schema:publisher": "[共同刊行]あかね書房"}).name, "あかね書房",
         "a co-publisher alone published the book")

    # ── WHY THE SEAT IS EMPTY, WHICH IS THREE DIFFERENT FACTS ──────────────────────────────────
    #
    # STANDING-INSTRUCTIONS §5: absence is a state. An empty publisher field says the same thing
    # whether MADB looked and found nothing, named somebody else, or never spoke, and only one of
    # those means anything further could be found.
    s.eq(m.publisher_basis({"schema:publisher": ["[発売]講談社", "一迅社"]}), "",
         "a record that names a publisher needs no reason for an empty seat")
    s.eq(m.publisher_basis({"schema:publisher": "[頒布]大垣書店"}), "not-stated",
         "a distributor alone means somebody published it and MADB does not say who")
    s.eq(m.publisher_basis({"schema:publisher": "[出版者不明]"}), "unknown-to-source",
         "and 出版者不明 means the cataloguer looked and the book does not say")
    s.eq(m.publisher_basis({"schema:publisher": "[s.n.]"}), "unknown-to-source",
         "which is what ISBD's sine nomine says in Latin on 4 records")
    s.eq(m.publisher_basis({}), "absent", "a record with no field at all makes no claim either way")

    s.eq([p.name for p in m.distributors({"schema:publisher": ["[発売]講談社", "一迅社"]})],
         ["講談社"], "the distributor is reported on its own, never as the publisher")
    s.eq(m.distributors({"schema:publisher": "一迅社"}), [],
         "and a record naming nobody in that role reports none")

    # WHICH RECORD OF THE CHAIN THE PUBLISHER IS READ FROM. A summary naming only a distributor is
    # saying nothing about who published, so it must not silence a volume that names one.
    DIST_ONLY = {"schema:publisher": "[発売]講談社"}
    FULL = {"schema:publisher": ["[発売]講談社", "一迅社"]}
    s.check(m.publisher_record([DIST_ONLY, FULL]) is FULL,
            "a distributor-only series record yields to the volume that names the publisher")
    s.check(m.publisher_record([{}, DIST_ONLY]) is DIST_ONLY,
            "and where the chain names none, the record that stated anything is still read")
    s.check(m.publisher_record([FULL, {"schema:publisher": "別の社"}]) is FULL,
            "the first record naming a publisher wins, so volumes cannot outvote their series")

    # AND THE JOIN THE SET COMPARISON RESTORES. ハイガクラ's volumes name the distributor beside
    # the publisher and its series record names the publisher alone, so comparing one value against
    # one value refused 14 title joins of that shape across release 1.2.18.
    HAI_V = {"schema:identifier": "M9", "schema:name": "ハイガクラ",
             "schema:publisher": ["[頒布]講談社　∥　コウダンシャ", "一迅社　∥　イチジンシャ"],
             "schema:brand": "ZERO-SUM COMICS"}
    HAI_S = {"schema:identifier": "C9", "schema:name": "ハイガクラ",
             "schema:publisher": "一迅社　∥　イチジンシャ", "schema:brand": "IDコミックス"}
    s.check(m.agrees(HAI_V, HAI_S), "a distributor listed first does not hide the publisher")
    s.check(not m.agrees(NEW, OLD),
            "and トワ・エ・モア is still two works, which the looser comparison must not undo")

    # ── WHAT THE RECORD SAYS ───────────────────────────────────────────────────────────────────
    #
    # The two readings above only matter if they reach the file. This is the shape a consumer
    # parses, so it is asserted on the rendered text rather than on the functions behind it.
    SER = {"schema:identifier": "C7", "schema:name": "ある作品",
           "schema:publisher": ["[発売]講談社　∥　コウダンシャ", "一迅社　∥　イチジンシャ"],
           "schema:brand": ["IDコミックス", "Yurihime comics"]}
    VOLS = [{"schema:identifier": "M7", "schema:volumeNumber": "1", "schema:isbn": "9784758000000",
             "schema:datePublished": "2020-01",
             "schema:brand": ["IDコミックス", "Yurihime comics"]}]
    text = m.render("C7", VOLS, {"C7": SER}, "series-link", "1.2.18", "2026-08-07",
                    m.ROUTE_IMPRINT, m.LABEL_IMPRINT)
    s.check('publisher: "一迅社"' in text, "the record states the publisher")
    s.check('distributor: "講談社"' in text,
            "and the distributor in a field of its own, which is the whole of the fix")
    s.check("publisher_basis:" not in text, "a record naming a publisher gives no reason for a gap")
    s.check('publisher_stated: "[発売]講談社 / 一迅社"' in text,
            "and keeps the field it was read out of, so the reading can be disputed")
    s.check('  - name: "講談社"\n    role: distributor\n    role_stated: "発売"' in text,
            "the distributor is named with the role MADB gave it")
    s.check('  - name: "一迅社"\n    role: publisher' in text, "and so is the publisher")
    s.check('imprint: "Yurihime comics"' in text, "the imprint names the line that carries the label")
    s.check('imprint_stated: "IDコミックス / Yurihime comics"' in text, "with the brand as stated")
    s.check("marketing_label: yuri" in text, "and the label the imprint earned")
    s.ne(text.count('publisher: "'), 2, "the publisher is stated once, not twice")

    # A record with one unmarked publisher says it once. `publishers` and `publisher_stated` are
    # for what a single line cannot carry, and repeating the line is what §3 is about.
    PLAIN = dict(SER, **{"schema:publisher": "太田出版", "schema:brand": "F×COMICS"})
    plain = m.render("C7", [dict(VOLS[0], **{"schema:brand": "F×COMICS"})], {"C7": PLAIN},
                     "series-link", "1.2.18", "2026-08-07", m.ROUTE_IMPRINT, m.LABEL_IMPRINT)
    s.check("publishers:" not in plain, "one party with no role needs no list")
    s.check("publisher_stated:" not in plain, "and no copy of itself under another name")
    s.check('imprint: "F×COMICS"' in plain, "a brand nothing matched is stated as it was")
    s.check("imprint_stated:" not in plain, "and is not repeated either")
    s.check("publisher_from:" not in plain, "a record that speaks for itself says so by silence")

    # MADB LEAVES schema:publisher OFF 10 OF THESE SERIES RECORDS while every volume of them names
    # 一迅社. Those were the last works whose label had a term to quote and nobody to attribute it
    # to, so the evidence table withheld them after the imprint was already right.
    THIN = {"schema:identifier": "C8", "schema:name": "うすい記録",
            "schema:brand": ["IDコミックス", "Yurihime comics"]}
    thin = m.render("C8", [dict(VOLS[0], **{"schema:publisher":
                                            ["[発売]講談社", "一迅社"]})],
                    {"C8": THIN}, "series-link", "1.2.18", "2026-08-07",
                    m.ROUTE_IMPRINT, m.LABEL_IMPRINT)
    s.check('publisher: "一迅社"' in thin, "a silent series record takes the publisher its books name")
    s.check("publisher_from: volumes" in thin, "and says that is where it was read")

    # A CHAIN THAT NAMES NOBODY IN THE ROLE. The record must say the publisher is unknown and name
    # the distributor beside it, because the alternative is a blank field a consumer reads as "not
    # filled in yet" and a distributor quietly standing in for a publisher is what started this.
    NOPUB = {"schema:identifier": "C9", "schema:name": "頒布のみ",
             "schema:brand": ["IDコミックス", "Yurihime comics"],
             "schema:publisher": "[頒布]講談社　∥　コウダンシャ"}
    nopub = m.render("C9", [dict(VOLS[0])], {"C9": NOPUB}, "series-link", "1.2.18", "2026-08-07",
                     m.ROUTE_IMPRINT, m.LABEL_IMPRINT)
    # AND THE COMPOSED TITLE HAS TO REACH THE FILE, which is the half a function-level test cannot
    # show. A title-only work takes its descriptive fields from the first volume, and that is the
    # record the subtitle sits on.
    solo = m.render("T:怪異部", [dict(VOLS[0], **KAII)], {}, "title-only", "1.2.18", "2026-08-07",
                    m.ROUTE_IMPRINT, m.LABEL_IMPRINT)
    s.check('ja: "怪異部 : M県Y市の怪現象について"' in solo,
            "the record states the whole name its own reading reads out")
    s.check('yomi: "カイイブ : エムケン ワイシ ノ カイゲンショウ ニ ツイテ"' in solo,
            "and the reading it was checked against, unchanged")

    s.check('publisher: ""' in nopub, "a distributor is not promoted into the empty publisher seat")
    s.check("publisher_basis: not-stated" in nopub, "and the record says why the seat is empty")
    s.check('distributor: "講談社"' in nopub, "with the party MADB did name in its own field")
    s.check('publisher_stated: "[頒布]講談社"' in nopub, "and the string all of it was read out of")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "madb.extract"))
