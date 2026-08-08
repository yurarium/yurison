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

ONE CLIENT, ONE CACHE, AND WHY THE SECOND ONE COST 978 VOLUMES. `fetch()` here is the only thing in
this project that asks openBD anything, and `openbd/enrich.py` and `cmoa_volumes.py` both call it.
That much was already true. What was not is where the answer landed: the cache directory came in as
an argument with no default, so the same question was asked into `names-cache/openbd.json` and
`openbd-cache/openbd.json`, the two files drifted to 2,425 and 2,401 ISBNs, and the enrichment pass
read the thinner one and left 978 volumes unanswered for no reason except which file was opened.
A default fixes what a convention did not: `CACHE` is the one location, `--cache` moves it for a
caller who means to, and the three callers cannot diverge by forgetting.

Usage:  openbd_reading.py                        fetch and print entries for curated.yaml
        openbd_reading.py --offline              re-read the cache without a request
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import net  # noqa: E402
import paths  # noqa: E402
from names import ndl_reading  # noqa: E402

HOST = "api.openbd.jp"
PAUSE = 1.6
# openBD takes a comma-separated list. Kept well under the limit so one bad ISBN costs one batch.
BATCH = 50

# THE one place openBD's answers are kept. See ONE CLIENT, ONE CACHE above.
CACHE = paths.cache("openbd-cache")
STORE_NAME = "openbd.json"

# HOW LONG "openBD HOLDS NOTHING FOR THIS ISBN" IS WORTH BELIEVING.
#
# A null here is a real answer and it is worth keeping: 245 of the corpus's ISBNs are books nobody
# registered, and each one costs a request to re-establish. It is not permanent, though. openBD
# carries a publisher's JPRO registration, and a book missing today is one a publisher has not
# filed YET, so an absence that never expires would hold a title out of the enrichment pass for
# ever on the strength of one lookup.
#
# Three months, and it can be short because asking is cheap here in a way it is not at NDL: 50
# ISBNs travel in one request, so re-asking every null the corpus holds costs five requests and
# about ten seconds. The expiry is set by how fast a registration appears, and not by what asking
# costs.
NEGATIVE_DAYS = 90

# `[作画]名前 / [原作]名前` is how MADB writes a credit. The role in brackets is cataloguing.
ROLE = re.compile(r"^\[[^\]]*\]")

# MADB also writes `[上田香子][訳]`, with the NAME in a bracket and the role in the next one, so
# stripping one leading group leaves `[訳]` standing where a person should be. A group is a role
# when it is spelt out of role words and nothing else; anything else in brackets is a name and
# keeps its content.
# The role words that actually appear, not every word that could be one. 漫 企 and 者 were
# missing, so 漫画, 企画 and 著者 were read as names. A katakana role is spelled out because
# admitting katakana to the class would strip a katakana name in brackets, which is not a role.
ROLE_ONLY = re.compile(r"^(?:[著作画原訳編監修構成脚本案翻者漫企・\s]+"
                       r"|キャラクター原案|カバーイラスト|イラスト|カバー|デザイン)$")
BRACKET = re.compile(r"\[([^\]]*)\]")

# A ROLE WRITTEN IN ROUND BRACKETS AFTER THE NAME. openBD and the platforms write `苗川采(著者)`
# and `Ｍａｇｐｉｅ（翻訳）` where MADB writes `[著]苗川采`, and only the square form was being
# removed. 138 credits carried one, 96 of them 著者, and each left the name unmatched in the store
# so the row rendered as Japanese on an English page.
#
# ANCHORED AT THE END AND LENGTH-LIMITED, because a bracket in the middle of a name is part of the
# name: `sono.N（SHUEISHA）` is not a role and `LYCORIS(企画)` is. Only a trailing bracket whose
# whole content is role words comes off.
TRAILING_ROLE = re.compile(r"[（(]\s*([^）)]{1,10})\s*[）)]\s*$")


def credit_name(part):
    """One credit with its cataloguing notation removed, or '' where it was all notation.

    A doubled delimiter is still one delimiter: MADB writes `[[著]]椿木とりか` as well as `[著]`,
    and a reader that took the brackets literally found a person called `[著]椿木とりか`.
    """
    part = re.sub(r"\[+", "[", re.sub(r"\]+", "]", part))
    kept = BRACKET.sub(lambda m: "" if ROLE_ONLY.match(m.group(1)) else m.group(1), part)
    kept = TRAILING_ROLE.sub(lambda m: "" if ROLE_ONLY.match(m.group(1)) else m.group(0), kept)
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


ISBN = re.compile(r"[0-9]{9}[0-9X]|[0-9]{13}")


