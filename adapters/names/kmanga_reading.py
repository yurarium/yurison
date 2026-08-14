#!/usr/bin/env python3
"""How a name is read, weighed off the kana a retailer prints beside the byline it sells under.

WHY THIS EXISTS. Every route to a reading a source STATES has now been asked and answered.
`ndl_reading.py` is closed, because `ndlsearch.ndl.go.jp/robots.txt` disallows `/api` and the
catalogue's own search page carries no results in the document: the same 564,314 bytes come back
for every creator, and the records arrive from the disallowed endpoint afterwards.
`openbd_reading.py` has been asked about all 2,417 ISBNs the corpus states. `madb_reading.py` has
been run against the pinned release. `platform_reading.py` found one platform in the whole set with
an author page on it. What is left after those is 747 author names carrying a morphological
analyser's guess, and 529 of them are on a work with a print edition, so a shop that files those
books is looking at the same people.

まんが王国 prints the kana in the 著者・作者 field of every title page it sells:
`<a href="/search/author/15404">甲斐谷忍<span class="f10">（かいたにしのぶ）</span></a>`. It prints
nothing where it knows nothing, which is how 堀賢一 appears on the same line with no gloss at all.

WHAT BASIS THIS CARRIES, AND WHY IT IS THE WEAKER ONE. `researched`, never `stated`. `stated` says
a source printed the kana as its own claim about the name, and a retailer does not say where its
kana came from: it may be the publisher's registered yomi, it may be the shop's own filing key, and
one page carries both possibilities with nothing on it to separate them. `curate.py` names a
bookshop listing as evidence a reviewer may weigh, so the entry says a person weighed it and the
note says what was weighed.

  THE ARGUMENT `shop_reading.py` MAKES FOR BOOK☆WALKER DOES NOT CARRY HERE, and it is worth saying
  why, because the two modules look alike. That one records `stated` with `platform` beside it
  because BOOK☆WALKER is KADOKAWA's own retail arm, so the yomi on the page is the publisher's for
  its own edition. まんが王国 is Beaglee's and is nobody's publishing arm, so the same sentence
  cannot be written about it and the weaker basis is the honest one.

WHAT MAKES IT A JUDGEMENT AND NOT A BULK IMPORT. The reservation is recorded in
`data/queue/author-readings-progress.md`, which found this route, declined to run it, and said why:
applying `researched` to four hundred names mechanically is a bulk import wearing a reviewer's
label. What is applied here is a rule with its counter-cases tested, and every entry carries the
page, the book, and the string it replaces, so a reader can open the evidence and disagree.

  THE SHOPS DISAGREE WITH EACH OTHER, which is the reason the note names its one source and claims
  no more. DMM files 桜庭友紀 as さくらばゆうき where another listing gives さくらばゆき. Nothing
  here resolves that; it records which page was read.

WHAT IT REFUSES.

  A GLOSS BELONGS TO THE NAME BESIDE IT AND NOT TO THE NAME IN THE SAME POSITION. Three credits on
  one book give three anchors, each carrying its own name and its own gloss or none, and the pair is
  read out of one anchor. Attaching one artist's reading to another artist's name is the worst
  outcome available here: 古川楊也 was published under a different artist's name once already.

  A SEARCH HIT IS NOT AN IDENTIFICATION. `/search/word/` matches a name inside a title, so 若
  returns books by people called nothing like 若. The shop's own spelling of the credit has to equal
  ours on `ndl_reading.key`, which is what keeps 竹嶋 from answering for 竹嶋えく. The result tile
  carries the byline, so the test is applied before a book is opened as well as after, and a person
  absent from the shop's shelves costs one request.

  A KANA NAME KEEPS ITS OWN KANA. `openbd_reading.normalised` refuses a reading that has lost kana
  the surface carries, for the reason it was written: とりいしづく filed under トリイシズク is the
  artist's name with a different kana in it.

WHAT IT CANNOT SEE. Whether the shop is right. The gloss is one string on one page with no working
shown, and this module weighs it against the only other thing anybody holds, which is the guess it
replaces. Where those two agree the entry says so and the agreement is worth something; where they
differ the entry says that too and a reader with the page in front of them is better placed than
either.

Usage:  kmanga_reading.py --cache DIR            fetch and print entries for curated.yaml
        kmanga_reading.py --cache DIR --offline  re-read the cache without a request
"""
import pathlib as _pl0
import sys as _sys0

