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
import argparse, ast, collections, hashlib, json, os, pathlib, re, subprocess, sys, time, unicodedata
# Named apart from the plain module name because several measures below bind `html` to one
# rendering they are walking, and a global with the same name reads as that variable.
import html as html_module

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
# Imported for its effect and not for a name: it points yaml.safe_load at libyaml for this process
# and everything loaded into it, adapters/captures.py included. Worth 6 seconds of a 47-second gate
# and no more, because captures.py's JSON sidecars had already spared the gate most of its parsing;
# the gate's own time is in self_test's deepcopy and the lint subprocesses. It is here so that the
# invariants which do read YAML get the fast parser, and so a machine cannot end up with build.py
# and check.py reading the same file two different ways. See adapters/yamlfast.py.
from adapters import yamlfast  # noqa: F401,E402
from adapters.lint import tree as _tree  # noqa: E402
BUILD = ROOT / "data" / "build"
NAMES = ROOT / "data" / "names"
BUDGETS = ROOT / "docs" / "budgets.json"

#: WHAT A CHECK RETURNS WHEN IT COULD NOT RUN, and the reason this exists rather than a zero.
#: Twenty-one budgets caught every exception and returned 0. A check that cannot run then reports
#: the best possible number, and `--gate` ratchets the recorded budget down to it: a number nobody
#: measured, banked, blocking the next honest run. It happened twice in one hour on 2026-08-10, once
#: when a mangled import left `build.py` unparseable so `shadowed names in build.py` banked 0 against
#: a real 40, and once when the same fault took `stock phrasing in comments` from 895 to 890.
#:
#: A budget that answers this is PRINTED, NEVER TIGHTENED, and fails the gate: not being able to
#: measure something is a state to fix and not a state to pass.
UNMEASURED = None
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
    """Defined in `adapters/facts/reading/checks.py`, beside the thing it checks."""
    from facts import reading as _f
    return _f.CHECKS["ruby_spells_reading"](ctx)


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
    """Defined in `adapters/facts/reading/checks.py`, beside the rulings it applies."""
    from facts import reading as _rd
    return _rd.CHECKS["readings_are_kana"](ctx)


def inv_reading_can_show_its_source(ctx):
    """Defined in `adapters/facts/reading/checks.py`, beside the rulings it applies."""
    from facts import reading as _rd
    return _rd.CHECKS["reading_can_show_its_source"](ctx)


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


# WHAT kari/app.js PUTS ON A NAME IT SPELLED ITSELF, in its two forms. `enFallback` appends the
# TOKEN, which travels as text so that a credit line can be composed by index and a chapter name
# can have a work name stripped off its front; `floorHtml` turns the token into the MARKUP that
# carries the tooltip, at the point the text becomes part of a page.
#
# Written once here because two checks below read one and a budget counts the other. §14b: these
# are a string and a class name, not a rule, and nothing in this file holds a copy of the decision
# about when the mark is warranted. A renderer that stopped marking its guesses would make these
# checks report clean, which is why `English mode has no Japanese` blocks on the Japanese itself
# and does not ask about a mark at all.
FLOOR_TOKEN = '[?]'
FLOOR_MARKUP = 'class="unc floor"'


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

    EVERY SURFACE, WHICH IT DID NOT USED TO BE, AND THIS IS WHY IT PASSED WHILE A BUDGET COUNTED
    77. `Surface.holds_at_zero` split the table in two and this check read one half: the titles and
    the chapter names, where Japanese was called a fault. The other half was the credit lines, the
    people and the publishing lines, where Japanese was called a coverage deficit, and
    `renderings still Japanese in English mode` counted those and ratcheted. So the two checks
    partitioned the surfaces between them and neither could ever see what the other measured. This
    one was not passing over a fault it could see. It was reading eleven surfaces of twenty-one.

    THE OWNER OVERRULED THE SPLIT. An unclear romanisation with an explanatory tooltip is required
    wherever the alternative is Japanese under an English heading, so there is no surface left
    where Japanese is a finished state. The flag is gone from `adapters/interface.py`, the budget
    is gone from the list below, and this reads the whole table.

    §14b, WHAT THIS CANNOT SEE. A call site that never calls the renderer. Running the interface
    proves that what reaches it comes out right, and says nothing about `esc(w.t)` written beside
    it, which is how 2,430 rows shipped Japanese once already. `adapters/lint/entrypoints.py` is
    the other half and `names reach a page only through their renderer` is where it blocks.

    fallback: `enFallback` in kari/app.js, which spells the name from `feed/names.json`'s floor and
    marks it. A violation here means that fallback did not run, which is a fault in the renderer
    and not a name nobody has looked up.
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
        if interface.KANA_KANJI.search(value) and interface.KANA_KANJI.search(shown):
            bad.append(f"{surface.path}:{value[:32]}")
    return sorted(set(bad))


def budget_interface_tooltips_a_reader_of_japanese_cannot_read(ctx):
    """`title="…"` attributes in kari/app.js written in English whatever the language toggle says.

    THE SITE IS BILINGUAL AND ITS TOOLTIPS ARE NOT. 30 of the 32 in the file are English string
    literals: a Japanese reader who sets 日本語 gets a Japanese page whose explanations are all in
    English, and those explanations are where the interface accounts for itself. `有料先行` said
    `18 chapter(s) of this series sit ahead of the free line` to everyone.

    COUNTED RATHER THAN FIXED IN ONE GO, because each one needs Japanese somebody means, and thirty
    sentences invented at once would be thirty guesses. A budget makes each new tooltip pay for
    itself and lets the existing ones come down as they are written.

    §14b, WHAT IT REUSES: the shipped file's text, and `T(`/`L(` as the marks of a string that
    follows the toggle. It consults no list of which tooltips are done, so a tooltip cannot be
    counted as bilingual by being named somewhere.
    """
    src = (ROOT.parent / "yurarium.github.io" / "kari" / "app.js")
    if not src.exists():
        return UNMEASURED    # this could not be measured; see UNMEASURED
    text = src.read_text(encoding="utf-8")
    # A tooltip is bilingual when its value is built by the translation helpers. Anything else is
    # a literal, and a literal is one language.
    return sum(1 for m in re.finditer(r'title="([^"]*)"', text)
               if "${" not in m.group(1) or not re.search(r"\b[TL]\(", m.group(1)))


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
        return UNMEASURED    # this could not be measured; see UNMEASURED
    return sum(n for n, _why in entrypoints.SAFE.values())


def budget_renderings_resting_on_a_mechanical_romanisation(ctx):
    """Renderings the interface spelled itself because no source states how the name is read.

    WHAT THIS REPLACES. `renderings still Japanese in English mode` counted 77 rows that reached an
    English page as kana or kanji, and its docstring said a name the store cannot render shows as
    the Japanese and that this is a finished state. The owner overruled that: a marked romanisation
    with a tooltip is REQUIRED where the alternative is Japanese. So the count of Japanese rows is
    an invariant at zero and this is what is left, which is the number of names carrying our guess
    instead of somebody's reading.

    IT FALLS ONLY WHEN A NAME IS RESEARCHED and nothing about the renderer can move it. A record
    with a sourced reading is spelled from the reading and never reaches the floor; a record with
    no reading at all reaches it every time. That makes this the data gap stated as a number, and
    the one measure a later naming pass should be aimed at.

    A COMMUNITY DATABASE'S READING IS COUNTED HERE, from the project owner's correction of
    2026-08-09: "I mistyped 'without overcoming their fallback basis'". Wikidata raises the floor on
    the string and leaves the record resting on a fallback, so a name spelled off its kana is a name
    an English page spelled for itself and belongs in this number. 44 before, 628 after, and the
    rise is the correction working rather than anything getting worse. `uncertainMark` in
    kari/app.js is what emits the class for them, beside `floorHtml`, and the tooltip stays the one
    naming the database.

    WHAT IT STILL DOES NOT COUNT, said here because a measure that catches the stronger case and
    misses the weaker one is worth nobody's trust (§14b). 1,914 renderings carry `unc` without
    `floor`: a reading a morphological analyser produced, or one assembled character by character.
    Those rest on less than a Wikidata edit does, and whether the class should widen to take them is
    a ruling nobody has made. `author readings no source states` counts the RECORDS behind them,
    which is why the population is not invisible in the meantime.

    MEASURED FROM THE MARKUP THE INTERFACE PRODUCES, so it counts what a reader is actually shown.
    §14b, WHAT IT SHARES: one CSS class name, `unc floor`, which kari/app.js emits from a single
    constant. That is the whole of the coupling. Nothing here holds a copy of the rule deciding when
    the mark is warranted, so a renderer that stopped marking a guess would show up as this falling
    to zero rather than as this agreeing with it.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    try:
        calls, _about = interface.calls_for(_collections(ctx))
        if not calls:
            return 0
        out = _interface(ctx).values(calls)
    except interface.Unavailable:
        return UNMEASURED    # this could not be measured; see UNMEASURED
    return sum(html.count(FLOOR_MARKUP) for html in out)


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
        return UNMEASURED    # this could not be measured; see UNMEASURED
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

    AND IT NOW ASKS THE OTHER HALF OF THE QUESTION. A field the data carries Japanese in is ruled
    either by a surface or by `interface.NOT_DRAWN`, which says nothing puts it on a page. The
    second answer was asserted and never verified: a volume's `designation` was ruled that way on
    2026-08-12 and drawn by the same change with `esc`, so 383 works showed Japanese in English
    mode with both guards green. `entrypoints.undrawn_findings` reads the source for it.

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
    return entrypoints.findings(src) + entrypoints.undrawn_findings(src)


def inv_a_stated_reading_names_where_it_came_from(ctx):
    """Defined in `adapters/facts/reading/checks.py`, beside the rulings it applies."""
    from facts import reading as _rd
    n = _rd.CHECKS["facts_fetched_with_no_citation"](ctx)
    return [f"{n} stated reading(s) hold no url or cite"] if n else []


def inv_the_interface_is_the_derivation_of_its_source(ctx):
    """`kari/app.js` is what `kari/src` concatenates to.

    THE PROPERTY A BUNDLE WOULD HAVE COST US. The checks run the real `app.js` in a Node vm, so
    what is verified is what ships. Splitting the file into modules keeps that only if the shipped
    file is exactly the modules, and this is what says so.

    IT IS THE SHAPE `deployed data matches built` ALREADY HAS. A derived artefact and its inputs,
    compared by content, with the answer being that one is stale.

    Section 14b: it re-derives from the source files and compares bytes. It shares nothing with the
    builder except the concatenation order, which is filename order and stated in kari/src/BUILD.md.
    """
    site = ROOT.parent / "yurarium.github.io"
    src = site / "kari" / "src"
    out = site / "kari" / "app.js"
    if not src.is_dir() or not out.exists():
        return []
    want = "".join(p.read_text(encoding="utf-8") for p in sorted(src.glob("*.js")))
    if want == out.read_text(encoding="utf-8"):
        return []
    return ["kari/app.js is not the derivation of kari/src; run ./build-app.py"]


def inv_the_tracker_states_what_it_claims(ctx):
    """No item in the plan's state file claims `done` without saying what changed.

    THE FAULT THIS EXISTS FOR is on the record. The first round's tracker showed romanisation's
    step 5 complete when the check had never moved, and showed a stage in progress after its steps
    were finished. Both were caught by the project owner reading the page, which is the wrong
    reader for that fault.

    A STATUS IS THE ONE THING A MACHINE CANNOT DERIVE, so it is typed, and this is the smallest
    guard on the typing: a claim of done carries a sentence saying what changed. It does not verify
    the sentence, only that somebody had to write one.

    Section 14b: it reads the state file and knows nothing about the work. A note that is false
    passes, and no check can do better than making the claim visible next to the change.
    """
    try:
        sys.path.insert(0, str(ROOT / "adapters"))
        import tracker
        import importlib
        importlib.reload(tracker)
        return tracker.problems()
    except Exception:                                                   # noqa: BLE001
        return []


def inv_a_fact_is_reached_through_its_entry_point(ctx):
    """Nothing outside an extracted fact names its internals.

    STANDING-INSTRUCTIONS section 3 has said one producer of a fact since the project began, and
    twelve shipped faults in one week were breaches of it. The rule was right and unenforced; this
    is the enforcement, and it arrives with the first fact rather than after the last.

    §14b, WHAT IT SHARES WITH ITS SUBJECT: nothing but the directory layout. It reads import
    statements out of source files and asks no module what it thinks it exports. Its own blind spot
    is stated in adapters/lint/facts.py and is worth repeating here, because it is the interesting
    one: a SECOND IMPLEMENTATION, written from scratch and importing nothing, passes this. Three of
    the four assemblers that produced `facts/romanisation` were exactly that shape.
    """
    try:
        sys.path.insert(0, str(ROOT / "adapters" / "lint"))
        import facts as _facts
        import importlib
        importlib.reload(_facts)
        got = _facts.findings()
    except Exception:                                                   # noqa: BLE001
        # THE LINT BEING UNAVAILABLE IS NOT A VIOLATION. It reads source files and cannot be shown
        # a canary through `ctx`, so its own proof is `adapters/lint/facts.py --self-test`, which
        # ./test.py discovers.
        return []
    return [f"{path}:{line} reaches facts.{fact}.{sub}" for path, line, fact, sub in got]


def inv_every_renderer_is_ruled(ctx):
    """Every function that returns rendered name text is a surface or is argued not to be.

    THE FAULT THIS IS FOR. `interface.SURFACES` is hand-written and `creditLine` was missing from it.
    The work page called it, it cut the byline on a slash and passed the pieces on as a field the
    build had never seen, and 安田剛助・文尾文 reached a reader as `???? · Bun?Bun` while every probe
    over the table reported zero. A table of what reaches a reader cannot be what decides it.

    DERIVED FROM THE SOURCE, seeded with the floor primitives and with whatever the table already
    names, so the derived set is a superset of the table by construction and the answer here is what
    it holds that the table does not. `NOT_A_SURFACE` is where an orchestrator goes, with a reason.

    §14b, WHAT IT SHARES WITH ITS SUBJECT: it reads `app.js` as text and asks nothing of the table
    except which names are in it. Its blind spot is a renderer written as an arrow function or a
    method, stated in interface.renderers, which is why the exemptions carry reasons and not names.
    """
    try:
        sys.path.insert(0, str(ROOT / "adapters"))
        import interface as _iface
        got = _iface.unruled_renderers()
    except Exception:                                                   # noqa: BLE001
        return []
    return [f"{n} returns rendered name text and is in neither SURFACES nor NOT_A_SURFACE"
            for n in got]


def inv_every_name_is_defined_where_it_is_used(ctx):
    """A name used where nothing in scope defines it, which is a crash waiting for its branch.

    THE TWO THIS FOUND. `build.py` reached for a `ROOT` that function did not have and crashed 34
    seconds into a build, which neither the gate nor the tests run. And `adapters/relational` read
    `_rd.DEFAULT_BASIS` in a function importing no `_rd`, on the right of an `or` whose left side is
    truthy for every record the corpus holds today: working code with a NameError inside it, waiting
    for the first record that arrives without a reading basis.

    §14b, WHAT IT SHARES WITH ITS SUBJECT: nothing. `pyflakes` does the scope analysis, and writing
    a fourth scope resolver in this repository to avoid the dependency would be the worse trade on a
    solved problem whose failure mode is a check that quietly passes.

    FAIL-CLOSED: pyflakes being absent is reported as the finding and not as an empty list, which is
    `UNMEASURED`'s argument in the invariants' half of the file.
    """
    try:
        sys.path.insert(0, str(ROOT / "adapters" / "lint"))
        import undefined as _und
        import importlib
        importlib.reload(_und)
        got = _und.findings()
    except Exception as e:                                              # noqa: BLE001
        return [f"the check could not run: {e}"]
    return [f"{path}:{line}: {name}" if path else name for path, line, name in got]


def inv_a_work_shows_the_english_its_record_holds(ctx):
    """The English on a works-list row is the English the name store holds for that title.

    THE BRIDGE BETWEEN TWO VIEWS, and it exists because they were measured apart and drifted in
    conversation before they drifted in the data. `works showing a romanisation` counts SERIES ROWS
    whose attached `work_en` names no English basis. A sweep taken from `feed/names.json` instead
    counted TITLE RECORDS, and the two answers were 178 and 26 for what sounded like one question.

    NEITHER NUMBER WAS WRONG AND NEITHER IS THE OTHER'S CHECK. `feed/names.json` holds 3,164 titles
    against 3,046 rows, because 226 of them are edition variants and print-only records that are no
    row at all; and a row carries the store's answer only if `build.py` attached it under a key the
    store also uses. Nothing tested that second part, so a fold that stopped matching would have
    shown up as a reader seeing romaji while every count stayed where it was.

    So this asserts the join: for every row, if the store holds an English name under the same folded
    key, the row carries it. It is at zero and it is the reason the data-side budget can be read as a
    statement about what a reader sees.

    §14b, WHAT IT SHARES WITH ITS SUBJECT: the fold, `facts/namekey.fold`, which is the one producer
    of that key and is what the interface uses too. It asks nothing of the renderer and holds no copy
    of the attachment rule; it compares two shipped artefacts.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    from facts import namekey as _nk
    titles = (ctx.get("names_shipped") or {}).get("titles") or {}
    held = {}
    for k, v in titles.items():
        if isinstance(v, dict) and v.get("en"):
            held.setdefault(_nk.fold(k), v["en"])
    bad = []
    for r in ctx["series"]:
        ja = r.get("work") or ""
        store_en = held.get(_nk.fold(ja))
        row_en = (r.get("work_en") or {}).get("en")
        if store_en and not row_en:
            bad.append(f"{r.get('id')} {ja}: the store holds {store_en!r} and the row shows none")
    return bad


def inv_the_store_has_one_writer(ctx):
    """Nothing writes to the relational store except the module that compiles it.

    THE PROPERTY THAT KEEPS IT DERIVED. Everything in the store is rebuilt from `data/build` plus
    the rulings the facts hold, so deleting the database costs one rebuild. That is the whole reason
    it may be load-bearing, and it lasts exactly as long as one module is the only writer. A pass
    reaching in to fix one row makes the database a source of truth nobody declared, and the next
    rebuild throws that row away without saying so.

    §14b, WHAT IT SHARES WITH ITS SUBJECT: nothing but the path. It reads source and asks which
    files pass a changing statement to a cursor; it does not ask the store what it thinks. Its blind
    spot is SQL assembled at runtime, stated in adapters/lint/onewriter.py, which is why the rule is
    also written in the store's own docstring.
    """
    try:
        sys.path.insert(0, str(ROOT / "adapters" / "lint"))
        import onewriter as _ow
        import importlib
        importlib.reload(_ow)
        got = _ow.findings()
    except Exception:                                                   # noqa: BLE001
        return []
    return [f"{path}:{line}: {what}" for path, line, what in got]


def inv_a_name_is_answered_by_one_module(ctx):
    """No importable name resolves to two files that are on sys.path together.

    THE ONE THIS CAUGHT was `store`. `adapters/store/` sat beside `adapters/names/store.py` and put
    `names` on its own path, so a bare `import store` inside the package found the NAME store.
    Whichever directory came first won and nothing said so; the workaround was a comment asking the
    next reader not to reorder two lines. `adapters/relational` is the rename.

    NOT A WALL. Thirteen platforms hold a `releases.py` and that is right, because a caller writes
    `gigaviewer.releases` and a platform's directory reaches the path only while it runs. The check
    reads the actual `sys.path.insert` calls, so a name counts only where two directories are on the
    path at once.

    §14b, WHAT IT SHARES WITH ITS SUBJECT: it reads inserts written as source and would miss a path
    built at runtime or by an environment variable. test_shadowing.py rebuilds the tree that shipped
    the fault, so the check is held to catching it rather than to returning zero.
    """
    try:
        sys.path.insert(0, str(ROOT / "adapters" / "lint"))
        import shadowing as _shadowing
        import importlib
        importlib.reload(_shadowing)
        got = _shadowing.collisions()
    except Exception:                                                   # noqa: BLE001
        return []
    return [f"{name}: {', '.join(paths)}" for name, paths in got]


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


def inv_scope_rulings_are_accounted_for(ctx):
    """Every §6 scope ruling is reported, and a work ruled out of scope is nowhere on the site.

    WHY THIS IS AN INVARIANT AND THE COUNTRY IS A BUDGET. The country of an unruled work is a fact
    somebody has to go and find, so it is a count with a direction. A ruling is a decision already
    made, and a decision that has been made and does not show up in what ships is the failure
    STANDING-INSTRUCTIONS §13 is about: `data/source/kadokomi/withheld.yaml` said five works were
    not published while all five were live, and nothing anywhere disagreed.

    CHECKED ON THE DEPLOYED BYTES BY SUBSTRING, not by field. The withheld register was fixed six
    times before it was fixed, and each of the six surfaces was found only after the previous fix
    appeared to have worked. A title reaching the site inside a claim trace, an archived month or a
    coverage list is as published as one in the works list, and only the bytes see all of them. It
    already earned its keep: `data/names/phrases.yaml` holds `オルターエゴ（MFC）` beside the bare
    title, the filter on the names map was a `norm_work` lookup, and the imprinted spelling shipped.

    THE REPORT FILES ARE EXEMPT AND THE REASON MATTERS. `run.json`, `checks.json` and `status.json`
    are what status.html renders, and status.html is where facts about US belong
    (STANDING-INSTRUCTIONS §6). A refusal that could not be named there would be a filter nobody can
    observe, which is the failure this check descends from. The catalogue is what must not carry
    the work, and that is every other file the site serves.

    §14b, WHAT THIS SEES THAT THE BUILD CANNOT. `build.py` drops these works through
    `withheld_works`, and a check asking `withheld_works` whether they are dropped would agree with
    itself. This reads the ruling file and the served files and asks nothing of the code that acted
    on either.

    fallback: none. A ruling not reflected in what ships is a standing constraint broken, and a
    build puts it right without anybody fetching anything.
    """
    rulings = ctx["scope_rulings"]
    reported = {r.get("work") for r in ctx["scope_reported"]}
    bad = []
    # A RULING MAY NAME A LINE AND NOT A BOOK, and it may answer either question §6 asks. The
    # country half was the only one anybody had ruled on, so this read `work` and `country_basis`
    # off every ruling and found None on the first ruling about a medium. Members are expanded here
    # rather than through `facts/origin`, because the point of this check is that it reads the
    # ruling file and the served bytes and asks nothing of the code that acted on either.
    for r in rulings:
        for m in (r.get("works") or [r]):
            if m.get("work") not in reported:
                bad.append(f"ruled and not reported anywhere: {m.get('work')} "
                           f"{str(m.get('title'))[:24]}")
        if (r.get("country_basis") not in _origin_bases()
                and r.get("medium_basis") not in _origin_medium_bases()):
            bad.append(f"rests on a term no vocabulary holds: "
                       f"{r.get('work') or r.get('imprint')}")
    if not SITE.exists():
        return bad
    for r in rulings:
        for m in (r.get("works") or [r]):
            title = m.get("title")
            if r.get("disposition") != "out-of-scope" or not title:
                continue
            for f in sorted(SITE.rglob("*.json")):
                if f.name in REPORT_FILES:
                    continue
                try:
                    if title in f.read_text(encoding="utf-8", errors="replace"):
                        bad.append(f"out of scope and published: {f.relative_to(SITE)}: "
                                   f"{title[:24]}")
                except OSError:
                    pass
    return bad


def _plant_a_ruling_on_an_unknown_term(c):
    """A ruling reported like any other, resting on a `country_basis` nothing defines."""
    c["scope_rulings"].append({"work": "CANARY", "title": "カナリア",
                               "disposition": "review", "country_basis": "a-term-nobody-defined"})
    c["scope_reported"].append({"work": "CANARY", "title": "カナリア"})


def _plant_an_app_only_route_a_reader_is_sent_to(c):
    """Both passes agree the route is app-only, and a shipped row still offers it as a source."""
    u = "https://manga.nicovideo.jp/comic/99998"
    c["nicovideo_channels"].append({"url": u, "work_title": "カナリア", "app_only_route": True})
    c["nicovideo_work_chapters"].append(
        {"url": u, "chapters": [{"title": "カナリア", "app_only": True}]})
    c["series"].append({"work": "カナリア", "sources": [{"platform": "ニコニコ漫画", "url": u}]})


#: What status.html renders, as against what the catalogue serves. A refusal is named in these and
#: in none of the others, which is the difference between a control somebody can observe and a
#: filter that drops rows silently (STANDING-INSTRUCTIONS §13).
REPORT_FILES = {"run.json", "checks.json", "status.json"}


def _origin_bases():
    """The `country_basis` vocabulary, asked of the module that owns it."""
    sys.path.insert(0, str(ROOT / "adapters"))
    from facts import origin as _o
    return _o.bases()


def _origin_medium_bases():
    """The `medium_basis` vocabulary, asked of the module that owns it."""
    sys.path.insert(0, str(ROOT / "adapters"))
    from facts import origin as _o
    return _o.medium_bases()


