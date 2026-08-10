#!/usr/bin/env python3
"""Volume histories and first publication dates for the コミックシーモア rows in the queue.

WHY THIS EXISTS. `data/queue/admitted.yaml` holds 1,844 works admitted from cmoa's 百合・GL shelf on
the designation test, and not one of them can become a record: DEFINITIONS §6 makes
`first_publication` the inclusion test itself, and a shelf row states a title, an author, a
publisher and an imprint and no date at all. This reads the work page each row already points at,
which states the volume list and, for a volume that was printed, an ISBN and 出版年月.

THE ISBN IS THE WHOLE GAME, AND THE PAGE IS HOW YOU GET IT. Measured on a random 80 of the 1,844:

  出版年月, the shop stating the volume's publication month, is present on 8. It costs nothing
  beyond the page already being fetched and it is the only route that works without an ISBN.

  An ISBN is stated on 23, and an ISBN is worth having: measured against the 410 distinct ISBNs
  the first 584 work pages actually produced, openBD answers with a date for 275 of them and the
  MADB 単行本 dataset for 349. Together they answer 371, which is 90%. MADB adds 96 that openBD
  has no record of and openBD adds 22 that MADB does not, so both are worth running and neither
  contains the other.

  So the page fetch is worth its cost, because the page is the only place the ISBN is written:
  the shelf listing does not carry one. What the page cannot supply, nothing downstream can
  invent. An ISBN is stated only where a volume was printed, and 754 of the 1,844 rows come from
  ナンバーナイン and クロスフォリオ出版, digital distributors whose pages carry no ISBN and no
  出版年月 at all. On the random sample that is 29% of the shelf reachable and 71% not, and no
  amount of further fetching moves it.

配信開始日 IS NOT A PUBLICATION DATE, IN EITHER DIRECTION, and that is measured rather than
assumed. It is the day コミックシーモア began selling the file, a fact about the shop's catalogue in
the same class as the platform import stamp that once had ハロー、メランコリック！ reading dormant
off the day 講談社 loaded it. Across the 353 volumes where the shop states both a print date and a
delivery date:

  154 delivered BEFORE the print date, 51 in the same month, 22 one or two months after,
  23 later that year, 58 one to three years after, and 45 more than three years after.

The extreme is 一迅社 title 153015, printed 2007-11-01 and delivered 2018-07-18, a hundred and
twenty-eight months. So it is not a publication date, it is not an upper bound on one, and it is
not a lower bound either. A capture that filled the date field from it would put a decade's error
into the field that decides whether a work is in scope, and every row would look answered.

  IT IS THE DATE FOR THE DIGITAL-ONLY ROWS, REVERSED BY THE PROJECT OWNER ON 2026-08-08. What
  stands above is the measurement and it is untouched: everything in it is about volumes stating
  BOTH dates, and where a print date exists the print date wins and `delivery.promote` refuses the
  delivery date on sight. What changed is the case with nothing else, which this module argued
  against on these grounds:

    cmoa's own description of #ミカちゃんともなちゃん says the file is the ebook edition of the
    author's 個人誌, so the shop states that an earlier publication exists and does not say when.

  The argument was that this made the date a stand-in for something better. It does not, and the
  reason is now in DEFINITIONS §6: publication for a doujinshi is a nebulous idea to begin with,
  since the first offering is usually a day at an event and no register records it the way a 奥付
  records a printing. So an earlier EDITION existing does not mean an earlier DATE exists, and this
  module was treating a value that is undefined as one that was being withheld. Measured over the
  cache, the shop states an earlier edition on 174 of these pages and says the file is itself a
  doujinshi on 79.

  What the rows now carry is the delivery event, said as itself: `first_publication_basis` reads
  `shop-delivery-date` and `first_publication_event` reads `shop-delivery`. Nothing calls it an
  estimate of an earlier publication, because calling it one asserts the very thing §6 says is
  usually absent. Absence of a date is still a state (STANDING-INSTRUCTIONS §5) and
  `shop-delivery-date-refused` is where a row lands that has a printing to defer to instead.

WHAT A DATE HERE BOUNDS. A volume's publication is not a work's first publication where the work
was serialised in a magazine first; the tankōbon follows the chapters. So `first_publication_date`
is volume 1's, an upper bound for a serialised work and exact for one that was not serialised. It
is written as evidence toward §6 rather than as a settled answer to it.

THE FIELD NAMES ARE data/queue/bookwalker-volumes.yaml's, where the two shops mean the same thing.
The other half of this queue is the same problem at a different shop, and whatever promotes these
rows should read one vocabulary. `first_publication_basis` is where they differ, because the two
shops are silent in different ways and the reason for each silence is the useful part.

Usage:  cmoa_volumes.py                     capture work pages, resuming from the output file
        cmoa_volumes.py --limit 50          the first 50 works still outstanding
        cmoa_volumes.py --madb              date the captured ISBNs from MADB, no network
        cmoa_volumes.py --openbd            and from openBD, for what MADB does not hold
        cmoa_volumes.py --delivery          take the delivery date where nothing else answers, and
                                            read each cached page for what the shop says its
                                            edition is. No network; the pages are already on disk
        cmoa_volumes.py --volumes           open each printed volume's own page for its ISBN
        cmoa_volumes.py --report            read the output and print what it holds

FOUR STAGES, EACH RESUMABLE FROM THE OUTPUT FILE. The work-page pass is one request per work and
is what produces the ISBNs; `--madb` costs no requests at all; `--openbd` costs one per hundred
ISBNs and adds what MADB does not hold; the volume pass is one request per volume and fills out a
volume history without changing any work's first publication. Running the first two is the whole
of what §6 needs.
"""
import argparse
import datetime
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import blurbdate                                                               # noqa: E402
import cmoa                                                                    # noqa: E402
import delivery                                                                # noqa: E402
import paths                                                                   # noqa: E402
import shelfingest                                                             # noqa: E402
import yaml                                                                    # noqa: E402
from madb import isbn_dates                                                    # noqa: E402
from names import openbd_reading                                               # noqa: E402
from openbd import enrich                                                      # noqa: E402

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
# cmoa's robots.txt disallows account, basket and reader paths, and /search/result/. None is
# touched here: /title/<id>/ is the work page and it is allowed.
PAUSE = 1.6
TIMEOUT = 40
# cmoa lists 20 volumes to a page in easy mode. The cap is a guard against a paging bug spending a
# run on one work, not a statement about how long a series can be: 40 pages is 800 volumes.
MAX_LIST_PAGES = 40

