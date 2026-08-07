#!/usr/bin/env python3
"""What each source says about a thin-evidence candidate, read off its own page.

WHY THIS EXISTS. `evidence.py` narrows 296 candidates using what the corpus already holds. For the
works structure cannot settle, the remaining question is what a source SAYS, and DEFINITIONS §7
fixes what may be asked: whether anything designates the work, and whether anything contradicts the
one shelf that does. Not whether the work is really yuri.

THE THREE PAGES, AND WHY EACH IS WORTH A REQUEST.

  THE SHOP'S OWN WORK PAGE. BOOK☆WALKER presents its 書籍ジャンル on every work page, and tag 14 is
  the shelf that admitted 221 of these works. Reading the page asks the shelf listing's own claim
  back at the shop three days later, and it is the sharpest thing in this pass: sampled first on
  eight rows drawn at random from the capture, all eight carried tag 14, and `w01734`, the one work
  the operator has judged as not belonging, does not. The listing and the work page are different
  pages by different mechanisms, so this is not the check sharing the subject's blind spot
  (STANDING-INSTRUCTIONS §14b); it is the same shop asked a second time in a second place.

  THE TAG IS A FACT ABOUT A VOLUME, NOT ABOUT A WORK, and reading a series page alone gets this
  wrong. 霧尾ファンクラブ is unmistakably yuri: its series page carries 女性向け and 女性マンガ and
  nothing else, volume 1 carries 女性向け, 女性マンガ and 学園, and volume 2 carries 百合. A first
  version of this pass called 22 works contradicted off their series pages, every one of them a
  series row and not one of them a volume row, which is the shape of a rule that is measuring the
  page and not the shop. So a series page that does not carry the tag settles nothing until its
  volumes have been read, and `volume_pages` is what the second round reads.

  A SERIES PAGE LISTS SOME OF ITS VOLUMES, NOT ALL. The 22 above expose between 2 and 13 links
  each, against volume counts running to 119. So a work with the tag on none of the volumes we
  reached is a finding about the volumes we reached, and the row says how many that was.

  コミックシーモア states its top-level genre, its publisher and its imprint in a breadcrumb, and its
  百合・GL genre alongside them. Same question, other shop.

  THE PUBLISHER'S OWN PLATFORM. カドコミ files each work under a genre, a sub-genre and its own tag
  list, and it operates the 百合 and GL tags this project already enumerates. Where the shop shelves
  a work as yuri and the publisher's platform files it as 少女 / ラブコメ / 女装, the publisher is the
  better witness under DEFINITIONS §4, and the platform's positive filing is the substance. Its
  silence is not: 115 of our 372 カドコミ works sit outside those tags.

WHAT IS READ AND NOT KEPT. Every one of these pages carries the publisher's synopsis. REQUIREMENTS
§2 and §4 put that text out of bounds, so `blurb` exists to be read by a person during the pass and
is never written to the repository. What reaches `data/queue/thin-evidence-review.yaml` is our own
statement of what the page establishes.

PARSING IS SOMEBODY ELSE'S JOB WHERE IT ALREADY HAS AN OWNER. `bookwalker.tags` and
`kadokomi.confirm.work_data` are imported rather than reimplemented. Two producers of one fact with
nothing forcing agreement is the shape behind seven shipped bugs here (STANDING-INSTRUCTIONS §3),
and the copies drift silently.

The parsers are pure and are tested offline. `main` fetches; nothing else here touches a socket.
"""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "kadokomi"))

import bookwalker  # noqa: E402
import confirm  # noqa: E402
import net  # noqa: E402

# BOOK☆WALKER's own 百合 genre. The number is the shelf DEFINITIONS §2 names, and it is the thing
# being asked about, so it is a parameter of the question rather than a constant to be assumed.
BW_YURI_TAG = "14"

# コミックシーモア's own word for genre 37. Matched as the shop prints it; the shop's identifier is
# not in the page text.
CMOA_YURI_GENRE = "百合・GL"

LD_JSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

# A volume's own page, linked from its series page. `/de<uuid>/` is the shop's detail address; the
# sample links robots.txt disallows carry `?sample=` and are not this shape.
BW_VOLUME = re.compile(r'href="(https://bookwalker\.jp/de[0-9a-f-]{36}/)"')

# At least 1.5 s between requests to one host. net.PAUSE is 1.2, which is the value every existing
# adapter runs at; this pass raises it rather than lowering anything.
PAUSE = 1.6


