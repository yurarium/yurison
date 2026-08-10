#!/usr/bin/env python3
"""What マガポケ says about its own series: how long it is, and what each episode was called.

Two things live here because they are two readings of the same claim. `episode_ids` counts the run
off the series page; `feed_episodes` reads the run itself out of the feed the platform publishes
next to it. The count is what caught the gap and the feed is what closes it, and keeping them
together is what lets one check the other.

HOW MANY EPISODES, read from the series page
============================================

WHY THIS EXISTS. Every one of our twelve マガポケ works capped at ten to twelve chapters, which is
what a rolling free window looks like rather than a catalogue. 将来的に死んでくれ was the case that
made it visible: we held ten chapters ending in October 2019 and filed the work dormant, while the
platform's own page lists forty-two episodes. The work was not dormant and the capture was not
current; we had been reading the free window and calling it the series.

WHAT THE PAGE STATES. The page carries a key map naming `episode_id_list`, and then, further along
in the run of values, the ids themselves. That is the platform counting its own series, so it is an
attestation about the length of the run under DEFINITIONS §5, and it is worth having even though it
carries no titles or dates: it says how much of a series we are missing.

HOW IT IS FOUND. Not by the key, which holds a position into a value table rather than the ids. The
list is found by its shape: an array of N integers followed immediately by a run of exactly N more.
The array is the positions and the run is the ids, and the two agreeing on N is the parse checking
itself. Reading the positions instead would give a list of the right length and entirely wrong
values, which is the failure this is written to make impossible.

WHAT IT IS NOT. A chapter list. There are no titles and no dates in the id list, so it cannot fill
in the chapters we lack. What it does is stop a truncated capture being read as a finished
serialisation, and it is now also the yardstick the feed below is measured against.

WHAT EACH EPISODE WAS CALLED, read from the series feed
=======================================================

WHERE THE FEED CAME FROM. The episode page states the episode in its own data layer: `episode_name`
is the 【第N話】… string that also reaches the <title> tag, and `start_time` is a date, so the run
could have been rebuilt one episode page at a time. Six hundred requests. The same data layer also
carries `rss_feed_url`, and that feed holds the WHOLE series at
`https://mgpk-cdn.magazinepocket.com/static/rss/<title_id>/feed.xml`: title, date, author and
episode URL for every episode, oldest to newest, in one request per series. 将来的に死んでくれ's
returns all 42. So the route is the platform's own feed and the episode page is not fetched at all,
which is also the posture REQUIREMENTS §5 asks for: the listing, never the reader page.

THE FEED IS CHECKED AGAINST TWO THINGS WE ALREADY HELD, because a feed nobody has cross-examined is
just a longer list.

Against the id list on the series page: 21 series, and the item count equals `episodes_stated`
exactly on 18 of them. The other three are each over by one, and each of those has exactly one item
dated in the future. The page counts what it has published and the feed adds what it has scheduled,
which is REQUIREMENTS §5's "a future date is a schedule, never a release" arriving from a second
direction. build.py already drops future-dated chapters and counts them as upcoming, so they are
written here rather than silently discarded.

Against the free window we captured by rendering the page: 202 chapters across 30 works matched on
title and date, with nothing disagreeing and nothing missing. The feed says what the page says and
keeps going.

WHAT THE DATES ARE WORTH. `<pubDate>`, which unlike GigaViewer's Atom `<updated>` is a publication
date by the format's own definition. It still carries the import signature REQUIREMENTS §5
describes, and here it is blatant: every one of ハロー、メランコリック！'s 40 episodes is dated
2021-11-11 13:00:00, and 46 of きたない君がいちばんかわいい's 63 are dated 2022-03-10 14:00:00. Those
are the days 講談社 loaded a finished series onto the platform. The dates are the honest record of
what the source says and §4 keeps them; `adapters/importdates.py` is what stops them being read as
publication, and it is left to do that job rather than second-guessed here. No clustering rule is
computed in this module, because two producers of one fact is this project's most-repeated bug.

WHAT THE FEED DOES NOT SAY. Access. There is no free, ticket or point state anywhere in it, and
none is invented: that comes from the rendered page, for the ten-episode window where the platform
shows it, and the rest of the run is silent about access rather than free.
"""
import re
import htmlbits as _htmlbits                                            # noqa: E402

