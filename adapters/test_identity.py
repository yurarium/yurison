#!/usr/bin/env python3
"""identity.py: an identifier that never moves, and a join that needs more than a title."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import identity as ident  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/identity.py"]

# Quoted from the two populations. 春夏秋冬 is a real joined pair; the anthology stories are the
# only URL collisions in the corpus and both sit on comic.pixiv.net containers.
PRINTS = [{"id": "C270392", "t": "春夏秋冬", "c": "[作画]蔵王大志 / [原作]影木栄貴"},
          {"id": "C999999", "t": "夏とレモンとオーバーレイ", "c": "[原作]Ru / [漫画]宮原都"}]
WEB = [{"work": "春夏秋冬", "author": "蔵王大志", "url": "https://example.jp/a"},
       {"work": "夏とレモンとオーバーレイ", "author": "漫画：宮原都,原作：Ru", "url": "https://example.jp/b"}]


def main(s):
    # A CHAPTER ADDRESS IS NOT AN IDENTITY. build.py gives a row its newest chapter's address, so
    # on a GigaViewer platform the anchor moved every time the work published and minted a second
    # identifier for a work already held.
    s.eq(ident.stable_url("https://pocket.shonenmagazine.com/title/03056/episode/441581"),
         "https://pocket.shonenmagazine.com/title/03056",
         "a chapter under a work address is reduced to the work address")
    s.eq(ident.web_anchor("https://pocket.shonenmagazine.com/title/03056/episode/441581"),
         ident.web_anchor("https://pocket.shonenmagazine.com/title/03056/episode/999999"),
         "so two chapters of one work give one anchor")
    # THE SAME SHAPE ON TWO MORE PLATFORMS. ヤンマガWeb hangs a 32-digit hexadecimal chapter off
    # the work, so the work is the prefix.
    s.eq(ident.stable_url("https://yanmaga.jp/comics/TANGO/0887c82c0482f0b770e2af3a19275b62"),
         "https://yanmaga.jp/comics/TANGO",
         "a chapter under a work path on ヤンマガWeb is reduced to the work")
    s.eq(ident.stable_url("https://yanmaga.jp/comics/TANGO/0887c82c0482f0b770e2af3a19275b62/"),
         "https://yanmaga.jp/comics/TANGO", "and a trailing slash is not a different address")
    # マンガワン spells the work's own segment differently, so this one is a rewrite. Verified by
    # fetching: manga-one.com/title/28129 answers 200 and titles itself メイド＆ロイド….
    s.eq(ident.stable_url("https://manga-one.com/manga/28129/chapter/355684"),
         "https://manga-one.com/title/28129",
         "マンガワン's chapter address is rewritten to the work address it serves")

    # AND WHERE THERE IS NO WORK ADDRESS TO FALL BACK ON, nothing is invented.
    for kept in ("https://comic-days.com/episode/12207421983997344603",
                 "https://ichicomi.com/episode/12207421983829237114",
                 "https://manga.nicovideo.jp/comic/72312",
                 # THE COUNTER-CASE THAT DECIDED THE MANGAWAN RULE. This is already a work
                 # address. A rule reading /manga/<n> without demanding a chapter under it would
                 # rewrite all 78 COMIC FUZ rows to /title/<n>, which that site does not serve.
                 "https://comic-fuz.com/manga/2474",
                 # マンガワン's other shape. The work's id is not in it, so there is nothing to
                 # reduce and inventing one would be inventing an address.
                 "https://manga-one.com/viewer/290902",
                 # Already the work on ヤンマガWeb: one segment under /comics/, not two.
                 "https://yanmaga.jp/comics/TANGO",
                 # Two segments, but the second is not a chapter hash.
                 "https://yanmaga.jp/comics/TANGO/volumes",
                 # A work address on a host that uses /title/ without any chapter beneath it.
                 "https://www.ganganonline.com/title/1234",
                 # The rewrite is anchored on the host that was measured. Another site's
                 # /manga/<n>/chapter/<n> is not known to serve /title/<n>.
                 "https://example.jp/manga/28129/chapter/355684"):
        s.eq(ident.stable_url(kept), kept, f"an address with no work prefix is unchanged: {kept}")
    s.eq(ident.stable_url(""), "", "an empty address is empty")

    s.eq(ident.match_key("Ａ　Ｂ！"), "ab", "width, spacing and decoration are not part of a name")
    s.eq(ident.match_key("彩純ちゃん【カラーイラスト特典付】"), ident.match_key("彩純ちゃん"),
         "and neither is a bonus note in brackets")

    # ONE PRODUCER OF THE CREDIT. Both forms have to reach the same people, or the join misses
    # every work whose two sources write the credit differently.
    s.eq(ident.people("[作画]蔵王大志 / [原作]影木栄貴"), {"蔵王大志", "影木栄貴"},
         "the print form names its people")
    s.eq(ident.people("漫画：宮原都,原作：Ru"), {"宮原都", "ru"},
         "and the platform form names the same kind of thing")

    s.eq(ident.mint([]), "w00001", "the first identifier")
    s.eq(ident.mint(["w00001", "w00007"]), "w00008",
         "and the next one is past the highest, not past the count")
    s.eq(ident.mint(["w00003", "not-an-id"]), "w00004", "a stranger in the file decides nothing")

    # A COLLECTION'S STORIES SHARE A CONTAINER URL. Five stories on one pixiv work would otherwise
    # be one identity, which is how an anthology quietly eats its own contents.
    a1 = ident.web_anchor("https://comic.pixiv.net/works/9716", "君は光", shared=True)
    a2 = ident.web_anchor("https://comic.pixiv.net/works/9716", "ときめきライラック", shared=True)
    s.check(a1 != a2, "two stories on one container URL are two works")
    s.eq(ident.web_anchor("https://example.jp/a", "君は光"), "web:https://example.jp/a",
         "while a URL of its own needs no title to disambiguate it")
    s.eq(ident.web_anchor(""), None, "no URL, no anchor")

    reg, conflicts = ident.assign([], [("web:u1", [], "One"), ("web:u2", [], "Two")])
    s.eq([e["id"] for e in reg], ["w00001", "w00002"], "each work gets an identifier")
    s.eq(conflicts, [], "and nothing is in conflict on a first run")

    # THE WHOLE POINT. Running again must return the same identifiers, or every published address
    # breaks on the next build.
    again, _ = ident.assign(reg, [("web:u1", [], "One"), ("web:u2", [], "Two")])
    s.eq([(e["id"], e["title"]) for e in again], [("w00001", "One"), ("w00002", "Two")],
         "a second run over the same works is a no-op")

    grown, _ = ident.assign(reg, [("web:u3", [], "Three")])
    s.eq([e["id"] for e in grown], ["w00001", "w00002", "w00003"],
         "a work absent from this run keeps its identifier and its row")
    s.eq(ident.index(grown)["web:u1"], "w00001", "carried over entries still resolve")

    # A title correction must not mint a second identifier for one work.
    renamed, _ = ident.assign(reg, [("web:u1", [], "One, corrected")])
    s.eq(len([e for e in renamed if not e.get("merged_into")]), 2,
         "a work whose title changed is the same work")
    s.eq([e["title"] for e in renamed if e["id"] == "w00001"], ["One, corrected"],
         "and the registry follows the better title")

    joinedreg, _ = ident.assign(reg, [("web:u1", ["madb:C1"], "One")])
    s.eq(ident.index(joinedreg)["madb:C1"], "w00001",
         "a print anchor joins the work it belongs to rather than making a new one")
    s.eq(ident.index(joinedreg)["web:u1"], "w00001", "and the work keeps its own anchor")

    # THE CASE THAT BROKE THE FIRST VERSION OF THIS, quoted from the corpus. 超深宇宙より愛をこめて
    # is a 15-chapter serialisation and a 1-chapter 読み切り版, two rows with two URLs, and one MADB
    # record whose title matches both. Looking a work up by any of its anchors let the shared
    # C-number pull the two rows into one identity without anybody deciding that they are one work.
    shared, clash = ident.assign(joinedreg, [("web:u2", ["madb:C1"], "Two")])
    s.eq([(c["anchor"], c["held_by"]) for c in clash], [("madb:C1", "w00001")],
         "a print record already attached elsewhere is reported, not taken")
    s.eq(ident.index(shared)["web:u2"], "w00002",
         "and the second work keeps its own identifier instead of being absorbed")
    s.eq(ident.index(shared)["madb:C1"], "w00001", "the print record stays where it was")

    # AN ATTACH IS NOT A MERGE. A work held only as a printed book, whose serialisation had never
    # been read, gains the address it was always published at. Nothing is retired, because the
    # serialisation was never a record of its own.
    attached, err = ident.attach(reg, "web:nico1", "w00001", "copyright line names the publisher")
    s.eq(err, None, "attaching a free anchor succeeds")
    s.eq(ident.index(attached)["web:nico1"], "w00001", "and the work answers to its new address")
    s.eq([a["basis"] for a in next(e for e in attached if e["id"] == "w00001")["attached"]],
         ["copyright line names the publisher"],
         "the evidence travels with the anchor, because nothing re-derives it")
    s.eq(len([e for e in attached if not e.get("merged_into")]), 2,
         "and no identifier is minted or retired")

    # THE REFUSAL. An anchor another live work holds is a claim that the two are one work, and
    # that claim is a merge with its own basis. Silently moving it would join two works by
    # accident, which is the failure `assign` reports as a contested anchor.
    again2, err2 = ident.attach(attached, "web:u2", "w00001", "hopeful")
    s.check(err2 and "w00002" in err2, "an anchor held elsewhere is refused, naming the holder")
    s.eq(ident.index(again2)["web:u2"], "w00002", "and it stays where it was")

    twice, err3 = ident.attach(attached, "web:nico1", "w00001", "again")
    s.eq(err3, None, "attaching the same anchor twice is harmless")
    s.eq(len(next(e for e in twice if e["id"] == "w00001")["attached"]), 1,
         "and does not record the evidence a second time")

    s.check(ident.attach(reg, "web:x", "w99999", "basis")[1],
            "attaching to an identifier that does not exist is refused")

    # THE WHOLE FILE AT ONCE, which is how a discovery pass applies two hundred of them. The joins
    # file is the record and this registry is derived from it, so a second run must be a no-op.
    joins = {"joins": [{"anchor": "web:nico2", "id": "w00001", "basis": "publisher agrees"},
                       {"anchor": "web:u2", "id": "w00001", "basis": "hopeful"},
                       {"anchor": "web:nico3", "id": "w00404", "basis": "nowhere"}]}
    bulk, applied, refused = ident.attach_all(reg, joins)
    s.eq(applied, 1, "only the free anchor is applied")
    s.eq(len(refused), 2, "the held anchor and the unknown identifier are both refused, with why")
    s.eq(ident.index(bulk)["web:nico2"], "w00001", "and the applied one resolves")

    twice2, applied2, _ = ident.attach_all(bulk, joins)
    s.eq(applied2, 0, "running the same joins file again attaches nothing")
    s.eq(len(next(e for e in twice2 if e["id"] == "w00001")["attached"]), 1,
         "and records the evidence once")

    merged = ident.merge(joinedreg, "w00002", "w00001", "same work, author agrees")
    s.eq(ident.index(merged)["web:u2"], "w00001", "a retired identifier still resolves")
    s.eq([e.get("merged_into") for e in merged if e["id"] == "w00002"], ["w00001"],
         "and it stays in the file rather than being deleted")

    got = ident.propose(WEB, PRINTS)
    s.eq(len(got), 2, "both titles match across the populations")
    s.eq(sorted(e["basis"] for _w, _p, e in got), ["title-and-author", "title-and-author"],
         "and both are corroborated by a person named on each side")

    # THE COUNTER-CASE, which is the reason any of this is conditional. citrus+ matched an
    # unrelated 2007 book on its title alone.
    stranger = ident.propose([{"work": "citrus+", "author": "サブロウタ", "url": "u"}],
                             [{"id": "C0", "t": "citrus+", "c": "[著]別人"}])
    s.eq([e["basis"] for _w, _p, e in stranger], ["title-only"],
         "a title match with nobody in common is a lead and not a join")
    s.eq([e["agreed"] for _w, _p, e in stranger], [[]], "and it names no agreement")

    s.eq(ident.propose([], PRINTS), [], "nothing to match against, nothing proposed")

    # RELATED WORKS, NOT MERGED ONES. Both shapes are quoted from the corpus. 超深宇宙より愛をこめて
    # carries its marker in brackets, which `fold` removes, so it folds equal to its serialisation.
    # 白妙様、秘密ですよ／読切版 marks itself after a slash and needs the variant rule.
    s.eq(ident.variant_base("白妙様、秘密ですよ／読切版"), ident.match_key("白妙様、秘密ですよ"),
         "a title naming itself a separate edition gives up its base")
    s.eq(ident.variant_base("超深宇宙より愛をこめて"), None, "an ordinary title is not a variant")
    s.eq(ident.variant_base("読み切り版"), None,
         "and a title that is only the marker has no base to point at")

    pair = [{"work": "超深宇宙より愛をこめて", "author": "アシダカヲズ", "url": "u1"},
            {"work": "超深宇宙より愛をこめて【読み切り版】", "author": "アシダカヲズ", "url": "u2"}]
    got = ident.siblings(pair)
    s.eq(len(got), 1, "a one-shot beside its serialisation is one relation")
    s.eq({got[0][0]["url"], got[0][1]["url"]}, {"u1", "u2"}, "naming both works")

    slash = [{"work": "白妙様、秘密ですよ", "author": "みなみ", "url": "u3"},
             {"work": "白妙様、秘密ですよ／読切版", "author": "みなみ", "url": "u4"}]
    s.eq(len(ident.siblings(slash)), 1, "and so is one that marks itself after a slash")

    # THE COUNTER-CASE. A shared title with nobody in common is how citrus+ went wrong, and it must
    # not become a relation either.
    s.eq(ident.siblings([{"work": "同じ題", "author": "甲", "url": "u5"},
                         {"work": "同じ題", "author": "乙", "url": "u6"}]), [],
         "two works sharing a title and no author are not related on that alone")
    s.eq(ident.siblings([pair[0]]), [], "one work relates to nothing")

    # ── a join that came by identifier ───────────────────────────────────────────────────────
    # The platform route does not compare titles at all: the serialisation's own page named the
    # shop, the shop named the ISBN, the ISBN named the record. So this join is taken where
    # `propose` would have refused for want of agreement on a person's name.
    import collections                                                         # noqa: PLC0415
    web = [{"work": "雨夜の月", "author": "くずしろ", "url": "https://comic-days.com/episode/1",
            "sources": [{"url": "https://comic-days.com/episode/1"},
                        {"url": "https://pocket.shonenmagazine.com/title/2202/episode/9"}]}]
    shared = collections.Counter(w["url"] for w in web)
    ch = ident.chain_joins({"joins": [
        {"platform_url": "https://pocket.shonenmagazine.com/title/2202/episode/9",
         "madb_work_id": "C900", "agreement": "agreed"}]}, web, shared)
    s.eq(ch, {"web:https://comic-days.com/episode/1": ["C900"]},
         "a join found through a work's second platform still lands on the work's own anchor")

    s.eq(ident.chain_joins({"joins": [{"platform_url": "https://nowhere.invalid/x",
                                       "madb_work_id": "C900"}]}, web, shared), {},
         "and a join naming an address this database does not hold attaches to nothing")

    # A LEAD THE CAPTURE MARKED AS DISAGREEING IS NOT A JOIN. くらげバンチ's sidebar on
    # ストロベリークォーツ advertises the author's other series, so the ISBN on that page reaches a
    # record that is not the serialisation. Taking it would be a wrong merge.
    s.eq(ident.chain_joins({"joins": [
        {"platform_url": "https://comic-days.com/episode/1", "madb_work_id": "C901",
         "agreement": "differs"}]}, web, shared), {},
         "a disagreeing lead attaches to nothing")

    # The chain is what `assign` is then given, and the print record must not mint a second id.
    entries, conflicts = ident.assign([], [
        ("web:https://comic-days.com/episode/1", ["madb:C900"], "雨夜の月"),
        ("madb:C900", [], None)])
    s.eq(len(entries), 1, "the record joins the work's identity rather than starting its own")
    s.eq(sorted(entries[0]["anchors"]), ["madb:C900", "web:https://comic-days.com/episode/1"],
         "and the identity holds both addresses")
    s.eq(conflicts, [], "with nothing contested")

    # A WRONG JOIN COMES BACK UNLESS THE REFUSAL IS STORED. This is the whole value of `detach`:
    # the joins file is re-applied on every run, so the three shop-query joins removed on
    # 2026-08-08 would have returned the next morning. けいおん! onto けいおん！Ｓｈｕｆｆｌｅ is the
    # shape: an author query answered with the author's other book, agreeing on the person alone.
    joined, err = ident.attach(
        [{"id": "w00837", "title": "けいおん！Ｓｈｕｆｆｌｅ", "anchors": ["web:fuz1897"]}],
        "madb:C335320", "w00837", "the shop's author query listed it")
    s.eq(err, None, "the wrong join was taken in the first place")
    gone = ident.detach(joined, "madb:C335320", "けいおん! is a different work, numbered 1 to 4")
    s.eq(ident.index(gone).get("madb:C335320"), None, "detaching removes the address")
    s.eq(gone[0]["anchors"], ["web:fuz1897"], "and leaves the work's own")
    s.check("attached" not in gone[0], "the evidence for the wrong join goes with it")
    s.eq([d["anchor"] for d in gone[0]["detached"]], ["madb:C335320"],
         "and the refusal is recorded where the next run will read it")
    back, err2 = ident.attach(gone, "madb:C335320", "w00837", "the shop's author query, again")
    s.check(err2, "so the joins file cannot re-apply it")
    s.eq(ident.index(back).get("madb:C335320"), None, "and the address stays off")
    s.eq(ident.refused(gone), {"madb:C335320": ["w00837"]}, "the refusals are readable as a whole")

    # `assign` is the other door into the same registry, and `propose` re-derives its joins from the
    # two populations every run, so it has to honour the decision as well. Without this the anchor
    # is refused by --attachments and re-attached ten lines later by the assignment.
    kept, _ = ident.assign(gone, [("web:fuz1897", ["madb:C335320"], "けいおん！Ｓｈｕｆｆｌｅ"),
                                  ("madb:C335320", [], "けいおん!")])
    s.eq(ident.index(kept)["madb:C335320"], "w00838",
         "the detached record gets an identifier of its own")
    s.eq(next(e for e in kept if e["id"] == "w00837")["anchors"], ["web:fuz1897"],
         "and the work it was wrongly joined to keeps only its own address")

    # Detaching an anchor nobody holds changes nothing, so a re-run is not an error.
    s.eq(ident.detach(gone, "madb:C999999", "basis"), gone, "detaching what is not held is a no-op")
    # ── A SECOND KIND OF OBJECT MINTS THROUGH THE SAME MACHINERY ────────────────────────────────
    #
    # adapters/credit_identity.py gives a credit the same promise this gives a work, so the prefix
    # is a parameter here instead of a second scheme with its own rules about a contested anchor.
    s.eq(ident.mint([]), "w00001", "the first work identifier")
    s.eq(ident.mint([], "c"), "c00001", "and the first credit identifier, five digits wide too")
    s.eq(ident.mint(["c00001", "w09999"], "c"), "c00002",
         "each prefix counts only its own, so a work id cannot advance the credit sequence")

    # HIGHEST TAKEN PLUS ONE, NEVER THE COUNT. A retired entry stays in the file for ever, so the
    # two numbers part company the moment anything merges, and counting would reissue an address.
    retired = [{"id": "c00001", "merged_into": "c00003", "anchors": ["credit:a"]},
               {"id": "c00003", "anchors": ["credit:b"]}]
    s.eq(ident.mint([e["id"] for e in retired], "c"), "c00004",
         "a retired identifier is never handed out again")

    # A LABEL FOLLOWS A WORK AND NOT A CREDIT. Titles are corrected here often, so a work's entry
    # follows its row. A credit's label is the spelling the identifier was minted for, and a merge
    # lends the retired spelling's anchor to the survivor, so following the row let the losing
    # spelling become the survivor's label.
    lent = [{"id": "c00001", "title": "獅尾", "anchors": ["credit:獅尾", "credit:ししお"]}]
    kept, _c = ident.assign(lent, [("credit:ししお", [], "ししお")], "c", relabel=False)
    s.eq(kept[0]["title"], "獅尾", "the surviving spelling stays the entry's label")
    moved, _c = ident.assign(lent, [("credit:ししお", [], "ししお")], "c")
    s.eq(moved[0]["title"], "ししお", "and a work's title is allowed to move, which is the default")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