_sys0.path.insert(0, str(_pl0.Path(__file__).resolve().parents[1]))

import population as _population  # noqa: E402

import html as _html
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names import ndl_reading  # noqa: E402
from names.store import NameStore  # noqa: E402

BASE = "https://comic.k-manga.jp"
UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.6
# How many books to open for one name before giving up on it. A person the shop stocks is credited
# on the first hit; a longer walk is the search having matched something else, and each step costs
# a request.
DEPTH = 3

# One result tile on a word search, and the two things it carries. The document is split on the
# opening marker and each piece is read on its own, because reading the whole page with one pattern
# per field pairs the first book with the third byline the moment a tile omits one.
TILE = '<li class="book-list--target">'
TILE_LINK = re.compile(r'href="/title/(\d+)')
TILE_CREDIT = re.compile(r'<span class="book-list--author-item">(.*?)</span>', re.S)

# The byline block on a title page. The heading is matched on its own class so that a redesign
# yields nothing instead of yielding whichever list follows the word 作者 next, and the two
# headings the shop uses are both named because a file listing one would settle fewer names and
# report a clean run.
BYLINE = re.compile(r'<dt class="book-info--detail-title">\s*(?:著者・作者|作者|著者)\s*</dt>\s*'
                    r'<dd class="book-info--detail-item">(.*?)</dd>', re.S)
# One credit inside it. The gloss is a span the shop sizes rather than names, so the anchor is the
# unit and the span is read out of its content.
CREDIT = re.compile(r'<a[^>]*href="/search/author/(\d+)"[^>]*>(.*?)</a>', re.S)
GLOSS = re.compile(r'<span[^>]*>\s*[（(]\s*([^）)]*?)\s*[）)]\s*</span>', re.S)
TAG = re.compile(r"<[^>]+>")


def _text(fragment):
    return re.sub(r"\s+", " ", TAG.sub("", _html.unescape(fragment or ""))).strip()


def hits(page):
    """`[(title_id, [credit])]` for the books a search offers, in the shop's ranking.

    THE TILE ALREADY SAYS WHO WROTE THE BOOK, and reading it is what keeps the run affordable and
    honest at the same time. `/search/word/` matches inside a title, so a bare name comes back with
    books by people called nothing like it, and opening those to find out costs a request each and
    settles nothing. On the first thirty names it was 30 of the 96 requests spent on books that
    turned out to credit somebody else.
    """
    out, seen = [], set()
    for piece in (page or "").split(TILE)[1:]:
        m = TILE_LINK.search(piece)
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        out.append((m.group(1), [_text(c) for c in TILE_CREDIT.findall(piece)]))
    return out


def books_for(page, name):
    """The books on a search page whose own tile credits this person, in the shop's ranking.

    The tile's spelling has to equal ours on `ndl_reading.key`. That is the same comparison the
    title page is held to, and it is here as well so that a name the shop does not stock costs one
    request and no guessing.
    """
    want = ndl_reading.key(name)
    return [tid for tid, who in hits(page) if any(ndl_reading.key(c) == want for c in who)]


def credits(page):
    """`[(name, gloss)]` from one title page's byline, with `gloss` empty where none is printed.

    An empty gloss is kept rather than dropped, because "the shop stocks this person and states no
    reading for them" is a different answer from "the shop has never heard of them", and only the
    first of those is settled by looking somewhere else.
    """
    block = BYLINE.search(page or "")
    if not block:
        return []
    out = []
    for _id, inner in CREDIT.findall(block.group(1)):
        g = GLOSS.search(inner)
        gloss = _text(g.group(1)) if g else ""
        name = _text(GLOSS.sub("", inner))
        if name:
            out.append((name, gloss))
    return out