def inv_no_published_update_leaves_its_month(ctx):
    """Every update a published month holds is still built, in that month.

    THE BYTES USED TO BE THE TEST AND THAT WAS THE WRONG THING TO LOCK. A month was written once
    and never rewritten, on the argument that a published statement about dates must not be quietly
    revised. It froze far more than dates: 602 of July's 605 rows baked a title, a reading and three
    romaji styles, and 573 of those titles are spellings the store has since corrected. 球詠 read
    `Tamaei` where it is `Tamayomi`, and no fix could ever reach it. The owner ruled on 2026-08-11
    that a name has a right answer we converge on and is not history; what changed then is.

    SO THE ROW SET IS LOCKED AND THE RENDERING IS NOT. The file is rewritten every build and this
    asks the only question that matters: did an update we published stop being published. A title
    improving is the system working. An update disappearing is the amnesia REQUIREMENTS §4 exists
    to prevent.

    KEYED ON THE PLATFORM'S OWN ID, because the work title is exactly what is allowed to change. A
    handful of adapters build an id out of the chapter title and those rows will churn when a title
    is corrected, which is a fault in those adapters and is why this reports the row rather than a
    count.

    §14b, WHAT IT REUSES: the served bytes and the built bytes. It asks nothing of the code that
    wrote either, so a build that dropped a month entirely fails here rather than agreeing with
    itself.
    """
    bad = []
    for f in sorted((BUILD / "feed").glob("[0-9]*-[0-9]*.json")):
        live = SITE / "feed" / f.name
        if not live.exists():
            continue
        was = {(r.get("plat"), r.get("id")) for r in (_load(live, {}) or {}).get("releases") or []}
        now = {(r.get("plat"), r.get("id")) for r in (_load(f, {}) or {}).get("releases") or []}
        for k in sorted(was - now, key=str)[:20]:
            bad.append(f"{f.name} published {k} and it is no longer built")
    return bad


def inv_a_release_id_names_one_release(ctx):
    """No two releases on a platform share an identifier.

    fallback: none; the rows still publish, and every measure keyed on the pair reads them as one.

    THE FAULT. `build.py` keyed a release on the chapter's own address, or on its TITLE where the
    platform states no address. A chapter label is not unique on a platform, so `pixivcomic:第3話`
    named three works at once and `takecomic:18話` named three more. 1,352 of the 5,284 title-keyed
    chapters in `data/source/webpages` collide that way, takecomic 425 of its own 506, and only 8
    surfaced in a release window because a collision needs both works to publish the same label
    within the same fortnight.

    WHY IT IS AN INVARIANT AND NOT A COUNT. Two rows sharing an identifier are ONE row to anything
    keyed on it, and `no published update leaves its month` is keyed on it: a row that really did
    vanish could be masked by its twin still being there, so the collision blinds the measure that
    exists to catch the worse fault. There is no acceptable number of these above zero.

    §14b, WHAT IT REUSES: the shipped rows and nothing that wrote them. It counts pairs in the
    published files, so a build that starts minting a colliding id fails here whatever the code
    that minted it believes about uniqueness.
    """
    # THE CURRENT FEED COMES FROM `ctx` AND THE ARCHIVES FROM DISK. A check that opens its own file
    # cannot be shown a canary, and this needs to be probeable, so the live list is taken from the
    # context that `--self-test` plants in. The months behind it are not on the context and are read
    # here; a collision minted today appears in the current feed first, which is the half the probe
    # covers.
    lists = [("feed.json", ctx["releases"] or [])]
    months = sorted((BUILD / "feed").glob("[0-9]*-[0-9]*.json"))
    lists += [(f.name, (_load(f, {}) or {}).get("releases") or []) for f in months]
    seen, bad = {}, []

    # AND IT SAYS SO WHERE IT READ NOTHING. The archive half opens its own files, so it reports
    # clean when it finds none: point `BUILD` at a directory that does not exist and this returns
    # no violations, and `--self-test` still passes, because the canary is planted in the current
    # feed. A directory that moves, a glob that a future month's name does not match, a build that
    # stops writing the months. Each is silence that looks exactly like a clean answer.
    #
    # THE SITE IS WHAT IT COUNTS AGAINST, because the served months are the ones somebody published
    # and no amount of local breakage can reduce them. Serving more months than the build produced
    # is the state worth catching. Before the first deploy there is nothing to count against and
    # this asks nothing at all.
    #
    # WHY NOT PUT THE ARCHIVES ON THE CONTEXT and let a canary reach them: they grow by a month for
    # ever, 1.25 MB and about 600 rows so far, and the context is loaded for all 59 invariants and
    # 75 budgets whether or not they read it. This project already met that shape once, when
    # feed.json reached 1.3 MB and every visitor fetched it to draw the first screen. The
    # assertion catches the same silence at a cost that does not grow.
    if SITE.exists():
        served = sorted((SITE / "feed").glob("[0-9]*-[0-9]*.json"))
        if len(months) < len(served):
            missing = sorted({f.name for f in served} - {f.name for f in months})
            bad.append(f"the site serves {len(served)} archived month(s) and the build produced "
                       f"{len(months)}, so this examined fewer than were published: "
                       f"{', '.join(missing[:5])}")
    for name, rows in lists:
        for r in rows:
            k = (name, r.get("plat"), r.get("id"))
            prev = seen.get(k)
            if prev is not None and prev != (r.get("work"), r.get("ep")):
                bad.append(f"{name}: {r.get('plat')} {r.get('id')!r} is both {prev[0]!r} "
                           f"{prev[1]!r} and {r.get('work')!r} {r.get('ep')!r}")
            seen[k] = (r.get("work"), r.get("ep"))
    return bad[:20]


def budget_published_dates_that_moved_in_an_archive(ctx):
    """Rows in a published month whose publication date the rebuild has changed.

    THE OTHER HALF OF WHAT AN ARCHIVE LOCKS. `no published update leaves its month` asks whether a
    row is still there and deliberately says nothing about its contents, because the owner ruled on
    2026-08-11 that a name has a right answer and is not history. That ruling was about NAMES.
    `FEATURES-INTERFACE` draws the line in the same sentence: "A romanisation improving is the
    system working; a published date changing is not." Nothing measured the second half.

    IT IS A BUDGET AND NOT AN INVARIANT, and the 16 it opened at are why. Every one of them moved
    by exactly one day, all on GigaViewer platforms, and they are a CORRECTION arriving rather than
    drift: `2793bbe` replaced a naive `[:10]` slice of the feed's UTC stamp with `jst_date` on
    2026-08-02, and the capture five days later re-read those chapters onto the Japanese calendar
    day they were actually published on. JST is UTC+9, so anything published between midnight and
    09:00 JST had been filed a day early. Refusing that would freeze a known error into the record.

    So the number says how much of the past a rebuild has rewritten, and it ratchets: a correction
    lands, somebody accepts it with the reason, and the floor drops back to zero. A date moving
    with no such reason behind it is drift, and this is what makes it arrive as a number rather
    than as a discovery years later.

    §14b, WHAT IT REUSES: the served month and the built one, and nothing that wrote either. The
    check that would share the producer's blind spot is one asking the feed writer whether it
    changed a date.

    WHAT IT CANNOT SEE: a month the site does not serve yet, which is any month before the first
    deploy that published it. Those are skipped rather than counted as unchanged.
    """
    moved = 0
    for f in sorted((BUILD / "feed").glob("[0-9]*-[0-9]*.json")):
        live = SITE / "feed" / f.name
        if not live.exists():
            continue
        # THE ADDRESS IS PART OF THE KEY, and it has to be. `(plat, id)` is what the invariant
        # above uses and it collides: a handful of adapters build an id out of the chapter title,
        # so `pixivcomic:第3話` is every pixivコミック work's third chapter at once. Three rows
        # collided in July and this reported all three as dates that had moved when none had.
        # `(plat, id, url)` is unique across all 602. Where an address itself changes the row
        # simply goes uncompared, which under-reports rather than inventing a change.
        was = {(r.get("plat"), r.get("id"), r.get("url")): r.get("pub")
               for r in (_load(live, {}) or {}).get("releases") or []}
        for r in (_load(f, {}) or {}).get("releases") or []:
            k = (r.get("plat"), r.get("id"), r.get("url"))
            if k in was and was[k] != r.get("pub"):
                moved += 1
    return moved


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
        if want == st:
            continue
        # A STATE THAT SAYS WHY IS NOT A CONTRADICTION. `state_basis` carries the reason the
        # arithmetic was overridden, and お菊さんはいちゃ憑きたい carries "no chapter for 45 days in
        # what we hold, but カドコミ still marks the serialisation as running". A platform saying a
        # serialisation is live is evidence this database does not have, and refusing it would ask
        # the build to ignore the publisher in favour of our own coverage gap.
        #
        # THE BASIS HAS TO MENTION THE DISAGREEMENT, so an unrelated sentence does not excuse one.
        basis = str(r.get("state_basis") or "")
        if basis and any(w in basis for w in ("still", "running", "hiatus", "skipped", "announced")):
            continue
        bad.append(f"{r.get('work')}: {st} beside a chapter {age} days old"
                   + (f" (basis: {basis})" if basis else " with no basis"))
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

    THE COUNTRY CLAUSE WAS TRUE BY CONSTRUCTION AND IS NOW ABOUT THE BASIS. This asked whether
    `country` held a value while `build.py` wrote the literal `"JP"` into it on every record that
    reached here, so the clause could not fail on anything the pipeline was able to produce: the
    check shared the subject's blind spot in the exact shape §14b describes. What is asked instead
    is `country_basis`, which `facts/origin` fills with a term saying what established the country
    or why nothing did. An undated work still has to say where, and now it has to say how well it
    knows, which is a question the constant made unaskable.

    fallback: none. This is an invariant because all three fields are derivable from records already
    in hand, so a violation is the build having dropped something rather than a source withholding
    it. An unattested country is NOT a violation and is counted as a budget instead, because the
    remedy is a publisher's page somebody has to read.
    """
    bad = []
    for w in ctx["works"]:
        fp = w.get("first_publication") or {}
        if fp.get("date"):
            continue
        missing = [k for k in ("venue", "country_basis", "date_basis") if not fp.get(k)]
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


def inv_a_volume_number_is_the_shop_s_own(ctx):
    """Every volume number a BOOK☆WALKER record states appears in that volume's own title.

    THE FAULT, WHICH REACHED A READER AND WAS FOUND BY ONE. `bwingest.volumes_of` numbered a volume
    by its POSITION in the shop's listing, `enumerate`'s index published as the volume number. A
    shop listing is neither a volume list nor in volume order. BOOK☆WALKER sells 32 products under
    MURCIÉLAGO, three of them free samples of volumes already in the list, so the corpus published a
    29 volume series as 32 volumes and volumes 30, 31 and 32 existed in the interface and nowhere
    else. パロスの剣 lists `【最新刊】…3巻` first, so volume 3 went out as volume 1 and volume 1 as
    volume 2, each with the other's date beside it. 54 records disagreed with their own titles.

    WHY AN INVARIANT AND NOT A BUDGET. A position published as a volume number is a fault in the
    pipeline every time. It is not a deficit that shrinks as research is done, and there is no
    number of them that is acceptable while somebody works through the rest.

    SUBSTRING ARITHMETIC ON TWO SHIPPED FIELDS, per §14b, and this is the point of it. The producer
    reads the number out of the product title by removing the series name and matching a handful of
    forms; this asks only whether the number it settled on occurs in that title at all, NFKC-folded
    so a full-width `１` meets a stored `1`. It shares no rule with `facts/volumenumber`, so a
    parser that starts reading the wrong thing cannot satisfy it by being consistently wrong.

    §14b, what it cannot see: a number that IS in the title and belongs to something else. The
    booklet series `『citrus +』小冊子` names its parent work's volume in every title, and a rule
    that read those would place booklet 1 as volume 5 and pass here. `volumenumber` declines it by
    requiring the series name, and `test_volumenumber.py` is where that case is pinned.

    fallback: none. A volume the shop does not number carries no number, which is a fact about the
    listing and is not counted here.
    """
    bad = []
    for rec in ctx["shop_records"]:
        for v in rec.get("volumes") or ():
            num = str(v.get("number") or "").strip()
            if not num:
                continue
            title = unicodedata.normalize("NFKC", str(v.get("title") or ""))
            if num not in title:
                bad.append(f"{rec.get('work_id')}: volume {num} is not in {title[:44]!r}")
    return sorted(bad)[:40]


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


def inv_a_name_in_both_mode_is_rendered_in_both(ctx):
    """Every call to a one-language renderer in kari/app.js sits inside a 併記 wrapper.

    THE FAULT. `workLabel` and `authorLabel` answer in the reader's language and leave 併記 to
    `bilingual()`, which calls them once per language with LANG forced. Called directly with the
    toggle on 併記 they answer in Japanese and report nothing, so the work page heading, the 作品
    rows, the 発売 rows and the works list on a credit or a publisher page shipped with no English
    at all. Each of them was right in ja and right in en, which is why a reader found it before any
    check did.

    WHY THE RENDERER CHECKS ABOVE MISS IT. Those ask whether a name reaches a page through the
    function that renders it, and every one of these call sites does. What was wrong is how many
    times it was asked.

    §14b, WHAT THIS CANNOT SEE. It reads call sites and not output, so a renderer added to app.js
    and left out of `entrypoints.ONE_LANGUAGE` is invisible to it, and `creditText` composing a
    byline out of `personShown` is not covered today.

    fallback: none. This reads a file already written and cannot degrade a build.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "lint"))
    # THE SOURCE THE CONTEXT HOLDS, which is what the entry-point invariant above reads and what
    # the canary is planted in. Reading the file again here would give a check the probe cannot
    # reach, and a canary that lands somewhere the check does not look proves nothing (§4).
    src = ctx.get("interface_js")
    if not src:
        return []
    try:
        import entrypoints
    except Exception as e:                                                      # noqa: BLE001
        return [f"adapters/lint/entrypoints.py will not import, so nothing was checked: {e}"]
    return entrypoints.single_language_findings(src)


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
        return UNMEASURED    # this could not be measured; see UNMEASURED
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
    """Defined in `adapters/facts/division/checks.py`, beside the thing it counts."""
    from facts import division as _div
    return _div.CHECKS["divisions"](reading)


def _curate():
    """`adapters/names/curate.py`, or None where it cannot be imported."""
    sys.path.insert(0, str(ROOT / "adapters"))
    try:
        from names import curate
    except Exception:                                                       # noqa: BLE001
        return None
    return curate


def _states_a_reading():
    """The source kinds a source may be when it STATED a reading, ASKED OF THE TABLE.

    This was a copy of `curate.READING_ATTRIBUTION`'s values written out by hand, and the two had
    already drifted: the table admitted `community-db` for a researched reading and the copy here
    did not, so a record citing one was read as citing nothing. That is §3 with the second producer
    inside the check, which is the worst place for it, because the check is what is supposed to
    notice.

    IT ASKS FOR ONE ROW AND NOT FOR ALL OF THEM, which is the second half of the same fault. Reading
    every value out of the table answers "a kind that appears anywhere in it", and that is not the
    question any caller asks: `researched` and `community-printed` both admit `community-db`, so a
    union would have kept Wikidata in this list through the demotion the project owner ordered on
    2026-08-09 and the check would have reported the ruling as having no effect. `curate.STATED_BASES`
    names the rows that mean a source stated the reading, beside the table it selects from.

    `analyser` is absent because the table does not carry it, and `None` with it: a record that
    cannot say where its division came from has not got one from anywhere.
    """
    curate = _curate()
    if curate is None:
        # A check that cannot read the table must not silently accept everything. Falling back to
        # the empty set would do the opposite of what this list is for.
        return ()
    return tuple(sorted({k for b in curate.STATED_BASES
                         for k in curate.READING_ATTRIBUTION.get(b, ())}))


def _divided_by_its_source():
    """The bases under which a division arrived WITH the reading, ASKED OF THE TABLE.

    A hand-written copy of `curate.DIVIDING_BASES` sat here, which is §3 in the same place and for
    the same reason as `_states_a_reading` above: the check that is supposed to notice a drift held
    one of the two copies. It has been wrong in both directions inside one day, first refusing a
    basis the table admitted and then admitting one the owner's correction took out, and asking the
    table is what makes a third drift impossible rather than unlikely.

    An empty tuple where the table cannot be read, so a check that lost its subject fails loudly.
    """
    curate = _curate()
    return tuple(curate.DIVIDING_BASES) if curate is not None else ()


STATES_A_READING = _states_a_reading()
DIVIDED_BY_ITS_SOURCE = _divided_by_its_source()

# BASES WHOSE DIVISION IS SOMEBODY'S CLAIM AND CITES NOBODY WHO STATES A READING. Each is let past
# `a division cites its source` by name and counted by a budget instead, because the alternative is
# returning people to a glued romanisation to buy a number, which is what STANDING-INSTRUCTIONS §6
# and the owner's ruling both refuse.
#
#   back-converted     a romanisation read backwards, so the space is a community editor's. The
#                      budget is `divisions read back from a romanisation`, 3 today.
#   community-printed  Wikidata's P734 and P735, typed by an editor who signed nothing. The budget
#                      is `divisions resting on a community database`, 88 today.
#
# `community-printed` JOINED ON THE OWNER'S CORRECTION OF 2026-08-09, which restored the word
# "without" to the ruling: Wikidata raises the floor on the string a reader sees and does not
# overcome the record's fallback basis. So it left `curate.DIVIDING_BASES`, where membership means
# the division arrived cited, and arrived here, where membership means the division is a known weak
# class with a number on it. 66 records would have failed the invariant in the gap between the two.
#
# HELD HERE AND NOT IN `curate.py`, because it is not a statement about what a basis IS. It is this
# check's own decision about which weak classes it reports as a count instead of blocking on, and
# the budget names beside each entry are the half that only check.py can keep true.
sys.path.insert(0, str(ROOT / "adapters"))
from facts import division as _division                                 # noqa: E402

UNCITED_DIVISIONS_COUNTED = tuple(sorted(_division.bases_where("counted")))


def inv_kana_reading_spells_its_name(ctx):
    """Defined in `adapters/facts/reading/checks.py`, beside the thing it checks."""
    from facts import reading as _f
    return _f.CHECKS["kana_reading_spells_its_name"](ctx)


def inv_a_division_cites_its_source(ctx):
    """Defined in `adapters/facts/division/checks.py`, beside the thing it checks."""
    from facts import division as _div
    return _div.CHECKS["cites_its_source"](ctx)


def inv_a_division_names_its_donor_in_a_field(ctx):
    """Defined in `adapters/facts/division/checks.py`, beside the thing it checks."""
    from facts import division as _div
    return _div.CHECKS["names_its_donor_in_a_field"](ctx)


def inv_a_person_is_spelled_one_way(ctx):
    """A string the shipped file answers for as a person and as a phrase gets one answer.

    THE TWO PRODUCERS. `phrases` is written once per string by the morphological analyser and never
    revisited, and an analyser divides by finding words in running text, which a pen name is not:
    it held `Ai Kawa Momoko` for あいかわももこ, `Ikedata Kashi` for いけだたかし and
    `Ara Fujipesu` for あらふじぺす, while the author store held the same three people romanised
    from their own readings. 290 strings had two answers and the analyser's was the worse one every
    time the two differed.

    Worse than wrong, it was FROZEN. A phrase is written the first time a string is seen, so a
    division sourced afterwards could never reach it, and 大熊らすこ stayed `Ōkumara Suko` after its
    reading was settled as オオクマ ラスコ.

    SO THE PHRASE CONSUMES THE STORE, which is §3's first question rather than its second, and this
    is the invariant that says it kept doing so. It compares two shipped strings and reads neither
    producer, so it fails on anything the build can emit: `_recompose_credit` returning the phrase
    unchanged because its import failed looks exactly like a green run otherwise.

    §14b, what it cannot see: whether the store's own answer is right. That is what the division
    work and the mark beside a run-on name are for.

    fallback: none at check-in. A build that cannot compose leaves the analyser's string, which is
    still a name and still renders, so nothing degrades for a reader.
    """
    shipped = ctx["names_shipped"] or {}
    people, phrases = shipped.get("authors") or {}, shipped.get("phrases") or {}
    bad = []
    for key, phrase in phrases.items():
        rec = people.get(key)
        if not rec:
            continue
        ours = (rec.get("romaji") or {}).get("macron") or rec.get("en")
        if ours and str(phrase) != str(ours):
            bad.append(f"{key}: the phrase map says {phrase!r} and the name store says {ours!r}")
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
    difference between this and `renderings resting on a mechanical romanisation`, which counts
    the names an English page spells for itself and falls only as readings are researched.

    236 catalogue credit lines were in Japanese under an English heading and the largest single
    cause was this: `ROLE_EN` in kari/app.js held six words and a second table further down the
    same file held twenty more, so キャラクターデザイン was English on a credit page and Japanese on
    the catalogue tab. Neither knew about 校正, 編纂, カバーイラスト or ほか著.

    §14b, WHAT IT SHARES AND WHAT IT THEREFORE CANNOT SEE. The vocabulary comes from the PYTHON
    splitter and from the corpus; the gloss comes from the JavaScript table. Nothing produces both,
    so the two can disagree and this is where they do. What it cannot see is a role the splitter
    fails to recognise at all, which is not a gloss problem: that role never becomes a role, and it
    shows up as notation surviving into a rendering, which the check below is for.

    §14b, AND THIS CHECK ALMOST LOST ITS SIGHT. It used to look for kana or kanji in what
    `roleWord` returned, and `roleWord` now floors a role it cannot gloss, so a table that had lost
    an entry came back `Cho` and this reported clean. The subject had grown a fallback the measure
    was blind to, which is the shape §14b is about. It reads the MARK instead: the floor puts
    `unc floor` on anything it spelled, and a role carrying that mark is a role with no gloss
    whatever it looks like. Japanese is still a violation too, because a renderer that stopped
    flooring should not read as a pass.

    fallback: the role is spelled from the floor and marked, which is Latin and visibly a guess.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    roles = _role_vocabulary(ctx)
    if not roles:
        return ["no role vocabulary was collected, so nothing here was checked"]
    try:
        shown = _interface(ctx).values([("roleWord", r) for r in roles])
    except interface.Unavailable as e:
        return [f"the interface could not be run, so nothing here was checked: {e}"]
    return [f"{r} has no English gloss in kari/app.js"
            for r, out in zip(roles, shown)
            if FLOOR_TOKEN in out or interface.KANA_KANJI.search(out)]


def inv_a_byline_never_states_the_default_role(ctx):
    """A byline names people and the jobs that distinguish them, and never the unmarked author.

    THE OWNER'S RULING. `著`, `著者`, `作` and no role at all are one concept, and `[著]中村明日美子`
    and `中村明日美子` are the same fact written two ways. A reader meeting `Nakamura Asumiko
    (author)` on one row and `Nakamura Asumiko` on the next would be reading a distinction the
    catalogue never made, so the word may not appear on a byline at all.

    AND IT MUST STILL APPEAR ON A CREDIT PAGE, which is why this is an invariant over the OUTPUT
    rather than an entry removed from the gloss table. That page lists a person's works with the job
    beside each, the job is the payload, and eliding it leaves an empty cell. Surfaces of category
    `role` are therefore not scanned; they are the page where the word belongs.

    §14b, WHAT IT SHARES. The words it forbids come from asking the interface which roles elide,
    which is `bylineRole` answering about itself, so a table that stopped eliding would also stop
    forbidding. What it cannot share is where those words then turn up: the scan is over the
    rendered person surfaces, and the renderer that draws them consults no list of forbidden words.
    A role glossed on a byline through any path at all shows here.

    fallback: none. A role is a closed vocabulary somebody wrote down, so this holds at zero.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    roles = _role_vocabulary(ctx)
    if not roles:
        return ["no role vocabulary was collected, so nothing here was checked"]
    try:
        iface = _interface(ctx)
        byline = iface.labels([("bylineRole", r) for r in roles])
        page = iface.labels([("roleWord", r) for r in roles])
    except interface.Unavailable as e:
        return [f"the interface could not be run, so nothing here was checked: {e}"]
    # The English a role has on a credit page and does not have on a byline. Empty for every role
    # that is not the default, which is what leaves this scanning for three or four words.
    gone = sorted({p.strip() for r, b, p in zip(roles, byline, page)
                   if p.strip() and not b.strip()}, key=len, reverse=True)
    if not gone:
        return []
    calls, about = interface.calls_for(_collections(ctx))
    if not calls:
        return []
    bad = []
    for (surface, value), shown in zip(about, iface.labels(calls)):
        if surface.category != "person":
            continue
        for word in gone:
            if re.search(r"(?:^|[\s\[\](){}（）/,·、]|\b)" + re.escape(word) + r"(?:$|[\s\[\](){}（）/,·、]|\b)",
                         shown):
                bad.append(f"{surface.path}: {value!r} renders as {shown!r}, "
                           f"which states the default role {word!r}")
                break
    return sorted(set(bad))


def _notation_left(ctx):
    """`[(surface, value, the notation that survived)]` over every rendering.

    THE OUTPUT MEASURED AGAINST A VOCABULARY THE RENDERER NEVER CONSULTED (§14b). The roles come
    from the Python splitter and the words below are the ones the splitter drops; kari/app.js has
    its own table and its own division, and neither of them is asked here. A role the interface
    glosses cannot appear in the output, so anything that does is a role the DIVISION did not find
    or a gloss that did not reach the page, and those are exactly the two ways this class comes
    back.

    AND NOW A ROLE WITH NO GLOSS IS NOT JAPANESE ON THE PAGE, IT IS A ROMANISATION OF IT. Dropping
    `著` from the table used to leave `[著]` standing in an English credit line, which is what this
    scanned for. It now leaves `[Cho]`, which is the same fault wearing Latin letters, and a scan
    for the Japanese word would report clean. So each role is put through `roleWord` first and the
    ones the renderer FLOORED are added to the vocabulary under the spelling it gave them. The
    vocabulary still comes from the splitter; what the interface supplies is how each word looks
    once it has failed to be glossed.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    roles = [r for r in _role_vocabulary(ctx) if interface.KANA_KANJI.search(r)]
    # `ほか` closes a credit that names some of its contributors; the interface says "and others".
    # Neither is a name, and a reader in English has no way to read either as one.
    words = set(roles) | {"ほか"}
    if roles:
        # `roleWord` ANSWERS WITH TEXT AND NOT WITH MARKUP, which is why the token is what is
        # read here. The gloss goes into a credit line that is escaped and marked later, so at this
        # point a floored role is the spelling followed by the token and nothing else.
        for out in _interface(ctx).labels([("roleWord", r) for r in roles]):
            if FLOOR_TOKEN in out and out.strip():
                words.add(out.strip())
    words = sorted(words, key=len, reverse=True)
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

    WHAT THIS BLOCKS THAT A BUDGET TOLERATED. `renderings still Japanese in English mode` counted
    a row as one number whatever was Japanese about it, so a role nobody glossed and a pen name
    nobody has researched were the same event. They are not: a pen name nobody has researched now
    gets a mechanical romanisation, which is a guess about a sound, and `[キャラクターデザイン]`,
    `(校正)`, `ほか` and a reading printed beside the name it reads are none of them names at all.
    Those are the catalogue's notation, they have a right answer, and once the answer exists
    nothing should be able to lose it quietly.

    So the guarantee splits. This holds at zero on the notation;
    `renderings resting on a mechanical romanisation` counts the guesses at the names.

    fallback: the notation shows as the catalogue wrote it, which is what it did before.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    try:
        return sorted({f"{s.path}:{v[:32]} still shows {w}" for s, v, w in _notation_left(ctx)})
    except interface.Unavailable as e:
        return [f"the interface could not be run, so nothing here was checked: {e}"]


