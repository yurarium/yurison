#!/usr/bin/env python3
"""Volume histories and dates for the BOOK☆WALKER rows in data/queue/admitted.yaml.

WHY THIS EXISTS. 2,438 rows were admitted from the shop's 百合 shelf on the designation test, and
none of them can become a work record: build.py requires `first_publication` under DEFINITIONS §6,
and the shelf listing states title, author, publisher and imprint only. This asks each work's own
pages for the rest.

WHAT THE SHOP STATES, AND WHAT IT DOES NOT. Read this before treating any date here as a
publication date, because two of the three findings are negative and they decide what §6 can be
answered with.

  配信開始日  ALWAYS present, on all 870 volumes read so far. It is the day BOOK☆WALKER began
              selling the file, which is an event in a shop's stock control rather than a
              publication of the work. Stored as `delivered` and never used as
              `first_publication`. THE MEASUREMENT, so nobody reaches for it later as an
              approximation: of the 276 volumes stating both dates, 115 were delivered before the
              print edition appeared, 123 on the same day and 38 after it, the last of those by up
              to 4,471 days. It is not a bound in either direction, and a decade-late delivery
              date written into a date field sorts and prints exactly like a publication date.
  底本発行日  Present on 276 of 870, 31.7%. The publication date of the print edition the file was
              made from, which IS a publication of the work. Stored as `printed`. It tracks the
              imprint almost perfectly: まんがタイムKRコミックス and 電撃コミックスNEXT state it on
              every volume sampled, and 百合コレ, YURI HUB, BLIC-GL and アトキンソン state it on
              none, because those titles have no print edition to date.
  ISBN        NEVER, on any of the 870. Not on the volume page, not on the series page, not in the
              JSON-LD, which carries a Product with a price and no identifier. The shop sells files
              and files have no ISBN. openBD and NDL are both keyed on ISBN, so this shelf reaches
              neither of them, and that is the finding rather than a gap to fill later.

ONE REQUEST PER VOLUME, AND THE SERIES PAGE DOES NOT SHORTEN IT. /series/<id>/list/ names every
volume, its uuid, its author and its label, and states the completion tag adapters/bookwalker.py
reads. It carries no date for any of them. So a series of nine volumes costs ten requests, and the
cost of this capture is set by that and nothing else.

NOTHING HERE IS RE-DERIVED. The listing rows on a series page are parsed by
recon/bookwalker_shelf.parse_listing, the completion tag by bookwalker.status_from_list, and the
designation test by shelfingest.designated. Each of those facts already had a producer, and a
second one with nothing forcing agreement is this project's dominant bug (STANDING-INSTRUCTIONS
§3). The only thing this module reads for itself is the volume information table, which nothing
else has ever read.

A DESIGNATION THE SHELF COULD NOT SHOW. The shelf showed a series title; a volume page shows the
volume's own title, its imprint and its publisher. Any of those can carry a marking the series
title did not, and a work whose volume 3 is an 【R-18版】 is excluded on volume 3. Exclusions are
counted with their reason and the title is written nowhere.
"""
import collections
import re

# What kind of venue the date came from, per basis, in build.py's vocabulary.
VENUE_TYPE = {
    "print-base-edition": "tankobon-imprint",
    "no-print-edition": "digital-imprint",
    "chapter-serial": "chapter-serial-imprint",
    "no-print-date-stated": "imprint",
    "print-edition-unknown": "imprint",
    "no-volumes-found": None,
}

# WHY JP IS ASSERTED, AND THE CASE IT WOULD GET WRONG. Every row here is a Japanese-language book
# from a Japanese publisher on a Japanese store, which is evidence about where it was published
# rather than proof. §6 puts a Korean webtoon localised to a Japanese platform OUT of scope, and
# such a title would pass this test, so the basis is recorded and a promotion step has to look at
# the publishers rather than take the country on trust.
COUNTRY_BASIS = ("Japanese-language edition from a Japanese publisher on the shop's Japanese "
                 "store. Not a check against §6's localisation exclusion, which needs the "
                 "publisher examined.")

# The volume information table. One dt per field, values in the dd that follows. The 話・連載 store
# renders a different template with the same dt/dd shape and a shorter table, so both classes are
# matched here rather than parsed twice.
INFO_DL = re.compile(r'<dl class="(?:t-c-detail-about-information__data|o-ttsk-card__data)">'
                     r'(.*?)</dl>', re.S)
INFO_PAIR = re.compile(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", re.S)
# Each linked value in a dd. 著者 puts one per <li>, so the anchors are the values.
INFO_LINK = re.compile(r"<a\b[^>]*>(.*?)</a>", re.S)
SERIES_IN_INFO = re.compile(r"/series/(\d+)/")

# 2025/12/26 and 2020/11/2 are both the shop's. Zero padding is not guaranteed.
YMD = re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})")

