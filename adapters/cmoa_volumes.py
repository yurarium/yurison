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

  IT IS NOT THE DATE FOR THE DIGITAL-ONLY ROWS EITHER, which is the tempting exception, because
  those rows are the ones with nothing else. cmoa's own description of #ミカちゃんともなちゃん says
  the file is the ebook edition of the author's 個人誌, so the shop is stating that an earlier
  publication exists and not saying when. Absence of a date is a state
  (STANDING-INSTRUCTIONS §5) and these rows keep it: `first_publication_basis` reads
  `shop-delivery-date-only` and `first_publication_date` stays null.

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
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cmoa                                                                    # noqa: E402
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


def fold(doc, rows):
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
    if first.get("delivered"):
        return None, "shop-delivery-date-only"
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
    # A cmoa publisher is a Japanese company selling a Japanese print edition, so a date from this
    # route carries JP. The venue is the publisher and NOT the magazine: this shop never names a
    # magazine, and a tankōbon publisher is not the venue of a serialised work's first chapter.
    w["first_publication_country"] = "JP" if date else None
    w["first_publication_venue"] = (w.get("publisher") or None) if date else None
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
#               page. It is a fact about the shop's stock and NOT a publication of the work: it
#               runs years late on a digitised back catalogue, 双葉社 stating 2007年12月 for a file
#               the shop began selling on 2012-10-05. It is never used as first_publication.
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
#   shop-publication-month     the shop states 出版年月 and neither catalogue holds the ISBN
#   isbn-stated-not-catalogued an ISBN is stated and no catalogue asked has a record of it
#   shop-delivery-date-only    the shop states only the day it began selling the file. No print
#                              edition, so no ISBN will ever exist and no ISBN route can help.
#   no-date-stated             the page carries no date of any kind
#   no-volumes-found           the page listed nothing this pass could read
#
# A DATE HERE IS VOLUME 1'S AND NOT ALWAYS THE WORK'S. A serialised work was published in a
# magazine before its tankōbon, and this shop never names the magazine. So the date bounds the
# work's first publication from above rather than being it, and whether that satisfies §6 for a
# serialised work is a decision for whoever promotes these rows.
#
# EXCLUSIONS ARE COUNTED AND NEVER NAMED, as in admitted.yaml. A work page states a genre and an
# imprint the listing row did not, either of which can carry a designation (DEFINITIONS §7).
"""


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
        L.append("    volumes:")
        for v in w.get("volumes") or []:
            L.append(f"      - volume: {v['volume']}")
            for k in ("title", "url", "isbn", "printed", "printed_basis", "delivered"):
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
                doc, _ = fold(doc, [rec])
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
PREFERENCE = ["madb-tankobon", "openbd-registration", "shop-publication-month"]


def apply_dates(doc, dates, basis):
    """Fill `printed` from a `{isbn: date}` answer, and recompute what it settles.

    A BETTER SOURCE REPLACES A WORSE ONE AND NEVER THE OTHER WAY. Both catalogue passes may run,
    in either order, and a run of the weaker one afterwards must not undo the stronger. Silence
    changes nothing at all: a catalogue that does not hold an ISBN has not corrected anything.

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
    ap.add_argument("--report", action="store_true", help="say what the output file holds")
    a = ap.parse_args(argv)

    shelf = wanted_ids(a.admitted)
    doc = load(a.out)
    doc["retrieved"] = doc.get("retrieved") or datetime.date.today().isoformat()
    doc["asked"] = len(shelf)

    if a.report:
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
