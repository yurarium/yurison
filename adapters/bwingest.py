#!/usr/bin/env python3
"""BOOK☆WALKER's yuri shelf as work records, joined presumptively and reviewed after.

WHY THIS IS DIFFERENT FROM THE cmoa ROUTE. コミックシーモア states ISBNs, so its works entered
through `by_isbn.py`: the shop said which edition, and the national bibliography supplied the
record. BOOK☆WALKER states none, on any of 5,709 volumes read, because it sells files. There is no
catalogue record to fetch, so what the shop says is all there is.

THE DECISION THIS RESTS ON, taken by the project owner on 2026-08-06: join presumptively and watch
for edge cases, because being wrong later about a small number of works does not outweigh holding
two thousand more. So a title that matches nothing enters as a new work on the shop's own listing,
and a title that matches something we already hold does NOT merge: it goes to a review queue.
Titles are spellings, ids are identifiers, and トワ・エ・モア is what happens when the two are
confused.

WHAT A RECORD FROM HERE CLAIMS, AND WHAT IT DOES NOT. It claims the work exists, that this shop
sells it, who the shop credits, and the print date where the shop states one. It claims no
marketing_label: a shop's genre shelf is never publisher-side (DEFINITIONS §4), so admission is
under §2's third branch and `admitted_by` names the shelf. The date is the shop's 底本発行日 where
it prints one, and where it does not the row says why rather than borrowing the delivery date,
which is a fact about the shop's stock.
"""
import pathlib
import re
import sys
# `adapters/` ON THE PATH BEFORE THE FACT IS IMPORTED, at module level and not inside main().
# This file already inserted it, 190 lines down in a function, while the imports it is for run
# at import time. It worked in every shell here because PYTHONPATH is set in all of them.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[0]))

from names import credits as _credits  # noqa: E402
from facts import inclusion as _inclusion  # noqa: E402
from facts import volumenumber as _volnum  # noqa: E402

SHOP = "bookwalker.jp"
# ONE HOME FOR WHAT A SHOP'S YURI SHELF IS CALLED (§3): this and `madb/by_isbn.SHELVES` each said
# what bookwalker's shelf is, and each wrote out the sentence explaining what a shelf admits.
SHELF = _inclusion.shelf_of(SHOP)

# A volume title carrying its own number: `作品名 3`.
VOLUME_SUFFIX = re.compile(r"\s*(?:第\s*)?\d+\s*(?:巻)?\s*$")

# WHAT MARKS THE NUMBER OFF FROM THE NAME. 22 titles in the corpus end in a digit and most of those
# digits are the name: `魔法少女201`, `あやめ14`, `Smile0`, `P-0004`, `ラブフェロモンNo.5`. What the
# volume numbers have that those lack is a boundary. A space is one, 第 is one, and a sentence-final
# mark is one, so `ふぉーおぶあかいんど！2` is volume 2 and `あやめ14` is a girl's name and an age.
#
# AND A FULL-WIDTH DIGIT IS ITS OWN BOUNDARY. `うどみょん１` is glued straight to the kana with no
# mark at all, and BOOK☆WALKER writes it full-width, as it does for every volume number it sets in
# a Japanese title. Every one of the digits that is part of a name is half-width.
_N = r"[\s　]*(?:第[\s　]*)?[0-9０-９]+[\s　]*巻?[\s　]*$"
NUMBERED_OFF = re.compile(rf"(?P<keep>[！？。、]){_N}|[\s　]+(?:第[\s　]*)?[0-9０-９]+[\s　]*巻?[\s　]*$"
                          rf"|第{_N}|[０-９]+[\s　]*巻?[\s　]*$")

# 集 IS THE WORD THE NUMBER COUNTS. `乙女ホリック 再録集4` is the fourth of ギロチン銀座's 再録集 and
# `乙女ホリック` is not a work; seven of the nine single-volume titles ending in a digit are this,
# which is why the count of volumes could never have decided it. They all have exactly one.
COUNTED_BY = re.compile(r"集\s*$")