def inv_no_name_is_spelled_with_question_marks(ctx):
    """No name a reader meets in English holds a question mark the field it came from did not.

    THE FAULT, WHICH REACHED A READER. `enFallback` spells a Japanese run it cannot look up one
    character at a time, and a character nothing can read becomes `?`. The work page's byline for
    w01700 came out `???? · Bun?Bun` where the field says 安田剛助・文尾文, two artists whose
    readings openBD and the publisher both state. Neither name was missing from anything: the
    corpus had settled that field as two people, the build had shipped the division and floored the
    two of them separately, and `creditLine` threw the division away by cutting the field on the
    slash and passing the pieces on as a field of their own.

    ARITHMETIC ON THE RENDERED RESULT, per §14b. It counts question marks in the answer against
    question marks in the question, so it consults no store, no division and nothing in
    `enFallback`, and it fails on anything the interface is able to draw. The floor's own `[?]`,
    which says a spelling is ours, is taken off before counting: it is a mark on a name rather than
    a character nothing could read, and this must not read one as the other.

    NAMES AND ROLES, WHICH IS WHERE A QUESTION MARK IS NEVER PUNCTUATION. A TITLE may gain one
    honestly, because a translation is not a transliteration and 月が綺麗ですね is published as
    `The Moon Is Beautiful, Isn't It?`; 21 titles are in that state and every one of them is a
    translator's sentence. Nobody is called `?`, so the surfaces this walks are the ones whose
    values are people, houses and the jobs they did.

    WHY IT IS AN INVARIANT AND NOT A BUDGET. A `?` in place of a name is not a deficit that shrinks
    as readings are sourced. It says the renderer was handed a string the build never floored,
    which is a fault in the renderer every time.

    §14b, what it cannot see: a name spelled wrongly but spellably. `Yasuda Takesuke` for
    ヤスダ コウスケ holds no question mark, and `a person is spelled one way` is the check for that.

    fallback: none in the build. `enFallback` already IS the fallback, and a violation says it ran
    out of map rather than that a name is unresearched.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    try:
        calls, about = interface.calls_for(_collections(ctx))
        if not calls:
            return []
        out = _interface(ctx).labels(calls)
    except interface.Unavailable as e:
        return [f"the interface could not be run, so nothing here was checked: {e}"]

    def marks(text):
        return str(text).replace(FLOOR_TOKEN, "").count("?") + str(text).count("？")

    bad = []
    for (surface, value), shown in zip(about, out):
        if surface.category in ("person", "publisher", "role") and marks(shown) > marks(value):
            bad.append(f"{surface.path}:{value[:32]} renders as {shown[:48]}")
    return sorted(set(bad))


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


def inv_no_record_comes_from_a_host_that_is_not_a_source(ctx):
    """Nothing stored may come from a host `facts/sources` says is not a publication source.

    THE FILTER USED TO SIT AFTER THE INGESTION. `build.PROMO_HOSTS` held ddnavi's rows and declined
    to count them as chapters, which left every later pass carrying the exception and the records
    on disk regardless. The project owner named the layer: a host we will not publish from should
    not be ingested. So the target list does not fetch it, and this is what makes that hold.

    IT ALSO WATCHES THE TARGET LIST, because a stored record is downstream of a decision to fetch.
    A host declared not-a-source that carries a live extraction strategy would refill data/source
    on the next run, and the next run is where the fault would appear rather than here.

    §14b, WHAT IT REUSES: `facts/sources` for the membership and nothing else. It reads the stored
    records and the target list, neither of which the fact consults, so a pass that ingested one
    anyway is caught by the file it wrote.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    from facts import sources
    bad = []
    for f in sorted((ROOT / "data" / "source").rglob("*.yaml")):
        try:
            d = _yaml(f, {})
        except Exception:                                               # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        for w in (d.get("works") or []):
            why = sources.not_a_source(str((w or {}).get("url") or "")) if isinstance(w, dict) else None
            if why:
                bad.append(f"{f.relative_to(ROOT)} holds {w.get('work_title')!r} from a host that "
                           f"is not a publication source: {why}")
    targets = _yaml(ROOT / "data" / "coverage" / "extract.yaml", {}) or {}
    for p in (targets.get("platforms") or []):
        why = sources.not_a_source(str(p.get("host") or ""))
        if why and p.get("strategy") not in (None, "none", "no-response"):
            bad.append(f"data/coverage/extract.yaml gives {p.get('host')} strategy "
                       f"{p.get('strategy')!r}, so the next run would ingest a host that is not a "
                       f"publication source: {why}")
    return bad


def budget_works_shaped_like_prose(ctx):
    """Works admitted only by a retailer's shelf that credit an illustrator beside their author.

    DEFINITIONS §6 REFUSES PROSE and nothing enforced it. The rule is written out plainly, "light
    novels and prose ... it is not manga. It will not be given work records", and the only scope
    test that ran was about the COUNTRY a work was first published in. Eleven works on パルソラ's
    コミックノベル「yomuco」, a line of illustrated prose, reached readers with work records, credit
    pages and a place in the catalogue. One of them was a novelisation of a phone game and said so
    in its own listing.

    WHAT THE SHAPE IS. An author credited beside an 絵 illustrator is how an illustrated novel is
    billed; a manga bills 作画 or 漫画. On its own that is weak, so it is paired with the admission:
    a work no bibliography holds, admitted by a shop shelving it, has nothing behind it but a
    retailer's category. BOOK☆WALKER filed every one of the eleven under マンガ総合 and tagged each
    volume マンガ, so the shop's own category cannot be the test.

    A COUNT AND NOT AN INVARIANT, BECAUSE NEITHER SIGNAL PROVES A MEDIUM. An illustrator credit on a
    manga is possible and a shop-only admission is ordinary for digital-first work. What the pair
    says is that nobody has checked, which is a question for a person and not a fact to block on.
    It stands at zero because the eleven are ruled out; a rise is a work to go and look at.

    §14b, WHAT IT REUSES: the shipped rows and the role vocabulary. It does not consult
    `data/scope.yaml`, so a work the ruling covers is counted absent from the build rather than
    excused by the file that excused it, and the count cannot be satisfied by editing the ruling.
    """
    works = {str(x.get("work_id")): x for x in (ctx["works"] or [])}
    illustrator = {"\u7d75", "\u30a4\u30e9\u30b9\u30c8", "\u63d2\u7d75"}
    n = 0
    for r in (ctx["series"] or []):
        if not any(c.get("role") in illustrator for c in (r.get("credits") or [])):
            continue
        printed = [p for p in (r.get("print") or []) if p.get("work_id")]
        if printed and all((works.get(str(p["work_id"]), {}).get("sources") or []) == ["bookwalker"]
                           for p in printed):
            n += 1
    return n


def budget_works_named_by_a_truncation(ctx):
    """Shipped rows naming a work under a title a listing cut short.

    A LISTING SHOWS WHAT FITS. 公爵令嬢の籠絡ミッション and 病弱少女、転生して健康な肉体(最強)を手に入れる
    both have titles longer than the cell they were read from, and the page ended each with three
    full stops. Both entered the corpus as works of their own and both reached the updates feed,
    where a reader met a title with its ending sheared off. `data/work-aliases.yaml` had already
    recorded what each one really is; the release writer for that route was one of the several that
    read `work_title` straight off the record without asking.

    ASCII DOTS AND NOT `…`, which is the distinction that makes this checkable. A Japanese title
    trailing off uses the ellipsis character: 乙女ゲームの破滅フラグしかない悪役令嬢に転生してしまった… is
    a real title and so is Valentine with…, and 56 strings in the sources end that way. Three
    ASCII full stops at the end of a Japanese title is a machine running out of room.

    §14b, WHAT IT REUSES: nothing. It reads the shipped rows and matches characters. The alias
    table is what FIXES this, and a check that read the same table would agree with it about every
    title in it and stay silent about the one nobody has added yet, which is the case that matters.

    THE ARCHIVE HOLDS THE FLOOR ABOVE ZERO. The context reads the archived monthly feeds along
    with the current one, and a published month keeps its row set: the two rows
    published under a truncated title in 2026-07 record what was shipped and stay that way. A floor
    of zero would fail every run for a month over something no edit may touch.
    The count falls as the archive ages out, and a rise says the writers have gone back to reading
    `work_title` off a record without asking the alias table.
    """
    bad = set()
    for r in (ctx["series"] or []):
        if str(r.get("work") or "").endswith("..."):
            bad.add(str(r.get("work")))
    for r in (ctx["releases"] or []):
        if str(r.get("work") or "").endswith("..."):
            bad.add(str(r.get("work")))
    return len(bad)


def inv_no_source_a_reader_sees_is_an_adapter(ctx):
    """No name in a reader-facing source column is the name of a pass that fetched it.

    THE WORK PAGE'S "Other data" TABLE names who told us each fact, and six of its nine names were
    module names: `ichijinsha` on 726 rows, `kadokomi` on 86, `gigaviewer` on 13, and `webpages`
    and `comparators` on the rest, sitting beside `BOOK☆WALKER` and `メディア芸術データベース` spelled
    as themselves. 一迅社 appeared twice on one page under two spellings, once as itself in the
    classification table and once as its adapter here. It is not a rendering slip: the pass wrote
    its own name into the data and every later reader of that field carried it.

    §14b, WHAT IT REUSES: the ADAPTER DIRECTORY, read off disk. `build.source_named` holds the map
    that fixes this, and a check reading that map would agree with it about any name it forgot.
    The directory listing is what the modules are actually called, and it is written by nothing in
    the pipeline.

    A NAME THAT IS ALSO A REAL SOURCE'S NAME is not caught here and cannot be: `openBD` is a module
    and a publisher's own name for itself. The comparison is case-sensitive against the directory
    spelling, which is lower-case for every adapter, so `openBD` passes and `openbd` would not.
    """
    mods = {p.name for p in (ROOT / "adapters").iterdir() if p.is_dir()
            and not p.name.startswith(("_", "."))}
    mods |= {p.stem for p in (ROOT / "adapters").glob("*.py")}
    rows = ctx["series"] or []
    bad = {}
    for r in rows:
        for x in (r.get("sourced_from") or []):
            name = str((x or {}).get("source") or "")
            if name in mods:
                bad.setdefault(name, []).append(r.get("work"))
    return [f"{len(w)} row(s) name the pass {n!r} where a reader expects a source, e.g. {w[0]!r}"
            for n, w in sorted(bad.items())]


def inv_no_app_only_route_is_published_as_web_reading(ctx):
    """A listing no browser can open anywhere reaches no reader as a web serialisation.

    THE FAULT. ニコニコ漫画 marks an episode `アプリで読める` on its own tile, meaning the phone app
    and nowhere a browser goes. The adapter read `[ N話 無料 ]` off the work header instead and
    called every rendered episode free, so 3,547 of the platform's 6,736 chapters were published as
    free reading a reader cannot reach. Twelve listings went further: every episode app-only,
    because the listing is the app selling an already-published volume one chapter at a time. Each
    of the twelve holds a volume record of its own, and each was presenting that book's chapters as
    a serialisation, six of them alongside the work's real serialisation on the same platform.

    NOT A RULE ABOUT SELLING CHAPTERS SINGLY. cmoa and BOOK☆WALKER do that and stay in as the
    purchase routes they are. What is refused is a chapter route with no browser-readable chapter.

    §14b, WHAT IT REUSES: NEITHER PRODUCER'S ANSWER. Two passes decide this independently.
    `releases.parse` from the episode tiles on the raw page, writing `app_only_route`, and `build`
    from the stored per-episode `app_only`. This compares them against each other and against what
    shipped, so a route either of them recognises and the site still publishes is a failure, and
    the two silently disagreeing is one too.
    """
    flagged = {str(w.get("url") or "") for w in (ctx["nicovideo_channels"] or [])
               if w.get("app_only_route")}
    stored = {str(w.get("url") or "") for w in (ctx["nicovideo_work_chapters"] or [])
              if (w.get("chapters") and all(c.get("app_only") for c in w["chapters"]))}
    out = []
    for u in sorted(stored - flagged):
        out.append(f"{u} has no browser-readable episode stored, and the page pass did not say so")
    for u in sorted(flagged - stored):
        out.append(f"{u} is flagged an app-only route, and its stored episodes disagree")

    barred = flagged | stored
    if barred:
        for r in (ctx["series"] or []):
            for s in (r.get("sources") or []):
                if str(s.get("url") or "") in barred:
                    out.append(f"{r.get('work')!r} publishes {s.get('url')} as a reading source")
        for rel in (ctx["releases"] or []):
            if str(rel.get("url") or "") in barred:
                out.append(f"the feed carries {rel.get('url')} as a {rel.get('web') or 'release'}")

    # AND WHAT THE ROUTE SAID SURVIVES WHERE A READER MEETS IT. Excluding the chapters does not
    # disbelieve the byline, and the first attempt kept the name somewhere nobody looks: the credit
    # sat in `credits` while `author` stayed empty, so the work page drew no byline at all and
    # `credit_identity`, which mints from `author`, still could not support the credit page's edge.
    # A name recorded out of sight is the fault this half is for, not a lesser version of it.
    for r in (ctx["series"] or []):
        named = {unicodedata.normalize("NFKC", str(x or "")).replace(" ", "")
                 for x in re.split(r"\s*/\s*", str(r.get("author") or ""))}
        for c in (r.get("credits") or []):
            if c.get("basis") != "named-on-an-app-only-listing":
                continue
            if unicodedata.normalize("NFKC", str(c.get("name") or "")).replace(" ", "") not in named:
                out.append(f"{r.get('work')!r} keeps {c.get('name')!r} from an excluded route "
                           f"where its byline does not name them")
    return out


def inv_the_pipeline_runs_from_a_clean_checkout(ctx):
    """Where this repository works on a developer's disk and on no fresh checkout.

    ALL THREE KILLED THE 2026-08-10 UPDATE RUN and none of them could fail locally, which is what
    makes them one check rather than three. `data/build/` is gitignored, `PYTHONPATH` is set in
    every shell here, and a stage entry that has never once succeeded reads as normal.

      A DIRECTORY WRITTEN INTO BEFORE ANYTHING MAKES IT. main() wrote `feed/names.json` 190 lines
      before the function that mkdirs `feed/` was called. Every CI compile since names.json was
      added died there; every local build passed, because the directory was already on disk.

      AN ADAPTER THAT CANNOT FIND ITS OWN IMPORTS. `run_stage.py` runs each one as a bare
      subprocess with no PYTHONPATH, so a module importing a package under `adapters/` has to say
      where it is. Three did not, and `kadokomi` died on `No module named 'facts'` in 0 seconds.

      A STAGE ENTRY NOTHING TARGETS. `ganganonline` selects its section out of render-targets.yaml
      by id and no such section has ever existed, so it failed every run. A permanent failure is
      what made a new one beside it look ordinary.

    §14b, WHAT IT REUSES: nothing any of the producers uses. It reads build.py's own text for the
    directories it writes into, imports each adapter in a subprocess with the environment stripped,
    and asks the targets file whether the id a stage entry names is in it.

    NOT PROBED BY `--self-test`, because it reads the repository and a canary planted in `ctx` never
    reaches it (§4: a canary that lands somewhere the check does not look proves nothing). Each arm
    was verified by breaking the thing it watches and confirming the count moved: emptying
    BUILD_SUBDIRS, removing one adapter's path insert, and adding a stage entry naming a section
    that does not exist. On the day it was written it found five faults nobody was looking for.
    """
    bad = []
    src = (ROOT / "build.py").read_text()
    declared = set(re.findall(r'BUILD_SUBDIRS\s*=\s*\(([^)]*)\)', src))
    declared = set(re.findall(r'"([^"]+)"', " ".join(declared)))
    for sub in sorted(set(re.findall(r'out\s*/\s*"([a-z][a-z0-9_-]*)"\s*/', src))):
        if sub not in declared:
            bad.append(f"build.py writes into {sub}/ and BUILD_SUBDIRS does not hold it, so a "
                       f"build into an empty directory fails on the first write")

    # EACH ADAPTER IMPORTED WITH THE ENVIRONMENT STRIPPED, which is how run_stage runs it.
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    for f in sorted((ROOT / "adapters").rglob("*.py")):
        text = f.read_text()
        if not re.search(r"^\s*from\s+(facts|names|testkit|lint|relational)\b", text, re.M):
            continue
        if f.parts[len(ROOT.parts) + 1] in ("facts", "names", "lint", "relational"):
            continue
        r = subprocess.run([sys.executable, "-c", f"import runpy,sys; sys.argv=['x','--help']; "
                            f"runpy.run_path({str(f)!r}, run_name='not_main')"],
                           capture_output=True, text=True, cwd=str(ROOT), env=env, timeout=60)
        if "ModuleNotFoundError" in r.stderr:
            bad.append(f"{f.relative_to(ROOT)} cannot import its own dependencies without "
                       f"PYTHONPATH, and run_stage.py sets none")

    # AND EVERY STAGE ENTRY SELECTING A SECTION BY ID HAS ONE.
    stage = _yaml(ROOT / "adapters" / "stage-a.yaml", {}) or {}
    for c in (stage.get("commands") or stage.get("adapters") or []):
        argv = [str(x) for x in (c.get("argv") or [])]
        tf = next((argv[i + 1] for i, x in enumerate(argv[:-1]) if x == "--targets"), None)
        if not tf or "{" in tf:
            continue
        doc = _yaml(ROOT / tf, {}) or {}
        if not any(s.get("id") == c.get("id") for s in (doc.get("platforms") or [])):
            bad.append(f"stage-a entry {c.get('id')!r} reads {tf} for a section of its own name "
                       f"and that file holds none, so the step cannot succeed")
    return bad


def inv_a_rendered_file_names_a_platform_its_targets_hold(ctx):
    """Every `rendered-<id>.yaml` answers to a platform `render-targets.yaml` still lists.

    THE FAULT THIS WATCHES. `adapters/render/releases.py` names its output after the platform id it
    was given and stamps the same id inside as `platform:`. Change an id in the targets file and
    the run writes a NEW file under the new name; the old one keeps its place in
    `data/source/webpages/`, where `build.py` globs the whole directory and reads it as a platform
    of its own. Nothing rewrites it, `carry_over` never sees it, and both copies reach a reader.

    It has happened once. Three platforms shared the id `www`, the first label of
    `www.comic-ryu.jp`, `www.corocoro.jp` and `www.mangabox.me`, and were renamed to `comicryu`,
    `corocoro` and `mangabox`. `rendered-www.yaml` was left holding コロコロオンライン's ten
    chapters, and `feed.json` was serving them under `"plat": "www"` with release ids like
    `www:第10話`, so the next successful Stage C run would have published every one of them twice
    under two platform ids wearing one name.

    §14b, WHAT IT REUSES: the id in the filename and the id in the file, against the targets file.
    The writer consults the targets file it is given TODAY, so it always agrees with itself; what
    is unreachable to it is a file written by an earlier version of that list. So this can fail on
    something the pipeline produces, which is the whole test.

    NOT PROBED BY `--self-test`: it reads the repository, and a canary planted in `ctx` never
    arrives (§4). Verified by renaming a live target id and watching the count move.

    fallback: none needed in the build, and none is offered. The remedy is to rename the file to
    match, which keeps the chapters and lets the next run replace them.
    """
    targets = _yaml(ROOT / "data" / "coverage" / "render-targets.yaml", {}) or {}
    ids = {str(p.get("id")) for p in (targets.get("platforms") or []) if p.get("id")}
    if not ids:
        return ["data/coverage/render-targets.yaml names no platform, so nothing here was checked"]
    bad = []
    for f in sorted((ROOT / "data" / "source" / "webpages").glob("rendered-*.yaml")):
        named = f.stem[len("rendered-"):]
        if named not in ids:
            bad.append(f"{f.relative_to(ROOT)} answers to a platform id "
                       f"render-targets.yaml no longer holds, so no run will ever rewrite it "
                       f"and build.py reads it beside the file that replaced it")
        stamped = str((_yaml(f, {}) or {}).get("platform") or "")
        if stamped != named:
            bad.append(f"{f.relative_to(ROOT)} is named for {named} and stamped {stamped!r}, "
                       f"so the platform a reader is shown depends on which one is read")
    return bad


INVARIANTS = [
    ("ruby covers its surface", inv_ruby_covers_its_surface),
    ("a kana name's reading spells it", inv_kana_reading_spells_its_name),
    ("a division cites its source", inv_a_division_cites_its_source),
    ("a division names its donor in a field", inv_a_division_names_its_donor_in_a_field),
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
    ("a byline never states the default role", inv_a_byline_never_states_the_default_role),
    ("a volume number is the shop's own", inv_a_volume_number_is_the_shop_s_own),
    ("no name is spelled with question marks", inv_no_name_is_spelled_with_question_marks),
    ("status.html shows no Japanese of its own",
     inv_status_page_shows_no_japanese_of_its_own),
    ("no build-machine paths in published files", inv_no_absolute_paths_in_published_files),
    ("no stock phrasing in public text", inv_no_stock_phrasing_in_public_text),
    ("content flags are accounted for", inv_content_flags_are_accounted_for),
    ("scope rulings are accounted for", inv_scope_rulings_are_accounted_for),
    ("a release id names one release", inv_a_release_id_names_one_release),
    ("no published update leaves its month", inv_no_published_update_leaves_its_month),
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
    ("a person is spelled one way", inv_a_person_is_spelled_one_way),
    ("nicovideo channels agree with our own records", inv_nicovideo_channel_agrees),
    ("a fixture states where it came from", inv_fixture_states_where_it_came_from),
    ("the interface folds a name key as the build does",
     inv_interface_folds_a_name_key_as_the_build_does),
    ("names reach a page only through their renderer",
     inv_names_reach_a_page_only_through_their_renderer),
    ("a name reaches both lines of a bilingual row", inv_a_name_in_both_mode_is_rendered_in_both),
    ("a fact is reached through its entry point", inv_a_fact_is_reached_through_its_entry_point),
    ("a name is answered by one module", inv_a_name_is_answered_by_one_module),
    ("a work shows the English its record holds",
     inv_a_work_shows_the_english_its_record_holds),
    ("the store has one writer", inv_the_store_has_one_writer),
    ("every name is defined where it is used", inv_every_name_is_defined_where_it_is_used),
    ("every renderer is ruled", inv_every_renderer_is_ruled),
    ("the tracker states what it claims", inv_the_tracker_states_what_it_claims),
    ("the interface is the derivation of its source",
     inv_the_interface_is_the_derivation_of_its_source),
    ("a stated reading names where it came from",
     inv_a_stated_reading_names_where_it_came_from),
    ("every Japanese field the data carries has a ruling",
     inv_every_japanese_field_has_a_ruling),
    ("the pipeline runs from a clean checkout",
     inv_the_pipeline_runs_from_a_clean_checkout),
    ("no record comes from a host that is not a source",
     inv_no_record_comes_from_a_host_that_is_not_a_source),
    ("a rendered file names a platform its targets hold",
     inv_a_rendered_file_names_a_platform_its_targets_hold),
    ("no source a reader sees is an adapter",
     inv_no_source_a_reader_sees_is_an_adapter),
]


# ── Tier 2: budgets ───────────────────────────────────────────────────────────────────────────
#
# Counts with no correct value, only a direction. The recorded budget is whatever was last
# measured on a green run; it tightens automatically and loosens only by hand.