def author_url(page, name):
    """The shop's own page for this person, taken off the title page that credits them.

    The address is the citation, and it is read off the anchor the name sits in so that it cannot
    belong to the credit beside it.
    """
    block = BYLINE.search(page or "")
    if not block:
        return ""
    want = ndl_reading.key(name)
    for i, inner in CREDIT.findall(block.group(1)):
        if ndl_reading.key(_text(GLOSS.sub("", inner))) == want:
            return f"{BASE}/search/author/{i}"
    return ""


def records(pages, name):
    """Every book in `pages` whose byline names this person, with the reading it glosses.

    `pages` is `{title_id: html}`. The shape is `ndl_reading.settle`'s, so the agreement rule and
    its counter-cases stay in one place: a name the shop glosses two ways on two books is a finding
    to look at and never a majority to take.
    """
    from names import kana as kana_mod  # noqa: PLC0415
    want = ndl_reading.key(name)
    if not want:
        return []
    out = []
    for tid, page in (pages or {}).items():
        for who, gloss in credits(page):
            if ndl_reading.key(who) != want or not gloss:
                continue
            if not kana_mod.kana_only(gloss):
                continue
            out.append({"reading": kana_mod.to_katakana(gloss), "creator": who, "title_id": tid,
                        "title": book_title(page), "publisher": ""})
            break
    return out


BOOK_TITLE = re.compile(r"<title>(.*?)[｜|]", re.S)


def book_title(page):
    """What the shop calls the book, for the note. Empty where the page states no title."""
    m = BOOK_TITLE.search(page or "")
    return _text(m.group(1)) if m else ""


def resolve(pages, name):
    """The reading まんが王国 glosses for this name, or an unresolved answer.

    THE AGREEMENT RULE IS `ndl_reading.settle` AND NOT A SECOND COPY OF IT, for the reason that
    function's docstring gives: whether two records agree on a reading is one fact with one set of
    counter-cases, and the same fact derived twice is this project's most repeated bug.
    """
    return ndl_reading.settle(records(pages, name))


def entry(name, reading, ev, guess, url, reviewed):
    """The curated author entry for one reading weighed off this shop.

    `researched` and never `stated`, so the note has to carry the argument. It names the shop, the
    book the gloss was read on, and what the reading does to the string a reader is being shown.
    None of that is recoverable from the reading afterwards, and somebody re-reading this decision
    needs all of it.
    """
    where = ev["examples"][0][0] if ev.get("examples") else ""
    note = (f"まんが王国 prints this reading in the byline of the {ev['records']} book(s) it sells "
            f"under this name" + (f", e.g. {where!r}" if where else "") + ". The shop is a "
            "retailer and does not say where its kana came from, so this is weighed and not "
            "attributed: what is being recorded is that the shop files the person under these "
            "kana, on the page cited.")
    # A NAME WITH NO READING AT ALL IS THE THIRD CASE, and leaving it out put the word `None` into
    # a sentence somebody has to read. 生肉 is in that state on purpose: セイニク was refuted in
    # August and nothing replaced it, so the record shows the Japanese. There is no string to
    # disagree with and saying so is the whole content of the note.
    if not (guess or "").strip():
        note += (" The record shows no reading at all, so this replaces nothing. Either none was "
                 "ever derived, or the one that was is refuted, and the refutation is on the "
                 "record beside this.")
    elif (guess or "").replace(" ", "") != reading.replace(" ", ""):
        note += (f" It disagrees with {guess!r}, which no source had stated and which a "
                 "morphological analyser assembled, and it is taken over it because a shop filing "
                 "the artist's own books is closer to the name than a tokeniser reading it as "
                 "running text.")
    else:
        note += " It agrees with the reading already on display, which no source had stated."
    return {"reading": reading, "reading_basis": "researched", "reading_source_kind": "derived",
            "reading_note": note, "reading_source": "まんが王国", "reading_url": url,
            "source": "まんが王国", "source_kind": "derived", "source_url": url,
            "reviewed": reviewed}


