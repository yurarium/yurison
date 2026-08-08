#!/usr/bin/env python3
"""Invariants and budgets, defined once and read two ways.

WHY THIS EXISTS. Of the bugs that reached the published site, almost none were matters of taste —
they were statements that were simply false, and nothing was checking. Ruby that did not spell its
own reading. A claim in a feed that is supposed to hold only attested rows. Japanese on a page in
English-only mode. Each was found by eye, weeks apart, after shipping.

TWO CONSUMERS, ONE DEFINITION. The backend build runs unattended and the site must keep updating,
so at runtime a violated invariant DEGRADES to a stated fallback and is counted. A check-in has a
person present who can fix it, so there the same violation BLOCKS. Defining the rules once and
varying only the consequence is deliberate: two rule sets drift apart, and paths that disagree
about the same fact is the single most common bug in this project's history.

  ./check.py --runtime    count, report, exit 0 — for build.py and CI's data stage
  ./check.py --gate       exit non-zero on any violation or loosened budget — for hooks and CI
  ./check.py --self-test  prove the checks can actually fail (see below)

SELF-TEST, AND WHY IT IS NOT OPTIONAL. This project's characteristic failure is silence: an
analyser that returns the input instead of an error, a grep that swallows a traceback, a green tick
from a build of the wrong commit. A check that cannot demonstrate it would have caught something is
indistinguishable from a check that does nothing. --self-test plants a known-bad record and
requires each invariant to reject it, exactly as .githooks/leak-guard.sh canaries itself. `--gate`
runs it first and refuses to pass if it fails.

BUDGETS RATCHET ONE WAY. Tier-2 numbers are counts with no correct value, only a direction. A green
`--gate` tightens the recorded budget to what was actually measured; loosening one requires editing
docs/budgets.json by hand, which puts the reason in a commit message where it can be argued with.
"""
import argparse, ast, collections, json, os, pathlib, re, subprocess, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
# Imported for its effect and not for a name: it points yaml.safe_load at libyaml for this process
# and everything loaded into it, adapters/captures.py included. Worth 6 seconds of a 47-second gate
# and no more, because captures.py's JSON sidecars had already spared the gate most of its parsing;
# the gate's own time is in self_test's deepcopy and the lint subprocesses. It is here so that the
# invariants which do read YAML get the fast parser, and so a machine cannot end up with build.py
# and check.py reading the same file two different ways. See adapters/yamlfast.py.
from adapters import yamlfast  # noqa: F401,E402
BUILD = ROOT / "data" / "build"
NAMES = ROOT / "data" / "names"
BUDGETS = ROOT / "docs" / "budgets.json"
# Derived, not written out: the site repo sits beside this one. See adapters/paths.py.
SITE_ROOT = pathlib.Path(os.environ.get("YURARIUM_SITE") or ROOT.parent / "yurarium.github.io")
SITE = SITE_ROOT / "kari" / "data"

# Every file a reader can load. The English strings live inside the pages rather than in a
# resource file, so the pages themselves are the text; there is nowhere else to look.
READER_TEXT = [SITE_ROOT / "index.html", SITE_ROOT / "README.md",
               SITE_ROOT / "kari" / "index.html", SITE_ROOT / "kari" / "status.html",
               ROOT / "README.md"]     # this repo goes public at 1.0; its README is public text

JAPANESE = re.compile(r"[぀-ヿ一-鿿　-〿＀-￯]")
# Kana and the marks that only ever appear beside them. Narrower than JAPANESE on purpose: this
# asks whether a string a reader is shown INSTEAD of the Japanese still holds a character they
# cannot read, and a stray 　 or ＆ is a different complaint.
KANA_ANY = re.compile(r"[ぁ-ゖァ-ヺヽヾゝゞー]")
KANA = re.compile(r"^[぀-ヿ\s・ー]*$")


def _load(p, default=None):
    try:
        return json.loads(pathlib.Path(p).read_text())
    except Exception:
        return default


def _yaml(p, default=None):
    """One parse per file per run, shared with every other reader of it.

    The big queue captures run to megabytes and four budgets plus status.py each loaded them
    separately, so a deploy parsed the same YAML four or five times and did it again on the next
    deploy whether or not a capture had run. adapters/captures.py keys a sidecar on the file's size
    and modification time, so a rewritten capture misses and an untouched one is nearly free.
    """
    try:
        sys.path.insert(0, str(ROOT))
        from adapters import captures
        doc = captures.load(p)
        return doc if doc else (default if doc == {} and not pathlib.Path(p).exists() else doc)
    except Exception:
        return default


# ── Tier 1: invariants ────────────────────────────────────────────────────────────────────────
#
# Each returns a list of violations. Empty means the statement holds. Every one of these
# corresponds to something that actually went wrong; none is hypothetical.
#
# `fallback` names what the build does instead when the statement fails. It is documentation, not
# code — the degradation lives where the data is produced, and naming it here is what stops a
# silent fallback from being mistaken for a passing check.

def inv_ruby_spells_reading(ctx):
    """Ruby that does not spell its own reading is one record contradicting itself on one line.

    fallback: drop the ruby, keep the reading.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import kana
    except Exception:
        return []
    bad = []
    for r in ctx["series"]:
        we = r.get("work_en") or {}
        rd, rb = we.get("reading"), we.get("ruby")
        if not rd or not rb:
            continue
        # kana.ruby_spells is the definition of the question: a particle is written as it is
        # spelled and read as it sounds, so a literal comparison calls correct ruby a
        # contradiction. Putting わ over は would be the actual error.
        if not kana.ruby_spells(rb, rd):
            bad.append(r["work"])
    return bad


def inv_no_ruby_over_latin(ctx):
    """Furigana over "M" is not furigana — Sudachi reads M as メートル, metre.

    A single letter may keep the reading that is its own NAME (V in Vチューバー is ブイ).
    fallback: emit the run bare, with no reading.

    READ ON THE SHIPPED SPANS AS WELL AS THE STORED ONES, and it took a reader to find out why.
    This asked the store, and the store holds no spans for 紗痲 Fallin' Jail: build.py aligns the
    reading at render time for a record that has none. That alignment put Fallin over Fallin and
    Jail over Jail, the work shipped reading `紗痲しゃま FallinFallin' JailJail` in Japanese with
    furigana on, and every gate was green. §14b: a check that only sees what its subject stored
    cannot report what its subject produced.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import kana, pass4_analyser as p4
    except Exception:
        return []
    bad = []

    def look(where, spans):
        for span in spans or []:
            t, rd = (list(span) + [None, None])[:2] if isinstance(span, (list, tuple)) else (0, 0)
            if not (rd and t and all(c.isascii() for c in str(t))):
                continue
            nm = p4.LETTER_NAME.get(str(t).upper()) if len(str(t)) == 1 else None
            if nm and kana.to_hiragana(nm) == rd:
                continue
            bad.append(f"{where}: {t}->{rd}")

    for kind in ("titles", "authors"):
        for k, v in (ctx["names"].get(kind) or {}).items():
            look(k, v.get("furigana_spans"))
    for r in ctx["series"]:
        for key in ("work_en", "author_en"):
            look(f"{r.get('id')} {key}", (r.get(key) or {}).get("ruby"))
    return bad


def inv_feed_is_attested(ctx):
    """A listing site's claim is an INPUT. The feed holds what a platform attested, and nothing else.

    fallback: drop the row from the feed; it stays in the claim trace on status.html.
    """
    return [r.get("work") for r in ctx["releases"] if r.get("provenance") != "attested"]


def inv_no_unknown_kind(ctx):
    """Every update says what kind of update it is. `unknown` meant a claim row, and those are gone.

    fallback: drop the row rather than publish an uncategorised update.
    """
    return [r.get("work") for r in ctx["releases"] if r.get("kind") == "unknown"]


def inv_readings_are_kana(ctx):
    """The stored form is the KANA reading, never a romanised string (NAMES-PLAN §8.1).

    Yūri, Yuuri and Yuri all derive from kana and none derives from another, so a romanised string
    in this field permanently caps what the reader's style control can offer.
    fallback: reject that record; the work renders in Japanese.
    """
    # NOT "the reading is only kana". A reading legitimately carries digits, Latin and punctuation
    # straight through from the surface — 100日後に reads "100 ニチゴ ニ", and #うちらが最強 keeps its
    # hash. The thing §8.1 forbids is a ROMANISED string standing in for the reading, so the test
    # is whether a run of Latin letters appears in the surface it came from. If it does, it was
    # passed through; if it does not, something romanised it.
    bad = []
    for kind in ("titles", "authors"):
        for k, v in (ctx["names"].get(kind) or {}).items():
            rd = v.get("reading")
            if not rd:
                continue
            # FOLDED, because ＪＫ and JK are the same letters. A title writes them full-width and
            # a reading passes them through folded, and comparing raw called that a romanisation:
            # 先生とＪＫ failed on a reading of センセイ ト JK, which is the surface's own letters.
            # Folding cannot weaken the test, since a romanisation of kanji appears in the surface
            # under neither width.
            surface = unicodedata.normalize("NFKC", k).lower()
            for run in re.findall(r"[A-Za-z]{2,}", unicodedata.normalize("NFKC", rd)):
                if run.lower() not in surface:
                    bad.append(f"{kind}:{k[:20]}={rd[:24]}")
                    break
    return bad


def inv_reading_can_show_its_source(ctx):
    """A reading that says a source states it must be able to show that source.

    NAMES-PLAN §1: the failure mode is a plausible reading with no source behind it, presented as
    if it had one, which at a glance is indistinguishable from a correct one. `reading_basis:
    stated` IS that presentation. So the basis has to be backed by an address a reader can open,
    and the two shapes counted here are the two ways it stopped being.

    A CLAIM WITH NO DOCUMENT. 11 curated titles said a source stated their reading while naming
    `yurarium` and holding no page. One curated entry carries two claims and had one citation
    between them, so a title translated here and read off a shop page stamped the translation's
    provenance onto the reading. The reading_note beside each named BOOK☆WALKER and prose is not
    something a check can act on.

    A DOCUMENT WITH NO CLAIM. 11 refuted author readings kept a source and a date after the reading
    was withdrawn, and two kept a URL pointing at the MangaUpdates page for a DIFFERENT PERSON,
    which is the page the refutation was written to disown.

    §14b, WHAT THIS SHARES AND WHAT IT THEREFORE CANNOT SEE. It reuses `provenance.faults`, which
    is not the thing that produces an address: `store._stamp` writes one whenever a pass hands it
    over and has never looked at a basis, while this asks the basis and then asks whether an
    address is held. Two producers, and the check is the assertion that they agree, so a pass that
    forgot to record a page cannot satisfy it by forgetting consistently.

    What it cannot see is whether the page says what we say it says. An address that resolves to
    the wrong record passes here, and only the reader following it will know. That is the residual
    §14b names, and it is why the address is shipped rather than merely counted.

    fallback: the citation is not rendered, and the reading shows as it did before.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        from names import provenance
    except Exception:                                                       # noqa: BLE001
        return []
    bad = []
    for kind in ("titles", "authors"):
        for ja, fault, detail in provenance.faults(ctx["names"].get(kind) or {}):
            bad.append(f"{kind}:{ja[:24]} {fault} ({detail[:60]})")
    return bad


def _interface(ctx):
    """The interface, loaded once for this run and holding the names the browser would fetch.

    Built from `ctx` rather than from the files, so a canary planted in the context reaches the
    renderer like any other row (§14b). Kept on the context so several checks share one load.
    """
    import tempfile
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    if "_iface" not in ctx:
        # RUN THE SOURCE THE CONTEXT HOLDS, not the file on disk. `interface_js` is loaded in
        # `context()` for the reason everything else is: a check that opens its own file cannot be
        # shown a canary, and self_test plants one in this string to prove the fold comparison can
        # fail. Written out because node loads a path.
        src = ctx.get("interface_js") or ""
        path = None
        if src:
            fh = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
            fh.write(src)
            fh.close()
            path = fh.name
        ctx["_iface"] = interface.Interface(names=ctx["names_shipped"] or {}, prefs={"LANG": "en"},
                                            app_js=path)
    return ctx["_iface"]


def _status_interface(ctx):
    """status.html's own script, loaded in a context of its own.

    A SECOND CONTEXT AND NOT A SECOND SCRIPT IN THE FIRST. `app-status.js` declares `esc`, `T`,
    `splitLang`, `SEP` and `render` at the top level and so does `app.js`, and a `const` redeclared
    in one context's global lexical scope is a SyntaxError. They are two pages and they get two
    contexts, which is also what a browser gives them.
    """
    import tempfile
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    if "_siface" not in ctx:
        src = ctx.get("status_js") or ""
        if not src:
            return None
        fh = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
        fh.write(src)
        fh.close()
        # No name map. This page states facts about the collection and draws no name through the
        # store; handing it one would suggest otherwise.
        ctx["_siface"] = interface.Interface(names={"titles": {}, "authors": {}, "phrases": {}},
                                             prefs={"LANG": "en"}, app_js=fh.name)
    return ctx["_siface"]


def _collections(ctx):
    """The built collections under the names `adapters/interface.py` rules them by.

    THE RECORD PAGES ARE HERE BECAUSE A READER CAN OPEN THEM. `credits.json` and `publishers.json`
    are fetched only when one of those 2,405 addresses is visited, so neither was in this list and
    neither was measured; `status.json` is a whole published page nothing walked. A surface nobody
    walks is a surface nobody measures, and the first walk of the credit pages found the homophone
    list writing a name into the markup without asking the renderer for it.
    """
    return {"index": ctx["index"], "series": ctx["series"], "works": ctx["works"],
            "releases": ctx["releases"],
            "credits": list(((ctx["credit_pages"] or {}).get("credits") or {}).values()),
            "publishers": list(((ctx["publisher_pages"] or {}).get("publishers") or {}).values()),
            "status": [ctx["status"]] if ctx.get("status") else []}


def inv_english_mode_has_no_japanese(ctx):
    """English-only mode shows no kana and no kanji, asked of the interface rather than modelled.

    WHAT THIS USED TO BE, AND WHY IT WENT GREEN OVER A VISIBLE FAULT. It held a `fold`, a `render`
    reimplementing the name lookup and a `joins` guessing at app.js's fallback order, and the guess
    was generous: it tried the title with its subtitle stripped and with the separator turned into
    a space, and app.js tries neither. So
    `シャドウ・アサシンズ・ワールド : 影は薄いけど、最強忍者やってます` was on the 発売 tab in
    English mode with this check reporting nothing, which is the third drift of the same shape in
    one day (STANDING-INSTRUCTIONS §3).

    It now loads `kari/app.js` and calls the file's own label functions over every row of every
    surface `adapters/interface.py` rules. There is no model of the renderer left to be wrong.

    KANA AND KANJI, WHICH IS NARROWER THAN THIS USED TO ASK, and the narrowing is a finding rather
    than a relaxation. The old test also failed a full-width character, and running the real
    renderer showed why that is wrong: `2×2＝SHINOBUDEN+` is the work's OWN English name, published
    with a full-width ＝, and the interface renders `en_forms` where the transcription read `en`,
    an ASCII-folded copy. A reader in English meets the title the work publishes. What they must
    not meet is a script they cannot read. `full-width forms in English renderings` counts the rest
    so the narrowing is a number rather than a silence.

    §14b, WHAT THIS CANNOT SEE. A call site that never calls the renderer. Running the interface
    proves that what reaches it comes out right, and says nothing about `esc(w.t)` written beside
    it, which is how 2,430 rows shipped Japanese once already. `adapters/lint/entrypoints.py` is
    the other half and `names reach a page only through their renderer` is where it blocks.

    fallback: show the Japanese (§6), which is a finished state rather than a failure.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    try:
        iface = _interface(ctx)
        calls, about = interface.calls_for(_collections(ctx))
        if not calls:
            return []
        out = iface.labels(calls)
    except interface.Unavailable as e:
        # A check that could not run has not passed. Reported rather than skipped, because a
        # renderer nobody ran answers "no Japanese anywhere" for exactly the same reason a clean
        # page does (§4).
        return [f"the interface could not be run, so nothing here was checked: {e}"]
    bad = []
    for (surface, value), shown in zip(about, out):
        if not surface.holds_at_zero:
            continue
        if interface.KANA_KANJI.search(value) and interface.KANA_KANJI.search(shown):
            bad.append(f"{surface.path}:{value[:32]}")
    return sorted(set(bad))


def budget_interface_reads_outside_an_entry_point(ctx):
    """Reads of a name field in kari/app.js that are excepted rather than going through a renderer.

    THE EXCEPTIONS, COUNTED. `entrypoints.SAFE` lets a call site read a name field without
    rendering it, because some of them must: a comparator sorts on the Japanese, a grouping key is
    the string as written, and the work identifier in the address bar shares a field name with a
    title without being one. Each entry says which function, which field, what is done with the
    value and how many times, so a read added beside an allowed one fails.

    A number here rather than a list nobody looks at (§13). Every entry is a place where the
    guarantee rests on a sentence somebody wrote instead of on the arrangement, and the count is
    what makes adding one an argument rather than an edit.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "lint"))
    try:
        import entrypoints
    except Exception:                                                           # noqa: BLE001
        return 0
    return sum(n for n, _why in entrypoints.SAFE.values())


def budget_renderings_still_japanese_in_english_mode(ctx):
    """Rows the interface still shows in kana or kanji on an English page, where it is a deficit.

    WHAT IS LEFT ONCE THE NOTATION IS AN INVARIANT. This counted two different things and reported
    one number: a role nobody had glossed and a pen name nobody has researched. They are not the
    same event. `no cataloguing notation in an English rendering` and `every credit role has an
    English gloss` block on the first at zero, because the catalogue's notation has a right answer
    and losing it is a fault. What stays here is §6: a name the store cannot render shows as the
    Japanese, and that is a finished state rather than a failure.

    SO IT FALLS ONLY WHEN A NAME IS RESEARCHED, and it cannot go to zero this week. 94 of the
    surviving runs are credits with no record in the store at all, 25 are a magazine's editorial
    desk, 15 are records the store holds no reading for, and the rest are names inside a
    compound the store has met only in part.

    MEASURED BY RUNNING THE INTERFACE, so it owes nothing to any producer and cannot be reduced by
    changing what the build stores.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    try:
        calls, about = interface.calls_for(_collections(ctx))
        if not calls:
            return 0
        out = _interface(ctx).labels(calls)
    except interface.Unavailable:
        return 0
    return sum(1 for (s, value), shown in zip(about, out)
               if not s.holds_at_zero
               and interface.KANA_KANJI.search(value) and interface.KANA_KANJI.search(shown))


def budget_full_width_forms_in_english_renderings(ctx):
    """English renderings that still hold a full-width character, having no kana and no kanji.

    WHY THIS IS SEPARATE FROM THE INVARIANT. `English mode has no Japanese` used to fail a
    full-width character as well as a script, and running the real renderer showed that rule
    catching the work's own name: `2×2＝SHINOBUDEN+` is published with a full-width ＝ and the
    interface renders `en_forms`, where the transcription had read `en`, an ASCII-folded copy of
    it. Blocking there would ask a reader to be shown a title the work does not use.

    So the invariant narrowed to kana and kanji, and this counts what the narrowing let past, which
    is what stops a narrowing from being a silence (§13).

    308 OF THEM WERE A CATALOGUER'S TYPING AND ARE GONE. `Ｍａｇｐｉｅ`, `ｆｉｎｉｔｅ` and
    `Ｈｏｕｒａｉ　Ｄｏｌｌ` are Latin pen names typed full width, and the store holds nothing for
    them because a Latin pen name is not a transliteration of anything; the surface reached an
    English page with its width intact. `plainLatin` in kari/app.js folds a name holding no kana
    and no kanji, which is NFKC and not a reading. What is left is mostly a TITLE published with a
    full-width mark, `2×2＝SHINOBUDEN+` being the recorded one, and those are correct.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    fw = re.compile(r"[！-｠￠-￮　]")
    try:
        calls, about = interface.calls_for(_collections(ctx))
        if not calls:
            return 0
        out = _interface(ctx).labels(calls)
    except interface.Unavailable:
        return 0
    return sum(1 for (_s, _v), shown in zip(about, out)
               if fw.search(shown) and not interface.KANA_KANJI.search(shown))


def inv_names_reach_a_page_only_through_their_renderer(ctx):
    """No field carrying a name is put on a page except by the function that renders that kind.

    THE HALF A RUNNING RENDERER CANNOT DO. Every leak this project has shipped was a call site that
    did not call the renderer: `esc(w.t)` from index.json on the catalogue tab, a volume row
    labelled from the bibliographic record's title, `credit()` glossing the bracket and leaving the
    name. None of those reaches a renderer, so running one finds none of them.

    So this reads `kari/app.js` and asserts a relation between two sets. The fields carrying a name
    are DERIVED from the built data by `adapters/interface.py`, not listed here, so one added by a
    later pass has to be ruled on. The entry points are named beside them. Every read of one of
    those fields must be inside its entry point, an argument to it, or an entry in
    `entrypoints.SAFE` that says which function, which field, what is done with the value, how many
    times, and why.

    §14b, WHAT IT SHARES: `interface.SURFACES`, which is also what the check above renders through.
    That is the point rather than a cost. The two checks ask different questions of one table, and
    a table naming a field the interface does not render fails this one, while a table missing a
    field the DATA carries fails `every Japanese field the data carries has a ruling`.

    What it cannot see is a fault inside an entry point, which is what running the renderer is for.

    fallback: none. This reads a file in another repository and cannot degrade a build.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "lint"))
    src = ctx.get("interface_js")
    if not src:
        return []
    try:
        import entrypoints
    except Exception as e:                                                      # noqa: BLE001
        return [f"adapters/lint/entrypoints.py will not import ({e}), so nothing was checked"]
    return entrypoints.findings(src)