def isbns_in(node, out=None):
    """Every ISBN one loaded record states, wherever in the record its shape puts them.

    Kept separate from the directory walk so the collecting can be tested without a tree of files,
    and so a new record shape can be checked against it by writing the shape down.
    """
    out = set() if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "isbn" and isinstance(v, str):
                out.add(v.strip())
            elif k == "isbns" and isinstance(v, list):
                out.update(x.strip() for x in v if isinstance(x, str))
            else:
                isbns_in(v, out)
    elif isinstance(node, list):
        for v in node:
            isbns_in(v, out)
    # Six books from 2006 keep a ten-digit ISBN, so the length is not the test; the shape is.
    return sorted(i for i in out if ISBN.fullmatch(i))


def corpus_isbns(source="data/source"):
    """Every ISBN the corpus states. This is the population openBD can be asked about.

    WHY NOT `madb_credits`, WHICH ALREADY HANDS BACK ISBNS. That answers a narrower question, and
    the narrowing loses two whole shapes. A shop states an ISBN for a work MADB does not carry, and
    51 of those sit in data/source/comparators/shop-final-volumes.yaml. And a credit MADB spells
    differently from the store, or leaves off a volume altogether, hides a person who is on a book
    we hold: 49 MADB records carry ISBNs and no creator at all. openBD's answer carries the
    contributor's own name beside the reading, so asking about an ISBN settles whoever the
    publisher registered on it, whether or not we knew they were there. Keying the request on our
    own credits asks openBD only about people we could already name.

    THE WALK IS OVER ANY `isbn` OR `isbns` KEY, rather than over the shapes on disk today. A source
    arriving with its ISBNs one level deeper would otherwise be collected as nothing, settle no
    names, and report a clean run, which is the silence STANDING-INSTRUCTIONS §4 is about.
    """
    import yaml
    out = set()
    for path in sorted(pathlib.Path(source).rglob("*.yaml")):
        isbns_in(yaml.safe_load(path.read_text()) or {}, out)
    return sorted(i for i in out if ISBN.fullmatch(i))


def unsettled_readings(path="data/names/authors.yaml"):
    """Every name in the store that no source has stated a reading for, against what it shows now.

    This is the queue, and it is generated rather than typed. A hand-picked list of names to fix
    was how the first curation round skipped every work that already carried a machine answer.

    THE TEST IS "NOTHING STATED IT", NOT "AN ANALYSER SAID SO". Selecting on
    `reading_basis == 'analyser'` reads the answer already in the field and so skips every name
    with no answer at all: 高良真生 carries a refutation and no reading, five names carry a reading
    back-converted out of a community database, and on the old filter all six counted as settled
    and were never asked about. `curate.todo` records the same mistake made the other way round on
    the title side, where "has no `en`" excluded every work already showing a romanisation.

    A LATIN-SCRIPT PEN NAME WITH NOTHING RECORDED IS OUT, deliberately.
    `bookwalker_shelf.reading_route` files those as `latin` and says there is no kana reading to
    state, and putting one there is this project deciding how a name written to be read as it
    stands is pronounced. One that already carries a reading is IN, because that reading came from
    somewhere: U-temo holds ウ テモ back-converted out of MangaUpdates, which curate.py refuses as
    evidence, and the publisher registering the book files it ユウテモ.
    """
    import yaml
    names = (yaml.safe_load(pathlib.Path(path).read_text()) or {}).get("names") or {}
    return {n: r.get("reading") for n, r in names.items() if unsettled(r)}


# What counts as settled: a source stated it, or the name is kana and is its own reading. Anything
# else is a machine's answer or no answer, and both are worth asking a publisher about.
SETTLED = ("stated", "surface", "researched")


def unsettled(record):
    """Whether one store record still wants a reading. The rule `unsettled_readings` selects on.

    A KANA NAME IS SETTLED HERE AND UNSETTLED IN `boundary_queue`, and the two are different
    questions about one record. なもり is its own reading and no publisher can improve on it, which
    is why `surface` counts as settled. Where the name divides is not in the surface at all, so
    treating the record as finished left 337 kana names romanising as one word. See
    `adapters/names/boundary.py`.
    """
    if record.get("script") == "latin" and not record.get("reading"):
        return False
    return record.get("reading_basis") not in SETTLED


def boundary_queue(path="data/names/authors.yaml"):
    """`{name: its undivided reading}` for every kana name whose division nothing has stated.

    Generated for the same reason `unsettled_readings` is: a hand-picked list of names skips
    whatever already carries an answer, and here every one of them does.
    """
    import yaml

    from names import boundary
    names = (yaml.safe_load(pathlib.Path(path).read_text()) or {}).get("names") or {}
    return {n: r.get("reading") for n, r in names.items() if boundary.wants_boundary(n, r)}


