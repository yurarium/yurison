#!/usr/bin/env python3
"""How a name is read, taken from the reading the publisher registered with the book.

WHY THIS EXISTS. `ndl_reading.py` was the only route to a stated author reading, and it is closed:
`ndlsearch.ndl.go.jp/robots.txt` disallows `/api`, which is where its OpenSearch lives. openBD
answers the same question from a different direction. Publishers register their books through JPRO
and 版元ドットコム, and the registration carries `PersonName: {content, collationkey}`: the name as
printed, and the kana it is filed under. That is the publisher stating how their own author is read,
which under `curate.py` is `reading_basis: stated` with `reading_source_kind: publisher-jp`.

WHAT IT IS WORTH. 251 author readings in the store were assembled by a morphological analyser,
which is guessing wearing a label: analysers are trained on running text and pen names are neither.
On the 56 this route settled, 24 disagreed with the analyser, including 東雲水生, which the analyser
read シノノメ スイセイ and the publisher files as シノノメ ミズオ. A stated reading replaces a guess
outright; it is never merged with one.

WHAT IT CANNOT REACH, WHICH IS MOST OF THE PROBLEM. openBD is keyed by ISBN and has no author
search, so it answers only for a name attached to a book we hold an ISBN for. Every web-only artist
is out of reach here exactly as they were out of reach at NDL, and for the same underlying reason:
no ISBN, no catalogue record, no stated reading anywhere. That is silence about the sources, not
about the artist, and it stays `unresolved`.

WHAT IS NOT STORED. Raw openBD payloads are never committed. REQUIREMENTS §3: the terms forbid
transferring use rights on, and a bulk field dump is the case that is unclear. The cache this
writes lives outside the repository, and what reaches data/ is one reading per name with the ISBN
it was read from.

Usage:  openbd_reading.py --cache DIR            fetch and print entries for curated.yaml
        openbd_reading.py --cache DIR --offline  re-read the cache without a request
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from names import ndl_reading  # noqa: E402

UA = "yurarium/0.1 (bibliographic database; +https://yurarium.github.io/)"
PAUSE = 1.6
# openBD takes a comma-separated list. Kept well under the limit so one bad ISBN costs one batch.
BATCH = 50

# `[作画]名前 / [原作]名前` is how MADB writes a credit. The role in brackets is cataloguing.
ROLE = re.compile(r"^\[[^\]]*\]")

# MADB also writes `[上田香子][訳]`, with the NAME in a bracket and the role in the next one, so
# stripping one leading group leaves `[訳]` standing where a person should be. A group is a role
# when it is spelt out of role words and nothing else; anything else in brackets is a name and
# keeps its content.
ROLE_ONLY = re.compile(r"^[著作画原訳編監修構成脚本案翻・\s]+$")
BRACKET = re.compile(r"\[([^\]]*)\]")


def credit_name(part):
    """One credit with its cataloguing notation removed, or '' where it was all notation.

    A doubled delimiter is still one delimiter: MADB writes `[[著]]椿木とりか` as well as `[著]`,
    and a reader that took the brackets literally found a person called `[著]椿木とりか`.
    """
    part = re.sub(r"\[+", "[", re.sub(r"\]+", "]", part))
    kept = BRACKET.sub(lambda m: "" if ROLE_ONLY.match(m.group(1)) else m.group(1), part)
    return kept.strip()


def contributors(record):
    """`(name, reading)` for everyone openBD lists on one book, dropping anyone it cannot read.

    A record with no collationkey states no reading, and the pair is the only thing worth having:
    the name alone is already on the shelf. `record` may be None, which is how openBD says it holds
    nothing for an ISBN. That is an answer, and the caller reads it as one.
    """
    detail = ((record or {}).get("onix") or {}).get("DescriptiveDetail") or {}
    out = []
    for c in detail.get("Contributor") or []:
        pn = c.get("PersonName") or {}
        name, reading = pn.get("content"), pn.get("collationkey")
        if name and reading:
            out.append((name, reading))
    return out


def records(payload, name):
    """Every book in `payload` whose registration names this person, with the reading it states.

    `payload` is `{isbn: record}` as openBD returns it. The comparison is `ndl_reading.key`, so
    `林家, 志弦` and `林家志弦` are one person and `竹嶋` is not `竹嶋えく`: a surname answering for a
    full name is how one artist's reading ends up under another artist's work.
    """
    want = ndl_reading.key(name)
    if not want:
        return []
    out = []
    for isbn, record in (payload or {}).items():
        summary = (record or {}).get("summary") or {}
        for who, raw in contributors(record):
            if ndl_reading.key(who) != want:
                continue
            reading = ndl_reading.spaced(raw)
            if not reading:
                continue
            out.append({"reading": reading, "title": summary.get("title") or "",
                        "publisher": summary.get("publisher") or "", "creator": who,
                        "isbn": isbn})
            break
    return out


def resolve(payload, name):
    """The reading the publishers state for this name, or an unresolved answer.

    THE AGREEMENT RULE IS `ndl_reading.settle`, NOT A SECOND COPY OF IT. Whether two records agree
    on a reading is one fact with one set of counter-cases, and this project's most repeated bug is
    the same fact derived twice (STANDING-INSTRUCTIONS §3). Volumes of one series carry the same
    registration, so agreement is the ordinary case here and a disagreement is worth stopping on.
    """
    return ndl_reading.settle(records(payload, name))


def query(isbns):
    """The openBD URL for a batch. One request carries a whole series, which is the point of it."""
    import urllib.parse
    return "https://api.openbd.jp/v1/get?isbn=" + urllib.parse.quote(",".join(isbns))


def madb_credits(source="data/source/madb"):
    """`{name: [isbn]}` over every MADB record on disk. No network: the ISBNs are already here."""
    import yaml
    out = {}
    for path in sorted(pathlib.Path(source).glob("*.yaml")):
        d = yaml.safe_load(path.read_text()) or {}
        isbns = [v["isbn"] for v in (d.get("volumes") or []) if v.get("isbn")]
        for part in re.split(r"\s*/\s*", d.get("creator") or ""):
            who = credit_name(part)
            if who and isbns:
                out.setdefault(who, []).extend(isbns)
    return {k: sorted(set(v)) for k, v in out.items()}


def guessed_readings(path="data/names/authors.yaml"):
    """Every name in the store whose reading an analyser assembled rather than a source stating it.

    This is the queue, and it is generated rather than typed. A hand-picked list of names to fix
    was how the first curation round skipped every work that already carried a machine answer.
    """
    import yaml
    names = (yaml.safe_load(pathlib.Path(path).read_text()) or {}).get("names") or {}
    return {n: r.get("reading") for n, r in names.items() if r.get("reading_basis") == "analyser"}


def fetch(isbns, cache, offline=False):
    """openBD records for these ISBNs, from the cache where it has them and the API where not."""
    import time
    import urllib.request

    cache = pathlib.Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    store = cache / "openbd.json"
    held = json.loads(store.read_text()) if store.exists() else {}
    missing = [i for i in isbns if i not in held]
    if offline or not missing:
        return {i: held.get(i) for i in isbns}
    for i in range(0, len(missing), BATCH):
        part = missing[i:i + BATCH]
        req = urllib.request.Request(query(part), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode("utf-8"))
        for isbn, rec in zip(part, body):
            held[isbn] = rec
        # Written per batch rather than at the end, so an interrupted run resumes (NAMES-PLAN §4).
        store.write_text(json.dumps(held, ensure_ascii=False))
        print(f"  batch {i // BATCH + 1}: asked {len(part)}, "
              f"openBD holds {sum(1 for x in body if x)}", flush=True)
        time.sleep(PAUSE)
    return {i: held.get(i) for i in isbns}


def healthy(payload):
    """Whether a payload is worth reading, as `(ok, held, asked)`.

    THE FLOOR IS THERE BECAUSE SILENCE HAS TWO CAUSES. openBD answers with a null per ISBN it does
    not hold, so a host in trouble and a shelf of books nobody registered arrive in exactly the same
    shape: every record null, no exception raised, nought settled, reported as a clean run. A pass
    that cannot tell those apart publishes the first as if it were the second.

    Some nulls are ordinary: 31 of the 143 ISBNs in the first run are books openBD has dropped or
    never carried, and that is the inventory being an inventory. All of them is not.

    A SHARE RATHER THAN "AT LEAST ONE", because the failure to catch is a TRUNCATED answer and not
    only an empty one. The first version refused a payload that was null all the way down, which a
    batch loop that died after one batch of fifty clears easily: it comes back with a handful of
    records, settles a handful of names, and the run reads as a thin day rather than as a fetch
    that stopped. The measured share is 78% held, so half is clear of a healthy run by a wide
    margin and well above anything a stopped loop returns.

    The counter-case, so the floor is not lowered later without thinking: a run whose ISBNs are
    mostly pre-registration books would legitimately fall under half. That is a real answer about
    an old shelf, and the response to it is to look at which ISBNs went unheld, not to move the
    floor down until the run passes.
    """
    asked = len(payload or {})
    held = sum(1 for v in (payload or {}).values() if v)
    return (asked == 0 or held * 2 >= asked), held, asked


def entries(payload, wanted, reviewed):
    """Curated author entries for the names this payload settles, and why each one is a change.

    Returns `(entries, unresolved)`. An entry is only proposed where the reading is katakana and
    differs from nothing the store already states, because this replaces a guess and must not
    quietly restate one.
    """
    out, unresolved = {}, {}
    for name, guess in sorted(wanted.items()):
        reading, ev = resolve(payload, name)
        if not reading:
            unresolved[name] = ev["status"]
            continue
        if not ndl_reading.is_kana(reading):
            unresolved[name] = "not-katakana"
            continue
        first = ev["examples"][0]
        note = (f"openBD carries this reading as the publisher's own collationkey on "
                f"{ev['records']} volume(s), e.g. {first[0]!r} ({first[1]}).")
        if (guess or "").replace(" ", "") != reading.replace(" ", ""):
            note += f" It replaces {guess!r}, which an analyser assembled."
        out[name] = {"reading": reading, "reading_basis": "stated",
                     "reading_source_kind": "publisher-jp", "reading_note": note,
                     "source": "openBD", "source_url": query([records(payload, name)[0]["isbn"]]),
                     "source_kind": "publisher-jp", "reviewed": reviewed}
    return out, unresolved


def main(argv=None):
    import argparse
    import datetime

    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", required=True, help="where raw openBD payloads go; not the repo")
    ap.add_argument("--offline", action="store_true", help="use only what the cache holds")
    ap.add_argument("--reviewed", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)

    guesses = guessed_readings()
    credits = madb_credits()
    wanted = {n: g for n, g in guesses.items() if n in credits}
    isbns = sorted({i for n in wanted for i in credits[n]})
    print(f"{len(guesses)} guessed readings, {len(wanted)} of them on a book we hold an ISBN for; "
          f"{len(isbns)} ISBN(s) to ask about")

    payload = fetch(isbns, a.cache, a.offline)
    ok, held, asked = healthy(payload)
    print(f"HEALTH: openBD holds {held} of {asked} ISBN(s) asked about")
    if not ok:
        print(f"Refusing to write: openBD answered for {held} of {asked} ISBN(s), under the half "
              "a healthy run clears. That is the host in trouble or a fetch that stopped partway, "
              "rather than a shelf of unregistered books, and the three look identical from here.")
        return 1
    found, unresolved = entries(payload, wanted, a.reviewed)
    print(f"{len(found)} settled, {len(unresolved)} not: "
          f"{sorted(set(unresolved.values()))}")
    print(yaml.safe_dump({"authors": found}, allow_unicode=True, sort_keys=True, width=100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