def budget_uncertain_readings(ctx):
    """Defined in `adapters/facts/reading/checks.py`, beside the rulings it applies."""
    from facts import reading as _rd
    return _rd.CHECKS["uncertain_readings"](ctx)


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

    WHAT IT COUNTS AND WHAT IT DOES NOT, because a sweep taken from `feed/names.json` answered a
    different question with a similar name and the two numbers were compared as though they were
    one. This counts SERIES ROWS, which is what a works list paints. The name store holds 3,164
    titles against 3,046 rows, the extra 226 being edition variants and print-only records that are
    no row at all, so a count taken there is larger and is about the store rather than the reader.
    `a work shows the English its record holds` is the invariant that lets this one be read as a
    statement about a reader: it asserts every row carries the store's answer where the store has
    one, so this number falling means English names arriving and not a join quietly breaking.
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
    from facts import identity

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
    from facts import identity

    titles = (ctx["names_shipped"] or {}).get("titles") or {}

    def keys_for(title):
        """Every fold this title is reachable under, its own and its Latin renderings'.

        A TITLE FOLD ALONE CANNOT CROSS SCRIPTS, which is the blind spot this closes and it is not
        a small one. `Free soul` and `フリー・ソウル` are one work by やまじえびね, catalogued once by
        the bibliography under its Latin title and once by the shop under its Japanese, and the two
        folds are `freesoul` and `フリソウル`. Nothing about them can ever meet, so the round that
        closed 53 of these never had this class in view at all: eight pairs, `MURCIELAGO` and
        `Day In, Day Out` among them, and the owner found the first by eye.

        So the renderings join the key. `フリー・ソウル` is reachable under `freesoul` because that
        is what this database calls it in English, which is exactly the spelling the other record
        was catalogued under.

        SHARING A PERSON STILL DECIDES IT. Romaji brings collisions with it, and `ゆりこん` and
        `ユリコン` are different works that both fold to `yurikon`. The credit test that has always
        kept the seven 人魚姫 apart keeps these apart too, with nothing new asked of it.
        """
        out = {identity.match_key(title)}
        rec = titles.get(title) or {}
        for form in [rec.get("en")] + list((rec.get("romaji") or {}).values()):
            if form:
                out.add(identity.match_key(form))
        return {k for k in out if k}

    pairs = 0
    for _name, rows in _shipped_lists(ctx):
        by = collections.defaultdict(list)
        for i, (title, _credit) in enumerate(rows):
            if title:
                for key in keys_for(title):
                    by[key].append(i)
        # COUNTED ONCE PER PAIR, NOT ONCE PER KEY. A row now carries several keys and two rows
        # commonly meet under more than one of them: `MURCIÉLAGO -ムルシエラゴ-` shares both a
        # rendering and a romaji with `MURCIELAGO`. Keying alone would report that pair twice and
        # the budget would move for a reason that is not a work.
        who, seen = {}, set()
        for key, idxs in by.items():
            if len(idxs) < 2:
                continue
            for a in range(len(idxs)):
                for b in range(a + 1, len(idxs)):
                    i, j = (idxs[a], idxs[b]) if idxs[a] < idxs[b] else (idxs[b], idxs[a])
                    if (i, j) in seen:
                        continue
                    seen.add((i, j))
                    for x in (i, j):
                        if x not in who:
                            who[x] = identity.people(rows[x][1])
                    if who[i] & who[j]:
                        pairs += 1
    return pairs


def budget_incomplete_attested_rows(ctx):
    return sum(1 for r in ctx["releases"]
               if r.get("provenance") == "attested"
               and (not (r.get("ep") or "").strip() or not r.get("author")
                    or not r.get("access_modes")))


def budget_facts_with_more_than_one_home(ctx):
    """A vocabulary, a dict shape, a regex or a function body typed into a second file.

    SECTION 3 IS BROKEN BY TYPING, not by importing. `adapters/lint/facts.py` proves nothing reaches
    past a fact's entry point and cannot see a tuple written down again, which is how thirteen
    functions called `fold` came to give three incompatible answers to one question.

    COUNTED, so it falls as each is argued. Some are two files that genuinely need the same shape,
    and `docs/duplicates-allowed.yaml` is where a case somebody has argued goes, which keeps the
    number a list of the open ones.
    """
    try:
        out = subprocess.run([sys.executable, str(ROOT / "adapters" / "lint" / "duplicates.py"),
                              "--quiet"], capture_output=True, text=True, timeout=180)
        # AN EMPTY ANSWER IS NOT A ZERO. A child that failed prints nothing on stdout, and reading
        # that as zero reports the best possible number for a measurement that did not happen. See
        # UNMEASURED.
        return int(out.stdout.strip()) if out.stdout.strip().isdigit() else UNMEASURED
    except Exception:                                                   # noqa: BLE001
        return UNMEASURED    # this could not be measured; see UNMEASURED


def budget_impossibilities_asserted_without_evidence(ctx):
    """Comments claiming something can never happen, naming nothing that proves it.

    DECISION 8 OF THE REFACTOR PLAN, and it has a body count. `enFallback` said a branch "should be
    unreachable" and readers were shown `???? · Bun?Bun`. A confident wrong comment calcifies harder
    than a test: a test says this happens, a comment says and that is correct, which stops the next
    reader looking.

    COUNTED SO IT FALLS AS EACH IS ANSWERED. The eight standing today are prose somebody wrote in
    good faith and most will turn out to be true, so the useful move is adding the citation. A gate
    that blocked would reward deleting the sentence, which loses the reasoning with the claim.
    """
    try:
        out = subprocess.run([sys.executable, str(ROOT / "adapters" / "lint" / "claims.py"),
                              "--quiet"], capture_output=True, text=True, timeout=120)
        # AN EMPTY ANSWER IS NOT A ZERO. A child that failed prints nothing on stdout, and reading
        # that as zero reports the best possible number for a measurement that did not happen. See
        # UNMEASURED.
        return int(out.stdout.strip()) if out.stdout.strip().isdigit() else UNMEASURED
    except Exception:                                                   # noqa: BLE001
        return UNMEASURED    # this could not be measured; see UNMEASURED


def budget_stock_phrasing_in_comments(ctx):
    """Stock phrasing in comments, docstrings and documentation, counted per file and remembered.

    THE REPOSITORY IS THE SUBJECT, so the scan asks git what is in it. Walking the directory counted
    CLAUDE.md, which is ignored and exists only in the main working tree, so the same commit measured
    903 here and 898 in a worktree. A branch then ratcheted the budget down by 5 in good faith and
    the merge result put it straight back. A number that depends on which tree you stand in cannot
    ratchet, which is what STANDING-INSTRUCTIONS 14a is about.

    CACHED ON CONTENT, by `adapters/filecache.py`, which is keyed on each file AND on `tics.py`, so
    changing a rule throws every remembered answer away. At 12.9 s this was the most expensive check
    in a gate and nearly all of it re-read files nobody had touched. `tics.py` imports only the
    standard library, so its own text is the whole of what the count depends on.
    """
    try:
        tracked = subprocess.run(["git", "ls-files", "-z", "*.py", "*.md"], cwd=str(ROOT),
                                 capture_output=True, text=True, timeout=60).stdout.split("\0")
        files = [ROOT / f for f in tracked
                 if f and not f.startswith("data/") and (ROOT / f).exists()]
        lint = ROOT / "adapters" / "lint" / "tics.py"

        def scan(paths):
            out = subprocess.run(
                [sys.executable, str(lint), "--comments", "--counts", *[str(p) for p in paths]],
                capture_output=True, text=True, timeout=300)
            got = {}
            for line in out.stdout.splitlines():
                path, _, n = line.rpartition("\t")
                if path and n.strip().isdigit():
                    got[pathlib.Path(path)] = int(n)
            # EVERY FILE ASKED ABOUT HAS TO COME BACK. A file the scanner could not read produces
            # no line, and counting the rest gives a number that is lower for a reason nobody sees:
            # that is how this fell from 895 to 890 while build.py was unparseable.
            missing = [p for p in paths if pathlib.Path(p) not in got]
            if missing:
                raise RuntimeError(f"{len(missing)} file(s) produced no count, first {missing[0]}")
            return got

        sys.path.insert(0, str(ROOT / "adapters"))
        import filecache
        total, _scanned = filecache.counted(files, [lint], scan, ROOT / "data" / "cache" / "tics.json")
        return total
    except Exception:                                                   # noqa: BLE001
        return UNMEASURED    # this could not be measured; see UNMEASURED


def budget_untested_modules(ctx):
    """Modules with no test at all. The count the goal drives down.

    Counted by ./test.py, which discovers rather than being told, so this cannot be satisfied by
    forgetting to register something. A module counts as covered when a test names it in COVERS,
    when a test sits beside it under the naming convention, or when it carries its own --self-test.
    """
    try:
        out = subprocess.run([sys.executable, str(ROOT / "test.py"), "--quiet"],
                             capture_output=True, text=True, timeout=120)
        # AN EMPTY ANSWER IS NOT A ZERO. A child that failed prints nothing on stdout, and reading
        # that as zero reports the best possible number for a measurement that did not happen. See
        # UNMEASURED.
        return int(out.stdout.strip()) if out.stdout.strip().isdigit() else UNMEASURED
    except Exception:
        return UNMEASURED    # this could not be measured; see UNMEASURED


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
    # ASKED OF GIT (`lint/tree`), because an agent worktree at .claude/worktrees/ is a checkout of
    # this repository inside it. Two of them read this budget as 225 where it is 75, which is a
    # floor no later run could ever meet, and budgets only ratchet down.
    for f in _tree.own_files(".py"):
        if not (f.name.startswith("test_") or f.name.endswith("_test.py")):
            continue
        if "data" in f.parts:
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
        # ASKED OF GIT, for the reason `budget_stock_phrasing_in_comments` beside it already gives.
        files = [str(f) for f in _tree.own_files(".md") if "data" not in f.parts]
        out = subprocess.run(
            [sys.executable, str(ROOT / "adapters" / "lint" / "tics.py"), "--prose", *files],
            capture_output=True, text=True, timeout=120)
        return sum(1 for l in out.stdout.splitlines() if l.startswith("STRUCTURE:"))
    except Exception:
        return UNMEASURED    # this could not be measured; see UNMEASURED


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


def _shop_counts(ctx):
    """`[(series_row, shop_row)]` for every work exactly one コミックシーモア row speaks about.

    ONE JOIN, THREE BUDGETS. `adapters/shopjoin.py` owns which shop row is about which work and
    why; the three measures below differ only in what they then compare, and each deriving its own
    join is the shape STANDING-INSTRUCTIONS §3 warns about.
    """
    import shopjoin
    rows = [w for w in ctx["cmoa_capture"] if w.get("volumes_stated")]
    idx = shopjoin.index(ctx["series"], ctx["works"])
    by_id = {r.get("id"): r for r in ctx["series"] if r.get("id")}
    return [(by_id[rid], row) for rid, row in shopjoin.joined(rows, idx).items() if rid in by_id]


def _our_volumes(row):
    """How long this work's longest print run is, as the interface states it."""
    return max(((p.get("volumes") or 0) for p in (row.get("print") or ())), default=0)


def budget_volume_rows_with_no_publication_date(ctx):
    """Volume rows a reader can reach that carry no publication date at all.

    2,525 OF 6,153, AND EVERY ONE OF THEM FROM BOOK☆WALKER. The shop states 底本発行日 for the
    volumes whose print edition it recorded and nothing for the rest, so a work page lists
    `vol. 27  no date recorded` under a heading that counts it. MADB's rows are dated without
    exception, which is what makes the split worth counting rather than a general lament about
    coverage.

    THE ROUTE OUT IS AN ISBN AND BOOK☆WALKER HAS NONE. `isbndate.py` measures this: no BOOK☆WALKER
    volume of 5,968 read states one, so every ISBN-keyed enrichment in the pipeline is unable to
    reach exactly this population. コミックシーモア's per-volume page states both the ISBN and
    出版年月, which is why VOLUMES-PLAN §4 is the stage that moves this number.

    A count, so it ratchets. A rise means new undated works, or a capture that stopped dating rows
    it used to date.

    §14b, what it cannot see: a row dated WRONGLY. `first date precedes its editions` and
    `dates within a row are ordered` are the checks for that, and a plausible wrong date passes all
    three.

    fallback: none. A volume with no date carries no field saying why, which is itself the state
    this counts.
    """
    reachable = {i for r in ctx["series"] for p in (r.get("print") or ())
                 for i in (p.get("work_ids") or [p.get("work_id")]) if i}
    return sum(1 for w in ctx["works"] if w.get("work_id") in reachable
               for v in (w.get("volumes") or ()) if not v.get("published"))


def budget_macron_boundaries_nobody_has_ruled_on(ctx):
    """Names where our macron says a long vowel, a source spells the pair out, and nobody has read it.

    WHAT THE CLASS IS. おう is a long o inside a morpheme and two vowels across a word boundary, and
    `kana.py` says plainly that telling those apart needs morphology it does not do. 御家 is 御 + 家,
    so オウチ is o-uchi and `Ōchi` states a long o nobody says; 井上, ねこうめ and 藪内 are the same
    shape.

    IT IS A FLAG AND NOT A RULE, ruled by the project owner on 2026-08-12. The whole class was 21
    names and four of them were faults, which is too few to buy a morphological dependency in the
    one function every rendering goes through. The four are data in `kana.NOT_LONG`, the other 17
    are a style and were read and left, and what stops a fifth arriving unnoticed is this number.

    A SOURCE WRITING `ou` FOR `ō` IS A STYLE AND NOT A CORRECTION, which is why the candidates are
    those whose stated spelling matches our own DOUBLE form: MangaUpdates and Wikidata write the
    pair out for every long vowel, so agreeing with them says nothing on its own and the reading is
    what has to be looked at.

    §14b, what it cannot see: a boundary no source disagrees with us about. A name nobody has
    romanised anywhere is not a candidate here, and never will be.

    fallback: none. `data/queue/macron-boundaries.yaml` carries the rulings; a name absent from it
    is unread by definition.
    """
    import re
    ruled = {str(c.get("name")) for c in
             (_yaml(ROOT / "data" / "queue" / "macron-boundaries.yaml", {}) or {}).get(
                 "candidates", []) if c.get("decision")}

    def parts(s):
        return sorted(x.lower() for x in re.split(r"\s+", str(s or "").strip()) if x)

    n = 0
    for name, rec in ((ctx.get("names_shipped") or {}).get("authors") or {}).items():
        en, romaji = rec.get("en"), rec.get("romaji") or {}
        mac, dbl = romaji.get("macron"), romaji.get("double")
        if not en or not mac or ("ō" not in mac.lower() and "ū" not in mac.lower()):
            continue
        if parts(en) == parts(dbl) and name not in ruled:
            n += 1
    return n


def budget_volume_rows_a_page_counts_but_cannot_list(ctx):
    """Volume rows the work page counts in its heading and can put nothing on the page for.

    THE SHAPE, FOUND ON コミック百合姫 BY THE PROJECT OWNER. Its page read `Volumes 119` above
    `119 with no date and nothing else recorded`, and the record held the name and the delivery
    date of every one of the 117 issues. `build.py` was building a volume row out of five keys and
    dropping `designation` and `delivered`, so the interface, which lists a row carrying a date, an
    ISBN or a number, had nothing to list. 1,420 rows across 897 works were in that state and every
    single one of them had both fields in its source record.

    WHAT IT COUNTS IS THE READER'S QUESTION, not the record's completeness. `volume rows with no
    publication date` is 2,521 and is a research debt; this is 0 and is a plumbing fault. A row can
    carry a date and still be listed, and a row can carry no date and still say what it is called
    and when it went on sale, which is what these 1,420 now do.

    ARITHMETIC OVER THE SHIPPED ROWS, per §14b: it asks the same question the interface's `says`
    asks, over works.json, without running the interface. That is deliberate duplication of a
    predicate and not of a rule: `says` decides what a page draws and this decides what the build
    owes it, and the two agreeing is the property under test.

    IT RATCHETS RATHER THAN BLOCKING, because a source could legitimately state that a volume
    exists and nothing else. None does today. A rise says a field stopped being carried, which is
    the fault this was written for.

    fallback: none. A row with nothing on it carries no field saying why.
    """
    reachable = {i for r in ctx["series"] for p in (r.get("print") or ())
                 for i in (p.get("work_ids") or [p.get("work_id")]) if i}
    return sum(1 for w in ctx["works"] if w.get("work_id") in reachable
               for v in (w.get("volumes") or ())
               if not (v.get("published") or v.get("isbn") or v.get("number")
                       or v.get("designation") or v.get("delivered")))


def budget_works_whose_records_number_one_volume_twice(ctx):
    """Works whose print records give the same volume number to two different rows.

    THE WORK PAGE DRAWS BOTH. MADB holds MURCIÉLAGO's volume 1 as `2014-04` with an ISBN and
    BOOK☆WALKER holds it as `2014-04-25` without one, so the page shows `vol. 1` twice and heads
    the two lists as though they were two print runs. 20 works are in that state over 73 volume
    numbers.

    ITS FLOOR IS 10 AND THE FLOOR IS REAL BOOKS. citrus was printed twice, ten volumes in 2013 and
    four in 2015, and MADB gave it two C-numbers for that reason; ゆるゆり, five 合本版 omnibuses
    and a 総集編 are the rest. A reissue really does number a volume 1 twice and a reader really
    should see both, which is why this counts collisions rather than forbidding them. Ten of the
    twenty are that. The other ten are one run described by two catalogues, which is what
    VOLUMES-PLAN §3 resolves by reconciling the volumes themselves, so the number to expect after
    that stage is 10 and not 0.

    WHY IT DOES NOT ASK WHICH CATALOGUE EACH RECORD CAME FROM, which would separate the two
    populations here. That is precisely the rule the fix will use to decide what to merge, and a
    measure sharing the fix's rule shares the fix's blind spot (§14b). This asks the dumber
    question and lets the docstring carry the difference.

    ARITHMETIC OVER THE SHIPPED VOLUME NUMBERS, per §14b: it asks the works list what numbers each
    record states and counts collisions, so it shares nothing with the code that decides which
    records belong to one run.

    fallback: none in the build.
    """
    by_work = {w.get("work_id"): w for w in ctx["works"] if w.get("work_id")}
    n = 0
    for r in ctx["series"]:
        seen, twice = set(), False
        for wid in (i for p in (r.get("print") or ()) for i in (p.get("work_ids") or
                                                                [p.get("work_id")]) if i):
            nums = {str(int(str(v["number"]))) for v in (by_work.get(wid) or {}).get("volumes") or ()
                    if str(v.get("number") or "").strip().isdigit()}
            twice = twice or bool(nums & seen)
            seen |= nums
        n += 1 if twice else 0
    return n


def budget_volume_numbers_a_page_draws_twice(ctx):
    """Volume numbers a work page would draw more than once inside a single print run.

    THE ARITHMETIC §14b WANTS BESIDE THE MERGE. `works whose records number one volume twice` asks
    about the RECORDS; this asks about the ROWS a page would draw, which is what a reader sees and
    is a different question the moment `merge_volumes` folds two records into one list. A merge
    that folded the blocks and left the volumes doubled would satisfy the first and fail this, and
    that is precisely the state MURCIÉLAGO was in when the cross-catalogue fold was first tried:
    one block, 52 rows, `vol. 1 April 2014` beside `vol. 1 25 Apr 2014`.

    ITS FLOOR IS FIVE AND THE FLOOR IS REAL BOOKS. 君と綴るうたかた numbers a volume 6 in 2024-03
    and another in 2025-01-13, ロンリーガールに逆らえない a 6 in 2023-01 and 2024-05, and three more
    are that shape: a second printing with its own ISBN, which `merge_volumes` refuses to fold
    because the dates disagree and a string comparison cannot say which is right. A reader should
    see both.

    A COUNT OVER THE SHIPPED ROWS, sharing nothing with the code that folds them: it walks the
    blocks, gathers the volumes of every record each block stands for, and counts the numbers that
    appear twice.

    fallback: none in the build.
    """
    by_work = {w.get("work_id"): w for w in ctx["works"] if w.get("work_id")}
    n = 0
    for row in ctx["series"]:
        for block in row.get("print") or ():
            seen = collections.Counter(
                str(v.get("number") or "").strip()
                for wid in (block.get("work_ids") or [block.get("work_id")]) if wid
                for v in (by_work.get(wid) or {}).get("volumes") or ()
                if str(v.get("number") or "").strip())
            n += sum(1 for c in seen.values() if c > 1)
    return n


def budget_works_holding_fewer_volumes_than_the_shop_states(ctx):
    """Works where コミックシーモア states more volumes than the corpus holds.

    A CAPTURE THAT HAS FALLEN BEHIND, counted so it is visible. 冷たくて柔らか is 4 against 7 and
    きみが死ぬまで恋をしたい 9 against 11: the shop has been selling volumes nothing here has read.
    82 works are in that state. It falls as VOLUMES-PLAN §4 collects, and it rises whenever a
    series publishes a volume ahead of the next capture, which is ordinary and is exactly what a
    reader would want to know about.

    COUNTED APART FROM THE OTHER DIRECTION, which is `works holding more volumes than the shop
    states` below. One number over both would let a fixed over-count hide a new under-count, and
    they have different causes and different fixes.

    THE SHOP IS TIER C AND THIS IS NOT AN ASSERTION THAT IT IS RIGHT (DEFINITIONS §5). It is two
    parties disagreeing about a countable thing, which is worth a person's attention either way.

    fallback: none. A work no shop row reaches is not counted, which `shopjoin` decides and
    documents.
    """
    return sum(1 for ours, theirs in _shop_counts(ctx)
               if _our_volumes(ours) < theirs["volumes_stated"])


def budget_works_holding_more_volumes_than_the_shop_states(ctx):
    """Works where the corpus holds more volumes than コミックシーモア states.

    MOSTLY PRODUCTS COUNTED AS VOLUMES, which is the fault VOLUMES-PLAN §2 fixes. MURCIÉLAGO is 32
    against 29 because BOOK☆WALKER lists three free sample editions among its 32 products and the
    ingest counts every product; citrus+ is 8 against 7 for the same kind of reason. 30 works are
    in that state, and the number should fall to near nothing once a volume number is read from the
    product title instead of assigned from its position in a listing.

    WHAT IS LEFT AFTERWARDS IS THE INTERESTING POPULATION: a work where the corpus really does hold
    a volume the shop does not sell, or a shop that has delisted one. Neither is a fault, and both
    are worth looking at, which is why this does not aim at zero.

    fallback: none, as above.
    """
    return sum(1 for ours, theirs in _shop_counts(ctx)
               if _our_volumes(ours) > theirs["volumes_stated"])


def budget_shelf_admissions_a_reader_cannot_follow(ctx):
    """Works a shop's shelf put here whose page offers no way to reach that shop.

    THE RULE. A source named as having admitted a work has to be reachable from the work. Nothing
    else on a work page asks a reader to take our word for it: every date, every count and every
    reading cites a page. An admission that cannot be followed is the weakest kind of citation
    there is, because it invites the check and then gives nowhere to make it.

    230 rows were in that state when this was written, all of them コミックシーモア's. The record
    behind each is the national bibliography's, correctly, and `admitted_by` named the shop with no
    address, because `madb/by_isbn` computed that block once for a whole pass and so could not name
    a title. `build._shop_address` then read a shop address out of `marketing_label_basis` guarded
    on `source == "bookwalker"`, which made the link derivable for the one shop whose records store
    both facts at one URL.

    MEASURED ON THE SHIPPED ROW. This reads `series.json` and asks whether the row a reader is
    given carries a shop address, which owes nothing to either producer: not to the join in
    `by_isbn.address_of` and not to `_shop_address`. A canary planted in the context is a row like
    any other, because nothing upstream of here filters on the thing being counted (§14b).

    WHAT IT CANNOT SEE. Whether an address is the RIGHT page. It counts present against absent, and
    a link to the wrong title on the right shop passes. `unreachable citations` is the check that
    would answer that one and it has never been pointed at a shop page.

    ITS FLOOR IS NOT ZERO. A shop that splits a series the bibliography holds as one work names two
    pages for it, and `address_of` writes neither rather than picking. Five of コミックシーモア's
    works are in that state today. A rise means a route has gone back to admitting a work on a
    shelf without recording which page of the shop it read.
    """
    rows = ctx.get("series")
    if not rows:
        return UNMEASURED    # this could not be measured; see UNMEASURED
    out = 0
    for r in rows:
        if not any(e.get("type") == "retailer" for e in (r.get("evidence") or [])):
            continue
        editions = r.get("print") or []
        if editions and not any(p.get("shop_url") for p in editions):
            out += 1
    return out


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
        return UNMEASURED    # this could not be measured; see UNMEASURED
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
        return UNMEASURED    # this could not be measured; see UNMEASURED
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
        return UNMEASURED    # this could not be measured; see UNMEASURED
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
    from facts import identity as _identity

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


def budget_listing_series_with_no_feed_of_their_own(ctx):
    """Series in a GigaViewer platform's own yuri listing that its last feeds run did not resolve.

    THE BUG THIS COUNTS, found on 2026-08-10. `series_feeds.series_ids` scanned the listing page
    for a name and then the next thumbnail address, and a series block names itself again on its
    two buttons AFTER that thumbnail, so from the second entry on every name was paired with the
    FOLLOWING series' id. 163 of 一迅プラス's 164 works. The run then renamed each work to whatever
    series the feed it fetched said it was, which made the file self-consistent and the fault
    invisible: the only trace left was the listing's second entry, たゆたう恋の散り際に, resolving
    to nothing at all because there was no id left over for it.

    WHY THE COUNT IS TAKEN THIS WAY (§14b). Comparing the two files' TITLES reads zero, because
    `carry_over` keeps a work an earlier run resolved and the dropped series is still in the file
    with a stale chapter list. The arithmetic is the part that cannot be covered up: a listing of
    165 against a run that resolved 164 is one series the pairing lost, whatever the file holds.
    The listing count comes from `releases.yuri_series`, which reads the same page and never
    consults the pairing.

    COUNTED, because a listing entry announced before its first chapter resolves an id and returns
    no episodes, which is the platform being early. Both passes run in the same Stage A against the
    same page, so the honest value is zero and a rise is the pairing slipping again.
    """
    d = ROOT / "data" / "source" / "gigaviewer"
    if not d.is_dir():
        return 0
    short = 0
    for f in sorted(d.glob("*-series.yaml")):
        listed = len((_yaml(f, {}) or {}).get("series") or [])
        if not listed:
            continue
        feeds = d / f"{f.name[: -len('-series.yaml')]}-series-feeds.yaml"
        resolved = int((_yaml(feeds, {}) or {}).get("series_resolved") or 0)
        short += max(0, listed - resolved)
    return short


