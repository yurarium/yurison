#!/usr/bin/env python3
"""stubs.py: a citation that resolves without JavaScript, and never for a work we withdrew."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import stubs  # noqa: E402
import testkit  # noqa: E402

COVERS = ["adapters/stubs.py"]

WORK = {"id": "w00055", "work": "ぜんぶ壊して地獄で愛して", "author": "くわばらたもつ",
        "chapters": 91, "latest": "2026-07-28", "url": "https://pocket.shonenmagazine.com/x",
        "state_basis": "no chapter for 18 days, and nothing states it has ended",
        "work_en": {"en": "Break It All, Love Me in Hell"},
        "print": [{"volumes": 4, "publisher": "[頒布]講談社",
                   "imprint": "IDコミックス. Yurihime comics", "first": "2023-09"}]}


def main(s):
    h = stubs.render(WORK)
    s.check("ぜんぶ壊して地獄で愛して" in h, "the work names itself")
    s.check("Break It All, Love Me in Hell" in h, "in both languages where it has both")
    s.check("91 chapters" in h and "4 volumes in print" in h,
            "and states its two publications, which is the whole point of the join")
    s.check("no chapter for 18 days" in h, "the basis travels with the state")

    # THE CATALOGUING PREFIX IS NOT THE PUBLISHER'S NAME. MADB writes [頒布] for the distributor.
    s.check("講談社" in h and "[頒布]" not in h, "the role prefix is stripped before a reader sees it")

    # NOT INDEXED. The site's posture is deliberate and a new page must not quietly opt in.
    s.check("noindex" in h, "a stub carries the same robots posture as the page it belongs to")
    s.check('href="../../app.css"' in h, "and reaches the shared stylesheet from two levels down")

    # THE HANDOVER, which the first version got wrong. app.js renders into the interface's own
    # markup, and a stub does not carry it, so loading the bundle here left a reader on a dead page.
    s.check('src="../../app.js"' not in h, "the bundle is not loaded where there is nothing to run it on")
    s.check("location.replace" in h and "work=w00055" in h,
            "a reader with scripts is handed to the interface, at this work")

    # A STUB IS STILL A PAGE. Somebody arrives here from a citation, so it must not depend on the
    # script it also loads.
    s.check(h.startswith("<!doctype html>"), "it is a document, not a fragment")

    esc = stubs.render({"id": "w1", "work": '<script>x</script>', "work_en": {}})
    s.check("<script>x</script>" not in esc, "a title is escaped, not executed")
    s.check("&lt;script&gt;" in esc, "and survives as text")

    files = stubs.written("work", [WORK, {"id": "w00056", "work": "b"}])
    s.eq(sorted(files), ["work/w00055/index.html", "work/w00056/index.html"],
         "one file per work, at its own address")

    # AN ID BUILDS A PATH, SO IT IS CHECKED RATHER THAN TRUSTED. Ours are [A-Za-z0-9], but a stray
    # slash would write outside the tree.
    s.eq(stubs.written("work", [{"id": "../../etc/x", "work": "b"}]), {},
         "an identifier that is not one writes nothing")
    s.eq(stubs.written("work", [{"work": "no id"}]), {},
         "and a work registered since the last identity run writes nothing either")

    s.eq(stubs.summary({}), "", "nothing known, nothing claimed")
    s.eq(stubs.summary({"chapters": 3}), "3 chapters", "and only what is known is stated")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
