#!/usr/bin/env python3
"""bookwalker.py: reading a shop's completion marker, and only about the right work."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import bookwalker as bw  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/bookwalker.py"]

TAIL = " - マンガ（漫画）│電子書籍無料試し読み・まとめ買いならBOOK☆WALKER"

# Both quoted from the served pages, which is the whole evidence for the rule.
DONE = f"<title>【完結】コンカフェ嬢は恋を着る（ＦＵＺコミックス）{TAIL}</title>"
RUNNING = f"<title>きみが死ぬまで恋をしたい（百合姫コミックス）{TAIL}</title>"


def main(s):
    s.eq(bw.status(DONE, "コンカフェ嬢は恋を着る"), "completed",
         "the shop marks a finished series in front of its name")

    # THE COUNTER-CASE, checked before believing the rule. きみが死ぬまで恋をしたい updates every
    # month and its page carries no 完結 at all, so the marker distinguishes rather than decorates.
    s.eq(bw.status(RUNNING, "きみが死ぬまで恋をしたい"), None,
         "and a running series carries no marker, which is not evidence either way")

    # A MARKER READ OFF SOMEBODY ELSE'S PAGE IS WORSE THAN NO ANSWER. A title search routinely
    # returns a different series, so the page has to name the work that was asked about.
    s.eq(bw.status(DONE, "まったく別の作品"), None,
         "a completed page for another work says nothing about this one")
    s.eq(bw.status(DONE, "コンカフェ"), "completed",
         "while a work whose name the page contains is the work the page is about")

    # Width and spacing differ between our catalogue and the shop, and must not decide it.
    s.eq(bw.status("<title>【完結】ＡＢＣの日々" + TAIL + "</title>", "ABCの日々"), "completed",
         "full-width and half-width name the same series")

    s.eq(bw.status("", "any"), None, "no page, no answer")
    s.eq(bw.status("<html>no title here</html>", "any"), None, "and no title, no answer")

    s.eq(bw.series_ids('a href="https://bookwalker.jp/series/490418/" '
                       'b href="https://bookwalker.jp/series/490418/" '
                       'c href="https://bookwalker.jp/series/190256/"'),
         ["490418", "190256"], "each series once, in the order the search lists them")
    s.eq(bw.series_ids("nothing"), [], "and none where the search found none")

    # THE OTHER WAY THE SHOP SAYS IT, and the one this module used to miss. 惑星クローゼット ended
    # in 2020 and carries no 【完結】 in any page title, so `status` answered None about it while
    # its volume list tags every volume 完結 and summarises them on tag 42. The whole dormant sweep
    # ran on the title-only reader, which is why its silence was never evidence.
    # Both fixtures are quoted from the served /list/ pages.
    ENDED = ('<title>惑星クローゼット（バーズコミックス）(マンガ（漫画）)の電子書籍無料試し読みなら'
             'BOOK☆WALKER</title>'
             '<a href="https://bookwalker.jp/tag/1491/?a=1"><span>青年マンガ(4)</span></a>'
             '<a href="https://bookwalker.jp/tag/42/?a=1"><span>完結(4)</span></a>'
             '<a href="https://bookwalker.jp/tag/55/?a=1"><span>SF(4)</span></a>')
    RUNS = ('<title>きみが死ぬまで恋をしたい（百合姫コミックス）(マンガ（漫画）)の電子書籍無料試し読み'
            'ならBOOK☆WALKER</title>'
            '<a href="https://bookwalker.jp/tag/14/?a=1"><span>百合(11)</span></a>'
            '<a href="https://bookwalker.jp/tag/146/?a=1"><span>ファンタジー(4)</span></a>')

    s.eq(bw.status_from_list(ENDED, "惑星クローゼット"), "completed",
         "a volume list tagged 完結 says the series finished")
    s.eq(bw.status_from_list(RUNS, "きみが死ぬまで恋をしたい"), None,
         "and a running series carries no such tag, so the tag distinguishes")

    # Tag 55 is SF on this very page. Reading completion off a tag number nobody checked is how a
    # sweep produces confident wrong answers, so the id is pinned by its label.
    s.eq(bw.tags(ENDED)["55"], "SF(4)", "tag 55 is a genre, not the completion marker")
    s.eq(bw.tags(ENDED)["42"], "完結(4)", "tag 42 is the completion marker")

    s.eq(bw.status_from_list(ENDED, "まったく別の作品"), None,
         "a finished list for another work says nothing about this one")
    s.eq(bw.status_from_list("", "any"), None, "no page, no answer")
    s.eq(bw.tags("nothing here"), {}, "and no tags where the page has none")

    # ── THE NEWEST VOLUME'S OWN DESCRIPTION ───────────────────────────────────────────────────
    # 女だから、とパーティを追放されたので… carries no 【完結】 and no 完結 tag, and its sixth
    # volume, titled 【最新刊】, says 堂々完結. Built from the shape, not the shop's sentence.
    work = "女だから、とパーティを追放されたので伝説の魔女と最強タッグを組みました"
    def page(title, desc):
        return (f"<title>{title} - BOOK☆WALKER -</title>"
                f'<meta property="og:description" content="{desc}">')
    newest = page(f"【最新刊】{work}（６）", "物語、堂々完結！")
    s.eq(bw.blurb_completed(newest, work), "completed", "the newest volume saying 完結 settles it")
    s.eq(bw.blurb_completed(page(f"{work}（３）", "物語、堂々完結！"), work), None,
         "but only the newest: an earlier volume can describe an arc that ended mid-run")
    s.eq(bw.blurb_completed(page("【最新刊】別の作品（６）", "堂々完結！"), work), None,
         "and only about this work")
    for desc in ("第一部完結！", "学園編完結", "未完結の物語", "完結編スタート"):
        s.eq(bw.blurb_completed(page(f"【最新刊】{work}（６）", desc), work), None,
             f"{desc} does not end the series")
    s.eq(bw.blurb_completed(page(f"【最新刊】{work}（６）", "感動の最終巻"), work), "completed",
         "and a last volume named as one does")
    s.eq(bw.latest_volume('<a href="https://bookwalker.jp/de1-2/">6</a><a href="https://bookwalker.jp/de0-1/">5</a>'),
         "https://bookwalker.jp/de1-2/", "the newest volume is the list's first product")

    # ── ASKED ONCE, AND AGAIN ONLY WHEN IT MAY HAVE CHANGED ────────────────────────────────────
    ws = [{"work": x} for x in ("new", "quiet", "grew", "old", "bare")]
    checked = {"quiet": {"on": "2026-10-01", "volumes": 6},
               "grew": {"on": "2026-10-01", "volumes": 6},
               "old": {"on": "2026-03-01", "volumes": 6},
               "bare": "2026-10-01"}
    vols = {"quiet": 6, "grew": 7, "old": 6, "bare": 9}
    got = [w["work"] for w in bw.plan(ws, checked, "2026-10-15", 10, vols)]
    s.eq(got, ["new", "old", "grew"],
         "never asked first, then half a year on, then a work holding a new volume")
    s.check("quiet" not in got, "a work asked this month with no new volume is not asked again")
    s.check("bare" not in got,
            "and an entry an older run wrote as a bare date says nothing about volumes, so waits")
    s.eq([w["work"] for w in bw.plan(ws, checked, "2026-10-15", 1, vols)], ["new"],
         "and the batch is capped")
    import yaml
    s.eq(bw._asked(yaml.safe_load('{"on": "2026-10-01", "volumes": 6}')), ("2026-10-01", 6),
         "the date survives YAML, which reads a bare `on` as true")

if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
