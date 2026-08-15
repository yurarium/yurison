#!/usr/bin/env python3
"""remaining/releases.py: the fallback routes, and the label-trimming they all need.

COVERS = ['adapters/remaining/releases.py']
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import releases as rm


def main(s):
    # The HOST comes from the page fetched, not from the link. Some installs write the feed link
    # relative, and requiring the absolute form made the route decline silently on コミックゼノン
    # and 一迅プラス, whose feed links had been checked by hand.
    called = []

    def fake_get(url, *a, **k):
        called.append(url)
        if "free_only" in url:
            return "<feed></feed>"
        return ('<feed><entry><title>第1話</title><updated>2026-08-03T00:00:00Z</updated>'
                '<link href="/episode/1"/><author><name>作者</name></author></entry></feed>')

    real, rm.get = rm.get, fake_get
    try:
        rows = rm.from_giga('<a href="/atom/series/42">feed</a>', "https://comic-zenon.com/x")
        s.check(any("comic-zenon.com" in u for u in called),
                "a RELATIVE feed link still resolves, using the page's own host")
        s.check(rows, "and the route returns rows rather than declining")

        # A page with no feed link at all yields nothing rather than raising.
        called.clear()
        s.eq(rm.from_giga("<html>no feed</html>", "https://x.jp/y"), [],
             "no feed link means no rows")

        # A page URL that is not a URL cannot supply a host, so the route declines.
        s.eq(rm.from_giga('<a href="/atom/series/42">f</a>', "not a url"), [],
             "an unusable page URL declines rather than guessing a host")
    finally:
        rm.get = real

    # from_generic must reject anything without a date, and trim the label furniture that rendered
    # pages put next to the chapter: "第1話 … 更新日:" was arriving as the title.
    page = ('<script type="application/ld+json">'
            + json.dumps([{"name": "第1話 はじまり 更新日:", "datePublished": "2026-08-03"}])
            + "</script>")
    rows = rm.from_generic(page)
    for r in rows:
        s.check("更新日" not in r["title"], "the date's own label is trimmed off the chapter name")
    s.eq(rm.from_generic("<html></html>"), [], "a page with nothing extractable yields nothing")

    # Where the page names the element holding the chapter's title, try_markup marks the row exact
    # and this route must take it whole rather than cutting it down. The like and comment counts
    # beside a chapter used to end up in its name: 'Episode.3 -1 0 0' on フラコミlike!.
    listed = ('<ul><li><div class="episode-name">Episode.3 -1</div>'
              '<span>14</span><span>0</span><time>2025/12/26</time></li>'
              '<li><div class="episode-name">Episode.3 -2</div>'
              '<span>0</span><span>0</span><time>2026/01/09</time></li></ul>')
    got = [r["title"] for r in rm.from_generic(listed)]
    s.eq(got, ["Episode.3 -1", "Episode.3 -2"],
         "a named title element is taken whole, counts and all trailing furniture left behind")

    # A HOST WITH ITS OWN ADAPTER IS NOT RE-READ HERE, and this adapter asks one list rather than
    # keeping a copy. Its copy said comic.pixiv.net alone, so ニコニコ's meta line reached the
    # build as a chapter called `3話 無料` for お姉さんは女子小学生に興味があります。 beside 竹コミ's
    # 64 real ones. The counter-case is the whole reason this adapter exists: a GigaViewer host is
    # still its to try, because the platform pass is what skipped the work.
    s.check(rm.dedicated.covers("https://manga.nicovideo.jp/comic/31194"),
            "a host with a dedicated adapter is recognised through the shared list")
    s.check(rm.dedicated.covers("https://comic-zenon.com/episode/12207421983944323839") is None,
            "and a GigaViewer host is not, or the residue this adapter reaches goes unread")


    a_one_shot_states_one_date(s)


def a_one_shot_states_one_date(s):
    """A work the platform marks 読み切り has one chapter, and its date is that chapter's.

    The extractors want a chapter-shaped label before they keep a date. きら星ポータル's page for
    ツイてるギャルとミエてる陰キャ prints 読み切り and 2026年6月17日 and no 第N話, so the date was
    thrown away and the work reported as having no dated chapter list. Ruled by the project owner
    on 2026-08-10: updated reads as released here.
    """
    page = '<p>読み切り</p><span>2026年6月17日</span>'
    got = rm.from_generic(page)
    s.eq(len(got), 1, "a one-shot page yields its single release")
    s.eq(got[0]["updated"], "2026-06-17", "dated by the one date the page states")
    s.check(got[0].get("oneshot"), "and typed as a one-shot rather than a numbered chapter")

    # NARROW ON PURPOSE, and each of these is why.
    s.eq(rm.from_generic('<span>2026年6月17日</span>'), [],
         "a page that does not say it is a one-shot is not read as one")
    s.eq(rm.from_generic('<p>読み切り</p>'), [],
         "nor one that says so and states no date")
    s.eq(rm.from_generic('<p>読み切り</p><span>2026年6月17日</span><span>2026年5月1日</span>'), [],
         "nor one stating two, which is the page saying something this cannot read")

    # AND A PAGE WITH A CHAPTER LIST NEVER REACHES IT, because the ordinary route answers first.
    listed = ('<div>第1話 A<time datetime="2026-06-01">2026年6月1日</time></div>'
              '<div>第2話 B<time datetime="2026-06-08">2026年6月8日</time></div>'
              '<p>読み切り</p>')
    got2 = rm.from_generic(listed)
    s.check(got2 and not any(g.get("oneshot") for g in got2),
            "a page listing chapters is read as chapters even where the word appears on it")


    # ── A CREDIT THE PAGE LABELS, WHERE THE TITLE STATES NONE ─────────────────────────────────
    #
    # The title rule needs a `|` to anchor on. きら星ポータル writes `作品 / 誌名 - サイト`, so
    # ツイてるギャルとミエてる陰キャ arrived with an empty author while its page says
    # `著者：深水たろー` in an anchor to the site's own author page. WORKS-PLAN section 5b.
    import sys as _s
    _s.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from names import credits as _c
    got = rm.LABELLED_CREDIT.search('<a href="/authors/2000538">\u8457\u8005\uff1a\u6df1\u6c34\u305f\u308d\u30fc</a>')
    s.eq(got.group(1) if got else None, "\u6df1\u6c34\u305f\u308d\u30fc",
         "the label names the field and the name follows it, anchor and all")
    s.check(not rm.LABELLED_CREDIT.search("\u8457\u8005\uff1a"),
            "a label with nothing after it names nobody")
    # THE LABEL DOES NOT VOUCH FOR WHAT FOLLOWS IT. Everything still goes through people_only, so a
    # one-shot title sitting where a name belongs is refused exactly as it is in a page title.
    _m = rm.LABELLED_CREDIT.search("\u8457\u8005\uff1a\u8aad\u5207 \u753b\u5bb6\u306e\u8096\u50cf")
    s.eq(_c.people_only(_m.group(1)) if _m else None, None,
         "a label beside a chapter is still not a person")


    # ── A DATE WITH A CLOCK ON IT IS A TIMESTAMP ─────────────────────────────────────────────
    #
    # THE FAULT A READER FOUND. ヤンジャン+ renders `"2026-08-15 20:56:30"` in its page state, which
    # is when the page was served, and this took it for a publication date: 横槍メンゴ新作読切シリ
    # ーズ was dated 2026-08-10 on the tenth and 2026-08-15 on the fifteenth, so it appeared under
    # 更新 as a new one-shot every day for anyone who had already read it.
    s.eq(rm.from_oneshot('読み切りを読む 2026年6月17日'),
         [{"title": "読み切り", "updated": "2026-06-17", "oneshot": True}],
         "a date a platform prints beside the button is the one-shot's date")
    s.eq(rm.from_oneshot('読み切りを読む "2026-06-17 20:56:30"')[0]["updated"], rm.TODAY,
         "and a date carrying hours and minutes is a machine stamp, so the day we read it is what "
         "there is")

    # THE DAY IS MATCHED WHOLE OR NOT AT ALL. Without that the engine backs off the refused
    # timestamp and takes `2026-08-1`, which normalises to the first of the month: a wrong date
    # instead of no date, which is worse than the fault it was fixing.
    s.eq(rm.from_oneshot('読み切り "2026-08-15 20:56:30"')[0]["updated"], rm.TODAY,
         "a refused timestamp yields no date rather than a truncated day")
    s.eq(rm.from_oneshot('読み切り 2026年6月17日 のほか "2026-08-15 20:56:30" とある'),
         [{"title": "読み切り", "updated": "2026-06-17", "oneshot": True}],
         "a page carrying both is read for the date and not for the stamp")

    # THE WORK SURVIVES A PAGE THAT STATES NO DATE, which is the half that took a run down when it
    # did not: refusing the stamp removed the only chapter, the work left the catalogue, and a
    # curated title then named nothing. `build.py` holds a guessed date at first sighting.
    #
    # ── A PLATFORM THAT SERVES ITS CHAPTER LIST FROM AN API ──────────────────────────────────
    #
    # ヤンジャン+ renders a Nuxt shell and fetches the list a reader sees from `webapi.ynjn.jp`, so
    # every route that reads markup found nothing and the work fell through to the one-shot
    # heuristic: 横槍メンゴ新作読切シリーズ shipped as a single untitled 読み切り while the platform
    # lists Vol.1 and Vol.2, both free. The project owner had read both.
    api = ('{"data":{"all_count":2,"episodes":['
           '{"cost":0,"id":296537,"name":" Vol.1","reading_condition":"EPISODE_READ_CONDITION_FREE"},'
           '{"cost":330,"id":309195,"name":" Vol.2","reading_condition":"EPISODE_READ_CONDITION_PAY"}'
           ']},"is_success":true}')
    got = rm.from_ynjn("https://ynjn.jp/title/30352", lambda _u: api)
    s.eq([e["title"] for e in got], ["Vol.1", "Vol.2"],
         "the platform's own list, with the space it pads each name with taken off")
    s.eq([e["access_modes"] for e in got], [["free"], ["purchase"]],
         "and what it costs to open each, which no pattern in the page states")

    # NO DATE IS INVENTED. The API states none, so the row carries the day it was read and
    # `build.py` holds that at first sighting rather than letting it walk with the calendar.
    s.eq({e["updated"] for e in got}, {rm.TODAY}, "a chapter with no stated date is dated today")

    s.eq(rm.from_ynjn("https://comic-days.com/episode/1", lambda _u: api), [],
         "another platform's address is not this platform's list")
    s.eq(rm.from_ynjn("https://ynjn.jp/title/30352", lambda _u: "not json"), [],
         "and an answer this cannot read is no chapter list rather than a guess")

    # AND THE GUARDS THAT WERE ALREADY THERE. Two dates mean the page is saying something this
    # cannot read, and a page that never calls itself a one-shot is not one.
    s.eq(rm.from_oneshot('読み切り 2026年6月17日 と 2026年7月1日'), [],
         "two dates are a page this may not read")
    s.eq(rm.from_oneshot('第1話 2026年6月17日'), [], "and a page with no 読み切り on it is not one")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "remaining.releases"))
