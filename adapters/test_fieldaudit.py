#!/usr/bin/env python3
"""fieldaudit: a platform that lost a field across its own rows, told from one that never had it.

COVERS = ['adapters/fieldaudit.py']

WHY THE THRESHOLDS ARE THE SUBJECT. Each rule was separated after the shape before it hid
something: a bare total of three failed a run on four rows that were four platforms each publishing
an update the way they publish it, and the rows stating no access were quietly consuming the
tripwire meant to catch a lost title. A threshold nobody tests is a number somebody picked.

NO DATABASE IS BUILT HERE, AND THE LINT WAS RIGHT ABOUT WHY. This suite opened its own sqlite and
planted rows in it, and `adapters/lint/onewriter.py` counts that as a second writer of the store:
the exemption belongs to the compiler and its own suite, and a fixture spelling the schema out here
is a second statement of the schema as well. The query is a population in `relational/asks.py` now,
asked where the corpus's questions live, and what this module owns is the reading of the answer.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fieldaudit                                                       # noqa: E402
import testkit                                                          # noqa: E402

COVERS = ["adapters/fieldaudit.py"]


def _rows(rows_, route="own"):
    """Rows as the store's population returns them. `rows_` is (platform, ep, author, modes)."""
    return [{"id": f"r{i}", "plat": plat, "route": route, "ep": ep, "author": author,
             "work": f"work {i}", "access": modes}
            for i, (plat, ep, author, modes) in enumerate(rows_)]


