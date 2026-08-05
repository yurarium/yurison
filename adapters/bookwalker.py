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
import re
import unicodedata

SERIES_URL = re.compile(r"https://bookwalker\.jp/series/(\d+)")
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
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


def main(argv=None):
    """Ask the shop about every work whose state rests on silence."""
    import argparse, datetime, json, pathlib, time, urllib.parse, urllib.request

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--series", default="data/build/series.json")
    ap.add_argument("--out", default="data/coverage/bookwalker-completion.yaml")
    ap.add_argument("--state", default="dormant")
    ap.add_argument("--pause", type=float, default=2.5)
    a = ap.parse_args(argv)

    ua = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"

    def get(url):
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read().decode("utf-8", "replace")

    works = [w for w in json.loads(pathlib.Path(a.series).read_text())["series"]
             if w.get("state") == a.state]
    rows, unmarked, missing = [], 0, 0
    for w in works:
        try:
            found = series_ids(get("https://bookwalker.jp/search/?word="
                                   + urllib.parse.quote(w["work"])))
        except Exception as e:                                              # noqa: BLE001
            print(f"  skip {w['work'][:22]}: {e}")
            continue
        time.sleep(a.pause)
        if not found:
            missing += 1
            continue
        # Only the first result is read. A shop's search ranks by relevance, and walking further
        # down it to find a 完結 anywhere is how you end up citing a different series.
        #
        # The volume list is read rather than the series page, because it carries BOTH signals: the
        # 【完結】 the title may hold and the 完結 tag the volumes carry. Reading only the title
        # missed 惑星クローゼット, which ended in 2020 and is tagged but not titled.
        try:
            html = get(f"https://bookwalker.jp/series/{found[0]}/list/")
        except Exception as e:                                              # noqa: BLE001
            print(f"  skip {w['work'][:22]}: {e}")
            continue
        time.sleep(a.pause)
        st = status(html, w["work"]) or status_from_list(html, w["work"])
        if st == "completed":
            rows.append({"work": w["work"], "series": found[0], "title": page_title(html),
                         "marker": "title" if FINISHED in page_title(html) else "volume-tag",
                         "latest_chapter": w.get("latest")})
        else:
            unmarked += 1

    js = lambda v: json.dumps(v, ensure_ascii=False)                        # noqa: E731
    L = ["# Works BOOK☆WALKER marks 【完結】, for works whose state here rests on silence.",
         "#",
         "# A licensed distributor selling the publisher's edition, so this is a shop describing",
         "# its own stock. An absent marker is recorded nowhere, because a running series and a",
         "# series the shop has not marked look identical and neither says the work continues.",
         "source: bookwalker.jp", "role: completion-claim", "source_kind: licensor",
         f"retrieved: {datetime.date.today().isoformat()}",
         f"queried: {len(works)}", f"unmarked: {unmarked}", f"not_stocked: {missing}", "works:"]
    for r in sorted(rows, key=lambda x: x["work"]):
        L.append(f"  - work: {js(r['work'])}")
        L.append(f"    url: {js('https://bookwalker.jp/series/' + r['series'] + '/')}")
        L.append(f"    shop_title: {js(r['title'].split(' - ')[0])}")
        L.append(f"    marker: {js(r.get('marker'))}")
        L.append(f"    latest_chapter: {js(r.get('latest_chapter'))}")
    L.append("")
    pathlib.Path(a.out).write_text("\n".join(L))
    print(f"{len(rows)} of {len(works)} {a.state} works are marked 完結 "
          f"({unmarked} unmarked, {missing} not stocked) -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