# The volume's own title, from the JSON-LD Product the page carries. Taken from there rather than
# from <title>, which appends the shop's advertising to every page and would need unpicking.
LD_NAME = re.compile(r'"@type":\s*"Product".*?"name":\s*"((?:[^"\\]|\\.)*)"', re.S)
H1 = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S)

# How the shop marks a role after a name in the information table.
ROLE_SUFFIX = re.compile(r"[(（](?:著者|著|作画|漫画|原作|原案|イラスト|訳者|編集|監修|"
                         r"キャラクター原案|その他)[)）]\s*$")

FIELDS = {"シリーズ": "series_title", "著者": "authors", "レーベル": "imprint",
          "出版社": "publisher", "カテゴリ": "category", "配信開始日": "delivered",
          "底本発行日": "printed", "ページ概数": "pages"}

# ISBN is not on these pages at all. The pattern exists so that a page which one day DOES state one
# is read rather than silently dropped, and so a reader can see the field was looked for.
ISBN = re.compile(r"ISBN[^0-9]{0,4}((?:97[89])?[-0-9Xx]{9,17})")


def _text(s):
    """Markup out, entities decoded, runs of ASCII space collapsed."""
    import html
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"[ \t\r\n]+", " ", html.unescape(s)).strip()


def iso_date(s):
    """`2025/12/26` and `2020/11/2` as `2025-12-26` and `2020-11-02`, else None.

    Returns None rather than the input where nothing parses. A date field holding a string the
    shop rendered for a human is the silent-plausible failure of STANDING-INSTRUCTIONS §4: it
    sorts, it prints, and it is not a date.
    """
    m = YMD.search(s or "")
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    if not (1900 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{mo:02d}-{d:02d}"


def info_table(html_text):
    """`{field: [values]}` from a volume page's information table, by the shop's own labels.

    Values come from the anchors where the dd has any, because 著者 lists one person per anchor and
    flattening the dd to text would join two people into one name. A dd with no anchor is its text.
    """
    m = INFO_DL.search(html_text or "")
    if not m:
        return {}
    out = {}
    for dt, dd in INFO_PAIR.findall(m.group(1)):
        key = _text(dt)
        links = [_text(v) for v in INFO_LINK.findall(dd)]
        values = [v for v in links if v] or ([_text(dd)] if _text(dd) else [])
        if key and values:
            out.setdefault(key, values)
    return out


def volume_title(html_text):
    """The volume's own title, as the shop names it in its Product payload."""
    m = LD_NAME.search(html_text or "")
    if m:
        return _text(m.group(1).replace("\\/", "/"))
    h = H1.search(html_text or "")
    return _text(h.group(1)) if h else None


def strip_role(name):
    """`イノウエ(著)` as `イノウエ`. The role rides on the name in this table."""
    return ROLE_SUFFIX.sub("", (name or "").strip()).strip()


def volume(html_text, uuid=None):
    """One volume's bibliographic record, or None where the page states no title.

    A page with no title is a failed fetch and not a volume with no name. It is the shape an error
    shell, a redirect to a sign-in page and a truncated response all arrive in, and recording it
    would put a row into the file asserting the shop states nothing about a work it states plenty
    about. `healthy` counts these and the run refuses to continue when they take over.
    """
    title = volume_title(html_text)
    if not title:
        return None
    t = info_table(html_text)
    series = t.get("シリーズ") or []
    dl = INFO_DL.search(html_text)
    # The series id from the information table's own link, not from anywhere else on the page. A
    # volume page carries series links in its breadcrumb, its recommendations and its footer, and
    # the first one found off the whole page belongs to whichever block the shop rendered first.
    m = SERIES_IN_INFO.search(dl.group(1) if dl else "")
    isbn = ISBN.search(html_text or "")
    return {
        "uuid": uuid,
        "title": title,
        "series_id": m.group(1) if m else None,
        "series_title": series[0] if series else None,
        "authors": [strip_role(a) for a in t.get("著者", [])],
        "imprint": (t.get("レーベル") or [None])[0],
        "publisher": (t.get("出版社") or [None])[0],
        "category": (t.get("カテゴリ") or [None])[0],
        # The shop's own two dates, kept apart and neither renamed into the other.
        "delivered": iso_date((t.get("配信開始日") or [""])[0]),
        "printed": iso_date((t.get("底本発行日") or [""])[0]),
        "isbn": isbn.group(1) if isbn else None,
    }


# The 話・連載 store. 293 of the admitted rows live here and they are not volumes: the shop sells
# them one chapter at a time and its series page carries no volume list at all, which is why the
# volume-store parser reads nothing from them.
WA_TITLE = re.compile(r'<h1 class="o-ttsk-card__title">(.*?)</h1>', re.S)
WA_UPDATED = re.compile(r'<p class="o-ttsk-card__update-date">(.*?)</p>', re.S)
WA_AUTHORS = re.compile(r'<ul class="o-ttsk-card__author-list">(.*?)</ul>', re.S)
WA_CHAPTERS = re.compile(r'<h2 class="p-episode__title[^"]*">\s*全([0-9,]+)話')
WA_TAGS = re.compile(r'<ul class="o-ttsk-card__tag-list">(.*?)</ul>', re.S)


def warensai(html_text, series_id=None):
    """One 話・連載 series as the shop states it, or None where the page states no title.

    WHAT IT STATES AND WHAT IT REFUSES TO. A chapter count, the label, the publisher, the author,
    the shop's genre tags, and one date: 更新, the day the latest chapter went up. That is the most
    recent publication and not the first, so it answers §6 in the wrong direction and is stored as
    `updated` under its own name. Nothing here has a 底本発行日, because there is no print edition
    to have one.

    THE GENRE TAGS ARE NEW EVIDENCE. The shelf capture recorded facet membership; this page prints
    the work's own tags, so a row tagged アダルト would announce itself here and nowhere earlier.
    They are passed to the designation test for that reason.
    """
    t = WA_TITLE.search(html_text or "")
    if not t:
        return None
    info = info_table(html_text)
    auth = WA_AUTHORS.search(html_text or "")
    tags = WA_TAGS.search(html_text or "")
    ch = WA_CHAPTERS.search(html_text or "")
    up = WA_UPDATED.search(html_text or "")
    return {
        "series_id": series_id,
        "title": _text(t.group(1)),
        "authors": [n for n in (strip_role(_text(a)) for a in
                                (INFO_LINK.findall(auth.group(1)) if auth else [])) if n],
        "imprint": (info.get("レーベル") or [None])[0],
        "publisher": (info.get("出版社") or [None])[0],
        "genre": " ".join(_text(x) for x in
                          (INFO_LINK.findall(tags.group(1)) if tags else [])),
        "chapters": int(ch.group(1).replace(",", "")) if ch else None,
        "updated": iso_date(up.group(1) if up else ""),
    }


def first_publication(volumes):
    """`(date, basis)` for the work, from its volumes, or `(None, reason)`.

    ONLY 底本発行日 ANSWERS §6. It is the print edition's publication date, stated by the shop about
    the object it made the file from. 配信開始日 is when this shop started selling, which is a fact
    about the shop: it is later than the print date on some rows and earlier on others, so it is
    not even a consistent bound in one direction, and DEFINITIONS §6 asks for the date the work was
    first published rather than the date a retailer picked it up.

    Even a stated 底本発行日 is the volume's date, not necessarily the work's. A serialised work was
    published in a magazine before its tankōbon, and this shop never mentions the magazine. So the
    basis is named `print-base-edition` rather than `first_publication`, and whoever promotes these
    rows into data/source has to decide whether a tankōbon date satisfies §6 for a serialised work.
    """
    dated = [v["printed"] for v in volumes if v.get("printed")]
    if dated:
        return min(dated), "print-base-edition"
    if volumes:
        # Refined later against what the imprint does elsewhere. See `date_basis`: an undated row
        # is either a format with no print edition to date or a silence nothing explains, and the
        # difference is not visible from one work's own pages.
        return None, "no-print-date-stated"
    return None, "no-volumes-found"


# How many volumes an imprint must contribute before its silence is read as a fact about the
# imprint. At five, an imprint that really dated half its volumes clears the bar 97 times in a
# hundred, and below it the honest answer is that nobody can tell yet.
MIN_IMPRINT_VOLUMES = 5


def imprint_key(row):
    """What to group a row by when asking whether its publisher issues print editions.

    The imprint where the shop states one, the publisher where it does not. 178 admitted rows carry
    the shop's ―― for an absent label, and pooling those into a single imprint called nothing would
    put ナンバーナイン's output and 一迅社's in the same bucket and let one answer for the other.
    """
    return row.get("imprint") or row.get("publisher") or None


def imprint_print_dates(rows):
    """`{imprint: (volumes read, volumes stating 底本発行日)}` across the whole capture."""
    out = {}
    for r in rows:
        for v in r.get("volumes") or []:
            k = imprint_key(v)
            if not k:
                continue
            read, dated = out.get(k, (0, 0))
            out[k] = (read + 1, dated + (1 if v.get("printed") else 0))
    return out


def date_basis(row, stats):
    """Why a work has the date it has, or why it has none. `(basis, note)`.

    TWO SILENCES THAT MEAN DIFFERENT THINGS, which is the whole point of this function. "The shop
    states no print date" and "there is no print edition" are different sentences and only the
    second explains itself, so an undated row is sorted between them on evidence rather than left
    in one heap. The evidence is what the row's own imprint does across the rest of the capture:
    百合コレ states 底本発行日 on none of its volumes because ナンバーナイン publishes no print
    editions, and まんがタイムKRコミックス states it on every one.

    WHAT `no-print-date-stated` DOES NOT CLAIM. It does not say a print edition exists. 百合姫
    コミックス is a print imprint that also sells 特装版小冊子電子版 and 【単話】 splits, which are
    digital-only products from a printing house, and they land here. The label says what is known,
    which is that the imprint's own record does not account for the silence.
    """
    if row.get("store") == "話・連載":
        return ("chapter-serial",
                "Sold by the chapter on the shop's 話・連載 store. There are no volumes and no "
                "print edition, and the only date the shop states is 更新, the day the latest "
                "chapter went up, which is the most recent publication rather than the first.")
    if row["first_publication_date"]:
        return ("print-base-edition",
                "The earliest 底本発行日 across the work's volumes, which is the publication date "
                "of the print edition the file was made from. A serialised work appeared in a "
                "magazine before its tankōbon and this shop never mentions the magazine, so this "
                "is the earliest publication the shop attests rather than the work's first.")
    if not (row.get("volumes") or []):
        return ("no-volumes-found",
                "The series page listed nothing this capture could read. Nobody has an answer "
                "about this work yet, which is not the same as the shop having none.")
    k = imprint_key((row.get("volumes") or [{}])[0]) or imprint_key(row)
    read, dated = stats.get(k, (0, 0))
    if read >= MIN_IMPRINT_VOLUMES and dated == 0:
        return ("no-print-edition",
                f"Digital-only. The shop states 底本発行日 on none of the {read} volumes it holds "
                f"under {k}, so there is no print edition for it to carry a publication date. The "
                f"absence is the format rather than a gap in the shop's record.")
    if dated:
        return ("no-print-date-stated",
                f"The shop states no 底本発行日 for this work, and {k} does state one on {dated} "
                f"of its {read} volumes elsewhere, so the imprint being digital-only does not "
                f"account for it. Whether a print edition exists is unresolved.")
    return ("print-edition-unknown",
            f"The shop states no 底本発行日 for this work, and it holds too few volumes under {k} "
            f"({read}) to tell a digital-only imprint from a silence. Undecided rather than "
            f"negative.")


def healthy(asked, usable):
    """Whether a pass is worth writing, as `(ok, usable, asked)`.

    A SHARE RATHER THAN "DID WE GET ANYTHING", for the reason openbd_reading.py gives: the failure
    to catch is a TRUNCATED pass and not only an empty one. A loop that dies after forty of nine
    thousand fetches comes back with forty volumes, records them, and reads as a slow day. The
    measured share of volume pages that parse is 100% on every page fetched so far, so half is far
    below a healthy run and far above what a host serving error shells returns.

    `usable` counts pages that stated a TITLE, not pages that stated a date. Those are different
    failures and only the first one is the host's: a volume with no 底本発行日 is the shop declining
    to state a print date, which is an answer and is recorded as one.

    The counter-case, so the floor is not lowered later without thinking: a pass restricted to
    doujin imprints would state no print date on almost every row and still be entirely healthy,
    which is why the floor is not on dates.
    """
    return (asked == 0 or usable * 2 >= asked), usable, asked


# Below this many volume pages the share means nothing: two failures out of three is a floor
# breach on a sample that a single timeout produces. The floor is checked as the pass runs rather
# than only at the end, because a pass that writes for an hour and refuses afterwards has already
# written the hour.
MIN_SAMPLE = 20


def exclusion(vol):
    """Why a volume is excluded, or None. Reuses the designation test rather than restating it.

    THIS IS THE FIRST PAGE TO STATE ANY OF IT. The shelf showed a series title; a volume page
    shows each volume's own title, imprint and publisher. A series admitted on its series title can
    hold a volume marked 【R-18版】
    or issued on an adult imprint, and that volume is where the designation becomes visible.

    THE COUNTER-CASE IS THE WHOLE SHELF. Every volume page on this site carries
    `window.BW_R18_BASE_URL = "https://r18.bookwalker.jp"` in its head, because the shop links its
    adult store from every page it serves. A designation test run over the raw markup would exclude
    all 2,438 rows and report the shelf as pornography. So the test is run over the FIELDS the shop
    states about this book, never over the page.
    """
    import pathlib
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    import shelfingest                                                    # noqa: PLC0415
    from recon import bookwalker_shelf as shelf                           # noqa: PLC0415

    reason = shelfingest.designated({"title": vol.get("title"), "imprint": vol.get("imprint"),
                                     "publisher": vol.get("publisher"),
                                     "genre": vol.get("genre")})
    if reason:
        return reason
    marker = shelf.censored_marker(vol.get("title"))
    if marker:
        return f"the volume title carries a {marker} censorship marker"
    return None


def work_row(row, volumes, completed=None, series_read=False, serial=None):
    """One admitted work as this capture leaves it: its volumes and what they settle.

    `volumes` is every volume this pass read for the work. The order is the shop's on the series
    page, which is not chronological, so the row is sorted by whatever date it has and the sort key
    is stated rather than assumed.

    `serial` is the 話・連載 record where the work is sold by the chapter. Such a work has no
    volumes and no print edition, and filing it as `no-volumes-found` would report the shop's
    silence as this capture's failure. It gets its own basis, because those are different states
    and only one of them is worth another request (STANDING-INSTRUCTIONS §5).
    """
    vols = sorted(volumes, key=lambda v: (v.get("printed") or v.get("delivered") or "9999",
                                          v.get("title") or ""))
    date, basis = first_publication(vols)
    if serial and not vols:
        basis = "chapter-serial-no-publication-date"
    # The venue comes from the volume that SUPPLIED the date, found by the date rather than by
    # position. `vols` is sorted on printed-or-delivered, so its first row can be a volume with no
    # print date at all and an early delivery date, and taking the publisher off that row would
    # attribute the date to a different book (STANDING-INSTRUCTIONS §3: one fact, one derivation).
    dated_vol = next((v for v in vols if v.get("printed") == date), None) if date else None
    return {
        "shop_id": row["shop_id"],
        "url": row["url"],
        "id_kind": "series" if "/series/" in row["url"] else "detail",
        "store": "話・連載" if serial else "単行本",
        "series_read": series_read,
        "volumes_found": len(vols),
        "chapters": (serial or {}).get("chapters"),
        "last_updated": (serial or {}).get("updated"),
        "first_publication_date": date,
        "first_publication_basis": basis,
        # WHERE, WHICH IS WHAT THE SCOPE TEST ACTUALLY ASKS (§6, amended 2026-08-05). The venue and
        # the country are required of every record; the date is recorded where it is attested and
        # its absence is stated where it is not. So the venue is filled for an undated work too,
        # from the publisher the shop names, which it names on every volume.
        "first_publication_venue": ((dated_vol or {}).get("publisher")
                                    or (serial or {}).get("publisher")
                                    or (vols[0].get("publisher") if vols else None)),
        "first_publication_volume": dated_vol.get("title") if dated_vol else None,
        "completed": completed,
        "dates_stated": sum(1 for v in vols if v.get("printed")),
        "isbns_stated": sum(1 for v in vols if v.get("isbn")),
        "imprint": (serial or {}).get("imprint") or (vols[0].get("imprint") if vols else None),
        "publisher": (serial or {}).get("publisher") or (vols[0].get("publisher") if vols
                                                         else None),
        "authors": (serial or {}).get("authors") or (vols[0].get("authors") if vols else []),
        "shop_genre": (serial or {}).get("genre"),
        "volumes": vols,
    }


# ---------------------------------------------------------------------------------------------
# The run. Everything above is pure and tested offline; everything below is I/O and checkpointing.

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.6
# robots.txt permits everything used here for `User-agent: *`. The one rule that touches these
# paths is `Disallow: /de*/?sample=*`, the 試し読み links, which nothing here follows.
ROBOTS_HOST = "bookwalker.jp"

HEADER = """\
# Volume histories for the BOOK☆WALKER rows of data/queue/admitted.yaml. NOT RECORDS.
#
# Keyed by `shop_id`, which is the series number or the volume uuid the admitted row already
# carries, so this joins back without matching titles. Still data/queue/: promotion into
# data/source/ needs the joins and a decision this file does not make.
#
# WHAT THE SHOP STATES.
#   delivered   配信開始日, the day BOOK☆WALKER began selling the file. On all 870 volumes read so
#               far. It is a fact about the shop's stock and NOT a publication of the work: of the
#               276 volumes stating both dates, 115 were delivered BEFORE the print edition, 123 on
#               the day, and 38 after it by up to 4,471 days. It is not a bound in either
#               direction, and it is never used as first_publication.
#   printed     底本発行日, the publication date of the print edition the file was made from. On 276
#               of 870. This IS a publication of the work and it is the only field here that
#               answers DEFINITIONS §6. It tracks the imprint: the print labels state it on every
#               volume, the digital-first labels on none.
#   isbn        Never stated, on any of the 870. The shop sells files. openBD and NDL are both
#               keyed on ISBN, so neither is reachable from this shelf.
#
# A WORK THAT EXISTS IS RECORDED WHETHER OR NOT WE CAN DATE IT (§6, amended 2026-08-05). The scope
# test turns on WHERE, so `venue` and `country` are filled for every row here and the date is
# recorded where the shop attests one. An undated row states WHY, and two of the reasons are not
# the same reason:
#
#   print-base-edition      dated. The earliest 底本発行日 across the work's volumes.
#   no-print-edition        UNDATED AND EXPLAINED. The shop states 底本発行日 on none of the
#                           volumes it holds under this imprint, across the whole capture, so the
#                           title is digital-only and there is no print edition to carry a date.
#                           The absence is the format.
#   chapter-serial          UNDATED AND EXPLAINED. Sold by the chapter on the 話・連載 store: no
#                           volumes, no print edition, and one date, 更新, which is the day the
#                           LATEST chapter went up. Kept apart under `last_updated` and never
#                           promoted, because it answers §6 in the wrong direction.
#   no-print-date-stated    UNDATED AND UNEXPLAINED. The imprint DOES state 底本発行日 elsewhere,
#                           so digital-only does not account for this one. It does not claim a
#                           print edition exists: 百合姫コミックス is a print imprint that also
#                           sells 特装版小冊子電子版 and 【単話】 splits, and those land here.
#   print-edition-unknown   UNDATED AND UNDECIDED. Too few volumes read under the imprint to tell
#                           a digital-only label from a silence.
#   no-volumes-found        not read. The series page listed nothing this pass could parse, which
#                           is this capture having no answer rather than the shop having none.
#
# EVEN print-base-edition IS THE VOLUME'S DATE AND NOT ALWAYS THE WORK'S. A serialised work was
# published in a magazine before its tankōbon and this shop never mentions the magazine.
#
# NO DATE IS EVER INVENTED TO FILL THE FIELD. 配信開始日 stays `delivered` on the volume and is
# never promoted, and the measurement below is why.
#
# EXCLUSIONS ARE COUNTED AND NEVER NAMED, as in admitted.yaml. A volume page shows the volume's
# own title, imprint and publisher, any of which can carry a designation the series title did not.
# `excluded_last_pass` counts what THIS pass met. An excluded row keeps no identifier here, so it
# is not marked done and is met again next pass; withdrawing it belongs in admitted.yaml.
"""


def _write(path, state):
    """Rewrite the whole file from `state`, which must hold every work ever captured.

    REBUILDING FROM ONLY THIS RUN'S FETCHES IS THE FAILURE THIS EXISTS TO PREVENT, and it has cost
    this project earlier work three times. `state["works"]` is loaded from the file at startup and
    only ever added to, so a pass that reaches forty works writes those forty on top of the
    thousands already there rather than in place of them.
    """
    import json
    import pathlib

    def js(v):
        return json.dumps(v, ensure_ascii=False)

    works = state["works"]
    rows = list(works.values())
    # Built once over every row, because the question it answers is about an imprint's record
    # across the whole capture rather than about any one work.
    stats = imprint_print_dates(rows)
    bases = collections.Counter(date_basis(r, stats)[0] for r in rows)
    dated = [r for r in rows if r["first_publication_date"]]
    L = [HEADER.rstrip("\n"), "",
         "source: bookwalker.jp",
         "role: volume-histories",
         "record_type: retailer_volume_capture",
         "from_queue: data/queue/admitted.yaml",
         "key: shop_id",
         f"retrieved: {state['retrieved']}",
         f"admitted_rows: {state['admitted']}",
         f"works_captured: {len(rows)}",
         "counts:"]
    for k, n in [
            ("with_a_date", len(dated)),
            ("undated_no_print_edition", bases["no-print-edition"]),
            ("undated_chapter_serial", bases["chapter-serial"]),
            ("undated_no_print_date_stated", bases["no-print-date-stated"]),
            ("undated_print_edition_unknown", bases["print-edition-unknown"]),
            ("unread_no_volumes_found", bases["no-volumes-found"]),
            ("with_a_venue", sum(1 for r in rows if r["first_publication_venue"])),
            ("volumes_read", sum(r["volumes_found"] for r in rows)),
            ("volumes_with_print_date", sum(r["dates_stated"] for r in rows)),
            ("volumes_with_isbn", sum(r["isbns_stated"] for r in rows)),
            ("marked_completed", sum(1 for r in rows if r["completed"] == "completed"))]:
        L.append(f"  {k}: {n}")
    L.append("fetches:")
    for k in sorted(state["fetches"]):
        L.append(f"  {k}: {state['fetches'][k]}")
    # COUNTS AND REASONS, NO IDENTIFIERS, following what shelfingest.py writes into admitted.yaml.
    # A shop_id resolves to a title through the queue file beside this one, so recording the ids of
    # the rows excluded as pornography would name them by join, which is the thing DEFINITIONS §7
    # forbids. The cost of holding that line is that an excluded row is not marked done and is
    # fetched again on the next pass, which is why the figure is per pass rather than cumulative:
    # accumulating it would multiply the same handful of rows by the number of passes and report a
    # count nobody could reconcile. Withdrawing them belongs in admitted.yaml, not here.
    L.append("excluded_last_pass:")
    for k in sorted(state["excluded"]):
        L.append(f"  {js(k)}: {state['excluded'][k]}")
    L.append("works:")
    for sid in sorted(works):
        r = works[sid]
        basis, note = date_basis(r, stats)
        L.append(f"  - shop_id: {js(r['shop_id'])}")
        for k in ("url", "id_kind", "store", "series_read", "volumes_found", "chapters",
                  "last_updated", "completed", "dates_stated", "isbns_stated",
                  "imprint", "publisher", "authors", "shop_genre"):
            L.append(f"    {k}: {js(r.get(k))}")
        # Shaped as build.py writes it, so a promotion step maps rather than re-derives.
        L.append("    first_publication:")
        L.append(f"      date: {js(r['first_publication_date'])}")
        L.append(f"      date_basis: {js(basis)}")
        L.append(f"      venue: {js(r['first_publication_venue'])}")
        L.append(f"      venue_type: {js(VENUE_TYPE.get(basis))}")
        L.append(f"      venue_volume: {js(r['first_publication_volume'])}")
        L.append(f"      country: {js('JP' if r['first_publication_venue'] else None)}")
        L.append(f"      country_basis: {js(COUNTRY_BASIS if r['first_publication_venue'] else None)}")
        L.append(f"      note: {js(note)}")
        L.append("    volumes:")
        for v in r["volumes"]:
            L.append(f"      - uuid: {js(v.get('uuid'))}")
            for k in ("title", "series_id", "series_title", "authors", "imprint", "publisher",
                      "category", "delivered", "printed", "isbn"):
                L.append(f"        {k}: {js(v.get(k))}")
    L.append("")
    pathlib.Path(path).write_text("\n".join(L))


def _read(path, admitted):
    """Whatever a previous run left, as the state this one continues from."""
    import datetime
    import pathlib

    import yaml

    blank = {"retrieved": datetime.date.today().isoformat(), "admitted": admitted,
             "works": {}, "excluded": {}, "fetches": {}}
    p = pathlib.Path(path)
    if not p.exists():
        return blank
    doc = yaml.safe_load(p.read_text()) or {}
    if not doc.get("works"):
        return blank
    blank["retrieved"] = doc.get("retrieved", blank["retrieved"])
    # Deliberately not carried over. See the note beside `excluded_last_pass` in _write.
    blank["excluded"] = {}
    blank["fetches"] = doc.get("fetches") or {}
    # EVERY ROW IS RE-DERIVED THROUGH `work_row` RATHER THAN LOADED AS IT STANDS. The volumes are
    # what was fetched; everything above them in a row is a summary of the volumes. Loading the
    # summary back verbatim would leave rows written by an older version of this module disagreeing
    # with rows written after it, in a file where nothing forces the two to agree, which is the
    # shape of seven bugs in this project's history (STANDING-INSTRUCTIONS §3). Re-deriving costs
    # nothing, needs no migration, and makes the summary provably a function of the volumes.
    for w in doc["works"]:
        serial = ({"chapters": w.get("chapters"), "updated": w.get("last_updated"),
                   "imprint": w.get("imprint"), "publisher": w.get("publisher"),
                   "authors": w.get("authors"), "genre": w.get("shop_genre")}
                  if w.get("store") == "話・連載" else None)
        blank["works"][str(w["shop_id"])] = work_row(
            {"shop_id": w["shop_id"], "url": w["url"]}, w.get("volumes") or [],
            w.get("completed"), w.get("series_read"), serial)
    return blank


def main(argv=None):
    """Ask each admitted work's own pages for its volumes and their dates, resumably."""
    import argparse
    import pathlib
    import sys
    import time
    import urllib.request

    import yaml

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from recon import bookwalker_shelf as shelf                           # noqa: PLC0415
    from recon import probe                                              # noqa: PLC0415
    import bookwalker                                                    # noqa: PLC0415

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--queue", default="data/queue/admitted.yaml")
    ap.add_argument("--out", default="data/queue/bookwalker-volumes.yaml")
    ap.add_argument("--pause", type=float, default=PAUSE)
    ap.add_argument("--max-fetches", type=int, default=200,
                    help="requests this pass. The capture resumes, so a cap is a budget and "
                         "never a truncation.")
    ap.add_argument("--spread", action="store_true",
                    help="walk the outstanding rows evenly across the queue instead of from the "
                         "front. The queue is sorted by title, and a capped pass down it measures "
                         "the start of the alphabet rather than the shelf.")
    a = ap.parse_args(argv)

    q = yaml.safe_load(pathlib.Path(a.queue).read_text())
    rows = [w for w in q["works"] if w.get("shop") == "bookwalker.jp"]
    st = _read(a.out, len(rows))
    todo = [r for r in rows if str(r["shop_id"]) not in st["works"]]
    if a.spread:
        # WHY THE ORDER MATTERS FOR A CAPPED PASS. admitted.yaml is sorted by title, and title
        # order is not random with respect to imprint: the symbols and Latin titles at the front
        # are largely digital-first doujin labels, which state no print date. A pass down the
        # front of the queue therefore measures the front of the alphabet and reports it as the
        # shelf. Interleaving costs nothing and makes the share it observes mean something.
        step = max(1, len(todo) // max(1, a.max_fetches))
        todo = [r for i, r in enumerate(todo) if i % step == 0] if step > 1 else todo
    print(f"{len(rows)} admitted BOOK☆WALKER rows, {len(st['works'])} already captured, "
          f"{len(todo)} to go; budget {a.max_fetches} requests this pass"
          f"{', spread across the queue' if a.spread else ''}")

    # ROBOTS IS ASKED BEFORE THE FIRST REQUEST, not remembered from the last run. probe.py was
    # truncating disallow lists to twelve rules and reporting a forbidden endpoint as permitted,
    # which sent three rounds of author lookups down a route robots refuses. Asking here costs one
    # request and is the only thing that makes the permission observed rather than assumed.
    rules = probe.robots_rules(ROBOTS_HOST)
    for path in ("/series/1/list/", "/de00000000-0000-0000-0000-000000000000/"):
        if rules["present"] and not probe.allowed(path, rules["disallow"]):
            print(f"Refusing to fetch: robots.txt disallows {path} for User-agent: *.")
            return 1
    print(f"robots.txt: {len(rules['disallow'])} rules for User-agent: *, none covering "
          f"/series/ or /de<uuid>/")

    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read().decode("utf-8", "replace")

    # Counted for this pass only. The floor is a statement about the pass that just ran, so a
    # healthy history must not be able to carry a broken pass over the line.
    fetched = parsed = unparsed = 0
    st["fetches"].setdefault("volume_pages_unusable_total", 0)

    def volume_page(uuid):
        """One volume page as a record, counting the unusable ones so the floor can see them."""
        nonlocal fetched, parsed, unparsed
        html_text = get(f"https://bookwalker.jp/de{uuid}/")
        fetched += 1
        time.sleep(a.pause)
        v = volume(html_text, uuid)
        if v:
            parsed += 1
        else:
            unparsed += 1
            st["fetches"]["volume_pages_unusable_total"] += 1
        return v

    def thin():
        """Whether the pass has gone bad, checked as it runs rather than after it."""
        n = parsed + unparsed
        return n >= MIN_SAMPLE and not healthy(n, parsed)[0]

    stopped = None
    for row in todo:
        if fetched >= a.max_fetches:
            stopped = "budget"
            break
        if thin():
            stopped = "thin"
            break
        sid = str(row["shop_id"])
        vols, completed, series_read, listed, serial = [], None, False, 0, None
        try:
            if "/series/" in row["url"]:
                page = get(f"https://bookwalker.jp/series/{sid}/list/")
                fetched += 1
                time.sleep(a.pause)
                series_read = True
                completed = (bookwalker.status(page, row["title"])
                             or bookwalker.status_from_list(page, row["title"]))
                uuids = [r["id"] for r in shelf.parse_listing(page)
                         if r["id_kind"] == "detail" and r["id"]]
                if not uuids:
                    # No volume list. Either the 話・連載 store, whose template this is, or a
                    # series page that changed shape. `warensai` tells those apart by whether the
                    # page states a 話・連載 card, so a changed template stays a failure rather
                    # than being filed as a chapter serial.
                    serial = warensai(page, sid)
                listed = len(uuids)
                for u in uuids:
                    if fetched >= a.max_fetches or thin():
                        stopped = "budget" if fetched >= a.max_fetches else "thin"
                        break
                    v = volume_page(u)
                    if v:
                        vols.append(v)
            else:
                listed = 1
                v = volume_page(sid)
                if v:
                    vols.append(v)
        except Exception as e:                                            # noqa: BLE001
            print(f"  {sid}: {type(e).__name__}; left for the next pass")
            continue
        if stopped:
            # A work whose volumes were cut short by the budget or by the floor is left for the
            # next pass entire. Writing the half of it that was read would file a nine-volume
            # series as a two-volume one, and the row would then be `done` and never revisited.
            break
        if not vols and not serial:
            # Either every volume page failed to parse, or a series page listed no volumes and
            # carried no 話・連載 card either. Both are the host or a changed template rather than
            # a work with nothing to say, and recording one would put a row in the file asserting
            # the shop states nothing about a work it states plenty about.
            print(f"  {sid}: {listed} volume page(s) and no serial card; left for the next pass")
            continue
        # A designation the shelf could not show. Counted with its reason, and the title is not
        # written into this repository (DEFINITIONS §7).
        reasons = {r for r in (exclusion(v) for v in (vols + ([serial] if serial else []))) if r}
        if reasons:
            for r in sorted(reasons):
                st["excluded"][r] = st["excluded"].get(r, 0) + 1
            print(f"  {sid}: excluded, {len(reasons)} reason(s)")
            continue
        st["works"][sid] = work_row(row, vols, completed, series_read, serial)
        # Checkpointed per work rather than at the end, so an interrupted pass loses one work.
        _write(a.out, st)

    ok, got, asked = healthy(parsed + unparsed, parsed)
    print(f"HEALTH: {got} of {asked} volume page(s) stated a title")
    if not ok:
        print(f"Refusing to write: {got} of {asked} volume pages parsed, under the "
              "half a healthy pass clears. That is the host serving something other than a book "
              "page, or a fetch that stopped partway, and both look identical from here. What was "
              "already in the file is left as it was.")
        return 1

    st["fetches"]["last_pass_requests"] = fetched
    st["fetches"]["last_pass_volumes"] = parsed
    _write(a.out, st)
    rows_done = list(st["works"].values())
    dated = sum(1 for r in rows_done if r["first_publication_date"])
    left = len(rows) - len(st["works"]) - sum(st["excluded"].values())
    print(f"{len(st['works'])} works captured ({dated} with a first publication date, "
          f"{len(st['works']) - dated} without), {fetched} requests this pass, "
          f"{sum(st['excluded'].values())} excluded, {left} rows left -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