def inv_every_japanese_field_has_a_ruling(ctx):
    """Every field the built data carries in Japanese is either a name with a renderer or is not.

    WHY THE FIELD LIST IS DERIVED. A list of the fields carrying a name is exactly the kind of
    thing that goes stale without saying so: a pass adds a field, nothing renders it through the
    store, and a reader meets Japanese under an English heading. So the paths are read off the data
    on every run, and each has to be answered either by `interface.SURFACES`, which says what
    renders it, or by `interface.NOT_A_NAME`, which says it is Japanese on purpose and why.

    A NEW FIELD IS A DECISION SOMEBODY MAKES. That is the whole of what this buys, and it is the
    part neither running the renderer nor reading the source can supply: both of those start from a
    field somebody already thought about.

    fallback: none. An unruled field is not a build failure; it is a question for a person, and
    check-in is where a person is.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    return [f"{path}: holds Japanese and nothing says whether it is a name"
            for path in interface.unruled(_collections(ctx))]


def inv_no_absolute_paths_in_published_files(ctx):
    """No file we publish names a directory on the machine that built it.

    checks.json records example findings, and several invariants report a finding as
    "<file>:<line>: <what>" with an absolute path. A failing prose lint therefore wrote a home
    directory into a public repository, and the commit hook was the only thing that noticed.
    A guard in the writer fixes today's case; this one fails the next writer to do it.
    fallback: none available. A path leak is not something to degrade past.
    """
    import re as _re
    bad = []
    pat = _re.compile(r"(/home/|/Users/|C:\\Users\\)[^\s\"']+")
    for f in sorted(BUILD.rglob("*.json")):
        try:
            hits = pat.findall(f.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if hits:
            bad.append(f"{f.relative_to(BUILD)}: {len(hits)} absolute path(s)")
    return bad


def inv_fixture_states_where_it_came_from(ctx):
    """A committed fixture names the page it was cut from, and matches its own digest.

    WHAT GOES WRONG WITHOUT THIS. Tests run offline, so a parser can only be tested against markup
    somebody wrote down, and markup somebody wrote down contains what they imagined. The ニコニコ
    channel pattern read a promotional sidebar banner instead of the breadcrumb and matched on
    every page of the site, so all 180 works agreed on one wrong answer; the fixture it had been
    written against had no sidebar in it. Six months on, an invented page and a captured one are
    the same file. The header is what tells them apart, so it is required rather than encouraged.

    THE DIGEST IS RECOMPUTED HERE, from the bytes after the separator, with no help from
    adapters/fixtures.py. That is the part of this check that does not share its subject's blind
    spot (§14b): everything else defers to `fixtures.problems`, which is the one definition of a
    well-formed header and is therefore also blind to a `fixtures.py` that has stopped splitting
    the file where it says it does. Hashing the raw text catches that, because it owes the module
    nothing but the name of the separator.

    WHAT IT CANNOT SEE. Whether the markup is honest. A person who edits a fixture and recomputes
    its digest passes, and so does one who captured the wrong page. `fixtures.py recheck` answers
    the second by re-deriving from the caches, and the first is what `why` and a reader are for.

    fallback: none available. Nothing in build.py reads a fixture, so there is nothing to degrade
    to; a bad fixture is a test that is lying and belongs blocked at check-in.
    """
    import hashlib as _h
    bad = []
    for name, text in sorted((ctx["fixtures"] or {}).items()):
        head, sep, body = text.partition("\n---\n")
        if not sep:
            bad.append(f"{name}: no separator between the header and the markup")
            continue
        m = re.search(r"^body_sha256:\s*(\S+)\s*$", head, re.M)
        if not m:
            bad.append(f"{name}: records no body_sha256")
        elif _h.sha256(body.encode("utf-8")).hexdigest() != m.group(1):
            bad.append(f"{name}: the markup is not what its body_sha256 says it is, so it has "
                       "been edited since it was captured")
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        import fixtures
    except Exception:                                                           # noqa: BLE001
        return bad + ["adapters/fixtures.py will not import, so no header can be read"]
    for name, text in sorted((ctx["fixtures"] or {}).items()):
        bad += fixtures.problems(name, text)
    return bad


def inv_no_stock_phrasing_in_public_text(ctx):
    """Public prose says things rather than performing them.

    Not a disguise: the project does not hide being AI-driven, and nothing here defeats a detector.
    These are constructions that waste a sentence, reach for an abstraction where a fact belongs,
    or add rhythm in place of content. The documentation ships so a third party can pick the
    project up, which makes it part of the deliverable rather than notes to ourselves.

    Only the HARD list and density are absolute. Words that are filler only in bulk are a budget.
    fallback: none needed. This reads files already written; it cannot degrade a build.
    """
    out = subprocess.run(
        [sys.executable, str(ROOT / "adapters" / "lint" / "tics.py"), "--prose",
         *[str(f) for f in READER_TEXT if f.exists()]],
        capture_output=True, text=True, timeout=60)
    # Parse on the lint's own markers, not on an em dash: this line used to split on " — " and the
    # lint's output separator changed, which would have made the invariant silently vacuous.
    # Structural findings count too, or the check would report them and block nothing.
    bad = [l.split(" -> ")[0].strip() for l in out.stdout.splitlines() if " -> " in l]
    bad += [l.strip() for l in out.stdout.splitlines() if l.startswith("STRUCTURE:")]
    return bad


def inv_content_flags_are_accounted_for(ctx):
    """Every content flag a source raised is reported, and every withheld one is absent.

    THE FAILURE THIS REPLACES. adapters/kadokomi/confirm.py wrote a register of works flagged
    `ratingLevel='adult'` from the project's first run, headed "Not published". Nothing read it,
    all five were live on the public site, and no number anywhere disagreed. A register nothing
    consumes is worse than no register: it reads as a control that is working.

    So this does NOT check that flagged works are withheld. Policy is that they are published,
    because every platform here is a commercial publisher's web arm. It checks that the register
    and the published report agree, which is the thing that failed. A flag arriving from a new
    source, on a platform nobody has thought about, cannot now pass unmentioned: it either appears
    in run.json's content_flags or this fails.

    Withholding remains available per entry (`withhold: true`), and where used it is checked
    against the DEPLOYED bytes by substring, because field-shaped checks missed five of the six
    surfaces those titles were on.

    fallback: none. This guards a standing constraint rather than a data-quality target.
    """
    reg = {}
    for f in sorted((ROOT / "data" / "source").rglob("withheld.yaml")):
        for w in (_yaml(f, {}) or {}).get("works") or []:
            if w.get("work_title"):
                reg[w["work_title"]] = bool(w.get("withhold"))
    run = _load(BUILD / "run.json", {}) or {}
    reported = {r.get("title"): r for r in (run.get("content_flags") or {}).get("rows") or []}

    bad = []
    for title, withhold in reg.items():
        if title not in reported:
            bad.append(f"flagged but not reported anywhere: {title[:30]}")
        elif bool(reported[title].get("withheld")) != withhold:
            bad.append(f"report disagrees with the register: {title[:30]}")
    # THE BUILD-TIME SIGNAL NEEDS GUARDING TOO. Scoping this check to the file register alone left
    # the marketing flags reported and unchecked: a fire-drill deleted all three from the report and
    # this passed, which is the shape the whole invariant exists to catch. So they are recomputed
    # here from the DEPLOYED works list, using build.py's own patterns rather than a second copy.
    #
    # ONE WORK IS OFTEN TWO ROWS, AND THE TWO SPELL IT DIFFERENTLY. A serialisation row and a book
    # row for the same work sit side by side in series.json, and 昨日シたのに覚えてないの？ 百合えっ
    # ち短編集 is spaced on the platform where the bibliography writes ISBD's colon. `marketing_flags`
    # keys on `norm_work` and reports one row for the pair; comparing the raw strings asked for two
    # and named the surviving spelling as unaccounted for. So the comparison is on the same
    # normalised form, which is the ANSWER build.py reached and not the PATTERN it reached it with:
    # the patterns above are still applied here to a list build.py did not hand over, so a flag that
    # stopped being raised at all is still what this catches.
    expect_marketing, norm = set(), lambda t: t
    try:
        sys.path.insert(0, str(ROOT))
        import importlib.util
        _spec = importlib.util.spec_from_file_location("buildpat", ROOT / "build.py")
        _b = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_b)
        norm = _b.norm_work
        for r in (_load(SITE / "series.json", {}) or {}).get("series", []):
            w = r.get("work") or ""
            if _b.ADULT_MARKETED.search(w) and _b.COLLECTION_MARK.search(w):
                expect_marketing.add(w)
    except Exception as e:
        bad.append(f"could not recompute the marketing signal: {type(e).__name__}")

    reported_norm = {norm(t) for t in reported}
    expect_norm = {norm(t) for t in expect_marketing}
    for title in expect_marketing:
        if norm(title) not in reported_norm:
            bad.append(f"adult-marketed and not reported: {title[:30]}")

    for title, row in reported.items():
        # The file register records what a SOURCE said; the marketing signal is what the build
        # noticed. Both must be reported; only the first must exist on disk.
        if title not in reg and norm(title) not in expect_norm:
            bad.append(f"reported as flagged but not in any register: {title[:30]}")

    # A withheld work must be absent from everything served, checked on the bytes.
    for title, withhold in reg.items():
        if not withhold:
            continue
        for f in sorted(SITE.rglob("*.json")):
            try:
                if title in f.read_text(encoding="utf-8", errors="replace"):
                    bad.append(f"withheld but published: {f.relative_to(SITE)}: {title[:24]}")
            except OSError:
                pass
    return bad


def inv_archives_unchanged(ctx):
    """A published month is written once. That is what protects its dates (REQUIREMENTS §5).

    fallback: keep the published file and warn — build.py already does this; here it is asserted.
    """
    bad = []
    for f in sorted((BUILD / "feed").glob("[0-9]*-[0-9]*.json")):
        live = SITE / "feed" / f.name
        if live.exists() and live.read_bytes() != f.read_bytes():
            bad.append(f.name)
    return bad


def inv_deployed_matches_built(ctx):
    """What the site serves is what the build produced.

    fallback: do not copy the differing file; the previous one stays served.

    TIMING MATTERS FOR THIS ONE. It is false for the whole window between a build finishing and
    deploy.sh copying, which is exactly when build.py runs the checks — so the report published
    beside the data claimed five violations that copying had already fixed, every single time.
    deploy.sh now re-runs the checks after copying and ships the report last. A report that is
    wrong by construction is worse than no report: it teaches the reader to ignore it.
    """
    if not SITE.exists():
        return []
    bad = []
    for f in list(BUILD.glob("*.json")) + list((BUILD / "feed").glob("*.json")):
        rel = f.relative_to(BUILD)
        # checks.json reports on this comparison and is written after it; including it would have
        # the check fail on its own output.
        if rel.name == "checks.json":
            continue
        live = SITE / rel
        if live.exists() and live.read_bytes() != f.read_bytes():
            bad.append(str(rel))
    return bad


def inv_state_agrees_with_its_own_date(ctx):
    """A work's published state must be consistent with the date published beside it.

    State is decided from one platform's row and the headline date is merged across all of them, so
    the two can disagree without anything looking wrong. きみが死ぬまで恋をしたい shipped as
    `dormant` beside a latest chapter of 2026-07-18, three weeks old, because コミックDAYS was
    behind and its row won the sort. A reader seeing that sees the database contradict itself.

    The thresholds are build.py's: active within 45 days, slow within a year, dormant beyond it.
    This does not recompute the state, which would only restate the same arithmetic; it checks that
    whatever decided it did not leave a date behind that says something else.
    """
    import datetime
    today = datetime.date.today()
    bad = []
    for r in ctx["series"]:
        st, lat = r.get("state"), r.get("latest")
        if st not in ("active", "slow", "dormant") or not lat:
            continue
        try:
            age = (today - datetime.date.fromisoformat(str(lat)[:10])).days
        except ValueError:
            continue
        want = "active" if age <= 45 else ("slow" if age <= 365 else "dormant")
        if want != st:
            bad.append(f"{r.get('work')}: {st} beside a chapter {age} days old")
    return bad


def inv_no_refutation_of_print_serials(ctx):
    """A web platform cannot refute a claim about a work that also runs in a magazine.

    The two record different events. コミック百合姫 prints an instalment and 一迅プラス puts it online
    weeks later, so the platform's chapter dates say nothing about whether the work published on
    the claimed date — it published in print. Sixteen of nineteen refutations were 一迅プラス, eleven
    of them works we hold on a 百合姫 imprint in our own print catalogue, and their gaps clustered at
    magazine intervals: 14, 28, 31, 35, 36 days, several NEGATIVE because the web chapter came
    after the claim rather than before it.

    REQUIREMENTS §4 already says absence is evidence of absence only where the list is known to be
    complete. A publisher's web arm is not a complete list of that publisher's publications; the
    magazine is.

    fallback: the claim is dispositioned print-serialised, not refuted, and stays open to a source
    that can actually speak to magazine dates.
    """
    run = _load(BUILD / "run.json", {}) or {}
    refuted = [t for t in (run.get("claims", {}).get("trace") or [])
               if t.get("disposition") == "refuted"]
    if not refuted:
        return []
    works = ctx["works"]

    def nm(x):
        t = x.get("title")
        return (t.get("ja") if isinstance(t, dict) else t) or ""

    def norm(t):
        return re.sub(r"[\s　・･!！?？…‥、。,.\-–—〜~\"'’“”()（）\[\]【】]", "", (t or "").lower())

    print_titles = {norm(nm(x)) for x in works}
    return [t["work"] for t in refuted if norm(t["work"]) in print_titles]


def inv_undated_works_say_where_and_why(ctx):
    """A work with no publication date still states where it was published, and why it is undated.

    DEFINITIONS §6 was amended on 2026-08-05 so that a work that exists is recorded whether or not
    anyone can date it. What it asks in exchange is the part that got dropped: the scope test turns
    on WHERE, so the venue and the country are required of every record, and the missing date is
    stated as `date_basis` rather than left as an empty field pretending nobody looked.

    THE BUILD WROTE `venue: null` ON EVERY UNDATED WORK, contradicting §6 in the same branch whose
    comment cites it, and 1,209 records carried it. Every one of them had a venue: BOOK☆WALKER
    names a publisher on every volume it sells and `bwingest.py` had been storing it all along.

    IT ALSO WROTE ONE REASON OVER FOUR. `no-date-attested` stood for an imprint that prints nothing,
    a chapter serial that has no volumes at all, an imprint that dates its other books and not this
    one, and too little read to tell those apart. The capture had already sorted them and the
    build flattened the answer, so a later pass had nothing to aim at.

    So this asks both questions of every undated work. `no-date-attested` is still legitimate, for
    a source that genuinely said nothing about why, and it is what the fourth branch means.

    fallback: none. This is an invariant because both fields are derivable from records already in
    hand, so a violation is the build having dropped something rather than a source withholding it.
    """
    bad = []
    for w in ctx["works"]:
        fp = w.get("first_publication") or {}
        if fp.get("date"):
            continue
        missing = [k for k in ("venue", "country", "date_basis") if not fp.get(k)]
        if missing:
            bad.append(f"{w.get('work_id')}: undated and states no {', '.join(missing)}")
    return bad


def inv_per_book_dates_cite_their_page(ctx):
    """A date read off one book's own page names that page.

    THE BUG THIS KEEPS CATCHABLE. cmoa states ISBN 9784758062862 for える・えるシスター 1巻, and
    that ISBN is 白砂村 (7) at 一迅社. The publisher's page for it parsed, stated the ISBN asked
    about and stated a date, so every mechanical signal said the row was answered; only comparing
    the page's title against the shop's caught it. The lasting protection is not the comparison,
    which lives in the adapter, but that a reader can open the page a date came from and see for
    themselves. A date from `publisher-own-page` or `books-or-jp-registration` with no page beside
    it is a claim nobody can check.

    The bulk catalogues are exempt because they have no per-book page. `madb-tankobon` and
    `openbd-registration` name a dataset, and the dataset version is recorded with the record.

    fallback: none. The URL is what the route fetched, so its absence means the writer dropped it
    rather than a source withholding it.

    It reads `ctx` rather than the file, so `--self-test` can plant a canary in it. A check that
    opens its own file cannot be shown one, and then reports healthy without having been exercised.
    """
    cited = {"publisher-own-page", "books-or-jp-registration"}
    return [f"{w.get('shop_id')}: {w.get('first_publication_basis')} and no page cited"
            for w in ctx["cmoa_capture"]
            if w.get("first_publication_basis") in cited and not w.get("first_publication_source")]


def inv_a_stated_printing_precedes_the_delivery(ctx):
    """A printing the shop states in words cannot fall after the day it began delivering the file.

    §14b, WHAT THIS SEES THAT THE PRODUCER CANNOT. `adapters/blurbdate.py` reads a sentence in the
    description box and never opens a volume row, so 配信開始日 is a number it has no access to. This
    compares the two. A four-digit run picked out of a plot summary lands anywhere, and landing after
    the shop began selling the file is the half of "anywhere" that a machine can recognise. It caught
    nothing on the 33 rows the first pass produced, where the gaps run from six weeks to thirteen
    years, and that is the measurement rather than an assumption about the rule.

    IT IS NOT THE WHOLE CHECK ON THAT RULE, and saying so is the point of §14b. A wrong year that
    happens to precede the delivery is invisible here, which is why `test_blurbdate.py` pins the
    constructions and why the term matched is on the row for a person to read.

    COMPARED AT THE PRECISION STATED. Six of these say a year and nothing more, so `2016` is tested
    against the first four characters of the delivery date. Padding it to `2016-01-01` would invent
    a day and then test the day.

    fallback: none. Both values are in the file, so a violation is this pass having read the wrong
    number and not a source withholding one.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        import blurbdate as _b
    except Exception:                                                       # noqa: BLE001
        return []
    bad = []
    for w in ctx["cmoa_capture"]:
        if w.get("first_publication_basis") != _b.BASIS:
            continue
        stated = str(w.get("first_publication_date") or "")
        delivered = sorted(str(v.get("delivered"))[:10] for v in (w.get("volumes") or [])
                           if v.get("delivered"))
        if not stated:
            bad.append(f"{w.get('shop_id')}: basised on a stated printing and carries no date")
            continue
        if delivered and stated > delivered[0][:len(stated)]:
            bad.append(f"{w.get('shop_id')}: stated printing {stated} follows the shop's "
                       f"delivery on {delivered[0]}")
    return bad


def inv_one_row_per_identifier(ctx):
    """No two rows may carry the same work identifier.

    A merge retires an identifier and both records then resolve to the survivor. The row that each
    record produced was still emitted separately, so the works list held one work twice under one
    id, and both copies linked to the same page. 13 pairs shipped that way, every one of them a
    merge, and nothing failed because each row was individually well formed.

    An id is what an address is built from, so two rows holding one is the case where the interface
    cannot tell a reader which record they are looking at.
    """
    seen, bad = {}, []
    for r in ctx["series"]:
        wid = r.get("id")
        if not wid:
            continue
        if wid in seen:
            bad.append(f"{wid}: held by both {seen[wid]} and {r.get('work')}")
        seen[wid] = r.get("work")
    return bad


def _credit_surfaces(ctx):
    """Every spelling the credit registry answers for, folded the way its anchors are folded."""
    out = set()
    for e in (ctx["credits"] or {}).get("credits") or []:
        for a in e.get("anchors") or []:
            a = str(a or "")
            if a.startswith("credit:"):
                out.add(a[len("credit:"):])
    return out


def inv_credit_identifiers_resolve(ctx):
    """Every credit identifier in use must exist, and every retired one must reach a live one.

    AN ADDRESS PUBLISHED ONCE HAS TO KEEP RESOLVING, which is the whole reason these identifiers are
    opaque and minted. A retired one keeps `merged_into` and a stub forwards from it, so a
    `merged_into` naming an id that is not in the file, or a pair of them naming each other, is an
    address that resolves nowhere and a forwarder that cannot be written. The work registry met the
    same failure from the other side: 20 of 26 retired ids had no forwarder and twenty published
    addresses stopped working inside a day.

    It also asserts that the derived edge file only names identifiers the registry holds live, since
    an edge on a retired id is a work pointing at an address that forwards.
    """
    entries = (ctx["credits"] or {}).get("credits") or []
    by_id = {str(e.get("id")): e for e in entries if e.get("id")}
    live = {k for k, e in by_id.items() if not e.get("merged_into")}
    bad = []
    for cid, e in sorted(by_id.items()):
        target = e.get("merged_into")
        if not target:
            continue
        seen = {cid}
        while target and str(target) not in live:
            if str(target) not in by_id or str(target) in seen:
                bad.append(f"{cid} retires into {target}, which is not a live identifier")
                break
            seen.add(str(target))
            target = by_id[str(target)].get("merged_into")
        if not e.get("merge_basis"):
            bad.append(f"{cid} is retired with no basis recorded")
    for row in (ctx["credit_works"] or {}).get("credits") or []:
        if str(row.get("id")) not in live:
            bad.append(f"the edge file names {row.get('id')}, which is not a live identifier")
    return bad


# The cataloguing MADB wraps around a publisher's name. Written here as a shape and not as a list
# of role words, deliberately: `adapters/madb/extract.py` decides which words are roles, and a copy
# of its table here would report exactly what the adapter already handles and nothing else
# (STANDING-INSTRUCTIONS §14b). Any bracket in a stored publisher is a finding.
ROLE_NOTATION = re.compile(r"[\[［][^\]］]*[\]］]|[（(]\s*(?:発売|頒布|発売所|共同刊行)\s*[）)]")

# The words a Japanese source uses for this genre, in the form an imprint name is compared in.
# `adapters/classify/credence.py` holds a similar pattern for deciding what to SHOW, so the two
# overlap and can drift. What this cannot see is a label whose evidence is right and whose display
# is broken; that is credence's own to answer, and this measures the record instead.
YURI_TERM_IN_IMPRINT = re.compile(r"百合|ガールズ・?ラブ|yuri", re.I)


def inv_publisher_is_a_name_not_a_role(ctx):
    """A stored publisher must name a publisher, not the role somebody held.

    MADB writes a distributor as `[発売]講談社` and states the publisher beside it in the same
    field, and `extract.py` read the first value. 206 records therefore named 講談社 where 一迅社
    published, and the reader's per-publisher view showed 205 works under 講談社 against 20 that
    are actually its. Nothing failed: the volumes section stripped the bracket and displayed the
    same wrong name, so the page agreed with itself.

    A bracket is the whole test. It is cataloguing wherever it appears in this field, and reading
    what the bracket SAYS is the adapter's job rather than this check's, so a role the adapter
    stops recognising still shows up here.

    AND THE BLIND SPOT THAT LEAVES, which is the whole of STANDING-INSTRUCTIONS §14b. Taking the
    bracket off is precisely what the adapter does, so a check looking only for brackets cannot see
    the fault it was written for: 講談社 lifted OUT of `[発売]講談社` and stored bare is a clean
    publisher field naming the wrong party, and the first version of this check would have passed
    it for the rest of its life. The second clause measures the stored name against
    `publisher_stated`, which is the source string the record keeps beside the reading, and asks
    whether the name it stored appears in that string anywhere except inside a bracket.

    THE COUNTER-CASE, which is why the clause is not simply "the name came out of a bracket". 297
    records of release 1.2.18 name one house twice, once as the distributor and once plain:
    `["[発売]小学館", "小学館"]` is 小学館 delivering its own book. The stored name is legitimate
    there and it does come out of a bracket, so the finding needs the name to appear NOWHERE
    unbracketed.

    What neither clause can see: a name that is wrong for reasons the source string does not carry,
    and any record MADB gave a single unmarked publisher, which keeps no `publisher_stated` because
    there is nothing to dispute.

    fallback: none is possible. The name is what is published; a wrong one is served.
    """
    bad = []
    for r in ctx["madb_records"]:
        who = str(r.get("publisher") or "")
        m = ROLE_NOTATION.search(who)
        if m:
            bad.append(f"{r.get('work_id')}: publisher {who!r} holds {m.group(0)!r}")
            continue
        if who and _lifted_out_of_notation(who, str(r.get("publisher_stated") or "")):
            bad.append(f"{r.get('work_id')}: publisher {who!r} is stated only inside notation, "
                       f"in {r.get('publisher_stated')!r}")
    return bad


# One value of the source field, and the name left when the cataloguing around it is taken off.
# Neither pattern names a role: which words are roles is the adapter's decision, and a copy of its
# table here would report what the adapter already handles and nothing else (§14b).
_NOTATION_HEAD = re.compile(r"^\s*[\[［][^\]］]*[\]］]\s*")
_NOTATION_TAIL = re.compile(r"\s*[（(][^）)]*[）)]\s*$")


def _lifted_out_of_notation(who, stated):
    """Whether `who` appears in the source string only as the name inside a role marker."""
    if not stated:
        return False
    parts = [p.strip() for p in stated.split(" / ") if p.strip()]
    if who in parts:
        return False
    return any(who in (_NOTATION_HEAD.sub("", p).strip(), _NOTATION_TAIL.sub("", p).strip())
               for p in parts if _NOTATION_HEAD.match(p) or _NOTATION_TAIL.search(p))


def inv_no_html_entity_in_a_stored_name(ctx):
    """A name holding an HTML entity, which is markup that got into the data and stayed.

    A capture reads escaped text out of a page, so a title with an ampersand arrives as five
    characters that are not in its name. Nothing downstream can tell them from the name: the
    analyser read `amp` as a word and shipped `Hiyo & Amp ; Bibi to !` to readers, and the store
    was keyed on the escaped string, so it never met the same work under its real title.

    AN INVARIANT AND NOT A BUDGET. An entity in a name is always wrong, there is no quantity of it
    to work down, and the fix belongs in whichever pass wrote it.

    IT READS THE SHIPPED NAMES AND THE SERIES ROWS, not the capture that produced them, so it does
    not share the blind spot of the adapter that escaped the text (§14b). An adapter that unescapes
    correctly and a check that asks the same adapter would agree while the reader saw markup.
    """
    ent = re.compile(r"&(?:amp|lt|gt|quot|apos|nbsp|#\d+);")
    bad = []
    for kind in ("titles", "authors", "publishers"):
        bad += [f"{kind}: {k}" for k in (ctx["names_shipped"] or {}).get(kind) or {} if ent.search(k)]
    bad += [f"series: {r.get('work')}" for r in ctx["series"] if ent.search(str(r.get("work") or ""))]
    return bad


def inv_interface_folds_a_name_key_as_the_build_does(ctx):
    """The browser's fold and the build's fold, run against each other on the corpus.

    WHY THERE ARE TWO COPIES AT ALL. `data/build/feed/names.json` is keyed on the FOLDED Japanese
    string and on nothing else, so the browser has to fold a row's title the same way to find its
    rendering. `adapters/names/key.fold` is the definition and `foldKey` in `kari/app.js` is the
    same two operations in JavaScript, which cannot import it.

    WHAT A DISAGREEMENT COSTS. Not a degraded lookup: a lost one. Unlike the publisher map, which
    is keyed by the raw catalogued string as well as the normalised one so either answer finds the
    record, the title map holds the folded key alone. A browser folding differently renders
    Japanese on a work whose English this project holds, and the page says nothing about why.

    THIS USED TO READ THE SOURCE AND ASK FOR THE TWO OPERATIONS BY NAME, and said so: it could not
    run the JavaScript, so it could not see a disagreement the two implementations would only
    reveal on a particular string. It runs the JavaScript now. Every title, author and chapter name
    the corpus holds is folded both ways and the two answers are compared, so the check is over the
    strings this project actually has rather than over a regular expression matching a function
    body.

    §14b: the corpus is the input to both sides, and neither fold produced it, so this can fail on
    anything the build is able to emit. What it cannot see is a string neither collection carries.

    fallback: none. A key is either the same key on both sides or the map stops answering.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    import interface
    try:
        import key as _key
    except Exception:                                                           # noqa: BLE001
        return []
    strings = sorted({s for r in list(ctx["series"]) + list(ctx["releases"])
                      for s in (r.get("work"), (r.get("author") or "").strip(), r.get("ep"),
                                r.get("collection"), r.get("latest_ep"))
                      if s and isinstance(s, str)})
    if not strings:
        return []
    try:
        theirs = _interface(ctx).values([("foldKey", s) for s in strings])
    except interface.Unavailable as e:
        return [f"the interface could not be run, so the two folds were not compared: {e}"]
    return [f"{s[:28]}: app.js folds it {a!r} and adapters/names/key.fold folds it {b!r}"
            for s, a, b in zip(strings, theirs, (_key.fold(s) for s in strings)) if a != b]


def inv_a_record_without_a_publisher_says_why(ctx):
    """A record naming no publisher must state which kind of nothing that is.

    The fix that took the distributor out of the publisher field leaves the field empty wherever
    MADB named a distributor and nobody else, and an empty string is the shape
    STANDING-INSTRUCTIONS §5 is written about: it reads the same as a field nobody has filled in.
    `publisher_basis` carries the three answers and `adapters/madb/extract.py` documents them.

    Measured on the record and not on the adapter's own count, so a route that starts writing
    records by some other path is held to it too.

    fallback: none. A consumer that cannot tell "MADB looked and the book does not say" from "we
    have not read this yet" will guess, and guessing a publisher from an imprint is the thing the
    whole change refuses to do.
    """
    return [f"{r.get('work_id')}: no publisher and no publisher_basis"
            for r in ctx["madb_records"]
            if not str(r.get("publisher") or "").strip()
            and not str(r.get("publisher_basis") or "").strip()]


def budget_imprint_names_the_interface_disagrees_with(ctx):
    """Imprint strings the browser renders as one name and the shipped map calls another.

    THE SECOND PRODUCER, COUNTED WHILE IT LASTS. `imprintOf` in app.js decides which imprint a
    string names and `data/names/imprints.yaml` decides the same thing with a registry behind it.
    Both now read the map the build ships, so the two stopped having separate opinions, and this
    number went to zero by the disagreement ending rather than by anybody hiding it.

    IT IS MEASURED BY RUNNING `imprintOf`, not by a copy of it. This file used to hold
    `_app_imprint_of`, a transcription kept so the two could be compared, which is a comparison
    between the map and a Python function claiming to be the browser. It is now the browser.

    Counted on distinct pairs so that one wrong name does not read as hundreds.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    shipped = (ctx["names_shipped"] or {}).get("imprints") or {}
    raw = sorted({str(pr.get("imprint") or "").strip()
                  for r in ctx["series"] for pr in (r.get("print") or [])
                  if str(pr.get("imprint") or "").strip() in shipped})
    if not raw:
        return 0
    try:
        shown = _interface(ctx).labels([("imprintOf", s) for s in raw])
    except interface.Unavailable:
        return 0
    return len({(got, shipped[s]["name"]) for s, got in zip(raw, shown)
                if got != shipped[s]["name"]})


