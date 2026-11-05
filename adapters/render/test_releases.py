#!/usr/bin/env python3
"""render/releases.py: badges, and the one that means "you can read this now".

COVERS = ['adapters/render/releases.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as rd


def main(s):
    # A REFUSAL RENDERS TOO, and a page that does not name the work is not a reading of it.
    s.check(not rd.names_work("<html><body><h1>403 ERROR</h1>The request could not be satisfied."
                              "</body></html>", "ひなゆり冒険記"),
            "CloudFront's 403 page does not name the work")
    s.check(rd.names_work("<html><body><h1>ひなゆり冒険記</h1><p>第1話</p></body></html>",
                          "ひなゆり冒険記"), "a work page naming the work does")
    s.check(rd.names_work("<html><body><h1>お姉さんは女子小学生に興味があります。 1巻</h1></body></html>",
                          "お姉さんは 女子小学生に興味があります"),
            "spacing and punctuation do not decide it, and a longer printed title still names it")
    s.check(not rd.names_work("<html><body>anything</body></html>", ""),
            "a target with no title cannot be confirmed by its page")

    # ── A PAGE THAT DOES NOT NAME THE WORK SAYS WHY, WHERE IT CAN ─────────────────────────────
    #
    # Sixteen were recorded as refusals in the week `names_work` came in, and five were.
    cf = "<html><body><h1>403 ERROR</h1>The request could not be satisfied.</body></html>"
    s.eq(rd.why_not_named(cf, "https://drecomi-plus.jp/series/CD00038")[0], "blocked",
         "CloudFront's 403 page is a refusal")
    comici = "<body><p>現在、一部の通信環境からのアクセスを制限しております</p></body>"
    s.eq(rd.why_not_named(comici, "https://bigcomics.jp/series/x")[0], "blocked",
         "comici's restricted-network page is a refusal")
    pixiv = ('<body><nav>ホーム 単行本</nav><p>お探しのページは見つかりませんでした。</p>'
             '<a href="/">トップページへ戻る</a></body>')
    s.eq(rd.why_not_named(pixiv, "https://comic.pixiv.net/works/2454")[0], "missing",
         "pixivコミック's own not-found page says the work is not there")
    one = "<body><p>お探しのページは見つかりませんでした。 コンテンツの掲載期間が 終了した可能性があります。</p></body>"
    s.eq(rd.why_not_named(one, "https://manga-one.com/viewer/268349")[0], "missing",
         "and so does マンガワン's")
    mb = ('<head><link rel="canonical" href="https://www.mangabox.me/reader/"></head>'
          '<body>絶対服従タワーマンション 比良坂小学校の裏校舎</body>')
    r, note = rd.why_not_named(mb, "https://www.mangabox.me/reader/262412/")
    s.eq(r, "missing", "マンガボックス sending a work's reader on to the listing is the work gone")
    s.check("https://www.mangabox.me/reader/" in note, "and the note says where the address went")
    ryu = '<head><link rel="canonical" href="https://comic-ryu.jp"></head><body>新着情報</body>'
    s.eq(rd.why_not_named(ryu, "https://www.comic-ryu.jp/series/hinayuriboukenki/")[0], "missing",
         "COMICリュウ sending a series page to its front page, across www, is the page gone")
    same = ('<head><link rel="canonical" href="https://comic.pixiv.net/works/7440"></head>'
            '<body>何か</body>')
    s.eq(rd.why_not_named(same, "https://comic.pixiv.net/works/7440/")[0], "blocked",
         "a page that calls itself the address we asked and names nothing gives no reason,"
         " and stays the reading names_work was written for")
    other = '<head><link rel="canonical" href="https://elsewhere.jp/"></head><body>何か</body>'
    s.eq(rd.why_not_named(other, "https://www.mangabox.me/reader/1/")[0], "blocked",
         "another site's front page is not this site saying the work is gone")
    s.check(not rd.above("https://www.mangabox.me/reader/1/", "https://www.mangabox.me/read"),
            "a shorter path counts only on a segment boundary")
    s.eq(rd.says_it_is('<meta property="og:url" content="https://comic.pixiv.net/magazines/206">'),
         "https://comic.pixiv.net/magazines/206", "og:url stands in where there is no canonical link")

    # A REFUSAL IS ASKED AGAIN, so one that lifts is seen the next run. A page gone is kept.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        cache = pathlib.Path(d)
        checks = {}
        for url, page in (("https://drecomi-plus.jp/series/CD00038", cf),
                          ("https://comic.pixiv.net/works/2454", pixiv)):
            rd.cache_file(url, cache).write_text(page)
        s.eq(rd.not_named(checks, "ドリコミ+", {"title": "勇者の旅の裏側で",
                                                "url": "https://drecomi-plus.jp/series/CD00038"},
                          cf, cache), "refused", "a refusal is counted as one")
        s.check(not rd.cache_file("https://drecomi-plus.jp/series/CD00038", cache).exists(),
                "and its cached copy is dropped")
        s.eq(checks["ドリコミ+|勇者の旅の裏側で"]["result"], "blocked", "and recorded blocked")
        s.eq(rd.not_named(checks, "pixivコミック", {"title": "姫のためなら死ねる",
                                                    "url": "https://comic.pixiv.net/works/2454"},
                          pixiv, cache), "not there", "a page gone is counted as gone")
        s.check(rd.cache_file("https://comic.pixiv.net/works/2454", cache).exists(),
                "and its cached copy is kept for its week")
        s.eq(checks["pixivコミック|姫のためなら死ねる"]["result"], "missing", "and recorded missing")

    # ── WHAT THE REGISTER SAYS IS NOT A WORK IS NOT RENDERED AS ONE ───────────────────────────
    plat = {"works": [{"title": "ゆりひめ@ピクシブ", "url": "https://comic.pixiv.net/magazines/206"},
                      {"title": "a", "url": "https://comic.pixiv.net/works/1"},
                      {"title": "b", "url": "https://comic.pixiv.net/works/2"}]}
    nw = {"https://comic.pixiv.net/magazines/206": "ゆりひめ@ピクシブ"}
    s.eq([w["title"] for w in rd.works_to_render(plat, nw, 40)], ["a", "b"],
         "pixiv百合姫's channel is passed over")
    s.eq([w["title"] for w in rd.works_to_render(plat, nw, 1)], ["a"],
         "and the limit counts the works rendered, not the one passed over")
    s.eq([w["title"] for w in rd.works_to_render(plat, {}, 40)][0], "ゆりひめ@ピクシブ",
         "where the register lists nothing, every target is rendered")
    # ── A PLATFORM WITH ITS OWN ADAPTER IS NOT RENDERED AS WELL ───────────────────────────────
    spec = {"platforms": [{"id": "magapoke"}, {"id": "ganganonline",
                                               "own_adapter": "adapters/ganganonline/releases.py"}]}
    s.eq([p["id"] for p in rd.rendered_platforms(spec)], ["magapoke"],
         "ガンガンONLINE is read by its own adapter and not rendered beside it")
    s.eq(rd.rendered_platforms({}), [], "and an empty list renders nothing")

    # ── A CONTROL SITTING WHERE A BYLINE SITS IS NOT A BYLINE ─────────────────────────────────
    #
    # `author_near_title` is positional: it takes the first short line under the work's title that
    # is not interface furniture. On a page that HAS a byline that is right, and 怨霊日和 went quiet
    # on マガポケ in March and its page stopped printing one, so the line underneath was the heading
    # of the recommendations block. The work shipped as あなたへのオススメ！ against the イマイ悠 the
    # site was already serving, which is a capture overwriting a good value with a worse one.
    s.eq(rd.author_near_title(
        "<body><h1>怨霊日和</h1><div>あなたへのオススメ！</div><div>イマイ悠</div></body>", "怨霊日和"),
        "イマイ悠", "the recommendations heading is stepped over and the byline under it is taken")

    # A ONE-SHOT LISTS ONE EPISODE, and the platform's own list is enough to say so.
    page = ('<div class="cursor-pointer block border-b-1 x"><p class="line-clamp-1 y">アマデウス</p>'
            '<span>無料</span><p class="text-xs text-gray-700 z">2025/02/24</p></div>')
    eps = rd.episodes_structured(page, rd.STRUCTURED["mangaone"])
    s.eq(eps, [{"title": "アマデウス", "updated": "2025-02-24", "access_modes": ["free"]}],
         "マンガワン's list states a one-shot's date and access")
    s.check(rd.enough(eps, True), "and one row from the platform's own list is a work's chapters")
    s.check(not rd.enough(eps, False), "while one row from a generic extractor is not")

    # THE AGE BADGE IS NOT THE EPISODE'S NAME. pixiv sets 本日UP or 5日前UP beside a recent episode,
    # so the same chapter was captured under a new title every day.
    page = ('<a href="/viewer/stories/1"><div>16-①</div><div>本日UP</div>'
            '<div>更新日：2026年10月22日</div></a>'
            '<a href="/viewer/stories/2"><div>15-②</div><div>5日前UP</div><div>再会</div>'
            '<div>更新日：2026年10月17日</div></a>')
    s.eq([e["title"] for e in rd.episodes_pixiv(page)], ["16-①", "15-② 再会"],
         "a relative-age badge is dropped and the subtitle beside it kept")

    # pixivコミック WRITES ITS FOLLOW BUTTON BEHIND A NON-BREAKING SPACE, so the entity sat in front
    # of the word and a prefix match never saw it. Five works carried `フォローする` as their author.
    s.eq(rd.author_near_title(
        "<body><h1>蝶と帝国</h1><div>&nbsp;フォローする</div><div>もち</div></body>", "蝶と帝国"),
        "もち", "an entity in front of a control does not hide it from the stop list")

    # AND THE ORDINARY CASE IS UNTOUCHED, which is the whole risk of widening a stop list: マガポケ
    # renders 「オカルトタイムズ」 and then 「いどんち」, and that is what this function is for.
    s.eq(rd.author_near_title(
        "<body><h1>オカルトタイムズ</h1><div>いどんち</div></body>", "オカルトタイムズ"),
        "いどんち", "a byline directly under the title is still read")

    # THREE BADGES, NOT TWO. マガポケ marks a chapter --free, --point, or --ticket-free, the last
    # meaning readable now by spending a ticket the platform hands out. It was invisible twice
    # over: the capture was (\w+) and '-' is not a word character, so --ticket-free captured as
    # "ticket"; and anything not exactly "free" was called purchase. The one state meaning "you
    # can read this right now" was recorded as the one meaning you cannot.
    s.check("ticket-free" in rd.ACCESS_BADGE or "ticket" in rd.ACCESS_BADGE,
            "the ticket badge is in the map at all")
    tick = rd.ACCESS_BADGE.get("ticket-free") or rd.ACCESS_BADGE.get("ticket")
    s.eq(tick, ["free-timed"], "a ticket chapter is free-timed, never purchase")
    s.eq(rd.ACCESS_BADGE.get("free"), ["free"], "a free badge is free")

    spec = {"item": r'(?=<li class="ep")',
            "date": r'data-date="(\d{4}-\d{2}-\d{2})"',
            "title": r'class="t">([^<]+)<',
            "free_marker": r"is-free"}
    page = ('<li class="ep" data-date="2026-08-03"><span class="t">第1話</span><i class="is-free">'
            '</i></li>'
            '<li class="ep" data-date="2026-08-10"><span class="t">第2話</span></li>')
    rows = rd.episodes_structured(page, spec)
    s.eq(len(rows), 2, "both items are read")
    if len(rows) == 2:
        s.eq(rows[0]["title"], "第1話", "the title is taken from the spec's group")
        s.eq(rows[0]["updated"], "2026-08-03", "the date is normalised")
        s.eq(rows[0]["access_modes"], ["free"], "the free marker is presence-based")
        s.eq(rows[1]["access_modes"], ["purchase"], "its absence is the other state")

    # An item missing either half is skipped rather than half-recorded, because a row with a title
    # and no date reorders the feed and a row with a date and no title says nothing.
    s.eq(rd.episodes_structured('<li class="ep" data-date="2026-08-03"></li>', spec), [],
         "an item with no title is skipped")
    s.eq(rd.episodes_structured('<li class="ep"><span class="t">第1話</span></li>', spec), [],
         "an item with no date is skipped")
    s.eq(rd.episodes_structured("", spec), [], "an empty page yields nothing")

    # CARRY-OVER. --limit-per-host bounds a run; it must not bound the FILE. pixivコミック has 131
    # targets and a limit of 40, so overwriting cost 68 works and 291 chapters in one run, and 13
    # claims that had been attested went back to untraced.
    import tempfile, yaml as _yaml
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "rendered-x.yaml"
        f.write_text(_yaml.safe_dump({"works": [
            {"work_title": "A", "url": "u/1", "chapters": [{"title": "1", "updated": "2026-01-01"}]},
            {"work_title": "B", "url": "u/2", "chapters": [{"title": "1", "updated": "2026-01-02"}]},
        ]}, allow_unicode=True))
        kept = rd.carry_over(f, [{"url": "u/1"}])
        s.eq([w["url"] for w in kept], ["u/2"],
             "a work this run did not reach is kept")
        s.check(all(w["url"] != "u/1" for w in kept),
                "and a work it did reach is not carried over, so the fresh reading wins")
        s.eq(rd.carry_over(f, [{"url": "u/1"}, {"url": "u/2"}]), [],
             "a run that reached everything carries nothing over")
        s.eq(rd.carry_over(pathlib.Path(d) / "absent.yaml", [{"url": "u/1"}]), [],
             "a first run has nothing to carry over and does not fail")


    a_clean_read_is_recorded(s)
    renders_rendered_together_do_not_expire_together(s)


def renders_rendered_together_do_not_expire_together(s):
    """Every page was rendered on 2026-10-20 in 2944 s of a 50-minute step, so every page expired
    on the 27th and the step was killed half way. The age limit now varies by url, and past the
    run's budget a page is read from whatever copy it has rather than rendered."""
    import tempfile, time as _time
    urls = [f"https://example.test/works/{n}" for n in range(200)]
    ages = {rd.max_age(u) for u in urls}
    s.check(len(ages) > 1, "two hundred urls do not share one age limit")
    s.check(all(rd.RENDER_AGE_DAYS - rd.STAGGER_DAYS <= a <= rd.RENDER_AGE_DAYS for a in ages),
            "and each lies within the stagger below the full age")
    s.eq(rd.max_age(urls[0]), rd.max_age(urls[0]), "a url keeps the same limit from run to run")

    with tempfile.TemporaryDirectory() as d:
        cache = pathlib.Path(d)
        url = "https://example.test/old"
        key = rd.re.sub(r"[^A-Za-z0-9]", "_", url)[-120:]
        old = cache / f"{key}.html"
        old.write_text("<html>stale</html>")
        month = _time.time() - 30 * 86400
        __import__("os").utime(old, (month, month))
        spent = _time.time() - 1
        s.eq(rd.render(url, cache, deadline=spent), "<html>stale</html>",
             "past the budget, a stale copy is read instead of rendering")
        try:
            rd.render("https://example.test/never", cache, deadline=spent)
            s.check(False, "a page with no copy past the budget is refused")
        except rd.OverBudget:
            s.check(True, "a page with no copy past the budget is refused")


