#!/usr/bin/env python3
"""magapoke.py: how long the platform says its own series is, and what it calls each episode."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import magapoke  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/magapoke.py"]

# Quoted from the served 将来的に死んでくれ page, shortened to five episodes. The array after the
# key holds positions into the page's value table and the ids follow it, which is the whole reason
# this needs a parser rather than a JSON load.
PAGE = ('"thumbnail_rect_image_url":243,"episode_id_list":244,"total_episode_count":153}'
        ',195,"将来的に死んでくれ","長門知大",'
        '[245,246,247,248,249],152378,154585,156461,158606,160031,'
        '{"status":5,"response_code":6}')

# Quoted from https://mgpk-cdn.magazinepocket.com/static/rss/195/feed.xml, three of its 42 items,
# byte for byte apart from the cut. The channel block is kept whole because it is half the point:
# it carries a <title>, a <pubDate> and a <link> of exactly the shape an item carries.
FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>マガポケ（将来的に死んでくれ）</title>
    <pubDate>Wed, 09 Oct 2019 00:00:00 +0900</pubDate>
    <link>https://pocket.shonenmagazine.com/title/00195/episode/152378</link>
    <description>女子高生・菱川 俊が恋しているのは、同じく女子高生の刑部小槙！</description>
    <item>
      <title>【第42話】将来的に死んでくれ</title>
      <link>https://pocket.shonenmagazine.com/title/00195/episode/296085</link>
      <guid isPermalink="false">296085</guid>
      <pubDate>Wed, 09 Oct 2019 00:00:00 +0900</pubDate>
      <description>将来的に死んでくれ</description>
      <enclosure url="https://mgpk-cdn.magazinepocket.com/static/titles/195/episodes/296085/thumb.png" type="image/png" length="0"/>
      <author>長門知大</author>
    </item>
    <item>
      <title>【第41話】あなたは法楽</title>
      <link>https://pocket.shonenmagazine.com/title/00195/episode/289666</link>
      <guid isPermalink="false">289666</guid>
      <pubDate>Mon, 09 Sep 2019 00:00:00 +0900</pubDate>
      <description>将来的に死んでくれ</description>
      <author>長門知大</author>
    </item>
    <item>
      <title>【第1話】「あなたのためなら、いくらでも」</title>
      <link>https://pocket.shonenmagazine.com/title/00195/episode/152378</link>
      <guid isPermalink="false">152378</guid>
      <pubDate>Fri, 30 Dec 2016 00:00:00 +0900</pubDate>
      <description>将来的に死んでくれ</description>
      <author>長門知大</author>
    </item>
  </channel>
</rss>
"""


