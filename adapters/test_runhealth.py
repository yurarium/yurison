#!/usr/bin/env python3
"""runhealth.py: a source's failures are counted across runs and become one issue, then none.

COVERS = ['adapters/runhealth.py']
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testkit                                                          # noqa: E402
import runhealth as rh                                                  # noqa: E402


def main(s):
    down = {"id": "comicboost", "ok": False, "error": "HTTP 503", "stage": "stage-a"}
    up = {"id": "comicboost", "ok": True, "stage": "stage-a"}
    other = {"id": "kadokomi", "ok": True, "stage": "stage-a"}

    led = rh.record({}, [down, other], "2026-10-15", "run/1")
    e = led["sources"]["comicboost"]
    s.eq((e["consecutive"], e["failing_since"], e["error"]), (1, "2026-10-15", "HTTP 503"),
         "a failure starts a count and remembers why and since when")
    s.eq(led["sources"]["kadokomi"]["last_ok"], "2026-10-15", "and a success is dated")

    for d in ("2026-10-15b", "2026-10-16"):
        led = rh.record(led, [down], d)
    e = led["sources"]["comicboost"]
    s.eq((e["consecutive"], e["failing_since"]), (3, "2026-10-15"),
         "three runs down in a row, still dated from the first")
    s.eq(led["sources"]["kadokomi"]["last_ok"], "2026-10-15",
         "and a source not run this time is left as it was")

    acts = rh.plan(led, {})
    s.eq([(a["action"], a["title"]) for a in acts], [("open", "Source failing: comicboost")],
         "a source down three runs gets one issue")
    s.check("HTTP 503" in acts[0]["body"] and "2026-10-15" in acts[0]["body"],
            "which says why and since when")
    acts = rh.plan(led, {"Source failing: comicboost": 7})
    s.eq([(a["action"], a.get("number")) for a in acts], [("update", 7)],
         "and is updated, not duplicated, while it stays down")

    led = rh.record(led, [up], "2026-10-17")
    s.eq(led["sources"]["comicboost"]["consecutive"], 0, "a success resets the count")
    s.check("failing_since" not in led["sources"]["comicboost"], "and the run of failures ends")
    s.eq([(a["action"], a.get("number")) for a in rh.plan(led, {"Source failing: comicboost": 7})],
         [("close", 7)], "so its issue closes")

    once = rh.record({}, [down], "2026-10-15")
    s.eq(rh.plan(once, {}), [], "one bad run is recorded and raises nothing")
    s.eq(rh._parse_outcome("fieldaudit=fail:2 findings"),
         {"id": "fieldaudit", "ok": False, "error": "2 findings", "stage": "checks"},
         "a check reports its outcome in one argument")


if __name__ == "__main__":
    sys.exit(testkit.run(main, "runhealth"))