# The page must say it has such a list at all before its shape is trusted.
KEY = '"episode_id_list"'

PAIR = re.compile(r"\[(\d+(?:,\d+)*)\]((?:,\d+)+)")


def episode_ids(html):
    """Every episode id the page lists for the series, in the order the page gives them.

    Empty where the page carries no such list, or where it carries one in a shape this does not
    recognise. A page redesign therefore reports nothing rather than something wrong.
    """
    h = html or ""
    if KEY not in h:
        return []
    for m in PAIR.finditer(h):
        pos = m.group(1).split(",")
        run = [x for x in m.group(2).split(",") if x]
        if len(run) == len(pos) and len(pos) > 1:
            return [int(x) for x in run]
    return []


def total_episodes(html):
    """How many episodes the platform says the series has, or None where it says nothing."""
    return len(episode_ids(html)) or None


# ── the series feed ────────────────────────────────────────────────────────────────────────────
FEED = "https://mgpk-cdn.magazinepocket.com/static/rss/{}/feed.xml"
TITLE_URL = "https://pocket.shonenmagazine.com/title/{}"

# The id in a work URL is zero-padded to five digits and the feed path is not padded at all.
TITLE_ID = re.compile(r"https?://pocket\.shonenmagazine\.com/title/(\d+)")

# Scoped to <item> deliberately. The channel has a <title>, a <pubDate> and a <link> of its own, and
# a pattern run over the whole document collects them as a 43rd episode named マガポケ（作品名）
# dated the same day as the newest chapter. Each item is matched first and its fields only inside it.
ITEM = _htmlbits.RSS_ITEM
CHANNEL_TITLE = re.compile(r"<channel>\s*<title>([^<]*)</title>")
FIELD = {k: re.compile(rf"<{k}[^>]*>([^<]*)</{k}>") for k in
         ("title", "link", "guid", "pubDate", "author")}


def feed_url(title_id):
    """Where the feed for a series lives, given anything that names the series."""
    m = TITLE_ID.match(str(title_id or ""))
    n = (m.group(1) if m else str(title_id or "")).lstrip("0")
    return FEED.format(n) if n else ""


def title_ids(works):
    """Every マガポケ series id named by a list of work records, oldest padding stripped.

    Fed from the files we already hold rather than from a list kept by hand, so a work the render
    or sitemap adapter finds next week is fetched the run after without anyone editing anything.
    """
    out = {}
    for w in works or []:
        if not isinstance(w, dict):
            continue
        for u in [w.get("url") or ""] + (w.get("urls") if isinstance(w.get("urls"), list) else []):
            m = TITLE_ID.match(str(u))
            if m:
                out.setdefault(m.group(1).lstrip("0"), w.get("work_title") or w.get("title") or "")
    return out


def feed_series_name(xml):
    """Which series the feed says it is: マガポケ（将来的に死んでくれ） gives the name inside.

    The pairing of an id with a name comes from a work record and an id is a number, so a wrong
    pairing produces a plausible list of somebody else's episodes. The feed states the answer, so
    the pairing is checked rather than trusted.

    The brackets are counted from the end. Both the wrapper and some work titles use them, and
    念願の悪役令嬢(ラスボス)の身体を手に入れたぞ！ has a pair of its own inside the wrapper's.
    """
    m = CHANNEL_TITLE.search(xml or "")
    if not m:
        return None
    inner = _last_bracketed(m.group(1))
    return inner.strip() if inner else None


CLOSERS = {")": "(", "）": "（"}
OPENERS = set(CLOSERS.values())


def _last_bracketed(s):
    """Contents of the last balanced bracket group, or None. See gigaviewer/series_feeds.py, which
    learned the same lesson on a platform whose own name contains brackets."""
    for i in range(len(s) - 1, -1, -1):
        if s[i] not in CLOSERS:
            continue
        depth = 0
        for j in range(i, -1, -1):
            if s[j] in CLOSERS:
                depth += 1
            elif s[j] in OPENERS:
                depth -= 1
                if depth == 0:
                    return s[j + 1:i]
        return None
    return None


