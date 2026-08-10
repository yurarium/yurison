#!/usr/bin/env python3
"""Read each lead's own platform page and decide whether it is the printed work we hold.

WHY A SECOND PASS. `sweep.py` matched a title, and RUNBOOK §11 is explicit that a title is the
strongest lead available and no kind of evidence on its own. So every lead is taken to the
platform's own page, which is Tier B, and the creator, the publisher or the imprint has to agree
there before anything is recorded. Web漫画アンテナ states an author too, and it is not used for
this: it is Tier C, and a Tier C field settling a join is exactly what REQUIREMENTS §1 forbids.
Its job was to turn "somewhere among 96 sites" into one address.

WHAT A PAGE IS ASKED FOR, AND WHY IT IS NOT THE WHOLE PAGE. Only fields that describe the page
itself: its `<title>`, its Open Graph title, a `<meta name="author">`, a JSON-LD `author`, and
where a platform has its own payload, the credits inside it. A platform sidebar advertises the
author's OTHER series and a search of the whole document would agree with anything. The previous
pass measured three joins refused for exactly that, and they earned their keep.

THREE VERDICTS AND NOT TWO.

  `agreed`     the creator, the publisher or the imprint is named on both sides. A join.
  `differs`    the page credits somebody and none of them is this work's creator. A refusal, and
               worth counting: a rise means a platform has started advertising its neighbours.
  `undecided`  one side names nobody, or the page could not be read. An anthology credits a table
               of contents and MADB credits it to nobody, so there is nothing to agree about.
               Left alone and reported, because a duplicate row costs less than a wrong merge.

Usage:  confirm.py                      every lead in the search file
        confirm.py --host manga.nicovideo.jp
"""
import argparse
import collections
import datetime
import html as _html
import json
import pathlib
import re
import sys
import urllib.parse

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import net                                                                     # noqa: E402
from identity import match_key, people                                              # noqa: E402
import pathlib as _pl, sys as _sy                                         # noqa: E401,E402
_sy.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))    # noqa: E402
import htmlbits as _htmlbits                                            # noqa: E402

BRACKET = re.compile(r"^\[[^\]]*\]")
TAG = re.compile(r"<[^>]+>")

TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
OG_TITLE = _htmlbits.OG_TITLE
META_AUTHOR = re.compile(r'<meta[^>]+name="author"[^>]+content="([^"]*)"', re.I)
JSONLD = re.compile(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I)

# A platform writes "work - author | site" in its title element, and the site half is a constant
# that has nothing to say about who made the manga. Dropping it keeps a house name in the site
# brand from agreeing with a publisher: ビッコミ renders 「… | ビッコミ（ビッグコミックス）」 and
# 小学館's own name is not in it, but 月マガ基地 and その他 sites of that shape exist and the guard
# costs nothing.
SITE_HALF = re.compile(r"\s*[|｜]\s*")


def describes_page(html):
    """`{"lines": [...], "credits": [...]}`: what a page says about itself, in two strengths.

    Deliberately narrow. A work page carries the site's whole catalogue in its navigation and its
    recommendations, so a document-wide search for a name agrees with almost anything.

    THE TWO STRENGTHS DECIDE WHETHER A REFUSAL IS POSSIBLE, and separating them is the correction
    this parser most needed. A `credit` is a field whose job is to name a person: a `meta author`,
    a JSON-LD `author`, or the platform's own author object. A `line` is a title element, which on
    many platforms carries the author after a dash and on many others carries the work title and
    nothing else. A line can therefore establish agreement and can never establish disagreement:
    `フツーの恋って何？ - 路草` names a site, not a rival author, and reading it as one refused a
    join that nothing had contradicted. 87 leads were refused on that reasoning and most of them
    were pages that simply state no author.
    """
    lines, credits = [], []
    for m in TITLE.finditer(html or ""):
        t = _html.unescape(TAG.sub(" ", m.group(1))).strip()
        if t:
            lines.append(SITE_HALF.split(t)[0])
    for m in OG_TITLE.finditer(html or ""):
        t = _html.unescape(m.group(1)).strip()
        if t:
            lines.append(SITE_HALF.split(t)[0])
    for m in META_AUTHOR.finditer(html or ""):
        t = _html.unescape(m.group(1)).strip()
        if t:
            credits.append(t)
    for m in JSONLD.finditer(html or ""):
        try:
            d = json.loads(m.group(1))
        except (ValueError, TypeError):
            continue
        for obj in (d if isinstance(d, list) else [d]):
            if not isinstance(obj, dict):
                continue
            a = obj.get("author")
            for x in (a if isinstance(a, list) else [a]):
                if isinstance(x, str):
                    credits.append(x)
                elif isinstance(x, dict) and isinstance(x.get("name"), str):
                    credits.append(x["name"])
    return {"lines": lines, "credits": credits}