# THE FLOOR, AND WHY IT IS A SHARE. A batch loop that dies halfway comes back with a handful of
# rows, writes them, and reads as a quiet day rather than as a fetch that stopped. So the measure
# is the SHARE of what was asked that came back usable, taken over a sliding window so a run that
# goes bad in the middle stops in the middle instead of at the end.
#
# The counter-case, so this is not lowered later to make a run pass: a window of works cmoa has
# delisted would legitimately be all 404, and the answer to that is to look at which ids went
# missing rather than to move the floor. On the measured sample every one of 80 pages parsed.
FLOOR = 0.5
WINDOW = 40


def outstanding(wanted, doc):
    """Which ids still need fetching: asked for, and not already answered or excluded.

    Resumption is computed from the OUTPUT rather than tracked in a side file. A cursor and a
    document are the same fact in two places, and they part company the first time a run is killed
    between writing one and the other.
    """
    held = set(doc.get("works") or {}) | set(doc.get("excluded_ids") or [])
    return [i for i in wanted if i not in held]


def fold_in(doc, rows):
    """Add rows to the document, keeping every work the rows do not mention.

    The merge semantics are `cmoa.merge`'s, not a second copy of them. Rebuilding a file from only
    what the current run fetched is the failure this project has met three times, and it is silent:
    the file is well-formed, smaller, and says nothing about what went missing.
    """
    key = "cmoa_title_id"                    # cmoa.merge's own name for the id; not stored here
    held = [dict(w, **{key: i}) for i, w in (doc.get("works") or {}).items()]
    inner, added = cmoa.merge({"titles": held},
                              [dict(r, **{key: r["shop_id"]}) for r in rows])
    doc = dict(doc)
    doc["works"] = {r[key]: {k: v for k, v in r.items() if k != key} for r in inner["titles"]}
    return doc, added


def usable(rec):
    """Whether a parsed page is worth keeping.

    A work page that lists no volume is not a thin answer, it is a page that did not parse: cmoa
    lists at least the volume it is showing. Testing for the specific bad value rather than for an
    exception is the point (STANDING-INSTRUCTIONS §4). A stylesheet change returns 200, a body,
    and nothing the parser recognises, which is exactly what a floor has to catch.
    """
    return bool(rec) and bool(rec.get("volumes"))


def healthy(usable_count, asked):
    """Whether a window of results is worth writing, as `(ok, usable, asked)`."""
    return (asked == 0 or usable_count >= asked * FLOOR), usable_count, asked


def first_publication(rec):
    """Volume 1's publication and the basis for it, as `(date, basis)`.

    THE BASIS IS RETURNED EVEN WHEN THE DATE IS NOT, because "no date" has four causes here with
    four different remedies, and a null with no reason beside it collapses them into one. An ISBN
    no catalogue holds wants another catalogue tried; a page with no ISBN will never have one, so
    nothing keyed on ISBN can ever answer it and the remedy is a source that is not a shop.

    Which catalogue's date is in the field is `PREFERENCE`'s decision and is recorded on the volume
    as `printed_basis`, so this function reports rather than re-deciding it. The vocabulary matches
    `data/queue/bookwalker-volumes.yaml` where the two shops mean the same thing, so that whatever
    promotes these rows reads one set of names rather than two.
    """
    vols = rec.get("volumes") or []
    if not vols:
        return None, "no-volumes-found"
    first = next((v for v in vols if v.get("volume") == 1), None)
    if first is None:
        return None, "no-first-volume-listed"
    if first.get("printed"):
        return first["printed"], first.get("printed_basis") or "shop-publication-month"
    if first.get("isbn"):
        return None, "isbn-stated-not-catalogued"
    # A PRINTING THE SHOP STATED IN WORDS. `read_editions` puts it on the row from the work page's
    # description, so it is absent until that stage has run. It sits BELOW the catalogue branches
    # above on purpose: a bibliography holds a record and a blurb holds a sentence, so where both
    # exist the record answers. It sits ABOVE the delivery date because it is a printing, and a
    # printing always wins (adapters/blurbdate.py, and the owner's ruling of 2026-08-08).
    stated = rec.get("edition_date")
    # THE DELIVERY DATE, WHICH THIS MODULE SPENT ITS DOCSTRING REFUSING. The owner reversed the
    # digital-only half of that refusal on 2026-08-08 (DEFINITIONS §6, docs/GAPS.md), and
    # `delivery.promote` is where the rule now lives so the print-date refusal has one home. It is
    # stricter than the branch above: this function reads volume 1 and `promote` reads every volume,
    # so a work whose fifth volume states a printing is refused here even though volume 1 says
    # nothing. The old basis name `shop-delivery-date-only` said the date was unusable and is gone.
    date, refused = delivery.promote(vols, stated_print=stated)
    if refused == delivery.REFUSED_BLURB:
        return stated, blurbdate.BASIS
    if date:
        return date, delivery.BASIS
    if first.get("delivered"):
        return None, "shop-delivery-date-refused"
    return None, "no-date-stated"


def record(parsed, shelf_row):
    """One work page as the row that goes in the file, or None where a designation excludes it.

    The designation test is `shelfingest.designated`, run again HERE, because a work page states a
    genre and an imprint that the listing row did not. A row that entered the queue clean and turns
    out on its own page to be filed アダルト has to leave, and it leaves as a count.
    """
    fields = {"genre": " ".join(parsed.get("genres") or []),
              "imprint": parsed.get("imprint"), "publisher": parsed.get("publisher"),
              "title": " ".join(v.get("name") or "" for v in parsed.get("volumes") or [])}
    why = shelfingest.designated(fields)
    if why:
        return None, why
    marker = next((m for v in parsed.get("volumes") or []
                   for m in [cmoa.censored_marker(v.get("name"))] if m), None)
    if marker:
        return None, f"a volume is titled as a censored edition ({marker})"

    vols = []
    for v in parsed["volumes"]:
        row = {"volume": v["volume"], "title": v["name"], "url": v["url"]}
        if v["volume"] == parsed.get("detail_volume"):
            row["isbn"] = parsed.get("isbn")
            # `printed` and `delivered` are bookwalker-volumes.yaml's names for the same two facts:
            # the print edition's publication, and the day the shop began selling the file.
            row["printed"] = parsed.get("published")
            row["printed_basis"] = "shop-publication-month" if parsed.get("published") else None
            row["delivered"] = parsed.get("distribution_started")
        vols.append(row)
    out = {"shop_id": parsed["cmoa_title_id"],
           "url": f"{cmoa.BASE}/title/{parsed['cmoa_title_id']}/",
           "shelf_title": (shelf_row or {}).get("title"),
           "publisher": parsed.get("publisher"), "imprint": parsed.get("imprint"),
           "shop_genres": parsed.get("genres"), "completed": parsed.get("completed"),
           "volumes_stated": parsed.get("volumes_stated"), "volumes": vols}
    return settle(out), None


