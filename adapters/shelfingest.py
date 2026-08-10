#!/usr/bin/env python3
"""Retailer shelf rows into work records, on the designation test and nothing else.

WHY THIS EXISTS. 4,303 rows sat in data/queue/ admitted to nothing, because the question standing
in front of them was "is this pornography", which is subjective and cannot be answered in the
binary. DEFINITIONS §7 was amended on 2026-08-05 to say the test is a DESIGNATION and never a
judgement, and this applies that and only that.

WHAT EXCLUDES A WORK. A designation somebody else made: the shop's own adult genre, an adult
imprint, an R-18 or 18禁 marking. Nothing here reads a title and forms a view.

WHAT DOES NOT EXCLUDE A WORK, and this is the change that admits most of them. Doujinshi is a
publication mode, not a content classification: most yuri doujinshi is R-18 and the designation
already excludes it, so a doujin row carrying no designation enters on the same terms as a
commercial one. Excluding the category would drop admissible works to spare us a judgement.

WHAT IS RECORDED INSTEAD OF DECIDED. `age_gated` per retailer, from the shop's own shelving, so a
publisher whose output is adult-adjacent is described rather than adjudicated. Where the content is
explicit the work carries `explicit_content` and stays out of default views. Three dispositions
rather than two is what lets the line hold without a rule reading "we thought it looked like
pornography".

A BIBLIOGRAPHIC RECORD IS NOT THE WORK. A title and a publisher may be held for something no page
of which would ever be shown, and build.py already refuses a cover on an explicit record.
"""
import re
import unicodedata

# A designation somebody else made. Each is a fact recorded by a shop or printed on a volume.
ADULT_GENRE = ("アダルト", "アダルトマンガ")
ADULT_MARK = re.compile(r"R-?18|18禁|成人向|成年コミック")
# Publisher lines that ARE the designation, because the publisher runs them as its adult imprint.
ADULT_IMPRINT = ("Ghost Ship", "秋水社ORIGINAL", "ヤングアンリアル")

# Explicit without being designated: §7's middle band, included and flagged.
EXPLICIT = re.compile(r"えっち|エッチ|セフレ|レズ風俗|官能|ラブスレイブ|ハーレム肉便器")


def width(s):
    return unicodedata.normalize("NFKC", str(s or "")).strip()


def designated(row):
    """Why this row is excluded, or None. Only a designation counts."""
    g = width(row.get("genre"))
    if any(a in g for a in ADULT_GENRE):
        return f"the shop files it under {g}"
    for f in ("imprint", "publisher"):
        v = width(row.get(f))
        if any(a.lower() in v.lower() for a in ADULT_IMPRINT):
            return f"published on {v}, an adult imprint"
    for f in ("title", "imprint"):
        if ADULT_MARK.search(width(row.get(f))):
            return "carries an R-18 or 成年 marking"
    return None


def age_gated(row, shop):
    """What the shop did with it, recorded rather than judged.

    `gated` where the shop put it behind its adult shelf, `open` where it stocked it openly. Both
    shelves captured here are the shop's ALL-AGES yuri listing, so a row reaching this module was
    stocked openly by definition; the value still says which shop said so.
    """
    return {"shop": shop, "state": "gated" if designated(row) else "open"}


def explicit(row):
    """Whether the content is explicit, which is a flag and never an exclusion."""
    return bool(EXPLICIT.search(width(row.get("title"))))


def normalise(row, shop):
    """One shelf row as a candidate work record, or None where a designation excludes it."""
    why = designated(row)
    if why:
        return None
    title = width(row.get("title"))
    if not title:
        return None
    authors = row.get("authors") or ([row.get("author")] if row.get("author") else [])
    authors = [re.sub(r"^\s*(著|作画|原作|漫画)\s*[:：]\s*", "", width(a)) for a in authors if a]
    return {
        "title": title,
        "authors": authors,
        "publisher": width(row.get("publisher")) or None,
        "imprint": width(row.get("imprint")) or (row.get("label") or [None])[0],
        "url": row.get("url"),
        "shop_id": row.get("cmoa_title_id") or row.get("id"),
        "completed": bool(row.get("completed") or row.get("completed_facet")
                          or row.get("completed_marker")),
        "doujin": bool(row.get("doujin")),
        "age_gated": age_gated(row, shop),
        "explicit_content": explicit(row),
    }


def ingest(rows, shop):
    """(records, excluded) where excluded holds only a count per reason, never a title."""
    out, why = [], {}
    for r in rows:
        rec = normalise(r, shop)
        if rec is None:
            reason = designated(r) or "no title"
            why[reason] = why.get(reason, 0) + 1
            continue
        out.append(rec)
    return out, why


def main(argv=None):
    import argparse, datetime, json, pathlib                                # noqa: E401
    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--queue", default="data/queue")
    ap.add_argument("--out", default="data/queue/admitted.yaml")
    a = ap.parse_args(argv)

    q = pathlib.Path(a.queue)
    shops = [("bookwalker.jp", q / "bookwalker-yuri.yaml", "items"),
             ("cmoa.jp", q / "cmoa-yuri.yaml", "titles")]
    all_rows, excluded, per = [], {}, {}
    for shop, path, key in shops:
        if not path.exists():
            continue
        doc = yaml.safe_load(path.read_text()) or {}
        recs, why = ingest(doc.get(key) or [], shop)
        for r in recs:
            r["shop"] = shop
        all_rows += recs
        per[shop] = len(recs)
        for k, v in why.items():
            excluded[k] = excluded.get(k, 0) + v

    js = lambda v: json.dumps(v, ensure_ascii=False)                        # noqa: E731
    L = ["# Shelf rows admitted on the designation test (DEFINITIONS §7, 2026-08-05).",
         "#",
         "# Nothing here asks whether a work IS pornography. A row is excluded only where somebody",
         "# else designated it: the shop's own adult genre, an adult imprint, an R-18 marking.",
         "# Doujinshi is a publication mode and excludes nothing by itself.",
         "#",
         "# EXCLUSIONS ARE COUNTED AND NEVER NAMED. A title we exclude as pornography is not written",
         "# into a file in this repository.",
         "#",
         "# Still data/queue/: these are candidates. Admission into data/source/ needs the joins",
         "# and the volume histories that give a work its dates.",
         f"retrieved: {datetime.date.today().isoformat()}",
         f"admitted: {len(all_rows)}", f"by_shop: {js(per)}",
         f"excluded: {js(excluded)}", "works:"]
    for r in sorted(all_rows, key=lambda x: (x["shop"], x["title"])):
        L.append(f"  - title: {js(r['title'])}")
        for k in ("authors", "publisher", "imprint", "url", "shop", "shop_id",
                  "completed", "doujin", "explicit_content", "age_gated"):
            L.append(f"    {k}: {js(r[k])}")
    L.append("")
    pathlib.Path(a.out).write_text("\n".join(L))
    print(f"admitted {len(all_rows)} of {len(all_rows) + sum(excluded.values())} shelf rows "
          f"({per}); excluded {sum(excluded.values())} on a designation -> {a.out}")
    for k, v in sorted(excluded.items(), key=lambda kv: -kv[1]):
        print(f"  {v:5}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
