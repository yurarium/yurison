#!/usr/bin/env python3
"""Find the verbal tics that mark text as machine-written.

WHY THIS EXISTS. Almost every word in this project's prose was drafted by an assistant, and
assistants have a house style: a small set of constructions that appear far more often in generated
text than in written English. A reader who knows the tells reads them as a signature. The project's
text should read as the project's, so the tells are removed.

This is a lint and not a matter of taste, because "write naturally" is advice nobody can act on and
a word list is. The list is deliberately in two tiers, for the same reason check.py is:

  HARD   constructions with no legitimate use here. Absolute, so an invariant: must be zero in
         anything a reader sees.
  SOFT   ordinary words that are fine once and a tell in bulk — "comprehensive", "leverage",
         "robust". A count with a direction, so a budget. Flagging these as errors would make the
         check something to be deleted rather than obeyed, which is the failure mode recorded in
         adapters/lint/shadowing.py.

WHAT IS DELIBERATELY NOT FLAGGED, so it is not "helpfully" added later:

  Em dashes. They are the best-known tell and they would be the wrong rule here — the user writes
  them, this project's documents use them throughout on purpose, and a rule that fires on every
  page of correct prose teaches everyone to ignore the tool.

  Bold-lead bullets and numbered rules. Also a tell in the wild, also load-bearing in these
  documents, where the whole point is that a rule can be found and cited.

  Rule-of-three escalation, the "short sentence for emphasis." beat, and paragraphs that restate
  their own first line. These are real and are the residue this cannot catch; they are a matter of
  judgement and are named in STANDING-INSTRUCTIONS §11 instead.

SCOPE. Public-facing prose is the invariant. Code comments and docstrings are the budget: they are
in scope and are being cleaned, but there is a backlog and a backlog must not block a build. Commit
messages already written are history and are left alone.

Usage:  tics.py --prose FILE...      what a reader sees; reports HARD only
        tics.py --comments FILE...   comments, docstrings and .md; reports HARD + SOFT
        tics.py --self-test          prove it catches its own canary
Exit 1 if anything is found, so it can gate.
"""
import argparse, ast, io, pathlib, re, sys, tokenize

# ── The list ──────────────────────────────────────────────────────────────────────────────────
#
# Each entry is (pattern, what to write instead). The second field is not decoration: a lint that
# says "don't" and not "instead" gets satisfied by deleting the sentence.

HARD = [
    (r"\bit'?s not (just|merely|only)\b.{0,60}?\bit'?s\b", "say what it is, once"),
    (r"\bnot (just|merely|simply)\b[^.]{0,40}\bbut (also )?\b", "say what it is, once"),
    (r"\bit'?s (important|worth) (to )?not(e|ing)\b", "state the thing; the reader decides if it matters"),
    (r"\bit should be noted\b", "state the thing"),
    (r"\bin today'?s\b|\bever-(evolving|changing|growing)\b|\bfast-paced world\b", "cut"),
    (r"\bdelv(e|es|ing) into\b", "examines, or cut"),
    (r"\b(rich )?tapestry\b", "cut"),
    (r"\btreasure trove\b|\bhidden gem\b", "name the thing"),
    (r"\ba testament to\b", "shows, or cut"),
    (r"\bat its core\b", "cut"),
    (r"\bdiv(e|es|ing) into the world\b|\blet'?s dive in\b", "cut"),
    (r"\bembark(ing|s)? on\b", "start"),
    (r"\bnavigating the (complexit|landscape|challeng|world)", "name the difficulty"),
    (r"\bunlock(ing)? the\b|\bunleash(ing)? the\b", "say what it does"),
    (r"\bgame[- ]chang(er|ing)\b|\brevolutioni[sz]", "say what changed"),
    (r"\bcutting[- ]edge\b|\bstate[- ]of[- ]the[- ]art\b", "cut, or name the version"),
    (r"\bseamlessly\b", "cut"),
    (r"\bin conclusion\b", "cut; stop instead"),
    (r"\bthe world of\b|\bthe realm of\b", "cut"),
    (r"\bwhen it comes to\b", "for, or in"),
    (r"\bplays a (crucial|vital|key|pivotal|significant) role\b", "say what it does"),
    (r"\ba (myriad|plethora) of\b", "many, or the number"),
    (r"\bmeticulously\b", "cut"),
    (r"\bshed(s|ding)? light on\b", "shows"),
    (r"\bunderscor(e|es|ing) the (importance|need|value)\b", "say why it matters"),
    (r"\bboasts? (a|an|the)\b", "has"),
    (r"\bstands? as (a|an|the)\b", "is"),
    (r"\bwhether you'?re\b|\bwhether you are a\b", "cut"),
    (r"\bfrom .{3,30} to .{3,30}, (the|this|it|we)\b", "cut the sweep; start at the point"),
    (r"[\U0001F300-\U0001FAFF✨⭐⚡]", "no decorative emoji"),  # not on CJK lines: see EVIDENCE
]