def inv_imprint_spelling_belongs_to_its_own_publisher(ctx):
    """A line's spelling may not be recorded under a house the line does not name.

    THE FAILURE THIS IS FOR. A loose match eats a real imprint, and the cheapest version of that
    mistake reaches across companies: the pattern that opened this work matched KADOKAWA's
    BRIDGE COMICS while looking for 一迅社's 百合姫 line. Matching is scoped by publisher so that
    cannot happen, and this is the statement of it that can be observed instead of assumed.

    Measured on the shipped map against the corpus, so it holds whatever produced the map. Each
    entry names the houses its line runs under; a row carrying that spelling under any other house
    is the finding. The publisher is read as the record stores it. It used to be read through this
    file's copy of a `publisherOf` in `kari/app.js` that has since been deleted there, the
    cataloguing having moved into `adapters/madb/extract.py`; `a publisher is a name, not a role`
    holds the stored string to carrying no notation, so there is nothing left here to strip.

    fallback: none. The interface would show one company's line under another company's name, and
    that is the category error the publisher pages are being built to avoid.
    """
    shipped = (ctx["names_shipped"] or {}).get("imprints")
    if not shipped:
        return []
    bad = []
    for r in ctx["series"]:
        for pr in (r.get("print") or []):
            raw = str(pr.get("imprint") or "").strip()
            fact = shipped.get(raw)
            if not fact or not fact.get("publishers"):
                continue
            pub = str(pr.get("publisher") or "").strip()
            if pub and pub not in fact["publishers"]:
                bad.append(f"{pr.get('work_id')}: {raw} is {fact['name']}'s and the row says {pub}")
    return sorted(set(bad))


def inv_first_date_precedes_its_editions(ctx):
    """A work cannot first appear after the volume that collects it was published.

    The row's date came from the platform's own chapters, which is the day it posted them. Where a
    platform re-serialises a finished title the two are years apart: ワインガールズ read
    2026-04-19 beside volumes beginning 2017-12, and 140 rows across 12 platforms sat in the recent
    end of the date sort on a date their own book run predated.

    `importdates` cannot see this. It looks for a bulk stamp, many works landing on one day, and a
    slow re-run of a single title leaves no such signature. The collected edition is the evidence,
    and it only became readable once the book runs were attached.

    A volume with no date says nothing here and is skipped, which is silence about the sources
    rather than about the work.

    A DELIVERY DATE IS NOT AN EDITION AND CANNOT TRIP THIS, deliberately. `print[].first` is a
    printing, `print[].delivered_from` is the day a shop began delivering a file, and 154 of the 353
    volumes stating both were delivered BEFORE the printing. Reading the delivery date here would
    have reported the commonest case in the shop's catalogue as a contradiction and invited someone
    to reorder dates that are not in conflict. `a delivery date never stands beside a printing` is
    the invariant that covers those rows.
    """
    bad = []
    for r in ctx["series"]:
        first = r.get("first")
        if not first:
            continue
        dates = [p.get("first") for p in (r.get("print") or []) if p.get("first")]
        if dates and min(dates)[:7] < str(first)[:7]:
            bad.append(f"{r.get('work')}: first {first} beside a volume from {min(dates)}")
    return bad


def inv_a_delivery_date_never_stands_beside_a_printing(ctx):
    """A work dated from a shop's 配信開始日 holds no publication date from anywhere else.

    THE HALF OF THE EARLIER REFUSAL THAT WAS NOT OVERRIDDEN. `adapters/cmoa_volumes.py` measured
    配信開始日 against a stated print date across 353 volumes: 154 delivered before the printing, 51
    in the same month, 45 more than three years after, the extreme 128 months. So it is not a
    publication date, not an upper bound on one and not a lower bound either. The owner's ruling of
    2026-08-08 accepts it only where NO paper record is reachable, and this is what holds that line
    once the rows are built.

    §14b, WHAT IT CAN SEE THAT THE PRODUCER CANNOT. `delivery.promote` refuses on the volumes of ONE
    source record, so a check asking the same question of the same volumes would be true by
    construction. Both halves here read further than the producer did:

    The row half reads a works-list row, where `build.py` folds print blocks from several records
    onto one identity. A retailer record dated by delivery and a bibliography record for the same
    work land on one row, and only the row can see both.

    The volume half reads the MERGED volumes, after the openBD join has had its turn. A date arriving
    through the enrichment layer never passed through `promote`. BOOK☆WALKER states no ISBN so
    nothing keys openBD from that side today, which is why this reads 0 and not why it always will.

    It is an invariant and not a budget: a printing existing beside a delivery date means one of them
    should not be in the field, which is a fault and not a quantity.

    fallback: none. Both dates are already in hand, so a violation is the merge having preferred the
    wrong one and not a source withholding anything.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        import delivery as _d
    except Exception:                                                       # noqa: BLE001
        return []
    bad = []
    for r in ctx["series"]:
        if not any(p.get("delivered_from") for p in (r.get("print") or [])):
            continue
        printed = [p.get("first") for p in (r.get("print") or []) if p.get("first")]
        if printed:
            bad.append(f"{r.get('work')}: delivery-dated beside a printing from {min(printed)}")
    for w in ctx["works"]:
        fp = w.get("first_publication") or {}
        if fp.get("date_basis") != _d.BASIS:
            continue
        dated = [v.get("published") for v in (w.get("volumes") or []) if v.get("published")]
        if dated:
            bad.append(f"{w.get('work_id')}: delivery-dated and volume {min(dated)} is printed")
        if fp.get("date_event") != _d.EVENT:
            bad.append(f"{w.get('work_id')}: delivery-dated and does not say which event")
    return bad


def _curated():
    """data/names/curated.yaml as {kind: {name: record}}, or empty where it is absent.

    Keyed `titles` and `authors` at the top level, NOT `names`. Reading it as `names` returns
    nothing and a check built on that can never fire, which is how the first attempt at this
    invariant passed while testing nothing.
    """
    import yaml as _y
    f = ROOT / "data" / "names" / "curated.yaml"
    if not f.exists():
        return {}
    doc = _y.safe_load(f.read_text()) or {}
    return {k: (doc.get(k) or {}) for k in ("titles", "authors")}


def inv_curated_values_reach_the_store(ctx):
    """A curated English name must be in the store the build reads, not only in the file it was
    written in.

    curated.yaml is the source and titles.yaml the derived state, which the module says outright.
    Editing the first without running adapters/names/curate.py leaves the site serving the old
    value with the new one committed beside it, so a diff shows a change that never shipped.

    運命のヤマダダダダダダダダダダ served "Yamada of Fate, da-da-da-daaa" for a day while
    curated.yaml said "The Yamadadadadadadadadada of Destiny". The same shape as a 単話 fix
    committed without re-running bwingest and as an emitter whose flag was never written. An edit
    to an input is not a change to the output until the step between them runs.

    Only a name the store already holds is compared. A curated entry for a work not in the corpus
    is waiting for the work, which is a different thing from a stale value.
    """
    bad = []
    for kind, rows in _curated().items():
        store = ctx["names"].get(kind) or {}
        for name, rec in rows.items():
            want = (rec or {}).get("en")
            got = (store.get(name) or {}).get("en")
            if want and got and got != want:
                bad.append(f"{kind}/{name}: curated {want!r}, store holds {got!r}")
    return bad


def inv_ruby_covers_its_surface(ctx):
    """The base text of a furigana span set must reconstruct the string it annotates.

    INDEPENDENT OF THE ALIGNER (§14b). `ruby spells the reading` asks whether the ruby spells the
    READING, using `kana.ruby_spells`, which is the function `build.py` filters with, so nothing
    reaching it can fail it. Nobody asked the other question: whether the bases still add up to the
    TITLE. A span set that drops a character, repeats one, or annotates a string it was not built
    from passes the first question and fails this one.

    Folded under NFKC, because `align` normalises before building spans while the row keeps the
    width the source used: 20 rows differ only as （私に） against (私に), which is the aligner
    working. Whitespace goes too, since a set carries separator spans the surface writes its own
    way. What survives the folding is a real difference in what the spans cover.
    """
    bad = []
    for r in ctx["series"]:
        for key, surface in (("work_en", r.get("work")), ("author_en", r.get("author"))):
            spans = (r.get(key) or {}).get("ruby")
            if not spans or not surface:
                continue
            built = "".join(str((s or [""])[0] or "") for s in spans)
            a = unicodedata.normalize("NFKC", built).replace(" ", "").replace("\u3000", "")
            b = unicodedata.normalize("NFKC", str(surface)).replace(" ", "").replace("\u3000", "")
            if a != b:
                bad.append(f"{r.get('id')} {key}: ruby covers {a[:40]!r}, surface is {b[:40]!r}")
    return bad


def inv_dates_within_a_row_are_ordered(ctx):
    """A row cannot first appear after it last appeared.

    INDEPENDENT BY CONSTRUCTION (§14b). `first date precedes its editions` tests the exact condition
    `build.py` enforces when it moves a first date back to the earliest volume, so it holds by
    construction and detects nothing. This asks what no pass enforces: that a row's own dates are in
    order. `first` is assembled from the sources and then moved back by the print run, `latest` comes
    from the serialisation, `latest_any` from whichever event is newest. Nothing makes them agree,
    and a row beginning after it ended is incoherent however it arose.

    Compared on the month, because a volume states 2024-03 where a chapter states 2024-03-18.
    """
    bad = []
    for r in ctx["series"]:
        first, latest, any_ = r.get("first"), r.get("latest"), r.get("latest_any")
        for name, later in (("latest", latest), ("latest_any", any_)):
            if first and later and str(first)[:7] > str(later)[:7]:
                bad.append(f"{r.get('id')}: first {first} after {name} {later}")
        if latest and any_ and str(latest)[:7] > str(any_)[:7]:
            bad.append(f"{r.get('id')}: latest {latest} after latest_any {any_}")
    return bad


def _divisions(reading):
    """How many pieces a reading is written in. One means it states no division."""
    return len([p for p in re.split(r"[\s　]+", str(reading or "").strip()) if p])


# The source kinds that STATE a reading, as `curate.READING_ATTRIBUTION` admits them, plus the
# artist's own surface. `analyser` is deliberately absent and `None` with it: a record that cannot
# say where its division came from has not got one from anywhere.
STATES_A_READING = ("publisher-jp", "platform", "national-library", "author", "licensor", "derived")


def inv_kana_reading_spells_its_name(ctx):
    """A name written in kana IS its reading, so the reading may not hold different kana.

    WHAT IT GUARDS, AND WHY IT IS NOT TRUE BY CONSTRUCTION. `pass1_kana` folds a kana surface to
    katakana and that half cannot fail. The half that can is a STATED reading landing on a kana
    name: a JPRO collationkey is a filing key before it is a reading and folds the kana that sort
    together, so openBD files とりいしづく under トリイ シズク and いづみやおとは under
    イズミヤ オトハ. Taking either whole republishes the artist's name with a different kana in it,
    which is one person under two spellings with nothing in the record saying they are the same.
    23 kana author names carry a reading from a source rather than from their own surface.

    Boundaries come out first, because a boundary IS admitted here and is what
    `adapters/names/boundary.py` carries onto our kana. What must not change is the spelling.

    WHAT IT THEREFORE CANNOT SEE, since §14b asks: a boundary in the wrong PLACE. Nothing mechanical
    can, which is why only a stated one is ever taken.

    Authors only. A title's reading legitimately differs from its surface, because は is written as
    the topic particle and read ワ: 7 kana titles are in that state and every one of them is right.

    fallback: none. A misspelt name is served under the artist's own work.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import kana
    except Exception:
        return []
    strip = str.maketrans("", "", " 　")
    bad = []
    for k, v in (ctx["names"].get("authors") or {}).items():
        rd = v.get("reading")
        if not rd or not kana.kana_only(k):
            continue
        want = unicodedata.normalize("NFC", kana.to_katakana(k)).translate(strip)
        got = unicodedata.normalize("NFC", kana.to_katakana(rd)).translate(strip)
        if want != got:
            bad.append(f"{k}: reading {rd!r} spells {got[:24]!r}")
    return bad


def inv_a_division_cites_its_source(ctx):
    """A division a name does not itself write has to say where it came from.

    THIS IS WHAT STOPS THE BOUNDARY PASS BECOMING A GUESSER. `adapters/names/boundary.py` will only
    carry a division some record states, and the way to be sure it stays that way is not to read the
    module: it is to require every division in the store to name its origin. A record that acquired
    one from an analyser, a surname lexicon or somebody's intuition has nothing to put here and
    fails the gate.

    AN ANALYSER DIVIDES EVERY NAME IT IS GIVEN, so its answer is a citation of nothing. It is also
    at its weakest on exactly these: 331 kana names carried its answer, and
    よつば◎ますみ。 came back ヨツバ ◎ マスミ。 with the kana untouched and a division nobody stated.
    `madb_reading.py` refuses to publish an analyser's boundary under a catalogue's name for the
    same reason, at length. So the source has to be one that states readings.

    くわばら たもつ writes its own division and needs no citation, which is why the surface is
    counted rather than assumed to have none.

    fallback: none. A guessed division reads as a fact about a real person's name.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import kana
    except Exception:
        return []
    bad = []
    for k, v in (ctx["names"].get("authors") or {}).items():
        rd = v.get("reading")
        if not rd or not kana.kana_only(k):
            continue
        if _divisions(rd) <= _divisions(k):
            continue
        if v.get("reading_boundary") or v.get("reading_source_kind") in STATES_A_READING:
            continue
        bad.append(f"{k}: divided as {rd!r} with nothing saying who divided it")
    return bad


def inv_nicovideo_channel_agrees(ctx):
    """The channel a ニコニコ work is filed under, against the channel we recorded ourselves.

    THE FAULT. `adapters/nicovideo/releases.py` read the channel from the first `/official/` link
    in the page, and that link is the opening banner of the sidebar, which is the same on every
    page of the site. All 180 works read `nicomanga`, including the 32 the breadcrumb puts on
    きららベース. It stood for six days, from the day the platform was onboarded, because nothing
    read the field.

    WHY THIS MEASURE AND NOT THE PARSER'S (§14b). Asking the pages again would ask the code that
    was wrong. `data/source/nicovideo/resolved.yaml` and `data/source/webpages/nicovideo-titles.yaml`
    state the channel for the works whose identity was settled by hand, and the adapter reads
    neither: it takes `comic_id` out of the first and nothing at all out of the second. So this
    compares two independent records of one fact, which is §3's invariant rather than a second
    opinion from the same source.

    WHAT IT CANNOT SEE, said here because a check that does not name its blind spot grows one.
    Only four works carry a channel we recorded by hand, so 157 of the 161 are unexamined by the
    comparison. The second clause covers the specific way this failed: a value read from something
    that does not vary by page is the SAME for every work, and that is arithmetic on the output
    owing nothing to the parser. It would have caught the original fault on its own.

    Zero comparisons is a violation and not a pass. A check that quietly stopped matching anything
    reports exactly as clean as one that ran (§4).

    fallback: keep ニコニコ漫画 as the platform and drop the channel. A channel is where within a
    platform a work sits, so losing it costs a qualifier; getting it wrong files the work under a
    publisher it has nothing to do with.
    """
    rows = ctx["nicovideo_channels"]
    if not rows:
        return []
    recorded = ctx["nicovideo_recorded_channels"]
    bad, compared = [], 0
    for r in rows:
        want = recorded.get(str(r.get("comic_id") or ""))
        if not want:
            continue
        compared += 1
        got = r.get("channel")
        if got != want:
            bad.append(f"{r.get('work_title')}: recorded as {want}, "
                       f"the platform page reads {got or 'no channel'}")
    if not compared:
        bad.append(f"{len(rows)} ニコニコ work(s) and not one channel recorded to compare against; "
                   "the comparison this check makes is no longer being made")
    # No floor under this. The adapter refuses to write a file holding fewer than 20 works, so
    # a population that has collapsed to one channel is a fault however few rows carry one.
    channels = {r.get("channel") for r in rows if r.get("channel")}
    if len(channels) == 1:
        bad.append(f"every ニコニコ channel we hold reads {next(iter(channels))}, which is what a "
                   "value taken from an element that does not vary by page looks like")
    return bad



def inv_a_shipped_identifier_resolves(ctx):
    """A name the interface can link must link to a record that exists.

    THE FOLD IS THE FAILURE MODE AND IT IS SILENT. `feed/names.json` is keyed by a name folded NFKC
    with spaces removed, and the anchors the identifiers were minted under are folded the same way
    on purpose: `credit_identity.credit_key` and `publisher_identity.house_key` each say so in a
    docstring, which is three copies of one rule. §3 is what happens next. A drift does not raise
    anything: it puts an id on a name whose record the page data no longer holds, and a reader
    clicking a credit lands on a page that renders nothing.

    IT ASSERTS BOTH DIRECTIONS OF THE JOIN. An id on a name that no record answers for is a dead
    link; a record whose page the deploy will write is fine on its own, because the registry is
    append-only and legitimately holds credits nothing currently names.

    WHAT IT SHARES AND THEREFORE CANNOT SEE (§14b). Both sides come out of one build, so it cannot
    tell whether the id is the RIGHT record: a fold that mapped every credit to c00001 consistently
    would pass here. `credit pages listing a work that does not name them` is the measure for that,
    and it reads the credit field as a string and consults no fold at all.

    fallback: the name renders as it always did and is not a link.
    """
    bad = []
    shipped = ctx["names_shipped"] or {}
    for kind, doc, key in (("authors", ctx["credit_pages"], "credits"),
                           ("publishers", ctx["publisher_pages"], "publishers")):
        have = set((doc or {}).get(key) or {})
        if not have:
            continue
        for name, rec in sorted((shipped.get(kind) or {}).items()):
            got = (rec or {}).get("id")
            if got and str(got) not in have:
                bad.append(f"{kind}:{name[:24]} links {got}, which no record answers for")
    return bad


def _role_vocabulary(ctx):
    """Every role string a credit field can state, from the splitter and from the corpus.

    BOTH, BECAUSE NEITHER IS THE WHOLE ANSWER. `inputs.ROLES` is what the splitter will recognise
    and so is what it can hand the interface tomorrow; the corpus is what it hands it today, and it
    states compounds that no list holds, because they are built rather than written down:
    `キャラクター原案・漫画` and `原作監修・文` are two roles joined by the field that wrote them.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    from names import creditline, inputs
    fields = [str((r.get("c") or "")) for r in ctx["index"]]
    fields += [str((w.get("creator") or "")) for w in ctx["works"]]
    fields += [str((r.get("author") or "")) for r in ctx["series"]]
    fields += [str((r.get("author") or "")) for r in ctx["releases"]]
    stated = set(creditline.roles_stated([f for f in fields if f]))
    stated |= {r for e in ((ctx["credit_pages"] or {}).get("credits") or {}).values()
               for w in (e.get("works") or []) for r in (w.get("roles") or [])}
    return sorted(stated | set(inputs.ROLES) | set(inputs.BRACKET_ROLES))


def inv_every_credit_role_has_an_english_gloss(ctx):
    """Every job a credit can state comes out of the interface in English.

    WHY THIS IS AN INVARIANT AND NOT A COUNT. A role is a closed vocabulary somebody wrote down, so
    a role with no gloss is a missing table entry and not a name nobody has researched. That is the
    difference between this and `renderings still Japanese in English mode`, which counts names
    §6 leaves standing and cannot go to zero until somebody has looked names up.

    236 catalogue credit lines were in Japanese under an English heading and the largest single
    cause was this: `ROLE_EN` in kari/app.js held six words and a second table further down the
    same file held twenty more, so キャラクターデザイン was English on a credit page and Japanese on
    the catalogue tab. Neither knew about 校正, 編纂, カバーイラスト or ほか著.

    §14b, WHAT IT SHARES AND WHAT IT THEREFORE CANNOT SEE. The vocabulary comes from the PYTHON
    splitter and from the corpus; the gloss comes from the JavaScript table. Nothing produces both,
    so the two can disagree and this is where they do. What it cannot see is a role the splitter
    fails to recognise at all, which is not a gloss problem: that role never becomes a role, and it
    shows up as notation surviving into a rendering, which the check below is for.

    fallback: the role shows as the source wrote it, which is the fallback every name takes.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    roles = _role_vocabulary(ctx)
    if not roles:
        return ["no role vocabulary was collected, so nothing here was checked"]
    try:
        shown = _interface(ctx).labels([("roleWord", r) for r in roles])
    except interface.Unavailable as e:
        return [f"the interface could not be run, so nothing here was checked: {e}"]
    return [f"{r} has no English gloss in kari/app.js"
            for r, out in zip(roles, shown) if interface.KANA_KANJI.search(out)]


def _notation_left(ctx):
    """`[(surface, value, the notation that survived)]` over every rendering.

    THE OUTPUT MEASURED AGAINST A VOCABULARY THE RENDERER NEVER CONSULTED (§14b). The roles come
    from the Python splitter and the words below are the ones the splitter drops; kari/app.js has
    its own table and its own division, and neither of them is asked here. A role the interface
    glosses cannot appear in the output, so anything that does is a role the DIVISION did not find
    or a gloss that did not reach the page, and those are exactly the two ways this class comes
    back.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    roles = [r for r in _role_vocabulary(ctx) if interface.KANA_KANJI.search(r)]
    # `ほか` closes a credit that names some of its contributors; the interface says "and others".
    # Neither is a name, and a reader in English has no way to read either as one.
    words = sorted(set(roles) | {"ほか"}, key=len, reverse=True)
    calls, about = interface.calls_for(_collections(ctx))
    if not calls:
        return []
    out = _interface(ctx).labels(calls)
    bad = []
    for (surface, value), shown in zip(about, out):
        if surface.category not in ("person", "role"):
            continue
        for word in words:
            # DELIMITED, because a role word is also an ordinary word and pen names are built out
            # of ordinary words. 文 sits inside 文尾文 and 作 inside 佐喜ハジメ's neighbours; what
            # makes an occurrence notation is that a bracket or a separator stands either side.
            if re.search(r"(?:^|[\s\u3000\[\](){}（）〔〕【】/／、,，・･&＆:：])"
                         + re.escape(word)
                         + r"(?:$|[\s\u3000\[\](){}（）〔〕【】/／、,，・･&＆:：])", shown):
                bad.append((surface, value, word))
                break
    return bad