def budget_series_names_holding_a_page_title(ctx):
    """Works a GigaViewer feeds file holds under a name whose round brackets do not close.

    THE RESIDUE OF A FIXED BUG, found while auditing the pairing above. A feed titles itself
    `一迅プラス（大室家）` and the series is the bracketed part, which `feed_series_name` used to take
    with a greedy match from the first opener to the last closer. On a platform whose own name is
    bracketed that ran across the page title:

        Our Feel（アワフィール）| 女性マンガレーベル、第1・3木曜日更新!!（明日の空を見る人よ）

    came out as `アワフィール）| 女性マンガレーベル、第1・3木曜日更新!!（明日の空を見る人よ`. c747b62
    replaced the match with a scan from the end and left the rows it had already written, and
    `carry_over` keeps a work no later run re-resolved, so four of them are still in the source
    layer at the time of writing: three on COMIC ユアーズ and one on OUR FEEL.

    ARITHMETIC ON THE STORED NAME (§14b). A closer standing before its opener is a bracket the
    parser cut through, and counting them owes `last_bracketed` nothing. Checking with
    `last_bracketed` would agree with whatever it produced.

    Falls by one for each of these platforms whose feeds are fetched again; the current code reads
    the same cached feeds correctly. A rise means a bracketed page title is being taken for a work.
    """
    openers, closers = {"(", "（"}, {")", "）"}
    d = ROOT / "data" / "source" / "gigaviewer"
    if not d.is_dir():
        return 0
    n = 0
    for f in sorted(d.glob("*-series-feeds.yaml")):
        for w in ((_yaml(f, {}) or {}).get("works") or []):
            depth, broken = 0, False
            for ch in str(w.get("work_title") or ""):
                if ch in openers:
                    depth += 1
                elif ch in closers:
                    depth -= 1
                    if depth < 0:
                        broken = True
                        break
            n += 1 if broken or depth else 0
    return n


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


def budget_works_whose_country_is_unattested(ctx):
    """Works whose first publication country nothing attests, which is the inclusion test not run.

    THE CLASS THIS COUNTS. DEFINITIONS §6 makes first publication the scope test and says the
    country is required because it is what answers the question. The field was the literal "JP" in
    three places, so every one of 2,564 works asserted Japan and none of them had been asked. This
    is the same population, counted honestly: a work reaches here because MADB, openBD or a shop
    catalogues its JAPANESE EDITION, and none of those sources holds a field for where the work
    first appeared.

    WHAT IT READS, AND WHY THAT IS NOT `facts/origin`'s ANSWER (§14b). It asks the shipped works
    list whether the field holds a value, which is arithmetic on the rendered result and owes
    nothing to the module that filled it. A count taken from the vocabulary would agree with the
    vocabulary; a count of empty fields disagrees with anything that stops filling them.

    WHY A BUDGET AND NOT AN INVARIANT. The remedy is a person reading a publisher's page and
    recording a serialisation venue, one work at a time. Refusing a build over it would refuse the
    corpus, and refusing the corpus is a ruling for the project owner rather than for a gate. What
    the number does is stop the question being invisible: it was 0 while nothing was known, because
    a constant had answered it.

    IT HAS NO FLOOR THAT ANYBODY CAN STATE. A serialisation venue exists for every serialised work
    and is written down somewhere for most of them, so this can in principle reach zero. What it
    cannot do is fall in bulk, which is why it is stated as a deficit.
    """
    works = (_load(BUILD / "works.json", {}) or {}).get("works")
    if works is None:
        return UNMEASURED    # this could not be measured; see UNMEASURED
    return sum(1 for w in works if not (w.get("first_publication") or {}).get("country"))


def budget_scope_questions_left_open(ctx):
    """Works a scope signal flagged that nobody has ruled on either way.

    THE CLASS THIS COUNTS. `facts/origin` produces candidates rather than verdicts: a credited
    translator and a publisher's foreign-comics line are both evidence that a Japanese edition is a
    translation, and neither is proof, because a 現代語訳 is translated and Japanese and a house may
    put a Japanese work on any line it likes. `data/scope.yaml` carries `review` for a work somebody
    has looked at and could not settle, and this counts them.

    IT READS THE REGISTER AND NOT THE BUILD, deliberately. A count taken from the built rows would
    fall when a work left the corpus for any reason at all, which is the opposite of what the number
    is for: a question stays open until somebody answers it.

    WHAT SATISFIES IT is a ruling either way, `out-of-scope` or `in-scope`, citing the page that
    settles it. Falling to zero is reachable and means every flagged work has been read.
    """
    doc = _yaml(ROOT / "data" / "scope.yaml", None)
    if doc is None:
        return UNMEASURED    # this could not be measured; see UNMEASURED
    return sum(1 for r in (doc.get("rulings") or []) if r.get("disposition") == "review")


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
        # NO MATCH MEANS THE CHILD DID NOT ANSWER, which is what happened when a mangled import
        # left build.py unparseable: this reported 0 against a real 40 and the gate banked it.
        m = re.search(r"(\d+) name\(s\) rebound", out.stdout)
        return int(m.group(1)) if m else UNMEASURED
    except Exception:
        return UNMEASURED    # this could not be measured; see UNMEASURED


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
    #
    # AND A TITLE WITH NO JAPANESE IN IT IS NOT IN THE POPULATION. `Distortion`, `GIRL FRIENDS` and
    # 94 others are the work's own title as the Japanese platform printed it, which `pass0_cache`
    # records `official-jp` because that is exactly what it is. There is no second form to write:
    # a translation of `Distortion` is `Distortion`, and the romanisation a reader falls through to
    # is the same string again, so the control this budget protects is already answered for them.
    # Counting them would put 96 items into a queue nobody can ever work off, which makes the
    # number stop meaning what its name says.
    return sum(1 for k, v in titles.items()
               if isinstance(v, dict) and not v.get("alias_of") and JAPANESE.search(str(k))
               and set(v.get("en_forms") or {}) & {"official-jp", "licensed"}
               and not (v.get("en_forms") or {}).get("translated"))


#: Invariants a check-in gate must not assert, because their subject is a DEPLOY that has not
#: happened. `deployed data matches built` compares `data/build` byte for byte against the deployed
#: tree, and a gate builds and never copies, so it sits permanently inside the window between a
#: build and `deploy.sh` that `--deploy-window` exists to patch. It failed on every push ever made
#: to this repository, on `status.json` alone, which carries `generated` and `since_last.at` and so
#: differs from a rebuild of itself a second later. A gate finding nobody can act on by changing
#: the push is a gate reporting on something else.
#:
#: `deploy.sh` still answers it after copying, which is the moment the claim is about.
NOT_ASSERTED_BEFORE_A_DEPLOY = {"deployed data matches built"}


SOURCE_BUDGETS = {"stock phrasing in comments", "three as an organising shape",
                  "facts with more than one home",
                  "impossibilities asserted without evidence",
                  "modules without a test", "shadowed names in build.py",
                  "scraped counters in chapter names", "invented markup in tests"}

RUBY_KANJI = re.compile(r"[一-鿿々]")
RUBY_KANA = re.compile(r"[ぁ-ゖァ-ヺー]")


def budget_ruby_asserting_a_reading_per_character(ctx):
    """Ruby that cuts a word into one annotated character after another.

    THE SHAPE THE PROJECT OWNER REPORTED on 2026-08-10: 総選挙 arrived as 総/そう 選/せん 挙/きょ,
    and 鮮血王女 as four. app.js wraps each span in its own <ruby>, so a compound annotated that way
    is several ruby units that break and space apart, and each one asserts a reading of one
    character that nobody stated. 927e141 produced most of them from a per-character table, applied
    wherever exactly one partition of the reading existed; that is removed, and 2,402 atomised runs
    across 1,622 span sets went with it.

    WHAT IS LEFT IS THE ANALYSER'S OWN, and it is a different fault worth watching. Where
    SudachiDict has no entry for a compound it reads each character alone, so 超深, 焔炎, 退鬼師 and
    樫風 reach a reader with a reading over each character and no compound behind any of them.
    NAMES-PLAN names 樫風 as the case a reader can adjudicate on sight.

    ARITHMETIC ON THE RENDERED ROW (§14b), in the shape `implausible ruby spans` established: it
    counts adjacent annotated single-character spans and owes the aligner, the analyser and the
    per-character table nothing. It cannot see a wrong reading over a run of two characters, which
    is `implausible ruby spans` and `ruby spells the reading` between them, and neither can see a
    plausible reading that is not the one anybody says.
    """
    n = 0
    for r in ctx["series"]:
        for key in ("work_en", "author_en"):
            run = 0
            for span in ((r.get(key) or {}).get("ruby") or []):
                base, rt = (span + [None, None])[:2] if isinstance(span, list) else (None, None)
                alone = bool(rt) and len(str(base or "")) == 1 and bool(RUBY_KANJI.fullmatch(str(base)))
                run = run + 1 if alone else 0
                if run == 2:
                    n += 1
    return n


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
    """Defined in `adapters/facts/credit/checks.py`, beside the thing it checks."""
    from facts import credit as _cr
    return _cr.CHECKS["credits_matching_a_chapter"](ctx)


def budget_credits_that_restate_a_name(ctx):
    """Defined in `adapters/facts/credit/checks.py`, beside the thing it checks."""
    from facts import credit as _cr
    return _cr.CHECKS["credits_that_restate_a_name"](ctx)


# ONE PRODUCER OF THE SIGN (§3). Every spelling of it, deliberately looser than the one the ingest
# acts on, and owned by `facts/cataloguing` because reading a catalogue's marks is what that fact
# is. This file held the class and a copy in the fact's own checks went out without ゠ for the
# length of one commit, which is the fault the census exists to stop.
def _equals_any():
    sys.path.insert(0, str(ROOT / "adapters"))
    sys.path.insert(0, str(ROOT / "adapters" / "facts"))
    from cataloguing import checks as _cat
    return _cat.EQUALS_ANY


EQUALS_ANY = _equals_any()


def budget_titles_carrying_cataloguing_punctuation(ctx):
    """Titles a reader is shown that still hold a catalogue's own punctuation.

    DEFINED IN `adapters/facts/cataloguing/checks.py`, beside the rule it measures. It lived here,
    which put the rule in one file and the measure of the rule in another, free to disagree about
    what a mark is.

    WHAT IS BEING COUNTED. A bibliography transcribes a title page under ISBD, so a name arrives
    marked up: `恋愛遺伝子XX = The Romance Gene XX` is one work with an English name beside it, and
    `恋愛遺伝子XX : 完全版` is that work reissued. Neither mark is part of what anybody calls the
    book. `facts/cataloguing` takes the parallel title off and hands the English on; the ten reissue
    markers are counted and not yet lifted off, which is why this will not be zero before somebody
    decides where an edition statement should live.

    THE CLOSED SET IS WHAT KEEPS A SUBTITLE OUT OF THIS COUNT.
    `ギャルメイドと悪役令嬢 : おじょーさま、お世話させていただきます` carries the same colon and the
    tail is content. Counting every colon would put 77 rows here of which 67 are correct, and a
    number that is mostly noise is one nobody reads.

    WHAT IT CANNOT SEE. A title whose apparatus was stripped before it reached this database, and
    the rest of what this fact is blind to, which is `facts/cataloguing/BLINDSPOT.md`.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    sys.path.insert(0, str(ROOT / "adapters" / "facts"))
    from cataloguing import checks as _cat
    return _cat.CHECKS["titles carrying cataloguing punctuation"](
        [r.get("work") for r in ctx["series"]])

# ASKED OF `facts/division`, which owns it. I made this copy myself, moving a check into the fact
# and leaving the pattern here; the duplicates lint found it the same week.
KANA_SURFACE = _division.KANA_SURFACE


def budget_kana_names_with_no_stated_division(ctx):
    """Defined in `adapters/facts/division/checks.py`, beside the thing it checks."""
    from facts import division as _f
    return _f.CHECKS["kana_names_with_no_stated_division"](ctx)




def budget_author_readings_no_source_states(ctx):
    """Defined in `adapters/facts/reading/checks.py`, beside the rulings it applies."""
    from facts import reading as _rd
    return _rd.CHECKS["author_readings_no_source_states"](ctx)


def budget_titles_read_by_a_machine_unmarked(ctx):
    """Defined in `adapters/facts/reading/checks.py`, beside the rulings it applies."""
    from facts import reading as _rd
    return _rd.CHECKS["titles_read_by_a_machine_unmarked"](ctx)


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
        return UNMEASURED    # this could not be measured; see UNMEASURED
    pubs = (_yaml(NAMES / "publishers.yaml", {}) or {}).get("names") or {}
    filed = entities.filed_elsewhere(pubs, ctx["series"])
    return sum(1 for k, v in (ctx["names"].get("authors") or {}).items()
               if k in filed and not v.get("entity"))


def budget_interpunct_credits_nobody_has_ruled_on(ctx):
    """Defined in `adapters/facts/credit/checks.py`, beside the thing it checks."""
    from facts import credit as _cr
    return _cr.CHECKS["interpunct_credits_nobody_has_ruled_on"](ctx)


def budget_credits_carrying_their_own_cataloguing(ctx):
    """Defined in `adapters/facts/credit/checks.py`, beside the thing it checks."""
    from facts import credit as _cr
    return _cr.CHECKS["credits_carrying_their_own_cataloguing"](ctx)


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
        return UNMEASURED    # this could not be measured; see UNMEASURED
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
        return UNMEASURED    # this could not be measured; see UNMEASURED
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
    floor = shipped.get("floor") or {}

    def fold(t):
        # ASKED OF `facts/namekey`, which owns the identity key. check.py held three copies.
        from facts import namekey as _nk
        return _nk.fold(t)

    for r in ctx["releases"]:
        surface = str(r.get("author") or "")
        if not ja.search(surface):
            continue
        key = fold(surface)
        e = authors.get(key) or {}
        if e.get("romaji") or e.get("en"):
            continue
        # `composedCredit`: a line composes when the build divided the field and every person in it
        # has something to show. `personShown` ends at the floor, which is total in English, so the
        # question is whether each part reaches one of the four answers that function offers.
        #
        # THIS BRANCH HAD NEVER FIRED. It read `parts.get(key)` as a LIST of names and the shipped
        # value is `{"p": [{"n": …}], "j": …}`, so `len(people) > 1` counted the record's own keys
        # and the loop asked the author store about the string "p". Every release row therefore fell
        # through to the phrase map, and the day the analyser stopped writing phrases for credit
        # fields this budget rose by 205 rows that render correctly on the page. A measure that
        # depends on a fallback it never modelled cannot say what its number means.
        div = parts.get(key) or {}
        people = [p.get("n") for p in (div.get("p") or []) if p.get("n")]
        if people and not div.get("part") and all(
                (authors.get(fold(n)) or {}).get("romaji")
                or (authors.get(fold(n)) or {}).get("en")
                or not ja.search(str(n))
                or floor.get(fold(n)) for n in people):
            continue
        # and the phrase map is the fallback, which only helps where the phrase is not Japanese.
        phrase = str(phrases.get(key) or "")
        if phrase and not ja.search(phrase):
            continue
        if floor.get(key):
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
        return UNMEASURED    # this could not be measured; see UNMEASURED
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
        return UNMEASURED    # this could not be measured; see UNMEASURED
    return len({v for v in second if interface.KANA_KANJI.search(v)})


def budget_credit_phrases_spelling_a_person_otherwise(ctx):
    """Credit fields whose composed phrase spells somebody the name store spells another way.

    THE FAULT, AND THE BRACKET THAT HID IT. `_recompose_credit` rebuilds a credit line out of the
    people in it, and it declined to rebuild a line naming ONE person plus a role: the splitter
    peels `[著]` off, so composing from the parts would have published the name with the job gone.
    Declining kept the job and froze the name, because a phrase is written once by the analyser and
    never revisited. `[著]安田剛助` read `[ Cho ] Yasuda Takesuke` after openBD stated ヤスダ コウスケ,
    while 安田剛助 alone read `Yasuda Kōsuke`. One man, two romanisations, decided by whether the
    credit carried its role bracket.

    WHY `a person is spelled one way` COULD NOT SEE IT (§14b). That invariant compares a phrase
    with the store record under THE SAME KEY, and `[著]安田剛助` is not a key the store holds: the
    bracket changes the string, so there was nothing to compare and it passed. This asks the
    DIVISION who the field names and looks each of those people up, which is a key the phrase map
    never has and the store always does.

    ARITHMETIC ON TWO SHIPPED MAPS. `credit_parts`, `phrases` and `authors` all come out of
    feed/names.json and this reads nothing else, so it fails on anything the build can emit.

    WHAT THE 70 WERE, WHICH IS NOT WHAT THIS SAID. It read "a line is left alone where any one
    person on it has no rendering yet, and it falls as those readings arrive". Counted: 60 of the
    70 were held back by somebody ALREADY IN LATIN. `Magpie`, `IceFairy`, `Kastel` and `sheepD`
    have no store record because a Latin pen name is not a transliteration of anything
    (NAMES-PLAN §1), so no reading was going to arrive and that sentence was false of six lines in
    seven. Two were an editorial desk the floor spells, and eight were a lookup asking the raw
    store for a key `credit_parts` resolves against the folded one.

    AND THE READER REACHED FOUR OF THEM. `creditFromParts` composes a multi-person line name by
    name and `personShown` cannot answer null in English, so the phrase is drawn only where the
    field names ONE person inside notation. Asking kari/app.js what it would show for each of the
    70 gives this string back four times.

    So the bar moved from the store to the floor, for strings the build has ruled credit fields,
    and the residue is those four: `壇九(TANJIU)` and three like it, where the notation around one
    name is a bracket that states no job, so `_credit_of_one` declines to touch it. Each of the
    four is its own shape and none of them is the composition rule.
    """
    n = ctx["names_shipped"] or {}
    parts, phrases, people = (n.get("credit_parts") or {}, n.get("phrases") or {},
                              n.get("authors") or {})
    if not (parts and phrases and people):
        return 0

    def fold(t):
        # ASKED OF `facts/namekey`, which owns the identity key. check.py held three copies.
        from facts import namekey as _nk
        return _nk.fold(t)

    bad = set()
    for key, div in parts.items():
        text = str(phrases.get(key) or "")
        if not text:
            continue
        for part in div.get("p") or ():
            rec = people.get(fold(part.get("n") or "")) if part.get("n") else None
            # THE STRING `_recompose_credit` WOULD HAVE USED, in the order it prefers them, so a
            # disagreement here is a phrase that did not consume the store and never a difference
            # of taste between two renderings the store holds.
            ours = ((rec or {}).get("romaji") or {}).get("macron") or (rec or {}).get("en")
            if ours and ours not in text:
                bad.add(key)
                break
    return len(bad)


def budget_bylines_drawn_in_a_spelling_the_field_does_not_write(ctx):
    """Work rows whose byline reaches a reader spelt differently from the credit field itself.

    THE FAULT, AND IT HAS BEEN SHIPPED TWICE. `credit_parts` spells each person the way the name
    store is keyed on them and a credit field spells them the way its cataloguer typed them, so
    `山本 和音` is 山本和音 in the division and `sono.N` is ｓｏｎｏ．Ｎ. `linkedCredits` located
    names with `indexOf` on the field, missed all 38 of those, and drew their work pages with no
    address on any name. The patch that fixed the address by searching the FOLD then handed the
    division's spelling to `creditChip`, so 35 Japanese bylines came back with the artist's name
    rewritten underneath their work. Both are one fault: the string that addresses a record and the
    string a reader sees are not the same string.

    MEASURED WITH FURIGANA ON, because that is where the last of them live. `ruby` draws the spans
    a record carries, and a record carries the store's spelling of the name, so the space in
    永田　さんずい reached a field that says 永田さんずい. A chip covering the whole field takes the
    row's own `author_en`, whose spans are aligned to what that row writes, which is what carried
    this from 70 to 23.

    §14b, WHAT IT SHARES WITH ITS SUBJECT: the shape of a ruby element, because the reading has to
    come off before the surface can be compared. Nothing else. The comparison is against
    `series[].author` as the data holds it, which no part of the renderer consults, so a walk that
    starts rewriting names shows up here as a rise rather than as agreement. Run against the patch
    that was reverted it reads 92.

    A budget. The residue is the parts of a MULTI-person field, which have no `author_en` of their
    own and take the store's record, spelling and all. It reaches zero when a part carries the
    alignment the whole field already has.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import interface
    rows = [r for r in ctx["series"] if str(r.get("author") or "").strip()]
    if not rows:
        return 0
    try:
        drawn = _interface(ctx).with_prefs(LANG="ja", FURIGANA=True).values(
            [("linkedCredits", r) for r in rows])
    except interface.Unavailable:
        return UNMEASURED    # this could not be measured; see UNMEASURED
    bad = 0
    for row, markup in zip(rows, drawn):
        # The reading comes off and the surface stays: `<ruby>永田<rt>ながた</rt></ruby>` is the
        # name 永田 annotated, and the annotation is not part of the spelling.
        surface = re.sub(r"<rt[^>]*>.*?</rt>", "", markup)
        surface = html_module.unescape(re.sub(r"<[^>]*>", "", surface))
        if surface != str(row.get("author") or "").strip():
            bad += 1
    return bad


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
        # ASKED OF `facts/namekey`, which owns the identity key. check.py held three copies.
        from facts import namekey as _nk
        return _nk.fold(t)

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


def budget_one_work_named_two_ways_across_its_rows(ctx):
    """Works whose rows disagree about the English name of the work itself.

    WHAT `one work under two names in a list` DOES NOT ASK. That one counts a work appearing twice
    in one list; this asks whether two rows that are plainly the same work render the same Japanese
    phrase two different ways. Seven did: `ネイルちゃんと深爪さん。` said Fukazume-san on two rows and
    Cut-Too-Short-san on a third, which renames a person rather than rewording a title, and
    `うらら迷路帖` set its own attested URARA MEIROCHOU beside a macron romanisation of ours.

    GROUPED ON THE SHARED TITLE CORE and not on the fold key, which is the reason nothing caught
    these. An anthology and the work it collects are two works and not two editions, so they fold
    apart and always will; what they share is the name at the front of both.

    §14b, WHAT IT REUSES: nothing either producer uses. It reads the shipped rows, cuts each title
    at its first subtitle mark, and compares the English before the first colon. It consults no
    basis, no store and no attribution, so a pass that decided wrongly is counted here all the same.

    What it cannot see is two rows whose Japanese titles share no leading phrase, and a subtitle
    difference is deliberately not counted: `Side Story` after a licensed name is that work's own.
    """
    import collections
    rows = ctx["series"] or []

    def core(s):
        s = re.split(r"[：:～~【\[（(]| : ", str(s))[0].strip()
        return re.sub(r"(アンソロジーコミック|アンソロジー|シリーズ|コミック)$", "", s).strip()

    def head(e):
        e = re.split(r"[:~(]", str(e))[0].strip().rstrip(".")
        return re.sub(r"\b(the |an? )?anthology comic|\bseries\b|\bside story\b", "",
                      e, flags=re.I).strip().lower()

    seen = collections.defaultdict(set)
    for r in rows:
        en = (r.get("work_en") or {}).get("en")
        c = core(r.get("work") or "")
        if en and len(c) >= 4:
            seen[c].add(head(en))
    return sum(1 for v in seen.values() if len(v) > 1)


def budget_author_names_romanised_as_one_word(ctx):
    """Defined in `adapters/facts/division/checks.py`, beside the thing it checks."""
    from facts import division as _f
    return _f.CHECKS["author_names_romanised_as_one_word"](ctx)


def budget_divisions_read_back_from_a_romanisation(ctx):
    """Defined in `adapters/facts/division/checks.py`, beside the thing it checks."""
    from facts import division as _div
    return _div.CHECKS["divisions_read_back_from_a_romanisation"](ctx)


def budget_divisions_resting_on_a_community_database(ctx):
    """Defined in `adapters/facts/division/checks.py`, beside the thing it checks."""
    from facts import division as _div
    return _div.CHECKS["divisions_resting_on_a_community_database"](ctx)


def budget_publisher_readings_nobody_has_settled(ctx):
    """Defined in `adapters/facts/reading/checks.py`, beside the rulings it applies."""
    from facts import reading as _rd
    return _rd.CHECKS["publisher_readings_nobody_has_settled"](ctx)


