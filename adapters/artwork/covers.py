#!/usr/bin/env python3
"""Fetch a work's splash or cover image, so a person can read the names off it.

WHY THIS EXISTS. A platform's own artwork carries two things the markup around it does not. The
Latin title a work gives itself is often set into the logo and nowhere in the page text, and a
title's furigana is printed over the kanji on the splash where no reading field states it. Both
outrank anything this database composes: a name a work gives itself is the name, and a reading the
publisher prints is not a guess. Neither is reachable by parsing HTML, so the picture is fetched
and a person looks at it.

IT IS A CURATION PASS AND NOT PART OF THE BUILD. Nothing here writes to `data/source`, no adapter
imports it, and `build.py` never calls it. What it produces is a local cache of images and a ledger
of what was fetched; what a person produces from it is a curated name, which goes through
`data/names/curated.yaml` like any other and carries its own basis and source.

THE MEDIA POLICY IS THE REASON THE CACHE SITS OUTSIDE THE REPOSITORY. REQUIREMENTS §2 says no image
file is ever committed, and states the risk plainly: committing a cover means GitHub stores and
serves a copy, and a takedown removes the repository rather than trimming it. That rule is about
the REPOSITORY, and this obeys it by writing to the cache directory beside the checkout, which is
where every other fetch this project makes already lands and which nothing commits or publishes.

  What leaves this pass is a FACT: a Latin title, a reading. §2 says bibliographic facts are safe
  to store and titles are too short for copyright. The image is a working copy that a person reads
  and the site never references. The separate rule about REFERENCING a cover by URL, which permits
  openBD alone, is untouched: nothing here puts an image on a page.

POLITENESS IS NOT REIMPLEMENTED. `net.fetch_many` already paces per host, runs hosts concurrently,
backs off a 503 for every worker at once, keeps redirects and never caches a refusal. This asks it
for pages and then for images, so no host sees traffic faster than any other pass here makes it.
"""
import argparse
import json
import pathlib
import re
import sys
import time
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import net                                                              # noqa: E402
import paths                                                            # noqa: E402

#: Where the images and the ledger live: beside the checkout, never inside it. See the header.
CACHE = paths.CACHE_ROOT / "covers-cache"

#: A DOM `adapters/render/` already produced, which is the only way to read some platforms. Two
#: refuse a plain fetch outright: comic-fuz answers 403 to this user agent on every request, and
#: comic.pixiv.net serves a shell that builds its page in JavaScript, so the markup that comes back
#: states no splash. Between them that was 52 works of the first 640, and the pictures were already
#: on this disk. Reading them costs no request at all, which is the politest fetch there is.
RENDERED = paths.CACHE_ROOT / "render-cache"


def rendered(url):
    """The rendered DOM for this address where one was already made, else None.

    THE KEY IS `render/releases.py`'s, copied deliberately and narrowly. Importing that module
    would drag a headless browser's dependencies into a pass that only wants to read a file, and
    the key is one line. What it must not do is DIVERGE, so `test_covers` pins the two together by
    asking the real function for its answer.
    """
    f = RENDERED / (re.sub(r"[^A-Za-z0-9]", "_", url)[-120:] + ".html")
    try:
        return f.read_text(encoding="utf-8", errors="replace") if f.exists() else None
    except OSError:
        return None

#: A page states its splash in one of these, in this order of preference. `og:image` is what a
#: platform hands a social card and is the artwork it chose to represent the work, which is exactly
#: the image with the logo on it. The others are fallbacks that some older platforms still use.
META = (
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)', re.I),
    re.compile(r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)', re.I),
)

#: A platform's own placeholder is not artwork. These are served where a work has no cover, so
#: caching them fills the store with one grey rectangle under many names.
PLACEHOLDER = re.compile(r"(no[-_]?image|noimg|placeholder|default[-_](cover|thumb)|blank)", re.I)


def image_url(html, page_url):
    """The splash a page states, made absolute, or None where it states none."""
    for pat in META:
        m = pat.search(html or "")
        if m:
            u = m.group(1).strip()
            if not u or PLACEHOLDER.search(u):
                return None
            # A TAG CAN HOLD SOMETHING THAT IS NOT AN ADDRESS. 123hon.com serves its og:image
            # containing `<?php echo $ContentsData[...`, an unrendered template, and `urljoin` made
            # a URL out of it that `urlopen` refused for holding control characters. The page is
            # answering; it is simply not stating a picture, so this reads as no image rather than
            # as a host that could not be reached.
            if any(c in u for c in "<>\"'") or any(ord(c) < 0x20 for c in u):
                return None
            return urllib.parse.urljoin(page_url, u)
    return None


def extension(url, data):
    """The file extension to store under, taken from the BYTES and not from the address.

    A platform commonly serves `.../cover.jpg?w=640` that is really a WebP, and one serves an
    address with no extension at all. The magic number is what the file is.
    """
    sigs = ((b"\x89PNG\r\n\x1a\n", ".png"), (b"\xff\xd8\xff", ".jpg"), (b"GIF8", ".gif"),
            (b"RIFF", ".webp"), (b"<svg", ".svg"), (b"<?xml", ".svg"))
    for sig, ext in sigs:
        if (data or b"").startswith(sig):
            return ext
    tail = pathlib.PurePosixPath(urllib.parse.urlparse(url).path).suffix.lower()
    return tail if tail in (".png", ".jpg", ".jpeg", ".gif", ".webp") else ".bin"