def settle(w):
    """Fill a work's derived counts and its first publication, from the volumes it holds.

    Called on capture and again after the openBD join, so the two never state different answers
    from the same volumes. Deriving `first_publication_date` in one place and the counts in another
    is this project's most repeated bug (STANDING-INSTRUCTIONS §3).
    """
    vols = w.get("volumes") or []
    date, basis = first_publication(w)
    w["volumes_found"] = len(vols)
    w["dates_stated"] = sum(1 for v in vols if v.get("printed"))
    w["isbns_stated"] = sum(1 for v in vols if v.get("isbn"))
    w["first_publication_date"] = date
    w["first_publication_basis"] = basis
    # The page the date was read off, where the route that supplied it reads one page per book. A
    # bulk catalogue has no such page and leaves this null. The null is an answer: the basis names
    # the dataset and the dataset version is recorded with the record.
    first = next((v for v in vols if v.get("volume") == 1), None)
    w["first_publication_source"] = (first or {}).get("printed_source") if date else None
    # A cmoa publisher is a Japanese company selling a Japanese print edition, so a date from this
    # route carries JP. The venue is the publisher and NOT the magazine: this shop never names a
    # magazine, and a tankōbon publisher is not the venue of a serialised work's first chapter.
    w["first_publication_country"] = "JP" if date else None
    w["first_publication_venue"] = (w.get("publisher") or None) if date else None
    if basis == blurbdate.BASIS:
        # WHICH PAGE STATES THE DATE. The sentence sits in the description box on the work page,
        # which is volume 1's own page on this shop: `record` gives volume 1 the work URL and every
        # later volume a `/vol/n/` address under it. So citing the work page cites the page the
        # sentence is on, and a reader can open it and read the shop's words for themselves.
        w["first_publication_source"] = w.get("url")
        # WHICH CLAIM THE SHOP MADE. 発行 and 初出 are different assertions about different events
        # and the row has to say which, for the same reason a delivery date has to say it is one.
        w["first_publication_event"] = w.get("edition_date_event")
        w.pop("first_publication_followup", None)
    elif basis == delivery.BASIS:
        # WHICH VOLUME'S PAGE STATES THE DATE. A delivery date is read off a volume page and not
        # from a catalogue, so unlike the branch above there IS a page to cite, and the volume
        # holding the earliest date is the one that states it. `first_publication_source` is that
        # page, so a reader can check the number against the shop.
        _early = min((v for v in vols if v.get("delivered")),
                     key=lambda v: str(v["delivered"])[:10])
        w["first_publication_source"] = _early.get("url")
        w["first_publication_event"] = delivery.EVENT
        # THE FOLLOW-UP STATE, WHICH IS NOT A QUEUE LENGTH. `edition_statement` is filled by
        # --delivery from the cached page and is absent until that has run, so a row with no
        # statement sorts to `unclassified` and is counted as unsorted instead of as outstanding.
        w["first_publication_followup"] = delivery.followup(
            w.get("edition_statement"),
            self_published=delivery.self_published(w.get("author"), w.get("publisher"),
                                                   w.get("imprint")))
    else:
        for k in ("first_publication_event", "first_publication_followup"):
            w.pop(k, None)
    return w


def fetch(url, cache, offline=False):
    """One page, from the cache where it is held. Returns the body or None, never raising."""
    cache = pathlib.Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / (url.replace("https://www.cmoa.jp/", "").replace("/", "_").replace("?", "_")
                 .replace("&", "_").replace("=", "-") + ".html")
    if f.exists():
        return f.read_text(encoding="utf-8", errors="replace")
    if offline:
        return None
    time.sleep(PAUSE)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError) as e:                  # noqa: BLE001
        print(f"    {url}: {type(e).__name__}: {e}", flush=True)
        return None
    f.write_text(body)
    return body


def capture_one(title_id, cache, offline=False):
    """A work page, following the volume list onto further pages where the shop says there are."""
    body = fetch(cmoa.work_url(title_id), cache, offline)
    if body is None:
        return None
    parsed = cmoa.work(body, title_id)
    stated = parsed.get("volumes_stated") or 0
    page = 1
    while parsed["volumes"] and len(parsed["volumes"]) < stated and page < MAX_LIST_PAGES:
        page += 1
        more = fetch(f"{cmoa.BASE}/title/{title_id}/?page={page}&order=up&disp_mode=easy",
                     cache, offline)
        if more is None:
            break
        got = cmoa.volumes(more, title_id)
        known = {v["volume"] for v in parsed["volumes"]}
        added = [v for v in got if v["volume"] not in known]
        if not added:
            break
        parsed["volumes"] += added
    return parsed