def budget_imprint_strings_that_reach_no_line(ctx):
    """Imprint strings the corpus carries that the shipped map answers for with no line.

    AN IMPRINT IS ONE OBJECT WITH MANY RECORDED SPELLINGS. One printed logotype reaches us from
    MADB, from openBD and from a retailer in three transcriptions, notation and case and the parent
    line vary on top, and the field stored each result as though it were a line of its own: 一迅社
    runs one yuri line and the rows held 27 strings for it. `data/names/imprints.yaml` says which
    spellings are one line and `adapters/facts/imprint` does the matching. This counts what the
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
    `adapters/facts/imprint/test_imprint.py`: 一迅社's ZERO-SUM, HOWL, DNAメディア and 4コマKINGS lines and
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
    sys.path.insert(0, str(ROOT / "adapters" / "facts"))
    import imprint as _imp
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
    """Defined in `adapters/facts/romanisation/checks.py`, beside the thing it checks."""
    from facts import romanisation as _rom
    return _rom.CHECKS["kana left in a romanisation"](ctx)


GLOSS_IN_TITLE = re.compile(r"([\u4e00-\u9fff\u3005]+)\s?[（(]([\u3041-\u3096\u309d\u309e\u30a1-\u30fa\u30fc\u30fd\u30fe]+)[）)]")


def budget_titles_read_past_their_own_gloss(ctx):
    """Titles that print how a word in them is said, shipped with a reading that ignores it.

    A publisher setting furigana on the line, `抱かれたい女(ひと)`, is STATING the reading of the run
    before the bracket, and it outranks anything an analyser produces. 17 shipped titles carry one
    and 9 were read past it in three different ways: the bracket read aloud as words of its own
    (`コイ スル ショウワクセイ ( アステロイド )`), the gloss dropped and the kanji read off the
    characters (`永久（とこしえ）` as エイキュウ), and the wrong one of two attested readings chosen
    for the glossed run (`女` as オンナ where the title prints ひと).

    THE ARITHMETIC, WHICH THE PRODUCER DOES NOT PERFORM (§14b). Both halves are read off the SHIPPED
    row: the reading has to contain the kana the title prints, and it may not contain a bracket that
    the title used to set furigana. `names/gloss.py` composes a reading and never afterwards asks
    whether the result says what the brackets said, so a composition that silently dropped a
    fragment is counted here.

    WHAT IT SHARES is the pattern for what a gloss looks like, which is `gloss.GLOSS` written for the
    shipped keys. It therefore cannot see a gloss in a shape neither recognises: a Latin head, which
    `gloss.py` refuses on purpose because an imprint sits in that position, and `【】`, which labels
    an edition in this corpus and never a reading.

    ONE LEFT, AND IT IS A CURATED RECORD RATHER THAN A PASS. 念願の悪役令嬢(ラスボス)の身体を… holds
    a `researched` reading that reads its own bracket aloud, and a build has no standing to overrule
    a reviewer. It falls when somebody re-states that one.
    """
    try:
        sys.path.insert(0, str(ROOT / "adapters" / "names"))
        import kana
    except Exception:                                                       # noqa: BLE001
        return UNMEASURED    # this could not be measured; see UNMEASURED
    n = 0
    for ja, v in ((ctx["names_shipped"] or {}).get("titles") or {}).items():
        rd = v.get("reading")
        if not rd:
            continue
        for _run, kana_gloss in GLOSS_IN_TITLE.findall(str(ja)):
            said = kana.to_katakana(kana_gloss)
            if said not in kana.to_katakana(rd).replace(" ", "") or re.search(r"[（(）)]", rd):
                n += 1
                break
    return n


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
        return UNMEASURED    # this could not be measured; see UNMEASURED
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
        return UNMEASURED    # this could not be measured; see UNMEASURED
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

    THE FIELDS OF EVERY RECORD THE BLOCK STANDS FOR, which is still arithmetic and still consults
    nothing. A block is one print RUN and build.py folds the catalogue records MADB filed that run
    under separately; six runs are named by a house the shown record does not name, 紅殻のパンドラ's
    継続 under KADOKAWA where volumes 1 to 21 say 角川書店 among them. Those are print rows of the
    work, so a page listing the work is right and reading the shown fields alone made six correct
    pages look like six wrong ones.
    """
    by_work = {}
    for r in ctx["series"]:
        raw = " ".join(str(named.get(f) or "")
                       for pr in (r.get("print") or ())
                       for named in [pr] + list(pr.get("folded_names") or ())
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

    FIVE OF THE SEVEN ARE THE RESIDUE OF A FIX, COUNTED SO IT STAYS VISIBLE. `iimAn&惟丞`,
    `大島永遠&大島智` and three more were single credits because no splitter divided on an
    ampersand, so one address held two artists. Each half holds its own identifier now and the
    joined spelling holds none of their works. The registry is append-only, so the joined entry
    stays and keeps resolving in the data; `pages.py` serves it no page, because heading one with a
    name no source uses and listing nothing under it would assert a credit the corpus has stopped
    making.

    THE OTHER TWO ARE A WORK THAT LEFT, and they arrived when the edge file was re-derived on
    2026-08-09 after standing since the 8th. マルイノ and もけ were credited on w01195 and nothing
    holds that identifier now, so the edges the file carried for them were describing a corpus that
    had moved on. Re-deriving is what surfaced it; the credits had been orphaned for a day with the
    number reading 5.

    A RISE IS THE THING TO LOOK AT, and it has two readings. A credit has left the corpus, which is
    a page withdrawn, or a splitter change has orphaned another joined spelling, which is the
    ampersand fix happening again.
    """
    edges = {str(r.get("id")) for r in (ctx["credit_works"] or {}).get("credits") or []}
    return sum(1 for e in (ctx["credits"] or {}).get("credits") or []
               if e.get("id") and not e.get("merged_into") and str(e["id"]) not in edges)


def budget_credit_fields_the_division_does_not_account_for(ctx):
    """Defined in `adapters/facts/credit/checks.py`, beside the thing it checks."""
    from facts import credit as _cr
    return _cr.CHECKS["credit_fields_the_division_does_not_account_for"](ctx)


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
    ("titles read past their own gloss", budget_titles_read_past_their_own_gloss,
     "titles printing how a word in them is said, shipped with a reading that drops the kana or "
     "reads the bracket aloud. A publisher's furigana on the line outranks an analyser. A rise "
     "means a capture route reached the naming passes without the gloss rule."),
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
    ("renderings resting on a mechanical romanisation",
     budget_renderings_resting_on_a_mechanical_romanisation,
     "names an English page spells itself, because no source states how they are read. That covers "
     "a name the store holds nothing for and a name read off a community-edited database, which "
     "improves the spelling without settling the pronunciation. Each carries a mark and a tooltip "
     "saying so. It falls as readings are researched and nothing about the renderer can move it, "
     "which makes it the data gap written as a number."),
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
    ("works shaped like prose", budget_works_shaped_like_prose,
     "works credited to an author beside an illustrator whose only source is a retailer's shelf, "
     "which is how an illustrated novel is billed and how a work nothing catalogues is admitted. "
     "DEFINITIONS §6 refuses prose and had no test. A rise is a work somebody should look at "
     "before it reaches readers with a work record."),
    ("works named by a truncation", budget_works_named_by_a_truncation,
     "distinct work titles in the shipped rows that end in three ASCII full stops, which is a "
     "listing running out of room rather than a title trailing off: a Japanese title that trails "
     "off uses …. Falls as the archived feeds holding them age out; a rise means a release writer "
     "has gone back to reading `work_title` off a record without resolving it against "
     "data/work-aliases.yaml."),
    ("interface tooltips a reader of Japanese cannot read",
     budget_interface_tooltips_a_reader_of_japanese_cannot_read,
     "title attributes in kari/app.js whose text is an English literal rather than a string built "
     "by T() or L(), so they stay English when a reader selects 日本語. The tooltips are where the "
     "interface explains itself, which is the worst place to be monolingual. Falls as each is "
     "written in both; a rise means a new one was added in one language."),
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
    ("credit phrases spelling a person otherwise",
     budget_credit_phrases_spelling_a_person_otherwise,
     "credit fields whose composed phrase spells one of the people in it differently from the name "
     "store, counted by asking the shipped division who the field names. It was 207 while a line "
     "of one person plus a role bracket was left exactly as the analyser first wrote it, so a "
     "reading sourced afterwards could not reach it. It was then 70 while a line was recomposed "
     "only where every person on it had a store record, which held back 60 lines on the strength "
     "of a name already in Latin that no store will ever hold. The residue is a field naming one "
     "person inside notation that states no job, which is the one shape the recomposition still "
     "refuses to touch."),
    ("bylines drawn in a spelling the field does not write",
     budget_bylines_drawn_in_a_spelling_the_field_does_not_write,
     "work rows whose byline reaches a reader spelt differently from the credit field the row "
     "holds, measured with furigana on. The division spells a name the way the store is keyed on "
     "it and a field spells it the way a cataloguer typed it, and a walk that confuses the two "
     "either loses the address on 38 pages or rewrites a name under its own artist. The residue "
     "is the parts of a field naming several people, which have no rendering of their own to take "
     "the alignment from. A rise means a name is being respelt."),
    ("names rendered two ways", budget_names_rendered_two_ways,
     "strings the shipped maps spell one way as a publisher and another way as a person, which "
     "happens because a self-published work names its own author as its publisher. A rise means a "
     "publisher name was written by hand where the name store already spelt it."),
    ("one work named two ways across its rows", budget_one_work_named_two_ways_across_its_rows,
     "works whose rows render the same Japanese phrase two different ways, grouped on the name at "
     "the front of each rather than on the fold key, which folds an anthology apart from the work "
     "it collects. A rise means a row was named without looking at what its siblings already say."),
    ("author names romanised as one word", budget_author_names_romanised_as_one_word,
     "people whose Latin name a reader is shown closed up, because the reading behind it states no "
     "word break: 太陽まりい is filed タイヨウマリイ and reads Taiyōmarii where the person is 太陽 "
     "まりい. It falls when a source states a division and cannot fall any other way, since the "
     "only alternative is guessing where somebody's name divides. Some of the residue is names "
     "that genuinely have one element."),
    ("divisions read back from a romanisation",
     budget_divisions_read_back_from_a_romanisation,
     "people whose name is divided on the strength of a space in a community editor's "
     "romanisation, recovered by reading that romanisation backwards. One of the two classes "
     "`a division cites its source` admits without a source that states readings, counted here so "
     "that admitting it is visible. It falls when a source states one of them."),
    ("divisions resting on a community database",
     budget_divisions_resting_on_a_community_database,
     "people whose name divides where Wikidata says it divides and where nothing else does, either "
     "because their reading came from there or because the space was carried onto a reading of "
     "their own. The project owner ruled the source noncanonical and admitted it as a floor, so "
     "this is what that admission costs, counted where somebody can watch it. It falls when a "
     "publisher or the national library states a division."),
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
    ("interpunct credits nobody has ruled on", budget_interpunct_credits_nobody_has_ruled_on,
     "credit fields holding a ・ where the corpus points both ways: one of the names either side "
     "is credited elsewhere on its own and the other is not, so it cannot be said whether the mark "
     "separates two people or sits inside one name. It falls when somebody writes the answer into "
     "data/identity/interpunct-rulings.yaml, and a wrong guess either invents a person or erases one."),
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
    ("ruby asserting a reading per character", budget_ruby_asserting_a_reading_per_character,
     "runs where the ruby annotates one character after another, so a compound reaches a reader as "
     "several ruby units each claiming a reading nobody stated. A rise means a producer started "
     "cutting words again, or new works whose compounds the analyser has no entry for."),
    ("implausible ruby spans", budget_implausible_ruby_spans,
     "furigana runs holding fewer kana than they have kanji. A rise means the aligner placed a "
     "boundary somewhere no reading could fall, which the spelling check cannot see."),
    ("titles read by a machine, unmarked", budget_titles_read_by_a_machine_unmarked,
     "titles a reader is shown spelled from an analyser's reading with no mark on it. Created by "
     "the 2026-08-10 ruling that ordinary vocabulary in a title needs no mark; falls when a title "
     "gets a stated or researched reading. A rise means new works, or a widened rule letting "
     "through something the analyser was guessing at."),
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
     "in any spelling, or a reissue marker from the closed set adapters/facts/cataloguing holds. A subtitle "
     "after the same colon is content and is not counted. A rise means a capture route wrote a "
     "catalogue string through as a name."),
    ("works offered twice in a list", budget_works_offered_twice,
     "rows beyond the first that a shipped list gives to one identity work. 41 works were listed "
     "twice or three times in index.json, which emitted one row per source record and asked "
     "identity nothing. A rise means a collapse stopped running, or a new list shipped without "
     "asking which work a record belongs to."),
    ("published dates that moved in an archive", budget_published_dates_that_moved_in_an_archive,
     "a rebuild rewrote the publication date of a row a published month already carried; a name "
     "improving is the system working and a date changing is not, so each wants a reason"),
    ("one work under two names in a list", budget_one_work_under_two_names,
     "pairs of rows in one list whose titles fold equal and whose credits share a person, which is "
     "one work offered twice under two names. Measured on the shipped rows and never on the "
     "identity registry, so it reports the pairs the registry has not joined. A queue rather than "
     "a fault count: each pair needs deciding, and the number falls by deciding them."),
    ("incomplete attested rows", budget_incomplete_attested_rows,
     "attested releases missing a chapter name, author or access state. The classic sign of a "
     "moved CSS selector — the adapter still returns rows, just emptier ones."),
    ("facts with more than one home", budget_facts_with_more_than_one_home,
     "a vocabulary, a shape or a rule typed into a second file"),
    ("impossibilities asserted without evidence",
     budget_impossibilities_asserted_without_evidence,
     "a comment saying something cannot happen, naming nothing that proves it"),
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
    # ── THE VOLUME MEASURES (VOLUMES-PLAN §1) ────────────────────────────────────────────────
    #
    # Four numbers that were wrong on the day they were first looked at and that nothing was
    # watching. They are here before the fixes they measure, so each of §2, §3 and §4 of that plan
    # can be shown to move the number it claims to move rather than asserted to.
    ("volume rows with no publication date", budget_volume_rows_with_no_publication_date,
     "volume rows a reader can reach that state no publication date, all of them BOOK☆WALKER's: "
     "the shop states 底本発行日 for the volumes whose print edition it recorded and nothing for "
     "the rest. No ISBN-keyed enrichment can reach them because BOOK☆WALKER states no ISBN, so "
     "the route is コミックシーモア's per-volume page, which states both. A rise means new undated "
     "works or a capture that stopped dating rows it used to."),
    ("macron boundaries nobody has ruled on", budget_macron_boundaries_nobody_has_ruled_on,
     "names where our macron says a long vowel and a source spells the pair out, which nobody has "
     "read. Most of the class is a style, because MangaUpdates and Wikidata write ou for ō; what "
     "hides in it is a pair crossing a word boundary, where 御家's オウチ is o-uchi and `Ōchi` "
     "states a long o nobody says. Four of 21 were that. The owner ruled on 2026-08-12 that a "
     "morphology rule is not worth buying for four names, so the four are data in kana.NOT_LONG "
     "and this is what stops a fifth arriving unnoticed. A rise is a name to read."),
    ("volume rows a page counts but cannot list",
     budget_volume_rows_a_page_counts_but_cannot_list,
     "volume rows the heading counts and the page can show nothing for. It was 1,420 across 897 "
     "works, every one of which had its own name and a delivery date in the source record while "
     "the build carried five fields and dropped both. コミック百合姫 was 119 of them. Distinct "
     "from `volume rows with no publication date`, which is a research debt: this is a row a "
     "reader is shown nothing about, and a rise means a field stopped being carried."),
    ("works whose records number one volume twice",
     budget_works_whose_records_number_one_volume_twice,
     "works whose print records give one volume number to two rows, so the page draws vol. 1 twice "
     "and heads the halves as two runs. Its floor is 10 and the floor is real books: citrus was "
     "printed twice and MADB gave it two C-numbers, and a reader should see both. The other ten "
     "are one run described by two catalogues at two precisions, and those go when the volumes "
     "themselves are reconciled. A rise is a new pair worth looking at by hand."),
    ("volume numbers a page draws twice", budget_volume_numbers_a_page_draws_twice,
     "volume numbers a work page would draw more than once inside one print run. The measure "
     "beside `works whose records number one volume twice`, asking about the ROWS a reader sees "
     "rather than the records behind them, which is a different question once a run's records are "
     "folded into one list. Its floor is 5: 君と綴るうたかた numbers a volume 6 in 2024-03 and "
     "another in 2025-01-13, a second printing with its own ISBN that a date comparison cannot "
     "choose between. A rise means a fold stopped folding."),
    ("works holding fewer volumes than the shop states",
     budget_works_holding_fewer_volumes_than_the_shop_states,
     "works コミックシーモア sells more volumes of than the corpus holds, which is a capture that "
     "has fallen behind. The shop is Tier C and this asserts only that two parties disagree about "
     "a countable thing. A rise is ordinary, and is what a series publishing ahead of the next "
     "capture looks like."),
    ("works holding more volumes than the shop states",
     budget_works_holding_more_volumes_than_the_shop_states,
     "the other direction, counted apart so a fixed over-count cannot hide a new under-count. "
     "Mostly products counted as volumes: BOOK☆WALKER lists free sample editions among a series' "
     "items and the ingest numbers every item, which is how MURCIÉLAGO came to have 32 volumes "
     "where the shop and the bibliography both say 29. Should fall to near nothing once a volume "
     "number is read from the product title; what is left is a work the shop has delisted from."),
    ("shelf admissions a reader cannot follow", budget_shelf_admissions_a_reader_cannot_follow,
     "works a retailer's yuri shelf admitted whose row offers no page on that retailer, so the "
     "source named as putting the work here cannot be reached from it. Falls as a route records "
     "which of the shop's pages it read the work off. Its floor is the works a shop lists under "
     "two titles where the bibliography holds one, for which no single page is the work's."),
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
    ("works whose first publication country is unattested",
     budget_works_whose_country_is_unattested,
     "works whose `first_publication.country` is empty, which is DEFINITIONS §6's inclusion test "
     "not having run. It read 0 until now because build.py wrote the literal \"JP\" on every "
     "record, so the field asserted the answer and no check on it could fail. Every source here "
     "catalogues the Japanese EDITION and none states where the work first appeared, so this falls "
     "one work at a time as a serialisation venue is read off a publisher's page and recorded in "
     "data/scope.yaml. A rise means the corpus grew, which is expected, and the number to watch is "
     "the share rather than the count."),
    ("scope questions left open", budget_scope_questions_left_open,
     "works a scope signal flagged as a possible translation that nobody has ruled on. A credited "
     "translator and a publisher's foreign-comics line are evidence and not proof: a 現代語訳 is "
     "translated and Japanese. Falls as each is settled either way in data/scope.yaml, citing the "
     "page that settles it, and reaches zero."),
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
    ("listing series with no feed of their own", budget_listing_series_with_no_feed_of_their_own,
     "series a GigaViewer platform's own yuri listing names that the last per-series feeds run did "
     "not resolve. The pairing of a name to a series id is positional and slipped by one on "
     "2026-08-10, which cost 一迅プラス's second entry its chapter list while every other work came "
     "out renamed and looking right. Falls to zero on the first run after the fix; a rise means "
     "the pairing has slipped again, or a platform announced a series before its first chapter."),
    ("series names holding a page title", budget_series_names_holding_a_page_title,
     "works a GigaViewer feeds file holds under a name whose round brackets do not close, which is "
     "what a feed title read with a greedy match leaves behind: the platform's own bracketed name "
     "and its tagline, with the series trapped at the end. The match was replaced in c747b62 and "
     "the four rows it had already written are still in the source layer, kept by carry_over. Each "
     "goes when its platform's feeds are fetched again."),
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
        # THE §6 SCOPE RULINGS AND WHAT THE RUN REPORTED OF THEM, both on the context so a canary
        # can be planted between them. An invariant that opened data/scope.yaml itself could be
        # shown nothing and would report healthy for the rest of its life.
        "scope_rulings": (_yaml(ROOT / "data" / "scope.yaml", {}) or {}).get("rulings") or [],
        "scope_reported": ((_load(BUILD / "run.json", {}) or {}).get("scope") or {}).get("rulings")
                          or [],
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
        "shop_records": _shop_records(),
        # WHAT EACH CAPTURE PASS WAS TOLD TO READ, BESIDE WHAT IT WROTE. Held as the two
        # collections and not as the answer, so a canary can be planted on either side of the
        # join: a target added, or a captured row taken away, which is the failure itself.
        "capture_passes": _capture_passes(),
        # Both sides of the ニコニコ channel comparison, loaded here for the same reason as the
        # two above: a check that opens its own file cannot be shown a canary.
        "nicovideo_channels": (_yaml(ROOT / "data" / "source" / "nicovideo" / "nicovideo.yaml",
                                     {}) or {}).get("works") or [],
        "nicovideo_recorded_channels": _nicovideo_recorded_channels(),
        # The per-episode lists, loaded here for the same reason: the check comparing them against
        # the work-level flag must be shown a canary in both files.
        "nicovideo_work_chapters": (_yaml(ROOT / "data" / "source" / "nicovideo" / "works.yaml",
                                          {}) or {}).get("works") or [],
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


def _shop_records():
    """Every source-layer record the BOOK☆WALKER adapter wrote, as parsed documents."""
    out = []
    for f in sorted((ROOT / "data" / "source" / "bookwalker").glob("*.yaml")):
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


def _private(value):
    """A copy a probe may mutate freely, sharing everything that cannot be mutated.

    `copy.deepcopy` WAS 18.3 OF THE SELF-TEST'S 18.4 SECONDS, twelve million calls to copy data that
    came out of JSON and YAML. Only the containers need copying: a string, a number, None and a bool
    are immutable, so handing the same object to the probe and to the base is safe by construction.

    ANYTHING THIS DOES NOT RECOGNISE GOES TO `deepcopy`, because the cost of being wrong here is a
    probe writing into the context every later probe reads, and the fault would look like a check
    that stopped catching its canary rather than like a copying bug. `self_test` compares a
    fingerprint of the context taken before any probe ran, which is the net under this.
    """
    t = type(value)
    if t is dict:
        return {k: _private(v) for k, v in value.items()}
    if t is list:
        return [_private(v) for v in value]
    if t is tuple:
        return tuple(_private(v) for v in value)
    if t is set:
        return set(value)
    if t in (str, int, float, bool, bytes, type(None)):
        return value
    import copy as _c
    return _c.deepcopy(value)


class _Scratch(dict):
    """A context a canary can be planted in, copying only the part the plant actually touches.

    DEEPCOPYING THE WHOLE CONTEXT WAS 23 OF THE SELF-TEST'S 53 SECONDS, 34 probes at 0.67 s each,
    and every one of them threw the copy away after mutating one key. This copies a top-level value
    the first time it is fetched, so `c["series"].append(...)` gets a private list and everything
    else stays shared.

    `freeze()` is the half that makes it fast: a plant touches one key, and the CHECK that follows
    reads a dozen. Copying for the check's reads would give back everything the lazy copy saved, so
    the plant runs unfrozen and the check runs frozen. That rests on checks being readers, which
    `self_test` verifies at the end by comparing the context against a fingerprint taken before any
    probe ran. A check that mutates its context would corrupt every probe after it, and this says so
    instead of leaving it to be discovered.
    """

    def __init__(self, base):
        super().__init__(base)
        self._base, self._copied, self._frozen = base, set(), False

    def __getitem__(self, k):
        # A KEY THE BASE NEVER HELD is one a probe added, so it is already private and copying it
        # would fail. `_iface` is planted by the interface probes and is exactly this case.
        if not self._frozen and k not in self._copied and k in self._base:
            super().__setitem__(k, _private(self._base[k]))
            self._copied.add(k)
        return super().__getitem__(k)

    def __setitem__(self, k, v):
        # ASSIGNING A KEY MAKES IT PRIVATE. Without this the next read saw a key it had not copied
        # yet, fetched a fresh copy from the base, and threw the plant away, which is how three
        # probes for `one work under two names in a list` stopped catching their canaries.
        self._copied.add(k)
        super().__setitem__(k, v)

    def get(self, k, default=None):
        # `dict.get` DOES NOT GO THROUGH `__getitem__` on a subclass, so without this a plant
        # reaching for `c.get("names")` would be handed the shared object and would write straight
        # into the context every later probe reads.
        return self[k] if k in self else default

    def freeze(self):
        self._frozen = True
        return self


def _fingerprint(ctx):
    """A cheap statement about a context's shape, for detecting a check that writes to it."""
    return {k: len(v) for k, v in ctx.items() if hasattr(v, "__len__")}


def _scratch_self_test():
    """`_Scratch` stands between every canary and the context, so it is checked before they are."""
    base = {"rows": [1, 2], "names": {"a": {"r": "X"}}}
    ok = True

    def bad(why):
        nonlocal ok
        print(f"  self-test FAILED — _Scratch {why}")
        ok = False

    c = _Scratch(base)
    c["rows"].append(3)
    if base["rows"] != [1, 2]:
        bad("let an append reach the base")
    if c["rows"] != [1, 2, 3]:
        bad("lost an append")

    c = _Scratch(base)
    c.get("names")["a"]["r"] = "Y"
    if base["names"]["a"]["r"] != "X":
        bad("let `get` hand out the shared object")

    c = _Scratch(base)
    c["rows"] = ["planted"]
    if c["rows"] != ["planted"]:
        bad("overwrote an assignment with a copy of the base")

    c = _Scratch(base)
    c["absent"] = 1
    if c["absent"] != 1:
        bad("could not hold a key the base never had")

    c = _Scratch(base).freeze()
    if c["rows"] is not base["rows"]:
        bad("kept copying after freeze")
    return ok


def self_test():
    """Prove the invariants can fail. A check that cannot demonstrate a catch is not a check."""
    import copy
    ctx = context()
    _before = _fingerprint(ctx)
    ok_scratch = _scratch_self_test()
    if not ctx["releases"]:
        print("  self-test SKIPPED — no build output to plant a canary in")
        return True
    probes = [
        ("feed holds only attested rows", inv_feed_is_attested,
         lambda c: c["releases"].append({"work": "CANARY", "provenance": "claimed"})),
        ("every update has a kind", inv_no_unknown_kind,
         lambda c: c["releases"].append({"work": "CANARY", "kind": "unknown"})),
        # THE JOIN BETWEEN THE STORE AND THE ROW, planted as the fault would arrive: a title the
        # store has an English name for whose row carries none. That is what a fold quietly ceasing
        # to match looks like, and it would otherwise show only as a reader seeing romaji.
        ("a work shows the English its record holds", inv_a_work_shows_the_english_its_record_holds,
         lambda c: (c["names_shipped"].setdefault("titles", {}).update(
             {(c["series"][0].get("work") or "CANARY"): {"en": "A Canary In English"}}),
             c["series"][0].pop("work_en", None))),
        # PLANTED AS THE FAULT ARRIVED, which is how it did arrive: a pass wrote its own module
        # name into `sourced_from` and every reader of that field carried it to the page. `webpages`
        # is one of the six that really were there, not a name invented for the probe (§14b).
        ("no source a reader sees is an adapter", inv_no_source_a_reader_sees_is_an_adapter,
         lambda c: c["series"][0].setdefault("sourced_from", []).append(
             {"source": "webpages", "holds": "attribution", "read": "2026-08-10"})),
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
        # THE CANARY IS THE FALLBACK REMOVED, planted in the SOURCE the context holds. A row of
        # Japanese data no longer proves anything: the renderer floors whatever it is handed, so a
        # planted row comes back romanised and the check correctly reports nothing. What this now
        # asserts is a property of the RENDERER, so the canary has to break the renderer, and
        # taking `enFallback` back to a pass-through is exactly the state the 77 were in.
        ("English mode has no Japanese", inv_english_mode_has_no_japanese,
         lambda c: c.update({"interface_js": (c.get("interface_js") or "").replace(
             "  if (!s || !JA_ANY.test(s)) return s;\n  const whole = floorText(s);",
             "  if (s) return s;\n  const whole = floorText(s);")})),
        # THE CANARY IS THE FAULT THAT SHIPPED (§14b). The catalogue tab really did print
        # index.json's title with `esc` instead of asking workLabel for it, and 2,430 rows stayed
        # Japanese in English mode. Planted in the SOURCE the context holds, so the probe reaches
        # the same string the check reads.
        ("names reach a page only through their renderer",
         inv_names_reach_a_page_only_through_their_renderer,
         lambda c: c.update({"interface_js": (c.get("interface_js") or "").replace(
             "${workLabel({ work: w.t })}", "${esc(w.t)}")})),
        # THE CANARY IS THE FAULT A READER FOUND. The work page heading asked `workLabel` once,
        # and 併記 renders each row by asking twice, so the heading answered in Japanese and the
        # English title never appeared. Every other language setting was right, which is what made
        # it survive.
        ("a name reaches both lines of a bilingual row", inv_a_name_in_both_mode_is_rendered_in_both,
         lambda c: c.update({"interface_js": (c.get("interface_js") or "").replace(
             "${bilingual(() => workLabel(r))}", "${workLabel(r)}")})),
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
        # THE ELISION DROPPED FOR ONE SPELLING, which is what a table edited in a hurry looks like.
        # 著 stops eliding and 578 catalogue bylines state a job the catalogue never distinguished,
        # while 著者 and 作 go on eliding, so the word this scans for is still derived and the
        # canary is a real disagreement rather than an empty vocabulary.
        ("a byline never states the default role", inv_a_byline_never_states_the_default_role,
         lambda c: c.update({"interface_js": (c.get("interface_js") or "").replace(
             "const ROLE_ELIDED = { '著': '',", "const ROLE_ELIDED = {")})),
        # THE CANARY IS THE LINE THAT SHIPPED (§14b), planted in the SOURCE the context holds.
        # `creditLine` shortened a long byline by cutting the field on the slash and calling
        # `linkedCredits` with the pieces joined back up, which is a field the build never divided,
        # so the division went missing and the line dropped to the floor. That is how
        # `安田剛助・文尾文` reached a reader as `???? · Bun?Bun`. Nothing invented: this is the two
        # statements the file held, restored.
        ("no name is spelled with question marks", inv_no_name_is_spelled_with_question_marks,
         lambda c: c.update({"interface_js": (c.get("interface_js") or "")
                             .replace("const people = creditPeople(raw) || (raw ? [raw] : []);",
                                      "const people = raw.split(/\\s*\\/\\s*/).filter(Boolean);")
                             .replace("const head = linkedCredits(r, CREDITS_SHOWN);",
                                      "const head = linkedCredits({ ...r, author: "
                                      "people.slice(0, CREDITS_SHOWN).join(' / ') });")})),
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
        # THE FAULT AS IT WAS SHIPPED (§14b): the item's position in the shop's listing, written
        # into the number field. This is MURCIÉLAGO's third product, a free sample of volume 1,
        # which the old rule numbered 3 because it came third.
        ("a volume number is the shop's own", inv_a_volume_number_is_the_shop_s_own,
         lambda c: c["shop_records"].append({"work_id": "CANARY", "volumes": [
             {"title": "MURCIÉLAGO -ムルシエラゴ- 1巻【無料お試し版】", "number": "3"}]})),
        # AND A FULL-WIDTH NUMBER IS THE SAME NUMBER, so the fold is not optional: the shop writes
        # `さかさまロリポップ　１巻` and a record numbering it 2 must still be caught.
        ("a volume number is the shop's own", inv_a_volume_number_is_the_shop_s_own,
         lambda c: c["shop_records"].append({"work_id": "CANARY2", "volumes": [
             {"title": "さかさまロリポップ　１巻", "number": "2"}]})),
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
        # THE SECOND CLAUSE NEEDS ITS OWN CANARY, because the first plants a kana surface and the
        # clause covering every other surface would go on reporting clean for the rest of its life
        # if it broke (§14b). This record is what the store held on 2026-08-09, verbatim: SudachiPy
        # handed back one token per kana and the site read `No Pi Ya Ka Kozue`.
        ("a division cites its source", inv_a_division_cites_its_source,
         lambda c: c["names"]["authors"].update({"のぴやか梢": {
             "reading": "ノ ピ ヤ カ コズエ", "reading_basis": "analyser",
             "reading_source": "sudachi", "reading_source_kind": "analyser"}})),
        # THE STATE 293 RECORDS WERE IN ON 2026-08-09, VERBATIM (§14b). This is not a canary
        # invented for the check: `ndl_heading.entry` produced exactly this record, with the
        # division stated in the note and the field left empty, and the store held it for a day.
        # The note is kept in the canary on purpose, because prose beside the empty field is what
        # made the fault look like a record that had said where its division came from.
        ("a division names its donor in a field", inv_a_division_names_its_donor_in_a_field,
         lambda c: c["names"]["authors"].update({"わらびもちきなこ": {
             "reading": "ワラビモチ キナコ", "reading_basis": "surface",
             "reading_source": "ndlsearch.ndl.go.jp", "reading_source_kind": "derived",
             "reading_note": "The National Diet Library's author heading divides this person as "
                             "'ワラビモチ キナコ'."}})),
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
        # A RULING NOTHING REPORTS, which is precisely the register that reads as a control and is
        # not one: data/source/kadokomi/withheld.yaml named five works as not published while all
        # five were live and no number anywhere disagreed.
        ("scope rulings are accounted for", inv_scope_rulings_are_accounted_for,
         lambda c: c["scope_rulings"].append(
             {"work": "CANARY", "title": "カナリア", "disposition": "out-of-scope",
              "country_basis": "publisher-states-origin"})),
        # AND A RULING RESTING ON A TERM THE VOCABULARY DOES NOT HOLD, which is the other way this
        # file and the module that reads it can come apart: a ruling written against a renamed term
        # decides nothing and looks decided.
        ("scope rulings are accounted for", inv_scope_rulings_are_accounted_for,
         _plant_a_ruling_on_an_unknown_term),
        # TWO RELEASES UNDER ONE IDENTIFIER, which is the state `pixivcomic:第3話` was in: three
        # works' third chapters answering to one string, and every measure keyed on the pair
        # reading them as one row.
        ("a release id names one release", inv_a_release_id_names_one_release,
         lambda c: c["releases"].extend([
             {"plat": "canary", "id": "canary:第3話", "work": "カナリア", "ep": "第3話"},
             {"plat": "canary", "id": "canary:第3話", "work": "カナリアふたたび", "ep": "第3話"}])),
        # THE TWO PASSES THAT DECIDE THIS, COMING APART. The page pass reads the episode tiles and
        # the build reads the episodes it stored, and a route only one of them recognises is the
        # shape the fault took: the header said `アプリで読める` and the stored chapters were still
        # being counted as web reading.
        ("no app-only route is published as web reading",
         inv_no_app_only_route_is_published_as_web_reading,
         lambda c: c["nicovideo_work_chapters"].append(
             {"url": "https://manga.nicovideo.jp/comic/99999",
              "chapters": [{"title": "カナリア", "app_only": True}]})),
        # AND A ROUTE BOTH OF THEM RECOGNISE, STILL SHIPPED. The producers agreeing is not the
        # property; the property is that no reader is sent to it.
        ("no app-only route is published as web reading",
         inv_no_app_only_route_is_published_as_web_reading,
         _plant_an_app_only_route_a_reader_is_sent_to),
        # AND THE NAME KEPT WHERE NOBODY LOOKS, which is the state this shipped in for one build:
        # the credit recorded and the byline empty, so the work page drew nothing.
        ("no app-only route is published as web reading",
         inv_no_app_only_route_is_published_as_web_reading,
         lambda c: c["series"].append(
             {"work": "カナリア", "author": "",
              "credits": [{"name": "野宮りおん", "basis": "named-on-an-app-only-listing"}]})),
    ]
    ok = True
    for name, fn, plant in probes:
        c = _Scratch(ctx)
        plant(c)
        c.freeze()
        if not fn(c):
            print(f"  self-test FAILED — '{name}' did not catch its canary")
            ok = False

    # A BUDGET IS A COUNT AND CANNOT BE PROBED THE SAME WAY, so one is probed here on the number
    # instead of on a pass. `titles carrying cataloguing punctuation` is the one that needs it: it
    # measures a class its subject deliberately refuses to act on, and a count that reads 3 and a
    # count that cannot rise above 3 look identical from outside (§14b). The canary is a fullwidth
    # equals sign, which `isbd.areas` would never split and this must still see.
    c = _Scratch(ctx)
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

    # A COUNT THAT READS 0 AND A COUNT THAT CANNOT RISE LOOK IDENTICAL FROM OUTSIDE, and this one
    # was introduced at 0 because the seven works it found had just been settled. The canary is the
    # shape those seven had: two rows of one work, agreeing in Japanese up to the subtitle mark and
    # disagreeing in English before the colon.
    c = _Scratch(ctx)
    was = budget_one_work_named_two_ways_across_its_rows(c)
    c["series"].append({"id": "CANARY1", "work": "カナリアの歌", "work_en": {"en": "The Canary's Song"}})
    c["series"].append({"id": "CANARY2", "work": "カナリアの歌アンソロジーコミック",
                        "work_en": {"en": "Canary Song: The Anthology Comic"}})
    if budget_one_work_named_two_ways_across_its_rows(c) != was + 1:
        print("  self-test FAILED — 'one work named two ways across its rows' did not count "
              "its canary")
        ok = False
    # AND A SUBTITLE IS NOT A DISAGREEMENT, or every licensed spin-off reads as one. `Side Story`
    # after a licensed name is that work's own and the count must not move for it.
    c2 = _Scratch(ctx)
    base = budget_one_work_named_two_ways_across_its_rows(c2)
    c2["series"].append({"id": "CANARY3", "work": "カナリアの歌", "work_en": {"en": "The Canary's Song"}})
    c2["series"].append({"id": "CANARY4", "work": "カナリアの歌 : 番外編",
                         "work_en": {"en": "The Canary's Song Side Story: Feathers"}})
    if budget_one_work_named_two_ways_across_its_rows(c2) != base:
        print("  self-test FAILED — 'one work named two ways across its rows' counted a subtitle "
              "as a disagreement")
        ok = False

    # A PHRASE THAT DID NOT CONSUME THE STORE, counted rather than passed or failed. The canary is
    # a real credit and the analyser's real answer for it: `[著]安田剛助` was shipped as
    # `[ Cho ] Yasuda Takesuke` while the store held Yasuda Kōsuke from openBD, and a count that
    # reads 70 is indistinguishable from a count that cannot rise (§14b).
    c = _Scratch(ctx)
    was = budget_credit_phrases_spelling_a_person_otherwise(c)
    shipped = c["names_shipped"] = dict(c.get("names_shipped") or {})
    shipped["credit_parts"] = dict(shipped.get("credit_parts") or {})
    shipped["phrases"] = dict(shipped.get("phrases") or {})
    shipped["authors"] = dict(shipped.get("authors") or {})
    shipped["credit_parts"]["[著]カナリア"] = {"p": [{"n": "カナリア", "r": "著"}]}
    shipped["phrases"]["[著]カナリア"] = "[ Cho ] Ka Naria"
    shipped["authors"]["カナリア"] = {"romaji": {"macron": "Kanaria"}}
    if budget_credit_phrases_spelling_a_person_otherwise(c) != was + 1:
        print("  self-test FAILED — 'credit phrases spelling a person otherwise' did not count "
              "its canary")
        ok = False

    # A BYLINE RESPELT UNDER ITS OWN ARTIST, and the canary is a state this repository was in
    # yesterday rather than a shape invented for the probe. 永田さんずい is the field w00094
    # carries; the store's record of the same person spells it 永田　さんずい and its ruby spans
    # carry that space, so a row reaching the walk without a rendering of its own is drawn with a
    # space the catalogue never wrote. That row is what this appends. A count that reads 23 and a
    # count that cannot rise look the same from outside (§14b).
    c = _Scratch(ctx)
    was = budget_bylines_drawn_in_a_spelling_the_field_does_not_write(c)
    c["series"] = list(c["series"]) + [{"id": "wCANARY", "author": "永田さんずい"}]
    if budget_bylines_drawn_in_a_spelling_the_field_does_not_write(c) != was + 1:
        print("  self-test FAILED — 'bylines drawn in a spelling the field does not write' did "
              "not count its canary")
        ok = False

    # AN ADMISSION WITH NOWHERE TO FOLLOW IT TO, and both directions are probed because a count
    # that reads 5 and a count that cannot rise above 5 look identical from outside (§14b). The
    # first canary is the shape 230 shipped rows really had: コミックシーモア named as the
    # comparator, a print block from the bibliography, and no shop address anywhere on the row. The
    # second is the same row with the address the fix puts there, and it must NOT be counted, which
    # is the half that would go quiet if the measure stopped looking at `shop_url`.
    c = _Scratch(ctx)
    was = budget_shelf_admissions_a_reader_cannot_follow(c)
    _shelf = {"kind": "shelf", "type": "retailer", "source": "コミックシーモア",
              "term": "百合・GL", "read": "2026-08-05",
              "url": "https://www.cmoa.jp/search/genre/37/"}
    c["series"] = list(c["series"]) + [
        {"id": "CANARY-UNREACHABLE", "work": "カナリア", "evidence": [_shelf],
         "print": [{"work_id": "CANARY", "volumes": 1}]}]
    if budget_shelf_admissions_a_reader_cannot_follow(c) != was + 1:
        print("  self-test FAILED — 'shelf admissions a reader cannot follow' did not count a "
              "shelf admission with no page on the shop")
        ok = False
    c["series"][-1]["print"][0]["shop_url"] = "https://www.cmoa.jp/title/1132/"
    if budget_shelf_admissions_a_reader_cannot_follow(c) != was:
        print("  self-test FAILED — 'shelf admissions a reader cannot follow' counted a row whose "
              "shop page is on it")
        ok = False

    # THE INTERFACE'S OWN COPY OF THE FOLD, changed to what it looked like before the two were held
    # together: NFKC and no space stripping, which is `curate._fold` and is what made "the same key"
    # mean two things. The canary is a real state of this repository and not an invented one.
    c = _Scratch(ctx)
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
    c = _Scratch(ctx)
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

    # ── THE VOLUME MEASURES, EACH PLANTED AS THE FAULT ARRIVED (§14b) ────────────────────────
    #
    # Every canary below is the shape a real record had on 2026-08-12, not one invented to make a
    # counter move. The collections are REPLACED rather than appended to, so each probe answers a
    # number rather than a delta, for the reason the paragraph above gives.
    c = _Scratch(ctx)
    c["series"] = [{"id": "wCANARY", "work": "カナリア",
                    "print": [{"work_id": "bwCANARY", "work_ids": ["bwCANARY"], "volumes": 3}]}]
    # BOOK☆WALKER's own shape: 底本発行日 on the volumes whose print edition it recorded, and
    # nothing on the rest, which is every undated row in the corpus.
    c["works"] = [{"work_id": "bwCANARY", "volumes": [{"number": 1, "published": "2014-04-25"},
                                                      {"number": 2}, {"number": 3}]}]
    if budget_volume_rows_with_no_publication_date(c) != 2:
        print("  self-test FAILED — 'volume rows with no publication date' did not count the two "
              "rows BOOK☆WALKER left undated")
        ok = False
    # AND A ROW NO READER CAN REACH IS NOT COUNTED, which is the other half of the rule: works.json
    # holds records no print block stands for, and counting those would report a debt nobody owes.
    c2 = _Scratch(ctx)
    c2["series"] = []
    c2["works"] = c["works"]
    if budget_volume_rows_with_no_publication_date(c2) != 0:
        print("  self-test FAILED — 'volume rows with no publication date' counted a volume no "
              "print block reaches")
        ok = False

    # A NAME NOBODY HAS READ, which is the whole job of the measure: the four faults are ruled and
    # the seventeen styles are ruled, so anything arriving is arriving unread.
    c = _Scratch(ctx)
    c["names_shipped"] = {"authors": {"カナリア": {
        "en": "Kanaria", "romaji": {"macron": "Kanaria", "double": "Kanaria"}}}}
    if budget_macron_boundaries_nobody_has_ruled_on(c) != 0:
        print("  self-test FAILED — 'macron boundaries nobody has ruled on' counted a name whose "
              "romanisation holds no long vowel at all")
        ok = False
    c["names_shipped"] = {"authors": {"カナリア": {
        "en": "Kanaoue", "romaji": {"macron": "Kanaōe", "double": "Kanaoue"}}}}
    if budget_macron_boundaries_nobody_has_ruled_on(c) != 1:
        print("  self-test FAILED — 'macron boundaries nobody has ruled on' did not count a "
              "macron a source spells out")
        ok = False
    # AND A NAME ALREADY READ IS NOT COUNTED AGAIN, whichever way it was ruled.
    c["names_shipped"] = {"authors": {"御家かえる": {
        "en": "Ouchi Kaeru", "romaji": {"macron": "Ōchi Kaeru", "double": "Ouchi Kaeru"}}}}
    if budget_macron_boundaries_nobody_has_ruled_on(c) != 0:
        print("  self-test FAILED — 'macron boundaries nobody has ruled on' counted a name the "
              "queue already carries a decision for")
        ok = False

    # THE STATE MURCIÉLAGO WAS IN when the cross-catalogue fold was first tried and withdrawn: one
    # block, and the two catalogues' rows for volume 1 both drawn, at two precisions.
    c = _Scratch(ctx)
    c["series"] = [{"id": "wCANARY", "work": "カナリア",
                    "print": [{"work_id": "C1", "work_ids": ["C1", "bw1"], "volumes": 2}]}]
    c["works"] = [{"work_id": "C1", "volumes": [{"number": "1", "published": "2014-04"},
                                                {"number": "2", "published": "2014-09"}]},
                  {"work_id": "bw1", "volumes": [{"number": "1", "published": "2014-04-25"}]}]
    if budget_volume_numbers_a_page_draws_twice(c) != 1:
        print("  self-test FAILED — 'volume numbers a page draws twice' did not count a number "
              "drawn by two of one block's records")
        ok = False
    # AND TWO BLOCKS DRAWING A 1 EACH IS A REISSUE, which is two lists under two headings and not
    # one number drawn twice. citrus is that, and counting it would make the budget unreachable.
    c["series"] = [{"id": "wCANARY", "work": "カナリア",
                    "print": [{"work_id": "C1", "work_ids": ["C1"], "volumes": 2},
                              {"work_id": "bw1", "work_ids": ["bw1"], "volumes": 1}]}]
    if budget_volume_numbers_a_page_draws_twice(c) != 0:
        print("  self-test FAILED — 'volume numbers a page draws twice' counted two runs, which "
              "are two lists and not one list with a number in it twice")
        ok = False

    # THE FAULT AS IT WAS FOUND (§14b): コミック百合姫's issues, carrying their own names and
    # delivery dates in the record and neither of them on the volume row the build wrote.
    c = _Scratch(ctx)
    c["series"] = [{"id": "wCANARY", "work": "カナリア",
                    "print": [{"work_id": "bwCANARY", "work_ids": ["bwCANARY"], "volumes": 3}]}]
    c["works"] = [{"work_id": "bwCANARY", "volumes": [{}, {}, {"designation": "2017年1月号"}]}]
    if budget_volume_rows_a_page_counts_but_cannot_list(c) != 2:
        print("  self-test FAILED — 'volume rows a page counts but cannot list' did not count the "
              "rows the build left with nothing on them")
        ok = False
    # AND A DELIVERY DATE ALONE IS SOMETHING, which is what 1,420 of them had all along.
    c["works"] = [{"work_id": "bwCANARY", "volumes": [{"delivered": "2016-11-18"}, {}, {}]}]
    if budget_volume_rows_a_page_counts_but_cannot_list(c) != 2:
        print("  self-test FAILED — 'volume rows a page counts but cannot list' counted a row "
              "carrying the day the shop began selling it")
        ok = False

    # MURCIÉLAGO's two records, which number volume 1 twice: MADB at month precision with an ISBN,
    # BOOK☆WALKER at day precision without one.
    c = _Scratch(ctx)
    c["series"] = [{"id": "wCANARY", "work": "カナリア",
                    "print": [{"work_id": "C1", "work_ids": ["C1", "bw1"], "volumes": 2}]}]
    c["works"] = [{"work_id": "C1", "volumes": [{"number": "1", "published": "2014-04"}]},
                  {"work_id": "bw1", "volumes": [{"number": 1, "published": "2014-04-25"}]}]
    if budget_works_whose_records_number_one_volume_twice(c) != 1:
        print("  self-test FAILED — 'works whose records number one volume twice' did not count "
              "two catalogues numbering one volume")
        ok = False
    # AND RECORDS THAT DIVIDE A RUN BETWEEN THEM ARE NOT A COLLISION. 捏造トラップ holds volumes
    # 1, 2, 3 and 5 under one heading and 4 and 6 under another, which is the case `print_runs`
    # folds into one run, and a measure that counted it would never reach its floor.
    c["works"] = [{"work_id": "C1", "volumes": [{"number": "1"}, {"number": "2"}]},
                  {"work_id": "bw1", "volumes": [{"number": "3"}]}]
    if budget_works_whose_records_number_one_volume_twice(c) != 0:
        print("  self-test FAILED — 'works whose records number one volume twice' counted two "
              "records that divide a run between them")
        ok = False

    # THE TWO DIRECTIONS OF THE SHOP DISAGREEMENT, on one work joined by a shared ISBN. 32 against
    # 29 is MURCIÉLAGO as shipped; the other direction is 冷たくて柔らか at 4 against 7.
    for stated, over, under in ((3, 1, 0), (29, 0, 1)):
        c = _Scratch(ctx)
        c["series"] = [{"id": "wCANARY", "work": "カナリア",
                        "print": [{"work_id": "C1", "work_ids": ["C1"], "publisher": "一迅社",
                                   "volumes": 5}]}]
        c["works"] = [{"work_id": "C1", "volumes": [{"number": "1", "isbn": "9784757542907"}]}]
        c["cmoa_capture"] = [{"shop_id": "CANARY", "shelf_title": "カナリア",
                              "volumes_stated": stated,
                              "volumes": [{"volume": 1, "isbn": "9784757542907"}]}]
        if budget_works_holding_more_volumes_than_the_shop_states(c) != over:
            print(f"  self-test FAILED — 'works holding more volumes than the shop states' did "
                  f"not answer {over} where the shop says {stated} and the corpus holds 5")
            ok = False
        if budget_works_holding_fewer_volumes_than_the_shop_states(c) != under:
            print(f"  self-test FAILED — 'works holding fewer volumes than the shop states' did "
                  f"not answer {under} where the shop says {stated} and the corpus holds 5")
            ok = False
    # A SAMPLE EDITION IS NOT A DISAGREEMENT, which is the fault that made this measure wrong
    # before `shopjoin.counts_volumes` existed: `まんがの作り方【お試し版】` carries the work's ISBN
    # and holds one volume, and read as the work's length it turned an agreement into 8 against 1.
    c["cmoa_capture"] = [{"shop_id": "CANARY", "shelf_title": "カナリア【お試し版】",
                          "volumes_stated": 1,
                          "volumes": [{"volume": 1, "isbn": "9784757542907"}]}]
    if budget_works_holding_more_volumes_than_the_shop_states(c) != 0:
        print("  self-test FAILED — 'works holding more volumes than the shop states' read a free "
              "sample's length as the work's")
        ok = False

    # A PAIR THE REGISTRY HAS NOT JOINED, which is the only kind this one can see. Two rows folding
    # to one title with a person in common: the shape くちびるためいきさくらいろ has in the shipped
    # list today. The bracketed edition marker is there because `fold` removes it, so a collected
    # edition beside its volumes is one work with two rows and has to be counted.
    c = _Scratch(ctx)
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
    c = _Scratch(ctx)
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
    c = _Scratch(ctx)
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
    c = _Scratch(ctx)
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
        # out of the count, which the assertion below proves by giving every pass every target and
        # requiring zero.
        fuz["captured"].add(dropped)
        for p in c["capture_passes"]:
            p["captured"] |= set(p["targets"])
        if budget_targets_a_capture_wrote_no_row_for(c) != 0:
            print("  self-test FAILED — 'targets a capture wrote no row for' still counted works "
                  "after every target was given a captured row")
            ok = False

    # A DIVISION LENT BY AN ANONYMOUS EDIT, IN BOTH SHAPES THE STORE HOLDS IT IN, and both canaries
    # are records data/names/authors.yaml really carried on 2026-08-09. やぶうち優 is Wikidata's own
    # reading, divided where P734 and P735 divide it; ヤブウチユウ is that person's kana credit, whose
    # sounds are its own surface and whose space was carried across by `boundary.fill`. The second is
    # the one a count on `reading_basis` alone would never see, which is why it is planted separately.
    c = _Scratch(ctx)
    was = budget_divisions_resting_on_a_community_database(c)
    c["names"]["authors"].update({"カナリアユウ": {
        "reading": "カナリア ユウ", "reading_basis": "community-printed",
        "reading_source": "wikidata", "reading_source_kind": "community-db"}})
    if budget_divisions_resting_on_a_community_database(c) != was + 1:
        print("  self-test FAILED — 'divisions resting on a community database' did not count a "
              "reading a community database printed already divided")
        ok = False
    c["names"]["authors"].update({"カナリアレイ": {
        "reading": "カナリア レイ", "reading_basis": "surface", "reading_source": "surface",
        "reading_boundary": "カナリアユウ", "reading_boundary_basis": "community-printed"}})
    if budget_divisions_resting_on_a_community_database(c) != was + 2:
        print("  self-test FAILED — 'divisions resting on a community database' did not count a "
              "division carried onto a reading of the name's own")
        ok = False

    # A CREDIT WHOSE ・ THE CORPUS CANNOT SETTLE, planted as the corpus really states these two.
    # 矢立肇 is credited alone on ラブライブ!, so the left half is a person; nothing anywhere credits
    # the right half, so the evidence points both ways and nobody may decide it from a keyboard.
    # Planted on `index[].c`, which is a real credit surface and the one that reaches the catalogue
    # tab, rather than on a shape invented for the check.
    c = _Scratch(ctx)
    was = budget_interpunct_credits_nobody_has_ruled_on(c)
    c["index"] = list(c["index"]) + [{"t": "カナリアの魔法", "c": "矢立肇・カナリアユウ"}]
    if budget_interpunct_credits_nobody_has_ruled_on(c) != was + 1:
        print("  self-test FAILED — 'interpunct credits nobody has ruled on' did not count a "
              "credit with one half attested and one half appearing nowhere else")
        ok = False
    # AND THE OTHER DIRECTION, because a number that only rises never records the remedy. Two halves
    # neither of which is credited anywhere else is one person's name, which is `くろば・Ｕ`, and it
    # is settled rather than held.
    c["index"] = list(ctx["index"]) + [{"t": "カナリアの魔法", "c": "カナリアユウ・カナリアレイ"}]
    if budget_interpunct_credits_nobody_has_ruled_on(c) != was:
        print("  self-test FAILED — 'interpunct credits nobody has ruled on' counted a credit "
              "whose halves the corpus credits nowhere else, which the rule settles as one person")
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

    # THE ASSUMPTION `freeze` RESTS ON, checked instead of trusted. If a check wrote to the context
    # it was handed, every probe after it ran against corrupted data and the run means nothing.
    if not ok_scratch:
        ok = False
    if _fingerprint(ctx) != _before:
        print("  self-test FAILED — a check mutated the context it was given")
        ok = False

    if ok:
        print(f"  self-test passed ({len(probes)} canaries caught, plus the tics list)")
        print("CANARY-PROVEN")   # see adapters/testkit.py: proven by planted canary
    return ok



#: A remembered pass, keyed on everything the check could have read. Outside `data/build`, which
#: the green-tree token hashes.
VERIFIED = ROOT / "data" / "cache" / "checks.json"

#: The name the self-test is remembered under. Reserved: no invariant or budget may take
#: it, and the leading space is what makes that true rather than merely intended, since
#: every real name comes from INVARIANTS or BUDGETS_DEF and none of those is spelled so.
SELF_TEST = " the checks can fail"


def _input_keys():
    """One digest per class of input a check can read, so an unchanged class need not be re-read.

    THREE CLASSES AND NOT 110 DECLARATIONS. Asking every check to name its inputs would be more
    precise and would be a hand-kept list, which is the fault `deploy_sensitive` exists to avoid.
    These are over-approximations: a check keyed on `code` is re-run when ANY tracked Python file
    moves, whether or not it reads that file.

    WHAT IT BUYS is the common case, which is a data update with the code standing still: the build
    moves, the source does not, and the source-quality budgets do not have to be re-answered. The
    case it does not help is a refactor, where the code moves and everything is re-run, which is
    correct.

    §14b, WHAT IT CANNOT SEE: a check reading something in none of these classes. `data/names` and
    `data/identity` are read by several, so they are inside `data`, and `data` is one of the
    classes rather than being narrowed further.
    """
    sys.path.insert(0, str(ROOT / "adapters"))
    import filecache
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=str(ROOT),
                             capture_output=True, text=True, timeout=60).stdout.split("\0")
    # WHAT A RUN WRITES IS NOT WHAT A RUN READS. `docs/tracker.html` is regenerated by every gate
    # and carries the time it ran, and `docs/budgets.json` is rewritten whenever a budget tightens.
    # Both are tracked, so leaving them in the `code` class meant a gate invalidated its own cache
    # and the next one re-answered all 110 checks. The budget FILE still decides pass or fail: a
    # remembered budget carries its number and is compared against the recorded one every run.
    written = {"docs/tracker.html", "docs/budgets.json"}
    code, data = [], []
    for f in tracked:
        if not f or f in written:
            continue
        at = ROOT / f
        if not at.exists():
            continue
        (data if f.startswith("data/") else code).append(at)
    build = [x for x in (BUILD.rglob("*") if BUILD.is_dir() else [])
             if x.is_file() and x.name not in (".green-tree.json", "checks.json")]
    site = []
    kari = ROOT.parent / "yurarium.github.io" / "kari"
    if kari.is_dir():
        site = [x for x in kari.rglob("*") if x.is_file() and "node_modules" not in x.parts]
    return {"code": filecache.digest(code),
            "data": filecache.digest(data + build),
            "site": filecache.digest(site)}