# A bracketed imprint on the end of a title: `雪解けとアガパンサス（電撃コミックスNEXT）`. 771 of
# 2,093 carry one, because BOOK☆WALKER labels the edition in the volume's name. The imprint is a
# field of its own, and leaving it in the title put a Latin imprint inside a Japanese work's
# reading: `ヒメチャン ワ オモイ オンナ （fuz コミックス）`.
IMPRINT_TAIL = re.compile(r"[（(][^）)]{2,30}?(?:コミックス|コミック|COMICS|comics|文庫|"
                          r"ノベルス|BOOKS|books)[^）)]{0,12}[）)]\s*$")


# Any trailing bracket, which is only a label if the record itself says so.
ANY_TAIL = re.compile(r"[（(]([^）)]{1,24})[）)]\s*$")


def strip_imprint(title, publisher=None, imprint=None):
    """`(title, imprint)`: the work's name, and the edition label the shop put in it.

    A WORD IN BRACKETS IS ONLY A LABEL IF THE RECORD SAYS IT IS. Matching on a list of words that
    look like imprints caught `（電撃コミックスNEXT）` and missed `（ナンバーナイン）`, `（百合コレ）`
    and `（orSiS）`, which are publishers and imprints carrying no such word: 938 titles end in a
    bracket and 933 of those brackets hold the record's OWN publisher or imprint. So the record
    answers the question about itself.

    The five that do not are left alone, and they are why this cannot be done by pattern alone:
    `白き乙女の人狼（ウェアウルフ）` is a reading gloss and part of the title, and `（英語版）` says
    which edition a volume is.
    """
    raw = (title or "").strip()
    m = ANY_TAIL.search(raw)
    if not m:
        return raw, None
    label = m.group(1).strip()
    for own in (imprint, publisher):
        own = (own or "").strip()
        if own and (label == own or label in own or own in label):
            return raw[:m.start()].strip(), label
    # Not this record's own label. It may still be an edition line naming a comics imprint.
    if IMPRINT_TAIL.search(raw):
        return raw[:m.start()].strip(), label
    return raw, None


def title_of(work):
    """The work's title: the series name where the shop groups it, else the single volume's own.

    284 of 2,423 rows read no volumes at all and have no title anywhere. Those are works the
    capture could not open, not works without a name, and they are skipped rather than invented.

    A SHOP HOLDING ONE VOLUME STILL NUMBERS IT. `うどみょん１` reached the works list under that
    name, volume number and all, because the number was only stripped from works with more than one
    volume, and a doujin the shop stocks one volume of has one. Its own reading note said "apart
    from the volume number" while the title kept it. What decides is the word before the number.
    """
    vols = work.get("volumes") or []
    if not vols:
        return ""
    series = (vols[0].get("series_title") or "").strip()
    if series:
        return series
    return without_volume_number((vols[0].get("title") or "").strip())


def without_volume_number(title):
    """`title` with a trailing volume number removed, where the number is the volume's and not the
    work's. A title that is nothing but its number keeps it, having no name left otherwise."""
    m = NUMBERED_OFF.search(title)
    if not m or not m.start():
        return title
    kept = m.group("keep") or ""
    head = title[:m.start()].strip()
    if not head or COUNTED_BY.search(head):
        return title
    return head + kept


# A release sold one chapter at a time. 単話 and 単話版 are exactly that, and 分冊版 is a volume
# split into parts sold separately. Neither is a 巻.
CHAPTERWISE = re.compile(r"【\s*(?:単話|単話版|分冊版|話売り)\s*】|\[\s*(?:単話|分冊版)\s*\]")


def chapterwise(title):
    """Whether the shop sells this one chapter at a time, by its own marking on the title."""
    return bool(CHAPTERWISE.search(title or ""))