HEADER = """\
# Volume histories for the コミックシーモア rows of data/queue/admitted.yaml. NOT RECORDS.
#
# Keyed by `shop_id`, which is the cmoa title id the admitted row already carries, so this joins
# back without matching a title against a title. Still data/queue/: promotion into data/source/ is
# a separate step and a decision this file does not make.
#
# WHAT THE SHOP STATES.
#   delivered   配信開始日, the day コミックシーモア began selling the file. Present on every volume
#               page. It is a fact about the shop's stock and not the same fact as a printing: it
#               runs years late on a digitised back catalogue, 双葉社 stating 2007年12月 for a file
#               the shop began selling on 2012-10-05. Where a print date exists the print date is
#               the work's and this is not evidence about it. Where none exists anywhere, this is
#               the date the row carries, ruled by the project owner on 2026-08-08.
#   printed     出版年月, the print edition's publication month, or the date openBD holds against
#               the volume's ISBN. This IS a publication of the work and the only field here that
#               answers DEFINITIONS §6. Absent on the digital distributors, which are most of this
#               shelf.
#   isbn        Stated for a volume that was printed, in ten or thirteen digits; converted to
#               thirteen here because that is the form openBD answers.
#
# WHAT first_publication_basis MEANS.
#   madb-tankobon              the 文化庁メディア芸術データベース 単行本 dataset holds a date
#                              against the volume's ISBN. Sourced from NDLサーチ, so this is the
#                              national bibliography.
#   openbd-registration        openBD holds one and MADB does not
#   publisher-own-page         the book's own publisher states 発売日 on its own site.
#                              adapters/publisher_dates.py, and `first_publication_source` is the
#                              page it was read off.
#   books-or-jp-registration   出版書誌データベース holds 発行年月日 and no publisher page does.
#                              adapters/booksorjp.py. Kept apart from the line above so a reader
#                              can tell a first-hand statement from an aggregator's record and so
#                              these rows can be replaced if a publisher page appears.
#   shop-publication-month     the shop states 出版年月 and neither catalogue holds the ISBN
#   isbn-stated-not-catalogued an ISBN is stated and no catalogue asked has a record of it
#   shop-delivery-date         the shop states only the day it began delivering the file, on every
#                              volume of the work. No print edition, so no ISBN will ever exist and
#                              no ISBN route can help. The date names the delivery and is exactly
#                              true of it. adapters/delivery.py holds the rule and the wording.
#   shop-blurb-print-date      the shop's own description states when the doujin edition this file
#                              was made from was published. That is a printing, so it answers ahead
#                              of the delivery date and behind any catalogue record.
#                              adapters/blurbdate.py holds the rule and the wording.
#   shop-delivery-date-refused a delivery date is stated and another volume states a printing, so
#                              the printing answers and this one is not evidence about it. Nothing
#                              in this capture is in that state, and the term exists so that a row
#                              which reaches it is visible instead of silently undated.
#   no-date-stated             the page carries no date of any kind
#   no-volumes-found           the page listed nothing this pass could read
#
# THREE FIELDS A DELIVERY-DATED ROW ALSO CARRIES.
#   first_publication_event      `shop-delivery`, so nothing downstream reads the date as a printing
#   first_publication_followup   whether a better date could exist. NOT A BACKLOG:
#                                `no-earlier-record-expected` is finished work under DEFINITIONS §6,
#                                `unclassified` means the shop said nothing about the edition, and
#                                only `earlier-edition-unsourced` is a row a source could answer.
#   edition_statement            what the shop's own description says this file's edition is. The
#                                term is recorded and the sentence is not, because a shop's あらすじ
#                                is copyrighted (REQUIREMENTS §2).
#
# WHAT A ROW DATED FROM THE DESCRIPTION CARRIES INSTEAD.
#   edition_date                 the printing the description states, at the precision it stated:
#                                2016, 2022-05 or 2023-12-03. Not padded to a day.
#   edition_date_event           `issue` for 発行 and `first-appearance` for 初出, which are two
#                                claims about two events and need not fall on the same day
#   first_publication_event      the same claim, once the date is the row's answer
#   first_publication_source     the work page, which is where the sentence is
#
# AND ONE FIELD ANY OF THESE ROWS MAY CARRY.
#   edition_event                the sales event the description names, as `comitia 150` or
#                                `comiket 102`. Recorded as an event and never converted to a day:
#                                Comiket 98 was cancelled and its number used up, and 関西コミティア
#                                numbers a separate series, so arithmetic on the number is wrong in
#                                two ways that produce a plausible date. adapters/blurbdate.py.
#
# TWO FIELDS THAT APPEAR ONLY WHERE THEY SAY SOMETHING.
#   printed_source   the page a per-book route read the date off. A bulk catalogue has none, and
#                    its absence is an answer rather than an omission.
#   publisher_isbn   the ISBN the publisher's own page states for this volume, where the shop's
#                    differs. cmoa prints 9784758062862 for える・えるシスター 1巻 and that ISBN is
#                    白砂村 (7) at 一迅社. The shop's number is left as the shop states it, because
#                    this file is a capture of what cmoa says and rewriting it would lose the
#                    disagreement, which is the part worth keeping.
#
# A DATE HERE IS VOLUME 1'S AND NOT ALWAYS THE WORK'S. A serialised work was published in a
# magazine before its tankōbon, and this shop never names the magazine. So the date bounds the
# work's first publication from above rather than being it, and whether that satisfies §6 for a
# serialised work is a decision for whoever promotes these rows.
#
# EXCLUSIONS ARE COUNTED AND NEVER NAMED, as in admitted.yaml. A work page states a genre and an
# imprint the listing row did not, either of which can carry a designation (DEFINITIONS §7).
"""


# WHERE cmoa PUTS ITS OWN DESCRIPTION. `title_intro_box` on the work page, present on all 1,971
# pages in the cache. The box is read and never stored: a shop's あらすじ is copyrighted
# (REQUIREMENTS §2), so what is kept is one of `delivery`'s terms and the keyword that matched.
#
# WHY NOT `meta name="description"`. It concatenates the shop's boilerplate, the volume title and
# the blurb, so a match cannot be attributed to the blurb. WHY NOT THE WHOLE PAGE: 321 of the 1,971
# pages carry a doujin word somewhere and 285 carry one in the description. The rest are in reader
# reviews and in the sidebar of other people's books, and a count over the page would have read as
# the shop stating something about 36 works it says nothing about.
# THE END OF THE BOX IS A NAMED ELEMENT AND NOT A COUNT OF CLOSING TAGS. The first version of this
# ended at the third `</div>`, which lands in the right place on cmoa's current template and is one
# nested wrapper away from reading half the page. `comic_description_hide` is the shop's own name
# for the element after the description and follows the box on all 1,971 cached pages.
INTRO_BOX = re.compile(r'<div class="title_intro_box".*?(?=<div id="comic_description_hide")', re.S)
INTRO_OPEN = re.compile(r'<div class="title_intro_box"')
TAGS = re.compile(r"<[^>]+>")

# THE SYNOPSIS ALONE, WHICH IS A NARROWER SPAN OF THE SAME BOX AND EXISTS FOR ONE REASON. The box
# above holds the shop's own metadata table after the blurb, and one of its lines is
# `配信開始日 ： 2015年8月18日`. A rule looking for a date in the box would find that line on every
# page in the cache and hand the delivery date back as though the shop had stated a printing, which
# is the one answer this whole round exists to avoid. So `blurbdate` reads the synopsis and
# `delivery.edition_statement` keeps reading the box, whose wider span changes none of its 174 and
# 79 answers and does change `mentions_doujin` on seven pages where the word is in the shop's own
# tags. `comic_description_related_text_box` opens the table on all 1,971 cached pages.
SYNOPSIS = re.compile(r'<div id="comic_description".*?(?=<div class="related_box)', re.S)


