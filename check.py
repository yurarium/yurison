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
import argparse, json, os, pathlib, re, subprocess, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent
BUILD = ROOT / "data" / "build"
NAMES = ROOT / "data" / "names"
BUDGETS = ROOT / "docs" / "budgets.json"
# Derived, not written out: the site repo sits beside this one. See adapters/paths.py.
SITE_ROOT = pathlib.Path(os.environ.get("YURARIUM_SITE") or ROOT.parent / "yurarium.github.io")
SITE = SITE_ROOT / "kari" / "data"

# Every file a reader can load. The English strings live inside the pages rather than in a
# resource file, so the pages themselves are the text; there is nowhere else to look.
READER_TEXT = [SITE_ROOT / "index.html", SITE_ROOT / "README.md",
               SITE_ROOT / "kari" / "index.html", SITE_ROOT / "kari" / "status.html"]

JAPANESE = re.compile(r"[぀-ヿ一-鿿　-〿＀-￯]")
KANA = re.compile(r"^[぀-ヿ\s・ー]*$")


def _load(p, default=None):
    try:
        return json.loads(pathlib.Path(p).read_text())
    except Exception:
        return default


def _yaml(p, default=None):
    try:
        import yaml
        return yaml.safe_load(pathlib.Path(p).read_text())
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
        flat = kana.to_hiragana(rd).replace(" ", "")
        got = "".join(x[1] or kana.to_hiragana(x[0]) for x in rb).replace(" ", "")
        if got != flat:
            bad.append(r["work"])
    return bad


def inv_no_ruby_over_latin(ctx):
    """Furigana over "M" is not furigana — Sudachi reads M as メートル, metre.

    A single letter may keep the reading that is its own NAME (V in Vチューバー is ブイ).
    fallback: emit the run bare, with no reading.
    """
    sys.path.insert(0, str(ROOT / "adapters" / "names"))
    try:
        import kana, pass4_analyser as p4
    except Exception:
        return []
    bad = []
    for kind in ("titles", "authors"):
        for k, v in (ctx["names"].get(kind) or {}).items():
            for t, rd in (v.get("furigana_spans") or []):
                if not (rd and t and all(c.isascii() for c in t)):
                    continue
                nm = p4.LETTER_NAME.get(t.upper()) if len(t) == 1 else None
                if nm and kana.to_hiragana(nm) == rd:
                    continue
                bad.append(f"{k}: {t}->{rd}")
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
            for run in re.findall(r"[A-Za-z]{2,}", rd):
                if run.lower() not in k.lower():
                    bad.append(f"{kind}:{k[:20]}={rd[:24]}")
                    break
    return bad


def inv_english_mode_has_no_japanese(ctx):
    """English-only mode shows no kanji, kana or full-width characters.

    Checked against the join the interface actually performs — the names file keyed by folded
    string — rather than against the store, because the store legitimately holds the Japanese.
    fallback: show the Japanese (§6), which is a finished state rather than a failure.
    """
    n = ctx["names_shipped"]
    if not n:
        return []
    T, A, P = n.get("titles", {}), n.get("authors", {}), n.get("phrases", {})

    def fold(t):
        return unicodedata.normalize("NFKC", t or "").replace(" ", "")

    def render(kind, raw):
        k = fold(raw)
        if kind in ("work", "author"):
            r = (T if kind == "work" else A).get(k)
            if r and (r.get("en") or (r.get("romaji") or {}).get("macron")):
                return r.get("en") or r["romaji"]["macron"]
        return P.get(k, raw)

    bad = []
    for r in ctx["releases"]:
        for kind, val in (("work", r.get("work")), ("author", (r.get("author") or "").strip()),
                          ("p", r.get("ep")), ("p", r.get("collection"))):
            if val and JAPANESE.search(render(kind, val)):
                bad.append(f"{kind}:{val[:24]}")
    return sorted(set(bad))


def inv_no_machine_tells_in_reader_text(ctx):
    """Nothing a reader sees carries the verbal tics of generated text.

    Almost all of this project's prose was drafted by an assistant, and assistants have a house
    style. A reader who knows the tells reads them as a signature, so they are removed. Only the
    HARD list is checked here — constructions with no legitimate use — because the invariant is an
    absolute statement. The ordinary words that are a tell only in bulk are a budget instead.

    fallback: none needed. This reads files that are already written; it cannot degrade a build.
    """
    out = subprocess.run(
        [sys.executable, str(ROOT / "adapters" / "lint" / "tics.py"), "--prose",
         *[str(f) for f in READER_TEXT if f.exists()]],
        capture_output=True, text=True, timeout=60)
    return [l.split(" — ")[0].strip() for l in out.stdout.splitlines() if " — " in l]


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
    works = _load(BUILD / "works.json", []) or []
    works = works.get("works") if isinstance(works, dict) else works

    def nm(x):
        t = x.get("title")
        return (t.get("ja") if isinstance(t, dict) else t) or ""

    def norm(t):
        return re.sub(r"[\s　・･!！?？…‥、。,.\-–—〜~\"'’“”()（）\[\]【】]", "", (t or "").lower())

    print_titles = {norm(nm(x)) for x in works}
    return [t["work"] for t in refuted if norm(t["work"]) in print_titles]


