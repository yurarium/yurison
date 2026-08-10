#!/usr/bin/env python3
"""fixtures.py: cutting a real page down without cutting the counter-case out.

COVERS = ['adapters/fixtures.py']

WHAT THIS HAS TO PROVE, beyond that the functions run. A fixture library is a checking mechanism,
and a checking mechanism that cannot be shown to catch anything is the failure this project meets
more than any other (STANDING-INSTRUCTIONS §4). So the drift paths are exercised on planted pages:
an anchor that has disappeared, and a parser that has stopped reading a field. Both are the
conditions `recheck` exists to report, and neither can be reached by running it against the caches,
because the caches agree with the fixtures today.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fixtures
import testkit

PAGE = """<html>
<head><title>A work</title></head>
<body>
<div id="side"><ul><li>one</li><li>two</li><li>three</li><li>four</li></ul></div>
<div class="meta"><div class="inner">the date</div></div>
<img src="x.png">
<script id="__NEXT_DATA__" type="application/json">
{"items": [{"id": 1, "note": "keep me", "blurb": "a synopsis"},
           {"id": 2, "note": "drop me", "blurb": "another synopsis"}],
 "groups": [{"name": "no id here", "long": "0123456789012345678901234567890123456789"}]}
</script>
</body></html>"""


def payload(page):
    """The JSON out of the page's script element, the way an adapter reads it."""
    return json.loads(page.split('application/json">', 1)[1].rsplit("</script>", 1)[0])