def volumes_of(work, series=None):
    """`[{number, published, delivered}]`, dated by the print edition and never by the file.

    `delivered` is the day the shop began selling the file and runs years late on a back catalogue,
    so it is recorded and never promoted to a publication date. `printed` is 底本発行日, the print
    edition this file was made from, which is a publication of the work.

    THE NUMBER IS THE ONE THE SHOP WROTE, AND WAS THE ITEM'S POSITION IN THE LISTING. `enumerate`'s
    index went out as the volume number, and a shop listing is neither a volume list nor in volume
    order: BOOK☆WALKER sells 32 products under MURCIÉLAGO, three of them free samples of volumes
    already in it, so the corpus published a 29 volume series as 32 volumes and invented 30, 31 and
    32. パロスの剣 lists `【最新刊】…3巻` first, so volume 3 went out as volume 1. 54 records
    disagreed with their own product titles. `facts/volumenumber` reads the title against the
    series name and answers None where the shop did not say, which the interface already draws.

    A FREE SAMPLE IS NOT A VOLUME and is dropped here, the way `chapterwise` drops 単話 and 分冊版
    for the same reason: it is a product, and the question is how long the work is.
    """
    out = []
    for v in work.get("volumes") or []:
        title = (v.get("title") or "").strip()
        if _volnum.is_sample(title):
            continue
        row = {"number": _volnum.stated(title, series), "title": title}
        # AND WHAT IT IS CALLED WHERE THAT IS NOT A NUMBER. `2017年1月号` is a label and
        # `お昼のメガネさん` is a whole other name under a shop umbrella; both are what the record
        # says about this instalment and neither is a position in a run. Carried whole, because
        # the alternative is a work page counting 119 rows and listing none of them.
        if not row["number"]:
            got = _volnum.designation(title, series)
            if got:
                row["designation"] = got
        if v.get("printed"):
            row["published"] = str(v["printed"])[:10]
        if v.get("delivered"):
            row["delivered"] = str(v["delivered"])[:10]
        out.append(row)
    return out


def _volume_count(vols):
    """How many volumes these products are: distinct stated numbers, plus the ones nobody numbered.

    THE FIRST VERSION COUNTED DISTINCT NUMBERS ALONE AND WAS WRONG, which the shop said straight
    away: 魔法少女三十路 lists seven volumes and states a number on one of them, so it came out as
    one volume where コミックシーモア says seven, and 17 works moved into `works holding fewer
    volumes than the shop states` on the strength of it. A volume nobody numbered is still a
    volume; what it lacks is a name for its place in the run.

    WHAT THE DISTINCT COUNT IS FOR is a listing that carries one volume twice, which is why the
    numbered half is not simply counted either.
    """
    stated = {v["number"] for v in vols if v.get("number")}
    return len(stated) + sum(1 for v in vols if not v.get("number"))


