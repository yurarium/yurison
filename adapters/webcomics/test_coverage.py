#!/usr/bin/env python3
"""webcomics/coverage.py: the antenna's normalisation.

COVERS = ['adapters/webcomics/coverage.py']

The antenna is Tier C: it says a work exists and where, and nothing it says becomes a record. What
it DOES decide is whether two mentions are one work, so the normalisation below is load-bearing.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit
import coverage as wc


def main(s):
    s.eq(wc.norm("ＹＵＲＩ"), wc.norm("yuri"), "width and case fold")
    s.eq(wc.norm("百合 の 花"), wc.norm("百合の花"), "spacing is not identity")
    s.ne(wc.norm("百合"), wc.norm("薔薇"), "different titles stay different")
    s.eq(wc.norm(None), "", "None normalises rather than raising")

    # The invisible characters this source actually emits. 竹コミ with a U+200E compared unequal to
    # 竹コミ, so one platform appeared as two and nothing showed in a diff.
    s.eq(wc.norm("竹コミ‎‏"), wc.norm("竹コミ"), "bidi marks are stripped")
    s.eq(wc.norm("百​合"), wc.norm("百合"), "a zero-width space is stripped")
    s.eq(wc.norm("﻿竹コミ"), wc.norm("竹コミ"), "a byte-order mark is stripped")

    # TWO NORMALISERS, ONE JOB, AND THEY DISAGREE. coverage_union.norm strips "+" and this one
    # keeps it, so 少年ジャンプ+ and 花とゆめ+ lose their plus on one path and not the other. No
    # collision exists in the current data, because the magazines 少年ジャンプ and 花とゆめ are not
    # platform names here, so this is latent rather than live. Both behaviours are pinned so the
    # difference cannot be erased by tidying one into the other without deciding which is right.
    s.eq(wc.norm("少年ジャンプ+"), "少年ジャンプ+", "this source keeps the plus")
    s.ne(wc.norm("少年ジャンプ+"), wc.norm("少年ジャンプ"), "so the platform is distinct from the magazine")

    the_health_check_fires_on_nothing(s)


def the_health_check_fires_on_nothing(s):
    """A page yielding nothing is the loudest signal there is, and it left here quietly.

    `if not rows: break` sat ABOVE the health check, so 1 to 9 entries on page 1 exited with
    HEALTH and 0 entries broke out of the loop and reported success. Every CI run of this pass
    printed `listings: 0 over 8 page(s)` and returned 0, which is why nobody looked at it.
    """
    import subprocess
    import tempfile

    here = pathlib.Path(__file__).resolve()
    root = here.parents[2]

    def run(pages):
        """The CLI against a seeded cache, which `fetch` reads instead of the network."""
        with tempfile.TemporaryDirectory() as d:
            cache, out = pathlib.Path(d) / "c", pathlib.Path(d) / "out"
            cache.mkdir()
            for n, body in pages.items():
                (cache / f"page{n}.html").write_text(body)
            return subprocess.run(
                [sys.executable, str(here.parent / "coverage.py"), "--out", str(out),
                 "--cache", str(cache), "--retrieved", "2026-08-10", "--pages", "3"],
                capture_output=True, text=True, cwd=str(root), timeout=120)

    empty = "<html><body>nothing here</body></html>"
    r = run({1: empty, 2: empty, 3: empty})
    s.ne(r.returncode, 0, "page 1 yielding nothing fails rather than reporting a clean zero")
    s.check("HEALTH" in (r.stdout + r.stderr),
            "and says the markup moved or the host served something else")

    # AND AN EMPTY PAGE AFTER THE FIRST IS THE END OF THE LISTING, which is ordinary and must
    # not fail. The counter-case is what stops the fix turning pagination into an error.
    # BUILT FROM THE SHAPE `parse` READS, in the fields it names, and short enough that no literal
    # here is pretending to be a page: the entry block, the title anchor, and nothing else.
    entry = ('<div class="entry"><div class="entry-title"><a href="https://x.test/{i}">t{i}</a>'
             '</div><div class="entry-date">2026/08/10</div></div>')
    full = "".join(entry.format(i=i) for i in range(12))
    r2 = run({1: full, 2: empty, 3: empty})
    s.eq(r2.returncode, 0, "a full first page and an empty second is the end of the list")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "webcomics.coverage"))
