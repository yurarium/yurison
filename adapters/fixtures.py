#!/usr/bin/env python3
"""Real page markup, cut down and committed, so a parser can be tested against what it will meet.

WHY THIS EXISTS. Tests here run offline, so a parser can only be tested against markup somebody
wrote down, and until now there was nowhere shared to write it down. Every test that needed a page
invented one, and an invented page contains what its author imagined. Three faults came out of that
in one round:

  A ニコニコ漫画 pattern took `channel_slug` from a promotional sidebar banner instead of from the
  breadcrumb. The banner is on every page of the site, so all 180 works agreed on `nicomanga` and
  no count noticed. The fixture it was written against had a breadcrumb and no sidebar.

  The same pattern spelt a slug `[a-z0-9_]+`, which stops at a hyphen. ニコニコ百合姫 is
  `nico-yurihime`, so 28 works would have been filed under a channel called `nico`.

  A COMIC FUZ pass rewrote `/series/` to `/manga/` into a local variable and then fetched the
  original address. The rewrite was tested, the fetch was not, and the only reason anyone found out
  was a work missing from a capture.

Roughly thirty cache directories sit beside this repository holding real pages, 59,882 files in
`capture-cache` alone. A test may not read them: a cache is transient, and a test that depends on
one fails when somebody clears it. So a page is copied out of a cache ONCE, by hand, cut to the
blocks a parser reads, and committed here.

THE FOUR QUESTIONS THIS ANSWERS.

**Where it came from.** Every fixture carries the URL it was fetched from, the day it was fetched,
the cache entry it was cut out of, and the SHA-256 of the whole page before cutting. A fixture with
no provenance is indistinguishable from an invented one after six months, which is the problem this
exists to remove, so `check.py`'s `a fixture states where it came from` refuses a header without
those fields.

**How it stays small.** `keep` names the elements a parser reads and the rest of the page is
dropped. A ニコニコ work page is 118 KB; the six blocks its adapter reads are 3 KB. `redact` drops
values the project may not store (REQUIREMENTS §2 forbids publisher synopsis) and long strings that
carry no rule, which is what makes a COMIC FUZ payload fit.

**What stops it being cut too far.** A page reduced past the counter-case is worse than no fixture,
because it passes and proves nothing: the sidebar banner IS the ニコニコ counter-case, and a
fixture holding only the breadcrumb would have passed the broken pattern. So `capture` runs the
parser twice, once on the whole page and once on the cut, and refuses to write unless the two
agree. The callable it agreed with is recorded in the header, and `recheck` runs the comparison
again.

**What stops it going stale.** `recheck` re-derives every fixture from the cache entry it names and
reports where the answer has moved. It reads the cache rather than the network, so it costs nothing
and runs at the end of Stage A, when the caches have just been refilled. It is a REPORT and exits
0: a page that changed since 2026 is a finding worth a person's attention and not a reason to block
every commit until somebody deals with it.

THE FILE FORMAT is a YAML header, a line holding `---`, then the markup verbatim. One file, so a
fixture cannot lose its provenance by being moved, and format-agnostic, because an Atom feed and a
JSON payload need the same header and cannot share HTML's comment syntax.

WHY NOT STORE THE WHOLE PAGE. Thirty ニコニコ pages at 118 KB is a second copy of the internet in a
repository whose data files are its point, and nobody reads a 118 KB fixture, so nobody can tell it
is wrong (STANDING-INSTRUCTIONS §12).

Usage:
    fixtures.py capture nicovideo/work-kirara --url https://manga.nicovideo.jp/comic/69333 \\
        --cached-as nico/69333.html --retrieved 2026-08-01 \\
        --keep '<ul class="sg_pankuzu">' --keep '<div id="mg_official"' \\
        --agrees-with adapters/nicovideo/releases.py:parse --why 'the breadcrumb against the banner'
    fixtures.py list          what is held, and what each costs in bytes
    fixtures.py verify        offline: every header well formed, every body matching its digest
    fixtures.py recheck       re-derive from the caches and report where a page has moved
"""
import argparse
import datetime
import difflib
import hashlib
import importlib.util
import json
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paths  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "fixtures"
SEP = "---"

