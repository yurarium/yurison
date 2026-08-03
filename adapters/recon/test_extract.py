#!/usr/bin/env python3
"""recon/extract.py: pulling dated chapter entries out of whatever a page happens to embed."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import extract


def main(s):
    # A date this project will store must be a real calendar date in a plausible range. Publication
    # dates outside it are parser noise, and a wrong date is worse than no date because it silently
    # reorders the feed.
    s.eq(extract.norm_date("2026-08-03"), "2026-08-03", "an ISO date passes through")
    s.eq(extract.norm_date("published 2026-8-3 by x"), "2026-08-03", "a date is found and padded")
    s.check(extract.norm_date("1200-01-01") is None, "a year before 1990 is refused")
    s.check(extract.norm_date("2026-13-01") is None, "month 13 is refused")
    s.check(extract.norm_date("2026-01-45") is None, "day 45 is refused")
    s.check(extract.norm_date("no date here") is None, "text without a date yields none")
    s.check(extract.norm_date(None) is None, "None yields none rather than raising")

    # JSON-LD is the best case: the publisher states the structure.
    page = ('<html><script type="application/ld+json">'
            + json.dumps({"@type": "Book", "datePublished": "2026-07-01", "name": "第1話"})
            + '</script></html>')
    got = extract.try_jsonld(page)
    s.check(got is not None, "json-ld is found when present")
    s.check(extract.try_jsonld("<html>no script</html>") in (None, [], {}),
            "a page without json-ld yields nothing rather than raising")

    # entries_from_obj walks arbitrary nesting, because platforms bury the list at varying depth.
    obj = {"props": {"pageProps": {"episodes": [
        {"title": "第1話", "date": "2026-01-01"}, {"title": "第2話", "date": "2026-01-08"}]}}}
    ents = extract.entries_from_obj(obj)
    s.check(isinstance(ents, list), "walking a nested object returns a list")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "recon.extract"))