def inv_no_cataloguing_notation_in_an_english_rendering(ctx):
    """A credit line in English holds names and nothing else the catalogue wrote around them.

    WHAT THIS BLOCKS THAT A BUDGET TOLERATED. `renderings still Japanese in English mode` counts a
    row as one number whatever is Japanese about it, so a role nobody glossed and a pen name nobody
    has researched were the same event. They are not: §6 says a name with no rendering shows as the
    Japanese and calls that finished, and it says nothing of the kind about `[キャラクター
    デザイン]`, `(校正)`, `ほか` or a reading printed beside the name it reads. Those are the
    catalogue's notation, they have a right answer, and once the answer exists nothing should be
    able to lose it quietly.

    So the guarantee splits. This holds at zero and blocks; the budget keeps the names.

    fallback: the notation shows as the catalogue wrote it, which is what it did before.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    try:
        return sorted({f"{s.path}:{v[:32]} still shows {w}" for s, v, w in _notation_left(ctx)})
    except interface.Unavailable as e:
        return [f"the interface could not be run, so nothing here was checked: {e}"]


def inv_status_page_shows_no_japanese_of_its_own(ctx):
    """status.html in English says nothing in Japanese except the rows it is reporting on.

    THE PAGE FOR FACTS ABOUT US IS STILL A PAGE. §1 puts coverage and backlog here rather than in
    front of a reader, and nothing had ever asked it what it renders: `app-status.js` builds every
    sentence out of `T('日本語', 'English')` pairs, and a pair whose Japanese half contains a bare
    ` / ` loses its own numbers, which happened once and was fixed by hand.

    THE DATA IT REPORTS IS ANOTHER MATTER AND IS NOT EXCUSED, IT IS RULED. `outstanding[].rows[]`
    is the list of works with no English name; naming them in English is the thing that queue
    exists to do, so the Japanese in it is the subject rather than a failure to render. Those
    values are ruled in `interface.NOT_A_NAME` and are recognised HERE by being the values
    themselves, not by the check looking away from a region of the page.

    fallback: none. This reads a file in another repository and cannot degrade a build.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    iface = _status_interface(ctx)
    doc = ctx.get("status") or {}
    if not iface or not doc:
        return []
    sections = ["lastRun", "connectors", "outstanding", "stats", "gate"]
    try:
        shown = iface.labels([(fn, doc) for fn in sections])
    except interface.Unavailable as e:
        return [f"status.html could not be run, so nothing here was checked: {e}"]
    ruled = {str(v) for row in (doc.get("outstanding") or [])
             for v in (row.get("rows") or []) if isinstance(v, str)}
    ruled |= {str(b.get("means") or "") for b in ((doc.get("gate") or {}).get("budgets") or [])}
    bad = []
    for name, text in zip(sections, shown):
        for run in set(re.findall(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff]+", text)):
            if any(run in v for v in ruled):
                continue
            bad.append(f"status.html:{name} shows {run} in English mode")
    return sorted(set(bad))


INVARIANTS = [
    ("ruby covers its surface", inv_ruby_covers_its_surface),
    ("a kana name's reading spells it", inv_kana_reading_spells_its_name),
    ("a division cites its source", inv_a_division_cites_its_source),
    ("dates within a row are ordered", inv_dates_within_a_row_are_ordered),
    ("curated values reach the store", inv_curated_values_reach_the_store),
    ("ruby spells the reading", inv_ruby_spells_reading),
    ("one row per identifier", inv_one_row_per_identifier),
    ("every credit identifier resolves", inv_credit_identifiers_resolve),
    ("a shipped identifier resolves", inv_a_shipped_identifier_resolves),
    ("first date precedes its editions", inv_first_date_precedes_its_editions),
    ("no ruby over bare Latin", inv_no_ruby_over_latin),
    ("feed holds only attested rows", inv_feed_is_attested),
    ("every update has a kind", inv_no_unknown_kind),
    ("readings are stored as kana", inv_readings_are_kana),
    ("a reading can show its source", inv_reading_can_show_its_source),
    ("English mode has no Japanese", inv_english_mode_has_no_japanese),
    ("every credit role has an English gloss", inv_every_credit_role_has_an_english_gloss),
    ("no cataloguing notation in an English rendering",
     inv_no_cataloguing_notation_in_an_english_rendering),
    ("status.html shows no Japanese of its own",
     inv_status_page_shows_no_japanese_of_its_own),
    ("no build-machine paths in published files", inv_no_absolute_paths_in_published_files),
    ("no stock phrasing in public text", inv_no_stock_phrasing_in_public_text),
    ("content flags are accounted for", inv_content_flags_are_accounted_for),
    ("archives are unchanged", inv_archives_unchanged),
    ("deployed data matches built", inv_deployed_matches_built),
    ("no refutation of print serials", inv_no_refutation_of_print_serials),
    ("state agrees with its own date", inv_state_agrees_with_its_own_date),
    ("undated works say where and why", inv_undated_works_say_where_and_why),
    ("a delivery date never stands beside a printing",
     inv_a_delivery_date_never_stands_beside_a_printing),
    ("per-book dates cite their page", inv_per_book_dates_cite_their_page),
    ("a stated printing precedes the delivery", inv_a_stated_printing_precedes_the_delivery),
    ("a publisher is a name, not a role", inv_publisher_is_a_name_not_a_role),
    ("a record without a publisher says why", inv_a_record_without_a_publisher_says_why),
    ("an imprint spelling belongs to its own publisher",
     inv_imprint_spelling_belongs_to_its_own_publisher),
    ("no HTML entity in a stored name", inv_no_html_entity_in_a_stored_name),
    ("nicovideo channels agree with our own records", inv_nicovideo_channel_agrees),
    ("a fixture states where it came from", inv_fixture_states_where_it_came_from),
    ("the interface folds a name key as the build does",
     inv_interface_folds_a_name_key_as_the_build_does),
    ("names reach a page only through their renderer",
     inv_names_reach_a_page_only_through_their_renderer),
    ("every Japanese field the data carries has a ruling",
     inv_every_japanese_field_has_a_ruling),
]


# ── Tier 2: budgets ───────────────────────────────────────────────────────────────────────────
#
# Counts with no correct value, only a direction. The recorded budget is whatever was last
# measured on a green run; it tightens automatically and loosens only by hand.

def budget_uncertain_readings(ctx):
    return sum(1 for kind in ("titles", "authors")
               for v in (ctx["names"].get(kind) or {}).values() if v.get("reading_uncertain"))


def budget_works_without_english(ctx):
    return sum(1 for r in ctx["series"]
               if not (r.get("work_en") or {}).get("en")
               and not (r.get("work_en") or {}).get("romaji"))


def budget_works_without_an_english_name(ctx):
    """Works that show a romanisation where an English name should be.

    THIS IS NOT the budget above, and the difference is the whole point. That one counts works
    that would render in JAPANESE in English-only mode, and a romanisation satisfies it, so it
    read 0 while 929 of 1,074 titles said nothing at all to a reader who wants to know what a
    work is. The number was right about what it measured and useless for the question anybody
    would ask of it, which is this project's characteristic failure moved up into the metrics.

    A romanisation is a finished answer for a coinage, a portmanteau of two characters' names, or
    a title that is already a name. It is not a finished answer for あなたのとなり, which is four
    kana meaning next to you. Nothing here can tell those apart, so the count includes both and
    comes down as titles are reviewed rather than to zero.
    """
    return sum(1 for r in ctx["series"]
               if (r.get("work_en") or {}).get("basis") not in ("official-jp", "licensed",
                                                                "translated"))


def _shipped_lists(ctx):
    """The lists a build publishes, as (name, [(title, credit)]).

    EVERY SURFACE SEPARATELY, which is STANDING-INSTRUCTIONS §13's rule and the reason these are
    kept apart instead of pooled. Five titles reached the public site through six paths and each was
    found only after the previous fix appeared to have worked. A list is a surface; a work offered
    twice on two of them is two faults and is counted twice here on purpose.
    """
    return [
        ("index", [(str(r.get("t") or ""), str(r.get("c") or "")) for r in ctx["index"]]),
        ("series", [(str(r.get("work") or ""), str(r.get("author") or "")) for r in ctx["series"]]),
    ]


def budget_works_offered_twice(ctx):
    """Rows beyond the first that a shipped list gives to one identity work.

    THE CLASS. `index.json` emitted one row per SOURCE RECORD, and the national bibliography holds
    several records for one book run, so 41 works were offered twice or three times: ゆるゆり and
    citrus split by two spellings of one imprint, 紅殻のパンドラ split where the run continues under
    a subtitle, and `School zone = スクールゾーン` beside `スクールゾーン` because one record carried
    the whole ISBD line as its name. `build.one_row_per_work` collapses them through the identity
    registry, keeping every record's identifier on the row so no published address stops resolving.

    WHAT THIS CAN AND CANNOT SEE (§14b). It asks the identity registry, and both producers now ask
    the identity registry, so it is close to true by construction: `one_row_per_work` groups on the
    answer this verifies with, and the works list folds print records on the same lookup. What it
    therefore catches is a collapse that stops running, and a NEW list that ships without asking
    identity at all, which is how this arrived. What it cannot catch is two records of one work the
    registry never joined, because both then look like separate works to it and to the producer
    alike. `one work under two names in a list` is the measure for that, and it owes the registry
    nothing.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import identity

    reg = ctx["identity"]
    byanchor = identity.index(reg)
    extra = 0
    for _name, rows in [("index", ctx["index"]), ("series", ctx["series"])]:
        seen = collections.Counter()
        for r in rows:
            # Every record the row stands for. An index row carries `ids` since the collapse; a
            # works-list row carries its print records, and either can be several.
            ids = (r.get("ids") or ([r["id"]] if r.get("id") and _name == "index" else [])
                   or [p.get("work_id") for p in (r.get("print") or [])])
            for wid in {byanchor.get(identity.print_anchor(i)) for i in ids if i}:
                if wid:
                    seen[wid] += 1
        extra += sum(n - 1 for n in seen.values() if n > 1)
    return extra


def budget_one_work_under_two_names(ctx):
    """Pairs of rows in one shipped list that name one work twice, on the rows' own evidence.

    WHAT IT MEASURES. Two rows whose titles fold equal and whose credits share a person. Folding
    removes width, spacing, decorative punctuation and bracketed matter, so 【合本版】, 【電子単行本】
    and （英語版） fold away and a work sold in a collected edition beside its volumes lands here:
    DEFINITIONS §7 says the test binds the work and not the edition, so that is one work with two
    rows. Sharing a person is what keeps 人魚姫 apart from the seven other 人魚姫, and it is the same
    evidence the identity registry requires before joining anything.

    WHY IT DOES NOT SHARE THE PRODUCER'S BLIND SPOT (§14b). It never opens the identity registry. It
    compares the rows a reader is served against each other, so the pairs it reports are exactly the
    ones the registry has NOT joined, which is the population `works offered twice in a list` is
    structurally unable to see. The reverse is also true and both are kept: a collapse that stops
    running produces rows this cannot tell apart from two works, because their titles then agree and
    it would count them as a pair, which is right, and it says nothing about why.

    WHICH FOLD, AND WHY NOT THE RENDERER'S. `names/key.fold` is the key the interface looks a
    RENDERING up under, and a measure about renderings has to use it or it reports a number the page
    contradicts. This asks a different question, so it uses `identity.fold`, which is the project's
    answer to whether two records are the same WORK and is the more aggressive of the two: it strips
    every space that one does, and bracketed matter besides. So every pair the interface's fold
    would join is joined here as well, and this cannot under-report against what a reader sees.

    IT IS A QUEUE AND NOT A FAULT COUNT. Every pair needs somebody to decide whether it is one work,
    a reissue under another name, or two works an author gave one title. リリウム・テラリウム and
    くちびるためいきさくらいろ appear twice each and look like the first; 少女² 完全版 beside 少女²
    is the second. Nothing here decides, and a fall in the number has to come from deciding rather
    than from tightening the fold.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import identity

    pairs = 0
    for _name, rows in _shipped_lists(ctx):
        by = collections.defaultdict(list)
        for title, credit in rows:
            if title:
                by[identity.fold(title)].append(credit)
        for key, credits in by.items():
            if not key or len(credits) < 2:
                continue
            who = [identity.people(c) for c in credits]
            pairs += sum(1 for i in range(len(who)) for j in range(i + 1, len(who))
                         if who[i] & who[j])
    return pairs


def budget_incomplete_attested_rows(ctx):
    return sum(1 for r in ctx["releases"]
               if r.get("provenance") == "attested"
               and (not (r.get("ep") or "").strip() or not r.get("author")
                    or not r.get("access_modes")))


def budget_stock_phrasing_in_comments(ctx):
    try:
        files = [str(f) for f in list(ROOT.rglob("*.py")) + list(ROOT.rglob("*.md"))
                 if ".git" not in f.parts and "data" not in f.parts]
        out = subprocess.run(
            [sys.executable, str(ROOT / "adapters" / "lint" / "tics.py"), "--comments",
             "--quiet", *files], capture_output=True, text=True, timeout=120)
        return int(out.stdout.strip() or 0)
    except Exception:
        return 0


def budget_untested_modules(ctx):
    """Modules with no test at all. The count the goal drives down.

    Counted by ./test.py, which discovers rather than being told, so this cannot be satisfied by
    forgetting to register something. A module counts as covered when a test names it in COVERS,
    when a test sits beside it under the naming convention, or when it carries its own --self-test.
    """
    try:
        out = subprocess.run([sys.executable, str(ROOT / "test.py"), "--quiet"],
                             capture_output=True, text=True, timeout=120)
        return int(out.stdout.strip() or 0)
    except Exception:
        return 0


def budget_invented_markup_in_tests(ctx):
    """String literals in tests that are shaped like a page and came from nobody's page.

    A test can only exercise a parser against markup somebody wrote down, and until
    `data/fixtures/` existed the only place to write it was the test file. Three faults came out of
    that in one round, the ニコニコ sidebar being the expensive one: the pattern read a real
    element correctly and the element was the wrong one, and the invented page did not contain the
    element it should have preferred.

    WHAT COUNTS. A literal of 200 characters or more holding both `<` and `>`. The threshold is
    doing real work rather than rounding: `<div class="meta_info">2026年8月3日更新</div>` is 45
    characters, states one parsing rule, and belongs in the test where a reader sees the rule and
    its input together. A 700-character block with a breadcrumb and a sidebar in it is impersonating
    a page, and the page is on disk in a cache.

    MEASURED ON THE TEST FILES AND NOT ON THE FIXTURE LIBRARY, which is the point (§14b). Counting
    fixtures would rise as the work got done and would say nothing about the tests that never
    converted. This falls only when a literal is replaced by a capture, and it does not reach zero
    on its own: several of these are JSON payloads and feed bodies for platforms whose pages nobody
    has cached.
    """
    n = 0
    for f in sorted(ROOT.glob("**/test_*.py")) + sorted(ROOT.glob("**/*_test.py")):
        if ".git" in f.parts or "data" in f.parts:
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and len(node.value) >= 200 and "<" in node.value and ">" in node.value
                    and not (ast.get_docstring(tree) == node.value)):
                n += 1
    return n


def budget_nicovideo_works_with_no_rights(ctx):
    """ニコニコ works captured with no copyright line read off their page.

    THE FAULT THIS COUNTS. `rights` matched `<small class="copyright">(C)` and nothing else. Of the
    157 cached work pages carrying the line, 101 open with something the pattern could not read: ©
    bare, © with the emoji variation selector, Ⓒ, （C）and (ｃ) in fullwidth, &copy with no
    semicolon, one @, and three that end the line with `<br />` so the element did not match at
    all. Every one of those returned [], which is indistinguishable from a page stating no rights
    (§5), and this is the only field on the platform that names a PUBLISHER.

    MEASURED ON THE CAPTURED ROWS, which owe nothing to the pattern (§14b): the check asks whether
    a row carries the field, and the producer never asks that question. A budget rather than an
    invariant because it does not reach zero. A work its own author posted carries no copyright
    element at all, and 19 of the works here are in that position.
    """
    rows = (_yaml(ROOT / "data" / "source" / "nicovideo" / "works.yaml", {}) or {}).get("works")
    return sum(1 for w in (rows or []) if not w.get("rights"))


def budget_unguarded_captures(ctx):
    """Adapters that fetch from a host, write into data/source, and have no floor to refuse on.

    A host that is down or serving nonsense is not a rare event, and an adapter without a floor
    writes whatever it got over the last good capture. Half of them do refuse: comicboost exits on
    "no series returned chapters", comicfuz on a work count below its minimum. The rest would
    happily replace 1,952 chapters with nothing and report success.

    This is the prevention half of GAPS §8. adapters/ledger.py is the detection half and reports
    the damage after the fact; a floor stops it happening. A count, so it ratchets down.
    """
    import re as _re
    n = 0
    for f in sorted(ROOT.glob("adapters/**/*.py")):
        if f.name.startswith("test_") or f.name == "testkit.py":
            continue
        try:
            src = f.read_text()
        except Exception:                                                   # noqa: BLE001
            continue
        fetches = "urllib.request" in src or "urlopen(" in src
        writes = "data/source" in src
        guarded = bool(_re.search(r"Refusing to write|HEALTH:", src))
        if fetches and writes and not guarded:
            n += 1
    return n


def budget_adapters_fetching_without_net(ctx):
    """Adapters that open a URL themselves instead of going through adapters/net.py.

    WHAT EACH ONE COSTS. net.py holds four things a hand-rolled fetch does not: the pause is owed
    per host, so 27 hosts do not queue behind one; the status code survives, so a 404 and a 503 are
    different events; the final URL comes back, so a work that moved is visible; and a 503 is
    retried with a backoff every worker on that host pays. A module with its own urlopen has none
    of them, and the ones this project spends the most time in were exactly the holdouts.

    IT COUNTS THE CALL AND NOT THE IMPORT. `editions/capture.py` imports net for its pause, its key
    and its outcome handling, and still calls urlopen once for the one route that needs an extra
    header. That is a considered exception and it is still counted, because the number is "how much
    fetching happens outside the shared path" and a partial migration is partly outside it.

    net.py itself is not counted, and neither is the resolver's HttpCache: `names/resolver.py` is
    the four numbered name passes' own transport, with a journal and an offline mode net.py does
    not have, and folding it in is a separate job from this one.
    """
    exempt = {"net.py", "resolver.py"}
    n = 0
    for f in sorted(ROOT.glob("adapters/**/*.py")):
        if f.name.startswith("test_") or f.name in exempt:
            continue
        try:
            src = f.read_text()
        except Exception:                                                   # noqa: BLE001
            continue
        if "urlopen(" in src:
            n += 1
    return n


def budget_structural_triples(ctx):
    """Three used as an organising shape in documents that ship at 1.0.

    Public prose is the invariant. This is the backlog in the internal documents, which become
    public at 1.0 and so need the same pass. A count, so it ratchets down instead of blocking.
    """
    try:
        files = [str(f) for f in sorted(ROOT.rglob("*.md"))
                 if ".git" not in f.parts and "data" not in f.parts]
        out = subprocess.run(
            [sys.executable, str(ROOT / "adapters" / "lint" / "tics.py"), "--prose", *files],
            capture_output=True, text=True, timeout=120)
        return sum(1 for l in out.stdout.splitlines() if l.startswith("STRUCTURE:"))
    except Exception:
        return 0


def budget_scraped_counters_in_chapter_names(ctx):
    """Chapter names ending in the like and comment counts the source page printed beside them.

    193 of these were stored as chapter names: '3話① 26 8' on マンガPark, '第4話 3,203 3' on
    コロコロオンライン. The extraction flattened a chapter's block into one run of text, so a count
    written in an element of its own ran into the name next to it.

    Counted where a reader meets a chapter name, which is the feed's own `ep` and each series'
    latest chapter. That is narrower than the source files hold, and deliberately: it is the
    number that says how many damaged names are on the page rather than in the data.

    It is a count rather than an invariant because a chapter name may legitimately end in a
    number. pixivコミック numbers its chapters EPISODE 01 to EPISODE 30. So the shape measured is
    the narrow one that cannot be a name: two bare numbers, separated by a space, at the end.
    """
    pat = re.compile(r"\s\d[\d,]*\s+\d[\d,]*$")
    names = [r.get("ep") or "" for r in ctx["releases"]]
    names += [r.get("latest_ep") or "" for r in ctx["series"]]
    return sum(1 for n in names if pat.search(n))


def budget_unreadable_bookwalker_rows(ctx):
    """Rows admitted from BOOK☆WALKER that still cannot become work records.

    THIS IS THE CONSUMER FOR data/queue/bookwalker-volumes.yaml, and it exists because a produced
    file with no consumer reads as done while doing nothing (STANDING-INSTRUCTIONS §13).

    WHAT MAKES A ROW READABLE IS A VENUE, NOT A DATE. §6 was amended on 2026-08-05: the scope test
    turns on WHERE a work was first published, and a work that exists is recorded whether or not
    anyone can date it, with the absence stated as `first_publication.date_basis`. So this counts
    rows with no venue, which is rows nobody has fetched yet plus the few whose series page listed
    nothing readable. Counting undated rows instead would park this number near 1,500 for ever and
    report finished work as a debt, because 1,500 of these titles are digital-only and have no
    print edition anywhere to carry a date.

    ONE BUDGET PER SHOP, not one over both. `undated cmoa candidates` counts the other half of the
    same queue. Folding cmoa's 1,844 rows into this number would have read as the budget loosening
    by 1,839 on the day the second capture started, which is a ratchet saying nothing about either
    shop.

    A count, so it ratchets down, and unlike the date it really does reach zero when the capture
    completes.
    """
    return _retailer_rows("data/queue/bookwalker-volumes.yaml", "bookwalker.jp", "venue")


def budget_undated_cmoa_candidates(ctx):
    """The same count for data/queue/cmoa-volumes.yaml, which is its named consumer.

    cmoa's silences differ from BOOK☆WALKER's and the file distinguishes them: an ISBN openBD does
    not hold is reachable through another catalogue, while a title with no print edition has no
    ISBN to reach it with. Neither shows up here, which is why the basis is in the file.

    IT FELL FROM 1,220 TO 11 ON 2026-08-08, AND WHAT IT MEASURES CHANGED WITH IT. The owner's ruling
    of that day dates a digital-only row from the shop's own 配信開始日, so the 1,209 rows this
    counted are answered. What is left is rows nothing has captured, which really does reach zero
    when the capture finishes.

    THE RISK IN A NUMBER THIS SMALL. This counts ADMITTED rows against captured ones, so a fresh
    shelf capture admitting a dozen titles blows a budget of 11 before anyone has fetched a page,
    for a rise nobody caused. That is a budget doing its job badly and it is worth raising with a
    recorded reason instead of being worked around.
    """
    return _undated_retailer_rows("data/queue/cmoa-volumes.yaml", "cmoa.jp")


def budget_volumes_with_an_isbn_and_no_date(ctx):
    """Volumes a reader is shown that state an ISBN and carry no publication date.

    An ISBN encodes no date and it is a key into registries that state one, so a volume holding an
    ISBN and no date is a lookup nobody has done. This is the gap `adapters/isbndate.py` closes and
    the number that keeps it visible after it has been closed once.

    §14b, WHAT IT IS MEASURED OVER. The built works and not `data/source/madb/`, where the gap was
    found. Counting the source records would leave this reporting 26 for ever, because the answer
    lands in the enrichment layer and the merge is what brings the two together; the check would
    have been blind in exactly the place the fix works. Over the built rows it falls when a reader
    would see a date and rises when one stops reaching the page, whichever route supplied it.

    Its floor is not zero. openBD held no record at all for 245 of the corpus's 2,321 ISBNs, and
    for a book nobody registered there is nothing to look up.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        import isbndate
    except Exception:                                                       # noqa: BLE001
        return 0
    return len(isbndate.undated_isbn_volumes(ctx["works"]))


def budget_bookwalker_series_unread(ctx):
    """BOOK☆WALKER rows whose series listing nobody has read to the end.

    THIS IS A DATING MEASURE AND NOT A TIDINESS ONE. `first_publication` for these rows is the
    earliest 底本発行日 across the volumes the capture read, so a work read at one volume has its
    first publication chosen from a sample of one, and a work read at 60 of 133 from a truncated
    one. The count is too low in a way anybody can see; the date is wrong in a way nobody can.

    It counts two things that both mean the same request. 1,175 rows were captured from a
    `/de<uuid>/` link the shelf gave, so their series page was never opened at all, and 931 of them
    name a series id nothing followed. A further handful were read at exactly the listing's page
    size, before this module knew the listing paginates.

    `adapters/recon/bookwalker_volumes.py --follow-series` works through them and the number
    reaches zero when it finishes, because every row here has a series id to fetch. Rows naming no
    series are not counted: the shop states none for a standalone volume, which is an answer.
    """
    from adapters import captures as _cap

    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        from recon import bookwalker_volumes as _bv
        doc = _cap.load(ROOT / "data/queue/bookwalker-volumes.yaml")
    except Exception:                                                       # noqa: BLE001
        return 0
    works = {str(w["shop_id"]): w for w in (doc.get("works") or []) if w.get("shop_id")}
    return len(_bv.series_to_follow(works))


def budget_bookwalker_listings_unconfirmed(ctx):
    """BOOK☆WALKER rows whose series listing nothing ever checked against the shop's own count.

    A SEPARATE BUDGET FROM `bookwalker series unread`, for the same reason cmoa has its own: a
    class discovered today folded into an existing ratchet reads as that ratchet loosening by
    however many rows the new class holds, which is a number saying nothing about either.

    `series_unconfirmed` carries what went wrong and why every such row has to be read again
    rather than only the ones that can be shown to be short.
    """
    from adapters import captures as _cap

    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        from recon import bookwalker_volumes as _bv
        doc = _cap.load(ROOT / "data/queue/bookwalker-volumes.yaml")
    except Exception:                                                       # noqa: BLE001
        return 0
    works = {str(w["shop_id"]): w for w in (doc.get("works") or []) if w.get("shop_id")}
    return len(_bv.series_unconfirmed(works))


def _retailer_rows(cap, shop, field):
    """Admitted rows for one shop that no capture has given `field` a value for.

    `field` is `date` or `venue` of the row's `first_publication`. BOTH SHAPES ARE READ, because
    the two captures moved to a nested `first_publication:` block at different times and a reader
    that knows only one of them reports every row in the other file as missing the field. That is
    the silent-plausible failure: a budget that quietly counts the whole queue looks exactly like a
    capture that has not started (STANDING-INSTRUCTIONS §4).
    """
    from adapters import captures as _cap
    try:
        admitted = _cap.load(ROOT / "data/queue/admitted.yaml")
        total = sum(1 for w in admitted["works"] if w.get("shop") == shop)
    except Exception:                                                       # noqa: BLE001
        return 0
    p = ROOT / cap
    if not p.exists():
        return total
    try:
        doc = _cap.load(p)
    except Exception:                                                       # noqa: BLE001
        return total
    return total - sum(1 for w in (doc.get("works") or [])
                       if (w.get("first_publication") or {}).get(field)
                       or w.get(f"first_publication_{field}"))


def _undated_retailer_rows(cap, shop):
    """Admitted rows for one shop that no capture has given a publication date."""
    return _retailer_rows(cap, shop, "date")


def budget_rows_with_a_moving_address(ctx):
    """Rows anchored on a chapter address whose work has no work-level address to fall back on.

    THE BUG THIS COUNTS. build.py gives a row the address of its newest chapter, and identity.py
    anchors the work on the row's address, so on a GigaViewer platform a work that publishes looks
    like a work never seen before. Five changed hands on 2026-08-07 and each was about to be minted
    a second identifier for a work already held.

    WHY A COUNT AND NOT AN INVARIANT. The remedy is a fetch. A work arriving on one of these
    platforms is counted here the moment it lands, before anybody has read its address, and that
    rise is the notice to run adapters/gigaviewer/workaddress.py and apply what it writes. An
    invariant would say the same thing by refusing a build that has nothing wrong with it.

    WHAT SATISFIES IT. A second web address on the same host, held by the same identifier, that is
    not itself a chapter. The second half of that matters: data/queue/address-moved.yaml repaired
    five works by attaching the OTHER chapter address they had moved to, which keeps those five
    resolving and does nothing about the next move. A count satisfied by another chapter address
    would have read 502 where the answer was 507.
    """
    import urllib.parse as _up
    sys.path.insert(0, str(ROOT))
    from adapters import identity as _identity

    held = {}
    for e in ctx["identity"]:
        held.setdefault(e.get("merged_into") or e.get("id"), set()).update(e.get("anchors") or [])

    def host(a):
        return _up.urlparse(a.split("web:", 1)[-1]).netloc

    bad = 0
    for r in ctx["series"]:
        stable = _identity.stable_url(r.get("url") or "")
        if "/episode" not in stable:
            continue
        mine, others = f"web:{stable}", set()
        for a in held.get(r.get("id")) or set():
            if (a.startswith("web:") and not a.startswith(mine) and "/episode" not in a
                    and host(a) == host(mine)):
                others.add(a)
        if not others:
            bad += 1
    return bad


def budget_updates_naming_an_unheld_work(ctx):
    """Feed rows whose work has no record, so the row can offer a reader nothing but the platform.

    THE CLASS THIS COUNTS. Every platform pass takes its targets from its own list and nothing
    compares the lists against each other. ニコニコ漫画's release pass reads the comparator
    candidates and its own resolved ids; its chapter pass reads the print-to-web joins file. A
    serialisation in the first list and not the second publishes an update every week and never
    becomes a work, so it cannot be browsed, searched or classified.

    WHY IT DOES NOT READ `wid`. That field is build.py's record of its own title match, and the
    archived month was written before the field existed, so counting rows without one gives 610
    where the answer is 29. The measure has to give the same answer whenever it is asked.

    WHAT IT CANNOT SEE (§14b). The built feed offers titles and nothing else to join on, so a work
    held under a spelling no fold reconciles is invisible here, as it is to build.py. That is named
    rather than papered over, and it is not what failed: the live rows are missing under a fold
    touching only width and case, and missing again under one stripping every mark in the string.
    adapters/test_feedgap.py pins three works the archived month spells differently from the series
    file, none of which carries a `wid`, so a count taken from that field would have been wrong
    about all three.

    WHY A COUNT. The remedy is a capture and a classification, and a work arriving in the feed is
    counted the moment it lands, before anybody could have made either. An invariant here would
    refuse a build whose only fault is that the world moved yesterday.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import feedgap
    return len(feedgap.unheld(ctx["releases"], ctx["series"]))


