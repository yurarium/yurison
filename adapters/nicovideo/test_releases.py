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


if __name__ == "__main__":
    sys.exit(testkit.run(main, "nicovideo.releases"))
