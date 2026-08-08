#!/usr/bin/env python3
"""What a second catalogue's date adds to a volume date we already hold, keyed by ISBN.

WHY THIS EXISTS. An ISBN encodes no date. It is a key into a registry that states one, and for a
Japanese book openBD answers from the publisher's own JPRO registration. `openbd/enrich.py` already
asks openBD for every ISBN in the corpus and writes what it gets to `data/source/openbd/`, so the
answers were on disk before this module existed. What was missing is the comparison: `build.py`
tested the two dates for string equality, so a month and a day in that month came out as a
disagreement and were filed beside each other with neither taken.

Measured over the 2,321 ISBN-bearing volumes in `data/source/madb/` on 2026-08-08:

  1,540  openBD states the same month we hold
     26  we hold no date at all and openBD states one
     22  openBD states a day inside the month we hold
      9  openBD states a day in a DIFFERENT month from the one we hold
     10  we hold a day and openBD states a month that is not its month
    253  we hold a day and openBD restates its month
    461  openBD holds no date for the ISBN

PRECISION IS PART OF THE FACT, AND THE STRING IS HOW IT IS CARRIED. A date is `YYYY`, `YYYY-MM` or
`YYYY-MM-DD`, and its length says which. Nothing stores a separate precision field, deliberately:
that would be one fact with two producers, and the pair would drift the first time a value was
edited without its label (STANDING-INSTRUCTIONS §3). `precision` is the one place that reads the
length, so callers stop counting characters. `enrich.pubdate` is the one place that produces the
string, and this module imports it instead of normalising again.

THE DISTINCTION THIS MODULE EXISTS TO DRAW. 2013-05 and 2013-05-24 are one fact at two precisions,
so the day is worth taking and nothing is being decided by taking it. 2013-05 and 2013-06-02 are
two sources saying different things, and the difference is not rounding. Recording a month as
though it were a day would put a false ordering into the volume list; taking a day from a different
month would put a wrong date there. Both populations are counted and only the first is applied.

A DATE THAT DOES NOT SAY WHERE IT CAME FROM. Every date this module hands back arrives with the
relation that justified it, and `build.py` writes the basis onto the volume beside the date. The
vocabulary is `cmoa_volumes.PREFERENCE`'s, so nothing downstream has to learn a second set of names
for the same catalogues.

THE PUBLISHER'S OWN PAGE STATES A DIFFERENT DATE, NOT A FINER ONE. Recorded here because it is the
largest route left and the measurement is what stops it being taken. 644 of the month-precision
volumes carry a 9784758 prefix, which is 一迅社's, and 一迅社 runs a site keyed on the ISBN stating
a day-precise 発売日;
`publisher_dates.ichijinsha_book` already reads it. On a random 60 of them the page answered 59
times, and 57 of those 59 fell in the month BEFORE the one we hold: 一迅社 puts a book on sale
around the 17th and dates the colophon the following month. So the publisher states 発売日 and the
bibliography states 奥付, these are two facts about one book, and applying the publisher's as a
sharpening would move 644 volumes back a month while looking like an improvement in precision. It
is worth capturing as its own field with its own basis, and it is not worth capturing as this one.
The two that did land in the month we hold are the calendar agreeing by accident, not a subset that
can be taken (STANDING-INSTRUCTIONS §2: fix by rule, not by case).

WHAT ELSE WAS ASKED, AND WHAT IT ANSWERED. The MADB bulk release agrees with all 2,286 dates the
corpus already holds and states nothing for the 26 it does not, because `madb/extract.py` read the
corpus off those very records: one fact seen twice, and no second opinion in it. コミックシーモア's
`printed` agrees on all 538 volumes it shares with the corpus, for the same reason at one remove,
since its own dates came from MADB and openBD. Its `delivered` is the day the shop began selling a
file and is not a publication date in either direction; `cmoa_volumes` measures a worst case of 128
months and this module never reads it. BOOK☆WALKER states no ISBN on any of 5,968 volumes read, so
nothing keyed on one can reach it.

Usage:  isbndate.py --report          say what each catalogue on disk adds, and to how many
"""
import argparse
import glob
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from openbd.enrich import pubdate                                              # noqa: E402

# How long an ISO date is at each precision. The string IS the precision; see the module docstring.
_WIDTH = {4: "year", 7: "month", 10: "day"}
_RANK = {"": 0, "year": 1, "month": 2, "day": 3}

# What a comparison can conclude. Named so a count of each can be read without a key.
SILENT = "silent"           # the catalogue holds no date for this ISBN
FILLS = "fills"             # we hold nothing and the catalogue states a date
SHARPENS = "sharpens"       # the catalogue states a finer date inside the one we hold
AGREES = "agrees"           # the same date at the same precision
RESTATES = "restates"       # a coarser date that contains the one we hold
DISAGREES = "disagrees"     # two sources saying different things, at any precision