def budget_targets_a_capture_wrote_no_row_for(ctx):
    """Works a capture pass was given and produced no row for, across every platform pass.

    THE CLASS THIS COUNTS. A pass fetches its targets, drops the ones that failed into a local
    `failed` list, prints that list and exits zero. The print scrolls away, so an absence in
    data/source is indistinguishable from a work nobody ever named. ぬるめた is the case that showed
    it: `data/source/comicfuz/resolved.yaml` records the confirmed address as `/series/2389`,
    `adapters/comicfuz/releases.py` computed the `/manga/` spelling to decide the row was a target
    and then fetched the original, `/series/2389` answers 404, and the capture was written with 46
    of its 47 confirmed works and reported success.

    WHAT IT READS, AND WHY NOT THE OBVIOUS THING (§14b). The target lists, which a pass consumes
    and never rewrites, against the captures. It reads no `failed` list and no counter a pass
    prints: `works_resolved` in a capture header counts the rows underneath it, so it agrees with
    the capture whatever was asked for, and a measure taken from it could never have seen this.
    `adapters/capturegap.py` also declines to reuse the adapter's address handling, which is the
    code that failed, and accepts both spellings of a FUZ address directly.

    WHAT IT CANNOT SEE. A work no target list names. That is coverage and not a capture fault, and
    `updates naming a work we do not hold` is the measure for it.

    WHY A COUNT. A platform that has stopped serving a work will keep the number above zero, and
    four of the five counted today are that: ニコニコ answers 200 for them with a 9.7 KB shell and
    no `meta_info`, where a work it still serves renders 200 KB. Refusing a build over a work the
    platform withdrew would be refusing it because the world moved.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import capturegap
    return len(capturegap.missing(ctx["capture_passes"]))


def budget_shadowed_names(ctx):
    try:
        out = subprocess.run([sys.executable, str(ROOT / "adapters" / "lint" / "shadowing.py"),
                              str(ROOT / "build.py")], capture_output=True, text=True, timeout=60)
        m = re.search(r"(\d+) name\(s\) rebound", out.stdout)
        return int(m.group(1)) if m else 0
    except Exception:
        return 0


# name, measure, what a rise would mean. The third field exists because a bare number in a JSON
# file tells a later reader nothing about why it matters or which way is good, and a budget nobody
# understands is a budget that gets raised to make a build pass.
# WHICH BUDGETS ARE ABOUT THE SOURCE RATHER THAN THE DATA.
#
# These count things in this repository's own Python and Markdown: the prose in its comments, the
# shape of its sentences, whether a module has a test. None of them can change as a result of
# deploying, and none says anything about the data being published. They ran on every deploy anyway
# and were 7.5 of its 8.3 seconds, because they spawn linters over every file in the tree.
#
# They are not dropped: `--gate` runs them before a commit, which is when the source can have
# changed, and a run that skips them says so in checks.json rather than omitting the row. A budget
# that quietly stops being measured is the failure this project keeps meeting.
def budget_titles_with_no_translation_of_our_own(ctx):
    """Titles holding an official or licensed English name and no translation we made.

    EN_ORDER IS A READER PREFERENCE, not a ranking applied once at build time. A reader who moves
    official-jp and licensed down is asking to see what the publisher did not choose, and only a
    record holding more than one form can answer. Where the only English is the publisher's, that
    reader falls through to a romanisation, so the control silently does nothing.

    MEASURED ON THE SHIPPED FILE, because the store holds one name per title and assembles
    en_forms at build time. A count taken from the store would read zero forever while the
    interface offered a control with nothing behind it, which is the shape of blind spot §14b
    exists to refuse.

    A count, so it ratchets down as translations are written. It is deliberately not a floor on
    how many titles hold several forms: that number falls whenever the corpus legitimately
    shrinks, so it would need explaining away on ordinary churn, and it says nothing at all about
    the titles that never held a second form.
    """
    f = ROOT / "data" / "build" / "feed" / "names.json"
    if not f.exists():
        return 0
    titles = (_load(f, {}) or {}).get("titles") or {}
    # ONE TITLE HELD UNDER TWO KEYS IS ONE TITLE. The map answers for the catalogued spelling of a
    # title as well as the platform's, so a work whose subtitle a cataloguer wrote after a colon has
    # two entries pointing at one record; counting keys read that as two titles needing a
    # translation. The alias carries `alias_of` for exactly this.
    return sum(1 for v in titles.values()
               if isinstance(v, dict) and not v.get("alias_of")
               and set(v.get("en_forms") or {}) & {"official-jp", "licensed"}
               and not (v.get("en_forms") or {}).get("translated"))


SOURCE_BUDGETS = {"stock phrasing in comments", "three as an organising shape",
                  "modules without a test", "shadowed names in build.py",
                  "scraped counters in chapter names", "invented markup in tests"}

RUBY_KANJI = re.compile(r"[一-鿿々]")
RUBY_KANA = re.compile(r"[ぁ-ゖァ-ヺー]")


def budget_implausible_ruby_spans(ctx):
    """Ruby spans holding fewer kana than the run has kanji, which nobody could read aloud.

    `ruby spells the reading` passes on every one of these, because い + ぬのえさはいろう does
    concatenate to いぬのえさはいろう. It checks the spelling and says nothing about where the
    boundaries fell, so 狗之餌 shipped carrying い while 廃狼 carried the other eight.

    A run of N kanji needs at least N kana. That is arithmetic and not a heuristic, which is why
    this counts only the impossible ones and leaves the merely surprising alone: 承る is one kanji
    and four kana, and a rule with an upper bound would spend its life arguing about it.
    """
    bad = 0
    for r in ctx["series"]:
        for key in ("work_en", "author_en"):
            for span in ((r.get(key) or {}).get("ruby") or []):
                base, rt = (span + [None, None])[:2] if isinstance(span, list) else (None, None)
                if not rt:
                    continue
                nk = len(RUBY_KANJI.findall(str(base or "")))
                if nk and len(RUBY_KANA.findall(str(rt))) < nk:
                    bad += 1
    return bad


NOT_A_PERSON = re.compile(r"^(?:[#＃]?\d+[(（]?\d*[)）]?|[\d\W_]+)$")


def budget_credits_matching_a_chapter(ctx):
    """Credits that name a chapter of the same work.

    WHY NOT A REGEX (§14b). The previous measure carried its own copy of `credits.is_a_person`'s
    pattern, so it could only report what that pattern already catches, and the copies had drifted:
    the check recognised fewer forms than the adapter, missing 第3話, so neither number meant
    what it said.

    THE FAULT IS OBSERVABLE WITHOUT A PATTERN. 平良深姉妹はどっちもヤんでる was credited to
    `金子ある / #1(1)` because a route read a page title's middle field as an author, and that same
    string sits in the platform's feed as a chapter of that work. So compare the credits against the
    chapter names this database already holds for the work. A credit naming a chapter is wrong
    whatever it is made of, and no rule about digits is involved.
    """
    chapters = {}
    for rel in ctx["releases"]:
        w, ep = str(rel.get("work") or ""), str(rel.get("ep") or "").strip()
        if w and ep:
            chapters.setdefault(w, set()).add(unicodedata.normalize("NFKC", ep))
    bad = 0
    for r in ctx["series"]:
        eps = chapters.get(str(r.get("work") or ""))
        if not eps:
            continue
        for part in re.split(r"\s*/\s*", str(r.get("author") or "")):
            if part.strip() and unicodedata.normalize("NFKC", part.strip()) in eps:
                bad += 1
    return bad


def budget_credits_that_restate_a_name(ctx):
    """Credits where one part restates another, asked without the name store.

    WHY NOT THE STORE (§14b). The previous measure compared each part against the store's recorded
    reading of the part before it, which is how `credits.dedupe` decides the same question. The
    measure was blind wherever the fix was blind, read 0, and a reader found
    `田口ケンジ / タグチケンジ` on a live page with every gate green.

    THE SIGNAL IS IN THE STRINGS. A name written partly in katakana keeps that katakana in its
    reading: 田口ケンジ reads タグチケンジ and both end ケンジ. A part written wholly in katakana,
    ending in the same katakana run another part ends in, is restating that part. Nothing here
    consults the store, the analyser, or anything that produced the field.

    WHAT IT CANNOT SEE, named because §14b asks for it. A name carrying no katakana, 蓬餅 against
    ヨモギモチ, leaves no shared run to match on. Those need a reading from somewhere, which is the
    fix's job. This counts a population the store cannot reach, so the two are blind in different
    places instead of the same one.
    """
    kata_tail = re.compile(r"[ァ-ヺー]+$")
    has_kanji = re.compile(r"[一-鿿々]")
    all_kata = re.compile(r"^[ァ-ヺー・\s]+$")
    bad = 0
    for r in ctx["series"]:
        parts = [x.strip() for x in re.split(r"\s*/\s*", str(r.get("author") or "")) if x.strip()]
        for n, part in enumerate(parts):
            if not all_kata.match(part):
                continue
            for other in parts[:n] + parts[n + 1:]:
                if not has_kanji.search(other):
                    continue
                tail = kata_tail.search(other)
                if tail and part.endswith(tail.group(0)) and len(part) > len(tail.group(0)):
                    bad += 1
                    break
    return bad


# Every spelling of the sign, deliberately looser than the one the ingest acts on. See the budget
# below for why the looseness is the whole point.
EQUALS_ANY = re.compile(r"[=＝゠]")


def budget_titles_carrying_cataloguing_punctuation(ctx):
    """Titles a reader is shown that still hold a catalogue's own punctuation.

    WHAT IS BEING COUNTED. A bibliography transcribes a title page under ISBD, so a name arrives
    marked up: `恋愛遺伝子XX = The Romance Gene XX` is one work with an English name beside it, and
    `恋愛遺伝子XX : 完全版` is that work reissued. Neither mark is part of what anybody calls the
    book. `adapters/isbd.py` takes the parallel title off and hands the English on; the ten reissue
    markers are counted here and not yet lifted off, which is why this number will not be zero
    before somebody decides where an edition statement should live.

    THE CLOSED SET IS WHAT KEEPS A SUBTITLE OUT OF THIS COUNT.
    `ギャルメイドと悪役令嬢 : おじょーさま、お世話させていただきます` carries the same colon and the
    tail is content: it says something about the book that the first six words do not. Counting
    every colon would put 77 rows here of which 67 are correct, and a number that is mostly noise
    is one nobody reads. `isbd.edition_statement` is the only thing that can tell the two apart.

    WHY THIS IS NOT BLIND WHERE THE INGEST IS (§14b). `isbd.areas` acts on ` = ` alone: one sign,
    spaces both sides, Latin on the right, before any colon. This looks for an equals sign in any
    spelling, anywhere in the string, whatever surrounds it. So it reports exactly the cases the
    split refused, which is what it does today: `ルミナス = ブルー` is one name written with a sign
    in it, `School zone = スクールゾーン` runs the languages the other way round, and
    `ニニンがシノブ伝ぷらす = 2×2=SHINOBUDEN+` has two signs and no way to say where the name ends.
    Each is a deliberate refusal and each stays visible instead of being defined out of the count.

    WHAT IT CANNOT SEE. A title whose apparatus was stripped before it reached this database. A
    shop writes `シナモン` where the catalogue writes the whole ISBD line, so a work admitted from a
    shelf can be here under a name nobody had to correct, and nothing in this count says whether
    that name is the one the publisher printed.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import isbd

    # WHAT A READER IS SHOWN IS THE WORK, and a record is a transcription of one edition. This
    # counted works.json too, where a MADB record faithfully carries `X : 完全版` for a reissue that
    # is now filed under the work it reissues, so 13 of 15 were the record layer doing its job
    # (§5 keeps a source record as it arrived). The work is what carries the name, and where a
    # publisher states that name it is canonical: an edition files under it.
    #
    # A SIGN A PUBLISHER PRINTS IS NOT PUNCTUATION. ルミナス＝ブルー is one name with a fullwidth
    # sign in it, so `isbd.RULED` holds it and this asks that map before the pattern, which is
    # otherwise deliberately loose enough to catch every spelling of the mark.
    bad = 0
    for title in [str(r.get("work") or "") for r in ctx["series"]]:
        if title in isbd.RULED:
            continue
        if EQUALS_ANY.search(title) or isbd.edition_statement(title):
            bad += 1
    return bad

KANA_SURFACE = re.compile(r"^[ぁ-ゖァ-ヺーゝゞヽヾ・･\s　]+$")


def budget_kana_names_with_no_stated_division(ctx):
    """Kana author names whose romanisation ships as one unbroken word of eight letters or more.

    THIS IS A COVERAGE DEFICIT AND NOT A FAULT COUNT, and the difference is the whole reason the
    name says `no stated division` instead of what the first version said. Two populations are in
    here and nothing in the data separates them:

      A DIVISION NOBODY HAS STATED YET. いがらしゆみこ is Igarashi Yumiko and shipped as
      Igarashiyumiko. Finding a source moves it out of the count.

      A NAME THAT IS ONE WORD. こかむも is printed Kokamumo in Latin on ぬるめた's own tankōbon
      cover, by the publisher, and Kokamumo is the right answer. It is four kana with no boundary
      and it sits in this count looking exactly like the first kind.

    So the number falling is not by itself an improvement, and a rule that pushed it down by
    inferring boundaries would break こかむも against a Latin form the publisher set. What makes it
    safe to reduce is `a division cites its source`, which refuses any division nothing states, and
    the reduction has to come from finding sources. Every division this branch made was checked
    against the Latin forms the store holds: 171 agree and none contradicts.

    WHAT WOULD SEPARATE THE TWO. A Latin form the publisher or the artist set, which is evidence
    that the name is one word in the same way a collationkey is evidence that it is two. The store
    holds no such form for any name in this count; the 26 Latin forms it does hold for them all come
    from Wikidata or MangaUpdates, which `curate.py` refuses as evidence for a name.

    MEASURED ON WHAT SHIPS, AND IT OWES THE FIX NOTHING (§14b). `boundary.py` decides by asking
    whether another record states a division; this counts letters in the romanisation that reaches
    the browser and asks nothing at all.

    THE SURFACE HAS TO BE KANA, which is what keeps a name out of it. Ｔｏｍｏｒｒｏｗｓ is Latin and
    is somebody's whole rendering. Eight letters is where a Japanese personal name written in one
    piece stops being plausible, and it is the threshold the fault was reported at.
    """
    n = 0
    for k, v in ((ctx["names_shipped"] or {}).get("authors") or {}).items():
        p = (v.get("romaji") or {}).get("plain") or ""
        if len(p) >= 8 and " " not in p and KANA_SURFACE.match(k or ""):
            n += 1
    return n


def budget_author_readings_no_source_states(ctx):
    """Author names shipping as a romanisation of ours under the unverified mark.

    THE DEFICIT THE NAMING WORK IS AGAINST, and it is written as a budget because there is no
    correct value for it and no floor anybody can compute. Every name in here renders in English as
    a romanisation of a reading nobody but a morphological analyser has ever produced, which is the
    one thing NAMES-PLAN section 1 says must never be presented as if it had a source. The mark is
    what says so on the page, and this is the same population counted where a person can watch it
    move.

    IT FALLS ONLY WHEN A NAME GETS SOURCED. `build.py` clears the mark for `stated` and for
    `researched` and for nothing else, so the only way to move this number is to find a source or
    to weigh one, and both of those leave a citation on the record. Suppressing the mark would move
    it too, which is why the number is kept beside the reason: a fall with no new citations behind
    it is the failure, not the success.

    NOT `uncertain readings`, WHICH SITS A FEW LINES ABOVE IT. That one counts the store's
    `reading_uncertain`, a flag pass 4 sets when it could not read a word at all and assembled the
    reading character by character. This one counts what a READER meets, which is 703 names against
    that budget's 73, and the two moved in opposite directions for a whole round without anyone
    being able to see it.

    MEASURED ON WHAT SHIPS AND OWING THE PASSES NOTHING (section 14b). The routes that reduce it
    select on `reading_basis`; this reads the rendered record, where `basis` is what the English
    column holds and the mark is what the browser draws. A pass that recorded a reading and failed
    to reach the feed would settle a name by its own measure and change nothing here.

    IT HAS A FLOOR OF EIGHT AND NOBODY CAN SOURCE THEM. A refuted reading leaves the record with no
    reading and no English, and `basis: romaji` and the mark stay on it, so 伊実 and 生肉 and the
    six others count here while rendering as the Japanese they are. Those are decisions somebody
    made and researched: 伊実 is a Chinese creator NDL deliberately files without kana, and there is
    nothing to replace the guess with. They are left in the count because taking them out would
    mean this number and the population the naming rounds are measured against are two different
    sets, and worth naming here so the next round does not spend a day on them.
    """
    return sum(1 for v in ((ctx["names_shipped"] or {}).get("authors") or {}).values()
               if v.get("basis") == "romaji" and (v.get("uncertain") or v.get("unverified")))


def budget_credits_the_corpus_files_as_a_venue(ctx):
    """Credits in the author store that the corpus records elsewhere as a publisher or an imprint.

    IT ASKS A QUESTION THE FIX DOES NOT (§14b). `entities.kind` reads a vocabulary of organisation
    words, so a measure built on that vocabulary can only ever report what the vocabulary already
    catches. This one never looks at the name: it asks whether this same string appears in
    data/names/publishers.yaml or on a volume's publisher or imprint field, which is the corpus
    filing it as something other than a person. 一迅社 and ガレットワークス are here and carry no
    organisation word between them.

    CANDIDATES, NOT FAULTS, and the counter-case is why. A doujin artist is their own imprint, so
    山名沢湖 and 雪尾ゆき are filed as publishers of their own books and are people. Marking a credit
    on this evidence alone would take them with it, which is exactly why the adapter does not use it.
    The number is the honest residue: it falls when a credit is marked or the corpus stops filing it
    both ways, and it never has to reach zero.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import entities
    except Exception:
        return 0
    pubs = (_yaml(NAMES / "publishers.yaml", {}) or {}).get("names") or {}
    filed = entities.filed_elsewhere(pubs, ctx["series"])
    return sum(1 for k, v in (ctx["names"].get("authors") or {}).items()
               if k in filed and not v.get("entity"))


def budget_credits_carrying_their_own_cataloguing(ctx):
    """Store records the build declines to publish a rendering for.

    COUNTED ON THE OUTPUT, so the filter is observable (STANDING-INSTRUCTIONS §13). A filter that
    silently drops rows looks identical to one that has stopped working, so this compares the store
    against what shipped instead of asking `entities.kind` again. `はいむらきよたか(キャラクター
    デザイン)` is a person with a role welded on and the store holds the person beside it, so the
    lookup is meant to reach the person; the record is kept and its rendering withheld.

    A rise means a route started writing cataloguing into the author position again, which is what
    `pass4_analyser.is_credit_line` is there to stop.

    FOLDED, because the shipped map is keyed the way the interface asks: `build.py` writes it under
    the folded string so a name reaches it under whichever width and spacing a platform used.
    Comparing raw counts 147 records that shipped perfectly well under their folded key.
    """
    shipped = ((ctx["names_shipped"] or {}).get("authors") or {})
    fold = (lambda t: unicodedata.normalize("NFKC", t or "").replace(" ", "").replace("　", ""))
    return sum(1 for k, v in (ctx["names"].get("authors") or {}).items()
               if v.get("reading") and k not in shipped and fold(k) not in shipped)


def budget_credit_fields_no_identifier_covers(ctx):
    """Name-shaped runs of a shipped credit field that no credit identifier accounts for.

    THE MEASURE FOR THE CREDIT IDENTIFIERS, BUILT NOT TO SHARE THEIR BLIND SPOT (§14b). Everything
    that assigns one finds a credit with `inputs.split_credits_detail`, so a count that asked the same
    splitter could only ever report what the splitter already handles. That is the shape that let
    `田口ケンジ / タグチケンジ` reach a reader with every gate green: the measure and the fix asked one
    question and got one answer.

    This asks a different question. It deletes every registered spelling out of the credit field AS
    SHIPPED and reports what is left that still looks like a name. That is arithmetic on the string,
    and it consults no splitter, no fold, no name store and no registry lookup, so it can fail on
    anything the pipeline is able to emit: a credit the splitter drops, a fold that collapsed two
    people into one key, a registry the pass forgot to write.

    IT COUNTS CANDIDATES AND NOT FAULTS, and the residue is legible. A role label is name-shaped and
    is legitimately unregistered, so 原作 and 著者 are in it, along with the imprint notes a
    bibliography rides along inside a bracket (早川書房刊, GA文庫) and one furigana gloss, the ひろ of
    博（ひろ）. Excluding those would mean holding a copy of the role vocabulary here, which is the
    third shape §14b names and the one that had already drifted.

    WHAT IS IN IT THAT IS A FAULT, today: `フォローする` is a Follow button a page capture handed over
    as a byline, and 虫原 and 科戸コウ are credits only a release row names. Both are counted rather
    than minted, because an address for a button is worse than a number that is not zero.

    DISTINCT RUNS, so a new uncovered name cannot hide behind a role label already in the list. The
    count is 19 and does not grow with the corpus.
    """
    surfaces = _credit_surfaces(ctx)
    if not surfaces:
        return 0
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        import credit_identity
    except Exception:                                                       # noqa: BLE001
        return 0
    left = set()
    for r in list(ctx["series"]) + list(ctx["releases"]):
        left.update(credit_identity.uncovered(r.get("author") or "", surfaces))
    return len(left)


def budget_credits_sharing_a_reading_nobody_ruled_on(ctx):
    """Readings the shipped name map gives to several credits that no ruling has settled.

    WHY IT HAS TO BE COUNTED. 82 readings answered for 164 credits when the identifiers were minted,
    and 74 of the pairs were one credit a source had recorded twice: MADB states a name beside its own
    reading in the field where the slash separates two people, so 秋山はる and アキヤマハル both
    became records. Left alone, that is one artist with two addresses each showing half their works.

    THE RESIDUE IS RULED ON AND NOT FILTERED, which is why this is at zero instead of absent. A
    reading newly sourced can put two credits together that nobody has looked at, and the pairs that
    need a person are exactly the ones a rule cannot settle: かぼちゃ against カボちゃ differ in which
    characters are katakana, which is what a stylised pen name does on purpose. So a new pair arrives
    as a number that has risen and blocks at check-in, where somebody can rule on it.

    READ OFF THE SHIPPED FILE, not the store. The store holds a reading and only the build spells it,
    folds the key and decides what ships, so asking the store would count records rather than the
    renderings a reader can see two of, and would answer 0 while the duplicate was live.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        import credit_identity
    except Exception:                                                       # noqa: BLE001
        return 0
    return len(credit_identity.unruled((ctx["names_shipped"] or {}).get("authors") or {},
                                       ctx["credit_rulings"] or {}))


def budget_renderings_with_nothing_to_show(ctx):
    """Renderings that leave a Japanese name with no English form at all.

    `English mode has no Japanese` reads `feed/names.json`, the join the FEED performs, and never
    the series rows. So a work page could show 花宮みぃ in English-only mode while that check
    passed, which is how 35 rows shipped: every one a multi-credit author field mixing a Latin name
    with Japanese ones.

    The cause is in build.py's `credits_en`. A part already in Latin is in the name store with an
    `en` and no `reading` and no `romaji`, correctly, because it needs neither. The composer read
    "found in the store" as "resolved", intersected the romanisation styles across the parts, got
    an empty set from the Latin one, and emitted a composed name carrying no romanisation at all.

    A rendering with no `romaji` is not itself wrong: a title already in Latin needs none. What is
    wrong is holding neither a romanisation nor an English name while the surface is Japanese,
    because there is then nothing to put on an English page.

    COUNTED ACROSS EVERY VIEW, because it reached all of them. The works list and the work page
    read the series rows; the updates and releases lists read `feed/names.json`, keyed on the whole
    author field folded. A field naming several people never matches a store keyed one person to a
    record, and the releases feed separates its credits with a comma where a series row uses a
    slash, so a composer splitting on one of them misses the other.

    This counts rather than blocks only until it reaches 0.

    RE-MEASURED 2026-08-07, and it had been wrong in both directions at once. It read 150 while the
    series rows carried 192 Japanese author fields on an English page, and the two numbers had
    almost nothing to do with each other.

      A ROW WITH NO RENDERING AT ALL WAS SKIPPED. `if not e` passed over exactly the case the
      docstring above names, so of the 192 the measure could see 10. Nothing to show is nothing to
      show, whether the field is empty or missing.

      A RELEASE ROW WAS ASKED A QUESTION THE INTERFACE DOES NOT ASK. This looked the whole credit
      field up in `names.json`'s `authors`, which is keyed one PERSON to a record and can never
      hold a field naming three of them. The interface renders those rows from `credit_parts` and
      `phrases`, and every one of the 140 counted here rendered correctly on the page. A measure
      that counts 140 rows nobody can see broken cannot reach zero and buries the 49 that are.

    So the release half asks the question the way `authorLabel` answers it. That is deliberately a
    check modelled on its subject, against §14b, and what it therefore CANNOT see is a phrase whose
    English is wrong rather than absent. `English mode has no Japanese` is the invariant that reads
    the shipped strings themselves; this counts the rows with no string to read.
    """
    import re as _re
    ja = _re.compile(r"[぀-ヿ一-鿿々]")
    bad = 0
    for r in ctx["series"]:
        for key, surface in (("work_en", r.get("work")), ("author_en", r.get("author"))):
            e = r.get(key) or {}
            if e.get("romaji") or e.get("en"):
                continue
            if ja.search(str(surface or "")):
                bad += 1
    shipped = ctx["names_shipped"] or {}
    authors = shipped.get("authors") or {}
    phrases = shipped.get("phrases") or {}
    parts = shipped.get("credit_parts") or {}

    def fold(t):
        return unicodedata.normalize("NFKC", t or "").replace(" ", "")

    for r in ctx["releases"]:
        surface = str(r.get("author") or "")
        if not ja.search(surface):
            continue
        key = fold(surface)
        e = authors.get(key) or {}
        if e.get("romaji") or e.get("en"):
            continue
        # `creditFromParts`: a line composes when every person in it has a romanisation of theirs.
        people = parts.get(key) or []
        if len(people) > 1 and all((authors.get(fold(p)) or {}).get("romaji") for p in people):
            continue
        # and the phrase map is the fallback, which only helps where the phrase is not Japanese.
        phrase = str(phrases.get(key) or "")
        if phrase and not ja.search(phrase):
            continue
        bad += 1
    return bad


