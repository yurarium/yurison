#!/usr/bin/env python3
"""series_feeds.py: reading a per-series Atom feed, and the id it is fetched by.

COVERS = ['adapters/gigaviewer/series_feeds.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import series_feeds as sf

FEED = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>一迅プラス（大室家）</title>
  <entry>
    <title>第136話</title>
    <link href="https://x.jp/episode/136"/>
    <updated>2026-08-02T15:00:00Z</updated>
  </entry>
  <entry>
    <title>第135話</title>
    <link href="https://x.jp/episode/135"/>
    <updated>2026-07-26T03:00:00Z</updated>
  </entry>
</feed>"""


def main(s):
    # The feed states its own series name, which is why a misattributed id can be caught. The id is
    # read positionally off a thumbnail URL, and that pairing has been wrong: 夕子先輩は育てられない
    # took on its neighbour's six chapters.
    # The real shape is 一迅プラス（大室家）: platform outside, series inside the brackets. Only the
    # inner part identifies the work, and a title without brackets identifies nothing, so it
    # returns None instead of handing back the platform name as though it were a series.
    s.eq(sf.feed_series_name(FEED), "大室家", "the series name is taken from inside the brackets")
    s.check(sf.feed_series_name("<title>一迅プラス</title>") is None,
            "a title with no bracketed series yields None, not the platform name")
    s.check(sf.feed_series_name("<feed></feed>") is None,
            "a feed without a title yields None rather than raising")

    # THE PLATFORM WHOSE OWN NAME CONTAINS BRACKETS. A greedy match spanned from the first opener
    # to the last closer, so 23 COMIC OGYAAA!! series were named after the platform and its
    # tagline with the real title trapped at the end. Four of them reached the published database.
    s.eq(sf.feed_series_name(
        "<title>COMIC OGYAAA!! (コミックオギャー)｜おもしろい、がうまれるところ（あの子は優しすぎる。）</title>"),
        "あの子は優しすぎる。",
        "the series is the LAST bracket group, not everything between the first and the last")

    # The counter-case that rules out the obvious fix. A non-greedy pattern solves the above and
    # breaks this instead, returning the inner group; counting depth from the end handles both.
    s.eq(sf.last_bracketed("X（あの子（仮））"), "あの子（仮）",
         "a series title containing brackets survives whole")
    s.eq(sf.last_bracketed("一迅プラス（大室家）"), "大室家", "the ordinary one-group case still works")
    s.check(sf.last_bracketed("一迅プラス") is None, "no brackets means no name")
    s.check(sf.last_bracketed("stray ) closer") is None,
            "a closer with no opener claims nothing rather than guessing")

    eps = sf.episodes(FEED)
    s.eq(len(eps), 2, "both entries are read")
    if len(eps) == 2:
        s.eq(eps[0]["title"], "第136話", "titles come from the entry")
        s.check(all(e.get("url") for e in eps), "every entry carries its own URL")
        # Dates are platform-attested here, not heuristic, so they must survive exactly.
        s.eq(eps[0]["updated"], "2026-08-03",
             "15:00 UTC is the next day in Tokyo, and the feed is dated in JST")
        s.eq(eps[1]["updated"], "2026-07-26", "03:00 UTC is the same day in Tokyo")

    s.eq(sf.episodes("<feed></feed>"), [], "an empty feed yields no episodes")

    # JST conversion is the same fact as in releases.py, and both must agree.
    s.eq(sf.jst_date("2026-08-03T15:00:00Z"), "2026-08-04", "the boundary is 15:00 UTC")
    s.eq(sf.jst_date("2026-08-03T14:59:59Z"), "2026-08-03", "one second earlier is the day before")

    # Normalisation is used to compare the listing's name against the feed's.
    s.eq(sf.norm("ＹＵＲＩ"), sf.norm("yuri"), "width and case fold for the comparison")

    # The series id is extracted from a percent-encoded thumbnail URL, which is fragile by nature.
    html = ('<img src="https://cdn.x.jp/series-sub-thumbnail-vertical-with-logo%2F'
            'abc123-deadbeef.png"><span>大室家</span>')
    ids = sf.series_ids(html)
    s.check(isinstance(ids, (dict, set, list)), "series_ids returns a collection")
    s.check(len(sf.series_ids("<html>nothing</html>")) == 0,
            "a page with no thumbnails yields no ids rather than raising")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "series_feeds"))
