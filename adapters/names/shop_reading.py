#!/usr/bin/env python3
"""How a title is read, taken from the shop page the publisher's own blurb is carried on.

WHY THIS EXISTS. 3,520 of the corpus's titles carry a reading a morphological analyser assembled,
and the analyser is wrong on exactly the words a title is made of: 豹藤さんは攻略したい came out
`ヒョウ フジサン ワ コウリャク シタイ`, which gets the surname wrong and misses that the work
glosses 攻略 as おと, from 落とす, so that the gaming word for clearing a route puns on seducing
someone.

BOOK☆WALKER states the answer twice on the page it sells the book from, and a pass that reads only
structured fields walks past the second one.

  ITS KEYWORDS FIELD CARRIES THE WHOLE TITLE'S READING.
  `豹藤さんは攻略（おと）したい,ヒョウドウサンハオトシタイ,由井ひな子,みんなのコミック,マンガ,電子書籍`.
  One katakana field per work, stated by the shop, and it already has the gloss in it.

  ITS DESCRIPTION WRITES FURIGANA IN RUNNING TEXT. `高１の豹藤（ひょうどう）くどきは…`. A publisher's
  blurb routinely glosses a surname on first use, which is a stated reading sitting in prose rather
  than in a field. Read for the pairs alone.

WHAT IS STORED, AND WHAT IS NOT. One reading per title, and the `漢字（かな）` pairs. Never the
blurb: REQUIREMENTS §2 keeps synopsis text out of this repository, so the prose is parsed in memory
and dropped, and the cache it was parsed from lives outside the repo.

WHAT THE READING IS WORTH. The shop is the publisher's own retail arm and the string is the
publisher's registered yomi for the edition, the same field openBD returns as a `collationkey`. So
this is `reading_basis: stated` with `reading_source_kind: platform`, citing the page it was read
on. It is not the artist's own statement of a personal name and it is not offered as one: this
settles TITLES. Where a title IS a person's name, NAMES-PLAN §5c inherits the higher bar and the
entry says so.

THE PARSE CHECKS ITSELF, because a comma-separated field is exactly the shape that silently returns
the wrong element. A title containing a comma pushes the reading along by one, so the reading is
found by being the first katakana-only field AND the fields in front of it must rejoin to the
title the page states. A page whose two do not agree yields nothing.
"""
import html as _html
import re
import unicodedata

KEYWORDS = re.compile(r'<meta name="keywords" content="([^"]*)"')
DESCRIPTION = re.compile(r'<meta name="description" content="([^"]*)"')

# A reading, as the shop writes one: katakana and the marks that ride with it. Deliberately the
# same shape `curate.KATAKANA` accepts, minus the letters and digits, because a keyword field also
# holds a publisher's Latin imprint and that must not be mistaken for a reading.
KATAKANA_ONLY = re.compile(r"^[ァ-ヺー・\s0-9０-９！-／：-＠［-｀｛-～、。〜…【】〇○◯"
                           r"─━♪♭♯★☆♡♥◎△▽※＆!-/:-@\[-`{-~]+$")

# 漢字（かな）in running text. The bracket is full width in Japanese prose and half width in a
# minority of blurbs, so both are read; the gloss must be kana and the head must contain a kanji,
# which is what keeps it off （笑）and off a bracketed English word.
FURIGANA = re.compile(r"([々㐀-䶿一-鿿]{1,12})[（(]([ぁ-んー]{1,20})[）)]")


def _meta(page, pattern):
    m = pattern.search(page or "")
    return _html.unescape(m.group(1)) if m else ""


def fold(s):
    """Width-folded and stripped of the spaces a shop adds, for comparing two spellings."""
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").strip()


# What the shop writes in that field about itself. Every keywords line ends with these, they are
# katakana, and a work whose reading is missing would otherwise be recorded as being called マンガ.
BOILERPLATE = {"マンガ", "電子書籍", "コミック", "ライトノベル", "ラノベ", "小説", "雑誌", "写真集"}