# Fields a fixture may not be without. `why` is here for the same reason as the rest: a cut nobody
# explained is a cut nobody can judge, and the sidebar in the ニコニコ fixtures looks like padding
# until its line says it is the counter-case.
REQUIRED = ("url", "retrieved", "captured", "keep", "why", "source_sha256", "source_bytes",
            "body_sha256")

VOID = {"br", "hr", "img", "input", "meta", "link", "source", "col", "area", "base", "embed",
        "param", "track", "wbr"}


# ── reading ───────────────────────────────────────────────────────────────────────────────────

def path_of(name):
    return DIR / f"{name}.fixture"


def read(name):
    """`(header, body)` for one fixture. Raises rather than returning an empty body (§4).

    A missing fixture is a broken test and not an empty page, and a test handed "" would report a
    parser returning nothing as correct behaviour.
    """
    p = path_of(name)
    if not p.exists():
        raise FileNotFoundError(f"no fixture {name}; {p} does not exist")
    return split(p.read_text(encoding="utf-8"), str(p))


def split(text, where="<text>"):
    head, sep, body = text.partition(f"\n{SEP}\n")
    if not sep:
        raise ValueError(f"{where}: no '{SEP}' line separating the header from the body")
    meta = yaml.safe_load(head) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"{where}: the header is not a mapping")
    return meta, body


def load(name):
    """The markup, for a test to hand to a parser."""
    return read(name)[1]


def header(name):
    return read(name)[0]


def names():
    return sorted(str(p.relative_to(DIR))[: -len(".fixture")]
                  for p in DIR.rglob("*.fixture")) if DIR.exists() else []


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── cutting a page down ───────────────────────────────────────────────────────────────────────

def element(text, anchor, nth=1):
    """`(start, end)` of the whole element the `nth` occurrence of `anchor` opens.

    WHY A TAG WALK AND NOT A WINDOW OF BYTES. The first version of this took N characters either
    side of the anchor, which is easy and cuts through a tag, and a fixture whose markup does not
    close is a fixture that tests the parser's error handling by accident. Counting the tag's own
    opens and closes gives whole elements, which is what a parser is written against.

    Raises when the anchor is not there. A cut that silently kept nothing would produce a fixture
    that passes every test by containing no counter-case at all, which is the failure this module
    exists to prevent, so it is loud.
    """
    if not anchor.startswith("<"):
        raise ValueError(f"an anchor names an element and must start with '<': {anchor!r}")
    at, found = -1, 0
    while found < nth:
        at = text.find(anchor, at + 1)
        if at < 0:
            raise ValueError(f"anchor {anchor!r} occurs fewer than {nth} time(s) in the page")
        found += 1
    tag = re.match(r"<([A-Za-z][A-Za-z0-9]*)", anchor).group(1).lower()
    close = text.find(">", at)
    if close < 0:
        raise ValueError(f"anchor {anchor!r} opens a tag that never closes")
    if tag in VOID or text[close - 1] == "/":
        return at, close + 1
    depth, i = 1, close + 1
    pat = re.compile(rf"<(/?){tag}\b", re.I)
    while depth:
        m = pat.search(text, i)
        if not m:
            raise ValueError(f"<{tag}> opened at {at} is never closed")
        depth += -1 if m.group(1) else 1
        i = m.end()
    return at, text.find(">", i) + 1


def cut(text, keep):
    """The named elements, in document order, with overlaps merged.

    Document order matters: `nicovideo.parse` slices the page at `id="episode_list"` before reading
    episodes, so a fixture that reordered the blocks would answer differently from the page.
    Repeating an anchor takes its next occurrence, which is how a page carrying two `meta_info`
    blocks contributes both.
    """
    spans, seen = [], {}
    for anchor in keep:
        # An Atom feed holds one `<entry>` per chapter and the count is not the fixture author's
        # business, so `<entry>*` takes all of them. Naming a number would make the fixture stale
        # the next time the series published.
        if anchor.endswith("*"):
            anchor, n = anchor[:-1], 0
            while True:
                n += 1
                try:
                    spans.append(element(text, anchor, n))
                except ValueError:
                    if n == 1:
                        raise
                    break
            continue
        seen[anchor] = seen.get(anchor, 0) + 1
        spans.append(element(text, anchor, seen[anchor]))
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return "\n".join(text[a:b] for a, b in merged)