# The arithmetic `check.py`'s `implausible ruby spans` does, on the spans this reading would
# produce. A run of N kanji needs at least N kana; fewer is not surprising, it is unreadable.
RUBY_KANJI = re.compile(r"[々㐀-䶿一-鿿]")
RUBY_KANA = re.compile(r"[ぁ-んァ-ヺー]")


def alignable(name, reading):
    """Whether this reading can be laid over the name without a run nobody could say aloud.

    WHY A SOURCED READING NEEDS THIS AT ALL. The shop states the sounds and states no boundary, and
    a name whose surface holds a mark between two kanji runs gives the aligner nothing to anchor on
    there. 筋肉☆太郎 is キンニクタロウ, which is right, and the placement came out 筋肉 over き and
    太郎 over んにくたろう. The reading was an improvement and the page was worse for it.

    IT CONSUMES `kana.align` RATHER THAN MODELLING IT (section 3). That function is what build.py
    calls to place a sourced reading, so asking it is asking the thing that will actually run.
    Where it declines to place the reading at all the answer is yes: no ruby is produced, the
    reading and the romanisation are untouched, and there is nothing misplaced to catch.

    THE COUNTER-CASES, which a cruder rule got wrong. The first version refused any reading that
    dropped a mark the surface carries, and that rejects three good readings to catch this one:
    小鬼36℃ is コオニサンジュウロクド and 惚れた女の遺言.mp3 is ホレタオンナノユイゴンドット
    エムピースリー, where the shop is reading the mark ALOUD, which is more than any other source
    here does. What is wrong with 筋肉☆太郎 is not the dropped ☆, it is where the kana landed.
    """
    from names import kana as kana_mod  # noqa: PLC0415
    for base, rt in (kana_mod.align(name, reading) or []):
        if not rt:
            continue
        kanji = len(RUBY_KANJI.findall(str(base)))
        if kanji and len(RUBY_KANA.findall(str(rt))) < kanji:
            return False
    return True


# What this route calls itself in data/names/attempts.yaml. Pass 2 is the bulk-database pass, and
# a shop answering one lookup per name is that shape rather than pass 3's metered search.
SOURCE = "k-manga"
ASK_PASS = 2

# The one status that means the SHOP answered and holds nothing. Everything else is either a page
# that never came back or a refusal of ours, and neither is the shop saying no.
#
# WHY THE LIST IS THIS SHORT. `store.attempt` writes a name off for good: `open_for` will not offer
# it again, which is the property that makes a slow route affordable and is also the property that
# makes a wrong entry unrecoverable without an edit. `no-page` is the dangerous one. It covers a
# request that failed and it covers a name an offline re-read never asked about, and writing either
# down as an absence would teach every later round to skip a name the shop does stock.
ANSWERED_NO = ("no-record",)


def negatives(unresolved):
    """The names this route may write off, out of everything it did not settle.

    Separated from `entries` so the rule can be read and tested on its own. A negative is worth as
    much as a reading here: a name the shop does not stock costs a request to find out and the
    answer does not change, so the round after this one should not pay for it again.
    """
    return sorted(n for n, why in (unresolved or {}).items() if why in ANSWERED_NO)


