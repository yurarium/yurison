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
             {"title": "既にある", "platforms": ["カドコミ"], "urls": ["https://comic-walker.com/detail/KC_1_S/"]},
             {"title": "笑顔のたえない職場です。", "platforms": ["コミックDAYS"], "urls": ["https://comic-days.com/episode/1"]}]
    merged, added = cd.merge(base, extra, already_held={
        cd.norm_work("笑顔のたえない職場です。"): {"https://comic-days.com/episode/2"}})
    s.eq(added, [mai], "a 百合ナビ work nothing names or holds is added")
    s.eq(merged[0], base[0], "the antenna's candidates come first and unchanged")
    s.eq(len(merged), 2, "a title the antenna already names is not added a second time")
    s.check(all(c["title"] != "笑顔のたえない職場です。" for c in added),
            "and a work a capture already holds is not fetched twice from another address")

    # AN ADDRESS A PERSON FOUND JOINS THE WORK, where 百合ナビ's would be left out for being named.
    inaba = [{"title": "魔法少女イナバ", "platforms": ["カドコミ"],
              "urls": ["https://comic-walker.com/detail/KC_007952_S"]}]
    growl = {"title": "魔法少女イナバ", "platform": "コミックグロウル",
             "url": "https://comic-growl.com/series/aa1ae7d41e228"}
    out, n = cd.found(inaba, [growl])
    s.eq((out[0]["urls"], out[0]["platforms"], n),
         (["https://comic-walker.com/detail/KC_007952_S", "https://comic-growl.com/series/aa1ae7d41e228"],
          ["カドコミ", "コミックグロウル"], 1),
         "a found address is added to the candidate the work already has")
    s.eq(inaba[0]["urls"], ["https://comic-walker.com/detail/KC_007952_S"], "without editing the list it was given")
    s.eq(cd.found(out, [growl])[1], 0, "and the same address twice is one target")
    out, n = cd.found([], [dict(growl, title="どこにもない")])
    s.eq((len(out), out[0]["platforms"], n), (1, ["コミックグロウル"], 1),
         "a work no list names gets a candidate of its own")

    # AND AN ADDRESS FOUND GONE LEAVES THE TARGETS, without the antenna's file being edited.
    akane = [{"title": "おしごとですよ! 赤根さん", "platforms": ["コミックグロウル"],
              "urls": ["https://comic-growl.com/episode/13933686331793881861"]},
             {"title": "両方", "urls": ["https://a.example/1", "https://b.example/2/"]}]
    out, n = cd.without(akane, [{"url": "https://comic-growl.com/episode/13933686331793881861"},
                                {"url": "https://b.example/2"}])
    s.eq(([c["title"] for c in out], out[0]["urls"], n), (["両方"], ["https://a.example/1"], 2),
         "a gone address is taken out, and a work left with none is left out")

    # THE COUNTER-CASE THE FIRST VERSION GOT WRONG. A capture holding the work at the address this
    # list gave it is the list's own catch; dropping the work for it starves that capture next run.
    nico = {"title": "アイドルビーバック！", "platforms": ["ニコニコ漫画"],
            "urls": ["https://manga.nicovideo.jp/comic/64462"]}
    k = cd.norm_work(nico["title"])
    _, added = cd.merge([], [nico], {k: {"https://manga.nicovideo.jp/comic/64462"}})
    s.eq(added, [nico], "a work held only at its own address stays on the list")
    _, added = cd.merge([], [nico], {k: {"https://manga.nicovideo.jp/comic/64462/"}})
    s.eq(added, [nico], "and a trailing slash does not make its own address another one")
    _, added = cd.merge([], [nico], {k: {"https://manga.nicovideo.jp/comic/64462",
                                          "https://comic-walker.com/detail/KC_2_S"}})
    s.eq(added, [], "a work also held at another address is reached already")
    _, added = cd.merge([], [nico], {k: {""}})
    s.eq(added, [], "and a capture that records no address counts as elsewhere")
    onryo = {"title": "怨霊日和", "platforms": ["マガポケ"],
             "urls": ["https://pocket.shonenmagazine.com/title/03338/episode/443763"]}
    _, added = cd.merge([], [onryo], {cd.norm_work("怨霊日和"): {"https://pocket.shonenmagazine.com/title/03125"}})
    s.eq(added, [onryo], "a title held at another address on the same site is a second page there")
    _, added = cd.merge([{"title": "怨霊日和", "urls": ["https://pocket.shonenmagazine.com/title/03125"]}],
                        [onryo], {})
    s.eq(added, [onryo], "and so is one the antenna names at another work page on that site")
    kc = {"title": "既にある", "urls": ["https://comic-walker.com/detail/KC_9_S"]}
    s.eq(cd.merge(base, [kc], {})[1], [kc], "two カドコミ detail ids are two works' pages")
    ep = {"title": "笑顔のたえない職場です。", "urls": ["https://comic-days.com/episode/1"]}
    s.eq(cd.merge([], [ep], {cd.norm_work(ep["title"]): {"https://comic-days.com/atom/series/9"}})[1], [],
         "but an episode address says nothing about which work it is, so it is reached")

    with tempfile.TemporaryDirectory() as d:
        (pathlib.Path(d) / "x.yaml").write_text("works:\n  - work_title: 何かの作品\n", encoding="utf-8")
        (pathlib.Path(d) / "y.yaml").write_text(
            "works:\n  - work_title: 別の作品\n    url: https://example.jp/s/1?x=1\n", encoding="utf-8")
        s.check(cd.norm_work("何かの作品") in cd.held(d), "held titles are read off the captures")
        s.eq(cd.held_at(d)[cd.norm_work("別の作品")], {"https://example.jp/s/1"},
             "and so is where each is held, in the form a candidate's address is compared in")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "candidates"))
