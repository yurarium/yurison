#!/usr/bin/env python3
"""Where a person's name divides, taken from the author heading on a National Diet Library record.

WHY THIS EXISTS. A romanisation is spelled out of the reading, so a reading with no space in it
romanises as one word: 太陽まりい is filed タイヨウマリイ by the media-arts catalogue and comes out
`Taiyōmarii`. The person is 太陽 まりい. 459 author records were in that state, and no rule inside
this project can fix it, because the surface of a Japanese name carries no boundary and neither
does an undivided reading. NAMES-PLAN records two attempts at deriving one and why both were
refused. A division has to be STATED.

NDL states it, in a field nothing here was reading. A record page prints 著者標目 beside
タイトルよみ, and the heading is a cataloguing authority's own division of the person:

    美術制作者 ： 美鈴, ちょこ  ミレイ, チョコ  ( 034528963 )典拠

The surface divided, then the reading divided, then the authority record's number. `ndl_books.py`
has been parsing the same pages for a title's reading since 2026-08-08 and walked past this field,
which is the shape STANDING-INSTRUCTIONS §14c is about: the route was open the whole time and one
use of it had been mistaken for all of them.

WHAT IS TAKEN, AND IT IS ONLY THE OFFSETS. `boundary.carry` puts the heading's division onto the
kana we already hold, and refuses unless the two strings correspond character for character. So a
heading that is about somebody else, or that spells the name with different kana, yields nothing
rather than a boundary in the wrong place. The reading published is still ours; NDL supplies where
it breaks.

WHY THE NAME MUST MATCH BEFORE THE READING IS READ. The heading is one run of text and splitting it
into a name and a reading by eye is the guess this module exists to avoid: `藤沢 チヒロ` ends in
katakana and so does its reading. The split is therefore not guessed at all. The name sits in its
own anchor on the page, the reading is the text between that anchor and the authority number, and
the caller says which person it is asking about, so a heading whose name is not the name we asked
about is discarded before its reading is looked at.

WHAT SILENCE MEANS. Nothing about the person. NDL catalogues on deposit, so a web-only artist with
no printed book has no record and no heading, and most of this corpus is web serialisation. That is
`no-heading`, and it leaves the name romanised as one word with the mark NAMES-PLAN §5d puts on it.

WHAT THIS DOES NOT DO. Fetch. `ndl_books.py` owns the one path this project may ask NDL for, with
robots.txt's disallow of `/api` enforced in `build_url` rather than remembered, and its cache and
its pacing. This module is handed a page and answers about it, which is also what lets its test run
with no network.
"""
import html as _html
import re
import sys
import pathlib
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from facts import division as boundary                                                    # noqa: E402

# The heading field, and the one this module reads. `著者標目` is the person; `タイトル` and
# `著者` are `ndl_books.py`'s business.
HEADING = "著者標目"

# One heading ends where its authority button begins. The pages print `典拠` as the button's label
# after every heading, including the last, so splitting on it yields one chunk per person.
AUTHORITY = "典拠"

_A = re.compile(r"<a\b[^>]*>(.*?)</a>", re.S)
_TAG = re.compile(r"<[^>]+>")

# A birth year, which NDL puts on both halves of a heading: `南木, 義隆, 1991- ナンボク, ヨシタカ,
# 1991-`. It is cataloguing apparatus and not part of anybody's name, and left in it would make the
# reading disagree with ours and the whole heading yield nothing.
_YEAR = re.compile(r"[,、]?\s*\d{4}\s*-\s*\d{0,4}\s*$")

# What a reading may be made of. Katakana, the marks that divide one, and nothing else. This is the
# second half of the safety: the name must be the one asked about AND the rest must look like a
# reading, so a heading whose markup ran together into one string cannot supply a division.
_KATAKANA = re.compile(r"[ァ-ヺーゝゞ][ァ-ヺーゝゞ,、\s　・･]*$")


def _text(fragment):
    """One HTML fragment as the text a reader sees, with markup, comments and entities gone."""
    return re.sub(r"\s+", " ", _html.unescape(_TAG.sub("", fragment or ""))).strip()


