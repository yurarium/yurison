#!/usr/bin/env python3
"""Whether the page each curated name cites is there, and whether it shows the name.

WHY THIS EXISTS. curate.py refuses an attributed name with no page behind it, and refuses one whose
note admits the page was never opened. Neither can tell a page somebody read from an address
somebody wrote down. The naming job's 悪魔のリドル cited sevenseas.com/series/riddle-story-of-devil/,
which returns 404, under a name the licensor's real page does not use. Its note happened to say the
address was guessed; one that said nothing would have passed every rule. Opening the address is the
only test, and it cannot run offline, so it runs on a schedule and the gate reads what it recorded.

WHAT IT RECORDS, per address, in data/state/cited-pages.yaml:

  answered    the host served a page. `shows` then says, for each attributed English name citing
              it, whether the page carries that name, compared with case, spacing and punctuation
              folded away. Only a licensed or official-jp name is looked for, because those claim
              the page states them; a reading's catalogue page states kana, not English.
  absent      404 or 410. `absent_runs` counts the runs in a row that said so, because one 404
              during a deploy is not evidence (net.py, WHAT THIS DOES NOT DO). An answer resets it.
  refused     the host declined: 403, 5xx, a timeout. Says nothing
              about the page, so it leaves `absent_runs` where it was, and it is asked again after
              RETRY_REFUSED days rather than at the next rotation.
  disallowed  robots.txt asks us not to fetch it, so nothing was sent. Not a fault in the entry.

A NAME THE PAGE DOES NOT SHOW IS RECORDED, NOT CONCLUDED. A page with almost no readable text is a
shell its scripts fill in, and is not searched at all. One that has text may still set the English
only in its artwork, so `shows: false` is a lead for a person. An address
that keeps answering 404 is a finding, and the gate counts it.

WHICH ADDRESSES A RUN OPENS. Every address never checked, then the longest-unchecked of those not
looked at in `--recheck-days`, up to `--limit`. A new entry from the naming job is opened in the
first run after it lands; the rest rotate.

Usage:  cited_pages.py --cache DIR [--limit 300] [--recheck-days 90] [--retrieved YYYY-MM-DD]
"""
import argparse
import datetime
import html
import pathlib
import re
import sys
import unicodedata
import urllib.parse
import urllib.robotparser

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import net  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
CURATED = ROOT / "data" / "names" / "curated.yaml"
STATE = ROOT / "data" / "state" / "cited-pages.yaml"

#: The fields of a curated entry that hold an address, and whether an English name rests on it.
URL_FIELDS = {"source_url": True, "en_url": True, "reading_url": False}

#: The bases whose English claims the cited page states it.
STATED_BY_PAGE = ("licensed", "official-jp")

#: Seconds between requests to a host that wants more than net.PAUSE. ndl_books.PAUSE for the
#: national library, so this sweep is no faster against it than the pass that reads it.
PAUSES = {"ndlsearch.ndl.go.jp": 1.6, "id.ndl.go.jp": 1.6}

#: The product token robots.txt rules are matched against.
AGENT = "yurarium"


def cited(doc):
    """`{url: [citation]}` for every address a curated entry gives.

    A citation is `{kind, ja, field, en}`, with `en` set only where an English name the page is
    claimed to state rests on this address.
    """
    out = {}
    for kind, entries in (doc or {}).items():
        if not isinstance(entries, dict):
            continue
        for ja, e in entries.items():
            if not isinstance(e, dict):
                continue
            for field, carries_en in URL_FIELDS.items():
                url = str(e.get(field) or "").strip()
                if not url.startswith(("http://", "https://")):
                    continue
                en = None
                if (carries_en and e.get("en") and e.get("basis") in STATED_BY_PAGE
                        and (e.get("en_source_kind") or e.get("source_kind")) != "derived"
                        and (field == "en_url" or not e.get("en_url"))):
                    en = str(e["en"])
                out.setdefault(url, []).append({"kind": kind, "ja": str(ja), "field": field,
                                                "en": en})
    return out


def _fold(s):
    s = unicodedata.normalize("NFKC", html.unescape(str(s or ""))).casefold()
    return re.sub(r"[\W_]+", "", s)


#: Fewer readable characters than this and a page is a shell its scripts fill in the browser. The
#: media arts database serves 1.4 KB of markup with no title in it for every record.
SHELL = 200


def visible(text):
    """The characters a page shows a reader without running its scripts."""
    t = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", text or "")
    return " ".join(html.unescape(re.sub(r"(?s)<[^>]+>", " ", t)).split())


def is_markup(text):
    """Whether a body is a page that could carry a title: markup, and not an empty shell."""
    head = (text or "")[:4000].lower()
    return ("<html" in head or "<!doctype html" in head) and len(visible(text)) >= SHELL


def shows(text, en):
    """Whether a page carries an English name, case, spacing and punctuation folded away."""
    want = _fold(en)
    return bool(want) and want in _fold(text)


def robots_allows(robots_text, url):
    """Whether a robots.txt body lets AGENT fetch `url`. None for the body means no file."""
    if robots_text is None:
        return True
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(robots_text.splitlines())
    return rp.can_fetch(AGENT, url)


def outcome(result):
    """`answered`, `absent` or `refused`, in net.py's terms for what a fetch established."""
    return {net.ANSWERED: "answered", net.ABSENT: "absent"}.get(net.outcome(result), "refused")


#: Days before an address whose host declined is asked again. A refusal is not an answer, so it
#: does not wait out the rotation an answer earns.
RETRY_REFUSED = 7