def title_reading(page, want=None):
    """`(title, reading)` the shop states for the work, or None.

    `want` is the title we asked about. Given one, the page has to agree it is that work, because
    a shop URL that has been reused for a different edition answers happily with somebody else's
    reading and nothing in the response says so.
    """
    fields = [f.strip() for f in _meta(page, KEYWORDS).split(",")]
    if len(fields) < 2:
        return None
    # The reading is the first katakana field that is not the shop describing its own catalogue,
    # and everything in front of it is the title, which is how a title containing a comma survives.
    idx = next((i for i, f in enumerate(fields)
                if i and f and f not in BOILERPLATE and KATAKANA_ONLY.match(f)), None)
    if idx is None:
        return None
    title, reading = ",".join(fields[:idx]).strip(), fields[idx]
    if not title or not reading:
        return None
    if want is not None and fold(title) != fold(want):
        return None
    return title, without_volume(title, reading)


VOLUME_TAIL = re.compile(r"[0-9０-９]+$")


def without_volume(title, reading):
    """The reading with the volume number the shop appends to it taken off.

    THE SHOP SELLS A VOLUME AND THE CORPUS HOLDS A SERIES. BOOK☆WALKER files 100日後に咲く百合's
    first volume with the reading `ヒャクニチゴニサクユリ001`, where the title field carries no
    number at all. Kept, that publishes a series called Hyakunichigonisakuyuri001.

    The title answers this about itself: digits come off the reading only where the title has none
    of its own on the end. 100日後に咲く百合 has digits at the FRONT and keeps them, and a work
    genuinely named with a trailing number keeps its reading whole.
    """
    if VOLUME_TAIL.search(fold(title)):
        return reading
    return VOLUME_TAIL.sub("", reading).strip() or reading


def furigana_pairs(text):
    """`[(kanji, kana)]` a blurb glosses in running text, deduplicated, in the order written.

    Takes TEXT rather than a page so the caller decides which part of the document is a publisher's
    blurb. Reading the whole page instead would collect every gloss in the site's furniture and
    every recommendation beside it.
    """
    out = []
    for kanji, kana in FURIGANA.findall(text or ""):
        if (kanji, kana) not in out:
            out.append((kanji, kana))
    return out


def blurb_furigana(page):
    """The pairs a shop page's own description glosses. The blurb itself is never returned."""
    return furigana_pairs(_meta(page, DESCRIPTION))


def entry(title, reading, url, guess, reviewed, pairs=()):
    """The curated title entry for one reading a shop states."""
    note = ("BOOK☆WALKER's own page for this work carries the reading in its keywords field, "
            "beside the title. The shop is the publisher's retail arm and the string is the yomi "
            "registered for the edition.")
    if pairs:
        note += (" The publisher's blurb on the same page glosses "
                 + "、".join(f"{k}（{v}）" for k, v in pairs[:4]) + " in running text, which is the "
                 "same reading written a second way.")
    if (guess or "").replace(" ", "") != reading.replace(" ", ""):
        note += f" It replaces {guess!r}, which no source had stated."
    else:
        note += " It agrees with the reading already shown, which no source had stated."
    return {"reading": reading, "reading_basis": "stated", "reading_source_kind": "platform",
            "reading_note": note, "source": "BOOK☆WALKER", "source_kind": "platform",
            "source_url": url, "reviewed": reviewed}