def boundary_entries(payload, wanted, reviewed):
    """Curated entries carrying openBD's division onto our own kana. `(entries, unresolved)`.

    WHY THIS IS NOT `entries` WITH A FLAG. `entries` proposes openBD's STRING, and for a kana name
    that string is the wrong thing to publish: a collation key folds づ to ず, so taking it whole
    republishes the artist's name with a different kana in it. `normalised` already refuses that and
    files the name as `filing-key-normalised`, which threw away the one thing the key could still
    add. `boundary.carry` keeps the surface's kana and takes only the offsets.

    THE ENTRY SAYS `surface`, BECAUSE THAT IS WHAT THE KANA ARE. The division is openBD's and the
    note says so; the sounds are the artist's own spelling and no source is being credited with
    them. Claiming `stated` here would put a publisher's name on kana it did not supply.
    """
    from names import boundary
    out, unresolved = {}, {}
    for name, current in sorted(wanted.items()):
        reading, ev = resolve(payload, name)
        if not reading:
            unresolved[name] = ev["status"]
            continue
        got = boundary.carry(name, reading)
        if not got:
            unresolved[name] = ("no-boundary-stated" if not boundary.cuts(reading)
                                else "does-not-correspond")
            continue
        first = ev["examples"][0]
        note = (f"openBD's collationkey on {ev['records']} volume(s), e.g. {first[0]!r} "
                f"({first[1]}), divides this name as {reading!r}. The kana here are the name's own "
                f"surface and only the division is taken, since a collationkey is a filing key "
                f"first: it folds the kana that sort together. It divides {current!r}.")
        out[name] = {"reading": got, "reading_basis": "surface",
                     "reading_source_kind": "derived", "reading_note": note,
                     "source": "openBD", "source_url": query([records(payload, name)[0]["isbn"]]),
                     "source_kind": "publisher-jp", "reviewed": reviewed}
    return out, unresolved


def store_path(cache=None):
    """The one file openBD's answers live in. `cache` may name the file itself or its directory."""
    p = pathlib.Path(cache or CACHE)
    return p if p.name == STORE_NAME else p / STORE_NAME


def load(cache=None):
    """`(records, asked)`: what openBD said per ISBN, and the date each ISBN was asked about.

    THE DATE IS WHY THE SHAPE CHANGED. The file used to be `{isbn: record or null}`, and a null in
    it is the most valuable thing there: it is a request already paid for whose answer was
    "nobody registered this book". With no date beside it that answer is permanent, and a book the
    publisher files next spring stays out of every enrichment run for ever.

    A FILE IN THE OLD SHAPE IS READ, not rebuilt. 2,400 answers sit in one on this machine and
    throwing them away to gain a date would cost 48 requests to learn what is already known. Their
    nulls carry no date, so they read as expired and are asked once more, which is five requests
    and stamps them.
    """
    p = store_path(cache)
    if not p.exists():
        return {}, {}
    doc = json.loads(p.read_text())
    if isinstance(doc.get("records"), dict):
        return doc["records"], doc.get("asked") or {}
    return doc, {}


def save(records, asked, cache=None):
    p = store_path(cache)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"records": records, "asked": asked}, ensure_ascii=False))


def worth_asking(isbns, records, asked, recheck_after=NEGATIVE_DAYS):
    """The ISBNs still worth a request, and the ones a recorded absence answers for.

    An ISBN openBD HELD is never asked again: a registration does not change in a way this project
    reads. An ISBN it did not hold is asked again once the absence is old enough, because that is
    the answer that can turn into a record.
    """
    from names import store as store_mod                                    # noqa: PLC0415
    ask, known = [], []
    for i in isbns:
        if records.get(i):
            continue
        when = asked.get(i)
        if i in records and when and store_mod.days_since(when) < recheck_after:
            known.append(i)
        else:
            ask.append(i)
    return ask, known


