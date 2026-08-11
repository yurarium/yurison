#!/usr/bin/env python3
"""credit_identity.py: one address per credit, and the rule that a shared reading does not decide.

Every string quoted below is a credit this corpus carries, and the pairs are the ones the ruling on
the 82 shared readings turned on. A pair invented for the test would prove the shape functions can
answer, and not that they answer correctly about anything the pipeline emits (§14b).
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import credit_identity as ci  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/credit_identity.py"]

# Two works and the credit fields they carry, quoted from series.json. w00097's field names four
# people with slashes and one role label; w01218 names two.
ROWS = [{"id": "w00097", "author": "羽田遼亮 / 中島零 / 潮一葉 / 赤衣丸歩郎"},
        {"id": "w01218", "author": "古賀由人 / 4kaえんぴつ"},
        {"id": "w01242", "author": "秋山はる"}]


def main(s):
    tmp = pathlib.Path(tempfile.mkdtemp())

    # ── The fold, which is also the interface's lookup key ────────────────────────────────────
    s.eq(ci.credit_key("4ka エンピツ"), ci.credit_key("4kaエンピツ"),
         "a space inside a credit is not an identity: 4ka エンピツ and 4kaエンピツ are one artist")
    s.eq(ci.credit_key("2C＝がろあ"), ci.credit_key("2C=がろあ"),
         "and a fullwidth equals sign folds to the same credit NFKC already settles")
    s.ne(ci.credit_key("かぼちゃ"), ci.credit_key("カボちゃ"),
         "the fold must not touch script, or the counter-case would collapse before it is judged")
    s.eq(ci.anchor("秋山はる"), "credit:秋山はる", "an anchor is the credit as filed, folded")
    s.eq(ci.anchor("   "), None, "and a credit with nothing in it anchors nothing")

    # ── What a shared reading is evidence of ──────────────────────────────────────────────────
    # THE MERGING SHAPES. A source converting a name converts all of it.
    s.eq(ci.relation("ばったん", "バッタン", "バッタン"), "full-script-flip",
         "one credit written in the two kana scripts")
    s.eq(ci.relation("蛙田あめこ", "蛙田アメコ", "カエルダアメコ"), "full-script-flip",
         "and the same where only the given name's kana move, behind an identical surname")
    s.eq(ci.relation("毒田ぺパ子", "毒田ペパ子", "ドクタペパコ"), "full-script-flip",
         "and where one character moves, since the katakana side keeps no hiragana at all")
    s.eq(ci.relation("秋山はる", "アキヤマハル", "アキヤマハル"), "kana-reading",
         "a name beside its own reading, which is what MADB writes into one creator field")
    s.eq(ci.relation("ヤブウチユウ", "やぶうち優", "ヤブウチ ユウ"), "kana-reading",
         "in either order, and with the reading word-separated as the store holds it")
    s.eq(ci.relation("お子様ランチ", "おこさまランチ", "オコサマランチ"), "kana-reading",
         "including a coinage whose kanji spelling reads as ordinary words")

    # THE COUNTER-CASE, and it is the reason the flip test asks for a clean side. カボちゃ and
    # かぼちゃ agree on the sound and differ in WHICH characters are katakana, leaving ちゃ in
    # hiragana behind カボ. No transcription produces that and a stylised pen name does.
    s.eq(ci.relation("かぼちゃ", "カボちゃ", "カボチャ"), "partial-script-flip",
         "a flip that leaves hiragana behind is not a transcription")
    s.eq(ci.full_script_flip("かぼちゃ", "カボちゃ"), False,
         "so the merging test refuses it outright")
    s.eq(ci.full_script_flip("ばったん", "バッタン"), True, "while the wholesale change passes")

    # TWO NAMES THAT SOUND ALIKE. 多㐂 reads タキ because 㐂 is the variant of 喜; 瀧 reads タキ as
    # an ordinary surname. Nothing relates the spellings and the pair stays two credits.
    s.eq(ci.relation("多㐂", "瀧", "タキ"), "unrelated", "two spellings sharing only a reading")
    s.eq(ci.relation("蒼井", "青い", "アオイ"), "unrelated", "and two with no character in common")
    s.eq(ci.relation("須藤佑実", "須藤祐美", "スドウユミ"), "unrelated",
         "including one differing by the kanji of the given name, which no script rule explains")
    # A kanji spelling is never the kana reading of another kanji spelling, whatever they read as.
    s.eq(ci.kana_reading_of("蒼井", "青い", "アオイ"), False,
         "the reading test requires one side to be kana")

    # ── What the credit field yields, and where the role goes ─────────────────────────────────
    wanted, edges = ci.population(ROWS)
    s.eq(len(wanted), 7, "seven credits over the three fields")
    s.eq([w[2] for w in wanted][:4], ["羽田遼亮", "中島零", "潮一葉", "赤衣丸歩郎"],
         "in the order the source wrote them")
    entries, conflicts = ci.assign([], wanted)
    s.eq(conflicts, [], "with nothing contested")
    s.eq([e["id"] for e in entries][:2], ["c00001", "c00002"],
         "identifiers are opaque and sequential, so a renaming cannot break an address")
    s.eq(ci.credit_key(entries[0]["title"]), "羽田遼亮", "and each holds the credit as filed")

    # A ROLE IS NOT AN IDENTITY. One person is 原作 on one work and 作画 on another, so the label
    # belongs on the pairing. The splitter that finds the name is the one that reports it.
    wanted2, edges2 = ci.population([{"id": "w00001", "author": "原作／宮澤伊織　作画／水野英多"},
                                     {"id": "w00002", "author": "水野英多"}])
    s.eq(edges2[ci.anchor("水野英多")], [("w00001", "作画"), ("w00002", None)],
         "the same person carries a role on one work and none on the other")
    s.eq(edges2[ci.anchor("宮澤伊織")], [("w00001", "原作")],
         "and a label written before the slash names the credit after it")

    # ONE LINE PER PAIRING. The works list writes a credit field with the notation already taken off
    # and the release rows keep it, so the same credit reaches the same work twice, once bare and
    # once labelled. Emitting both read as somebody working on one book two separate times.
    wanted4, edges4 = ci.population([{"id": "w01225", "author": "大鷹シン / ホマレ"}],
                                    [{"wid": "w01225", "author": "原作/大鷹シン 漫画/ホマレ"}])
    reg4, _c = ci.assign([], wanted4)
    written = ci.save_edges(str(tmp / "edges.yaml"), reg4, edges4, "2026-08-08")
    s.eq(written[reg4[0]["id"]], {"w01225": ["原作"]},
         "one work, once, carrying whichever of the two rows named the job")

    # ── Minting from the works list, never from a release row ─────────────────────────────────
    # `&nbsp;フォローする` is a Follow button a page capture handed over as a byline, and it is in a
    # release row today. Minting there would publish an address for a control.
    wanted3, edges3 = ci.population(
        [{"id": "w00097", "author": "羽田遼亮 / 中島零 / 潮一葉 / 赤衣丸歩郎"}],
        [{"wid": "w00097", "author": "&nbsp;フォローする"},
         {"wid": "w00032", "author": "矢立肇・富野由悠季"}])
    s.eq([w[2] for w in wanted3], ["羽田遼亮", "中島零", "潮一葉", "赤衣丸歩郎"],
         "a release row mints no identifier")
    s.eq(ci.anchor("フォローする") in edges3, False, "so a Follow button gets no address")
    s.eq(edges3.get(ci.anchor("矢立肇")), None,
         "and a release-only credit reaches no edge either, having no identifier to hang one on")

    # ── The merge, the attach, and which one a ruling gets ────────────────────────────────────
    # BOTH SPELLINGS CREDIT WORKS, so an identifier has to be RETIRED. おこさまランチ contributes to
    # two 宙出版 anthologies and お子様ランチ to 少年画報社's トランススイッチ.
    both, _e = ci.population([{"id": "w01423", "author": "おこさまランチ"},
                              {"id": "w02425", "author": "お子様ランチ"}])
    reg, _c = ci.assign([], both)
    reg, retired_n, attached_n, kept, refused = ci.apply_rulings(reg, {"rulings": [{
        "reading": "オコサマランチ", "surfaces": ["おこさまランチ", "お子様ランチ"],
        "decision": "merge", "keep": "おこさまランチ", "basis": "one coinage written two ways"}]})
    s.eq((retired_n, attached_n, refused), (1, 0, []),
         "a spelling that holds an identifier is retired and not attached")
    s.eq(ci.identity.index(reg)[ci.anchor("お子様ランチ")],
         ci.identity.index(reg)[ci.anchor("おこさまランチ")],
         "and the retired address still resolves, to the credit it became")
    s.eq(ci.retired(reg), {"c00002": "c00001"}, "with the retirement recorded")

    # ONE SPELLING CREDITS NOTHING, so nothing can be retired. カヤコ reached the store from MADB's
    # creator field for 猫魔法…, where the slash separates a name from its own reading as well as
    # two people, and `credits.dedupe` had already taken it out of the credit a reader sees.
    one, _e = ci.population([{"id": "w00820", "author": "かやこ"}])
    reg2, _c = ci.assign([], one)
    reg2, retired2, attached2, _k, refused2 = ci.apply_rulings(reg2, {"rulings": [{
        "reading": "カヤコ", "surfaces": ["かやこ", "カヤコ"], "decision": "merge",
        "keep": "かやこ", "basis": "one credit MADB recorded beside its own reading"}]}, "2026-08-08")
    s.eq((retired2, attached2, refused2), (0, 1, []),
         "a spelling nothing has minted is attached, because a merge would retire an id nobody holds")
    s.eq(len(reg2), 1, "so no second identifier exists to retire")
    s.eq(reg2[0]["attached"][0]["basis"], "one credit MADB recorded beside its own reading",
         "and the evidence travels with the anchor a ruling added, since nothing re-derives it")
    # The whole point of the attach: a later run meeting the second spelling in a credit field
    # resolves it to the address the first already holds.
    later, _e = ci.population([{"id": "w00820", "author": "かやこ"}, {"id": "w9", "author": "カヤコ"}])
    reg3, _c = ci.assign(reg2, later)
    s.eq(len(reg3), 1, "so the second spelling never mints an address of its own")

    # RE-RUNNABLE. The ruling document is the record and the registry is derived from it, so a
    # second pass must be a no-op and not a second line of evidence.
    reg4, r4, a4, _k, _r = ci.apply_rulings(reg2, {"rulings": [{
        "reading": "カヤコ", "surfaces": ["かやこ", "カヤコ"], "decision": "merge",
        "keep": "かやこ", "basis": "one credit MADB recorded beside its own reading"}]})
    s.eq((r4, a4), (0, 0), "applying a ruling twice changes nothing")
    s.eq(len(reg4[0]["attached"]), 1, "and records the evidence once")

    # A MERGE WITHOUT A BASIS IS REFUSED. Saying two spellings are one credit is a claim, and where
    # it retires an identifier it is not reversible for anyone holding a link.
    _r5, _n, _a, _k, refused5 = ci.apply_rulings(reg, {"rulings": [{
        "surfaces": ["おこさまランチ", "お子様ランチ"], "decision": "merge",
        "keep": "おこさまランチ"}]})
    s.eq(len(refused5), 1, "a merge with no basis is refused")
    s.check("basis" in refused5[0], "and says so")

    # A pair kept apart is recorded rather than left to be re-derived at the next capture.
    _r6, _n6, _a6, kept6, _x = ci.apply_rulings(reg, {"rulings": [{
        "reading": "カボチャ", "surfaces": ["かぼちゃ", "カボちゃ"], "decision": "keep",
        "shape": "partial-script-flip", "basis": "the flip could be the artist's own styling"}]})
    s.eq(len(kept6), 1, "a keep is carried to the registry's homophones list")

    # ── Withdrawing an identifier minted for something that was never a credit ────────────────
    # c00268 was published at credit/c00268/ for `１冊目：叔母さんは神絵師`, which is chapter 1 of
    # 新刊100億冊ください: コミックDAYS puts the newest chapter where the page title puts the author.
    chap, _e = ci.population([{"id": "w00167",
                               "author": "破賀ミチル / １冊目：叔母さんは神絵師"}])
    s.eq([w[2] for w in chap], ["破賀ミチル"],
         "the splitter no longer hands a numbered heading over as a credit, so none is minted")
    # The address was published before it did, so the registry still has to answer for it.
    reg7, _c = ci.assign([], [(ci.anchor("破賀ミチル"), [], "破賀ミチル"),
                              (ci.anchor("１冊目：叔母さんは神絵師"), [],
                               "１冊目：叔母さんは神絵師")])
    reg7, ret7, att7, _k7, ref7 = ci.apply_rulings(reg7, {"rulings": [{
        "surfaces": ["１冊目：叔母さんは神絵師"], "decision": "withdraw", "to": "破賀ミチル",
        "basis": "chapter 1 of the work, read out of a page title's byline field"}]}, "2026-08-09")
    s.eq((ret7, att7, ref7), (1, 0, []), "a withdrawal retires the identifier it names")
    s.eq(ci.retired(reg7), {"c00002": "c00001"},
         "so the published address forwards to the credit the same field really named")
    s.eq(ci.identity.index(reg7).get(ci.anchor("１冊目：叔母さんは神絵師")), None,
         "and the chapter title resolves to nobody, because a withdrawal detaches instead of lending")
    s.eq(reg7[1]["detached"][0]["anchor"], ci.anchor("１冊目：叔母さんは神絵師"),
         "the spelling the address was minted for is kept beside the entry as the evidence")
    # RE-RUNNABLE, and the anchor being out of the index is exactly what makes that awkward.
    reg8, ret8, _a8, _k8, ref8 = ci.apply_rulings(reg7, {"rulings": [{
        "surfaces": ["１冊目：叔母さんは神絵師"], "decision": "withdraw", "to": "破賀ミチル",
        "basis": "chapter 1 of the work, read out of a page title's byline field"}]}, "2026-08-09")
    s.eq((ret8, ref8), (1, []), "a second run finds it already withdrawn rather than reporting a fault")
    s.eq(len(reg8[1]["detached"]), 1, "and records the evidence once")
    # A WITHDRAWAL MAY NAME NO SUCCESSOR, and leaving `to` out says so. It used to be
    # required, which left the machinery unable to express the case it is most obviously for:
    # BOOK☆WALKER and GigaViewer write `アンソロジー` in an anthology's creator field, being the
    # format of the book and no byline at all, and c01868 was minted and published for it. The
    # chapter-title precedent had a successor because the same field really did name somebody
    # beside the chapter; that one named nobody, and choosing a successor to satisfy the shape
    # would have filed nine anthologies under whoever was chosen. The anchor is detached, so
    # nothing resolves to the identifier again and it stays retired and empty.
    _r9, _n9, _a9, _k9, refused9 = ci.apply_rulings(reg, {"rulings": [{
        "surfaces": ["おこさまランチ"], "decision": "withdraw", "basis": "not a credit at all"}]})
    s.eq(len(refused9), 0, "a withdrawal naming no successor is allowed")
    s.check(not any("おこさまランチ" in str(e.get("anchors") or []) for e in _r9),
            "and the anchor is detached, so the string resolves to nobody")
    # BUT A `to` THAT NAMES NOBODY LIVE IS STILL REFUSED, which is the case leaving it out is not:
    # one says there is no successor, the other names one that does not exist.
    _r9b, _n9b, _a9b, _k9b, refused9b = ci.apply_rulings(reg, {"rulings": [{
        "surfaces": ["おこさまランチ"], "decision": "withdraw", "to": "だれもいない",
        "basis": "not a credit"}]})
    s.eq(len(refused9b), 1, "a withdrawal sending readers to a credit that is not live is refused")
    _r10, _n10, _a10, _k10, refused10 = ci.apply_rulings(reg, {"rulings": [{
        "surfaces": ["おこさまランチ", "お子様ランチ"], "decision": "withdraw",
        "to": "お子様ランチ", "basis": "x"}]})
    s.eq(len(refused10), 1, "and one naming two spellings is refused, since it settles a string")

    # ── The unruled measure, which is what makes a new pair arrive as a number ────────────────
    shipped = {"かぼちゃ": {"reading": "カボチャ"}, "カボちゃ": {"reading": "カボチャ"},
               "多㐂": {"reading": "タキ"}, "瀧": {"reading": "タキ"},
               "秋山はる": {"reading": "アキヤマハル"}}
    s.eq(len(ci.shared_readings(shipped)), 2, "two readings answer for more than one credit")
    doc = {"rulings": [{"surfaces": ["かぼちゃ", "カボちゃ"], "decision": "keep", "basis": "x"}]}
    s.eq([rd for rd, _s in ci.unruled(shipped, doc)], ["タキ"],
         "and the pair with no ruling is the one reported")

    # ── The measure that does not share the assigner's blind spot ─────────────────────────────
    surfaces = {"羽田遼亮", "中島零", "潮一葉", "赤衣丸歩郎"}
    s.eq(ci.uncovered("羽田遼亮 / 中島零 / 潮一葉 / 赤衣丸歩郎", surfaces), [],
         "a field every credit of which holds an identifier leaves nothing behind")
    s.eq(ci.uncovered("羽田遼亮 / 中島零 / 潮一葉 / 赤衣丸歩郎", surfaces - {"潮一葉"}), ["潮一葉"],
         "and a credit that reaches no identifier is reported, without asking the splitter")
    # THE LONGEST SPELLING GOES FIRST, or a short credit eats the head of a longer one and the
    # remainder reads as a name nobody holds. 田口囁一 and 田口ケンジ are two credits.
    s.eq(ci.uncovered("田口囁一 / 田口ケンジ", {"田口囁一", "田口ケンジ"}), [],
         "a credit sharing a prefix with another is not left half-deleted")
    s.eq(ci.uncovered("&nbsp;フォローする", {"クール教信者"}), ["nbsp", "フォローする"],
         "a Follow button handed over as a byline is what the residue is for")

    # ── What a retired credit id serves ──────────────────────────────────────────────────────
    pages = ci.forwarders(reg)
    s.eq(sorted(pages), ["credit/c00002/index.html"],
         "a retired identifier gets a page and a live one does not")
    body = pages["credit/c00002/index.html"]
    for fragment in ('rel="canonical" href="../../credit/c00001/"',
                     'content="noindex,nofollow"',
                     'http-equiv="refresh" content="0; url=../../credit/c00001/"',
                     'location.replace("../../credit/c00001/")',
                     "This record is now"):
        s.check(fragment in body, f"the stub carries {fragment}")
    s.check("work/c00001" not in body,
            "and it points inside its own root, which the shared renderer used to ignore")

    # ── Kinds, so that a company does not get a person-shaped page ────────────────────────────
    s.eq(ci.kind_of("円谷プロダクション"), "company", "a television company is a company")
    s.eq(ci.kind_of("「真夜中ぱんチ」製作委員会"), "committee", "and a committee a committee")
    s.eq(ci.kind_of("電撃G'sマガジン"), "magazine", "and a magazine names itself one")
    s.eq(ci.shape_of(ci.kind_of("電撃G'sマガジン")), "venue",
         "which DEFINITIONS treats as a place where yuri is published")
    s.eq(ci.shape_of(ci.kind_of("円谷プロダクション")), "organisation", "against an organisation")
    s.eq(ci.kind_of("伊藤ハチ"), None, "and silence for a credit no rule recognises")
    s.eq(ci.shape_of(None), "person", "which is the shape a credit gets by default")
    # NOTATION IS NOT A KIND HERE. `はいむらきよたか(キャラクターデザイン)` is one person with a role
    # welded on, and the splitter takes the role off before an identifier is minted, so the credit
    # that reaches this is the person. Reporting it as an entity would file a person as a thing.
    s.eq(ci.kind_of("はいむらきよたか(キャラクターデザイン)"), None,
         "cataloguing welded to a name is not a kind of credit")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