def main(s):
    # ── THE QUESTION IS THE STORE'S, AND IT ASKS FOR WHAT THE AUDIT READS ─────────────────────
    #
    # A population that stopped returning `access` would make every row look unpriced, so the
    # columns are named here rather than assumed from the rows a run happens to have.
    from relational import asks
    sql = asks.POPULATIONS[fieldaudit.POPULATION]["sql"]
    for column in ("plat", "route", "ep", "author", "work", "access"):
        s.check(f" AS {column}" in sql, f"the population names {column}")
    s.check("provenance = 'attested'" in sql, "and asks only about attested rows")

    # ── A ROW MISSING A NAME, AND ONE MISSING ONLY ITS PRICE ─────────────────────────────────
    #
    # The two are counted apart because they are different faults. An empty string and whitespace
    # are both "no episode title": a selector matching the wrong element returns that element.
    mixed = _rows([
        ("A", "第1話", "作者", 1),      # complete
        ("A", "", "作者", 1),           # no episode title
        ("A", "   ", "作者", 1),        # whitespace is not a title either
        ("A", "第2話", None, 1),        # no author
        ("A", "第3話", "作者", 0),      # named, states no access
    ])
    s.eq(len(fieldaudit.unnamed(mixed)), 3, "a blank, a whitespace title and a missing author")
    s.eq([r["ep"] for r in fieldaudit.unpriced(mixed)], ["第3話"],
         "and a row is unpriced only where it is otherwise complete")

    # ── A MOVED SELECTOR TAKES OUT ITS OWN PLATFORM ──────────────────────────────────────────
    #
    # Three rows is the floor because a platform publishing one or two updates says nothing either
    # way, and half its rows is what tells a moved selector from a work published without a byline.
    lost = _rows([("A", "", "作者", 1)] * 3 + [("A", "第1話", "作者", 1)])
    s.eq(fieldaudit.moved(lost), [("A", 3, 4)], "three of four rows is a platform that lost it")
    s.eq(fieldaudit.moved(_rows([("A", "", "作者", 1)] * 2 + [("A", "第1話", "作者", 1)] * 2)), [],
         "two is under the floor, whatever share of the platform it is")
    s.eq(fieldaudit.moved(_rows([("A", "", "作者", 1)] * 3 + [("A", "第1話", "作者", 1)] * 4)), [],
         "and three of seven is a handful rather than a selector")

    # SCATTERED ACROSS PLATFORMS IS NOT A MOVED SELECTOR, which is the case that failed a run: four
    # rows on three platforms in two shapes, each publishing an update the way it does.
    scattered = _rows([("ニコニコ漫画", "", "作者", 1), ("ニコニコ漫画", "", "作者", 1),
                       ("ヤンジャン+", "読み切り", None, 1), ("きら星ポータル", "読み切り", None, 1)]
                      + [("ニコニコ漫画", "第1話", "作者", 1)] * 8)
    s.eq(fieldaudit.moved(scattered), [], "no platform is over its share")
    s.eq(fieldaudit.findings(scattered), [], "so the run is not stopped")

    # ── AND A DRIFT ACROSS EVERYTHING STILL TRIPS ────────────────────────────────────────────
    #
    # A change to a shared renderer shows up as a few rows everywhere and no platform over its
    # share, which per-platform counting cannot see.
    wide = _rows([(f"P{i}", "", "作者", 1) for i in range(fieldaudit.SPREAD + 1)]
                 + [(f"P{i}", "第1話", "作者", 1)
                    for i in range(fieldaudit.SPREAD + 1) for _ in range(3)])
    s.eq(fieldaudit.moved(wide), [], "one lost row per platform is nobody's selector")
    s.eq(len(fieldaudit.findings(wide)), 1, "and the spread rule is what catches it")
    s.check("spread too widely" in fieldaudit.findings(wide)[0],
            "saying which rule fired, because they mean different things")

    # ── A ROUTE THAT READS NO ACCESS IS NOT A ROW THAT LOST ONE ──────────────────────────────
    #
    # コミックエッセイ劇場, やわらかスピリッツ and てれびくんヒーローコミックス are read by
    # `try_labels`, which takes a bare list of chapter labels off a page carrying no date, no byline
    # and no price. Their rows grow as they publish, so a flat ceiling over them counts the corpus
    # rather than a fault: コミックエッセイ劇場 alone reached 23 rows and took the total to 107 on
    # 2026-08-16, stopping a run in which nothing had gone wrong.
    LABELS = {"コミックエッセイ劇場"}
    quiet = _rows([("コミックエッセイ劇場", "第1話", "作者", 0)] * 40)
    s.eq(fieldaudit.unpriced(quiet, LABELS), [],
         "a route the register says reads no access contributes no silent rows")
    s.eq(len(fieldaudit.unpriced(quiet, set())), 40,
         "and the same rows count where the register says nothing about the route")

    # ASKED OF THE REGISTER RATHER THAN OF THE ROWS, which is the whole of why it is safe. A
    # platform whose every row is silent may equally have lost the field this morning, and a rule
    # that inferred the exemption from the rows would excuse exactly the failure this exists for.
    s.check("コミックエッセイ劇場" in fieldaudit.route_states_no_access(),
            "the coverage register names the labels routes")
    s.check("マガポケ" not in fieldaudit.route_states_no_access(),
            "and a platform read by a route that does state access is not among them")

    # ── A PRICE SELECTOR MOVES THE SAME WAY A TITLE SELECTOR DOES ────────────────────────────
    #
    # The access side had only a flat ceiling, so the one instrument that could fire was the one
    # that counts the corpus. Same floor, same share, and what makes it a loss rather than a route
    # is that some row THAT ROUTE read does state access.
    lost_price = _rows([("P", "第1話", "作者", 0)] * 3 + [("P", "第2話", "作者", 1)])
    s.eq(fieldaudit.access_moved(lost_price, set()), [("P", 3, 4)],
         "three of four rows silent on a route that states access elsewhere")
    s.eq(fieldaudit.access_moved(_rows([("P", "第1話", "作者", 0)] * 4), set()), [],
         "a route that states access on none of its rows is a route and not a loss")

    # PER ROUTE AND NOT PER PLATFORM, which is the difference between a finding and a false one.
    # コミックゼノン is read by its own adapter, stating access on both its rows, and by the
    # catch-all resolver, stating it on neither. Counted per platform that is three of four rows
    # silent on a platform that states access, and nothing has moved.
    zenon = (_rows([("コミックゼノン", "読切 ゲームフレンド", "作者", 1),
                    ("コミックゼノン", "読切 予行練習", "作者", 1)], route="comic-zenon")
             + _rows([("コミックゼノン", "読み切り", "作者", 0),
                      ("コミックゼノン", "読み切り2", "作者", 0)], route="remaining"))
    s.eq(fieldaudit.access_moved(zenon, set()), [],
         "two routes on one platform are two readings, and neither has stopped")
    s.eq(fieldaudit.findings(zenon), [], "so the run is not stopped")

    # ── ROWS STATING NO ACCESS ARE THEIR OWN NUMBER ──────────────────────────────────────────
    #
    # マガポケ is read by two routes and one of them carries access on none of its chapters, so a
    # work reached only by the feed states none. Counted with the lost titles, those consumed the
    # tripwire meant to catch the first row that really lost one.
    # A SHARE AND NOT A COUNT, after a count tripped three times in three days and was right once.
    # It went 25 to 60 to 100 to 80, and each move was the corpus rather than a fault: three
    # `try_labels` platforms, then those platforms publishing, then コミックDAYS listing 第39話 to
    # 第46話 of ドリーム☆ジャンボ☆ガール in one go, stated `observed` by the platform's own atom
    # feed. A number that has to be raised whenever the corpus does something ordinary is measuring
    # the corpus. Spread across platforms so no route is over its own share.
    quiet = 60
    under = (_rows([(f"P{i}", "第1話", "作者", 0) for i in range(quiet)])
             + _rows([(f"P{i}", "第2話", "作者", 1) for i in range(quiet) for _ in range(9)]))
    s.eq(fieldaudit.findings(under, set()), [],
         "six per cent of the rows silent is where this corpus has run all week")
    over = (_rows([(f"P{i}", "第1話", "作者", 0) for i in range(quiet)])
            + _rows([(f"P{i}", "第2話", "作者", 1) for i in range(quiet) for _ in range(4)]))
    s.eq(len(fieldaudit.findings(over, set())), 1, "a fifth of them is a finding")
    s.check("state no access" in fieldaudit.findings(over, set())[0], "which says so in its words")

    # AND IT STAYS PUT AS THE CORPUS GROWS, which is the whole point of asking a proportion. The
    # same six per cent on twice the rows is the same answer.
    s.eq(fieldaudit.findings(under + under, set()), [],
         "twice the corpus at the same share is still not a finding")

    # A FLOOR UNDER THE SHARE, because a share of a handful is noise: a run that captured twenty
    # rows and stated access on none is a run to look at, and a tenth of twenty is two.
    s.eq(fieldaudit.findings(_rows([("P", "第1話", "作者", 0)] * fieldaudit.NO_ACCESS_FLOOR),
                             set()), [],
         "a capture too small to have a share is not judged on one")

    # ── THE HEALTHY ANSWER ───────────────────────────────────────────────────────────────────
    s.eq(fieldaudit.findings(_rows([("A", "第1話", "作者", 1)] * 40)), [],
         "a capture with every field on every row stops nothing")
    s.eq(fieldaudit.findings([]), [],
         "and a run that captured nothing has no field to have lost, which the count says instead")


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
