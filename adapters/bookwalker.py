#!/usr/bin/env python3
"""Whether a licensed storefront marks a series finished.

WHY THIS EXISTS. The dormant list keeps containing works that plainly ended, and every structured
route we have misses them: the antenna drops a series when it stops updating, COMIC FUZ publishes
no status field, and NDL tells us when the volumes stopped but not whether the story did. What was
missing was somebody stating completion about a work nobody is publishing any more.

BOOK☆WALKER states it, in two places, and reading only one of them is how this module spent a
sweep answering None about works that had plainly ended. A finished series carries 【完結】 in front
of its name on its series page, and コンカフェ嬢は恋を着る is that case: dormant here, 【完結】 there.
It also tags the volumes themselves, which is the only signal 惑星クローゼット carries, a series
that ended in 2020 with no 【完結】 in any title. `status` reads the first and `status_from_list`
the second, and the sweep asks for both off one page.

THE COUNTER-CASE WAS TESTED FIRST. きみが死ぬまで恋をしたい updates monthly, and its series page
carries no 完結 anywhere at all, so the marker distinguishes rather than decorates.

WHAT SILENCE MEANS. Nothing. A running series is not marked, and neither is one the shop has not
got round to marking, so an absent 【完結】 is not evidence the work continues. This reports what it
found and declines to invent the opposite, which is why `status` answers `completed` or None.

WHAT KIND OF SOURCE THIS IS. A licensed distributor, so it sells the publisher's edition and takes
the publisher's word about it. Ranked below the platform serialising the work and above an
aggregator: it is a shop describing its own stock, which is a matter of record.
"""
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import population  # noqa: E402
import htmlbits as _htmlbits                                            # noqa: E402

SERIES_URL = re.compile(r"https://bookwalker\.jp/series/(\d+)")
TITLE = _htmlbits.TITLE
FINISHED = "【完結】"


def _fold(s):
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").replace("　", "").lower()


def series_ids(html):
    """Every series the search page links to, in the order it lists them."""
    out, seen = [], set()
    for m in SERIES_URL.finditer(html or ""):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


def page_title(html):
    m = TITLE.search(html or "")
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


TAG = re.compile(r'/tag/(\d+)/[^"]*"[^>]*>(.*?)</a>', re.S)
FINISHED_TAG = "42"


def tags(html):
    """{tag_id: label} from a series page, first label per id."""
    out = {}
    for m in TAG.finditer(html or ""):
        out.setdefault(m.group(1),
                       re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip())
    return out


def status_from_list(html, work_title):
    """`completed` where the volume list is tagged finished, otherwise None.

    WHY THIS EXISTS BESIDE `status`. The shop marks completion two ways and this module read only
    one. 惑星クローゼット carries no 【完結】 in any page title, so `status` answered None about a
    series that ended in 2020, while its `/series/<id>/list/` page tags every volume 完結 and
    summarises them as `完結(4)` on tag 42. The whole dormant sweep ran on the title-only reader,
    so silence there was never the evidence it was taken for.

    THE COUNTER-CASE WAS CHECKED FIRST. きみが死ぬまで恋をしたい, which updates monthly, carries no
    tag 42 at all on the same page, so the tag distinguishes rather than decorates.

    The page still has to name the work asked about, for the reason `status` gives: a marker read
    off somebody else's page is a wrong answer with a citation attached.
    """
    title = page_title(html)
    if not title:
        return None
    if _fold(work_title) not in _fold(title):
        return None
    return "completed" if FINISHED_TAG in tags(html) else None


#: A product page on BOOK☆WALKER, which is what a series list links each volume to.
PRODUCT = re.compile(r'href="(https://bookwalker\.jp/de[0-9a-f-]+/)"')
#: The shop's own word that this is the newest volume, in the product page's title.
NEWEST = "【最新刊】"
OG_DESCRIPTION = re.compile(r'<meta property="og:description" content="([^"]*)"')
#: Where the description says the series ended. 完結 is read only where nothing beside it narrows
#: it to an arc: 第一部完結 and 学園編完結 end a part, 未完結 says the opposite, and 完結編 names a
#: final arc that can run several volumes. 最終巻 and 完結巻 name the volume itself as the last.
ENDED = re.compile(r"(?<![部編章未])完結(?!編)|最終巻")


def latest_volume(list_html):
    """The first product the series list links, which is the newest: the list opens 最新刊から."""
    m = PRODUCT.search(list_html or "")
    return m.group(1) if m else None


def blurb_completed(product_html, work_title):
    """`completed` where the NEWEST volume's own description says the series ended, else None.

    THE SHOP'S DESCRIPTION OF ITS LAST VOLUME. 女だから、とパーティを追放されたので伝説の魔女と最強
    タッグを組みました carries neither 【完結】 nor the 完結 tag, and its sixth volume, titled
    【最新刊】, says 堂々完結 in the shop's own description; the owner pointed to it on 2026-10-15.
    Most series end on a stated last volume, and this is where a shop states it.

    ONLY THE NEWEST, AND ONLY ABOUT THIS WORK. A volume not titled 【最新刊】 may describe an arc
    that ended mid-run, and a page not naming the work is somebody else's. The sentence itself is
    not kept: a shop's description is copyrighted (REQUIREMENTS §2), and what is recorded is the
    fact and the page that states it.
    """
    title = page_title(product_html)
    if not title or NEWEST not in title or _fold(work_title) not in _fold(title):
        return None
    m = OG_DESCRIPTION.search(product_html or "")
    return "completed" if m and ENDED.search(m.group(1)) else None