def cache_name(url, legacy=False):
    """The file one fetched page is kept under, which has to be one file per page.

    THE READABLE PART IS NOT THE KEY. `re.sub(r"[^A-Za-z0-9]", "_", url)[-140:]` is the shape three
    adapters here share, and it is one character away from being wrong: the longest author name in
    the store, 「真夜中ぱんチ」製作委員会, lands on exactly 140 and the truncation has started eating
    the constant prefix. Nothing in the store collides today, measured over all 2,336 names, and a
    name a little longer would, silently: the second fetch would read back the first one's page, and
    a page about somebody else parses to "this person is not credited", which is indistinguishable
    from a person the shop does not stock.

    So the identity is a hash of the whole URL and the readable part is decoration. `legacy` gives
    the old name, because several hundred pages are already on disk under it and re-fetching them
    to rename them would be hours of somebody else's bandwidth for no answer that changes.
    """
    import hashlib  # noqa: PLC0415
    plain = re.sub(r"[^A-Za-z0-9]", "_", url)
    if legacy:
        return plain[-140:] + ".html"
    return plain[-100:] + "-" + hashlib.sha1(url.encode()).hexdigest()[:12] + ".html"


def by_reader_reach(wanted, series):
    """`[(name, current reading)]`, most-credited first, so a stopped run stops in the right place.

    WHY THE ORDER IS PART OF THE MODULE. This run is hours long at one request at a time, so it
    will be stopped and resumed, and whatever it reached is what a reader sees the benefit of.
    Sorted by name, the first hundred are the symbols and the Latin handles, which are the names
    least likely to be in a shop and least often on a page. `curate.todo` orders the title queue the
    same way and for the same reason: a queue picked by hand or by codepoint is a queue nobody can
    defend the shape of.

    Ties break on the name, so two runs over one corpus ask in the same order and the cache from the
    first is worth something to the second.
    """
    import collections  # noqa: PLC0415
    on = collections.Counter()
    for w in series or []:
        for part in re.split(r"\s*/\s*", w.get("author") or ""):
            part = part.strip()
            if part in wanted:
                on[part] += 1
    return sorted(wanted.items(), key=lambda kv: (-on[kv[0]], kv[0]))


def healthy(answered, asked):
    """Whether a run is worth reading, as `(ok, answered, asked)`.

    THE FLOOR IS THERE BECAUSE SILENCE HAS TWO CAUSES, which is the argument
    `openbd_reading.healthy` makes at length and this shares. A shop that is down answers every
    request with an error, settles nothing, and reports a clean run that looks exactly like a batch
    of people it does not stock. Nothing here can tell those apart from the result, so the count of
    pages that came back is asserted instead.
    """
    return (asked == 0 or answered * 2 >= asked), answered, asked


def entries(fetch, wanted, reviewed, depth=DEPTH, order=None):
    """Curated author entries for the names this shop settles. `(entries, unresolved, health)`.

    `fetch(url)` returns a page or an empty string, and is passed in so that the walk can be run
    against a directory of fixtures with no network at all. That split is what lets the walk be
    tested: one search per name, then the books whose own tile credits the person, opened in the
    shop's ranking until `depth` of them have been read.

    `order` is `[(name, guess)]` where the caller has an opinion about which names matter most;
    without one the queue is sorted, which is fine for a run that will finish.
    """
    import urllib.parse  # noqa: PLC0415

    from names.openbd_reading import normalised  # noqa: PLC0415
    out, unresolved = {}, {}
    answered = asked = 0
    for name, guess in (order if order is not None else sorted(wanted.items())):
        asked += 1
        search = fetch(f"{BASE}/search/word/{urllib.parse.quote(name)}")
        if not search:
            unresolved[name] = "no-page"
            continue
        answered += 1
        pages, hit = {}, ""
        for tid in books_for(search, name)[:depth]:
            page = fetch(f"{BASE}/title/{tid}")
            if not page:
                continue
            pages[tid] = page
            hit = hit or author_url(page, name)
        recs = records(pages, name)
        reading, ev = ndl_reading.settle(recs)
        if not reading:
            unresolved[name] = ev["status"]
            continue
        if not ndl_reading.is_kana(reading):
            unresolved[name] = "not-katakana"
            continue
        if normalised(name, reading):
            unresolved[name] = "filing-key-normalised"
            continue
        if not alignable(name, reading):
            unresolved[name] = "ruby-would-be-implausible"
            continue
        out[name] = entry(name, reading, ev, guess,
                          hit or f"{BASE}/title/{recs[0]['title_id']}", reviewed)
    return out, unresolved, healthy(answered, asked)


