#!/usr/bin/env python3
"""shopfinal.py: the shop says the series ended and says how long it is, or it says nothing."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import shopfinal as sf  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/shopfinal.py"]


def work(**kw):
    base = {"shop_id": "1", "completed": True, "volumes_stated": 3, "volumes_found": 3,
            "volumes": [{"volume": 1, "isbn": "9784000000011"},
                        {"volume": 2, "isbn": "9784000000028"},
                        {"volume": 3, "isbn": "978-4-00-000003-5"}]}
    base.update(kw)
    return base


def main(s):
    # THE ORDINARY CASE. Complete, three stated, three read, so the third one ended it.
    got = sf.final_volume(work())
    s.eq(got["volume"], 3, "the last volume of a series the shop says is finished")
    s.eq(sf.claims({"works": [work()]})[0]["isbn"], "9784000000035",
         "keyed by ISBN as digits, because that is what identifies an edition")

    # A CAPTURE THAT STOPPED EARLY MUST NOT NAME A FINAL VOLUME. This is the whole reason the
    # count is consulted: the last volume we happen to hold is not the last volume.
    s.eq(sf.final_volume(work(volumes_stated=5)), None,
         "a shop stating five volumes and three read settles nothing")
    s.eq(sf.final_volume(work(volumes_stated=None)), None,
         "and a shop that states no count settles nothing either")

    # STILL RUNNING IS NOT FINISHED.
    s.eq(sf.final_volume(work(completed=False)), None, "a series the shop has not marked complete")

    # NO ISBN, NO CLAIM. A title would identify the wrong volume as readily as the right one.
    s.eq(sf.final_volume(work(volumes=[{"volume": 1}, {"volume": 2}, {"volume": 3}])), None,
         "a final volume stating no ISBN is not claimed by some other route")
    s.eq(sf.final_volume(work(volumes=[])), None, "and a work with no volumes read is not claimed")

    # The highest number is the last one, whatever order the page listed them in.
    shuffled = work(volumes=[{"volume": 3, "isbn": "9784000000035"},
                             {"volume": 1, "isbn": "9784000000011"},
                             {"volume": 2, "isbn": "9784000000028"}])
    s.eq(sf.final_volume(shuffled)["volume"], 3, "order on the page is not the order of publication")

    # A numbered set whose top number is not the stated count is not settled: the shop says four
    # volumes and the numbers run to three, so something was not read.
    s.eq(sf.final_volume(work(volumes_stated=4, volumes_found=4)), None,
         "the last number read has to be the number the shop stated")

    s.eq(sf.claims({}), [], "an empty capture claims nothing, and does not raise")

    # WHETHER THE SERIES FINISHED IS NOT THE SAME QUESTION as which volume ended it. Nominating one
    # volume out of several needs the count to agree, because a short capture would nominate the
    # wrong one. Whether it finished is one fact the shop states about the series, and how much of
    # the shelf we read has no bearing on whether it is true.
    short = work(volumes_stated=9)
    s.eq(sf.final_volume(short), None, "a short capture names no final volume")
    s.eq(len(sf.finished({"works": [short]})), 1, "and still records that the series finished")
    s.eq(sf.finished({"works": [short]})[0]["isbns"][0], "9784000000011",
         "keyed by every ISBN on the work, so it joins on whichever volume we hold")
    s.eq(sf.finished({"works": [work(completed=False)]}), [],
         "a series the shop has not marked complete is not recorded as finished")
    s.eq(sf.finished({"works": [work(volumes=[{"volume": 1}])]}), [],
         "and a work stating no ISBN cannot be joined, so it is not claimed")
    s.eq(sf.finished({}), [], "an empty capture finishes nothing")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
