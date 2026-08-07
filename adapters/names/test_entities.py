#!/usr/bin/env python3
"""entities.py: a credit that is not a person says what it is instead."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import testkit  # noqa: E402
from names import entities as e  # noqa: E402

COVERS = ["adapters/names/entities.py"]


def main(s):
    # THE FIVE THE AUTHOR STORE WAS ACTUALLY HOLDING.
    s.eq(e.kind("円谷プロダクション"), "company", "a television company is a company")
    s.eq(e.kind("代々木アニメーション学院"), "school", "a school is a school")
    s.eq(e.kind("「真夜中ぱんチ」製作委員会"), "committee", "a production committee is a real credit")
    s.eq(e.kind("アサルトリリィプロジェクト"), "project", "and a franchise is a project")
    s.eq(e.kind("電撃G'sマガジン"), "magazine", "a magazine in a byline is a venue, not an author")
    s.eq(e.kind("スタジオコロリド"), "studio", "the class word opens this one instead of closing it")
    s.eq(e.kind("東方Project"), "project", "written in Latin on the same corpus")

    # THE PEOPLE. Every one of these is a pen name this corpus carries, and a rule keyed on a single
    # organisation character would take them: 部 in 阿部, 社 as a tail, 会 in a coinage.
    for who in ("阿部潤", "渡部亮平", "そそう支部", "コダマナオコ", "サブロウタ", "タイザン5",
                "はいむらきよたか", "五十嵐純", "わらびもちきなこ"):
        s.eq(e.organisation(who), None, f"{who} is not marked an organisation")

    # NOTATION IS A DUPLICATE, NOT AN ENTITY. The store holds the person separately.
    s.eq(e.kind("はいむらきよたか(キャラクターデザイン)"), "notation",
         "a role welded to a name is cataloguing around a record that already exists")
    s.eq(e.kind("石田可奈(キャラクターデザイン)"), "notation", "the name the role list was widened for")
    s.eq(e.notation("はいむらきよたか"), False, "and the name itself is not notation")
    s.eq(e.notation("南瓜かぷちー(表紙"), False,
         "an unbalanced bracket is a capture that went wrong, which is a different fault")

    # THE SWEEP.
    names = {"円谷プロダクション": {}, "五十嵐純": {}, "一迅社": {"entity": "company"}}
    s.eq(e.sweep(names), {"円谷プロダクション": "company"}, "only what changed is reported")
    s.eq(names["円谷プロダクション"]["entity"], "company", "and the record carries the mark")
    s.eq(e.sweep(names), {}, "a second sweep changes nothing")
    s.check("entity" not in names["五十嵐純"], "a person is left unmarked, which is not a claim")

    # THE CHECK'S OWN SOURCE, which shares no vocabulary with the rule above.
    rows = [{"print": [{"publisher": "一迅社", "imprint": "IDコミックス"}]}, {"print": []}]
    got = e.filed_elsewhere({"ガレットワークス"}, rows)
    s.check("一迅社" in got and "IDコミックス" in got and "ガレットワークス" in got,
            "a publisher, an imprint and the publisher store all count")
    s.check("円谷プロダクション" not in got,
            "and the word list's own catches are not in it, which is the point of asking separately")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
