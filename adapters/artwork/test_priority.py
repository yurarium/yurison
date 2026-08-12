#!/usr/bin/env python3
"""artwork/priority.py: the OCR ordering keeps every cover in the queue.

COVERS = ['adapters/artwork/priority.py']

THE PROPERTY UNDER TEST IS THAT NOTHING IS DROPPED. Ordering by what tesseract can read is safe
only because it orders; the moment a zero score removed a cover, every cursive and hand-lettered
title would vanish from the pass without anyone noticing. So the test that matters is a round trip
of the whole queue, and the noise case that motivated scoring against a dictionary.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import priority                                                        # noqa: E402
import testkit                                                         # noqa: E402

VOCAB = {"love", "peace", "watch", "baseball", "game", "the", "and", "dating", "right"}


def _dictionary_beats_letter_counting(s):
    # WHAT TESSERACT MAKES OF A JAPANESE LOGO: letter shapes that are not words.
    noise = "Asi wRE Aorkhle ose Bho Wan Les Wed wig via tHe Dab"
    real = "LOVE and PEACE"
    s.eq(priority.words(real, VOCAB), ["LOVE", "and", "PEACE"], "real words are kept as printed")
    s.eq(len(priority.words(noise, VOCAB)), 1,
         "glyph noise scores almost nothing, where counting three-letter runs scored it 12")
    s.check(len(priority.words(noise, VOCAB)) < len(priority.words(real, VOCAB)),
            "so a cover with English outranks a cover with none")


def _ordering_keeps_everything(s):
    queue = [{"file": "a.jpg"}, {"file": "b.jpg"}, {"file": "c.jpg"}, {"file": "d.jpg"}]
    got = priority.ordered(queue, {"c.jpg": 5, "a.jpg": 1})
    s.eq([x["file"] for x in got], ["c.jpg", "a.jpg", "b.jpg", "d.jpg"],
         "most English first, and the unscored follow")
    s.eq(len(got), len(queue), "EVERY COVER IS STILL IN THE QUEUE; this is the whole safety of it")
    s.eq(sorted(x["file"] for x in got), sorted(x["file"] for x in queue), "and they are the same ones")

    # A SCORE OF ZERO SINKS A COVER, IT DOES NOT REMOVE IT.
    blank = priority.ordered(queue, {"a.jpg": 0, "b.jpg": 0, "c.jpg": 0, "d.jpg": 0})
    s.eq([x["file"] for x in blank], ["a.jpg", "b.jpg", "c.jpg", "d.jpg"],
         "with nothing to go on the queue is left exactly as it came, value order intact")


def _no_dictionary_is_survivable(s):
    s.eq(priority.vocabulary("/nonexistent/words"), set(),
         "a machine without a word list scores nothing rather than raising")
    s.eq(priority.words("LOVE and PEACE", set()), [],
         "and every cover then ties, which leaves the value ordering in place")


def main(s):
    _dictionary_beats_letter_counting(s)
    _ordering_keeps_everything(s)
    _no_dictionary_is_survivable(s)


if __name__ == "__main__":
    sys.exit(testkit.run(main, __file__))
