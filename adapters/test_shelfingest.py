#!/usr/bin/env python3
"""shelfingest.py: a designation excludes, and nothing else does."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import shelfingest as si  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/shelfingest.py"]


def main(s):
    # DOUJINSHI IS A PUBLICATION MODE. Treating it as a content class would drop admissible works
    # to spare us a judgement, and the designation already excludes most yuri doujinshi anyway.
    d = {"title": "彼女と彼女の話。", "publisher": "ナンバーナイン", "doujin": True,
         "genre": "青年マンガ"}
    s.check(si.designated(d) is None, "a doujin row carrying no designation is not excluded by it")
    s.eq(si.normalise(d, "cmoa.jp")["doujin"], True, "and the fact is recorded rather than acted on")

    # WHAT DOES EXCLUDE: something somebody else designated.
    s.check(si.designated({"title": "x", "genre": "アダルトマンガ"}),
            "the shop's own adult genre is a designation")
    s.check(si.designated({"title": "x", "imprint": "Ghost Ship"}),
            "and so is an adult imprint the publisher runs as one")
    s.check(si.designated({"title": "何か【R-18版】"}), "and an R-18 marking on the volume")
    s.check(si.designated({"title": "ふつうの百合", "genre": "女性マンガ"}) is None,
            "an ordinary row on an ordinary shelf is not designated anything")

    # EXPLICIT IS A FLAG, NEVER AN EXCLUSION. §7's middle band: 一迅社 publishes えっち anthologies
    # openly and they are not pornography by the test above.
    e = {"title": "百合えっち短編集", "genre": "女性マンガ", "publisher": "一迅社"}
    s.check(si.designated(e) is None, "an explicit title carries no designation on its own")
    s.eq(si.normalise(e, "cmoa.jp")["explicit_content"], True, "and is admitted with the flag set")

    # AGE-GATING IS RECORDED, NOT JUDGED. Both captured shelves are the shop's all-ages listing.
    s.eq(si.normalise(e, "cmoa.jp")["age_gated"], {"shop": "cmoa.jp", "state": "open"},
         "the shop stocked it openly and the record says which shop said so")

    recs, why = si.ingest([d, e, {"title": "x", "genre": "アダルトマンガ"}], "cmoa.jp")
    s.eq(len(recs), 2, "two admitted, one designated")
    s.eq(sum(why.values()), 1, "and the exclusion is counted")
    # A TITLE WE EXCLUDE AS PORNOGRAPHY IS NOT WRITTEN INTO A FILE IN THIS REPOSITORY.
    s.check(all("x" not in k for k in why), "the reason is recorded and the title is not")

    # Role prefixes are cataloguing notation, not part of a name.
    s.eq(si.normalise({"title": "t", "author": "著: 蒼井紫", "genre": "マンガ"},
                      "bookwalker.jp")["authors"], ["蒼井紫"],
         "a credit role is stripped before the name is stored")
    s.eq(si.normalise({"title": "", "genre": "マンガ"}, "cmoa.jp"), None, "no title, no record")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