def trim(text, spec):
    """Keep the first `n` repeats of a child element inside a kept block, and say how many went.

    WHY A BLOCK CAN BE WORTH KEEPING AND TOO BIG TO KEEP WHOLE. ニコニコ's sidebar is the whole
    reason these fixtures exist: it renders a banner for every official channel on the site, the
    first of them ニコニコ漫画（公式）, and a channel pattern that is not scoped to the breadcrumb
    answers `nicomanga` for every work on the platform. It is also 41,737 bytes of the page's
    120,964, because there are 157 banners, and 156 of them repeat what the first one already
    proves.

    So the first two stay and the rest become a comment saying how many were dropped. Two rather
    than one, because a fixture holding a single banner no longer looks like a list and the next
    person to read it would not see why an unscoped pattern goes wrong.

    The count is written into the fixture instead of being silently absent: a reader who cannot
    tell a cut from a short page cannot judge either (STANDING-INSTRUCTIONS §12).
    """
    for rule in spec or []:
        a, b = element(text, rule["in"])
        block, kids = text[a:b], []
        i = 0
        while True:
            try:
                s, e = element(block, rule["keep"], len(kids) + 1)
            except ValueError:
                break
            kids.append((s, e))
            i = e
            if i >= len(block):
                break
        n = int(rule["n"])
        if len(kids) <= n:
            continue
        head = block[: kids[n - 1][1]]
        tail = block[kids[-1][1]:]
        note = f"\n<!-- fixture: {len(kids) - n} more {rule['keep']} dropped -->\n"
        text = text[:a] + head + note + tail + text[b:]
    return text


def on_json(text, walk):
    """Apply `walk` to a whole-JSON body, or to each JSON payload embedded in a script element.

    COMIC FUZ serves its chapter list as `<script id="__NEXT_DATA__" type="application/json">`,
    which is markup on the outside and data on the inside, so the reductions below have to reach
    through the tag. A page holding no JSON comes back untouched.
    """
    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        return json.dumps(walk(json.loads(stripped)), ensure_ascii=False)

    def one(m):
        return m.group(1) + json.dumps(walk(json.loads(m.group(2))), ensure_ascii=False) + m.group(3)

    return re.sub(r'(<script[^>]*application/json[^>]*>)(.*?)(</script>)', one, text, flags=re.S)


def redact(text, keys=(), over=0):
    """Replace values a fixture may not carry.

    TWO RULES, EACH DOING A DIFFERENT JOB. `keys` names fields by name, which is how REQUIREMENTS
    §2 is kept: a COMIC FUZ payload carries `longDescription`, the publisher's synopsis, and a
    fixture is committed. `over` replaces any string longer than N characters, which removes the
    signed thumbnail and page-image URLs that state no rule any parser reads.

    THE SHAPE SURVIVES, because a parser reads shapes. A redacted string is still a string and a
    redacted key is still present, so `access_of` meets the fields it will meet live.
    """
    if not keys and not over:
        return text

    def walk(v):
        if isinstance(v, dict):
            return {k: (f"[redacted: {k}]" if k in keys else walk(x)) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, str) and over and len(v) > over:
            return f"[{len(v)} chars omitted]"
        return v

    return on_json(text, walk)


def sample(text, spec):
    """Keep named records out of a long JSON list and drop the rest.

    WHY NAMED AND NOT THE FIRST N. COMIC FUZ's 球詠 carries 228 chapters in 19 volume groups and
    89 KB of payload, which is a page and not a fixture. Keeping the first twelve would keep twelve
    purchases and lose every state that made the work worth capturing: the chapter that is free,
    the unbadged one that is a チャージ and reads free over time, and the badged type 1 that is
    先行. That last shape is 85 chapters out of 354 and sits at the newest end.

    So the rule names the records by their own identifier. A fixture reduced by position is
    reduced by whatever the page happened to sort by, and the FUZ adapter was wrong for months
    about exactly the state that positional sampling would have thrown away.

    A list whose items do not carry `where` is left alone, so naming `chapterId` reaches the
    chapters and not the volume groups around them.
    """
    for rule in spec or []:
        key, values = rule["where"], set(rule["values"])

        def walk(v, key=key, values=values):
            if isinstance(v, list):
                if any(isinstance(x, dict) and key in x for x in v):
                    return [walk(x) for x in v if isinstance(x, dict) and x.get(key) in values]
                return [walk(x) for x in v]
            if isinstance(v, dict):
                return {k: walk(x) for k, x in v.items()}
            return v

        text = on_json(text, walk)
    return text


