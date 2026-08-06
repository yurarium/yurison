#!/usr/bin/env python3
"""How a name is read, taken from the national media-arts catalogue's own transcription of it.

WHY THIS EXISTS, AND WHY IT IS EMBARRASSING. Every other route to a stated author reading is shut.
`ndl_reading.py` is closed because `ndlsearch.ndl.go.jp/robots.txt` disallows `/api`, where its
OpenSearch lives. `openbd_reading.py` is keyed by ISBN and has now been asked about every ISBN the
corpus states, settling everything it can. That left 609 names carrying a morphological analyser's
guess or nothing at all, and the plan for them was one web search per artist.

The answer was already on disk. MADB writes a creator as a two-element list, the credit followed
by `{"@value": "ホシノナツミ", "@language": "ja-hrkt"}`, and `madb/extract.py` has had a `reading()`
function that reads exactly that field since the first commit. It is used for titles and publishers
and never for people, and `extract.people()` throws the creator's away in one line: "A trailing
all-katakana part is the reading of the name before it, not a second person." NAMES-PLAN §2 said
in as many words that MADB and openBD carry kana readings and we are throwing them away, and no
pass acted on it. 19,145 usable pairs sit in one release file.

WHAT IT COSTS: no requests at all. The pinned release is already in the cache that `extract.py`
reads, and a run over it is a re-parse of data we hold.

WHAT IT IS WORTH. A national cataloguing authority stating how a name is said, which under
`curate.py` is `reading_basis: stated` with `reading_source_kind: national-library`, the same
standing NDL's `dcndl:creatorTranscription` has, from the other national catalogue. And it reaches
pen names no analyser could: 九羊ボン is filed クラムボン and 千葉侑生 is filed チバユウ.

ONE PERSON PER RECORD, AND THAT IS THE WHOLE OF THE SAFETY. A record crediting two people is
refused outright, in either of the two shapes MADB writes one.

  RUN TOGETHER IN ONE STRING. `畠山耕太郎 /松田康志` is filed `ハタヤマコウタロウマツダヤスシ`,
  one reading with no boundary in it. Nothing but a guess can split that.

  AS SEPARATE LIST ELEMENTS, AND THIS ONE IS WORSE, because it looks readable and is not. MADB
  writes `["城之内寧々", "川奈あめ", {"@value": "カワナアメ"}, {"@value": "ジョウノウチネネ"}]`:
  every name, then every reading, AND THE TWO LISTS ARE NOT IN THE SAME ORDER. The readings are
  sorted and the names are not, so taking the first of each pairs 城之内寧々 with 川奈あめ's
  reading. A first version of this module did exactly that and `ndl_reading.settle` caught it on
  four names only because their other records disagreed; a person credited only ever beside
  somebody else would have been misnamed silently.

Attaching one artist's reading to another artist's name is the worst outcome available here:
`古川楊也` was once published under a different artist's name and it took a refutation to undo. So
`schema:creator` yields a pair only when it holds exactly one name and exactly one reading, which
costs 3% of the pairs on release 1.2.18 and removes both ways this pass could misname somebody.

WHAT THE READING DOES NOT CARRY. A boundary between family and given name. NDL writes `タケシマ,
エク` and openBD writes a `collationkey` with a comma; MADB writes `ホシノナツミ` closed up, and
528 store records already hold an unspaced reading for the same reason. The reading is stored as
the catalogue states it. Putting the space back where an analyser thinks a word ends would publish
a guessed boundary under a national catalogue's name, which is exactly the dressing-up this pass
exists to undo.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from madb import extract                                                      # noqa: E402
from names import ndl_reading                                                 # noqa: E402

# The release files that carry a creator with a reading beside it. 105 and 109 carry none, and a
# file is named here rather than globbed so that a release dropping one fails visibly instead of
# quietly settling fewer names.
FILES = ("metadata101.json", "metadata104.json", "metadata106.json", "metadata108.json")

# More than one person in one credit. MADB separates credits with a slash and nothing else, and
# `[著]畠山耕太郎 /松田康志` shows it also writes the slash without a space.
SEVERAL = re.compile(r"/")


def credit_reading(rec):
    """`(name, reading)` for a record crediting exactly one person, else None.

    THE COUNT IS THE TEST, not the content. `extract.primary` returns the first string and
    `extract.reading` the first ja-hrkt value, and on a two-person record those two are not each
    other's; see the module docstring. So the field is required to hold one of each before either
    is read at all.

    The role marker comes off the name with the same function `madb/extract.py` uses on it, so a
    change to what a role looks like reaches both readers of MADB credits at once.
    """
    field = rec.get("schema:creator", "")
    if not isinstance(field, list):
        return None                             # a bare string states a credit and no reading
    plain = [x for x in field if isinstance(x, str)]
    kanas = [x for x in field
             if isinstance(x, dict) and x.get("@language") == "ja-hrkt" and x.get("@value")]
    if len(plain) != 1 or len(kanas) != 1:
        return None
    raw, kana = plain[0], str(kanas[0]["@value"])
    if SEVERAL.search(raw):
        return None                             # one element, two people, one unsplittable reading
    name = extract.strip_role(raw)
    reading = ndl_reading.spaced(kana)
    return (name, reading) if name and reading else None


def index(graph):
    """`{comparison key: [record]}` over one release file, in the shape `ndl_reading.settle` wants.

    Keyed on `ndl_reading.key`, which is what makes 林家志弦 and `林家, 志弦` one person and keeps
    竹嶋 from answering for 竹嶋えく.
    """
    out = {}
    for rec in graph:
        pair = credit_reading(rec)
        if not pair:
            continue
        name, reading = pair
        out.setdefault(ndl_reading.key(name), []).append({
            "reading": reading, "creator": name,
            "title": extract.primary(rec.get("schema:name", "")),
            "publisher": extract.split_reading(extract.primary(rec.get("schema:publisher", ""))),
            "madb_id": rec.get("schema:identifier", ""),
        })
    return out


def merge(a, b):
    """Two file indexes as one. A release is several files and a person is in more than one."""
    for k, v in b.items():
        a.setdefault(k, []).extend(v)
    return a


def resolve(idx, name):
    """The reading MADB states for this name, or an unresolved answer.

    THE AGREEMENT RULE IS `ndl_reading.settle` AND NOT A SECOND COPY OF IT, for the reason that
    function's own docstring gives: whether two records agree on a reading is one fact with one set
    of counter-cases, and this project's most repeated bug is the same fact derived twice.
    """
    return ndl_reading.settle(idx.get(ndl_reading.key(name)) or [])


def entries(idx, wanted, reviewed):
    """Curated author entries for the names this index settles. `(entries, unresolved)`."""
    out, unresolved = {}, {}
    for name, guess in sorted(wanted.items()):
        reading, ev = resolve(idx, name)
        if not reading:
            unresolved[name] = ev["status"]
            continue
        if not ndl_reading.is_kana(reading):
            unresolved[name] = "not-katakana"
            continue
        # THE SAME REFUSAL openbd_reading MAKES, and for the same artist. A kana name is its own
        # reading, and a catalogue's filing key normalises kana that sort together: とりいしづく
        # is filed トリイシズク. Taking the key over the surface republishes the artist's name with
        # a different kana in it.
        from names.openbd_reading import normalised                    # noqa: PLC0415
        if normalised(name, reading):
            unresolved[name] = "filing-key-normalised"
            continue
        title, publisher = ev["examples"][0]
        # A series node carries no publisher, so the bracket is written only where there is
        # something in it. `'きみはがんばれの魔法' ()` reads as a missing field rather than as a
        # record that never had one.
        where = f"{title!r}" + (f" ({publisher})" if publisher else "")
        note = (f"MADB records this reading beside the credit on {ev['records']} record(s) of the "
                f"pinned release, e.g. {where}.")
        if (guess or "").replace(" ", "") != reading.replace(" ", ""):
            note += f" It replaces {guess!r}, which no source had stated."
        else:
            note += " It agrees with the reading already held, which no source had stated."
        out[name] = {"reading": reading, "reading_basis": "stated",
                     "reading_source_kind": "national-library", "reading_note": note,
                     "source": "MADB", "source_kind": "national-library",
                     "source_url": "https://mediaarts-db.artmuseums.go.jp/id/"
                                   + str(idx[ndl_reading.key(name)][0]["madb_id"]),
                     "reviewed": reviewed}
    return out, unresolved


def healthy(idx):
    """Whether an index is worth reading, as `(ok, pairs)`.

    A MISSING RELEASE FILE AND A CATALOGUE WITH NO READINGS LOOK THE SAME FROM HERE: both give an
    empty index, settle nothing and report a clean run. The measured count on release 1.2.18 is
    over forty thousand names, so a floor well under it catches a file that failed to load without
    tripping on a release that reorganised.
    """
    return len(idx) >= 5000, len(idx)


def main(argv=None):
    import argparse
    import datetime
    import json

    import yaml

    from names.openbd_reading import unsettled_readings                # noqa: PLC0415

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", required=True, help="the pinned MADB release directory")
    ap.add_argument("--index", default=None,
                    help="where the name index is kept; outside the repo, and reused")
    ap.add_argument("--rebuild", action="store_true", help="re-read the release files")
    ap.add_argument("--reviewed", default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)

    # THE INDEX IS CACHED because the release is 1.3 GB of JSON and re-reading it to answer a
    # second question is minutes of nothing. NAMES-PLAN §4: every pass is resumable and re-parsing
    # after a fix costs nothing.
    store = pathlib.Path(a.index) if a.index else pathlib.Path(a.cache) / "creator-readings.json"
    if store.exists() and not a.rebuild:
        idx = json.loads(store.read_text())
        print(f"index: {len(idx)} name(s), from {store}")
    else:
        idx = {}
        for name in FILES:
            got = index(extract.load(a.cache, name))
            print(f"  {name}: {len(got)} name(s) with a stated reading", flush=True)
            merge(idx, got)
        store.write_text(json.dumps(idx, ensure_ascii=False))
        print(f"index: {len(idx)} name(s), written to {store}")

    ok, pairs = healthy(idx)
    if not ok:
        print(f"Refusing to write: the index holds {pairs} name(s), under the floor a healthy "
              "release clears. That is a file that failed to load rather than a catalogue with no "
              "readings in it, and the two look identical from here.")
        return 1

    wanted = unsettled_readings()
    found, unresolved = entries(idx, wanted, a.reviewed)
    print(f"{len(wanted)} name(s) with no stated reading; {len(found)} settled, "
          f"{len(unresolved)} not: {sorted(set(unresolved.values()))}")
    print(yaml.safe_dump({"authors": found}, allow_unicode=True, sort_keys=True, width=100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