def targets(series, recent_first=True):
    """[(work, page url, latest date)] for every web work carrying an address.

    RECENTLY UPDATED FIRST, because a pass that is cancelled after an hour should have covered the
    works most likely to have changed. Ordering is the whole of the difference: the tail is the
    same set either way, and a run that finishes reaches all of it.

    ONE ADDRESS PER WORK. A work serialising in three places has three, and the artwork on each is
    the same work's; fetching all three buys nothing and costs three hosts a request. The row's own
    preferred source is taken where it names one.
    """
    out = []
    for r in series or ():
        if not r.get("chapters"):
            continue
        srcs = [s for s in (r.get("sources") or []) if s.get("url")]
        if not srcs:
            continue
        pref = next((s for s in srcs if s.get("platform") == r.get("preferred")), srcs[0])
        out.append((r.get("work"), pref["url"], str(r.get("latest") or "")))
    out.sort(key=lambda x: (x[2] or ""), reverse=recent_first)
    return out


class Ledger:
    """What has been tried, so a cancelled run resumes and a later run is differential.

    IT RECORDS OUTCOMES AND NOT ONLY SUCCESSES. A work whose page states no splash is the case that
    makes this worth keeping: without a record, every rerun fetches that page again for ever to
    learn the same nothing. A permanent failure is remembered; a refusal is not, because a 503 is
    the host asking to be tried later.

    IT LIVES BESIDE THE CACHE IT DESCRIBES. A ledger in the repository would claim a fresh clone
    holds images that are not there.
    """

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.rows = {}
        if self.path.exists():
            try:
                self.rows = json.loads(self.path.read_text())
            except (OSError, ValueError):
                self.rows = {}

    def done(self, page):
        r = self.rows.get(page)
        return bool(r) and r.get("state") in ("stored", "no-image", "gone")

    def put(self, page, **row):
        self.rows[page] = {**row, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.rows, ensure_ascii=False, indent=1))
        tmp.replace(self.path)

    def counts(self):
        c = {}
        for r in self.rows.values():
            c[r.get("state")] = c.get(r.get("state"), 0) + 1
        return c


def run(series, cache=CACHE, minutes=240, limit=None, refresh=False, workers=8, batch=40):
    """Fetch pages, read the splash each states, fetch that, and record every outcome.

    IN BATCHES, AND THE LEDGER IS SAVED AFTER EACH. A four-hour pass killed at three hours has to
    keep three hours of work, so nothing is held in memory that a cancel would lose.
    """
    cache = pathlib.Path(cache)
    led = Ledger(cache / "ledger.json")
    todo = [t for t in targets(series) if refresh or not led.done(t[1])]
    if limit:
        todo = todo[:limit]
    started, done = time.time(), 0
    print(f"{len(todo)} work(s) to look at; {len(led.rows)} already in the ledger")

    for i in range(0, len(todo), batch):
        if (time.time() - started) / 60 >= minutes:
            print(f"time budget of {minutes} min reached; stopping cleanly")
            break
        chunk = todo[i:i + batch]
        # A PAGE SOMEBODY ALREADY RENDERED IS NOT FETCHED AGAIN. Asked before the network, so a
        # platform that refuses this agent or builds its page in JavaScript is answered from the
        # DOM the browser pass left behind rather than being asked and refused.
        have = {t[1]: rendered(t[1]) for t in chunk}
        ask = [t[1] for t in chunk if not have.get(t[1])]
        pages = net.fetch_many(ask, cache / "pages", max_age_days=30, workers=workers)
        wanted = {}
        for work, page, _latest in chunk:
            dom = have.get(page)
            if dom:
                iu = image_url(dom, page)
                if iu:
                    wanted[iu] = (work, page)
                else:
                    led.put(page, work=work, state="no-image",
                            why="the rendered page states no splash")
                continue
            res = pages.get(page)
            if res is None or res.text is None:
                state = "gone" if res is not None and net.is_permanent(res) else "unreachable"
                led.put(page, work=work, state=state,
                        why=(res.error if res is not None else "no result"))
                continue
            iu = image_url(res.text, res.final_url or page)
            if not iu:
                led.put(page, work=work, state="no-image", why="the page states no splash")
                continue
            wanted[iu] = (work, page)

        if wanted:
            got = net.fetch_many(list(wanted), None, workers=workers, binary=True)
            for iu, (work, page) in wanted.items():
                res = got.get(iu)
                if res is None or not res.raw:
                    state = "gone" if res is not None and net.is_permanent(res) else "unreachable"
                    led.put(page, work=work, state=state, image=iu,
                            why=(res.error if res is not None else "no result"))
                    continue
                name = net.cache_key(iu) + extension(iu, res.raw)
                out = cache / "images" / name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(res.raw)
                led.put(page, work=work, state="stored", image=iu, file=name,
                        bytes=len(res.raw))
        done += len(chunk)
        led.save()
        print(f"  {done}/{len(todo)}  {led.counts()}", flush=True)

    led.save()
    return led


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--series", default="data/build/series.json")
    ap.add_argument("--cache", default=str(CACHE))
    ap.add_argument("--minutes", type=float, default=240,
                    help="stop cleanly after this long; the ledger makes the next run continue")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--refresh", action="store_true",
                    help="look again at works the ledger has already settled")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--report", action="store_true", help="print the ledger's counts and stop")
    a = ap.parse_args(argv)

    if a.report:
        led = Ledger(pathlib.Path(a.cache) / "ledger.json")
        print(f"{len(led.rows)} work(s) recorded: {led.counts()}")
        return 0

    series = json.loads(pathlib.Path(a.series).read_text()).get("series") or []
    led = run(series, cache=a.cache, minutes=a.minutes, limit=a.limit,
              refresh=a.refresh, workers=a.workers)
    print(f"\nledger: {len(led.rows)} work(s) {led.counts()}")
    print(f"images: {pathlib.Path(a.cache) / 'images'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
