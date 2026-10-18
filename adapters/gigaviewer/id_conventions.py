#!/usr/bin/env python3
"""Whether a GigaViewer platform numbers every serial chapter's own id, sampled from its whole output.

WHY THIS EXISTS. くらげバンチ marks no one-shot as one, and titles both its one-shots and some
serials after the work. What tells them apart is the id the platform gives each episode in its page
data: `firstpenguin_requiem_005` for a serial's fifth chapter, a bare `saechan_tonari` for a
one-shot. Ten of the eleven one-shots this project holds there carry a bare id. But the two serials
the captures hold are too few to show that serials never do, because the captures follow the yuri
line only, so this reads the platform's own feed of everything it has just published.

WHAT IT RECORDS, per platform: of the sampled episodes whose page says their series is running
(`series_ongoing` 1, so certainly a serial), how many carry an id ending in an episode number. The
build trusts a bare id as a one-shot's only where every sampled serial's id is numbered and the
sample is at least MIN_SAMPLE. Platforms that number everything, one-shots included, as コミックDAYS
does (`16273_0001`), answer the question with nothing and are recorded as such.

    id_conventions.py [--out data/coverage/gigaviewer-id-conventions.yaml] [--cache DIR]
"""
import argparse
import datetime
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import net                                                              # noqa: E402
import paths                                                            # noqa: E402
from facts import serialisation as _ser                                 # noqa: E402
from series_feeds import page_facts                                     # noqa: E402

#: An id ending in an episode number: `_005`, `_0001`, `_001-1`, `_s0001-0`.
NUMBERED = re.compile(r"[_-][a-z]?0*\d{1,4}(?:[_-]\d+)?$", re.I)
#: The fewest running serials a sample must hold before it says anything.
MIN_SAMPLE = 10
#: How many of the platform feed's newest episodes are read.
SAMPLE = 30
EPISODE = re.compile(r'<link href="(https://[^"]+/episode/\d+)"')
#: The episode's own title in the page data, which says whether it is a side story.
EPISODE_TITLE = re.compile(r'(?:&quot;|")episode_title(?:&quot;|")\s*:\s*(?:&quot;|")([^&"]*)')


def numbered(content_id):
    return bool(NUMBERED.search(content_id or ""))


def measure(pages):
    """`{running, numbered}` over sampled episode pages' facts. A side story is left out: a running
    serial's 番外編 takes a bare id on くらげバンチ, and a side story is never a work of its own."""
    running = [f for f in pages if f.get("ongoing") and f.get("content_id")
               and not _ser.EXTRA_TITLE.search(f.get("episode_title") or "")]
    return {"running": len(running), "numbered": sum(numbered(f["content_id"]) for f in running)}


def keeps(m):
    """Whether a platform numbers every running serial's ids, on a sample large enough to say so."""
    return m.get("running", 0) >= MIN_SAMPLE and m.get("numbered") == m.get("running")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="data/coverage/gigaviewer-id-conventions.yaml")
    ap.add_argument("--cache", default=str(paths.cache("giga-id-sample")))
    ap.add_argument("--platforms", default="adapters/gigaviewer/platforms.yaml")
    a = ap.parse_args(argv)

    reg = (yaml.safe_load(open(a.platforms)) or {}).get("platforms") or []
    today = datetime.date.today().isoformat()
    out = {}
    for p in reg:
        feed = p.get("atom") or f"https://{p['host']}/atom"
        xml = net.fetch(feed, a.cache, max_age_days=1).text or ""
        facts = []
        for url in list(dict.fromkeys(EPISODE.findall(xml)))[:SAMPLE]:
            html = net.fetch(url, a.cache, max_age_days=30).text or ""
            t = EPISODE_TITLE.search(html)
            facts.append({**page_facts(html), "episode_title": t.group(1) if t else ""})
        m = measure(facts)
        out[p["name"]] = {**m, "keeps": keeps(m)}
        print(f"{p['name']:16} {m['numbered']}/{m['running']} running serials numbered"
              + ("  keeps" if keeps(m) else ""))
    pathlib.Path(a.out).write_text(
        "# Whether each GigaViewer platform numbers every running serial's episode id, sampled from\n"
        "# its own feed of everything it has just published. Written by\n"
        "# adapters/gigaviewer/id_conventions.py; see its docstring for what `keeps` licenses.\n"
        + yaml.safe_dump({"source": "gigaviewer", "role": "platform-convention",
                          "retrieved": today, "platforms": out},
                         allow_unicode=True, sort_keys=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