def description(body):
    """The shop's own description of a work, as text, or "" where the page carries no box.

    Falls back to the rest of the page where the box opens and the closing marker is absent, since
    a template that has moved its own marker is better read imperfectly than reported as silent. A
    page with no box at all answers "", which is the case a health floor should see.
    """
    body = str(body or "")
    m = INTRO_BOX.search(body) or INTRO_OPEN.search(body)
    if not m:
        return ""
    seg = body[m.start():m.end()] if m.re is INTRO_BOX else body[m.start():]
    return re.sub(r"\s+", " ", TAGS.sub(" ", seg)).strip()


def synopsis(body):
    """The shop's blurb without the metadata table under it, or "" where the page carries neither.

    Falls back to `description` where the table's own element is absent, so a template that has
    renamed one marker is read imperfectly and not reported as silent. A date rule reading the wider
    span is the risk `SYNOPSIS` was written for, and it is a bounded one: the table names 配信開始日,
    which is already on the row from the volume page, so a wrong answer here would agree with the
    delivery date and be visible as such rather than inventing a new number.
    """
    body = str(body or "")
    m = SYNOPSIS.search(body)
    if not m:
        return description(body)
    return re.sub(r"\s+", " ", TAGS.sub(" ", m.group(0))).strip()


def read_editions(doc, cache, today=None):
    """Fill what the shop's description says about the edition, as `(doc, counts)`. No network.

    THE PAGES ARE ALREADY PAID FOR, which is why this is a separate stage and why it never fetches:
    the delivery dates and the descriptions were both on the work pages the capture read, and only
    the dates were kept. A row whose page is not in the cache keeps no statement and sorts to
    `unclassified`, which is the truthful answer for a page nobody has read.

    THREE FACTS COME OFF ONE READING OF ONE PAGE. Which edition the file is, when the shop says the
    earlier edition was published, and which sales event it names. They are filled together so no
    later stage has to open the page again and reach a different answer from it.

    NONE OF THEM IS THE SENTENCE. A shop's あらすじ is copyrighted (REQUIREMENTS §2), so what lands
    on the row is one of `delivery`'s or `blurbdate`'s own terms, the date, and the event number the
    shop printed.
    """
    tally = {"pages_read": 0, "mentions_doujin": 0, delivery.EARLIER_EDITION: 0,
             delivery.OWN_DOUJIN: 0, "no_cached_page": 0, "blurb_dated": 0, "event_named": 0}
    for tid, w in doc["works"].items():
        body = fetch(cmoa.work_url(tid), cache, offline=True)
        if body is None:
            tally["no_cached_page"] += 1
            continue
        tally["pages_read"] += 1
        text = description(body)
        if delivery.mentions_doujin(text):
            tally["mentions_doujin"] += 1
        said = delivery.edition_statement(text)
        if said:
            w["edition_statement"] = said
            tally[said] += 1
        else:
            w.pop("edition_statement", None)
        # The date and the event come off the SYNOPSIS and the statement off the box. `SYNOPSIS`
        # carries the reason, which is that the box holds the shop's own 配信開始日 line.
        blurb = synopsis(body)
        date, claim = blurbdate.stated(blurb, today=today)
        if date:
            w["edition_date"], w["edition_date_event"] = date, claim
            tally["blurb_dated"] += 1
        else:
            w.pop("edition_date", None)
            w.pop("edition_date_event", None)
        event = blurbdate.sold_at(blurb) if said else None
        if event:
            w["edition_event"] = event[0] + (f" {event[1]}" if event[1] else "")
            tally["event_named"] += 1
        else:
            w.pop("edition_event", None)
        settle(w)
    return doc, tally


def counts(doc):
    """What the file holds, by basis. Written into the document so a reader need not recount."""
    works = list((doc.get("works") or {}).values())
    out = {"with_first_publication_date": sum(1 for w in works if w.get("first_publication_date")),
           "volumes_read": sum(len(w.get("volumes") or []) for w in works),
           "volumes_with_print_date": sum(w.get("dates_stated") or 0 for w in works),
           "volumes_with_isbn": sum(w.get("isbns_stated") or 0 for w in works),
           "marked_completed": sum(1 for w in works if w.get("completed"))}
    for w in works:
        k = "by_basis_" + (w.get("first_publication_basis") or "unknown").replace("-", "_")
        out[k] = out.get(k, 0) + 1
    # WHAT THE WEAKEST DATE IN THE FILE AMOUNTS TO, counted here so nothing has to recount it. The
    # follow-up tally is NOT a backlog: `no_earlier_record_expected` is finished work under
    # DEFINITIONS §6, `unclassified` means the shop said nothing about the edition, and only
    # `earlier_edition_unsourced` is a row a better source could answer.
    for w in works:
        for field, prefix in (("first_publication_followup", "followup_"),
                              ("edition_statement", "shop_states_")):
            if w.get(field):
                k = prefix + w[field].replace("-", "_")
                out[k] = out.get(k, 0) + 1
    # WHAT THE SHOP DATED ITSELF, at the precision it stated. A month is what most of these say and
    # a year is what six of them say, so rounding either to a day would state a day nobody wrote.
    # `events_named` counts rows naming a sales event, which is a lead a person could date from an
    # event calendar and which this pass deliberately does not date (adapters/blurbdate.py).
    for w in works:
        if w.get("edition_date"):
            out["blurb_date_" + blurbdate.precision(w["edition_date"])] = \
                out.get("blurb_date_" + blurbdate.precision(w["edition_date"]), 0) + 1
        if w.get("edition_event"):
            out["events_named"] = out.get("events_named", 0) + 1
    return out


