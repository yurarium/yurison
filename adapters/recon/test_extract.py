#!/usr/bin/env python3
"""recon/extract.py: pulling dated chapter entries out of whatever a page happens to embed."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import extract


def main(s):
    # A date this project will store must be a real calendar date in a plausible range. Publication
    # dates outside it are parser noise, and a wrong date is worse than no date because it silently
    # reorders the feed.
    s.eq(extract.norm_date("2026-08-03"), "2026-08-03", "an ISO date passes through")
    s.eq(extract.norm_date("published 2026-8-3 by x"), "2026-08-03", "a date is found and padded")
    s.check(extract.norm_date("1200-01-01") is None, "a year before 1990 is refused")
    s.check(extract.norm_date("2026-13-01") is None, "month 13 is refused")
    s.check(extract.norm_date("2026-01-45") is None, "day 45 is refused")
    s.check(extract.norm_date("no date here") is None, "text without a date yields none")
    s.check(extract.norm_date(None) is None, "None yields none rather than raising")

    # JSON-LD is the best case: the publisher states the structure.
    page = ('<html><script type="application/ld+json">'
            + json.dumps({"@type": "Book", "datePublished": "2026-07-01", "name": "第1話"})
            + '</script></html>')
    got = extract.try_jsonld(page)
    s.check(got is not None, "json-ld is found when present")
    s.check(extract.try_jsonld("<html>no script</html>") in (None, [], {}),
            "a page without json-ld yields nothing rather than raising")

    # entries_from_obj walks arbitrary nesting, because platforms bury the list at varying depth.
    obj = {"props": {"pageProps": {"episodes": [
        {"title": "第1話", "date": "2026-01-01"}, {"title": "第2話", "date": "2026-01-08"}]}}}
    ents = extract.entries_from_obj(obj)
    s.check(isinstance(ents, list), "walking a nested object returns a list")

    # A block flattened for the markup strategy loses the nodes that are only a counter, because a
    # like count printed beside a chapter was arriving as part of its name. The boundary between
    # nodes is what makes this safe: the count is a node, a title's own trailing number is not.
    s.eq(extract.block_text('<p class="t">3話①</p><span>26</span><span>8</span>'), "3話①",
         "a node that is only a number is left out of the flattened block")
    s.eq(extract.block_text('<p class="t">EPISODE 30</p><span>12</span>'), "EPISODE 30",
         "a number inside a longer node stays, because it is part of the name")
    s.eq(extract.block_text("<b>1,203</b><i>第4話</i>"), "第4話",
         "a count written with a thousands separator is a counter too")

    # try_markup marks a title it read off the page's own title element, so callers know not to
    # trim it. マンガPark names that element; ダ・ヴィンチニュース does not.
    s.eq(extract.named_title('<div class="episode-name">Chapter.3 第1話-3</div>'),
         "Chapter.3 第1話-3", "the page's named title element is read whole")
    s.check(extract.named_title('<span class="badge-number">第1回</span>'
                                '<h2 class="ttl"><a href="/x">タイトル</a></h2>') is None,
            "ダ・ヴィンチニュース names neither its badge nor its heading, so nothing is read exactly")
    s.check(extract.named_title('<p class="lead">連載中</p>') is None,
            "an element with no chapter label in it is not a title")

    rows, sel = extract.try_markup(
        '<ul><li><p class="chapterTitle">第1話</p><span>26</span>'
        '<div class="date">2026/01/05</div></li>'
        '<li><p class="chapterTitle">第2話</p><span>8</span>'
        '<div class="date">2026/01/12</div></li></ul>')
    s.check(all(r.get("exact") for r in rows),
            "rows read off a named title element are marked exact")
    s.check(all(r["title"] in ("第1話", "第2話") for r in rows),
            "and carry the name the page wrote, with no counter attached")
    s.check(sel and sel.get("tag"), "the container it keyed on is still reported")

    # Commented-out markup is not content. コミックノヴァ leaves a promo box for another work inside
    # a comment, and it was being stored as the chapter '更新！ 第8話 -->'.
    commented = ('<!-- <div class="episode-name">第8話</div><time>2020/12/25</time> -->'
                 '<ul><li><div class="episode-name">第1話</div><time>2023/08/11</time></li>'
                 '<li><div class="episode-name">第2話</div><time>2023/08/25</time></li></ul>')
    got, _ = extract.try_markup(commented)
    s.check(all("第8話" not in r["title"] for r in got),
            "a chapter that exists only inside an HTML comment is not extracted")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "recon.extract"))
