#!/usr/bin/env python3
"""pass0_cache.py: pulling a creator's handle out of pages we already hold.

COVERS = ['adapters/names/pass0_cache.py']

A false positive here is a misnamed person, which §1 treats as the expensive kind of error. A false
negative only costs a lookup in pass 3. The rules are therefore deliberately strict, and the tests
are mostly about what must NOT be taken as a name.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import testkit
from adapters.names import pass0_cache as p0


def main(s):
    s.eq(p0.HANDLE.findall('href="https://twitter.com/yamada_taro"'), ["yamada_taro"],
         "a twitter handle is found")
    s.eq(p0.HANDLE.findall('href="https://x.com/yamada"'), ["yamada"], "x.com works too")
    s.eq(p0.PIXIV_USER.findall("https://pixiv.net/users/12345"), ["12345"], "a pixiv id is found")

    # Twitter's OWN paths are not handles. Taking them would credit works to "intent" and "share".
    for path in ("intent", "share", "home", "hashtag", "search", "i"):
        s.check(path in p0.NOT_HANDLES, f"{path} is excluded as a site path, not a person")

    # A handle becomes a name only when it LOOKS like one. Digit soup is an account, not a person.
    s.check(p0.NAME_SHAPED.match("yamada"), "a plain handle is name-shaped")
    s.check(p0.NAME_SHAPED.match("yamada_taro"), "an underscore separator is name-shaped")
    s.check(p0.NAME_SHAPED.match("a.b-c"), "dots and hyphens separate too")
    s.check(not p0.NAME_SHAPED.match("user12345"), "digits are not name-shaped")
    s.check(not p0.NAME_SHAPED.match("_leading"), "a leading separator is not name-shaped")
    s.check(not p0.NAME_SHAPED.match("a_b_c_d_e"), "too many segments is not a name")

    # The print half is out of scope and its readings are already on disk, so those caches are
    # skipped rather than blurring the two halves for no gain.
    s.check("madb-cache" in p0.SKIP_CACHES, "the print bibliographic cache is skipped")
    s.check("openbd-cache" in p0.SKIP_CACHES, "and so is openBD's")

    # The host must be recoverable from a cache FILENAME, because one directory holds many hosts:
    # giga-series-cache alone carries comic-days.com, sunday-webry.com and several more. Counting
    # against the directory hides a platform account inside a bigger denominator.
    s.eq(p0.CACHE_HOST.findall("https___comic_days_com_atom_series_1"), ["comic_days_com"],
         "the host is recovered from the cache filename")
    s.eq(p0.CACHE_HOST.findall("KC_000031_S.html"), [],
         "a filename carrying no host yields none, and the directory stands in")

    # ── WHICH SURFACES NEED NO LOOKING UP AT ALL ──────────────────────────────────────────────
    #
    # The rule used to ask `script_class(ja) == "latin"`, which is a bucket rather than the
    # question. `2332` is a work BOOK☆WALKER sells under that title and it holds no kanji, no kana
    # and no Latin letter, so it landed in `other`, got no record, and was the last row keeping
    # `works without English` off zero.
    s.check(p0.needs_no_romanising("Distortion"), "a Latin title is already its own English")
    s.check(p0.needs_no_romanising("2332"), "and so is a title made of digits, which has no reading to find")
    s.check(p0.needs_no_romanising("Girl@Girl"), "punctuation inside it changes nothing")
    s.check(not p0.needs_no_romanising("球詠"), "kanji has to be read before it can be spelled")
    s.check(not p0.needs_no_romanising("ゆゆ式"), "and so does kana")
    # THE COUNTER-CASE THAT NARROWED THE RULE. The first version asked only whether the surface
    # held Japanese, which admitted five Korean pen names sitting in the same `other` bucket as
    # `2332`. Hangul romanises, so recording one as its own English would publish a name in the
    # script the reader asked not to see and claim on the record that no romanising was involved.
    s.check(not p0.needs_no_romanising("싱글벙글환상향"),
            "Hangul is a letter waiting to be read, which is what separates it from a digit")
    # THE COUNTER-CASE THAT KEEPS THE RULE HONEST. `mixed` is kana beside Latin, and the kana half
    # still owes a reading, so a surface with any Japanese in it goes to the later passes.
    s.check(not p0.needs_no_romanising("Vチューバー"),
            "Latin beside kana is not a finished name; the kana half still has to be read")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.pass0_cache"))