def yaml_document(doc):
    """The output file. Written whole on every checkpoint, so a killed run loses one page."""
    js = json.dumps
    L = [HEADER,
         "source: cmoa.jp",
         "role: volume-histories",
         "record_type: retailer_volume_capture",
         "from_queue: data/queue/admitted.yaml",
         "key: shop_id",
         f"retrieved: {doc.get('retrieved')}",
         f"admitted_rows: {doc.get('asked', 0)}",
         f"works_captured: {len(doc['works'])}",
         "counts:"]
    for k, v in counts(doc).items():
        L.append(f"  {k}: {v}")
    L.append(f"excluded: {js(doc.get('excluded') or {}, ensure_ascii=False)}")
    L.append(f"excluded_ids: {js(sorted(doc.get('excluded_ids') or []))}")
    L.append("works:")
    for tid in sorted(doc["works"], key=int):
        w = doc["works"][tid]
        L.append(f"  - shop_id: \"{tid}\"")
        for k in ("url", "shelf_title", "publisher", "imprint", "shop_genres", "completed",
                  "volumes_stated", "volumes_found", "dates_stated", "isbns_stated",
                  "first_publication_date", "first_publication_basis",
                  "first_publication_country", "first_publication_venue"):
            L.append(f"    {k}: {js(w.get(k), ensure_ascii=False)}")
        # Written only where there is one, so the 1,800 rows dated from a bulk catalogue do not
        # each carry a null saying the catalogue has no per-book page.
        if w.get("first_publication_source"):
            L.append(f"    first_publication_source: {js(w['first_publication_source'])}")
        # WHAT THE SHOP SAID ABOUT THIS FILE'S EDITION, written only on the rows it said it about.
        # `first_publication_event` names the event the date is of, which is what stops a reader
        # downstream treating a delivery for a printing; the follow-up state says whether anything
        # is waiting on a source; `edition_statement` is which edition the description says the file
        # is; `edition_date` is the printing the description dates and `edition_date_event` the
        # claim it dated; and `edition_event` is the sales event it named, recorded as an event
        # because this pass will not turn an event number into a day. Every one of them is a term
        # or a number and never the sentence, which is copyrighted (REQUIREMENTS §2).
        for k in ("first_publication_event", "first_publication_followup", "edition_statement",
                  "edition_date", "edition_date_event", "edition_event"):
            if w.get(k):
                L.append(f"    {k}: {js(w[k])}")
        L.append("    volumes:")
        for v in w.get("volumes") or []:
            L.append(f"      - volume: {v['volume']}")
            for k in ("title", "url", "isbn", "publisher_isbn", "printed", "printed_basis",
                      "printed_source", "delivered"):
                if v.get(k) is not None:
                    L.append(f"        {k}: {js(v[k], ensure_ascii=False)}")
    L.append("")
    return "\n".join(L)


def load(path):
    """Read the output file back into the shape a run folds into.

    THE ID COMES OFF THE ROW AND THE DOCUMENT IS RE-KEYED BY IT, and the first version of this did
    neither: it read a mapping whose rows did not repeat their own id, so every work loaded from
    disk came back with an empty one and the next fold filed the whole document under "". Resuming
    is the half of a capture that only runs on the second day, which is exactly why it gets shipped
    broken; `test_cmoa_volumes.py` writes a document, reads it, folds one row in, and checks the
    earlier works are still addressable.
    """
    doc = yaml.safe_load(pathlib.Path(path).read_text()) if pathlib.Path(path).exists() else None
    doc = doc or {}
    # `asked` is written out as `admitted_rows` and was not read back, so any pass that loaded the
    # file and rewrote it reset the shelf size to 0. It is one fact under two names and the names
    # are joined here, in the one place that turns the file back into a document.
    doc["asked"] = doc.get("asked") or doc.get("admitted_rows") or 0
    works = doc.get("works") or []
    if isinstance(works, dict):                       # a mapping is accepted, a list is written
        works = [dict(w, shop_id=str(k)) for k, w in works.items()]
    doc["works"] = {str(w["shop_id"]): w for w in works if w.get("shop_id")}
    return doc


def wanted_ids(admitted):
    d = yaml.safe_load(pathlib.Path(admitted).read_text()) or {}
    return {str(w["shop_id"]): w for w in (d.get("works") or []) if w.get("shop") == "cmoa.jp"}


def run_pages(doc, shelf, todo, cache, out, offline=False):
    """Fetch and checkpoint, one work at a time, stopping if the run goes bad rather than at the end."""
    window, asked, kept = [], 0, 0
    excluded = dict(doc.get("excluded") or {})
    excluded_ids = set(doc.get("excluded_ids") or [])
    for n, tid in enumerate(todo, 1):
        parsed = capture_one(tid, cache, offline)
        asked += 1
        ok = usable(parsed)
        window.append(ok)
        if ok:
            rec, why = record(parsed, shelf.get(tid))
            if why:
                excluded[why] = excluded.get(why, 0) + 1
                excluded_ids.add(tid)
            else:
                doc, _ = fold_in(doc, [rec])
                kept += 1
        doc["excluded"], doc["excluded_ids"] = excluded, sorted(excluded_ids)
        pathlib.Path(out).write_text(yaml_document(doc))
        if n % 25 == 0:
            print(f"  {n}/{len(todo)} asked, {kept} kept, {len(doc['works'])} in file", flush=True)
        if len(window) >= WINDOW:
            good, u, a = healthy(sum(window[-WINDOW:]), WINDOW)
            if not good:
                print(f"Refusing to write further: {u} of the last {a} work pages parsed into a "
                      f"volume list, under the {FLOOR:.0%} a healthy run clears. That is the host "
                      f"in trouble or a page whose markup has moved, and both look identical from "
                      f"here. {len(doc['works'])} works already in the file are untouched.",
                      flush=True)
                return doc, asked, kept, False
    return doc, asked, kept, True


def volumes_outstanding(doc, printed_only=True):
    """`[(shop_id, volume)]` for volumes nobody has opened the page of.

    A volume page states 配信開始日 whatever else it withholds, so `delivered` is the mark of a
    page that has been read. Volume 1 carries it from the work page, and the rest do not until
    this stage asks.

    `printed_only` is where the cost goes. cmoa states an ISBN for a volume that was printed, and
    a work whose first volume has none is a digital-only title whose later volumes will not have
    one either. Asking about them buys a 配信開始日 that answers nothing under §6, so the default
    spends the requests where an answer is possible.
    """
    out = []
    for tid, w in sorted((doc.get("works") or {}).items(), key=lambda kv: int(kv[0])):
        vols = w.get("volumes") or []
        first = next((v for v in vols if v.get("volume") == 1), None)
        if printed_only and not (first or {}).get("isbn"):
            continue
        out += [(tid, v["volume"]) for v in vols if not v.get("delivered")]
    return out


