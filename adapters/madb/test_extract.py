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


if __name__ == "__main__":
    sys.exit(testkit.run(main, "madb.extract"))