def budget_publishers_with_no_english(ctx):
    """Publisher and imprint names that stay Japanese in English-only mode.

    COUNTED ON THE NAME A READER SEES. This used to read `PUB_EN` out of `app.js` and count the raw
    catalogued strings it had no entry for, which double-counted: 講談社 reaches the corpus as
    itself, as `[発売]講談社` and as `[頒布]講談社`, and all three were counted while the interface
    renders all three as Kodansha. Cataloguing is stripped first now, so this counts publishers.

    MEASURED ON THE SHIPPED MAP, WHICH IS WHERE §14b BIT. It used to re-run `publishers.render`
    over the store, which is the producer's own join: a name the build had failed to write into
    feed/names.json still counted as rendered, because the check derived its own answer instead of
    reading the build's. It also could not see a romanisation, because the store holds a reading
    and only the build spells it. What it counts now is the keys the shipped file HAS.

    STILL SHARES THE NORMALISERS, and §14b says to say so and to name what that hides. It cannot
    see a disagreement between `publishers.publisher_of` here and `publisherOf` in app.js, which is
    the one way a name in the shipped file can still render as Japanese. What guards that instead
    is the file being keyed by the RAW catalogued string as well as the normalised one, so either
    implementation's answer finds the record.

    Names, not rows: one publisher rendered once serves every work it publishes.
    REUSES THE ADAPTER'S NORMALISERS, and §14b says to say so and to name what that hides. It
    cannot see a disagreement between `publishers.publisher_of` here and the interface's own
    reading, which is the one way a name in the store can still render as Japanese. What guards
    that instead is the shipped file being keyed by the RAW catalogued string as well as the
    normalised one, so either answer finds the record.

    So it reads the shipped mapping wherever the build puts it, and counts the distinct names the
    data carries that the mapping has no entry for. Names, not rows: one publisher rendered once
    serves every work it publishes.

    THE DISTRIBUTOR IS COUNTED BECAUSE IT IS SHOWN. Taking it out of the publisher field did not
    take it off the page: the volumes row names it and says it delivered the book, so a reader in
    English mode meets it and it needs a rendering like any other name. Adding it can only move
    this number up, and a number that rises because a field that was hidden inside another one is
    now its own is a real change in what is measured rather than coverage lost.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import publishers as _pub
    except Exception:                                                       # noqa: BLE001
        return 0
    shipped = (ctx["names_shipped"] or {}).get("publishers")
    if shipped is None:
        return 0
    return len(_pub.unnamed(shipped, _pub.corpus_names_from_rows(ctx["series"])))


def budget_publisher_keys_the_interface_misses(ctx):
    """Publisher, distributor and imprint names the browser still shows in Japanese.

    THE FAULT THIS FOUND, and it had been invisible to every measure in the file.
    `GP-KIDS/高菜しんの` is catalogued in the publisher field AND the imprint field, and the two
    normalise differently, so whichever field was read first decided what the shown name was, the
    other field's name never entered the map, and the interface asked for a key nothing held.

    HOW IT USED TO ASK, AND WHY THAT WENT. It held `_app_publisher_of` and `_app_imprint_of`, this
    file's transcriptions of the browser's normalisers, kept deliberately as a third copy so a
    drift between the interface and the pipeline would show up as a disagreement. The copy went
    stale the way §3 says a copy does: `publisherOf` no longer exists in `kari/app.js` at all, the
    cataloguing having moved upstream into `adapters/madb/extract.py`, and this file was still
    stripping brackets on the browser's behalf.

    So it asks the browser. `pubBoth` and `imprintOf` are called through
    `adapters/interface.py`, on the strings the corpus holds, and what comes back Japanese is what
    a reader sees in Japanese. There is nothing left here to drift.

    Japanese only. A name already in Latin passes through the interface untouched and needs no
    entry, which is the same rule `platName` follows.

    THE IMPRINT MAP IS PASSED IN, and for one round it was not. `imprintOf` stopped segmenting and
    started returning the registry's canonical name for the line, this copy followed it, and the
    caller went on invoking it with no map. So the copy of the consumer resolved every imprint
    string to itself, which is what the OLD interface did, and the measure quietly went on
    answering the previous question: it read 5 while 11 canonical line names reached a reader in
    Japanese and 4 catalogued strings it was counting had stopped being shown at all. A copy of the
    consumer has to be called the way the consumer is called (STANDING-INSTRUCTIONS §14b).
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    if (ctx["names_shipped"] or {}).get("publishers") is None:
        return 0
    raw = {}
    for r in ctx["series"]:
        for pr in (r.get("print") or []):
            for field, fn in (("publisher", "pubBoth"), ("distributor", "pubBoth"),
                              ("imprint", "imprintOf")):
                s = str(pr.get(field) or "").strip()
                if s and interface.KANA_KANJI.search(s):
                    raw[(fn, s)] = True
    if not raw:
        return 0
    keys = sorted(raw)
    try:
        # `imprintOf` answers with the LINE, which is then shown like any other publisher name, so
        # the two-step is what a reader meets and asking only the first step would count a line
        # resolved as a line rendered.
        shown = _interface(ctx).labels([(fn, s) for fn, s in keys])
        second = _interface(ctx).labels([("pubBoth", v) for v in shown])
    except interface.Unavailable:
        return 0
    return len({v for v in second if interface.KANA_KANJI.search(v)})


def budget_names_rendered_two_ways(ctx):
    """Strings the shipped maps spell one way as a publisher and another way as a person.

    THE FAULT THIS IS FOR. 25 print rows name their own author as the publisher, because a work
    self-published through a shop's individual-publishing service has nobody else to name. So the
    same string is rendered by two maps, and two of them had already drifted on the live site:
    ガレットワークス was `Galette Works` beside its books and `Garettowākusu` beside its name, and
    ネジ式１３番地 was `Nejishiki 13-banchi` one place and `Neji Shiki Ichisan Banchi` the other.
    One person, one page, two spellings, and nothing in either producer could see the other.

    ARITHMETIC ON THE RENDERED RESULT, per §14b. It compares two shipped strings and consults
    neither store, neither basis and neither producer's code, so it can fail on anything the build
    is able to emit. What it cannot see is a name rendered two ways in two places that are not
    these two maps.

    A budget, because it is not zero today and the residue is legitimate: where a publisher-side
    source names a circle in Latin and the person's record only romanises it, the publisher entry
    is the better answer and the fix belongs on the author side.
    """
    n = ctx["names_shipped"] or {}
    pubs, people = n.get("publishers") or {}, n.get("authors") or {}
    if not (pubs and people):
        return 0

    def fold(t):
        return unicodedata.normalize("NFKC", t or "").replace(" ", "")

    bad = set()
    for ja, rec in pubs.items():
        person = people.get(fold(ja))
        if not person:
            continue
        theirs = person.get("en") or (person.get("romaji") or {}).get("macron")
        ours = rec.get("en")
        if theirs and ours and theirs != ours:
            bad.add(fold(ja))
    return len(bad)


def budget_publisher_readings_nobody_has_settled(ctx):
    """Publisher keys shipped as OUR romanisation whose reading no source states.

    WHY THIS EXISTS, AND WHY IT IS NOT THE BUDGET ABOVE. `publishers with no English` reached zero
    largely by romanising, which finished the rendering and moved the sourcing rather than doing
    it: a romanisation is the reading spelt in Latin, so a name romanised off a reading nobody has
    stated is published on a guess and carries the mark that says so. 134 keys were in that state
    on 2026-08-08 and no number anywhere said so, which is STANDING-INSTRUCTIONS §13: the first
    budget's fall to zero read as the work being done.

    A DEFICIT, so it falls only when a reading gets sourced. The route that would empty it without
    doing that is suppressing the mark in the interface, which was tried once and rejected, and
    this reads the SHIPPED map and asks for the mark precisely so that suppressing it would show
    up here as a fall nobody earned.

    The rule is `publishers.unsettled_readings`, which owes the producer nothing: `unverified` is
    computed in build.py out of `verified` and `reading_basis`, and this reads neither, only the
    file a reader is served. §14b, what it therefore cannot see: a reading cited to a page that
    says something else. No count can see that; only a reader following the citation will.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import publishers as _pub
    except Exception:                                                       # noqa: BLE001
        return 0
    # `names_shipped` and not `names`: the store holds a reading, and only the build spells it and
    # decides whether to mark it. Asking the store would count records rather than renderings and
    # would answer 0 while a reader was being shown 134 marks, which is what the first draft did.
    return len(_pub.unsettled_readings((ctx["names_shipped"] or {}).get("publishers") or {}))


def budget_imprint_strings_that_reach_no_line(ctx):
    """Imprint strings the corpus carries that the shipped map answers for with no line.

    AN IMPRINT IS ONE OBJECT WITH MANY RECORDED SPELLINGS. One printed logotype reaches us from
    MADB, from openBD and from a retailer in three transcriptions, notation and case and the parent
    line vary on top, and the field stored each result as though it were a line of its own: 一迅社
    runs one yuri line and the rows held 27 strings for it. `data/names/imprints.yaml` says which
    spellings are one line and `adapters/names/imprints.py` does the matching. This counts what the
    registry has not reached.

    A COVERAGE DEFICIT, and the number a curating round is against. It falls as houses are entered
    and it will not reach zero: some of these strings are not imprints at all. `ガレットワークス` on
    37 rows is the company whose books クロスフォリオ出版 distributes, and `まんがタイムきらら` is a
    magazine, both sitting in the imprint field where a line's name goes. Those are for the
    publisher-page work to answer and folding them into a line to empty this number would be worse
    than the number.

    §14b, AND WHY THIS IS COUNTED ON THE SHIPPED FILE. The registry is curated for exactly this
    reason. A matcher that gave every unrecognised string a line of its own would reach every string
    by construction, and this count would read zero for the rest of its life while the split it
    exists to measure carried on. So an unmatched string produces no entry, and this asks the corpus
    for its imprint strings and the shipped map whether it holds each one. It imports nothing from
    the module, folds nothing, splits nothing, and shares no table with the matcher: the map's own
    keys are the only thing consulted.

    WHAT IT THEREFORE CANNOT SEE is a string that reaches the WRONG line. `an imprint spelling
    belongs to its own publisher` catches that across houses. Within one house nothing can, because
    the two spellings look alike by construction, so the guard is the counter-case pinned in
    `adapters/names/test_imprints.py`: 一迅社's ZERO-SUM, HOWL, DNAメディア and 4コマKINGS lines and
    its bare umbrella must each land somewhere other than the yuri line.
    """
    # A MISSING MAP COUNTS EVERY STRING, and it is not shortcut to zero. `return 0` on an absent key
    # is the silence STANDING-INSTRUCTIONS §4 is about: a build that stopped writing the map and a
    # registry that had placed everything would report the same number. This way the map going away
    # reads as every string reaching no line, which is what has happened.
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    import key as _k
    shipped = (ctx["names_shipped"] or {}).get("imprints") or {}
    missing = set()
    for r in ctx["series"]:
        for pr in (r.get("print") or []):
            raw = str(pr.get("imprint") or "").strip()
            pub = str(pr.get("publisher") or "").strip()
            if raw and raw not in shipped and not (pub and _k.fold(raw) == _k.fold(pub)):
                missing.add(raw)
    return len(missing)


def budget_an_imprint_field_repeating_its_publisher(ctx):
    """Print rows whose imprint field holds the same name as their publisher field.

    A SHOP'S INDIVIDUAL-PUBLISHING SERVICE WRITES THIS. An artist publishes their own book, the
    service is the publisher of record, and its catalogue puts the same name in both fields. There
    is no line, so there is nothing a registry could name and no curation anybody can do, which is
    why these left `imprint strings that reach no line`: counted there they read as 100 lines
    waiting to be curated and they are none.

    IT IS STILL A FAULT, and a quieter one. `GP-KIDS/高菜しんの` is catalogued in both fields and the
    two normalise differently, as a publisher to itself and as an imprint to the person, so the map
    was keyed on whichever field was read first and the interface asked for a key nothing answered.
    A field holding a name that is not an imprint is where that comes from.

    MEASURED ON THE FIELDS AND NOT ON THE REGISTRY (§14b), so it cannot be satisfied by curating
    anything: the only thing that moves it is the capture writing one name in one place.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    import key as _k
    n = 0
    for r in ctx["series"]:
        for pr in (r.get("print") or []):
            raw = str(pr.get("imprint") or "").strip()
            pub = str(pr.get("publisher") or "").strip()
            if raw and pub and _k.fold(raw) == _k.fold(pub):
                n += 1
    return n


def budget_labels_with_nothing_to_quote(ctx):
    """Records carrying a yuri label whose imprint states no term that says so.

    The work page quotes the term each source used, and a term making no yuri claim would put a
    reader in front of a claim they cannot weigh, so the row is withheld and the reader is told
    nothing. 118 records were in that state: `extract.py` selected volumes on a 百合姫 brand and
    stored the series record, whose own brand MADB writes as ["IDコミックス", "Yurihime comics"],
    and the first value is 一迅社's general comics line.

    Counted on the record and not on the page, so it says whether the EVIDENCE is held rather than
    whether the renderer chose to show it. A record labelled from a platform's tag holds its term
    somewhere else and is not counted here.
    """
    # THE LINE'S NAME COUNTS, THE ABBREVIATION DOES NOT, AND THE TWO ARE DIFFERENT QUESTIONS.
    # `YH comics` says nothing a reader can weigh, and teaching this pattern those two letters would
    # empty the class by fiat, which an earlier round refused for that reason. Asking the registry
    # which LINE the spelling names is not the same move: 一迅社's own page says the line is
    # 百合姫コミックス, the registry records that with its source, and `imprintOf` shows a reader the
    # line and not the spelling. So the record quotes a term, and 49 works were being withheld on an
    # abbreviation nobody had mapped.
    #
    # A SPELLING THE REGISTRY DOES NOT PLACE STILL COUNTS, and a line whose own name says nothing
    # counts too, so this cannot be satisfied by curating an entry that carries no term either.
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    import imprints as _imp
    _idx = _imp.index(_imp.load())

    def _quotable(rec):
        imp = str(rec.get("imprint") or "")
        if YURI_TERM_IN_IMPRINT.search(imp):
            return True
        line = _imp.resolve(rec.get("publisher"), imp, _idx)
        return bool(line and YURI_TERM_IN_IMPRINT.search(str(line.get("name") or "")))

    return sum(1 for r in ctx["madb_records"]
               if r.get("marketing_label") in ("yuri", "gl") and not _quotable(r))


def budget_kana_left_in_a_romanisation(ctx):
    """Values the shipped names file offers in place of Japanese that still hold a kana character.

    A romanisation exists so that a reader who cannot read kana has something to read, so one kana
    left in it is the whole point of the string undone. `kana.romanise` emits a character it has no
    table entry for, which is the right default for ☆ and × and was wrong for kana: ＲＤーＳｏｕｎｄｓ
    shipped as `RDー Sounds` because the ー lengthened nothing, and 竹ヶ原 romanised as `takeヶhara`.

    WHAT IT ASKS THAT THE PRODUCER DOES NOT (§14b). `romanise` decides what to emit by looking a
    mora up in BASE, DIGRAPH and PUNCT; this looks at the finished string and asks whether any
    character in it is kana. It shares no table with the subject and would have caught both faults
    above on the shipped bytes, which is where a reader met them.

    IT COVERS THE COMPOSED CREDIT LINES TOO, and that is where the one remaining case is:
    西沢5ミリ renders as `Nishisawa 5 ミリ`, a credit whose parts are rendered one at a time and one
    of whose parts has no rendering. That is `credits`, not `kana`, so the number is not zero and
    naming why is better than scoping it out.
    """
    n = ctx["names_shipped"] or {}
    bad = 0
    for kind in ("titles", "authors", "publishers", "credit_parts", "phrases"):
        for v in (n.get(kind) or {}).values():
            vals = list((v.get("romaji") or {}).values()) if isinstance(v, dict) else [v]
            for s in vals:
                if isinstance(s, str) and KANA_ANY.search(s):
                    bad += 1
    return bad


def budget_titles_shorter_than_their_own_reading(ctx):
    """Records whose reading states other title information the stored name does not carry.

    A bibliography marks other title information with ISBD's ` : `, and MADB writes that mark into
    the READING of a title even where it has put the words themselves in a field of their own. A
    record holding 怪異部 beside カイイブ : エムケン ワイシ ノ カイゲンショウ ニ ツイテ is a name its
    own catalogue entry contradicts, and the works list showed `Kaii Bu` for a work published as
    怪異部～M県Y市の怪現象について～. 20 records of this corpus were in that state and 17 of them
    are now stated whole.

    WHAT KEEPS THIS NUMBER OFF ZERO, and why that is the honest answer. MADB's
    `schema:alternativeHeadline` is cut short on a few Latin values: 紗痲 states `Fallin` where the
    reading says フォーリン ジェイル, 冷たくて柔らか states `PiNK` where it says
    ピンキー キャンディ キス. `extract.subtitle` refuses those, so the record keeps the shorter name
    and the reading goes on saying there is more. Recovering the words from the kana is the guess
    NAMES-PLAN forbids, so this falls when a source STATES the rest, and not before.

    WHAT IT SHARES WITH ITS SUBJECT (§14b). `extract.subtitle` consults the reading for a Latin
    value and never for a Japanese one, so for the 16 Japanese subtitles this asks a question the
    producer did not, on a field the producer did not write. For the Latin ones it reports the
    refusals, which is the number above and is what it is here to keep visible. It cannot see a
    subtitle MADB states in neither place: 3 of the 20 had no reading of their own and were found
    by looking at the field instead.
    """
    n = 0
    for r in ctx["madb_records"]:
        t = r.get("title") if isinstance(r.get("title"), dict) else {}
        if " : " in str(t.get("yomi") or "") and " : " not in str(t.get("ja") or ""):
            n += 1
    return n


def budget_citations_withheld_from_readers(ctx):
    """Readings holding an address the site may not link to, so the citation is not shown.

    All 36 are NDL creator searches against `ndlsearch.ndl.go.jp/api`, which that host's robots.txt
    disallows (REQUIREMENTS §1). Recording the query we ran is right and linking it would advertise
    a route we agreed not to take, so `provenance.cite` withholds it. A search is also not the
    record that states a reading, so these want the `/books/` page in place of the query however the
    robots rule falls.

    COUNTED BECAUSE THE WITHHOLDING IS SILENT. §4: a reader sees a reading with no citation and a
    reading whose citation we suppressed as exactly the same thing, so without this number the
    suppression is unobservable and could grow without anyone noticing.

    §14b, WHAT IT REUSES: `provenance.uncitable`, which is the same route table `cite` consults, so
    it cannot see a closed route nobody has added to that table. What guards THAT is the table being
    written from the host's robots.txt rather than from what our own fetchers happen to avoid.

    fallback: the reading renders without a citation, exactly as an unsourced one does.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        from names import provenance
    except Exception:                                                       # noqa: BLE001
        return 0
    return sum(len(provenance.uncitable(ctx["names"].get(k) or {}))
               for k in ("titles", "authors"))


def budget_one_page_cited_for_two_claims(ctx):
    """Records citing one page for a reading and an English name that name different source kinds.

    The invariant next door asks whether an address is held. This asks whether it can be the right
    one for both claims, which is a different question and could not be folded into it: every
    record counted here holds an address, so the invariant passes and a reader is still offered a
    citation that did not produce what it sits beside.

    It does not accuse a field, because the borrowing runs both ways. 100日後に咲く百合 cited Yen
    Press for a Japanese reading; thirteen titles are the reverse, where Wikidata really does state
    the reading and our own translation took its address.

    §14b, WHAT IT REUSES: `provenance.borrowed`, which compares two addresses for equality and two
    source kinds for difference. It reads no basis, no lookup table and nothing any pass wrote as a
    judgement, so no producer can make it agree by being consistently wrong. What it cannot see is
    two claims read from different pages on one host, since the addresses then differ and it says
    nothing at all.

    Falls as a reviewer records the page each claim was read from. The floor is not obviously zero:
    犬井あゆ and 野宮りおん cite the shop page their bylines were joined on, while their readings
    come from the National Diet Library, whose record id was never written down and is on no disk
    here.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        from names import provenance
    except Exception:                                                       # noqa: BLE001
        return 0
    return sum(len(provenance.borrowed(ctx["names"].get(k) or {}))
               for k in ("titles", "authors"))



def _shipped_credit_field(ctx):
    """`{work id: the credit field a reader is shown}`, folded once for comparison."""
    return {str(r.get("id")): unicodedata.normalize("NFKC", str(r.get("author") or "")).replace(
        " ", "") for r in ctx["series"] if r.get("id")}


def budget_credit_pages_listing_a_work_that_does_not_name_them(ctx):
    """Pairings a credit page would show whose work does not carry that credit's spelling.

    THE MEASURE THAT DOES NOT SHARE THE PAGE GENERATOR'S BLIND SPOT (§14b), and the fault it is
    aimed at is the one a credit page makes newly possible: a person's page listing somebody else's
    book. Nothing before this could be wrong in that direction, because nothing joined a credit to
    a work; now 4,351 edges do, and every one of them is a public claim that a named person worked
    on a named book.

    EVERYTHING THAT BUILDS THE EDGE ASKS THE SAME THREE THINGS. `credit_identity.credits_on` splits
    the field with `inputs.split_credits_detail`, folds each part with `credit_key`, and resolves
    the fold through `identity.index`. A check that asked any of those could only ever report what
    they already handle, which is exactly how w01478 reached a live page credited
    `田口ケンジ / タグチケンジ` while the budget counting that class read 0.

    SO THIS ASKS THE STRING. It takes the spelling the registry recorded for the credit and looks
    for it inside the credit field of each work the page would list, as shipped. That is substring
    arithmetic over two published fields: it owes nothing to the splitter, nothing to the fold
    beyond NFKC and spaces, which is what the field itself is normalised under, and nothing to the
    registry lookup. A splitter that divided a name in half, a fold that collapsed two people, or a
    merge applied to the wrong pair all land here, and none of them can be hidden by the producer
    agreeing with itself.

    IT COUNTS CANDIDATES AND NOT FAULTS, and the eight it reports are the honest floor rather than
    a queue. Six are MERGES doing exactly what a merge is for: おこさまランチ absorbed お子様ランチ,
    獅尾 absorbed ししお, and the surviving spelling is by construction not the one on every work
    the retired spelling credited. Two are the release rows, which carry edges the works list does
    not, 矢立肇 and 富野由悠季 on w00032 among them.

    That is also what makes a RISE informative. A number that moves without a merge or a new
    release-row edge behind it is a page claiming somebody worked on a book that does not name
    them, and that is the one thing these pages make newly possible.

    WHAT IT CANNOT SEE: an edge whose credit really is in the field and is the wrong person of that
    name. Only a reader following it will know, which is why the seven credits held apart under
    `homophones` were ruled on by hand.
    """
    fields = _shipped_credit_field(ctx)
    n = 0
    for cid, fact in ((ctx["credit_pages"] or {}).get("credits") or {}).items():
        spelling = unicodedata.normalize("NFKC", str(fact.get("credit") or "")).replace(" ", "")
        if not spelling:
            continue
        for w in fact.get("works") or []:
            field = fields.get(str(w.get("id")))
            if field is not None and spelling not in field:
                n += 1
    return n


def budget_publisher_pages_listing_a_work_from_another_house(ctx):
    """Pairings a house page would show whose work names no such publisher on any print row.

    The publisher half of the measure above and independent in the same way. `publisher_identity`
    finds a house by running `publishers.publisher_of` over the field and folding the result; this
    looks for the house's recorded name inside the raw `publisher` and `distributor` strings of the
    work's own print rows, which is arithmetic on two shipped fields and consults neither function.

    A house catalogued under two names it was renamed through would land here, which is the case
    worth finding: 角川書店 became KADOKAWA and the older records were not rewritten, so a merge is
    what settles it and an unmerged pair is a house showing half its shelf.
    """
    by_work = {}
    for r in ctx["series"]:
        raw = " ".join(str(pr.get(f) or "") for pr in (r.get("print") or ())
                       for f in ("publisher", "distributor"))
        by_work[str(r.get("id"))] = unicodedata.normalize("NFKC", raw).replace(" ", "")
    n = 0
    for _hid, fact in ((ctx["publisher_pages"] or {}).get("publishers") or {}).items():
        name = unicodedata.normalize("NFKC", str(fact.get("name") or "")).replace(" ", "")
        if not name:
            continue
        for wid in fact.get("works") or []:
            field = by_work.get(str(wid))
            if field is not None and name not in field:
                n += 1
    return n


def budget_credit_identifiers_naming_nobody(ctx):
    """Live credit identifiers that no work in the corpus is credited to.

    THE RESIDUE OF A FIX, COUNTED SO IT STAYS VISIBLE. All five are one shape: `iimAn&惟丞`,
    `大島永遠&大島智` and three more were single credits because no splitter divided on an
    ampersand, so one address held two artists. Each half holds its own identifier now and the
    joined spelling holds none of their works. The registry is append-only, so the joined entry
    stays and keeps resolving in the data; `pages.py` serves it no page, because heading one with a
    name no source uses and listing nothing under it would assert a credit the corpus has stopped
    making.

    A RISE IS THE THING TO LOOK AT. It means either a credit has left the corpus, which is a page
    withdrawn, or a splitter change has orphaned another joined spelling, which is this fix
    happening again and wants the same read.
    """
    edges = {str(r.get("id")) for r in (ctx["credit_works"] or {}).get("credits") or []}
    return sum(1 for e in (ctx["credits"] or {}).get("credits") or []
               if e.get("id") and not e.get("merged_into") and str(e["id"]) not in edges)


