#!/usr/bin/env python3
"""episode_lists.py: a GigaViewer series' whole run, expired episodes included.

COVERS = ['adapters/gigaviewer/episode_lists.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit                                                          # noqa: E402
import episode_lists as el                                              # noqa: E402

#: The shape サンデーうぇぶり returned for 女だから、とパーティを追放されたので… on 2026-10-15, newest
#: first, cut to three entries.
PAGE = [
    {"title": "75. 第31話 (4)", "display_open_at": "2024-07-07T15:00:00Z",
     "viewer_uri": "https://www.sunday-webry.com/episode/75",
     "status": {"label": "unpublished", "type": "private"}},
    {"title": "2. 第1話 (2)", "display_open_at": "2021-04-11T15:00:00Z",
     "viewer_uri": "https://www.sunday-webry.com/episode/2", "status": {"label": "is_purchasable"}},
    {"title": "1. 第1話", "display_open_at": "2021-04-11T15:00:00Z",
     "viewer_uri": "https://www.sunday-webry.com/episode/1", "status": {"label": "is_free"}},
]


def main(s):
    ch = el.chapters(PAGE)
    s.eq([c["title"] for c in ch], ["1. 第1話", "2. 第1話 (2)", "75. 第31話 (4)"],
         "the list comes back oldest first, as the other captures order it")
    s.eq(ch[-1]["updated"], "2024-07-08",
         "dated in Japan: 15:00Z is midnight the next day there")
    s.eq((ch[0].get("access_modes"), ch[1].get("access_modes")), (["free"], ["purchase"]),
         "free and priced as the platform states them")
    s.check(ch[-1].get("withdrawn") and not ch[-1].get("access_modes"),
            "and an expired episode is withdrawn, with no access mode to be counted as readable")
    s.eq(el.access({}), ([], False), "an entry stating no status claims nothing")

    feeds = {"sundaywebry": {"works": [{"work_title": "A", "series_id": "1"}]}}
    reg = [{"id": "w1", "title": "B", "anchors": ["web:https://www.sunday-webry.com/atom/series/2"]},
           {"id": "w2", "title": "C", "merged_into": "w1",
            "anchors": ["web:https://www.sunday-webry.com/atom/series/3"]},
           {"id": "w3", "title": "D", "anchors": ["web:https://elsewhere.jp/atom/series/4"]}]
    got = el.targets(feeds, reg, {"sundaywebry": "www.sunday-webry.com"})
    s.eq(got, {("sundaywebry", "1"): "A", ("sundaywebry", "2"): "B"},
         "series from the feeds held and the registry's anchors, not a retired entry or another host")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "gigaviewer.episode_lists"))