def _named(text):
    """Every name-shaped token in one descriptive line.

    `people` reads a credit line, which is what a platform's author field is. A title element is
    not a credit line, so its parts are also kept whole: `酒と鬼は二合まで - 羽柴実里,zinbei`
    splits into a work title and two names, and only the names will agree with anything.
    """
    out = set(people(text))
    for part in re.split(r"\s*[-–—/／,、]\s*", text or ""):
        f = match_key(part)
        if f:
            out.add(f)
    return out


def verdict(creator_line, publisher, says, imprint=""):
    """`(agreed|differs|undecided, evidence)` for one page against one printed record.

    A short name cannot be matched inside a longer string without agreeing by accident, since `ED`
    appears in every second English word, so a name of one or two folded characters has to be a
    whole part of a descriptive line and not a substring of one.

    `differs` needs a CREDIT on the page, not merely a title. A page stating no author contradicts
    nothing, and calling that a refusal turns silence into evidence, which is the mistake
    STANDING-INSTRUCTIONS §5 names.
    """
    want = {match_key(n) for n in people(creator_line) if match_key(n)}
    tokens, credit_tokens = set(), set()
    for ln in says.get("lines") or []:
        tokens |= _named(ln)
    for c in says.get("credits") or []:
        credit_tokens |= _named(c)
    tokens |= credit_tokens
    joined = " ".join(match_key(x) for x in (says.get("lines") or []) + (says.get("credits") or []))

    for n in sorted(want, key=len, reverse=True):
        if n in tokens or (len(n) >= 3 and n in joined):
            return "agreed", f"creator {n} is named on the platform page"
    pub = match_key(BRACKET.sub("", publisher or ""))
    if pub and (pub in tokens or (len(pub) >= 3 and pub in joined)):
        return "agreed", f"publisher {pub} is named on the platform page"
    # The imprint, which RUNBOOK §11 accepts and which one platform states where nothing else
    # does: COMIC FUZ tags a series まんがタイムKRコミックス, the label printed on the volume.
    imp = match_key(imprint or "")
    if imp and (imp in tokens or (len(imp) >= 3 and imp in joined)):
        return "agreed", f"imprint {imp} is named on the platform page"
    if want and credit_tokens:
        return "differs", "the page credits somebody else"
    if not want:
        return "undecided", "the printed record credits nobody"
    return "undecided", "the page states no author, so nothing but the title agrees"


# ── per-platform readers ──────────────────────────────────────────────────────────────────────
# カドコミ and ニコニコ both ship a module called `releases`, so neither may be imported by name:
# whichever landed on sys.path first would answer for both, silently. Loaded by path instead, once.
def _by_path(name, relative):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        name, pathlib.Path(__file__).resolve().parents[1] / relative)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def nico_says(html):
    """ニコニコ's own author field and its copyright line, which names the publisher.

    Both are credits rather than title lines, so this platform can refuse a lead as well as
    confirm one: `サラダボウル` on ニコニコ is 東方's, by TJLJFJLJ, and the printed 講談社 book of
    that title is きぃやん's.
    """
    nv = _by_path("nico_releases", "nicovideo/releases.py")
    d = nv.parse(html) or {}
    says = describes_page(html)
    says["credits"] += [x for x in [d.get("author")] if x] + nv.rights(html)
    return says


def kadokomi_says(html):
    """カドコミ's work object, which names its authors with their roles.

    Falling back to the page's own title lines matters: the object lives inside `__NEXT_DATA__`,
    a site rebuild would empty it, and a silent empty result would turn every カドコミ join into
    `undecided` with nothing saying why.
    """
    kr = _by_path("kadokomi_releases", "kadokomi/releases.py")
    w = (kr.work_data(html) or {}).get("work") or {}
    names = [a.get("name") for a in (w.get("authors") or []) if isinstance(a, dict) and a.get("name")]
    if not names:
        return describes_page(html)
    return {"lines": [w.get("title") or ""], "credits": names}


def fuz_says(html):
    """COMIC FUZ's own payload: its authors, and the tags that name its imprint and magazine.

    The page's title element carries the work's name and nothing else, so reading only that filed
    every 芳文社 lead as undecided. The author is in `__NEXT_DATA__` under `authorships`, and the
    tag list holds まんがタイムKRコミックス and まんがタイムきららフォワード beside the update day
    and the audience. The imprint is one of the three fields RUNBOOK §11 accepts, and on this
    platform it is often the one that answers.
    """
    fz = _by_path("fuz_releases", "comicfuz/releases.py")
    pp = fz.page_props(html) or {}
    names = [(a.get("author") or {}).get("authorName") for a in (pp.get("authorships") or [])
             if isinstance(a, dict)]
    names += [t.get("name") for t in (pp.get("tags") or []) if isinstance(t, dict) and t.get("name")]
    names = [n for n in names if n]
    if not names:
        return describes_page(html)
    return {"lines": [(pp.get("manga") or {}).get("mangaName") or ""], "credits": names}