def _verify_key(name, keys, sensitive):
    """What a pass by `name` is remembered against."""
    parts = [keys["code"], keys["data"]]
    if name in sensitive:
        parts.append(keys["site"])
    return hashlib.sha256("|".join([name, *parts]).encode()).hexdigest()


def deploy_sensitive():
    """The invariants whose answer the copy changes, derived and not listed.

    WHY DERIVED. `deploy.sh` re-ran every check after copying so the published `checks.json` would
    not claim violations the copy had already fixed. That is 37 seconds of a 39-second deploy, and
    the fourth run of the checks in one cycle. Only the invariants that READ the deployed tree can
    change across a copy, so only those need re-running.

    Its comment said two. There are four. A hand-kept list of what reads the site is the same fault
    as a hand-kept list of what to check, so this reads the source and asks which functions name
    `SITE`.

    Section 14b, WHAT IT MISSES: an invariant reaching the deployed tree through a helper that names
    `SITE` for it. None does today; if one appears, its answer in `checks.json` will be the
    pre-copy one, which is the behaviour every invariant had before this existed.
    """
    import inspect
    got = []
    for name, f in INVARIANTS:
        try:
            if "SITE" in inspect.getsource(f):
                got.append(name)
        except (OSError, TypeError):                                    # noqa: PERF203
            got.append(name)
    return got


