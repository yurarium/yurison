#!/usr/bin/env python3
"""gigaviewer/id_conventions.py: a platform's serial ids are numbered before a bare id is trusted.

COVERS = ['adapters/gigaviewer/id_conventions.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import id_conventions as ic                                             # noqa: E402
import testkit                                                          # noqa: E402


def main(s):
    for cid in ("firstpenguin_requiem_005", "16273_0001", "ojousama-matching_001-1",
                "y_R0116_s0001-0", "KOMODO_001"):
        s.check(ic.numbered(cid), f"{cid} carries an episode number")
    for cid in ("saechan_tonari", "harumegu_yomikiri", "ec1047363x"):
        s.check(not ic.numbered(cid), f"{cid} does not")
    run = [{"ongoing": True, "content_id": f"work{i}_00{i}"} for i in range(1, 10)]
    s.eq(ic.measure(run + [{"content_id": "oneshot"}]), {"running": 9, "numbered": 9},
         "only an episode whose series is running is counted, since only that is surely a serial")
    s.check(not ic.keeps(ic.measure(run)), "nine is too few to say")
    ten = run + [{"ongoing": True, "content_id": "work10_010"}]
    s.check(ic.keeps(ic.measure(ten)), "ten serials, every one numbered, keeps the convention")
    s.check(not ic.keeps(ic.measure(ten + [{"ongoing": True, "content_id": "bare_slug"}])),
            "and one bare serial id breaks it")
    extra = {"ongoing": True, "content_id": "ponkotu_bangai_halloween",
             "episode_title": "ハロウィン特別番外編"}
    s.check(ic.keeps(ic.measure(ten + [extra])),
            "but a serial's side story, which takes a bare id and is never a work of its own, does not")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "gigaviewer.id_conventions"))