SOFT = [
    (r"\b(moreover|furthermore|additionally)\b", "and, or a new sentence"),
    (r"\bleverag(es|ing)\b|\bto leverage\b|\bleverage (the|a|an|our|its|their|existing)\b", "use"),
    (r"\butili[sz](e|es|ing)\b", "use"),
    (r"\brobust\b", "say what it withstands"),
    (r"\bseamless\b", "cut"),
    (r"\bcomprehensive\b", "complete, or say of what"),
    (r"\bholistic\b", "cut"),
    (r"\bvibrant\b|\bbustling\b", "cut"),
    (r"\b(intricate|nuanced)\b", "say what the distinction is"),
    (r"\bpivotal\b", "say what turned on it"),
    (r"\bfoster(s|ing)?\b", "cause, help, or build"),
    (r"\belevat(e|es|ing)\b", "improve, or say how"),
    (r"\bempower(s|ing)?\b", "let, or enable"),
    (r"\bshowcas(e|es|ing)\b", "show"),
    (r"\bspearhead", "lead"),
    (r"\bstreamlin(e|es|ing)\b", "simplify, or say what was removed"),
    (r"\bfacilitat(e|es|ing)\b", "help, or let"),
    (r"\bdelve", "cut"),
    (r"\brealm\b", "area, or field"),
    (r"\blandscape\b", "cut, unless literally terrain"),
    (r"\bcrucial\b", "say what fails without it"),
    (r"\bis key\b|\bkey to (understanding|unlocking|success)\b|\ba key (part|role|component|aspect)\b", "say what it does"),
    (r"\bwealth of\b", "many, or the number"),
    (r"\bin the ever\b", "cut"),
]

# Evidence is quoted, not written, and must survive the lint unaltered. The scraped pixiv banner
# in adapters/render/releases.py carries a ✨ and that character is the point of the citation. A
# decorative emoji in our own English will never share a line with Japanese, so CJK exempts a line
# from the emoji rule — narrow enough to be safe, and it fails visibly rather than silently.
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff00-\uffef]")

HARD_RX = [(re.compile(p, re.I), fix) for p, fix in HARD]
SOFT_RX = [(re.compile(p, re.I), fix) for p, fix in SOFT]


def fires(rx, fix, text):
    """Whether a rule fires on a line — the single place that decides it.

    Both the scan and the self-test go through here. Keeping the exemption inside scan() and
    testing the raw patterns is the two-producers-of-one-fact shape (STANDING-INSTRUCTIONS §3):
    the first version of this file did exactly that and the self-test disagreed with the tool.
    """
    text = text.translate(SMART)
    m = rx.search(text)
    if not m:
        return None
    if fix.startswith("no decorative") and CJK.search(text):
        return None                   # quoted source data, not our prose
    return m.group(0).strip()


# ── Extracting the text that counts ───────────────────────────────────────────────────────────

STYLE = re.compile(r"<style\b.*?</style>", re.S | re.I)
COMMENT = re.compile(r"<!--|-->")
TAG = re.compile(r"<[^>]+>")

# Typographic apostrophes and quotes are folded before matching. This is not cosmetic: generated
# text overwhelmingly uses the curly apostrophe, so `it'?s` matched none of the phrases it exists
# to catch. A fire-drill found it — the invariant was passing because it could not see the string.
SMART = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u2010": "-",
                       "\u2011": "-", "\u00a0": " "})