def budget_credit_fields_the_division_does_not_account_for(ctx):
    """Credit fields whose shipped division leaves part of the field unexplained.

    THE NUMBER THAT KEEPS A TIDY ANSWER FROM BEING A LOSSY ONE (§13). The 発売 tab rebuilds a
    byline out of the division, so a division that has lost a contributor would drop that
    contributor from the page in every language with nothing saying so. `creditline.coverage` takes
    the names, the roles and the notation out of the field and reports what is left; where anything
    is, the interface renders the field as written instead of rebuilding it, and this counts how
    often that happens.

    It was 23 when the measure was written and is 0 now: the doubled bracket, the Korean pen names
    and the repeated credit each accounted for a share of it. A rise means the splitter has met a
    shape it cannot divide, and the page it affects is showing the catalogue's own string.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    from names import creditline
    shipped = (ctx["names_shipped"] or {}).get("credit_parts") or {}
    return sum(1 for v in shipped.values() if isinstance(v, dict) and v.get("part"))


BUDGETS_DEF = [
    ("citations withheld from readers", budget_citations_withheld_from_readers,
     "readings whose recorded address is on a route the site may not link to, so the citation is "
     "held back. All of them are NDL creator searches on the disallowed /api path. Falls as the "
     "record page is recorded in place of the query; a rise means a pass stored a query again."),
    ("one page cited for two claims", budget_one_page_cited_for_two_claims,
     "records whose reading and whose English name cite the same page while naming different "
     "kinds of source, so at most one of the two can be right about where it came from. A rise "
     "means an entry carried one address for two claims again."),
    ("kana left in a romanisation", budget_kana_left_in_a_romanisation,
     "strings the shipped names file offers in place of Japanese that still hold a kana character, "
     "which undoes the one job a romanisation has. A rise means a renderer met a kana it has no "
     "table entry for and printed it."),
    ("titles shorter than their own reading", budget_titles_shorter_than_their_own_reading,
     "MADB records whose stated reading carries ISBD's mark for other title information while the "
     "stored name carries none, so the work is held under a name shorter than the one the "
     "catalogue read out. Falls when a source states the missing words; a rise means a route went "
     "back to reading the title out of one field."),
    ("labels with nothing to quote", budget_labels_with_nothing_to_quote,
     "records carrying a publisher-side yuri label whose imprint holds no term saying so, which "
     "is a label the work page cannot show a reader the evidence for. A rise means a pass has "
     "gone back to storing a field from a record other than the one that justified the label."),
    ("titles with no translation of our own", budget_titles_with_no_translation_of_our_own,
     "titles whose only English is the publisher's or the licensor's, so a reader who moves those "
     "down EN_ORDER is shown a romanisation instead of an alternative. A rise means a translation "
     "stopped reaching the shipped file, which is coverage lost and never a tidy-up."),
    ("publishers with no English", budget_publishers_with_no_english,
     "distinct publisher and imprint names that render as Japanese in English-only mode. A rise "
     "means new publishers entered the corpus faster than their names were rendered."),
    ("publisher keys the interface misses", budget_publisher_keys_the_interface_misses,
     "publisher names app.js asks the shipped map for and does not get, normalised the way the "
     "browser normalises. A rise means the two implementations of the cataloguing rule have "
     "drifted, which is the one failure the budget above cannot see."),
    ("an imprint field repeating its publisher", budget_an_imprint_field_repeating_its_publisher,
     "print rows whose imprint field holds the same name as their publisher field, which a shop's "
     "individual-publishing service writes when an artist publishes their own book. There is no "
     "line to name; what moves this is the capture writing one name in one place."),
    ("imprint strings that reach no line", budget_imprint_strings_that_reach_no_line,
     "imprint strings the corpus carries that no entry in data/names/imprints.yaml answers for, so "
     "the string stands as its own object. A coverage deficit: it falls as houses are curated and "
     "it will not reach zero, because some of these are a company name or a magazine sitting in the "
     "imprint field. A rise means new imprint spellings entered faster than they were placed."),
    ("renderings still Japanese in English mode",
     budget_renderings_still_japanese_in_english_mode,
     "rows the interface shows in kana or kanji on an English page, on the surfaces where that is "
     "coverage rather than a fault: a credit line whose role has no gloss, a person with no "
     "reading, a publishing line with no name. The invariant blocks on work titles; this is the "
     "rest, and nothing counted it before."),
    ("credit fields the division does not account for",
     budget_credit_fields_the_division_does_not_account_for,
     "credit fields whose shipped division leaves part of the field unexplained, so the interface "
     "renders the string as the catalogue wrote it instead of rebuilding a byline that would have "
     "lost something. A rise means the splitter met a shape it cannot divide."),
    ("full-width forms in English renderings",
     budget_full_width_forms_in_english_renderings,
     "English renderings holding a full-width character and no kana or kanji, which is what "
     "narrowing the invariant to a script let past. Mostly a Latin pen name catalogued in full "
     "width; some are official titles and are correct, so this will not reach zero."),
    ("interface reads outside an entry point",
     budget_interface_reads_outside_an_entry_point,
     "reads of a name-carrying field in kari/app.js that are excepted in entrypoints.SAFE rather "
     "than going through the function that renders that kind of name. Each names its function, "
     "its field, what is done with the value and how many there are. A rise means a new call site "
     "was argued for instead of using the renderer."),
    ("imprint names the interface disagrees with",
     budget_imprint_names_the_interface_disagrees_with,
     "imprint strings app.js renders as one name and the shipped map calls another, counted as "
     "distinct pairs. It is the second producer of one fact, live and visible to a reader: 一迅社's "
     "yuri line shows as its magazine's name on 346 rows. It goes to zero when the interface reads "
     "feed/names.json's imprints map, and nothing else can move it down."),
    ("names rendered two ways", budget_names_rendered_two_ways,
     "strings the shipped maps spell one way as a publisher and another way as a person, which "
     "happens because a self-published work names its own author as its publisher. A rise means a "
     "publisher name was written by hand where the name store already spelt it."),
    ("publisher readings nobody has settled", budget_publisher_readings_nobody_has_settled,
     "publisher and imprint keys shipped as a romanisation of ours over a reading no source "
     "states, which is what the mark beside them says. A coverage deficit and the other half of "
     "the budget above it: that one reached zero by romanising, and a romanisation is the reading "
     "spelt out. It falls as readings get sourced, and it is measured on the shipped map so that "
     "hiding the mark would show as a fall nobody earned."),
    ("renderings with nothing to show", budget_renderings_with_nothing_to_show,
     "works whose English rendering holds neither a romanisation nor an English name while the "
     "surface is Japanese. A rise means a composed name lost its romanisation."),
    ("kana names with no stated division", budget_kana_names_with_no_stated_division,
     "author names written entirely in kana whose romanisation ships as one unbroken word of eight "
     "letters or more, because the surface states no boundary and the reading is the surface. A "
     "coverage deficit and not a fault count: こかむも is printed Kokamumo by its own publisher and "
     "belongs in this number as much as Igarashiyumiko did. It falls only when a source states a "
     "division, which `a division cites its source` is what enforces, and it never reaches zero."),
    ("author readings no source states", budget_author_readings_no_source_states,
     "author names a reader meets as a romanisation carrying the unverified mark, because the "
     "reading behind the romanisation is a morphological analyser's and nobody else's. A coverage "
     "deficit and not a fault count, and the number a naming round is against. It falls when a "
     "name is sourced or a reviewer weighs a reading, since those are the two bases `build.py` "
     "clears the mark for. A fall with no new citation behind it means the mark stopped rendering, "
     "which is the failure this counts to prevent."),
    ("credits the corpus files as a venue", budget_credits_the_corpus_files_as_a_venue,
     "credits in the author store that this corpus also records as a publisher or an imprint, and "
     "that carry no mark saying what they are. Candidates rather than faults, because a doujin "
     "artist is their own imprint. A rise means a route put a company where a byline goes."),
    ("credits carrying their own cataloguing", budget_credits_carrying_their_own_cataloguing,
     "author records the build publishes no rendering for, which today is a name with a role "
     "welded on to it and the person held separately beside it. A rise means a capture started "
     "writing cataloguing into the author position again."),
    ("credits that restate a name", budget_credits_that_restate_a_name,
     "author fields where one credit is the reading of another, so one person is counted twice. "
     "A rise means a route wrote a name and its reading into one field as two credits."),
    ("credits matching a chapter", budget_credits_matching_a_chapter,
     "author fields holding a credit made only of digits or markup. A rise means a parser folded "
     "something that is not a name into a byline."),
    ("credit fields an identifier does not cover", budget_credit_fields_no_identifier_covers,
     "name-shaped runs of a shipped credit field that no credit identifier accounts for, measured by "
     "deleting the registered spellings out of the field and reading what is left. A rise means a "
     "credit stopped reaching an identifier, and the count owes nothing to the splitter that assigns "
     "them, so it can say so."),
    ("credit pages listing a work that does not name them",
     budget_credit_pages_listing_a_work_that_does_not_name_them,
     "pairings a credit page would show whose work does not carry that credit's spelling in its "
     "own credit field. Substring arithmetic on two shipped fields, so it owes the splitter, the "
     "fold and the registry lookup nothing and cannot be satisfied by them agreeing. It will not "
     "reach zero: six of the eight are merges, where the surviving spelling is by construction not "
     "the one on the retired spelling's works, and two are release-row edges. A rise with neither "
     "behind it is a page claiming somebody worked on a book that does not name them."),
    ("publisher pages listing a work from another house",
     budget_publisher_pages_listing_a_work_from_another_house,
     "pairings a house page would show whose work names no such publisher on any print row. The "
     "publisher half of the measure above and independent the same way. A rise means one house is "
     "showing another's shelf, which is what an unmerged renaming looks like."),
    ("credit identifiers naming nobody", budget_credit_identifiers_naming_nobody,
     "live credit identifiers no work is credited to, so they get no page. All five are joined "
     "spellings the ampersand split left behind, each half now holding its own address. A rise "
     "means a credit left the corpus or another splitter change orphaned a spelling."),
    ("credits sharing a reading nobody has ruled on", budget_credits_sharing_a_reading_nobody_ruled_on,
     "readings the shipped name map gives to several credits with no ruling on the pair. Should be "
     "0: a rise means a newly sourced reading has put two credits together and nobody has said "
     "whether they are one credit written twice or two names that sound alike."),
    ("implausible ruby spans", budget_implausible_ruby_spans,
     "furigana runs holding fewer kana than they have kanji. A rise means the aligner placed a "
     "boundary somewhere no reading could fall, which the spelling check cannot see."),
    ("uncertain readings", budget_uncertain_readings,
     "readings assembled character by character because no analyser could read the word. A rise "
     "means new works whose kanji nothing can read, or a regression in the analyser passes."),
    ("works without English", budget_works_without_english,
     "works that render in Japanese in English-only mode. Should be 0; a rise means the automatic "
     "naming pass stopped covering something it used to."),
    ("works showing a romanisation", budget_works_without_an_english_name,
     "works with no English name, showing a romanisation instead. Distinct from the budget above, "
     "which a romanisation satisfies: this is the one that answers 'can a reader tell what this "
     "is'. Never reaches zero, because romanising is right for a coinage."),
    ("titles carrying cataloguing punctuation", budget_titles_carrying_cataloguing_punctuation,
     "titles a reader is shown that still hold a bibliography's own ISBD markup: an equals sign "
     "in any spelling, or a reissue marker from the closed set adapters/isbd.py holds. A subtitle "
     "after the same colon is content and is not counted. A rise means a capture route wrote a "
     "catalogue string through as a name."),
    ("works offered twice in a list", budget_works_offered_twice,
     "rows beyond the first that a shipped list gives to one identity work. 41 works were listed "
     "twice or three times in index.json, which emitted one row per source record and asked "
     "identity nothing. A rise means a collapse stopped running, or a new list shipped without "
     "asking which work a record belongs to."),
    ("one work under two names in a list", budget_one_work_under_two_names,
     "pairs of rows in one list whose titles fold equal and whose credits share a person, which is "
     "one work offered twice under two names. Measured on the shipped rows and never on the "
     "identity registry, so it reports the pairs the registry has not joined. A queue rather than "
     "a fault count: each pair needs deciding, and the number falls by deciding them."),
    ("incomplete attested rows", budget_incomplete_attested_rows,
     "attested releases missing a chapter name, author or access state. The classic sign of a "
     "moved CSS selector — the adapter still returns rows, just emptier ones."),
    ("stock phrasing in comments", budget_stock_phrasing_in_comments,
     "stock phrasing and filler in comments, docstrings and documentation, plus em dashes, which "
     "are a budget here and zero in public text. Public prose is an invariant instead; this is the "
     "backlog and it ratchets down. See adapters/lint/tics.py for what is deliberately not "
     "flagged, and why legibility beats camouflage."),
    ("invented markup in tests", budget_invented_markup_in_tests,
     "page-shaped string literals of 200 characters or more in test files, which is markup "
     "somebody wrote from memory standing in for a page. Falls as tests move to "
     "data/fixtures/; does not reach zero, because some platforms have no cached page to cut. "
     "A rise means a test went back to inventing one."),
    ("nicovideo works with no rights", budget_nicovideo_works_with_no_rights,
     "ニコニコ works captured with no copyright line read off their page, which is the only field "
     "the platform gives that names a publisher. Falls when the capture re-runs against the "
     "widened pattern; does not reach zero, because a work its own author posted carries no "
     "copyright element at all."),
    ("modules without a test", budget_untested_modules,
     "Python modules no suite covers. Offline tests are the enforcement for factoring as well: a "
     "module that cannot be tested without a network has not separated its logic from its I/O, so "
     "this number falling is the refactoring, not a proxy for it."),
    ("adapters fetching without net.py", budget_adapters_fetching_without_net,
     "modules that call urlopen themselves instead of going through adapters/net.py, and so have "
     "no per-host pause, no retry for a 503, no status code to tell an absent work from a refused "
     "request, and no sight of a redirect. Falls as each one is migrated. Its floor is not zero: "
     "adapters/editions/capture.py sends one route an extra header and keeps everything else "
     "net.py has, and a route that must not be fetched at all should not be made convenient."),
    ("captures with no floor", budget_unguarded_captures,
     "adapters that fetch from a host, write into data/source, and have nothing to refuse on. A "
     "host serving nonsense replaces the last good capture and reports success. adapters/ledger.py "
     "reports the damage afterwards; a floor prevents it."),
    ("unreadable bookwalker rows", budget_unreadable_bookwalker_rows,
     "rows admitted from BOOK☆WALKER's shelf with no first publication VENUE, which is what §6's "
     "scope test turns on since the 2026-08-05 amendment. A row without one has not been fetched "
     "yet, or its series page listed nothing readable. Falls as "
     "adapters/recon/bookwalker_volumes.py works through the queue, and reaches zero when it "
     "finishes. The date is deliberately not what is counted: 1,500 of these titles are "
     "digital-only, have no print edition anywhere, and are complete records without one."),
    ("bookwalker series unread", budget_bookwalker_series_unread,
     "BOOK☆WALKER rows whose series listing has not been read to the end, so their volume list "
     "and the first publication drawn from it rest on whichever volumes were fetched. The shelf "
     "linked one volume for 1,175 of them and this module read only page one of a paginated "
     "listing for a few more. Falls as adapters/recon/bookwalker_volumes.py --follow-series works "
     "through them, and reaches zero, because every row counted here names a series to fetch."),
    ("bookwalker listings unconfirmed", budget_bookwalker_listings_unconfirmed,
     "BOOK☆WALKER rows whose series listing was read before the reader compared what it read "
     "against the shop's own 全N件. Until 2026-08-06 the last row of a listing swallowed the "
     "markup printed underneath it and was identified by the related-series link in there, so it "
     "was dropped; a listing is sorted newest first, so the row dropped is the OLDEST volume and "
     "`first_publication` is the earliest date across the volumes read. Falls as "
     "adapters/recon/bookwalker_volumes.py --follow-series re-reads them, and reaches zero, "
     "because every row counted here names a series to fetch."),
    ("volumes with an isbn and no date", budget_volumes_with_an_isbn_and_no_date,
     "volumes on a work page stating an ISBN and no publication date. An ISBN is a key into a "
     "registry that states one, so each of these is a lookup nobody has done. Falls as "
     "adapters/openbd/enrich.py --fetch works through the corpus. Its floor is the books openBD "
     "has no record of, which was 245 of 2,321 ISBNs when this was written."),
    ("undated cmoa candidates", budget_undated_cmoa_candidates,
     "the same count for the コミックシーモア half of the queue, falling as adapters/cmoa_volumes.py "
     "works through it. Its floor is high and known: cmoa states an ISBN or an 出版年月 only where "
     "a volume was printed, and 754 of the 1,844 rows come from two digital distributors whose "
     "pages carry neither."),
    ("three as an organising shape", budget_structural_triples,
     "lists of exactly three items, and runs of three bold-led paragraphs, in documents that ship "
     "at 1.0. Three reads as rhetoric; four reads as an inventory. When there really are three "
     "things, write them as prose or find the fourth that was left out to make the shape work."),
    ("scraped counters in chapter names", budget_scraped_counters_in_chapter_names,
     "chapter names ending in the view or like counts printed next to them on the source page. A "
     "rise means an extractor has gone back to flattening a chapter block into one run of text "
     "instead of reading the element the page names as the title."),
    ("shadowed names in build.py", budget_shadowed_names,
     "names rebound more than 300 lines from their first binding. Two shipped bugs came from this; "
     "see adapters/lint/shadowing.py for why the count is not simply falling."),
    ("updates naming a work we do not hold", budget_updates_naming_an_unheld_work,
     "release rows whose work has no record, so the row links to the platform and nowhere else and "
     "the work cannot be browsed, searched or classified. Coverage stated as a deficit, because "
     "there is no floor to hold it up: it falls as the works are judged against DEFINITIONS §2 and "
     "given records, and it reaches zero, since every row counted here names a work to decide "
     "about. A rise means a discovery pass has started reporting updates for works no capture "
     "covers. Rulings already made are in data/queue/unheld-works.yaml and reduce nothing."),
    ("targets a capture wrote no row for", budget_targets_a_capture_wrote_no_row_for,
     "works a platform pass was given as a target and wrote no row for. The pass put each in a "
     "`failed` list, printed it and dropped it, so until now a work asked for and not got left "
     "nothing in the repository at all. A rise means a pass has stopped resolving something it "
     "used to, which is either an address that moved or a platform that withdrew a work. It falls "
     "when the target is captured, or when a platform's refusal is written into a register the "
     "count reads, as data/source/kadokomi/withheld.yaml already is."),
    ("rows with a moving address", budget_rows_with_a_moving_address,
     "rows anchored on a chapter address whose identifier holds no work-level address on the same "
     "host. A chapter address moves when the work publishes, so a rise means a work has arrived "
     "whose address nobody has read yet and which would be minted a second identifier the next "
     "time it updates. Run adapters/gigaviewer/workaddress.py and apply what it writes with "
     "identity.py --attachments."),
]


# ── Running ───────────────────────────────────────────────────────────────────────────────────

def context():
    releases = []
    cur = _load(BUILD / "feed" / "current.json", {})
    releases += cur.get("releases", [])
    for f in sorted((BUILD / "feed").glob("[0-9]*-[0-9]*.json")):
        releases += (_load(f, {}) or {}).get("releases", [])
    # Loaded HERE rather than in each check that wants it, so a canary planted in the context
    # reaches every one of them. A check that reads its own file off disk cannot be shown a
    # canary at all, and self_test then reports it healthy without ever having exercised it.
    works = _load(BUILD / "works.json", []) or []
    return {
        "releases": releases,
        "works": works.get("works") if isinstance(works, dict) else works,
        # THE BIBLIOGRAPHIC LIST AS SHIPPED. Nothing here read it until 41 works were found listed
        # twice in it, which is the state a file can reach when it is deployed and measured by
        # nothing. Loaded with the rest so a canary can be planted in front of the checks that use
        # it, for the reason the comment above gives.
        "index": _load(BUILD / "index.json", []) or [],
        # THE INTERFACE'S OWN SOURCE. Read here for the same reason as everything else: a check that
        # opens its own file cannot be shown a canary, and this one is holding a copy of a Python
        # function to its original.
        "interface_js": ((SITE_ROOT / "kari" / "app.js").read_text()
                         if (SITE_ROOT / "kari" / "app.js").exists() else ""),
        # status.html's script, read here for the same reason app.js is. It is a published page
        # and nothing had ever asked it what it shows.
        "status_js": ((SITE_ROOT / "kari" / "app-status.js").read_text()
                      if (SITE_ROOT / "kari" / "app-status.js").exists() else ""),
        "status": _load(BUILD / "status.json", {}) or {},
        "series": (_load(BUILD / "series.json", {}) or {}).get("series", []),
        "names": {k: ((_yaml(NAMES / f"{k}.yaml", {}) or {}).get("names") or {})
                  for k in ("titles", "authors")},
        "names_shipped": _load(BUILD / "feed" / "names.json", {}),
        "cmoa_capture": _capture_works("data/queue/cmoa-volumes.yaml"),
        "identity": (_yaml(ROOT / "data" / "identity" / "works.yaml", {}) or {}).get("works") or [],
        # THE CREDIT REGISTRY AND WHAT WAS RULED ABOUT IT. Whole documents rather than their `credits`
        # lists, because two of the three checks below read a second key: the rulings file is asked
        # which pairs are settled and the edge file which identifiers a work points at. Loaded here so
        # a canary can be planted in front of them.
        "credits": _yaml(ROOT / "data" / "identity" / "credits.yaml", {}) or {},
        # THE TWO FILES THE NEW PAGES ARE BUILT FROM. Loaded here with everything else so a canary
        # can be planted in front of the checks that read them; a check that opens its own file
        # cannot be shown one, and self_test then reports it healthy having exercised nothing.
        "credit_pages": _load(BUILD / "credits.json", {}) or {},
        "publisher_pages": _load(BUILD / "publishers.json", {}) or {},
        "credit_rulings": _yaml(ROOT / "data" / "identity" / "credit-rulings.yaml", {}) or {},
        "credit_works": _yaml(ROOT / "data" / "identity" / "credit-works.yaml", {}) or {},
        # THE SOURCE LAYER, not the build. Two checks below ask what the RECORD states, because
        # that is where the fact is produced and a build in between can only lose it. Loaded here
        # with everything else so a canary can be planted in front of them; a check that opens its
        # own file cannot be shown one, and self_test then reports it healthy having exercised
        # nothing.
        "madb_records": _madb_records(),
        # WHAT EACH CAPTURE PASS WAS TOLD TO READ, BESIDE WHAT IT WROTE. Held as the two
        # collections and not as the answer, so a canary can be planted on either side of the
        # join: a target added, or a captured row taken away, which is the failure itself.
        "capture_passes": _capture_passes(),
        # Both sides of the ニコニコ channel comparison, loaded here for the same reason as the
        # two above: a check that opens its own file cannot be shown a canary.
        "nicovideo_channels": (_yaml(ROOT / "data" / "source" / "nicovideo" / "nicovideo.yaml",
                                     {}) or {}).get("works") or [],
        "nicovideo_recorded_channels": _nicovideo_recorded_channels(),
        # THE RAW TEXT, not the parsed header, for the reason the comments above give and for one
        # more: the check that matters here recomputes the body digest, and it can only do that on
        # bytes nobody has re-serialised on the way in.
        "fixtures": _fixture_files(),
    }


def _fixture_files():
    """`{name: raw text}` for every committed fixture."""
    d = ROOT / "data" / "fixtures"
    return {str(p.relative_to(d))[: -len(".fixture")]: p.read_text(encoding="utf-8")
            for p in sorted(d.rglob("*.fixture"))} if d.exists() else {}


def _plant_edge_on_a_retired_credit(c):
    """Point a work's credit edge at an identifier a merge has retired.

    THE CANARY IS A STATE THE PIPELINE PRODUCES (§14b). `identity.index` resolves a retired anchor
    to its successor, so an edge lands on the survivor as long as the resolution runs. Skipping it
    is what put 13 print pairs into one row under one id in the works registry, and the same slip
    here would leave a work linking to an address that forwards somewhere else.
    """
    retired = next((e["id"] for e in (c["credits"] or {}).get("credits") or []
                    if e.get("merged_into")), None)
    if retired:
        c["credit_works"].setdefault("credits", []).append({"id": retired, "works": [{"id": "w1"}]})


def _capture_passes():
    """Every platform pass, holding its target list and the rows its captures state."""
    sys.path.insert(0, str(ROOT / "adapters"))
    import capturegap
    return capturegap.load(ROOT, read=lambda p: _yaml(p, {}) or {})


def _plant_edited_fixture(c):
    """One committed fixture, with its markup changed and its digest left alone.

    THE CANARY IS THE REAL FILE (§14b), not a shape invented for the probe: a fixture that has been
    edited to make a failing test pass keeps a header that says where it came from and stops being
    the page it names. Nothing else here can see that.
    """
    name = next(iter(c["fixtures"]), None)
    if name:
        c["fixtures"][name] = c["fixtures"][name] + "\n<div>a line nobody captured</div>"


def _anonymous_fixture():
    """Markup with a well-formed digest and nothing saying where it came from."""
    import hashlib as _h
    body = "<div>markup somebody wrote</div>"
    return (f"body_sha256: {_h.sha256(body.encode()).hexdigest()}\nformat: html\n"
            f"---\n{body}")


def _nicovideo_recorded_channels():
    """`{comic_id: channel}` for the ニコニコ works whose channel a person wrote down.

    These files settle identity by hand, one confirmed search result at a time, and the adapter
    reads no channel out of either. That is what makes them a second record of the fact rather
    than an echo of the first.
    """
    out = {}
    for rel in ("data/source/nicovideo/resolved.yaml",
                "data/source/webpages/nicovideo-titles.yaml"):
        for w in (_yaml(ROOT / rel, {}) or {}).get("works") or []:
            cid = str(w.get("comic_id") or "")
            if not cid:
                m = re.search(r"manga\.nicovideo\.jp/comic/(\d+)", str(w.get("url") or ""))
                cid = m.group(1) if m else ""
            if cid and w.get("channel"):
                out[cid] = w["channel"]
    return out


def _madb_records():
    """Every source-layer record the MADB adapter wrote, as parsed documents."""
    out = []
    for f in sorted((ROOT / "data" / "source" / "madb").glob("*.yaml")):
        doc = _yaml(f, None)
        if isinstance(doc, dict):
            out.append(doc)
    return out


def _capture_works(rel):
    """The work rows of a retailer capture, as a list, or an empty one where the file is absent."""
    doc = _yaml(ROOT / rel, {}) or {}
    works = doc.get("works") or []
    return list(works.values()) if isinstance(works, dict) else works


def _plant_stale_translation(c):
    """Make one store translation disagree with the curated file, which is the fault exactly."""
    for kind, rows in _curated().items():
        for name, rec in rows.items():
            if (rec or {}).get("en") and name in (c["names"].get(kind) or {}):
                c["names"][kind][name] = dict(c["names"][kind][name] or {},
                                              en="CANARY STALE VALUE")
                return


def _plant_nicovideo_banner(c):
    """File ONE work whose channel we recorded under the sidebar's banner, as the adapter did."""
    for r in c["nicovideo_channels"]:
        if str(r.get("comic_id") or "") in c["nicovideo_recorded_channels"]:
            r["channel"], r["channel_slug"] = "ニコニコ漫画（公式）", "nicomanga"
            return


def _plant_one_nicovideo_channel_for_all(c):
    """Give every work the same channel, which is the shape of a value read off a fixed element.

    The value is one we really recorded, so the comparison agrees with all four of its rows and
    only the uniformity clause is left to object.
    """
    one = next(iter(c["nicovideo_recorded_channels"].values()), "きららベース")
    for r in c["nicovideo_channels"]:
        r["channel"] = one


def _plant_imprint_under_another_house(c):
    """File a shipped imprint spelling under a company that does not run that line.

    Taken out of the shipped map so the canary is a string the build wrote, and the house is one the
    corpus already holds, so the row differs from a real one only in the join being wrong. Where the
    map is empty the check has nothing to say and the probe plants nothing, which self_test reports
    as an uncaught canary instead of passing quietly.
    """
    shipped = (c["names_shipped"] or {}).get("imprints") or {}
    spelling = next((k for k, v in sorted(shipped.items()) if (v or {}).get("publishers")), None)
    if spelling:
        c["series"].append({"id": "CANARY", "work": "CANARY",
                            "print": [{"work_id": "CANARY", "publisher": "講談社",
                                       "imprint": spelling}]})