def main(s):
    # ── the tag walk ──────────────────────────────────────────────────────────────────────────
    #
    # A NESTED DIV IS THE CASE THAT DECIDES THIS. Taking bytes to the next `</div>` would cut the
    # meta block off at its own inner element and leave markup that does not close, which is a
    # fixture testing the parser's error handling by accident.
    a, b = fixtures.element(PAGE, '<div class="meta">')
    s.eq(PAGE[a:b], '<div class="meta"><div class="inner">the date</div></div>',
         "an element is taken whole, past the close tag of anything nested inside it")

    a, b = fixtures.element(PAGE, "<img")
    s.eq(PAGE[a:b], '<img src="x.png">', "a void element is its own tag and needs no close")

    s.raises(ValueError, lambda: fixtures.element(PAGE, "<nothing"),
             "an anchor that is not on the page raises rather than keeping nothing")
    s.raises(ValueError, lambda: fixtures.element(PAGE, 'class="meta"'),
             "an anchor that does not name an element is refused")
    s.raises(ValueError, lambda: fixtures.element(PAGE, "<li>", 9),
             "asking for a repeat the page does not have raises")
    s.eq(fixtures.element(PAGE, "<li>", 2)[0], PAGE.find("<li>two"),
         "a repeated anchor can be taken by occurrence")

    # ── the cut ───────────────────────────────────────────────────────────────────────────────
    #
    # DOCUMENT ORDER IS NOT THE ORDER THE ANCHORS WERE WRITTEN IN. nicovideo.parse slices the page
    # at `id="episode_list"` before reading episodes, so a fixture that reordered the blocks would
    # answer differently from the page it came from.
    out = fixtures.cut(PAGE, ['<div class="meta">', "<title>"])
    s.check(out.index("<title>") < out.index('<div class="meta">'),
            "blocks come back in the order the page has them, not the order they were asked for")

    s.eq(fixtures.cut(PAGE, ['<div class="meta">', '<div class="inner">']),
         '<div class="meta"><div class="inner">the date</div></div>',
         "a block inside another is merged instead of being emitted twice")

    s.eq(fixtures.cut(PAGE, ["<li>*"]).count("<li>"), 4,
         "a starred anchor takes every occurrence, which is what an Atom feed of entries needs")

    # ── trimming a repeated child ─────────────────────────────────────────────────────────────
    trimmed = fixtures.trim(fixtures.cut(PAGE, ['<div id="side">']),
                            [{"in": '<div id="side">', "keep": "<li>", "n": 2}])
    s.eq(trimmed.count("</li>"), 2, "only the first two repeats are kept")
    s.check("three" not in trimmed and "four" not in trimmed, "and the rest are gone")
    s.check("2 more <li> dropped" in trimmed,
            "and the fixture says how many went, because a reader who cannot tell a cut from a "
            "short page cannot judge either")
    s.check(trimmed.rstrip().endswith("</div>"),
            "the block still closes, so the markup around the cut is intact")

    # ── sampling a JSON list by name ──────────────────────────────────────────────────────────
    #
    # NAMED AND NOT POSITIONAL. On COMIC FUZ the free chapters are the oldest and the 先行 ones the
    # newest, so keeping the first N keeps one state and throws away the three that made the page
    # worth capturing.
    sampled = payload(fixtures.sample(PAGE, [{"where": "id", "values": [2]}]))
    s.eq([i["id"] for i in sampled["items"]], [2], "only the named record survives")
    s.eq(len(sampled["groups"]), 1,
         "a list whose records do not carry the named key is left alone, so naming a chapter id "
         "does not empty the volume groups around it")

    # ── redaction ─────────────────────────────────────────────────────────────────────────────
    red = fixtures.redact(PAGE, keys={"blurb"}, over=20)
    s.check("a synopsis" not in red,
            "a named key is taken out, which is how a publisher synopsis stays out of the "
            "repository (REQUIREMENTS §2)")
    s.check("0123456789012345678901234567890123456789" not in red,
            "and any string past the limit goes with it")
    s.check("keep me" in red, "while a short value nobody named survives")
    body = payload(red)
    s.eq(sorted(body["items"][0]), ["blurb", "id", "note"],
         "THE SHAPE SURVIVES: a redacted key is still present, so a parser meets the fields it "
         "will meet live")
    s.eq(fixtures.redact(PAGE, keys=set(), over=0), PAGE,
         "a fixture that redacts nothing is left byte for byte alone")

    # ── the guard against cutting too far ─────────────────────────────────────────────────────
    #
    # This is the whole reason `capture` takes a page rather than a snippet. The counter-case here
    # is the ニコニコ one in miniature: `channel` reads the breadcrumb, so a cut that keeps only
    # the sidebar changes its answer and a cut that keeps only the breadcrumb does not.
    ref = "adapters/nicovideo/releases.py:channel"
    nico = fixtures.load("nicovideo/work-in-a-channel")
    meta = {"agrees_with": ref, "keep": ['<ul class="sg_pankuzu">']}
    whole, part = fixtures.agrees(nico, fixtures.derive(nico, meta), meta)
    s.eq(whole, part, "a cut that keeps the block the parser reads agrees with the whole page")

    thin = {"agrees_with": ref, "keep": ['<div id="mg_official"']}
    whole, part = fixtures.agrees(nico, fixtures.derive(nico, thin), thin)
    s.ne(part, whole, "and a cut that drops it does not, which is what capture refuses on")
    s.eq(part, {}, "the over-cut page answers with nothing at all here")

    # ── what a well-formed fixture is ─────────────────────────────────────────────────────────
    held = fixtures.names()
    s.check(len(held) >= 4, "the library holds fixtures to check")
    s.eq([p for n in held for p in fixtures.problems(n)], [],
         "every committed fixture states where it came from and matches its own digest")
    for n in held:
        s.check(len(fixtures.header(n).get("why", "")) > 40,
                f"{n} says in words what its blocks are there to prove")

    # A CHECK THAT CANNOT BE SHOWN TO CATCH SOMETHING IS NOT A CHECK. These plant the two faults
    # `problems` exists for, on a fixture written into a temporary directory so nothing committed
    # is touched.
    import tempfile
    real = fixtures.DIR
    try:
        with tempfile.TemporaryDirectory() as d:
            fixtures.DIR = pathlib.Path(d)
            good = ("body_sha256: " + fixtures.sha("<p>x</p>") + "\ncaptured: '2026-08-08'\n"
                    "keep:\n- <p>\nretrieved: '2026-08-01'\nsource_bytes: 9\n"
                    "source_sha256: aa\nurl: https://example.invalid/x\nwhy: because\n"
                    "---\n<p>x</p>")
            fixtures.path_of("t/ok").parent.mkdir(parents=True)
            fixtures.path_of("t/ok").write_text(good)
            s.eq(fixtures.problems("t/ok"), [], "the planted fixture is accepted as it stands")

            fixtures.path_of("t/edited").write_text(good.replace("<p>x</p>\n---", "<p>x</p>\n---")
                                                    .replace("---\n<p>x</p>", "---\n<p>edited</p>"))
            s.check(any("edited by hand" in p for p in fixtures.problems("t/edited")),
                    "a body changed after capture is caught, which is the way a fixture gets "
                    "quietly reshaped to make a test pass")

            fixtures.path_of("t/anon").write_text(good.replace("why: because", "why: ''"))
            s.check(any("states no why" in p for p in fixtures.problems("t/anon")),
                    "a fixture nobody explained is refused")

            fixtures.path_of("t/nowhere").write_text(
                good.replace("url: https://example.invalid/x", "url: somewhere"))
            s.check(any("not an address" in p for p in fixtures.problems("t/nowhere")),
                    "and so is one whose provenance is not an address a page was fetched from")

            fixtures.path_of("t/headless").write_text("<p>x</p>")
            s.check(fixtures.problems("t/headless"),
                    "a file with no header at all is a problem and not an empty fixture")
    finally:
        fixtures.DIR = real

    s.raises(FileNotFoundError, lambda: fixtures.load("nicovideo/no-such-fixture"),
             "a test naming a fixture that is not there fails loudly rather than parsing ''")

    # ── the drift report ──────────────────────────────────────────────────────────────────────
    #
    # `shape` decides what recheck calls news. A live work page changes whenever the work updates,
    # so comparing answers would report something on nearly every fixture on nearly every run, and
    # a report that is always full is one nobody reads (§13).
    s.eq(fixtures.shape({"updated": "2026-07-28", "channel": "きららベース"}),
         fixtures.shape({"updated": "2026-08-30", "channel": "コミックNewtype"}),
         "a page whose values moved on reads the same, because that is not a finding")
    s.ne(fixtures.shape({"updated": "2026-07-28", "channel": "きららベース"}),
         fixtures.shape({"updated": "2026-07-28"}),
         "a field that has stopped coming back does not, which is what a moved selector looks "
         "like from outside")
    s.ne(fixtures.shape({"updated": "2026-07-28", "channel": "きららベース"}),
         fixtures.shape({"updated": "2026-07-28", "channel": ""}),
         "and so does one that comes back empty, which is how this fails in practice")
    s.eq(fixtures.shape([{"a": 1}, {"b": 2}]), [{"a": "int", "b": "int"}],
         "a list is read as the union of what its records carry, so a shorter list is not drift")

    # The two conditions recheck reports, planted on the real page so the planting is not the
    # thing being tested. Removing the breadcrumb is a selector that has moved; removing the
    # sidebar is a block that is gone.
    moved = nico.replace('<ul class="sg_pankuzu">', '<ul class="sg_navigation">')
    s.raises(ValueError, lambda: fixtures.derive(moved, meta),
             "a page that no longer holds the block a fixture cuts is caught by the cut itself")

    live = {"agrees_with": "adapters/nicovideo/releases.py:parse", "keep": []}
    today = fixtures.callable_at(live["agrees_with"])(moved)
    held_answer = fixtures.callable_at(live["agrees_with"])(nico)
    s.ne(fixtures.shape(today), fixtures.shape(held_answer),
         "and where the block survives under a new name, the parser reads fewer fields off it, "
         "which is the THINNER line in the report")
    s.check("channel" not in (today or {}),
            "specifically the channel, which is the field that went")

    a_recheck_that_compared_nothing(s)


def a_recheck_that_compared_nothing(s):
    """A recheck with no cache to read makes no assertion, and has to say so in its exit code.

    THE RUN THAT SHOWED IT. CI on 2026-08-10 had a cold cache, so all 11 fixtures reported no copy
    to compare against and the summary read "0 the parser now reads differently". Zero findings and
    zero comparisons print the same way, and the step is `continue-on-error`, so it passed silently
    while asserting nothing about any parser.
    """
    import os
    import subprocess
    import tempfile

    root = pathlib.Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as empty:
        env = {**os.environ, "YURI_CACHE": empty}
        r = subprocess.run([sys.executable, str(root / "adapters" / "fixtures.py"), "recheck"],
                           capture_output=True, text=True, cwd=str(root), env=env, timeout=120)
        s.eq(r.returncode, 2, "a recheck that could compare nothing exits non-zero")
        s.check("NOTHING WAS COMPARED" in r.stdout,
                "and says so, because the count of findings above it reads the same either way")
        s.check("with no copy to compare against" in r.stdout,
                "beside the count of how many it could not read")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "fixtures"))