def due(state, urls, today, limit, recheck_days):
    """The addresses this run opens: never checked first, then the longest unchecked, capped."""
    never = sorted(u for u in urls if u not in state)

    def cutoff(row):
        days = RETRY_REFUSED if row.get("outcome") == "refused" else recheck_days
        return (today - datetime.timedelta(days=min(days, recheck_days))).isoformat()
    stale = sorted((u for u in urls
                    if u in state and str(state[u].get("checked", "")) <= cutoff(state[u])),
                   key=lambda u: (str(state[u].get("checked", "")), u))
    picked = never + stale
    return picked if limit is None else picked[:limit]


def record(state, url, got, today, citations, text=None, final_url=None):
    """Fold one observation into the state. `got` is an outcome or `disallowed`."""
    old = state.get(url) or {}
    row = {"checked": today.isoformat(), "outcome": got}
    if got == "absent":
        row["absent_runs"] = int(old.get("absent_runs") or 0) + 1
        row["first_absent"] = old.get("first_absent") or today.isoformat()
    elif got in ("refused", "disallowed") and old.get("absent_runs"):
        # A refusal says nothing about the page, so a run of 404s it interrupts is not reset.
        row["absent_runs"] = old["absent_runs"]
        row["first_absent"] = old.get("first_absent")
    if got == "answered":
        if final_url:
            row["moved_to"] = final_url
        names = sorted({c["en"] for c in citations if c.get("en")})
        if names and is_markup(text):
            row["shows"] = {n: shows(text, n) for n in names}
    state[url] = row
    return row


def absent(state, doc, runs=2):
    """`[(kind, ja, url)]` for every citation whose address has answered 404 `runs` times in a row."""
    out = []
    for url, cites in cited(doc).items():
        if int((state.get(url) or {}).get("absent_runs") or 0) >= runs:
            out += [(c["kind"], c["ja"], url) for c in cites]
    return sorted(set(out))


def unshown(state, doc):
    """`[(kind, ja, url, en)]` for every attributed name whose answered page does not carry it."""
    out = []
    for url, cites in cited(doc).items():
        seen = (state.get(url) or {}).get("shows") or {}
        out += [(c["kind"], c["ja"], url, c["en"]) for c in cites
                if c.get("en") and seen.get(c["en"]) is False]
    return sorted(set(out))


def load(path=STATE):
    p = pathlib.Path(path)
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def save(state, path=STATE):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# Written by adapters/names/cited_pages.py; what each cited address answered.\n"
                 + yaml.safe_dump(dict(sorted(state.items())), allow_unicode=True,
                                  sort_keys=True, width=100),
                 encoding="utf-8")


def run(doc, state, today, fetch_all, robots, limit=None, recheck_days=90):
    """Open every due address through `fetch_all(urls)` and record what each answered.

    `fetch_all` returns `{url: net.Result}`; net.fetch_many keeps each host serial at its own pause
    while hosts run side by side. `robots(host)` returns the host's robots.txt body, None for no
    file, or raises net.Refused when the host would not serve one. Both are passed in so a test
    drives the whole sweep with no network.

    A HOST THAT DECLINES TO SERVE A ROBOTS.TXT HAS STATED NO RULE, so it is read as having none. The
    project owner's ruling, 2026-11-01. It opens the image CDNs that answer the file with a 403.
    Seven Seas answers the file and its pages alike with a Cloudflare 520, so its pages still come
    back refused, and that refusal is recorded against each page rather than retried around.
    """
    cites = cited(doc)
    rules, counts, wanted = {}, {}, []
    # An address no entry cites any more is no longer a question, and a 404 left standing for one
    # would count against an entry that has already moved off it.
    for url in [u for u in state if u not in cites]:
        del state[url]
        counts["dropped"] = counts.get("dropped", 0) + 1
    for url in due(state, cites, today, limit, recheck_days):
        host = urllib.parse.urlparse(url).netloc
        if host not in rules:
            try:
                rules[host] = robots(host)
            except net.Refused:
                rules[host] = None
                counts["robots.txt not served"] = counts.get("robots.txt not served", 0) + 1
        if not robots_allows(rules[host], url):
            record(state, url, "disallowed", today, cites[url])
            counts["disallowed"] = counts.get("disallowed", 0) + 1
        else:
            wanted.append(url)
    for url, result in sorted((fetch_all(wanted) if wanted else {}).items()):
        got = outcome(result)
        record(state, url, got, today, cites[url], text=result.text, final_url=result.moved)
        counts[got] = counts.get(got, 0) + 1
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--curated", default=str(CURATED))
    ap.add_argument("--state", default=str(STATE))
    ap.add_argument("--cache", required=True)
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--recheck-days", type=int, default=90)
    ap.add_argument("--retrieved", default=None, help="the run's date, YYYY-MM-DD")
    a = ap.parse_args(argv)

    today = (datetime.date.fromisoformat(a.retrieved) if a.retrieved
             else datetime.date.today())
    doc = yaml.safe_load(pathlib.Path(a.curated).read_text(encoding="utf-8")) or {}
    state = load(a.state)
    for host, seconds in PAUSES.items():
        net.set_pause(host, seconds)

    def fetch_all(urls):
        return net.fetch_many(urls, a.cache, max_age_days=1, workers=8, attempts=3)

    def robots(host):
        r = net.fetch(f"https://{host}/robots.txt", a.cache, max_age_days=7, attempts=3)
        return net.body(r)

    counts = run(doc, state, today, fetch_all, robots, limit=a.limit, recheck_days=a.recheck_days)
    save(state, a.state)
    print("cited pages: " + (", ".join(f"{n} {k}" for k, n in sorted(counts.items()))
                             or "nothing due"))
    for kind, ja, url in absent(state, doc, runs=1):
        print(f"  absent  {kind}/{ja}  {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