def derive(page, meta, keep=True):
    """The body a header says it produces, applied to a whole page. One producer of this rule.

    `capture` writes with it and `recheck` re-derives with it, so a fixture that has drifted is a
    statement about the PAGE. Two copies of the reduction would make it a statement about which
    copy ran (STANDING-INSTRUCTIONS §3).

    TWO KINDS OF REDUCTION, AND ONLY ONE OF THEM IS GUARDED. `keep` is a structural cut: it drops
    blocks and claims the parser reads none of them, which is a claim a machine can test by
    running the parser both ways, and `agrees` does. `trim`, `sample` and `redact` change what the
    kept blocks CONTAIN, on purpose, so no comparison can approve them. They are declared in the
    header and defended in `why`, and `keep=False` is how `agrees` holds them constant on both
    sides of its comparison.
    """
    text = cut(page, meta["keep"]) if keep else page
    return redact(sample(trim(text, meta.get("trim")), meta.get("sample")),
                  keys=set(meta.get("redact") or []), over=int(meta.get("redact_over") or 0))


# ── the agreement that stops a cut going too far ──────────────────────────────────────────────

def callable_at(ref):
    """`adapters/nicovideo/releases.py:parse` -> the function.

    Loaded by path with the module's own directory on sys.path, because these adapters import
    their siblings by bare name the way the test runner runs them.
    """
    rel, _, fn = ref.partition(":")
    p = (ROOT / rel).resolve()
    sys.path.insert(0, str(p.parent))
    spec = importlib.util.spec_from_file_location(f"_fx_{p.stem}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, fn)


def agrees(page, body, meta):
    """Whether the parser reads the cut page the same way it reads the whole one.

    THIS IS THE GUARD AGAINST CUTTING TOO FAR, and it is why `capture` takes a whole page rather
    than a snippet somebody pasted. A cut that drops a block the parser reads changes the answer.

    THE DECLARED REDUCTIONS RUN ON BOTH SIDES, so what is compared is the cut alone. See `derive`
    for why those cannot be approved by comparison.

    WHAT THIS CANNOT SEE. A cut that drops the COUNTER-CASE leaves the answer unchanged, which is
    exactly why the ニコニコ sidebar looks droppable. Nothing mechanical catches that, so `why`
    carries it in words, and `check.py` refuses a fixture whose `why` is empty.
    """
    fn = callable_at(meta["agrees_with"])
    return fn(derive(page, meta, keep=False)), fn(body)


# ── the CLI ───────────────────────────────────────────────────────────────────────────────────

def source_page(url, cached_as, fetch):
    """The whole page, from the cache entry named in the header or from the network.

    FETCHING IS A DELIBERATE ACT SOMEBODY RUNS. `./test.py` blocks sockets in every child, so
    nothing under it can reach this, and that is the intended shape: creating a fixture is a
    person's decision and running a test is not.
    """
    if cached_as:
        p = paths.CACHE_ROOT / cached_as
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
        if not fetch:
            raise SystemExit(f"no cache entry {cached_as}; pass --fetch to read the page instead")
    if not fetch:
        raise SystemExit("give --cached-as <dir/entry> or --fetch")
    # THE SEAM IS net.py, WHICH IS NOT EDITED HERE. It already carries the user agent, the per-host
    # pause and the redirect reporting this would otherwise duplicate, and duplicating a fetch is
    # how twenty-seven adapters ended up agreeing on nothing.
    import net
    r = net.fetch(url, paths.CACHE_ROOT / "fixture-capture", max_age_days=0)
    if not r.text:
        raise SystemExit(f"{url}: {r.error or r.status}")
    if r.moved:
        print(f"NOTE: {url} redirected to {r.final_url}; the fixture records the address asked for")
    return r.text


def _trim_rule(s):
    """`<div id="mg_official"|<li>|2` as the header records it."""
    a, b, n = s.split("|")
    return {"in": a, "keep": b, "n": int(n)}


def _sample_rule(s):
    """`chapterId=2933,47947` as the header records it. Numbers stay numbers."""
    key, _, vals = s.partition("=")
    return {"where": key, "values": [int(v) if v.lstrip("-").isdigit() else v
                                     for v in vals.split(",")]}


def cmd_capture(a):
    page = source_page(a.url, a.cached_as, a.fetch)
    meta = {"url": a.url, "retrieved": a.retrieved,
            "captured": datetime.date.today().isoformat(),
            "cached_as": a.cached_as, "format": a.format,
            "source_bytes": len(page.encode("utf-8")), "source_sha256": sha(page),
            "keep": list(a.keep), "trim": [_trim_rule(t) for t in a.trim],
            "sample": [_sample_rule(s) for s in a.sample],
            "redact": list(a.redact_key), "redact_over": a.redact_over,
            "agrees_with": a.agrees_with, "why": a.why.strip()}
    body = derive(page, meta)
    if a.agrees_with:
        whole, part = agrees(page, body, meta)
        if whole != part:
            print(f"CUT TOO FAR: {a.agrees_with} reads the whole page and the cut differently.")
            print(f"  whole page : {whole!r}")
            print(f"  the cut    : {part!r}")
            return 1
    meta["body_sha256"] = sha(body)
    p = path_of(a.name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=True)
                 + f"{SEP}\n" + body, encoding="utf-8")
    kept = len(body.encode("utf-8"))
    print(f"wrote {p.relative_to(ROOT)}: {kept} bytes kept of {meta['source_bytes']} "
          f"({kept * 100 // max(meta['source_bytes'], 1)}%)")
    return 0


