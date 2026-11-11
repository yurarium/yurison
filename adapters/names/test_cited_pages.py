#!/usr/bin/env python3
"""cited_pages.py: what a sweep of curated addresses records, driven with no network."""
import datetime
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import net  # noqa: E402
import testkit  # noqa: E402
from names import cited_pages as cp  # noqa: E402

COVERS = ["adapters/names/cited_pages.py"]

GUESSED = "https://sevenseas.com/series/riddle-story-of-devil/"
REAL = "https://sevenseasentertainment.com/series/akuma-no-riddle-riddle-story-of-devil/"
NDL = "https://ndlsearch.ndl.go.jp/books/R100000002-I1"
SHELL = "https://yenpress.com/9781975336233/mizuno-and-chayama"
PRIVATE = "https://example.jp/private/page"
MADB = "https://mediaarts-db.artmuseums.go.jp/id/C1"
PROSE = "<p>" + "A long description of the book, as a catalogue page would print it. " * 4 + "</p>"

DOC = {
    "titles": {
        "悪魔のリドル": {"en": "Akuma no Riddle: Riddle Story of Devil", "basis": "licensed",
                       "source_kind": "licensor", "source_url": REAL},
        "guessed": {"en": "Riddle Story of Devil", "basis": "licensed", "source_kind": "licensor",
                    "source_url": GUESSED},
        "水野と茶山": {"en": "Mizuno and Chayama", "basis": "licensed", "source_kind": "licensor",
                    "source_url": SHELL},
        "ours": {"en": "Wine Girls", "basis": "translated", "source_kind": "derived",
                 "reading": "ワイン", "reading_url": NDL},
        "madb": {"en": "GUNBURED × SISTERS", "basis": "official-jp", "source_kind": "bibliography",
                 "source_url": MADB},
        "hidden": {"en": "Hidden", "basis": "licensed", "source_kind": "licensor",
                   "source_url": PRIVATE},
    },
    "authors": {"x": {"reading": "エックス", "reading_url": NDL, "source_url": "not an address"}},
}

PAGES = {
    REAL: "<!doctype html><html><h1>Akuma no Riddle: Riddle Story of Devil</h1>" + PROSE + "</html>",
    SHELL: "<!DOCTYPE html><html><h1>Mizuno</h1>" + PROSE + "</html>",
    MADB: "<!doctype html><html><div id=app></div><script>" + PROSE + "</script></html>",
    NDL: "<!doctype html><html>ワイン</html>",
}


def page(url):
    if url in PAGES:
        return net.Result(PAGES[url], 200, url, None, False, None, "h")
    if url == GUESSED:
        return net.Result(None, 404, url, None, False, "HTTP 404", "h")
    return net.Result(None, 503, url, None, False, "HTTP 503", "h")


def fetch_all(urls):
    return {u: page(u) for u in urls}


def robots(host):
    return "User-agent: *\nDisallow: /private/\n" if host == "example.jp" else None