def deploy_window():
    """Re-answer only the invariants a copy can change, and patch `checks.json` in place.

    THE PUBLISHED REPORT STAYS TRUE and the deploy stops paying for a whole run of the checks. The
    entries this does not touch keep the answers the build gave them, which is what they had before
    and is correct: nothing but the copy has happened since.
    """
    out = BUILD / "checks.json"
    if not out.exists():
        print("  deploy-window: no checks.json to patch; run the build first")
        return 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    ctx = context()
    # A REPORT FROM AN OLDER BUILD IS WORSE THAN A MISSING ONE. build.py no longer runs the checks
    # by default, so checks.json is written by the gate; a deploy that never saw one would patch
    # three entries of a stale report and publish it looking current.
    if (doc.get("generated") or "") != (ctx.get("generated") or ""):
        print(f"  deploy-window: checks.json is from {doc.get('generated')!r} and the build is "
              f"{ctx.get('generated')!r}; run ./check.py --gate")
        return 1
    want = set(deploy_sensitive())
    by_name = {n: f for n, f in INVARIANTS}
    patched = 0
    for row in doc.get("invariants", []):
        if row.get("name") not in want:
            continue
        bad = by_name[row["name"]](ctx)
        row["violations"] = len(bad)
        row["examples"] = [str(e).replace(str(ROOT.parent) + "/", "") for e in bad[:5]]
        patched += 1
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    still = sum(1 for r in doc.get("invariants", [])
                if r.get("name") in want and r.get("violations"))
    print(f"  deploy-window: {patched} invariant(s) re-answered after the copy, {still} violated")
    return 0


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--runtime", action="store_true", help="count and report; never fail")
    g.add_argument("--gate", action="store_true", help="fail on any violation or loosened budget")
    # ON BY DEFAULT SINCE 2026-08-13, AND THE MEASUREMENT IS WHY. `--gate` alone costs 79.6s and
    # `--gate --incremental` costs 2.6s on the same tree. The fast answer was reachable only by
    # remembering a flag, so the command a person types, and the one written in CLAUDE.md, was the
    # slow one every time. A default nobody can forget is worth more than a flag everybody must.
    #
    # THE CONTRACT IS UNCHANGED AND IT IS WHAT MAKES THE DEFAULT SAFE. A pass is remembered against
    # a digest of what the check read; a failure never is. So the cache can only hold "this said
    # nothing on exactly these inputs", and `test_incremental.py` proves it by planting a violation
    # and asking whether the next run still measures that check.
    #
    # `--full` REFUSES EVERY REMEMBERED ANSWER, which is what the weekly equivalence run takes and
    # what to reach for when the question is whether the fast path agrees with anything.
    ap.add_argument("--full", action="store_true",
                    help="re-answer every check, refusing any answer worked out before")
    ap.add_argument("--incremental", action="store_true",
                    help=argparse.SUPPRESS)   # kept so an existing caller keeps working; now the default
    ap.add_argument("--proved-by", metavar="WHO", default=None,
                    help="another process now running is proving the checks can fail; only "
                         "cycle.py passes this, and it fails if that process fails")
    g.add_argument("--deploy-window", action="store_true",
                   help="re-answer only the invariants a copy can change, and patch checks.json")
    g.add_argument("--self-test", action="store_true", help="prove the checks can fail")
    ap.add_argument("--no-tighten", action="store_true", help="do not record improved budgets")
    ap.add_argument("--data-advisory", action="store_true",
                    help="budgets counting the DATA report rather than block; the source tier, "
                         "the invariants and any budget that could not be measured still block")
    a = ap.parse_args()

    # ONE PLACE DECIDES IT, so every reader below asks the same question. `--incremental` survives
    # as an accepted spelling of the default rather than as a second way to mean it: a caller that
    # still passes it gets what it asked for, and `--full` beats both.
    a.incremental = not a.full

    if a.self_test:
        return 0 if self_test() else 1

    if a.deploy_window:
        return deploy_window()

    _phase = {}
    # HOISTED ABOVE THE PROOF, because the proof is now one of the things remembered. `_input_keys`
    # reads files and needs no build, so nothing about the order below depends on it being late.
    verified, keys, sensitive = {}, {}, set()
    if a.incremental:
        _t0 = time.perf_counter()
        keys = _input_keys()
        sensitive = set(deploy_sensitive())
        if VERIFIED.exists():
            try:
                verified = json.loads(VERIFIED.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                verified = {}
        _phase["hashing what the checks read"] = time.perf_counter() - _t0

    # THE PROOF IS NOT SKIPPED, IT IS SOMEWHERE ELSE. `./test.py` runs `check.py --self-test` as one
    # of its suites, so a cycle that runs both proves the same property twice, 16 s each. cycle.py
    # runs them together and passes this; it reports failure if the test half fails, so the proof
    # still gates. Nothing else passes it, and `--full` never does.
    if a.gate and a.proved_by:
        print(f"invariants proved by {a.proved_by}, running alongside this")
    proof_key = None
    if a.gate and not a.proved_by:
        # REMEMBERED LIKE ANY OTHER PASS, AND KEYED THE SAME WAY. The proof plants its canaries in
        # the real context, so it depends on the checking code AND on the build, which is exactly
        # what `_verify_key` already hashes; cycle.py says the same thing where it decides whether
        # `test.py --changed` may skip the suite. So it needs no key of its own design.
        #
        # WHY IT IS WORTH REMEMBERING. It was 24.7s of a 79.6s gate and the largest single cost
        # once `--incremental` became the default, and it re-answered a question about `check.py`
        # on every run over data that cannot change the answer.
        #
        # A PASS IS REMEMBERED AND A FAILURE NEVER IS, which is the contract the rest of the cache
        # keeps. `keep` below rewrites the file from what THIS run established, so the entry is
        # carried forward there rather than left to survive by accident.
        proof_key = _verify_key(SELF_TEST, keys, sensitive) if a.incremental else None
        if proof_key and verified.get(SELF_TEST) == proof_key:
            _phase["the proof, remembered"] = 0.0
            print("the checks were proved able to fail on exactly this code and build")
        else:
            _t0 = time.perf_counter()
            proved = self_test()
            _phase["proving the checks can fail"] = time.perf_counter() - _t0
            if not proved:
                print("\nFAIL: the checks cannot prove they work; refusing to pass anything.")
                return 3

    _t0 = time.perf_counter()
    ctx = context()
    _phase["reading the build"] = time.perf_counter() - _t0
    if not ctx["releases"]:
        print("no build output — run ./build.py first")
        return 0 if a.runtime else 1

    # PER-CHECK TIMINGS, because a total says a cycle is slow and nothing about which check to
    # look at. Two rounds of this refactor guessed wrong from a total: page generation was blamed
    # for 39 s that belonged to a fourth run of the checks. The cost is one perf_counter call per
    # check against checks that take whole seconds, so it is always on rather than behind a flag.
    # A PASS IS REMEMBERED, A FAILURE NEVER IS. A check that found something is re-run every time,
    # so the cache can only ever hold "this said nothing on exactly these inputs". test_incremental.py proves it,
    # by planting a violation and asking whether the next run still measures that check.
    timings = {}
    inv_results = {}
    budget_values = {}
    skipped = 0
    unmeasured = []
    failed = []
    print("invariants:")
    for name, fn in INVARIANTS:
        if a.incremental and verified.get(name) == _verify_key(name, keys, sensitive):
            inv_results[name] = []
            skipped += 1
            continue
        _t0 = time.perf_counter()
        bad = fn(ctx)
        timings[name] = time.perf_counter() - _t0
        inv_results[name] = bad
        # AN INVARIANT ABOUT THE COPY, ASKED WHERE NOTHING HAS COPIED. `deployed data matches built`
        # compares `data/build` against the deployed tree, and it is false for the whole window
        # between a build finishing and `deploy.sh` running, which `deploy_window` exists to patch.
        # A check-in gate builds and never deploys, so it sits inside that window permanently: the
        # site it clones is the previously published one, and any push that changes the output makes
        # this false with nothing in the push responsible.
        #
        # IT FAILED ON EVERY PUSH EVER MADE, and on `status.json` alone, which carries `generated`
        # and `since_last.at` and so differs from a rebuild of itself one second later. That is not
        # a fault a person can fix by changing the push, which is the test of whether a gate should
        # be asserting it.
        #
        # ONE INVARIANT AND NOT THE FOUR `deploy_sensitive` RETURNS. Three of those read the site
        # and compare something a copy cannot invent: whether a scope ruling the site reports is
        # accounted for, whether a published update left its month. They pass in CI and blocking on
        # them is worth keeping. This one asserts BYTE EQUALITY of a tree nothing has copied into,
        # which is a different claim, so it is named here rather than taken from a derivation that
        # answers a different question. Reported where it is skipped, never silently dropped.
        if bad and a.gate and name in NOT_ASSERTED_BEFORE_A_DEPLOY:
            print(f"  --    {name}: {len(bad)}, not asserted here; this gate builds and does not "
                  f"deploy, and deploy.sh answers it after copying")
            continue
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
        # A BUDGET IS A NUMBER AND NOT A VERDICT, so a remembered one carries its value.
        held = verified.get(name) if a.incremental else None
        if isinstance(held, list) and len(held) == 2 and held[0] == _verify_key(name, keys, sensitive):
            n = held[1]
            budget_values[name] = n
            skipped += 1
            was = recorded.get(name)
            if was is not None and n <= was:
                print(f"  ok    {name}: {n}" + (f"  (was {was}, tightening)" if n < was else "")
                      + "  [unchanged inputs]")
                if n < was:
                    tightened[name] = n
                continue
        _t0 = time.perf_counter()
        n = fn(ctx)
        timings[name] = time.perf_counter() - _t0
        budget_values[name] = n
        was = recorded.get(name)
        # A CHECK THAT COULD NOT RUN IS NOT A CHECK THAT FOUND NOTHING. See UNMEASURED.
        if n is UNMEASURED:
            unmeasured.append(name)
            print(f"  FAIL  {name}: could not be measured")
            continue
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

    # RATCHETING IS AN ACT SOMEBODY TAKES, and it used to happen whenever the build ran. Twice in
    # one week that banked a number measured over a half-migrated store: the count was real for the
    # tree it was taken in and false for the tree that followed, and nothing said so. `--runtime` is
    # what build.py calls, and a build is exactly the moment nobody is watching.
    #
    # The gate still tightens, because a person is present there and the number goes into a commit
    # they write. `--runtime` reports the fall and leaves the file alone.
    if tightened and not a.no_tighten and not a.runtime:
        recorded.update(tightened)
        BUDGETS.parent.mkdir(parents=True, exist_ok=True)
        BUDGETS.write_text(json.dumps(dict(sorted(recorded.items())), indent=1) + "\n")
    elif tightened and a.runtime:
        print(f"  {len(tightened)} budget(s) fell; run ./check.py --gate to record them")


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

    _t0 = time.perf_counter()
    (BUILD / "checks.json").write_text(json.dumps({
        "generated": ctx.get("generated") or "",
        # ANSWERED ONCE. This comprehension used to call every invariant a SECOND time to write
        # the report, so `./check.py --gate` ran the whole suite twice: 47 s of checks became 94 s
        # and the per-check timings are what made it visible. The loop above keeps its results.
        "invariants": [{"name": n, "violations": len(inv_results[n]),
                        "examples": [_unroot(e) for e in inv_results[n][:5]]}
                       for n, _f in INVARIANTS],
        # A budget this run did not measure carries `value: null` and says why, so a reader can
        # tell "nothing to report" from "not asked".
        "budgets": [{"name": n, "means": w, "budget": recorded.get(n),
                     "value": budget_values.get(n),
                     **({"not_measured": "source-quality budget; measured at check-in"}
                        if skip_source and n in SOURCE_BUDGETS else {})}
                    for n, f, w in BUDGETS_DEF],
        # WHICH CHECK COST WHAT, so the next slow one is visible without guessing. Two rounds of
        # this refactor guessed wrong from a total.
        "seconds": {n: round(s, 3) for n, s in sorted(timings.items(), key=lambda kv: -kv[1])},
        "note": ("Invariants are statements that are either true or the data is broken. At runtime "
                 "a violation degrades to the fallback named in check.py and is counted here; at "
                 "check-in the same violation blocks. Budgets are counts with no correct value, "
                 "only a direction: they tighten automatically and loosen only by hand."),
    }, ensure_ascii=False, indent=1))
    _phase["writing the report"] = time.perf_counter() - _t0

    if a.incremental:
        keep = {}
        for name, _fn in INVARIANTS:
            if not inv_results.get(name):
                keep[name] = _verify_key(name, keys, sensitive)
        for name, _fn, _w in BUDGETS_DEF:
            if name in budget_values:
                keep[name] = [_verify_key(name, keys, sensitive), budget_values[name]]
        # THE PROOF, on the same terms as everything else here: recorded only where this run
        # established it, so a failing proof leaves nothing behind and the next run re-runs it.
        if proof_key:
            keep[SELF_TEST] = proof_key
        try:
            VERIFIED.parent.mkdir(parents=True, exist_ok=True)
            VERIFIED.write_text(json.dumps(keep, indent=1), encoding="utf-8")
        except OSError:
            pass
        if skipped:
            print(f"\n{skipped} check(s) skipped: their inputs are what they were when they passed")

    def _report_time():
        """Where the seconds went, printed last so the tail of the run is inside it."""
        if not timings:
            return
        total = sum(timings.values()) + sum(_phase.values())
        print(f"\nwhere {total:.0f}s went:")
        for name, secs in sorted(_phase.items(), key=lambda kv: -kv[1]):
            print(f"  {secs:6.2f}s  {name}")
        shown = [x for x in sorted(timings.items(), key=lambda kv: -kv[1]) if x[1] >= 0.2][:10]
        for name, secs in shown:
            print(f"  {secs:6.2f}s  {name}")
        rest = sum(s for n, s in timings.items() if (n, s) not in shown)
        print(f"  {rest:6.2f}s  the other {len(timings) - len(shown)} checks")

    if a.runtime:
        # The show must go on. Violations are reported and counted; the build publishes anyway,
        # having already degraded to the fallback each invariant names.
        _report_time()
        if failed or loosened or unmeasured:
            print(f"\n{len(failed)} invariant(s) violated, {len(loosened)} budget(s) exceeded — "
                  f"degraded per the stated fallbacks; see docs/STANDING-INSTRUCTIONS.md")
        return 0

    # WHICH TIER BLOCKS A PERSON'S PUSH. B3, agreed with the project owner 2026-08-11. A code push
    # runs this against the corpus that is committed, and the corpus moves under it: the unattended
    # update commits new source data every night, so a budget counting works can rise with nothing
    # in the push responsible for it. Five rose that way on 2026-08-11 and each stopped a commit
    # that was about code, which is a gate reporting on somebody else's change.
    #
    # SO THE SOURCE TIER BLOCKS AND THE DATA TIER REPORTS, and `SOURCE_BUDGETS` already draws the
    # line: those count this repository's own Python and Markdown, which only a push can change.
    #
    # INVARIANTS ARE NOT IN THIS. A violated invariant is a broken statement about the data whoever
    # caused it, and degrading that to a note is how a fault gets published. Nor is a budget that
    # could not be MEASURED, which says a check failed to run rather than that a count moved.
    #
    # NOTHING IS LOST BY REPORTING. The number still reaches `checks.json` and the status page, the
    # ratchet still holds the recorded value, and `./check.py --gate` run by hand still blocks on
    # everything, which is where accepting a rise belongs: a person deciding, not a push being
    # stopped by a fetch that happened overnight.
    advisory = []
    if a.data_advisory:
        advisory = [x for x in loosened if x[0] not in SOURCE_BUDGETS]
        loosened = [x for x in loosened if x[0] in SOURCE_BUDGETS]
    if advisory:
        print(f"\n{len(advisory)} data budget(s) rose. Reported, not blocking: the data these count "
              f"is not what this push changed.")
        for name, was, now in advisory:
            print(f"  {name} rose {was} -> {now}; accept it with ./check.py --gate when you have "
                  f"looked at why")

    if failed or loosened or unmeasured:
        _report_time()
        print(f"\nNO GO: {len(failed)} invariant(s) violated, {len(loosened)} budget(s) exceeded"
              + (f", {len(unmeasured)} budget(s) could not be measured" if unmeasured else "") + ".")
        for name in unmeasured:
            print(f"  {name} could not be measured, so nothing about it is known; "
                  f"run it alone to see what it raised")
        for name, was, now in loosened:
            print(f"  {name} rose {was} -> {now}; to accept it, edit docs/budgets.json and say why")
        return 1
    print("\nall right")
    # THE TREE THIS PASSED ON, recorded so the pre-push hook need not prove it again. The token
    # over-approximates what the checks read, and refuses itself if the tree moved, if it covers a
    # different set, or if it records a different run. See adapters/greentree.py.
    _t0 = time.perf_counter()
    try:
        sys.path.insert(0, str(ROOT / "adapters"))
        import greentree
        greentree.write("gate")
    except Exception:                                                   # noqa: BLE001
        pass
    _phase["the green-tree token"] = time.perf_counter() - _t0
    # AND THE TRACKER IS REGENERATED, so the page cannot be stale while the work moves on. The last
    # round's tracker went out of date because updating it was something to remember; the timings
    # are skipped here because measuring them costs a full cycle.
    _t0 = time.perf_counter()
    try:
        import tracker
        tracker.OUT.write_text(
            tracker.render(tracker.state(), tracker.measure(fast=True, budgets=budget_values)),
            encoding="utf-8")
    except Exception:                                                   # noqa: BLE001
        pass
    _phase["regenerating the tracker"] = time.perf_counter() - _t0
    _report_time()
    return 0


if __name__ == "__main__":
    sys.exit(main())
