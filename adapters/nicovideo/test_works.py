#!/usr/bin/env python3
"""nicovideo/works.py: a ニコニコ page as a work record rather than as an update.

COVERS = ['adapters/nicovideo/works.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import fixtures                                                                # noqa: E402
import testkit                                                                 # noqa: E402
import works as W                                                              # noqa: E402
import releases as nvr                                                          # noqa: E402

# 運命のヤマダダダダダダダダダダ, the worked example of the pass this was written for: 芳文社's
# printed book, found on a platform 芳文社 does not run.
PAGE = """
<title>運命のヤマダダダダダダダダダダ / おにぎりパクパク おすすめ無料漫画 - ニコニコ漫画</title>
<div class="meta_info">2026年07月16日更新 2025年06月19日開始 [ 5話 無料 ]</div>
<div id="episode_list"><ul>
<li class="episode_item"><div class="episode" data-number="1">
  <div class="title"><a href="/watch/mg926551">第1話</a></div></div></li>
<li class="episode_item"><div class="episode" data-number="17">
  <div class="title"><a href="/watch/mg1100331">第16話</a></div></div></li>
</ul></div>
<small class="copyright">(C)おにぎりパクパク/芳文社</small>
"""


def main(s):
    r = W.record("72312", PAGE)
    s.eq(r["work_title"], "運命のヤマダダダダダダダダダダ", "the work is named")
    s.eq(r["author"], "おにぎりパクパク", "and credited")
    s.eq(r["url"], "https://manga.nicovideo.jp/comic/72312", "and addressed by its work id")
    s.eq(r["started"], "2025-06-19", "the serialisation start date is kept")
    s.eq(r["updated"], "2026-07-16", "and the last update")
    s.eq(r["rights"], ["おにぎりパクパク", "芳文社"],
         "the copyright line is kept, because it names the publisher")
    s.eq([c["title"] for c in r["chapters"]], ["第1話", "第16話"],
         "every rendered episode becomes a chapter")
    s.eq(r["chapters"][0]["access_modes"], ["free"],
         "the rendered episodes are the free ones, which the page states")

    # AN EPISODE THE WEB CANNOT OPEN IS NOT A FREE ONE. An episode tile may carry
    # `アプリで読める`: readable in the phone app and nowhere a browser goes. Calling those free put
    # a chapter in the free view a reader cannot reach, on 3,547 of the platform's 6,736 chapters.
    #
    # READ PER EPISODE AND NOT OFF THE HEADER. 満腹百合 is the counter-case in one page: the header
    # states the badge and three of its seven episodes still open in a browser, so a rule reading
    # the work-level line would be wrong about all three. The fixture keeps both answers.
    eps = nvr.episodes(fixtures.load("nicovideo/work-part-app-only"))
    s.eq(len(eps), 7, "every episode is read")
    s.eq([bool(e["app_only"]) for e in eps], [False] * 3 + [True] * 4,
         "the opening episodes read free in a browser and the rest are app-only")

    s.check(not any(e["app_only"] for e in nvr.episodes(fixtures.load("nicovideo/work-in-a-channel"))),
            "a page with no selling label marks nothing app-only")
    s.check(all("updated" not in c for c in r["chapters"]),
            "and none of them carries a date, because the platform states none")

    # NO PER-CHAPTER ADDRESS. THE BUG THIS PINS: build.py gives a row the address of its newest
    # chapter, and identity.py anchors the work on the row's address, so a chapter address would
    # mint a new identifier every time the work published. 180 rows arrived with a /watch/ address
    # and none of them could be attached to the printed work it belonged to.
    s.check(all("url" not in c for c in r["chapters"]),
            "a chapter carries no address, so the row keeps the work page's")

    # PARTIAL IS ASKED OF THE PAGE. Two items rendered whose positions reach 17 is the page saying
    # it left some out. THE BUG THIS WOULD HAVE BEEN: naming the whole platform partial reports a
    # complete 37-chapter run as a fraction of something longer.
    s.check(r["partial"], "five items numbered up to 17 is a partial list")
    whole = W.record("3", '<title>全話 / 作者 - ニコニコ漫画</title>'
                          '<div class="meta_info">2026年01月02日更新</div>'
                          '<div id="episode_list"><ul>'
                          '<li class="episode_item"><div class="episode" data-number="1">'
                          '<div class="title"><a href="/watch/mg1">第1話</a></div></div></li>'
                          '<li class="episode_item"><div class="episode" data-number="2">'
                          '<div class="title"><a href="/watch/mg2">第2話</a></div></div></li>'
                          '</ul></div>')
    s.check(not whole["partial"], "and a list whose positions run 1 to 2 is the whole run")

    # THE STATE THIS MUST NOT INVENT. A page that could not be read is not a serialisation with no
    # episodes, and a record saying otherwise publishes our failure as a fact about the manga
    # (STANDING-INSTRUCTIONS §4).
    s.check(W.record("1", "<html>an error page</html>") is None,
            "a page with no title yields no record rather than an empty one")
    s.check(W.record("1", "") is None, "and neither does an empty body")

    # A work with no readable episode is still a work: the platform names it and dates it. What it
    # must not do is claim a chapter.
    bare = W.record("2", '<title>作品 / 作者 - ニコニコ漫画</title>'
                         '<div class="meta_info">2026年01月02日更新</div>')
    s.eq(bare["chapters"], [], "a page rendering no episode states no chapters")
    s.eq(bare["updated"], "2026-01-02", "while still stating when the work last moved")

    # THE ADDRESS IS WHAT IDENTIFIES A TARGET, not the title beside it. A joins file names
    # several platforms and only the ニコニコ rows belong to this adapter.
    doc = {"joins": [
        {"url": "https://manga.nicovideo.jp/comic/72312", "platform_title": "運命のヤマダ"},
        {"url": "https://comic-walker.com/detail/KC_000031_S", "platform_title": "別作品"},
        {"url": "https://manga.nicovideo.jp/comic/72312", "platform_title": "同じ作品、二度目"},
    ]}
    s.eq(W.targets(doc), {"72312": "運命のヤマダ"},
         "only ニコニコ addresses are targets, and one address is one target")
    s.eq(W.targets({}), {}, "an empty joins file names nothing")
    s.eq(W.targets({"joins": [{"url": "https://manga.nicovideo.jp/watch/mg1"}]}), {},
         "an episode address is not a work address")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "nicovideo.works"))
