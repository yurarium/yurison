#!/usr/bin/env python3
"""How a name is read, taken from the platform that publishes the work saying so beside the byline.

WHY THIS EXISTS. NAMES-PLAN §4a measured the platform caches for furigana over a byline and found
none in 278 pages, and that measurement is right about the page a chapter is read on. It is wrong
about one page nobody had looked at: ヤンマガWeb keeps an author page per artist and prints the
reading under the name, `宇藤あかり` over `うどうあかり`. That is 講談社 stating how its own author
is read, which under `curate.py` is `reading_basis: stated` with `reading_source_kind: platform`.

WHAT IT REACHES, AND HOW LITTLE THAT IS. One platform. Every GigaViewer site was checked and none
of them has an author page at all: となりのヤングジャンプ, サンデーうぇぶり, 少年ジャンプ+,
コミックDAYS, くらげバンチ and 一迅プラス answer a creator search with titles and no reading, and
カドコミ's search page carries the name and nothing beside it. So this settles the nine artists our
corpus holds on ヤンマガWeb and nobody else, and it is written down as a module rather than done by
hand because the shape will be worth reusing the moment a second platform grows the same page.

THE RUBY IS HIRAGANA AND THE STORE HOLDS KATAKANA, which is a conversion and not a judgement:
`names/kana.py` already does it for the deterministic pass and is used here rather than repeated.

WHAT IS NOT DONE. The author page states no boundary between family and given name, since
`うどうあかり` is one run, so none is invented, for the reason `madb_reading.py` gives at length.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names import kana as kana_mod                                            # noqa: E402

# ヤンマガWeb's author page. The name and its reading sit in one block; the class names are the
# platform's own and are matched exactly, so a redesign yields nothing rather than yielding the
# heading of whatever replaced it.
AUTHOR_NAME = re.compile(r'<h1 class="author-name-text">\s*(.*?)\s*</h1>', re.S)
AUTHOR_RUBY = re.compile(r'<span[^>]*class="[^"]*author-name-ruby[^"]*"[^>]*>\s*(.*?)\s*</span>',
                         re.S)

# Where a series page links to the author page. `/comics/authors` without a hash is the index.
AUTHOR_LINK = re.compile(r'href="(/comics/authors/[0-9a-f]{8,})"')

TAG = re.compile(r"<[^>]+>")


def _text(fragment):
    return re.sub(r"\s+", " ", TAG.sub("", fragment or "")).strip()


def author_links(page, base="https://yanmaga.jp"):
    """Every author page a series page links to, in the order it lists them.

    ORDER MATTERS AND POSITION DOES NOT SETTLE ANYTHING. A work with two credits links to two
    author pages, and which link is whose is decided by reading the page it points at, not by
    where it sits. Each author page states its own name.
    """
    out = []
    for href in AUTHOR_LINK.findall(page or ""):
        u = base + href
        if u not in out:
            out.append(u)
    return out


def name_and_reading(page):
    """`(name, reading)` from an author page, with the reading as the katakana the store holds.

    Returns None where either half is missing. A page with a name and no ruby is a real state,
    where the platform has left the field empty, and that is silence. It is not a licence to derive
    a reading instead.
    """
    n = AUTHOR_NAME.search(page or "")
    r = AUTHOR_RUBY.search(page or "")
    if not n or not r:
        return None
    name, ruby = _text(n.group(1)), _text(r.group(1))
    if not name or not ruby:
        return None
    reading = kana_mod.to_katakana(ruby)
    # THE RUBY HAS TO BE KANA. A platform that starts putting a romanisation or a handle in that
    # slot would otherwise be recorded as stating a Japanese reading.
    if not kana_mod.kana_only(ruby):
        return None
    return name, reading


def entry(name, reading, url, guess, reviewed):
    """The curated author entry for one reading a platform states."""
    note = (f"ヤンマガWeb prints this reading under the name on its own author page. "
            f"The platform is 講談社's, and the work is published on it.")
    if (guess or "").replace(" ", "") != reading.replace(" ", ""):
        note += f" It replaces {guess!r}, which no source had stated."
    else:
        note += " It agrees with the reading already held, which no source had stated."
    return {"reading": reading, "reading_basis": "stated", "reading_source_kind": "platform",
            "reading_note": note, "source": "ヤンマガWeb", "source_kind": "platform",
            "source_url": url, "reviewed": reviewed}


def main(argv=None):
    import argparse
    import datetime
    import json

    import yaml

    import net                                                         # noqa: PLC0415
    import paths                                                       # noqa: PLC0415
    from names.openbd_reading import unsettled_readings                # noqa: PLC0415

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", default="data/build")
    # Defaulted, not required: see adapters/paths.py for the rule.
    ap.add_argument("--cache", default=str(paths.cache("platform-reading-cache")),
                    help="where fetched pages live; outside the repo")
    ap.add_argument("--platform", default="ヤンマガWeb")
    ap.add_argument("--reviewed", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)

    cache = pathlib.Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)

    refused = []

    def fetch(url):
        """The page, or "" where there is none or the platform would not serve it.

        THE ERROR USED TO BE CACHED, and here it was worse than a wasted run: a failure was written
        into the cache as a page beginning `__ERROR__`, that page parsed to no author link and no
        reading, and the artist was filed `no-author-page`, which is a statement about the artist.
        A refusal is collected instead and printed, so a run against a platform that was down does
        not read as a run that found nothing to state.
        """
        r = net.fetch(url, cache, net.AGE_LISTING)
        if net.is_refusal(r):
            refused.append(url)
            return ""
        return r.text or ""

    wanted = unsettled_readings()
    series = json.loads((pathlib.Path(a.build) / "series.json").read_text())["series"]
    # Which work pages to open: the ones on this platform crediting somebody with no stated
    # reading. The author page is reached from the work, because the platform's author index is
    # paginated and the works are the population we care about.
    pages = []
    for w in series:
        on = any((s.get("platform") or "") == a.platform for s in (w.get("sources") or []))
        if not on:
            continue
        if any(p.strip() in wanted for p in re.split(r"\s*/\s*", w.get("author") or "")):
            u = (w.get("url") or "").rstrip("/")
            parts = u.split("/")
            if re.fullmatch(r"[0-9a-f]{32}", parts[-1]):
                u = "/".join(parts[:-1])
            if u and u not in pages:
                pages.append(u)

    found, unresolved = {}, {}
    for u in pages:
        page = fetch(u)
        for link in author_links(page):
            got = name_and_reading(fetch(link))
            if not got:
                continue
            name, reading = got
            if name in wanted and name not in found:
                found[name] = entry(name, reading, link, wanted[name], a.reviewed)
    for name in wanted:
        if name not in found:
            unresolved[name] = "no-author-page"

    # Printed even at nought, because a run that met no refusals and a run whose refusals were
    # swallowed look identical from the output otherwise (STANDING-INSTRUCTIONS §4).
    print(f"{len(pages)} work page(s) on {a.platform}; {len(found)} reading(s) stated; "
          f"{len(refused)} page(s) the platform would not serve")
    print(yaml.safe_dump({"authors": found}, allow_unicode=True, sort_keys=True, width=100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
