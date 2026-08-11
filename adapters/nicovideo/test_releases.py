#!/usr/bin/env python3
"""nicovideo/releases.py: dates from meta_info, or none at all.

COVERS = ['adapters/nicovideo/releases.py']

THE PAGES HERE ARE REAL. Every assertion about markup runs against `data/fixtures/nicovideo/`,
which holds four ニコニコ work pages cut down from the capture cache with their addresses and
retrieval dates recorded. The short literals below are different in kind: each states one parsing
rule, so it is written out where a reader can see the rule and the input together.

WHY THAT CHANGED. This file used to carry the pages as string constants somebody wrote, and the
adapter's two worst faults were faults in what those constants imagined. The sidebar was missing,
so a pattern reading the wrong element passed. The copyright line was spelt `(C)`, which is the
minority spelling, and the majority went unread on 98 of 154 pages for as long as the test agreed
with the author about what a page looks like.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fixtures
import testkit
import releases as nv


def main(s):
    s.eq(nv.iso(2026, 8, 3), "2026-08-03", "single digits are padded, so dates sort as strings")
    s.eq(nv.iso("2026", "12", "31"), "2026-12-31", "strings are accepted")

    page = '<div class="meta_info">2026年8月3日更新 / 2025年1月5日開始</div>'
    got = nv.parse(page)
    s.eq(got.get("updated"), "2026-08-03", "the update date is read")
    s.eq(got.get("started"), "2025-01-05", "the start date is read")

    # A missing block means NO date. §6: a guessed date is worse than none, because it silently
    # reorders the feed and nothing downstream can tell it was invented.
    s.check(nv.parse("<html>no meta_info here</html>") is None,
            "an absent block yields None rather than a guess")

    partial = nv.parse('<div class="meta_info">2026年8月3日更新</div>')
    s.eq(partial.get("updated"), "2026-08-03", "an update date alone is read")
    s.check("started" not in partial, "and no start date is invented")

    unparsable = nv.parse('<div class="meta_info">近日公開</div>')
    s.check(not (unparsable or {}).get("updated"), "text without a date yields no date")

    # ── one whole work page, as the platform serves it ────────────────────────────────────────
    #
    # 球詠 in きららベース. Read `why` in the fixture header for what each kept block is doing
    # there; the sidebar in particular looks like padding and is the counter-case.
    kirara = fixtures.load("nicovideo/work-in-a-channel")
    whole = nv.parse(kirara)

    s.eq(whole["updated"], "2026-07-28", "the work-level 更新 date is read")
    s.eq(whole["started"], "2016-08-13", "and 開始, which is a real serialisation start date")
    s.eq(whole["free_episodes"], 4, "[ 4話 無料 ] states how many episodes are free")
    s.check("app_only_route" not in whole,
            "a work a browser can read is not an app-only route")

    # A ROUTE WITH NO BROWSER-READABLE CHAPTER. 満腹百合 is the counter-case that keeps this from
    # swallowing the ordinary free-trial shape: 4 of its 7 episodes are app-only and 3 are not, so
    # it IS a web serialisation and must not be marked. 108 works are in that state and only 12
    # have no readable chapter anywhere.
    s.check("app_only_route" not in nv.parse(fixtures.load("nicovideo/work-part-app-only")),
            "a work whose later chapters moved into the app is still a web serialisation")
    s.check(nv.parse(fixtures.load("nicovideo/work-app-only-route"))["app_only_route"],
            "a work with no browser-readable episode anywhere is an app-only route")

    # THE REAL BLOCK IS NOT ONE LINE. The invented version read
    # `2026年07月16日更新 2025年06月19日開始 [ 5話 無料 ]` as a single run of text. The page puts
    # each date on its own line, wraps the free-episode count in a span, and hangs the favourite
    # button inside the same div, so the whitespace collapse in `parse` is load-bearing rather
    # than tidiness.
    s.check("\n" in kirara[kirara.find('class="meta_info"'):][:400],
            "the block really does span lines, which is what the collapse is for")

    s.eq(whole["title"], "球詠", "ニコニコ states the work and its author in the title element")
    s.eq(whole["author"], "マウンテンプクイチ", "and the author survives the split on /")

    # ── the copyright line, in the spelling the platform actually uses ────────────────────────
    #
    # THE FAULT THIS PINS. `rights` matched `<small class="copyright">(C)` and nothing else, and
    # returned [] for every other spelling, which is indistinguishable from a page stating no
    # rights (§5). Across the 184 cached pages, 157 carry the line and 101 of them open with
    # something the old pattern could not read: © bare, © with the emoji variation selector, Ⓒ,
    # （C）and (ｃ) in fullwidth, &copy with no semicolon, and one @. This page is one of them.
    s.eq(nv.rights(kirara), ["マウンテンプクイチ", "芳文社"],
         "the copyright line names the author and the publisher")
    s.check("©" in kirara, "and this page writes the mark as ©, not as (C)")
    s.eq(nv.rights("<p>no copyright line here</p>"), [],
         "a page without the element yields nothing rather than a guess")

    # ── the rendered episode list ─────────────────────────────────────────────────────────────
    #
    # PARTIAL BY CONSTRUCTION, and this page proves it in a way the invented one could not: 球詠
    # has 244 numbered positions and the page renders four of them, the first and the last three.
    eps = nv.episodes(kirara[kirara.find('id="episode_list"'):])
    s.eq([e["number"] for e in eps], [1, 20, 243, 244],
         "the platform renders the opening episode and the newest few, not the work")
    s.eq(eps[1]["title"], "番外編〜新変化球？〜",
         "an extra sits between them, at its own position number")
    s.eq(eps[-1]["url"], "https://manga.nicovideo.jp/watch/mg1046376",
         "an episode link is made absolute")
    s.check(all("updated" not in e for e in eps),
            "no episode carries a date, because the platform states none")

    # ONE READER OF THIS MARKUP. `parse` used to walk the episode list itself for the newest item,
    # and the discovery pass needed the whole list. Two copies of one rule is the shape that has
    # produced seven bugs here, so `parse` consumes `episodes`.
    s.eq(whole["latest_episode"], "第117球：織り込み済みだけど(後編)",
         "the newest episode is the highest-numbered one")
    s.eq(whole["rendered_episodes"], 4, "and the page says how many it showed")
    s.ne(whole["latest_episode"], "番外編〜新変化球？〜",
         "an extra sitting between numbered chapters is not mistaken for the newest")

    # ── which channel the work is in ──────────────────────────────────────────────────────────
    #
    # The old rule read a real element correctly and the element was the wrong one. It took the
    # first /official/ address on the page, which is the first banner in the sidebar, and the
    # sidebar is identical on every page of the site. All 180 works we held answered `nicomanga`.
    s.eq(nv.channel(kirara), {"channel": "きららベース", "channel_slug": "kirara"},
         "the channel is the one the breadcrumb names")
    s.check("/official/nicomanga/" in kirara,
            "the banner the broken rule matched is still in this fixture, or it proves nothing")
    s.check("nicomanga" not in str(nv.channel(kirara)),
            "and the answer is not that banner")

    # 「[公式]」 is the breadcrumb's own label for a channel, not part of its name.
    # data/platforms.yaml records it as きららベース, and a value carrying the prefix joins to
    # nothing.
    s.check("[公式] きららベース" in kirara, "the page writes the label into the crumb")
    s.eq(nv.channel(kirara)["channel"], "きららベース", "and it is not part of the name")

    # A slug with a hyphen in it. `[a-z0-9_]+` stopped at the hyphen and would have filed
    # ニコニコ百合姫's works under a channel called `nico`, which is not a channel at all.
    spica = fixtures.load("nicovideo/work-in-a-hyphenated-channel")
    s.eq(nv.channel(spica), {"channel": "ニコニコ百合姫", "channel_slug": "nico-yurihime"},
         "a hyphen belongs to the slug and does not end it")

    # THE STATE THIS MUST NOT FILL IN. ニコニコ漫画 carries a section anybody may post to, and a
    # work there has no channel: the second crumb is a genre listing and the sidebar is unchanged.
    # 19 of the 180 works we hold are in this position, so a rule that always answers is wrong 19
    # times and looks right (§5).
    solo = fixtures.load("nicovideo/work-in-no-channel")
    s.eq(nv.channel(solo), {},
         "a work outside the official channels is recorded as being in none")
    s.check("/official/nicomanga/" in solo,
            "and the sidebar it did not answer from is present here too")
    s.eq(nv.parse(solo)["title"], "同居人に片思いしてる百合漫画",
         "the rest of the page is read as usual")
    s.check("channel" not in nv.parse(solo),
            "and parse carries no channel key rather than an empty one")

    # A WORK ITS AUTHOR POSTED HAS NO COPYRIGHT ELEMENT AT ALL. The old test asserted this against
    # `<p>no copyright line here</p>`, which is nobody's page. This is the state on a real one.
    s.eq(nv.rights(solo), [], "a page that states no rights yields none")
    s.check('class="copyright"' not in solo, "because the element is genuinely absent")

    # WHAT AN ERROR PAGE ACTUALLY LOOKS LIKE, and the invented markup had it backwards on both
    # counts. The old test built this case as the sidebar with no breadcrumb. The real page is the
    # other way round: a breadcrumb reading ニコニコ静画 then エラー, and no sidebar whatsoever.
    # Four of the 184 pages the last run fetched were this.
    gone = fixtures.load("nicovideo/error-page")
    s.check("mg_official" not in gone, "an error page renders no channel sidebar")
    s.check('class="sg_pankuzu"' in gone, "and it does render a breadcrumb")
    s.eq(nv.channel(gone), {}, "which names no channel, so no channel is recorded")
    s.check(nv.parse(gone) is None, "and there is no meta_info, so there is no date")

    dated = nv.parse('<div class="meta_info">2026年08月01日更新</div>' + kirara)
    s.eq(dated.get("channel_slug"), "kirara", "parse carries the channel onto the record")

    # A PAGE IS HTML AND ITS TEXT IS ESCAPED. ひよ&びびっと! was captured as `ひよ&amp;びびっと!`,
    # the analyser read `amp` as a word, and the romanisation shipped to readers as
    # `Hiyo & Amp ; Bibi to !`. Every other file holding this title has it right.
    _amp = nv.parse('<title>ひよ&amp;びびっと! / ゆとりいぬ おすすめ無料漫画 - ニコニコ漫画</title>'
                    '<div class="meta_info">2026年8月1日更新</div>')
    s.eq(_amp.get("title"), "ひよ&びびっと!", "an entity in the title is read as the character")
    s.eq(_amp.get("author"), "ゆとりいぬ", "and the author survives the split")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "nicovideo.releases"))
