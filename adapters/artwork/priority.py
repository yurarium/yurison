#!/usr/bin/env python3
"""Order the cover queue by how much English an OCR pass can see on each image.

THIS IS A PRIORITY AND IT MUST NEVER BECOME A FILTER. Tesseract cannot read the covers that matter
most: a cursive `Girls in the Hell.`, a six-pixel vertical `Hyaluron & Daruma`, a title lettered
into a logo. Those are precisely the finds a person is here to make, so a queue trimmed by OCR
would share the blind spot of the thing it trims for, and the misses would be silent. Ordering
loses nothing: a cover OCR reads as blank goes last and is still opened.

Scoring counts DICTIONARY WORDS, not letters. A first attempt counted any run of three letters and
called 1,079 of 1,243 covers Latin-bearing, because tesseract reads Japanese glyphs as letter
noise; the top of that ranking was gibberish. Real English is made of real words.
"""
import pathlib
import re
import subprocess

WORD = re.compile(r"[A-Za-z]{3,}")
DICT = pathlib.Path("/usr/share/dict/american-english")


def vocabulary(path=None):
    """The word list, lowercased, three letters and up. Empty if the system has no dictionary."""
    p = pathlib.Path(path) if path else DICT
    if not p.exists():
        return set()
    return {w.strip().lower() for w in p.read_text(errors="ignore").splitlines()
            if w.strip().isalpha() and len(w.strip()) >= 3}


def words(text, vocab):
    """The real English words in a page of OCR output, in the order they were read."""
    return [w for w in WORD.findall(text or "") if w.lower() in vocab]


def read(image, timeout=60):
    """What tesseract makes of one image. Empty string when it cannot be run at all."""
    try:
        return subprocess.run(["tesseract", str(image), "-", "-l", "eng", "--psm", "11"],
                              capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def ordered(queue, scores):
    """The queue, most-English first, with every entry still in it.

    Ties and unscored entries keep the order they arrived in, so the value ordering underneath
    (works with no English name first) survives inside each band.
    """
    return sorted(queue, key=lambda x: -scores.get(x["file"], 0))
