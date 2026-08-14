#!/usr/bin/env python3
"""English licences from the licensor's own catalogue.

WHY THIS EXISTS. 19 works in the database carry a licensed English title against a corpus of a
thousand, and the field is much larger than that. A licensed title is the one an English reader
actually meets, so it outranks anything we translate, and NAMES-PLAN requires it to come from a
licensor's own catalogue page instead of from a database that aggregates them.

Seven Seas is the largest yuri licensor and tags its own catalogue: `/tag/yuri/` lists the series
and each series page states the Japanese title outright in a `originaltitle` block, so the join to
our corpus is on the Japanese name and needs no fuzzy matching of English against English.

THE IMPRINT MATTERS. Ghost Ship is Seven Seas' adult line. DEFINITIONS §7 excludes works marketed
as pornography outright, and an adult imprint is one of its four signals, so the imprint is read
from the page and carried rather than discarded. Nothing here decides the exclusion; it records
what the licensor says so the decision can be made on evidence.
"""
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import population  # noqa: E402
import html as _html

SERIES = re.compile(r'href="(https://sevenseasentertainment\.com/series/[^"#?]+)"[^>]*>(.*?)</a>',
                    re.S)
ORIGINAL = re.compile(r'<div id="originaltitle">(.*?)</div>', re.S)
IMPRINT = re.compile(r'/">(Ghost Ship|Seven Seas|Airship|Steamship)</a>')
RATING = re.compile(r'<div id="(olderteen\d*|teen\d*|mature\d*|adult\d*)"')


def _txt(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", _html.unescape(s or ""))).strip()


def series_links(html):
    """{url: english_title} for every series the listing names, first title per url."""
    out = {}
    for u, t in SERIES.findall(html or ""):
        t = _txt(t)
        if t and u not in out:
            out[u] = t
    return out


def original_title(html):
    """(japanese, romaji) from the series page, or (None, None).

    The block holds both, separated by a pipe. The Japanese half is what joins to our corpus; the
    romaji is the licensor's own and is kept because it is attested rather than derived.
    """
    m = ORIGINAL.search(html or "")
    if not m:
        return None, None
    parts = [p.strip() for p in _txt(m.group(1)).split("|")]
    ja = parts[0] if parts and parts[0] else None
    ro = parts[1] if len(parts) > 1 and parts[1] else None
    return ja, ro


def imprint(html):
    """Which of the publisher's lines carries the work. Ghost Ship is the adult one."""
    m = IMPRINT.search(html or "")
    return m.group(1) if m else None


def match_key(s):
    """A join key for a licensor catalogue, stripping decoration characters. Same rule as
    `identity.match_key` and kept separate because the two catalogues may diverge.

    ORIGINALLY CALLED `fold`. A join key for a Japanese title: width and decoration differ between catalogues."""
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"""[\s　・!！?？。、,，~〜ー―\-–—:：;；'"“”‘’()\[\]{}「」『』【】]+""", "", s).lower()


def main(argv=None):
    """Read the licensor's yuri tag and record every licence it states."""
    import argparse, datetime, json, pathlib, time, urllib.request

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tag", default="https://sevenseasentertainment.com/tag/yuri/")
    ap.add_argument("--pages", type=int, default=4)
    # THE STORE BY DEFAULT AND A FILE ONLY WHEN ASKED, §13. It defaulted to a build artefact, so
    # the pass needed a compile it never declared and died on a fresh runner that had none.
    ap.add_argument("--series", default=None,
                    help="read the population from this series.json instead of from the store")
    ap.add_argument("--out", default="data/queue/english-licences.yaml")
    ap.add_argument("--pause", type=float, default=1.5)
    a = ap.parse_args(argv)

    ua = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"

    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read().decode("utf-8", "replace")

    found = {}
    for p in range(1, a.pages + 1):
        url = a.tag if p == 1 else f"{a.tag.rstrip('/')}/page/{p}/"
        try:
            page = get(url)
        except Exception as e:                                              # noqa: BLE001
            print(f"  stop at page {p}: {e}")
            break
        new = series_links(page)
        before = len(found)
        found.update({k: v for k, v in new.items() if k not in found})
        print(f"  page {p}: {len(new)} link(s), {len(found)} total")
        time.sleep(a.pause)
        if len(found) == before:
            break

    ours = {match_key(w["work"]): w for w in population.works(a.series)}
    rows, unmatched, noja = [], 0, 0
    for url, en in sorted(found.items()):
        try:
            page = get(url)
        except Exception as e:                                              # noqa: BLE001
            print(f"  skip {en[:30]}: {e}")
            continue
        time.sleep(a.pause)
        ja, ro = original_title(page)
        if not ja:
            noja += 1
            continue
        held = ours.get(match_key(ja))
        if not held:
            unmatched += 1
        rows.append({"en": en, "ja": ja, "romaji": ro, "imprint": imprint(page),
                     "url": url, "held": bool(held),
                     "our_work": held["work"] if held else None})

    js = lambda v: json.dumps(v, ensure_ascii=False)                        # noqa: E731
    L = ["# English licences stated by the licensor's own catalogue. A CANDIDATE LIST.",
         "#",
         "# data/queue/ sits outside the source tree so nothing here becomes a record by accident.",
         "# `held` says whether the Japanese title joins a work we already carry; the rest are",
         "# licensed yuri we do not hold at all, which is a coverage finding in its own right.",
         "#",
         "# `imprint` is carried because Ghost Ship is the publisher's adult line, and an adult",
         "# imprint is one of DEFINITIONS §7's four exclusion signals. Nothing is decided here.",
         "source: sevenseasentertainment.com", "role: licence-claim", "source_kind: licensor",
         f"retrieved: {datetime.date.today().isoformat()}",
         f"series_listed: {len(found)}", f"with_japanese_title: {len(rows)}",
         f"no_japanese_title: {noja}", f"not_held_by_us: {unmatched}", "licences:"]
    for r in rows:
        L.append(f"  - en: {js(r['en'])}")
        L.append(f"    ja: {js(r['ja'])}")
        L.append(f"    romaji: {js(r['romaji'])}")
        L.append(f"    imprint: {js(r['imprint'])}")
        L.append(f"    url: {js(r['url'])}")
        L.append(f"    held: {js(r['held'])}")
        L.append(f"    our_work: {js(r['our_work'])}")
    L.append("")
    pathlib.Path(a.out).write_text("\n".join(L))
    print(f"{len(rows)} licence(s), {len(rows)-unmatched} joining works we hold, "
          f"{unmatched} we do not -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