def _year_off(s):
    return _YEAR.sub("", str(s or "")).strip().rstrip(",、").strip()


def _spaced(s):
    """A heading's separator written as the space every other source here writes it with.

    THE COMMA IS THE WHOLE POINT OF THE FIELD and it is the one character `boundary.py` does not
    know about: `cuts` divides on spaces and interpuncts, so `タイヨウ, マリイ` read literally states
    no division and `太陽, まりい` does not compare equal to our 太陽まりい. Cataloguing uses the
    comma as its separator and nothing else, so it is turned into one here, at the edge that knows
    the format. Teaching every other module a rule that is only true of NDL would put NDL's
    cataloguing convention into code that has never met it.
    """
    return re.sub(r"[\s　]+", " ", re.sub(r"[,、]", " ", str(s or ""))).strip()


def field(page, label=HEADING):
    """The raw HTML of one `<dd>`, by the `<dt>` beside it. `""` where the page has no such field.

    HTML, because the structure is what makes the split safe: the name is inside an anchor and the
    reading is not, and a page rendered down to text loses the one thing that says where one ends.
    `ndl_books.fields` returns text and is right to, since every field it reads is a single value.
    """
    pat = re.compile(r"<dt[^>]*>((?:(?!</dt>).)*)</dt>\s*<dd[^>]*>(.*?)</dd>", re.S)
    for dt, dd in pat.findall(page or ""):
        if _text(dt) == label:
            return dd
    return ""


def headings(page):
    """`[(name, reading)]`, one per person the record's author heading names.

    The reading is `""` where the heading states none, which is the ordinary case for a one-element
    name: 缶乃 is filed カンノ and there is nothing to divide.
    """
    out = []
    for chunk in field(page).split(AUTHORITY):
        m = _A.search(chunk)
        if not m:
            continue
        name = _year_off(_text(m.group(1)))
        # Everything between the name's anchor and the authority number's anchor. The number is a
        # link too, so the reading is what precedes the next `<a`, less the bracket that opens it.
        rest = chunk[m.end():]
        nxt = rest.find("<a")
        reading = _text(rest if nxt < 0 else rest[:nxt]).rstrip("( ").strip()
        reading = _year_off(reading)
        if name:
            ok = bool(_KATAKANA.fullmatch(reading or ""))
            out.append((_spaced(name), _spaced(reading) if ok else ""))
    return out


def stated(page, name):
    """NDL's divided reading for `name` on this page, or `None`.

    The comparison is `boundary.flat`, so a heading writing `美鈴, ちょこ` answers for our 美鈴ちょこ
    and a heading about somebody else does not answer at all. Where two headings on one page give
    the same person two different divisions the page states none, which is `boundary.settle`'s rule
    and is not decided again here.
    """
    want = boundary.flat(name)
    got = {r for n, r in headings(page) if r and boundary.flat(n) == want}
    return sorted(got)[0] if len(got) == 1 else None


def divide(page, name, reading):
    """Our own `reading`, divided where this page's heading divides the same person. `None` else.

    THE KANA STAY OURS. NDL transcribes に as ニ and をを as オオ, and a heading is a filing form
    before it is a pronunciation, so taking its string whole would republish somebody's name with
    different kana in it. `boundary.carry` takes the offsets and refuses where the two do not
    correspond, which is the same rule `openbd_reading.boundary_entries` applies to a collation key.
    """
    donor = stated(page, name)
    return boundary.carry(reading, donor) if donor else None


def authority_url(page, name):
    """The authority record the heading cites for this person, for the entry to point at.

    A DIVISION HAS TO NAME WHERE IT CAME FROM (`curate.py`), and the record page is about a BOOK,
    so citing it alone would leave a reader hunting a name in a bibliographic table. The authority
    id is the catalogue's identifier for the person, printed beside every heading.
    """
    want = boundary.flat(name)
    for chunk in field(page).split(AUTHORITY):
        anchors = _A.findall(chunk)
        if len(anchors) < 2 or boundary.flat(_spaced(_year_off(_text(anchors[0])))) != want:
            continue
        rid = _text(anchors[1])
        if re.fullmatch(r"\d+", rid):
            return f"http://id.ndl.go.jp/auth/entity/{rid}"
    return None


