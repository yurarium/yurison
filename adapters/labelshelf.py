#!/usr/bin/env python3
"""A publisher's own 百合 label read as a shelf: KADOKAWA works カドコミ tags and serves no chapters of.

WHY THIS EXISTS. カドコミ lists KADOKAWA's catalogue whether or not a work was ever serialised on
the web, and tags each listing with the publisher's own genres. `build.set_aside` rightly keeps a
listing with no episodes off the web side, since カドコミ never published it. But 52 of those
listings carry the publisher's 百合 tag and were in the corpus by no other route: まりあ†ほりっく,
<harmony/> ハーモニー, 水野と茶山, 吸血鬼ちゃん×後輩ちゃん, 悪魔のリドル. BOOK☆WALKER does not shelve them
under its tag 14, so the shelf intake never met them, and the web side had set them aside. A
publisher's label satisfies DEFINITIONS §2 on its own (`marketing_label ≠ none`), so these are works
the definitions admit that nothing was reading.

WHAT IT WRITES. `data/queue/kadokomi-label.yaml`, rows in the shape `shelfingest.py` reads from a
shop's shelf, each naming the BOOK☆WALKER series that sells the volumes and carrying
`publisher_label`, the カドコミ page that states the tag. From there the print intake runs as it
does for a shelf row: `shelfingest` admits it, `recon/bookwalker_volumes.py` reads its volumes and
dates, `bwingest` writes the record with the label, and `naming/mint.py` gives it an identifier.

WHY BOOK☆WALKER. It is KADOKAWA's own shop and sells the publisher's whole catalogue as files, and
the print intake already reads it. A series is taken only where its own listing names the work and
credits one of the people カドコミ credits; a search returns neighbours, and a label attached to the
wrong series would be a wrong designation with a citation.

Usage:  labelshelf.py [--kadokomi data/source/kadokomi/chapters.yaml] [--out ...] [--limit N]
"""
import datetime
import json
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bookwalker                                                        # noqa: E402

OUT = "data/queue/kadokomi-label.yaml"
#: How long a work BOOK☆WALKER did not answer for waits before it is asked again.
ASK_AGAIN_DAYS = 91
#: How many search results are opened. Relevance puts the work first when the shop has it.
OPEN = 3


def _fold(s):
    s = unicodedata.normalize("NFKC", str(s or ""))
    return re.sub(r"[\s・、。!?！？~〜\-–—:：'\"“”‘’()（）<>＜＞/]+", "", s).lower()


def unserved(doc):
    """The カドコミ listings that carry the publisher's 百合 tag and serve no episode."""
    return [w for w in (doc or {}).get("works") or []
            if w.get("marketing_label") == "yuri" and not (w.get("chapters") or w.get("episodes"))
            and w.get("work_title")]


def shelved(path):
    """Folded titles a shop's shelf already admitted, which this intake leaves to that route.

    THE LABEL ADDS WORKS AND REWRITES NONE. オルターエゴ is on BOOK☆WALKER's shelf and ruled out of
    scope as a Spanish original, so the store holds no title for it, and the first run matched it
    and replaced the shelf's admission on its record. A work a shelf admitted is already on its way
    in; what reaches nothing else is what this is for."""
    import yaml
    p = pathlib.Path(path)
    if not p.exists():
        return set()
    return {_fold(r.get("title")) for r in (yaml.safe_load(p.read_text()) or {}).get("works") or []
            if r.get("title") and not r.get("publisher_label")}


def held_by(key, held):
    """Whether a folded title is one the corpus already holds, as a whole or inside a longer one.

    A LONGER TITLE COUNTS. The corpus files ゆりなつ -民宿かがや- under its print title, and a
    listing whose fold sits inside a held title, or the reverse, is a lead for bwingest's review
    rather than a work to bring in a second time. Short folds are not compared that way, because
    `きのこ` is inside too many titles to mean anything."""
    if key in held:
        return True
    return len(key) > 3 and any(len(h) > 3 and (key in h or h in key) for h in held)


def matches(list_html, title, authors):
    """Whether a series listing is this work: its title names it and the page credits its people."""
    stem = re.split(r"\(マンガ（漫画）\)|の電子書籍| - ", bookwalker.page_title(list_html))[0]
    if not stem or _fold(title) not in _fold(stem):
        return False
    body = _fold(list_html)
    return any(_fold(a) and _fold(a) in body for a in authors or [])


def row(work, shop_id, url, stem, retrieved):
    """One shelf-shaped row for `shelfingest`, with the publisher's label it stands on."""
    return {
        "title": stem,
        "authors": list(work.get("authors") or []),
        "url": url,
        "id": str(shop_id),
        "publisher_label": {
            "source": "kadokomi",
            "url": work.get("url"),
            "retrieved": str((work.get("marketing_label_basis") or {}).get("retrieved")
                             or retrieved),
            "label": "百合",
            "note": "The publisher applies its 百合 tag to this work on カドコミ, its own platform, "
                    "which lists the work and serves no episode of it.",
        },
    }


def due(entry, today, every=ASK_AGAIN_DAYS):
    """Whether a work asked before, and not found, is to be asked again."""
    if not entry:
        return True
    try:
        return (datetime.date.fromisoformat(today)
                - datetime.date.fromisoformat(str(entry))).days >= every
    except ValueError:
        return True