def capture_volume(title_id, n, cache, offline=False):
    """One volume's own page, as `{isbn, printed, delivered}`, or None where it did not read.

    The 作品情報 block on `/title/<id>/vol/<n>/` describes THAT volume: 12分のエチュード's volume 2
    page states 9784758075510 and 2016-06-18 against volume 1's 9784758074803 and 2015-09-19. The
    volume list on the same page is the whole work's and is ignored here, because the number asked
    for is already known and reading it back off the page would be a second producer of it.
    """
    body = fetch(cmoa.volume_url(title_id, n), cache, offline)
    if body is None:
        return None
    parsed = cmoa.work(body, title_id)
    if not parsed.get("distribution_started") and not parsed.get("isbn"):
        return None
    return {"isbn": parsed.get("isbn"),
            "printed": parsed.get("published"),
            "printed_basis": "shop-publication-month" if parsed.get("published") else None,
            "delivered": parsed.get("distribution_started")}


def run_volumes(doc, todo, cache, out, offline=False):
    """Fetch volume pages, checkpointing per work so a killed run loses one work at most."""
    window, asked, kept = [], 0, 0
    for n, (tid, vol) in enumerate(todo, 1):
        got = capture_volume(tid, vol, cache, offline)
        asked += 1
        window.append(bool(got))
        if got:
            for v in doc["works"][tid]["volumes"]:
                if v["volume"] == vol:
                    v.update({k: x for k, x in got.items() if x is not None})
            settle(doc["works"][tid])
            kept += 1
        pathlib.Path(out).write_text(yaml_document(doc))
        if n % 50 == 0:
            print(f"  {n}/{len(todo)} volume pages, {kept} read", flush=True)
        if len(window) >= WINDOW and not healthy(sum(window[-WINDOW:]), WINDOW)[0]:
            print(f"Refusing to write further: fewer than {FLOOR:.0%} of the last {WINDOW} volume "
                  f"pages stated anything. Nothing already in {out} was removed.", flush=True)
            return doc, asked, kept, False
    return doc, asked, kept, True


def isbns_held(doc):
    """Every ISBN the capture holds, with the (title id, volume) it came from."""
    out = {}
    for tid, w in (doc.get("works") or {}).items():
        for v in w.get("volumes") or []:
            if v.get("isbn"):
                out.setdefault(v["isbn"], []).append((tid, v["volume"]))
    return out


# Which catalogue's answer stands where more than one speaks. MADB first: it is the national
# bibliography, sourced from NDLサーチ, and it answered 22 of the 23 ISBNs sampled against openBD's
# 10. openBD next, because a publisher's own registration outranks the shop's transcription of it.
# The shop's 出版年月 last, and it is still the only answer for a volume neither catalogue holds.
#
# THE ORDER IS ALSO THE ONE THAT KEEPS THIS CORPUS CONSISTENT WITH ITSELF, which is the argument
# that decided it. On the first 463 works captured, MADB disagreed with the shop on 14 volumes and
# 13 of those are one month later: 双葉社's GIRL FRIENDS is 2007-12 at the shop and 2008-01 at MADB,
# and openBD independently says 200801. So cmoa states the ON-SALE month and the catalogues state
# the 奥付 date, the two are a month apart by construction, and every date already in
# data/source/ came from openBD's convention. Taking the shop's would have introduced a second
# convention into one field, which is worse than being a month out.
#
# The fourteenth is 169776, thirteen months apart, and it is a lead rather than noise. A gap that
# size is a different edition or a mismatched ISBN, and the count is how anyone would ever see it.
#
# THE TWO ROUTES ADDED ON 2026-08-07 SIT BELOW BOTH CATALOGUES AND ABOVE THE SHOP, and the reason
# is what each of them is a record OF. `adapters/publisher_dates.py` reads the publisher's own book
# page, which is first-hand and outranks the shop's transcription; `books-or-jp-registration` is
# the aggregator behind it and is taken only where the publisher no longer has a page. Neither can
# displace a catalogue date, because both state 発売日 while MADB and openBD state the 奥付 date,
# and the paragraph above is why one field must not carry two conventions. The ordering is moot for
# the 49 rows that prompted it, where no catalogue holds the ISBN at all, and it is written down so
# it stays right when one of them does.
PREFERENCE = ["madb-tankobon", "openbd-registration", "publisher-own-page",
              "books-or-jp-registration", "shop-publication-month"]


def apply_dates(doc, dates, basis, sources=None):
    """Fill `printed` from a `{isbn: date}` answer, and recompute what it settles.

    A BETTER SOURCE REPLACES A WORSE ONE AND NEVER THE OTHER WAY. Both catalogue passes may run,
    in either order, and a run of the weaker one afterwards must not undo the stronger. Silence
    changes nothing at all: a catalogue that does not hold an ISBN has not corrected anything.

    `sources` is an optional `{isbn: url}` naming the page a date was read off. A bulk catalogue
    has no per-book page to cite and passes none; a route that reads one page per book passes one,
    and it is stored beside the date so a reader can check the claim and so a date taken from a
    weaker route can be found again if a better page appears.

    Returns `(doc, filled, disagreements)`. A disagreement is counted rather than resolved, because
    two catalogues differing by a month is the ordinary gap between a 奥付 date and an on-sale
    date, and differing by years would be a join that has gone wrong. Only the count distinguishes
    them, and only if somebody is keeping it.
    """
    where = isbns_held(doc)
    filled = disagreements = 0
    rank = PREFERENCE.index(basis)
    for isbn, date in (dates or {}).items():
        if not date:
            continue
        for tid, n in where.get(isbn, []):
            for v in doc["works"][tid]["volumes"]:
                if v["volume"] != n:
                    continue
                held, held_basis = v.get("printed"), v.get("printed_basis")
                if held and held != date:
                    disagreements += 1
                if held_basis in PREFERENCE and PREFERENCE.index(held_basis) < rank:
                    continue
                v["printed"], v["printed_basis"] = date, basis
                v["printed_source"] = (sources or {}).get(isbn)
                filled += 1
    for w in doc["works"].values():
        settle(w)
    return doc, filled, disagreements


