#!/usr/bin/env python3
"""titling.py: a platform's own way of titling a one-shot, measured before it is trusted.

COVERS = ['adapters/titling.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import titling as tt                                                    # noqa: E402


def one(t, c=None):
    return {"work_title": t, "chapters": [{"title": c if c is not None else t}]}


def serial(t, n=3):
    return {"work_title": t, "chapters": [{"title": f"第{i}話"} for i in range(1, n + 1)]}


def main(s):
    keeps = [one(f"作品{i}") for i in range(9)] + [one("連載物", "1. 1回表")] + \
        [serial(f"連載{i}") for i in range(5)]
    m = tt.measure(keeps)
    s.eq((m["named"], m["singles"], m["serials"], m["serials_named"]), (9, 10, 5, 0),
         "self-named single instalments and serials are counted apart")
    s.check(tt.keeps(m), "a platform naming nine of ten one-shots after the work and no serial keeps it")
    breaks = keeps + [{"work_title": "連載X", "chapters": [{"title": "連載X"}, {"title": "第2話"}]}]
    s.check(not tt.keeps(tt.measure(breaks)),
            "one serial titling a chapter after its work is enough to break it")
    s.check(not tt.keeps(tt.measure([one(f"作品{i}") for i in range(9)])),
            "and a platform with too few serials to say has no convention")
    s.check(tt.self_named("ニカはおいしい血が吸いたい!", "ニカはおいしい血が吸いたい！"),
            "a width difference does not make two titles different")
    got = tt.conventions([{"platform_name": "うぇぶり", "works": keeps},
                          {"platform_name": "ジャンプ", "works": breaks}])
    s.eq(list(got), ["うぇぶり"], "only the platform keeping it is returned, with its counts")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "titling"))
