#!/usr/bin/env python3
"""How a TITLE is read, taken from the National Diet Library's record page for the book.

WHY THIS EXISTS AND WHY IT IS NOT `ndl_reading.py`. That module reads
`dcndl:creatorTranscription` off an OpenSearch response and answers about a PERSON. This one
answers about a WORK, from a different document on a different path, and the two are separate for
the reason the split is worth having: `/api` is disallowed by `ndlsearch.ndl.go.jp/robots.txt` and
the record pages under `/books/` are not, so one of the two routes may be fetched and the other may
not. Folding them together would put a permitted fetch behind a module whose docstring says the
route is closed, and somebody would eventually reopen the wrong one.

  A CORRECTION TO `ndl_reading.py`, WHICH SAYS THE RECORD PAGES RETURN 503. They do not, as of
  2026-08-08: `/books/R100000002-I026095900` serves 218 KB of rendered HTML with the full
  bibliographic table in it. That note was written when the API was the only route anyone had
  tried, and taking it at face value is what left the title readings unsourced for another round.

WHAT IT READS. The record page prints a definition list of the catalogue's own fields, and the one
this wants is `タイトルよみ`: a national cataloguing authority stating how the title is said. Under
`curate.py` that is `reading_basis: stated` with `reading_source_kind: national-library`.

WHY THE WHOLE TABLE IS PARSED RATHER THAN ONE FIELD. `タイトル` and `著者` are what decide whether
the record is about the work we asked about, and a reading taken without checking them is a string
match against every book in Japan. `ndl.py` records the same lesson from the other side: a title
search for `citrus+` returns an unrelated book from 2007. So `fields()` returns everything and the
caller does the joining, which also means a new field costs no code here.

WHAT A MATCH REQUIRES, AND WHY IT IS STRICTER THAN IT LOOKS. Our catalogue stores the title a
PLATFORM shows, which carries apparatus a book does not: 【単話版】 for a chapter sold on its own,
（BC） for an imprint, a volume number. NDL holds the book. So the comparison folds width and
strips the bracketed apparatus from our side before comparing, and it still demands equality
afterwards: a prefix match would let `恋する小惑星` answer for `恋する小惑星アンソロジー`, which is
a different book with a different reading.

WHAT SILENCE MEANS. Nothing about the work. Most of this corpus is web serialisation with no
tankobon, so NDL holds no record and there is no reading to state. That is `no-record`, and it is
never a licence to keep the analyser's guess and call it sourced.
"""
import html as _html
import pathlib
import re
import unicodedata

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
# Beside the repository, where every other cache directory in this project lives, and
# derived from this file so it names no particular machine.
DEFAULT_CACHE = pathlib.Path(__file__).resolve().parents[2].parent / "ndl-cache"
PAUSE = 1.6

HOST = "https://ndlsearch.ndl.go.jp"
# THE ONE PATH THIS MODULE MAY FETCH. robots.txt disallows `/api` and `/statistics` among others,
# and `build_url` refuses anything not under here rather than trusting a caller to remember.
BOOKS = "/books/"
SEARCH = "/search"

TITLE = "タイトル"
READING = "タイトルよみ"
AUTHOR = "著者"