def openbd_dates(payload):
    """`{isbn: date}` from an openBD payload.

    `enrich.pubdate` and not a second normaliser beside it. openBD writes YYYYMMDD, YYYYMM and
    occasionally nothing, and which precisions are kept is one decision with one place to change
    it (STANDING-INSTRUCTIONS §3).
    """
    return {isbn: enrich.pubdate(((rec or {}).get("summary") or {}).get("pubdate"))
            for isbn, rec in (payload or {}).items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--admitted", default="data/queue/admitted.yaml")
    ap.add_argument("--out", default="data/queue/cmoa-volumes.yaml")
    ap.add_argument("--cache", default=str(paths.cache("cmoa-cache")))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offline", action="store_true", help="parse only what the cache holds")
    ap.add_argument("--madb", action="store_true",
                    help="date held ISBNs from the MADB bulk dataset; no network")
    ap.add_argument("--madb-cache", default=str(paths.cache("madb-cache") / "1.2.18"))
    ap.add_argument("--openbd", action="store_true", help="join held ISBNs against openBD")
    ap.add_argument("--volumes", action="store_true",
                    help="open each volume's own page for its ISBN and dates")
    ap.add_argument("--all-volumes", action="store_true",
                    help="with --volumes, ask about digital-only works too")
    ap.add_argument("--delivery", action="store_true",
                    help="re-settle every row and read each cached page for what the shop says "
                         "about its edition; no network")
    ap.add_argument("--report", action="store_true", help="say what the output file holds")
    a = ap.parse_args(argv)

    shelf = wanted_ids(a.admitted)
    doc = load(a.out)
    doc["retrieved"] = doc.get("retrieved") or datetime.date.today().isoformat()
    doc["asked"] = len(shelf)

    if a.report:
        return report(doc, shelf)

    if a.delivery:
        before = counts(doc).get("with_first_publication_date", 0)
        doc, tally = read_editions(doc, a.cache)
        pathlib.Path(a.out).write_text(yaml_document(doc))
        after = counts(doc).get("with_first_publication_date", 0)
        print(f"HEALTH: {tally['pages_read']} of {len(doc['works'])} work page(s) held in the "
              f"cache, {tally['no_cached_page']} not")
        print(f"{tally['mentions_doujin']} description(s) mention a doujin word; the shop states "
              f"an earlier edition on {tally[delivery.EARLIER_EDITION]} and states the file is "
              f"itself a doujinshi on {tally[delivery.OWN_DOUJIN]}")
        print(f"{tally['blurb_dated']} description(s) date the earlier edition themselves and "
              f"{tally['event_named']} name the sales event without dating it")
        print(f"{after - before} work(s) gained a date, {after} dated in all -> {a.out}")
        return report(doc, shelf)

    if a.madb:
        held = isbns_held(doc)
        index = isbn_dates.load(a.madb_cache)
        answers = {i: index.get(i) for i in held}
        got = sum(1 for v in answers.values() if v)
        print(f"HEALTH: MADB holds a date for {got} of {len(held)} ISBN(s) captured")
        doc, filled, dis = apply_dates(doc, answers, "madb-tankobon")
        pathlib.Path(a.out).write_text(yaml_document(doc))
        print(f"{filled} volume(s) dated from the national bibliography, {dis} disagreeing with a "
              f"date already held -> {a.out}")
        return report(doc, shelf)

    if a.openbd:
        held = isbns_held(doc)
        print(f"{len(held)} ISBN(s) held across {len(doc['works'])} works")
        payload = openbd_reading.fetch(sorted(held), paths.cache("openbd-cache"), a.offline)
        ok, got, asked = openbd_reading.healthy(payload)
        print(f"HEALTH: openBD holds {got} of {asked} ISBN(s) asked about")
        if not ok:
            print("Refusing to write: openBD answered for under half the ISBNs asked about, which "
                  "is a stopped fetch or a host in trouble rather than a shelf of unregistered "
                  "books, and the two look identical from here.")
            return 1
        doc, filled, dis = apply_dates(doc, openbd_dates(payload), "openbd-registration")
        pathlib.Path(a.out).write_text(yaml_document(doc))
        print(f"{filled} volume(s) gained a registered publication date, {dis} disagreeing with a "
              f"date already held -> {a.out}")
        return report(doc, shelf)

    if a.volumes:
        todo = volumes_outstanding(doc, printed_only=not a.all_volumes)
        if a.limit:
            todo = todo[:a.limit]
        print(f"{len(todo)} volume page(s) to open")
        doc, asked, kept, _ = run_volumes(doc, todo, a.cache, a.out, a.offline)
        good, u, n = healthy(kept, asked)
        print(f"HEALTH: {u} of {n} volume page(s) stated something")
        if asked and not good:
            print(f"Refusing to treat this run as a capture: {u} of {n} volume pages read, under "
                  f"the {FLOOR:.0%} floor. Nothing already in {a.out} was removed.")
            return 1
        return report(doc, shelf)

    todo = outstanding(sorted(shelf, key=int), doc)
    if a.limit:
        todo = todo[:a.limit]
    print(f"{len(shelf)} cmoa rows admitted, {len(doc['works'])} already captured, "
          f"{len(todo)} to fetch now")
    doc, asked, kept, completed = run_pages(doc, shelf, todo, a.cache, a.out, a.offline)
    good, u, n = healthy(kept, asked)
    print(f"HEALTH: {u} of {n} work page(s) asked about parsed into a volume list")
    if asked and not good:
        print(f"Refusing to treat this run as a capture: {u} of {n} pages came back usable, under "
              f"the {FLOOR:.0%} floor. Nothing already in {a.out} was removed.")
        return 1
    return report(doc, shelf)


def report(doc, shelf):
    """What the file holds, printed. The basis breakdown is the answer worth reading.

    A count of works without a date says how far there is to go and nothing about how to get
    there. The basis says which silence each row is in, and the four silences have four different
    remedies, one of which is that there is no remedy.
    """
    works = doc.get("works") or {}
    c = counts(doc)
    print(f"\nadmitted rows            : {len(shelf)}")
    print(f"captured                 : {len(works)}")
    print(f"excluded on a designation: {sum((doc.get('excluded') or {}).values())}")
    for k, v in sorted((doc.get("excluded") or {}).items(), key=lambda kv: -kv[1]):
        print(f"    {v:5}  {k}")
    print(f"volumes read             : {c['volumes_read']}")
    print(f"volumes stating an ISBN  : {c['volumes_with_isbn']}")
    print(f"works with a date        : {c['with_first_publication_date']}")
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        if k.startswith("by_basis_"):
            print(f"    {v:5}  {k[len('by_basis_'):].replace('_', '-')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