def prose_of(path):
    """Yield (line, text) for text a reader could see.

    CSS is dropped outright — `grid`, `key`, `landscape` all live there and none of it is prose.
    Script blocks are kept, because the interface's English strings are JS string literals; the
    word list is prose-specific enough that identifiers do not collide.
    """
    raw = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    if path.suffix in (".html", ".htm"):
        raw = STYLE.sub(lambda m: "\n" * m.group(0).count("\n"), raw)
        # Unwrap comment delimiters BEFORE stripping tags. `<[^>]+>` swallows a whole HTML comment,
        # which is how a planted canary went unnoticed; the text inside one is still ours and is
        # still served.
        raw = COMMENT.sub(" ", raw)
        raw = TAG.sub(" ", raw)
    for i, line in enumerate(raw.splitlines(), 1):
        yield i, line


def comments_of(path):
    """Yield (line, text) for comments, docstrings and markdown body."""
    raw = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".md":
        for i, line in enumerate(raw.splitlines(), 1):
            yield i, line
        return
    if path.suffix != ".py":
        return
    try:
        for tok in tokenize.generate_tokens(io.StringIO(raw).readline):
            if tok.type == tokenize.COMMENT:
                yield tok.start[0], tok.string
    except (tokenize.TokenError, IndentationError):
        pass
    try:
        tree = ast.parse(raw)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if not doc:
                continue
            base = getattr(node, "lineno", 1)
            for off, line in enumerate(doc.splitlines()):
                yield base + off, line


def scan(paths, rules, extract):
    hits = []
    for p in paths:
        p = pathlib.Path(p)
        if not p.exists() or p.name == "tics.py":
            continue                  # a list of the words must contain the words
        for line, text in extract(p):
            for rx, fix in rules:
                found = fires(rx, fix, text)
                if found:
                    hits.append((str(p), line, found, fix))
    return hits


def self_test():
    """A clean report has to mean the check ran, not that it found nothing to run on."""
    canaries = [
        ("it's not just a database, it's a record", HARD_RX),
        ("delving into the rich tapestry of the genre", HARD_RX),
        ("It's important to note that this is cached.", HARD_RX),
        ("a comprehensive and robust solution", SOFT_RX),
        # All three placements a fire-drill tried. Two were missed by the first version: an HTML
        # comment (eaten by the tag stripper) and a JS string using a curly apostrophe.
        ("It\u2019s important to note that this is cached.", HARD_RX),
        ("<!-- delves into the rich tapestry -->", HARD_RX),
    ]
    ok = True
    for text, rules in canaries:
        if not any(fires(rx, fix, text) for rx, fix in rules):
            print(f"  FAIL: canary not caught: {text!r}")
            ok = False
    # The counter-case matters more than the canary: prose that must NOT fire.
    for text in ("The em dash — used throughout — is deliberate.",
                 "A key is a folded string.",
                 "it keeps one key in one place",                 # not "key to understanding"
                 "the long tail offered no leverage",             # the noun, not the verb
                 'a chapter called "300話以上✨】無料で"',          # quoted evidence, not our prose
                 "grid-template-columns: 1fr;",
                 "Absence is a state, not a missing value."):
        hit = [rx.pattern for rx, fix in HARD_RX if fires(rx, fix, text)]
        if hit:
            print(f"  FAIL: false positive on {text!r} from {hit}")
            ok = False
    print("  tics self-test:", "pass" if ok else "FAIL")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--prose", action="store_true", help="reader-facing text; HARD only")
    ap.add_argument("--comments", action="store_true", help="comments and docs; HARD + SOFT")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="print the count only")
    a = ap.parse_args()

    if a.self_test:
        return 0 if self_test() else 1

    rules = HARD_RX if a.prose else HARD_RX + SOFT_RX
    extract = prose_of if a.prose else comments_of
    hits = scan(a.files, rules, extract)

    if a.quiet:
        print(len(hits))
    else:
        for path, line, found, fix in hits:
            print(f"{path}:{line}: {found!r} — {fix}")
        print(f"{len(hits)} tic(s) in {len(a.files)} file(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
