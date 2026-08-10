#!/usr/bin/env python3
"""facts/marketing: what counts as a platform calling a work yuri.

COVERS = ['adapters/facts/marketing/__init__.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "names"))
import testkit                                                          # noqa: E402
from facts import marketing as m                                        # noqa: E402


def main(s):
    for t in ("百合", "GL", "ガールズラブ"):
        s.check(m.is_yuri_label(t), f"{t} is a platform calling the work yuri")
    s.check(m.is_yuri_label(" 百合 "), "and surrounding space is not part of the label")

    # DELIBERATELY NARROW, and this is the half that matters. A magazine name is not a genre tag,
    # and admitting on one is a different argument from admitting on the other.
    for t in ("百合姫", "ガール", "GIRLS", "コミック百合姫", "BL", ""):
        s.check(not m.is_yuri_label(t), f"{t!r} is not a yuri genre label")
    s.check(not m.is_yuri_label(None), "and neither is nothing")

    s.eq(m.labels_in(["恋愛", "百合", "学園"]), ["百合"], "labels_in keeps only the labels")
    s.eq(m.labels_in([]), [], "and an empty list finds none")
    s.eq(m.labels_in(None), [], "as does nothing at all")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
