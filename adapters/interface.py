#!/usr/bin/env python3
"""Ask the interface what it would show, instead of asserting what it should.

WHAT THIS REPLACES. `check.py` held hand transcriptions of `kari/app.js`: a `fold`, a `render`
reimplementing the name lookup, a `joins` guessing at the order app.js falls back in, and copies of
`publisherOf` and `imprintOf`. STANDING-INSTRUCTIONS §3 says the same fact derived in two places
drifts with nothing forcing agreement, and each of those was a second derivation.

It drifted where it costs the most. `English mode has no Japanese` was extended to walk the volume
rows, went green, and a reader could still see
`シャドウ・アサシンズ・ワールド : 影は薄いけど、最強忍者やってます` on the 発売 tab. The
transcription tried the title with its subtitle stripped and with the separator turned into a
space; app.js tries neither. The check passed because its model of the renderer was kinder than the
renderer.

So this runs the renderer. `interface.js` evaluates `kari/app.js` as GitHub Pages serves it, in a
node vm with a stubbed browser around it, and calls the file's own functions. Nothing here spells a
rule that app.js already spells.

WHAT IT COSTS. One node process, which loads app.js in about 90 ms and renders the whole corpus of
2,558 work titles in about 30 ms. A gate run pays roughly 0.6 s in total, most of it parsing
`feed/names.json`, which node reads by path rather than being handed on stdin for that reason.
Nothing browser-shaped runs: no jsdom, no headless Chrome, no page.

WHAT IT CANNOT SEE, and this is the reason `adapters/lint/entrypoints.py` exists beside it. Running
the renderer proves that what reaches the renderer is rendered correctly. It says nothing about a
call site that never calls it, and every leak this project has had was one of those: the works list
wrote `esc(w.t)` from index.json and shipped 2,430 rows of Japanese, and the 発売 tab labelled a
volume from a catalogued record title. `entrypoints.py` is the static half, and it is the half that
can fail on a path no run exercises.

Offline: node is given a request on stdin and reads two files by path. Its own fetch entries are
removed before app.js is evaluated, because ./test.py installs its guard in Python and a node
grandchild is outside it.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS = pathlib.Path(__file__).resolve().parent / "interface.js"
SITE_ROOT = pathlib.Path(os.environ.get("YURARIUM_SITE") or ROOT.parent / "yurarium.github.io")
APP_JS = SITE_ROOT / "kari" / "app.js"


# ── which field goes through which function ───────────────────────────────────────────────────
#
# THE ONE TABLE, READ TWICE. `check.py` renders each field here through the function named beside
# it and asks what a reader would see. `adapters/lint/entrypoints.py` reads the same table and
# proves that kari/app.js never puts one of these fields on a page any other way. Neither half is
# worth much alone: rendering proves that what reaches the renderer is right, and the lint proves
# that everything reaches it.
#
# `arg` says how a caller builds the argument, because an entry point takes either a ROW or a
# STRING. `workLabel` reads `r.work` and `r.work_en` off a row, so a surface whose title lives
# somewhere else on the row hands the row over with `work` set to that field, which is what
# renderReleases does with `workLabel({ work: w.title.ja })`. That much is a model of the caller,
# and it is the part the lint checks rather than assumes.
KANA_KANJI = re.compile(r"[぀-ヿ㐀-鿿豈-﫿]")
JAPANESE_ANY = re.compile(r"[぀-ヿ㐀-鿿豈-﫿　-〿＀-￯]")


class Surface:
    """One field of one built collection, and the interface function that renders it.

    `arg` is how the caller builds the argument, because the entry points take three shapes.
    `value` hands over the string. `row:<field>` hands over the row with `<field>` set to this
    value, which is what `workLabel({ work: w.title.ja })` does on the 発売 tab. `record` hands
    over the whole record, which is what the publisher parts take, and `fields` then says which of
    its fields this surface accounts for.

    `holds_at_zero` says whether a Japanese rendering here is a fault or a deficit. A work title
    that stays Japanese in English mode is a fault and blocks. An imprint whose line has no English
    name yet is a coverage deficit with a budget already counting it, and blocking on it would
    stop every commit until somebody had romanised 44 publishing lines.
    """

    def __init__(self, path, entry, arg, category, why, holds_at_zero=True, fields=()):
        # `entry` may name more than one function where the interface legitimately has more than
        # one: the publisher parts exist as a plain-string form and an escaped form carrying each
        # name's mark, and both are entry points for the same three fields. The first is the one
        # this renders through; the lint accepts any of them.
        self.path, self.entry = path, (entry,) if isinstance(entry, str) else tuple(entry)
        self.arg = arg
        self.category, self.why, self.holds_at_zero = category, why, holds_at_zero
        self.fields = tuple(fields)

    @property
    def renders_with(self):
        return self.entry[0]

    @property
    def accessor(self):
        """What the JavaScript reads: `works[].title.ja` is `title.ja` to app.js."""
        return self.path.split("[].", 1)[1] if "[]." in self.path else self.path

    @property
    def ruled_paths(self):
        """Every derived path this surface accounts for."""
        if not self.fields:
            return (self.path,)
        stem = self.path[:-2] if self.path.endswith("[]") else self.path
        return tuple(f"{stem}[].{f}" if self.path.endswith("[]") else f"{stem}.{f}"
                     for f in self.fields)

    @property
    def accessors(self):
        """What app.js reads for this surface, one accessor per field it accounts for."""
        return tuple(p.split("[].", 1)[1] if "[]." in p else p for p in self.ruled_paths)


SURFACES = [
    Surface("index[].t", ("workLabel", "workTextOf"), "row:work", "title",
            "the catalogue tab's title, drawn from the compact index"),
    Surface("index[].c", "credit", "value", "person",
            "the catalogue tab's credit line, roles and people in one string",
            holds_at_zero=False),
    Surface("works[].title.ja", ("workLabel", "workTextOf"), "row:work", "title",
            "the 発売 tab labels a volume row from the bibliographic record's title"),
    Surface("works[].creator", "creditNames", "value", "person",
            "the 発売 tab's byline, the credit field split into the people in it",
            holds_at_zero=False),
    Surface("works[]", ("publisherParts", "publisherPartsHtml", "pubBoth"), "record",
            "publisher",
            "who made the book, on a volume row: the house, the distributor and the line",
            holds_at_zero=False,
            fields=("publisher", "distributor", "imprint")),
    Surface("series[].work", ("workLabel", "workTextOf"), "row:work", "title",
            "the works tab's title, from the row that joined the platforms"),
    Surface("series[].author", "authorLabel", "row:author", "person",
            "the works tab's byline", holds_at_zero=False),
    Surface("series[].latest_ep", "phraseOf", "value", "phrase",
            "the newest chapter's name, shown beside the row"),
    Surface("series[].collection", ("workTextOf", "workLabel"), "value", "title",
            "the collection a work belongs to, named on its own page"),
    Surface("series[].print[]", ("publisherParts", "publisherPartsHtml", "pubBoth"), "record",
            "publisher",
            "the same three names on a work page's volume list", holds_at_zero=False,
            fields=("publisher", "distributor", "imprint")),
    Surface("releases[].work", ("workLabel", "workTextOf"), "row:work", "title",
            "the updates tab's title"),
    Surface("releases[].author", "authorLabel", "row:author", "person",
            "the updates tab's byline", holds_at_zero=False),
    Surface("releases[].ep", ("phraseOf", "epText", "epLine"), "value", "phrase",
            "the chapter name on an update row"),
    Surface("releases[].collection", ("workTextOf", "workLabel"), "value", "title",
            "the collection an instalment belongs to, which is a work and gets a work's rendering"),
]

# Fields whose values hold Japanese and are NOT a name. Each is ruled here so that a field arriving
# with no ruling fails `every Japanese field has a ruling` rather than passing unnoticed, which is
# what a hand-written list of name fields does after six months.
#
# A `ja` field beside an `en` one is the commonest shape here: the row carries both languages and
# the interface picks one, so the Japanese side is Japanese on purpose.
NOT_A_NAME = {
    "index[].y": "the yomi, a reading aid shown only in Japanese",
    "series[].completed_basis": "why a run is called finished, in English",
    "series[].completed_basis_ja": "the same sentence in Japanese, shown in Japanese mode",
    "series[].state_basis": "why a row is called active, in English",
    "series[].state_basis_ja": "the same sentence in Japanese, shown in Japanese mode",
    "series[].evidence[].source": "a source's own name, shown as it names itself",
    "series[].evidence[].term": "the term a source used, quoted rather than translated",
    "series[].state_claims[].source": "a source's own name",
    "series[].state_claims[].term": "the term a source used",
    "series[].sourced_from[].source": "a source's own name",
    "series[].sources[].platform": "a platform's own name; platName renders it",
    "series[].stated_next.platform": "a platform's own name",
    "series[].stated_next.cadence": "the cadence a platform states, quoted",
    "series[].skipped[][]": "chapter identifiers a capture could not read; nothing renders them",
    "works[].title.yomi": "the reading, a Japanese-side aid",
    "works[].first_publication.venue": "the magazine a work first ran in",
    "works[].first_publication.note": "where the date came from, quoted from the record",
    "works[].marketing_label_basis.note": "the publisher's own words, quoted as evidence",
    "works[].admitted_by[].shelf": "the shop shelf that admitted the work, quoted",
    "works[].volumes[].number": "a volume number written in words, 上 and 下 among them",
    "releases[].plat_name": "a platform's own name",
    "releases[].preferred": "a platform's own name",
    "releases[].also_on[]": "a platform's own name",
    "releases[].channel.name": "a channel's own name",
    "releases[].channel.host": "a channel's host, its own name",
    "releases[].channel.origin": "where a channel came from",
    "releases[].channel_name": "a channel's own name",
    "releases[].access_basis": "why a chapter is free or paid, quoted from the platform",
    "releases[].ahead_ep": "a chapter name held ahead of the free window",
    "releases[].ahead_next_ep": "the next chapter name held ahead",
    "releases[].origin_note": "where an imported date came from",
    "releases[].same_title_elsewhere": "a title held by a different work, named for the reader",
    "releases[].id": "a chapter identifier a platform assigned",
    "releases[].kind_basis": "why a row was called a chapter, quoted from what it was read off",
}

RENDERING_RECORDS = ("work_en.", "author_en.", "title.en")


class Unavailable(Exception):
    """node is not installed, or kari/app.js is not beside this repository.

    Raised rather than returning nothing, per §4: a renderer that answered "no Japanese anywhere"
    because it never ran is indistinguishable from a clean page. Callers decide whether that is
    fatal; `check.py` reports it as a violation, because a check that cannot run has not passed.
    """


def available():
    return bool(shutil.which("node")) and APP_JS.exists() and HARNESS.exists()


def render(calls, names=None, names_path=None, prefs=None, app_js=None, timeout=120):
    """Run `calls` through kari/app.js and return `[{"html": …, "text": …}]`.

    `calls` is a list of `(function name, argument)`, both of them app.js's own: `("workLabel",
    {"work": "雨夜の月"})` is the interface being asked what it would put on a row. The argument is
    whatever the function takes, which for the label functions is a row.

    `names` is `feed/names.json` as a dict, or `names_path` is where to read it from. The path form
    exists because that file is 3.8 MB and serialising it into node's stdin costs more than
    rendering does. Passing the dict is what lets `check.py` plant a canary in it (§14b).

    `prefs` sets app.js's own preference variables by name, so `{"LANG": "en"}` is English-only
    mode as a reader selects it. A name app.js does not hold raises rather than being ignored,
    because a preference that silently did nothing would make every check below vacuous.
    """
    app = pathlib.Path(app_js or APP_JS)
    if not shutil.which("node"):
        raise Unavailable("node is not on PATH, so kari/app.js cannot be run")
    if not app.exists():
        raise Unavailable(f"{app} does not exist, so there is no interface to ask")
    req = {"names": names, "names_path": str(names_path) if names_path else None,
           "prefs": prefs or {}, "calls": [list(c) for c in calls]}
    out = subprocess.run([shutil.which("node"), str(HARNESS), str(app)],
                         input=json.dumps(req, ensure_ascii=False), capture_output=True,
                         text=True, timeout=timeout)
    if out.returncode != 0 and not out.stdout.strip():
        raise Unavailable(f"node exited {out.returncode}: {(out.stderr or '').strip()[:400]}")
    try:
        reply = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise Unavailable(f"the harness wrote no reply: {(out.stdout + out.stderr)[:400]}")
    if not reply.get("ok"):
        raise Unavailable(reply.get("error") or "the harness refused")
    return reply["results"]


class Interface:
    """One loaded copy of the interface, holding the name map the browser would have fetched.

    Batched deliberately. Every call spawns node, so asking row by row would spawn once per row;
    the callers below hand over every row of a surface at once and read the answers back in order.
    """

    def __init__(self, names=None, names_path=None, prefs=None, app_js=None):
        self.names, self.names_path = names, names_path
        self.prefs = dict(prefs or {})
        self.app_js = app_js

    def with_prefs(self, **prefs):
        p = dict(self.prefs)
        p.update(prefs)
        return Interface(self.names, self.names_path, p, self.app_js)

    def labels(self, calls):
        """The rendered text of each call, tags and entities removed.

        What a reader reads. A label is HTML, so a check asking whether Japanese survived has to
        look inside the markup and not at it.
        """
        return [r["text"] for r in self.rendered(calls)]

    def values(self, calls):
        """What each call returned, untouched.

        For a function that answers with a string rather than with markup. `foldKey` is the case
        that made this necessary: it folds `4話②＜完＞` to `4話2<完>`, and the tag stripper above
        read `<完>` as an element and threw it away, so a comparison against the Python fold
        reported a disagreement that only the harness had.
        """
        return [r["html"] for r in self.rendered(calls)]

    def rendered(self, calls):
        return render(calls, names=self.names, names_path=self.names_path,
                      prefs=self.prefs, app_js=self.app_js)


# ── what the data carries, derived rather than listed ─────────────────────────────────────────

def derive_fields(collections, depth=7):
    """Every path in the built data holding Japanese, as `{path: values seen}`.

    DERIVED, BECAUSE A LIST GOES STALE WITHOUT SAYING SO. The set of fields carrying a name is not
    a thing to write down once: a pass adds a field, nothing renders it through the store, and a
    reader meets Japanese under an English heading. So the fields are read off the data on every
    run and each one has to be ruled, either by `SURFACES` or by `NOT_A_NAME`.

    EVERY ROW, NOT A SAMPLE. The first version read 800 rows per collection on the argument that
    this is a census of shapes rather than of values, and check.py's own canary went straight
    through it: a probe appends its row to the end of 3,200, and a field nobody has ruled on is
    exactly the kind that appears on one row. Reading the lot costs a quarter of a second.
    """
    out = {}

    def walk(node, path, d=0):
        if d > depth:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k, d + 1)
        elif isinstance(node, list):
            for v in node:
                walk(v, f"{path}[]", d + 1)
        elif isinstance(node, str) and JAPANESE_ANY.search(node):
            out[path] = out.get(path, 0) + 1

    for name, rows in collections.items():
        walk(list(rows or []), name)
    return out


def unruled(collections):
    """Paths the data carries in Japanese that nothing here has ruled on.

    A path is ruled by being rendered through a named function (`SURFACES`), by being declared a
    Japanese string rather than a name (`NOT_A_NAME`), or by belonging to a rendering record.
    Anything else is a field somebody added and nobody decided about, which is the state this
    whole arrangement exists to make impossible.
    """
    ruled = {p for s in SURFACES for p in s.ruled_paths} | set(NOT_A_NAME)
    bad = []
    for path in sorted(derive_fields(collections)):
        if path in ruled or any(part in path for part in RENDERING_RECORDS):
            continue
        bad.append(path)
    return bad


def calls_for(collections):
    """`([(fn, arg), …], [(surface, value), …])` for every value of every ruled surface.

    Returned as two lists in step rather than one list of pairs, because the first goes to node as
    the request and the second stays here to say what each answer was about.
    """
    calls, about = [], []
    for s in SURFACES:
        if s.arg == "record":
            # One call per record, and the values it accounts for travel beside it: the parts are
            # rendered together, so asking three times would render the same row three times and
            # still not say which field a Japanese name came out of.
            for row, _ in _values_at(collections, s.path):
                held = [row.get(f) for f in s.fields if isinstance(row.get(f), str)]
                if not any(v.strip() for v in held):
                    continue
                calls.append((s.renders_with, row))
                about.append((s, " ".join(held)))
            continue
        for row, value in _values_at(collections, s.path):
            if not isinstance(value, str) or not value.strip():
                continue
            if s.arg.startswith("row:"):
                field = s.arg.split(":", 1)[1]
                arg = dict(row) if isinstance(row, dict) else {}
                arg[field] = value
            else:
                arg = value
            calls.append((s.renders_with, arg))
            about.append((s, value))
    return calls, about


def _values_at(collections, path):
    """`(row, value)` for each value at a dotted path, the row being the record it sits on.

    The row travels with the value because the row-taking entry points read a second field off it:
    `workLabel` wants `work_en` beside `work`, and handing it the string alone would ask the
    interface a question no caller asks.
    """
    # `works[]` is the record itself and `works[].title.ja` is a field of it, so the trailing
    # marker is taken off before the split rather than being left to fall through as a key nothing
    # holds, which is how this returned nothing at all for the publisher surfaces.
    head, _, rest = (path[:-2] if path.endswith("[]") else path).partition("[].")
    rows = collections.get(head) or []
    out = []
    for row in rows:
        for value in _dig(row, rest, row):
            out.append(value)
    return out


def _dig(node, path, row):
    if not path:
        return [(row, node)]
    key, _, rest = path.partition(".")
    if key.endswith("[]"):
        key = key[:-2]
        got = (node or {}).get(key) if isinstance(node, dict) else None
        return [v for item in (got or []) for v in _dig(item, rest, item)]
    if not isinstance(node, dict) or key not in node:
        return []
    return _dig(node[key], rest, row)


def _self_check():
    """Prove the harness loads the real file and answers from it, not from anything here."""
    if not available():
        print("SKIP: node or kari/app.js is not available")
        return 0
    got = render([["workLabel", {"work": "雨夜の月"}], ["foldKey", "ＡＢ　Ｃ"]],
                 names={"titles": {}, "authors": {}, "phrases": {}}, prefs={"LANG": "en"})
    print(json.dumps(got, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(_self_check())
