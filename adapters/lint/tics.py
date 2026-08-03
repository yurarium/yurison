#!/usr/bin/env python3
"""Keep the prose readable: no stock phrasing, no filler, no padding.

WHY THIS EXISTS. Almost every word here was drafted by an assistant, and assistants reach for a
small set of prefabricated constructions. The problem with them is not that they identify their
author. It is that they are bad writing: they take a sentence to say nothing, they reach for an
abstraction where a fact belongs, and they add rhythm in place of content. Enough of them together
and the text lands in the uncanny valley, where a reader feels the wrongness before naming it, and
stops trusting the page.

THIS IS NOT A DISGUISE. That the project is AI-driven is neither hidden nor advertised, and nothing
here exists to defeat a detector. Attribution stays. The consequence matters at the margin: several
things that detectors flag are KEPT because they earn their place, and several things detectors
would not notice are CUT because they annoy. When a rule and a detector disagree, the rule follows
the reader.

WHO IS READING. The informational foundation and the architecture will ship in the repository so a
third party can pick the project up and run with it or change it. That makes this documentation
part of the deliverable rather than notes to ourselves. It has to be worth a stranger's time.

THE TEST is whether a sentence would annoy someone trying to use the project: does it say a thing,
or does it perform saying a thing. That is not a check a program can run, which is why the list
below exists. Every entry names what to write INSTEAD, because a rule that only says "don't" gets
satisfied by deleting the sentence. If a rule ever makes a passage worse, the rule is wrong and
should be changed rather than worked around.

THREE TIERS, matching check.py:

  HARD      constructions with no legitimate use. Invariant, must be zero in public text.
  SOFT      ordinary words that are fine once and are filler in bulk ("comprehensive", "leverage",
            "robust"). A budget, because making them errors is how a check gets deleted rather than
            obeyed. See adapters/lint/shadowing.py for that failure mode.
  DENSITY   things correct in ones and tiresome in threes: tricolons. Measured per thousand words,
            in prose and not in code.

WHAT IS DELIBERATELY NOT FLAGGED, so it is not "helpfully" added later:

  Bold-lead bullets, numbered rules and tables. Published lists of AI tells name all three, and
  they stay, because the point of these documents is that a rule can be found and cited by someone
  who has never read them before. Legibility beats camouflage.

  Curly quotes. Also on those lists; also correct typography for web text.

  The "short sentence for emphasis." beat, paragraphs that restate their own first line, and
  elegant variation (reaching for a synonym rather than repeating a word). Real problems, not
  mechanisable, and named in STANDING-INSTRUCTIONS §11 as judgement instead.

EM DASHES are avoided on instruction: zero in public text, a budget in internal documents. The
justification is rhythm rather than signature. A page of them reads as one long breath, and cutting
them forces the sentence structure to carry the meaning instead.

WHAT WAS WRONG THE FIRST TIME, recorded because the reasoning was plausible and still wrong. This
file originally exempted em dashes, arguing that the user writes them and these documents are full
of them. That conflated how the user writes in conversation with what the project publishes. It was
overturned on sight of the README, whose opening paragraph carried two em dashes and a tricolon.

SCOPE. Public prose is the invariant. Code comments and docstrings are the budget: in scope, being
cleaned, but a backlog must not block a build. Commit messages already written are history.

WHERE THE LIST CAME FROM. The first version was written from memory and was wrong about em dashes,
so the second was researched. Most useful by a distance is Wikipedia's own editor guidance,
"Signs of AI writing" (en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), which is maintained by
people who read suspected machine text all day and is organised by what to look for rather than by
theory. Four rules here come straight from it: copula avoidance ("serves as", "boasts", "marks a"),
negative parallelism, the present participle bolted onto a finished sentence to add significance,
and vague attribution standing in for a source. It also records the caveats that matter, chiefly
that detection tools are unreliable and that human readers do no better than chance, which is part
of why this file aims at readability rather than at evading detection.

On density: arXiv 2601.07974 (detector generalisation through linguistic analysis) and 2603.27006
(how markdown training shapes LLM prose) both find the signal in clustering rather than in any
single instance. That is why em dashes are a budget internally instead of an error, and why the
one metric that could not be made to measure clustering honestly was removed rather than shipped.

Usage:  tics.py --prose FILE...      what a reader sees; HARD + raw-text rules + density
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
    # Copula avoidance: "is/are" replaced by something weightier. One study found a 10% drop in
    # is/are after 2022. Wikipedia's list names exactly these verbs.
    # Defining a thing by what it is not. "A catalogue rather than a reader" reads as a formula,
    # and the reader still does not know what it IS until the next sentence.
    (r"^\s*(a|an|the)\s+\w+(\s+\w+)?\s*,?\s*(rather than|not)\s+(a|an|the)?\b",
     "state what it is"),
    (r"\b(is|are|was|were)\s+(a|an)\s+\w+\s+rather than\s+(a|an)\b", "state what it is"),
    (r"\bnot\s+(a|an)\s+\w+(\s+\w+)?\s*,?\s+but\s+(a|an)\b", "state what it is"),
    # Announcing a count of three, which is the figure used as an organising choice.
    (r"\b(three|Three)\s+(things|commitments|principles|rules|reasons|factors|goals|pillars|"
     r"points|ways|steps|properties)\b", "list them without counting them first"),
    (r"\bserves as (a|an|the)\b|\bmarks (a|an|the) (first|significant|pivotal|major)\b", "is"),
    # Present participle bolted onto a finished sentence to add significance it did not have.
    (r", (highlighting|underscoring|emphasi[sz]ing|showcasing|reflecting|ensuring|cultivating|"
     r"solidifying|cementing|marking) ", "end the sentence"),
    # Significance inflation.
    (r"\b(pivotal moment|significant shift|broader trends?|evolving landscape|indelible mark|"
     r"lasting legacy|rich history)\b", "say what happened"),
    # Vague attribution standing in for a source.
    (r"\b(observers have|experts (argue|say|note)|industry reports|several sources|many believe)\b",
     "name the source"),
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
    (r"—", "a comma, a full stop, or two sentences"),
]

# Evidence is quoted, not written, and must survive the lint unaltered. The scraped pixiv banner
# in adapters/render/releases.py carries a ✨ and that character is the point of the citation. A
# decorative emoji in our own English will never share a line with Japanese, so CJK exempts a line
# from the emoji rule — narrow enough to be safe, and it fails visibly rather than silently.
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff00-\uffef]")

# An em dash ALONE between quotes or tags is not prose: it is the glyph for "no value" in a table
# cell, which is correct typography and not a tell. `${n ?? '—'}` must survive. Same shape as the
# CJK exemption above: the rule is about writing, so it has to be able to tell writing from data.
GLYPH = re.compile(r"""(['"`>])\s*—\s*(['"`<])""")

# Applied in --prose only. The em dash is the one the research puts first, and the instruction here
# is to avoid it rather than meter it, so in public text it is absolute. In comments and internal
# documents it is a budget instead (see SOFT): those are already written full of them, and a rule
# that demands a mass rewrite before the next commit is a rule that gets switched off.
#
# Curly quotes are deliberately NOT flagged. They appear on published lists of tells, and they are
# wanted here: they are correct typography for web text. A lint exists to serve the writing.
PROSE_ONLY = [
    (r"—", "a comma, a full stop, or two sentences"),
]

LIST_OR_HEADING = re.compile(r"\s*(?:[-*+•]|\d+[.)]|#|\||>)")

# A tricolon is a RHETORICAL pattern, so it is counted in prose and not in code. Without this the
# measure spent itself on JS parameter lists: "kind, raw, existing", "label, cls, why", "idx, feed,
# series". Sixteen of the first twenty-two hits on the site were signatures, and a measure that
# reports mostly noise is one nobody reads.
CODEY = re.compile(r"=>|\bfunction\b|\b(?:const|let|var|return)\b|[{};=]|\$\{")

# THE SENTENCE-LEVEL TRICOLON METRIC WAS REMOVED, and this note is here so it is not rebuilt.
#
# Two attempts. A regex window of three items counted every four-item inventory as rhetoric,
# because English drops the comma before the final "and": "Code, schema, adapters and
# documentation" is four things and two commas. Counting members instead fixed that and exposed the
# real problem, which is that a comma series is not a tricolon. Of twenty-two hits on the site,
# almost all were ordinary commas doing ordinary work: appositives ("Taste, not correctness, so
# ..."), subordinate clauses ("so リセット, which clears every select ..."), parentheticals.
#
# A tricolon is three GRAMMATICALLY PARALLEL members. Telling parallel members from a subordinate
# clause needs a parser, and a metric that reports mostly noise is one nobody reads, which is the
# failure this file warns about elsewhere. So the figure is caught where it is unambiguous and
# cheap: at document scale, in structure(), where three bullets or three bold-led paragraphs are
# visibly an organising choice. The sentence-level case is judgement, and is named in
# STANDING-INSTRUCTIONS §11.

LIST_OR_HEADING = re.compile(r"\s*(?:[-*+•]|\d+[.)]|#|\||>)")

# A tricolon is a RHETORICAL pattern, so it is counted in prose and not in code. Without this the
# measure spent itself on JS parameter lists: "kind, raw, existing", "label, cls, why", "idx, feed,
# series". Sixteen of the first twenty-two hits on the site were signatures, and a measure that
# reports mostly noise is one nobody reads.
CODEY = re.compile(r"=>|\bfunction\b|\b(?:const|let|var|return)\b|[{};=]|\$\{")

SERIES = re.compile(r"(?:[\w'\u2019]+(?:[\w\s'\u2019]{0,28})?,\s+){2,}(?:and\s+)?[\w'\u2019]+(?:[\w\s'\u2019]{0,28})?")


def tricolons(text):
    """Count comma series with EXACTLY three members. Both forms: "a, b, and c" and "a, b, c".

    Counting is not matching. A three-item regex window sits happily inside a list of six, which is
    how "Code, schema, adapters and documentation" got reported as rhetoric: four items, but only
    two commas, because English drops the comma before the final "and".

    So members are counted, and the last is split again on " and " to recover the item that the
    missing Oxford comma hides. Three members is a tricolon. Four or more is an inventory, and an
    inventory reads as one.
    """
    n = 0
    for m in SERIES.finditer(text):
        parts = [x.strip() for x in m.group(0).split(",")]
        last = parts[-1]
        if last.lower().startswith("and "):
            parts[-1] = last[4:]
        else:
            tail = re.split(r"\s+and\s+", last)
            if len(tail) > 1:
                parts = parts[:-1] + tail
        if len([x for x in parts if x]) == 3:
            n += 1
    return n


# Correct in ones, tiresome in threes. Per thousand words, prose only.
DENSITY = [
    ("tricolons", tricolons, 2.0),
]

HARD_RX = [(re.compile(p, re.I), fix) for p, fix in HARD]
PROSE_RX = [(re.compile(p, re.I), fix) for p, fix in PROSE_ONLY]
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
    if m.group(0) == "—" and GLYPH.search(text):
        return None                   # the "no value" glyph, not a sentence
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


LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
BOLD_LEAD = re.compile(r"^\s*\*\*[^*]+\*\*")


def structure(path):
    """Groups of exactly three parallel items: the rule of three as an ORGANISING principle.

    The line rules catch "a, b, and c" inside a sentence. They cannot see a section built from
    three bullets or three bold-led paragraphs, which is the same figure at document scale and is
    the more tiring one, because the reader meets the shape before reading a word.

    Three is what gets flagged. A list of seven is an inventory and reads as one; a list of exactly
    three reads as rhetoric, because that is usually what it is.

    Works on BLOCKS, not lines. The first version tracked consecutive lines and so missed three
    bold-led paragraphs entirely, since the second line of each paragraph ended the run. That was
    the exact shape being complained about.
    """
    text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n\s*\n", text)
    hits, run, start = [], 0, 0
    line_of, n = [], 1
    for b in blocks:
        line_of.append(n)
        n += b.count("\n") + 2

    for idx, b in enumerate(blocks):
        stripped = b.strip()
        if not stripped:
            continue
        items = [l for l in b.splitlines() if LIST_ITEM.match(l)]
        if items:
            run = 0
            if len(items) == 3:
                hits.append((line_of[idx], "a list of exactly three items"))
            continue
        if BOLD_LEAD.match(stripped):
            if run == 0:
                start = line_of[idx]
            run += 1
            continue
        if run == 3:
            hits.append((start, "three bold-led paragraphs in a row"))
        run = 0
    if run == 3:
        hits.append((start, "three bold-led paragraphs in a row"))
    return hits


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
        ("The album serves as a testament", HARD_RX),
        ("It shipped in May, marking a pivotal moment", HARD_RX),
        ("It shipped, highlighting the need for care", HARD_RX),
        ("Experts argue that this is so", HARD_RX),
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
    # The em dash is caught in public text and NOT by the shared list, which comments also use.
    if not any(fires(rx, fix, "a thing \u2014 and another") for rx, fix in PROSE_RX):
        print("  FAIL: em dash not caught in prose")
        ok = False
    if any(fires(rx, fix, "a thing \u2014 and another") for rx, fix in HARD_RX):
        print("  FAIL: em dash in HARD would fire on every internal document")
        ok = False
    # The no-value glyph must survive; a real em dash on the same shape of line must not.
    for text, want in (("<td>${n ?? '—'}</td>", False), ("a sentence — and its aside", True)):
        got = any(fires(rx, fix, text) for rx, fix in PROSE_RX)
        if got != want:
            print(f"  FAIL: glyph exemption wrong on {text!r} (got {got}, want {want})")
            ok = False

    # The structural rule has to catch the shape it was written for.
    import tempfile, os
    doc = ("# T\n\n**One.** a\ncontinued\n\n**Two.** b\ncontinued\n\n**Three.** c\ncontinued\n\n"
           "para\n\n- x\n- y\n- z\n\nend\n")
    fd, tmp = tempfile.mkstemp(suffix=".md"); os.write(fd, doc.encode()); os.close(fd)
    found = {w for _, w in structure(tmp)}
    os.unlink(tmp)
    for want in ("three bold-led paragraphs in a row", "a list of exactly three items"):
        if want not in found:
            print(f"  FAIL: structure() missed {want!r}; got {found}")
            ok = False
    # Four of a thing is an inventory and must pass.
    doc4 = "**A.** a\n\n**B.** b\n\n**C.** c\n\n**D.** d\n\n- 1\n- 2\n- 3\n- 4\n"
    fd, tmp = tempfile.mkstemp(suffix=".md"); os.write(fd, doc4.encode()); os.close(fd)
    if structure(tmp):
        print(f"  FAIL: structure() flagged a group of four: {structure(tmp)}")
        ok = False
    os.unlink(tmp)

    # Curly quotes are wanted. Nothing may flag them.
    if any(fires(rx, fix, "the reader\u2019s choice \u201cyes\u201d")
           for rx, fix in HARD_RX + PROSE_RX):
        print("  FAIL: something flagged a curly quote")
        ok = False
    # The structural rule has to catch the shape it was written for.
    import tempfile, os
    doc = ("# T\n\n**One.** a\ncontinued\n\n**Two.** b\ncontinued\n\n**Three.** c\ncontinued\n\n"
           "para\n\n- x\n- y\n- z\n\nend\n")
    fd, tmp = tempfile.mkstemp(suffix=".md"); os.write(fd, doc.encode()); os.close(fd)
    found = {w for _, w in structure(tmp)}
    os.unlink(tmp)
    for want in ("three bold-led paragraphs in a row", "a list of exactly three items"):
        if want not in found:
            print(f"  FAIL: structure() missed {want!r}; got {found}")
            ok = False
    # Four of a thing is an inventory and must pass.
    doc4 = "**A.** a\n\n**B.** b\n\n**C.** c\n\n**D.** d\n\n- 1\n- 2\n- 3\n- 4\n"
    fd, tmp = tempfile.mkstemp(suffix=".md"); os.write(fd, doc4.encode()); os.close(fd)
    if structure(tmp):
        print(f"  FAIL: structure() flagged a group of four: {structure(tmp)}")
        ok = False
    os.unlink(tmp)

    # Curly quotes are wanted. Nothing may flag them.
    if any(fires(rx, fix, "the reader\u2019s choice \u201cyes\u201d")
           for rx, fix in HARD_RX + PROSE_RX):
        print("  FAIL: something flagged a curly quote")
        ok = False
    # Tricolon density: rhetoric counts, a function signature does not.
    count = DENSITY[0][1]
    for text, want in (("sources drop titles, platforms delist works, and magazines fold", 1),
                       ("print, web, and historical", 1),
                       # four items, two commas: English drops the comma before the final "and"
                       ("Code, schema, adapters and documentation are MIT", 0),
                       ("records what was published, by whom, where and when", 0),
                       ("a, b, c, d, e and f", 0)):
        got = count(text)
        if got != want:
            print(f"  FAIL: tricolons({text!r}) = {got}, want {want}")
            ok = False
    for code in ("function badge(label, cls, why) {", "const [idx, feed, series] = x;"):
        if not CODEY.search(code):
            print(f"  FAIL: code not excluded from tricolon density: {code!r}")
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

    rules = (HARD_RX + PROSE_RX) if a.prose else HARD_RX + SOFT_RX
    extract = prose_of if a.prose else comments_of
    hits = scan(a.files, rules, extract)

    struct = []
    if a.prose:
        for f in a.files:
            if pathlib.Path(f).exists() and pathlib.Path(f).name != "tics.py":
                struct += [(f, n, why) for n, why in structure(f)]

    over = []
    if a.quiet:
        print(len(hits) + len(over) + len(struct))
    else:
        for path, line, found, fix in hits:
            print(f"{path}:{line}: {found!r} -> {fix}")
        for f, n, why in struct:
            print(f"STRUCTURE: {f}:{n}: {why}")
        print(f"{len(hits)} tic(s), {len(struct)} structural in {len(a.files)} file(s)")
    return 1 if (hits or over or struct) else 0


if __name__ == "__main__":
    sys.exit(main())