def listing_title(page):
    """The work's name off a BOOK☆WALKER page title, without the shop's suffix or the imprint.

    A series listing titles itself `水野と茶山（ビームコミックス）(マンガ（漫画）)の電子書籍無料試し読み
    ならBOOK☆WALKER` and a product page `… - マンガ（漫画）…`, so both suffixes come off, and then the
    imprint in its closing full-width brackets, which bwingest strips the same way from a record."""
    t = re.split(r"\(マンガ（漫画）\)|の電子書籍| - ", page or "")[0].strip()
    return re.sub(r"（[^（）]*）$", "", t).strip() or t


def queries(title):
    """What to search for: the title, then the title without its decoration.

    THE SHOP'S SEARCH DOES NOT FORGIVE PUNCTUATION. `＜harmony/＞ ハーモニー` returns nothing at all,
    and a ～subtitle～ narrows a search to the edition that prints it, so each is tried without."""
    out = [title]
    for pat in (r"[<＜][^>＞]*[>＞]", r"[～〜~][^～〜~]*[～〜~]?$"):
        t = re.sub(pat, "", title).strip()
        if t and t not in out:
            out.append(t)
    return out


def find(get, work):
    """`(shop id, page address, listing title)` for this work on BOOK☆WALKER, or None.

    A SERIES WHERE THE SHOP GROUPS ONE, A PRODUCT WHERE IT DOES NOT. A single-volume work has no
    series page, and the search's series links are then its sidebar: わたしの友達が世界一かわいい came
    back with five series, none of them it, and the work itself as a product. Both are opened, the
    series first, and only a page naming the work and crediting its people is taken."""
    for q in queries(work["work_title"]):
        html = bookwalker.search(get, q)
        pages = [(sid, f"https://bookwalker.jp/series/{sid}/",
                  f"https://bookwalker.jp/series/{sid}/list/")
                 for sid in bookwalker.series_ids(html)[:OPEN]]
        seen = []
        for u in bookwalker.PRODUCT.findall(html):
            if u not in seen:
                seen.append(u)
        pages += [(re.search(r"/de([0-9a-f-]+)/", u).group(1), u, u) for u in seen[:OPEN]]
        for sid, url, read in pages:
            page = get(read)
            if matches(page, work["work_title"], work.get("authors")):
                return sid, url, listing_title(bookwalker.page_title(page))
    return None


def write(path, items, checked, retrieved):
    js = lambda v: json.dumps(v, ensure_ascii=False)                       # noqa: E731
    L = ["# The publisher's own 百合 label, read as a shelf (adapters/labelshelf.py).",
         "#",
         "# KADOKAWA works カドコミ tags 百合 and serves no episode of, each matched to the",
         "# BOOK☆WALKER series that sells its volumes. Candidates, in data/queue/: shelfingest.py",
         "# admits them and the print intake gives them records.",
         f"retrieved: {retrieved}", f"found: {len(items)}", "items:"]
    for r in sorted(items, key=lambda x: x["title"]):
        L.append(f"  - title: {js(r['title'])}")
        for k in ("authors", "url", "id"):
            L.append(f"    {k}: {js(r[k])}")
        L.append("    publisher_label:")
        for k, v in r["publisher_label"].items():
            L.append(f"      {k}: {js(v)}")
    L.append("checked:")
    for t, d in sorted(checked.items()):
        L.append(f"  {js(t)}: {js(d)}")
    L.append("")
    pathlib.Path(path).write_text("\n".join(L), encoding="utf-8")


def main(argv=None):
    import argparse

    import yaml
    import net
    import paths
    import population

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kadokomi", default="data/source/kadokomi/chapters.yaml")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--admitted", default="data/queue/admitted.yaml")
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--cache", default=str(paths.cache("labelshelf-cache")))
    a = ap.parse_args(argv)

    today = datetime.date.today().isoformat()
    prior = yaml.safe_load(pathlib.Path(a.out).read_text()) if pathlib.Path(a.out).exists() else {}
    prior = prior or {}
    items = {r["title"]: r for r in prior.get("items") or []}
    found_for = {r["publisher_label"]["url"] for r in items.values()}
    checked = {str(k): str(v) for k, v in (prior.get("checked") or {}).items()}

    held = {_fold(t) for t in population.titles()} | shelved(a.admitted)
    works = [w for w in unserved(yaml.safe_load(pathlib.Path(a.kadokomi).read_text()))
             if not held_by(_fold(w["work_title"]), held) and w.get("url") not in found_for
             and due(checked.get(w["work_title"]), today)][:a.limit]
    print(f"{len(works)} labelled カドコミ listing(s) with no episode and no work here to look up")

    def get(url):
        # THROUGH net.py, which paces the host and tells an absence from a refusal: a search the
        # shop has nothing for comes back empty, and a 503 raises rather than reading as "not sold".
        return net.body(net.fetch(url, a.cache, max_age_days=7)) or ""

    hits, refused = 0, 0
    for w in works:
        try:
            got = find(get, w)
        except net.Refused as e:
            refused += 1
            print(f"  refused {w['work_title'][:24]}: {e}")
            continue
        if got:
            hits += 1
            items[got[2]] = row(w, got[0], got[1], got[2], today)
            checked.pop(w["work_title"], None)
        else:
            checked[w["work_title"]] = today
    # THE FLOOR. A shop that refused every lookup has said nothing, and writing would record each
    # work as one it does not sell, which keeps them out for a season.
    if works and refused == len(works):
        print(f"HEALTH: BOOK☆WALKER refused all {refused} lookup(s). Refusing to write.")
        return 1
    write(a.out, list(items.values()), checked, today)
    print(f"  matched {hits} to a BOOK☆WALKER series; {len(items)} held in {a.out}; "
          f"{len(checked)} the shop did not answer for")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