# The relations that change what we publish. Everything else leaves the held date standing.
TAKEN = (FILLS, SHARPENS)


def precision(date):
    """`year`, `month`, `day`, or `''` for a date that states nothing."""
    return _WIDTH.get(len(str(date or "").strip()), "")


def relation(held, offered):
    """How `offered` stands to `held`, as one of the names above.

    Both are normalised through `enrich.pubdate` first, so a catalogue writing `20130524` and one
    writing `2013-05-24` reach the comparison in the same shape.

    CONSISTENCY IS A PREFIX TEST, and it has to be, because the alternative is arithmetic on dates
    whose precision differs. 2013-05-24 begins with 2013-05, so the two agree as far as the coarser
    one speaks. 2013-06-02 does not, and no amount of rounding makes it.
    """
    held, offered = pubdate(held), pubdate(offered)
    if not offered:
        return SILENT
    if not held:
        return FILLS
    if held == offered:
        return AGREES
    finer = _RANK[precision(offered)] > _RANK[precision(held)]
    fine, coarse = (offered, held) if finer else (held, offered)
    if not fine.startswith(coarse):
        return DISAGREES
    return SHARPENS if finer else RESTATES


def resolve(held, offered):
    """`(date, relation)`: what to publish for this volume, and why.

    The held date stands unless the offer fills a hole or sharpens it. A disagreement is handed
    back as a disagreement and never resolved here: which of two catalogues is right about a book
    is not a question a string comparison can answer, and the count is what makes it visible.
    """
    how = relation(held, offered)
    return (pubdate(offered) if how in TAKEN else pubdate(held)), how


def survey(volumes, offers):
    """`{relation: count}` over volumes carrying an ISBN, against an `{isbn: date}` answer.

    `volumes` is any iterable of dicts holding `isbn` and, where one is known, `published`. Kept
    separate from the file walk so a survey can be run over rows in memory, which is how the tests
    exercise it without a corpus.
    """
    out = {}
    for v in volumes:
        isbn = str((v or {}).get("isbn") or "").strip()
        if not isbn:
            continue
        how = relation(v.get("published"), (offers or {}).get(isbn))
        out[how] = out.get(how, 0) + 1
    return out


def undated_isbn_volumes(works):
    """Volumes that state an ISBN and no date, over built work records.

    THE MEASURE READS THE OUTPUT, NOT THE ROUTE (STANDING-INSTRUCTIONS §14b). A count taken over
    `data/source/madb/` would be blind in the same place the fix is: it would go on reporting 26
    after openBD had answered for all of them, because the answer lands in a different file. Taken
    over the built works it falls when a reader would see a date and rises when one stops reaching
    the page, whichever route filled it.
    """
    return [f"{w.get('work_id')} {v.get('isbn')}"
            for w in (works or [])
            for v in (w.get("volumes") or [])
            if v.get("isbn") and not v.get("published")]


def _corpus(source="data/source"):
    """`[(directory, work_id, volume)]` for every volume on disk that states an ISBN.

    The enrichment layer is skipped because it is the answer side of the comparison, and counting
    it as a holding would have every openBD date agreeing with itself.
    """
    import yaml
    out = []
    for path in sorted(glob.glob(f"{source}/*/*.yaml")):
        doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
        if not isinstance(doc, dict) or doc.get("source") == "openbd":
            continue
        for v in doc.get("volumes") or []:
            if isinstance(v, dict) and v.get("isbn"):
                out.append((pathlib.Path(path).parent.name, doc.get("work_id"), v))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--source", default="data/source")
    ap.add_argument("--openbd", default=None,
                    help="an openBD payload to compare against; defaults to the enrichment layer")
    a = ap.parse_args(argv)

    import json

    import yaml
    offers = {}
    if a.openbd:
        for isbn, rec in json.loads(pathlib.Path(a.openbd).read_text()).items():
            offers[isbn] = pubdate(((rec or {}).get("summary") or {}).get("pubdate"))
    else:
        for path in sorted(glob.glob(f"{a.source}/openbd/*.yaml")):
            for v in (yaml.safe_load(open(path, encoding="utf-8")) or {}).get("volumes") or []:
                if v.get("isbn") and v.get("published"):
                    offers[v["isbn"]] = str(v["published"])

    rows = _corpus(a.source)
    print(f"{len(rows)} volume(s) stating an ISBN; openBD answers for {len(offers)}")
    held = {}
    for _dir, _wid, v in rows:
        held[precision(v.get("published"))] = held.get(precision(v.get("published")), 0) + 1
    for name in ("day", "month", "year", ""):
        if held.get(name):
            print(f"  held at {name or 'no date':10s}: {held[name]}")
    counts = survey([v for _d, _w, v in rows], offers)
    for name in (FILLS, SHARPENS, AGREES, RESTATES, DISAGREES, SILENT):
        print(f"  {name:10s}: {counts.get(name, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