def main(s):
    s.eq(magapoke.episode_ids(PAGE), [152378, 154585, 156461, 158606, 160031],
         "the ids are read from the run that follows, not from the positions")
    s.eq(magapoke.total_episodes(PAGE), 5, "which is how long the platform says the series is")

    # THE FAULT THIS GUARDS. The positions are a numeric array of exactly the right length sitting
    # exactly where a list of ids would be, so taking it gives a believable and wholly wrong answer.
    s.check(245 not in magapoke.episode_ids(PAGE),
            "a position is never returned as an id, however plausible the length looks")

    s.eq(magapoke.episode_ids("<html>nothing to say</html>"), [],
         "a page that lists no episodes lists none")
    s.eq(magapoke.total_episodes("<html>nothing to say</html>"), None,
         "and states no total rather than a total of zero")
    s.eq(magapoke.episode_ids(""), [], "and neither does an empty page")

    s.eq(magapoke.episode_ids('"episode_id_list":244,[245,246],"a string, not a run"'), [],
         "positions with no run behind them are not answered from the positions")
    s.eq(magapoke.episode_ids('[245,246,247],152378,154585,156461'), [],
         "and a page that never names the list is not read for one")

    # A run of a different length is a shape we do not understand, so it yields nothing rather than
    # a guess. This is what a page redesign would look like.
    s.eq(magapoke.episode_ids('"episode_id_list":244,[245,246,247],152378,154585'), [],
         "positions and ids disagreeing on how many there are decides nothing")

    # ── the series feed ────────────────────────────────────────────────────────────────────────
    eps = magapoke.feed_episodes(FEED)
    s.eq(len(eps), 3, "one row per item, and the feed's own order kept")
    s.eq(eps[0]["title"], "【第42話】将来的に死んでくれ", "the episode title is the item's title")
    s.eq(eps[0]["updated"], "2019-10-09", "and its date is the item's pubDate, as a JST date")
    s.eq(eps[0]["url"], "https://pocket.shonenmagazine.com/title/00195/episode/296085",
         "the link is the episode's own page")
    s.eq(eps[0]["episode_id"], "296085", "and the guid is the episode id")
    s.eq(eps[0]["author"], "長門知大", "the author is stated per item and was there to be read")
    s.eq(eps[-1]["updated"], "2016-12-30",
         "the run reaches back past the ten-episode free window to episode 1")

    # THE FAULT THIS GUARDS. <channel> opens with a <title>, a <pubDate> and a <link>, and they are
    # indistinguishable from an item's. Matched across the whole document they become a 43rd
    # episode named マガポケ（将来的に死んでくれ）, dated the same day as the newest chapter, linking
    # to episode 1. It would have a title, a date and a URL, so no field check could see it.
    s.check(all("マガポケ" not in e["title"] for e in eps),
            "the channel's own title is never returned as an episode")
    s.eq([e["title"] for e in eps].count("【第42話】将来的に死んでくれ"), 1,
         "and the channel's pubDate does not duplicate the newest episode")

    s.eq(magapoke.feed_series_name(FEED), "将来的に死んでくれ",
         "the feed states which series it is, so a mispaired id can be caught")
    s.eq(magapoke.feed_series_name(
        "<channel><title>マガポケ（念願の悪役令嬢(ラスボス)の身体を手に入れたぞ！）</title>"),
        "念願の悪役令嬢(ラスボス)の身体を手に入れたぞ！",
        "including a title carrying brackets of its own inside the wrapper's")
    s.eq(magapoke.feed_series_name("<rss><channel></channel></rss>"), None,
         "a feed that names no series names none")

    # A date that cannot be read yields nothing rather than a guess, and the row goes with it.
    s.eq(magapoke.feed_date("Wed, 09 Oct 2019 00:00:00 +0900"), "2019-10-09",
         "an RFC 822 stamp already in JST keeps its date")
    s.eq(magapoke.feed_date("Wed, 09 Oct 2019 15:00:00 +0000"), "2019-10-10",
         "and one in UTC is converted, because 15:00Z is the next day in Tokyo")
    s.eq(magapoke.feed_date("last Thursday"), "", "an unreadable stamp states no date")
    s.eq(magapoke.feed_episodes(
        "<item><title>【第1話】</title><pubDate>whenever</pubDate></item>"), [],
        "so an item with no readable date is dropped rather than dated today")
    s.eq(magapoke.feed_episodes("<html>not a feed</html>"), [],
         "and a page that is not a feed yields no episodes")

    # The id is padded to five digits in a work URL and not padded at all in the feed path.
    s.eq(magapoke.feed_url("https://pocket.shonenmagazine.com/title/00195"),
         "https://mgpk-cdn.magazinepocket.com/static/rss/195/feed.xml",
         "the feed path drops the padding the work URL carries")
    s.eq(magapoke.feed_url("195"), "https://mgpk-cdn.magazinepocket.com/static/rss/195/feed.xml",
         "and a bare id reaches the same place")
    s.eq(magapoke.feed_url(""), "", "nothing names no feed")

    # THE COUNTER-CASE, and the reason this compares normalised. Seven of the 37 series differed
    # from the platform's spelling by punctuation width alone. Reported as misattributions they
    # would bury the one that matters, which is a work record pointing at another series' id.
    s.eq(magapoke.reconcile_name("私の百合はお仕事です!", "私の百合はお仕事です！"),
         ("私の百合はお仕事です!", False),
         "full-width against half-width is the same series, and our spelling is kept")
    s.eq(magapoke.reconcile_name("念願の悪役令嬢(ラスボス)の身体を手に入れたぞ!",
                                 "念願の悪役令嬢（ラスボス）の身体を手に入れたぞ！"),
         ("念願の悪役令嬢(ラスボス)の身体を手に入れたぞ!", False),
         "and so is bracket width")
    s.eq(magapoke.reconcile_name("夕子先輩は育てられない", "亜澄ちゃんと胡蝶ちゃん"),
         ("亜澄ちゃんと胡蝶ちゃん", True),
         "a different series is a misattribution, and the feed's own name wins")
    s.eq(magapoke.reconcile_name("将来的に死んでくれ", None), ("将来的に死んでくれ", False),
         "a feed that names no series overturns nothing")

    # A PARTIAL RUN MUST NOT DELETE WHAT IT DID NOT FETCH. The target list is derived from other
    # source files, which their own adapters rewrite every run, so a work can vanish from the
    # targets for a day without anything having happened to it. Replacing the whole file with
    # whatever came back would take its history with it: the same fault cost 49 works in
    # adapters/webpages/releases.py and 96 series in adapters/gigaviewer/series_feeds.py.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "magapoke-feeds.yaml"
        f.write_text(
            'works:\n'
            '  - work_title: "kept"\n'
            '    url: "https://pocket.shonenmagazine.com/title/00195"\n    chapters: []\n'
            '  - work_title: "refetched"\n'
            '    url: "https://pocket.shonenmagazine.com/title/03125"\n    chapters: []\n')
        got = magapoke.carry_over(f, ["3125"])
        s.eq([w["work_title"] for w in got], ["kept"],
             "a series this run did not fetch is kept, because not asking is not a finding")
        s.eq(got[0]["episodes"], [],
             "and comes back in the shape the writer takes, which names the list episodes")
        s.eq(magapoke.carry_over(f, ["195", "3125"]), [],
             "and a series it did fetch is left to the fresh feed")
        # Keyed on the id inside the URL, not on the URL. The padding differs between the work
        # page and the feed path, so comparing strings would carry every series over twice.
        s.eq(magapoke.carry_over(f, ["00195", "3125"]), [],
             "the padded and unpadded forms of an id are the same series")
        s.eq(magapoke.carry_over(pathlib.Path(d) / "absent.yaml", []), [],
             "a file that does not exist yet carries nothing over")

    ids = magapoke.title_ids([
        {"work_title": "将来的に死んでくれ", "url": "https://pocket.shonenmagazine.com/title/00195"},
        {"work_title": "どこかよそ", "url": "https://comic-days.com/title/1234"},
        {"work_title": "怨霊日和", "url": "https://pocket.shonenmagazine.com/title/03125/episode/1"},
    ])
    s.eq(ids, {"195": "将来的に死んでくれ", "3125": "怨霊日和"},
         "targets come from the URLs we already hold, and only from this platform's")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