def bookwalker_filing(html):
    """{tag id: name} as BOOK☆WALKER files this work today, plus whether the yuri shelf is there.

    Returns `shelved: None` for a page with no tags at all, which is a page we failed to read
    rather than a work the shop has unshelved. Those are different findings and STANDING-
    INSTRUCTIONS §5 says so: absence is a state, not a missing value.
    """
    tags = bookwalker.tags(html or "")
    return {"tags": tags, "shelved": (BW_YURI_TAG in tags) if tags else None}


def volume_pages(html):
    """The volume detail addresses a BOOK☆WALKER series page links to, in the order it lists them.

    Deduplicated because the page links the same volume from its cover and from its title.
    """
    seen = []
    for m in BW_VOLUME.finditer(html or ""):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def _ld(html, kind):
    """Every ld+json object of one @type on the page, including those inside an @graph."""
    out = []
    for m in LD_JSON.finditer(html or ""):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        for obj in (d if isinstance(d, list) else [d]):
            if not isinstance(obj, dict):
                continue
            for cand in [obj] + [g for g in (obj.get("@graph") or []) if isinstance(g, dict)]:
                if cand.get("@type") == kind:
                    out.append(cand)
    return out


def cmoa_filing(html):
    """How コミックシーモア files this work: genre, publisher, imprint, and its yuri shelf.

    `blurb` is the shop's synopsis. It is returned for a person to read during the pass and must
    not be stored (REQUIREMENTS §2).
    """
    prod = (_ld(html, "Product") or [{}])[0]
    book = (_ld(html, "Book") or [{}])[0]
    crumbs = [i.get("name") for c in _ld(html, "BreadcrumbList")
              for i in (c.get("itemListElement") or []) if isinstance(i, dict)]
    # 16 of the 64 pages read carry no Product block at all, and the breadcrumb answers the same
    # questions on those: it names the genre, the publisher and the imprint in order.
    return {
        "genre": prod.get("category"),
        "publisher": prod.get("brand"),
        "name": prod.get("name") or book.get("name"),
        "crumbs": crumbs,
        # WHO THE SHOP SAYS WROTE IT. Worth a field of its own because it answers a DEFINITIONS §6
        # question the rest of this pass cannot: サンストーン is credited to ステファン・セジク and
        # 上田香子, a foreign author and a Japanese translator, and a work whose Japanese edition is a
        # translation of a non-Japanese original is out of scope whatever any shelf says.
        "authors": [a.get("name") for a in (book.get("author") or []) if isinstance(a, dict)],
        "shelved": (CMOA_YURI_GENRE in html) if html else None,
        "blurb": prod.get("description"),
    }


def kadokomi_filing(html):
    """How カドコミ files this work: its genre, sub-genre and its own tag list.

    The payload is read by `kadokomi/confirm.py`, which routes around the platform's
    robots-disallowed API by reading the rendered page. Nothing here re-derives it.
    """
    data = confirm.work_data(html or "")
    if not data:
        return None
    w = data.get("work") or {}
    tags = [t.get("name") if isinstance(t, dict) else t for t in (w.get("tags") or [])]
    return {
        "title": w.get("title"),
        "genre": (w.get("genre") or {}).get("name"),
        "sub_genre": (w.get("subGenre") or {}).get("name"),
        "tags": [t for t in tags if t],
        "yuri_tagged": any(t in confirm.YURI_TAGS for t in tags if t),
    }


READERS = {"bookwalker": bookwalker_filing, "cmoa": cmoa_filing, "kadokomi": kadokomi_filing}


def read(kind, html):
    """Dispatch to the reader for one kind of page. Raises on a kind nobody has written one for."""
    if kind not in READERS:
        raise ValueError(f"no reader for {kind!r}; see READERS in this module")
    return READERS[kind](html)


def main(argv=None):
    """Fetch the pages named in a plan and write what each says. I/O only."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", required=True,
                    help="JSON: [{work, kind, url}], written by review.py --plan")
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-age-days", type=int, default=30)
    a = ap.parse_args(argv)

    net.PAUSE = max(net.PAUSE, PAUSE)
    plan = json.loads(pathlib.Path(a.plan).read_text(encoding="utf-8"))
    pages = net.fetch_many([p["url"] for p in plan], a.cache,
                           max_age_days=a.max_age_days, workers=3)
    out = {}
    for p in plan:
        r = pages[p["url"]]
        out.setdefault(p["work"], []).append({
            "kind": p["kind"], "url": p["url"], "status": r.status,
            "said": read(p["kind"], r.text) if r.text else None,
            "error": r.error,
        })
    pathlib.Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    print(f"read {len(plan)} pages for {len(out)} works -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