def search_url(name):
    """Where a person's headings are listed, on the search path `ndl_books.build_url` permits.

    Built through that function and not assembled here, so the one place that knows which NDL paths
    robots.txt allows stays the only place that can produce a URL for this host.
    """
    from names import ndl_books
    return ndl_books.build_url(ndl_books.SEARCH, cs="bib",
                               **{"q-author": f'"{name}"'})


def entry(page, name, reading, reviewed, record=None):
    """A `curated.yaml` author entry carrying this heading's division, or `None`.

    `reading_basis: surface` and not `stated`, for the reason `openbd_reading.boundary_entries`
    gives: the kana published are the name's own and only the division is NDL's. Saying `stated`
    would put a national catalogue's name on kana it did not supply.

    THE ONE PLACE AN ENTRY IS BUILT. `main` fetches and calls this; nothing assembles a second
    version of the same dictionary, so the note a reader reads is the note the test pins.
    """
    got = divide(page, name, reading)
    if not got:
        return None
    donor = stated(page, name)
    where = f" on record {record}" if record else ""
    return {"reading": got,
            "reading_basis": "surface",
            "reading_source_kind": "derived",
            # WHERE THE DIVISION CAME FROM, IN THE FIELD THAT HOLDS THAT FACT. This entry once said
            # it in `reading_note` alone, which is prose: `boundary.fill` writes `reading_boundary`
            # for the same fact, so the store had two slots for one thing and 212 records filled
            # only the unqueryable one. The note below still carries the argument, which is what a
            # note is for and what no field can hold.
            "reading_boundary": f"the National Diet Library's author heading{where}",
            "reading_note": (f"The National Diet Library's author heading{where} divides this "
                             f"person as {donor!r}. The kana here are the name's own surface and "
                             f"only the division is taken, since a heading is a filing form first: "
                             f"it folds the kana that sort together. It divides {reading!r}, which "
                             f"stated no division at all."),
            "source": "ndlsearch.ndl.go.jp",
            "source_url": authority_url(page, name) or search_url(name),
            "source_kind": "national-library",
            "reviewed": reviewed}


# The label this route records its negatives under in data/names/attempts.yaml. Its own, and not
# `ndl_books.SOURCE`: a work NDL holds no record of and a person NDL states no heading for are two
# different absences, and sharing a label would let one answer for the other.
SOURCE = "ndl-heading"


def sweep(names, get, max_records=3):
    """Ask NDL to divide each of `{name: reading}`. `{name: (page, rid)}` and why each other failed.

    THE PAGE COMES BACK RATHER THAN THE ANSWER, so `entry` stays the only thing that turns a page
    into a record. A sweep that built its own entry would be the second producer §3 is about.

    `get(url)` returns a page, `None` where NDL says it holds nothing, and raises `net.Refused`
    where it will not say. That third case is why it is a parameter: a wall of 503s must leave the
    ledger untouched, and a function that returned None for both would write every refusal down as
    an absence and never ask again.

    THE SEARCH IS BY AUTHOR AND NOT BY TITLE, which is the difference between this and
    `ndl_books.py`. That module knows which book it wants and checks the record states the same
    title. This one wants the PERSON, so any record they are credited on will do and the check is
    that the heading names them: `いがらしゆみこ` searched by author returns records headed
    `五十嵐 由美子`, a different spelling of a name read the same way, and `stated` refuses it.
    """
    from names import ndl_books
    settled, refused = {}, {}
    for name, reading in names.items():
        if not reading:
            refused[name] = "no-reading"
            continue
        try:
            page = get(search_url(name))
        except Exception as e:                                             # noqa: BLE001
            refused[name] = f"fetch-failed: {e}"
            continue
        if page is None:
            refused[name] = "no-record"
            continue
        ids = ndl_books.record_ids(page)[:max_records]
        if not ids:
            refused[name] = "no-record"
            continue
        why = "no-heading"
        for rid in ids:
            try:
                rec = get(ndl_books.record_url(rid))
            except Exception as e:                                         # noqa: BLE001
                why = f"fetch-failed: {e}"
                continue
            if rec is None:
                continue
            if divide(rec, name, reading):
                settled[name] = (rec, rid)
                break
            if stated(rec, name):
                # A heading that names this person and states no division of them. Different from
                # no heading at all, and the more informative answer: the catalogue has looked at
                # this name and files it as one element.
                why = "heading-states-no-division"
        if name not in settled:
            refused[name] = why
    return settled, refused