def record(work, retrieved):
    """One work as a source record, or None where the capture read nothing about it."""
    title, from_title = strip_imprint(title_of(work), work.get("publisher"), work.get("imprint"))
    if not title:
        return None
    # THE SERIES NAME THE VOLUME TITLES CARRY, which is the shop's own and not the one `title_of`
    # derives: a series filed as `さかさまロリポップ（まんがタイムKRコミックス）` names its volumes
    # `さかさまロリポップ　１巻`, so the imprint has to come off before the two can be compared. It
    # is 3,634 of 4,792 rows that miss otherwise, which is most of them.
    _series = (work.get("volumes") or [{}])[0].get("series_title")
    _series, _ = strip_imprint(_series, work.get("publisher"), work.get("imprint"))
    vols = volumes_of(work, _series)
    # WHAT THE SHOP SELLS ONE CHAPTER AT A TIME IS NOT A SET OF VOLUMES.
    # 付き合ってあげてもいいかな【単話】 lists 133 items and the shop numbers them （１） to （133）:
    # they are chapters sold individually, and calling them 第1巻 to 第133巻 says the work is 133
    # volumes long. 24 works and 496 items are in that state.
    by_chapter = chapterwise(title_of(work))
    dated = [v["published"] for v in vols if v.get("published")]
    fp = work.get("first_publication") or {}
    return {
        "chapterwise": by_chapter,
        # A chapter-wise release has no volumes to count, and its items keep their own dates so
        # nothing about when it published is lost.
        "chapter_count": len(vols) if by_chapter else 0,
        "title": title,
        "shop_id": work.get("shop_id"),
        "url": work.get("url"),
        # A CAPTURED AUTHOR THAT CANNOT BE A NAME IS NOT ONE. The shelf gave `７` as the creator
        # of four books, one of them published by ななつぼし, which is a fragment of the listing
        # read into the author slot. Dropping it leaves the work with no credit, which is what we
        # actually know, and `works crediting nobody` counts that where a wrong name would not be
        # counted at all.
        "creator": " / ".join(a for a in (work.get("authors") or []) if _credits.is_a_person(a)),
        "publisher": work.get("publisher"),
        # The shop's own imprint field where it has one, else the label it wrote into the title.
        "imprint": work.get("imprint") or from_title,
        # HOW MANY VOLUMES, NOT HOW MANY PRODUCTS. The distinct numbers where the shop states
        # them, because a listing repeats a volume under a second cover; the count of items only
        # where it states none, which is the best that can be said about a set nobody numbered.
        "volume_count": 0 if by_chapter else _volume_count(vols),
        # WHAT THE SHOP SAYS THIS IS. BOOK☆WALKER writes `[雑誌]` after an issue's title, and it
        # is the only thing in reach that says what a product IS rather than what it is called.
        # A work page calling 117 issues of コミック百合姫 `収録巻` claims a numbering they have
        # never had; see `volumenumber.is_periodical` for why nothing here infers it.
        "periodical": any(_volnum.is_periodical(v.get("title")) for v in vols),
        "volumes": [] if by_chapter else vols,
        "chapters": vols if by_chapter else [],
        "first_published": min(dated) if dated else None,
        "date_basis": None if dated else (fp.get("date_basis") or "no-date-attested"),
        "venue": fp.get("venue") or work.get("publisher"),
        "completed": bool(work.get("completed")),
    }


def split(records, held):
    """`(new, review)`: works whose title we do not hold, and works whose title we already do.

    A MATCHING TITLE IS THE STRONGEST LEAD HERE AND THE WEAKEST KIND OF EVIDENCE, so it decides
    which pile a work lands in and never decides a merge. The review
    pile is small by construction and is where a person settles whether two records are one work.
    """
    new, review = [], []
    for r in records:
        (review if r["_key"] in held else new).append(r)
    return new, review