def fetch(isbns, cache=None, offline=False, recheck_after=NEGATIVE_DAYS):
    """openBD records for these ISBNs, from the store where it has them and the API where not.

    A REFUSAL ABORTS AND WRITES NOTHING. openBD answers with a null per ISBN it does not hold, so a
    host in trouble and a shelf of unregistered books arrive in the same shape once the refusal has
    been flattened into "no body". `net.body` raises instead of flattening it, and the raise is
    load-bearing: recording a refused batch as fifty nulls would put fifty books beyond every
    future run for as long as the absence stands.
    """
    records, asked = load(cache)
    missing, known = worth_asking(isbns, records, asked, recheck_after)
    print(f"  {len(known)} ISBN(s) skipped: openBD said it holds nothing for them within "
          f"{recheck_after} days", flush=True)
    if offline or not missing:
        return {i: records.get(i) for i in isbns}

    net.set_pause(HOST, PAUSE)
    stamp = _today()
    for i in range(0, len(missing), BATCH):
        part = missing[i:i + BATCH]
        page = net.body(net.fetch(query(part), None))
        if page is None:
            # The batch endpoint answering 404 is a statement about the endpoint. It says nothing
            # about any book, and must not be written down as though it had.
            raise net.Refused(f"openBD answered nothing for a batch of {len(part)}")
        body = json.loads(page)
        if not isinstance(body, list) or len(body) != len(part):
            # zip() would silently pair the first n and leave the rest looking unasked, which is
            # the truncated answer `healthy()` was written against, arriving one layer lower.
            raise net.Refused(f"openBD returned {len(body)} answers to {len(part)} ISBNs")
        for isbn, rec in zip(part, body):
            records[isbn] = rec
            asked[isbn] = stamp
        # Written per batch rather than at the end, so an interrupted run resumes (NAMES-PLAN §4).
        save(records, asked, cache)
        print(f"  batch {i // BATCH + 1}: asked {len(part)}, "
              f"openBD holds {sum(1 for x in body if x)}", flush=True)
    return {i: records.get(i) for i in isbns}


def _today():
    import datetime
    return datetime.date.today().isoformat()


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


def normalised(name, reading):
    """Whether a stated reading has lost kana the name itself carries.

    A COLLATIONKEY IS A FILING KEY BEFORE IT IS A READING, and JPRO normalises the kana that sort
    together. とりい しづく is filed トリイ, シズク; トクヲツム is filed トクオツム; いづみやおとは
    is filed イズミヤ, オトハ. Against a kanji name that costs nothing anyone can see, and the key
    is still the only statement of how the name is said. Against a KANA name it is a loss, because
    there the surface is the reading and no lookup was needed: taking the key over it republishes
    the artist's name with a different kana in it.

    The pair that shows it: the store holds とりいしづく at トリイシヅク off its own surface, and
    would have taken トリイ シズク off openBD for とりい しづく. One artist, two spellings, two
    readings, and nothing in either record to say they are the same person.

    What the key may still add to a kana name is the boundary between the elements, which the
    surface does not carry: ささだあすか is ササダ アスカ. So agreement on the kana is the test, not
    agreement on the string.
    """
    from names import kana as kana_mod  # noqa: PLC0415
    if not kana_mod.kana_only(name):
        return False
    strip = str.maketrans("", "", " 　・")
    return (kana_mod.to_katakana(name).translate(strip)
            != (reading or "").translate(strip))


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
        if normalised(name, reading):
            unresolved[name] = "filing-key-normalised"
            continue
        first = ev["examples"][0]
        note = (f"openBD carries this reading as the publisher's own collationkey on "
                f"{ev['records']} volume(s), e.g. {first[0]!r} ({first[1]}).")
        if (guess or "").replace(" ", "") != reading.replace(" ", ""):
            # NOT "which an analyser assembled". The queue holds readings from more than one
            # machine now: five were back-converted out of MangaUpdates, which curate.py refuses
            # as evidence, and naming the wrong producer in the record is worse than naming none.
            note += f" It replaces {guess!r}, which no source had stated."
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
    ap.add_argument("--cache", default=str(CACHE),
                    help="where raw openBD payloads go; not the repo, and one place for all three "
                         "callers unless you mean otherwise")
    ap.add_argument("--offline", action="store_true", help="use only what the cache holds")
    ap.add_argument("--reviewed", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)

    wanted = unsettled_readings()
    isbns = corpus_isbns()
    print(f"{len(wanted)} name(s) with no stated reading; asking openBD about {len(isbns)} "
          f"ISBN(s) the corpus states")

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

    # THE SECOND QUESTION, asked of the same payload because it costs no request. A kana name is
    # settled as a READING and open as a DIVISION, and asking only the first left 337 author names
    # romanising as one word.
    # A name openBD has just stated a whole reading for is not asked for a division as well: that
    # entry already carries one, and a second entry under the same key would overwrite it with the
    # weaker claim.
    divide = {k: v for k, v in boundary_queue().items() if k not in found}
    cut, uncut = boundary_entries(payload, divide, a.reviewed)
    print(f"{len(divide)} name(s) written in one run; {len(cut)} divided, {len(uncut)} not: "
          f"{sorted(set(uncut.values()))}")
    found.update(cut)
    print(yaml.safe_dump({"authors": found}, allow_unicode=True, sort_keys=True, width=100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
