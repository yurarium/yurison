#!/usr/bin/env python3
"""delivery.py: a print date refuses a delivery date, and a plot summary is not an edition."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit  # noqa: E402
import delivery as D  # noqa: E402

COVERS = ["adapters/delivery.py"]


def main(s):
    # ── A PRINT DATE WINS, WHICH IS THE PART THE OWNER'S RULING DID NOT OVERRIDE ──
    # 一迅社 title 153015 is the extreme the refusal was measured on: printed 2007-11-01 and
    # delivered 2018-07-18, a hundred and twenty-eight months apart.
    s.eq(D.promote([{"printed": "2007-11", "delivered": "2018-07-18"}]),
         (None, D.REFUSED_PRINT), "a stated print date refuses the delivery date outright")
    # 154 of 353 volumes were delivered BEFORE the printing, so the refusal cannot be "the later of
    # the two" or the commonest case in the corpus would slip through as a bound on the printing.
    s.eq(D.promote([{"printed": "2012-10", "delivered": "2007-12-05"}]),
         (None, D.REFUSED_PRINT), "and refuses it when the delivery came first, which is the norm")
    # `published` is the name a source record uses and `printed` the name the capture uses. A reader
    # of only one of them answers "no print date" for the other and promotes over a printing.
    s.eq(D.promote([{"published": "2012-10", "delivered": "2007-12-05"}]),
         (None, D.REFUSED_PRINT), "and reads the source layer's name for the same field")
    # One volume of a set stating a printing is the work having a paper record.
    s.eq(D.promote([{"delivered": "2014-02-14"},
                    {"printed": "2006-04", "delivered": "2014-02-14"}]),
         (None, D.REFUSED_PRINT), "one printed volume answers for the work")

    # ── THE DIGITAL-ONLY CASE, WHICH IS WHAT THE RULING CHANGED ──
    s.eq(D.promote([{"delivered": "2018-10-20"}]), ("2018-10-20", None),
         "真夜中だけのおともだち: the one date the shop states becomes the work's")
    s.eq(D.promote([{"delivered": "2019-04-01"}, {"delivered": "2018-10-20"}]),
         ("2018-10-20", None), "the earliest delivery, so no later date can precede it")
    s.eq(D.promote([]), (None, None), "no volumes is no date and no refusal to explain")
    s.eq(D.promote([{"title": "x"}]), (None, None), "a volume stating neither date says nothing")

    # ── THE COUNTER-CASES, WRITTEN BEFORE THE PATTERNS ──
    # A keyword sweep for 同人誌 over the cmoa cache hits 321 pages of 1,971 and is wrong about
    # these. Each construction was found in a real description and each would be claimed by the
    # obvious rule. THE INPUTS ARE THE MATCHED CONSTRUCTION AND NOT THE DESCRIPTION: a shop's
    # あらすじ is copyrighted (REQUIREMENTS §2), so nothing here is long enough to be one, and the
    # story words that surrounded these phrases are deliberately absent.
    s.eq(D.edition_statement("同人誌風マンガとして登場"), None,
         "同人誌風 is a commercial book in the style of one, which 立花館To Lieあんぐる is")
    s.eq(D.edition_statement("コミティアの人気作家が送る初オリジナル連載"), None,
         "コミティアの人気作家 describes the author and not this edition")
    s.eq(D.edition_statement("参加した同人誌即売会で、崇拝する絵師"), None,
         "an event in the plot is not a statement about publishing")
    s.eq(D.edition_statement("同人誌イベントに出ることを知り"), None,
         "and neither is a character going to one")
    s.eq(D.edition_statement("百合マンガです"), None,
         "a description saying nothing about the edition answers None")
    s.eq(D.edition_statement(""), None, "and so does no description at all")

    # ── WHAT THE SHOP DOES STATE. Each of these is cmoa's or the publisher's note about WHICH
    # EDITION the file is, which is a bibliographic statement and not a synopsis. ──
    s.eq(D.edition_statement("※本作は天野しゅにんたの個人誌作品の電子書籍版となります。"),
         D.EARLIER_EDITION, "cmoa's own boilerplate for a reissued 個人誌")
    s.eq(D.edition_statement("同人誌で発表された４作を収録"),
         D.EARLIER_EDITION, "and the same claim in the publisher's own words")
    s.eq(D.edition_statement("過去に発行した同人誌＆寄稿作品の再録"),
         D.EARLIER_EDITION, "再録 states the earlier printing")
    s.eq(D.edition_statement("創作同人誌、初の電子配信"),
         D.EARLIER_EDITION, "初の電子配信 says the file is new and the book is not")
    s.eq(D.edition_statement("以前同人誌として発行した作品です。大幅な加筆修正有。"),
         D.EARLIER_EDITION, "and so does a publisher naming its own earlier printing")
    s.eq(D.edition_statement("【当コンテンツは同人誌作品です】"),
         D.OWN_DOUJIN, "the file itself is the doujinshi")
    s.eq(D.edition_statement("創作百合同人誌 40P（表紙込）"),
         D.OWN_DOUJIN, "ナンバーナイン states it with the page count")
    s.eq(D.edition_statement("（２０２２年５月発行の創作百合同人誌です）"),
         D.OWN_DOUJIN, "and states the year of its own printing in passing")
    s.eq(D.edition_statement("（コミックマーケット102発行・同人誌）"),
         D.OWN_DOUJIN, "an event named as the printing is the same statement")
    # The tie is common and the more specific claim is the one the refused argument turned on.
    s.eq(D.edition_statement("本作は創作百合同人誌の電子書籍版となります。"), D.EARLIER_EDITION,
         "a description saying both reports the earlier edition")

    s.check(D.mentions_doujin("参加した同人誌即売会で"),
            "the wide count sees the word the strict rule refuses")
    s.check(not D.mentions_doujin("百合マンガです"), "and does not see it where it is absent")

    # ── THE FOLLOW-UP STATE, WHICH IS NOT A QUEUE LENGTH ──
    s.eq(D.followup(D.OWN_DOUJIN), D.SETTLED,
         "a doujinshi the platform sells is finished work under DEFINITIONS §6")
    s.eq(D.followup(D.EARLIER_EDITION), D.OPEN, "an earlier edition stated and not dated is open")
    s.eq(D.followup(None), D.UNSORTED, "and a shop that said nothing sorts into neither")
    s.eq(D.followup(None, self_published=True), D.SETTLED,
         "あおい華葉 publishing her own book has no commercial printing to find")
    s.eq(D.followup(D.EARLIER_EDITION, self_published=True), D.OPEN,
         "a stated earlier edition outranks the publisher field, which is weaker evidence")
    s.check(all(k in D.FOLLOWUP_NOTE for k in (D.SETTLED, D.OPEN, D.UNSORTED)),
            "every follow-up state carries the sentence explaining it")
    s.check(D.BASIS in D.BASIS_NOTE, "and the basis carries its own")

    # ── ONE COUNT, TWO SHAPES OF ROW ──
    # The works list writes `first_event` flat and a work record writes `date_event` inside
    # `first_publication`. Three call sites read this figure and none of them recounts it.
    rows = [{"first_event": D.EVENT, "first_followup": D.SETTLED},
            {"first_event": D.EVENT, "first_followup": D.UNSORTED},
            {"first_event": D.EVENT},
            {"first_publication": {"date_event": D.EVENT, "date_followup": D.OPEN}},
            {"first_event": None, "first": "2006-04"}]
    got = D.tally(rows)
    s.eq(got["rows"], 4, "a printed row is not counted and both shapes of delivery row are")
    s.eq(got["followup"][D.UNSORTED], 2,
         "a row stating no follow-up state counts as unsorted and not as settled")
    s.eq(got["followup"][D.OPEN], 1, "and a work record's own field is read")
    s.eq(D.tally([]), {"rows": 0, "followup": {}}, "no rows is no count and no crash")
    s.eq(D.tally(None)["rows"], 0, "and neither is no argument")

    # ── SELF-PUBLISHING IS THREE FIELDS AGREEING, NOT A GUESS ──
    s.check(D.self_published("あおい華葉", "あおい華葉", "あおい華葉"),
            "author, publisher and imprint all one person")
    s.check(D.self_published("嵩乃朔", "嵩乃朔"), "an unstated imprint does not refute it")
    s.check(not D.self_published("あおい華葉", "一迅社", "百合姫コミックス"),
            "a publisher who is not the author")
    s.check(not D.self_published("あおい華葉 / 別人", "あおい華葉"),
            "one name inside a credit line of several is not one name")
    s.check(not D.self_published("", ""), "two empty fields agree and prove nothing")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