def main(argv=None):
    import argparse
    import datetime
    import pathlib
    import sys

    import yaml

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    import net                                                         # noqa: PLC0415
    import paths                                                       # noqa: PLC0415
    from build import norm_work                                        # noqa: PLC0415

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # Defaulted, not required: see adapters/paths.py for the rule and why the alternative left a
    # two hour sweep with nothing on disk. This directory already holds bookwalker.jp pages that
    # thin/sources.py fetched, and net.py keys them by host, so sharing it is a saving.
    ap.add_argument("--cache", default=str(paths.cache("shop-reading-cache")),
                    help="where fetched pages live; outside the repo")
    ap.add_argument("--source", default="data/source/bookwalker")
    ap.add_argument("--names", default="data/names/titles.yaml")
    ap.add_argument("--limit", type=int, default=0, help="stop after this many pages")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--reviewed", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)

    cache = pathlib.Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    # 1.5 s, which is what this route asked for before it shared a fetcher. Asked for by host, so
    # net.PAUSE stays where it is for the other 26.
    net.set_pause("bookwalker.jp", 1.5)

    def fetch(url):
        """The page, or None where the shop said there is none. Raises net.Refused otherwise.

        THE ERROR USED TO BE CACHED. A failure was written into the cache directory as a page
        beginning `__ERROR__`, so a shop that was briefly down left a permanent answer on disk: the
        file existed, it was served for ever after, and the work was counted `no-page` on every
        subsequent run. net.py does not cache a refusal, and the raise is what stops it being
        counted as an absence here.
        """
        r = net.cached(url, cache) if a.offline else net.fetch(url, cache, net.AGE_LISTING)
        if r is None:
            return None                                   # offline, and this page was never got
        return net.body(r)

    held = (yaml.safe_load(pathlib.Path(a.names).read_text()) or {}).get("names") or {}
    # SETTLED IS FINAL (NAMES-PLAN §4): a title a source has stated is never asked about again.
    unsettled = {k: v.get("reading") for k, v in held.items()
                 if v.get("reading_basis") not in ("stated", "surface", "researched")}

    urls = {}
    for f in sorted(pathlib.Path(a.source).glob("*.yaml")):
        d = yaml.safe_load(f.read_text()) or {}
        ti = (d.get("title") or {}).get("ja")
        if ti and d.get("shop_url"):
            urls.setdefault(norm_work(ti), (ti, d["shop_url"]))

    queue = [(k, *urls[norm_work(k)]) for k in sorted(unsettled) if norm_work(k) in urls]
    if a.limit:
        queue = queue[:a.limit]

    found = {}
    # `refused` is kept apart from `no-page` because they are different facts. The shop stating it
    # has no such page is about the book; the shop declining to answer is about the shop, and a run
    # that met a wall of refusals must not read as a run that found the books absent.
    misses = {"no-page": 0, "refused": 0, "no-keywords": 0, "title-disagrees": 0}
    for key, shop_title, url in queue:
        try:
            page = fetch(url)
        except net.Refused:
            misses["refused"] += 1
            continue
        if not page:
            misses["no-page"] += 1
            continue
        got = title_reading(page, want=shop_title)
        if not got:
            misses["title-disagrees" if title_reading(page) else "no-keywords"] += 1
            continue
        found[key] = entry(got[0], got[1], url, unsettled[key], a.reviewed, blurb_furigana(page))

    # THE SAME FLOOR openbd_reading AND madb_reading CARRY. A shop that is down answers every page
    # with an error, states nothing, and reports a clean run with an empty result, which looks
    # exactly like a batch of works the shop happens not to carry. Nothing is written into
    # data/source from here, so the cost of the confusion is a wasted run rather than a lost
    # capture; it is still worth refusing rather than printing an empty answer.
    unanswered = misses["no-page"] + misses["refused"]
    print(f"HEALTH: {len(queue) - unanswered} of {len(queue)} page(s) answered "
          f"({misses['refused']} refused)")
    if queue and unanswered == len(queue):
        print("Refusing to write: not one page answered. That is the shop unreachable rather than "
              "a batch it does not carry, and the two look identical from here.")
        return 1
    print(f"{len(unsettled)} title(s) with no stated reading, {len(queue)} of them on the shop; "
          f"{len(found)} stated, misses {misses}")
    print(yaml.safe_dump({"titles": found}, allow_unicode=True, sort_keys=True, width=100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