def says_of(url, html):
    """What one page says about itself, through the platform's own parser where there is one."""
    host = urllib.parse.urlparse(url).netloc.lower()
    if host.endswith("manga.nicovideo.jp"):
        return nico_says(html)
    if host.endswith("comic-walker.com"):
        return kadokomi_says(html)
    if host.endswith("comic-fuz.com"):
        return fuz_says(html)
    return describes_page(html)


def promo_hosts():
    """The hosts whose instalments are a 試し読み of a finished book rather than a serialisation.

    Read from `build.py`, which already refuses to count them as chapters, so this pass and the
    build cannot disagree about what a serialisation is. A lead here would produce an anchor with
    no row behind it (DEFINITIONS §6: a sample is not web publication).
    """
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    import build
    return tuple(build.PROMO_HOSTS)


def leads(doc, skip_hosts=()):
    """[(work, url, platform)] for every candidate address in the search file, without repeats."""
    out = []
    for w in doc.get("asked") or []:
        seen = set()
        for h in (w.get("nico_hits") or []):
            if h.get("url") and h["url"] not in seen:
                seen.add(h["url"])
                out.append((w, h["url"], "ニコニコ漫画"))
        for h in (w.get("antenna_hits") or []):
            u = h.get("url") or ""
            if u and u not in seen and not any(s in u for s in skip_hosts):
                seen.add(u)
                out.append((w, u, h.get("site") or ""))
    return out


def js(v):
    return json.dumps(v, ensure_ascii=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--search", default="data/queue/serialisation-search.yaml")
    ap.add_argument("--out", default="data/queue/serialisation-confirmed.yaml")
    ap.add_argument("--cache", default="/tmp/yuri-serialisation-pages")
    ap.add_argument("--host", help="only leads on this host")
    ap.add_argument("--age", type=int, default=net.AGE_LISTING)
    a = ap.parse_args(argv)

    doc = yaml.safe_load(pathlib.Path(a.search).read_text()) or {}
    todo = leads(doc, promo_hosts())
    if a.host:
        todo = [t for t in todo if a.host in t[1]]
    print(f"{len(todo)} lead(s) on {len({urllib.parse.urlparse(u).netloc for _w, u, _p in todo})} host(s)")

    pages = net.fetch_many([u for _w, u, _p in todo], a.cache, a.age, workers=8)

    rows, counts = [], collections.Counter()
    for w, url, plat in todo:
        r = pages.get(url)
        if not r or r.text is None:
            v, ev = "unreadable", (r.error if r else "not fetched")
            says = {"lines": [], "credits": []}
        else:
            says = says_of(url, r.text)
            v, ev = verdict(w.get("author") or "", (w.get("publisher") or [""])[0], says,
                            (w.get("imprint") or [""])[0])
        counts[v] += 1
        rows.append({"id": w["id"], "title": w["title"], "author": w.get("author"),
                     "publisher": w.get("publisher"), "madb": w.get("madb"),
                     "url": url, "platform": plat, "verdict": v, "evidence": ev,
                     "page_says": (says["lines"] + says["credits"])[:5]})

    L = ["# Every serialisation lead, taken to the platform's own page and tested for agreement.",
         "#",
         "# NOT A RECORD, and one step from being one. A row reading `agreed` is a join waiting to",
         "# be applied with `identity.py --attach`; the rest are reported and left alone. RUNBOOK",
         "# §11: an undecided join costs a duplicate row, and a wrong merge is hard to see once",
         "# made.",
         "#",
         "# `page_says` is what the page says about ITSELF: its title lines and author fields, and",
         "# on ニコニコ its copyright line. Never the whole document: a sidebar advertising the",
         "# author's other series agrees with anything.",
         "source: the platforms named in `platform`",
         "role: join-evidence",
         f"retrieved: {datetime.date.today().isoformat()}",
         "record_type: serialisation_confirmation",
         f"leads: {len(rows)}",
         "confirmed:"]
    for r in sorted(rows, key=lambda x: (x["verdict"], x["id"])):
        L.append(f"  - id: {r['id']}")
        L.append(f"    title: {js(r['title'])}")
        L.append(f"    author: {js(r['author'])}")
        L.append(f"    publisher: {js(r['publisher'])}")
        L.append(f"    madb: {js(r['madb'])}")
        L.append(f"    platform: {js(r['platform'])}")
        L.append(f"    url: {js(r['url'])}")
        L.append(f"    verdict: {r['verdict']}")
        L.append(f"    evidence: {js(r['evidence'])}")
        L.append(f"    page_says: {js(r['page_says'])}")
    L.append("")
    pathlib.Path(a.out).write_text("\n".join(L))

    for k, n in counts.most_common():
        print(f"  {k:11s} {n}")
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