def self_test():
    """Prove the invariants can fail. A check that cannot demonstrate a catch is not a check."""
    import copy
    ctx = context()
    if not ctx["releases"]:
        print("  self-test SKIPPED — no build output to plant a canary in")
        return True
    probes = [
        ("feed holds only attested rows", inv_feed_is_attested,
         lambda c: c["releases"].append({"work": "CANARY", "provenance": "claimed"})),
        ("every update has a kind", inv_no_unknown_kind,
         lambda c: c["releases"].append({"work": "CANARY", "kind": "unknown"})),
        ("readings are stored as kana", inv_readings_are_kana,
         lambda c: c["names"]["titles"].update({"カナリア": {"reading": "Kanaria Romaji"}})),
        # BOTH CANARIES ARE RECORDS THE PIPELINE REALLY WROTE, which is §14b's requirement and not
        # a stylistic preference: a canary invented for the test proves the check can fail on
        # something nothing produces. The first is #ふれない as curate.py left it, the second is
        # 古川楊也 as its refutation left it, and both were live in data/names on 2026-08-07.
        ("a reading can show its source", inv_reading_can_show_its_source,
         lambda c: c["names"]["titles"].update({"カナリア": {
             "reading": "フレナイ", "reading_basis": "stated", "reading_source": "yurarium",
             "reading_source_kind": "derived"}})),
        ("a reading can show its source", inv_reading_can_show_its_source,
         lambda c: c["names"]["authors"].update({"カナリア": {
             "reading_source": "sudachi", "reading_at": "2026-08-06",
             "reading_url": "https://www.mangaupdates.com/author/0fnry5y/hoshino-katsura",
             "reading_refuted": "the reading of a different person's name"}})),
        ("English mode has no Japanese", inv_english_mode_has_no_japanese,
         lambda c: c["releases"].append({"work": "カナリア", "provenance": "attested"})),
        # THE CANARY IS THE FAULT THAT SHIPPED (§14b). The catalogue tab really did print
        # index.json's title with `esc` instead of asking workLabel for it, and 2,430 rows stayed
        # Japanese in English mode. Planted in the SOURCE the context holds, so the probe reaches
        # the same string the check reads.
        ("names reach a page only through their renderer",
         inv_names_reach_a_page_only_through_their_renderer,
         lambda c: c.update({"interface_js": (c.get("interface_js") or "").replace(
             "${workLabel({ work: w.t })}", "${esc(w.t)}")})),
        # THE CANARY IS THE TABLE LOSING AN ENTRY, planted in the SOURCE the context holds so it
        # reaches the file the check evaluates. 著 is the commonest role in the corpus by a long
        # way, 766 credits state it, and it was in the six-word table this replaced, so a round
        # that rewrites `ROLE_EN` and drops it is not a hypothetical.
        ("every credit role has an English gloss", inv_every_credit_role_has_an_english_gloss,
         lambda c: c.update({"interface_js": (c.get("interface_js") or "").replace(
             "'著': 'author', '著者': 'author',", "'著者': 'author',")})),
        # AND THE SAME LOSS SEEN FROM THE OTHER END. The line still renders and the name is still
        # replaced; what is left is `[著]` standing in the middle of an English credit, which is
        # what a reader would meet. One fault, two checks, and they fail for different reasons:
        # the first reads the table, the second reads the page.
        ("no cataloguing notation in an English rendering",
         inv_no_cataloguing_notation_in_an_english_rendering,
         lambda c: c.update({"interface_js": (c.get("interface_js") or "").replace(
             "'著': 'author', '著者': 'author',", "'著者': 'author',")})),
        # THE STATUS PAGE WRITING A SENTENCE OF ITS OWN IN JAPANESE. Planted in the SOURCE the
        # context holds, the same way the entry-point probe is, so it reaches the file the check
        # evaluates. `T('統計', 'Statistics')` is a pair; dropping the English half is what a
        # section added in a hurry looks like.
        ("status.html shows no Japanese of its own",
         inv_status_page_shows_no_japanese_of_its_own,
         lambda c: c.update({"status_js": (c.get("status_js") or "").replace(
             "T('統計', 'Statistics')", "T('統計', '統計')")})),
        # A field carrying Japanese that nothing has ruled on, which is what every pass adding a
        # field looks like from here.
        ("every Japanese field the data carries has a ruling", inv_every_japanese_field_has_a_ruling,
         lambda c: c["series"].append({"work": "CANARY", "a_field_nobody_ruled": "日本語"})),
        ("undated works say where and why", inv_undated_works_say_where_and_why,
         lambda c: c["works"].append({"work_id": "CANARY", "first_publication": {"date": None}})),
        # A row holding both dates, which is what the fold in build.py can produce.
        ("a delivery date never stands beside a printing",
         inv_a_delivery_date_never_stands_beside_a_printing,
         lambda c: c["series"].append({"work": "CANARY", "id": "CANARY",
                                       "print": [{"delivered_from": "2018-07-18",
                                                  "first": "2007-11"}]})),
        ("per-book dates cite their page", inv_per_book_dates_cite_their_page,
         lambda c: c["cmoa_capture"].append({"shop_id": "CANARY",
                                             "first_publication_basis": "publisher-own-page"})),
        # A year read out of a plot summary, which is the failure this rule can produce: the shop
        # began delivering the file in 2015 and the sentence claims it was printed in 2019.
        ("a stated printing precedes the delivery", inv_a_stated_printing_precedes_the_delivery,
         lambda c: c["cmoa_capture"].append({
             "shop_id": "CANARY", "first_publication_basis": "shop-blurb-print-date",
             "first_publication_date": "2019-04", "volumes": [{"delivered": "2015-08-18"}]})),
        # A second row claiming an id the first row already holds, which is what a merge produced.
        ("one row per identifier", inv_one_row_per_identifier,
         lambda c: c["series"].append({"id": next(r["id"] for r in c["series"] if r.get("id")),
                                       "work": "CANARY"})),
        ("first date precedes its editions", inv_first_date_precedes_its_editions,
         lambda c: c["series"].append({"id": "CANARY", "work": "CANARY", "first": "2030-01",
                                       "print": [{"first": "2000-01"}]})),
        ("curated values reach the store", inv_curated_values_reach_the_store,
         _plant_stale_translation),
        # Ruby whose bases no longer add up to the title they annotate.
        ("ruby covers its surface", inv_ruby_covers_its_surface,
         lambda c: c["series"].append({"id": "CANARY", "work": "カナリア",
                                       "work_en": {"ruby": [["ちがう", None]]}})),
        # A row that begins after it ended.
        ("dates within a row are ordered", inv_dates_within_a_row_are_ordered,
         lambda c: c["series"].append({"id": "CANARY", "work": "CANARY",
                                       "first": "2030-01", "latest": "2020-01"})),
        # The distributor MADB names ahead of the publisher, stored as the publisher.
        ("a publisher is a name, not a role", inv_publisher_is_a_name_not_a_role,
         lambda c: c["madb_records"].append({"work_id": "CANARY", "publisher": "[発売]講談社"})),
        # A SPELLING THE MAP REALLY HOLDS, PUT UNDER A HOUSE THAT DOES NOT RUN IT (§14b). The
        # invented version of this canary would be a made-up imprint, which proves only that the
        # dictionary lookup works. This takes the first spelling the build shipped and files it
        # under 講談社, which is the shape a substring match produces: the 一迅社 pattern that
        # opened this work reached KADOKAWA's BRIDGE COMICS in exactly that way.
        ("an imprint spelling belongs to its own publisher",
         inv_imprint_spelling_belongs_to_its_own_publisher, _plant_imprint_under_another_house),
        # BOTH CANARIES ARE THE FILE AS IT STOOD ON 2026-08-07 (§14b), not an invented bad value:
        # every work was filed under ニコニコ漫画（公式）, the first banner in the sidebar. The
        # first plants it on one recorded work, so only the comparison can catch it; the second
        # plants a channel that IS recorded on every work, so only the uniformity clause can.
        # Probing them together would let either cover for the other going quiet.
        ("nicovideo channels agree with our own records", inv_nicovideo_channel_agrees,
         _plant_nicovideo_banner),
        ("nicovideo channels agree with our own records", inv_nicovideo_channel_agrees,
         _plant_one_nicovideo_channel_for_all),
        # BOTH OF THESE CANARIES ARE STRINGS THE PIPELINE REALLY PRODUCES (§14b), which is a
        # different claim from a canary the check happens to catch. openBD returns トリイ シズク for
        # とりいしづく, with づ folded to ず by the collation, and the only thing keeping it out of
        # the store is `openbd_reading.normalised` refusing it. SudachiPy divides あいかわももこ as
        # アイ カワ モモコ with the kana untouched, and it would divide 206 of the 354 names that
        # have no stated boundary, あかまる as ア カマル among them.
        ("a kana name's reading spells it", inv_kana_reading_spells_its_name,
         lambda c: c["names"]["authors"].update({"とりいしづく": {"reading": "トリイ シズク"}})),
        ("a division cites its source", inv_a_division_cites_its_source,
         lambda c: c["names"]["authors"].update({"あいかわももこ": {
             "reading": "アイ カワ モモコ", "reading_basis": "analyser",
             "reading_source": "sudachi", "reading_source_kind": "analyser"}})),
        # THE SAME FAULT WITH THE NOTATION TIDIED OFF, which is what the pipeline can actually
        # produce and what the canary above cannot prove is caught (§14b). A bracket planted into
        # the context is downstream of the adapter that removes brackets, so it exercises a shape
        # nothing upstream can still emit.
        ("a publisher is a name, not a role", inv_publisher_is_a_name_not_a_role,
         lambda c: c["madb_records"].append({"work_id": "CANARY", "publisher": "講談社",
                                             "publisher_stated": "[発売]講談社"})),
        # THE STRING THE PIPELINE REALLY WROTE (§14b), not one invented for the canary. The
        # nicovideo capture stored exactly this until the parser was taught to unescape, and the
        # romanisation built from it reached readers.
        ("no HTML entity in a stored name", inv_no_html_entity_in_a_stored_name,
         lambda c: c["series"].append({"work": "ひよ&amp;びびっと!"})),
        # A publisher field left empty with nothing saying which kind of empty it is.
        ("a record without a publisher says why", inv_a_record_without_a_publisher_says_why,
         lambda c: c["madb_records"].append({"work_id": "CANARY", "publisher": ""})),
        # ONE CANARY PER WAY THE CHECK CAN FAIL, so that none of them can cover for another going
        # quiet. A fixture whose markup was edited after capture, which is how a failing test gets
        # quietly made to pass. A page pasted in with no header at all, which is the state this
        # exists to make impossible. Markup carrying a header that says nothing about where it came
        # from, which is an invented page wearing a fixture's clothes.
        ("a fixture states where it came from", inv_fixture_states_where_it_came_from,
         _plant_edited_fixture),
        ("a fixture states where it came from", inv_fixture_states_where_it_came_from,
         lambda c: c["fixtures"].update({"CANARY": "<div>a page somebody pasted in</div>"})),
        # ITS DIGEST IS CORRECT, so only the header requirements can catch this one. Giving it a
        # wrong digest too would let the arithmetic above cover for `fixtures.problems` going
        # quiet, and the two are asserting different things.
        ("a fixture states where it came from", inv_fixture_states_where_it_came_from,
         lambda c: c["fixtures"].update({"CANARY": _anonymous_fixture()})),
        # A RETIREMENT THAT REACHES NOTHING. This is the state the work registry was in when 20 of
        # its 26 retired ids had no forwarder: `merged_into` recorded and nothing live at the end of
        # it, so the address resolved nowhere and no stub could be written for it.
        ("every credit identifier resolves", inv_credit_identifiers_resolve,
         lambda c: c["credits"].setdefault("credits", []).append(
             {"id": "c99999", "credit": "カナリア", "merged_into": "c99998",
              "merge_basis": "a canary", "anchors": ["credit:カナリア"]})),
        # AND A WORK POINTING AT AN ADDRESS THAT FORWARDS, which is the same fault from the other
        # side and is what put 13 print pairs into one row under one id.
        ("every credit identifier resolves", inv_credit_identifiers_resolve,
         _plant_edge_on_a_retired_credit),
        # A NAME CARRYING AN ADDRESS NOTHING ANSWERS FOR, which is what a fold drifting apart
        # produces and produces silently: the link renders, the page it opens is blank. The canary
        # is the shape the pipeline makes, an `id` on a shipped author record, not an invented key.
        ("a shipped identifier resolves", inv_a_shipped_identifier_resolves,
         lambda c: c["names_shipped"].setdefault("authors", {}).update(
             {"カナリア": {"reading": "カナリア", "id": "c99999"}})),
        ("a shipped identifier resolves", inv_a_shipped_identifier_resolves,
         lambda c: c["names_shipped"].setdefault("publishers", {}).update(
             {"カナリア社": {"en": "Canary", "id": "h99999"}})),
    ]
    ok = True
    for name, fn, plant in probes:
        c = copy.deepcopy(ctx)
        plant(c)
        if not fn(c):
            print(f"  self-test FAILED — '{name}' did not catch its canary")
            ok = False

    # A BUDGET IS A COUNT AND CANNOT BE PROBED THE SAME WAY, so one is probed here on the number
    # instead of on a pass. `titles carrying cataloguing punctuation` is the one that needs it: it
    # measures a class its subject deliberately refuses to act on, and a count that reads 3 and a
    # count that cannot rise above 3 look identical from outside (§14b). The canary is a fullwidth
    # equals sign, which `isbd.areas` would never split and this must still see.
    c = copy.deepcopy(ctx)
    was = budget_titles_carrying_cataloguing_punctuation(c)
    # BOTH ARE PLANTED AS WORKS, because that is what this counts now. It used to walk works.json
    # too, where a record faithfully transcribes an edition it is filed under, so one canary sat in
    # each layer. A record is not a title a reader is shown.
    c["series"].append({"id": "CANARY1", "work": "カナリア＝CANARY"})
    c["series"].append({"id": "CANARY2", "work": "カナリア : 完全版"})
    if budget_titles_carrying_cataloguing_punctuation(c) != was + 2:
        print("  self-test FAILED — 'titles carrying cataloguing punctuation' did not count "
              "its canaries")
        ok = False

    # THE INTERFACE'S OWN COPY OF THE FOLD, changed to what it looked like before the two were held
    # together: NFKC and no space stripping, which is `curate._fold` and is what made "the same key"
    # mean two things. The canary is a real state of this repository and not an invented one.
    c = copy.deepcopy(ctx)
    c["interface_js"] = (c.get("interface_js") or "").replace(
        "return (t || '').normalize('NFKC').replace(/ /g, '');",
        "return (t || '').normalize('NFKC');")
    if not inv_interface_folds_a_name_key_as_the_build_does(c):
        print("  self-test FAILED — 'the interface folds a name key as the build does' did not "
              "catch a fold that stops stripping spaces")
        ok = False

    # THE CANARY IS THE STATE THE BUILD WAS IN THIS MORNING (§14b), not a shape invented for the
    # probe. `index.json` really did carry two rows for w00901, one titled スクールゾーン and one
    # titled School zone = スクールゾーン, each naming its own record, and that is what an uncollapsed
    # list looks like. Both new budgets are probed on it and they must answer differently: the
    # registry-based one sees the two records land on one work, and the pairs one cannot, because
    # the two titles do not fold equal. That difference is the reason both exist.
    c = copy.deepcopy(ctx)
    _reg = next((e for e in c["identity"] if len(
        [a for a in (e.get("anchors") or []) if a.startswith("madb:")]) >= 2), None)
    if _reg:
        # The two lists are replaced rather than appended to, so the probe answers a number and not
        # a delta. Two records of one work already collapsed into one row would make an appended
        # canary raise the count by two, and a probe whose expected value depends on data it did
        # not plant is the kind that goes quiet without anyone noticing.
        _mad = [a[len("madb:"):] for a in _reg["anchors"] if a.startswith("madb:")]
        c["series"] = []
        c["index"] = [{"id": _mad[0], "ids": [_mad[0]], "t": "カナリア", "c": "犬"},
                      {"id": _mad[1], "ids": [_mad[1]], "t": "Canary = カナリア", "c": "犬"}]
        if budget_works_offered_twice(c) != 1:
            print("  self-test FAILED — 'works offered twice in a list' did not count a work "
                  "given two rows")
            ok = False
        # AND THE PAIRS BUDGET MUST MISS IT, which is why both exist. The two titles do not fold
        # equal, so nothing about the rows themselves says they are one work; only the registry does.
        if budget_one_work_under_two_names(c) != 0:
            print("  self-test FAILED — 'one work under two names in a list' claimed to see a pair "
                  "only the registry can join")
            ok = False
    else:
        print("  self-test FAILED — no joined work in the registry to plant a canary on")
        ok = False

    # A PAIR THE REGISTRY HAS NOT JOINED, which is the only kind this one can see. Two rows folding
    # to one title with a person in common: the shape くちびるためいきさくらいろ has in the shipped
    # list today. The bracketed edition marker is there because `fold` removes it, so a collected
    # edition beside its volumes is one work with two rows and has to be counted.
    c = copy.deepcopy(ctx)
    c["index"] = []
    c["series"] = [{"work": "カナリア", "author": "犬井カナ"},
                   {"work": "カナリア【合本版】", "author": "犬井カナ"}]
    if budget_one_work_under_two_names(c) != 1:
        print("  self-test FAILED — 'one work under two names in a list' did not count its pair")
        ok = False
    # AND IT MUST NOT COUNT A SHARED TITLE ALONE. Seven works are called 人魚姫 by seven authors, and
    # a rule keying on the title would report every pair of them.
    c["series"][-1] = {"work": "カナリア【合本版】", "author": "別人"}
    if budget_one_work_under_two_names(c) != 0:
        print("  self-test FAILED — 'one work under two names in a list' counted two authors' "
              "works as one")
        ok = False
    # A CREDIT THAT NO LONGER REACHES AN IDENTIFIER, which is the fault this measure exists for and
    # the one a measure built on the assigner's own splitter could never see. Taking a spelling out
    # of the registry reproduces exactly what a pass that stopped minting for it would leave behind,
    # and the residue has to name the credit rather than fall silent.
    c = copy.deepcopy(ctx)
    was = budget_credit_fields_no_identifier_covers(c)
    entries = (c["credits"] or {}).get("credits") or []
    dropped = next((e for e in entries
                    if any(str(a).startswith("credit:") for a in e.get("anchors") or [])
                    and not e.get("merged_into")), None)
    if dropped:
        c["credits"]["credits"] = [e for e in entries if e is not dropped]
        if budget_credit_fields_no_identifier_covers(c) <= was:
            print("  self-test FAILED — 'credit fields an identifier does not cover' did not count "
                  f"a credit the registry stopped answering for ({dropped.get('credit')})")
            ok = False

    # A PAIR OF CREDITS SHARING A READING WITH NOBODY'S RULING ON IT, which is the state
    # data/names/authors.yaml was in for all 82 pairs on the morning of 2026-08-08. Taking a ruling
    # away puts one pair back into it, and a count that cannot rise here is a count that would let an
    # artist quietly hold two addresses.
    c = copy.deepcopy(ctx)
    was = budget_credits_sharing_a_reading_nobody_ruled_on(c)
    rulings = (c["credit_rulings"] or {}).get("rulings") or []
    if rulings:
        c["credit_rulings"]["rulings"] = rulings[1:]
        if budget_credits_sharing_a_reading_nobody_ruled_on(c) != was + 1:
            print("  self-test FAILED — 'credits sharing a reading nobody has ruled on' did not "
                  "count a pair whose ruling was taken away")
            ok = False

    # THE CANARY IS THE FAILURE ITSELF, NOT AN INVENTED ONE (§14b). A capture written without a row
    # for a work it was told to read is a document this pipeline really produced: it is what
    # data/source/comicfuz/works.yaml was on 2026-08-07, holding 46 of resolved.yaml's 47 works.
    # Taking a captured row away reproduces that state exactly, and the count must rise for it.
    c = copy.deepcopy(ctx)
    fuz = next((p for p in c["capture_passes"] if p["captured"]), None)
    if fuz:
        was = budget_targets_a_capture_wrote_no_row_for(c)
        dropped = sorted(fuz["captured"] & set(fuz["targets"]))[0]
        fuz["captured"].discard(dropped)
        if budget_targets_a_capture_wrote_no_row_for(c) != was + 1:
            print("  self-test FAILED — 'targets a capture wrote no row for' did not count a "
                  "capture that dropped a work it was told to read")
            ok = False
        # AND THE OTHER DIRECTION, which is the state the fixed FUZ pass produces the first time it
        # runs. A number that can only rise is a number that will never record the remedy, and this
        # one has a remedy: capture the work. Giving a missed target a captured row must take it
        # out of the count.
        fuz["captured"].add(dropped)
        for p in c["capture_passes"]:
            p["captured"] |= set(p["targets"])
        if budget_targets_a_capture_wrote_no_row_for(c) != 0:
            print("  self-test FAILED — 'targets a capture wrote no row for' still counted works "
                  "after every target was given a captured row")
            ok = False

    # The tics invariant reads files rather than ctx, so there is nothing to plant. It carries its
    # own canaries — and its own counter-cases, which matter more: three of the first four things
    # it reported were the rules being wrong, not the prose.
    sub = subprocess.run([sys.executable, str(ROOT / "adapters" / "lint" / "tics.py"),
                          "--self-test"], capture_output=True, text=True, timeout=60)
    if sub.returncode != 0:
        print("  self-test FAILED — 'no machine tells in reader text':")
        print("   ", sub.stdout.strip().replace("\n", "\n    "))
        ok = False

    if ok:
        print(f"  self-test passed ({len(probes)} canaries caught, plus the tics list)")
        print("CANARY-PROVEN")   # see adapters/testkit.py: proven by planted canary
    return ok


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--runtime", action="store_true", help="count and report; never fail")
    g.add_argument("--gate", action="store_true", help="fail on any violation or loosened budget")
    g.add_argument("--self-test", action="store_true", help="prove the checks can fail")
    ap.add_argument("--no-tighten", action="store_true", help="do not record improved budgets")
    a = ap.parse_args()

    if a.self_test:
        return 0 if self_test() else 1

    if a.gate and not self_test():
        print("\nFAIL: the checks cannot prove they work; refusing to pass anything.")
        return 3

    ctx = context()
    if not ctx["releases"]:
        print("no build output — run ./build.py first")
        return 0 if a.runtime else 1

    failed = []
    print("invariants:")
    for name, fn in INVARIANTS:
        bad = fn(ctx)
        if bad:
            failed.append((name, bad))
            print(f"  FAIL  {name}: {len(bad)}")
            for x in bad[:4]:
                print(f"          {x}")
        else:
            print(f"  ok    {name}")

    # A deploy checks the data it is deploying. The source cannot have changed since the gate ran.
    skip_source = bool(a.runtime)
    recorded = _load(BUDGETS, {}) or {}
    print("\nbudgets (ratchet down only):")
    loosened, tightened = [], {}
    for name, fn, _why in BUDGETS_DEF:
        if skip_source and name in SOURCE_BUDGETS:
            continue
        n = fn(ctx)
        was = recorded.get(name)
        if was is None:
            tightened[name] = n
            print(f"  set   {name}: {n}")
        elif n > was:
            loosened.append((name, was, n))
            print(f"  FAIL  {name}: {n} (budget {was})")
        else:
            if n < was:
                tightened[name] = n
            print(f"  ok    {name}: {n}" + (f"  (was {was}, tightening)" if n < was else ""))

    if tightened and not a.no_tighten:
        recorded.update(tightened)
        BUDGETS.parent.mkdir(parents=True, exist_ok=True)
        BUDGETS.write_text(json.dumps(dict(sorted(recorded.items())), indent=1) + "\n")


    # A report only a build log ever sees is a report nobody reads. The technical view exists to
    # carry facts about our own process, and "which invariants degraded on the last run" is exactly
    # that. Written on both paths so the file is never stale relative to the data beside it.
    # EXAMPLES ARE STRIPPED OF ABSOLUTE PATHS. Several invariants report a finding as
    # "<file>:<line>: <what>", and the file is an absolute path on whichever machine ran the
    # build. checks.json is committed and published, so a failing prose lint wrote the developer's
    # home directory into the public repository. The leak guard caught it, but only because that
    # run happened to fail; the hazard is in the writer and belongs here.
    def _unroot(x):
        return str(x).replace(str(ROOT.parent) + "/", "").replace(str(ROOT) + "/", "")

    (BUILD / "checks.json").write_text(json.dumps({
        "generated": ctx.get("generated") or "",
        "invariants": [{"name": n, "violations": len(v), "examples": [_unroot(e) for e in v[:5]]}
                       for n, v in [(n, f(ctx)) for n, f in INVARIANTS]],
        # A budget this run did not measure carries `value: null` and says why, so a reader can
        # tell "nothing to report" from "not asked".
        "budgets": [{"name": n, "means": w, "budget": recorded.get(n),
                     "value": None if (skip_source and n in SOURCE_BUDGETS) else f(ctx),
                     **({"not_measured": "source-quality budget; measured at check-in"}
                        if skip_source and n in SOURCE_BUDGETS else {})}
                    for n, f, w in BUDGETS_DEF],
        "note": ("Invariants are statements that are either true or the data is broken. At runtime "
                 "a violation degrades to the fallback named in check.py and is counted here; at "
                 "check-in the same violation blocks. Budgets are counts with no correct value, "
                 "only a direction: they tighten automatically and loosen only by hand."),
    }, ensure_ascii=False, indent=1))

    if a.runtime:
        # The show must go on. Violations are reported and counted; the build publishes anyway,
        # having already degraded to the fallback each invariant names.
        if failed or loosened:
            print(f"\n{len(failed)} invariant(s) violated, {len(loosened)} budget(s) exceeded — "
                  f"degraded per the stated fallbacks; see docs/STANDING-INSTRUCTIONS.md")
        return 0

    if failed or loosened:
        print(f"\nNO GO: {len(failed)} invariant(s) violated, {len(loosened)} budget(s) exceeded.")
        for name, was, now in loosened:
            print(f"  {name} rose {was} -> {now}; to accept it, edit docs/budgets.json and say why")
        return 1
    print("\nall right")
    return 0


if __name__ == "__main__":
    sys.exit(main())