def main(argv=None):
    import argparse
    import json
    import sys

    import yaml

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from build import norm_work                                              # noqa: E402

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", default="data/queue/bookwalker-volumes.yaml")
    ap.add_argument("--build", default="data/build")
    ap.add_argument("--out", default="data/source/bookwalker")
    ap.add_argument("--review", default="data/queue/bw-review.yaml")
    a = ap.parse_args(argv)

    doc = yaml.safe_load(pathlib.Path(a.capture).read_text()) or {}
    retrieved = str(doc.get("retrieved") or "")
    records = []
    skipped = 0
    for w in (doc.get("works") or []):
        r = record(w, retrieved)
        if r is None:
            skipped += 1
            continue
        r["_key"] = norm_work(r["title"])
        records.append(r)

    # WHAT WE HOLD FROM SOMEWHERE ELSE. titles.json is the build stating its corpus (GAPS §12), and
    # after the first run of this pass that corpus INCLUDES what this pass wrote. Compared against
    # it raw, every record looked like a duplicate of itself on the second run: 2,093 new works
    # became 415, with 1,724 filed for review against their own entries. So this pass subtracts its
    # own previous output, and the question stays "does anything BUT BOOK☆WALKER know this title".
    titles = json.loads((pathlib.Path(a.build) / "titles.json").read_text()).get("titles") or []
    held = {norm_work(t) for t in titles}
    mine = set()
    for f in pathlib.Path(a.out).glob("*.yaml"):
        prev = yaml.safe_load(f.read_text()) or {}
        got = (prev.get("title") or {}).get("ja")
        if got:
            mine.add(norm_work(got))
    held -= mine
    new, review = split(records, held)

    js = lambda v: json.dumps(v, ensure_ascii=False)                          # noqa: E731
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # ONE FILE PER WORK, which is what load_dir reads and what data/source/madb already is.
    for f in out.glob("*.yaml"):
        f.unlink()
    for r in new:
        wid = "bw-" + str(r["shop_id"])
        L = ["# Source-layer record. Stored as fetched; never hand-edited (REQUIREMENTS §5).",
             "#",
             "# BOOK☆WALKER states no ISBN, so no catalogue record stands behind this one: what the",
             "# shop says is all there is. Joined presumptively on its title, and a title that",
             "# already names a work we hold went to data/queue/bw-review.yaml instead of here.",
             "source: bookwalker", f"retrieved: {retrieved}",
             f"work_id: {js(wid)}", "record_type: retailer_work_record",
             f"shop_id: {js(r['shop_id'])}", f"shop_url: {js(r['url'])}",
             "title:", f"  ja: {js(r['title'])}",
             f"creator: {js(r['creator'] or '')}",
             f"publisher: {js(r['publisher'] or '')}",
             f"imprint: {js(r['imprint'] or '')}",
             f"volume_count: {r['volume_count']}"]
        # A release the shop sells one chapter at a time says so, and says how many, so nothing
        # downstream has to infer it from a volume count of zero.
        if r.get("chapterwise"):
            L += ["chapterwise: true", f"chapter_count: {r['chapter_count']}"]
        # The shop's own word for what these are, written only where it said so.
        if r.get("periodical"):
            L.append("periodical: true")
        if r.get("first_published"):
            L.append(f"first_published: {js(r['first_published'])}")
        else:
            L.append(f"date_basis: {js(r['date_basis'])}")
        L.append(f"venue: {js(r['venue'] or '')}")
        L.append(f"completed: {js(r['completed'])}")
        L.append("volumes:")
        for v in r["volumes"]:
            L.append(f"  - title: {js(v['title'])}")
            for k in ("number", "designation", "published", "delivered"):
                if v.get(k) is not None:
                    L.append(f"    {k}: {js(v[k])}")
        # §2's third branch: a licensed retailer's yuri shelf is a comparator, and §4 keeps a
        # shop's shelf out of marketing_label however strong a lead it is.
        L += _inclusion.admitted_by([SHOP], retrieved, quote=js)
        L += [
              "marketing_label: none",
              "marketing_label_basis:",
              "  source: bookwalker",
              f"  url: {js(r['url'])}",
              f"  retrieved: {retrieved}",
              "  note: >-",
              "    Admitted on BOOK☆WALKER's yuri shelf. A shop's shelf is never publisher-side",
              "    labelling (§4), so this axis stays `none`, which says nothing about content.",
              ""]
        (out / f"{wid}.yaml").write_text("\n".join(L))

    R = ["# BOOK☆WALKER works whose title already names something we hold. NOT merged: a title is",
         "# the strongest lead available here and the weakest kind of identifier, and トワ・エ・モア",
         "# is one title over two unrelated works. Each of these needs a person to say whether the",
         "# two records are one work.",
         f"retrieved: {retrieved}", f"pending: {len(review)}", "works:"]
    for r in sorted(review, key=lambda x: x["title"]):
        R.append(f"  - title: {js(r['title'])}")
        for k in ("shop_id", "url", "creator", "publisher", "volume_count", "first_published"):
            if r.get(k) is not None:
                R.append(f"    {k}: {js(r[k])}")
    R.append("")
    pathlib.Path(a.review).write_text("\n".join(R))

    print(f"BOOK☆WALKER: {len(records)} works read, {skipped} skipped with nothing captured")
    print(f"  new records      : {len(new)} -> {a.out}")
    print(f"  titles we hold   : {len(review)} -> {a.review}, for review rather than merge")
    print(f"  dated by the shop: {sum(1 for r in new if r.get('first_published'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