def main(s):
    cites = cp.cited(DOC)
    s.eq(sorted(cites), sorted([REAL, GUESSED, SHELL, NDL, PRIVATE, MADB]),
         "every address a curated entry gives, once, and nothing that is not an address")
    s.eq(len(cites[NDL]), 2, "two entries citing one page are two citations of one address")
    s.eq([c["en"] for c in cites[NDL]], [None, None],
         "a reading's catalogue page and our own translation are not looked for an English name")
    s.eq(cites[REAL][0]["en"], "Akuma no Riddle: Riddle Story of Devil",
         "a licensed name is looked for on the page it cites")
    art = cp.cited({"titles": {"w": {"en": "WAVER(S)", "basis": "official-jp",
                                     "source_kind": "publisher-jp", "source_url": REAL,
                                     "en_shown": "artwork"}}})
    s.eq(art[REAL][0]["en"], None, "a name the page sets only in its artwork is not looked for")
    both = {"en": "Otherside Picnic", "basis": "licensed", "source_kind": "licensor",
            "source_url": REAL, "official": "Otherside Picnic", "official_url": SHELL}
    two = cp.cited({"titles": {"w": both}})
    s.eq((two[REAL][0]["en"], two[SHELL][0]["en"]), ("Otherside Picnic", "Otherside Picnic"),
         "the publisher's English beside a licensor's is looked for on its own page")
    two = cp.cited({"titles": {"w": dict(both, official_shown="artwork")}})
    s.eq(two[SHELL][0]["en"], None, "unless it too is set only in artwork")

    s.check(cp.shows("<h1>Akuma no Riddle &ndash; Riddle Story of Devil</h1>",
                     "Akuma no Riddle: Riddle Story of Devil"),
            "punctuation, entities and case are folded away before comparing")
    s.check(not cp.shows("<h1>Riddle Story of Devil</h1>", "Akuma no Riddle: Riddle Story of Devil"),
            "a page showing a shorter name does not show the cited one")
    s.check(not cp.is_markup('{"isbn": "978"}'), "a JSON answer is not a page to look in")
    s.check(not cp.robots_allows("User-agent: *\nDisallow: /private/\n", PRIVATE),
            "robots.txt is obeyed")
    s.check(cp.robots_allows(None, PRIVATE), "a host with no robots.txt sets no rule")

    day1, day2 = datetime.date(2026, 11, 1), datetime.date(2026, 11, 8)
    state = {}
    counts = cp.run(DOC, state, day1, fetch_all, robots)
    s.eq(counts, {"answered": 4, "absent": 1, "disallowed": 1}, "one run opens every address")
    s.eq(state[REAL]["shows"], {"Akuma no Riddle: Riddle Story of Devil": True},
         "the licensor page shows the name cited to it")
    s.eq(state[SHELL]["shows"], {"Mizuno and Chayama": False},
         "a page with text that does not carry the name is recorded as not showing it")
    s.check("shows" not in state[MADB],
            "a shell its scripts fill in is not searched, so it is never a page that lacks the name")
    s.check("shows" not in state[NDL], "an address no English rests on is not searched")
    s.eq(state[PRIVATE]["outcome"], "disallowed", "nothing is sent where robots.txt says not to")
    s.eq(cp.absent(state, DOC), [], "one 404 is not yet a finding")
    s.eq(cp.unshown(state, DOC), [("titles", "水野と茶山", SHELL, "Mizuno and Chayama")],
         "the names a page did not show are listed for a person")

    s.eq(cp.run(DOC, state, day2, fetch_all, robots), {}, "nothing is due again inside recheck_days")
    cp.run(DOC, state, day2, fetch_all, robots, recheck_days=0)
    s.eq(cp.absent(state, DOC), [("titles", "guessed", GUESSED)],
         "a second 404 in a row is the finding the gate counts")

    # A refusal between two 404s says nothing about the page, so the run is not reset by it.
    flaky = {GUESSED: {"checked": "2026-10-01", "outcome": "absent", "absent_runs": 1,
                       "first_absent": "2026-10-01"}}
    cp.record(flaky, GUESSED, "refused", day1, cites[GUESSED])
    s.eq(flaky[GUESSED]["absent_runs"], 1, "a refusal keeps the count of 404s it interrupted")
    cp.record(flaky, GUESSED, "answered", day2, cites[GUESSED], text="<html></html>")
    s.check("absent_runs" not in flaky[GUESSED], "and an answer ends it")

    def refusing(host):
        raise net.Refused("no")
    s.eq(cp.run(DOC, {}, day1, fetch_all, refusing)["robots.txt not served"], 6,
         "each host whose robots.txt is not served is counted once")
    open_ = {}
    cp.run(DOC, open_, day1, fetch_all, refusing)
    s.eq(open_[PRIVATE]["outcome"], "refused",
         "and read as stating no rule, so its pages are opened and record what they answered")
    s.eq(open_[REAL]["outcome"], "answered", "a page behind an unserved robots.txt is read")
    s.eq(len(cp.due(open_, cites, day2, None, 90)), 1,
         "a refused page is asked again after a week, not at the next rotation")

    gone = {"https://example.jp/old": {"checked": "2026-10-01", "outcome": "absent",
                                        "absent_runs": 3}}
    s.eq(cp.run(DOC, gone, day1, fetch_all, robots).get("dropped"), 1,
         "an address no entry cites any more is dropped from the state")
    s.check("https://example.jp/old" not in gone, "so its 404s count against nobody")

    s.eq(cp.due({}, cites, day1, 2, 90), sorted(cites)[:2], "a limit caps one run")

    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "s.yaml"
        cp.save(state, p)
        s.eq(cp.load(p), state, "the state survives being written and read back")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "names.cited_pages"))