def cmd_list(a):
    total = 0
    for n in names():
        m = header(n)
        b = len(load(n).encode("utf-8"))
        total += b
        print(f"  {n:44} {b:7} of {m.get('source_bytes', 0):8}  {m.get('retrieved')}  "
              f"{m.get('url')}")
    print(f"\n{len(names())} fixture(s), {total} bytes")
    return 0


def problems(name, text=None):
    """Everything wrong with one fixture, as sentences. Empty means the header holds up.

    TAKES THE TEXT AND NOT ONLY THE NAME, so `check.py` can plant a canary in front of it. A check
    that opens its own file cannot be shown one, and check.py's canary run then reports it healthy
    having exercised nothing (STANDING-INSTRUCTIONS §14b). This is the only definition of a
    well-formed fixture; the gate and the command below both call it rather than holding a copy
    each.

    (Spelling the flag out here would make ./test.py collect this module as a self-testing one,
    which is a discovery rule keyed on the string and worth knowing about before it bites.)
    """
    bad = []
    try:
        meta, body = split(text, name) if text is not None else read(name)
    except Exception as e:                                                      # noqa: BLE001
        return [f"{name}: unreadable ({type(e).__name__}: {e})"]
    for k in REQUIRED:
        if not meta.get(k):
            bad.append(f"{name}: states no {k}")
    if meta.get("body_sha256") and sha(body) != meta["body_sha256"]:
        bad.append(f"{name}: the markup does not match the body_sha256 its header records, so it "
                   "has been edited by hand since it was captured")
    if not str(meta.get("url", "")).startswith(("http://", "https://")):
        bad.append(f"{name}: `url` is not an address a page was fetched from")
    return bad


def cmd_verify(a):
    bad = [b for n in names() for b in problems(n)]
    for b in bad:
        print(f"  {b}")
    print(f"{len(names())} fixture(s), {len(bad)} problem(s)")
    return 1 if bad else 0


def shape(v):
    """What a parser's answer is MADE OF, with the values thrown away.

    WHY NOT COMPARE THE ANSWER ITSELF. A live work page changes every time the work updates: a new
    chapter, a later 更新 date, one more episode rendered. A recheck that reported all of those
    would report something on nearly every fixture on nearly every run, and a report that is
    always full is a report nobody reads (STANDING-INSTRUCTIONS §13).

    What is worth a person's attention is a field that has STOPPED coming back, which is what a
    moved selector looks like from outside and what `incomplete attested rows` counts after the
    fact. So the comparison is on the keys, and the fixture drifting in its values is not news.
    """
    if isinstance(v, dict):
        return {k: shape(x) for k, x in sorted(v.items()) if x not in (None, "", [], {})}
    if isinstance(v, list):
        out = {}
        for x in v:
            out.update(shape(x) if isinstance(x, dict) else {})
        return [out] if out else ["..."] if v else []
    return type(v).__name__


