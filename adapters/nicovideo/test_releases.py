#!/usr/bin/env python3
"""nicovideo/releases.py: dates from meta_info, or none at all.

COVERS = ['adapters/nicovideo/releases.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
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

    # Tags inside the block must not break the date, since the markup carries links and spans.
    tagged = nv.parse('<div class="meta_info"><span>2026年8月3日更新</span></div>')
    s.eq((tagged or {}).get("updated"), "2026-08-03", "markup inside the block is stripped first")

    # ── the work page's other two facts ───────────────────────────────────────────────────────
    # Quoted from 運命のヤマダダダダダダダダダダ, which is 芳文社's book found on this platform.
    WORK = """
    <div class="meta_info">2026年07月16日更新 2025年06月19日開始 [ 5話 無料 ]</div>
    <div id="episode_list"><ul>
    <li class="episode_item"><div class="episode" data-number="1">
      <div class="title"><a href="/watch/mg926551">第1話</a></div></div></li>
    <li class="episode_item"><div class="episode" data-number="13">
      <div class="title"><a href="/watch/mg1006876">番外編</a></div></div></li>
    <li class="episode_item"><div class="episode" data-number="17">
      <div class="title"><a href="/watch/mg1100331">第16話</a></div></div></li>
    </ul></div>
    <small class="copyright">(C)おにぎりパクパク/芳文社</small>
    """
    s.eq(nv.rights(WORK), ["おにぎりパクパク", "芳文社"],
         "the copyright line names the author and the publisher")
    s.eq(nv.rights("<p>no copyright line here</p>"), [],
         "a page without the line yields nothing rather than a guess")

    eps = nv.episodes(WORK)
    s.eq([e["title"] for e in eps], ["第1話", "番外編", "第16話"],
         "every rendered episode is read, extras included")
    s.eq(eps[-1]["url"], "https://manga.nicovideo.jp/watch/mg1100331",
         "an episode link is made absolute")
    s.eq(eps[1]["number"], 13, "the platform's own position number is kept")
    s.check(all("updated" not in e for e in eps),
            "no episode carries a date, because the platform states none")

    # ONE READER OF THIS MARKUP. `parse` used to walk the episode list itself for the newest item,
    # and the discovery pass needed the whole list. Two copies of one rule is the shape that has
    # produced seven bugs here, so `parse` consumes `episodes`.
    whole = nv.parse(WORK)
    s.eq(whole["latest_episode"], "第16話", "the newest episode is the highest-numbered one")
    s.eq(whole["rendered_episodes"], 3, "and the page says how many it showed")
    s.check("番外編" != whole["latest_episode"],
            "an extra sitting between numbered chapters is not mistaken for the newest")

    # ── which channel the work is in ──────────────────────────────────────────────────────────
    #
    # QUOTED FROM THE PAGES, NOT WRITTEN HERE. Every string below is byte for byte out of
    # manga.nicovideo.jp as fetched on 2026-08-07, cut to the two blocks that matter. A pattern
    # tested against markup somebody imagined proves the pattern matches what they imagined, and
    # the bug this covers was exactly that: the old rule read a real element correctly and the
    # element was the wrong one.
    #
    # The sidebar is here because it is the counter-case. It renders a banner for every official
    # channel on the site and opens with ニコニコ漫画（公式）, so any rule that is not scoped to
    # the breadcrumb answers `nicomanga` for every work on the platform. All 180 we held did.
    SIDEBAR = (
        '<div id="mg_official" class="menu_block">\n    <h2 class="menu_legend">\n      公式マンガ\n'
        '    </h2>\n    <ul>\n'
        '      <li><a href="/official/nicomanga/"><div class="mg_banner"><img '
        'data-original="https://deliver.cdn.nicomanga.jp/thumb/4265156q" src="/manga/img/_.gif" '
        'title="ニコニコ漫画（公式）" alt="ニコニコ漫画（公式）" class="lazyload"></div></a></li>'
        '<li><a href="/official/kirara/"><div class="mg_banner"><img '
        'data-original="https://deliver.cdn.nicomanga.jp/thumb/5709925q" src="/manga/img/_.gif" '
        'title="きららベース" alt="きららベース" class="lazyload">'
        '<p class="date_balloon">08/01更新</p></div></a></li>\n    </ul>\n  </div>')
    CRUMB = ('<ul class="sg_pankuzu">\n'
             '                        <li itemscope itemtype="http://data-vocabulary.org/Breadcrumb">'
             '<a href="/manga/" itemprop="url"><span itemprop="title">マンガ</span></a></li>\n'
             '                    <li itemscope itemtype="http://data-vocabulary.org/Breadcrumb">'
             '<a href="{href}" itemprop="url"><span itemprop="title">{label}</span></a></li>\n'
             '                    <li class="active" itemscope '
             'itemtype="http://data-vocabulary.org/Breadcrumb">'
             '<span itemprop="title">{work}</span></li>\n            </ul>')

    tart = CRUMB.format(href="/official/kirara", label="[公式] きららベース",
                        work="おちこぼれフルーツタルト") + SIDEBAR
    s.eq(nv.channel(tart), {"channel": "きららベース", "channel_slug": "kirara"},
         "the channel is the one the breadcrumb names")
    s.check("nicomanga" not in str(nv.channel(tart)),
            "and not the first banner in the sidebar, which is on every page of the site")

    # 「[公式]」 is the breadcrumb's own label for a channel, not part of its name. data/platforms.yaml
    # records it as きららベース, and a value carrying the prefix would join to nothing.
    s.eq(nv.channel(tart)["channel"], "きららベース", "the 公式 label is not part of the name")

    # A slug with a hyphen in it. `[a-z0-9_]+` stopped at the hyphen and would have filed
    # ニコニコ百合姫's works under a channel called `nico`, which is not a channel at all.
    spica = CRUMB.format(href="/official/nico-yurihime", label="[公式] ニコニコ百合姫",
                         work="スピカをつかまえて") + SIDEBAR
    s.eq(nv.channel(spica), {"channel": "ニコニコ百合姫", "channel_slug": "nico-yurihime"},
         "a hyphen belongs to the slug and does not end it")

    # THE STATE THIS MUST NOT FILL IN. ニコニコ漫画 carries a section anybody may post to, and a
    # work there has no channel: the second crumb is a genre listing, and the sidebar is unchanged.
    # 19 of the 180 works we hold are in this position, so a rule that always answers is wrong 19
    # times and looks right (§5).
    solo = ('<ul class="sg_pankuzu">\n'
            '                        <li itemscope itemtype="http://data-vocabulary.org/Breadcrumb">'
            '<a href="/manga/" itemprop="url"><span itemprop="title">マンガ</span></a></li>\n'
            '                    <li itemscope itemtype="http://data-vocabulary.org/Breadcrumb">'
            '<a href="/manga/list?category=%E3%81%9D%E3%81%AE%E4%BB%96%E3%83%9E%E3%83%B3%E3%82%AC" '
            'itemprop="url"><span itemprop="title">その他マンガ</span></a></li>\n'
            '                    <li class="active" itemscope '
            'itemtype="http://data-vocabulary.org/Breadcrumb">'
            '<span itemprop="title">同居人に片思いしてる百合漫画</span></li>\n            </ul>') + SIDEBAR
    s.eq(nv.channel(solo), {},
         "a work outside the official channels is recorded as being in none")

    # An error page renders the sidebar and no breadcrumb of its own. Four of the 184 pages the
    # last run fetched were these.
    s.eq(nv.channel(SIDEBAR), {}, "a page with no breadcrumb yields no channel")

    dated = nv.parse('<div class="meta_info">2026年08月01日更新</div>' + tart)
    s.eq(dated.get("channel_slug"), "kirara", "and parse carries the channel onto the record")

    # A PAGE IS HTML AND ITS TEXT IS ESCAPED. ひよ&びびっと! was captured as `ひよ&amp;びびっと!`,
    # the analyser read `amp` as a word, and the romanisation shipped to readers as
    # `Hiyo & Amp ; Bibi to !`. Every other file holding this title has it right.
    _amp = nv.parse('<title>ひよ&amp;びびっと! / ゆとりいぬ おすすめ無料漫画 - ニコニコ漫画</title>'
                    '<div class="meta_info">2026年8月1日更新</div>')
    s.eq(_amp.get("title"), "ひよ&びびっと!", "an entity in the title is read as the character")
    s.eq(_amp.get("author"), "ゆとりいぬ", "and the author survives the split")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "nicovideo.releases"))
