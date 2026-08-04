#!/usr/bin/env python3
"""How many episodes マガポケ says a series has, read from its own page.

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

WHAT IT IS NOT. A chapter list. There are no titles and no dates here, so this cannot fill in the
chapters we lack, and it must not be used to date anything. What it does is stop a truncated
capture being read as a finished serialisation.
"""
import re

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


if __name__ == "__main__":
    raise SystemExit(main())