# Vue renders each field as `<dt>label</dt><dd>value</dd>` with hydration comments inside both.
_DT = re.compile(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", re.S)
_TAG = re.compile(r"<[^>]+>")
_RECORD = re.compile(r"/books/(R\d+-I\d+)")

# Apparatus a platform puts on a title and a book does not carry. Removed from OUR side only,
# because NDL is transcribing a printed title page and has none of it.
_APPARATUS = re.compile(r"[【（(\[][^】）)\]]*[】）)\]]\s*$")

# ISBD's other-title-information mark, as `adapters/isbd.py` reads it. Not imported from there: that
# module answers what a work is CALLED and this one only wants somewhere shorter to search, so it
# is allowed to be loose in ways a stored name may not be.
COLON = re.compile(r"\s*:\s*")


def _text(fragment):
    """One HTML fragment as the text a reader sees, with the markup and entities gone."""
    return re.sub(r"\s+", " ", _html.unescape(_TAG.sub("", fragment or ""))).strip()


def fields(page):
    """Every `<dt>` label on a record page against its value, first occurrence winning.

    FIRST WINS BECAUSE THE PAGE REPEATS ITSELF. `資料種別` appears twice on every record and
    `請求記号` appears under two different headings, so a dict built last-wins silently prefers
    whichever copy the template happens to emit later. Nothing here depends on those two, and the
    rule is written down so that a field which does start mattering is not read from the copy
    nobody looked at.
    """
    out = {}
    for label, value in _DT.findall(page or ""):
        k, v = _text(label), _text(value)
        if k and k not in out:
            out[k] = v
    return out


def record_ids(page):
    """Every bibliographic record a search results page links to, in order, without repeats.

    Each result links to its record more than once, from the cover image and from the title, so
    the same id comes back several times running and the order is what carries the ranking.
    """
    seen, out = set(), []
    for rid in _RECORD.findall(page or ""):
        if rid not in seen:
            seen.add(rid)
            out.append(rid)
    return out


def fold(title):
    """A title in the form two catalogues can be compared on.

    Width-folded and lower-cased, with the trailing bracketed apparatus off and spaces removed.
    `ひとりぼっちの○○生活【タテスク】` and `ひとりぼっちの○○生活` are one work under two
    spellings; `恋する小惑星` and `恋する小惑星アンソロジー` are two works and stay two.
    """
    s = unicodedata.normalize("NFKC", title or "").strip()
    prev = None
    while s != prev:                       # 【連載版】（BC） is two groups, and both are apparatus
        prev = s
        s = _APPARATUS.sub("", s).strip()
    return re.sub(r"[\s　]+", "", s).lower()


def search_terms(title):
    """The keywords to search a title under, best first, without repeats.

    ONE QUERY IS NOT ENOUGH, and the shape of the miss is worth recording. Our catalogue stores a
    title with everything the platform prints on it, so `遠山えま百合集 : センセイとの時間。` goes to
    NDL with the ISBD colon and the subtitle attached and matches nothing, while `遠山えま百合集`
    returns the one record that holds it. Thirteen titles came back `no-record` for that reason and
    NDL had every one of them.

    Widening the SEARCH does not widen what is accepted: `reading()` still compares the record's own
    `タイトル` against the full stored title, so a head that matches a different book is refused
    exactly as it was before. The head is a way to find the record, not a way to agree with it.
    """
    s = str(title or "").strip()
    out = []
    for term in (s, COLON.split(s)[0], _APPARATUS.sub("", s).strip(),
                 COLON.split(_APPARATUS.sub("", s))[0].strip()):
        t = term.strip()
        if t and t not in out:
            out.append(t)
    return out


def reading(page, title):
    """The kana NDL states for this title, or None where the record is about something else.

    The title check is the whole of the safety here, so it is done on the page's own `タイトル`
    rather than on the string the search was made with: a search matches loosely and a record
    states exactly what it is about.
    """
    f = fields(page)
    got, kana = f.get(TITLE), f.get(READING)
    if not kana or not got:
        return None
    if fold(got) != fold(title):
        return None
    return kana


def settle(readings):
    """One reading where the records agree, and None where they do not.

    A series has a record per volume and every one of them states the same タイトルよみ, so
    agreement is the ordinary case and disagreement is a finding. Two different readings for one
    written title means at least one record is about another book, which is the failure
    `ndl_reading.settle` is written against on the author side, and the answer there and here is
    to yield nothing rather than a majority.

    SPACING IS NOT DISAGREEMENT. NDL writes `ウララ メイロチョウ` with the word division in it and
    another volume of the same series supplies the same kana divided somewhere else. The kana is
    what the library is stating; where the division falls is a cataloguer's choice, and calling two
    of them a conflict would report a settled reading as unresolved.

    WHICH DIVISION TO KEEP, AND WHY IT IS NOT `ndl_reading.settle`'S ANSWER. That module takes the
    LONGEST form, because on the author side the alternatives are `シノノメミズオ` and
    `シノノメ, ミズオ` and the longer one has recovered a boundary the shorter one lost. On the
    title side the alternatives are four volumes of one series and the odd one out is a slip:
    うらら迷路帖 is transcribed `ウララ メイロチョウ` on three records and `ウラ ラ メイロチョウ` on
    the fourth, and longest-wins picks the slip and renders it `Ura Ra Meirochō`. So the answer here
    is the division most of the records agree on, and where they split evenly the one with fewest
    spaces in it: 紅茶の魔女 is two records each way on `ユウガ ナル` against `ユウガナル`, and
    優雅なる is one word. Every division seen is reported, because the tie-break is a preference and
    the reviewer is the one who can read the title.
    """
    import collections
    seen = [r for r in readings if (r or "").strip()]
    if not seen:
        return None, {"status": "no-record", "records": 0}
    by_kana = {}
    for r in seen:
        by_kana.setdefault(re.sub(r"[\s　]+", "", r), []).append(r)
    ev = {"records": len(seen)}
    if len(by_kana) > 1:
        return None, {**ev, "status": "conflicting", "readings": sorted(set(seen))}
    forms = next(iter(by_kana.values()))
    counts = collections.Counter(forms)
    best = min(sorted(counts), key=lambda f: (-counts[f], f.count(" "), f.count("　")))
    out = {**ev, "status": "stated"}
    if len(counts) > 1:
        out["divisions"] = sorted(counts)
    return best, out


def build_url(path, **params):
    """A URL on a path this module is allowed to fetch, or a refusal.

    THE RULE IS ENFORCED HERE RATHER THAN REMEMBERED. `/api` is disallowed by robots and
    `ndl_reading.py` exists to say so; the cost of that rule being carried in a docstring was three
    rounds of author readings fetched off a route that forbade it. A function that will not build
    the URL cannot be forgotten.
    """
    import urllib.parse
    if not (path == SEARCH or path.startswith(BOOKS)):
        raise ValueError(f"ndlsearch path {path!r} is not one this module may fetch; "
                         f"robots.txt allows {SEARCH} and {BOOKS} and disallows /api")
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    return HOST + path + q


def search_url(title):
    return build_url(SEARCH, cs="bib", keyword=title)


def record_url(rid):
    return build_url(BOOKS + rid)


def main(argv=None):
    """Ask NDL for the stated reading of every title named on stdin, and print what it found.

    Prints rather than writes, because what comes back is EVIDENCE FOR A REVIEWER and not a name.
    A title reading goes into `data/names/curated.yaml` by hand, with the record it was read from
    beside it, exactly as the author readings did: the extraction is mechanical and the decision
    that this record is about this work is not.
    """
    import argparse
    import hashlib
    import json
    import pathlib
    import sys
    import time
    import urllib.request

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--titles", help="a file of Japanese titles, one per line; stdin otherwise")
    # A CACHE NOBODY PASSES IS A CACHE NOBODY HAS. This defaulted to None, so a two hour
    # sweep of 124 publisher labels left nothing on disk and a re-run would pay for it
    # again. NDL rate-limits to roughly one page every few seconds, which makes its pages
    # the most expensive bytes this project fetches, and every other adapter here keeps a
    # cache directory beside the repository. Pass --no-cache to refuse one deliberately.
    ap.add_argument("--cache", default=str(DEFAULT_CACHE),
                    help="directory to keep fetched pages in")
    ap.add_argument("--no-cache", action="store_true", help="fetch without keeping pages")
    ap.add_argument("--pause", type=float, default=PAUSE)
    ap.add_argument("--retries", type=int, default=5, help="attempts before a 503 counts as one")
    ap.add_argument("--max-records", type=int, default=4,
                    help="record pages to open per title, best-ranked first")
    a = ap.parse_args(argv)

    src = pathlib.Path(a.titles).read_text() if a.titles else sys.stdin.read()
    want = [t.strip() for t in src.split("\n") if t.strip()]
    cache = None if a.no_cache else pathlib.Path(a.cache)
    if cache:
        cache.mkdir(parents=True, exist_ok=True)

    def get(url, key):
        """One page, from the cache where it is there and from NDL where it is not.

        503 IS THE ANSWER TO ASKING TOO FAST, not to asking for the wrong thing. A record page is
        200 KB and a first run at 1.6 s between requests had 61 of 100 titles refused this way,
        which reads exactly like a work NDL does not hold. Backing off and asking again turns that
        into an answer; treating it as a negative would have written 61 works off as having no
        catalogue record.
        """
        # THE CACHE NAME IS A HASH BECAUSE THE KEYS ARE JAPANESE. Substituting the unsafe
        # characters mapped every kanji and kana to `_`, so `search-遠山えま百合集` and
        # `search-怪異部` were one file, and the second title silently read the first title's
        # results and reported `no-record`. A cache that answers the wrong question is worse than
        # no cache: it looks exactly like a work NDL does not hold.
        p = cache / (hashlib.sha1(key.encode()).hexdigest()[:24] + ".html") if cache else None
        if p and p.exists():
            return p.read_text()
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        for attempt in range(a.retries):
            try:
                with urllib.request.urlopen(req, timeout=45) as r:
                    body = r.read().decode("utf-8", "replace")
                break
            except urllib.error.HTTPError as e:
                if e.code not in (429, 503) or attempt == a.retries - 1:
                    raise
                time.sleep(a.pause * (2 ** attempt) + 4)
        if p:
            p.write_text(body)
        time.sleep(a.pause)
        return body

    for t in want:
        row, got, seen, failed = {"title": t}, [], set(), None
        for term in search_terms(t):
            try:
                page = get(search_url(term), "search-" + term)
            except Exception as e:                                          # noqa: BLE001
                failed = str(e)
                continue
            for rid in record_ids(page)[:a.max_records]:
                if rid in seen:
                    continue
                seen.add(rid)
                try:
                    rec = get(record_url(rid), rid)
                except Exception:                                           # noqa: BLE001
                    continue
                r = reading(rec, t)
                if r:
                    got.append((r, rid))
            if got:
                break
        if not got and failed:
            print(json.dumps({**row, "status": "fetch-failed", "error": failed},
                             ensure_ascii=False))
            continue
        answer, ev = settle([r for r, _ in got])
        print(json.dumps({**row, "reading": answer, **ev, "searched": len(seen),
                          "records": [rid for _, rid in got]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
