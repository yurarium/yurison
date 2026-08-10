#!/usr/bin/env python3
"""The tankobon record for a work, from the National Diet Library.

WHY THIS EXISTS. 92 works sit at `state: dormant`, which rests on silence. Every route we have for
turning that silence into an answer is pointed at works that still move: the antenna drops a series
when it stops updating, so not one of the 92 carries a 完結 tag; COMIC FUZ, which holds a dozen of
them, publishes no serialisation status at all; and our own tankobon corpus is a single imprint, so
it reaches none of the 芳文社 and 講談社 works in the list.

NDL reaches all of them. It is a national library, it is free, and it holds every book published in
Japan, so it answers the one question none of those routes can: is the publisher still issuing
volumes of this series. 2DK、Gペン、目覚まし時計。 sat at the top of the dormant list, and its
eighth and last volume came out in January 2019.

WHAT IT IS EVIDENCE OF. Not completion. A series that has stopped appearing in print may still be
running online: at least one major title has announced exactly that, continuing on the web with no
further tankobon. So a stopped volume run is weighed rather than obeyed, and it is decisive only
where the serialisation is silent too. Where the platform says the work is running, the same record
means the print edition ended and the story did not.

DISAMBIGUATION IS THE HARD PART. A title search for `citrus+` returns two volumes of an unrelated
book from 2007. So a record counts only where the creator agrees with the author we hold, and a
work whose author we do not know gets no answer rather than a guess.
"""
import re
import unicodedata
import htmlbits as _htmlbits                                            # noqa: E402

ITEM = _htmlbits.RSS_ITEM
MANGA = "漫画"


def _tag(item, name):
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", item, re.S)
    return (m.group(1).strip() if m else "")


def _fold(s):
    """Comparison form for an author name: width-folded, spaces removed."""
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").replace("　", "").lower()


def volumes(xml, author=None):
    """The manga volumes NDL holds under this search, newest last.

    `author` is required to mean anything. Without agreement on who made it, a title search is a
    string match against every book in Japan, and the answer it gives is confident and wrong.
    """
    out = []
    for item in ITEM.findall(xml or ""):
        if MANGA not in _tag(item, "dcndl:genre"):
            continue
        isbn = _tag(item, r"dc:identifier[^>]*dcndl:ISBN")
        if not isbn:
            m = re.search(r'<dc:identifier[^>]*ISBN[^>]*>(.*?)</dc:identifier>', item, re.S)
            isbn = m.group(1).strip() if m else ""
        if not isbn:
            continue
        creator = _tag(item, "dc:creator")
        if author and _fold(author) not in _fold(creator) and _fold(creator) not in _fold(author):
            continue
        issued = _tag(item, "dcterms:issued")
        vol = _tag(item, "dcndl:volume")
        out.append({"volume": vol, "issued": issued, "isbn": isbn,
                    "publisher": _tag(item, "dc:publisher"), "creator": creator,
                    "title": _tag(item, "dc:title")})
    out.sort(key=lambda v: (v["issued"], v["volume"]))
    return out


def run(xml, author=None):
    """What the volume record says about the series, or None where it says nothing.

    `last_issued` is the fact worth having. The count is reported as what NDL holds rather than as
    the length of the series, because a library's holdings are not a publisher's catalogue and a
    missing volume would otherwise become an assertion about the work.
    """
    v = volumes(xml, author)
    if not v:
        return None
    return {"held": len(v), "first_issued": v[0]["issued"], "last_issued": v[-1]["issued"],
            "last_volume": v[-1]["volume"] or None, "publisher": v[-1]["publisher"],
            "last_isbn": v[-1]["isbn"]}


def main(argv=None):
    """Ask NDL for the volume record of every work in a state that rests on silence."""
    import argparse, datetime, json, pathlib, time, urllib.parse, urllib.request

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--series", default="data/build/series.json")
    ap.add_argument("--out", default="data/coverage/ndl-volumes.yaml")
    ap.add_argument("--state", default="dormant")
    ap.add_argument("--pause", type=float, default=1.5)
    a = ap.parse_args(argv)

    works = [w for w in json.loads(pathlib.Path(a.series).read_text())["series"]
             if w.get("state") == a.state]
    ua = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
    rows, no_author, silent = [], 0, 0
    for w in works:
        author = (w.get("author") or "").strip()
        if not author:
            no_author += 1
            continue
        url = ("https://ndlsearch.ndl.go.jp/api/opensearch?cnt=50&title="
               + urllib.parse.quote(w["work"]))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=40) as r:
                xml = r.read().decode("utf-8", "replace")
        except Exception as e:                                              # noqa: BLE001
            print(f"  skip {w['work'][:24]}: {e}")
            continue
        got = run(xml, author)
        if got:
            rows.append(dict(got, work=w["work"], author=author,
                             latest_chapter=w.get("latest")))
        else:
            silent += 1
        time.sleep(a.pause)

    js = lambda v: json.dumps(v, ensure_ascii=False)                        # noqa: E731
    L = ["# The tankobon record from the National Diet Library for works whose state rests on",
         "# silence.",
         "#",
         "# EVIDENCE, NOT A VERDICT. A publisher stopping is not the same as a story stopping: a",
         "# series can carry on online with no further volumes, and at least one has announced",
         "# exactly that. So `last_issued` decides nothing on its own. Read beside a silent",
         "# serialisation it is strong; read beside a platform that says the work is running it",
         "# means the print edition ended and the story did not.",
         "#",
         "# A record counts only where NDL's creator agrees with the author we hold, because a",
         "# title search matches every book in Japan and `citrus+` returns an unrelated 2007 book.",
         "source: ndlsearch.ndl.go.jp", "role: volume-record", "source_kind: national-library",
         f"retrieved: {datetime.date.today().isoformat()}",
         f"queried: {len(works)}", f"no_author: {no_author}", f"no_record: {silent}", "works:"]
    for r in sorted(rows, key=lambda x: x["last_issued"]):
        L.append(f"  - work: {js(r['work'])}")
        L.append(f"    author: {js(r['author'])}")
        L.append(f"    volumes_held: {r['held']}")
        L.append(f"    first_issued: {js(r['first_issued'])}")
        L.append(f"    last_issued: {js(r['last_issued'])}")
        if r.get("last_volume"):
            L.append(f"    last_volume: {js(r['last_volume'])}")
        L.append(f"    publisher: {js(r['publisher'])}")
        L.append(f"    last_isbn: {js(r['last_isbn'])}")
        L.append(f"    latest_chapter: {js(r.get('latest_chapter'))}")
    L.append("")
    pathlib.Path(a.out).write_text("\n".join(L))
    print(f"{len(rows)} of {len(works)} {a.state} works have a volume record "
          f"({no_author} lack an author, {silent} returned nothing) -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
