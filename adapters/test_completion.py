#!/usr/bin/env python3
"""completion.py: what a reviewed verdict must show before it counts."""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit  # noqa: E402
import completion as comp  # noqa: E402

COVERS = ["adapters/completion.py"]

OK = {"verdict": "completed", "basis": "the final chapter's page says 完結",
      "source": "COMIC FUZ", "source_kind": "platform",
      "source_url": "https://example.invalid/1", "reviewed": "2026-08-04"}


def main(s):
    s.eq(comp.problems("W", OK), [], "a verdict with a cited page")
    s.check(comp.problems("W", {k: v for k, v in OK.items() if k != "basis"}),
            "a verdict with no basis is an opinion with a schema")
    s.check(comp.problems("W", {k: v for k, v in OK.items() if k != "source_url"}),
            "platform evidence without the page it was read from")
    s.check(not comp.problems("W", dict(OK, source_kind="derived", source_url=None)),
            "a reviewer's own reasoning owes no page, because it cites none")
    s.check(comp.problems("W", dict(OK, verdict="finished")),
            "a verdict outside the three is refused")
    s.check(comp.problems("W", dict(OK, ended_on="not-a-date")), "and a date that is not one")
    s.check(comp.problems("W", dict(OK, wat=1)), "an unknown key is an error, not ignored")

    # UNSETTLED CLAIMS NOTHING, so it owes no citation. It still owes a sentence, or it cannot be
    # told apart from nobody having looked, which is the state it exists to replace.
    s.eq(comp.problems("W", {"verdict": "unsettled", "reviewed": "2026-08-04",
                             "basis": "the platform page is gone and no archive holds it"}), [],
         "an unsettled verdict needs no source")
    s.check(comp.problems("W", {"verdict": "unsettled", "reviewed": "2026-08-04"}),
            "but it does need to say what was looked at")

    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "c.yaml"
        f.write_text("works:\n  A:\n    verdict: completed\n  B:\n    verdict: unsettled\n"
                     "  C:\n    verdict: continuing\n")
        got = comp.verdicts(f)
        s.eq(sorted(got), ["A", "C"], "unsettled decides nothing and is not returned")
        s.eq(comp.verdicts(pathlib.Path(d) / "absent.yaml"), {},
             "no file is no verdicts, not a crash")


if __name__ == "__main__":
    raise SystemExit(testkit.run(main, pathlib.Path(__file__).name))
