#!/usr/bin/env python3
"""candidates.py: 百合ナビ's works reach the capture steps without being cited as the antenna's.

COVERS = ['adapters/candidates.py']
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import candidates as cd                                                 # noqa: E402


def main(s):
    base = [{"title": "既にある", "platforms": ["カドコミ"], "urls": ["https://comic-walker.com/detail/KC_1_S"]}]
    mai = {"title": "舞ちゃんのお姉さん飼育ごはん。", "platforms": ["竹コミ！"],
           "urls": ["https://takecomic.jp/series/68270e5ebb4a6"]}
    extra = [mai,
             {"title": "既にある", "platforms": ["カドコミ"], "urls": ["https://comic-walker.com/detail/KC_9_S"]},
             {"title": "笑顔のたえない職場です。", "platforms": ["コミックDAYS"], "urls": ["https://comic-days.com/episode/1"]}]
    merged, added = cd.merge(base, extra, already_held={cd.norm_work("笑顔のたえない職場です。")})
    s.eq(added, [mai], "a 百合ナビ work nothing names or holds is added")
    s.eq(merged[0], base[0], "the antenna's candidates come first and unchanged")
    s.eq(len(merged), 2, "a title the antenna already names is not added a second time")
    s.check(all(c["title"] != "笑顔のたえない職場です。" for c in added),
            "and a work a capture already holds is not fetched twice from another address")

    with tempfile.TemporaryDirectory() as d:
        (pathlib.Path(d) / "x.yaml").write_text("works:\n  - work_title: 何かの作品\n", encoding="utf-8")
        s.check(cd.norm_work("何かの作品") in cd.held(d), "held titles are read off the captures")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "candidates"))