def cmd_recheck(a):
    """Re-derive every fixture from its source and say where the page has moved under it.

    IT REPORTS AND EXITS 0. A ニコニコ page that changed since it was captured is worth a person
    reading, and it is no reason to fail a commit that touched something else. A check that fires
    on the calendar gets switched off rather than obeyed. `--strict` is for whoever wants to act on
    it, and Stage A runs it plain so the finding lands in the run log.

    IT READS THE CACHES, NOT THE NETWORK. The pages are already on disk, refilled by every capture
    run, so this costs a second and needs nobody's permission. `--fetch` is there for a fixture
    whose cache entry has been cleared.
    """
    gone, thinner, unseen = 0, 0, 0
    for n in names():
        meta, body = read(n)
        try:
            page = source_page(meta["url"], meta.get("cached_as"), a.fetch)
        except SystemExit as e:
            unseen += 1
            print(f"  ?        {n}: {e}")
            continue
        if sha(page) == meta.get("source_sha256"):
            print(f"  same     {n}: the page is byte for byte what it was")
            continue
        try:
            fresh = derive(page, meta)
        except ValueError as e:
            gone += 1
            print(f"  GONE     {n}: the page no longer holds what this fixture cuts. {e}")
            continue
        if not meta.get("agrees_with"):
            print(f"  content  {n}: the page has changed and nothing here can say whether it "
                  "still parses, because the header names no callable to agree with")
            continue
        today, held = (shape(x) for x in agrees(page, body, meta))
        if today == held:
            print(f"  ok       {n}: the page has changed and {meta['agrees_with']} still reads "
                  "the same fields off it")
            continue
        thinner += 1
        print(f"  THINNER  {n}: {meta['agrees_with']} reads different fields off today's page "
              f"than off this fixture, captured {meta['retrieved']}")
        for line in difflib.unified_diff(json.dumps(held, indent=1, ensure_ascii=False).splitlines(),
                                         json.dumps(today, indent=1, ensure_ascii=False).splitlines(),
                                         "the fixture", "today", lineterm=""):
            print(f"             {line}")
    print(f"\n{len(names())} fixture(s): {gone} whose blocks are gone, {thinner} the parser now "
          f"reads differently, {unseen} with no copy to compare against")
    # A RECHECK THAT COMPARED NOTHING IS NOT A CLEAN RECHECK. On 2026-08-10 CI ran this with a cold
    # cache and every one of the 11 fixtures had no copy to read, so the line above said "0 the
    # parser now reads differently" and the whole point of the step had not happened. That zero is
    # indistinguishable from a clean bill, which is the thing `check.UNMEASURED` exists to stop
    # elsewhere in this project. It says so here instead, and says it in the exit code, because the
    # workflow step runs `continue-on-error` and a red step is how it reaches a person.
    if unseen and unseen == len(names()):
        print("  NOTHING WAS COMPARED. Every fixture names a cache entry this run does not hold, so "
              "this step made no assertion about any parser. Pass --fetch to read the pages, or run "
              "it where the caches are warm.")
        return 2
    return 1 if ((gone or thinner) and a.strict) else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("capture", help="cut one real page down into a committed fixture")
    c.add_argument("name", help="nicovideo/work-kirara")
    c.add_argument("--url", required=True)
    c.add_argument("--retrieved", required=True, help="the day the page was fetched")
    c.add_argument("--cached-as", help="entry beside the repository, as dir/name")
    c.add_argument("--fetch", action="store_true", help="read the live page")
    c.add_argument("--keep", action="append", required=True, metavar="ANCHOR")
    c.add_argument("--trim", action="append", default=[], metavar="IN|CHILD|N",
                   help="keep the first N repeats of CHILD inside the block at IN")
    c.add_argument("--sample", action="append", default=[], metavar="KEY=V,V",
                   help="in a JSON list, keep only the records whose KEY is one of these")
    c.add_argument("--redact-key", action="append", default=[])
    c.add_argument("--redact-over", type=int, default=0)
    c.add_argument("--agrees-with", metavar="FILE.py:func")
    c.add_argument("--format", default="html")
    c.add_argument("--why", required=True, help="what these blocks are here to prove")
    c.set_defaults(fn=cmd_capture)

    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)

    r = sub.add_parser("recheck")
    r.add_argument("--fetch", action="store_true", help="read the live pages, not the caches")
    r.add_argument("--strict", action="store_true", help="exit 1 when a fixture has drifted")
    r.set_defaults(fn=cmd_recheck)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