def feed_date(stamp):
    """The date JST considers this to be, from an RFC 822 stamp, or "" where it is unreadable.

    Every stamp observed is already +0900, but the conversion is done rather than assumed: slicing
    a UTC stamp dated a whole platform a day early on GigaViewer, and that bug is not worth having
    twice. An unparseable stamp yields nothing, because a chapter with no date is a chapter and a
    chapter with a wrong date is a lie about when it came out.
    """
    import email.utils
    try:
        d = email.utils.parsedate_to_datetime(str(stamp or "").strip())
    except (TypeError, ValueError):
        return ""
    if d is None:
        return ""
    if d.tzinfo is None:
        return d.date().isoformat()
    import datetime
    return d.astimezone(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()


def reconcile_name(held, stated):
    """Which name to record for a series, and whether the pairing was wrong. (name, misattributed).

    The id comes from a work record's URL and the name from the same record, so a record pointing
    at the wrong title id hands us somebody else's whole history under our title. The feed says
    which series it is, so the pairing is checked rather than trusted.

    COMPARED NORMALISED, and the first version was not. Seven of the 37 series tripped it, every
    one on punctuation width alone: the platform writes 私の百合はお仕事です！ and our catalogue
    writes 私の百合はお仕事です!. That is not a misattribution, and seven false reports of one are
    how a real one goes unnoticed. `textnorm.norm` is the form the rest of the project compares
    titles in, so it is the form asked here.

    The catalogue's spelling wins where the two agree. Taking the platform's would put a second
    spelling of seven titles into data/source for no gain, since everything downstream folds them.
    """
    import textnorm

    if not stated:
        return held, False
    if not held:
        return stated, False
    if textnorm.norm(stated) == textnorm.norm(held):
        return held, False
    return stated, True


def feed_episodes(xml):
    """Every episode the feed lists, in the order the feed gives them, or [] where it lists none.

    That order is newest first, which is also how rendered-magapoke.yaml and every other chapter
    list in data/source/ is written. Nothing downstream reads a chapter by position, so this is
    only about a file staying diffable against its neighbours.

    An item with no title or no readable date is dropped: those two are what the row is for.
    """
    import html as _html
    out = []
    for b in ITEM.findall(xml or ""):
        def f(k):
            m = FIELD[k].search(b)
            return _html.unescape(m.group(1)).strip() if m else ""
        t, when = f("title"), feed_date(f("pubDate"))
        if not t or not when:
            continue
        out.append({"title": t, "updated": when, "url": f("link"),
                    "episode_id": f("guid"), "author": f("author") or None})
    return out


def main(argv=None):
    """Fetch each マガポケ title page and record how long the platform says the series is."""
    import argparse, datetime, json, pathlib, time, urllib.request
    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--works", default="data/source/webpages/sitemap-magapoke.yaml")
    ap.add_argument("--out", default="data/coverage/magapoke-lengths.yaml")
    ap.add_argument("--pause", type=float, default=1.2)
    a = ap.parse_args(argv)

    src = yaml.safe_load(pathlib.Path(a.works).read_text()) or {}
    ua = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
    rows, silent = [], 0
    for w in (src.get("works") or []):
        url = w.get("url") or ""
        if "/title/" not in url:
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read().decode("utf-8", "replace")
        except Exception as e:
            print(f"  skip {w.get('work_title')}: {e}")
            continue
        ids = episode_ids(html)
        if not ids:
            silent += 1
        else:
            rows.append({"work_title": w["work_title"], "url": url, "episodes_stated": len(ids),
                         "last_episode_url": f"{url}/episode/{ids[-1]}"})
        time.sleep(a.pause)

    if not rows:
        raise SystemExit("HEALTH: no page stated an episode count. Refusing to write.")

    js = lambda v: json.dumps(v, ensure_ascii=False)
    L = ["# How many episodes マガポケ states each series has, read from the series page.",
         "#",
         "# The platform counting its own series, so an attestation about the length of the run.",
         "# It carries no titles and no dates, so it cannot fill in the chapters we lack; what it",
         "# does is say how much of a series we are missing, which is what stops a capture of the",
         "# free window being read as the whole serialisation.",
         "#",
         "# `last_episode_url` is the point of it. Holding fewer chapters than the platform states",
         "# does not by itself mean our newest is stale: 将来的に死んでくれ has 42 episodes, we hold",
         "# 10, and the one we call newest is the 42nd. Where our newest is the last episode the",
         "# platform lists, the date is the series' real latest and only the count is wrong. Where",
         "# it is not, the work has run on past what we saw and nothing may be concluded from our",
         "# silence.",
         "source: magapoke", "platform: magapoke", 'platform_name: "マガポケ"',
         "role: series-length", f"retrieved: {datetime.date.today().isoformat()}",
         f"pages_silent: {silent}", "works:"]
    for r in sorted(rows, key=lambda x: x["work_title"]):
        L.append(f"  - work_title: {js(r['work_title'])}")
        L.append(f"    url: {js(r['url'])}")
        L.append(f"    episodes_stated: {r['episodes_stated']}")
        L.append(f"    last_episode_url: {js(r['last_episode_url'])}")
    L.append("")
    pathlib.Path(a.out).write_text("\n".join(L))
    print(f"{len(rows)} series stated, {silent} silent -> {a.out}")
    return 0


# How few series may come back before the run is treated as a failure of the route rather than a
# thin day. Set below the 37 currently known so a work leaving the catalogue does not trip it, and
# high enough that a changed feed path, which would return nothing at all, does.
MIN_SERIES = 20


def carry_over(path, fetched_ids):
    """Works already in the file that this run did not fetch, so a partial run keeps them.

    The target list is derived from other source files, and those are rewritten every run by
    adapters with their own coverage. A work that drops out of them for a day must not take its
    whole chapter history with it: `adapters/webpages/releases.py` explains what that cost when a
    pass reaching 65 works deleted 49, and the same fault has now been fixed in three adapters.

    A series this run fetched is replaced, because a fresh feed beats a stored one. A series it did
    not fetch is kept, because not asking for a feed is not a finding about the work.
    """
    import pathlib
    import yaml

    p = pathlib.Path(path)
    if not p.exists():
        return []
    old = yaml.safe_load(p.read_text()) or {}
    # Both sides stripped of padding. A work URL writes the id as 00195 and the feed path writes
    # it as 195, so comparing the strings as given makes every series look unfetched and carries
    # the whole file over on top of the fresh reading.
    done = {str(x).lstrip("0") for x in fetched_ids}
    keep = []
    for w in (old.get("works") or []):
        m = TITLE_ID.match(str(w.get("url") or ""))
        if m and m.group(1).lstrip("0") in done:
            continue
        w = dict(w, episodes=w.get("chapters") or [])
        w.pop("chapters", None)
        w.pop("chapter_count", None)
        keep.append(w)
    return keep


def chapters_main(argv=None):
    """Fetch each マガポケ series feed and write the chapters the platform lists for it."""
    import argparse, datetime, glob, json, pathlib, time, urllib.request
    import yaml

    ap = argparse.ArgumentParser(description="マガポケ series feeds: titles and dates per episode")
    ap.add_argument("--targets", nargs="*", default=["data/source/webpages/*.yaml",
                                                     "data/coverage/magapoke-lengths.yaml"],
                    help="glob patterns of files whose works name マガポケ series URLs")
    ap.add_argument("--out", default="data/source/webpages/magapoke-feeds.yaml")
    ap.add_argument("--retrieved", default=datetime.date.today().isoformat())
    ap.add_argument("--pause", type=float, default=1.5)
    ap.add_argument("--limit", type=int, default=400)
    a = ap.parse_args(argv)

    wanted = {}
    for pat in a.targets:
        for f in sorted(glob.glob(pat)):
            try:
                d = yaml.safe_load(pathlib.Path(f).read_text())
            except Exception:                                                    # noqa: BLE001
                continue
            if isinstance(d, dict):
                for tid, name in title_ids(d.get("works")).items():
                    wanted.setdefault(tid, name)

    ua = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
    works, failed, corrected = [], [], 0
    for tid, name in sorted(wanted.items(), key=lambda kv: int(kv[0]))[: a.limit]:
        url = feed_url(tid)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=40) as r:
                xml = r.read().decode("utf-8", "replace")
        except Exception as e:                                                   # noqa: BLE001
            failed.append((tid, name, type(e).__name__))
            continue
        finally:
            time.sleep(a.pause)
        eps = feed_episodes(xml)
        if not eps:
            failed.append((tid, name, "no items"))
            continue
        name, wrong = reconcile_name(name, feed_series_name(xml))
        corrected += wrong
        works.append({"work_title": name, "title_id": tid,
                      "url": TITLE_URL.format(tid.zfill(5)), "feed": url, "episodes": eps})

    if len(works) < MIN_SERIES:
        raise SystemExit(f"HEALTH: {len(works)} series returned a feed, below {MIN_SERIES}. "
                         "The feed path or its shape may have changed. Refusing to write.")

    fetched = len(works)
    works += carry_over(a.out, [w["title_id"] for w in works])
    works.sort(key=lambda w: w["work_title"])

    js = lambda v: json.dumps(v, ensure_ascii=False)
    L = ["# マガポケ — every episode of each series, from the feed the platform publishes for it.",
         "#",
         "# One request per series to",
         "# https://mgpk-cdn.magazinepocket.com/static/rss/<title_id>/feed.xml, which the episode",
         "# page names in its own data layer as rss_feed_url. It holds the whole run rather than",
         "# the ten-episode free window the work page draws, which is as far as the three other",
         "# マガポケ files here could reach and why each of them is marked partial.",
         "#",
         "# Checked against both things we already held. The item count equals the series page's",
         "# own episode_id_list except where the feed carries a future-dated episode the page has",
         "# not published yet, and every one of the 202 chapters captured from the rendered page",
         "# agrees on title and date.",
         "#",
         "# Dates are <pubDate>, a publication date by the format's definition. Some of them are",
         "# still the day 講談社 loaded a finished series onto the platform rather than the day the",
         "# chapter came out: all 40 of ハロー、メランコリック！ sit on 2021-11-11. Kept as the source",
         "# states them (REQUIREMENTS §4); adapters/importdates.py is what marks such a date unfit",
         "# to headline a series.",
         "#",
         "# No access state. The feed carries none, so these chapters say nothing about access",
         "# rather than saying free. No genre label is established here (DEFINITIONS §4).",
         "source: magapoke", "platform: magapoke", 'platform_name: "マガポケ"',
         'publisher: "講談社"', f"retrieved: {a.retrieved}",
         "record_type: web_work_chapters", "identification_mode: discovery-candidate",
         "date_basis: platform-stated", "date_confidence: reported",
         f"series_fetched: {fetched}", f"series_held: {len(works)}", "works:"]
    for w in works:
        L.append(f"  - work_title: {js(w['work_title'])}")
        if w.get("title_id"):
            L.append(f"    title_id: {js(w['title_id'])}")
        L.append(f"    url: {js(w['url'])}")
        if w.get("feed"):
            L.append(f"    feed: {js(w['feed'])}")
        L.append(f"    chapter_count: {len(w['episodes'])}")
        L.append("    chapters:")
        for e in w["episodes"]:
            L.append(f"      - title: {js(e['title'])}")
            L.append(f"        updated: {e['updated']}")
            for k in ("author", "url"):
                if e.get(k):
                    L.append(f"        {k}: {js(e[k])}")
            if e.get("access_modes"):
                L.append(f"        access_modes: {js(e['access_modes'])}")
    L.append("")
    pathlib.Path(a.out).write_text("\n".join(L))

    n = sum(len(w["episodes"]) for w in works)
    print(f"series fetched : {fetched} of {len(wanted)} named")
    print(f"series held    : {len(works)}")
    print(f"chapters       : {n}")
    if corrected:
        print(f"MISATTRIBUTED  : {corrected} — a work record named a title id belonging to another "
              "series; corrected from the feed's own title")
    if failed:
        print(f"failed         : {len(failed)}  {failed[:6]}")
    print(f"written        : {a.out}")
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "chapters":
        raise SystemExit(chapters_main(sys.argv[2:]))
    raise SystemExit(main())