def a_clean_read_is_recorded(s):
    """Only failures reached the ledger, so success looked like never having looked.

    `checkstate.record` was called on `blocked` and on `empty` and nowhere else. `schedule.py` sorts
    by `overdue_days`, which returns None for a work with no row, and None sorts first as most
    overdue. So a work read cleanly every run was permanently the most overdue thing in the list:
    アイ・ヘイ・チュー published on 2026-08-07, was read without trouble, and was listed overdue on
    the 8th.
    """
    import sys as _s
    _s.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    import checkstate

    checks = {}
    checkstate.record(checks, "P", "read cleanly", "ok", when="2026-08-07")
    checkstate.record(checks, "P", "came back empty", "empty", when="2026-08-01")
    s.eq(checkstate.overdue_days(checks, "P", "read cleanly", __import__("datetime").date(2026, 8, 8)), 1,
         "a work read cleanly yesterday is one day since we looked")
    s.eq(checkstate.overdue_days(checks, "P", "came back empty", __import__("datetime").date(2026, 8, 8)), 7,
         "and one that failed a week ago is seven")
    s.eq(checkstate.overdue_days(checks, "P", "never seen", __import__("datetime").date(2026, 8, 8)), None,
         "a work with no row is None, which is what sorts first")
    s.check(checkstate.overdue_days(checks, "P", "read cleanly", __import__("datetime").date(2026, 8, 8))
            < checkstate.overdue_days(checks, "P", "came back empty", __import__("datetime").date(2026, 8, 8)),
            "so recording the clean read is what stops it outranking a real failure")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "render.releases"))