def main(argv=None):
    import argparse  # noqa: PLC0415
    import datetime  # noqa: PLC0415
    import json  # noqa: PLC0415
    import time  # noqa: PLC0415
    import urllib.request  # noqa: PLC0415

    import yaml  # noqa: PLC0415

    from names.openbd_reading import unsettled_readings  # noqa: PLC0415

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", required=True, help="where fetched pages live; outside the repo")
    ap.add_argument("--offline", action="store_true", help="use only what the cache holds")
    ap.add_argument("--limit", type=int, default=0, help="stop after this many names")
    ap.add_argument("--names", default="data/names/authors.yaml")
    ap.add_argument("--build", default="data/build", help="where the corpus states its works")
    ap.add_argument("--store", default="data/names", help="where the attempts are recorded")
    ap.add_argument("--no-record", dest="record", action="store_false",
                    help="do not write the names the shop answered nothing for")
    ap.add_argument("--reviewed", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)

    cache = pathlib.Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)

    def fetch(url):
        f = cache / cache_name(url)
        old = cache / cache_name(url, legacy=True)
        if not f.exists() and old.exists():
            f = old
        if f.exists():
            t = f.read_text()
            return "" if t.startswith("__ERROR__") else t
        if a.offline:
            return ""
        f = cache / cache_name(url)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                t = r.read(2_000_000).decode("utf-8", "replace")
        except Exception as e:                                                # noqa: BLE001
            t = f"__ERROR__ {type(e).__name__} {e}"
        f.write_text(t)
        time.sleep(PAUSE)
        return "" if t.startswith("__ERROR__") else t

    store = NameStore(a.store)
    wanted = unsettled_readings(a.names)
    # ASKED AND EMPTY IS AS FINAL AS SETTLED. A name this shop has already answered nothing for is
    # not offered again, which is what makes a route costing one request per name affordable to
    # re-run at all.
    skipped = sorted(n for n in wanted if store.tried(n, SOURCE))
    wanted = {k: v for k, v in wanted.items() if k not in set(skipped)}
    series = _population.series()
    order = by_reader_reach(wanted, series)
    if a.limit:
        order = order[:a.limit]
        wanted = dict(order)
    print(f"{len(order)} name(s) with no settled reading, most-credited first; "
          f"asking まんが王国 about each. {len(skipped)} asked before and not asked again",
          flush=True)

    found, unresolved, (ok, answered, asked) = entries(fetch, wanted, a.reviewed, order=order)
    print(f"HEALTH: {answered} of {asked} search page(s) answered")
    if not ok:
        print("Refusing to write: fewer than half the searches came back. That is the shop "
              "unreachable or a run that stopped partway, and neither can be told from a batch of "
              "people it does not stock by looking at the result.")
        return 1
    print(f"{len(found)} settled, {len(unresolved)} not: {sorted(set(unresolved.values()))}")

    # THE NEGATIVE IS THE PART THAT CANNOT BE RECONSTRUCTED. A reading found is in the store for
    # good; a name the shop answered nothing for is a request somebody pays again unless it is
    # written down. attempts.yaml has held that fact for 2,002 names since pass 2 and no reading
    # route has ever added to it.
    wrote = negatives(unresolved)
    if a.record:
        for name in wrote:
            store.attempt(name, ASK_PASS, SOURCE)
        store.compact()
    store.close()
    others = {k: v for k, v in unresolved.items() if v not in ANSWERED_NO}
    print(f"{len(wrote)} name(s) the shop answered nothing for, "
          f"{'written to' if a.record else 'not written to'} {a.store}/attempts.yaml; "
          f"{len(others)} not written off, because a page that never came back and a refusal of "
          f"ours are not the shop saying no")
    print(yaml.safe_dump({"authors": found}, allow_unicode=True, sort_keys=True, width=100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