def status(html, work_title):
    """`completed` where the shop marks this series finished, otherwise None.

    The page title has to name the work we asked about. A search for one title routinely returns a
    different series, and a marker read off somebody else's page is worse than no answer: it is a
    wrong one with a citation attached.
    """
    title = page_title(html)
    if not title:
        return None
    stem = title.split(" - ")[0]
    if _fold(work_title) not in _fold(stem):
        return None
    return "completed" if FINISHED in stem else None


def plan(works, checked, today, limit, every_days=30):
    """The works to ask this run: never asked first, then the longest since, each at most monthly.

    THE SWEEP RAN ONCE. It asked 53 dormant works on 2026-08-05 and nothing ran it again, while the
    works resting on silence grew to 384. A daily run cannot ask all of them at a pause of seconds a
    request, so each run asks a batch, and `checked` is what the file remembers between runs.
    """
    import datetime as _dt
    due = []
    for w in works:
        last = (checked or {}).get(w["work"])
        if last:
            try:
                age = (_dt.date.fromisoformat(today) - _dt.date.fromisoformat(str(last))).days
            except ValueError:
                age = every_days
            if age < every_days:
                continue
        due.append((last or "", w))
    due.sort(key=lambda x: x[0])
    return [w for _, w in due[:limit]]


def main(argv=None):
    """Ask the shop about works whose state rests on silence, a batch a run."""
    import argparse, datetime, json, pathlib, time, urllib.parse, urllib.request
    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # THE STORE BY DEFAULT AND A FILE ONLY WHEN ASKED, §13. It defaulted to a build artefact, so
    # the pass needed a compile it never declared and died on a fresh runner that had none.
    ap.add_argument("--series", default=None,
                    help="read the population from this series.json instead of from the store")
    ap.add_argument("--out", default="data/coverage/bookwalker-completion.yaml")
    ap.add_argument("--states", nargs="+", default=["dormant", "slow", "unknown"])
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--pause", type=float, default=2.5)
    a = ap.parse_args(argv)

    ua = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"

    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        finally:
            time.sleep(a.pause)

    out = pathlib.Path(a.out)
    prior = (yaml.safe_load(out.read_text()) or {}) if out.exists() else {}
    rows = {r["work"]: r for r in prior.get("works") or [] if r.get("work")}
    checked = {str(k): str(v) for k, v in (prior.get("checked") or {}).items()}
    today = datetime.date.today().isoformat()

    works, seen = [], set()
    for st in a.states:
        for w in population.works_in_state(st, a.series):
            if w["work"] not in seen:
                seen.add(w["work"])
                works.append(w)
    todo = plan(works, checked, today, a.limit)
    print(f"{len(works)} works rest on silence; asking {len(todo)} this run")
    found = 0
    for w in todo:
        try:
            ids = series_ids(get("https://bookwalker.jp/search/?word=" + urllib.parse.quote(w["work"])))
            checked[w["work"]] = today
            if not ids:
                continue
            # Only the first result is read. A shop's search ranks by relevance, and walking further
            # down it to find a 完結 anywhere is how you end up citing a different series.
            # The volume list carries both of the series' own markers, the 【完結】 a title may
            # hold and the 完結 tag the volumes carry; its first product is the newest volume.
            html = get(f"https://bookwalker.jp/series/{ids[0]}/list/")
            marker, volume = None, None
            if status(html, w["work"]) == "completed":
                marker = "title"
            elif status_from_list(html, w["work"]) == "completed":
                marker = "volume-tag"
            else:
                volume = latest_volume(html)
                if volume and blurb_completed(get(volume), w["work"]) == "completed":
                    marker = "latest-volume"
            if marker:
                found += 1
                rows[w["work"]] = {"work": w["work"], "series": ids[0], "title": page_title(html),
                                   "marker": marker, "volume": volume if marker == "latest-volume"
                                   else None, "latest_chapter": w.get("latest"), "found": today}
        except Exception as e:                                              # noqa: BLE001
            print(f"  skip {w['work'][:22]}: {type(e).__name__}")

    js = lambda v: json.dumps(v, ensure_ascii=False)                        # noqa: E731
    L = ["# Works BOOK☆WALKER marks finished, for works whose state here rests on silence.",
         "#",
         "# A licensed distributor selling the publisher's edition, so this is a shop describing",
         "# its own stock: 【完結】 in the series title, the 完結 tag on its volumes, or its newest",
         "# volume's own description saying the series ended. An absent marker is recorded nowhere",
         "# but `checked`, because a running series and one the shop has not marked look identical.",
         "source: bookwalker.jp", "role: completion-claim", "source_kind: licensor",
         f"retrieved: {today}", "works:"]
    for r in sorted(rows.values(), key=lambda x: x["work"]):
        L.append(f"  - work: {js(r['work'])}")
        L.append(f"    url: {js(r.get('url') or 'https://bookwalker.jp/series/' + str(r.get('series')) + '/')}")
        L.append(f"    shop_title: {js(str(r.get('title') or r.get('shop_title') or '').split(' - ')[0])}")
        L.append(f"    marker: {js(r.get('marker'))}")
        if r.get("volume"):
            L.append(f"    volume: {js(r['volume'])}")
        L.append(f"    latest_chapter: {js(r.get('latest_chapter'))}")
        if r.get("found"):
            L.append(f"    found: {js(str(r['found']))}")
    L.append("checked:")
    for k in sorted(checked):
        L.append(f"  {js(k)}: {js(checked[k])}")
    L.append("")
    out.write_text("\n".join(L))
    print(f"{found} of {len(todo)} asked are marked finished; {len(rows)} in all -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