INVARIANTS = [
    ("ruby spells the reading", inv_ruby_spells_reading),
    ("no ruby over bare Latin", inv_no_ruby_over_latin),
    ("feed holds only attested rows", inv_feed_is_attested),
    ("every update has a kind", inv_no_unknown_kind),
    ("readings are stored as kana", inv_readings_are_kana),
    ("English mode has no Japanese", inv_english_mode_has_no_japanese),
    ("no machine tells in reader text", inv_no_machine_tells_in_reader_text),
    ("archives are unchanged", inv_archives_unchanged),
    ("deployed data matches built", inv_deployed_matches_built),
    ("no refutation of print serials", inv_no_refutation_of_print_serials),
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


def budget_incomplete_attested_rows(ctx):
    return sum(1 for r in ctx["releases"]
               if r.get("provenance") == "attested"
               and (not (r.get("ep") or "").strip() or not r.get("author")
                    or not r.get("access_modes")))


def budget_machine_tells_in_comments(ctx):
    try:
        files = [str(f) for f in list(ROOT.rglob("*.py")) + list(ROOT.rglob("*.md"))
                 if ".git" not in f.parts and "data" not in f.parts]
        out = subprocess.run(
            [sys.executable, str(ROOT / "adapters" / "lint" / "tics.py"), "--comments",
             "--quiet", *files], capture_output=True, text=True, timeout=120)
        return int(out.stdout.strip() or 0)
    except Exception:
        return 0


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
BUDGETS_DEF = [
    ("uncertain readings", budget_uncertain_readings,
     "readings assembled character by character because no analyser could read the word. A rise "
     "means new works whose kanji nothing can read, or a regression in the analyser passes."),
    ("works without English", budget_works_without_english,
     "works that render in Japanese in English-only mode. Should be 0; a rise means the automatic "
     "naming pass stopped covering something it used to."),
    ("incomplete attested rows", budget_incomplete_attested_rows,
     "attested releases missing a chapter name, author or access state. The classic sign of a "
     "moved CSS selector — the adapter still returns rows, just emptier ones."),
    ("machine tells in comments", budget_machine_tells_in_comments,
     "verbal tics of generated text in comments, docstrings and documentation. Reader-facing text "
     "is an invariant instead; this is the backlog, and it ratchets down. See adapters/lint/tics.py "
     "for what is deliberately not flagged."),
    ("shadowed names in build.py", budget_shadowed_names,
     "names rebound more than 300 lines from their first binding. Two shipped bugs came from this; "
     "see adapters/lint/shadowing.py for why the count is not simply falling."),
]


# ── Running ───────────────────────────────────────────────────────────────────────────────────

def context():
    releases = []
    cur = _load(BUILD / "feed" / "current.json", {})
    releases += cur.get("releases", [])
    for f in sorted((BUILD / "feed").glob("[0-9]*-[0-9]*.json")):
        releases += (_load(f, {}) or {}).get("releases", [])
    return {
        "releases": releases,
        "series": (_load(BUILD / "series.json", {}) or {}).get("series", []),
        "names": {k: ((_yaml(NAMES / f"{k}.yaml", {}) or {}).get("names") or {})
                  for k in ("titles", "authors")},
        "names_shipped": _load(BUILD / "feed" / "names.json", {}),
    }


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
        ("English mode has no Japanese", inv_english_mode_has_no_japanese,
         lambda c: c["releases"].append({"work": "カナリア", "provenance": "attested"})),
    ]
    ok = True
    for name, fn, plant in probes:
        c = copy.deepcopy(ctx)
        plant(c)
        if not fn(c):
            print(f"  self-test FAILED — '{name}' did not catch its canary")
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

    recorded = _load(BUDGETS, {}) or {}
    print("\nbudgets (ratchet down only):")
    loosened, tightened = [], {}
    for name, fn, _why in BUDGETS_DEF:
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
    (BUILD / "checks.json").write_text(json.dumps({
        "generated": ctx.get("generated") or "",
        "invariants": [{"name": n, "violations": len(v), "examples": v[:5]}
                       for n, v in [(n, f(ctx)) for n, f in INVARIANTS]],
        "budgets": [{"name": n, "value": f(ctx), "budget": recorded.get(n), "means": w}
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
