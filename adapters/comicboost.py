#!/usr/bin/env python3
"""Chapter lists from comicブースト, which reconnaissance had filed as unreadable.

WHY THIS EXISTS. data/coverage/extract.yaml records comic-boost.com with `strategy: none` and
15 exclusive works, so a platform we could not read was holding works nothing else does. It is in
fact server-rendered: each chapter is an `<h4 class="title">` with an `update-date` beside it, and
the whole catalogue is listed in the site's own sitemap.

WHAT IT IS FOR HERE. 百合にはさまる男は死ねばいい!? reached us only through ダ・ヴィンチニュース,
which publishes a read-through of a book it sells rather than a serialisation. comicブースト is not
the underlying source either: its seven chapters are a 出張掲載, all posted on one day to mark the
tankobon, and the page says so. It is still the right anchor, because it is a publisher's web
platform carrying the work under its own name, and because it is reachable.

The one-day posting is left to speak for itself. Seven chapters sharing a date is exactly the
signature adapters/importdates.py looks for, so those dates cannot become the work's latest, and
the state comes from what the shop says instead.
"""
import re

OG = re.compile(r'<meta property="og:title" content="([^"]*)"')
ROW = re.compile(
    r'<h4 class="title">\s*(.*?)\s*</h4>(.*?)<p class="update-date">\s*([0-9/]+)\s*</p>', re.S)
FREE = re.compile(r'class="free"')
COIN = re.compile(r'data-coin="([1-9]\d*)"')


def work_title(html):
    """The work's name, without the platform's own furniture."""
    m = OG.search(html or "")
    return m.group(1).split("｜")[0].strip() if m else ""


def chapters(html):
    """[{title, updated, access_modes}] in the order the page lists them.

    The date sits in the same row as the title, so they are read as one match. Reading them as two
    lists and zipping would pair a title with somebody else's date the moment a row lacked one.
    """
    out = []
    for title, mid, date in ROW.findall(html or ""):
        parts = [int(x) for x in date.split("/") if x.isdigit()]
        if len(parts) != 3:
            continue
        out.append({
            "title": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title)).strip(),
            "updated": f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}",
            "access_modes": ["free"] if FREE.search(mid) else ["purchase"],
        })
    return out


def main(argv=None):
    """Read each named series page and write what it lists."""
    import argparse, datetime, json, pathlib, time, urllib.request
    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--targets", default="data/coverage/comicboost-targets.yaml")
    ap.add_argument("--out", default="data/source/webpages/comic-boost.yaml")
    ap.add_argument("--pause", type=float, default=1.5)
    a = ap.parse_args(argv)

    src = yaml.safe_load(pathlib.Path(a.targets).read_text()) or {}
    ua = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
    works = []
    for t in src.get("works") or []:
        url = t.get("url") or ""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read().decode("utf-8", "replace")
        except Exception as e:                                              # noqa: BLE001
            print(f"  skip {url}: {e}")
            continue
        ch = chapters(html)
        if ch:
            works.append({"work_title": work_title(html) or t.get("title"), "url": url,
                          "chapters": ch})
        time.sleep(a.pause)

    if not works:
        raise SystemExit("HEALTH: no series returned chapters. Refusing to write.")

    js = lambda v: json.dumps(v, ensure_ascii=False)                        # noqa: E731
    L = ["# comicブースト, read from its own server-rendered chapter lists.",
         "#",
         "# Reconnaissance filed this host `strategy: none`, which was wrong: the pages are plain",
         "# HTML and the dates are stated per chapter. Some of what it carries is 出張掲載, a run",
         "# posted in one day to mark a tankobon, and those dates are left as they are. A date",
         "# shared by a whole run is the signature importdates.py already looks for.",
         "source: webpages", "platform: comic-boost", 'platform_name: "comicブースト"',
         "publisher: フレックス", f"retrieved: {datetime.date.today().isoformat()}",
         "record_type: web_work_chapters", "identification_mode: known-work",
         "date_basis: stated", "date_confidence: reported", "works:"]
    for w in works:
        L.append(f"  - work_title: {js(w['work_title'])}")
        L.append(f"    url: {js(w['url'])}")
        L.append(f"    chapter_count: {len(w['chapters'])}")
        L.append("    chapters:")
        for c in w["chapters"]:
            L.append(f"      - title: {js(c['title'])}")
            L.append(f"        updated: {c['updated']}")
            L.append(f"        access_modes: {js(c['access_modes'])}")
    L.append("")
    pathlib.Path(a.out).write_text("\n".join(L))
    print(f"{len(works)} work(s), {sum(len(w['chapters']) for w in works)} chapters -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
