#!/usr/bin/env python3
"""render/targets.py: the rendered route's target list follows the candidates.

COVERS = ['adapters/render/targets.py']

The real case is ぎるてぃらいぶらり, listed by Web漫画アンテナ at its マガポケ title page and at an
episode link ending `?s`, and held by no capture because the target list was last written
2026-08-02.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import targets as rt                                                    # noqa: E402

TEXT = """# header the file carries
source: derived
role: render-targets
retrieved: 2026-08-02
platforms:
- id: pixivcomic
  name: pixivコミック
  host: comic.pixiv.net
  works:
  - title: ゆりひめ@ピクシブ
    url: https://comic.pixiv.net/works/1
# a note about the next section, which a rewrite would drop
- id: magapoke
  name: マガポケ
  host: pocket.shonenmagazine.com
  works:
  - title: 既にある作品
    url: https://pocket.shonenmagazine.com/title/00001
"""


def main(s):
    import yaml
    spec = yaml.safe_load(TEXT)
    guilty = {"title": "ぎるてぃらいぶらり",
              "urls": ["https://pocket.shonenmagazine.com/title/03349/episode/444683?s",
                       "https://pocket.shonenmagazine.com/title/03349"]}
    cands = [guilty,
             {"title": "既にある作品", "urls": ["https://pocket.shonenmagazine.com/title/00001"]},
             {"title": "他で取れる作品", "urls": ["https://pocket.shonenmagazine.com/title/00002"]},
             {"title": "別の場所", "urls": ["https://comic-days.com/episode/1"]}]
    adds = rt.additions(spec, cands, held={rt.norm_work("他で取れる作品")})
    s.eq(adds, {"magapoke": [("ぎるてぃらいぶらり", "https://pocket.shonenmagazine.com/title/03349")]},
         "a listed work no capture holds is added, at the work's page and not a chapter link")
    s.check("pixivcomic" not in adds, "a work on another host is not added to this platform")

    new = rt.insert(TEXT, adds)
    s.check("# a note about the next section, which a rewrite would drop" in new
            and "# header the file carries" in new, "every comment survives the edit")
    after = yaml.safe_load(new)
    s.eq([p["id"] for p in after["platforms"]], ["pixivcomic", "magapoke"],
         "the platform ids, which name the rendered files, are unchanged")
    mp = after["platforms"][1]["works"]
    s.eq([w["title"] for w in mp], ["既にある作品", "ぎるてぃらいぶらり"],
         "the new work is appended to its own platform's list, after what was there")
    s.eq(rt.additions(after, cands, held=set()) .get("magapoke", []),
         [("他で取れる作品", "https://pocket.shonenmagazine.com/title/00002")],
         "a second pass adds nothing already targeted")
    s.eq(rt.work_address(guilty["urls"], "pocket.shonenmagazine.com"),
         "https://pocket.shonenmagazine.com/title/03349", "the work's page is preferred")

    # THE RENDERED ROUTE'S OWN OUTPUT IS NOT "HELD ELSEWHERE", or a work it already renders
    # would be counted as reachable by another route and the rule would mean nothing.
    with tempfile.TemporaryDirectory() as d:
        (pathlib.Path(d) / "rendered-magapoke.yaml").write_text(
            "works:\n  - work_title: 描画のみ\n", encoding="utf-8")
        (pathlib.Path(d) / "magapoke-feeds.yaml").write_text(
            "works:\n  - work_title: フィードの作品\n", encoding="utf-8")
        held = rt.held_elsewhere(d)
        s.check(rt.norm_work("フィードの作品") in held, "a work a feed holds is held elsewhere")
        s.check(rt.norm_work("描画のみ") not in held, "a work only the rendered route holds is not")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "render.targets"))