def main(argv=None):
    """Ask NDL where each author name on stdin divides, and print entries for `curated.yaml`.

    AN ENTRY IS PRINTED AND NOT STORED, the same rule `ndl_books.main` follows: the extraction is
    mechanical and the decision that this heading is about this person is a reviewer's.

    THE NEGATIVE IS STORED, because it cost a request. A name NDL states no heading for goes to
    `data/names/attempts.yaml` and is not asked about again until the absence expires, which is
    what keeps a re-run from paying for the whole residue a second time.
    """
    import argparse
    import json
    import urllib.parse

    import yaml

    import net
    from names import ndl_books
    from names import store as store_mod

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--names", help="a file of Japanese author names, one per line; stdin otherwise")
    ap.add_argument("--cache", default=str(ndl_books.DEFAULT_CACHE))
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--pause", type=float, default=ndl_books.PAUSE)
    ap.add_argument("--retries", type=int, default=net.ATTEMPTS)
    ap.add_argument("--max-records", type=int, default=3)
    ap.add_argument("--store", default="data/names")
    ap.add_argument("--authors", default="data/names/authors.yaml")
    ap.add_argument("--no-store", action="store_true")
    ap.add_argument("--recheck-after", type=int, default=ndl_books.RECHECK_DAYS)
    ap.add_argument("--reviewed", default=store_mod.today())
    a = ap.parse_args(argv)

    # Owed to this host and not to the other 26, exactly as `ndl_books.main` sets it.
    net.set_pause(urllib.parse.urlparse(ndl_books.HOST).netloc, a.pause)

    store = (yaml.safe_load(pathlib.Path(a.authors).read_text()) or {}).get("names") or {}
    src = pathlib.Path(a.names).read_text() if a.names else sys.stdin.read()
    wanted = [n.strip() for n in src.splitlines() if n.strip()]
    st = None if a.no_store else store_mod.NameStore(a.store)
    todo = {n: (store.get(n) or {}).get("reading") or ""
            for n in wanted if st is None or not st.tried(n, SOURCE, a.recheck_after)}
    print(f"{len(todo)} name(s) to ask NDL about; {len(wanted) - len(todo)} skipped, already "
          f"answered nothing within {a.recheck_after} days", file=sys.stderr, flush=True)

    cache = None if a.no_cache else a.cache

    def get(url):
        return net.body(net.fetch(url, cache, max_age_days=a.recheck_after, attempts=a.retries))

    settled, refused = sweep(todo, get, a.max_records)
    out = {name: entry(page, name, todo[name], a.reviewed, rid)
           for name, (page, rid) in sorted(settled.items())}
    recorded = 0
    for name, why in sorted(refused.items()):
        # A REFUSAL IS NEVER WRITTEN DOWN. `net.body` raises on a 503 so that a host declining to
        # answer cannot be recorded as a host with nothing to say.
        if st is not None and not why.startswith("fetch-failed") and why != "no-reading":
            st.attempt(name, None, SOURCE)
            recorded += 1
    if st is not None:
        st.compact()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"{len(settled)} divided, {len(refused)} not; {recorded} absence(s) recorded",
          file=sys.stderr)
    for why in sorted({w.split(":")[0] for w in refused.values()}):
        print(f"  {sum(1 for w in refused.values() if w.split(':')[0] == why):4}  {why}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
